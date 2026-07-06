#!/usr/bin/env python3
"""
guardd — AgentOS 联邦式协同守护进程

职责：每 5 分钟执行一轮 9 模块循环，自动化跨机器协同。
安装方式：launchd (macOS) 或 crontab
周期：300 秒（可配置）

所有模块使用规则引擎，不调用 LLM，0 token 消耗。
"""
# 版本号从 01_core/VERSION 读取（唯一来源）
try:
    ver_file = Path(__file__).resolve().parent.parent.parent.parent / "01_core" / "VERSION"
    if ver_file.exists():
        for line in ver_file.read_text().splitlines():
            if line.startswith("GUARDD_VERSION="):
                version = line.split("=", 1)[1].strip()
                break
        else:
            version = "2.3.0"
    else:
        version = "2.3.0"
except Exception:
    version = "2.3.0"

import fcntl
import http.server
import json
import logging
import logging.handlers
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

# 确保 modules/ 目录在 Python 路径中
_guardd_dir = Path(__file__).resolve().parent
if str(_guardd_dir) not in sys.path:
    sys.path.insert(0, str(_guardd_dir))

# 调度引擎模块
from modules.task_store import TaskStore
from modules.priority_queue import PriorityQueue
from modules.slot_manager import BrowserSlotManager, AccountBusyError
from modules.executor import Executor
from modules.scheduler import Scheduler
from modules.heartbeat import HeartbeatReporter
from modules.oracle_sync import OracleSync

_guardd_start_time = time.time()

# ── 路径常量 ──────────────────────────────────────────────
AGENT_SYNC = Path(os.environ.get("AGENT_SYNC", str(Path.home() / "workbuddy-agent-os" / "agent-sync")))
AGENT_LOCAL = Path(os.environ.get("AGENT_LOCAL", str(Path.home() / "workbuddy-agent-os" / "agent-local")))
# ── 改造: 心跳数据写本机 local 目录, 不再污染 Gitee ──
DIR_CROSS = AGENT_LOCAL / "runtime" / "guardd"
HOSTNAME = os.uname().nodename

# ── 缓存 hostname 到文件, 防止 IP 变化导致身份漂移 ──
_CACHED_HOSTNAME_FILE = AGENT_LOCAL / "identity" / "cached_hostname"
_CACHED_HOSTNAME_FILE.parent.mkdir(parents=True, exist_ok=True)
if _CACHED_HOSTNAME_FILE.exists():
    cached = _CACHED_HOSTNAME_FILE.read_text().strip()
    if cached:
        HOSTNAME = cached
else:
    _CACHED_HOSTNAME_FILE.write_text(HOSTNAME, encoding="utf-8")

# ── 从 registry 解析注册名 ──
_REGISTRY_DIR = AGENT_SYNC / "04_memory" / "cross_machine" / "registry"
def _resolve_hostname(fallback=HOSTNAME):
    """通过缓存/MACHINE_UID/IP映射 三级降级解析注册名"""
    # 1. 缓存优先 — 防止 IP 变化导致身份漂移
    cache_file = AGENT_LOCAL / "identity" / "cached_hostname"
    if cache_file.exists():
        cached = cache_file.read_text().strip()
        if cached:
            return cached
    uid = ""
    uid_file = AGENT_LOCAL / "identity" / "machine_uid"
    if uid_file.exists():
        uid = uid_file.read_text().strip()
    raw = os.uname().nodename
    # 2. IP→hostname 映射（仅在无缓存时使用）
    ip_to_name = {
        "192.168.31.225": "chengzigedeAir",
        "192.168.31.226": "chengzigedeAir",
    }
    if raw in ip_to_name:
        return ip_to_name[raw]
    if uid and _REGISTRY_DIR.exists():
        for f in _REGISTRY_DIR.iterdir():
            if f.suffix != ".json":
                continue
            try:
                data = json.loads(f.read_text())
                if data.get("uid") == uid:
                    return data.get("hostname", fallback)
            except:
                pass
    return fallback

HOSTNAME = _resolve_hostname()

CROSS_MACHINE = AGENT_SYNC / "04_memory" / "cross_machine"
DIR_EVENTS = DIR_CROSS / "events"
DIR_STATUS = DIR_CROSS / "status"
DIR_REGISTRY = DIR_CROSS / "registry"
DIR_TASKS = CROSS_MACHINE / "tasks"
DIR_TASKS_PENDING = DIR_TASKS / "pending"
DIR_TASKS_COMPLETED = DIR_TASKS / "completed"
DIR_ENCRYPTED = CROSS_MACHINE / "encrypted"
DIR_ENCRYPTED_PENDING = DIR_ENCRYPTED / "pending"
DIR_ENCRYPTED_PROCESSED = DIR_ENCRYPTED / "processed"
DIR_KNOWLEDGE = CROSS_MACHINE / "knowledge"

DIR_REGISTRY = CROSS_MACHINE / "registry"
DIR_SECRETS = AGENT_LOCAL / "identity" / "secrets"
DIR_IDENTITY = AGENT_LOCAL / "identity"
DIR_GUARDD_LOG = AGENT_LOCAL / "runtime" / "guardd"
DIR_LOCAL_MEMORY = AGENT_LOCAL / "memory"
DIR_SUBMISSIONS = AGENT_LOCAL / "submissions"
DIR_SUBMISSIONS_TRIAGE = DIR_SUBMISSIONS / "memory_triage"
DIR_KNOWLEDGE_SYSTEM = AGENT_SYNC / "03_knowledge" / "99_system"
DIR_SUBMISSIONS_KNOWLEDGE = AGENT_SYNC / "03_knowledge" / "01_submissions"

LOG_FILE = DIR_GUARDD_LOG / "guardd.log"
LAST_RUN_FILE = DIR_GUARDD_LOG / "last_run.json"
ERROR_LOG_FILE = DIR_GUARDD_LOG / "errors.log"
VERSIONS_FILE = DIR_KNOWLEDGE / "versions.json"

# ── 任务管理器（v7 新增）──────────────────────────────────
# 管理通过 HTTP API 接收的任务进程
_task_lock = threading.Lock()
_running_tasks = {}  # run_id → {proc, cmd, status, start_time, machine}
TASK_LOG_DIR = AGENT_LOCAL / "runtime" / "guardd" / "tasks"
TASK_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _task_log_path(run_id: str) -> Path:
    return TASK_LOG_DIR / f"{run_id}.log"


def _start_task(run_id: str, cmd: str, machine: str = "") -> dict:
    """创建子进程执行命令，返回任务信息"""
    log_file = _task_log_path(run_id)
    with open(log_file, "w") as f:
        f.write(f"[{datetime.now()}] START: {cmd}\n")
    try:
        proc = subprocess.Popen(
            cmd, shell=True, stdout=open(log_file, "a"), stderr=subprocess.STDOUT,
            preexec_fn=os.setsid  # 独立进程组，方便 kill
        )
        task = {
            "run_id": run_id,
            "cmd": cmd,
            "machine": machine,
            "pid": proc.pid,
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "proc": proc,
        }
        with _task_lock:
            _running_tasks[run_id] = task
        logger.info(f"  🚀 任务已启动 [{run_id}] PID={proc.pid} cmd={cmd[:80]}")
        return {"status": "accepted", "run_id": run_id, "pid": proc.pid}
    except Exception as e:
        logger.error(f"  ❌ 任务启动失败 [{run_id}]: {e}")
        return {"status": "error", "error": str(e)}


def _stop_task(run_id: str) -> dict:
    """停止任务（SIGTERM → 2s → SIGKILL）"""
    with _task_lock:
        task = _running_tasks.get(run_id)
    if not task:
        return {"status": "error", "error": f"任务 {run_id} 不存在"}
    proc = task.get("proc")
    if not proc or proc.poll() is not None:
        task["status"] = "completed" if proc and proc.returncode == 0 else "crashed"
        return {"status": "already_stopped", "run_id": run_id}
    try:
        # SIGTERM 先礼貌终止
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        time.sleep(2)
        if proc.poll() is None:
            # 还没死 → SIGKILL
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        task["status"] = "cancelled"
        with _task_lock:
            _running_tasks[run_id] = task
        with open(_task_log_path(run_id), "a") as f:
            f.write(f"[{datetime.now()}] CANCELLED\n")
        logger.info(f"  ⏹ 任务已停止 [{run_id}] PID={proc.pid}")
        return {"status": "stopped", "run_id": run_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _get_tasks() -> list:
    """返回所有任务状态列表（不含 proc 对象）"""
    with _task_lock:
        # 更新已结束进程的状态
        for rid, t in list(_running_tasks.items()):
            proc = t.get("proc")
            if proc and proc.poll() is not None:
                t["status"] = "completed" if proc.returncode == 0 else "failed"
                t["exit_code"] = proc.returncode
                t["end_time"] = datetime.now(timezone.utc).isoformat()
        return [
            {k: v for k, v in t.items() if k != "proc"}
            for t in _running_tasks.values()
        ]


# ── HTTP 任务服务器（v7 新增）─────────────────────────────

class TaskHTTPHandler(http.server.BaseHTTPRequestHandler):
    """guardd HTTP API — 端口 9090"""

    def log_message(self, fmt, *args):
        logger.debug(f"HTTP: {args[0]} {args[1]}")

    def _send_json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/health":
            self._send_json(200, {
                "hostname": HOSTNAME,
                "version": version,
                "uptime_sec": round(time.time() - _guardd_start_time),
                "running_tasks": len([t for t in _get_tasks() if t.get("status") == "running"]),
                "total_tasks": len(_get_tasks()),
            })
        elif path == "/tasks":
            self._send_json(200, _get_tasks())
        elif path == "/scheduler/tasks":
            self._send_json(200, api_scheduler_status())
        elif path == "/scheduler/queue":
            from modules.priority_queue import PriorityQueue
            status = api_scheduler_status()
            self._send_json(200, {"queue": status.get("queue", [])})
        elif path == "/scheduler/slots":
            status = api_scheduler_status()
            self._send_json(200, status.get("slots", {}))
        elif path == "/accounts/status":
            try:
                from modules.account_monitor import AccountMonitor
                monitor = AccountMonitor()
                accts = monitor.collect_status()
                self._send_json(200, {
                    "hostname": HOSTNAME,
                    "machine_uid": MACHINE_UID,
                    "accounts": accts,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                logger.error(f"/accounts/status 采集失败: {e}")
                self._send_json(500, {"error": str(e)})
        elif path == "/accounts/profiles":
            try:
                home = __import__("pathlib").Path.home()
                pf = home / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix" / "data" / "profiles.json"
                if pf.exists():
                    profiles = json.loads(pf.read_text())
                else:
                    profiles = {}
                self._send_json(200, {
                    "hostname": HOSTNAME,
                    "machine_uid": MACHINE_UID,
                    "profiles": profiles,
                })
            except Exception as e:
                logger.error(f"/accounts/profiles 读取失败: {e}")
                self._send_json(500, {"error": str(e)})
        elif path == "/recordings":
            try:
                home = __import__("pathlib").Path.home()
                rec_dir = home / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix" / "recordings"
                rec_list = []
                if rec_dir.exists():
                    for f in sorted(rec_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                        rec_list.append({
                            "name": f.name,
                            "size": f.stat().st_size,
                            "mtime": f.stat().st_mtime,
                            "machine": HOSTNAME,
                        })
                    # 读录制文件名时附上文件内容
                    name = parsed.query.replace("name=", "") if "name=" in parsed.query else ""
                    if name:
                        rec_file = rec_dir / name
                        if rec_file.exists():
                            content = json.loads(rec_file.read_text())
                            content["_machine"] = HOSTNAME
                            self._send_json(200, {"recordings": rec_list, "detail": content})
                            return
                self._send_json(200, {"recordings": rec_list, "machine": HOSTNAME})
            except Exception as e:
                logger.error(f"/recordings 读取失败: {e}")
                self._send_json(500, {"error": str(e)})
        else:
            self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # 读取请求体
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return

        if path == "/task":
            cmd = data.get("cmd", "")
            run_id = data.get("run_id", str(uuid.uuid4().hex[:12]))
            machine = data.get("machine", HOSTNAME)
            if not cmd:
                self._send_json(400, {"error": "cmd 必填"})
                return
            result = _start_task(run_id, cmd, machine)
            self._send_json(200, result)

        elif path.startswith("/task/") and path.endswith("/stop"):
            run_id = path.split("/")[2]
            result = _stop_task(run_id)
            self._send_json(200, result)

        elif path == "/scheduler/submit":
            result = api_scheduler_submit(data)
            self._send_json(200, result)
        elif path == "/task/pause":
            _init_scheduler()
            task_id = data.get("task_id", "")
            ok = _scheduler.pause_task(task_id)
            self._send_json(200, {"status": "ok" if ok else "error", "task_id": task_id})
        elif path == "/task/resume":
            _init_scheduler()
            task_id = data.get("task_id", "")
            ok = _scheduler.resume_task(task_id)
            self._send_json(200, {"status": "ok" if ok else "error", "task_id": task_id})
        elif path == "/queue/reorder":
            _init_scheduler()
            task_id = data.get("task_id", "")
            new_priority = data.get("priority")
            move_to_front = data.get("move_to_front", False)
            ok = _scheduler.reorder_queue(task_id, new_priority, move_to_front)
            self._send_json(200, {"status": "ok" if ok else "error", "task_id": task_id})

        elif path == "/scheduler/stop":
            from modules.task_store import STATUS_FAILED
            _init_scheduler()
            if _scheduler:
                _scheduler.kill_active()
            self._send_json(200, {"status": "ok"})

        elif path == "/scheduler/reset":
            """重置调度器：杀活跃任务+清队列+杀浏览器（保留 task_store 历史）"""
            _init_scheduler()
            if _scheduler:
                _scheduler.kill_active()
                # 清空优先级队列
                _scheduler.queue = PriorityQueue()
            import os
            for p in ["camoufox", "firefox", "mc run"]:
                os.system('pkill -f ' + p + ' 2>/dev/null')
            self._send_json(200, {"status": "ok", "message": "reset: tasks killed, browsers killed, queue cleared"})

        else:
            self._send_json(404, {"error": "not_found"})


def _run_http_server():
    """在后台线程启动 HTTP 服务器"""
    server = http.server.HTTPServer(("0.0.0.0", 9090), TaskHTTPHandler)
    logger.info(f"  🌐 HTTP 任务服务器已启动: http://0.0.0.0:9090")
    server.serve_forever()


# ── 日志配置（带轮转：单文件最大 10MB，保留 3 个备份）────
_log_handler = logging.handlers.RotatingFileHandler(
    str(LOG_FILE), maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        _log_handler,
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("guardd")

# ── 机器 UID（用于 Push 认证）───────────────────────────
MACHINE_UID_FILE = DIR_IDENTITY / "machine_uid"
MACHINE_UID = ""
try:
    DIR_IDENTITY.mkdir(parents=True, exist_ok=True)
    if MACHINE_UID_FILE.exists():
        MACHINE_UID = MACHINE_UID_FILE.read_text(encoding="utf-8").strip()
    else:
        MACHINE_UID = str(uuid.uuid4())
        MACHINE_UID_FILE.write_text(MACHINE_UID, encoding="utf-8")
        logger.info(f"  新生成机器 UID: {MACHINE_UID[:8]}...")
except Exception as e:
    logger.warning(f"  UID 文件读写失败: {e}")
    MACHINE_UID = HOSTNAME  # 降级到 hostname

# ── WPRA v2.0: 本机机器命名空间 ──────────────────────
DIR_MACHINES = CROSS_MACHINE / "machines"
DIR_MY_MACHINE = DIR_MACHINES / MACHINE_UID
DIR_MY_EVENTS = DIR_MY_MACHINE / "events"

# ── 确保运行时目录存在 ───────────────────────────────
for d in [DIR_GUARDD_LOG, DIR_SUBMISSIONS_TRIAGE, DIR_TASKS_PENDING,
          DIR_TASKS_COMPLETED, DIR_ENCRYPTED_PENDING, DIR_ENCRYPTED_PROCESSED,
          DIR_MY_MACHINE, DIR_MY_EVENTS]:
    d.mkdir(parents=True, exist_ok=True)


# ════════════════════════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════════════════════════

def _read_json(path):
    """安全读取 JSON 文件，不存在或无效返回 None"""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_event(event_type, payload):
    """写入一条事件到 events/{date}/{uuid}.json"""
    today = datetime.now().strftime("%Y-%m-%d")
    event_dir = DIR_EVENTS / today
    event_dir.mkdir(parents=True, exist_ok=True)
    event = {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "hostname": HOSTNAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    path = event_dir / f"{event['id']}.json"
    path.write_text(json.dumps(event, indent=2, ensure_ascii=False), encoding="utf-8")
    return event["id"]


# ════════════════════════════════════════════════════════════
# WPRA v2.0 辅助函数
# ════════════════════════════════════════════════════════════

def _read_file_version(path):
    """读取文件的 file_version，不存在或无效返回 0"""
    data = _read_json(path)
    if isinstance(data, dict):
        return data.get("file_version", 0)
    return 0


def _write_machine_event(event_type, payload):
    """写入一条事件到 machines/{MACHINE_UID}/events/{date}.jsonl
    使用 JSONL 格式 (append-only)，比单文件更高效
    """
    today = datetime.now().strftime("%Y-%m-%d")
    event_file = DIR_MY_EVENTS / f"{today}.jsonl"
    event = {
        "event_id": str(uuid.uuid4()),
        "machine_uid": MACHINE_UID,
        "machine_name": HOSTNAME,
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }
    with open(event_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event["event_id"]


def _ensure_machine_identity():
    """确保 MACHINE.yaml 存在，首次运行时自动创建"""
    identity_file = DIR_MY_MACHINE / "MACHINE.yaml"
    if identity_file.exists():
        return
    import yaml
    identity = {
        "schema_version": "2.0",
        "file_schema": "machine-identity-v1",
        "machine_uid": MACHINE_UID,
        "machine_name": HOSTNAME,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "role": "workstation",
        "notes": f"Auto-registered by guardd v{version}",
    }
    identity_file.write_text(
        yaml.dump(identity, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    logger.info(f"  ✅ 机器身份已注册: {HOSTNAME} ({MACHINE_UID[:8]}...)")


def _push_to_dashboard(heartbeat_data):
    """反向连接: 将本机心跳+事件推送到 Dashboard

    优先级:
      1. 环境变量 GUARDD_DASHBOARD_URL
      2. agent-local/config.yaml 中的 dashboard_url 字段
      3. 空 → 不推送（本机独立运行）
    """
    dashboard_url = os.environ.get("GUARDD_DASHBOARD_URL", "")

    # 回退: 读本机 config.yaml
    if not dashboard_url:
        config_file = AGENT_LOCAL / "config.yaml"
        if config_file.exists():
            try:
                import yaml
                cfg = yaml.safe_load(config_file.read_text())
                if cfg and isinstance(cfg, dict):
                    dashboard_url = str(cfg.get("dashboard_url", "")).strip()
            except:
                pass

    if not dashboard_url:
        return

    # 读取最近事件用于时间线
    today = datetime.now().strftime("%Y-%m-%d")
    recent_events = []
    event_dir_today = DIR_EVENTS / today
    if event_dir_today.exists():
        for f in sorted(event_dir_today.iterdir())[-10:]:
            if f.suffix == ".json":
                try:
                    recent_events.append(json.loads(f.read_text()))
                except:
                    pass

    try:
        import urllib.request
        payload = json.dumps({
            "uid": MACHINE_UID,
            "hostname": HOSTNAME,
            "heartbeat": heartbeat_data,
            "version": version,
            "events": recent_events,
            "uptime": round(time.time() - _guardd_start_time) if _guardd_start_time else 0,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{dashboard_url}/api/push/heartbeat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        logger.debug(f"  推送 Dashboard 失败: {e}")  # debug 级别, 不刷屏


def _is_file_older_than(path, days=30):
    """判断文件是否超过指定天数"""
    try:
        mtime = path.stat().st_mtime
        age = time.time() - mtime
        return age > days * 86400
    except OSError:
        return False


def _safe_move(src, dst_dir):
    """安全移动文件到目标目录"""
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    # 避免覆盖
    if dst.exists():
        dst = dst_dir / f"{src.stem}_{int(time.time())}{src.suffix}"
    shutil.move(str(src), str(dst))
    return dst


def _get_local_versions():
    """读取本机已记录的版本信息，不存在返回空 dict"""
    local_ver = AGENT_LOCAL / "runtime" / "guardd" / "local_versions.json"
    return _read_json(local_ver) or {}


def _save_local_versions(versions):
    """保存本机版本信息"""
    path = AGENT_LOCAL / "runtime" / "guardd" / "local_versions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(versions, indent=2, ensure_ascii=False), encoding="utf-8")


# ════════════════════════════════════════════════════════════
# 模块 1：状态上报 (heartbeat)
# ════════════════════════════════════════════════════════════
# 每 300s 将本机状态写入 cross_machine/status/{hostname}/heartbeat.json
# 其他机器通过读取此文件判断本机是否在线、正在做什么
# ────────────────────────────────────────────────────────────

def module_heartbeat():
    """采集系统状态并写入 heartbeat.json（精简版：只传在线状态 + slot 状态）"""
    status_dir = DIR_STATUS / HOSTNAME
    status_dir.mkdir(parents=True, exist_ok=True)

    # 读取上次 last_run.json 中的 current_task
    last_run = _read_json(LAST_RUN_FILE)
    current_task = None
    if last_run:
        current_task = last_run.get("current_task")

    # 采集 slot 状态（精简版）
    slot_info = {"used": 0, "max": 3, "slots": []}
    if _slot_manager:
        try:
            full = _slot_manager.get_usage()
            slot_info["used"] = full.get("used", 0)
            slot_info["max"] = full.get("max", 3)
            for s in full.get("slots", []):
                slot_info["slots"].append({
                    "id": s.get("account_id", ""),
                    "pid": s.get("pid"),
                    "health": s.get("health", "unknown"),
                    "elapsed": s.get("elapsed_sec", 0),
                })
        except Exception:
            pass

    heartbeat = {
        "hostname": HOSTNAME,
        "version": version,
        "online": True,
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "slots": slot_info,
        "current_task": current_task,
    }

    path = status_dir / "heartbeat.json"
    path.write_text(json.dumps(heartbeat, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── 同时写入 v4 格式 status/live/{uid}.json (向后兼容) ──
    live_data = {**heartbeat, "_uid": MACHINE_UID, "_hostname": HOSTNAME,
                 "_received_at": datetime.now(timezone.utc).isoformat()}
    live_json = json.dumps(live_data, indent=2, ensure_ascii=False)

    # 写入本地
    live_dir_local = DIR_STATUS / "live"
    live_dir_local.mkdir(parents=True, exist_ok=True)
    (live_dir_local / f"{MACHINE_UID}.json").write_text(live_json, encoding="utf-8")

    # 同时写入 cross_machine（Dashboard 读这个目录）
    live_dir_cross = CROSS_MACHINE / "status" / "live"
    live_dir_cross.mkdir(parents=True, exist_ok=True)
    (live_dir_cross / f"{MACHINE_UID}.json").write_text(live_json, encoding="utf-8")

    # ── WPRA v2.0 心跳写入已移除（v4.2.0）──
    # 心跳数据仅写入：
    #   - status/{HOSTNAME}/heartbeat.json（本地状态目录）
    #   - status/live/{MACHINE_UID}.json（实时状态）
    # 不再写入 cross_machine/machines/{UID}/heartbeat.json，避免 Git 污染。
    # Dashboard 通过 guardd 的反向连接推送获取心跳。
    #
    # ── 记录心跳事件到 events/ ──
    _write_machine_event("heartbeat", {"cpu": cpu_load, "disk_avail": disk_info.get("available_gb", 0)})

    logger.info(f"  心跳已上报 — slots:{slot_info['used']}/{slot_info['max']} 在线")

    # ── 确保 MACHINE.yaml 存在（首次运行时自动创建）──
    _ensure_machine_identity()

    # ── 实时推送到 Dashboard (反向连接) ──
    _push_to_dashboard(heartbeat)

    # ── Git 同步: 将本机数据推送到远程, 拉取其他机器的数据 ──
    # ── 不再往 Gitee 写心跳文件, 改用本机 local 存储 ──
    # _git_sync()
    # ── 改为写本地状态文件 ──

    # ── Override 同步: 检查本机新账号并自动补全 ──
    _sync_account_override()

    # ── 版本检查: 对比 required-version, 落后则自动升级 ──
    _check_version()


def _git_sync():
    """Git 同步: 只 add 本机命名空间的文件 + 全局松散文件

    WPRA v2.0 核心规则：
    - 不再使用 git add -A（会 staging 其他机器的文件）
    - 使用 glob 查找本机文件后精确 add
    - 每个文件只被一个写入者管控，消除 git conflict
    """
    import glob as _glob
    try:
        repo = AGENT_SYNC
        repo_str = str(repo)

        # 先 pull, 避免 push 冲突
        # --autostash: 自动 stash 脏工作区再 rebase，修复 heartbeat 等模块写文件后 pull 失败的问题
        subprocess.run(["git", "pull", "--rebase", "--autostash"], capture_output=True, text=True,
                      timeout=30, cwd=repo_str)

        # 精确查找本机文件 → 精确 git add
        # 使用 glob 展开路径，确保 git 看到的是真实存在的文件
        rel_repo = repo_str
        add_globs = [
            f"04_memory/cross_machine/machines/{MACHINE_UID}/**",
            f"04_memory/cross_machine/data/*/{MACHINE_UID}.json",
            f"04_memory/cross_machine/status/live/{MACHINE_UID}.json",
            f"04_memory/cross_machine/status/{HOSTNAME}/**",
            f"04_memory/cross_machine/events/**",
            f"04_memory/cross_machine/tasks/**",
        ]
        for g in add_globs:
            full = os.path.join(rel_repo, g)
            for matched in _glob.glob(full, recursive=True):
                if os.path.isfile(matched):
                    rel = os.path.relpath(matched, rel_repo)
                    subprocess.run(["git", "add", rel], capture_output=True, text=True,
                                  timeout=15, cwd=repo_str)

        # 只在有变动时才 commit
        r = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                          text=True, timeout=10, cwd=repo_str)
        if r.stdout.strip():
            subprocess.run(["git", "commit", "-m",
                f"sync({HOSTNAME}): guardd {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
                         capture_output=True, text=True, timeout=15, cwd=repo_str)
        # push 到所有远程
        remotes = subprocess.run(["git", "remote"], capture_output=True,
                                text=True, timeout=10, cwd=repo_str)
        for remote in remotes.stdout.strip().splitlines():
            subprocess.run(["git", "push", remote, "main"], capture_output=True,
                          text=True, timeout=30, cwd=repo_str)
    except Exception as e:
        logger.warning(f"  Git sync 异常: {e}")


def _sync_account_override():
    """从 ORACLE.yaml 同步 override: 检测本机新账号并自动补全

    流程:
       1. 读取 ORACLE.yaml（联邦宪法，Gitee 同步）
       2. 读取 accounts.override.yaml（本机私有）
       3. 找到 ORACLE 中 machine=本机 但 override 中不存在的账号 ID
       4. 自动添加到 override（phone 用 mask 占位，用户后续可改）

    废除 accounts_registry.yaml（v4.2.0），所有账号分配统一在 ORACLE.yaml 中管理。
    """
    import yaml

    ORACLE_PATH = AGENT_SYNC / "ORACLE.yaml"
    OVERRIDE_PATH = AGENT_LOCAL / "tools" / "matrix" / "config" / "accounts.override.yaml"

    if not ORACLE_PATH.exists():
        logger.warning("  ORACLE.yaml 不存在，跳过 override 同步")
        return

    try:
        oracle = yaml.safe_load(ORACLE_PATH.read_text()) or {}
        ovr = yaml.safe_load(OVERRIDE_PATH.read_text()) if OVERRIDE_PATH.exists() else {"version": "1.0", "hostname": HOSTNAME, "accounts": []}

        ovr_ids = {a["id"] for a in ovr.get("accounts", [])}
        new_accounts = []

        for acct in oracle.get("accounts", []):
            # 只处理本机归属的账号
            if acct.get("machine", "") != HOSTNAME:
                continue

            # ORACLE 中一个 identity 可能绑定多个平台（douyin + xiaohongshu）
            platforms = acct.get("platforms", {})
            for platform, account_id in platforms.items():
                if account_id in ovr_ids:
                    continue  # 已在 override 中

                # 自动补全
                phone_mask = acct.get("phone", "")
                if len(phone_mask) > 7:
                    phone_mask = phone_mask[:3] + "****" + phone_mask[-4:]

                new_entry = {
                    "id": account_id,
                    "phone": phone_mask,
                    "platform": platform,
                    "identity": acct.get("identity", ""),
                    "enabled": True,
                }
                ovr.setdefault("accounts", []).append(new_entry)
                new_accounts.append(account_id)
                logger.info(f"  📝 自动补全 override: {account_id} ({platform})")

        if new_accounts:
            OVERRIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
            OVERRIDE_PATH.write_text(
                yaml.dump(ovr, default_flow_style=False, allow_unicode=True, sort_keys=False)
            )
            logger.info(f"  ✅ override 已更新: 新增 {len(new_accounts)} 个账号: {', '.join(new_accounts)}")
        else:
            logger.info("  ✅ override 同步检查: 无新账号")

    except Exception as e:
        logger.warning(f"  Override 同步异常: {e}")


def _check_version():
    """版本检查: 落后则自动拉取最新代码"""
    req_file = DIR_CROSS / "guardd-required-version.txt"
    if not req_file.exists():
        return
    try:
        required = req_file.read_text().strip()
        if version != required:
            logger.info(f"  版本落后: 当前={version}, 要求={required}, 正在升级...")
            # 拉取最新代码
            subprocess.run(["git", "pull", "--autostash"], capture_output=True, text=True,
                          timeout=30, cwd=str(AGENT_SYNC))
            logger.info(f"  升级完成, 请重启 guardd")
    except Exception as e:
        logger.warning(f"  Version check 异常: {e}")


# ════════════════════════════════════════════════════════════
# 模块 2：任务检查 (task_worker)
# ════════════════════════════════════════════════════════════
# 扫描 tasks/pending/ 中 target_host 为自己的任务
# 执行后将文件移到 completed/
# ────────────────────────────────────────────────────────────

def module_task_worker():
    """执行分配至本机的跨机任务"""
    if not DIR_TASKS_PENDING.exists():
        return

    task_schemas = {
        "sync_knowledge": {"desc": "同步知识库变更", "handler": "_handle_sync_knowledge"},
        "notify_event":  {"desc": "通知事件收到", "handler": "_handle_notify_event"},
        "run_script":    {"desc": "远程执行脚本", "handler": None},  # 需要安全沙箱，暂不实现
    }

    found = 0
    for f in sorted(DIR_TASKS_PENDING.iterdir()):
        if not f.name.endswith(".json"):
            continue

        task = _read_json(f)
        if not task:
            _safe_move(f, DIR_TASKS_COMPLETED)
            continue

        target = task.get("target_host", "")
        if target and target != HOSTNAME:
            continue  # 不是给本机的

        found += 1
        task_id = task.get("id", f.stem)
        task_type = task.get("type", "unknown")
        logger.info(f"  执行任务 [{task_id}]: type={task_type}")

        # 标记为 in_progress（写入 current_task）
        last_run = _read_json(LAST_RUN_FILE) or {}
        last_run["current_task"] = task_id
        LAST_RUN_FILE.write_text(
            json.dumps(last_run, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 根据 task_type 处理
        success = False
        if task_type in task_schemas and task_schemas[task_type]["handler"]:
            handler_name = task_schemas[task_type]["handler"]
            handler = globals().get(handler_name)
            if handler:
                try:
                    handler(task)
                    success = True
                except Exception as e:
                    logger.error(f"  任务 {task_id} 执行失败: {e}")
                    _write_event("task_failed", {"task_id": task_id, "error": str(e)})
        else:
            # 未知任务类型：标记完成但不执行
            success = True
            logger.info(f"  任务 {task_id} 类型 '{task_type}' 无需执行")

        # 清除 current_task
        last_run["current_task"] = None
        LAST_RUN_FILE.write_text(
            json.dumps(last_run, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 标记完成
        task["status"] = "completed"
        task["completed_at"] = datetime.now(timezone.utc).isoformat()
        task["completed_by"] = HOSTNAME
        (DIR_TASKS_PENDING / f.name).write_text(
            json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        _safe_move(DIR_TASKS_PENDING / f.name, DIR_TASKS_COMPLETED)
        _write_event("task_completed", {"task_id": task_id, "type": task_type, "success": success})

    if found == 0:
        logger.info("  无待处理任务")


def _handle_sync_knowledge(task):
    """处理知识同步任务——记录事件即可，实际同步由 NutSync 处理"""
    _write_event("knowledge_sync_ack", {
        "task_id": task.get("id"),
        "source": task.get("source_host"),
        "acknowledged": True,
    })


def _handle_notify_event(task):
    """处理通知事件——写入本地日志"""
    notice = task.get("payload", {})
    logger.info(f"  收到跨机通知: {notice.get('message', '')}")


# ════════════════════════════════════════════════════════════
# 模块 3：版本检查 (upgrade_checker)
# ════════════════════════════════════════════════════════════
# 读取 knowledge/versions.json，对比本地组件版本
# 有更新 → 非 breaking 自动执行，breaking 待确认
# ────────────────────────────────────────────────────────────

def module_upgrade_checker():
    """检查版本清单，发现新版本时触发更新事件 + 非破坏性更新自动执行"""
    remote_versions = _read_json(VERSIONS_FILE)
    if not remote_versions:
        logger.info("  版本清单不可用，跳过")
        return

    local_versions = _get_local_versions()
    components = remote_versions.get("components", {})
    updates_found = []
    auto_upgraded = []

    for name, spec in components.items():
        local_ver = local_versions.get(name, {}).get("version", "0.0.0")
        remote_ver = spec.get("current", "0.0.0")

        if remote_ver != local_ver:
            is_breaking = spec.get("breaking_change", False)
            updates_found.append({
                "component": name,
                "from": local_ver,
                "to": remote_ver,
                "breaking": is_breaking,
                "description": spec.get("description", ""),
            })

            # 自动执行非破坏性更新
            if not is_breaking:
                install_script = spec.get("install_script", "")
                if install_script:
                    script_path = AGENT_SYNC / install_script
                    if script_path.exists():
                        try:
                            subprocess.run(["bash", str(script_path)], check=True,
                                          capture_output=True, timeout=120)
                            auto_upgraded.append(name)
                            logger.info(f"    ✅ 自动升级 {name}: {local_ver}→{remote_ver}")
                            _write_event("component_upgraded", {
                                "component": name, "from": local_ver, "to": remote_ver
                            })
                        except subprocess.CalledProcessError as e:
                            logger.error(f"    ❌ 自动升级 {name} 失败: {e.stderr.decode()[:200]}")
                        except FileNotFoundError:
                            logger.info(f"    ⏭ 升级脚本不存在: {install_script}")
                    else:
                        logger.info(f"    ℹ️ {name} 有更新 {local_ver}→{remote_ver}，无安装脚本")

    if updates_found:
        if auto_upgraded:
            logger.info(f"  已自动升级: {', '.join(auto_upgraded)}")
        breaking = [u for u in updates_found if u['breaking']]
        if breaking:
            logger.info(f"  ⚠️ 破坏性更新待处理: {', '.join(b['component'] for b in breaking)}")
        _write_event("upgrades_available", {
            "updates": updates_found, "auto_upgraded": auto_upgraded,
            "check_time": datetime.now(timezone.utc).isoformat(),
        })
        new_local = {}
        for name, spec in components.items():
            new_local[name] = {"version": spec["current"],
                              "updated_at": datetime.now(timezone.utc).isoformat()}
        _save_local_versions(new_local)
    else:
        logger.info("  所有组件已最新")


# ════════════════════════════════════════════════════════════
# 模块 4：记忆提炼上报 (memory_triage)
# ════════════════════════════════════════════════════════════
# 扫描 agent-local/memory/ 中的原始记忆
# 规则过滤器：筛掉含本机路径/配置的记忆
# 保留通用方法论/概念/经验 → 写入 submissions/memory_triage/
# ────────────────────────────────────────────────────────────

def module_memory_triage():
    """过滤本地记忆并推送通用内容到提交箱"""
    if not DIR_LOCAL_MEMORY.exists():
        return

    # 已处理的文件追踪
    processed_file = AGENT_LOCAL / "runtime" / "guardd" / "triage_processed.txt"
    processed = set()
    if processed_file.exists():
        processed = set(processed_file.read_text(encoding="utf-8").splitlines())

    # 本机特有模式 —— 含这些内容的记忆不共享
    LOCAL_PATTERNS = [
        re.compile(r"/Users/" + os.getlogin() + r"/"),
        re.compile(HOSTNAME, re.IGNORECASE),
        re.compile(r"agent-local/"),
        re.compile(r"runtime/guardd"),
        re.compile(r"API[_-]?KEY[=:]?\s*\w{8,}", re.IGNORECASE),
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenAI style keys
        re.compile(r"AKID[\\w]+"),  # 阿里云/腾讯云 AK
        re.compile(r"password[=:]?\s*\\S+", re.IGNORECASE),
        re.compile(r"secret[=:]?\s*\\S+", re.IGNORECASE),
    ]

    # 机器通用内容关键词（含这些关键词的更可能跨机有价值）
    GENERAL_KEYWORDS = [
        "方法论", "workflow", "template", "最佳实践", "经验",
        "总结", "lesson", "心得", "技巧", "tip", "指南",
        "principle", "原则", "策略", "strategy", "architecture",
    ]

    new_files = []
    for f in DIR_LOCAL_MEMORY.rglob("*"):
        if not f.is_file() or f.name.startswith("."):
            continue
        if str(f) in processed:
            continue
        if f.suffix not in (".md", ".txt", ".json", ".yaml", ".yml"):
            continue

        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        # 规则过滤器：含本机特有模式 → 跳过
        if any(p.search(content) for p in LOCAL_PATTERNS):
            logger.info(f"    跳过本地记忆: {f.name} (包含本机特有内容)")
            processed.add(str(f))
            continue

        # 检查是否包含通用关键词
        has_general = any(kw in content for kw in GENERAL_KEYWORDS)
        if not has_general and len(content) < 100:
            logger.info(f"    跳过本地记忆: {f.name} (无通用内容)")
            processed.add(str(f))
            continue

        # 写入提交箱
        dest = DIR_SUBMISSIONS_TRIAGE / f.name
        # 避免重名
        if dest.exists():
            dest = DIR_SUBMISSIONS_TRIAGE / f"{f.stem}_{int(time.time())}{f.suffix}"
        dest.write_text(content, encoding="utf-8")
        new_files.append(f.name)
        processed.add(str(f))

    # 更新已处理记录
    if new_files:
        processed_file.write_text("\n".join(sorted(processed)), encoding="utf-8")
        _write_event("memory_triage", {
            "files": new_files,
            "count": len(new_files),
        })
        logger.info(f"  提交 {len(new_files)} 条通用记忆到 submissions/memory_triage/")
    else:
        logger.info("  无新记忆需要提炼")


# ════════════════════════════════════════════════════════════
# 模块 5：知识同步检查 (knowledge_sync)
# ════════════════════════════════════════════════════════════
# 检测 03_knowledge/ 的 CHANGELOG.md 最新变更
# 扫描 agent-local/submissions/ 推送到 03_knowledge/01_submissions/
# ────────────────────────────────────────────────────────────

def module_knowledge_sync():
    """检测知识库变更并推送本地提交"""
    # ── 检测知识库变更 ──
    changelog_path = AGENT_SYNC / "03_knowledge" / "CHANGELOG.md"
    last_check_file = AGENT_LOCAL / "runtime" / "guardd" / "knowledge_last_check.txt"

    if changelog_path.exists():
        try:
            # 读取 CHANGELOG 第一行内容作为变更指纹
            changelog_content = changelog_path.read_text(encoding="utf-8")
            # 取最新日期行
            date_lines = re.findall(r"^##\s+(\d{4}-\d{2}-\d{2})", changelog_content, re.MULTILINE)
            latest_date = date_lines[0] if date_lines else "unknown"

            last_date = ""
            if last_check_file.exists():
                last_date = last_check_file.read_text(encoding="utf-8").strip()

            if latest_date != last_date and latest_date != "unknown":
                _write_event("knowledge_updated", {
                    "latest_date": latest_date,
                    "previous_date": last_date or "none",
                })
                last_check_file.write_text(latest_date, encoding="utf-8")
                logger.info(f"  知识库有新变更: {latest_date}")
            else:
                logger.info(f"  知识库无新变更 (上次: {last_date})")
        except OSError as e:
            logger.error(f"  读取 CHANGELOG 失败: {e}")
    else:
        logger.info("  CHANGELOG.md 不存在，跳过")

    # ── 推送本地提交箱 → 知识库 submissions ──
    if not DIR_SUBMISSIONS.exists():
        return

    pushed = 0
    for sub_dir in DIR_SUBMISSIONS.iterdir():
        if not sub_dir.is_dir() or sub_dir.name.startswith("."):
            continue

        for f in sub_dir.glob("*"):
            if not f.is_file() or f.name.startswith("."):
                continue

            # 推送到 03_knowledge/01_submissions/{hostname}/
            target_dir = DIR_SUBMISSIONS_KNOWLEDGE / HOSTNAME / sub_dir.name
            target_dir.mkdir(parents=True, exist_ok=True)
            dest = target_dir / f.name

            if not dest.exists():
                shutil.copy2(str(f), str(dest))
                pushed += 1
                logger.info(f"    推送: {sub_dir.name}/{f.name}")

    if pushed > 0:
        _write_event("submissions_pushed", {"count": pushed, "hostname": HOSTNAME})
        logger.info(f"  推送 {pushed} 个文件到 01_submissions/{HOSTNAME}/")
    else:
        logger.info("  无新提交需要推送")


# ════════════════════════════════════════════════════════════
# 模块 6：加密消息接收 (encrypted_channel)
# ════════════════════════════════════════════════════════════
# 读取 encrypted/pending/ 中 target_host 为自己的文件
# 用本地私钥解密 → 存入 agent-local/identity/secrets/received/
# ────────────────────────────────────────────────────────────

def module_encrypted_channel():
    """解密发往本机的加密消息 → 解密后提示用户"""
    if not DIR_ENCRYPTED_PENDING.exists():
        return

    private_key_path = DIR_SECRETS / "private_key.pem"
    if not private_key_path.exists():
        logger.info("  无私钥文件，跳过加密频道")
        return

    found = 0
    for f in sorted(DIR_ENCRYPTED_PENDING.iterdir()):
        if not f.name.endswith(".json"):
            continue

        msg = _read_json(f)
        if not msg:
            _safe_move(f, DIR_ENCRYPTED_PROCESSED)
            continue

        target = msg.get("target_host", "")
        if target and target != HOSTNAME:
            continue

        found += 1
        msg_id = msg.get("id", f.stem)
        msg_type = msg.get("type", "unknown")
        sender = msg.get("sender", "unknown")
        logger.info(f"  发现加密消息 [{msg_id}] from={sender} type={msg_type}")

        # 创建用户通知文件（可用于前端/外部提示）
        notice = {
            "msg_id": msg_id, "sender": sender, "type": msg_type,
            "description": msg.get("description", ""),
            "received_at": datetime.now(timezone.utc).isoformat(),
            "needs_action": True,
        }
        notice_dir = DIR_GUARDD_LOG / "notifications"
        notice_dir.mkdir(parents=True, exist_ok=True)
        (notice_dir / f"{msg_id}.json").write_text(
            json.dumps(notice, indent=2, ensure_ascii=False), encoding="utf-8")

        # 如果是文件传输请求，特别标注
        if msg_type == "file_transfer":
            logger.info(f"  🔄 文件传输请求: {msg.get('description', '')}")
            notice["action_type"] = "approve_transfer"

        # 尝试解密
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            encrypted_data = msg.get("payload", "")
            if encrypted_data:
                with open(private_key_path, "rb") as key_file:
                    private_key = serialization.load_pem_private_key(key_file.read(), password=None)
                decrypted = private_key.decrypt(
                    bytes.fromhex(encrypted_data),
                    padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                 algorithm=hashes.SHA256(), label=None),
                )
                received_dir = DIR_SECRETS / "received"
                received_dir.mkdir(parents=True, exist_ok=True)
                out_path = received_dir / f"{msg_id}.json"
                out_path.write_text(decrypted.decode("utf-8"), encoding="utf-8")
                logger.info(f"    ✅ 解密成功 → {out_path}")
                notice["decrypted"] = True
                notice["output"] = str(out_path)
                _write_event("message_decrypted", {"msg_id": msg_id})
            else:
                # 无 payload 的消息（如请求类），确认收到即可
                logger.info(f"    ℹ️ 无加密载荷，确认收到")
                notice["decrypted"] = True
        except Exception as e:
            logger.error(f"    ⚠️ 解密失败: {e}")
            notice["decrypted"] = False
            notice["error"] = str(e)
            _write_event("message_decrypt_failed", {"msg_id": msg_id, "error": str(e)})

        # 更新通知状态
        notice["needs_action"] = False
        (notice_dir / f"{msg_id}.json").write_text(
            json.dumps(notice, indent=2, ensure_ascii=False), encoding="utf-8")

        _safe_move(f, DIR_ENCRYPTED_PROCESSED)

    if found == 0:
        logger.info("  无待处理加密消息")


# ════════════════════════════════════════════════════════════
# 模块 7：清理 (cleanup)
# ════════════════════════════════════════════════════════════
# 清理超过 30 天的旧事件文件和已完成的任务
# ────────────────────────────────────────────────────────────

def module_cleanup():
    """清理过期数据"""
    cleaned = 0

    # 清理过期事件文件 (>30天)
    if DIR_EVENTS.exists():
        for date_dir in DIR_EVENTS.iterdir():
            if not date_dir.is_dir() or date_dir.name.startswith("."):
                continue
            # 目录名格式: YYYY-MM-DD
            try:
                dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
                if (datetime.now() - dir_date).days > 30:
                    shutil.rmtree(str(date_dir))
                    cleaned += 1
                    logger.info(f"    清理事件目录: {date_dir.name}")
            except ValueError:
                continue

    # 清理过期已完成任务 (>30天)
    if DIR_TASKS_COMPLETED.exists():
        for f in DIR_TASKS_COMPLETED.iterdir():
            if f.is_file() and _is_file_older_than(f, 30):
                f.unlink()
                cleaned += 1
                logger.info(f"    清理完成任务: {f.name}")

    # 清理过期已处理加密消息 (>30天)
    if DIR_ENCRYPTED_PROCESSED.exists():
        for f in DIR_ENCRYPTED_PROCESSED.iterdir():
            if f.is_file() and _is_file_older_than(f, 30):
                f.unlink()
                cleaned += 1
                logger.info(f"    清理已处理加密消息: {f.name}")

    if cleaned > 0:
        logger.info(f"  清理了 {cleaned} 个过期条目")
    else:
        logger.info("  无过期数据需要清理")


# ════════════════════════════════════════════════════════════
# 模块 8：同步检查 (sync_checker)
# ════════════════════════════════════════════════════════════
# 自动 git pull → 检测变更 → 触发协同更新
# ────────────────────────────────────────────────────────────

def module_sync_checker():
    """自动拉取远程变更，检测是否有新的协同任务"""
    if not (AGENT_SYNC / ".git").exists():
        logger.info("  非 git 仓库，跳过同步检查")
        return

    try:
        # 1. git pull 获取远程变更
        result = subprocess.run(
            ["git", "pull", "--autostash"],
            capture_output=True, text=True, timeout=30,
            cwd=str(AGENT_SYNC),
        )
        output = result.stdout.strip()
        stderr = result.stderr.strip()

        if "Already up to date" in output:
            logger.info("  远程仓库已最新")
            return

        if result.returncode == 0:
            # 有更新！
            changed = "has new commits" in output or "Fast-forward" in output
            if changed or "files changed" in output:
                # 提取变更统计
                stats = ""
                for line in output.split("\n"):
                    if "files changed" in line:
                        stats = line.strip()
                        break
                logger.info(f"  🔄 检测到远程更新: {stats or output[:80]}")
                _write_event("sync_updated", {
                    "summary": output[:500],
                    "hostname": HOSTNAME,
                })
            else:
                logger.info(f"  git pull 输出: {output[:200]}")
        else:
            logger.warning(f"  git pull 失败: {stderr[:200]}")
    except subprocess.TimeoutExpired:
        logger.warning("  git pull 超时 (30s)")
    except FileNotFoundError:
        logger.info("  git 未安装，跳过同步检查")
    except Exception as e:
        logger.warning(f"  git pull 异常: {e}")


# ════════════════════════════════════════════════════════════
# 主循环
# ════════════════════════════════════════════════════════════

def module_dashboard_sync():
    """将本机Dashboard插件数据写入 cross_machine/data/{plugin}/{uid}.json

    确保所有机器的 Dashboard 可以看到本机的完整状态。
    格式统一由 DashboardPlugin.write_shared() 保证。
    """
    import importlib, pkgutil
    dashboard_plugins_dir = AGENT_SYNC / "05_tools" / "10_dashboard" / "plugins"
    if not dashboard_plugins_dir.exists():
        logger.debug("  Dashboard插件目录不存在，跳过")
        return

    sys.path.insert(0, str(dashboard_plugins_dir.parent))
    try:
        from plugins.base import MACHINE_UID as DASH_UID, HOSTNAME as DASH_HOST
        from plugins import discover_plugins
        discovered = discover_plugins()
        for name, inst in discovered.items():
            try:
                if hasattr(inst, 'write_shared'):
                    inst.write_shared()
                    logger.info(f"  ✓ dashboard/{name} 已同步")
            except Exception as e:
                logger.debug(f"  dashboard/{name} 同步失败: {e}")
    except Exception as e:
        logger.debug(f"  Dashboard插件加载失败: {e}")
    finally:
        sys.path.pop(0)


def _run_heartbeat_cycle():
    """执行一轮健康检查（9 模块）"""
    t0 = time.time()
    modules = [
        ("heartbeat", module_heartbeat),
        ("dashboard_sync", module_dashboard_sync),
        ("task_worker", module_task_worker),
        ("upgrade_checker", module_upgrade_checker),
        ("memory_triage", module_memory_triage),
        ("knowledge_sync", module_knowledge_sync),
        ("encrypted_channel", module_encrypted_channel),
        ("sync_checker", module_sync_checker),
        ("cleanup", module_cleanup),
    ]
    results = {}
    for name, func in modules:
        try:
            func()
            results[name] = "ok"
            logger.info(f"  ✓ {name}")
        except Exception as e:
            results[name] = f"error: {e}"
            logger.error(f"  ✗ {name}: {e}")
            with open(ERROR_LOG_FILE, "a") as f:
                f.write(f"{datetime.now()} {name}: {e}\n")
    elapsed = time.time() - t0
    last_run = {
        "hostname": HOSTNAME,
        "version": version,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(elapsed, 2),
        "results": results,
        "next_run": (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat(),
        "running_tasks": len(_get_tasks()),
    }
    with open(LAST_RUN_FILE, "w") as f:
        json.dump(last_run, f, indent=2, ensure_ascii=False)
    logger.info(f"guardd 心跳完成 — {elapsed:.2f}s, results={results}")




# ── 全局实例 ──
_task_store = None
_slot_manager = None
_scheduler = None
_heartbeat_reporter = None
_account_monitor = None
_oracle_sync = None

# 防止 _init_scheduler() 并发初始化（HTTP 线程和主线程竞态）
_init_lock = threading.Lock()


def _init_scheduler():
    """初始化调度引擎（线程安全，可重复调）"""
    global _task_store, _slot_manager, _scheduler, _heartbeat_reporter, _oracle_sync, _account_monitor, _schedule_bridge
    
    if _scheduler is not None:
        return  # 已初始化
    
    if not _init_lock.acquire(blocking=False):
        logger.warning("  ⏳ 另一线程正在初始化调度引擎，等待...")
        _init_lock.acquire(blocking=True)  # 等初始化完成
        _init_lock.release()
        return
    
    try:
        logger.info("  ⚙️ 初始化调度引擎 (v4.3.0)...")
        
        # TaskStore
        _task_store = TaskStore()
        logger.info(f"  📦 TaskStore 就绪 ({_task_store.count()})")
        
        # PriorityQueue
        queue = PriorityQueue()
        
        # SlotManager
        _slot_manager = BrowserSlotManager(max_slots=3)
        _slot_manager.cleanup_orphans()
        logger.info(f"  🖥️ SlotManager 就绪 ({_slot_manager.get_usage()['used']}/{_slot_manager.max_slots})")
        
        # Executor
        executor = Executor(_task_store, _slot_manager)
        
        # Scheduler（传入 on_task_event 回调用于状态推送）
        def _on_task_event(event_type, task):
            """任务状态变化时推送事件到 Dashboard"""
            try:
                payload = {
                    "event": event_type,
                    "machine": HOSTNAME,
                    "task_id": task.get("task_id", ""),
                    "cmd_type": task.get("cmd_type", ""),
                    "accounts": task.get("accounts", []),
                    "slot_id": task.get("slot_id"),
                    "status": task.get("status", ""),
                    "time": datetime.now(timezone.utc).isoformat(),
                }
                # 推送给本机 Dashboard
                import urllib.request as _urq
                import json as _js
                req = _urq.Request(
                    "http://127.0.0.1:9988/api/push/task-event",
                    data=_js.dumps(payload).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                _urq.urlopen(req, timeout=3)
            except Exception:
                pass  # Dashboard 不在线不影响执行

        _scheduler = Scheduler(_task_store, queue, _slot_manager, executor, on_task_event=_on_task_event)
        
        # HeartbeatReporter
        from modules.account_monitor import AccountMonitor
        from modules.schedule_bridge import ScheduleBridge
        _account_monitor = AccountMonitor()
        _schedule_bridge = ScheduleBridge(_task_store, _scheduler, HOSTNAME)
        _heartbeat_reporter = HeartbeatReporter(
            _task_store, _slot_manager, _scheduler,
            HOSTNAME, MACHINE_UID,
            dashboard_url="http://127.0.0.1:9988",
            account_monitor=_account_monitor
        )
        
        # OracleSync
        _oracle_sync = OracleSync(_task_store)
        _oracle_sync.sync()
        
        # 恢复未完成任务（始终恢复 ALL queued 任务，不局限于 recovered>0）
        recovered = _task_store.reset_unfinished()
        queued_tasks = _task_store.get_by_status("queued")
        if queued_tasks:
            logger.info(f"  🔄 恢复 {len(queued_tasks)} 个排队任务到队列 (含 {recovered} 个从 running 重置)")
            for task in queued_tasks:
                _scheduler.submit_task(task)
        
        logger.info("  ✅ 调度引擎初始化完成")
        
        # 发一轮心跳
        _heartbeat_reporter.send_to_dashboard()
        _heartbeat_reporter.write_local()
    except Exception as e:
        logger.error(f"  ❌ 调度引擎初始化失败: {e}")
    finally:
        _init_lock.release()


def _run_scheduler_loop():
    """在独立线程中运行调度循环"""
    _init_scheduler()
    logger.info("  🔁 调度循环启动 (15s间隔)")
    _scheduler.run_cycle()


def _run_enhanced_heartbeat():
    """增强版心跳 — 替换原有 module_heartbeat"""
    if _heartbeat_reporter is None:
        _init_scheduler()
    try:
        hb = _heartbeat_reporter.collect()
        _heartbeat_reporter.write_local(hb)
        _heartbeat_reporter.send_to_dashboard(hb)
        logger.info(f"  ✓ enhanced_heartbeat (slots={hb['slots']['used']}/{hb['slots']['max']})")
    except Exception as e:
        logger.error(f"  ✗ enhanced_heartbeat: {e}")


def api_scheduler_submit(task_json: dict) -> dict:
    """HTTP API 入口：提交任务到调度器"""
    _init_scheduler()
    _scheduler.submit_task(task_json)
    return {"status": "accepted", "task_id": task_json.get("task_id", "")}


def api_scheduler_status() -> dict:
    """HTTP API 入口：查询调度器状态

    每次调用先实时检查所有浏览器进程是否活着（os.kill pid 空信号），
    确保看板看到的是当前真实状态，不依赖 15 秒周期。
    """
    _init_scheduler()
    # 实时进程检测 — 每次 API 调用都查，0 延时
    if _slot_manager:
        try:
            for s_info in _slot_manager.get_usage().get("slots", []):
                pid = s_info.get("pid")
                if pid:
                    try:
                        os.kill(pid, 0)  # 空信号，仅测存活
                        s_info["health"] = "healthy"
                    except OSError:
                        s_info["health"] = "crashed"
                        s_info["pid"] = None  # 已死，清掉 PID
        except Exception:
            pass
    # 同步清理 scheduler 中已死的活跃任务
    if _scheduler and _scheduler.active_tasks:
        for slot_id, task in list(_scheduler.active_tasks.items()):
            slot_pid = None
            if _slot_manager:
                slots_info = _slot_manager.get_usage().get("slots", [])
                s_info = next((s for s in slots_info if s.get("slot_id") == slot_id), None)
                if s_info:
                    slot_pid = s_info.get("pid")
            # 如果 slot 有 PID 但进程已死，或 slot 已释放但 active_tasks 还有 → 强制释放
            if slot_pid is None and task.get("status") in ("running",):
                # PID 不存在 → 进程已崩溃 → 标记失败
                logger.warning(f"  ⚰️ [{task['task_id'][:30]}] 进程已死，强制释放 slot {slot_id}")
                task["status"] = "failed"
                task["error"] = "进程已崩溃"
                task["completed_at"] = time.time()
                _scheduler._release_slot(slot_id)
    return {
        "active": list(_scheduler.active_tasks.values()) if _scheduler and _scheduler.active_tasks else [],
        "queue": _scheduler.get_all_queued() if _scheduler else [],
        "queue_sizes": _scheduler.queue_sizes() if _scheduler else {},
        "slots": _slot_manager.get_usage() if _slot_manager else {},
        "counts": _task_store.count() if _task_store else {},
    }


def main():
    logger.info(f"guardd v{version} 启动 — hostname={HOSTNAME} (持久模式)")

    # 先初始化调度引擎（确保全局变量就绪）
    try:
        _init_scheduler()
        scheduler_thread = threading.Thread(target=_run_scheduler_loop, daemon=True)
        scheduler_thread.start()
        logger.info("  🔁 调度引擎后台线程已启动")
        # 5 秒进程追踪线程（独立于调度 cycle，更灵敏）
        if _slot_manager:
            track_thread = threading.Thread(target=_slot_manager.track_loop, args=(5.0,), daemon=True)
            track_thread.start()
            logger.info("  🔁 进程追踪线程已启动（每 5 秒检测 PID 存活）")
    except Exception as e:
        logger.warning(f"  调度引擎启动失败: {e} (不影响原有功能)")

    # 初始化完成后才启动 HTTP 服务器（避免竞态）
    http_thread = threading.Thread(target=_run_http_server, daemon=True)
    http_thread.start()

    # 先跑一轮心跳（含增强版）
    _run_heartbeat_cycle()
    try:
        _run_enhanced_heartbeat()
    except Exception as e:
        logger.debug(f"  增强心跳首轮失败: {e}")

    # 持续心跳循环（每 300 秒）
    while True:
        time.sleep(300)
        _run_heartbeat_cycle()
        try:
            _run_enhanced_heartbeat()
        except Exception as e:
            logger.debug(f"  增强心跳失败: {e}")


if __name__ == "__main__":
    main()

"""
command_bus.py — 统一命令传输层 v6

设计原则:
  v5 (2026-06-23): 按机器分组，每台机器只发一条命令（含多个账号）
  v6 (2026-06-25): 每台机器一个执行队列，串行执行

核心机制:
  1. 路由层不拆解命令 — 传全部账号，由 MC 引擎按 identity 分组
  2. 命令直接发到 guardd 调度器 — 不再排队串行化
  3. guardd 调度器内部管理 3 个 slot 和优先级队列
  4. MachineSession 仅做状态追踪和历史记录
  5. 不同机器之间并行执行（互不影响）
  6. 同一机器多任务并发由 guardd 调度器控制
  7. 强制停止 → cancel() 杀进程+清浏览器

架构:
  Dashboard → API → CommandBus → MachineSession(队列) → mc run → 引擎 → Camoufox
"""

import asyncio, copy, json, logging, os, shlex, socket, subprocess, sys, time, threading, urllib.request, urllib.error
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("dashboard.command_bus")

_THIS_DIR = Path(__file__).resolve().parent.parent
AGENT_SYNC = Path(os.environ.get("AGENT_SYNC", str(Path.home() / "workbuddy-agent-os" / "agent-sync")))
AGENT_LOCAL = Path(os.environ.get("AGENT_LOCAL", str(Path.home() / "workbuddy-agent-os" / "agent-local")))
ORACLE_PATH = AGENT_SYNC / "ORACLE.yaml"

from utils.identity import resolve_hostname

HOSTNAME = resolve_hostname()

# ── guardd HTTP API 客户端（v7）──────────────────────────
GUARDD_PORT = 9090

def _guardd_url(machine: str = "") -> str:
    """获取目标机器的 guardd URL（本机用 localhost，远程用 Tailscale IP）"""
    if not machine or machine == HOSTNAME:
        return f"http://localhost:{GUARDD_PORT}"
    info = _get_machine_info(machine)
    ip = info.get("ip", "")
    if ip:
        return f"http://{ip}:{GUARDD_PORT}"
    return ""

def _guardd_api(method, path, data=None, machine=""):
    """call guardd HTTP API via socket (avoids urllib+Tailscale timeout issue)"""
    url = _guardd_url(machine)
    if not url:
        logger.warning("guardd_api: machine {} URL empty".format(machine))
        return {}
    host = url.replace("http://", "").replace("https://", "")
    port = 9090
    if ":" in host:
        host, ps = host.split(":", 1)
        port = int(ps)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        if method == "GET":
            s.sendall("GET {} HTTP/1.0\r\nHost: {}\r\nConnection: close\r\n\r\n".format(path, host).encode())
        elif method == "POST":
            body = json.dumps(data or {}).encode()
            req = "POST {} HTTP/1.0\r\nHost: {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n".format(path, host, len(body))
            s.sendall(req.encode() + body)
        resp = b""
        while True:
            chunk = s.recv(4096)
            if not chunk: break
            resp += chunk
        s.close()
        if b"\r\n\r\n" in resp:
            return json.loads(resp.split(b"\r\n\r\n", 1)[1].decode())
        return {}
    except socket.timeout:
        logger.warning("guardd_api {} {}://{}:{}{} -> timeout".format(method, "http", host, port, path))
    except (socket.error, OSError) as e:
        logger.warning("guardd_api {} {}://{}:{}{} -> {}".format(method, "http", host, port, path, e))
    except json.JSONDecodeError as e:
        logger.warning("guardd_api {} {}://{}:{}{} -> JSON fail: {}".format(method, "http", host, port, path, e))
    return {}

class CommandStatus(str, Enum):
    QUEUED = "queued"
    PREFLIGHTING = "preflighting"
    PREFLIGHT_FAILED = "preflight_failed"
    DISPATCHING = "dispatching"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CRASHED = "crashed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in (CommandStatus.COMPLETED, CommandStatus.FAILED,
                        CommandStatus.TIMED_OUT, CommandStatus.CRASHED,
                        CommandStatus.CANCELLED, CommandStatus.PREFLIGHT_FAILED)

    @property
    def is_active(self) -> bool:
        return self in (CommandStatus.PREFLIGHTING, CommandStatus.DISPATCHING, CommandStatus.RUNNING)


class Command:
    """一条命令的完整生命周期（v5：支持多账号）"""

    def __init__(self, cmd_type: str, accounts: list, machine: str,
                 command_line: str, run_id: str, params: dict = None):
        self.cmd_type = cmd_type
        self.accounts = accounts              # [str] — 账号ID列表
        self.machine = machine
        self.command_line = command_line
        self.run_id = run_id
        self.params = params or {}

        self.status = CommandStatus.QUEUED
        self.pid = None
        self.message = ""
        self.result = None

        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.last_poll_at = None
        self.log_path = None

    @property
    def account_display(self) -> str:
        """显示用：'douyin_test,xhs_01' 或 'douyin_test'"""
        return ",".join(self.accounts)

    @property
    def elapsed_sec(self) -> float:
        if self.started_at is None:
            return 0
        end = self.completed_at or time.time()
        return end - self.started_at

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "type": self.cmd_type,
            "accounts": self.accounts,
            "account": self.accounts[0] if self.accounts else "",
            "machine": self.machine,
            "status": self.status.value,
            "command": self.command_line,
            "pid": self.pid,
            "message": self.message,
            "elapsed_sec": round(self.elapsed_sec, 1),
            "created_at": datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat(),
            "started_at": datetime.fromtimestamp(self.started_at, tz=timezone.utc).isoformat() if self.started_at else None,
            "completed_at": datetime.fromtimestamp(self.completed_at, tz=timezone.utc).isoformat() if self.completed_at else None,
            "result": self.result,
            "log_path": str(self.log_path) if self.log_path else None,
        }


_ORACLE_MACHINES = None

def _load_profiles() -> dict:
    """加载 profiles.json 获取账号行业标记"""
    import json
    try:
        from pathlib import Path
        profiles_path = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix" / "data" / "profiles.json"
        if profiles_path.exists():
            with open(profiles_path) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _get_machine_info(machine_name: str) -> dict:
    global _ORACLE_MACHINES
    if _ORACLE_MACHINES is None:
        if ORACLE_PATH.exists():
            import yaml
            _ORACLE_MACHINES = yaml.safe_load(ORACLE_PATH.read_text()).get("machines", {})
        else:
            _ORACLE_MACHINES = {}
    for name, info in _ORACLE_MACHINES.items():
        if name == machine_name or info.get("hostname") == machine_name:
            return {"name": name, "hostname": info.get("hostname", name),
                    "ip": info.get("tailscale_ip", ""), "user": info.get("ssh_user", "")}
    return {}


class MachineSession:
    """单台机器的命令执行会话（v6: 每台机器一个队列）"""

    _sessions = {}

    def __init__(self, machine: str):
        self.machine = machine
        self.is_local = (machine == HOSTNAME)
        self.commands: list[Command] = []     # 全部命令（含历史）
        self.current_cmd: Optional[Command] = None  # 正在执行的命令
        self.queued_cmds: list[Command] = []  # 排队等待的命令
        self.max_history = 50
        self._lock = threading.Lock()
        self.machine_info = _get_machine_info(machine) if not self.is_local else {}
        self.ssh_target = None
        if not self.is_local and self.machine_info.get("ip"):
            u = self.machine_info.get("user", "")
            self.ssh_target = f"{u}@{self.machine_info['ip']}" if u else self.machine_info["ip"]

    @property
    def is_busy(self) -> bool:
        """机器是否正在执行命令"""
        return self.current_cmd is not None and self.current_cmd.status.is_active

    @classmethod
    def get(cls, machine: str) -> "MachineSession":
        if machine not in cls._sessions:
            cls._sessions[machine] = cls(machine)
        return cls._sessions[machine]

    def graceful_exit(self, account_id: str = None):
        """优雅退出：执行前清理同机残留进程。

        只杀无 active 命令的僵尸进程；若有 active 命令，由 guardd 调度器排他管理，不抢杀。
        """
        for cmd in self.commands[:]:
            if cmd.status.is_active and (account_id is None or account_id in cmd.accounts):
                self.cancel(cmd)

        # 僵尸进程清理：只杀无 active 命令的残留
        active_for_account = any(
            cmd.status.is_active and (account_id is None or account_id in cmd.accounts)
            for cmd in self.commands
        )
        if active_for_account:
            return

        # 无 active 命令 → pkill 清理僵尸进程
        if self.is_local:
            target = account_id or ""
            try:
                subprocess.run(["pkill", "-f", f"mc run.*{target}"], capture_output=True, timeout=3)
                subprocess.run(["pkill", "-f", f"mc task.*{target}"], capture_output=True, timeout=3)
                subprocess.run(["pkill", "-f", f"mc collect.*{target}"], capture_output=True, timeout=3)
                subprocess.run(["pkill", "-f", f"mc smart-login.*{target}"], capture_output=True, timeout=3)
            except:
                pass
        elif self.ssh_target:
            target = account_id or ""
            try:
                subprocess.run(
                    ["ssh", "-o", "ConnectTimeout=5", self.ssh_target,
                     f"pkill -f 'mc (run|collect|smart-login|task).*{target}' 2>/dev/null; true"],
                    capture_output=True, timeout=5
                )
            except:
                pass

    def preflight(self) -> dict:
        with self._lock:
            active = [c for c in self.commands if c.status.is_active]
            if not self.is_local and self.ssh_target:
                try:
                    r = subprocess.run(
                        ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
                         self.ssh_target, "echo ok"],
                        capture_output=True, text=True, timeout=8
                    )
                    if r.returncode != 0:
                        logger.warning(f"  ⚠️ [{self.machine}] preflight SSH 不可达 (rc={r.returncode}), 仍然尝试发送")
                        return {"ok": True, "message": "SSH 不可达但尝试发送", "running": len(active)}
                except Exception as e:
                    logger.warning(f"  ⚠️ [{self.machine}] preflight SSH 异常: {e}, 仍然尝试发送")
                    return {"ok": True, "message": f"SSH 异常但尝试发送: {e}", "running": len(active)}
            return {"ok": True, "message": "就绪", "running": len(active)}

    def _clear_stale(self):
        """清理卡死的 current_cmd（_guardd_api 临时不可用导致 is_busy 卡死）"""
        cmd = self.current_cmd
        if not cmd:
            return
        elapsed = time.time() - (cmd.started_at or time.time())
        timeout_map = {
            "login": 600,      # 登录最多等 10 分钟
            "comment": 1200,   # 评论最多等 20 分钟
            "collect": 600,    # 采集最多等 10 分钟
            "nurture": 21600,  # 养号最多等 6 小时
        }
        max_time = timeout_map.get(cmd.cmd_type, 3600)
        if elapsed > max_time:
            cmd.status = CommandStatus.TIMED_OUT
            cmd.message = f"超时自动清理 ({int(elapsed)}s > {max_time}s)"
            self.current_cmd = None
            logger.warning(f"  ⏰ 清理卡死命令 ({cmd.cmd_type}, {int(elapsed)}s > {max_time}s)")

    def send(self, cmd: Command) -> dict:
        with self._lock:
            self._clear_stale()

            # 直接发送到 guardd 调度器（不再排队串行化）
            # guardd 调度器内部管理 3 个 slot 和优先级队列
            if self.is_local:
                result = self._send_local(cmd)
            else:
                result = self._send_remote(cmd)
            if "error" not in result:
                self.current_cmd = cmd
            self.commands.insert(0, cmd)
            self._trim_history()
            return result

    def _send_local(self, cmd: Command) -> dict:
        # 优先通过 guardd 调度引擎提交（v4.3.0）
        scheduler_task = {
            "task_id": cmd.run_id,
            "cmd_type": cmd.cmd_type,
            "accounts": cmd.accounts,
            "blueprint": cmd.params.get("blueprint", ""),
            "rounds": cmd.params.get("rounds", 1),
            "priority": cmd.params.get("priority", 0 if cmd.cmd_type in ("interact", "comment") else 1),
            "interval": cmd.params.get("interval", 0),
            "params": cmd.params,
            "command_line": cmd.command_line,
        }
        guardd_result = _guardd_api("POST", "/scheduler/submit", scheduler_task)
        if guardd_result.get("status") == "accepted":
            cmd.status = CommandStatus.DISPATCHING
            cmd.started_at = time.time()
            return {"guardd": True, "scheduler": True}

        logger.warning(f"  ❌ {cmd.run_id} -> scheduler submit failed: {guardd_result}")
        cmd.status = CommandStatus.FAILED
        cmd.error = "guardd scheduler 不可用"
        return {"guardd": False, "error": "guardd scheduler 不可用"}

        guardd_result = _guardd_api("POST", "/task", {
            "cmd": full_shell_cmd,
            "run_id": cmd.run_id,
            "machine": HOSTNAME,
        })
        if guardd_result.get("status") == "accepted":
            cmd.pid = guardd_result.get("pid")
            cmd.status = CommandStatus.DISPATCHING
            cmd.started_at = time.time()
            return {"pid": cmd.pid, "guardd": True}

        # guardd 完全不可用时降级为 subprocess（向后兼容）
        logger.warning(f"guardd 不可用，降级为 subprocess: {cmd.run_id}")
        try:
            mc_count = int(subprocess.run(
                ["pgrep", "-f", "python3.*-m mc"], capture_output=True, text=True, timeout=3
            ).stdout.strip() or "0") or 0
            if mc_count > 600:
                subprocess.run(["pkill", "-f", "python3.*-m mc"], capture_output=True, timeout=3)
                time.sleep(1)
                return {"error": f"系统 mc 进程数过高 ({mc_count})，已自动清理，请重试"}
        except:
            pass

        scripts_dir = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts"
        log_dir = AGENT_LOCAL / "runtime" / "commands"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{cmd.run_id}.log"
        cmd.log_path = log_path
        log_fh = open(log_path, "w")

        if cmd.cmd_type == "nurture":
            wrapper = str(AGENT_SYNC / "05_tools" / "10_dashboard" / "services" / "nurture_runner.sh")
            accts = ",".join(cmd.accounts)
            bp = cmd.params.get("blueprint") or "douyin_daily"
            rounds = cmd.params.get("rounds") or 10
            p = subprocess.Popen(
                ["bash", wrapper, accts, bp, str(rounds), cmd.run_id],
                stdout=log_fh, stderr=subprocess.STDOUT
            )
        else:
            python_path = f"{Path.home()}/.workbuddy/binaries/python/envs/agent-os/bin/python3"
            full_cmd = f"cd {scripts_dir} && PYTHONPATH='{scripts_dir}' {python_path} -m {cmd.command_line}"
            p = subprocess.Popen(
                full_cmd, shell=True, stdout=log_fh, stderr=subprocess.STDOUT
            )

        cmd.pid = p.pid
        cmd.status = CommandStatus.DISPATCHING
        cmd.started_at = time.time()
        return {"pid": cmd.pid, "log_path": str(log_path)}

    def _send_remote(self, cmd: Command) -> dict:
        logger.info("_send_remote: {} @ {}, accounts={}".format(cmd.run_id, self.machine, cmd.accounts))

        # ── 路径1: guardd /scheduler/submit (新调度引擎) ──
        scheduler_task = {
            "task_id": cmd.run_id,
            "cmd_type": cmd.cmd_type,
            "accounts": cmd.accounts,
            "blueprint": cmd.params.get("blueprint", ""),
            "rounds": cmd.params.get("rounds", 1),
            "priority": cmd.params.get("priority", 0 if cmd.cmd_type in ("interact", "comment") else 1),
            "interval": cmd.params.get("interval", 0),
            "params": cmd.params,
            "command_line": cmd.command_line,
        }
        guardd_result = _guardd_api("POST", "/scheduler/submit", scheduler_task, machine=self.machine)
        if guardd_result.get("status") == "accepted":
            cmd.status = CommandStatus.DISPATCHING
            cmd.started_at = time.time()
            cmd.message = "sent to {} via scheduler".format(self.machine)
            logger.info("  ✅ {} -> scheduler accepted".format(cmd.run_id))
            return {"guardd": True, "scheduler": True, "machine": self.machine}
        logger.info("  ⚠️ {} -> scheduler submit failed (result={}), trying old /task".format(cmd.run_id, guardd_result))

        # ── 路径2: guardd /task (旧API) ──
        # 构造 shell 命令
        py_discover = 'PY=$(ls $HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3 2>/dev/null || which python3); '
        scripts_dir = "$AGENT_SYNC/05_tools/07_matrix/scripts"
        env_setup = "export AGENT_SYNC=\"$HOME/workbuddy-agent-os/agent-sync\"; export AGENT_LOCAL=\"$HOME/workbuddy-agent-os/agent-local\"; export MC_PYTHON=\"$PY\"; export PYTHONPATH={}:$PYTHONPATH; ".format(scripts_dir)
        if cmd.cmd_type == "nurture":
            accts = ",".join(cmd.accounts)
            _bp = cmd.params.get("blueprint") or "douyin_daily"
            _rd = cmd.params.get("rounds") or 10
            wrapper = "$AGENT_SYNC/05_tools/10_dashboard/services/nurture_runner.sh"
            full_cmd = "{} {} bash {} {} {} {}".format(py_discover, env_setup, wrapper, accts, _bp, _rd, cmd.run_id)
        else:
            full_cmd = "{} {} cd {} && $MC_PYTHON -m {}".format(py_discover, env_setup, scripts_dir, cmd.command_line)
        guardd_result = _guardd_api("POST", "/task", {
            "cmd": full_cmd, "run_id": cmd.run_id, "machine": self.machine,
        }, machine=self.machine)
        if guardd_result.get("status") == "accepted":
            cmd.pid = guardd_result.get("pid")
            cmd.status = CommandStatus.DISPATCHING
            cmd.started_at = time.time()
            cmd.message = "sent to {} via guardd /task".format(self.machine)
            logger.info("  ✅ {} -> /task accepted".format(cmd.run_id))
            return {"pid": cmd.pid, "guardd": True, "machine": self.machine}
        logger.info("  ⚠️ {} -> /task failed (result={}), trying SSH".format(cmd.run_id, guardd_result))

        # ── 路径3: SSH nohup ──
        if not self.ssh_target:
            cmd.status = CommandStatus.FAILED
            cmd.message = "machine {} guardd and SSH unavailable".format(self.machine)
            logger.warning("  ❌ {} -> SSH target not available".format(cmd.run_id))
            return {"error": cmd.message}

        logger.warning("  🔌 {} -> fallback to SSH: {}".format(cmd.run_id, self.ssh_target))
        ssh_cmd = "nohup {} > /tmp/ops_{}.log 2>&1 &".format(full_cmd, cmd.run_id)

        try:
            r = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no",
                 self.ssh_target, ssh_cmd],
                capture_output=True, text=True, timeout=15
            )
            if r.returncode != 0:
                logger.warning("  ❌ {} -> SSH returned code {}: {}".format(cmd.run_id, r.returncode, r.stderr[:200]))
                cmd.status = CommandStatus.FAILED
                cmd.message = "SSH failed (code {}): {}".format(r.returncode, r.stderr[:100])
                return {"error": cmd.message}
            cmd.status = CommandStatus.DISPATCHING
            cmd.started_at = time.time()
            cmd.message = "command sent via SSH: {}".format(self.ssh_target)
            logger.info("  ✅ {} -> SSH sent OK".format(cmd.run_id))
            return {"status": "sent", "target": self.ssh_target}
        except Exception as e:
            cmd.status = CommandStatus.FAILED
            cmd.message = "SSH send failed: {}".format(e)
            logger.warning("  ❌ {} -> SSH exception: {}".format(cmd.run_id, e))
            return {"error": str(e)}

    def _remote_poll_result(self, cmd: Command) -> bool:
        """远程检查：SSH 到远端机器读取 result 文件"""
        if not self.ssh_target:
            return False
        try:
            if cmd.cmd_type == "nurture":
                check = f"cat $AGENT_LOCAL/runtime/nurture/results/{cmd.run_id}.json 2>/dev/null"
            else:
                check = f"cat $AGENT_LOCAL/runtime/results/{cmd.run_id}.json 2>/dev/null; cat /tmp/ops_{cmd.run_id}.log 2>/dev/null"
            r = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
                 self.ssh_target,
                 f"export AGENT_LOCAL=\"$HOME/workbuddy-agent-os/agent-local\"; {check}"],
                capture_output=True, text=True, timeout=8
            )
            if r.returncode == 0 and r.stdout.strip():
                # 尝试解析 JSON（nurture 结果文件）
                try:
                    data = json.loads(r.stdout)
                    cmd.result = data
                    s = data.get("status", "running")
                    if s == "completed":
                        cmd.status = CommandStatus.COMPLETED
                        cmd.completed_at = time.time()
                        cmd.message = f"远程执行完成"
                        return True
                    elif s == "failed":
                        cmd.status = CommandStatus.FAILED
                        cmd.completed_at = time.time()
                        cmd.message = f"远程执行失败: {data.get('error','')}"
                        return True
                    else:
                        steps = data.get("steps", {})
                        cmd.message = f"运行中 (已完成 {steps.get('success', 0)}/{steps.get('total', '?')} 步)"
                        cmd.status = CommandStatus.RUNNING
                        return True
                except ValueError:
                    # 不是 JSON — 可能是日志内容，检查是否包含完成标记
                    if "completed" in r.stdout.lower() or "done" in r.stdout.lower():
                        cmd.status = CommandStatus.COMPLETED
                        cmd.completed_at = time.time()
                        cmd.message = "远程执行完成"
                        return True
                    if "error" in r.stdout.lower() or "traceback" in r.stdout.lower():
                        cmd.status = CommandStatus.FAILED
                        cmd.completed_at = time.time()
                        cmd.message = "远程执行失败"
                        return True
                    # 有输出但未完成 — 运行中
                    if len(r.stdout.strip()) > 20:
                        cmd.status = CommandStatus.RUNNING
                        cmd.message = f"远程进程输出中 ({len(r.stdout)}bytes)"
                        return True
            return False
        except:
            return False

    def poll(self, cmd: Command) -> CommandStatus:
        with self._lock:
            if cmd.status.is_terminal:
                return cmd.status
            cmd.last_poll_at = time.time()

            # 按 cmd_type 获取轮询策略
            strategy = CMD_POLL_STRATEGY.get(cmd.cmd_type, DEFAULT_POLL_STRATEGY)
            grace_period = strategy.get("grace_period", 30)
            max_timeout = cmd.params.get("timeout", strategy.get("timeout", 600))
            check_process = strategy.get("check_process", True)
            check_log_completed = strategy.get("check_log_completed", [])

            # 通过 guardd 查询任务状态（v7）
            g_tasks = _guardd_api("GET", "/tasks", machine=self.machine)
            for gt in g_tasks if isinstance(g_tasks, list) else []:
                if gt.get("run_id") == cmd.run_id:
                    gs = gt.get("status", "")
                    if gs == "completed":
                        cmd.status = CommandStatus.COMPLETED
                        cmd.completed_at = time.time()
                        return cmd.status
                    elif gs in ("failed", "crashed"):
                        cmd.status = CommandStatus.FAILED
                        cmd.completed_at = time.time()
                        return cmd.status
                    elif gs == "cancelled":
                        cmd.status = CommandStatus.CANCELLED
                        cmd.completed_at = time.time()
                        return cmd.status
                    elif gs == "running":
                        cmd.status = CommandStatus.RUNNING
                        return cmd.status

            # 远程命令：通过 SSH 读取结果
            if not self.is_local and self.ssh_target:
                if self._remote_poll_result(cmd):
                    return cmd.status

            # 本机命令：优先读统一结果文件（mc/engine.py 写入）
            if self.is_local:
                _result_file = AGENT_LOCAL / "runtime" / "results" / f"{cmd.run_id}.json"
                if _result_file.exists():
                    try:
                        _data = json.loads(_result_file.read_text())
                        cmd.result = _data
                        s = _data.get("status", "running")
                        if s == "completed":
                            cmd.status = CommandStatus.COMPLETED
                            cmd.message = _data.get("message", "执行完成")
                            cmd.completed_at = time.time()
                        elif s == "failed":
                            cmd.status = CommandStatus.FAILED
                            cmd.message = _data.get("error", _data.get("message", "执行失败"))
                            cmd.completed_at = time.time()
                        elif s == "crashed":
                            cmd.status = CommandStatus.CRASHED
                            cmd.message = _data.get("error", "进程崩溃")
                            cmd.completed_at = time.time()
                        elif s == "cancelled":
                            cmd.status = CommandStatus.CANCELLED
                            cmd.completed_at = time.time()
                        else:
                            cmd.status = CommandStatus.RUNNING
                            steps = _data.get("steps", {})
                            cmd.message = f"运行中 (已完成 {steps.get('success', 0)}/{steps.get('total', '?')} 步)"
                        return cmd.status
                    except:
                        pass

                # 兼容旧路径: runtime/nurture/results/
                if cmd.cmd_type == "nurture":
                    result_dir = AGENT_LOCAL / "runtime" / "nurture" / "results"
                    result_file = result_dir / f"{cmd.run_id}.json"
                    if result_file.exists():
                        try:
                            data = json.loads(result_file.read_text())
                            s = data.get("status", "running")
                            cmd.result = data
                            if s == "completed":
                                cmd.status = CommandStatus.COMPLETED
                                cmd.completed_at = time.time()
                            elif s == "failed":
                                cmd.status = CommandStatus.FAILED
                                cmd.completed_at = time.time()
                            else:
                                cmd.status = CommandStatus.RUNNING
                                steps = data.get("steps", {})
                                cmd.message = f"运行中 (已完成 {steps.get('success', 0)}/{steps.get('total', '?')} 步)"
                            return cmd.status
                        except:
                            pass

            # 根据策略决定是否检测进程存活
            alive = False
            if check_process:
                alive = self._is_alive(cmd)
                if alive:
                    cmd.status = CommandStatus.RUNNING
                    cmd.message = "进程运行中"
                    return cmd.status
            else:
                # check_process=False：不依赖进程存活判断（login/logout 快速命令）
                # 检查日志中是否有完成标记
                if check_log_completed and cmd.log_path and cmd.log_path.exists():
                    log_text = cmd.log_path.read_text(encoding="utf-8", errors="replace")
                    for marker in check_log_completed:
                        if marker in log_text:
                            cmd.status = CommandStatus.COMPLETED
                            cmd.message = f"检测到完成标记: {marker}"
                            cmd.completed_at = time.time()
                            return cmd.status

            elapsed = cmd.elapsed_sec
            if elapsed < grace_period:
                cmd.status = CommandStatus.RUNNING
                cmd.message = f"{'远程' if not self.is_local else ''}进程启动中 ({int(elapsed)}s/{grace_period}s)"
                return cmd.status

            if elapsed > max_timeout:
                cmd.status = CommandStatus.TIMED_OUT
                cmd.message = f"执行超时 ({int(elapsed)}s > {max_timeout}s)"
                cmd.completed_at = time.time()
                return cmd.status

            if cmd.log_path and cmd.log_path.exists():
                tail = cmd.log_path.read_text().strip()
                if tail:
                    cmd.status = CommandStatus.COMPLETED
                    cmd.message = "进程已结束，无异常"
                    cmd.completed_at = time.time()
                    return cmd.status

            # 远程：检查是否有任何输出（即使进程已退出）
            if not self.is_local and self.ssh_target:
                try:
                    r = subprocess.run(
                        ["ssh", "-o", "ConnectTimeout=5", self.ssh_target,
                         f"cat /tmp/ops_{cmd.run_id}.log 2>/dev/null | wc -c"],
                        capture_output=True, text=True, timeout=5
                    )
                    if r.returncode == 0 and r.stdout.strip().isdigit() and int(r.stdout.strip()) > 0:
                        cmd.status = CommandStatus.COMPLETED
                        cmd.message = "远程进程已完成"
                        cmd.completed_at = time.time()
                        return cmd.status
                except:
                    pass

            cmd.status = CommandStatus.CRASHED
            cmd.message = "进程已消失，无输出"
            cmd.completed_at = time.time()
            return cmd.status

    def _is_alive(self, cmd: Command) -> bool:
        if self.is_local:
            if cmd.pid:
                try:
                    os.kill(cmd.pid, 0)
                    return True
                except OSError:
                    return False
            return False
        if self.ssh_target:
            # 先按 run_id 查（log 文件重定向包含 run_id）
            patterns = [cmd.run_id]
            # 再按进程名查（实际进程可能不包含 run_id）
            type_patterns = {
                "collect": ["mc run.*douyin_read_profile", "mc run.*xiaohongshu_read_profile"],
                "nurture": ["mc run", "camoufox.*-no-remote"],
                "login": ["smart-login", "mc smart-login"],
                "comment": ["task comment", "mc task"],
                "like": ["mc task like"],
            }
            patterns.extend(type_patterns.get(cmd.cmd_type, []))
            try:
                for p in patterns:
                    r = subprocess.run(
                        ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
                         self.ssh_target, f"pgrep -f '{p}'"],
                        capture_output=True, text=True, timeout=8
                    )
                    if r.returncode == 0:
                        return True
            except:
                pass
        return False

    def cancel(self, cmd: Command) -> dict:
        with self._lock:
            if cmd.status.is_terminal:
                return {"error": "命令已结束"}

            # 优先通过 guardd 停止（v7）
            g_stop = _guardd_api("POST", f"/task/{cmd.run_id}/stop", machine=self.machine)
            if g_stop.get("status") in ("stopped", "already_stopped"):
                # guardd 已处理进程清理
                pass
            else:
                # 降级：手动杀进程 + 清理浏览器
                if self.is_local and cmd.pid:
                    try:
                        os.kill(cmd.pid, 15)
                        time.sleep(0.5)
                        os.kill(cmd.pid, 9)
                    except:
                        pass
                    for aid in cmd.accounts:
                        try:
                            subprocess.run(["pkill", "-f", aid], capture_output=True, timeout=3)
                        except:
                            pass
                elif not self.is_local and self.ssh_target:
                    try:
                        subprocess.run(
                            ["ssh", self.ssh_target, f"pkill -f '{cmd.run_id}' 2>/dev/null"],
                            capture_output=True, text=True, timeout=5
                        )
                    except:
                        pass

            cmd.status = CommandStatus.CANCELLED
            cmd.message = "用户取消"
            cmd.completed_at = time.time()

            # 如果是当前正在执行的命令 → 启动下一条
            if self.current_cmd is cmd:
                self._start_next()

            return {"ok": True}

    def _cleanup_zombies(self):
        """清理僵尸进程：进程已死但状态未更新的命令"""
        for cmd in self.commands[:]:
            if cmd.status.is_active:
                if not self._is_alive(cmd):
                    if cmd.log_path and cmd.log_path.exists() and cmd.log_path.stat().st_size > 0:
                        cmd.status = CommandStatus.COMPLETED
                        cmd.message = "进程已结束"
                    else:
                        cmd.status = CommandStatus.CRASHED
                        cmd.message = "进程已消失"
                    cmd.completed_at = time.time()

        # 命令刚完成 → 启动队列下一条
        if cmd.status.is_terminal and self.current_cmd is cmd:
            self._start_next()

    def _start_next(self):
        """当前命令完成后，启动队列中的下一条"""
        self.current_cmd = None
        if self.queued_cmds:
            next_cmd = self.queued_cmds.pop(0)
            logger.info(f"  ⏩ 启动队列下一条: {next_cmd.run_id} ({next_cmd.cmd_type})")
            if self.is_local:
                r = self._send_local(next_cmd)
            else:
                r = self._send_remote(next_cmd)
            if "error" not in r:
                self.current_cmd = next_cmd

    def _trim_history(self):
        while len(self.commands) > self.max_history:
            self.commands.pop()

    def get_active_commands(self) -> list[Command]:
        return [c for c in self.commands if c.status.is_active]

    def get_queue_info(self) -> dict:
        """返回队列状态"""
        return {
            "busy": self.is_busy,
            "current_run_id": self.current_cmd.run_id if self.current_cmd else None,
            "current_type": self.current_cmd.cmd_type if self.current_cmd else None,
            "current_status": self.current_cmd.status.value if self.current_cmd else None,
            "queued_count": len(self.queued_cmds),
            "queued": [{"run_id": c.run_id, "type": c.cmd_type, "accounts": c.accounts}
                       for c in self.queued_cmds],
        }

    def get_recent_commands(self, limit: int = 20) -> list[dict]:
        return [c.to_dict() for c in self.commands[:limit]]


# ── 操作注册表（统一 cmd_type → 命令模板映射）───────────────
# 本注册表是整个系统通往执行层的唯一映射表。
# 新增操作类型只需在这里加一行，不需要改 dispatch 逻辑。
#
# 注册表字段说明:
#   template        — 命令模板，用 {ids} {blueprint} {rounds} 等变量渲染
#   defaults        — 参数默认值（前端不传 params 时使用）
#   auto_blueprint  — 是否根据账号 platform 字段自动选择采集蓝图
#   blueprint_map   — platform → blueprint 映射表
#   runner          — shell 包装器路径（nurture 专用）
#   single_account  — 是否一次只处理一个账号
#   required_params — 必填参数列表（缺失则报错）
#
# 前端调用示例:
#   POST /api/ops/run {type:'collect', accounts:['douyin_01'], params:{rounds:1}}
#   → CMD_REGISTRY["collect"] → "mc run --accounts=douyin_01 --blueprints=douyin_read_profile --rounds=1"
CMD_REGISTRY = {
    "nurture": {
        "runner": "nurture_runner.sh",            # shell 包装器
        "defaults": {"blueprint": "douyin_daily_clean", "rounds": 10},
        "auto_blueprint": False,
    },
    "collect": {
        "template": "mc run --accounts={ids} --blueprints={blueprint} --rounds={rounds}",
        "defaults": {"rounds": 1},
        "auto_blueprint": True,
        "blueprint_map": {
            "douyin": "douyin_read_profile",
            "xiaohongshu": "xiaohongshu_read_profile",
        },
    },
    "login": {
        "template": "mc smart-login {ids}",
        "single_account": True,
    },
    "logout": {
        "template": "mc run --accounts={ids} --blueprints=douyin_daily --rounds=1 --engine=auto",
    },
    "comment": {
        "template": "mc task comment --account={ids} --url={url} --direction={direction}",
        "required_params": ["url"],
    },
    "like": {
        "template": "mc run --accounts={ids} --blueprints=douyin_daily --rounds=1",
    },
    "interact": {
        "template": "mc run --accounts={ids} --blueprints={blueprint} --rounds=1 --url={url} --direction={direction} --corpus={corpus}",
        "defaults": {"blueprint": "interact_comment", "rounds": 1, "direction": "", "corpus": ""},
        "required_params": ["url"],
    },
    "record": {
        "template": "mc record start --accounts={ids} --platform={platform}",
        "single_account": True,
        "defaults": {"platform": "douyin"},
    },
    "smart_comment": {
        "master_only": True,
        "required_params": ["urls"],
        "single_account": True,
    },
}


# ── 命令轮询策略（按 cmd_type 设定不同的超时/检测方式）────────
# 解决：登录进程退出后 poll 不知道它已完成的问题
CMD_POLL_STRATEGY = {
    "login": {
        "grace_period": 15,       # 登录通常15秒内完成启动
        "timeout": 120,            # 登录超时2分钟
        "check_process": False,    # smart-login 启动浏览器后进程退出
        "check_log_completed": ["登录成功", "SMS验证码已发送", "浏览器已打开"],
    },
    "collect": {
        "grace_period": 30,
        "timeout": 600,
        "check_process": True,
        "check_log_completed": ["📊 执行完成", "✅ 采集完成"],
    },
    "nurture": {
        "grace_period": 60,
        "timeout": 1800,
        "check_process": True,
        "check_log_completed": ["📊 执行完成", "✅ 全部"],
    },
    "comment": {
        "grace_period": 20,
        "timeout": 300,
        "check_process": True,
        "check_log_completed": ["评论已发送", "✅ 完成"],
    },
    "like": {
        "grace_period": 20,
        "timeout": 300,
        "check_process": True,
        "check_log_completed": ["✅ 执行完成"],
    },
    "logout": {
        "grace_period": 15,
        "timeout": 120,
        "check_process": False,
        "check_log_completed": ["已退出"],
    },
    "record": {
        "grace_period": 15,
        "timeout": 7200,
        "check_process": True,
        "check_log_completed": ["✅ 录制完成", "📦 录制包已保存"],
    },
}
DEFAULT_POLL_STRATEGY = {"grace_period": 30, "timeout": 600, "check_process": True, "check_log_completed": []}


# ── 命令总线 ────────────────────────────────────────────────
class CommandBus:
    """全局命令总线 — 所有操作的统一入口"""

    @classmethod
    def dispatch(cls, cmd_type: str, accounts: list, params: dict = None, wait: bool = False) -> dict:
        """主入口：按机器分组后分发
        之前: 每个账号一条命令
        现在: 每台机器一条命令（含多个账号）
        """
        params = params or {}
        force_machine = params.get("machine", "")
        dry_run = params.get("dry_run", False)
        now_ts = int(time.time())

        # ── 前置校验 ──
        if not cmd_type:
            return {"status": "error", "message": "type 必填 (login/logout/nurture/comment/like/collect)", "errors": [{"message": "type 必填"}]}
        if not accounts:
            return {"status": "error", "message": "accounts 必填 (至少一个账号ID)", "errors": [{"message": "accounts 为空"}]}
        if not isinstance(accounts, list):
            accounts = [accounts]

        # 获取所有账号信息
        try:
            from matrix_mgmt import MatrixManager
            mgr = MatrixManager()
            all_accts = {a["id"]: a for a in mgr.list_accounts()}
        except Exception as e:
            return {"status": "error", "message": f"加载账号失败: {e}", "errors": [{"message": str(e)}]}

        # ── 加载 ORACLE 宪法（账号→机器映射表）──
        oracle_map = {}  # account_id → assigned_machine
        try:
            oracle_path = AGENT_SYNC / "ORACLE.yaml"
            if oracle_path.exists():
                import yaml
                oracle = yaml.safe_load(oracle_path.read_text())
                for entry in oracle.get("accounts", []):
                    machine = entry.get("machine", "")
                    for plat, acct_id in entry.get("platforms", {}).items():
                        oracle_map[acct_id] = machine
        except:
            pass  # ORACLE 文件不存在时不阻断执行

        # ── 逐个账号校验 ──
        errors = []
        warnings = []
        machine_groups = {}
        for aid in accounts:
            acct = all_accts.get(aid) if isinstance(aid, str) else aid
            if not acct:
                errors.append({"account": str(aid), "message": "账号不存在"})
                continue
            machine = force_machine or acct.get("owner_machine", "")
            if not machine:
                errors.append({"account": aid, "message": f"账号 {aid} 未分配机器 (owner_machine 为空)"})
                continue
            # ORACLE 合规检查
            oracle_machine = oracle_map.get(aid)
            if oracle_machine and oracle_machine != machine:
                warnings.append({"account": aid, "message": f"账号 {aid} 按 ORACLE 应在机器 {oracle_machine}，实际发往 {machine}"})
            elif not oracle_machine:
                warnings.append({"account": aid, "message": f"账号 {aid} 未在 ORACLE 登记，建议 git pull 同步后执行 fleet_reconcile"})
            if machine not in machine_groups:
                machine_groups[machine] = []
            machine_groups[machine].append(acct)

        results = []

        # 第二步：按机器分组构建命令任务
        # 返回 list[dict] = {machine, cmd_type, ids_str, is_local, cmd_line, params, run_id}
        tasks = []
        for machine, accts in machine_groups.items():
            is_local = (machine == HOSTNAME)
            all_ids = ",".join(a["id"] for a in accts)

            if cmd_type == "nurture":
                plat_groups = {}
                for a in accts:
                    p = a.get("platform", "douyin")
                    plat_groups.setdefault(p, []).append(a)
                for platform, plat_accts in plat_groups.items():
                    bp = params.get("blueprint") or {"douyin": "douyin_daily_clean", "xiaohongshu": "xhs_daily"}.get(platform, "douyin_daily_clean")
                    r = params.get("rounds", 10)
                    # 拆解：每个账号生成独立任务（让 guardd 3 slot 并行执行）
                    for a in plat_accts:
                        aid = a["id"]
                        tasks.append({
                            "machine": machine, "cmd_type": cmd_type,
                            "ids_str": aid, "is_local": is_local,
                            "nickname": a.get("nickname", ""),
                            "platform": a.get("platform", "douyin"),
                            "cmd_line": f"mc run --accounts={aid} --blueprints={bp} --rounds={r} --mix --interval=45-90",
                            "run_id": f"{cmd_type}_{now_ts}_{machine}_{aid}",
                        })
            elif cmd_type == "smart_comment":
                # 智能评论：先分析视频，再按账号拆解
                urls = params.get("urls", [])
                if not urls:
                    errors.append({"account": all_ids, "message": "smart_comment 需要 urls 参数"})
                    continue
                direction = params.get("direction", "praise")
                corpus_category = params.get("corpus_category", "")
                
                # 跳过分析模式：使用传入的标题直接匹配语料，无需开浏览器
                skip_analysis = params.get("skip_analysis", False)
                titles_map = params.get("titles", {})  # {url: "标题文本"}
                if skip_analysis and titles_map:
                    results = {}
                    for url in urls:
                        results[url] = {
                            "url": url,
                            "title": titles_map.get(url, ""),
                            "industry": "general",
                            "comment": "",
                        }
                else:
                    try:
                        from services.video_analyzer import VideoAnalyzer
                        import asyncio
                        analyzer = VideoAnalyzer(max_concurrent=2)
                        # 获取该机器上账号的行业（取第一个账号的行业做匹配）
                        profiles = _load_profiles()
                        first_account = accts[0]["id"] if accts else ""
                        account_industry = profiles.get(first_account, {}).get("industry", None)
                        # 如果用户指定了语料分类，限制分析器只从该分类选评论
                        if corpus_category:
                            account_industry = corpus_category
                        results = asyncio.run(analyzer.analyze_batch(
                            urls, account_industry=account_industry, direction=direction
                        ))
                    except Exception as e:
                        logger.error(f"  视频分析失败: {e}")
                        errors.append({"account": all_ids, "message": f"视频分析失败: {e}"})
                        continue

                # 预览模式：只分析不分发，返回分析结果
                is_preview = params.get("preview", False)
                if is_preview:
                    preview = {}
                    for url, data in results.items():
                        preview[url] = {
                            "title": data.get("title", ""),
                            "description": data.get("description", ""),
                            "industry": data.get("industry", "general"),
                            "tags": data.get("tags", []),
                            "comment": data.get("comment", ""),
                        }
                    logger.info(f"  👁️ 预览模式: {len(preview)} 个视频分析完成")
                    # 直接返回预览数据，不入 tasks
                    return {"status": "ok", "preview": preview}
                
                # 使用自定义评论（用户在前端修改后传回）
                custom_comments = params.get("comments", {})
                
                # 导入 CorpusManager（延迟导入，避免循环依赖）
                import sys as _sys
                _scripts_dir = str(AGENT_SYNC / "05_tools" / "07_matrix" / "scripts")
                if _scripts_dir not in _sys.path:
                    _sys.path.insert(0, _scripts_dir)
                from mc.corpus import CorpusManager
                _cm = CorpusManager()
                
                # 每个账号 × 每个 URL = 最小任务单元
                for a in accts:
                    aid = a["id"]
                    for url_data in results.values():
                        url = url_data.get("url", "")
                        video_title = url_data.get("title", "")
                        # 优先级1: 用户手动编辑的评论
                        comment = custom_comments.get(url)
                        if not comment:
                            # 优先级2: 每个账号从语料库独立随机取
                            comment = _cm.get_comment_for_video(
                                video_title=video_title,
                                direction=direction,
                                account_id=aid,
                            )
                        if not comment:
                            comment = url_data.get("comment", "")  # 兜底用 analyzer 的
                        if not comment:
                            continue
                        tasks.append({
                            "machine": machine, "cmd_type": "comment",
                            "ids_str": aid, "is_local": is_local,
                            "cmd_line": f'mc task comment --account={shlex.quote(aid)} --url={shlex.quote(url)} --comment={shlex.quote(comment)} -y',
                            "run_id": f"smart_comment_{int(time.time())}_{machine}_{aid}",
                            "priority": 0,  # P0
                            "nickname": a.get("nickname", ""),
                            "platform": a.get("platform", "douyin"),
                        })
                        logger.info(f"  📝 [{aid}] → 评论: {comment[:40]}...")
            else:
                # 从操作注册表读取模板
                cmd_config = CMD_REGISTRY.get(cmd_type)
                if not cmd_config:
                    errors.append({"account": all_ids, "message": f"不支持的操作: {cmd_type}"})
                    continue

                template = cmd_config.get("template", "")
                defaults = cmd_config.get("defaults", {})
                auto_bp = cmd_config.get("auto_blueprint", False)
                bp_map = cmd_config.get("blueprint_map", {})

                # 合并参数：params 覆盖 defaults
                merged = dict(defaults)
                merged.update(params)

                # Auto-blueprint: 根据账号平台自动选择采集蓝图（多平台用逗号分隔）
                if auto_bp and not merged.get("blueprint"):
                    platforms = set(a.get("platform", "douyin") for a in accts)
                    bp_list = [bp_map.get(p, "douyin_read_profile") for p in sorted(platforms)]
                    merged["blueprint"] = ",".join(bp_list)

                # 任务拆解：interact/comment/collect 等交互任务拆成 per-account 子任务
                # 这样每台机器的 guardd 调度队列中能看到每个账号的独立状态
                if cmd_type in ("interact", "comment", "collect") and len(accts) > 1:
                    for a in accts:
                        aid = a["id"]
                        try:
                            cmd_line_a = template.format(ids=aid, ids_str=aid, **merged)
                        except KeyError:
                            safe_kw = {k: merged.get(k, "") for k in
                                      [p[1] for p in __import__("string").Formatter().parse(template) if p[1]]}
                            safe_kw.update({"ids": aid, "ids_str": aid})
                            cmd_line_a = template.format(**safe_kw)
                        tasks.append({
                            "machine": machine, "cmd_type": cmd_type,
                            "ids_str": aid, "is_local": is_local,
                            "cmd_line": cmd_line_a,
                            "run_id": f"{cmd_type}_{now_ts}_{machine}_{aid}",
                            "nickname": a.get("nickname", ""),
                            "platform": a.get("platform", "douyin"),
                            "priority": params.get("priority", 1),
                        })
                else:
                    # 普通任务（登录/单账号等）：一条命令包含所有账号
                    try:
                        cmd_line = template.format(ids=all_ids, ids_str=all_ids, **merged)
                    except KeyError:
                        safe_kw = {k: merged.get(k, "") for k in
                                  [p[1] for p in __import__("string").Formatter().parse(template) if p[1]]}
                        safe_kw.update({"ids": all_ids, "ids_str": all_ids})
                        cmd_line = template.format(**safe_kw)
                    if not cmd_line:
                        errors.append({"account": all_ids, "message": f"不支持的操作: {cmd_type}"})
                        continue
                    tasks.append({
                        "machine": machine, "cmd_type": cmd_type,
                        "ids_str": all_ids, "is_local": is_local,
                        "cmd_line": cmd_line,
                        "run_id": f"{cmd_type}_{now_ts}_{machine}",
                    })

        # 第三步：并行分发到各台机器
        dispatched_cmds = []
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _do_send(t):
            # 合并 task-specific 字段到 params
            merged_params = dict(params)
            for extra_key in ("nickname", "platform", "priority"):
                if extra_key in t:
                    merged_params[extra_key] = t[extra_key]
            return cls._execute_one(
                t["cmd_type"], t["ids_str"], t["machine"],
                t["is_local"], t["cmd_line"], merged_params,
                t["run_id"], results, errors, dry_run
            )

        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = [ex.submit(_do_send, t) for t in tasks]
            for f in as_completed(futures):
                try:
                    cmd = f.result()
                    if cmd:
                        dispatched_cmds.append(cmd)
                except Exception as e:
                    logger.error(f"并行分发异常: {e}")

        # 第四步：任务拆解（interact 类型拆成 per-account 子任务）
        decomposed_count = 0
        for cmd in dispatched_cmds[:]:
            if cmd.cmd_type == "interact" and len(cmd.accounts) > 1:
                logger.info(f"  拆解 interact 任务: {len(cmd.accounts)}个账号 → 独立子任务")
                for acct in cmd.accounts:
                    sub_task = copy.deepcopy(cmd)
                    sub_task.run_id = f"{cmd.run_id}_{acct}"
                    sub_task.accounts = [acct]
                    sub_task.cmd_line = cmd.cmd_line.replace(
                        ",".join(cmd.accounts), acct
                    )
                    sub_task.params = dict(cmd.params)
                    sub_task.params["decomposed_from"] = cmd.run_id
                    # 投递到 guardd
                    _guardd_api("POST", "/scheduler/submit", {
                        "task_id": sub_task.run_id,
                        "cmd_type": "interact",
                        "accounts": [acct],
                        "blueprint": cmd.params.get("blueprint", "interact_comment"),
                        "priority": 0,
                        "interval": cmd.params.get("interval", 0),
                        "params": cmd.params,
                    }, machine=cmd.machine)
                    decomposed_count += 1
                # 移除原始群组命令
                dispatched_cmds.remove(cmd)

        # 第五步：等待执行结果（仅 wait=True 时）
        per_machine = {}
        if wait and dispatched_cmds:
            deadline = time.time() + params.get("timeout", 600)
            while time.time() < deadline:
                all_terminal = True
                for cmd in dispatched_cmds:
                    session = MachineSession.get(cmd.machine)
                    session.poll(cmd)
                    if not cmd.status.is_terminal:
                        all_terminal = False
                if all_terminal:
                    break
                time.sleep(15)

            # 聚合每台机器结果
            for cmd in dispatched_cmds:
                m = cmd.machine
                if m not in per_machine:
                    per_machine[m] = {"accounts": [], "status": "running",
                                       "success": 0, "failed": 0, "duration": 0}
                per_machine[m]["accounts"].extend(cmd.accounts)
                per_machine[m]["status"] = cmd.status.value
                per_machine[m]["duration"] = max(per_machine[m]["duration"], cmd.elapsed_sec)
                result_data = cmd.result or {}
                steps = result_data.get("steps", {}) or {}
                per_machine[m]["success"] += steps.get("success", 0) if steps else 0
                per_machine[m]["failed"] += steps.get("failed", 0) if steps else 0

            # 若全部完成则标记总状态
            all_terminal = all(cmd.status.is_terminal for cmd in dispatched_cmds)
            for m in per_machine:
                per_machine[m]["status"] = per_machine[m]["status"] if all_terminal else "running"

        total_success = sum(pm["success"] for pm in per_machine.values())
        total_failed = sum(pm["failed"] for pm in per_machine.values())
        total_accounts = sum(len(pm["accounts"]) for pm in per_machine.values())

        # 写入 batch log（smart_comment 专用，非预览模式）
        if cmd_type == "smart_comment" and not dry_run and not params.get("preview"):
            try:
                _save_batch_log(
                    batch_id=params.get("decomposed_from", f"smart_comment_{now_ts}"),
                    urls=params.get("urls", []),
                    video_ids=params.get("video_ids", []),
                    direction=params.get("direction", ""),
                    interval=params.get("interval", ""),
                    total=len(dispatched_cmds),
                    account_count=len(accts),
                    video_count=len(params.get("urls", [])),
                    machine_counts=per_machine if per_machine else {},
                )
            except Exception:
                pass

        return {
            "status": "completed" if (wait and all_terminal) else ("accepted" if not dry_run else "plan"),
            "total_accounts": total_accounts or None,
            "total_success": total_success or None,
            "total_failed": total_failed or None,
            "commands": results,
            "per_machine": per_machine if per_machine else None,
            "errors": errors if errors else None,
            "warnings": warnings if warnings else None,
        }

    @classmethod
    def _execute_one(cls, cmd_type, ids_str, machine, is_local, cmd_line, params, run_id, results, errors, dry_run):
        """执行单条命令，返回 Command 对象（供调用方追踪结果）"""
        acct_ids = ids_str.split(",")
        if dry_run:
            results.append({
                "accounts": acct_ids, "account": ids_str,
                "machine": machine, "is_local": is_local, "command": cmd_line,
            })
            return None

        cmd = Command(
            cmd_type=cmd_type, accounts=acct_ids, machine=machine,
            command_line=cmd_line, run_id=run_id, params=params
        )

        session = MachineSession.get(machine)
        cmd.status = CommandStatus.PREFLIGHTING
        pf = session.preflight()
        if not pf["ok"]:
            cmd.status = CommandStatus.PREFLIGHT_FAILED
            cmd.message = pf["message"]
            errors.append({"account": ids_str, "message": pf["message"]})
            results.append(cmd.to_dict())
            return cmd

        for a in acct_ids:
            session.graceful_exit(a)

        session.send(cmd)
        results.append(cmd.to_dict())
        return cmd

    @classmethod
    def get_status(cls, machine: str = None, account: str = None) -> list[dict]:
        """查询各机状态 — 优先从 guardd HTTP API 读取"""
        results = []
        machines = [machine] if machine else list(MachineSession._sessions.keys())
        if not machines:
            machines = [HOSTNAME]
        for m_name in machines:
            try:
                data = _guardd_api("GET", "/scheduler/tasks", machine=m_name)
                if data:
                    results.append({"machine": m_name, "data": data})
                    continue
            except Exception:
                pass
            # fallback: 从 MachineSession 读取（兼容旧版）
            session = MachineSession.get(m_name)
            for cmd in session.commands:
                if account and account not in cmd.accounts:
                    continue
                session.poll(cmd)
                results.append(cmd.to_dict())
        return results
    
    @classmethod
    def get_machine_status(cls, machine: str) -> dict:
        """查询单机状态 — 优先 guardd"""
        try:
            data = _guardd_api("GET", "/scheduler/tasks", machine=machine)
            if data:
                from services.browser_orchestrator import check_running_browsers
                browsers = check_running_browsers(machine)
                slots = data.get("slots", {})
                return {
                    "machine": machine,
                    "is_local": machine == HOSTNAME,
                    "active_task": data.get("active"),
                    "queue": data.get("queue", []),
                    "slots": slots,
                    "browsers_running": len(browsers) if browsers else slots.get("used", 0),
                    "browser_list": browsers if browsers else [],
                }
        except Exception:
            pass
        # fallback
        session = MachineSession.get(machine)
        return super().get_machine_status(machine)

    @classmethod
    def cancel(cls, run_id: str) -> dict:
        for session in MachineSession._sessions.values():
            for c in session.commands:
                if c.run_id == run_id:
                    return session.cancel(c)
        return {"error": f"未找到命令: {run_id}"}

    @classmethod
    def get_machine_status(cls, machine: str) -> dict:
        session = MachineSession.get(machine)
        active = session.get_active_commands()
        from services.browser_orchestrator import check_running_browsers
        browsers = check_running_browsers(machine)
        return {
            "machine": machine,
            "is_local": session.is_local,
            "active_commands": len(active),
            "browsers_running": len(browsers),
            "browser_list": browsers,
            "reachable": session.ssh_target is not None or session.is_local,
            "queue": session.get_queue_info(),
        }

    @classmethod
    def get_all_machines_status(cls) -> dict:
        from services.browser_orchestrator import check_running_browsers
        machines = {}
        # 从 guardd 查询所有已知机器
        known_machines = set(MachineSession._sessions.keys()) | {HOSTNAME}
        try:
            import yaml
            oracle = yaml.safe_load(ORACLE_PATH.read_text())
            for m_name in oracle.get("machines", {}):
                known_machines.add(m_name)
        except:
            pass
        for m_name in sorted(known_machines):
            machines[m_name] = cls.get_machine_status(m_name)
        return {"machines": machines}


# ── Poll 守卫线程（已迁移到 guardd 调度引擎）────────────────
# v4.3.0: CommandBus 不再负责轮询，由各机 guardd 的 Scheduler.run_cycle() 处理
# 保留空桩以兼容旧代码引用
def _start_poll_guard():
    """已废弃 — 轮询由 guardd 调度引擎处理"""
    pass


def cleanup_stale_commands() -> int:
    """清理所有僵尸命令：进程已死但状态为 running 的标记为 CRASHED"""
    count = 0
    for name, session in MachineSession._sessions.items():
        for cmd in session.commands:
            if cmd.status.is_active:
                # 先 poll 一下看能否自动判定
                session.poll(cmd)
                if cmd.status.is_active:
                    strategy = CMD_POLL_STRATEGY.get(cmd.cmd_type, DEFAULT_POLL_STRATEGY)
                    gp = strategy.get("grace_period", 30)
                    if cmd.elapsed_sec > (gp + 5):
                        cmd.status = CommandStatus.CRASHED
                        cmd.message = "僵尸清理: 进程已消失"
                        cmd.completed_at = time.time()
                        count += 1
                        logger.info(f"  🧹 清理僵尸: {cmd.run_id[:30]} ({cmd.cmd_type})")
        # 如果当前命令被清理了，启动下一条
        if session.current_cmd and session.current_cmd.status.is_terminal:
            session._start_next()
    return count


# ── Batch Log（执行记录持久化）─────────────────────────────

_BATCH_LOG_DIR = None

def _get_batch_log_dir():
    global _BATCH_LOG_DIR
    if _BATCH_LOG_DIR is None:
        _BATCH_LOG_DIR = AGENT_LOCAL / "runtime" / "commands" / "batches"
        _BATCH_LOG_DIR.mkdir(parents=True, exist_ok=True)
    return _BATCH_LOG_DIR


def _save_batch_log(batch_id: str, urls: list, video_ids: list,
                     direction: str, interval: str, total: int,
                     account_count: int, video_count: int,
                     machine_counts: dict):
    """保存一批任务的执行记录到 JSONL"""
    import json, threading, time
    log_entry = {
        "batch_id": batch_id,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "smart_comment",
        "total": total,
        "video_count": video_count,
        "account_count": account_count,
        "urls": urls[:20],  # 只存前20个，避免文件太大
        "video_ids": video_ids[:20],
        "direction": direction,
        "interval": interval,
        "machine_counts": machine_counts,
    }
    today = time.strftime("%Y-%m-%d")
    log_file = _get_batch_log_dir() / f"{today}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def _load_batch_logs(limit: int = 50) -> list:
    """读取执行记录（最新 N 条）"""
    import json
    log_dir = _get_batch_log_dir()
    if not log_dir.exists():
        return []
    entries = []
    for f in sorted(log_dir.glob("*.jsonl"), reverse=True):
        lines = f.read_text(encoding="utf-8").strip().split("\n")
        for line in reversed(lines):
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            if len(entries) >= limit:
                break
        if len(entries) >= limit:
            break
    return entries

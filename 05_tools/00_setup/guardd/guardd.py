#!/usr/bin/env python3
"""
guardd — AgentOS 联邦式协同守护进程

职责：每 5 分钟执行一轮 7 模块循环，自动化跨机器协同。
安装方式：launchd (macOS) 或 crontab
周期：300 秒（可配置）

所有模块使用规则引擎，不调用 LLM，0 token 消耗。
"""
version = "1.0.0"

import json
import logging
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── 路径常量 ──────────────────────────────────────────────
AGENT_SYNC = Path.home() / "workbuddy-agent-os" / "agent-sync"
AGENT_LOCAL = Path.home() / "workbuddy-agent-os" / "agent-local"
HOSTNAME = os.uname().nodename

CROSS_MACHINE = AGENT_SYNC / "04_memory" / "cross_machine"
DIR_EVENTS = CROSS_MACHINE / "events"
DIR_STATUS = CROSS_MACHINE / "status"
DIR_TASKS = CROSS_MACHINE / "tasks"
DIR_TASKS_PENDING = DIR_TASKS / "pending"
DIR_TASKS_COMPLETED = DIR_TASKS / "completed"
DIR_ENCRYPTED = CROSS_MACHINE / "encrypted"
DIR_ENCRYPTED_PENDING = DIR_ENCRYPTED / "pending"
DIR_ENCRYPTED_PROCESSED = DIR_ENCRYPTED / "processed"
DIR_KNOWLEDGE = CROSS_MACHINE / "knowledge"

DIR_REGISTRY = CROSS_MACHINE / "registry"
DIR_SECRETS = AGENT_LOCAL / "identity" / "secrets"
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

# ── 确保运行时目录存在 ───────────────────────────────
for d in [DIR_GUARDD_LOG, DIR_SUBMISSIONS_TRIAGE, DIR_TASKS_PENDING,
          DIR_TASKS_COMPLETED, DIR_ENCRYPTED_PENDING, DIR_ENCRYPTED_PROCESSED]:
    d.mkdir(parents=True, exist_ok=True)

# ── 日志配置 ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE)),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("guardd")


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
    """采集系统状态并写入 heartbeat.json"""
    status_dir = DIR_STATUS / HOSTNAME
    status_dir.mkdir(parents=True, exist_ok=True)

    # 采集 CPU 负载
    try:
        load_avg = os.getloadavg()
        cpu_load = round(load_avg[0], 2)  # 1 分钟负载
    except OSError:
        cpu_load = -1

    # 采集内存使用 (macOS: vm_stat)
    memory_info = {"total_gb": 0, "used_gb": 0, "percent": 0}
    try:
        result = subprocess.run(
            ["vm_stat"],
            capture_output=True, text=True, timeout=5
        )
        total_mem = 0
        page_size = 4096
        for line in result.stdout.split("\n"):
            if "page size of" in line:
                m = re.search(r"page size of (\d+)", line)
                if m:
                    page_size = int(m.group(1))
            if "Pages free" in line:
                m = re.search(r"Pages free:\s+(\d+)", line)
                if m:
                    free_pages = int(m.group(1))
            if "Pages active" in line:
                m = re.search(r"Pages active:\s+(\d+)", line)
                if m:
                    active_pages = int(m.group(1))
            if "Pages wired" in line:
                m = re.search(r"Pages wired down:\s+(\d+)", line)
                if m:
                    wired_pages = int(m.group(1))
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # 磁盘使用
    disk_info = {"total_gb": 0, "used_gb": 0, "available_gb": 0}
    try:
        st = os.statvfs(str(Path.home()))
        disk_info["total_gb"] = round(st.f_blocks * st.f_frsize / 1e9, 1)
        disk_info["available_gb"] = round(st.f_bavail * st.f_frsize / 1e9, 1)
        disk_info["used_gb"] = round(disk_info["total_gb"] - disk_info["available_gb"], 1)
    except OSError:
        pass

    # 读取上次 last_run.json 中的 current_task
    last_run = _read_json(LAST_RUN_FILE)
    current_task = None
    if last_run:
        current_task = last_run.get("current_task")

    heartbeat = {
        "hostname": HOSTNAME,
        "version": version,
        "role": "workstation",
        "os": f"macOS {os.uname().release} ({os.uname().machine})",
        "cpu": {
            "arch": os.uname().machine,
            "load_1m": cpu_load,
        },
        "memory": memory_info,
        "disk": disk_info,
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "status": "online",
        "guardd_version": version,
        "current_task": current_task,
    }

    path = status_dir / "heartbeat.json"
    path.write_text(json.dumps(heartbeat, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"  心跳已上报 — CPU load={cpu_load}, 磁盘可用={disk_info['available_gb']}G")


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
    """检查版本清单，发现新版本时触发更新事件"""
    remote_versions = _read_json(VERSIONS_FILE)
    if not remote_versions:
        logger.info("  版本清单不可用，跳过")
        return

    local_versions = _get_local_versions()
    components = remote_versions.get("components", {})
    updates_found = []

    for name, spec in components.items():
        local_ver = local_versions.get(name, {}).get("version", "0.0.0")
        remote_ver = spec.get("current", "0.0.0")

        # 简单版本比较（字符串比较适用于 semver 主版本号比较）
        if remote_ver != local_ver:
            is_breaking = spec.get("breaking_change", False)
            updates_found.append({
                "component": name,
                "from": local_ver,
                "to": remote_ver,
                "breaking": is_breaking,
                "description": spec.get("description", ""),
            })

    if updates_found:
        for u in updates_found:
            action = "需确认" if u["breaking"] else "自动"
            logger.info(f"  发现更新: {u['component']} {u['from']} → {u['to']} ({action})")

        _write_event("upgrades_available", {
            "updates": updates_found,
            "check_time": datetime.now(timezone.utc).isoformat(),
        })

        # 保存最新版本到本地（标记为已通知）
        new_local = {}
        for name, spec in components.items():
            new_local[name] = {
                "version": spec["current"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
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
    """解密发往本机的加密消息"""
    if not DIR_ENCRYPTED_PENDING.exists():
        return

    # 查找本地私钥
    private_key_path = DIR_SECRETS / "private_key.pem"
    if not private_key_path.exists():
        logger.info("  无私钥文件，跳过加密频道")

    # 扫描待处理消息
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
        logger.info(f"  发现加密消息 [{msg_id}]")

        # 解密（如果私钥存在且 cryptography 可用）
        if private_key_path.exists():
            try:
                from cryptography.hazmat.primitives import hashes, serialization
                from cryptography.hazmat.primitives.asymmetric import padding

                encrypted_data = msg.get("payload", "")
                if encrypted_data:
                    # 解密流程
                    with open(private_key_path, "rb") as key_file:
                        private_key = serialization.load_pem_private_key(
                            key_file.read(),
                            password=None,
                        )

                    try:
                        decrypted = private_key.decrypt(
                            bytes.fromhex(encrypted_data),
                            padding.OAEP(
                                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                algorithm=hashes.SHA256(),
                                label=None,
                            ),
                        )
                        # 写入 received/
                        received_dir = DIR_SECRETS / "received"
                        received_dir.mkdir(parents=True, exist_ok=True)
                        out_path = received_dir / f"{msg_id}.json"
                        out_path.write_text(decrypted.decode("utf-8"), encoding="utf-8")
                        logger.info(f"    解密成功 → {out_path}")
                        _write_event("message_decrypted", {"msg_id": msg_id})
                    except Exception as e:
                        logger.error(f"    解密失败: {e}")
                        _write_event("message_decrypt_failed", {"msg_id": msg_id, "error": str(e)})
            except ImportError:
                logger.info("    未安装 cryptography 库，跳过解密")
        else:
            logger.info(f"    消息待解密 (需私钥): {msg_id}")

        # 移出待处理区
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
# 主循环
# ════════════════════════════════════════════════════════════

def main():
    start_time = time.time()
    logger.info(f"guardd v{version} 启动 — hostname={HOSTNAME}")

    modules = [
        ("heartbeat", module_heartbeat),
        ("task_worker", module_task_worker),
        ("upgrade_checker", module_upgrade_checker),
        ("memory_triage", module_memory_triage),
        ("knowledge_sync", module_knowledge_sync),
        ("encrypted_channel", module_encrypted_channel),
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

    elapsed = time.time() - start_time

    # 写入 last_run.json
    last_run = {
        "hostname": HOSTNAME,
        "version": version,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(elapsed, 2),
        "results": results,
        "next_run": (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat(),
        "current_task": None,
    }
    with open(LAST_RUN_FILE, "w") as f:
        json.dump(last_run, f, indent=2, ensure_ascii=False)

    logger.info(f"guardd 完成 — {elapsed:.2f}s, results={results}")


if __name__ == "__main__":
    main()

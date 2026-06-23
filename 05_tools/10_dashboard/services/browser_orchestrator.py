"""
browser_orchestrator.py — 浏览器编排引擎

职责：
  1. 并发控制：每台机器最多 N 个浏览器同时运行
  2. 窗口位置分配：固定槽位，y顶端对齐，x间隔100px
  3. 错峰启动：各浏览器间隔数秒启动，避免同时假死
  4. 执行前预检：清理残留进程、验证身份目录
  5. 远程执行验证：dispatch 后确认进程真实启动
  6. 状态聚合：聚合本机+远程机器的执行状态

使用：
  from services.browser_orchestrator import preflight, verify_started, get_machine_status
"""

import asyncio, json, logging, os, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("dashboard.orchestrator")

# ── 全局配置 ──────────────────────────────────────────────
AGENT_SYNC = Path.home() / "workbuddy-agent-os" / "agent-sync"
AGENT_LOCAL = Path.home() / "workbuddy-agent-os" / "agent-local"

def _resolve_hostname() -> str:
    """优先从 cached_hostname 读取，兜底 os.uname"""
    cached = AGENT_LOCAL / "identity" / "cached_hostname"
    if cached.exists():
        return cached.read_text().strip()
    return os.uname().nodename

HOSTNAME = _resolve_hostname()

# 执行策略（统一来自 mc.execution_policy）
import sys as _sys
_policy_loaded = False
try:
    _scripts_dir = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts"
    _sys.path.insert(0, str(_scripts_dir))
    from mc.execution_policy import MAX_CONCURRENT, LAUNCH_STAGGER, SLOTS, preflight, slot_for, check_running_browsers
    _policy_loaded = True
except ImportError:
    # 兜底常量（策略层不可用时）
    MAX_CONCURRENT = 3
    LAUNCH_STAGGER = 15
    SLOTS = [
        {"id": 1, "position": (0, 0),   "size": (702, 783)},
        {"id": 2, "position": (100, 0), "size": (702, 783)},
        {"id": 3, "position": (200, 0), "size": (702, 783)},
    ]
    def preflight(local_only=True):
        return {"ok": True, "browsers": 0, "max_concurrent": MAX_CONCURRENT,
                "slots_available": MAX_CONCURRENT, "disk_gb": 0, "disk_ok": True,
                "stagger_delay": 0, "message": "策略层未加载，跳过检查"}
    def slot_for(account_id):
        return {"id": 1, "position": [0, 0], "size": [702, 783]}
    def check_running_browsers():
        return 0


# ── 核心函数 ──────────────────────────────────────────────


def check_running_browsers(machine: str = None) -> list[dict]:
    """检查指定机器（或本机）当前正在运行的浏览器进程

    Returns:
        [{"pid": int, "cmd": str, "machine": str}, ...]
    """
    if machine and machine != HOSTNAME:
        return _check_remote_browsers(machine)
    return _check_local_browsers()


def _check_local_browsers() -> list[dict]:
    """本地浏览器进程扫描"""
    result = []
    try:
        r = subprocess.run(
            ["pgrep", "-f", "camoufox.*-no-remote|HeadlessShell|chrome.*--remote-debugging|chromium.*remote-debug"],
            capture_output=True, text=True, timeout=5
        )
        if r.stdout.strip():
            for pid in r.stdout.strip().split("\n"):
                pid = pid.strip()
                if not pid:
                    continue
                cmd_r = subprocess.run(
                    ["ps", "-p", pid, "-o", "command="],
                    capture_output=True, text=True, timeout=3
                )
                result.append({
                    "pid": int(pid),
                    "cmd": cmd_r.stdout.strip()[:120],
                    "machine": HOSTNAME,
                })
    except Exception as e:
        logger.warning(f"检查本地浏览器失败: {e}")
    return result


def _check_remote_browsers(machine: str) -> list[dict]:
    """远程浏览器进程扫描"""
    try:
        from services.remote_exec import exec_remote
        r = exec_remote(machine,
            "ps aux | grep -i 'camoufox\\|HeadlessShell\\|chrome.*remote-debug\\|chromium.*remote-debug' | grep -v grep "
            "| awk '{print $2, $11, $12, $13}'",
            timeout=10)
        if r.get("status") == "ok" and r.get("stdout", "").strip():
            result = []
            for line in r["stdout"].strip().split("\n"):
                parts = line.strip().split(None, 3)
                if parts:
                    result.append({
                        "pid": int(parts[0]),
                        "cmd": " ".join(parts[1:])[:120],
                        "machine": machine,
                    })
            return result
    except Exception as e:
        logger.warning(f"检查远程 {machine} 浏览器失败: {e}")
    return []


def preflight(machine: str, account_id: str) -> dict:
    """执行前预检

    1. 检查该机器当前浏览器数量（不超过 MAX_CONCURRENT）
    2. 检查身份目录是否存在
    3. 检查是否有残留进程需要清理

    Returns:
        {"ok": bool, "message": str, "running": int, "slot": int|None}
    """
    issues = []

    # 1. 检查并发
    running = check_running_browsers(machine)
    running_count = len(running)
    if running_count >= MAX_CONCURRENT:
        return {
            "ok": False,
            "message": f"机器 {machine} 已有 {running_count} 个浏览器在运行（上限 {MAX_CONCURRENT}）",
            "running": running_count,
            "slot": None,
            "running_processes": running,
        }

    # 2. 分配槽位
    slot = None
    for s in SLOTS:
        used = {p.get("cmd", "") for p in running}
        # 简单判断：每个槽位在 cmd 中是否出现
        slot_key = f"--window_position={s['position'][0]},{s['position'][1]}"
        if not any(slot_key in cmd for cmd in used):
            slot = s
            break
    if not slot:
        slot = SLOTS[running_count]  # 兜底：取下一个未用槽位

    # 3. 检查身份目录
    identities_root = AGENT_LOCAL / "tools" / "matrix" / "identities"
    ident_name = account_id.replace("identities/", "")
    ident_dir = identities_root / ident_name
    if not ident_dir.exists():
        # 也可能是 phone_xxx 格式
        for d in identities_root.iterdir():
            if d.is_dir() and (d.name == account_id or d.name == ident_name):
                ident_dir = d
                break
        else:
            issues.append(f"身份目录 {ident_name} 不存在")

    return {
        "ok": len(issues) == 0,
        "message": "; ".join(issues) if issues else f"就绪（槽位 {slot['id']}）",
        "running": running_count,
        "slot": slot,
        "identity_dir_exists": ident_dir.exists(),
        "stagger_delay": running_count * LAUNCH_STAGGER,  # 错峰启动秒数
    }


def update_preflight_with_stagger(preflight_results: dict) -> dict:
    """给同一台机器的多个槽位分配错峰延迟"""
    for machine, pf in preflight_results.items():
        if pf.get("ok") and pf.get("slot"):
            slot_id = pf["slot"]["id"]
            pf["stagger_delay"] = (slot_id - 1) * LAUNCH_STAGGER
    return preflight_results


def verify_started(machine: str, account_id: str, timeout: int = 15) -> dict:
    """验证进程是否真实启动

    本地：
      1. 先查进程表中有无对应 account_id 的 mc run/collect 进程
      2. 再查 camoufox 浏览器进程
    远程：SSH 检查进程表

    Returns:
        {"running": bool, "pid": int|None, "machine": str}
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if machine == HOSTNAME:
            # 优先查 mc run/collect 进程（比浏览器引擎启动快）
            try:
                r = subprocess.run(
                    ["pgrep", "-f", account_id],
                    capture_output=True, text=True, timeout=5
                )
                if r.stdout.strip():
                    pid = int(r.stdout.strip().split("\n")[0])
                    return {"running": True, "pid": pid, "machine": machine}
            except:
                pass
            running = _check_local_browsers()
        else:
            running = _check_remote_browsers(machine)

        # 查找是否包含指定 account_id
        for p in running:
            if account_id in p["cmd"]:
                return {"running": True, "pid": p["pid"], "machine": machine}

        if running:
            # 有其他浏览器进程但非当前 account，再等等
            time.sleep(2)
        else:
            time.sleep(3)

    return {"running": False, "pid": None, "machine": machine}


def get_machine_status(machine: str) -> dict:
    """获取一台机器的完整状态"""
    browsers = check_running_browsers(machine)
    return {
        "machine": machine,
        "browsers_running": len(browsers),
        "browser_processes": browsers,
        "max_concurrent": MAX_CONCURRENT,
        "slots_available": MAX_CONCURRENT - len(browsers),
    }


def get_all_machines_status(machines: list[str]) -> dict:
    """获取所有机器的状态聚合"""
    statuses = {}
    for m in machines:
        try:
            statuses[m] = get_machine_status(m)
        except Exception as e:
            statuses[m] = {"machine": m, "error": str(e)}
    return {"machines": statuses}


def cleanup_stale(machine: str, account_id: str = None) -> dict:
    """清理残留浏览器进程"""
    cleaned = []
    if machine == HOSTNAME:
        patterns = ["camoufox", "HeadlessShell", "chrome.*--remote-debugging"]
        for pat in patterns:
            try:
                r = subprocess.run(["pkill", "-f", pat], capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    cleaned.append(f"已终止 {pat}")
            except:
                pass
    else:
        from services.remote_exec import exec_remote
        r = exec_remote(machine,
            "pkill -f camoufox 2>/dev/null; pkill -f HeadlessShell 2>/dev/null; pkill -f 'chrome.*remote-debug' 2>/dev/null; echo 'done'",
            timeout=10)
        cleaned.append(f"远程清理: {r.get('status', 'unknown')}")

    return {"cleaned": cleaned, "machine": machine}

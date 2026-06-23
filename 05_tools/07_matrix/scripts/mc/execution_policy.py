"""
execution_policy.py — 统一执行策略 v1

所有执行入口（CLI / Dashboard / API）都通过此策略层检查限制。
集中定义并发数、窗口槽位、启动间隔、超时、冷却等规则。

使用:
  from mc.execution_policy import policy, preflight, slot_for
  info = preflight()          # 返回 {ok, browsers, slots, delay, ...}
  slot = slot_for(account)    # 分配窗口槽位
"""

import json, logging, os, subprocess, time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("execution_policy")

# ════════════════════════════════════════════════════════════
# 一、策略常量（唯一来源）
# ════════════════════════════════════════════════════════════
MAX_CONCURRENT = 3            # 每台机器最多 3 个浏览器
LAUNCH_STAGGER = 15           # 每个浏览器启动间隔（秒）
AUTO_SHUTDOWN_MIN = 30        # 30 分钟无操作自动关闭
MIN_DISK_GB = 5               # 最小可用磁盘空间（GB）
MAX_TIMEOUT = 600             # 命令最大超时（秒）
GRACE_PERIOD_LOCAL = 5        # 本机进程启动宽限期（秒）
GRACE_PERIOD_REMOTE = 30      # 远程进程启动宽限期（秒）

# 窗口槽位：固定 3 个，y 顶端对齐，x 间隔 100px
SLOTS = [
    {"id": 1, "position": (0, 0),   "size": (702, 783)},
    {"id": 2, "position": (100, 0), "size": (702, 783)},
    {"id": 3, "position": (200, 0), "size": (702, 783)},
]

# 操作冷却时间（秒），用 (min, max) 范围随机化
OP_COOLDOWNS = {
    "like":         (2, 4),
    "collect":      (3, 6),
    "comment":      (30, 45),
    "follow":       (10, 20),
    "search":       (3, 6),
    "scroll_feed":  (2, 3),
    "reply":        (30, 45),
    "browse":       (5, 10),
    "default":      (2, 5),
}

# 登录超时（秒）
LOGIN_TIMEOUTS = {
    "cookie_verify":    40,
    "sms_recovery":     90,
    "douyin_login":     300,   # 含 4 分钟短信轮询
    "login_page":       120,
}

POLICY_VERSION = "1.0"

# ════════════════════════════════════════════════════════════
# 二、路径解析
# ════════════════════════════════════════════════════════════
def _resolve_paths():
    """解析 AGENT_SYNC 和 AGENT_LOCAL 路径"""
    home = Path.home()
    agent_sync = Path(os.environ.get("AGENT_SYNC", str(home / "workbuddy-agent-os" / "agent-sync")))
    agent_local = Path(os.environ.get("AGENT_LOCAL", str(home / "workbuddy-agent-os" / "agent-local")))
    return agent_sync, agent_local

AGENT_SYNC, AGENT_LOCAL = _resolve_paths()

# ════════════════════════════════════════════════════════════
# 三、策略导出（供前端展示）
# ════════════════════════════════════════════════════════════
def get_policy() -> dict:
    """返回完整策略配置，供 Dashboard 前端展示"""
    return {
        "version": POLICY_VERSION,
        "max_concurrent": MAX_CONCURRENT,
        "launch_stagger": LAUNCH_STAGGER,
        "auto_shutdown_min": AUTO_SHUTDOWN_MIN,
        "min_disk_gb": MIN_DISK_GB,
        "max_timeout": MAX_TIMEOUT,
        "grace_period_local": GRACE_PERIOD_LOCAL,
        "grace_period_remote": GRACE_PERIOD_REMOTE,
        "slots": [{"id": s["id"], "position": list(s["position"]), "size": list(s["size"])} for s in SLOTS],
        "op_cooldowns": {k: list(v) for k, v in OP_COOLDOWNS.items()},
        "login_timeouts": dict(LOGIN_TIMEOUTS),
    }

# ════════════════════════════════════════════════════════════
# 四、执行前预检
# ════════════════════════════════════════════════════════════
def preflight(local_only: bool = True) -> dict:
    """执行前全面检查——所有入口共用

    Returns:
        {
            "ok": bool,              # 是否通过检查
            "browsers": int,         # 当前浏览器数
            "max_concurrent": int,   # 最大允许数
            "slots_available": int,  # 可用槽位数
            "disk_gb": float,        # 剩余磁盘
            "disk_ok": bool,         # 磁盘是否足够
            "stagger_delay": int,    # 建议启动延迟（秒）
            "message": str,          # 检查结果描述
        }
    """
    result = {"ok": True, "browsers": 0, "max_concurrent": MAX_CONCURRENT,
              "slots_available": MAX_CONCURRENT, "disk_gb": 0, "disk_ok": True,
              "stagger_delay": 0, "message": "就绪"}

    # 1. 浏览器数检查
    try:
        r = subprocess.run(
            ["pgrep", "-f", "camoufox.*-no-remote|HeadlessShell|chrome.*remote-debug|chromium.*remote-debug"],
            capture_output=True, text=True, timeout=5
        )
        count = len([p for p in r.stdout.strip().split("\n") if p.strip()]) if r.stdout.strip() else 0
        result["browsers"] = count
        result["slots_available"] = max(0, MAX_CONCURRENT - count)

        if count >= MAX_CONCURRENT:
            result["ok"] = False
            result["message"] = f"浏览器已达上限: {count}/{MAX_CONCURRENT}，请等待或手动清理"
            return result

        # 计算建议延迟
        result["stagger_delay"] = count * LAUNCH_STAGGER
    except:
        pass

    # 2. 磁盘空间检查
    try:
        s = os.statvfs(str(AGENT_LOCAL))
        free_gb = (s.f_frsize * s.f_bavail) / (1024 ** 3)
        result["disk_gb"] = round(free_gb, 1)
        if free_gb < MIN_DISK_GB:
            result["ok"] = False
            result["disk_ok"] = False
            result["message"] = f"磁盘空间不足: {free_gb:.1f}GB < {MIN_DISK_GB}GB"
            return result
    except:
        pass

    return result


def check_running_browsers() -> int:
    """获取当前浏览器进程数（供各层共用）"""
    try:
        r = subprocess.run(
            ["pgrep", "-f", "camoufox.*-no-remote|HeadlessShell|chrome.*remote-debug|chromium.*remote-debug"],
            capture_output=True, text=True, timeout=5
        )
        if not r.stdout.strip():
            return 0
        return len([p for p in r.stdout.strip().split("\n") if p.strip()])
    except:
        return 0


def slot_for(account_id: str) -> Optional[dict]:
    """为账号分配窗口槽位——按当前浏览器数取模

    Returns:
        {"id": int, "position": [x, y], "size": [w, h]} or None
    """
    browser_count = check_running_browsers()
    if browser_count >= MAX_CONCURRENT:
        return None
    slot_idx = browser_count % len(SLOTS)
    return {
        "id": SLOTS[slot_idx]["id"],
        "position": list(SLOTS[slot_idx]["position"]),
        "size": list(SLOTS[slot_idx]["size"]),
    }


def get_cooldown(op_type: str = "default") -> tuple:
    """获取操作冷却时间范围"""
    return OP_COOLDOWNS.get(op_type, OP_COOLDOWNS["default"])


def get_login_timeout(timeout_type: str = "douyin_login") -> int:
    """获取登录超时时间"""
    return LOGIN_TIMEOUTS.get(timeout_type, 120)

"""
Peekaboo 使用策略层 — 控制截图频率和用量，避免 token 浪费

核心原则：
  1. 能不用不用 — 优先用 DOM/API/文本方式
  2. 非必要不截图 — 截图是最后手段
  3. 截图有冷却 — 5秒内不重复截
  4. 单会话上限 — 最多截 20 次
"""

import time
import subprocess
import os
from pathlib import Path

PEEKABOO_BIN = os.path.expanduser("~/.workbuddy/binaries/node/versions/22.12.0/bin/peekaboo")
if not os.path.exists(PEEKABOO_BIN):
    PEEKABOO_BIN = "peekaboo"  # fallback to PATH

# ============ 使用策略常量 ============
SCREENSHOT_COOLDOWN = 5          # 截图冷却（秒）
MAX_SCREENSHOTS_PER_SESSION = 20 # 单次对话最大截图数
CACHE_DIR = Path("/tmp/peekaboo_cache")
CACHE_DIR.mkdir(exist_ok=True)

# ============ 运行时状态 ============
_last_screenshot_time = 0.0
_screenshot_count = 0
_cache = {}


def screenshot(app: str = "frontmost", force: bool = False) -> str:
    """
    截图（带策略控制）

    Args:
        app: 目标应用名或 frontmost
        force: 跳过冷却/上限检查

    Returns:
        截图保存路径，或空字符串（被限制时）
    """
    global _last_screenshot_time, _screenshot_count

    now = time.time()

    # 检查上限
    if not force and _screenshot_count >= MAX_SCREENSHOTS_PER_SESSION:
        print("  ⚠️ 截图已达上限 (%d次)，跳过" % MAX_SCREENSHOTS_PER_SESSION)
        return ""

    # 检查冷却
    if not force and (now - _last_screenshot_time) < SCREENSHOT_COOLDOWN:
        remaining = SCREENSHOT_COOLDOWN - (now - _last_screenshot_time)
        print("  ⚠️ 截图冷却中，还剩 %.0f 秒" % remaining)
        return ""

    # 检查缓存（同一应用 30 秒内不重复截）
    cache_key = f"screenshot:{app}"
    if cache_key in _cache:
        cached_time, cached_path = _cache[cache_key]
        if (now - cached_time) < 30:
            print("  ⏭ 使用缓存截图 (%s)" % cached_path)
            return cached_path

    # 执行截图
    out_path = str(CACHE_DIR / f"screenshot_{int(now)}.png")
    env = {**os.environ, "NODE_OPTIONS": ""}
    for k in ["HTTP_PROXY", "HTTPS_PROXY"]:
        env.pop(k, None)

    try:
        cmd = [PEEKABOO_BIN, "image", "--app", app, "--path", out_path, "--json", "--log-level", "error"]
        subprocess.run(cmd, capture_output=True, timeout=15, env=env)
        _last_screenshot_time = now
        _screenshot_count += 1
        _cache[cache_key] = (now, out_path)
        print("  📸 截图已保存 (%s) [第%d次]" % (out_path, _screenshot_count))
        return out_path
    except Exception as e:
        print("  ⚠️ 截图失败: %s" % e)
        return ""


def reset():
    """重置截图计数器（新对话开始时调用）"""
    global _screenshot_count, _last_screenshot_time, _cache
    _screenshot_count = 0
    _last_screenshot_time = 0.0
    _cache = {}
    print("  🔄 Peekaboo 策略已重置")


def status() -> dict:
    """查看当前策略状态"""
    return {
        "screenshots_taken": _screenshot_count,
        "max_screenshots": MAX_SCREENSHOTS_PER_SESSION,
        "cooldown_remaining": max(0, SCREENSHOT_COOLDOWN - (time.time() - _last_screenshot_time)),
    }

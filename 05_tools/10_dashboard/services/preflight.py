"""
状态归零模块 — 操作执行前的准备和清理

每次操作前自动执行:
1. 杀残留浏览器进程 (camoufox)
2. 杀残留 Playwright 驱动
3. 清理临时文件
4. 检查并释放过期锁
5. 检查磁盘空间
6. 返回 ready 状态
"""

import subprocess, logging, shutil, time
from pathlib import Path

logger = logging.getLogger("dashboard.preflight")
TEMP_DIRS = ["/tmp/camoufox_*", "/tmp/playwright_*"]


def kill_processes(name: str) -> dict:
    """杀掉指定名称的进程"""
    try:
        r = subprocess.run(
            ["pkill", "-f", name],
            capture_output=True, text=True, timeout=5
        )
        # pkill returns 0 if killed, 1 if no process found (OK either way)
        return {"killed": r.returncode == 0, "output": r.stdout or r.stderr or ""}
    except subprocess.TimeoutExpired:
        return {"killed": False, "output": "超时"}
    except FileNotFoundError:
        return {"killed": False, "output": "pkill not available"}


def cleanup_temp_files() -> dict:
    """清理临时文件"""
    cleaned = 0
    for pattern in TEMP_DIRS:
        import glob
        for fp in glob.glob(pattern):
            try:
                shutil.rmtree(fp, ignore_errors=True)
                cleaned += 1
            except:
                pass
    return {"cleaned_dirs": cleaned}


def check_disk_space(min_gb: int = 5) -> dict:
    """检查磁盘空间"""
    try:
        r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        lines = r.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 4:
                avail = parts[3]
                # 转换成GB
                avail_gb = 0
                if avail.endswith("G"):
                    avail_gb = float(avail[:-1])
                elif avail.endswith("M"):
                    avail_gb = float(avail[:-1]) / 1024
                elif avail.endswith("T"):
                    avail_gb = float(avail[:-1]) * 1024
                elif avail.endswith("K"):
                    avail_gb = float(avail[:-1]) / 1024 / 1024
                else:
                    try:
                        avail_gb = float(avail)
                    except:
                        avail_gb = 0
                return {"available_gb": avail_gb, "sufficient": avail_gb >= min_gb}
    except:
        pass
    return {"available_gb": 0, "sufficient": False}


def check_browser_running() -> dict:
    """检查是否有浏览器正在运行"""
    try:
        r = subprocess.run(["pgrep", "-f", "camoufox"], capture_output=True, text=True, timeout=5)
        running = r.returncode == 0
        return {"running": running, "pids": r.stdout.strip() if running else ""}
    except:
        return {"running": False}


def run(machine: str = "") -> dict:
    """执行完整的 preflight check
    
    Returns:
        {"ready": True/False, "checks": {...}, "message": "..."}
    """
    checks = {}
    all_ok = True

    # 1. 杀残留浏览器
    c1 = kill_processes("camoufox")
    checks["kill_camoufox"] = c1
    time.sleep(0.5)

    # 2. 杀残留驱动
    c2 = kill_processes("playwright")
    checks["kill_playwright"] = c2
    time.sleep(0.3)

    # 3. 清理临时文件
    c3 = cleanup_temp_files()
    checks["cleanup_temp"] = c3

    # 4. 检查磁盘
    c4 = check_disk_space()
    checks["disk_space"] = c4
    if not c4.get("sufficient", True):
        all_ok = False

    # 5. 检查浏览器是否还在跑
    c5 = check_browser_running()
    checks["browser_still_running"] = c5
    if c5.get("running"):
        all_ok = False

    return {
        "ready": all_ok,
        "checks": checks,
        "message": "环境就绪" if all_ok else "环境未就绪，请查看 checks 详情",
    }

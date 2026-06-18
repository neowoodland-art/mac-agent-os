#!/usr/bin/env python3
"""
guardd — AgentOS 系统自愈守护进程 (v1.0)

职责：
  1. 检测：孤儿浏览器 / 磁盘空间 / Dashboard 存活 / 命令超时 / 浏览器超量
  2. 恢复：kill 孤儿进程 / 清理磁盘 / 重启 Dashboard / kill 超时命令
  3. 心跳：每 60s 向 Dashboard 推送健康状态 + 恢复事件

用法：
  python guardd.py                    # 前台运行（调试）
  nohup python guardd.py &            # 后台运行
  agentos serve guardd                # 通过 agentos 启动

约束：
  - 每项恢复动作有频率限制（rate limit），防止循环崩溃
  - 日志写入: agent-local/runtime/guardd/events.log
"""

import os, sys, json, time, subprocess, shutil, glob, logging
from pathlib import Path
from datetime import datetime, timezone

# ── 路径 ──────────────────────────────────────────────
# 先尝试从 matrix_mgmt 导入（有 yaml 依赖）
# 兜底用硬编码（不依赖 yaml）
try:
    from matrix_mgmt import AGENT_SYNC, AGENT_LOCAL
except ImportError:
    AGENT_SYNC = Path.home() / "workbuddy-agent-os" / "agent-sync"
    AGENT_LOCAL = Path.home() / "workbuddy-agent-os" / "agent-local"

LOG_DIR = AGENT_LOCAL / "runtime" / "guardd"
LOG_DIR.mkdir(parents=True, exist_ok=True)

EVENTS_LOG = LOG_DIR / "events.log"
STATUS_FILE = LOG_DIR / "status.json"

# ── 配置 ──────────────────────────────────────────────
INTERVAL = 60            # 检测间隔(秒)
DASHBOARD_URL = "http://localhost:9988"
MAX_BROWSERS = 3         # 最大浏览器数
MIN_DISK_GB = 5          # 最小磁盘空间
CMD_TIMEOUT = 1800       # 命令超时(秒) = 30min
HEARTBEAT_URL = f"{DASHBOARD_URL}/api/push/heartbeat"

# 频率限制（每个恢复动作计数）
_RATE_LIMIT = {}          # {action_name: [count, last_reset_time]}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("guardd")


# ══════════════════════════════════════════════════════
# 检测器
# ══════════════════════════════════════════════════════

def detect_orphan_browsers() -> list[dict]:
    """检测孤儿浏览器进程（PPID=1）"""
    orphans = []
    try:
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
        for line in r.stdout.split('\n'):
            if 'camoufox' not in line and 'HeadlessShell' not in line:
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            pid = parts[1]
            ppid = parts[2]
            if ppid == '1':  # 孤儿进程
                # 获取启动时间
                try:
                    pr = subprocess.run(["ps", "-p", pid, "-o", "lstart="],
                                      capture_output=True, text=True, timeout=5)
                    started = pr.stdout.strip()[:19] if pr.stdout.strip() else "?"
                except:
                    started = "?"
                orphans.append({"pid": int(pid), "started": started, "cmd": ' '.join(parts[10:])[:80]})
    except Exception as e:
        log.warning(f"检测孤儿浏览器失败: {e}")
    return orphans


def detect_running_browsers() -> list[dict]:
    """检测所有正在运行的浏览器"""
    browsers = []
    try:
        r = subprocess.run(
            ["pgrep", "-f", "camoufox.*-no-remote|HeadlessShell"],
            capture_output=True, text=True, timeout=5
        )
        for pid_str in r.stdout.strip().split('\n'):
            pid_str = pid_str.strip()
            if not pid_str:
                continue
            try:
                pid = int(pid_str)
                # 获取启动时间
                pr = subprocess.run(["ps", "-p", str(pid), "-o", "lstart="],
                                  capture_output=True, text=True, timeout=5)
                started = pr.stdout.strip()[:19] if pr.stdout.strip() else "?"
                browsers.append({"pid": pid, "started": started})
            except ValueError:
                continue
    except Exception:
        pass
    return browsers


def detect_disk_space() -> dict:
    """检测磁盘空间"""
    result = {"available_gb": 0, "sufficient": True}
    try:
        r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        parts = r.stdout.strip().split('\n')[1].split()
        avail = parts[3] if len(parts) >= 4 else "0"
        gb = 0
        if avail.endswith('Gi'): gb = float(avail[:-2])
        elif avail.endswith('G'): gb = float(avail[:-1])
        elif avail.endswith('Mi'): gb = float(avail[:-2]) / 1024
        elif avail.endswith('M'): gb = float(avail[:-1]) / 1024
        result["available_gb"] = round(gb, 1)
        result["sufficient"] = gb >= MIN_DISK_GB
    except Exception as e:
        log.warning(f"检测磁盘失败: {e}")
    return result


def detect_dashboard_alive() -> bool:
    """检测 Dashboard 是否存活"""
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             f"{DASHBOARD_URL}/api/health"],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip() == "200"
    except Exception:
        return False


def detect_stale_commands() -> list[dict]:
    """检测超时的命令进程"""
    stale = []
    try:
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
        now = time.time()
        for line in r.stdout.split('\n'):
            if 'mc run' not in line and 'mc collect' not in line and 'collect_batch_runner' not in line:
                continue
            parts = line.split()
            if len(parts) < 10:
                continue
            pid = parts[1]
            # 计算进程启动时间（ps 输出第9列是启动时间或已用时间）
            start_str = parts[8] if len(parts) > 8 else "?"
            cmd_line = ' '.join(parts[10:])[:80]
            stale.append({"pid": int(pid), "cmd": cmd_line, "start": start_str})
    except Exception as e:
        log.warning(f"检测超时命令失败: {e}")
    return stale


# ══════════════════════════════════════════════════════
# 恢复动作
# ══════════════════════════════════════════════════════

def _check_rate(action: str, max_per_hour: int = 3) -> bool:
    """频率限制：每项动作每小时最多执行 max_per_hour 次"""
    global _RATE_LIMIT
    now = time.time()
    if action not in _RATE_LIMIT:
        _RATE_LIMIT[action] = [0, now]
    count, last = _RATE_LIMIT[action]
    # 每小时重置
    if now - last > 3600:
        _RATE_LIMIT[action] = [0, now]
        return True
    if count >= max_per_hour:
        return False
    _RATE_LIMIT[action][0] += 1
    return True


def recover_orphan_browsers(orphans: list[dict]) -> list[str]:
    """杀死孤儿浏览器进程"""
    killed = []
    for o in orphans:
        if not _check_rate(f"kill_orphan_{o['pid']}"):
            continue
        try:
            subprocess.run(["kill", "-9", str(o['pid'])], capture_output=True, timeout=5)
            killed.append(f"孤儿进程 {o['pid']} ({o['cmd'][:40]})")
            log.warning(f"  🔴 已杀死孤儿: {o['pid']}")
        except Exception as e:
            log.warning(f"  杀死孤儿 {o['pid']} 失败: {e}")
    return killed


def recover_disk_space() -> list[str]:
    """磁盘空间不足时清理临时文件"""
    cleaned = []
    if not _check_rate("disk_cleanup", max_per_hour=2):
        return cleaned
    for pattern in ["/tmp/camoufox_*", "/tmp/playwright_*"]:
        for fp in glob.glob(pattern):
            try:
                shutil.rmtree(fp, ignore_errors=True)
                cleaned.append(f"已清理: {fp}")
            except:
                pass
    if cleaned:
        log.warning(f"  🧹 磁盘清理: {len(cleaned)}个临时目录")
    return cleaned


def recover_dashboard() -> list[str]:
    """重启 Dashboard"""
    actions = []
    if not _check_rate("restart_dashboard", max_per_hour=2):
        return actions
    
    dashboard_dir = AGENT_SYNC / "05_tools" / "10_dashboard"
    python = os.environ.get("MC_PYTHON",
        f"{Path.home()}/.workbuddy/binaries/python/envs/agent-os/bin/python3")
    
    try:
        # kill old
        subprocess.run(["pkill", "-f", "uvicorn.*9988"], capture_output=True, timeout=5)
        time.sleep(2)
        # start new
        subprocess.Popen(
            [python, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9988"],
            cwd=str(dashboard_dir),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        actions.append("Dashboard 已重启")
        log.warning("  🚑 Dashboard 已重启")
    except Exception as e:
        log.warning(f"  重启 Dashboard 失败: {e}")
    return actions


def recover_stale_commands(stale: list[dict]) -> list[str]:
    """杀死超时命令"""
    killed = []
    for s in stale:
        if not _check_rate(f"kill_cmd_{s['pid']}", max_per_hour=6):
            continue
        try:
            subprocess.run(["kill", "-9", str(s['pid'])], capture_output=True, timeout=5)
            killed.append(f"超时命令 {s['pid']} ({s['cmd'][:40]})")
            log.warning(f"  ⏰ 已杀死超时命令: {s['pid']}")
        except Exception as e:
            log.warning(f"  杀死命令 {s['pid']} 失败: {e}")
    return killed


def recover_excess_browsers(browsers: list[dict]) -> list[str]:
    """超过最大浏览器数时，按启动时间杀死最早的"""
    killed = []
    if len(browsers) <= MAX_BROWSERS:
        return killed
    if not _check_rate("kill_excess_browser", max_per_hour=3):
        return killed
    
    # 排序：越早的越可能在前
    excess = sorted(browsers, key=lambda b: b.get("started", ""))
    to_kill = excess[:-MAX_BROWSERS]  # 保留最新的 MAX_BROWSERS 个
    
    for b in to_kill:
        try:
            subprocess.run(["kill", "-9", str(b['pid'])], capture_output=True, timeout=5)
            killed.append(f"超额浏览器 {b['pid']}")
            log.warning(f"  📊 已杀死超额浏览器: {b['pid']}")
        except:
            pass
    return killed


# ══════════════════════════════════════════════════════
# 心跳推送
# ══════════════════════════════════════════════════════

def push_heartbeat(events: list[str], stats: dict):
    """向 Dashboard 推送心跳"""
    import uuid
    hostname = os.uname().nodename
    
    # 读取本机 UID
    uid_file = AGENT_LOCAL / "identity" / "machine_uid"
    uid = uid_file.read_text().strip() if uid_file.exists() else str(uuid.uuid4())[:8]
    
    payload = {
        "uid": uid,
        "hostname": hostname,
        "uptime": time.time(),
        "heartbeat": {
            "status": "online",
            "guardd_running": True,
            "guardd_version": "1.0",
            "disk_avail_gb": stats.get("disk_gb", 0),
            "browsers_running": stats.get("browsers", 0),
            "last_check": datetime.now(timezone.utc).isoformat(),
        },
        "events": [{"time": datetime.now().isoformat(), "message": e} for e in events],
    }
    
    try:
        subprocess.run(
            ["curl", "-s", "-X", "POST", HEARTBEAT_URL,
             "-H", "Content-Type: application/json",
             "-d", json.dumps(payload)],
            capture_output=True, timeout=10
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════
# 主循环
# ══════════════════════════════════════════════════════

def run_once() -> dict:
    """执行一次检测+恢复，返回事件列表"""
    events = []
    stats = {}
    
    # 1. 检测孤儿浏览器
    orphans = detect_orphan_browsers()
    if orphans:
        log.warning(f"🔴 检测到 {len(orphans)} 个孤儿浏览器")
        killed = recover_orphan_browsers(orphans)
        events.extend(killed)
    
    # 2. 检测磁盘
    disk = detect_disk_space()
    stats["disk_gb"] = disk["available_gb"]
    if not disk["sufficient"]:
        log.warning(f"🔴 磁盘不足: {disk['available_gb']}GB")
        cleaned = recover_disk_space()
        events.extend(cleaned)
        if not cleaned:
            events.append(f"磁盘不足: {disk['available_gb']}GB (跳过，已达频率上限)")
    
    # 3. 检测 Dashboard
    if not detect_dashboard_alive():
        log.warning("🔴 Dashboard 无响应")
        restarted = recover_dashboard()
        events.extend(restarted)
    else:
        stats["dashboard"] = "ok"
    
    # 4. 检测浏览器数量
    browsers = detect_running_browsers()
    stats["browsers"] = len(browsers)
    if len(browsers) > MAX_BROWSERS:
        log.warning(f"🟡 浏览器超量: {len(browsers)} > {MAX_BROWSERS}")
        killed = recover_excess_browsers(browsers)
        events.extend(killed)
    
    # 5. 检测超时命令
    stale = detect_stale_commands()
    if stale:
        log.warning(f"🟡 检测到 {len(stale)} 个超时命令")
        killed = recover_stale_commands(stale)
        events.extend(killed)
    
    # 写状态文件
    status = {
        "last_check": datetime.now().isoformat(),
        "orphans": len(orphans),
        "disk_gb": disk["available_gb"],
        "browsers": len(browsers),
        "stale_commands": len(stale),
        "events": events,
    }
    STATUS_FILE.write_text(json.dumps(status, indent=2, ensure_ascii=False))
    
    # 记录事件
    if events:
        with open(EVENTS_LOG, "a") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for e in events:
                f.write(f"[{ts}] {e}\n")
    
    # 推送心跳
    push_heartbeat(events, stats)
    
    return status


def main():
    print(f"\n{'='*50}")
    print(f" 🛡️  AgentOS guardd v1.0")
    print(f" {'='*50}")
    print(f" 日志: {EVENTS_LOG}")
    print(f" 间隔: {INTERVAL}s")
    print(f" Dashboard: {DASHBOARD_URL}\n")
    
    log.info("guardd 启动")
    
    while True:
        try:
            status = run_once()
            if status["events"]:
                log.info(f"  恢复动作: {'; '.join(status['events'])}")
            else:
                log.info(f"  健康 ✅ (浏览器:{status['browsers']} 磁盘:{status['disk_gb']}GB)")
        except KeyboardInterrupt:
            log.info("guardd 停止")
            break
        except Exception as e:
            log.error(f"guardd 异常: {e}")
        
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()

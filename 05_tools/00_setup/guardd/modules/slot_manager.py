"""
slot_manager.py — 浏览器槽位管理器 (guardd 模块)

职责:
  - 管理本机 Camoufox 浏览器实例（槽位）
  - 按 browser_id 识别，不依赖槽位编号（用户拖拽窗口不影响）
  - 同一账号不能同时在两个浏览器运行
  - 启动时扫描孤儿浏览器进程
"""
import os
import signal
import subprocess
import time
from threading import Lock
from typing import Optional, List


class AccountBusyError(Exception):
    """账号已在其他槽位运行"""
    pass


class BrowserSlotManager:
    """浏览器槽位管理器"""

    def __init__(self, max_slots: int = 3):
        self.max_slots = max_slots
        self.slots = [None] * max_slots  # list of dict or None
        self._lock = Lock()

    def acquire(self, account_id: str, identity_dir: str, nickname: str = "",
                platform: str = "douyin") -> Optional[dict]:
        """获取一个槽位，返回 slot_info dict
        Args:
            account_id: 账号ID (douyin_136)
            identity_dir: 身份目录名
            nickname: 账号昵称 (显示用)
            platform: 平台 (douyin / xiaohongshu)
        Raises: AccountBusyError 如果账号已在其他槽位运行
        """
        with self._lock:
            for s in self.slots:
                if s and s["account_id"] == account_id:
                    raise AccountBusyError(f"账号 {account_id} 已在 slot {s['slot_id']} 运行")

            for i in range(self.max_slots):
                if self.slots[i] is None:
                    info = {
                        "slot_id": i,
                        "account_id": account_id,
                        "nickname": nickname,
                        "platform": platform,
                        "browser_id": identity_dir,
                        "pid": None,
                        "blueprint": None,
                        "current_step": None,
                        "step_index": 0,
                        "total_steps": 0,
                        "started_at": time.time(),
                        "elapsed_sec": 0,
                        "cpu_percent": 0.0,
                        "memory_mb": 0.0,
                        "health": "healthy",
                        "last_heartbeat": time.time(),
                    }
                    self.slots[i] = info
                    return info
            return None

    def release(self, browser_id: str) -> bool:
        """按 browser_id 释放槽位（不依赖槽位编号）"""
        with self._lock:
            for i in range(self.max_slots):
                if self.slots[i] and self.slots[i]["browser_id"] == browser_id:
                    pid = self.slots[i].get("pid")
                    if pid:
                        try:
                            os.kill(pid, signal.SIGTERM)
                        except (OSError, ProcessLookupError):
                            pass
                    self.slots[i] = None
                    return True
            return False

    def release_by_account(self, account_id: str) -> bool:
        """按 account_id 释放槽位"""
        with self._lock:
            for i in range(self.max_slots):
                if self.slots[i] and self.slots[i]["account_id"] == account_id:
                    self.slots[i] = None
                    return True
            return False

    def update_step(self, browser_id: str, step_name: str, step_index: int = None, total_steps: int = None):
        """更新槽位中正在执行的步骤"""
        with self._lock:
            for s in self.slots:
                if s and s["browser_id"] == browser_id:
                    s["current_step"] = step_name
                    s["elapsed_sec"] = int(time.time() - s["started_at"])
                    s["last_heartbeat"] = time.time()
                    if step_index is not None:
                        s["step_index"] = step_index
                    if total_steps is not None:
                        s["total_steps"] = total_steps
                    return True
            return False

    def set_pid(self, browser_id: str, pid: int):
        """设置浏览器进程 PID"""
        with self._lock:
            for s in self.slots:
                if s and s["browser_id"] == browser_id:
                    s["pid"] = pid
                    return True
            return False

    def find_account(self, account_id: str) -> Optional[dict]:
        """查找账号在当前哪个槽位运行"""
        with self._lock:
            for s in self.slots:
                if s and s["account_id"] == account_id:
                    return s
            return None

    def find_by_browser(self, browser_id: str) -> Optional[dict]:
        with self._lock:
            for s in self.slots:
                if s and s["browser_id"] == browser_id:
                    return s
            return None

    def check_health(self):
        """每轮 cycle 检查所有浏览器进程健康状态"""
        with self._lock:
            for s in self.slots:
                if not s or not s.get("pid"):
                    continue
                try:
                    os.kill(s["pid"], 0)  # 空信号测存活
                except OSError:
                    s["health"] = "crashed"
                    s["account_id"] = None
                    continue
                # 采集 CPU/内存
                try:
                    r = subprocess.run(
                        ["ps", "-p", str(s["pid"]), "-o", "%cpu=,%mem=,rss="],
                        capture_output=True, text=True, timeout=3
                    )
                    parts = r.stdout.strip().split()
                    if len(parts) >= 3:
                        s["cpu_percent"] = float(parts[0])
                        s["memory_mb"] = float(parts[2]) / 1024
                        s["health"] = "warning" if float(parts[0]) > 80 else "healthy"
                except Exception:
                    pass
                s["elapsed_sec"] = int(time.time() - s["started_at"])
                s["last_heartbeat"] = time.time()

    def cleanup_orphans(self):
        """启动时扫描孤儿浏览器进程"""
        print("  [SlotManager] 扫描孤儿浏览器进程...")
        try:
            r = subprocess.run(
                ["ps", "aux"],
                capture_output=True, text=True, timeout=5
            )
            orphan_count = 0
            for line in r.stdout.split("\n"):
                if "camoufox" in line.lower() or "firefox" in line.lower():
                    parts = line.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            orphan_count += 1
                        except (OSError, ValueError):
                            pass
            if orphan_count:
                print(f"  [SlotManager] 清理 {orphan_count} 个孤儿浏览器进程")
        except Exception as e:
            print(f"  [SlotManager] 清理异常: {e}")

    def check_processes(self):
        """逐 slot 检查 PID 存活状态（5 秒线程调用）"""
        with self._lock:
            for s in self.slots:
                if not s or not s.get("pid"):
                    continue
                pid = s["pid"]
                alive = True
                try:
                    os.kill(pid, 0)
                except OSError:
                    alive = False
                if alive:
                    s["health"] = "healthy"
                    s["last_heartbeat"] = time.time()
                else:
                    s["health"] = "crashed"
                    s["pid"] = None
                    s["account_id"] = None

    def track_loop(self, interval: float = 5.0):
        """后台线程：每 5 秒检查一次所有 slot 的进程存活"""
        logger = __import__("logging").getLogger("guardd.slot_manager")
        while True:
            try:
                self.check_processes()
            except Exception as e:
                logger.error(f"track_loop 异常: {e}")
            __import__("time").sleep(interval)

    def get_usage(self) -> dict:
        with self._lock:
            slots_info = []
            for i, s in enumerate(self.slots):
                if s:
                    slots_info.append({
                    "slot_id": i,
                    "account_id": s["account_id"],
                    "nickname": s.get("nickname", ""),
                    "platform": s.get("platform", ""),
                    "browser_id": s["browser_id"],
                    "pid": s["pid"],
                    "blueprint": s.get("blueprint"),
                    "current_step": s.get("current_step"),
                    "step_index": s.get("step_index", 0),
                    "total_steps": s.get("total_steps", 0),
                    "elapsed_sec": s.get("elapsed_sec", 0),
                    "health": s.get("health", "unknown"),
                })
            return {
                "max": self.max_slots,
                "used": sum(1 for s in self.slots if s is not None),
                "slots": slots_info,
            }

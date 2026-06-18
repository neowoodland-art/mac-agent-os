"""
browser.py — 浏览器生命周期管理器

核心功能:
  1. Context manager: with BrowserManager() as bm:
  2. 自动检测并清理残留进程
  3. 自动清理 wal/shm 锁文件
  4. 记录 PID 到 pid_file
  5. 退出时妥善关闭 + 确认

用法:
    from mc.browser import BrowserManager

    with BrowserManager() as bm:
        bm.prepare("douyin_01")
        # ... 执行操作 ...

    # 退出时自动:
    #   - 关闭浏览器
    #   - 等待进程退出
    #   - 清理 wal/shm
    #   - 删除 pid_file
"""
import logging
import os
import signal
import sqlite3
import subprocess
import time
from pathlib import Path

log = logging.getLogger(__name__)

from matrix_mgmt import AGENT_LOCAL
LOCAL_ROOT = AGENT_LOCAL / "tools" / "matrix"
PID_DIR = Path("/tmp") / "mc_pids"


class BrowserManager:
    """浏览器生命周期管理器"""

    def __init__(self):
        self._managed_pids: list[int] = []
        PID_DIR.mkdir(parents=True, exist_ok=True)

    def __enter__(self):
        log.info("🚀 BrowserManager 启动")
        self._cleanup_stale()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        log.info("🛑 BrowserManager 关闭中...")
        self._close_all()
        self._cleanup_pid_files()
        log.info("✅ BrowserManager 已关闭")

    # ──────────────── 公共方法 ────────────────

    def prepare(self, identity: str) -> dict:
        """准备某个身份的浏览器环境

        Args:
            identity: 身份目录名 (douyin_01, douyin_04 等)

        Returns:
            {"status": "ok", "pid": pid} 或 {"status": "stale", "pid": old_pid}
        """
        pid_file = PID_DIR / f"{identity}.pid"

        # 检查是否有残留进程
        if pid_file.exists():
            old_pid = int(pid_file.read_text().strip())
            if self._is_process_alive(old_pid):
                log.warning(f"  ⚠️ {identity} 已有残留进程 PID={old_pid}，清理中...")
                self._kill_process(old_pid)
            pid_file.unlink(missing_ok=True)

        # 清理 cookie 锁文件
        self._cleanup_cookie_locks(identity)

        # 清理 Camoufox profile lock
        self._cleanup_profile_locks(identity)

        return {"status": "ok"}

    def register_pid(self, identity: str, pid: int):
        """记录进程 PID"""
        pid_file = PID_DIR / f"{identity}.pid"
        pid_file.write_text(str(pid))
        self._managed_pids.append(pid)
        log.info(f"  📝 {identity} PID={pid} 已注册")

    def is_healthy(self, identity: str) -> bool:
        """检查某个身份对应的浏览器是否存活"""
        pid_file = PID_DIR / f"{identity}.pid"
        if not pid_file.exists():
            return False
        try:
            pid = int(pid_file.read_text().strip())
            return self._is_process_alive(pid)
        except:
            return False

    # ──────────────── 内部方法 ────────────────

    def _is_process_alive(self, pid: int) -> bool:
        """检查进程是否存在"""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _kill_process(self, pid: int, force: bool = False):
        """安全终止进程"""
        try:
            if force:
                os.kill(pid, signal.SIGKILL)
                log.info(f"  💀 强制终止 PID={pid}")
            else:
                os.kill(pid, signal.SIGTERM)
                # 等待最多 5 秒
                for _ in range(10):
                    if not self._is_process_alive(pid):
                        break
                    time.sleep(0.5)
                if self._is_process_alive(pid):
                    os.kill(pid, signal.SIGKILL)
                    log.info(f"  💀 SIGTERM 超时，SIGKILL PID={pid}")
                else:
                    log.info(f"  ✅ PID={pid} 已正常退出")
        except ProcessLookupError:
            pass  # 进程已不存在
        except Exception as e:
            log.warning(f"  ⚠️ 终止 PID={pid} 失败: {e}")

    def _cleanup_stale(self):
        """清理所有残留的 mc 管理进程"""
        for pid_file in PID_DIR.glob("*.pid"):
            try:
                pid = int(pid_file.read_text().strip())
                if not self._is_process_alive(pid):
                    pid_file.unlink(missing_ok=True)
                    log.info(f"  🧹 清除残留 PID 文件: {pid_file.name}")
            except:
                pid_file.unlink(missing_ok=True)

    def _cleanup_cookie_locks(self, identity: str):
        """清理 cookie 数据库的 wal/shm 锁文件"""
        cookie_dir = LOCAL_ROOT / "identities" / identity / "user_data"
        for ext in ["-wal", "-shm"]:
            f = cookie_dir / f"cookies.sqlite{ext}"
            if f.exists():
                try:
                    # 检查是否被进程占用
                    f.unlink()
                    log.info(f"  🧹 清理锁文件: {f.name}")
                except OSError:
                    log.warning(f"  ⚠️ 锁文件被占用，跳过: {f.name}")

    def _cleanup_profile_locks(self, identity: str):
        """清理 Camoufox profile 锁文件"""
        profile_dir = LOCAL_ROOT / "identities" / identity / "user_data"
        for lock_file in [".parentlock", "lock", "parent.lock"]:
            f = profile_dir / lock_file
            if f.exists():
                try:
                    f.unlink()
                    log.info(f"  🧹 清理 profile 锁: {lock_file}")
                except:
                    pass

    def _close_all(self):
        """关闭所有管理的浏览器进程"""
        for pid in self._managed_pids:
            if self._is_process_alive(pid):
                self._kill_process(pid)
        self._managed_pids.clear()

    def _cleanup_pid_files(self):
        """清理所有 PID 文件"""
        for pid_file in PID_DIR.glob("*.pid"):
            pid_file.unlink(missing_ok=True)


def cleanup_all():
    """一键清理所有残留（供 Guardd 定时调用）"""
    with BrowserManager() as bm:
        bm._cleanup_stale()
    return {"status": "ok", "message": "所有残留已清理"}

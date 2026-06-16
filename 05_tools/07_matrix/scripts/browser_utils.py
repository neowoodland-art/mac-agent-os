"""
browser_utils.py — 浏览器优雅退出 + 前置检查 通用模块

功能:
  1. 优雅退出: 信号处理(SIGTERM/SIGINT) + 超时自动关闭(30min) + cleanup
  2. 前置检查: 检查账号浏览器是否已在运行
  3. PID 文件管理: 记录浏览器进程, 防止重复启动

用法:
  from browser_utils import GracefulBrowser, check_browser_running
  
  # 包装 CDPConnector
  browser = GracefulBrowser(conn, account_id, timeout_minutes=30)
  browser.setup()  # 注册信号处理器 + 前置检查
  
  # 正常退出
  await browser.shutdown()
"""

import asyncio, os, signal, time, json
from pathlib import Path

# PID 文件存储目录
PID_DIR = Path.home() / "workbuddy-agent-os" / "agent-local" / "runtime" / "browser_pids"
PID_DIR.mkdir(parents=True, exist_ok=True)


def get_pid_file(account_id: str) -> Path:
    """获取账号对应的 PID 文件路径"""
    safe_name = account_id.replace("/", "_").replace(" ", "_")
    return PID_DIR / f"{safe_name}.pid"


def is_browser_running(account_id: str) -> bool:
    """检查账号的浏览器是否已在运行
    
    通过 PID 文件 + 进程检查双重验证
    """
    pid_file = get_pid_file(account_id)
    if not pid_file.exists():
        return False
    
    try:
        data = json.loads(pid_file.read_text())
        pid = data.get("pid", 0)
        if pid and _pid_exists(pid):
            # 确认进程是我们启动的 Camoufox
            import subprocess
            r = subprocess.run(
                ["ps", "-p", str(pid), "-o", "comm="],
                capture_output=True, text=True, timeout=5
            )
            proc_name = r.stdout.strip().lower()
            if any(kw in proc_name for kw in ["camoufox", "firefox", "python"]):
                return True
    except Exception:
        pass
    
    # PID 文件过期，清理
    try:
        pid_file.unlink()
    except Exception:
        pass
    return False


def write_pid_file(account_id: str, pid: int, machine: str = ""):
    """写入 PID 文件"""
    data = {
        "account_id": account_id,
        "pid": pid,
        "machine": machine,
        "started_at": time.time(),
    }
    pid_file = get_pid_file(account_id)
    pid_file.write_text(json.dumps(data, indent=2))


def remove_pid_file(account_id: str):
    """删除 PID 文件"""
    pid_file = get_pid_file(account_id)
    try:
        if pid_file.exists():
            pid_file.unlink()
    except Exception:
        pass


def _pid_exists(pid: int) -> bool:
    """检查 PID 是否存活（跨平台）"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def cleanup_stale_pids():
    """清理所有过期的 PID 文件（启动时调用）"""
    for pid_file in PID_DIR.glob("*.pid"):
        try:
            data = json.loads(pid_file.read_text())
            pid = data.get("pid", 0)
            if not pid or not _pid_exists(pid):
                pid_file.unlink()
        except Exception:
            try:
                pid_file.unlink()
            except Exception:
                pass


class GracefulBrowser:
    """浏览器优雅退出管理器
    
    包装 CDPConnector，自动处理:
    - 信号处理 (SIGTERM/SIGINT → 优雅关闭)
    - 超时自动退出 (默认 30 分钟)
    - PID 文件管理
    - cleanup
    
    用法:
        conn = CDPConnector(...)
        gb = GracefulBrowser(conn, account_id="douyin_01", timeout_minutes=30)
        await gb.setup()          # 前置检查 + 信号注册
        await conn.connect()       # 正常使用
        # ...
        await gb.shutdown()        # 优雅退出
    """
    
    def __init__(self, cdp_connector, account_id: str = "",
                 timeout_minutes: int = 30, machine: str = ""):
        self.conn = cdp_connector
        self.account_id = account_id
        self.timeout_minutes = timeout_minutes
        self.machine = machine
        self._shutdown_flag = False
        self._original_handlers = {}
    
    async def setup(self, check_running: bool = True):
        """初始化: 前置检查 + 注册信号
        
        Args:
            check_running: 是否检查浏览器已在运行
        """
        # 清理过期 PID
        cleanup_stale_pids()
        
        # 前置检查: 浏览器是否已在运行
        if check_running and self.account_id:
            if is_browser_running(self.account_id):
                print(f"  ⚠️ 账号 '{self.account_id}' 的浏览器已在运行")
                print(f"     将尝试优雅关闭旧进程...")
                await self._close_existing()
        
        # 注册信号处理器
        self._register_signal_handlers()
        
        # 写入 PID 文件
        if self.account_id:
            write_pid_file(self.account_id, os.getpid(), self.machine)
    
    def _register_signal_handlers(self):
        """注册 SIGTERM/SIGINT → 优雅关闭"""
        for sig in (signal.SIGTERM, signal.SIGINT):
            original = signal.getsignal(sig)
            self._original_handlers[sig] = original
            
            def _handler(s, f, sig=sig, orig=original):
                if self._shutdown_flag:
                    return  # 防止重复调用
                self._shutdown_flag = True
                print(f"\n  ⚠️ 收到信号 {sig.name}, 正在优雅关闭...")
                # 创建新的事件循环任务来执行异步关闭
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(self._async_shutdown())
                    else:
                        loop.run_until_complete(self._async_shutdown())
                except Exception:
                    pass
                # 调用原始处理器（如果有）
                if orig and orig != signal.SIG_DFL and orig != signal.SIG_IGN:
                    try:
                        orig(s, f)
                    except Exception:
                        pass
            
            try:
                signal.signal(sig, _handler)
            except (ValueError, RuntimeError):
                pass  # 不在主线程时忽略
    
    def start_auto_shutdown_timer(self):
        """启动超时自动退出计时器（登录完成后调用）"""
        if self.timeout_minutes <= 0:
            return
        
        async def _timer():
            try:
                await asyncio.sleep(self.timeout_minutes * 60)
                if not self._shutdown_flag:
                    print(f"\n  ⏰ 超时 {self.timeout_minutes} 分钟，自动关闭浏览器")
                    await self._async_shutdown()
            except asyncio.CancelledError:
                pass
        
        self._timer_task = asyncio.ensure_future(_timer())
    
    def cancel_auto_shutdown(self):
        """取消超时计时器"""
        if hasattr(self, '_timer_task'):
            self._timer_task.cancel()
    
    async def shutdown(self):
        """主动优雅退出"""
        await self._async_shutdown()
    
    async def _async_shutdown(self):
        """实际关闭逻辑"""
        if self._shutdown_flag:
            return
        self._shutdown_flag = True
        
        print("  🧹 正在清理浏览器资源...")
        try:
            # 1. 先移除 PID 文件（避免被其他进程误用）
            if self.account_id:
                remove_pid_file(self.account_id)
            
            # 2. 优雅关闭 Camoufox (先关页面 → 再关 context → 再关 browser)
            if hasattr(self.conn, '_camoufox') and self.conn._camoufox:
                print("  🦊 关闭 Camoufox...")
                await self.conn._camoufox.stop()
            elif hasattr(self.conn, '_camoufox_browser') and self.conn._camoufox_browser:
                print("  🦊 关闭浏览器...")
                await self.conn._camoufox_browser.close()
            
            # 3. 关闭 Playwright
            if hasattr(self.conn, '_playwright') and self.conn._playwright:
                print("  🎭 关闭 Playwright...")
                await self.conn._playwright.stop()
            
            print("  ✅ 浏览器已优雅关闭")
        except Exception as e:
            print(f"  ⚠️ 关闭时出错: {e}")
        
        # 强制退出（如果在信号处理器中调用）
        # 给异步关闭一些时间
        await asyncio.sleep(1)
    
    async def _close_existing(self):
        """优雅关闭已存在的浏览器进程"""
        pid_file = get_pid_file(self.account_id)
        if not pid_file.exists():
            return
        
        try:
            data = json.loads(pid_file.read_text())
            pid = data.get("pid", 0)
            if pid and _pid_exists(pid):
                print(f"  🔄 向旧进程 (PID {pid}) 发送 SIGTERM...")
                os.kill(pid, signal.SIGTERM)
                # 等待最多 10 秒
                for _ in range(10):
                    await asyncio.sleep(1)
                    if not _pid_exists(pid):
                        print(f"  ✅ 旧进程已退出")
                        break
                else:
                    print(f"  ⚠️ 旧进程未响应，发送 SIGKILL")
                    os.kill(pid, signal.SIGKILL)
            pid_file.unlink()
        except Exception as e:
            print(f"  ⚠️ 关闭旧进程失败: {e}")

"""
recorder.py — 原子操作录制引擎 (v1.0)

三阶段管线 Phase 1:
  启动 Camoufox → 用户操作 → 按数字键标记步骤 → 
  系统自动捕获: URL + DOM + 截图 + CDP事件序列

用法:
  from mc.recorder import RecordingSession
  session = RecordingSession("douyin_01")
  await session.start()
  await session.record_step(1)  # 用户按1
  # 用户操作...
  await session.record_step(2)  # 用户按2
  package = await session.stop()
"""
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

LOCAL_ROOT = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix"
RECORDINGS_DIR = LOCAL_ROOT / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


class RecordingSession:
    """一次录制会话——管理浏览器、监听事件、保存步骤"""

    def __init__(self, account_id: str, platform: str = "auto",
                 entry_url: str = None):
        self.account_id = account_id
        self.platform = platform
        self.entry_url = entry_url
        self.conn = None
        self.page = None
        self._event_buffer = []       # CDP 事件缓存（两次步骤之间）
        self._steps = []              # 已保存的步骤
        self._is_recording = False
        self._start_time = None
        self._js_listener_ready = False

    async def start(self):
        """启动 Camoufox + 注入事件监听"""
        from cdp_connector import CDPConnector

        # 解析身份目录
        from matrix_mgmt import MatrixManager
        mgr = MatrixManager()
        accts = mgr.list_accounts()
        acct_info = None
        for a in accts:
            if a["id"] == self.account_id:
                acct_info = a
                break
        if not acct_info:
            raise ValueError(f"账号 {self.account_id} 不存在")

        identity_hint = acct_info.get("identity_hint", self.account_id)
        identity_dir = str(LOCAL_ROOT / "identities" / identity_hint)

        print(f"🦀 启动 Camoufox ({self.account_id})...")
        conn = CDPConnector(
            browser_type="camoufox",
            headless=False,
            window=(702, 783),
            identity_dir=identity_dir,
        )
        await conn.connect()
        await conn.init_anti_detection()
        self.conn = conn
        self.page = conn.page
        self._start_time = time.time()
        self._is_recording = True

        # 导航到入口页（"auto" 时从账号解析平台）
        if self.platform == "auto" and self.account_id:
            try:
                import sys
                sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
                from matrix_mgmt import MatrixManager
                mgr = MatrixManager()
                for a in mgr.list_accounts():
                    if a["id"] == self.account_id:
                        p = a.get("platform", "")
                        if p in ("douyin", "xiaohongshu"):
                            self.platform = p
                        break
            except: pass
        target = self.entry_url or {
            "douyin": "https://www.douyin.com/",
            "xiaohongshu": "https://www.xiaohongshu.com/explore",
        }.get(self.platform, "https://www.douyin.com/")

        print(f"🌐 打开 {target}")
        await self.page.goto(target, timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(4)

        # 注入 JS 事件监听器（捕获键盘/鼠标事件到 window.__recorded_events）
        await self._inject_event_listener()

        print(f"\n{'='*55}")
        print(f" 🎬 录制就绪！")
        print(f"   账号: {self.account_id}")
        print(f"   在浏览器中操作，然后按:")
        print(f"     数字键 1-8 → 标记步骤")
        print(f"     数字键 0   → 结束录制")
        print(f"{'='*55}\n")

    async def _inject_event_listener(self):
        """注入 CDP 事件捕获器——记录用户操作"""
        try:
            await self.page.evaluate("""() => {
                if (window.__recorder_injected) return;
                window.__recorder_injected = true;
                window.__recorded_events = [];

                // 监听键盘事件
                document.addEventListener('keydown', (e) => {
                    window.__recorded_events.push({
                        t: 'key',
                        k: e.key,
                        c: e.ctrlKey,
                        m: e.metaKey,
                        a: e.altKey,
                        s: e.shiftKey,
                        code: e.code,
                        ts: Date.now()
                    });
                }, true);

                // 监听鼠标点击
                document.addEventListener('mousedown', (e) => {
                    window.__recorded_events.push({
                        t: 'click',
                        x: e.clientX,
                        y: e.clientY,
                        btn: e.button,
                        target: (e.target.tagName || '') +
                                ((e.target.className && typeof e.target.className === 'string')
                                 ? '.' + e.target.className.slice(0,30) : ''),
                        ts: Date.now()
                    });
                }, true);

                // 监听鼠标滚轮
                document.addEventListener('wheel', (e) => {
                    window.__recorded_events.push({
                        t: 'scroll',
                        dx: Math.round(e.deltaX),
                        dy: Math.round(e.deltaY),
                        ts: Date.now()
                    });
                }, true);
            }""")
            self._js_listener_ready = True
        except Exception as e:
            print(f"⚠️  事件监听注入失败: {e}")
            self._js_listener_ready = False

    async def _flush_events(self) -> list:
        """取出并清空事件缓存"""
        if not self._js_listener_ready or not self.page:
            events = list(self._event_buffer)
            self._event_buffer = []
            return events
        try:
            events = await self.page.evaluate("""() => {
                const buf = window.__recorded_events || [];
                window.__recorded_events = [];
                return buf.slice(-200);  // 最多取200条
            }""")
            return events or []
        except:
            return []

    async def record_step(self, step_number: int) -> dict:
        """标记一个步骤——捕获当前页面状态 + 事件序列"""
        if not self._is_recording or not self.page:
            return {"step": step_number, "error": "not_recording"}

        ts = datetime.now()
        events = await self._flush_events()
        step_data = {
            "step": step_number,
            "time": ts.strftime("%H:%M:%S"),
            "ts_ms": int(ts.timestamp() * 1000),
            "elapsed": round(time.time() - self._start_time, 1),
            "events_since_last": len(events),
            "events": events,
        }

        # 采集页面状态
        try:
            state = await self.page.evaluate("""() => {
                const text = (document.body.innerText || '').trim();

                // 收集页面上所有可见的可交互元素
                const interactables = [];
                const selectors = ['button', 'a', 'input', 'textarea',
                    '[contenteditable]', '[data-e2e]', '[class*="btn"]', '[class*="tab"]',
                    'video', 'audio', '[role="button"]', '[role="link"]'];
                const found = new Set();
                document.querySelectorAll(selectors.join(',')).forEach(el => {
                    const r = el.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0 && r.top < window.innerHeight) {
                        const key = el.tagName + (el.className && typeof el.className === 'string' ? el.className.slice(0,20) : '');
                        if (!found.has(key)) {
                            found.add(key);
                            const e2e = el.getAttribute && el.getAttribute('data-e2e');
                            interactables.push({
                                tag: el.tagName.toLowerCase(),
                                text: (el.textContent||'').trim().slice(0,30),
                                cls: (el.className && typeof el.className === 'string') ? el.className.slice(0,40) : '',
                                e2e: e2e || '',
                                rect: `${Math.round(r.x)},${Math.round(r.y)} ${Math.round(r.w)}x${Math.round(r.h)}`,
                                vis: r.top < window.innerHeight && r.left < window.innerWidth
                            });
                        }
                    }
                });

                return {
                    url: window.location.href,
                    title: document.title,
                    text_snippet: text.slice(0, 2000),
                    interactable_count: interactables.length,
                    interactables: interactables.slice(0, 50),
                    viewport: `${window.innerWidth}x${window.innerHeight}`,
                    page_mode: text.includes('视频') && document.querySelector('video') ? 'player'
                              : text.includes('关注') && text.includes('粉丝') ? 'profile'
                              : text.length > 500 ? 'grid' : 'other',
                };
            }""")
            step_data["page"] = state
        except Exception as e:
            step_data["page"] = {"error": str(e)}

        # 截图
        try:
            ss_dir = RECORDINGS_DIR / "screenshots"
            ss_dir.mkdir(parents=True, exist_ok=True)
            ss_file = ss_dir / f"step{step_number}_{ts.strftime('%H%M%S')}.png"
            await self.page.screenshot(path=str(ss_file))
            step_data["screenshot"] = str(ss_file)
        except:
            step_data["screenshot"] = None

        self._steps.append(step_data)

        # 输出摘要
        p = step_data.get("page", {})
        mode = p.get("page_mode", "?")
        url_short = p.get("url", "?")[:50]
        print(f"  [{step_number}] {mode} {url_short}  "
              f"events={step_data['events_since_last']}  "
              f"interactables={p.get('interactable_count', '?')}")
        if events:
            # 显示最后几个重要事件
            key_events = [e for e in events if e.get('t') in ('key', 'click')][-3:]
            for e in key_events:
                if e['t'] == 'key':
                    print(f"       ⌨️ {e.get('k','?')}")
                elif e['t'] == 'click':
                    print(f"       🖱️ 点击 ({e.get('x',0)},{e.get('y',0)}) <{e.get('target','')}>")

        return step_data

    async def stop(self) -> dict:
        """结束录制——打包保存"""
        self._is_recording = False

        package = {
            "meta": {
                "account_id": self.account_id,
                "platform": self.platform,
                "start_time": datetime.fromtimestamp(self._start_time).strftime("%H:%M:%S"),
                "end_time": datetime.now().strftime("%H:%M:%S"),
                "duration": round(time.time() - self._start_time, 1),
                "total_steps": len([s for s in self._steps if isinstance(s.get('step'), int)]),
                "created": datetime.now().isoformat(),
            },
            "steps": self._steps,
        }

        # 保存录制包
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        pkg_file = RECORDINGS_DIR / f"recording_{self.account_id}_{ts}.json"
        with open(pkg_file, "w", encoding="utf-8") as f:
            json.dump(package, f, ensure_ascii=False, indent=2)

        print(f"\n💾 录制包已保存: {pkg_file}")
        print(f"   {package['meta']['total_steps']} 步, "
              f"耗时 {package['meta']['duration']}s")

        # 关闭浏览器
        if self.conn:
            try:
                await self.conn.close()
                print("🛑 浏览器已关闭")
            except:
                pass

        return package

    @staticmethod
    def list_recordings() -> list:
        """列出所有录制包"""
        files = sorted(RECORDINGS_DIR.glob("recording_*.json"))
        result = []
        for f in files:
            try:
                raw = f.read_text(encoding="utf-8")
                # 只解析 meta 部分，避免加载大量 steps 数据
                meta_end = raw.find('"steps"')
                if meta_end > 0:
                    meta_json = raw[:meta_end].rstrip(',\n ') + '}'
                    pkg = json.loads(meta_json)
                else:
                    pkg = json.loads(raw)
                meta = pkg.get("meta", {})
                result.append({
                    "file": f.name,
                    "path": str(f),
                    "account": meta.get("account_id", "?"),
                    "platform": meta.get("platform", "?"),
                    "steps": meta.get("total_steps", 0),
                    "duration": meta.get("duration", 0),
                    "created": meta.get("created", ""),
                })
            except:
                result.append({"file": f.name, "error": "parse_error"})
        return result

    @staticmethod
    def delete_recording(name_or_path: str) -> bool:
        """删除录制包和关联的截图"""
        p = Path(name_or_path)
        if not p.exists():
            p = RECORDINGS_DIR / name_or_path
        if not p.exists():
            return False
        # 删除录制包
        p.unlink()
        # 也删除关联的截图（可选）
        ss_dir = RECORDINGS_DIR / "screenshots"
        if ss_dir.exists():
            prefix = p.stem.replace("recording_", "")
            for ss in ss_dir.glob(f"*{prefix}*"):
                ss.unlink()
        return True

    @staticmethod
    def load_recording(name_or_path: str) -> dict:
        """加载录制包"""
        p = Path(name_or_path)
        if not p.exists():
            p = RECORDINGS_DIR / name_or_path
        if not p.exists():
            raise FileNotFoundError(f"录制包不存在: {name_or_path}")
        return json.loads(p.read_text(encoding="utf-8"))


# ── 独立运行（热键监听模式）──
async def _run_interactive(account_id: str, platform: str, timeout_minutes: int = 60):
    """交互式录制——监听键盘数字键
    
    Args:
        account_id: 账号 ID
        platform: 平台 (douyin/xiaohongshu)
        timeout_minutes: 无操作超时分钟 (默认 60，超时自动退出清理)
    """
    session = RecordingSession(account_id, platform)
    await session.start()
    loop = asyncio.get_running_loop()
    timeout_seconds = timeout_minutes * 60
    last_activity = loop.time()

    try:
        from pynput import keyboard
        DIGIT_VK = {18:1, 19:2, 20:3, 21:4, 23:5, 22:6, 26:7, 28:8, 25:9, 29:0}

        def on_release(key):
            nonlocal last_activity
            try:
                n = None
                if hasattr(key, 'vk') and key.vk in DIGIT_VK:
                    n = DIGIT_VK[key.vk]
                elif hasattr(key, 'char') and key.char and key.char.isdigit():
                    n = int(key.char)

                if n is None:
                    return True

                last_activity = loop.time()  # 更新最后活动时间

                if 1 <= n <= 8:
                    asyncio.run_coroutine_threadsafe(
                        session.record_step(n), loop
                    )
                elif n == 0:
                    asyncio.run_coroutine_threadsafe(
                        session.stop(), loop
                    )
                    return False  # 告诉 pynput 停止监听
                return True
            except:
                return True

        listener = keyboard.Listener(on_release=on_release)
        listener.start()
        print(f"⌨️ 数字键 1-8 标记步骤, 0 结束 (无操作 {timeout_minutes} 分钟自动退出)\n")

        while session._is_recording:
            await asyncio.sleep(1)
            # 超时检查
            if loop.time() - last_activity > timeout_seconds:
                print(f"\n⏰ 无操作超过 {timeout_minutes} 分钟，自动退出")
                await session.stop()
                break

        listener.stop()
        print("✅ 录制结束")

    except ImportError:
        print("⚠️ pynput 不可用，使用终端输入模式")
        try:
            while True:
                try:
                    cmd = input("步骤? ").strip()
                    if not cmd: continue
                    n = int(cmd)
                    if 1 <= n <= 8:
                        await session.record_step(n)
                    elif n == 0:
                        await session.stop()
                        break
                except (ValueError, KeyboardInterrupt):
                    break
        finally:
            await session.stop()
            print("✅ 录制已停止，资源已清理")

    except Exception:
        # 异常时也确保清理
        await session.stop()
        raise
    finally:
        # 无论如何，确保 Playwright driver 被清理
        await session.stop()
        _cleanup_playwright_drivers()


def _cleanup_playwright_drivers():
    """清理残留的 Playwright driver 进程（运行超过1小时的）"""
    import subprocess, os
    try:
        result = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.split("\n"):
            if "playwright/driver" in line and "node" in line:
                parts = line.split()
                if len(parts) > 1:
                    pid = parts[1]
                    try:
                        # 只杀掉非当前进程的 playwright driver
                        if pid != str(os.getpid()):
                            subprocess.run(["kill", pid], capture_output=True, timeout=5)
                    except:
                        pass
    except:
        pass


if __name__ == "__main__":
    import sys
    account = sys.argv[1] if len(sys.argv) > 1 else "douyin_01"
    platform = sys.argv[2] if len(sys.argv) > 2 else "douyin"
    asyncio.run(_run_interactive(account, platform))

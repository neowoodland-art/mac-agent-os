"""
recorder.py — 原子操作录制引擎 (v2.0)

三阶段管线 Phase 1:
  启动 Camoufox → 用户操作 → 反引号 `·` 标记步骤 / Esc 结束 → 
  系统自动捕获: URL + DOM + 截图 + CDP事件序列

用法:
  from mc.recorder import RecordingSession
  session = RecordingSession("douyin_01")
  await session.start()
  # 用户操作后在浏览器按 `·` 标记步骤，按 Esc 结束
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

from matrix_mgmt import AGENT_LOCAL
from ops._base import PageState
LOCAL_ROOT = AGENT_LOCAL / "tools" / "matrix"
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
        await asyncio.sleep(3)

        # ── 鼠标响应测试（确认浏览器加载完成）──
        try:
            await self.page.mouse.move(400, 300)
            await asyncio.sleep(0.3)
            await self.page.mouse.move(400, 320)
            await asyncio.sleep(0.3)
            await self.page.mouse.move(400, 300)
            print(f"   ✅ 浏览器响应正常")
        except Exception as e:
            print(f"   ⚠️ 浏览器响应异常: {e}")
            print(f"   可能是身份加载卡顿，继续等待...")
            await asyncio.sleep(5)

        # ── 登录态检测 ──
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from auth_manager import check_login_by_dom
            logged_in = await check_login_by_dom(self.page, self.platform)
            if not logged_in:
                print(f"⚠️  账号 {self.account_id} 未登录")
                print(f"   请在浏览器中扫码登录，登录后按 Enter 继续...")
                # 等用户登录——轮询检测每 3 秒一次
                import select, sys as _sys
                for i in range(60):  # 最多等 3 分钟
                    if await check_login_by_dom(self.page, self.platform):
                        print(f" ✅ 检测到登录成功!")
                        break
                    # 也允许按 Enter 跳过
                    if i % 10 == 0:  # 每 30 秒提示一次
                        print(f"   等待登录中... (剩余 {3-i//20} 分钟)")
                    await asyncio.sleep(3)
                else:
                    print(f" ⏰ 等待超时，继续以未登录状态录制")
            else:
                print(f" ✅ 已登录")
        except ImportError:
            print(f" ⚠️  登录检测模块不可用，跳过")
        except Exception as e:
            print(f" ⚠️  登录检测异常: {e}")

        # 注入 JS 事件监听器（捕获键盘/鼠标事件到 window.__recorded_events）
        await self._inject_event_listener()

        print(f"\n{'='*55}")
        print(f" 🎬 录制就绪！")
        print(f"   账号: {self.account_id}")
        print(f"   在浏览器中操作，然后按:")
        print(f"     F2 → 标记步骤（截图+状态指纹）")
        print(f"     F4 → 结束录制")
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
                        code: e.code,
                        c: e.ctrlKey,
                        m: e.metaKey,
                        a: e.altKey,
                        s: e.shiftKey,
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

                // 监听鼠标悬浮（元素边界变化时记录，不会产生大量事件）
                document.addEventListener('mouseover', (e) => {
                    const t = e.target;
                    const tag = (t.tagName || '').toLowerCase();
                    const txt = (t.textContent || '').trim().slice(0, 20);
                    const cls = (t.className && typeof t.className === 'string') ? t.className.slice(0,25) : '';
                    // 只记录有意义的悬浮：按钮/链接/菜单等
                    if (['a','button','li','span','div','img'].includes(tag) && (txt || cls)) {
                        window.__recorded_events.push({
                            t: 'hover',
                            tag: tag,
                            text: txt,
                            cls: cls,
                            x: e.clientX,
                            y: e.clientY,
                            ts: Date.now()
                        });
                    }
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

                // 页面关闭/离开时自动结束录制
                window.__recorder_closing = false;
                window.addEventListener('beforeunload', () => {
                    window.__recorder_closing = true;
                });
            }""")
            self._js_listener_ready = True
        except Exception as e:
            print(f"⚠️  事件监听注入失败: {e}")
            self._js_listener_ready = False

    async def _flush_events(self) -> list:
        """取出并清空事件缓存（导航后自动重注入 JS 监听器）"""
        if not self._js_listener_ready or not self.page:
            events = list(self._event_buffer)
            self._event_buffer = []
            return events
        try:
            events = await self.page.evaluate("""() => {
                const buf = window.__recorded_events || [];
                window.__recorded_events = [];
                return buf.slice(-200);
            }""")
            # 如果事件数组为空但页面还在，可能是导航导致注入丢失，重注入
            if not events and self.page:
                print(f"  🔄 页面导航检测，重注入事件监听器")
                await self._inject_event_listener()
            return events or []
        except:
            return []

    async def _capture_page_state(self) -> dict:
        """捕获当前页面的状态指纹（用于录制分析）
        
        使用与三段式操作相同的 PageState 结构，便于 Analyzer 分析。
        """
        state = PageState()
        if not self.page:
            return state.to_dict()
        try:
            state.url_pattern = self.page.url
            # 页面模式
            text = await self.page.evaluate("(document.body.innerText || '').trim()") or ""
            has_video = await self.page.evaluate("document.querySelectorAll('video').length > 0")
            if '/video/' in state.url_pattern and has_video:
                state.page_mode = 'player'
            elif has_video:
                state.page_mode = 'player'
            elif '/user/' in state.url_pattern or '/profile' in state.url_pattern:
                state.page_mode = 'profile'
            elif '/search/' in state.url_pattern:
                state.page_mode = 'search'
            elif 'xiaohongshu' in state.url_pattern:
                state.page_mode = 'grid' if 'explore' in state.url_pattern else 'unknown'
            else:
                state.page_mode = 'grid'
            # 关键选择器可见性
            for sel in ['[data-e2e="video-player-digg"]', '[data-e2e="video-player-collect"]',
                        '[data-e2e="searchbar-input"]', 'video', 'section.note-item']:
                try:
                    state.selectors[sel] = await self.page.locator(sel).first.is_visible()
                except:
                    state.selectors[sel] = False
            # 文本片段
            state.text_snippet = text[:2000]
        except:
            pass
        return state.to_dict()

    async def record_step(self, step_number: int) -> dict:
        """标记一个步骤——捕获当前页面状态 + 事件序列 + 状态指纹"""
        if not self._is_recording or not self.page:
            return {"step": step_number, "error": "not_recording"}

        # 捕获操作前状态
        before_state = await self._capture_page_state()
        ts = datetime.now()
        events = await self._flush_events()
        step_data = {
            "step": step_number,
            "time": ts.strftime("%H:%M:%S"),
            "ts_ms": int(ts.timestamp() * 1000),
            "elapsed": round(time.time() - self._start_time, 1),
            "events_since_last": len(events),
            "events": events,
            "before_state": before_state,
        }

        # 采集页面状态
        try:
            state = await self.page.evaluate("""() => {
                const text = (document.body.innerText || '').trim();

                // 收集页面上所有可见的可交互元素（包括弹层里的）
                const interactables = [];
                const found = new Set();
                // 获取所有可见元素（不限制选择器）
                const allEls = document.querySelectorAll('input, button, a, textarea, [contenteditable], [tabindex], [role="button"], [role="link"], [data-e2e], select, [class*="btn"], [class*="tab"]');
                allEls.forEach(el => {
                    const r = el.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0 && r.top < window.innerHeight) {
                        const key = el.tagName + (typeof el.className === 'string' ? el.className.slice(0,20) : '');
                        if (!found.has(key)) {
                            found.add(key);
                            const e2e = el.getAttribute && el.getAttribute('data-e2e');
                            interactables.push({
                                tag: el.tagName.toLowerCase(),
                                text: (el.textContent||'').trim().slice(0,35),
                                cls: (typeof el.className === 'string') ? el.className.slice(0,50) : '',
                                e2e: e2e || '',
                                placeholder: el.getAttribute ? (el.getAttribute('placeholder') || '') : '',
                                type: el.getAttribute ? (el.getAttribute('type') || '') : '',
                                rect: `${Math.round(r.x)},${Math.round(r.y)} ${Math.round(r.w)}x${Math.round(r.h)}`,
                                vis: r.top < window.innerHeight && r.left < window.innerWidth
                            });
                        }
                    }
                });

                // 额外：专门查找所有 input（可能是登录浮层里的）
                const allInputs = document.querySelectorAll('input');
                allInputs.forEach(el => {
                    const r = el.getBoundingClientRect();
                    const key = 'INPUT_extra_' + (el.placeholder || '') + (el.className || '');
                    if (r.width > 0 && r.height > 0 && !found.has(key)) {
                        found.add(key);
                        interactables.push({
                            tag: 'input',
                            text: '',
                            cls: (typeof el.className === 'string') ? el.className.slice(0,50) : '',
                            e2e: el.getAttribute ? (el.getAttribute('data-e2e') || '') : '',
                            placeholder: el.getAttribute ? (el.getAttribute('placeholder') || '') : '',
                            type: el.getAttribute ? (el.getAttribute('type') || '') : '',
                            rect: `${Math.round(r.x)},${Math.round(r.y)} ${Math.round(r.w)}x${Math.round(r.h)}`,
                            vis: true
                        });
                    }
                });

                return {
                    url: window.location.href,
                    title: document.title,
                    text_snippet: text.slice(0, 4000),
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

    async def stop(self, keep_open: bool = True) -> dict:
        """结束录制——打包保存

        Args:
            keep_open: 是否保持浏览器打开（默认 True）
        """
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

        # 关闭浏览器（keep_open=False 时才关）
        if self.conn and not keep_open:
            try:
                await self.conn.close()
                print("🛑 浏览器已关闭")
            except:
                pass
        elif self.conn and keep_open:
            print("🔓 浏览器保持打开状态")

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
async def _run_interactive(account_id: str, platform: str, timeout_minutes: int = 60,
                           keep_open: bool = True):
    """交互式录制——反引号标记步骤, Esc 结束

    操作方式:
      - 在浏览器窗口中操作
      - 每完成一个动作 → 按反引号 `·` 键标记一步
      - Esc → 结束录制
      - 无操作超时自动退出

    Args:
        account_id: 账号 ID
        platform: 平台 (douyin/xiaohongshu)
        timeout_minutes: 无操作超时分钟
        keep_open: 录制结束后是否保持浏览器打开
    """
    session = RecordingSession(account_id, platform)
    await session.start()
    loop = asyncio.get_running_loop()
    timeout_seconds = timeout_minutes * 60
    last_activity = loop.time()
    step_counter = 0
    _manual_end = False

    print(f"⌨️  在浏览器中按反引号 `·` 标记步骤, Esc 结束录制")
    print(f"    无操作 {timeout_minutes} 分钟自动退出\n")

    try:
        while session._is_recording:
            await asyncio.sleep(0.5)

            # 从浏览器 JS 事件缓冲区读取按键
            try:
                key_pressed = await session.page.evaluate("""() => {
                    const buf = window.__recorded_events || [];
                    for (let i = buf.length - 1; i >= 0; i--) {
                        const e = buf[i];
                        if (e && e.t === 'key') {
                            const code = e.code || '';
                            // F2 标记步骤, Esc / F4 结束
                            if (code === 'F2') return 'step';
                            if (code === 'F4' || e.k === 'Escape' || code === 'Escape') return 'quit';
                        }
                    }
                    // 检测页面是否正在关闭（浏览器标签被关）
                    if (window.__recorder_closing) return 'quit';
                    return '';
                }""")
            except:
                # page.evaluate 失败 = 页面已关闭，保存录制
                print(f"\n  🛑 浏览器已关闭，保存录制...")
                _manual_end = True
                await session.stop(keep_open=False)
                break

            if key_pressed == 'step':
                step_counter += 1
                last_activity = loop.time()
                await session.record_step(step_counter)
                print(f"  ✅ 第{step_counter}步已记录")

            elif key_pressed == 'quit':
                _manual_end = True
                print(f"\n  🛑 结束录制...")
                await session.stop(keep_open=True)
                break

            # 超时检查
            if loop.time() - last_activity > timeout_seconds:
                print(f"\n⏰ 无操作超过 {timeout_minutes} 分钟，自动退出")
                await session.stop(keep_open=False)
                break

        if not _manual_end and session._is_recording:
            await session.stop()

    except Exception as e:
        print(f"\n⚠️ 录制异常: {e}")
        print(f"   浏览器保持打开状态, 可手动操作或关闭")
        return

    finally:
        if keep_open and _manual_end:
            print(f"\n🔓 录制已完成, 浏览器保持打开 (可继续查看或手动关闭)")
        elif not keep_open:
            _cleanup_playwright_drivers()

    print(f"\n✅ 录制结束, 共 {step_counter} 步")


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
    import sys, os, atexit
    account = sys.argv[1] if len(sys.argv) > 1 else "douyin_01"
    platform = sys.argv[2] if len(sys.argv) > 2 else "douyin"

    # 退出时清理 PID 文件
    pid_file = RECORDINGS_DIR.parent.parent.parent / "agent-local" / "runtime" / "recording.pid"
    def _cleanup_pid():
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                if pid == os.getpid():
                    pid_file.unlink(missing_ok=True)
            except:
                pass
    atexit.register(_cleanup_pid)

    asyncio.run(_run_interactive(account, platform))

"""
豆包浏览器驱动 —— 原子操作链

通过 CloakBrowser 控制豆包网页版，自动分析抖音视频链接。
回退机制：CloakBrowser → Peekaboo → 人工

使用方式：
    from doubao_driver import DoubaoDriver
    
    driver = DoubaoDriver()
    result = driver.analyze_video("https://www.douyin.com/video/xxxxx")
    print(result["content"])  # 豆包的分析回复
"""

import re, json, time, os
from pathlib import Path

# 输出目录
OUTPUT_DIR = Path(__file__).parent / "scripts_output"
MATERIALS_DIR = Path.home() / "workbuddy-agent-os/agent-local/materials/videos"
# 分析提示词模板
PROMPT_TEMPLATE = """请分析这个抖音视频，按以下格式输出：

【核心观点】
（一句话概括视频的核心思想）

【金句摘录】
（列出视频中值得记录的金句，每条一句话）

【内容结构】
（分析视频的叙事结构，分点列出）

【延伸思考】
（这个内容对我们有什么启发或实用价值）

视频链接：{url}"""


class DoubaoDriver:
    """豆包网页版浏览器驱动"""

    def __init__(self, engine="cloakbrowser"):
        self.engine = engine
        self.browser = None
        self.page = None

    # ============ 原子操作 ============

    def _start_browser(self):
        """启动浏览器"""
        if self.engine == "cloakbrowser":
            from cloakbrowser import launch
            self.browser = launch(humanize=False)
        else:
            raise ValueError(f"不支持的引擎: {self.engine}")
        self.page = self.browser.new_page()

    def _ensure_logged_in(self) -> bool:
        """检查是否已登录豆包"""
        current_url = self.page.url
        # 未登录会跳转到 login 页面
        if "login" in current_url.lower() or "sign" in current_url.lower() or "auth" in current_url.lower():
            print("  ⚠️ 豆包未登录！请先在浏览器中登录 doubao.com")
            return False
        # 检查是否有输入框（登录后才能看到）
        inp = self._find_input()
        if not inp:
            print("  ⚠️ 找不到豆包输入框，可能未登录")
            return False
        return True

    def _find_input(self):
        """找到输入框，返回 element handle 或 None"""
        try:
            return self.page.wait_for_selector(
                'textarea[placeholder*="发消息"]',
                timeout=5000
            )
        except:
            try:
                return self.page.wait_for_selector('textarea', timeout=3000)
            except:
                return None

    def _paste_link(self, url: str):
        """粘贴链接到输入框"""
        inp = self._find_input()
        if inp:
            inp.click()
            inp.fill("")  # 清空
            inp.type(url, delay=50)  # 模拟输入，触发 React 状态
        time.sleep(0.5)

    def _click_send(self) -> bool:
        """点击发送按钮"""
        try:
            # 尝试用键盘发送
            self.page.keyboard.press("Enter")
            return True
        except:
            try:
                btn = self.page.query_selector('button:has(svg)')
                if btn:
                    btn.click()
                    return True
            except:
                pass
        return False

    def _wait_for_response(self, timeout: int = 60) -> bool:
        """等待豆包回复，检测新消息出现"""
        start = time.time()
        last_content_len = 0
        stable_count = 0

        while time.time() - start < timeout:
            content_len = self.page.evaluate('''() => {
                // 获取所有消息区域的内容
                const msgs = document.querySelectorAll('[class*="message"], [class*="chat"], [class*="answer"]');
                let total = 0;
                msgs.forEach(m => total += (m.textContent || '').length);
                return total;
            }''')

            if content_len > 100:  # 有实质内容
                if content_len == last_content_len:
                    stable_count += 1
                    if stable_count >= 3:  # 连续 3 次无变化，认为完成
                        return True
                else:
                    stable_count = 0
                last_content_len = content_len

            time.sleep(2)

        return False

    def _extract_response(self) -> str:
        """提取豆包的最后一条回复"""
        result = self.page.evaluate('''() => {
            // 尝试多种选择器获取 AI 回复
            const selectors = [
                '[class*="message"]',
                '[class*="answer"]',
                '[class*="response"]',
                '[class*="chat-item"]',
                '.chat-message',
                'div[data-testid*="answer"]'
            ];
            for (const sel of selectors) {
                const els = document.querySelectorAll(sel);
                if (els.length > 0) {
                    const last = els[els.length - 1];
                    return last.textContent || '';
                }
            }
            // fallback: 获取页面中最大的文本块（排除输入框）
            const ta = document.querySelector('textarea');
            const taVal = ta ? ta.value : '';
            const allText = document.body.innerText || '';
            // 减去输入框内容
            return allText.replace(taVal, '').trim();
        }''')
        return result.strip() if result else ""

    def _new_conversation(self):
        """新建对话（如有必要）"""
        # 豆包通常每次发送都是同一个对话，不需要新建
        pass

    def _close_browser(self):
        """关闭浏览器"""
        if self.browser:
            try:
                self.browser.close()
            except:
                pass

    # ============ 对外接口 ============

    def analyze_video(self, url: str, prompt: str = None) -> dict:
        """
        分析单个视频链接，返回豆包的分析结果

        Args:
            url: 抖音视频链接
            prompt: 自定义提示词（默认使用结构化模板）

        Returns:
            {success, content, url, elapsed, error}
        """
        if not prompt:
            prompt = PROMPT_TEMPLATE.format(url=url)

        t0 = time.time()
        try:
            self._start_browser()
            self.page.goto("https://www.doubao.com/chat", timeout=30000)

            if not self._ensure_logged_in():
                return {"success": False, "error": "豆包未登录", "url": url}

            # 找到输入框
            inp = self._find_input()
            if not inp.get("found"):
                return {"success": False, "error": "找不到输入框", "url": url}

            # 粘贴链接并发送
            self._paste_link(url)
            time.sleep(0.5)

            sent = self._click_send()
            if not sent:
                return {"success": False, "error": "发送按钮点击失败", "url": url}

            # 等待豆包分析
            ok = self._wait_for_response(timeout=60)
            if not ok:
                return {"success": False, "error": "豆包回复超时", "url": url}

            # 提取回复
            content = self._extract_response()
            elapsed = round(time.time() - t0, 1)

            return {
                "success": True,
                "content": content,
                "url": url,
                "elapsed": elapsed,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "url": url}
        finally:
            self._close_browser()

    def analyze_profile(self, profile_url: str, max_videos: int = 5) -> list[dict]:
        """
        分析主播主页的所有视频

        先用 OpenCLI 获取视频列表，再逐个分析

        Args:
            profile_url: 主播主页链接
            max_videos: 最大分析视频数

        Returns:
            [{success, content, url, title, ...}, ...]
        """
        print(f"  🔍 获取主播视频列表: {profile_url}")
        video_links = self._get_profile_videos(profile_url, max_videos)

        if not video_links:
            return [{"success": False, "error": "无法获取视频列表", "url": profile_url}]

        print(f"  ✅ 获取到 {len(video_links)} 个视频")
        results = []
        for i, v in enumerate(video_links):
            print(f"  [{i+1}/{len(video_links)}] 分析视频: {v['title'][:30]}...")
            r = self.analyze_video(v["url"])
            r["title"] = v.get("title", "")
            results.append(r)
            # 每个视频之间间隔一会，避免频率限制
            if i < len(video_links) - 1:
                time.sleep(3)

        return results

    def _get_profile_videos(self, profile_url: str, max_n: int) -> list[dict]:
        """通过 OpenCLI 获取主播视频列表"""
        import subprocess
        try:
            opencli = os.path.expanduser(
                "~/.workbuddy/binaries/node/versions/22.12.0/bin/opencli"
            )
            # 从 URL 提取 douyin user id
            uid = profile_url.strip("/").split("/")[-1]
            r = subprocess.run(
                [opencli, "douyin", "user", uid, "-f", "json", "--limit", str(max_n)],
                capture_output=True, text=True, timeout=30,
                env={**os.environ, "NODE_OPTIONS": ""},
            )
            data = json.loads(r.stdout) if r.stdout else {}
            items = data if isinstance(data, list) else data.get("data", [data])
            return [
                {"url": item.get("url", ""), "title": item.get("title", "")}
                for item in items[:max_n] if item.get("url")
            ]
        except Exception as e:
            print(f"  ⚠️ 获取视频列表失败: {e}")
            return []


# ============ 便捷函数 ============

def analyze_video(url: str) -> dict:
    """一键分析单个视频"""
    driver = DoubaoDriver()
    return driver.analyze_video(url)


def analyze_profile(url: str, max_videos: int = 5) -> list[dict]:
    """一键分析主播主页"""
    driver = DoubaoDriver()
    return driver.analyze_profile(url, max_videos)

"""
豆包浏览器驱动 v3 —— 持久化 session

用 CloakBrowser + 持久化用户目录
首次使用时需要在弹出的浏览器中手动登录豆包
之后自动复用登录态，无需再次登录
"""

import re, json, time, os, subprocess
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "scripts_output"
CLOAK_USER_DIR = Path.home() / ".cloakbrowser" / "doubao_profile"
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
    def __init__(self):
        self.context = None
        self.page = None

    def _start_persistent(self):
        """启动持久化浏览器（保留登录态）+ 小窗口适配"""
        CLOAK_USER_DIR.mkdir(parents=True, exist_ok=True)
        from cloakbrowser import launch_persistent_context
        self.context = launch_persistent_context(
            user_data_dir=str(CLOAK_USER_DIR),
            headless=False,
            viewport={"width": 1024, "height": 768},
            args=[
                "--window-size=1024,768",   # 小窗口
                "--window-position=50,50",    # 左上角偏移
                "--no-sandbox",
            ],
        )
        self.page = self.context.new_page()

    def _check_login(self) -> bool:
        """检查豆包登录状态"""
        self.page.goto("https://www.doubao.com/chat", timeout=30000)
        time.sleep(3)
        # 如果找不到「登录」按钮，说明已登录
        has_login_btn = self.page.evaluate(
            '() => Array.from(document.querySelectorAll("button"))'
            '.some(b => (b.textContent||"").includes("登录"))'
        )
        if has_login_btn:
            print("  ⚠️ 豆包未登录！请在打开的浏览器中手动登录")
            print("     登录完成后关掉浏览器即可")
            return False
        return True

    def analyze_video(self, url: str) -> dict:
        t0 = time.time()
        try:
            self._start_persistent()
            self._check_login()

            # 发送
            ta = self.page.query_selector('textarea[placeholder*="发消息"]')
            if not ta:
                return {"success": False, "error": "找不到输入框", "url": url}

            ta.fill(url)
            time.sleep(0.5)
            self.page.keyboard.press("Enter")
            print(f"  ⏳ 等待豆包分析...")

            # 等回复
            for i in range(30):
                time.sleep(2)
                body = self.page.evaluate("document.body.innerText || ''")
                if len(body) > 300:
                    content = body
                    elapsed = round(time.time() - t0, 1)
                    return {
                        "success": True,
                        "content": content,
                        "url": url,
                        "elapsed": elapsed,
                    }
            return {"success": False, "error": "回复超时", "url": url}

        except Exception as e:
            return {"success": False, "error": str(e), "url": url}
        finally:
            if self.context:
                try: self.context.close()
                except: pass

    def analyze_profile(self, profile_url: str, max_videos: int = 5) -> list[dict]:
        opencli = os.path.expanduser("~/.workbuddy/binaries/node/versions/22.12.0/bin/opencli")
        uid = profile_url.strip("/").split("/")[-1]
        try:
            r = subprocess.run([opencli, "douyin", "user", uid, "-f", "json", "--limit", str(max_videos)],
                capture_output=True, text=True, timeout=30,
                env={**os.environ, "NODE_OPTIONS": ""})
            items = json.loads(r.stdout) if r.stdout else []
            items = items if isinstance(items, list) else items.get("data", [items])
            videos = [{"url": v.get("url",""), "title": v.get("title","")} for v in items[:max_videos] if v.get("url")]
        except Exception as e:
            return [{"success": False, "error": str(e), "url": profile_url}]

        print(f"  ✅ 获取到 {len(videos)} 个视频")
        results = []
        for i, v in enumerate(videos):
            print(f"  [{i+1}/{len(videos)}] {v['title'][:30]}...")
            r = self.analyze_video(v["url"])
            r["title"] = v.get("title", "")
            results.append(r)
            time.sleep(2)
        return results


# 一键接口
def analyze_video(url: str) -> dict:
    return DoubaoDriver().analyze_video(url)

def analyze_profile(url: str, max_n: int = 5) -> list[dict]:
    return DoubaoDriver().analyze_profile(url, max_n)

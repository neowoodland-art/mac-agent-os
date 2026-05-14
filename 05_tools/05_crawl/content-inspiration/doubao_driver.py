"""
豆包浏览器驱动 v4 —— OpenCLI 浏览器控制

流程（全自动）：
  1. OpenCLI 打开抖音视频页
  2. 提取页面完整文字（标题+描述+章节字幕）
  3. 构造分享文案 → 发给豆包
  4. 提取结构化分析结果

无需点击分享按钮，无需人工复制链接。
"""

import re, json, time, os, subprocess
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "scripts_output"
OPENCLI = os.path.expanduser("~/.workbuddy/binaries/node/versions/22.12.0/bin/opencli")

ANALYSIS_PROMPT = """帮我总结这个视频的内容，包括以下5点：
1. 核心观点：视频的核心思想是什么？
2. 完整文案：视频里的每一句话/文案
3. 金句摘录：值得记录的句子
4. 背景音乐：用了什么风格的音乐
5. 内容结构：视频怎么组织的（开头/主体/结尾）

请按序号清晰输出。"""


def _oc(args: list, timeout: int = 30) -> str:
    """执行 OpenCLI 命令"""
    env = {**os.environ, "NODE_OPTIONS": ""}
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        env.pop(k, None)
    try:
        r = subprocess.run([OPENCLI] + args, capture_output=True, text=True, timeout=timeout, env=env)
        return r.stdout
    except:
        return ""


class DoubaoDriver:
    """豆包分析驱动（OpenCLI 版）"""

    def __init__(self):
        self.session = "doubao"

    # ============ 1. 提取视频页文字 ============

    def _extract_video_page(self, url: str) -> str:
        """打开视频页，提取所有可见文字"""
        # 绑定 session
        _oc(["browser", self.session, "bind"], timeout=5)
        time.sleep(1)
        # 打开视频
        _oc(["browser", self.session, "open", url], timeout=15)
        time.sleep(6)
        # 提取文字
        text = _oc(["browser", self.session, "eval", "document.body.innerText"], timeout=10)
        # 清理 JSON 包装
        text = re.sub(r'^\{[^}]*"result"[^}]*"|^"[}]$', '', text)
        return text.strip()

    def _build_share_text(self, url: str, page_text: str) -> str:
        """从页面文字构造分享文案"""
        # 清理无用行
        lines = page_text.split('\n')
        useful = [l for l in lines if len(l.strip()) > 3 and not any(
            kw in l for kw in ['开启读屏', '读屏标签', '精选', '推荐', '搜索',
                               '关注', '朋友', '我的', '直播', '放映厅',
                               '壁纸', '通知', '私信', '投稿', '登录',
                               '倍速', '智能', '清屏', '连播',
                               '展开', '条回复', '评论'])]
        context = '\n'.join(useful[:50])  # 取前50行有用内容
        return f"【抖音视频】\n{context}\n\n视频链接：{url}"

    # ============ 2. 豆包分析 ============

    def _send_to_doubao(self, text: str) -> str:
        """发送文字到豆包并提取回复"""
        # 打开豆包
        _oc(["browser", self.session, "open", "https://www.doubao.com/chat"], timeout=15)
        time.sleep(4)

        # 输入内容
        msg = f"{text}\n\n{ANALYSIS_PROMPT}"
        _oc(["browser", self.session, "type", "--nth", "0", "textarea", msg], timeout=15)
        time.sleep(1)

        # JS 触发发送
        _oc(["browser", self.session, "eval",
             "document.querySelector('textarea').dispatchEvent("
             "new KeyboardEvent('keydown',{key:'Enter',code:'Enter',keyCode:13,bubbles:true}))"],
            timeout=5)

        # 等回复
        time.sleep(25)

        # 提取
        result = _oc(["browser", self.session, "eval", "document.body.innerText"], timeout=10)
        return result

    def _parse_response(self, raw: str) -> dict:
        """解析豆包回复为结构化字段"""
        result = {
            "core_point": "",
            "full_text": "",
            "quotes": "",
            "music": "",
            "structure": "",
        }
        sections = re.split(r'[一二三四五]、', raw)
        for s in sections:
            if '核心' in s or '观点' in s:
                result["core_point"] = s.strip()
            elif '文案' in s or '字幕' in s:
                result["full_text"] = s.strip()
            elif '金句' in s:
                result["quotes"] = s.strip()
            elif '音乐' in s or 'BGM' in s or '配乐' in s:
                result["music"] = s.strip()
            elif '结构' in s:
                result["structure"] = s.strip()
        return result

    # ============ 对外接口 ============

    def analyze_video(self, url: str) -> dict:
        """分析单个视频，返回结构化结果"""
        t0 = time.time()
        try:
            print(f"  📄 提取视频页文字...")
            page_text = self._extract_video_page(url)
            if not page_text or len(page_text) < 50:
                return {"success": False, "error": "无法提取视频页内容", "url": url}

            share = self._build_share_text(url, page_text)
            print(f"  ✅ 已提取 {len(share)} 字，发送给豆包...")

            raw = self._send_to_doubao(share)
            parsed = self._parse_response(raw)

            elapsed = round(time.time() - t0, 1)
            return {
                "success": True,
                "url": url,
                "elapsed": elapsed,
                "raw_response": raw[-2000:],
                **parsed,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}

    def analyze_profile(self, profile_url: str, max_videos: int = 5) -> list[dict]:
        """分析主播主页的全部视频"""
        print(f"  🔍 获取主播视频列表...")
        uid = profile_url.strip("/").split("/")[-1]
        try:
            r = _oc(["browser", self.session, "open", profile_url], timeout=15)
            time.sleep(5)
            text = _oc(["browser", self.session, "eval", "document.body.innerText"], timeout=10)
            print(f"  📄 页面文字 {len(text)} 字")
        except:
            pass

        # 通过 OpenCLI 获取视频列表
        try:
            r = _oc(["douyin", "user-videos", uid, "-f", "json", "--limit", str(max_videos)], timeout=30)
            data = json.loads(r) if r else {}
            items = data if isinstance(data, list) else data.get("data", [data])
            videos = [{"url": v.get("url", ""), "title": v.get("title", "")} for v in items[:max_videos] if v.get("url")]
        except:
            videos = []

        if not videos:
            return [{"success": False, "error": "无法获取视频列表", "url": profile_url}]

        print(f"  ✅ 获取到 {len(videos)} 个视频")
        results = []
        for i, v in enumerate(videos):
            print(f"  [{i+1}/{len(videos)}] {v['title'][:30]}...")
            r = self.analyze_video(v["url"])
            r["title"] = v.get("title", "")
            results.append(r)
            if i < len(videos) - 1:
                time.sleep(3)
        return results


# 一键接口
def analyze_video(url: str) -> dict:
    return DoubaoDriver().analyze_video(url)

def analyze_profile(url: str, max_n: int = 5) -> list[dict]:
    return DoubaoDriver().analyze_profile(url, max_n)

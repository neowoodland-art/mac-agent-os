"""
豆包浏览器驱动 v5 —— 连续会话 + 稳定提取

改进：
  1. 连续对话：整个 session 只开一次豆包，所有视频在同一个对话中分析
  2. 稳定提取：直接用 prompt 中的【】标记做切分，不依赖数字序号
  3. 会话分离：抖音页面和豆包页面用不同的 session，不互相干扰
"""

import re, json, time, os, subprocess
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "scripts_output"
OPENCLI = os.path.expanduser("~/.workbuddy/binaries/node/versions/22.12.0/bin/opencli")

ANALYSIS_PROMPT = """请从这段视频内容中提取所有知识性内容，按以下格式完整记录，不要概括，不要总结：

【完整字幕】
逐句记录视频中的每一句话，一字不差

【提示词/指令原文】
如果视频中出现了AI提示词、模板、指令，请完整抄录，一字不改

【操作步骤】
视频中演示的具体操作流程，分步骤详细记录

【关键参数】
视频中提到的工具名称、参数设置、具体数字等

【核心技巧】
视频中传授的具体方法、技巧、经验

记住：只提取不总结，不要分析结构，不要分析背景音乐。"""


def _oc(args: list, timeout: int = 30) -> str:
    env = {**os.environ, "NODE_OPTIONS": ""}
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        env.pop(k, None)
    try:
        r = subprocess.run([OPENCLI] + args, capture_output=True, text=True, timeout=timeout, env=env)
        return r.stdout
    except:
        return ""


def _send_and_wait(text: str, wait_time: int = 25) -> str:
    """向当前 session 的输入框发送文字并等待回复"""
    _oc(["browser", "doubao", "type", "--nth", "0", "textarea", text], timeout=15)
    time.sleep(1)
    _oc(["browser", "doubao", "eval",
         "document.querySelector('textarea').dispatchEvent("
         "new KeyboardEvent('keydown',{key:'Enter',code:'Enter',keyCode:13,bubbles:true}))"],
        timeout=5)
    time.sleep(wait_time)
    return _oc(["browser", "doubao", "eval", "document.body.innerText"], timeout=10)


def _parse_sections(raw: str) -> dict:
    """从豆包回复中按【】标记提取各段落"""
    sections = {}
    # 定义要提取的标记
    markers = [
        "完整字幕", "提示词/指令原文", "提示词", "指令原文",
        "操作步骤", "关键参数", "核心技巧"
    ]
    for marker in markers:
        # 找 【xxx】 或 'xxx：' 或 'xxx:'
        patterns = [
            rf'【{re.escape(marker)}】\s*([\s\S]*?)(?=【|\Z)',
            rf'{re.escape(marker)}[：:]\s*([\s\S]*?)(?=【|\d[.、]|\Z)',
        ]
        for pat in patterns:
            m = re.search(pat, raw)
            if m:
                content = m.group(1).strip()
                # 清理 prompt 本身的说明文字
                content = re.sub(r'逐句记录.*|如果视频中.*|视频中演示.*|视频中提到.*|记住：.*', '', content)
                sections[marker] = content.strip()
                break
    return sections


class DoubaoDriver:
    """豆包分析驱动 v5"""

    def __init__(self):
        self.session_started = False

    def start_session(self):
        """启动豆包会话（只需一次）"""
        _oc(["browser", "doubao", "bind"], timeout=5)
        time.sleep(1)
        _oc(["browser", "doubao", "open", "https://www.doubao.com/chat"], timeout=15)
        time.sleep(5)
        self.session_started = True
        print("  ✅ 豆包会话已启动")

    def end_session(self):
        """结束会话"""
        self.session_started = False

    def analyze_video(self, url: str) -> dict:
        """分析单个视频"""
        t0 = time.time()
        try:
            # 1. 抖音 session 提取视频文字
            _oc(["browser", "douyin", "bind"], timeout=5)
            time.sleep(1)
            _oc(["browser", "douyin", "open", url], timeout=15)
            time.sleep(6)
            page_text = _oc(["browser", "douyin", "eval", "document.body.innerText"], timeout=10)
            page_text = re.sub(r'^\{[^}]*"result"[^}]*"|^"[}]$', '', page_text).strip()
            
            if not page_text or len(page_text) < 50:
                return {"success": False, "error": "无法提取视频页内容", "url": url}

            # 清理噪音
            lines = page_text.split('\n')
            useful = []
            skip_kw = ['开启读屏', '读屏标签', '精选', '推荐', '搜索',
                      '关注', '朋友', '我的', '直播', '放映厅', '壁纸',
                      '通知', '私信', '投稿', '登录', '倍速', '智能',
                      '清屏', '连播', '点击加载更多', '展开', '条回复',
                      '评论', '广告投放', '用户服务']
            for l in lines:
                t = l.strip()
                if len(t) > 5 and not any(kw in t for kw in skip_kw):
                    useful.append(t)
            context = '\n'.join(useful[:30])
            msg = f"视频 {url}\n\n视频内容：\n{context}\n\n{ANALYSIS_PROMPT}"

            # 2. 切回豆包 session 发送
            _oc(["browser", "doubao", "bind"], timeout=5)
            time.sleep(1)
            
            raw = _send_and_wait(msg)
            sections = _parse_sections(raw)

            elapsed = round(time.time() - t0, 1)
            return {
                "success": True,
                "url": url,
                "elapsed": elapsed,
                "raw_response": raw,
                "sections": sections,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}

    def analyze_profile(self, profile_url: str, max_videos: int = 5) -> list[dict]:
        """分析主播主页的全部视频（连续会话）"""
        # 获取视频列表
        _oc(["browser", "profile", "bind"], timeout=5)
        _oc(["browser", "profile", "open", profile_url], timeout=15)
        time.sleep(8)
        _oc(["browser", "profile", "scroll", "down"])
        time.sleep(3)
        _oc(["browser", "profile", "scroll", "down"])
        time.sleep(3)
        
        links_raw = _oc(["browser", "profile", "eval",
            "JSON.stringify(Array.from(document.querySelectorAll('a[href*=\"/video/\"]'))"
            ".slice(0," + str(max_videos) + ").map(a => ({url: a.href, title: (a.textContent||'').trim().slice(0,40)})))"
        ], timeout=10)
        try:
            videos = json.loads(links_raw)
        except:
            videos = []

        if not videos:
            return [{"success": False, "error": "无法获取视频列表", "url": profile_url}]

        # 启动豆包会话
        self.start_session()
        print(f"  ✅ 获取到 {len(videos)} 个视频，开始分析（同一对话）")

        results = []
        for i, v in enumerate(videos):
            print(f"\n  [{i+1}/{len(videos)}] {v.get('title','')[:30]}...")
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

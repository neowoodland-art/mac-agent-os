"""
豆包浏览器驱动 v7.1 —— 稳定等待法

改进：
  1. 豆包保持独立标签页，不关闭，不 rebind
  2. 抖音用另一个标签页，互不干扰
  3. 稳定等待法：触发增长后等连续 3 轮无变化才算完成，防止提前截断
  4. 改用 fill + click #flow-end-msg-send 替代 KeyboardEvent（React兼容）
"""

import re, json, time, os, subprocess
from pathlib import Path

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


def _oc(args, timeout=30):
    env = {**os.environ, "NODE_OPTIONS": ""}
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        env.pop(k, None)
    try:
        r = subprocess.run([OPENCLI] + args, capture_output=True, text=True, timeout=timeout, env=env)
        return r.stdout
    except:
        return ""


def _parse_sections(raw):
    """
    按标记提取各段落。
    支持两种格式：
      - 【】格式（旧）
      - === 标题 === 格式（新，豆包AI常用）
    """
    sections = {}
    
    # 先找 AI 回复的起始位置（跳过用户消息）
    lines = raw.split('\n')
    ai_start = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if (stripped.startswith('===') and 
            any(k in stripped for k in ['完整字幕', '提示词', '操作步骤', '关键参数', '核心技巧'])):
            next_chunk = '\n'.join(lines[i:i+4])
            if '逐句记录' not in next_chunk and '如果视频' not in next_chunk:
                ai_start = i
                break
    
    ai_raw = '\n'.join(lines[ai_start:]) if ai_start >= 0 else raw
    
    # 格式1：=== 标题 === 内容
    pattern = r'===\s*([^=]+?)\s*===\s*([\s\S]*?)(?====\s*[^=]|$)'
    for m in re.finditer(pattern, ai_raw):
        title = m.group(1).strip()
        content = m.group(2).strip()
        skip = ['逐句记录', '视频中演示', '视频中提到', '如果视频', '记住：', '完整抄录']
        if content and len(content) > 5 and not any(s in content[:40] for s in skip):
            sections[title] = content
    
    # 格式2：旧格式 【】兜底
    if not sections:
        markers = ["完整字幕", "提示词/指令原文", "提示词", "指令原文", "操作步骤", "关键参数", "核心技巧"]
        for marker in markers:
            m = re.search(rf'【{re.escape(marker)}】\s*([\s\S]*?)(?=【|\Z)', raw)
            if m:
                content = m.group(1).strip()
                content = re.sub(r'逐句记录.*|如果视频中.*|视频中演示.*|视频中提到.*|记住：.*', '', content)
                sections[marker] = content
    
    return sections


def _wait_for_response(session="doubao", max_wait=120, min_growth=500, stable_checks=3):
    """
    稳定等待法：检测页面文本显著增长后，再等连续 stable_checks 轮无变化才算完成。
    防止 AI 还在生成就被提前截断的老 bug。
    """
    before = len(_oc(["browser", session, "eval", "document.body.innerText"], timeout=10) or "")
    prev_len = before
    stable_count = 0
    triggered = False
    
    for i in range(max_wait // 5):
        time.sleep(5)
        body = _oc(["browser", session, "eval", "document.body.innerText"], timeout=10) or ""
        current_len = len(body)
        growth = current_len - prev_len
        total_growth = current_len - before
        
        has_sections = '===完整字幕' in body or '===操作步骤' in body or '===核心技巧' in body
        
        if total_growth > min_growth or has_sections:
            triggered = True
        
        if triggered:
            if growth == 0:
                stable_count += 1
            else:
                stable_count = 0  # 还在增长，重置
        
        if i > 0 and i % 2 == 0:
            status = f"    ⏳ {(i+1)*5}s...总增长{total_growth}字"
            if triggered:
                status += f" (稳定{stable_count}/{stable_checks})" if growth == 0 else " (增长中)"
            if has_sections:
                status += " ✅含结构"
            print(status, flush=True)
        
        if triggered and stable_count >= stable_checks:
            print(f"    ✅ 回复稳定，确认完成", flush=True)
            return body
    
    print(f"    ⏰ 超时({max_wait}s)，返回当前内容", flush=True)
    return _oc(["browser", session, "eval", "document.body.innerText"], timeout=10)


class DoubaoDriver:
    """豆包分析驱动 v7.1（稳定等待法）"""

    def __init__(self):
        self.doubao_ready = False
        self.douyin_session = "douyin"
        self.doubao_session = "doubao"

    def start_session(self):
        """启动豆包会话（只一次，标签页保持打开）"""
        # 先开一个空白标签给 douyin session
        _oc(["browser", self.douyin_session, "bind"], timeout=5)
        time.sleep(0.5)
        # 开新标签给 doubao session（在新标签页打开豆包）
        _oc(["browser", self.doubao_session, "tab", "new", "https://www.doubao.com/chat"], timeout=15)
        time.sleep(5)
        self.doubao_ready = True
        print("  ✅ 豆包会话已启动（独立标签页）")

    def analyze_video(self, url):
        """分析单个视频"""
        t0 = time.time()
        try:
            # 1. 抖音标签页：打开视频提取文字
            _oc(["browser", self.douyin_session, "bind"], timeout=5)
            time.sleep(0.5)
            _oc(["browser", self.douyin_session, "open", url], timeout=15)
            time.sleep(6)
            page_text = _oc(["browser", self.douyin_session, "eval", "document.body.innerText"], timeout=10)
            page_text = re.sub(r'^\{[^}]*"result"[^}]*"|^"[}]$', '', page_text).strip()
            
            if not page_text or len(page_text) < 50:
                return {"success": False, "error": "无法提取视频页内容", "url": url}

            # 清理
            skip_kw = ['开启读屏', '读屏标签', '精选', '推荐', '搜索',
                      '关注', '朋友', '我的', '直播', '放映厅', '壁纸',
                      '通知', '私信', '投稿', '登录', '倍速', '智能',
                      '清屏', '连播', '点击加载更多', '展开', '条回复',
                      '评论', '广告投放', '用户服务']
            useful = [l.strip() for l in page_text.split('\n') 
                     if len(l.strip()) > 5 and not any(k in l for k in skip_kw)]
            
            msg = f"视频 {url}\n\n视频内容：\n{chr(10).join(useful[:30])}\n\n{ANALYSIS_PROMPT}"

            # 2. 豆包标签页（已存在，用 fill 填入 + click 发送按钮）
            _oc(["browser", self.doubao_session, "bind"], timeout=5)
            time.sleep(0.5)
            _oc(["browser", self.doubao_session, "fill", "--nth", "0", "textarea", msg], timeout=15)
            time.sleep(1)
            # 触发发送（React 页面无法通过 dispatchEvent 捕获 KeyboardEvent）
            # 优先使用显式发送按钮 click，这个按钮有 id=flow-end-msg-send
            _oc(["browser", self.doubao_session, "click", "#flow-end-msg-send"], timeout=5)

            # 3. 智能等待回复
            raw = _wait_for_response(session=self.doubao_session)
            sections = _parse_sections(raw or "")

            elapsed = round(time.time() - t0, 1)
            return {
                "success": True,
                "url": url,
                "elapsed": elapsed,
                "raw_response": raw or "",
                "sections": sections,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}

    def analyze_profile(self, profile_url, max_videos=5):
        """分析主播主页"""
        _oc(["browser", "profile", "bind"], timeout=5)
        _oc(["browser", "profile", "open", profile_url], timeout=15)
        time.sleep(8)
        for _ in range(2):
            _oc(["browser", "profile", "scroll", "down"])
            time.sleep(3)

        links_raw = _oc(["browser", "profile", "eval",
            "JSON.stringify(Array.from(document.querySelectorAll('a[href*=\"/video/\"]'))"
            f".slice(0,{max_videos}).map(a=>({{url:a.href,title:(a.textContent||'').trim().slice(0,40)}})))"],
            timeout=10)
        try:
            videos = json.loads(links_raw)
        except:
            videos = []

        if not videos:
            return [{"success": False, "error": "无法获取视频列表", "url": profile_url}]

        self.start_session()
        print(f"  ✅ 获取到 {len(videos)} 个视频")

        results = []
        for i, v in enumerate(videos):
            print(f"\n  [{i+1}/{len(videos)}] {v.get('title','')[:30]}...")
            r = self.analyze_video(v["url"])
            r["title"] = v.get("title", "")
            results.append(r)
            time.sleep(2)
        return results


def analyze_video(url):
    return DoubaoDriver().analyze_video(url)

def analyze_profile(url, max_n=5):
    return DoubaoDriver().analyze_profile(url, max_n)

"""
搜索功能 — 支持 OpenCLI（浏览器桥接）与百度直接HTTP两种模式

OpenCLI 依赖：
  - npm 全局安装 @jackwener/opencli
  - Chrome 扩展已加载（opencli-extension）
  - opencli daemon 运行中
"""

import re, subprocess, json, os, threading, time

# OpenCLI 路径
OPENCLI_BIN = os.path.expanduser("~/.workbuddy/binaries/node/versions/22.12.0/bin/opencli")

# 平台映射：内部名称 → OpenCLI 子命令
PLATFORM_CMDS = {
    "douyin":      ("douyin", "search"),
    "zhihu":       ("zhihu", "search"),
    "xiaohongshu": ("xiaohongshu", "search"),
    "bilibili":    ("bilibili", "search"),
    "weibo":       ("weibo", "search"),
}


def _opencli_available() -> bool:
    """检查 OpenCLI 是否可用（扩展已连接）"""
    try:
        r = subprocess.run(
            [OPENCLI_BIN, "doctor"],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "NODE_OPTIONS": ""},
        )
        return "[OK]" in r.stdout and "Extension" in r.stdout and "connected" in r.stdout
    except:
        return False


def search_web(keyword: str, platform: str = "baidu", max_results: int = 15) -> list[dict]:
    """
    搜索平台内容，只返回元数据（不下载任何文件）

    平台支持（按优先级）：
      - baidu: 直连 httpx，无需扩展
      - douyin/zhihu/xiaohongshu/bilibili/weibo: 需 OpenCLI + Chrome 扩展

    Returns:
        [{url, title, author, brief, platform}, ...]
    """

    # ========== 百度搜索：直接HTTP ==========
    if platform == "baidu":
        return _search_baidu(keyword, max_results)

    # ========== OpenCLI 搜索 ==========
    cmd_info = PLATFORM_CMDS.get(platform)
    if not cmd_info:
        return []

    plat, action = cmd_info
    try:
        r = subprocess.run(
            [OPENCLI_BIN, plat, action, keyword, "-f", "json"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ.copy(), "NODE_OPTIONS": ""},
        )
        if r.returncode != 0:
            return []

        data = json.loads(r.stdout)
        # OpenCLI 返回格式：列表或对象列表
        items = data if isinstance(data, list) else data.get("data", data.get("results", [data]))

        results = []
        for item in items[:max_results]:
            url = item.get("url") or item.get("link") or ""
            title = item.get("title") or item.get("name") or ""
            author = item.get("author") or item.get("author_name") or ""
            brief = item.get("description") or item.get("desc") or item.get("snippet") or ""
            if url and title:
                results.append({
                    "url": url,
                    "title": str(title)[:40],
                    "author": str(author)[:20],
                    "brief": str(brief)[:80],
                    "platform": platform,
                })
        return results

    except subprocess.TimeoutExpired:
        print(f"[WARN] OpenCLI {platform} 搜索超时")
        return []
    except json.JSONDecodeError:
        print(f"[WARN] OpenCLI {platform} 返回非JSON")
        return []
    except FileNotFoundError:
        print(f"[WARN] OpenCLI 未安装，请执行: npm install -g @jackwener/opencli")
        return []
    except Exception as e:
        print(f"[WARN] OpenCLI {platform} 搜索失败: {e}")
        return []


def _search_baidu(keyword: str, max_results: int) -> list[dict]:
    """百度搜索：直接 HTTP 请求"""
    try:
        import httpx
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        resp = httpx.get(
            f"https://www.baidu.com/s?wd={keyword}&ie=utf-8",
            headers=headers, follow_redirects=True, timeout=15,
        )
        items = re.findall(r'<h3[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
        results = []
        seen = set()
        for href, title_html in items:
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            if title and len(title) > 4 and href not in seen:
                seen.add(href)
                full_url = href if href.startswith("http") else f"https://www.baidu.com{href}"
                results.append({
                    "url": full_url, "title": title[:40],
                    "author": "", "brief": "", "platform": "baidu",
                })
                if len(results) >= max_results:
                    break
        return results
    except Exception as e:
        print(f"[WARN] 百度搜索失败: {e}")
        return []


# ============ 内容类型映射 ============
CONTENT_TYPES = {
    "baidu": "文章",
    "douyin": "视频",
    "zhihu": "问答",
    "xiaohongshu": "图文",
    "bilibili": "视频",
    "weibo": "话题",
}

PLATFORM_LABELS = {
    "baidu": "🔍 百度",
    "douyin": "🎬 抖音",
    "zhihu": "📝 知乎",
    "xiaohongshu": "📕 小红书",
    "bilibili": "📺 B站",
    "weibo": "💬 微博",
}


def _search_platform_thread(keyword: str, platform: str, max_n: int, results: dict, index: int):
    """线程包装：搜索单个平台，结果存入 results[index]"""
    try:
        r = search_web(keyword, platform, max_n)
        results[index] = r if r else []
    except Exception as e:
        results[index] = []


def search_all(keyword: str, max_per_platform: int = 5) -> list[dict]:
    """
    全平台并行搜索，返回统一格式的合并结果列表。

    搜索6个平台：百度、抖音、知乎、小红书、B站、微博
    每个平台独立超时，失败不影响其他平台。

    Returns:
        [{platform, label, title, author, url, brief, type, size_hint, score}, ...]
    """
    platforms = ["baidu", "douyin", "zhihu", "xiaohongshu", "bilibili", "weibo"]
    thread_results = [None] * len(platforms)
    threads = []

    for i, plat in enumerate(platforms):
        t = threading.Thread(
            target=_search_platform_thread,
            args=(keyword, plat, max_per_platform, thread_results, i),
        )
        t.start()
        threads.append(t)

    # 等待所有线程完成（总超时60秒）
    for t in threads:
        t.join(timeout=60)

    # 合并结果，附带元数据
    all_results = []
    for i, plat in enumerate(platforms):
        items = thread_results[i] or []
        for item in items:
            all_results.append({
                "platform": plat,
                "label": PLATFORM_LABELS.get(plat, plat),
                "type": CONTENT_TYPES.get(plat, "其他"),
                "title": item.get("title", ""),
                "author": item.get("author", ""),
                "url": item.get("url", ""),
                "brief": item.get("brief", ""),
                "size_hint": _guess_content_size(item, plat),
                "score": _calc_match_score(keyword, item),
            })

    # 按匹配度排序
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results


def _guess_content_size(item: dict, platform: str) -> str:
    """估算内容量（视频时长/文字字数）"""
    title = item.get("title", "") or ""
    brief = item.get("brief", "") or ""
    combined = title + brief

    if platform in ("douyin", "bilibili"):
        # 视频平台：平均时长约 3-10 分钟
        return "3-10分钟视频"

    if platform in ("baidu", "zhihu", "weibo", "xiaohongshu"):
        # 文字平台：按摘要长度估算
        word_count = len(combined)
        if word_count > 100:
            return f"{word_count}字左右"
        elif platform in ("zhihu", "baidu"):
            return "长文（千字以上）"
        else:
            return "短文（简明）"

    return "未知"


def _calc_match_score(keyword: str, item: dict) -> int:
    """
    计算匹配度分数（1-5）
    基于标题和描述中关键词的匹配程度
    """
    title = (item.get("title", "") or "").lower()
    brief = (item.get("brief", "") or "").lower()
    kw = keyword.lower()

    score = 1
    # 标题包含完整关键词 → 高分
    if kw in title:
        score += 3
    # 描述包含关键词 → 中分
    if kw in brief:
        score += 2
    # 标题包含关键词的部分词 → 基础分
    for word in kw.split():
        if len(word) > 1 and word in title:
            score += 1

    return min(score, 5)

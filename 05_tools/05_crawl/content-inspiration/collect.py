"""
搜索功能 — 支持 OpenCLI（浏览器桥接）与百度直接HTTP两种模式

OpenCLI 依赖：
  - npm 全局安装 @jackwener/opencli
  - Chrome 扩展已加载（opencli-extension）
  - opencli daemon 运行中
"""

import re, subprocess, json, os

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

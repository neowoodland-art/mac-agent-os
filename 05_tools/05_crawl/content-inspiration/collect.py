def search_web(keyword: str, platform: str = "baidu", max_results: int = 15) -> list[dict]:
    """
    搜索平台内容，只返回元数据（不下载任何文件）

    当前可用平台：
      - baidu: 直接HTTP请求，无需任何配置
      - douyin/xiaohongshu/zhihu: 需浏览器渲染+登录，返回空，界面会提示手动粘贴链接

    Returns:
        [{url, title, author, brief, platform}, ...]
    """
    import re

    # 百度搜索：直接HTTP请求，解析搜索结果
    if platform == "baidu":
        try:
            import httpx
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
            url = f"https://www.baidu.com/s?wd={keyword}&ie=utf-8"
            resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=15)
            html = resp.text

            # 提取 h3 标题+链接（百度搜索结果标准结构）
            items = re.findall(r'<h3[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
            results = []
            seen = set()
            for href, title_html in items:
                title = re.sub(r'<[^>]+>', '', title_html).strip()
                if title and len(title) > 4 and href not in seen:
                    seen.add(href)
                    full_url = href if href.startswith("http") else f"https://www.baidu.com{href}"
                    results.append({
                        "url": full_url,
                        "title": title[:40],
                        "author": "",
                        "brief": "",
                        "platform": "baidu",
                    })
                    if len(results) >= max_results:
                        break
            return results
        except ImportError:
            print("[WARN] httpx 未安装")
            return []
        except Exception as e:
            print(f"[WARN] 百度搜索失败: {e}")
            return []

    # 其他平台需浏览器渲染，目前不支持直接HTTP搜索
    return []
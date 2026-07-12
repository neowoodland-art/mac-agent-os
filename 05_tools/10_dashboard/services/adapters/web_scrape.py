"""
web_scrape.py — 通用网页抓取适配器

工具：web_crawler skill → agent-browser（Chrome DOM提取）

用途：抓取非平台特定网页内容（文章、博客、新闻等）
"""
import asyncio, json, logging
from services.adapters import ScrapeAdapter

logger = logging.getLogger("dashboard.scrape.web")


class WebScrapeAdapter(ScrapeAdapter):
    platform = "web"
    adapter_name = "web_scrape"

    async def collect_item(self, target: str, depth: str = "light",
                           tool_level: int = 2) -> dict:
        """抓取单条网页内容"""
        ok, data, tool = await self._try_tools(tool_level, [
            ("web_crawler", lambda: self._web_crawl(target)),
            ("agent-browser", lambda: self._browser_extract(target)),
        ])
        if ok and data:
            return self._to_schema(data)
        return {"error": "所有工具均无法抓取"}

    async def collect_user(self, user_id: str, limit: int = 20) -> list[dict]:
        return []

    async def collect_comments(self, item_id: str, limit: int = 20) -> list[dict]:
        return []

    async def collect_search(self, keyword: str, limit: int = 20) -> list[dict]:
        return []

    # ── web_crawler 调用 ──

    async def _web_crawl(self, url: str):
        """通过 web_crawler skill 爬取网页"""
        try:
            from services.crawl_service import crawl_url
            result = await crawl_url(url)
            return result
        except ImportError:
            logger.warning("  ⚠️ web_crawler skill 未加载，尝试 Crawl4AI 直调")
            return await self._crawl4ai_fallback(url)
        except Exception as e:
            logger.warning(f"  ⚠️ web_crawler 失败: {e}")
            return await self._crawl4ai_fallback(url)

    async def _crawl4ai_fallback(self, url: str) -> dict:
        """通过 Crawl4AI 直接爬取"""
        try:
            import subprocess, json
            # 使用 crawl4ai 命令行
            proc = await asyncio.create_subprocess_exec(
                *["python3", "-m", "crawl4ai", url, "--json"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            if stdout:
                result = json.loads(stdout.decode().strip())
                return result
        except Exception as e:
            logger.warning(f"  ⚠️ Crawl4AI 降级失败: {e}")
        return None

    async def _browser_extract(self, url: str) -> dict:
        """通过 Chrome 浏览器提取页面内容"""
        from services.adapters.browser_helpers import page_extract
        selectors = ["article", "main", ".content", ".post-content", ".article-content",
                     "[class*='content']", "body"]
        data = await page_extract(url, selectors, headless=True)
        if data:
            # 提取最长文本块作为正文
            texts = []
            for sel, items in data.items():
                for t in items:
                    if len(t) > 100:
                        texts.append(t)
            content = max(texts, key=len) if texts else list(data.values())[0][0] if any(data.values()) else ""
            return {
                "url": url,
                "title": (await self._browser_title(url)).get("title", ""),
                "content": content,
            }
        return {}

    async def _browser_title(self, url: str) -> dict:
        """提取页面标题"""
        from services.adapters.browser_helpers import page_evaluate
        js = "() => ({title: document.title})"
        return await page_evaluate(url, js, headless=True)

    # ── 统一 Schema ──

    def _to_schema(self, raw: dict) -> dict:
        return {
            "platform": "web",
            "item_id": raw.get("url", ""),
            "url": raw.get("url", ""),
            "title": raw.get("title", ""),
            "author_name": raw.get("author", raw.get("site_name", "")),
            "author_id": "",
            "published_at": raw.get("published_at", raw.get("date", "")),
            "text_content": raw.get("content", raw.get("text", raw.get("markdown", ""))),
            "tags": raw.get("tags", []),
            "stats": {},
            "extra": {},
            "media": [],
            "comments": [],
        }

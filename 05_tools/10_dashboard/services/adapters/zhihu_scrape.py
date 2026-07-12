"""
zhihu_scrape.py — 知乎抓取适配器

工具：OpenCLI zhihu → agent-browser（Chrome DOM提取）
"""
import asyncio, json, logging, re
from services.adapters import ScrapeAdapter

logger = logging.getLogger("dashboard.scrape.zhihu")


class ZhihuScrapeAdapter(ScrapeAdapter):
    platform = "zhihu"
    adapter_name = "zhihu_scrape"

    async def collect_user(self, user_id: str, limit: int = 20) -> list[dict]:
        """抓取指定用户的回答/文章列表"""
        results = []
        ok, data, tool = await self._try_tools(2, [
            ("opencli", lambda: self._opencli_user_answers(user_id, limit)),
        ])
        if ok and data:
            for item in (data if isinstance(data, list) else [data]):
                results.append(self._to_schema(item))
        return results

    async def collect_item(self, target: str, depth: str = "light",
                           tool_level: int = 2) -> dict:
        """抓取单条回答/文章详情"""
        item_id = self._extract_id(target)
        if not item_id:
            return {"error": f"无法解析内容ID: {target}"}
        ok, data, tool = await self._try_tools(tool_level, [
            ("opencli", lambda: self._opencli_answer(item_id)),
        ])
        if ok and data:
            return self._to_schema(data)
        return {"error": "所有工具均无法抓取"}

    async def collect_comments(self, item_id: str, limit: int = 20) -> list[dict]:
        return []

    async def collect_search(self, keyword: str, limit: int = 20) -> list[dict]:
        """搜索问题/回答"""
        results = []
        ok, data, tool = await self._try_tools(2, [
            ("opencli", lambda: self._opencli_search(keyword, limit)),
        ])
        if ok and data:
            for item in (data if isinstance(data, list) else [data]):
                results.append(self._to_schema(item))
        return results

    # ── OpenCLI 调用 ──

    async def _opencli_user_answers(self, user_id: str, limit: int):
        return await self._run_opencli([
            "zhihu", "user-answers", user_id,
            "--limit", str(limit), "-f", "json"
        ])

    async def _opencli_answer(self, answer_id: str):
        return await self._run_opencli([
            "zhihu", "answer", answer_id, "-f", "json"
        ])

    async def _opencli_search(self, keyword: str, limit: int):
        return await self._run_opencli([
            "zhihu", "search", keyword,
            "--limit", str(limit), "-f", "json"
        ])

    # ── URL 解析 ──

    def _extract_id(self, target: str) -> str:
        """从 URL 提取 answer_id / question_id"""
        # zhihu.com/answer/{id}
        m = re.search(r'zhihu\.com/answer/(\d+)', target)
        if m:
            return m.group(1)
        # zhihu.com/question/{id}/answer/{id}
        m = re.search(r'zhihu\.com/question/\d+/answer/(\d+)', target)
        if m:
            return m.group(1)
        # 纯数字
        if target.isdigit():
            return target
        return ""

    # ── 统一 Schema ──

    def _to_schema(self, raw: dict) -> dict:
        return {
            "platform": "zhihu",
            "item_id": raw.get("answer_id", raw.get("id", raw.get("url_token", ""))),
            "url": raw.get("url", ""),
            "title": raw.get("title", raw.get("question_title", raw.get("excerpt", ""))),
            "author_name": raw.get("author", raw.get("user_name", raw.get("name", ""))),
            "author_id": raw.get("user_id", raw.get("author_id", "")),
            "published_at": raw.get("created_time", raw.get("created_at", raw.get("updated_time", ""))),
            "text_content": raw.get("content", raw.get("excerpt", "")),
            "tags": raw.get("topics", []),
            "stats": {
                "likes": raw.get("voteup_count", raw.get("likes", 0)),
                "comments": raw.get("comment_count", raw.get("comments", 0)),
                "shares": 0,
                "views": 0,
            },
            "extra": {
                "question_id": raw.get("question_id", ""),
                "answer_id": raw.get("answer_id", ""),
            },
            "media": [],
            "comments": [],
        }

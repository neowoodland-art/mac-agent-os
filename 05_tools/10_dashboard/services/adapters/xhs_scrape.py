"""
xhs_scrape.py — 小红书抓取适配器

工具：OpenCLI xiaohongshu → agent-browser
"""
import asyncio, json, logging
from services.adapters import ScrapeAdapter

logger = logging.getLogger("dashboard.scrape.xhs")


class XhsScrapeAdapter(ScrapeAdapter):
    platform = "xiaohongshu"
    adapter_name = "xhs_scrape"

    async def collect_user(self, user_id: str, limit: int = 20) -> list[dict]:
        """抓取指定用户的笔记列表"""
        results = []
        ok, data, tool = await self._try_tools(2, [
            ("opencli", lambda: self._opencli_user_notes(user_id, limit)),
        ])
        if ok and data:
            for item in (data if isinstance(data, list) else [data]):
                results.append(self._to_schema(item))
        return results

    async def collect_item(self, target: str, depth: str = "light",
                           tool_level: int = 2) -> dict:
        """抓取单篇笔记详情"""
        note_id = self._extract_note_id(target)
        if not note_id:
            return {"error": f"无法解析笔记ID: {target}"}
        ok, data, tool = await self._try_tools(tool_level, [
            ("opencli", lambda: self._opencli_note(note_id)),
        ])
        if ok and data:
            return self._to_schema(data)
        return {"error": "所有工具均无法抓取"}

    async def collect_comments(self, item_id: str, limit: int = 20) -> list[dict]:
        """抓取笔记评论"""
        ok, data, tool = await self._try_tools(2, [
            ("opencli", lambda: self._opencli_comments(item_id, limit)),
        ])
        if ok and data:
            return [
                {"author": c.get("nickname", ""), "text": c.get("text", ""),
                 "likes": c.get("likes", 0)}
                for c in (data if isinstance(data, list) else [data])
            ]
        return []

    async def collect_search(self, keyword: str, limit: int = 20) -> list[dict]:
        """搜索笔记"""
        results = []
        ok, data, tool = await self._try_tools(2, [
            ("opencli", lambda: self._opencli_search(keyword, limit)),
        ])
        if ok and data:
            for item in (data if isinstance(data, list) else [data]):
                results.append(self._to_schema(item))
        return results

    # ── OpenCLI 调用 ──

    async def _opencli_user_notes(self, user_id: str, limit: int):
        return await self._run_opencli([
            "xiaohongshu", "user", user_id,
            "--limit", str(limit), "-f", "json"
        ])

    async def _opencli_note(self, note_id: str):
        return await self._run_opencli([
            "xiaohongshu", "note", note_id, "-f", "json"
        ])

    async def _opencli_comments(self, note_id: str, limit: int):
        return await self._run_opencli([
            "xiaohongshu", "comments", note_id,
            "--limit", str(limit), "-f", "json"
        ])

    async def _opencli_search(self, keyword: str, limit: int):
        return await self._run_opencli([
            "xiaohongshu", "search", keyword,
            "--limit", str(limit), "-f", "json"
        ])

    # ── URL 解析 ──

    def _extract_note_id(self, target: str) -> str:
        import re
        m = re.search(r'xiaohongshu\.com/explore/([a-f0-9]+)', target)
        if m:
            return m.group(1)
        m = re.search(r'xiaohongshu\.com/discovery/item/([a-f0-9]+)', target)
        if m:
            return m.group(1)
        if target.isalnum() and len(target) >= 10:
            return target
        return ""

    # ── 统一 Schema ──

    def _to_schema(self, raw: dict) -> dict:
        return {
            "platform": "xiaohongshu",
            "item_id": raw.get("note_id", raw.get("id", "")),
            "url": raw.get("url", f"https://www.xiaohongshu.com/explore/{raw.get('note_id', '')}"),
            "title": raw.get("title", ""),
            "author_name": raw.get("author", raw.get("nickname", raw.get("user_name", ""))),
            "author_id": raw.get("user_id", raw.get("author_id", "")),
            "published_at": raw.get("create_time", raw.get("time", "")),
            "text_content": raw.get("desc", raw.get("description", raw.get("text", ""))),
            "tags": raw.get("tags", []),
            "stats": {
                "likes": raw.get("likes", raw.get("liked_count", 0)),
                "comments": raw.get("comments", raw.get("comment_count", 0)),
                "shares": raw.get("shares", raw.get("share_count", 0)),
                "views": raw.get("views", 0),
            },
            "extra": {
                "note_id": raw.get("note_id", ""),
                "user_id": raw.get("user_id", ""),
            },
            "media": [
                {"type": "image", "url": u} for u in (raw.get("images") or [])
            ] if raw.get("images") else [],
            "comments": [],
        }

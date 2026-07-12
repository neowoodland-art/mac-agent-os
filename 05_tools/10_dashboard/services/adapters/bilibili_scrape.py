"""
bilibili_scrape.py — B站抓取适配器

工具：OpenCLI bilibili → agent-browser（Chrome DOM提取）
"""
import asyncio, json, logging
from services.adapters import ScrapeAdapter

logger = logging.getLogger("dashboard.scrape.bilibili")


class BilibiliScrapeAdapter(ScrapeAdapter):
    platform = "bilibili"
    adapter_name = "bilibili_scrape"

    async def collect_user(self, user_id: str, limit: int = 20) -> list[dict]:
        """抓取指定 UP 主的视频列表"""
        results = []
        ok, data, tool = await self._try_tools(2, [
            ("opencli", lambda: self._opencli_user_videos(user_id, limit)),
        ])
        if ok and data:
            for item in (data if isinstance(data, list) else [data]):
                results.append(self._to_schema(item))
        return results

    async def collect_item(self, target: str, depth: str = "light",
                           tool_level: int = 2) -> dict:
        """抓取单条视频详情"""
        bvid = self._extract_bvid(target)
        if not bvid:
            return {"error": f"无法解析 BVID: {target}"}
        ok, data, tool = await self._try_tools(tool_level, [
            ("opencli", lambda: self._opencli_video(bvid)),
        ])
        if ok and data:
            return self._to_schema(data)
        return {"error": "所有工具均无法抓取"}

    async def collect_comments(self, item_id: str, limit: int = 20) -> list[dict]:
        """抓取视频评论"""
        ok, data, tool = await self._try_tools(2, [
            ("opencli", lambda: self._opencli_comments(item_id, limit)),
        ])
        if ok and data:
            return [
                {"author": c.get("nickname", c.get("user", "")),
                 "text": c.get("text", c.get("content", "")),
                 "likes": c.get("likes", c.get("like_count", 0))}
                for c in (data if isinstance(data, list) else [data])
            ]
        return []

    async def collect_search(self, keyword: str, limit: int = 20) -> list[dict]:
        """搜索视频"""
        results = []
        ok, data, tool = await self._try_tools(2, [
            ("opencli", lambda: self._opencli_search(keyword, limit)),
        ])
        if ok and data:
            for item in (data if isinstance(data, list) else [data]):
                results.append(self._to_schema(item))
        return results

    # ── OpenCLI 调用 ──

    async def _opencli_user_videos(self, mid: str, limit: int):
        return await self._run_opencli([
            "bilibili", "user-videos", mid,
            "--limit", str(limit), "-f", "json"
        ])

    async def _opencli_video(self, bvid: str):
        return await self._run_opencli([
            "bilibili", "video", bvid, "-f", "json"
        ])

    async def _opencli_comments(self, bvid: str, limit: int):
        return await self._run_opencli([
            "bilibili", "comments", bvid,
            "--limit", str(limit), "-f", "json"
        ])

    async def _opencli_search(self, keyword: str, limit: int):
        return await self._run_opencli([
            "bilibili", "search", keyword,
            "--limit", str(limit), "-f", "json"
        ])

    # ── URL 解析 ──

    def _extract_bvid(self, target: str) -> str:
        """从 URL 或文本中提取 BVID"""
        import re
        # bilibili.com/video/BVxxx
        m = re.search(r'bilibili\.com/video/([a-zA-Z0-9]+)', target)
        if m:
            return m.group(1)
        # 纯 BVID（BV 开头）
        if target.startswith("BV") and len(target) >= 10:
            return target
        return ""

    # ── 统一 Schema ──

    def _to_schema(self, raw: dict) -> dict:
        return {
            "platform": "bilibili",
            "item_id": raw.get("bvid", raw.get("aid", "")),
            "url": raw.get("url", f"https://www.bilibili.com/video/{raw.get('bvid', '')}"),
            "title": raw.get("title", ""),
            "author_name": raw.get("author", raw.get("up", raw.get("owner_name", ""))),
            "author_id": raw.get("mid", raw.get("owner_mid", "")),
            "published_at": raw.get("pubdate", raw.get("pub_time", raw.get("created", ""))),
            "text_content": raw.get("desc", raw.get("description", "")),
            "tags": raw.get("tags", []),
            "stats": {
                "likes": raw.get("likes", raw.get("stat_like", raw.get("like_count", 0))),
                "comments": raw.get("comments", raw.get("stat_reply", raw.get("reply_count", 0))),
                "shares": raw.get("shares", raw.get("stat_share", raw.get("share_count", 0))),
                "views": raw.get("views", raw.get("stat_view", raw.get("play_count", 0))),
            },
            "extra": {
                "bvid": raw.get("bvid", ""),
                "mid": raw.get("mid", raw.get("owner_mid", "")),
                "duration": raw.get("duration", raw.get("v_duration", 0)),
            },
            "media": [{
                "type": "video",
                "url": raw.get("play_url", ""),
                "duration": raw.get("duration", 0),
            }] if raw.get("play_url") else [],
            "comments": [],
        }

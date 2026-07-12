"""
douyin_scrape.py — 抖音抓取适配器

工具：OpenCLI douyin → agent-browser（Chrome DOM提取）
"""
import asyncio, json, logging
from services.adapters import ScrapeAdapter

logger = logging.getLogger("dashboard.scrape.douyin")


class DouyinScrapeAdapter(ScrapeAdapter):
    platform = "douyin"
    adapter_name = "douyin_scrape"

    # ── 公开接口 ──

    async def collect_user(self, user_id: str, limit: int = 20) -> list[dict]:
        """抓取指定用户的视频列表（含评论）"""
        results = []
        ok, data, tool = await self._try_tools(2, [
            ("opencli", lambda: self._opencli_user_videos(user_id, limit)),
            ("agent-browser", lambda: self._browser_user_profile(user_id, limit)),
        ])
        if ok and data:
            for item in data:
                results.append(self._to_schema(item))
        return results

    async def collect_item(self, target: str, depth: str = "light",
                           tool_level: int = 2) -> dict:
        """抓取单条视频详情"""
        aweme_id = self._extract_aweme_id(target)
        if not aweme_id:
            return {"error": f"无法解析视频ID: {target}"}

        ok, data, tool = await self._try_tools(tool_level, [
            ("opencli", lambda: self._opencli_stats(aweme_id)),
            ("agent-browser", lambda: self._browser_video_page(aweme_id)),
        ])
        if ok and data:
            return self._to_schema(data)
        return {"error": "所有工具均无法抓取"}

    async def collect_comments(self, item_id: str, limit: int = 20) -> list[dict]:
        """抓取评论区（需先有作者 sec_uid，目前返回空表）"""
        return []

    async def collect_search(self, keyword: str, limit: int = 20) -> list[dict]:
        """搜索视频"""
        results = []
        ok, data, tool = await self._try_tools(2, [
            ("opencli", lambda: self._opencli_search(keyword, limit)),
        ])
        if ok and data:
            for item in data:
                results.append(self._to_schema(item))
        return results

    # ── OpenCLI 调用 ──

    async def _opencli_user_videos(self, sec_uid: str, limit: int):
        data = await self._run_opencli([
            "douyin", "user-videos", sec_uid,
            "--limit", str(limit), "--with_comments", "true",
            "-f", "json"
        ])
        # OpenCLI JSON 输出直接是数组
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        # YAML 格式回退
        if isinstance(data, list) and len(data) > 0 and "aweme_id" in data[0]:
            return data
        return []

    async def _opencli_stats(self, aweme_id: str):
        try:
            return await self._run_opencli([
                "douyin", "stats", aweme_id, "-f", "json"
            ])
        except Exception as e:
            logger.warning(f"  ⚠️ douyin stats 失败: {e}")
            return None

    async def _opencli_search(self, keyword: str, limit: int):
        # OpenCLI 暂无抖音搜索命令，返回空
        return []

    # ── agent-browser 降级 ──

    async def _browser_video_page(self, aweme_id: str):
        """通过 Chrome 打开视频页提取数据"""
        from services.adapters.browser_helpers import page_evaluate
        url = f"https://www.douyin.com/video/{aweme_id}"
        js = """() => {
            const body = document.body.innerText || '';
            const title = document.title || '';
            const url = window.location.href;
            const uidM = body.match(/抖音号[：:]\\s*(\\S+)/);
            const nickM = body.match(/@(\\S+)/);
            function extractNum(label) {
                var m = body.match(new RegExp('(\\\\d+(?:\\\\.\\\\d+)?[万w]?)\\\\s*' + label));
                if (m) return m[1];
                m = body.match(new RegExp(label + '\\\\s*(\\\\d+(?:\\\\.\\\\d+)?[万w]?)'));
                return m ? m[1] : null;
            }
            return {
                aweme_id: '"' + url.match(/\\/video\\/(\\d+)/)?.[1] + '"',
                title: title,
                author_nickname: nickM ? nickM[1] : '',
                douyin_id: uidM ? uidM[1] : '',
                digg_count: extractNum('获赞') || '',
                fans: extractNum('粉丝') || '',
                following: extractNum('关注') || '',
            };
        }"""
        data = await page_evaluate(url, js)
        return data

    async def _browser_user_profile(self, user_id: str, limit: int):
        return []

    # ── URL 解析 ──

    def _extract_aweme_id(self, target: str) -> str:
        """从 URL 或文本中提取 aweme_id"""
        import re
        # 视频页: douyin.com/video/{id}
        m = re.search(r'douyin\.com/video/(\d+)', target)
        if m:
            return m.group(1)
        # iesdouyin.com/share/video/{id}
        m = re.search(r'iesdouyin\.com/share/video/(\d+)', target)
        if m:
            return m.group(1)
        # 纯数字
        if target.isdigit():
            return target
        return ""

    # ── 统一 Schema 转换 ──

    def _to_schema(self, raw: dict) -> dict:
        """OpenCLI 原始数据 → 统一 Schema"""
        return {
            "platform": "douyin",
            "item_id": raw.get("aweme_id", ""),
            "url": f"https://www.douyin.com/video/{raw.get('aweme_id', '')}",
            "title": raw.get("title", ""),
            "author_name": raw.get("author_nickname", raw.get("nickname", "")),
            "author_id": raw.get("author_id", raw.get("douyin_id", "")),
            "published_at": raw.get("create_time", raw.get("published_at", "")),
            "text_content": raw.get("title", ""),
            "tags": [],
            "stats": {
                "likes": raw.get("digg_count", raw.get("likes", 0)),
                "comments": raw.get("comment_count", 0),
                "shares": raw.get("share_count", 0),
                "views": raw.get("play_count", raw.get("views", 0)),
            },
            "extra": {
                "sec_uid": raw.get("sec_uid", ""),
                "duration": raw.get("duration", 0),
                "status": raw.get("status", ""),
            },
            "media": [{
                "type": "video",
                "url": raw.get("play_url", ""),
                "duration": raw.get("duration", 0),
            }] if raw.get("play_url") else [],
            "comments": [
                {
                    "author": c.get("nickname", ""),
                    "text": c.get("text", ""),
                    "likes": c.get("digg_count", 0),
                }
                for c in (raw.get("top_comments") or [])
            ] if raw.get("top_comments") else [],
        }

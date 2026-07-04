"""
video_analyzer.py — 视频分析引擎（仅 Master 节点运行）

职责:
  - 通过浏览器打开视频 URL 提取标题/描述
  - 关键词匹配法判断行业分类
  - 从对应语料池选评论

设计: 每个 URL 启动一个临时无头浏览器，分析完成即关闭。
不经过 Camoufox，不保留身份状态。
"""

import asyncio
import logging
import random
from typing import Optional

logger = logging.getLogger("dashboard.video_analyzer")

# ── 行业关键词映射（与 mc/corpus.py 的 INDUSTRY_TAGS 保持一致）──
INDUSTRY_TAGS = {
    "health": ["医生","医院","药","健康","养生","中医","体检","症状",
               "治疗","康复","营养","饮食","锻炼","专家","疾病","病症",
               "胃镜","肠镜","肠胃","手术","护理","方子","药材","食疗",
               "养生","保健","肠胃镜","医保","体检报告","专家门诊"],
    "finance": ["股票","基金","理财","投资","经济","A股","财经","行情","股民"],
    "tech":    ["手机","数码","电脑","科技","AI","人工智能","评测","软件","芯片"],
    "food":    ["美食","做饭","菜谱","餐厅","好吃","探店","吃播","烹饪","菜肴"],
}

# ── 万能评论池（所有账号通用）──
UNIVERSAL_COMMENTS = {
    "praise": [
        "博主说得很对",
        "讲得不错，学到了",
        "分析得很到位",
        "说得太对了",
        "很实用的分享，谢谢博主",
        "讲得很清楚，一下就懂了",
        "受益匪浅，谢谢分享",
        "这个观点很新颖，学习了",
    ],
    "question": [
        "请问这个怎么学？",
        "大概需要多长时间？",
        "这个在哪里可以买到？",
        "有推荐的教程吗？",
    ],
    "empathy": [
        "太真实了",
        "说出了我的心声",
        "确实是这样，深有体会",
    ],
    "agree": [
        "同意博主的观点",
        "说得很好，支持",
    ],
}

# ── 行业评论池 ──
INDUSTRY_COMMENTS = {
    "health": {
        "praise": [
            "医生讲得很清楚，通俗易懂",
            "这个方子很实用，收藏了",
            "讲得很专业，学到了",
            "科普得很好，应该让更多人看到",
            "简单明了，受益匪浅",
            "这个知识点太重要了，感谢科普",
        ],
        "question": [
            "这个症状一般怎么处理？",
            "平时饮食有什么需要注意的？",
            "这个检查大概需要多久？",
        ],
        "empathy": [
            "健康真的太重要了",
            "身体是革命的本钱，感谢提醒",
        ],
    },
    "general": {  # 兜底
        "praise": UNIVERSAL_COMMENTS["praise"],
        "question": UNIVERSAL_COMMENTS["question"],
        "empathy": UNIVERSAL_COMMENTS["empathy"],
    },
}


class VideoContext:
    """视频分析结果"""
    def __init__(self, title: str = "", description: str = "",
                 url: str = "", industry: str = "general",
                 tags: list = None):
        self.title = title
        self.description = description
        self.url = url
        self.industry = industry
        self.tags = tags or []

    def to_dict(self):
        return {
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "industry": self.industry,
            "tags": self.tags,
        }


class VideoAnalyzer:
    """视频分析器：提取信息 → 行业分类 → 选评论"""

    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self._rate_limit = 0  # 分析间隔，避免被抖音反爬

    async def analyze_batch(self, urls: list[str],
                            account_industry: Optional[str] = None,
                            direction: str = "praise") -> dict[str, dict]:
        """批量分析视频URL（最多 max_concurrent 并发）
        
        Args:
            urls: 视频URL列表
            account_industry: 执行评论的账号所属行业（health/general）
            direction: 评论方向（praise/question/empathy/agree）
        
        Returns:
            {url: {title, description, industry, tags, comment}}
        """
        sem = asyncio.Semaphore(self.max_concurrent)
        results = {}

        async def _analyze_one(url: str):
            async with sem:
                context = await self._extract_context(url)
                context.industry = self._classify(context)
                context.comment = self._pick_comment(
                    context.industry, account_industry, direction
                )
                results[url] = context.to_dict()
                results[url]["comment"] = context.comment
                logger.info(f"  ✅ {url[:50]} → [{context.industry}] {context.comment[:30]}...")

        tasks = [asyncio.create_task(_analyze_one(url)) for url in urls]
        await asyncio.gather(*tasks, return_exceptions=True)

        # 失败兜底
        for url in urls:
            if url not in results:
                results[url] = {
                    "url": url, "title": "", "description": "",
                    "industry": "general", "tags": [],
                    "comment": self._random("praise"),
                }

        return results

    async def _extract_context(self, url: str) -> VideoContext:
        """通过无头浏览器提取视频信息"""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=20000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)

                title = await page.title()
                title = title.replace(" - 抖音", "").replace(" - 今日头条", "").strip()

                desc = ""
                meta = await page.query_selector('meta[name="description"]')
                if meta:
                    desc = await meta.get_attribute("content") or ""

                # 提取标签/话题
                tags = []
                tag_els = await page.query_selector_all('[data-e2e="search-topic"], .topic-link, a[href*="tag"]')
                for el in tag_els[:5]:
                    t = await el.inner_text()
                    if t.strip():
                        tags.append(t.strip())

                ctx = VideoContext(
                    title=title,
                    description=desc,
                    url=url,
                    tags=tags,
                )

                return ctx
            finally:
                await browser.close()

    def _classify(self, context: VideoContext) -> str:
        """关键词匹配法判断行业"""
        text = f"{context.title} {context.description} {' '.join(context.tags)}"
        for ind, tags in INDUSTRY_TAGS.items():
            for tag in tags:
                if tag in text:
                    logger.debug(f"  🏷️ 匹配行业 {ind}: 关键词='{tag}'")
                    return ind
        return "general"

    def _pick_comment(self, video_industry: str,
                      account_industry: Optional[str],
                      direction: str = "praise") -> str:
        """选评论:
        - 账号行业匹配视频行业 → 行业池
        - 不匹配 → 万能池
        - 无账号行业 → 万能池
        """
        # 账号行业匹配视频行业 → 行业池
        if account_industry and video_industry == account_industry:
            pool = INDUSTRY_COMMENTS.get(video_industry, {})
            comments = pool.get(direction, pool.get("praise", UNIVERSAL_COMMENTS["praise"]))
            return random.choice(comments)

        # 不匹配 → 万能池
        return self._random(direction)

    def _random(self, direction: str = "praise") -> str:
        pool = UNIVERSAL_COMMENTS.get(direction, UNIVERSAL_COMMENTS["praise"])
        return random.choice(pool)

"""
comment_workbench.py — 评论工作台 API（v3 角色化评论）

路由前缀: /api/comment-workbench
"""
import logging
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("dashboard.comment_workbench")

_THIS_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = _THIS_DIR.parent / "07_matrix" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

router = APIRouter(prefix="/api/comment-workbench", tags=["comment_workbench"])

ROLE_LABELS = {
    "sharer": "分享型", "questioner": "提问型", "sympathizer": "共情型",
    "skeptic": "质疑型", "sufferer": "患者型", "filler": "灌水型",
    "expert_ref": "推荐型", "answerer": "解答型",
}

DEFAULT_ROLES = {
    "filler": 0.30, "questioner": 0.17, "sharer": 0.17,
    "sympathizer": 0.13, "sufferer": 0.10, "skeptic": 0.07,
    "expert_ref": 0.06, "answerer": 0.12,
}


def _get_corpus_mgr():
    from mc.corpus import CorpusManager
    return CorpusManager()


@router.get("/roles")
def api_roles(platform: str = "douyin"):
    """获取可用角色列表及默认比例"""
    mgr = _get_corpus_mgr()
    roles_raw = mgr.get_roles(platform)
    result = []
    for role_id, info in roles_raw.items():
        label = ROLE_LABELS.get(role_id, role_id)
        default_pct = DEFAULT_ROLES.get(role_id, 0)
        result.append({
            "id": role_id,
            "label": label,
            "count": info["count"],
            "examples": info["examples"][:3],
            "default_pct": default_pct,
        })
    return {"roles": result}


@router.post("/generate")
def api_generate_comments(data: dict):
    """按角色生成评论

    Body:
        video_title: str          — 视频标题
        video_tags: [str]         — 视频标签（可选）
        platform: str             — 平台，默认 douyin
        role_distribution: dict   — 角色比例，空则用默认（比例模式）
        role_counts: dict         — 角色精确条数 {"filler": 2, ...}（数字模式，优先于比例）
        total: int                — 比例模式下生成多少条，默认 30
        ai_enhance: bool          — 是否 AI 改写
        long_ratio: float         — 长评占比 0~1
    """
    video_title = data.get("video_title", "")
    video_tags = data.get("video_tags", []) or []
    video_industry = data.get("video_industry") or None
    guide_points = data.get("guide_points", "") or ""
    content_type = data.get("content_type", "") or ""
    direction = data.get("direction", "auto")
    platform = data.get("platform", "douyin")
    role_dist = data.get("role_distribution", {}) or DEFAULT_ROLES
    role_counts = data.get("role_counts") or None
    total = data.get("total", 30)
    ai_enhance = data.get("ai_enhance", False)
    long_ratio = data.get("long_ratio", 0.0)
    guide_ratio = min(max(float(data.get("guide_ratio", 1.0)), 0.0), 1.0)  # 引导结合比例 0~1

    if not video_title:
        raise HTTPException(400, detail="video_title 必填")

    mgr = _get_corpus_mgr()

    # 行业：前端指定 > 自动识别 > None(通用)
    if video_industry:
        industry = video_industry
    else:
        industry = mgr._classify_video(video_title)
        if not industry:
            for tag in video_tags:
                industry = mgr._classify_video(tag)
                if industry:
                    break
    # 视频标签转为逗号字符串
    tags_str = ", ".join(video_tags) if isinstance(video_tags, list) else str(video_tags)
    logger.info("  📋 视频行业: %s | 内容类型: %s | 引导: %.30s", industry or "通用", content_type or "-", guide_points or "-")

    gen_kwargs = dict(
        platform=platform,
        video_title=video_title,
        video_industry=industry,
        guide_points=guide_points,
        content_type=content_type,
        video_tags=tags_str,
        ai_enhance=ai_enhance,
        long_ratio=long_ratio,
        guide_ratio=guide_ratio,
    )
    if role_counts:
        # 数字模式：精确按角色条数取，total 由后端自动求和
        comments = mgr.batch_get_comments_by_roles(
            role_counts=role_counts,
            **gen_kwargs,
        )
    else:
        comments = mgr.batch_get_comments_by_roles(
            role_distribution=role_dist,
            total=total,
            **gen_kwargs,
        )
    return {"comments": comments, "total": len(comments)}


@router.post("/generate-discussion")
def api_generate_discussion(data: dict):
    """多人讨论模式：一次生成完整讨论剧本（单次 AI 调用）→ turns 列表

    Body:
        video_title: str        — 视频标题
        topic: str              — 讨论主题（用户主导概念）
        guide_items: [str]|str  — 引导要素（多个推荐对象，每行一个）
        outline: str            — 剧本走向（自由文本，如"先质疑→过来人澄清→带出医生"）
        total: int              — 总条数（3~40，默认 15）
        bystander_ratio: float  — 路人打酱油占比（0~0.5，默认 0.2）
    """
    video_title = (data.get("video_title") or "").strip()
    topic = (data.get("topic") or "").strip()
    outline = (data.get("outline") or "").strip()
    guide_path = (data.get("guide_path") or "").strip()
    total = max(3, min(60, int(data.get("total", 15))))
    bystander_ratio = min(max(float(data.get("bystander_ratio", 0.2)), 0.0), 0.5)
    role_counts = data.get("role_counts") or {}
    if not isinstance(role_counts, dict):
        role_counts = {}
    long_comment_count = max(0, min(3, int(data.get("long_comment_count", 2))))
    guide_count = max(0, int(data.get("guide_count", 0)))  # 0 = 自动按 30%
    guide_raw = data.get("guide_items") or []
    if isinstance(guide_raw, str):
        guide_items = [l.strip() for l in guide_raw.split("\n") if l.strip()]
    else:
        guide_items = [str(g).strip() for g in guide_raw if str(g).strip()]

    if not video_title and not topic:
        raise HTTPException(400, detail="video_title 或 topic 至少填一个")

    from mc.corpus import AIGenerator
    ai = AIGenerator()
    if not ai.available:
        raise HTTPException(503, detail="AI 不可用（检查 config/ai.yaml 或 agent-local 配置）")

    import asyncio as _asyncio
    try:
        loop = _asyncio.get_event_loop()
    except RuntimeError:
        loop = _asyncio.new_event_loop()
    turns = loop.run_until_complete(ai.generate_discussion_script(
        video_title=video_title,
        topic=topic,
        guide_items=guide_items,
        outline=outline,
        total=total,
        bystander_ratio=bystander_ratio,
        guide_path=guide_path,
        role_counts=role_counts,
        long_comment_count=long_comment_count,
        guide_count=guide_count,
    ))
    logger.info("  💬 讨论剧本生成: %d 条 (主题=%s 要素=%d)", len(turns), topic[:20], len(guide_items))
    warning = ""
    # 期望条数：配比模式 = 配比总和；自由模式 = total
    expected = total
    if role_counts:
        try:
            expected = sum(int(v) for v in role_counts.values() if str(v).strip().isdigit())
        except Exception:
            expected = total
    if expected and len(turns) < expected:
        warning = f"AI 少输出 {expected - len(turns)} 条（要求 {expected}，实际 {len(turns)}），可重新生成或手动补"
    return {"status": "ok", "turns": turns, "total": len(turns), "requested": expected, "warning": warning}


@router.post("/extract-topic")
def api_extract_topic(data: dict):
    """从视频标题提炼「讨论主题」（简短核心词，供讨论模式作起点）

    Body: { video_title: str }
    """
    video_title = (data.get("video_title") or "").strip()
    if not video_title:
        raise HTTPException(400, detail="video_title 必填")

    from mc.corpus import AIGenerator
    ai = AIGenerator()
    if not ai.available:
        raise HTTPException(503, detail="AI 不可用（检查 config/ai.yaml 或 agent-local 配置）")

    import asyncio as _asyncio
    try:
        loop = _asyncio.get_event_loop()
    except RuntimeError:
        loop = _asyncio.new_event_loop()
    topic = loop.run_until_complete(ai.extract_topic(video_title))
    logger.info("  🎯 主题提炼: %s → %s", video_title[:24], topic)
    return {"status": "ok", "topic": topic}


@router.post("/generate-path")
def api_generate_path(data: dict):
    """生成「引导路径」：起点(主题) → 终点(引导要素)，步数自适应 max(3, 2+要素数) 封顶 6

    Body: { topic: str, guide_items: [str]|str, outline?: str }
    """
    topic = (data.get("topic") or "").strip()
    outline = (data.get("outline") or "").strip()
    if not topic:
        raise HTTPException(400, detail="topic 必填")
    guide_raw = data.get("guide_items") or []
    if isinstance(guide_raw, str):
        guide_items = [l.strip() for l in guide_raw.split("\n") if l.strip()]
    else:
        guide_items = [str(g).strip() for g in guide_raw if str(g).strip()]

    from mc.corpus import AIGenerator
    ai = AIGenerator()
    if not ai.available:
        raise HTTPException(503, detail="AI 不可用（检查 config/ai.yaml 或 agent-local 配置）")

    import asyncio as _asyncio
    try:
        loop = _asyncio.get_event_loop()
    except RuntimeError:
        loop = _asyncio.new_event_loop()
    path = loop.run_until_complete(ai.generate_guide_path(topic, guide_items, outline))
    steps = len([l for l in (path or "").split("\n") if l.strip()])
    logger.info("  🧭 引导路径: %s + %d 要素 → %d 步", topic[:16], len(guide_items), steps)
    return {"status": "ok", "path": path, "steps": steps}


@router.post("/parse-outline")
def api_parse_outline(data: dict):
    """把用户的自然语言想法拆解成结构化「讨论走向」（供讨论模式生成用）

    Body: { raw_idea: str }  — 用户原始描述（可能跳跃/口语）
    """
    raw_idea = (data.get("raw_idea") or "").strip()
    if not raw_idea:
        raise HTTPException(400, detail="raw_idea 必填")

    from mc.corpus import AIGenerator
    ai = AIGenerator()
    if not ai.available:
        raise HTTPException(503, detail="AI 不可用（检查 config/ai.yaml 或 agent-local 配置）")

    import asyncio as _asyncio
    try:
        loop = _asyncio.get_event_loop()
    except RuntimeError:
        loop = _asyncio.new_event_loop()
    outline = loop.run_until_complete(ai.parse_discussion_outline(raw_idea))
    logger.info("  🧭 走向拆解: %s → %d 字", raw_idea[:24], len(outline or ""))
    return {"status": "ok", "outline": outline}


@router.post("/save-comments")
def api_save_comments(data: dict):
    """将精选评论保存到语料库

    Body: {
        "comments": [{"text": "...", "role": "...", "category": "..."}],
        "platform": "douyin"
    }
    """
    comments = data.get("comments", [])
    platform = data.get("platform", "douyin")
    if not comments:
        raise HTTPException(400, detail="comments 必填")

    mgr = _get_corpus_mgr()
    saved = 0
    for c in comments:
        text = c.get("text", "").strip()
        role = c.get("role", "filler")
        cat = c.get("category", "") or "入库评论"
        if not text:
            continue
        # 入库到指定分类（不存在则自动创建）
        mgr.add_comment(cat, text, platform)
        saved += 1

    logger.info("  ✅ 入库 %d 条评论 → %s/%s", saved, platform, cat)
    return {"status": "ok", "saved": saved}

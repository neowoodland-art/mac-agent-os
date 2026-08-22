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

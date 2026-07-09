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
    "expert_ref": "推荐型",
}

DEFAULT_ROLES = {
    "filler": 0.30, "questioner": 0.17, "sharer": 0.17,
    "sympathizer": 0.13, "sufferer": 0.10, "skeptic": 0.07,
    "expert_ref": 0.06,
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
    """按角色比例生成评论

    Body:
        video_title: str          — 视频标题
        video_tags: [str]         — 视频标签（可选）
        platform: str             — 平台，默认 douyin
        role_distribution: dict   — 角色比例，空则用默认
        total: int                — 生成多少条，默认 30
        ai_enhance: bool          — 是否 AI 改写
        long_ratio: float         — 长评占比 0~1
    """
    video_title = data.get("video_title", "")
    platform = data.get("platform", "douyin")
    role_dist = data.get("role_distribution", {}) or DEFAULT_ROLES
    total = data.get("total", 30)
    ai_enhance = data.get("ai_enhance", False)
    long_ratio = data.get("long_ratio", 0.0)

    if not video_title:
        raise HTTPException(400, detail="video_title 必填")

    mgr = _get_corpus_mgr()
    comments = mgr.batch_get_comments_by_roles(
        role_distribution=role_dist,
        platform=platform,
        video_title=video_title,
        total=total,
        ai_enhance=ai_enhance,
        long_ratio=long_ratio,
    )
    return {"comments": comments, "total": len(comments)}

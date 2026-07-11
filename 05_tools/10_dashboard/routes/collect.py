"""
routes/collect.py — 采集系统 API 路由 v1

端点：
  POST /api/collect/run       — 执行采集
  POST /api/collect/resolve   — 批量解析 URL
  GET  /api/collect/result    — 异步任务结果查询
  GET  /api/collect/tasks     — 任务列表
  GET  /api/collect/items     — 内容列表
  GET  /api/collect/items/{id} — 单条详情
  GET  /api/collect/stats     — 采集统计
  POST /api/collect/sources   — 创建采集源
  GET  /api/collect/sources   — 采集源列表
  DELETE /api/collect/sources/{id} — 删除采集源
"""
import asyncio, json, logging
from fastapi import APIRouter, HTTPException
from services.collect_engine import CollectEngine

logger = logging.getLogger("dashboard.routes.collect")
router = APIRouter(prefix="/api/collect", tags=["collect"])

_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        _engine = CollectEngine()
    return _engine


@router.post("/run")
async def api_collect_run(data: dict = {}):
    """执行采集任务"""
    try:
        targets = data.get("targets", data.get("target", []))
        if isinstance(targets, str):
            targets = [targets]

        request = {
            "targets": targets,
            "platform": data.get("platform", "auto"),
            "depth": data.get("depth", "light"),
            "tool_level": data.get("tool_level", 2),
            "machine": data.get("machine", ""),
            "multi_machine": data.get("multi_machine", False),
            "async_mode": data.get("async_mode", False),
        }
        engine = _get_engine()
        result = await engine.run(request)
        return {"status": "ok", **result}
    except Exception as e:
        logger.exception("采集执行失败")
        return {"status": "error", "message": str(e)}


@router.post("/resolve")
async def api_collect_resolve(data: dict = {}):
    """批量解析 URL，不执行采集"""
    try:
        urls = data.get("urls", data.get("targets", []))
        if isinstance(urls, str):
            urls = [urls]
        engine = _get_engine()
        results = engine.resolve_urls(urls)
        # 解析短链
        for r in results:
            if r["type"] == "shortlink":
                aweme_id = engine._resolve_shortlink(r["input"])
                if aweme_id:
                    r["type"] = "video"
                    r["target_id"] = aweme_id
                    r["platform"] = "douyin"
                    r["status"] = "resolved"
                else:
                    r["status"] = "unresolved"
        return {"status": "ok", "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/result")
async def api_collect_result(run_id: str = ""):
    """查询异步任务结果"""
    if not run_id:
        return {"status": "error", "message": "run_id 必填"}
    engine = _get_engine()
    result = engine.get_async_result(run_id)
    if result is None:
        return {"status": "error", "message": f"任务 {run_id} 不存在"}
    return {"status": "ok", "data": result}


@router.get("/tasks")
async def api_collect_tasks(status: str = "", platform: str = "",
                            limit: int = 50):
    """任务列表"""
    engine = _get_engine()
    tasks = engine.db.list_tasks(
        status=status or None,
        platform=platform or None,
        limit=min(limit, 200)
    )
    return {"status": "ok", "data": tasks}


@router.get("/items")
async def api_collect_items(platform: str = "", author_id: str = "",
                            limit: int = 100):
    """内容列表"""
    engine = _get_engine()
    items = engine.db.list_items(
        platform=platform or None,
        author_id=author_id or None,
        limit=min(limit, 200)
    )
    return {"status": "ok", "data": items}


@router.get("/items/{item_id}")
async def api_collect_item_detail(item_id: int):
    """单条内容详情（含评论区）"""
    engine = _get_engine()
    item = engine.db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="内容不存在")
    comments = engine.db.get_comments(item_id)
    item["comments"] = comments
    return {"status": "ok", "data": item}


@router.get("/stats")
async def api_collect_stats():
    """采集统计"""
    engine = _get_engine()
    stats = engine.get_stats()
    return {"status": "ok", **stats}


@router.post("/sources")
async def api_collect_create_source(data: dict = {}):
    """创建采集源"""
    platform = data.get("platform", "")
    source_type = data.get("source_type", "")
    target = data.get("target", "")
    if not platform or not target:
        return {"status": "error", "message": "platform 和 target 必填"}
    engine = _get_engine()
    engine.db.upsert_source(
        platform=platform,
        source_type=source_type,
        target=target,
        display_name=data.get("display_name", ""),
        schedule=data.get("schedule", ""),
        depth=data.get("depth", "light"),
        tool_level=data.get("tool_level", 2),
    )
    return {"status": "ok", "message": "采集源已创建"}


@router.get("/sources")
async def api_collect_list_sources():
    """采集源列表"""
    engine = _get_engine()
    sources = engine.db.list_sources()
    return {"status": "ok", "data": sources}


@router.delete("/sources/{source_id}")
async def api_collect_delete_source(source_id: int):
    """删除采集源"""
    engine = _get_engine()
    engine.db.delete_source(source_id)
    return {"status": "ok", "message": "采集源已删除"}

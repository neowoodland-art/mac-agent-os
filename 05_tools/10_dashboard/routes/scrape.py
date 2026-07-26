"""
routes/scrape.py — 抓取系统 API 路由 v1

端点：
  POST /api/scrape/run       — 执行抓取
  POST /api/scrape/resolve   — 批量解析 URL
  GET  /api/scrape/result    — 异步任务结果查询
  GET  /api/scrape/tasks     — 任务列表
  GET  /api/scrape/items     — 内容列表
  GET  /api/scrape/items/{id} — 单条详情
  GET  /api/scrape/stats     — 抓取统计
  POST /api/scrape/sources   — 创建抓取源
  GET  /api/scrape/sources   — 抓取源列表
  DELETE /api/scrape/sources/{id} — 删除抓取源
"""
import asyncio, json, logging
from fastapi import APIRouter, HTTPException
from services.scrape_engine import ScrapeEngine

logger = logging.getLogger("dashboard.routes.scrape")
router = APIRouter(prefix="/api/scrape", tags=["scrape"])

_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        _engine = ScrapeEngine()
    return _engine


@router.post("/douyin-stats")
async def api_douyin_stats(data: dict = {}):
    """获取抖音视频详细统计数据（隔离于养号系统）"""
    from services.douyin_stats import get_video_data
    url = (data.get("url") or "").strip()
    if not url:
        return {"status": "error", "message": "url 必填"}
    result = await get_video_data(url)
    return {"status": "ok" if "error" not in result else "error", **result}


@router.post("/run")
async def api_scrape_run(data: dict = {}):
    """执行抓取任务"""
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
        logger.exception("抓取执行失败")
        return {"status": "error", "message": str(e)}


@router.post("/resolve")
async def api_scrape_resolve(data: dict = {}):
    """批量解析 URL，不执行抓取"""
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


@router.get("/title")
async def api_scrape_title(url: str = ""):
    """获取网页标题（扫码级轻量请求，供互动页导入用）"""
    if not url:
        return {"status": "ok", "title": ""}
    if not url.startswith("http"):
        url = "https://" + url
    try:
        import urllib.request, re
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read(65536).decode("utf-8", errors="replace")
        m = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        title = m.group(1).strip() if m else ""
        # 抖音特殊处理：去掉 " - 抖音" 后缀
        for suffix in [" - 抖音", " - 抖音视频", " - 快手", " - 小红书"]:
            if title.endswith(suffix):
                title = title[:-len(suffix)]
                break
        return {"status": "ok", "title": title}
    except Exception as e:
        return {"status": "error", "message": str(e), "title": ""}


@router.get("/result")
async def api_scrape_result(run_id: str = ""):
    """查询异步任务结果"""
    if not run_id:
        return {"status": "error", "message": "run_id 必填"}
    engine = _get_engine()
    result = engine.get_async_result(run_id)
    if result is None:
        return {"status": "error", "message": f"任务 {run_id} 不存在"}
    return {"status": "ok", "data": result}


@router.get("/tasks")
async def api_scrape_tasks(status: str = "", platform: str = "",
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
async def api_scrape_items(platform: str = "", author_id: str = "",
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
async def api_scrape_item_detail(item_id: int):
    """单条内容详情（含评论区）"""
    engine = _get_engine()
    item = engine.db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="内容不存在")
    comments = engine.db.get_comments(item_id)
    item["comments"] = comments
    return {"status": "ok", "data": item}


@router.get("/stats")
async def api_scrape_stats():
    """抓取统计"""
    engine = _get_engine()
    stats = engine.get_stats()
    return {"status": "ok", **stats}


@router.post("/sources")
async def api_scrape_create_source(data: dict = {}):
    """创建抓取源"""
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
    return {"status": "ok", "message": "抓取源已创建"}


@router.get("/sources")
async def api_scrape_list_sources():
    """抓取源列表"""
    engine = _get_engine()
    sources = engine.db.list_sources()
    return {"status": "ok", "data": sources}


@router.delete("/sources/{source_id}")
async def api_scrape_delete_source(source_id: int):
    """删除抓取源"""
    engine = _get_engine()
    engine.db.delete_source(source_id)
    return {"status": "ok", "message": "抓取源已删除"}

# ── 抖音追踪系统（隔离于养号） ──

import json as _js, os as _os, time as _time, subprocess as _sp
from pathlib import Path as _Path

_TRACKER_DB = _Path(_os.environ.get("AGENT_LOCAL",
    str(_Path.home() / "workbuddy-agent-os" / "agent-local"))) / "data" / "douyin_tracker.json"


def _load_tracker() -> list:
    if _TRACKER_DB.exists():
        try:
            return _js.loads(_TRACKER_DB.read_text())
        except:
            pass
    return []


def _save_tracker(items: list):
    _TRACKER_DB.parent.mkdir(parents=True, exist_ok=True)
    _TRACKER_DB.write_text(_js.dumps(items, ensure_ascii=False, indent=2))


def _clean_douyin_title(raw: str) -> str:
    """清洗抖音标题：去掉『2.07 复制打开抖音，看看【xxx的作品】』前缀"""
    t = raw.strip()
    # 去掉开头的数字+空格（如 "2.07 "）
    import re as _re
    t = _re.sub(r'^[\d.]+[\s]*', '', t)
    # 去掉 "复制打开抖音" 及其变体
    t = _re.sub(r'^复制打开抖音[，,。.]*\s*', '', t)
    t = _re.sub(r'^打开抖音[，,。.]*\s*', '', t)
    t = _re.sub(r'^看看[，,。.]*\s*', '', t)
    # 去掉【xxx的作品】前缀
    t = _re.sub(r'^【[^】]+的作品】', '', t)
    # 再次去掉可能残留的 "复制打开抖音"
    t = _re.sub(r'复制打开抖音', '', t)
    return t.strip() or raw[:60]


@router.post("/import-topics")
async def api_import_topics(data: dict = {}):
    """从 tyhtak API 导入视频列表（轻量化，不调用 ops）"""
    import urllib.request as _urq
    api_url = (data.get("api_url") or "").strip()
    if not api_url:
        return {"status": "error", "message": "api_url 必填"}
    page = int(data.get("page", 1))
    page_size = int(data.get("page_size", 100))
    try:
        full_url = f"{api_url}?page={page}&pageSize={page_size}"
        resp = _urq.urlopen(full_url, timeout=15)
        body = _js.loads(resp.read().decode())
    except Exception as e:
        return {"status": "error", "message": f"请求失败: {e}"}
    raw_items = body.get("data", {}).get("items", [])
    items = []
    for item in raw_items:
        url = (item.get("share_url") or "").strip()
        if not url:
            continue
        vid = str(item.get("id", ""))
        items.append({
            "id": vid,
            "url": url,
            "title": _clean_douyin_title(item.get("share_text", "")),
            "author": item.get("nickname", "") or item.get("name", ""),
            "created_at": item.get("created_at", ""),
        })
    return {"status": "ok", "items": items, "total": len(items)}


@router.post("/track-video")
async def api_track_video(data: dict = {}):
    """采集单条视频并加入跟踪"""
    from services.douyin_stats import get_video_data
    url = (data.get("url") or "").strip()
    if not url:
        return {"status": "error", "message": "url 必填"}
    stats = await get_video_data(url)
    if "error" in stats:
        return {"status": "error", "message": stats["error"]}
    # 生成唯一 ID
    item_id = f"dy_{stats.get('aweme_id','')}"
    record = {
        "id": item_id,
        "url": url,
        "title": stats.get("title", ""),
        "author": stats.get("author", ""),
        "stats": {
            "likes": stats.get("likes", 0),
            "comments": stats.get("comments", 0),
            "collects": stats.get("collects", 0),
            "shares": stats.get("shares", 0),
        },
        "comment_texts": stats.get("comment_texts", []),
        "collected_at": _time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    # 保存
    items = _load_tracker()
    # 去重（同 ID 替换）
    for i, it in enumerate(items):
        if it["id"] == item_id:
            items.pop(i)
            break
    items.insert(0, record)
    _save_tracker(items)
    return {"status": "ok", "item": record}


@router.get("/tracked-videos")
async def api_tracked_videos():
    """获取已跟踪的视频列表"""
    return {"status": "ok", "items": _load_tracker()}


@router.post("/delete-tracked/{item_id}")
async def api_delete_tracked(item_id: str):
    """删除单条跟踪视频"""
    items = _load_tracker()
    before = len(items)
    items = [it for it in items if it["id"] != item_id]
    if len(items) < before:
        _save_tracker(items)
        return {"status": "ok"}
    return {"status": "error", "message": "未找到"}


@router.post("/refresh-video/{item_id}")
async def api_refresh_video(item_id: str):
    """刷新单条跟踪视频的数据"""
    from services.douyin_stats import get_video_data
    items = _load_tracker()
    found = None
    for it in items:
        if it["id"] == item_id:
            found = it
            break
    if not found:
        return {"status": "error", "message": "未找到该视频"}
    stats = await get_video_data(found["url"])
    if "error" in stats:
        resp = {"status": "error", "message": stats["error"]}
        if stats.get("login_expired"):
            resp["login_expired"] = True
            resp["message"] = "⛔ 抖音登录已过期，请重新登录。点击顶部「📱 打开抖音登录」按钮"
        return resp
    # 保存旧数据（用于对比）
    if "stats" in found:
        found["prev_stats"] = found.get("stats")
        found["prev_collected_at"] = found.get("collected_at", "")
    found["stats"] = {
        "likes": stats.get("likes", 0),
        "comments": stats.get("comments", 0),
        "collects": stats.get("collects", 0),
        "shares": stats.get("shares", 0),
    }
    found["comment_texts"] = stats.get("comment_texts", [])
    found["collected_at"] = _time.strftime("%Y-%m-%d %H:%M:%S")
    _save_tracker(items)
    return {"status": "ok", "item": found}


@router.get("/chrome-status")
async def api_chrome_status():
    """检查采集 Chrome 是否可用（只检查 profile 目录，不检查 CDP 端口）"""
    CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    profile_ok = _os.path.exists("/tmp/chrome-douyin-profile/Default/Cookies")
    chrome_installed = _os.path.exists(CHROME)
    return {"status": "ok", "online": True, "chrome_installed": chrome_installed, "profile_ok": profile_ok}


@router.get("/check-login")
async def api_check_login():
    """检查抖音登录状态"""
    from services.mediacrawler_adapter import check_login_status
    try:
        result = await check_login_status()
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/open-login")
async def api_open_login():
    """在 Chrome 中打开抖音登录页"""
    from services.mediacrawler_adapter import open_login_page
    try:
        result = await open_login_page()
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

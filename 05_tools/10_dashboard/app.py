"""
系统监控面板 — FastAPI 后端

架构:
  插件式数据源架构。每个模块 (AVE / Matrix / guardd 等) 实现 DashboardPlugin 基类,
  在 plugins/ 目录下注册。Dashboard 自动扫描并加载所有插件, 统一暴露 API。

API:
  GET  /api/plugins              — 插件列表
  GET  /api/summary              — 总览统计
  GET  /api/productions          — 生产列表
  GET  /api/productions/{id}     — 生产详情
  GET  /api/assets               — 资产列表
  GET  /api/assets/search        — 高级资产搜索
  GET  /api/assets/tags          — 标签云
  GET  /api/assets/stats         — 素材库统计
  GET  /api/assets/disk          — 磁盘占用
  GET  /api/costs/breakdown      — 费用分析
  GET  /api/health               — 健康检查

用法:
  # 通过 AVE main.py (推荐, 自动处理 path)
  python main.py dashboard

  # 独立启动
  python run.py

  # 或直接 uvicorn
  uvicorn app:app --reload --port 9988
"""
import sys
import os
from pathlib import Path
from typing import Optional

# ── 添加 AVE scripts 目录到 sys.path ──────────────────────
# Dashboard 需要读取 AVE 的 DB, 因此需要能 import lib.dashboard
# 路径: 10_dashboard/ → ../09_ave/scripts/
_AVE_SCRIPTS = Path(__file__).resolve().parent.parent / "09_ave" / "scripts"
if str(_AVE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_AVE_SCRIPTS))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException

# ── 插件系统 ───────────────────────────────────────────────
from plugins.base import DashboardPlugin
from plugins.ave import AVEDashboardPlugin

# 注册所有插件
_PLUGINS: dict[str, DashboardPlugin] = {}
_AVAILABLE: dict[str, bool] = {}


def _register_plugins():
    """扫描并注册所有插件"""
    plugins_to_register = [
        AVEDashboardPlugin,
    ]

    for plugin_cls in plugins_to_register:
        try:
            instance = plugin_cls()
            name = instance.name
            _PLUGINS[name] = instance
            _AVAILABLE[name] = instance.is_available()
        except Exception as e:
            _PLUGINS[plugin_cls.name] = None
            _AVAILABLE[plugin_cls.name] = False
            print(f"  [dashboard] 插件 {plugin_cls.name} 加载失败: {e}")


# ── FastAPI App ────────────────────────────────────────────

app = FastAPI(
    title="系统监控面板",
    version="1.0.0",
    description="多模块生产监控 — AVE / Matrix / guardd (插件式架构)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 静态文件 ──────────────────────────────────────────────
_static_dir = Path(__file__).parent / "static"
_static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/")
def index():
    """前端页面"""
    index_path = _static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"error": "index.html not found"}


@app.on_event("startup")
async def startup():
    _register_plugins()


# ═══════════════════════════════════════════════════════════
# 插件 API
# ═══════════════════════════════════════════════════════════

@app.get("/api/plugins")
def api_plugins():
    """已注册的插件列表"""
    result = []
    plugins_sorted = sorted(
        [p for p in _PLUGINS.values() if p is not None],
        key=lambda p: p.order,
    )
    for p in plugins_sorted:
        result.append({
            "name": p.name,
            "label": p.label,
            "description": p.description,
            "available": _AVAILABLE.get(p.name, False),
            "links": p.get_sidebar_links(),
        })
    return {"plugins": result}


# ═══════════════════════════════════════════════════════════
# 总览 (从所有插件聚合)
# ═══════════════════════════════════════════════════════════

@app.get("/api/summary")
def api_summary():
    """总览统计 (所有插件)"""
    result = {}
    for name, plugin in _PLUGINS.items():
        if plugin is None or not _AVAILABLE.get(name, False):
            continue
        try:
            result[name] = plugin.get_summary()
        except Exception:
            result[name] = {"error": "unavailable"}
    return result


# ═══════════════════════════════════════════════════════════
# 生产列表
# ═══════════════════════════════════════════════════════════

@app.get("/api/productions")
def api_productions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    strategy: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """生产列表 (默认从 AVE 插件获取)"""
    plugin = _PLUGINS.get("ave")
    if plugin is None or not _AVAILABLE.get("ave", False):
        raise HTTPException(status_code=503, detail="AVE plugin unavailable")
    return plugin.get_productions(limit=limit, offset=offset,
                                   strategy=strategy, status=status)


@app.get("/api/productions/{production_id}")
def api_production_detail(production_id: int):
    """生产详情"""
    plugin = _PLUGINS.get("ave")
    if plugin is None or not _AVAILABLE.get("ave", False):
        raise HTTPException(status_code=503, detail="AVE plugin unavailable")
    result = plugin.get_production_detail(production_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Production not found")
    return result


# ═══════════════════════════════════════════════════════════
# 资产 (AVE 专有)
# ═══════════════════════════════════════════════════════════

ASSET_SEARCH_AVAILABLE = False
_asset_search = None
try:
    from asset_manager.tags import AssetSearch
    _asset_search = AssetSearch()
    ASSET_SEARCH_AVAILABLE = True
except ImportError:
    pass


@app.get("/api/assets")
def api_assets(
    type: Optional[str] = Query(None, alias="type"),
    tag: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """资产列表 (AVE 资产)"""
    plugin = _PLUGINS.get("ave")
    if plugin is None or not _AVAILABLE.get("ave", False):
        raise HTTPException(status_code=503, detail="AVE plugin unavailable")
    # 从 AVE 的 lib.dashboard 获取
    from lib.dashboard import get_assets as _get_assets
    return _get_assets(asset_type=type, tag=tag, limit=limit, offset=offset)


@app.get("/api/assets/search")
def api_assets_search(
    keyword: str = Query(""),
    asset_type: Optional[str] = Query(None, alias="type"),
    source: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    min_duration: float = Query(0.0),
    max_duration: float = Query(0.0),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """高级资产搜索"""
    if not ASSET_SEARCH_AVAILABLE or _asset_search is None:
        raise HTTPException(status_code=501, detail="asset_manager not installed")
    tags = [tag] if tag else None
    results = _asset_search.search(
        keyword=keyword,
        asset_type=asset_type,
        source=source,
        tags=tags,
        min_duration=min_duration,
        max_duration=max_duration,
        limit=limit,
        offset=offset,
    )
    return {"total": len(results), "results": results}


@app.get("/api/assets/tags")
def api_assets_tags():
    """标签云"""
    if not ASSET_SEARCH_AVAILABLE or _asset_search is None:
        raise HTTPException(status_code=501, detail="asset_manager not installed")
    return {"tags": _asset_search.tag_stats()}


@app.get("/api/assets/stats")
def api_assets_stats():
    """素材库统计"""
    if not ASSET_SEARCH_AVAILABLE:
        raise HTTPException(status_code=501, detail="asset_manager not installed")
    from asset_manager.index import AssetIndex
    idx = AssetIndex()
    return idx.summarize()


@app.get("/api/assets/disk")
def api_assets_disk():
    """磁盘占用"""
    if not ASSET_SEARCH_AVAILABLE:
        raise HTTPException(status_code=501, detail="asset_manager not installed")
    from asset_manager.cache import CacheManager
    cm = CacheManager()
    return cm.disk_usage()


# ═══════════════════════════════════════════════════════════
# 费用分析
# ═══════════════════════════════════════════════════════════

@app.get("/api/costs/breakdown")
def api_cost_breakdown():
    """按策略的费用统计"""
    plugin = _PLUGINS.get("ave")
    if plugin is None or not _AVAILABLE.get("ave", False):
        raise HTTPException(status_code=503, detail="AVE plugin unavailable")
    return plugin.get_cost_breakdown()


# ═══════════════════════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "plugins": {
            name: "available" if _AVAILABLE.get(name, False) else "unavailable"
            for name in _PLUGINS
        },
    }


# ── 直接运行 ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9988
    print(f"📊 系统监控面板 → http://localhost:{port}")
    print(f"   插件列表:  http://localhost:{port}/api/plugins")
    print(f"   总览:      http://localhost:{port}/api/summary")
    print(f"   生产列表:  http://localhost:{port}/api/productions")
    print(f"   资产列表:  http://localhost:{port}/api/assets")
    print(f"   文档:      http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)

"""
系统监控面板 — FastAPI 后端 (v2.0 联邦协同版)

架构:
  插件式数据源架构 + 联邦多机标签。
  每个数据点都标注来源机器 hostname，支持 ?plugin= 切换数据源。

联邦数据模型:
  - 本机数据 (agent-local/)   → 带 source_hostname 标注
  - 共享数据 (agent-sync/)    → 天然跨机器可用
  - 前端渲染时按 hostname 分组展示

API:
  GET  /api/plugins              — 本机插件列表
  GET  /api/summary              — 聚合总览 (每插件+每机器)
  GET  /api/productions          — 生产列表 (?plugin= 切换数据源)
  GET  /api/productions/{id}     — 生产详情
  GET  /api/assets               — 资产列表 (?plugin= 切换数据源)
  GET  /api/assets/search        — 高级资产搜索
  GET  /api/assets/tags          — 标签云
  GET  /api/assets/stats         — 素材库统计
  GET  /api/assets/disk          — 磁盘占用
  GET  /api/costs/breakdown      — 费用分析 (?plugin= 切换数据源)
  GET  /api/machines             — 联邦机器状态 (来自 guardd 插件)
  GET  /api/health               — 健康检查
"""
import sys, os, json
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

# ── 联邦身份 ───────────────────────────────────────────────
HOSTNAME = os.uname().nodename

# ── 添加 AVE scripts 目录到 sys.path ──────────────────────
_AVE_SCRIPTS = Path(__file__).resolve().parent.parent / "09_ave" / "scripts"
if str(_AVE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_AVE_SCRIPTS))

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from plugins.base import DashboardPlugin
from plugins.ave import AVEDashboardPlugin
from plugins.guardd import GuarddPlugin

# ── 联邦路径 ───────────────────────────────────────────────
_CROSS_MACHINE_DIR = Path(__file__).resolve().parent.parent.parent / "04_memory" / "cross_machine"

_PLUGINS: dict[str, DashboardPlugin] = {}
_AVAILABLE: dict[str, bool] = {}

def _register_plugins():
    """注册所有数据源插件"""
    for plugin_cls in [AVEDashboardPlugin, GuarddPlugin]:
        try:
            inst = plugin_cls()
            _PLUGINS[inst.name] = inst
            _AVAILABLE[inst.name] = inst.is_available()
        except Exception as e:
            _PLUGINS[plugin_cls.name] = None
            _AVAILABLE[plugin_cls.name] = False
            print(f"  [dashboard] 插件 {plugin_cls.name} 加载失败: {e}")

def _get_plugin(name: str) -> DashboardPlugin:
    """获取插件实例，失败抛 503"""
    p = _PLUGINS.get(name)
    if p is None or not _AVAILABLE.get(name, False):
        raise HTTPException(503, detail=f"插件 {name} 不可用")
    return p

# ── FastAPI App ────────────────────────────────────────────
app = FastAPI(title="系统监控面板", version="2.0.0",
              description="联邦协同监控 — AVE / guardd (多机数据源)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

_static_dir = Path(__file__).parent / "static"
_static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

@app.get("/")
def index():
    index_path = _static_dir / "index.html"
    return FileResponse(str(index_path)) if index_path.exists() else {"error": "index.html not found"}

@app.on_event("startup")
async def startup():
    _register_plugins()

# ═══════════════════════════════════════════════════════════
# 联邦基础 API
# ═══════════════════════════════════════════════════════════

@app.get("/api/plugins")
def api_plugins():
    """本机已注册且可用的数据源插件列表"""
    result = []
    for p in sorted([p for p in _PLUGINS.values() if p], key=lambda p: p.order):
        result.append({
            "name": p.name, "label": p.label,
            "description": p.description,
            "available": _AVAILABLE.get(p.name, False),
            "links": p.get_sidebar_links(),
            "source_hostname": HOSTNAME,
        })
    return {"plugins": result, "source_hostname": HOSTNAME}

@app.get("/api/summary")
def api_summary():
    """聚合总览：每个可用的插件返回摘要，标注数据来源机器"""
    result = {"_meta": {"source_hostname": HOSTNAME, "generated_at": datetime.now(timezone.utc).isoformat()}}
    for name, plugin in _PLUGINS.items():
        if plugin is None or not _AVAILABLE.get(name, False):
            continue
        try:
            data = plugin.get_summary()
            if isinstance(data, dict):
                data["_source_hostname"] = HOSTNAME
            result[name] = data
        except Exception:
            result[name] = {"error": "unavailable", "_source_hostname": HOSTNAME}
    return result

# ═══════════════════════════════════════════════════════════
# 生产列表 (可切换插件)
# ═══════════════════════════════════════════════════════════

@app.get("/api/productions")
def api_productions(
    plugin: str = Query("ave", description="数据源插件名"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    strategy: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """生产列表，支持 ?plugin= 切换数据源"""
    p = _get_plugin(plugin)
    data = p.get_productions(limit=limit, offset=offset, strategy=strategy, status=status)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "_source_hostname" not in item:
                item["_source_hostname"] = HOSTNAME
    return {"data": data, "source_hostname": HOSTNAME, "plugin": plugin}

@app.get("/api/productions/{production_id}")
def api_production_detail(
    production_id: int,
    plugin: str = Query("ave", description="数据源插件名"),
):
    """生产详情，支持 ?plugin= 切换"""
    p = _get_plugin(plugin)
    result = p.get_production_detail(production_id)
    if result is None:
        raise HTTPException(404, detail="Not found")
    if isinstance(result, dict) and "_source_hostname" not in result:
        result["_source_hostname"] = HOSTNAME
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
    plugin: str = Query("ave", description="数据源插件名"),
    type: Optional[str] = Query(None, alias="type"),
    tag: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """资产列表，标注数据来源"""
    p = _get_plugin(plugin)
    from lib.dashboard import get_assets as _get_assets
    data = _get_assets(asset_type=type, tag=tag, limit=limit, offset=offset)
    if isinstance(data, dict):
        data["_source_hostname"] = HOSTNAME
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "_source_hostname" not in item:
                item["_source_hostname"] = HOSTNAME
    return {"data": data, "source_hostname": HOSTNAME, "plugin": plugin}

@app.get("/api/assets/search")
def api_assets_search(
    plugin: str = Query("ave", description="数据源插件名"),
    keyword: str = Query(""),
    asset_type: Optional[str] = Query(None, alias="type"),
    source: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    min_duration: float = Query(0.0), max_duration: float = Query(0.0),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
):
    if not ASSET_SEARCH_AVAILABLE or _asset_search is None:
        raise HTTPException(501, detail="asset_manager not installed")
    tags = [tag] if tag else None
    results = _asset_search.search(keyword=keyword, asset_type=asset_type,
        source=source, tags=tags, min_duration=min_duration,
        max_duration=max_duration, limit=limit, offset=offset)
    return {"total": len(results), "results": results, "source_hostname": HOSTNAME, "plugin": plugin}

@app.get("/api/assets/tags")
def api_assets_tags():
    if not ASSET_SEARCH_AVAILABLE:
        raise HTTPException(501, detail="asset_manager not installed")
    return {"tags": _asset_search.tag_stats(), "source_hostname": HOSTNAME}

@app.get("/api/assets/stats")
def api_assets_stats():
    if not ASSET_SEARCH_AVAILABLE:
        raise HTTPException(501, detail="asset_manager not installed")
    from asset_manager.index import AssetIndex
    return {**AssetIndex().summarize(), "_source_hostname": HOSTNAME}

@app.get("/api/assets/disk")
def api_assets_disk():
    if not ASSET_SEARCH_AVAILABLE:
        raise HTTPException(501, detail="asset_manager not installed")
    from asset_manager.cache import CacheManager
    return {**CacheManager().disk_usage(), "_source_hostname": HOSTNAME}

# ═══════════════════════════════════════════════════════════
# 费用分析
# ═══════════════════════════════════════════════════════════

@app.get("/api/costs/breakdown")
def api_cost_breakdown(
    plugin: str = Query("ave", description="数据源插件名"),
):
    """费用统计，支持 ?plugin= 切换"""
    p = _get_plugin(plugin)
    data = p.get_cost_breakdown()
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "_source_hostname" not in item:
                item["_source_hostname"] = HOSTNAME
    return {"data": data, "source_hostname": HOSTNAME, "plugin": plugin}

# ═══════════════════════════════════════════════════════════
# 联邦机器状态 (统一走 guardd 插件)
# ═══════════════════════════════════════════════════════════

@app.get("/api/machines")
def api_machines():
    """联邦机器状态：优先读取 push 实时数据，降级到 Git 心跳文件"""
    p = _PLUGINS.get("guardd")
    if p is None or not _AVAILABLE.get("guardd", False):
        return {"machines": [], "total": 0, "error": "guardd plugin unavailable"}
    try:
        machines = p.get_productions()
        # 用 push 实时数据覆盖 Git 数据
        now = datetime.now(timezone.utc)
        for m in machines:
            hostname = m["hostname"]
            live_file = _CROSS_MACHINE_DIR / "status" / hostname / "live.json"
            if live_file.exists():
                try:
                    live = json.loads(live_file.read_text())
                    received = live.get("_received_at", "")
                    if received:
                        try:
                            rt = datetime.fromisoformat(received)
                            delta = (now - rt).total_seconds()
                            if delta < 120:  # 2分钟内视为实时
                                m["_live"] = True
                                m["_last_push_sec"] = round(delta)
                                m["last_seen"] = received
                                m["status"] = "online"
                        except:
                            pass
                except:
                    pass
            if "_live" not in m:
                m["_live"] = False
        if isinstance(machines, list):
            for m in machines:
                if "_source_hostname" not in m:
                    m["_source_hostname"] = HOSTNAME
        return {"machines": machines, "total": len(machines) if isinstance(machines, list) else 0}
    except Exception as e:
        return {"machines": [], "total": 0, "error": str(e)}

# ═══════════════════════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "hostname": HOSTNAME,
        "plugins": {n: "available" if _AVAILABLE.get(n) else "unavailable" for n in _PLUGINS},
    }

# ═══════════════════════════════════════════════════════════
# 联邦 PUSH API (反向连接, UID 认证)
# ═══════════════════════════════════════════════════════════

# 已注册的机器 UID → hostname 映射表
# 首次收到新 UID 会自动注册（push_allow_auto_register=True 时）
_REGISTERED_UIDS: dict[str, dict] = {}
_PUSH_CONFIG = {
    "allow_auto_register": True,   # 首次收到未知 UID 是否自动注册
    "uid_whitelist": [],            # 非空时只接受列表中的 UID (优先级高于 auto_register)
}

def _load_uids():
    """从跨机 registry 加载已知 UID"""
    reg_dir = _CROSS_MACHINE_DIR / "registry"
    if not reg_dir.exists():
        return
    for f in reg_dir.iterdir():
        if f.suffix == ".json":
            try:
                data = json.loads(f.read_text())
                uid = data.get("uid", "")
                if uid:
                    _REGISTERED_UIDS[uid] = data
            except:
                pass

_load_uids()


@app.post("/api/push/heartbeat")
def api_push_heartbeat(data: dict):
    """接收各机器的实时心跳推送（反向连接, UID 认证）"""
    uid = data.get("uid", "")
    hostname = data.get("hostname", "unknown")

    if not uid:
        raise HTTPException(400, detail="missing uid")

    # UID 认证
    whitelist = _PUSH_CONFIG["uid_whitelist"]
    if whitelist and uid not in whitelist:
        raise HTTPException(403, detail=f"uid {uid[:8]}... not authorized")

    if uid not in _REGISTERED_UIDS and _PUSH_CONFIG["allow_auto_register"]:
        _REGISTERED_UIDS[uid] = {
            "uid": uid, "hostname": hostname,
            "first_seen": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"  新机器自动注册: {hostname} ({uid[:8]}...)")

    # 写入机器推送状态（内存 + 文件缓存）
    push_dir = _CROSS_MACHINE_DIR / "status" / hostname
    push_dir.mkdir(parents=True, exist_ok=True)
    push_file = push_dir / "live.json"

    hb = data.get("heartbeat", {})
    hb["_source"] = "push"
    hb["_received_at"] = datetime.now(timezone.utc).isoformat()
    hb["_uid"] = uid
    push_file.write_text(json.dumps(hb, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"status": "ok", "hostname": hostname, "uid": uid[:8] + "..."}


@app.get("/api/push/status")
def api_push_status():
    """查看所有已注册机器的推送状态"""
    machines = []
    for uid, info in _REGISTERED_UIDS.items():
        hostname = info.get("hostname", "unknown")
        push_file = _CROSS_MACHINE_DIR / "status" / hostname / "live.json"
        last_push = None
        if push_file.exists():
            try:
                last_push = json.loads(push_file.read_text()).get("_received_at", None)
            except:
                pass
        machines.append({
            "uid": uid[:8] + "...",
            "hostname": hostname,
            "first_seen": info.get("first_seen", ""),
            "last_push": last_push,
            "status": "active" if last_push else "waiting",
        })
    return {"machines": machines, "total": len(machines)}


if __name__ == "__main__":
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9988
    print(f"📊 系统监控面板 v2.0 — 联邦协同版")
    print(f"   本机: {HOSTNAME}")
    print(f"   → http://localhost:{port}")
    print(f"   插件: {', '.join(_PLUGINS.keys())}")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)

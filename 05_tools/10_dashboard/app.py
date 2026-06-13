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
import sys, os, json, time, logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger("dashboard")

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

# ── 联邦路径 ───────────────────────────────────────────────
_CROSS_MACHINE_DIR = Path(__file__).resolve().parent.parent.parent / "04_memory" / "cross_machine"

_PLUGINS: dict[str, DashboardPlugin] = {}
_AVAILABLE: dict[str, bool] = {}

def _register_plugins():
    """自动发现并注册所有插件"""
    from plugins import discover_plugins
    discovered = discover_plugins()
    for name, inst in discovered.items():
        try:
            _PLUGINS[name] = inst
            _AVAILABLE[name] = inst.is_available()
            # 写入共享数据
            try:
                inst.write_shared()
            except:
                pass
        except Exception as e:
            _PLUGINS[name] = None
            _AVAILABLE[name] = False
            logger.warning(f"  插件 {name} 加载失败: {e}")

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
    from fastapi.responses import HTMLResponse
    if index_path.exists():
        content = index_path.read_text(encoding="utf-8")
        return HTMLResponse(content=content, headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        })
    return {"error": "index.html not found"}

@app.on_event("startup")
async def startup():
    _register_plugins()

# ═══════════════════════════════════════════════════════════
# 联邦基础 API
# ═══════════════════════════════════════════════════════════

@app.get("/api/plugins")
def api_plugins():
    """返回所有注册插件的元信息 (v2)"""
    result = []
    for p in sorted([p for p in _PLUGINS.values() if p], key=lambda p: p.order):
        result.append({
            "name": p.name, "label": p.label, "icon": p.icon,
            "version": p.version, "description": p.description,
            "order": p.order, "available": _AVAILABLE.get(p.name, False),
            "sub_views": p.get_sub_views(),
            "source_hostname": HOSTNAME,
        })
    return {"plugins": result, "total": len(result), "source_hostname": HOSTNAME}


@app.get("/api/plugins/{name}/summary")
def api_plugin_summary(name: str):
    """返回指定插件的概览数据"""
    inst = _get_plugin(name)
    from plugins._registry import get_machine_list
    try:
        data = inst.summary(get_machine_list())
        return {"plugin": name, "data": data, "source_hostname": HOSTNAME}
    except Exception as e:
        return {"plugin": name, "error": str(e)}


@app.get("/api/plugins/{name}/detail")
def api_plugin_detail(name: str, machine: str = ""):
    """返回指定插件的详细面板"""
    inst = _get_plugin(name)
    try:
        data = inst.detail(machine)
        return {"plugin": name, "machine": machine or "all", "data": data}
    except Exception as e:
        return {"plugin": name, "error": str(e)}


@app.get("/api/plugins/{name}/actions")
def api_plugin_actions(name: str):
    """返回指定插件的可执行操作"""
    inst = _get_plugin(name)
    try:
        return {"plugin": name, "actions": inst.actions()}
    except Exception as e:
        return {"plugin": name, "actions": [], "error": str(e)}


@app.get("/api/summary")
def api_summary():
    """聚合总览 (所有插件 summary + 各机器心跳)"""
    result = {}
    for name, inst in sorted(_PLUGINS.items(), key=lambda x: x[1].order if x[1] else 99):
        if inst is None:
            continue
        try:
            from plugins._registry import get_machine_list
            result[name] = {
                "meta": {"label": inst.label, "icon": inst.icon, "version": inst.version},
                "data": inst.summary(get_machine_list()),
            }
        except Exception as e:
            result[name] = {"meta": {"label": inst.label}, "error": str(e)}
    return {"plugins": result, "source_hostname": HOSTNAME}


@app.get("/api/identity")
def api_identity():
    """返回本机身份信息 (顶栏用)"""
    from plugins.base import MACHINE_UID, HOSTNAME, AGENT_SYNC
    import subprocess
    git_ver = ""; git_repo = ""
    try:
        r = subprocess.run(["git","log","-1","--format=%h %ci"], capture_output=True, text=True,
                          timeout=5, cwd=str(AGENT_SYNC))
        git_ver = r.stdout.strip()
        r2 = subprocess.run(["git","remote","get-url","origin"], capture_output=True, text=True,
                           timeout=5, cwd=str(AGENT_SYNC))
        git_repo = r2.stdout.strip().split("/")[-1].replace(".git","")
    except: pass
    role = "工作站"
    reg_dir = _CROSS_MACHINE_DIR / "registry"
    if reg_dir.exists():
        for f in reg_dir.iterdir():
            if f.suffix == ".json":
                try:
                    d = json.loads(f.read_text())
                    if d.get("hostname","") == HOSTNAME or MACHINE_UID[:8] in f.name:
                        role = d.get("role", "工作站")
                except: pass
    return {"hostname": HOSTNAME, "uid": MACHINE_UID[:12]+"...", "role": role,
            "git_version": git_ver, "git_repo": git_repo}

# ═══════════════════════════════════════════════════════════
# 生产列表 (兼容旧版 → 委托给插件 detail)
# ═══════════════════════════════════════════════════════════

@app.get("/api/productions")
def api_productions(
    plugin: str = Query("ave", description="数据源插件名"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    strategy: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """生产列表 (v4 兼容)"""
    from plugins._registry import get_machine_list
    p = _get_plugin(plugin)
    try:
        data = p.detail()
        # 统一转成生产记录列表
        items = []
        if isinstance(data, dict):
            for hn, info in data.items():
                prods = []
                if isinstance(info, dict):
                    prods = info.get("productions", info.get("productions", []))
                    # 如果 info 本身不是 production 格式, 尝试直接放行
                    if not prods and "管线" in info:
                        prods = []
                for prod in prods:
                    if isinstance(prod, dict):
                        prod["_source_hostname"] = hn
                        items.append(prod)
        return {"data": items, "source_hostname": HOSTNAME, "plugin": plugin}
    except Exception as e:
        return {"data": [], "source_hostname": HOSTNAME, "plugin": plugin, "error": str(e)}


@app.get("/api/productions/{production_id}")
def api_production_detail(
    production_id: str,
    plugin: str = Query("ave", description="数据源插件名"),
):
    """生产详情 (v4 兼容)"""
    p = _get_plugin(plugin)
    try:
        data = p.detail()
        if isinstance(data, dict):
            for hn, info in data.items():
                if production_id in str(hn) or production_id in str(info):
                    return {"data": info, "source_hostname": hn, "plugin": plugin}
        return {"data": None, "plugin": plugin}
    except Exception as e:
        return {"data": None, "plugin": plugin, "error": str(e)}

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
# 角色管理 API (AVE 插件数据)
# ═══════════════════════════════════════════════════════════

@app.get("/api/characters")
def api_characters():
    """角色管理：列出所有已注册角色"""
    p = _PLUGINS.get("ave")
    if p is None or not _AVAILABLE.get("ave", False):
        return {"characters": {}, "active": "", "total": 0, "error": "ave plugin unavailable",
                "_source_hostname": HOSTNAME}
    try:
        data = p.get_characters()
        data["_source_hostname"] = HOSTNAME
        return data
    except Exception as e:
        return {"characters": {}, "active": "", "total": 0, "error": str(e),
                "_source_hostname": HOSTNAME}


# ── 角色生成/定制 API ──

@app.post("/api/characters/generate-portrait")
def api_generate_portrait(data: dict):
    """为已有角色生成定妆照（工作流编辑器调用）"""
    character_name = data.get("character_name", "")
    description = data.get("description", "")
    force = data.get("force", False)
    seed = data.get("seed", 0)

    if not character_name:
        raise HTTPException(400, detail="缺少 character_name")

    try:
        from character_generator.pipeline import CharacterGenerationPipeline
        pipeline = CharacterGenerationPipeline()
        result = pipeline.generate_portrait(character_name, force=force, seed=seed)
        return {"status": "ok", "name": character_name, "result": result}
    except Exception as e:
        logger.error(f"定妆照生成失败: {e}")
        raise HTTPException(500, detail=f"生成失败: {str(e)}")


@app.post("/api/characters/generate-from-direction")
def api_generate_from_direction(data: dict):
    """
    从粗方向生成完整角色（方向→扩展→属性→生成→注册）
    
    请求:
      direction: str — 粗方向描述
      name: str (可选) — 角色名
      generate_images: bool (默认 true) — 是否生成图像
      seed: int (可选) — 固定种子
      layers: dict (可选) — 前端模块化面板的逐层数据
    
    返回:
      {name, description, attributes, baseline, angles, expressions, registered}
    """
    direction = data.get("direction", "")
    name = data.get("name", "")
    generate_images = data.get("generate_images", True)
    seed = data.get("seed", 0)
    layers = data.get("layers", {})  # 新增：前端模块化面板的逐层数据

    if not direction:
        raise HTTPException(400, detail="缺少 direction")

    try:
        from character_generator.pipeline import CharacterGenerationPipeline
        pipeline = CharacterGenerationPipeline()
        result = pipeline.run_full(
            direction, character_name=name,
            generate_variants=generate_images, seed=seed,
        )
        return {"status": "ok", **result}
    except Exception as e:
        logger.error(f"角色生成失败: {e}")
        raise HTTPException(500, detail=f"角色生成失败: {str(e)}")


@app.post("/api/characters/update")
def api_update_character(data: dict):
    """更新角色属性"""
    name = data.get("name", "")
    if not name:
        raise HTTPException(400, detail="缺少 name")

    try:
        from character_generator.asset_registrar import AssetRegistrar
        registrar = AssetRegistrar()
        attrs = data.get("attributes", data)
        registrar.register_character_properties(name, attrs)
        return {"status": "ok", "name": name}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/api/characters/capabilities")
def api_character_capabilities():
    """返回角色生成引擎支持的变体类型"""
    from character_generator.prompt_assembler import PromptAssembler
    assembler = PromptAssembler()
    return {"variants": assembler.get_available_variants()}


@app.post("/api/characters/expand-direction")
def api_expand_direction(data: dict):
    """仅扩展方向描述，不生成图像"""
    direction = data.get("direction", "")
    if not direction:
        raise HTTPException(400, detail="缺少 direction")
    try:
        from character_generator.direction_expander import DirectionExpander
        expander = DirectionExpander()
        description = expander.expand(direction)
        return {"direction": direction, "description": description}
    except Exception as e:
        # 回退到直接使用原始方向
        return {"direction": direction, "description": direction}


# ═══════════════════════════════════════════════════════════
# 原子能力 API (AVE 插件数据)
# ═══════════════════════════════════════════════════════════

@app.get("/api/capabilities")
def api_capabilities():
    """原子能力：列出 AVE 所有底层能力"""
    p = _PLUGINS.get("ave")
    if p is None or not _AVAILABLE.get("ave", False):
        return {"groups": [], "total_items": 0, "error": "ave plugin unavailable",
                "_source_hostname": HOSTNAME}
    try:
        data = p.get_capabilities()
        data["_source_hostname"] = HOSTNAME
        return data
    except Exception as e:
        return {"groups": [], "total_items": 0, "error": str(e),
                "_source_hostname": HOSTNAME}

# ═══════════════════════════════════════════════════════════
# 费用分析
# ═══════════════════════════════════════════════════════════

@app.get("/api/costs/breakdown")
def api_cost_breakdown(
    plugin: str = Query("ave", description="数据源插件名"),
):
    """费用统计 (v4 兼容)"""
    p = _get_plugin(plugin)
    try:
        data = p.detail()
        return {"data": data, "source_hostname": HOSTNAME, "plugin": plugin}
    except Exception as e:
        return {"data": [], "source_hostname": HOSTNAME, "plugin": plugin, "error": str(e)}

# ═══════════════════════════════════════════════════════════
# 联邦机器状态 (统一走 guardd 插件)
# ═══════════════════════════════════════════════════════════

@app.get("/api/machines")
def api_machines():
    """联邦机器状态 (v2) — 委托给 guardd 插件"""
    p = _PLUGINS.get("guardd")
    if p is None or not _AVAILABLE.get("guardd", False):
        return {"machines": [], "total": 0, "error": "guardd plugin unavailable"}
    try:
        from plugins._registry import get_machine_list
        data = p.summary(get_machine_list())
        detail = p.detail()
        machines = []
        for hn, info in detail.items():
            m = {"hostname": hn}
            m.update(info)
            m["_source_hostname"] = HOSTNAME
            machines.append(m)
        return {"machines": machines, "total": len(machines)}
    except Exception as e:
        return {"machines": [], "total": 0, "error": str(e)}

# ═══════════════════════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════════════════════

@app.post("/api/git-sync")
def api_git_sync():
    """执行 git pull 拉取所有机器最新数据"""
    import subprocess
    from plugins.base import AGENT_SYNC
    try:
        r = subprocess.run(["git", "pull"], capture_output=True, text=True,
                          timeout=30, cwd=str(AGENT_SYNC))
        return {"success": r.returncode == 0, "output": r.stdout[-200:]}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/matrix-mgmt")
def matrix_mgmt_page():
    """Matrix 管理前端页面"""
    mgmt_path = _static_dir / "matrix_mgmt.html"
    if mgmt_path.exists():
        from fastapi.responses import HTMLResponse
        content = mgmt_path.read_text(encoding="utf-8")
        return HTMLResponse(content=content, headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
        })
    return {"error": "matrix_mgmt.html not found"}


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

_REGISTERED_UIDS: dict[str, dict] = {}
_ALLOW_AUTO_REGISTER = True
_UID_WHITELIST: list[str] = []
# 心跳历史 (用于时间线/热力图)
_HEARTBEAT_HISTORY: dict[str, list[dict]] = {}

def _load_uids():
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
    """接收实时心跳推送 — 以 UID 为主键存储, 无惧 hostname 变化"""
    uid = data.get("uid", "")
    hostname = data.get("hostname", "unknown")
    if not uid:
        raise HTTPException(400, detail="missing uid")
    if _UID_WHITELIST and uid not in _UID_WHITELIST:
        raise HTTPException(403, detail=f"uid not authorized")

    # 注册/更新 UID 信息
    now = datetime.now(timezone.utc)
    if uid in _REGISTERED_UIDS:
        _REGISTERED_UIDS[uid]["hostname"] = hostname
        _REGISTERED_UIDS[uid]["last_seen"] = now.isoformat()
    elif _ALLOW_AUTO_REGISTER:
        _REGISTERED_UIDS[uid] = {
            "uid": uid, "hostname": hostname,
            "first_seen": now.isoformat(),
            "last_seen": now.isoformat(),
        }

    # 以 UID 为文件名存储 live.json（非 hostname）
    live_dir = _CROSS_MACHINE_DIR / "status" / "live"
    live_dir.mkdir(parents=True, exist_ok=True)
    hb = data.get("heartbeat", {})
    hb["_source"] = "push"
    hb["_received_at"] = now.isoformat()
    hb["_uid"] = uid
    hb["_hostname"] = hostname
    hb["_events"] = data.get("events", [])
    hb["_uptime"] = data.get("uptime", 0)
    (live_dir / f"{uid}.json").write_text(
        json.dumps(hb, indent=2, ensure_ascii=False), encoding="utf-8")

    # 按 UID 记录心跳历史
    hist = _HEARTBEAT_HISTORY.setdefault(uid, [])
    hist.append({
        "t": now.isoformat(),
        "cpu": hb.get("cpu", {}).get("load_1m", 0),
        "disk_pct": hb.get("disk", {}).get("used_gb", 0),
        "ts": now.timestamp(),
        "hostname": hostname,
    })
    if len(hist) > 1440:
        _HEARTBEAT_HISTORY[uid] = hist[-1440:]
    return {"status": "ok", "uid": uid[:8] + "...", "hostname": hostname}


@app.get("/api/push/status")
def api_push_status():
    """查看已注册机器的 UID 和 hostname"""
    items = []
    for uid, info in _REGISTERED_UIDS.items():
        live_file = _CROSS_MACHINE_DIR / "status" / "live" / f"{uid}.json"
        lp = None
        if live_file.exists():
            try:
                lp = json.loads(live_file.read_text()).get("_received_at")
            except:
                pass
        items.append({
            "uid": uid[:8] + "...",
            "hostname": info.get("hostname", "unknown"),
            "first_seen": info.get("first_seen", ""),
            "last_seen": info.get("last_seen", ""),
            "last_push": lp,
            "status": "active" if lp else "waiting",
        })
    return {"machines": items, "total": len(items)}


# ═══════════════════════════════════════════════════════════
# 功能 API: 时间线 / 热力图 / 告警 / 升级 / 唤醒 / 日报
# ═══════════════════════════════════════════════════════════

@app.get("/api/timeline/{uid}")
def api_timeline(uid: str, window: int = 300):
    """CPU/磁盘变化折线图 (按UID查询)"""
    hist = _HEARTBEAT_HISTORY.get(uid, [])
    reg = _REGISTERED_UIDS.get(uid, {})
    return {
        "uid": uid[:8] + "...",
        "hostname": reg.get("hostname", "unknown"),
        "points": hist[-window:],
        "total": len(hist),
    }


@app.get("/api/heatmap")
def api_heatmap():
    """心跳热力图：各机器24小时活动分布 (按UID)"""
    now = datetime.now(timezone.utc)
    day_ago = now.timestamp() - 86400
    result = {}
    for uid, hist in _HEARTBEAT_HISTORY.items():
        recent = [p for p in hist if p.get("ts", 0) > day_ago]
        if not recent:
            continue
        reg = _REGISTERED_UIDS.get(uid, {})
        hostname = reg.get("hostname", uid[:8])
        hourly = [0] * 24
        for p in recent:
            try:
                hr = datetime.fromisoformat(p["t"]).hour
            except:
                hr = 0
            hourly[hr] += 1
        result[hostname] = {
            "uid": uid[:8] + "...",
            "total_pings": len(recent),
            "hourly": hourly,
            "last_seen": recent[-1]["t"] if recent else None,
        }
    return {"machines": result}


@app.get("/api/alerts")
def api_alerts():
    """离线告警：心跳超时5分钟以上的机器"""
    now = datetime.now(timezone.utc)
    alerts = []
    for uid, hist in _HEARTBEAT_HISTORY.items():
        if not hist:
            continue
        reg = _REGISTERED_UIDS.get(uid, {})
        hostname = reg.get("hostname", uid[:8])
        last = hist[-1]
        try:
            delta = (now - datetime.fromisoformat(last["t"])).total_seconds()
            if delta > 300:
                alerts.append({
                    "hostname": hostname,
                    "uid": uid[:8] + "...",
                    "level": "warning" if delta < 900 else "critical",
                    "since_sec": round(delta),
                    "last_seen": last["t"],
                })
        except:
            pass
    # 也检查有注册但无推送的机器
    for uid, reg in _REGISTERED_UIDS.items():
        hn = reg.get("hostname", "")
        if hn and uid not in _HEARTBEAT_HISTORY:
            alerts.append({
                "hostname": hn,
                "uid": uid[:8] + "...",
                "level": "info",
                "since_sec": 99999,
                "note": "已注册但未推送",
            })
    return {"alerts": alerts, "total": len(alerts)}


@app.post("/api/wakeup/{uid}")
def api_wakeup(uid: str):
    """一键唤醒：通过 UID 找到目标机器"""
    reg = _REGISTERED_UIDS.get(uid)
    if not reg:
        # 尝试从 live 目录反向查找
        live_file = _CROSS_MACHINE_DIR / "status" / "live" / f"{uid}.json"
        if live_file.exists():
            try:
                live = json.loads(live_file.read_text())
                target = live.get("_hostname", uid)
            except:
                target = uid
        else:
            target = uid
    else:
        target = reg.get("hostname", uid)
    task = {
        "id": f"wakeup_{target}_{int(time.time())}",
        "type": "run_guardd",
        "target_host": target,
        "source_host": HOSTNAME,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }
    task_dir = _CROSS_MACHINE_DIR / "tasks" / "pending"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / f"{task['id']}.json").write_text(
        json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "task_id": task["id"], "target": target}


@app.post("/api/upgrade/{uid}")
def api_upgrade(uid: str):
    """一键升级：通过 UID 找到目标机器"""
    reg = _REGISTERED_UIDS.get(uid)
    target = reg.get("hostname", uid) if reg else uid
    task = {
        "id": f"upgrade_{target}_{int(time.time())}",
        "type": "run_script",
        "script": "cd ~/workbuddy-agent-os/agent-sync && git pull && launchctl kickstart gui/$(id -u)/com.agentos.guardd",
        "target_host": target,
        "source_host": HOSTNAME,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }
    task_dir = _CROSS_MACHINE_DIR / "tasks" / "pending"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / f"{task['id']}.json").write_text(
        json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "task_id": task["id"], "target": target}


@app.get("/api/daily-summary")
def api_daily_summary():
    """今日联邦日报：汇总各机器的当天事件"""
    today = datetime.now().strftime("%Y-%m-%d")
    machines_report = {}
    for uid, hist in _HEARTBEAT_HISTORY.items():
        if not hist:
            continue
        reg = _REGISTERED_UIDS.get(uid, {})
        hostname = reg.get("hostname", uid[:8])
        last = hist[-1]
        summary = {"ping_count": len(hist), "events": [], "uid": uid[:8] + "..."}
        events = last.get("_events", []) if isinstance(last, dict) else []
        for ev in events[-5:]:
            summary["events"].append({
                "type": ev.get("type", "unknown"),
                "time": ev.get("timestamp", ""),
                "payload": ev.get("payload", {}),
            })
        machines_report[hostname] = summary
    return {
        "date": today,
        "machines": machines_report,
        "total_machines": len(machines_report),
    }


# ═══════════════════════════════════════════════════════════
# Matrix 管理 API (v3.0 新增)
# ═══════════════════════════════════════════════════════════

import importlib.util
_MATRIX_MGMT_PATH = Path(__file__).resolve().parent.parent / "07_matrix" / "scripts" / "matrix_mgmt.py"

def _init_matrix_mgmt():
    """初始化 MatrixManager 实例"""
    if not _MATRIX_MGMT_PATH.exists():
        return None
    spec = importlib.util.spec_from_file_location("matrix_mgmt", _MATRIX_MGMT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.MatrixManager()

def _get_matrix_mgr():
    mgr = _init_matrix_mgmt()
    if mgr is None:
        raise HTTPException(503, detail="matrix_mgmt module not found")
    return mgr


@app.get("/api/matrix/accounts")
def api_matrix_accounts():
    """列出所有账号及状态"""
    try:
        mgr = _get_matrix_mgr()
        return {"accounts": mgr.list_accounts(), "total": len(mgr.list_accounts())}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/api/matrix/profiles")
def api_matrix_account_profiles():
    """读取已保存的账号主页信息"""
    try:
        path = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix" / "data" / "profiles.json"
        if path.exists():
            return json.loads(path.read_text())
        return {}
    except:
        return {}


@app.get("/api/matrix/accounts/{account_id}")
def api_matrix_account(account_id: str):
    """获取单个账号详情"""
    try:
        mgr = _get_matrix_mgr()
        acct = mgr.get_account(account_id)
        if not acct:
            raise HTTPException(404, detail=f"账号 {account_id} 不存在")
        return acct
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/api/matrix/accounts")
async def api_matrix_create_account(data: dict):
    """创建新账号"""
    try:
        mgr = _get_matrix_mgr()
        # 记录到日志
        logger.info(f"Matrix: 创建账号 {data.get('id','')}")
        return mgr.create_account(data)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.put("/api/matrix/accounts/{account_id}")
async def api_matrix_update_account(account_id: str, data: dict):
    """更新账号"""
    try:
        mgr = _get_matrix_mgr()
        logger.info(f"Matrix: 更新账号 {account_id}")
        return mgr.update_account(account_id, data)
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.delete("/api/matrix/accounts/{account_id}")
def api_matrix_delete_account(account_id: str, delete_identity: bool = False):
    """删除账号"""
    try:
        mgr = _get_matrix_mgr()
        logger.info(f"Matrix: 删除账号 {account_id} (delete_identity={delete_identity})")
        return mgr.delete_account(account_id, delete_identity)
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/api/matrix/accounts/{account_id}/login-status")
def api_matrix_login_status(account_id: str):
    """检查登录状态"""
    try:
        mgr = _get_matrix_mgr()
        return mgr.check_login_status(account_id)
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/api/matrix/nurture/start")
async def api_matrix_nurture_start(data: dict):
    """启动批量养号（通过 mc CLI 执行）"""
    try:
        accounts = data.get("accounts", [])
        blueprints = data.get("blueprints", [])
        rounds = data.get("rounds", 5)
        mix = data.get("mix", False)
        daemon = data.get("daemon", False)

        if not accounts or not blueprints:
            raise HTTPException(400, detail="accounts 和 blueprints 必填")

        import subprocess
        mc_path = str(Path(__file__).resolve().parent.parent.parent / "05_tools" / "07_matrix" / "mc")
        cmd = [mc_path, "run", f"--accounts={','.join(accounts)}", f"--blueprints={','.join(blueprints)}", f"--rounds={rounds}"]
        if mix:
            cmd.append("--mix")
        if daemon:
            cmd.append("--daemon")

        logger.info(f"Matrix: 启动批量养号 {' '.join(cmd)}")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, cwd=str(Path(mc_path).parent))
        return {"status": "started", "pid": proc.pid, "cmd": " ".join(cmd)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── 原子操作 & 蓝图 ──

@app.get("/api/matrix/atom-ops")
def api_matrix_atom_ops():
    """列出所有可用原子操作"""
    try:
        mgr = _get_matrix_mgr()
        return {"ops": mgr.list_atomic_ops(), "total": len(mgr.list_atomic_ops())}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── 录制系统 API ──

@app.get("/api/matrix/record/list")
def api_record_list():
    """列出所有录制包"""
    from mc.recorder import RecordingSession
    return {"recordings": RecordingSession.list_recordings()}


@app.post("/api/matrix/record/analyze")
def api_record_analyze(data: dict):
    """分析录制包"""
    path = data.get("path", "")
    from mc.analyzer import analyze_recording_file
    result = analyze_recording_file(path)
    return result


@app.post("/api/matrix/record/export")
def api_record_export(data: dict):
    """导出录制包"""
    path = data.get("path", "")
    from mc.exporter import export_recording
    result = export_recording(path)
    return result


@app.post("/api/matrix/record/delete")
def api_record_delete(data: dict):
    """删除录制包"""
    path = data.get("path", "")
    from mc.recorder import RecordingSession
    ok = RecordingSession.delete_recording(path)
    return {"status": "ok" if ok else "error"}


@app.get("/api/matrix/blueprints")
def api_matrix_blueprints():
    """列出所有蓝图"""
    try:
        mgr = _get_matrix_mgr()
        return {"blueprints": mgr.list_blueprints(), "total": len(mgr.list_blueprints())}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/api/matrix/blueprints")
async def api_matrix_save_blueprint(data: dict):
    """保存蓝图"""
    try:
        mgr = _get_matrix_mgr()
        name = data.get("name", "")
        if not name:
            raise HTTPException(400, detail="蓝图名称必填")
        logger.info(f"Matrix: 保存蓝图 {name}")
        return mgr.save_blueprint(name, data)
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.delete("/api/matrix/blueprints/{name}")
def api_matrix_delete_blueprint(name: str):
    """删除蓝图"""
    try:
        mgr = _get_matrix_mgr()
        return mgr.delete_blueprint(name)
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/api/matrix/blueprints/{name}/execute")
async def api_matrix_execute_blueprint(name: str, data: dict):
    """执行蓝图"""
    try:
        mgr = _get_matrix_mgr()
        account_id = data.get("account", "")
        if not account_id:
            raise HTTPException(400, detail="account 必填")
        logger.info(f"Matrix: 执行蓝图 {name} on {account_id}")
        return mgr.execute_blueprint(name, account_id)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── 导入导出 ──

@app.get("/api/matrix/export")
def api_matrix_export():
    """导出账号配置+Cookie为ZIP"""
    try:
        mgr = _get_matrix_mgr()
        zip_path = mgr.export_accounts()
        return {"status": "ok", "path": zip_path, "size_kb": round(os.path.getsize(zip_path) / 1024, 1)}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/api/matrix/import")
async def api_matrix_import(data: dict):
    """从ZIP导入"""
    try:
        mgr = _get_matrix_mgr()
        zip_path = data.get("path", "")
        overwrite = data.get("overwrite", False)
        if not zip_path:
            raise HTTPException(400, detail="path 必填")
        return mgr.import_accounts(zip_path, overwrite)
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/api/matrix/system-info")
def api_matrix_system_info():
    """系统信息"""
    try:
        mgr = _get_matrix_mgr()
        return mgr.system_info()
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── 蓝图校验 ──

@app.post("/api/matrix/blueprints/validate")
async def api_matrix_validate_blueprint(data: dict):
    """校验蓝图步骤编排合法性"""
    try:
        mgr = _get_matrix_mgr()
        steps = data.get("steps", [])
        return mgr.validate_blueprint_steps(steps)
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── 备份恢复 ──

@app.get("/api/matrix/backups")
def api_matrix_backups():
    """列出所有备份"""
    try:
        mgr = _get_matrix_mgr()
        return {"backups": mgr.list_backups(), "total": len(mgr.list_backups())}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/api/matrix/backup")
async def api_matrix_create_backup(data: dict = {}):
    """创建全量备份"""
    try:
        mgr = _get_matrix_mgr()
        label = data.get("label", "manual")
        logger.info(f"Matrix: 创建备份 label={label}")
        return mgr.create_backup(label)
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/api/matrix/restore")
async def api_matrix_restore(data: dict):
    """恢复备份"""
    try:
        mgr = _get_matrix_mgr()
        identity = data.get("identity", "")
        path = data.get("path", "")
        if not identity or not path:
            raise HTTPException(400, detail="identity 和 path 必填")
        logger.info(f"Matrix: 恢复 {identity} 从 {path}")
        return mgr.restore_backup(identity, path)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── 跨机注册表 API ──

@app.get("/api/matrix/cross-machines")
def api_matrix_cross_machines():
    """跨机矩阵概览：聚合所有机器的账号状态"""
    try:
        mgr = _get_matrix_mgr()
        # 本机状态
        local_status = mgr.publish_status()
        accounts = mgr.list_accounts()

        # 按机器分组
        machines = {}
        for a in accounts:
            owner = a.get("owner_machine", "未分配")
            if owner not in machines:
                machines[owner] = {
                    "hostname": owner,
                    "total": 0, "local": 0,
                    "enabled": 0, "logged_in": 0,
                    "remote": 0, "accounts": [],
                }
            machines[owner]["total"] += 1
            if a.get("is_local"): machines[owner]["local"] += 1
            if a.get("_status") == "remote": machines[owner]["remote"] += 1
            if a.get("enabled", False): machines[owner]["enabled"] += 1
            if a.get("_status") == "logged_in": machines[owner]["logged_in"] += 1
            machines[owner]["accounts"].append({
                "id": a["id"],
                "platform": a.get("platform", ""),
                "phone_mask": a.get("phone_mask", ""),
                "status": a.get("_status", "unknown"),
                "enabled": a.get("enabled", False),
            })

        return {
            "machines": list(machines.values()),
            "total_machines": len(machines),
            "total_accounts": len(accounts),
            "source_hostname": HOSTNAME,
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── 语料库 API ──

@app.get("/api/matrix/corpus")
def api_matrix_corpus():
    """获取语料库分类和统计"""
    try:
        from mc.corpus import CorpusManager
        cm = CorpusManager()
        categories = cm.list_categories()
        total = sum(c.get("count", 0) for c in categories)
        return {"categories": categories, "total_comments": total}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/api/matrix/corpus/add")
async def api_matrix_corpus_add(data: dict):
    """添加评论到语料库"""
    try:
        from mc.corpus import CorpusManager
        cm = CorpusManager()
        platform = data.get("platform", "douyin")
        category = data.get("category", "")
        text = data.get("text", "")
        if not category or not text:
            raise HTTPException(400, detail="category 和 text 必填")
        cm.add_comment(category, text, platform)
        return {"status": "ok", "platform": platform, "category": category}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/api/matrix/corpus/detail")
def api_matrix_corpus_detail(platform: str = "douyin", category: str = ""):
    """获取某个分类下所有评论"""
    try:
        from pathlib import Path
        CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "05_tools" / "07_matrix" / "corpus"
        import yaml
        file_path = CORPUS_DIR / f"{platform}.yaml"
        if not file_path.exists():
            return {"comments": [], "templates": []}
        data = yaml.safe_load(file_path.read_text())
        cats = data.get("categories", {})
        cat = cats.get(category, {})
        return {
            "comments": cat.get("comments", []),
            "templates": cat.get("templates", []),
            "weight": cat.get("weight", 10),
            "enabled": cat.get("enabled", True),
            "label": cat.get("label", category),
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/api/matrix/corpus/delete")
async def api_matrix_corpus_delete(data: dict):
    """删除一条评论"""
    try:
        from mc.corpus import CorpusManager
        cm = CorpusManager()
        platform = data.get("platform", "douyin")
        category = data.get("category", "")
        index = data.get("index", -1)
        if not category or index < 0:
            raise HTTPException(400, detail="category 和 index 必填")
        cm.delete_comment(category, index, platform)
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── 登记注册 API ──

@app.post("/api/matrix/register")
async def api_matrix_register(data: dict):
    """登记注册新账号"""
    try:
        phone = data.get("phone", "").strip()
        platform = data.get("platform", "douyin")
        display_name = data.get("display_name", "")
        proxy = data.get("proxy", "")
        identity_mode = data.get("identity_mode", "new")  # "new" or "existing"
        existing_identity = data.get("existing_identity", "")
        notes = data.get("notes", "")

        if not phone:
            raise HTTPException(400, detail="手机号必填")

        # 生成账号ID
        import yaml
        from pathlib import Path
        AGENT_SYNC = Path(__file__).resolve().parent.parent.parent
        REGISTRY_PATH = AGENT_SYNC / "05_tools" / "07_matrix" / "accounts_registry.yaml"

        reg = yaml.safe_load(REGISTRY_PATH.read_text()) if REGISTRY_PATH.exists() else {"accounts": []}
        existing_ids = [a["id"] for a in reg.get("accounts", [])]

        # 自动编号 — 使用平台完整前缀
        pid_prefix = {"douyin": "douyin", "xiaohongshu": "xhs"}
        prefix = pid_prefix.get(platform, platform[:4])
        num = 1
        while f"{prefix}_{num:02d}" in existing_ids:
            num += 1
        new_id = f"{prefix}_{num:02d}"

        # 身份目录名
        identity_hint = existing_identity if identity_mode == "existing" and existing_identity else new_id

        # phone_mask
        phone_mask = phone[:3] + "****" + phone[-4:] if len(phone) >= 7 else phone

        # 写入 registry
        new_acct = {
            "id": new_id,
            "platform": platform,
            "phone_mask": phone_mask,
            "assigned_machine": HOSTNAME,
            "identity_hint": identity_hint,
            "window": [702, 783],
            "window_position": [0, 0],
            "notes": notes or f"{platform} {phone_mask}",
        }
        reg["accounts"].append(new_acct)
        REGISTRY_PATH.write_text(yaml.dump(reg, default_flow_style=False, allow_unicode=True, sort_keys=False))

        # 写入 override
        AGENT_LOCAL = Path.home() / "workbuddy-agent-os" / "agent-local"
        OVR_PATH = AGENT_LOCAL / "tools" / "matrix" / "config" / "accounts.override.yaml"
        ovr = yaml.safe_load(OVR_PATH.read_text()) if OVR_PATH.exists() else {"version": "1.0", "hostname": HOSTNAME, "accounts": []}
        ovr_acct = {"id": new_id, "phone": phone, "enabled": True}
        if proxy:
            ovr_acct["proxy"] = proxy
        ovr["accounts"].append(ovr_acct)
        OVR_PATH.write_text(yaml.dump(ovr, default_flow_style=False, allow_unicode=True, sort_keys=False))

        logger.info(f"Matrix: 新账号注册 {new_id} ({phone})")

        return {
            "status": "ok",
            "account_id": new_id,
            "platform": platform,
            "phone": phone_mask,
            "identity_hint": identity_hint,
            "notes": notes,
            "registry_updated": True,
            "override_updated": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ═══════════════════════════════════════════
# 工作流引擎 API
# ═══════════════════════════════════════════

from workflows import NODE_DEFINITIONS, WORKFLOW_TEMPLATES, get_runner, get_node_categories


@app.get("/api/workflow/nodes")
def api_workflow_nodes():
    """返回所有节点类型（按分类）"""
    return get_node_categories()


@app.get("/api/workflow/node/{node_type}")
def api_workflow_node(node_type: str):
    """返回单个节点定义"""
    node = NODE_DEFINITIONS.get(node_type)
    if not node:
        raise HTTPException(404, detail=f"未知节点类型: {node_type}")
    return node


@app.get("/api/workflow/templates")
def api_workflow_templates():
    """返回所有工作流模板"""
    return {"templates": WORKFLOW_TEMPLATES, "total": len(WORKFLOW_TEMPLATES)}


@app.post("/api/workflow/run")
def api_workflow_run(data: dict):
    """创建工作流运行"""
    template_id = data.get("template_id", "custom")
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    if not nodes:
        raise HTTPException(400, detail="缺少节点列表")
    runner = get_runner()
    run_id = runner.create_run(template_id, nodes, edges)
    runner.start_run(run_id)
    return {"run_id": run_id, "status": "running"}


@app.get("/api/workflow/runs")
def api_workflow_runs():
    """列出所有运行"""
    return {"runs": []}


@app.get("/api/workflow/runs/{run_id}")
def api_workflow_run_status(run_id: str):
    """获取运行状态"""
    runner = get_runner()
    run = runner.get_run(run_id)
    if not run:
            raise HTTPException(404, detail="运行不存在")
    return run


# ═══════════════════════════════════════════════
# C2 联邦命令与控制 API (v1.0)
# ═══════════════════════════════════════════════

_C2_BUS = None

def _get_c2_bus():
    global _C2_BUS
    if _C2_BUS is None:
        c2_path = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts" / "c2"
        if c2_path.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("command_bus",
                c2_path / "command_bus.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _C2_BUS = mod.CommandBus()
    return _C2_BUS


@app.get("/api/c2/ping")
def api_c2_ping():
    """远程健康检查"""
    bus = _get_c2_bus()
    if not bus:
        raise HTTPException(503, detail="C2 模块不可用")
    return bus.ping()


@app.post("/api/c2/command")
async def api_c2_receive_command(data: dict):
    """接收远程命令并执行"""
    bus = _get_c2_bus()
    if not bus:
        raise HTTPException(503, detail="C2 模块不可用")
    result = bus.receive_and_execute(data)
    return result


@app.get("/api/c2/commands")
def api_c2_commands(limit: int = 20):
    """查询命令历史"""
    bus = _get_c2_bus()
    if not bus:
        raise HTTPException(503, detail="C2 模块不可用")
    return {
        "recent": bus.list_recent_commands(limit),
        "pending": bus.list_pending_commands(),
    }


@app.get("/api/c2/status/{command_id}")
def api_c2_status(command_id: str):
    """查询单条命令状态"""
    bus = _get_c2_bus()
    if not bus:
        raise HTTPException(503, detail="C2 模块不可用")
    result = bus.check_status(command_id)
    if not result:
        raise HTTPException(404, detail="命令不存在")
    return result


@app.post("/api/c2/send")
async def api_c2_send(data: dict):
    """从本机 Dashboard 发送命令到远程机器"""
    bus = _get_c2_bus()
    if not bus:
        raise HTTPException(503, detail="C2 模块不可用")
    target = data.get("target", "")
    cmd_type = data.get("type", "")
    params = data.get("params", {})
    schedule_at = data.get("schedule_at", None)
    if not target or not cmd_type:
        raise HTTPException(400, detail="需要 target 和 type")
    result = bus.send(target, cmd_type, params, schedule_at)
    return result


@app.get("/api/c2/machines")
def api_c2_machines():
    """返回所有已知机器的实时状态"""
    from plugins._registry import get_machine_list
    # 从 command_bus 加载机器端点映射
    try:
        c2_path = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts" / "c2" / "command_bus.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("cb_endpoints", c2_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        endpoints = mod.MACHINE_ENDPOINTS
    except:
        endpoints = {}
    return {
        "machines": get_machine_list(),
        "endpoints": endpoints,
    }


@app.get("/api/c2/environment/{machine}")
def api_c2_remote_environment(machine: str):
    """远程环境检查快捷接口"""
    bus = _get_c2_bus()
    if not bus:
        raise HTTPException(503, detail="C2 模块不可用")
    if machine == HOSTNAME:
        result = bus.send(machine, "check_environment")
        if result.get("status") == "completed":
            return result.get("output", {})
        return result
    result = bus.send(machine, "check_environment")
    return result


# ═══════════════════════════════════════════════
# 知识库管理 API (可选 - 需要 fastapi)
# ═══════════════════════════════════════════════

try:
    from plugins.kb_api import router as kb_router
    app.include_router(kb_router)
    print("  ✅ 知识库管理 API 已加载")
except Exception as e:
    print(f"  ⏸ 知识库管理 API 未加载: {e}")

# ═══════════════════════════════════════════════
# SMS 短信/代理管理 API
# ═══════════════════════════════════════════════

try:
    from plugins.sms_proxy_api import router as sms_proxy_router
    app.include_router(sms_proxy_router)
    print("  ✅ 短信/代理管理 API 已加载")
except Exception as e:
    print(f"  ⏸ 短信/代理管理 API 未加载: {e}")


if __name__ == "__main__":
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9988
    print(f"📊 系统监控面板 v2.0 — 联邦协同版")
    print(f"   本机: {HOSTNAME}")
    print(f"   → http://localhost:{port}")
    print(f"   插件: {', '.join(_PLUGINS.keys())}")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)

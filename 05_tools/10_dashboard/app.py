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
    return FileResponse(str(index_path)) if index_path.exists() else {"error": "index.html not found"}

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
    """生产列表 (v4 兼容: 委托给插件 detail)"""
    from plugins._registry import get_machine_list
    p = _get_plugin(plugin)
    try:
        data = p.detail()
        # 兼容旧版: 转成列表
        if isinstance(data, dict):
            items = []
            for hn, info in data.items():
                if isinstance(info, dict):
                    info["_source_hostname"] = hn
                    items.append(info)
            data = items
        return {"data": data, "source_hostname": HOSTNAME, "plugin": plugin}
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

    # 持久化 UID 注册表
    reg_path = live_dir / "_registry.json"
    reg_path.write_text(json.dumps(_REGISTERED_UIDS, indent=2, ensure_ascii=False), encoding="utf-8")

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


if __name__ == "__main__":
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9988
    print(f"📊 系统监控面板 v2.0 — 联邦协同版")
    print(f"   本机: {HOSTNAME}")
    print(f"   → http://localhost:{port}")
    print(f"   插件: {', '.join(_PLUGINS.keys())}")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)

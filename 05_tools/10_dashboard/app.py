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
    """联邦机器状态：按 UID 去重, 展示注册名"""
    # 读取所有 live.json (实时 push 数据)
    live_by_uid: dict[str, dict] = {}
    status_dir = _CROSS_MACHINE_DIR / "status"
    if status_dir.exists():
        for host_dir in status_dir.iterdir():
            if not host_dir.is_dir():
                continue
            live_file = host_dir / "live.json"
            if not live_file.exists():
                continue
            try:
                live = json.loads(live_file.read_text())
                uid = live.get("_uid", "")
                if uid:
                    live_by_uid[uid] = live
            except:
                pass

    # 读取 guardd 插件数据（Git 持久层）
    p = _PLUGINS.get("guardd")
    git_machines = p.get_productions() if (p and _AVAILABLE.get("guardd", False)) else []

    # 按 hostname 去重, 优先用注册名
    seen_hostnames = set()
    merged = []
    now = datetime.now(timezone.utc)

    for m in git_machines:
        hn = m.get("hostname", "")
        if hn in seen_hostnames:
            continue
        seen_hostnames.add(hn)
        entry = dict(m)

        # 尝试用 hostname 匹配 live 数据中的 UID
        matched_uid = None
        for uid, live in live_by_uid.items():
            if live.get("hostname", "") == hn:
                matched_uid = uid
                break

        if matched_uid:
            live = live_by_uid[matched_uid]
            received = live.get("_received_at", "")
            if received:
                try:
                    rt = datetime.fromisoformat(received)
                    delta = (now - rt).total_seconds()
                    if delta < 120:
                        entry["_live"] = True
                        entry["_last_push_sec"] = round(delta)
                        entry["_uid"] = matched_uid[:8] + "..."
                        entry["last_seen"] = received
                        entry["status"] = "online"
                except:
                    pass
        if "_live" not in entry:
            entry["_live"] = False
        entry["_source_hostname"] = HOSTNAME
        merged.append(entry)

    # 补充有 push 但无 Git 心跳的机器（新注册未走 Git）
    for uid, live in live_by_uid.items():
        hn = live.get("hostname", "")
        if hn in seen_hostnames:
            continue
        received = live.get("_received_at", "")
        if not received:
            continue
        try:
            rt = datetime.fromisoformat(received)
            delta = (now - rt).total_seconds()
        except:
            delta = 999
        seen_hostnames.add(hn)
        disk = live.get("disk", {})
        merged.append({
            "hostname": hn,
            "status": "online" if delta < 300 else "offline",
            "last_seen": received,
            "os": live.get("os", ""),
            "cpu_load": live.get("cpu", {}).get("load_1m", 0),
            "disk_total_gb": disk.get("total_gb", 0),
            "disk_used_gb": disk.get("used_gb", 0),
            "disk_avail_gb": disk.get("available_gb", 0),
            "guardd_version": live.get("guardd_version", ""),
            "_live": delta < 120,
            "_last_push_sec": round(delta),
            "_uid": uid[:8] + "...",
            "_source_hostname": HOSTNAME,
        })
    return {"machines": merged, "total": len(merged)}

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
    """接收实时心跳推送（反向连接, UID 认证）"""
    uid = data.get("uid", "")
    hostname = data.get("hostname", "unknown")
    if not uid:
        raise HTTPException(400, detail="missing uid")
    if _UID_WHITELIST and uid not in _UID_WHITELIST:
        raise HTTPException(403, detail=f"uid not authorized")
    if uid not in _REGISTERED_UIDS and _ALLOW_AUTO_REGISTER:
        _REGISTERED_UIDS[uid] = {
            "uid": uid, "hostname": hostname,
            "first_seen": datetime.now(timezone.utc).isoformat(),
        }
    hb = data.get("heartbeat", {})
    now = datetime.now(timezone.utc)
    hb["_source"] = "push"
    hb["_received_at"] = now.isoformat()
    hb["_uid"] = uid
    hb["_events"] = data.get("events", [])
    hb["_uptime"] = data.get("uptime", 0)
    # 写入 live.json
    push_dir = _CROSS_MACHINE_DIR / "status" / hostname
    push_dir.mkdir(parents=True, exist_ok=True)
    (push_dir / "live.json").write_text(json.dumps(hb, indent=2, ensure_ascii=False), encoding="utf-8")
    # 追加到时间线历史（保留最近24h/1440条）
    hist = _HEARTBEAT_HISTORY.setdefault(hostname, [])
    hist.append({
        "t": now.isoformat(),
        "cpu": hb.get("cpu", {}).get("load_1m", 0),
        "disk_pct": hb.get("disk", {}).get("used_gb", 0),
        "ts": now.timestamp(),
    })
    if len(hist) > 1440:
        _HEARTBEAT_HISTORY[hostname] = hist[-1440:]
    return {"status": "ok", "hostname": hostname, "uid": uid[:8] + "..."}


@app.get("/api/push/status")
def api_push_status():
    """查看已注册机器状态"""
    items = []
    for uid, info in _REGISTERED_UIDS.items():
        hn = info.get("hostname", "unknown")
        pf = _CROSS_MACHINE_DIR / "status" / hn / "live.json"
        lp = None
        if pf.exists():
            try:
                lp = json.loads(pf.read_text()).get("_received_at")
            except:
                pass
        items.append({
            "uid": uid[:8] + "...", "hostname": hn,
            "first_seen": info.get("first_seen", ""),
            "last_push": lp, "status": "active" if lp else "waiting",
        })
    return {"machines": items, "total": len(items)}


# ═══════════════════════════════════════════════════════════
# 功能 API: 时间线 / 热力图 / 告警 / 升级 / 唤醒 / 日报
# ═══════════════════════════════════════════════════════════

@app.get("/api/timeline/{hostname}")
def api_timeline(hostname: str, window: int = 300):
    """CPU/磁盘变化折线图 (最近window条)"""
    hist = _HEARTBEAT_HISTORY.get(hostname, [])
    return {"hostname": hostname, "points": hist[-window:], "total": len(hist)}


@app.get("/api/heatmap")
def api_heatmap():
    """心跳热力图：各机器24小时活动分布"""
    now = datetime.now(timezone.utc)
    day_ago = now.timestamp() - 86400
    result = {}
    for hostname, hist in _HEARTBEAT_HISTORY.items():
        recent = [p for p in hist if p.get("ts", 0) > day_ago]
        # 按小时分桶
        hourly = [0] * 24
        for p in recent:
            try:
                hr = datetime.fromisoformat(p["t"]).hour
                hourly[hr] += 1
            except:
                pass
        result[hostname] = {
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
    for hostname in _HEARTBEAT_HISTORY:
        hist = _HEARTBEAT_HISTORY[hostname]
        if not hist:
            continue
        last = hist[-1]
        try:
            delta = (now - datetime.fromisoformat(last["t"])).total_seconds()
            if delta > 300:
                alerts.append({
                    "hostname": hostname,
                    "level": "warning" if delta < 900 else "critical",
                    "since_sec": round(delta),
                    "last_seen": last["t"],
                })
        except:
            pass
    # 也检查 Git 心跳文件中有但未 push 的机器
    p = _PLUGINS.get("guardd")
    if p:
        try:
            for m in p.get_productions():
                hn = m.get("hostname", "")
                if hn and hn not in _HEARTBEAT_HISTORY:
                    alerts.append({
                        "hostname": hn,
                        "level": "info",
                        "since_sec": 99999,
                        "note": "未接入实时推送",
                    })
        except:
            pass
    return {"alerts": alerts, "total": len(alerts)}


@app.post("/api/wakeup/{hostname}")
def api_wakeup(hostname: str):
    """一键唤醒：通过任务系统让目标机器跑一次 guardd"""
    task = {
        "id": f"wakeup_{hostname}_{int(time.time())}",
        "type": "run_guardd",
        "target_host": hostname,
        "source_host": HOSTNAME,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }
    task_dir = _CROSS_MACHINE_DIR / "tasks" / "pending"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / f"{task['id']}.json").write_text(
        json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "task_id": task["id"]}


@app.post("/api/upgrade/{hostname}")
def api_upgrade(hostname: str):
    """一键升级：让目标机执行 git pull + 重启 guardd"""
    task = {
        "id": f"upgrade_{hostname}_{int(time.time())}",
        "type": "run_script",
        "script": "cd ~/workbuddy-agent-os/agent-sync && git pull && launchctl kickstart gui/$(id -u)/com.agentos.guardd",
        "target_host": hostname,
        "source_host": HOSTNAME,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }
    task_dir = _CROSS_MACHINE_DIR / "tasks" / "pending"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / f"{task['id']}.json").write_text(
        json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "task_id": task["id"]}


@app.get("/api/daily-summary")
def api_daily_summary():
    """今日联邦日报：汇总各机器的当天事件 + 状态"""
    today = datetime.now().strftime("%Y-%m-%d")
    machines_report = {}
    # 收集各机器推送的 events
    for hostname in _HEARTBEAT_HISTORY:
        hist = _HEARTBEAT_HISTORY[hostname]
        if not hist:
            continue
        last = hist[-1]
        summary = {"ping_count": len(hist), "events": []}
        events = last.get("_events", [])
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
        "total_alerts": len(_HEARTBEAT_HISTORY),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9988
    print(f"📊 系统监控面板 v2.0 — 联邦协同版")
    print(f"   本机: {HOSTNAME}")
    print(f"   → http://localhost:{port}")
    print(f"   插件: {', '.join(_PLUGINS.keys())}")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)

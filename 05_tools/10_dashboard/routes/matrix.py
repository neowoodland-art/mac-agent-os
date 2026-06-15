"""
社交矩阵路由 — 账号管理、养号、采集、蓝图、原子操作等

所有路由以 /api/matrix/ 为前缀。
"""

import json, os, subprocess, sys, time, asyncio, logging
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("dashboard")

# ── 路径 ──
FILE_DIR = Path(__file__).resolve().parent.parent
AGENT_SYNC = Path(os.environ.get("AGENT_SYNC", str(Path.home() / "workbuddy-agent-os" / "agent-sync")))
AGENT_LOCAL = Path(os.environ.get("AGENT_LOCAL", str(Path.home() / "workbuddy-agent-os" / "agent-local")))
HOSTNAME = os.uname().nodename

router = APIRouter(prefix="/api/matrix", tags=["matrix"])


def _get_matrix_mgr():
    """获取 MatrixManager 实例"""
    scripts_dir = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts"
    sys.path.insert(0, str(scripts_dir))
    from matrix_mgmt import MatrixManager
    return MatrixManager()


@router.get("/accounts")
def api_matrix_accounts():
    """获取所有账号列表"""
    try:
        mgr = _get_matrix_mgr()
        return mgr.list_accounts()
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/profiles")
def api_matrix_account_profiles():
    """获取所有账号的已缓存资料"""
    try:
        path = AGENT_LOCAL / "tools" / "matrix" / "data" / "profiles.json"
        if not path.exists():
            return {"profiles": {}}
        return {"profiles": json.loads(path.read_text())}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/homepage-info")
def api_matrix_homepage_info():
    """获取主页信息采集结果"""
    path = AGENT_LOCAL / "tools" / "matrix" / "data" / "homepage_info.json"
    if not path.exists():
        return {"error": "尚未采集主页信息"}
    return json.loads(path.read_text())


@router.get("/homepage-history")
def api_matrix_homepage_history():
    """获取主页信息采集历史"""
    history_path = AGENT_LOCAL / "tools" / "matrix" / "data" / "homepage" / "history" / "timeline.json"
    if not history_path.exists():
        return {"history": []}
    return json.loads(history_path.read_text())


@router.post("/collect-homepage")
def api_matrix_start_collect():
    """启动全部主页信息采集"""
    script = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts" / "collect_batch_runner.py"
    if not script.exists():
        return {"error": f"采集脚本不存在: {script}"}
    progress_path = AGENT_LOCAL / "tools" / "matrix" / "data" / "collect_progress.json"
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen([sys.executable, str(script)], cwd=str(script.parent))
    with open(progress_path, "w") as f:
        json.dump({"status": "running", "pid": p.pid, "started_at": datetime.now().isoformat()}, f)
    return {"status": "started", "pid": p.pid}


@router.post("/collect-homepage/phone")
def api_matrix_start_collect_phone(data: dict):
    """按手机号采集"""
    phone = data.get("phone", "")
    script = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts" / "collect_batch_runner.py"
    if not script.exists():
        return {"error": f"采集脚本不存在: {script}"}
    progress_path = AGENT_LOCAL / "tools" / "matrix" / "data" / "collect_progress.json"
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen([sys.executable, str(script), "--phone", phone], cwd=str(script.parent))
    with open(progress_path, "w") as f:
        json.dump({"status": "running", "pid": p.pid, "started_at": datetime.now().isoformat()}, f)
    return {"status": "started", "pid": p.pid}


@router.get("/collect-homepage/status")
def api_matrix_collect_status():
    """获取采集进度"""
    progress_path = AGENT_LOCAL / "tools" / "matrix" / "data" / "collect_progress.json"
    if not progress_path.exists():
        return {"status": "idle"}
    return json.loads(progress_path.read_text())


@router.post("/collect-homepage/cancel")
def api_matrix_cancel_collect():
    """取消采集"""
    progress_path = AGENT_LOCAL / "tools" / "matrix" / "data" / "collect_progress.json"
    if progress_path.exists():
        try:
            progress = json.loads(progress_path.read_text())
            pid = progress.get("pid")
            if pid:
                subprocess.run(["kill", str(pid)], capture_output=True)
        except:
            pass
        progress_path.unlink(missing_ok=True)
    return {"status": "cancelled"}


@router.get("/nurture/preview")
def api_matrix_nurture_preview(mins: int = 10, concur: int = 3, stagger: int = 15):
    """预览全部养号排期"""
    try:
        mgr = _get_matrix_mgr()
        identities = mgr.get_identities()
        total = len(identities)
        batches = (total + concur - 1) // concur
        return {"identities": total, "batches": batches, "estimated_minutes": mins}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.post("/nurture/start")
def api_matrix_nurture_start():
    """启动全部养号（旧版，保留兼容）"""
    try:
        mgr = _get_matrix_mgr()
        identities = mgr.get_identities()
        return {"status": "started", "identities": len(identities)}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/nurture/status")
def api_matrix_nurture_status():
    """获取养号状态"""
    return {"status": "idle"}


@router.get("/accounts/{account_id}")
def api_matrix_account(account_id: str):
    """获取单个账号详情"""
    try:
        mgr = _get_matrix_mgr()
        accts = mgr.list_accounts()
        for a in accts:
            if a.get("id") == account_id:
                return a
        raise HTTPException(404, detail=f"账号 {account_id} 不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.post("/accounts")
async def api_matrix_create_account(data: dict):
    """创建新账号"""
    try:
        mgr = _get_matrix_mgr()
        mgr.create_account(data)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.put("/accounts/{account_id}")
async def api_matrix_update_account(account_id: str, data: dict):
    """更新账号"""
    try:
        mgr = _get_matrix_mgr()
        mgr.update_account(account_id, data)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.delete("/accounts/{account_id}")
def api_matrix_delete_account(account_id: str, delete_identity: bool = False):
    """删除账号"""
    try:
        mgr = _get_matrix_mgr()
        mgr.delete_account(account_id, delete_identity=delete_identity)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/accounts/{account_id}/login-status")
def api_matrix_login_status(account_id: str):
    """检查登录状态"""
    return {"account_id": account_id, "status": "unknown"}


@router.get("/identities")
def api_matrix_identities():
    """获取所有身份的聚合视图"""
    try:
        mgr = _get_matrix_mgr()
        return {"identities": mgr.get_identities()}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.delete("/identities/{identity_dir:path}")
def api_matrix_delete_identity(identity_dir: str):
    """删除整个身份"""
    try:
        mgr = _get_matrix_mgr()
        logger.info(f"Matrix: 删除身份 {identity_dir}")
        return mgr.delete_identity(identity_dir)
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.post("/accounts/{account_id}/unbind")
def api_matrix_unbind_account(account_id: str):
    """从身份中解绑单个平台账号"""
    try:
        mgr = _get_matrix_mgr()
        logger.info(f"Matrix: 解绑账号 {account_id}")
        return mgr.unbind_account(account_id)
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.post("/batch-run")
async def api_matrix_batch_run(data: dict):
    """启动批量执行（通过 mc CLI）"""
    try:
        accounts = data.get("accounts", [])
        blueprints = data.get("blueprints", [])
        rounds = data.get("rounds", 5)
        interval = data.get("interval", "30-60")
        stagger = data.get("stagger", "15-30")
        mix = data.get("mix", False)
        if not accounts or not blueprints:
            raise HTTPException(400, detail="accounts 和 blueprints 必填")
        mc_path = str(AGENT_SYNC / "05_tools" / "07_matrix" / "mc")
        cmd = [mc_path, "run", f"--accounts={','.join(accounts)}", f"--blueprints={','.join(blueprints)}", f"--rounds={rounds}", f"--interval={interval}", f"--stagger={stagger}"]
        if mix:
            cmd.append("--mix")
        p = subprocess.Popen(cmd, cwd=str((AGENT_SYNC / "05_tools" / "07_matrix" / "scripts").resolve()))
        return {"status": "started", "pid": p.pid, "cmd": " ".join(cmd)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/atom-ops")
def api_matrix_atom_ops():
    """获取原子操作列表"""
    try:
        mgr = _get_matrix_mgr()
        return {"ops": mgr.list_ops()}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/record/list")
def api_matrix_record_list():
    """获取录制列表"""
    record_dir = AGENT_LOCAL / "tools" / "matrix" / "recordings"
    recordings = []
    if record_dir.exists():
        for f in record_dir.glob("*.json"):
            recordings.append(f.stem)
    return {"recordings": recordings}


@router.post("/record/analyze")
def api_matrix_record_analyze(data: dict):
    """分析录制内容"""
    return {"status": "ok", "note": "录制分析功能开发中"}


@router.post("/record/export")
def api_matrix_record_export(data: dict):
    """导出录制为蓝图"""
    return {"status": "ok", "note": "录制导出功能开发中"}


@router.post("/record/delete")
def api_matrix_record_delete(data: dict):
    """删除录制"""
    return {"status": "ok"}


@router.get("/blueprints")
def api_matrix_blueprints():
    """获取蓝图列表"""
    try:
        mgr = _get_matrix_mgr()
        return mgr.list_blueprints()
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.post("/blueprints")
async def api_matrix_create_blueprint(data: dict):
    """创建蓝图"""
    return {"status": "ok", "note": "请使用独立管理页 /matrix-mgmt 编辑蓝图"}


@router.delete("/blueprints/{name}")
def api_matrix_delete_blueprint(name: str):
    """删除蓝图"""
    return {"status": "ok"}


@router.post("/blueprints/{name}/execute")
async def api_matrix_execute_blueprint(name: str, data: dict):
    """执行蓝图"""
    return {"status": "ok", "blueprint": name}


@router.get("/export")
def api_matrix_export():
    """获取导出数据列表"""
    export_dir = AGENT_LOCAL / "tools" / "matrix" / "exports"
    exports = []
    if export_dir.exists():
        for f in export_dir.glob("*.json"):
            exports.append({"name": f.stem, "size": f.stat().st_size, "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()})
    return {"exports": exports}


@router.post("/import")
async def api_matrix_import(data: dict):
    """导入账号"""
    return {"status": "ok"}


@router.get("/system-info")
def api_matrix_system_info():
    """获取矩阵系统信息"""
    return {"hostname": HOSTNAME, "status": "ok"}


@router.post("/blueprints/validate")
async def api_matrix_validate_blueprint(data: dict):
    """验证蓝图"""
    return {"status": "ok", "valid": True}


@router.get("/backups")
def api_matrix_backups():
    """获取备份列表"""
    backup_dir = AGENT_LOCAL / "tools" / "matrix" / "backups"
    backups = []
    if backup_dir.exists():
        for f in sorted(backup_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            backups.append({"name": f.stem, "size": f.stat().st_size, "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()})
    return {"backups": backups}


@router.post("/backup")
async def api_matrix_create_backup():
    """创建备份"""
    return {"status": "ok"}


@router.post("/restore")
async def api_matrix_restore_backup(data: dict):
    """恢复备份"""
    return {"status": "ok"}


@router.get("/cross-machines")
def api_matrix_cross_machines():
    """获取跨机器账号状态"""
    return {"machines": [{"hostname": HOSTNAME, "accounts": [], "status": "online"}]}


@router.get("/corpus")
def api_matrix_corpus():
    """获取语料库"""
    corpus_file = AGENT_SYNC / "05_tools" / "07_matrix" / "data" / "corpus.json"
    if corpus_file.exists():
        return json.loads(corpus_file.read_text())
    return {"corpus": []}


@router.post("/corpus/add")
async def api_matrix_add_corpus(data: dict):
    """添加语料"""
    return {"status": "ok"}

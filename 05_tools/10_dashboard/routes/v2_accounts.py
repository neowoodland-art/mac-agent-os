"""
v2_accounts.py — V2 统一账号管理 API 路由

基于 AccountService 提供联邦账号中心的统一数据视图。
旧 API（matrix.py /api/matrix/accounts）保留兼容。

前缀: /api/v2
"""
import json
import logging
import os
import sys
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("dashboard.routes.v2_accounts")

_THIS_DIR = Path(__file__).resolve().parent.parent
AGENT_SYNC = Path(os.environ.get("AGENT_SYNC", str(Path.home() / "workbuddy-agent-os" / "agent-sync")))
AGENT_LOCAL = Path(os.environ.get("AGENT_LOCAL", str(Path.home() / "workbuddy-agent-os" / "agent-local")))

router = APIRouter(prefix="/api/v2", tags=["v2_accounts"])


def _get_svc():
    """获取 AccountService 实例（延迟导入，单例缓存）"""
    if not hasattr(_get_svc, "_instance"):
        sys.path.insert(0, str(_THIS_DIR))
        from services.account_service import AccountService
        _get_svc._instance = AccountService()
    return _get_svc._instance


# ═══════════════════════════════════════════════════════════
# 账号列表与详情
# ═══════════════════════════════════════════════════════════

@router.get("/accounts")
def api_v2_accounts(
    machine: str = "",
    platform: str = "",
    status: str = "",
    q: str = "",
):
    """获取所有账号的统一视图"""
    try:
        svc = _get_svc()
        accounts = svc.get_all_accounts()

        if machine:
            accounts = [a for a in accounts if a.get("owner_machine") == machine]
        if platform:
            accounts = [a for a in accounts if a.get("platform") == platform]
        if status:
            accounts = [a for a in accounts if a.get("login_status") == status]
        if q:
            lq = q.lower()
            accounts = [a for a in accounts if lq in a["id"].lower() or lq in a.get("phone", "").lower()
                        or lq in a.get("nickname", "").lower() or lq in a.get("identity_dir", "").lower()
                        or lq in a.get("owner_machine", "").lower()]

        return {"accounts": accounts, "total": len(accounts), "generated_at": time.time()}
    except Exception as e:
        logger.error(f"v2/accounts 查询失败: {e}", exc_info=True)
        raise HTTPException(500, detail=str(e))


@router.get("/accounts/{account_id}")
def api_v2_account_detail(account_id: str):
    """获取单个账号详情"""
    try:
        svc = _get_svc()
        acct = svc.get_account_detail(account_id)
        if not acct:
            raise HTTPException(404, detail=f"账号 {account_id} 不存在")
        return acct
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/status-summary")
def api_v2_status_summary():
    """获取账号状态汇总"""
    try:
        svc = _get_svc()
        accounts = svc.get_all_accounts()
        summary = {"total": len(accounts), "logged_in": 0, "cookie_expiring": 0,
                    "no_cookie": 0, "banned": 0, "disabled": 0, "unknown": 0}
        for a in accounts:
            s = a.get("login_status", "unknown")
            if s in summary:
                summary[s] += 1
            else:
                summary["unknown"] += 1
        return summary
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.patch("/accounts/{account_id}")
def api_v2_update_notes(account_id: str, data: dict):
    """更新账号备注/标签

    - 本机账号：写入本机 accounts.yaml（MatrixManager）
    - 远程账号：本地找不到时，tags 写入集中标签文件（agent-local/data/account_tags_cache.json）
    """
    try:
        import yaml
        sys.path.insert(0, str(AGENT_SYNC / "05_tools" / "07_matrix" / "scripts"))
        from matrix_mgmt import MatrixManager
        mgr = MatrixManager()
        update_data = {}
        if "notes" in data:
            update_data["notes"] = data["notes"]
        if "tags" in data:
            update_data["tags"] = data["tags"]
        if not update_data:
            return {"status": "ok"}
        try:
            mgr.update_account(account_id, update_data)
        except ValueError:
            # 远程账号（本机 MatrixManager 无此账号）→ tags 写入集中标签文件
            if "tags" in update_data and update_data["tags"] is not None:
                _save_remote_tags(account_id, update_data["tags"])
            else:
                raise HTTPException(404, detail=f"账号 {account_id} 不存在")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


def _save_remote_tags(account_id: str, tags: list) -> None:
    """远程账号标签 → 集中标签文件（agent-local/data/account_tags_cache.json）

    读取侧 account_service._load_tags_cache 已从此文件读远程 tags，写入即可生效。
    """
    import json as _json
    _CACHE_PATH = AGENT_LOCAL / "data" / "account_tags_cache.json"
    data = {}
    if _CACHE_PATH.exists():
        try:
            data = _json.loads(_CACHE_PATH.read_text())
        except Exception:
            data = {}
    data[account_id] = [str(t) for t in (tags or [])]
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(_json.dumps(data, ensure_ascii=False, indent=1))
    logger.info("  🏷️ 远程账号 %s 标签已保存到集中文件 (%d 条)", account_id, len(data[account_id]))


# ═══════════════════════════════════════════════════════════
# 批量操作
# ═══════════════════════════════════════════════════════════

@router.post("/accounts/batch")
def api_v2_accounts_batch(data: dict):
    """批量操作选中的账号"""
    account_ids = data.get("account_ids", [])
    action = data.get("action", "")
    params = data.get("params", {})

    if not account_ids:
        raise HTTPException(400, detail="account_ids 必填")
    if not action:
        raise HTTPException(400, detail="action 必填")

    valid_actions = ("collect", "login", "nurture", "comment", "record")
    if action not in valid_actions:
        raise HTTPException(400, detail=f"action 必须是 {valid_actions} 之一")

    try:
        from services.command_bus import CommandBus
        svc = _get_svc()
        all_accounts = svc.get_all_accounts()
        acct_map = {a["id"]: a for a in all_accounts}
        machine_groups = {}
        for aid in account_ids:
            a = acct_map.get(aid)
            if not a:
                raise HTTPException(400, detail=f"账号 {aid} 不存在")
            m = a.get("owner_machine", "")
            if m not in machine_groups:
                machine_groups[m] = []
            machine_groups[m].append(aid)

        results = []
        for machine, ids in machine_groups.items():
            r = CommandBus.dispatch(action, ids, params)
            results.append(r)
        return {"status": "ok", "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"v2/accounts/batch 失败: {e}")
        raise HTTPException(500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# 状态刷新
# ═══════════════════════════════════════════════════════════

@router.post("/accounts/refresh")
def api_v2_accounts_refresh(data: dict):
    """强制刷新账号状态"""
    try:
        svc = _get_svc()
        account_ids = data.get("account_ids")
        result = svc.batch_refresh_status(account_ids)
        return {"status": "ok", "refreshed": len(result), "accounts": result}
    except Exception as e:
        raise HTTPException(500, detail=str(e))

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
    """获取所有账号的统一视图

    参数:
        machine: 按机器筛选（空=全部）
        platform: 按平台筛选（douyin / xiaohongshu）
        status: 按状态筛选
        q: 搜索关键词（手机号/昵称/账号ID/身份目录）
    """
    try:
        svc = _get_svc()
        accounts = svc.get_all_accounts()

        # 筛选
        if machine:
            accounts = [a for a in accounts if a.get("owner_machine") == machine]
        if platform:
            accounts = [a for a in accounts if a.get("platform") == platform]
        if status:
            accounts = [a for a in accounts if a.get("login_status") == status]
        if q:
            lq = q.lower()
            accounts = [
                a for a in accounts
                if lq in a["id"].lower()
                or lq in a.get("phone", "").lower()
                or lq in a.get("nickname", "").lower()
                or lq in a.get("identity_dir", "").lower()
                or lq in a.get("owner_machine", "").lower()
            ]

        return {
            "accounts": accounts,
            "total": len(accounts),
            "generated_at": time.time(),
        }
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


# ═══════════════════════════════════════════════════════════
# 批量操作
# ═══════════════════════════════════════════════════════════

@router.post("/accounts/batch")
def api_v2_accounts_batch(data: dict):
    """批量操作选中的账号

    Body:
        account_ids: [str] — 选中的账号ID列表
        action: str — 操作类型 (collect / login / nurture / comment)
        params: dict — 操作参数（选填）

    按机器分组后分别提交到 guardd 执行。
    """
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

        # 获取所有账号信息，按机器分组
        svc = _get_svc()
        all_accounts = svc.get_all_accounts()
        acct_map = {a["id"]: a for a in all_accounts}

        # 按机器分组
        by_machine = {}
        for aid in account_ids:
            acct = acct_map.get(aid)
            if not acct:
                continue
            machine = acct.get("owner_machine", "")
            if machine not in by_machine:
                by_machine[machine] = []
            by_machine[machine].append(aid)

        # 逐个机器提交
        results = []
        for machine, accounts_on_machine in by_machine.items():
            r = CommandBus.dispatch(action, accounts_on_machine, params)
            results.append({
                "machine": machine,
                "account_count": len(accounts_on_machine),
                "accounts": accounts_on_machine,
                "commands": r.get("commands", []),
            })

        return {
            "status": "ok",
            "action": action,
            "total_selected": len(account_ids),
            "machine_count": len(results),
            "machines": results,
        }

    except Exception as e:
        logger.error(f"v2/accounts/batch 失败: {e}")
        raise HTTPException(500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# 状态刷新
# ═══════════════════════════════════════════════════════════

@router.post("/accounts/refresh")
def api_v2_accounts_refresh(data: dict):
    """强制刷新账号状态

    Body:
        account_ids: [str] | null — 指定刷新哪些账号，null 则全部刷新
    """
    try:
        svc = _get_svc()
        account_ids = data.get("account_ids")
        result = svc.batch_refresh_status(account_ids)
        return {
            "status": "ok",
            "refreshed": len(result),
            "accounts": result,
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/status-summary")
def api_v2_status_summary():
    """获取账号状态汇总（用于仪表盘顶部概要）

    Returns:
        {total, logged_in, cookie_expiring, no_cookie, banned, disabled, unknown}
    """
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

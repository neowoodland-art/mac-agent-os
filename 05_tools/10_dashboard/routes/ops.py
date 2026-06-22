"""
routes/ops.py — 统一操作执行路由 v4

基于 command_bus 的完整命令生命周期管理。
所有操作类型通过同一个入口调度。
"""

import logging
from fastapi import APIRouter, HTTPException
from services.command_bus import CommandBus, MachineSession

logger = logging.getLogger("dashboard.ops")
router = APIRouter(prefix="/api/ops", tags=["ops"])


@router.post("/run")
def api_ops_run(data: dict = {}):
    """
    统一操作执行入口

    请求体:
      type: str       — 操作类型 (nurture/collect/login/logout/comment/like)
      accounts: [str] — 账号ID列表
      params: dict    — 操作特定参数（可选）
        blueprint: str  — 蓝图名（nurture 用，不传则自动检测）
        rounds: int     — 轮数（nurture 用，默认 10）
        phone: str      — 手机号（collect 用）
        url: str        — 视频链接（comment/like 用）
        direction: str  — 评论方向（comment 用）
        machine: str    — 强制指定目标机器
        dry_run: bool   — 仅预览不执行
    """
    try:
        op_type = data.get("type", "")
        accounts = data.get("accounts", [])
        params = data.get("params", {})

        if not op_type:
            return {"status": "error", "message": "type 必填 (nurture/collect/login/logout/comment/like)"}
        if not accounts:
            return {"status": "error", "message": "accounts 必填"}

        wait = data.get("wait", False)
        if data.get("dry_run") or params.get("dry_run"):
            params["dry_run"] = True

        result = CommandBus.dispatch(op_type, accounts, params, wait=wait)

        # wait=True 时响应可能包含执行结果摘要
        if wait and result.get("status") == "completed":
            summary = result.get("per_machine", {})
            s = f"完成: "
            for m, info in summary.items():
                s += f"{m}: {info.get('success',0)}成功/{info.get('failed',0)}失败 "
            logger.info(f"批量执行完毕 — {s}")

        return result

    except Exception as e:
        logger.exception("ops/run 失败")
        raise HTTPException(500, detail=str(e))


@router.get("/status")
def api_ops_status(machine: str = None, account: str = None):
    """查询所有命令状态"""
    return {"commands": CommandBus.get_status(machine=machine, account=account)}


@router.get("/history")
def api_ops_history(limit: int = 20):
    """查询命令执行历史（含每台机器的执行结果）"""
    return {"commands": CommandBus.get_status()[:limit]}


@router.get("/machines")
def api_ops_machines():
    """查询所有机器聚合状态"""
    return CommandBus.get_all_machines_status()


@router.post("/test-atom")
def api_ops_test_atom(data: dict = {}):
    """
    单步原子操作测试
    动态生成单步骤蓝图 → 通过 command_bus 执行

    请求体:
      op: str       — 原子操作名称 (goto_home/scroll_feed/like 等)
      account: str  — 账号ID
      platform: str — 平台 (douyin/xiaohongshu)，选填，自动检测
    """
    import json, tempfile, os, uuid
    from pathlib import Path

    op = data.get("op", "")
    account = data.get("account", "")
    platform = data.get("platform", "douyin")

    if not op:
        return {"status": "error", "message": "op 必填"}
    if not account:
        return {"status": "error", "message": "account 必填"}

    try:
        # 动态生成单步骤蓝图
        bp = {
            "id": f"test_{op}_{uuid.uuid4().hex[:8]}",
            "name": f"测试-{op}",
            "description": f"单步测试: {op}",
            "version": "1.0",
            "platform": platform,
            "steps": [{"step_id": 1, "op": op, "args": {}}]
        }

        # 写入临时蓝图文件
        bp_dir = Path(__file__).parent.parent / ".." / "07_matrix" / "blueprints"
        bp_file = bp_dir / f"_test_{op}.json"
        bp_file.parent.mkdir(parents=True, exist_ok=True)
        bp_file.write_text(json.dumps(bp, ensure_ascii=False, indent=2))

        # 执行 (1轮，不等待 → 后台异步执行)
        result = CommandBus.dispatch("nurture", [account], {
            "blueprint": f"_test_{op}".replace(".json",""),
            "rounds": 1,
            "single_op": op,
        }, wait=False)

        # 清理临时蓝图
        if bp_file.exists():
            bp_file.unlink()

        return {
            "status": result.get("status", "submitted"),
            "op": op,
            "account": account,
            "details": result.get("message", result.get("per_machine", "已提交")),
        }

    except Exception as e:
        logger.exception("test-atom 失败")
        raise HTTPException(500, detail=str(e))


@router.post("/cancel/{run_id}")
def api_ops_cancel(run_id: str):
    """取消命令"""
    return CommandBus.cancel(run_id)

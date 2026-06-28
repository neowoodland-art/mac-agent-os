"""
routes/ops.py — 统一操作执行路由 v5

⚠️ 本文件是 Dashboard 通往执行层的唯一入口。
   所有操作（养号/采集/登录/评论/点赞）都经过这里。

调用规范：
   前端统一发 POST /api/ops/run {type, accounts, params}
   → CommandBus.dispatch() → CMD_REGISTRY 模板映射 → mc 引擎

禁止：
   - 在前端直接调用 routes/matrix.py 的 POST 路由
   - 在 routes/matrix.py 中新增 POST 写操作
   - 绕过 CommandBus 直接 subprocess

操作类型（定义在 CMD_REGISTRY 中）：
   - nurture: 养号执行，走 nurture_runner.sh 包装器
   - collect: 主页采集，auto_blueprint 自动按账号平台选蓝图
   - login:   智能登录，走 mc smart-login
   - logout:  登出
   - comment: 定向评论
   - like:    点赞

修复记录:
   2026-06-28: /api/ops/queue 改为 ThreadPoolExecutor 并行查询，避免远程超时堵塞
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


@router.get("/running")
def api_ops_running():
    """聚合所有机器的运行中任务（从 guardd 获取）"""
    from services.command_bus import _guardd_api, HOSTNAME, _get_machine_info
    machines = []
    # 本机
    local_tasks = _guardd_api("GET", "/scheduler/tasks") or {}
    local_active = local_tasks.get("active") or local_tasks
    if local_active:
        machines.append({"machine": HOSTNAME, "tasks": [local_active] if isinstance(local_active, dict) else local_active})
    # 远程机器
    info = _get_machine_info("dummy")
    for name, minfo in getattr(_get_machine_info, "_oracle_machines", {}).items():
        if name == HOSTNAME:
            continue
        ip = minfo.get("tailscale_ip", "")
        if ip:
            remote_tasks = _guardd_api("GET", "/scheduler/tasks", machine=name) or {}
            if remote_tasks:
                machines.append({"machine": name, "tasks": remote_tasks})
    return {"machines": machines}


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


@router.get("/policy")
def api_ops_policy():
    """获取当前执行策略配置（供看板前端展示约束条）"""
    import sys, os
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "07_matrix", "scripts")
    sys.path.insert(0, scripts_dir)
    try:
        from mc.execution_policy import get_policy, preflight as _pf
        policy = get_policy()
        status = _pf()
        policy["current_status"] = status
        return policy
    except Exception as e:
        return {"version": "unknown", "error": str(e), "max_concurrent": 3}


@router.post("/cancel/{run_id}")
def api_ops_cancel(run_id: str):
    """取消命令"""
    return CommandBus.cancel(run_id)


@router.post("/cleanup-stale")
def api_ops_cleanup_stale():
    """清理僵尸命令：进程已死但状态为 running 的标记为 CRASHED，并释放队列"""
    from services.command_bus import cleanup_stale_commands
    count = cleanup_stale_commands()
    return {"status": "ok", "cleaned": count}


@router.get("/log/{run_id}")
def api_ops_log(run_id: str):
    """查看命令日志"""
    from pathlib import Path
    log_dir = Path.home() / "workbuddy-agent-os" / "agent-local" / "runtime" / "commands"
    for f in sorted(log_dir.glob(f"{run_id}*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.exists():
            tail = f.read_text(encoding="utf-8", errors="replace")[-5000:]
            return {"run_id": run_id, "log": tail, "path": str(f)}
    return {"run_id": run_id, "log": "", "path": ""}


@router.get("/queue")
def api_ops_queue(machine: str = None):
    """查看各机任务队列详情（含活跃任务、排队、槽位）

    使用 ThreadPoolExecutor 并行查询所有机器，避免单机超时堵塞整体。
    个别机器超时/离线不影响其他机器结果。
    """
    from services.command_bus import _guardd_api, ORACLE_PATH
    machines = [machine] if machine else []
    if not machines:
        try:
            import yaml
            oracle = yaml.safe_load(ORACLE_PATH.read_text())
            machines = list(oracle.get("machines", {}).keys())
        except Exception:
            machines = [__import__("utils.identity", fromlist=["resolve_hostname"]).resolve_hostname()]

    results = {}

    def query_machine(m):
        """查询单台机器，返回 (machine_name, data)"""
        try:
            data = _guardd_api("GET", "/scheduler/tasks", machine=m)
            if data:
                return (m, data)
            else:
                from services.command_bus import CommandBus
                ms = CommandBus.get_machine_status(m)
                return (m, {"active": ms.get("active_task"), "error": "guardd scheduler 未响应"})
        except Exception as e:
            return (m, {"error": str(e)})

    # 并行查询所有机器（本机快，远程可能超时，但不阻塞彼此）
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=len(machines)) as pool:
        futures = {pool.submit(query_machine, m): m for m in machines}
        for future in as_completed(futures):
            try:
                m, data = future.result()
                results[m] = data
            except Exception as e:
                m = futures[future]
                results[m] = {"error": str(e)}

    return {"machines": results}


@router.post("/task/cancel")
def api_ops_task_cancel(data: dict = {}):
    """取消任务 — 发送到对应机器的 guardd"""
    task_id = data.get("task_id", "")
    machine = data.get("machine", "")
    if not task_id:
        return {"status": "error", "message": "task_id 必填"}
    from services.command_bus import _guardd_api
    result = _guardd_api("POST", f"/task/{task_id}/stop", {}, machine=machine)
    return {"status": "ok", "task_id": task_id, "result": result}


@router.post("/task/submit")
def api_ops_task_submit(data: dict = {}):
    """提交任务到调度器 — 发到目标机器的 guardd"""
    task = data.get("task", {})
    machine = data.get("machine", "")
    if not task.get("task_id"):
        return {"status": "error", "message": "task.task_id 必填"}
    from services.command_bus import _guardd_api
    result = _guardd_api("POST", "/scheduler/submit", task, machine=machine)
    return {"status": "accepted", "result": result}


@router.post("/reset")
def api_ops_reset(data: dict = {}):
    """重置所有机器：清空任务队列 + 重启 guardd"""
    from services.command_bus import _guardd_api, ORACLE_PATH, HOSTNAME
    import yaml, subprocess, time
    
    # Get all machines
    machines = []
    try:
        oracle = yaml.safe_load(ORACLE_PATH.read_text())
        machines = list(oracle.get("machines", {}).keys())
    except:
        machines = [HOSTNAME]
    
    results = {}
    for m in machines:
        try:
            # Call guardd reset endpoint
            r = _guardd_api("POST", "/scheduler/stop", {}, machine=m)
            results[m] = "ok" if r else "no response"
        except Exception as e:
            results[m] = str(e)
    
    return {"status": "ok", "machines": results}

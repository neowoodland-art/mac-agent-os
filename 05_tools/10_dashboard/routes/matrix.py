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

from utils.identity import resolve_hostname

HOSTNAME = resolve_hostname()

router = APIRouter(prefix="/api/matrix", tags=["matrix"])


def _get_matrix_mgr():
    """获取 MatrixManager 实例"""
    scripts_dir = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts"
    sys.path.insert(0, str(scripts_dir))
    from matrix_mgmt import MatrixManager
    return MatrixManager()


@router.get("/accounts")
def api_matrix_accounts():
    """获取所有账号列表（含 profiles 昵称/粉丝数据）"""
    try:
        mgr = _get_matrix_mgr()
        accounts = mgr.list_accounts()
        # 合并 profiles.json 数据（昵称/粉丝/头像）
        profiles_path = AGENT_LOCAL / "tools" / "matrix" / "data" / "profiles.json"
        profiles = {}
        if profiles_path.exists():
            try:
                profiles = json.loads(profiles_path.read_text())
            except Exception:
                pass
        for acct in accounts:
            aid = acct.get("id", "")
            pid = acct.get("identity_dir", "").replace("identities/", "")
            profile = profiles.get(aid) or profiles.get(pid) or {}
            if profile:
                acct["nickname"] = profile.get("nickname", acct.get("nickname", ""))
                acct["fans"] = profile.get("fans", acct.get("fans", ""))
                acct["avatar"] = profile.get("avatar", acct.get("avatar", ""))
                acct["following"] = profile.get("following", acct.get("following", ""))
                acct["likes"] = profile.get("likes", acct.get("likes", ""))
                acct["posts"] = profile.get("posts", acct.get("posts", ""))
            # 从 homepage-info 补充联邦采集数据
            acct["_source_machine"] = acct.get("machine", "")
        return accounts
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
    """获取主页信息采集结果（聚合联邦数据 + 合并 profiles.json）

    数据来源（按优先级）：
      1. fleet_collector 缓存（其他机器数据）
      2. 本机 homepage_info.json
      3. profiles.json 覆盖补全
    """
    # 优先使用联邦采集聚合数据
    try:
        from services.fleet_collector import get_merged_homepage
        hp_data = get_merged_homepage()
    except Exception:
        hp_data = {"results": []}

    # 若联邦聚合无数据，降级到本机文件
    if not hp_data.get("results"):
        hp_path = AGENT_LOCAL / "tools" / "matrix" / "data" / "homepage_info.json"
        hp_data = {"results": []}
        if hp_path.exists():
            try:
                hp_data = json.loads(hp_path.read_text())
            except:
                hp_data = {"results": []}

    pf_path = AGENT_LOCAL / "tools" / "matrix" / "data" / "profiles.json"

    # 获取账号注册表，建立 account_id → identity_dir 映射
    ident_map = {}  # account_id → identity_dir
    phone_map = {}  # account_id → phone
    try:
        from matrix_mgmt import MatrixManager
        mgr = MatrixManager()
        for a in mgr.list_accounts():
            aid = a.get("id", "")
            ident_map[aid] = a.get("identity_dir", aid).replace("identities/", "")
            phone_map[aid] = a.get("phone", "")
    except:
        pass

    # 用 profiles.json 覆盖/补全最新数据
    if pf_path.exists():
        try:
            profiles = json.loads(pf_path.read_text())
            results = hp_data.get("results", [])

            # 1) 建立 (identity_dir → {platform → profile}) 映射（一个身份目录可能有抖音+小红书两个账号）
            prof_by_ident_plat = {}  # identity_dir → {douyin: profile, xiaohongshu: profile}
            prof_by_phone_plat = {}
            for acct_id, prof in profiles.items():
                ident = ident_map.get(acct_id, acct_id)
                phone = phone_map.get(acct_id, "")
                plat = prof.get("platform", "douyin")
                prof_by_ident_plat.setdefault(ident, {})
                prof_by_ident_plat[ident][plat] = prof
                if phone:
                    prof_by_phone_plat.setdefault(phone, {})
                    prof_by_phone_plat[phone][plat] = prof

            tracked = set()

            # 2) 覆盖已有 entry 的数据（按平台分别覆盖）
            for entry in results:
                ident = entry.get("identity_dir", "")
                phone = entry.get("phone", "")
                plat_profs = prof_by_ident_plat.get(ident) or prof_by_phone_plat.get(phone) or {}
                if ident:
                    tracked.add(ident)
                for plat, prof in plat_profs.items():
                    if plat not in entry:
                        entry[plat] = {}
                    p = entry[plat]
                    p["nickname"] = prof.get("nickname", p.get("nickname", ""))
                    p["fans"] = prof.get("fans", p.get("fans", ""))
                    p["likes"] = prof.get("likes", p.get("likes", ""))
                    p["posts"] = prof.get("posts", p.get("posts", ""))
                    p["following"] = prof.get("following", p.get("following", ""))

            # 3) 补全 profiles.json 有但 homepage_info 中没有的条目
            for acct_id, prof in profiles.items():
                ident = ident_map.get(acct_id, acct_id)
                if ident in tracked:
                    continue
                plat = prof.get("platform", "douyin")
                results.append({
                    "identity_dir": ident,
                    "phone": phone_map.get(acct_id, ""),
                    "status": "loaded",
                    plat: {
                        "nickname": prof.get("nickname", ""),
                        "fans": prof.get("fans", ""),
                        "likes": prof.get("likes", ""),
                        "posts": prof.get("posts", ""),
                        "following": prof.get("following", ""),
                    }
                })
                tracked.add(ident)
        except:
            pass

    return hp_data


@router.get("/homepage-history")
def api_matrix_homepage_history():
    """获取主页信息采集历史"""
    history_path = AGENT_LOCAL / "tools" / "matrix" / "data" / "homepage" / "history" / "timeline.json"
    if not history_path.exists():
        return {"history": []}
    return json.loads(history_path.read_text())


@router.post("/collect-homepage")
def api_matrix_start_collect(data: dict = {}):
    """
    启动主页信息采集 — 改为通过 CommandBus 走 mc run 蓝图

    请求体:
      account_ids: [str]  — 要采集的账号ID列表
      account_id: str     — 单账号（兼容旧调用）
    """
    account_ids = data.get("account_ids", [])
    account_id = data.get("account_id", "")
    if account_id and account_id not in account_ids:
        account_ids = [account_id]

    if not account_ids:
        return {"status": "error", "message": "请指定账号"}

    # 通过 CommandBus 分发 mc run 采集蓝图
    mgr = _get_matrix_mgr()
    all_accts = mgr.list_accounts()
    acct_map = {a["id"]: a for a in all_accts}

    # 按平台分组 → 每个平台一次批量命令（让 MC engine 自己排并发）
    platform_bp = {"douyin": "douyin_read_profile", "xiaohongshu": "xiaohongshu_read_profile"}
    platform_groups = {}  # {machine: {platform: [ids]}}

    for aid in account_ids:
        acct = acct_map.get(aid)
        if not acct:
            continue
        machine = acct.get("owner_machine", "chengzigedeAir")
        platform = acct.get("platform", "douyin")
        platform_groups.setdefault(machine, {})
        platform_groups[machine].setdefault(platform, []).append(aid)

    results = []
    from services.command_bus import CommandBus

    for machine, plat_ids in platform_groups.items():
        for platform, ids in plat_ids.items():
            bp = platform_bp.get(platform, "douyin_read_profile")
            cmd_result = CommandBus.dispatch("collect", ids, {
                "blueprint": bp,
                "rounds": 1,
                "dry_run": False,
            })
            results.append({
                "machine": machine,
                "platform": platform,
                "accounts": ids,
                "status": cmd_result.get("status", "dispatched"),
                "commands": cmd_result.get("commands", []),
            })

    return {"status": "ok", "results": results}


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
def api_matrix_nurture_start(data: dict = {}):
    """
    启动账号养号（预检 + 槽位分配 + 错峰启动）

    请求体:
      accounts: [str]    — 账号ID列表（必填）
      blueprint: str     — 蓝图名（可选）
      rounds: int        — 轮数（默认 10）
      machine: str       — 目标机器（可选）
      dry_run: bool      — 仅返回执行计划
    """
    try:
        accounts = data.get("accounts", [])
        if not accounts:
            return {"status": "error", "message": "accounts 必填"}

        custom_blueprint = data.get("blueprint", "")
        rounds = data.get("rounds", 10)
        force_machine = data.get("machine", "")
        dry_run = data.get("dry_run", False)

        mgr = _get_matrix_mgr()
        all_accts = mgr.list_accounts()
        acct_map = {a["id"]: a for a in all_accts}

        PLATFORM_MAP = {"douyin": "douyin_daily", "xiaohongshu": "xhs_daily"}

        plan = []
        for aid in accounts:
            acct = acct_map.get(aid)
            if not acct:
                plan.append({"account": aid, "error": "账号不存在", "ok": False})
                continue
            platform = acct.get("platform", "")
            owner = acct.get("owner_machine", HOSTNAME)
            target_machine = force_machine or owner
            bp = custom_blueprint or PLATFORM_MAP.get(platform, "douyin_daily")
            plan.append({
                "account": aid, "platform": platform, "blueprint": bp,
                "machine": target_machine, "is_local": (target_machine == HOSTNAME),
                "rounds": rounds, "owner": owner, "ok": True,
            })

        if dry_run:
            return {"status": "plan", "plan": plan}

        # 执行 — 按机器分组，每台机器手动分配槽位+错峰
        from services.browser_orchestrator import SLOTS, LAUNCH_STAGGER, verify_started
        from services.remote_exec import exec_remote

        results = []

        # 按机器分组
        machine_groups = {}
        for item in plan:
            if not item["ok"]:
                results.append(item)
                continue
            m = item["machine"]
            if m not in machine_groups:
                machine_groups[m] = []
            machine_groups[m].append(item)

        for machine, items in machine_groups.items():
            is_local = (machine == HOSTNAME)
            slot_idx = 0
            for item in items:
                slot = SLOTS[slot_idx % len(SLOTS)]
                slot_idx += 1
                stagger = (slot_idx - 1) * LAUNCH_STAGGER

                run_id = f"nurture_{int(time.time())}_{item['account']}"
                wrapper = str(AGENT_SYNC / "05_tools" / "10_dashboard" / "services" / "nurture_runner.sh")
                pos_x, pos_y = slot["position"]
                wrapper_cmd = f"bash {wrapper} {item['account']} {item['blueprint']} {item['rounds']} {run_id} {slot['id']} {pos_x} {pos_y}"

                if stagger > 0:
                    logger.info(f"⏳ 养号错峰等待 {stagger}s → {item['account']} (槽位{slot['id']})")
                    time.sleep(stagger)

                if is_local:
                    p = subprocess.Popen(
                        ["bash", wrapper, item["account"], item["blueprint"],
                         str(item["rounds"]), run_id, str(slot["id"]), str(pos_x), str(pos_y)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    time.sleep(3)
                    verified = verify_started(HOSTNAME, item["account"], timeout=10)
                    results.append({
                        "account": item["account"], "status": "started" if verified["running"] else "verify_failed",
                        "run_id": run_id, "pid": p.pid, "verified_pid": verified["pid"],
                        "slot": slot["id"], "position": f"{pos_x},{pos_y}",
                    })
                else:
                    r = exec_remote(machine, wrapper_cmd, timeout=15, fire_and_forget=True)
                    time.sleep(5)
                    verified = verify_started(machine, item["account"], timeout=10)
                    results.append({
                        "account": item["account"], "status": "started" if verified["running"] else "dispatch_only",
                        "run_id": run_id, "slot": slot["id"], "position": f"{pos_x},{pos_y}",
                        "dispatched": r.get("status"), "verified": verified["running"],
                    })

        return {"status": "started", "plan": plan, "results": results}

    except Exception as e:
        logger.exception("nurture/start 执行异常")
        raise HTTPException(500, detail=str(e))


@router.get("/nurture/status")
def api_matrix_nurture_status():
    """返回当前运行状态（含浏览器检测）"""
    try:
        from services.browser_orchestrator import check_running_browsers, get_machine_status
        local_browsers = check_running_browsers()
        ORACLE_PATH = AGENT_SYNC / "ORACLE.yaml"
        remote_machines = []
        if ORACLE_PATH.exists():
            import yaml
            oracle = yaml.safe_load(ORACLE_PATH.read_text())
            for name in oracle.get("machines", {}):
                if name != HOSTNAME:
                    try:
                        remote_machines.append(get_machine_status(name))
                    except:
                        remote_machines.append({"machine": name, "error": "不可达"})
        return {
            "status": "running" if local_browsers else "idle",
            "running_count": len(local_browsers),
            "local_browsers": local_browsers,
            "remote_machines": remote_machines,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/nurture/results")
def api_matrix_nurture_results(limit: int = 20):
    """返回最近养号执行结果"""
    try:
        results_dir = AGENT_LOCAL / "runtime" / "nurture" / "results"
        all_results = []
        if results_dir.exists():
            for f in sorted(results_dir.glob("nurture_*.json"), reverse=True)[:limit]:
                try:
                    data = json.loads(f.read_text())
                    all_results.append(data)
                except:
                    pass
        return {"results": all_results, "total": len(all_results)}
    except Exception as e:
        return {"results": [], "error": str(e)}


@router.get("/nurture/log/{run_id}")
def api_matrix_nurture_log(run_id: str):
    """返回指定 run_id 的详细日志"""
    try:
        log_path = AGENT_LOCAL / "runtime" / "nurture" / "logs" / f"{run_id}.log"
        if not log_path.exists():
            return {"error": f"日志不存在: {run_id}", "log": ""}
        content = log_path.read_text(encoding="utf-8", errors="replace")
        return {"run_id": run_id, "log": content[-5000:]}
    except Exception as e:
        return {"error": str(e), "log": ""}


@router.post("/nurture/cleanup")
def api_matrix_nurture_cleanup(data: dict = {}):
    """清理残留浏览器进程"""
    machine = data.get("machine", HOSTNAME)
    from services.browser_orchestrator import cleanup_stale
    return cleanup_stale(machine)


@router.get("/machine/{machine_name}/status")
def api_machine_status(machine_name: str):
    """获取一台机器的实时状态"""
    from services.browser_orchestrator import get_machine_status
    return get_machine_status(machine_name)


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
        return {"ops": mgr.list_atomic_ops()}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.post("/task/run")
def api_matrix_task_run(data: dict = {}):
    """统一执行评论/点赞等任务 — 通过 CommandBus 走 mc run

    请求体:
      type: str       — comment / like
      account: str    — 账号ID
      url: str        — 视频链接
      direction: str  — 评论方向（可选）
      corpus: str     — 语料库分类（可选）
    """
    task_type = data.get("type", "")
    account = data.get("account", "")
    url = data.get("url", "")

    if not task_type or not account:
        return {"error": "type 和 account 必填"}
    if not url:
        return {"error": "url 必填"}

    # 通过 CommandBus 分发 — 走 mc run 蓝图
    from services.command_bus import CommandBus

    if task_type == "comment":
        blueprint = "douyin_comment"
        params = {"blueprint": blueprint, "rounds": 1, "url": url}
        direction = data.get("direction")
        corpus = data.get("corpus")
        if direction:
            params["direction"] = direction
        if corpus:
            params["corpus"] = corpus
    elif task_type == "like":
        blueprint = "douyin_daily"
        params = {"blueprint": blueprint, "rounds": 1, "url": url}
    else:
        return {"error": f"不支持的任务类型: {task_type}"}

    result = CommandBus.dispatch(task_type, [account], params)
    return {
        "task_id": result.get("status", "dispatched"),
        "account": account,
        "url": url,
        "status": result.get("status", "ok"),
        "commands": result.get("commands", []),
    }

_RECORDING_PID_FILE = AGENT_LOCAL / "runtime" / "recording.pid"


@router.post("/accounts/{account_id}/record")
def api_matrix_account_record(account_id: str):
    """启动交互式录制（自动路由：本地 / 远程）

    检查账号归属机器，如果账号在远程机器上
    则通过 federation 系统在远程启动录制。
    操作方式:
      - Playwright 浏览器自动打开目标平台
      - 浏览器中操作
      - 反引号 `·` 标记步骤（截图+状态指纹）
      - Esc 结束录制并保存
    """
    # 检查账号是否在远程机器
    _target_machine = None
    try:
        from services.command_bus import CommandBus
        machines = CommandBus.get_all_machines_status()
        for m in machines:
            for a in (m.get("accounts") or []):
                if a.get("id") == account_id:
                    owner = a.get("owner_machine", "")
                    if owner and owner != HOSTNAME:
                        _target_machine = owner
                    break
    except:
        pass

    # 远程路由
    if _target_machine:
        import urllib.request, json as _json
        payload = _json.dumps({
            "machine": _target_machine,
            "account": account_id,
            "platform": "xiaohongshu" if account_id.startswith("xhs_") else "douyin"
        }).encode()
        try:
            req = urllib.request.Request(
                f"http://localhost:9988/api/federation/record",
                data=payload, headers={"Content-Type": "application/json"}, method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=10)
            result = _json.loads(resp.read())
            return {"status": "ok", "account": account_id, "machine": _target_machine,
                    "message": f"远程录制已启动 ({_target_machine})，操作后按 `·` 标记，Esc 结束"}
        except Exception as e:
            return {"status": "error", "message": f"远程录制启动失败: {e}"}

    # 本地执行
    if _RECORDING_PID_FILE.exists():
        try:
            pid = int(_RECORDING_PID_FILE.read_text().strip())
            import os, signal
            os.kill(pid, 0)
            return {"status": "ok", "message": f"已有录制进程在运行 (PID {pid})，请先结束再启动新录制"}
        except (ProcessLookupError, ValueError):
            _RECORDING_PID_FILE.unlink(missing_ok=True)

    platform = "douyin"
    if account_id.startswith("xhs_"):
        platform = "xiaohongshu"

    try:
        import subprocess, os, signal
        recorder_py = str(AGENT_SYNC / "05_tools" / "07_matrix" / "scripts" / "mc" / "recorder.py")
        log_dir = AGENT_LOCAL / "runtime" / "commands"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = open(log_dir / f"recorder_{account_id}_{int(time.time())}.log", "w")
        proc = subprocess.Popen(
            [sys.executable, recorder_py, account_id, platform],
            stdout=log_file, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        _RECORDING_PID_FILE.write_text(str(proc.pid))
        return {"status": "ok", "account": account_id, "platform": platform,
                "pid": proc.pid,
                "message": f"录制进程已启动 (PID {proc.pid})，操作后按 `·` 标记步骤，Esc 结束保存"}
    except Exception as e:
        return {"status": "error", "message": f"录制启动失败: {e}"}


@router.post("/record/stop")
def api_matrix_record_stop():
    """停止当前录制进程"""
    if not _RECORDING_PID_FILE.exists():
        return {"status": "ok", "message": "没有正在运行的录制"}
    try:
        pid = int(_RECORDING_PID_FILE.read_text().strip())
        import os, signal
        os.kill(pid, signal.SIGTERM)
        _RECORDING_PID_FILE.unlink(missing_ok=True)
        return {"status": "ok", "message": f"已发送停止信号 (PID {pid})"}
    except ProcessLookupError:
        _RECORDING_PID_FILE.unlink(missing_ok=True)
        return {"status": "ok", "message": "录制进程已结束"}
    except Exception as e:
        return {"status": "error", "message": f"停止失败: {e}"}


@router.get("/record/status")
def api_matrix_record_status():
    """查询录制进程状态"""
    if not _RECORDING_PID_FILE.exists():
        return {"running": False, "status": "idle", "pid": None}
    try:
        pid = int(_RECORDING_PID_FILE.read_text().strip())
        import os, signal
        os.kill(pid, 0)
        return {"running": True, "pid": pid}
    except (ProcessLookupError, ValueError):
        _RECORDING_PID_FILE.unlink(missing_ok=True)
        return {"running": False, "pid": None}


# ═══════════════════════════════════════════════════════════
# 录制 API — 别名兼容（编译产物用 /recordings/ 路径）
# ═══════════════════════════════════════════════════════════

@router.get("/recordings")
def api_matrix_recordings_list():
    """兼容别名: /recordings → /record/list"""
    return api_matrix_record_list()

@router.get("/recordings/stats")
def api_matrix_recordings_stats():
    """录制统计（按账号、平台）"""
    rec_dir = AGENT_LOCAL / "tools" / "matrix" / "recordings"
    stats = {"total": 0, "by_account": {}, "by_platform": {}}
    if not rec_dir.exists():
        return {"stats": stats}
    for f in rec_dir.glob("recording_*.json"):
        try:
            name = f.stem.replace("recording_", "", 1)
            parts = name.split("_")
            acct = parts[0] if parts else "?"
            plat = "douyin" if "douyin" in name else "xiaohongshu"
            stats["total"] += 1
            stats["by_account"][acct] = stats["by_account"].get(acct, 0) + 1
            stats["by_platform"][plat] = stats["by_platform"].get(plat, 0) + 1
        except:
            pass
    return {"stats": stats}

@router.get("/recordings/status")
def api_matrix_recordings_status():
    """兼容别名: /recordings/status → /record/status"""
    return api_matrix_record_status()

@router.post("/record/start")
def api_matrix_record_start(data: dict = {}):
    """兼容别名: /record/start → /accounts/{id}/record"""
    account = data.get("account", "")
    if not account:
        return {"status": "error", "message": "account 必填"}
    return api_matrix_account_record(account)

@router.post("/recordings/start")
def api_matrix_recordings_start(data: dict = {}):
    """兼容别名: /recordings/start → /accounts/{id}/record"""
    account = data.get("account", "")
    if not account:
        return {"status": "error", "message": "account 必填"}
    return api_matrix_account_record(account)

@router.post("/recordings/stop")
def api_matrix_recordings_stop():
    """兼容别名: /recordings/stop → /record/stop"""
    return api_matrix_record_stop()

@router.get("/recordings/{name}")
def api_matrix_recordings_detail(name: str):
    """兼容别名: /recordings/{name} → /record/detail/{name}"""
    return api_matrix_record_detail(name)

@router.post("/recordings/{name}/export")
def api_matrix_recordings_export(name: str):
    """兼容别名: /recordings/{name}/export → /record/export"""
    return api_matrix_record_export({"name": name, "labels": []})

@router.delete("/recordings/{name}")
def api_matrix_recordings_delete(name: str):
    """兼容别名: DELETE /recordings/{name} → /record/delete"""
    return api_matrix_record_delete({"name": name})


@router.get("/screenshot/{screenshot_path:path}")
def api_matrix_screenshot(screenshot_path: str):
    """提供录制截图访问（位于 agent-local，不在 web 根目录下）"""
    from fastapi.responses import FileResponse
    full_path = AGENT_LOCAL / "tools" / "matrix" / "recordings" / "screenshots" / screenshot_path
    if not full_path.exists():
        # 也可能是绝对路径
        alt_path = Path(screenshot_path)
        if alt_path.exists():
            full_path = alt_path
        else:
            raise HTTPException(404, detail="截图不存在")
    return FileResponse(str(full_path))


@router.get("/record/list")
def api_matrix_record_list():
    """获取录制列表"""
    record_dir = AGENT_LOCAL / "tools" / "matrix" / "recordings"
    recordings = []
    if record_dir.exists():
        for f in sorted(record_dir.glob("recording_*.json"), reverse=True):
            try:
                raw = f.read_text(encoding="utf-8")
                meta_end = raw.find('"steps"')
                if meta_end > 0:
                    import re
                    meta_json = raw[:meta_end].rstrip(',\n ') + '}'
                    meta = json.loads(meta_json).get("meta", {})
                else:
                    meta = json.loads(raw).get("meta", {})
                recordings.append({
                    "name": f.stem,
                    "account": meta.get("account_id", "?"),
                    "platform": meta.get("platform", "?"),
                    "steps": meta.get("total_steps", 0),
                    "duration": meta.get("duration", 0),
                    "created": meta.get("created", ""),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                })
            except:
                recordings.append({"name": f.stem, "error": "parse_error"})
    return {"recordings": recordings}


@router.get("/record/detail/{name}")
def api_matrix_record_detail(name: str):
    """获取录制详情（含分析结果）"""
    record_dir = AGENT_LOCAL / "tools" / "matrix" / "recordings"
    f = record_dir / f"{name}.json"
    if not f.exists():
        raise HTTPException(404, detail="录制包不存在")

    try:
        pkg = json.loads(f.read_text(encoding="utf-8"))
    except:
        raise HTTPException(500, detail="录制包解析失败")

    # 运行分析器
    analysis = {"actions": [], "steps_analyzed": 0}
    try:
        sys.path.insert(0, str(AGENT_SYNC / "05_tools" / "07_matrix" / "scripts"))
        from mc.analyzer import analyze_recording
        analysis = analyze_recording(pkg)
    except Exception as e:
        analysis = {"error": str(e)}

    # 组装返回（截图路径转 API URL）
    steps = pkg.get("steps", [])
    for s in steps:
        ss = s.get("screenshot", "")
        if ss and os.path.exists(ss):
            # 绝对路径 → /api/matrix/screenshot/ 相对URL
            s["screenshot_url"] = f"/api/matrix/screenshot/{os.path.basename(ss)}"
        else:
            s["screenshot_url"] = ""

    return {
        "meta": pkg.get("meta", {}),
        "steps": steps,
        "analysis": analysis,
        "total_steps": len(steps),
        "steps_analyzed": analysis.get("steps_analyzed", 0),
        "actions": analysis.get("actions", []),
        "blueprint_suggestions": analysis.get("blueprint_suggestions", []),
    }


@router.post("/record/delete/{name}")
def api_matrix_record_delete(name: str):
    """删除录制包"""
    record_dir = AGENT_LOCAL / "tools" / "matrix" / "recordings"
    f = record_dir / f"{name}.json"
    if not f.exists():
        # 尝试带 .json 后缀
        f2 = record_dir / name
        if f2.exists():
            f = f2
        else:
            return {"status": "error", "message": "录制包不存在"}
    try:
        from mc.recorder import RecordingSession
        RecordingSession.delete_recording(str(f))
        return {"status": "ok", "message": f"已删除: {name}"}
    except Exception as e:
        return {"status": "error", "message": f"删除失败: {e}"}


@router.post("/record/analyze")
def api_matrix_record_analyze(data: dict):
    """分析录制内容 — 已合并到 /record/detail/{name}"""
    name = data.get("name", "")
    if not name:
        return {"status": "error", "message": "name 必填"}
    return api_matrix_record_detail(name)


@router.post("/record/export")
def api_matrix_record_export(data: dict):
    """导出录制为蓝图——根据你的标签生成 JSON 蓝图"""
    name = data.get("name", "")
    labels = data.get("labels", [])       # [{"step":1, "op":"like"}, ...]
    blueprint_name = data.get("blueprint_name", name.replace("recording_", ""))

    if not name or not labels:
        return {"status": "error", "message": "name 和 labels 必填"}

    record_dir = AGENT_LOCAL / "tools" / "matrix" / "recordings"
    f = record_dir / f"{name}.json"
    if not f.exists():
        raise HTTPException(404, detail="录制包不存在")

    try:
        pkg = json.loads(f.read_text(encoding="utf-8"))
    except:
        raise HTTPException(500, detail="录制包解析失败")

    steps = pkg.get("steps", [])
    bp_steps = []
    seen_ops = set()
    for label in labels:
        step_num = label.get("step")
        op = label.get("op", "wait")
        # 去重：跳过连续重复的操作
        if op == seen_ops and op in ("scroll_feed", "wait_watch", "wait"):
            continue
        seen_ops = op
        step = {"step_id": len(bp_steps) + 1, "op": op, "args": label.get("args", {})}
        bp_steps.append(step)

    # 生成蓝图
    blueprint = {
        "id": blueprint_name,
        "name": blueprint_name,
        "platform": pkg.get("meta", {}).get("platform", "douyin"),
        "version": "1.0",
        "source": "recorded",
        "steps": bp_steps,
    }

    # 保存到 blueprints 目录
    blueprints_dir = AGENT_SYNC / "05_tools" / "07_matrix" / "blueprints"
    bp_file = blueprints_dir / f"{blueprint_name}.json"
    bp_file.write_text(json.dumps(blueprint, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"status": "ok", "blueprint": blueprint_name, "steps": len(bp_steps), "file": str(bp_file)}


@router.post("/record/delete")
def api_matrix_record_delete(data: dict):
    """删除录制"""
    name = data.get("name", "")
    if not name:
        return {"status": "error", "message": "name 必填"}
    record_dir = AGENT_LOCAL / "tools" / "matrix" / "recordings"
    f = record_dir / f"{name}.json"
    if f.exists():
        f.unlink()
    return {"status": "ok", "deleted": name}


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


@router.get("/corpus/detail")
def api_matrix_corpus_detail(platform: str = "", category: str = ""):
    """获取指定平台+分类的语料详情"""
    corpus_file = AGENT_SYNC / "05_tools" / "07_matrix" / "data" / "corpus.json"
    if not corpus_file.exists():
        return {"corpus": []}
    data = json.loads(corpus_file.read_text())
    items = data.get("corpus", [])
    if platform:
        items = [i for i in items if i.get("platform", "").lower() == platform.lower()]
    if category:
        items = [i for i in items if i.get("category", "").lower() == category.lower()]
    return {"corpus": items, "total": len(items)}


@router.post("/corpus/batch-add")
async def api_matrix_corpus_batch_add(data: dict):
    """批量添加语料"""
    items = data.get("items", [])
    if not items:
        return {"status": "error", "error": "items 必填"}
    corpus_file = AGENT_SYNC / "05_tools" / "07_matrix" / "data" / "corpus.json"
    existing = {"corpus": []}
    if corpus_file.exists():
        existing = json.loads(corpus_file.read_text())
    existing["corpus"].extend(items)
    corpus_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    return {"status": "ok", "added": len(items), "total": len(existing["corpus"])}


@router.post("/corpus/delete")
async def api_matrix_corpus_delete(data: dict):
    """删除语料"""
    delete_id = data.get("id", "")
    if not delete_id:
        return {"status": "error", "error": "id 必填"}
    corpus_file = AGENT_SYNC / "05_tools" / "07_matrix" / "data" / "corpus.json"
    if not corpus_file.exists():
        return {"status": "error", "error": "语料库为空"}
    existing = json.loads(corpus_file.read_text())
    before = len(existing.get("corpus", []))
    existing["corpus"] = [i for i in existing.get("corpus", []) if i.get("id") != delete_id]
    after = len(existing["corpus"])
    corpus_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    return {"status": "ok", "deleted": before - after}


@router.post("/accounts/{account_id}/login")
def api_matrix_account_login(account_id: str):
    """打开浏览器登录指定账号 — 走 CommandBus 五层分发"""
    from services.command_bus import CommandBus
    result = CommandBus.dispatch("login", [account_id], {})
    if result.get("status") == "accepted":
        return {"status": "ok", "account": account_id, "message": f"登录命令已发送"}
    return {"status": "error", "message": result.get("message", "调度失败")}

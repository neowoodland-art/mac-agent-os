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

# agent-os 统一 venv Python 路径（用于本地和远程 SSH 执行）
PYTHON = str(Path.home() / ".workbuddy" / "binaries" / "python" / "envs" / "agent-os" / "bin" / "python3")
# 远程机器的 Python 路径（动态替换 home 目录）
REMOTE_PYTHON = "$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3"

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
    """
    🚫 DEPRECATED — 数据读取请使用 /api/v2/accounts

    此接口供旧系统（inline.js / modules/）向后兼容。
    所有新的视图代码（views/*.js）已迁移到 /api/v2/accounts。
    新增功能请勿调用此接口。
    """
    logger.warning("🚫 DEPRECATED: /api/matrix/accounts 被调用，请使用 /api/v2/accounts")
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
                acct["industry"] = profile.get("industry", "general")
                # 合并封号状态：profiles.json 中的 status 覆盖通用状态
                pstatus = profile.get("status", "")
                if pstatus == "banned":
                    acct["_status"] = "banned"
                    acct["_banned"] = True
            # 从 homepage-info 补充联邦采集数据
            if not profile:
                fleet_dir = AGENT_LOCAL / "runtime" / "fleet_collector"
                if fleet_dir.exists():
                    for machine_dir in sorted(fleet_dir.iterdir()):
                        try:
                            # 1. 按 identity_dir 查 homepage_info
                            hp_file = machine_dir / "homepage_info.json"
                            if hp_file.exists():
                                hp_data = json.loads(hp_file.read_text())
                                for entry in hp_data.get("results", []):
                                    if entry.get("identity_dir", "").replace("identities/", "") == pid:
                                        for plat_key in ("douyin", "xiaohongshu"):
                                            plat_data = entry.get(plat_key, {}) or {}
                                            if plat_data.get("nickname"):
                                                acct.setdefault("nickname", plat_data["nickname"])
                                                acct.setdefault("fans", str(plat_data.get("fans", "")))
                                                acct.setdefault("avatar", plat_data.get("avatar", ""))
                                                acct.setdefault("following", str(plat_data.get("following", "")))
                                                acct.setdefault("likes", str(plat_data.get("likes", "")))
                                                acct.setdefault("posts", str(plat_data.get("posts", "")))
                                                acct["_source_machine"] = machine_dir.name
                                                break
                                        if acct.get("nickname"):
                                            break
                            # 2. 按 account_id 查 profiles.json
                            if not acct.get("nickname"):
                                pf_file = machine_dir / "profiles.json"
                                if pf_file.exists():
                                    remote_pf = json.loads(pf_file.read_text())
                                    rp = remote_pf.get(aid) or remote_pf.get(pid) or {}
                                    if rp:
                                        acct["nickname"] = rp.get("nickname", acct.get("nickname", ""))
                                        acct["fans"] = str(rp.get("fans", acct.get("fans", "")))
                                        acct["avatar"] = rp.get("avatar", acct.get("avatar", ""))
                                        acct["following"] = str(rp.get("following", acct.get("following", "")))
                                        acct["likes"] = str(rp.get("likes", acct.get("likes", "")))
                                        acct["posts"] = str(rp.get("posts", acct.get("posts", "")))
                                        acct["_source_machine"] = machine_dir.name
                        except Exception:
                            pass
            acct["_source_machine"] = acct.get("machine", acct.get("_source_machine", ""))
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


# ── 废弃：采集入口已统一到 POST /api/ops/run {type:'collect', accounts, params} ──
# 前端 matrix-collect.js 已改走统一入口，CommandBus 注册表自动按账号平台选择蓝图
# collect-homepage/phone、collect-homepage/status、collect-homepage/cancel 一并废弃

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
    """(已废弃) 改用 POST /api/ops/run {type:'nurture', accounts, params}"""
    accounts = data.get("accounts", [])
    if not accounts:
        return {"status": "error", "message": "accounts 必填"}
    from services.command_bus import CommandBus
    result = CommandBus.dispatch("nurture", accounts, {
        "blueprint": data.get("blueprint", "douyin_daily"),
        "rounds": data.get("rounds", 10),
    })
    return {"status": "started", "deprecated": True, "commands": result.get("commands", [])}


@router.get("/nurture/status")
def api_matrix_nurture_status():
    """返回当前运行状态（含浏览器检测）"""
    try:
        # 用 pgrep 直接查本机 Camoufox 进程（不依赖 browser_orchestrator 避免循环导入/挂起）
        local_browsers = []
        try:
            r = subprocess.run(
                ["pgrep", "-f", "camoufox.*--remote-debugging-port|HeadlessShell"],
                capture_output=True, text=True, timeout=5
            )
            if r.stdout.strip():
                for pid in r.stdout.strip().split("\n"):
                    pid = pid.strip()
                    if not pid:
                        continue
                    try:
                        cmd_r = subprocess.run(
                            ["ps", "-p", pid, "-o", "command="],
                            capture_output=True, text=True, timeout=3
                        )
                        local_browsers.append({"pid": int(pid), "cmd": (cmd_r.stdout or "").strip()[:80]})
                    except:
                        pass
        except:
            pass

        # 远程机器
        ORACLE_PATH = AGENT_SYNC / "ORACLE.yaml"
        remote_machines = []
        if ORACLE_PATH.exists():
            import yaml
            oracle = yaml.safe_load(ORACLE_PATH.read_text())
            for name in oracle.get("machines", {}):
                if name != HOSTNAME:
                    try:
                        # 简单 ping + pgrep 检查
                        import subprocess as _sp
                        pr = _sp.run(["ping", "-c", "1", "-W", "2", name],
                                     capture_output=True, timeout=5)
                        alive = pr.returncode == 0
                        remote_machines.append({"machine": name, "alive": alive})
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
    """创建新账号（支持写入远程机器）"""
    import subprocess
    import yaml
    try:
        mgr = _get_matrix_mgr()
        mgr.create_account(data)

        # 更新 ORACLE 机器归属
        owner_machine = data.get("owner_machine", "")
        aid = data.get("id", "")
        if owner_machine and aid:
            try:
                oracle_path = AGENT_SYNC / "ORACLE.yaml"
                if oracle_path.exists():
                    oracle = yaml.safe_load(oracle_path.read_text())
                    changed = False
                    for entry in oracle.get("accounts", []):
                        if aid in entry.get("platforms", {}).values():
                            entry["machine"] = owner_machine
                            changed = True
                            break
                    if not changed:
                        # 新账号添加到 ORACLE
                        plat = data.get("platform", "")
                        # identity 目录名：若传了 identity_dir 则取最后一段，否则用 aid
                        raw_id_dir = data.get("identity_dir", aid)
                        identity_name = raw_id_dir.replace("identities/", "")
                        oracle.setdefault("accounts", []).append({
                            "phone": data.get("phone", ""),
                            "machine": owner_machine,
                            "identity": identity_name,
                            "platforms": {plat: aid},
                        })
                    oracle_path.write_text(yaml.dump(oracle, default_flow_style=False, allow_unicode=True, sort_keys=False))
            except Exception:
                pass

        # 如果指定了远程机器，通过 SSH 写入该机器的 accounts.yaml
        if owner_machine and owner_machine != HOSTNAME:
            # 读取 ORACLE.yaml 获取机器 IP
            oracle_path = AGENT_SYNC / "ORACLE.yaml"
            if oracle_path.exists():
                oracle = yaml.safe_load(oracle_path.read_text())
                machine_cfg = oracle.get("machines", {}).get(owner_machine, {})
                remote_ip = machine_cfg.get("tailscale_ip", "")
                remote_user = machine_cfg.get("ssh_user", owner_machine)
                if remote_ip:
                    aid = data.get("id", "")
                    plat = data.get("platform", "")
                    phone = data.get("phone", "")
                    identity_dir = data.get("identity_dir", f"identities/{aid}")
                    # SSH 到远程机器创建账号（使用远程机器自己的 Python 路径）
                    remote_cmd = (
                        f"cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts && "
                        f"PYTHONPATH=\"$HOME/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts\" "
                        f"{REMOTE_PYTHON} -c "
                        f"\"from matrix_mgmt import MatrixManager; "
                        f"mgr = MatrixManager(); "
                        f"mgr.create_account({{'id':'{aid}','platform':'{plat}',"
                        f"'phone':'{phone}','identity_dir':'{identity_dir}','enabled':True}})\""
                    )
                    try:
                        r = subprocess.run(
                            ["ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no",
                             f"{remote_user}@{remote_ip}", remote_cmd],
                            capture_output=True, text=True, timeout=30
                        )
                        if r.returncode != 0:
                            logger.warning(f"远程创建账号 {aid} 失败 (stderr): {r.stderr.strip()}")
                        else:
                            logger.info(f"远程账号 {aid} 已在 {owner_machine} 创建成功")
                    except subprocess.TimeoutExpired:
                        logger.warning(f"远程创建账号 {aid} 超时 (30s)")
                    except Exception as e:
                        logger.warning(f"远程创建账号 {aid} 异常: {e}")

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
def api_matrix_delete_account(account_id: str):
    """彻底删除账号（配置+身份目录+ORACLE，支持远程机器同步清理）"""
    import yaml
    try:
        mgr = _get_matrix_mgr()
        # 查一下这个账号属于哪台机器（用于远程清理）
        owner_machine = ""
        try:
            oracle_path = AGENT_SYNC / "ORACLE.yaml"
            if oracle_path.exists():
                oracle = yaml.safe_load(oracle_path.read_text())
                for entry in oracle.get("accounts", []):
                    for plat, aid in entry.get("platforms", {}).items():
                        if aid == account_id:
                            owner_machine = entry.get("machine", "") or entry.get("assigned_machine", "")
                            break
        except Exception:
            pass

        # 删除本地配置 + 身份目录
        mgr.delete_account(account_id, delete_identity=True)

        # 从 ORACLE.yaml 中移除
        try:
            oracle_path = AGENT_SYNC / "ORACLE.yaml"
            if oracle_path.exists():
                oracle = yaml.safe_load(oracle_path.read_text())
                before = len(oracle.get("accounts", []))
                oracle["accounts"] = [
                    e for e in oracle.get("accounts", [])
                    if not any(account_id in v for v in e.get("platforms", {}).values())
                ]
                if len(oracle["accounts"]) < before:
                    oracle_path.write_text(
                        yaml.dump(oracle, default_flow_style=False, allow_unicode=True, sort_keys=False)
                    )
                    # 清除 AccountService 的 60 秒缓存，让后续查询立即读新数据
                    try:
                        from services.account_service import AccountService
                        svc = AccountService()
                        svc._oracle = None
                        svc._oracle_loaded = 0
                    except Exception:
                        pass
        except Exception:
            pass

        # 如果是远程机器的账号，SSH 同步删除
        if owner_machine and owner_machine != HOSTNAME:
            try:
                oracle_path = AGENT_SYNC / "ORACLE.yaml"
                if oracle_path.exists():
                    oracle = yaml.safe_load(oracle_path.read_text())
                    machine_cfg = oracle.get("machines", {}).get(owner_machine, {})
                    remote_ip = machine_cfg.get("tailscale_ip", "")
                    remote_user = machine_cfg.get("ssh_user", owner_machine)
                    if remote_ip:
                        remote_cmd = (
                            f"cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts && "
                            f"PYTHONPATH=\"$HOME/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts\" "
                            f"{REMOTE_PYTHON} -c "
                            f"\"from matrix_mgmt import MatrixManager; "
                            f"mgr = MatrixManager(); "
                            f"mgr.delete_account('{account_id}', delete_identity=True)\""
                        )
                        subprocess.run(
                            ["ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no",
                             f"{remote_user}@{remote_ip}", remote_cmd],
                            capture_output=True, text=True, timeout=30
                        )
            except Exception:
                pass

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
    """(已废弃) 改用 POST /api/ops/run {type, accounts, params}"""
    task_type = data.get("type", "")
    account = data.get("account", "")
    if not task_type or not account:
        return {"error": "type 和 account 必填"}
    from services.command_bus import CommandBus
    params = {"rounds": 1}
    if data.get("url"): params["url"] = data["url"]
    if data.get("direction"): params["direction"] = data["direction"]
    if data.get("corpus"): params["corpus"] = data["corpus"]
    result = CommandBus.dispatch(task_type, [account], params)
    return {"deprecated": True, "status": result.get("status", "ok"), "commands": result.get("commands", [])}

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
        scripts_dir = str(AGENT_SYNC / "05_tools" / "07_matrix" / "scripts")
        recorder_py = str(AGENT_SYNC / "05_tools" / "07_matrix" / "scripts" / "mc" / "recorder.py")
        log_dir = AGENT_LOCAL / "runtime" / "commands"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"recorder_{account_id}_{int(time.time())}.log"
        log_file = open(log_path, "w")
        # 设置环境变量：PYTHONPATH + AGENT_SYNC/AGENT_LOCAL
        rec_env = os.environ.copy()
        rec_env["PYTHONPATH"] = f"{scripts_dir}:{rec_env.get('PYTHONPATH', '')}"
        rec_env["AGENT_SYNC"] = str(AGENT_SYNC)
        rec_env["AGENT_LOCAL"] = str(AGENT_LOCAL)
        proc = subprocess.Popen(
            [sys.executable, recorder_py, account_id, platform],
            stdout=log_file, stderr=subprocess.STDOUT,
            start_new_session=True,
            env=rec_env,
        )
        log_file.write(f"recorder启动: account={account_id} platform={platform} pid={proc.pid}\nenv PYTHONPATH={scripts_dir}\n")
        log_file.flush()
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
    """获取录制列表（本机 + 联邦聚合）"""
    from services.command_bus import _guardd_api, HOSTNAME as CB_HOSTNAME

    seen = set()
    recordings = []

    # 1. 本机录制
    record_dir = AGENT_LOCAL / "tools" / "matrix" / "recordings"
    if record_dir.exists():
        for f in sorted(record_dir.glob("recording_*.json"), reverse=True):
            try:
                raw = f.read_text(encoding="utf-8")
                meta_end = raw.find('"steps"')
                if meta_end > 0:
                    meta_json = raw[:meta_end].rstrip(',\n ') + '}'
                    meta = json.loads(meta_json).get("meta", {})
                else:
                    meta = json.loads(raw).get("meta", {})
                rec = {
                    "name": f.stem,
                    "account": meta.get("account_id", "?"),
                    "platform": meta.get("platform", "?"),
                    "machine": meta.get("machine", HOSTNAME),
                    "phone": meta.get("phone", ""),
                    "nickname": meta.get("nickname", ""),
                    "steps": meta.get("total_steps", 0),
                    "duration": meta.get("duration", 0),
                    "created": meta.get("created", ""),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                }
                seen.add(f.stem)
                recordings.append(rec)
            except:
                recordings.append({"name": f.stem, "error": "parse_error", "machine": HOSTNAME})

    # 2. 远程机器录制（通过 guardd API）
    try:
        import yaml
        oracle_path = AGENT_SYNC / "ORACLE.yaml"
        if oracle_path.exists():
            oracle_data = yaml.safe_load(oracle_path.read_text())
            all_machines = list(oracle_data.get("machines", {}).keys())
        else:
            all_machines = ["5kechengdeAir", "7kecheng"]
        for machine in all_machines:
            if machine == HOSTNAME:
                continue
            try:
                data = _guardd_api("GET", "/recordings", machine=machine)
                if not data or not isinstance(data, dict):
                    continue
                remote_recs = data.get("recordings", [])
                for r in remote_recs:
                    rname = r.get("name", "").replace(".json", "")
                    if rname not in seen:
                        seen.add(rname)
                        r["name"] = rname
                        r.setdefault("machine", machine)
                        recordings.append(r)
            except Exception:
                pass
    except Exception:
        pass

    # 按时间倒序
    recordings.sort(key=lambda x: x.get("created", ""), reverse=True)
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


@router.get("/diag/accounts")
def api_matrix_diag_accounts():
    """诊断：追踪单个账号的完整数据链"""
    result = {
        "steps": {},
        "error": None,
    }
    try:
        # Step 1: ORACLE.yaml 中的账号声明
        oracle_path = AGENT_SYNC / "ORACLE.yaml"
        if oracle_path.exists():
            import yaml
            oracle = yaml.safe_load(oracle_path.read_text())
            result["steps"]["oracle_accounts"] = len(oracle.get("accounts", []))

        # Step 2: accounts.yaml 配置
        mgr = _get_matrix_mgr()
        accounts = mgr.list_accounts()
        result["steps"]["yaml_accounts"] = len(accounts)
        # 只看第一个远程账号的完整数据
        sample = None
        for a in accounts:
            if a.get("owner_machine") and a.get("owner_machine") != HOSTNAME:
                sample = {k: v for k, v in a.items() if not k.startswith("_")}
                sample["_status"] = a.get("_status")
                sample["owner_machine"] = a.get("owner_machine")
                break
        result["steps"]["sample_account"] = sample

        # Step 3: 本地 profiles.json
        pf_local = AGENT_LOCAL / "tools" / "matrix" / "data" / "profiles.json"
        if pf_local.exists():
            pf_data = json.loads(pf_local.read_text())
            result["steps"]["local_profiles_count"] = len(pf_data)
            if sample:
                aid = sample.get("id", "")
                pid = sample.get("identity_dir", "").replace("identities/", "")
                result["steps"]["local_profiles_by_aid"] = pf_data.get(aid, "NOT FOUND")
                result["steps"]["local_profiles_by_pid"] = pf_data.get(pid, "NOT FOUND")
        else:
            result["steps"]["local_profiles_count"] = "FILE NOT FOUND"

        # Step 4: fleet_collector 缓存
        fleet_dir = AGENT_LOCAL / "runtime" / "fleet_collector"
        result["steps"]["fleet_cache"] = {}
        if fleet_dir.exists():
            for md in sorted(fleet_dir.iterdir()):
                cache_entry = {"has_homepage": False, "has_profiles": False, "collected_at": ""}
                hp_file = md / "homepage_info.json"
                if hp_file.exists():
                    cache_entry["has_homepage"] = True
                    hp_data = json.loads(hp_file.read_text())
                    cache_entry["homepage_count"] = len(hp_data.get("results", []))
                    # 找 sample 账号
                    if sample:
                        pid = sample.get("identity_dir", "").replace("identities/", "")
                        for entry in hp_data.get("results", []):
                            if entry.get("identity_dir", "").replace("identities/", "") == pid:
                                cache_entry["homepage_match"] = entry
                                break
                pf_file = md / "profiles.json"
                if pf_file.exists():
                    cache_entry["has_profiles"] = True
                    pf_data = json.loads(pf_file.read_text())
                    cache_entry["profiles_count"] = len(pf_data)
                    if sample:
                        aid = sample.get("id", "")
                        cache_entry["profiles_by_aid"] = pf_data.get(aid, "NOT FOUND")
                ca_file = md / "collected_at.txt"
                if ca_file.exists():
                    cache_entry["collected_at"] = ca_file.read_text().strip()[:19]
                result["steps"]["fleet_cache"][md.name] = cache_entry
        else:
            result["steps"]["fleet_cache"]["status"] = "NOT CREATED"

        # Step 5: API 最终返回
        final = {}
        if sample:
            aid = sample.get("id", "")
            pid = sample.get("identity_dir", "").replace("identities/", "")
            # 模拟 API 合并逻辑
            pf_local_data = json.loads(pf_local.read_text()) if pf_local.exists() else {}
            profile = pf_local_data.get(aid) or pf_local_data.get(pid) or {}
            final["from_local_profiles"] = profile.get("nickname", "-") if profile else "NOT FOUND"
            if not profile:
                # fleet collector fallback
                for md in sorted(fleet_dir.iterdir()):
                    hp_file = md / "homepage_info.json"
                    if hp_file.exists():
                        hp_data = json.loads(hp_file.read_text())
                        for entry in hp_data.get("results", []):
                            if entry.get("identity_dir", "").replace("identities/", "") == pid:
                                for pk in ("douyin", "xiaohongshu"):
                                    pd = entry.get(pk, {}) or {}
                                    if pd.get("nickname"):
                                        final["from_fleet_homepage"] = pd["nickname"]
                                        final["from_fleet_machine"] = md.name
                                        break
                            if final.get("from_fleet_homepage"):
                                break
                    if final.get("from_fleet_homepage"):
                        break
        result["steps"]["final_api_nickname"] = final.get("from_fleet_homepage") or final.get("from_local_profiles") or "EMPTY!"
        result["steps"]["final_source"] = "fleet" if "from_fleet_homepage" in final else ("local" if "from_local_profiles" in final else "NONE")

    except Exception as e:
        import traceback
        result["error"] = f"{e}\n{traceback.format_exc()}"
    return result


@router.get("/corpus")
def api_matrix_corpus():
    """获取语料库概览（按平台+分类统计）"""
    try:
        from mc.corpus import CorpusManager
        cm = CorpusManager()
        cats = cm.list_categories()
        # 同时获取三阶场景数据
        scenes = cm.list_scenes()
        return {"categories": cats, "scenes": scenes, "total_comments": sum(c.get("count", 0) for c in cats)}
    except Exception as e:
        return {"categories": [], "scenes": [], "total_comments": 0, "error": str(e)}


@router.get("/corpus/category")
def api_matrix_corpus_category(platform: str = "douyin", category: str = ""):
    """获取指定分类的详情（所有评论+模板）"""
    if not category:
        return {"error": "category 必填"}
    try:
        from mc.corpus import CorpusManager
        cm = CorpusManager()
        data = cm._load(platform)
        cat = data.get("categories", {}).get(category, {})
        return {
            "platform": platform,
            "category": category,
            "label": cat.get("label", category),
            "weight": cat.get("weight", 10),
            "enabled": cat.get("enabled", True),
            "accessible": cat.get("accessible", []),
            "comments": cat.get("comments", []),
            "templates": cat.get("templates", []),
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/corpus/add")
async def api_matrix_add_corpus(data: dict):
    """添加一条评论"""
    platform = data.get("platform", "douyin")
    category = data.get("category", "")
    text = data.get("text", "")
    if not category or not text:
        return {"status": "error", "error": "category 和 text 必填"}
    try:
        from mc.corpus import CorpusManager
        cm = CorpusManager()
        cm.add_comment(category, text, platform)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/corpus/batch-add")
async def api_matrix_corpus_batch_add(data: dict):
    """批量添加语料（逐条处理）"""
    platform = data.get("platform", "douyin")
    category = data.get("category", "")
    texts = data.get("texts", [])
    if not category or not texts:
        return {"status": "error", "error": "category 和 texts 必填"}
    try:
        from mc.corpus import CorpusManager
        cm = CorpusManager()
        added = 0
        for t in texts:
            if t.strip():
                cm.add_comment(category, t.strip(), platform)
                added += 1
        return {"status": "ok", "added": added}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/corpus/delete")
async def api_matrix_corpus_delete(data: dict):
    """删除指定索引的评论"""
    platform = data.get("platform", "douyin")
    category = data.get("category", "")
    index = data.get("index", -1)
    if not category or index < 0:
        return {"status": "error", "error": "category 和 index 必填"}
    try:
        from mc.corpus import CorpusManager
        cm = CorpusManager()
        cm.delete_comment(category, index, platform)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/corpus/category/save")
async def api_matrix_corpus_category_save(data: dict):
    """保存分类设置（权重/启用/标签）"""
    platform = data.get("platform", "douyin")
    category = data.get("category", "")
    updates = {k: v for k, v in data.items() if k in ("weight", "enabled", "label")}
    if not category:
        return {"status": "error", "error": "category 必填"}
    try:
        from mc.corpus import CorpusManager
        cm = CorpusManager()
        cm.update_category(platform, category, **updates)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/corpus/scenes")
def api_matrix_corpus_scenes():
    """获取三阶场景语料"""
    try:
        from mc.corpus import CorpusManager
        cm = CorpusManager()
        scenes = cm.list_scenes()
        # 按场景类型分组
        groups = {"first_comment": [], "reply": [], "re_reply": []}
        for s in scenes:
            scene_id = s.get("id", "")
            if scene_id in groups:
                groups[scene_id].append(s)
        return {"scenes": scenes, "groups": groups}
    except Exception as e:
        return {"scenes": [], "groups": {}, "error": str(e)}


@router.post("/accounts/{account_id}/login")
def api_matrix_account_login(account_id: str):
    """打开浏览器登录指定账号 — 小红书走全自动 SMS，抖音走 CommandBus"""
    # 判断平台
    platform = "douyin"
    try:
        from matrix_mgmt import MatrixManager
        for a in MatrixManager().list_accounts():
            if a["id"] == account_id:
                p = a.get("platform", "")
                if p == "xiaohongshu":
                    platform = "xiaohongshu"
                break
    except Exception:
        pass

    if platform == "xiaohongshu":
        # 小红书：直接启动全自动 SMS 登录
        import subprocess
        scripts_dir = str(AGENT_SYNC / "05_tools" / "07_matrix" / "scripts")
        login_script = scripts_dir + "/matrix_modules/account/xiaohongshu_login.py"
        env = {**os.environ, "PYTHONPATH": scripts_dir, "AGENT_SYNC": str(AGENT_SYNC), "AGENT_LOCAL": str(AGENT_LOCAL)}
        try:
            proc = subprocess.Popen(
                [sys.executable, login_script, account_id, "--force"],
                env=env, start_new_session=True,
            )
            return {"status": "ok", "account": account_id, "message": f"小红书登录已启动 (PID {proc.pid})，浏览器自动处理验证码"}
        except Exception as e:
            return {"status": "error", "message": f"启动失败: {e}"}
    else:
        # 抖音：走现有 CommandBus
        from services.command_bus import CommandBus
        result = CommandBus.dispatch("login", [account_id], {})
        if result.get("status") == "accepted":
            return {"status": "ok", "account": account_id, "message": f"登录命令已发送"}
        return {"status": "error", "message": result.get("message", "调度失败")}

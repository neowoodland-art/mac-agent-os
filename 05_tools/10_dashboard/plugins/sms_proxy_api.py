"""
sms_proxy_api.py — 短信接收 + 代理管理 API

提供 Dashboard 接口，用于查看/测试短信API配置、代理状态。
版本: 1.0.0 | 更新: 2026-06-01
"""
import json, os, subprocess, sys
from pathlib import Path
from datetime import datetime

HOME = Path.home()
AGENT_SYNC = Path(os.environ.get("AGENT_SYNC", str(HOME / "workbuddy-agent-os" / "agent-sync")))
AGENT_LOCAL = Path(os.environ.get("AGENT_LOCAL", str(HOME / "workbuddy-agent-os" / "agent-local")))

SCRIPTS_DIR = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts"
IDENTITIES_ROOT = AGENT_LOCAL / "tools" / "matrix" / "identities"

sys.path.insert(0, str(SCRIPTS_DIR))

# 本机主机名
_HN_FILE = AGENT_LOCAL / "identity" / "cached_hostname"
if _HN_FILE.exists():
    HOSTNAME = _HN_FILE.read_text().strip()
else:
    import socket
    HOSTNAME = socket.gethostname()
if not HOSTNAME:
    HOSTNAME = "unknown"

SMS_YAML = SCRIPTS_DIR / "config" / "sms.yaml"

# 预导入账号管理
try:
    from matrix_mgmt import MatrixManager
    _matrix_mgmt_ok = True
except Exception as e:
    _matrix_mgmt_ok = False
    _matrix_mgmt_err = str(e)


class SMSManager:
    """短信API管理"""

    @staticmethod
    def get_config() -> dict:
        """读取当前SMS配置"""
        try:
            import yaml
            if SMS_YAML.exists():
                data = yaml.safe_load(SMS_YAML.read_text())
                return data.get("sms", {})
        except:
            pass
        return {}

    @staticmethod
    def update_config(phone: str = None, api_key: str = None, base_url: str = None) -> dict:
        """更新SMS配置"""
        try:
            import yaml
            cfg = {}
            if SMS_YAML.exists():
                cfg = yaml.safe_load(SMS_YAML.read_text()) or {}
            if "sms" not in cfg:
                cfg["sms"] = {}

            if phone: cfg["sms"]["phone"] = phone
            if api_key: cfg["sms"]["api_key"] = api_key
            if base_url: cfg["sms"]["base_url"] = base_url

            SMS_YAML.write_text(yaml.dump(cfg, default_flow_style=False, allow_unicode=True))
            return {"status": "ok", "config": cfg["sms"]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def test_receive(phone: str, timeout: int = 15) -> dict:
        """测试指定手机号的短信接收"""
        from urllib.request import Request, urlopen
        import time
        cfg = SMSManager.get_config()
        api_key = cfg.get("api_key", "gtmsg2026")
        base_url = cfg.get("base_url", "https://wx.tyhtak.com/api/biz/msg/messages")

        url = f"{base_url}?api_key={api_key}&receiver_phone={phone}&page=1&per_page=10"
        try:
            req = Request(url, headers={"User-Agent": "curl/7.0"})
            resp = urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            total = data.get("data", {}).get("total", 0)
            items = data.get("data", {}).get("items", [])
            latest = []
            for item in items[:5]:
                import re
                c = item.get("content", "")
                code = re.search(r"验证码[：:，,]\s*(\d{4,6})", c)
                latest.append({
                    "id": item.get("id"),
                    "content": c[:80],
                    "code": code.group(1) if code else None,
                    "time": item.get("created_at", ""),
                })
            return {
                "status": "ok",
                "phone": phone,
                "total": total,
                "messages": latest,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


class ProxyManager:
    """代理管理"""

    @staticmethod
    def get_all_proxies() -> list[dict]:
        """获取所有账号的代理配置"""
        try:
            from matrix_mgmt import MatrixManager
            mgr = MatrixManager()
            accounts = mgr.list_accounts()
        except Exception as e:
            return [{"error": str(e)}]

        results = []
        for a in accounts:
            if not a.get("is_local"):
                continue
            aid = a["id"]
            identity_dir = IDENTITIES_ROOT / aid
            config_path = identity_dir / "config.yaml"
            proxy = None
            if config_path.exists():
                try:
                    import yaml
                    data = yaml.safe_load(config_path.read_text())
                    proxy = data.get("identity", {}).get("proxy", None)
                except:
                    pass
            results.append({
                "account": aid,
                "platform": a.get("platform", ""),
                "proxy": proxy,
                "has_proxy": proxy is not None and str(proxy).strip() not in ("null", "None", ""),
                "login_status": a.get("_status", "unknown"),
            })
        return results

    @staticmethod
    def set_proxy(account_id: str, proxy: str) -> dict:
        """设置账号代理"""
        identity_dir = IDENTITIES_ROOT / account_id
        config_path = identity_dir / "config.yaml"
        if not config_path.exists():
            return {"status": "error", "error": f"账号 {account_id} 身份目录不存在"}

        try:
            import yaml
            data = yaml.safe_load(config_path.read_text()) or {}
            if "identity" not in data:
                data["identity"] = {}
            data["identity"]["proxy"] = proxy if proxy.strip() else None
            config_path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))
            return {"status": "ok", "account": account_id, "proxy": proxy}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def test_proxy(proxy: str) -> dict:
        """测试代理连通性"""
        import urllib.request
        try:
            start = datetime.now()
            if proxy and str(proxy).strip() not in ("null", "None", ""):
                handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
                opener = urllib.request.build_opener(handler)
                resp = opener.open("http://httpbin.org/ip", timeout=10)
                data = json.loads(resp.read().decode())
                elapsed = (datetime.now() - start).total_seconds()
                # 提取代理类型
                proxy_type = "HTTP"
                if proxy.startswith("socks5://") or proxy.startswith("socks://"):
                    proxy_type = "SOCKS5"
                elif proxy.startswith("socks4://"):
                    proxy_type = "SOCKS4"
                elif proxy.startswith("https://"):
                    proxy_type = "HTTPS"
                return {
                    "status": "ok",
                    "ip": data.get("origin", ""),
                    "type": proxy_type,
                    "elapsed": f"{elapsed:.1f}s",
                    "speed": "快" if elapsed < 0.5 else ("中" if elapsed < 2 else "慢"),
                }
            else:
                # 直连测试
                resp = urllib.request.urlopen("http://httpbin.org/ip", timeout=10)
                data = json.loads(resp.read().decode())
                elapsed = (datetime.now() - start).total_seconds()
                return {"status": "ok", "ip": data.get("origin", ""), "elapsed": f"{elapsed:.1f}s", "direct": True}
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ═══ FastAPI 路由 ═══
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/matrix", tags=["matrix"])
_sms = SMSManager()
_proxy = ProxyManager()


@router.get("/sms/config")
def api_sms_config():
    return _sms.get_config()


@router.put("/sms/config")
def api_sms_update(data: dict):
    return _sms.update_config(
        phone=data.get("phone"),
        api_key=data.get("api_key"),
        base_url=data.get("base_url"),
    )


@router.get("/sms/test/{phone}")
def api_sms_test(phone: str, timeout: int = 15):
    return _sms.test_receive(phone, timeout)


@router.get("/proxies")
def api_proxies():
    return {"proxies": _proxy.get_all_proxies()}


@router.put("/proxies/{account_id}")
def api_proxy_set(account_id: str, data: dict):
    return _proxy.set_proxy(account_id, data.get("proxy", ""))


@router.post("/proxies/test")
def api_proxy_test(data: dict):
    return _proxy.test_proxy(data.get("proxy", ""))


# ═══════════════════════════════════════════════
# SMS 账号管理 & 注册 API
# ═══════════════════════════════════════════════

def _account_status(a: dict) -> dict:
    """四维状态检测：identity / cookie / profile / registry"""
    aid = a["id"]
    # ① 有身份目录（使用 identity_dir 字段，兼容共享身份）
    ident_name = a.get("identity_dir") or a.get("identity_hint") or aid
    identity_dir = IDENTITIES_ROOT / ident_name.replace("identities/", "")
    has_identity = identity_dir.exists()
    # ② 有 Cookie（已登录）
    has_cookie = False
    if has_identity:
        ck = identity_dir / "user_data" / "cookies.sqlite"
        if ck.exists() and ck.stat().st_size > 100:
            try:
                import sqlite3
                conn = sqlite3.connect(str(ck), timeout=1)
                cnt = conn.execute("SELECT count(*) FROM moz_cookies WHERE name LIKE '%session%'").fetchone()[0]
                conn.close()
                has_cookie = cnt > 0
            except:
                pass
    # ③ 有昵称（已采集 profile）
    has_profile = False
    profiles_path = AGENT_LOCAL / "tools" / "matrix" / "data" / "profiles.json"
    if profiles_path.exists():
        try:
            profiles = json.loads(profiles_path.read_text())
            p = profiles.get(aid, {})
            nick = p.get("nickname", "")
            if nick and nick != aid:
                has_profile = True
        except: pass
    # 也检查 homepage_info.json（新采集系统）
    if not has_profile:
        hp_path = AGENT_LOCAL / "tools" / "matrix" / "data" / "homepage_info.json"
        if hp_path.exists():
            try:
                hp_data = json.loads(hp_path.read_text())
                phone = a.get("phone", "")
                for r in hp_data.get("results", []):
                    if r.get("phone") != phone:
                        continue
                    plat = a.get("platform", "")
                    pdata = r.get(plat, {})
                    if pdata and pdata.get("nickname") and pdata["nickname"] != aid:
                        has_profile = True
                        break
            except: pass
    # ④ 在 registry 中有记录（已同步到联邦）
    has_registry = False
    reg_path = AGENT_SYNC / "05_tools" / "07_matrix" / "accounts_registry.yaml"
    if reg_path.exists():
        try:
            import yaml
            reg = yaml.safe_load(reg_path.read_text()) or {"accounts": []}
            for ra in reg.get("accounts", []):
                if ra.get("id") == aid:
                    has_registry = True
                    break
        except: pass
    return {"has_identity": has_identity, "has_cookie": has_cookie,
            "has_profile": has_profile, "has_registry": has_registry,
            "busy": False, "busy_since": ""}


@router.get("/sms/accounts")
def api_sms_accounts():
    """返回所有本机账号（含手机号和昵称），供前端下拉选择"""
    if not _matrix_mgmt_ok:
        return {"error": f"账号模块未加载: {_matrix_mgmt_err}"}
    try:
        mgr = MatrixManager()
        accounts = mgr.list_accounts()
        profiles_path = AGENT_LOCAL / "tools" / "matrix" / "data" / "profiles.json"
        profiles = {}
        if profiles_path.exists():
            try:
                profiles = json.loads(profiles_path.read_text())
            except: pass

        # ══════════════════════════════════════════════════
        # 读 homepage_info.json（新采集系统的数据，按 phone 匹配）
        # ══════════════════════════════════════════════════
        hp_path = AGENT_LOCAL / "tools" / "matrix" / "data" / "homepage_info.json"
        hp_map = {}  # phone → {douyin: {}, xiaohongshu: {}}
        if hp_path.exists():
            try:
                hp_data = json.loads(hp_path.read_text())
                for r in hp_data.get("results", []):
                    phone = r.get("phone", "")
                    if phone:
                        hp_map[phone] = {
                            "douyin": r.get("douyin") or {},
                            "xiaohongshu": r.get("xiaohongshu") or {},
                        }
            except: pass

        result = []
        for a in accounts:
            aid = a["id"]
            p = profiles.get(aid, {})
            # 平台校验：profiles.json 中的 platform 必须和账号实际 platform 一致
            acct_plat = a.get("platform", "")
            profile_plat = p.get("platform", "")
            if profile_plat and profile_plat != acct_plat:
                p = {}  # 平台不匹配，忽略此 profile

            # 优先用 homepage_info.json 的数据（新采集系统）
            phone = a.get("phone", "")
            hp_entry = hp_map.get(phone, {})
            hp_plat = hp_entry.get(acct_plat, {})
            hp_nick = hp_plat.get("nickname", "")
            # 过滤无效昵称
            if hp_nick and ("登录后" in hp_nick or "问点点" in hp_nick or "推荐" in hp_nick):
                hp_nick = ""

            nick = hp_nick or p.get("nickname") or a.get("display_name") or aid
            fans = hp_plat.get("fans") or p.get("fans", "?")
            if fans == "" or fans is None:
                fans = p.get("fans", "?")
            posts = hp_plat.get("posts") or p.get("posts", "?")
            if posts == "" or posts is None:
                posts = p.get("posts", "?")
            following = hp_plat.get("following") or p.get("following", "?")
            if following == "" or following is None:
                following = p.get("following", "?")

            st = _account_status(a)

            # 读取指纹信息
            fingerprint = {}
            ident_name = a.get("identity_dir") or a.get("identity_hint") or aid
            cfg_path = IDENTITIES_ROOT / ident_name.replace("identities/", "") / "config.yaml"
            if cfg_path.exists():
                try:
                    import yaml
                    cfg = yaml.safe_load(cfg_path.read_text())
                    fingerprint = cfg.get("fingerprint_summary", {}) or {}
                except: pass

            # 检查账号忙碌状态
            busy = st.get("busy", False)
            busy_since = st.get("busy_since", "")
            
            result.append({
                "id": aid, "phone": phone,
                "nickname": nick, "platform": a.get("platform", ""),
                "is_local": a.get("is_local", False),
                "owner_machine": a.get("owner_machine") or a.get("_source_machine_name", ""),
                "has_identity": st["has_identity"],
                "has_cookie": st["has_cookie"],
                "has_profile": st["has_profile"],
                "has_registry": st["has_registry"],
                "fans": fans,
                "posts": posts,
                "following": following,
                "likes": hp_plat.get("likes") or p.get("likes", "?"),
                "identity_dir": a.get("identity_dir", ""),
                "fingerprint": fingerprint,
                "busy": busy,
                "busy_since": busy_since,
            })
        return {"accounts": result}
    except Exception as e:
        return {"error": str(e)}


@router.get("/sms/test/{phone_or_account}")
def api_sms_test_ext(phone_or_account: str, timeout: int = 15):
    """查短信（支持手机号或账号ID）"""
    if phone_or_account and len(phone_or_account) < 11 and _matrix_mgmt_ok:
        try:
            mgr = MatrixManager()
            for a in mgr.list_accounts():
                if a["id"] == phone_or_account and a.get("phone"):
                    return _sms.test_receive(a["phone"], timeout)
        except: pass
    return _sms.test_receive(phone_or_account, timeout)


@router.post("/accounts/register")
async def api_account_register(request: Request):
    """注册新账号：创建身份目录→写入accounts.yaml→打开浏览器登录"""
    data = await request.json() if request.headers.get("content-type") == "application/json" else {}
    plat = data.get("platform", "douyin")
    phone = data.get("phone", "").strip()
    nick = data.get("nickname", "").strip()
    if plat not in ("douyin", "xiaohongshu"):
        return {"status": "error", "error": "平台只支持 douyin / xiaohongshu"}
    if not phone:
        return {"status": "error", "error": "手机号不能为空"}
    # 生成 account_id
    prefix = {"douyin": "douyin_", "xiaohongshu": "xhs_"}.get(plat, "acct_")
    try:
        mgr = MatrixManager()
        existing = [a["id"] for a in mgr.list_accounts() if a["id"].startswith(prefix)]
        nums = [int(a.replace(prefix, "")) for a in existing if a.replace(prefix, "").isdigit()]
        n = max(nums) + 1 if nums else 1
    except: n = 1
    acct_id = f"{prefix}{n}"
    try:
        # 1. 判断身份目录：同手机号是否已有 identity
        import yaml
        LOCAL_ACCT_YAML = AGENT_LOCAL / "tools" / "matrix" / "config" / "accounts.yaml"
        existing_accts = []
        if LOCAL_ACCT_YAML.exists():
            raw = yaml.safe_load(LOCAL_ACCT_YAML.read_text()) or {}
            existing_accts = raw.get("accounts", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])

        # 查找同手机号的现有 identity_dir
        shared_identity_name = None
        for ea in existing_accts:
            if isinstance(ea, dict) and ea.get("phone") == phone:
                ed = ea.get("identity_dir") or ea.get("identity_hint") or ""
                if ed:
                    shared_identity_name = ed.replace("identities/", "")
                    break

        # 冲突检测：同手机号+同平台
        conflict = [ea for ea in existing_accts
                    if isinstance(ea, dict) and ea.get("phone") == phone
                    and ea.get("platform") == plat]
        if conflict:
            return {"status": "error", "error": f"手机号 {phone} 已有 {plat} 账号: {conflict[0]['id']}。如需重新注册，请先删除旧账号。"}

        if shared_identity_name:
            # 复用已有身份目录
            identity_name = shared_identity_name
            identity_dir = IDENTITIES_ROOT / identity_name
            # 确保目录存在
            identity_dir.mkdir(parents=True, exist_ok=True)
            (identity_dir / "user_data").mkdir(exist_ok=True)
        else:
            # 新建身份目录，以 phone_ 开头
            identity_name = f"phone_{phone}"
            identity_dir = IDENTITIES_ROOT / identity_name
            identity_dir.mkdir(parents=True, exist_ok=True)
            (identity_dir / "user_data").mkdir(exist_ok=True)
            config = {
                "fingerprint_summary": {"platform": "Win32", "screen": "1920x1080"},
                "identity": {"name": identity_name, "platform": plat, "created_at": datetime.now().isoformat()},
                "window": [802, 783],
            }
            (identity_dir / "config.yaml").write_text(yaml.dump(config, allow_unicode=True, default_flow_style=False))

        # 2. 写入 accounts.yaml
        accts = [a for a in existing_accts if isinstance(a, dict) and a.get("id") != acct_id]
        accts.append({
            "id": acct_id, "platform": plat, "phone": phone,
            "display_name": nick or acct_id, "enabled": True,
            "browser_type": "camoufox", "profile_dir": identity_name,
            "identity_dir": identity_name,
        })
        LOCAL_ACCT_YAML.write_text(yaml.dump({"accounts": accts}, allow_unicode=True, default_flow_style=False))
        # 3. 同步到 accounts_registry.yaml
        registry_path = AGENT_SYNC / "05_tools" / "07_matrix" / "accounts_registry.yaml"
        try:
            reg = yaml.safe_load(registry_path.read_text()) or {"accounts": []}
            reg["accounts"] = [a for a in reg["accounts"] if a.get("id") != acct_id]
            reg["accounts"].append({
                "id": acct_id, "platform": plat, "phone": phone,
                "display_name": nick or acct_id, "assigned_machine": HOSTNAME or "unknown",
            })
            registry_path.write_text(yaml.dump(reg, allow_unicode=True, default_flow_style=False))
        except: pass
        # 4. 启动浏览器登录
        agent_python = str(HOME / ".workbuddy" / "binaries" / "python" / "envs" / "matrix" / "bin" / "python3")
        cmd = [agent_python, "-m", "mc", "account", "login", acct_id]
        import subprocess
        subprocess.Popen(cmd, cwd=str(SCRIPTS_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"status": "ok", "account_id": acct_id, "message": f"账号 {acct_id} 已创建，浏览器已打开请登录",
                "next": "登录成功后可以在 Dashboard 采集昵称"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/accounts/{account_id}/login")
def api_account_login(account_id: str):
    """重新打开浏览器登录"""
    agent_python = str(HOME / ".workbuddy" / "binaries" / "python" / "envs" / "agent-os" / "bin" / "python3")
    import subprocess
    try:
        p = subprocess.Popen(
            [agent_python, "-m", "mc", "account", "login", account_id],
            cwd=str(SCRIPTS_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"status": "ok", "pid": p.pid, "message": f"浏览器已打开，请登录 {account_id}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/accounts/{account_id}/collect-profile")
def api_collect_profile(account_id: str):
    """采集账号昵称信息（根据平台选择正确蓝图）"""
    # 从账号注册表获取平台
    platform = "douyin"
    try:
        from matrix_mgmt import MatrixManager
        mgr = MatrixManager()
        for a in mgr.list_accounts():
            if a["id"] == account_id:
                p = a.get("platform", "douyin")
                platform = p if p in ("douyin", "xiaohongshu") else "douyin"
                break
    except: pass
    # 根据平台选择采集蓝图
    bp_name = "xiaohongshu_read_profile" if platform == "xiaohongshu" else "douyin_read_profile"
    agent_python = str(HOME / ".workbuddy" / "binaries" / "python" / "envs" / "agent-os" / "bin" / "python3")
    import subprocess
    try:
        p = subprocess.Popen(
            [agent_python, "-m", "mc", "run", "--accounts", account_id,
             "--blueprints", bp_name, "--rounds", "1"],
            cwd=str(SCRIPTS_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"status": "ok", "pid": p.pid, "message": f"正在采集 {account_id} 的昵称信息（{bp_name}）"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════════════
# 定时任务 & 人设 API
# ═══════════════════════════════════════════════

SCHEDULE_YAML = SCRIPTS_DIR / "config" / "schedule.yaml"


@router.get("/schedules")
def api_schedules():
    if not SCHEDULE_YAML.exists():
        return {"schedules": []}
    try:
        import yaml
        data = yaml.safe_load(SCHEDULE_YAML.read_text())
        scheds = data.get("schedules", {})
        result = []
        for sid, cfg in scheds.items():
            cfg["id"] = sid
            result.append(cfg)
        return {"schedules": result}
    except Exception as e:
        return {"error": str(e)}


@router.get("/schedules")
def api_schedules():
    """返回所有定时任务"""
    from mc.scheduler import load_all_schedules
    return {"schedules": load_all_schedules()}


@router.post("/schedules/toggle")
def api_schedule_toggle(data: dict):
    """启用/禁用定时任务"""
    sid = (data or {}).get("id", "")
    enabled = (data or {}).get("enabled", True)
    from mc.scheduler import load_all_schedules, save_all_schedules
    all_s = load_all_schedules()
    if sid in all_s:
        all_s[sid]["enabled"] = enabled
        save_all_schedules(all_s)
        return {"status": "ok"}
    return {"status": "error", "error": f"未找到任务 {sid}"}


@router.post("/schedules/delete")
def api_schedule_delete(data: dict):
    """删除定时任务"""
    sid = (data or {}).get("id", "")
    from mc.scheduler import load_all_schedules, save_all_schedules
    all_s = load_all_schedules()
    if sid in all_s:
        del all_s[sid]
        save_all_schedules(all_s)
        return {"status": "ok"}
    return {"status": "error", "error": f"未找到任务 {sid}"}


@router.get("/schedules/history")
def api_schedule_history():
    """返回最近20条执行历史"""
    from mc.scheduler import read_history
    return {"history": read_history(limit=20)}


@router.get("/corpus/personas")
def api_corpus_personas():
    """列出语料库中的身份（v2格式）"""
    from mc.corpus import CorpusManager
    cm = CorpusManager()
    return {"personas": cm.list_personas()}


@router.get("/corpus/scenes")
def api_corpus_scenes(persona: str = ""):
    """列出语料库中的场景（v2格式）"""
    from mc.corpus import CorpusManager
    cm = CorpusManager()
    return {"scenes": cm.list_scenes(persona) if not persona else cm.list_scenes(persona)}


@router.get("/personas")
def api_personas():
    pf = AGENT_LOCAL / "tools" / "matrix" / "data" / "profiles.json"
    if not pf.exists():
        return {"personas": {}}
    try:
        data = json.loads(pf.read_text())
        personas = {}
        for aid, info in data.items():
            if "persona" in info:
                personas[aid] = info["persona"]
        return {"personas": personas}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════
# 任务执行 API
# ═══════════════════════════════════════════════

@router.post("/task/run")
async def api_task_run(request: Request):
    """从 Dashboard 执行智能任务"""
    data = await request.json() if request.headers.get("content-type") == "application/json" else {}
    task_type = data.get("type", "comment")
    url = data.get("url", "")
    keyword = data.get("keyword", "")
    direction = data.get("direction", "")
    account = data.get("account", "")
    comment_text = data.get("comment", "")
    from mc.task import Task, run_task
    task = Task(type=task_type, url=url, keyword=keyword,
                direction=direction, account=account, comment_text=comment_text)
    errors = task.validate()
    if errors:
        return {"status": "error", "errors": errors}
    task.auto_fill()
    if not task.account:
        return {"status": "error", "errors": [f"没有可用的{task.platform}账号"]}
    result = await run_task(task)
    return {"status": "ok" if result.get("status") != "error" else "error",
            "success": result.get("success", 0),
            "failed": result.get("failed", 0),
            "total": result.get("total_steps", 0),
            "duration": result.get("duration", 0),
            "task_summary": task.summary(),
            "detail": result.get("error", "")}


# [删除账号使用 app.py 中已有的 DELETE /api/matrix/accounts/{id}]
# 前端调用时加 ?delete_identity=true
# 但 app.py 的 delete 有 bug(不写回 accounts.yaml)，前端需额外调用此 cleanup


@router.post("/accounts/{account_id}/cleanup")
def api_account_cleanup(account_id: str):
    """删除后被 app.py 的 bug 遗漏时，补清理 accounts.yaml 和 registry"""
    try:
        import yaml
        changed = False
        deleted_identity = False
        # 清理 accounts.yaml
        LOCAL_ACCT = AGENT_LOCAL / "tools" / "matrix" / "config" / "accounts.yaml"
        if LOCAL_ACCT.exists():
            raw = yaml.safe_load(LOCAL_ACCT.read_text()) or {}
            accts = raw.get("accounts", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
            # 先记录这个账号的 identity_dir
            deleted_identity_dir = None
            for a in accts:
                if isinstance(a, dict) and a.get("id") == account_id:
                    deleted_identity_dir = a.get("identity_dir") or a.get("identity_hint") or ""
                    break
            # 从配置中移除
            before = len(accts)
            accts = [a for a in accts if isinstance(a, dict) and a.get("id") != account_id]
            if len(accts) != before:
                data = {"accounts": accts}
                LOCAL_ACCT.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False))
                changed = True
            # 删除身份目录（仅当没有其他账号使用同一 identity_dir）
            if deleted_identity_dir:
                still_in_use = any(
                    isinstance(a, dict) and (a.get("identity_dir") or a.get("identity_hint") or "") == deleted_identity_dir
                    for a in accts
                )
                if not still_in_use:
                    import shutil
                    ident_path = IDENTITIES_ROOT / deleted_identity_dir.replace("identities/", "")
                    if ident_path.exists():
                        shutil.rmtree(ident_path)
                        deleted_identity = True
        # 清理 registry
        reg_path = AGENT_SYNC / "05_tools" / "07_matrix" / "accounts_registry.yaml"
        if reg_path.exists():
            reg = yaml.safe_load(reg_path.read_text()) or {"accounts": []}
            before = len(reg["accounts"])
            reg["accounts"] = [a for a in reg["accounts"] if a.get("id") != account_id]
            if len(reg["accounts"]) != before:
                reg_path.write_text(yaml.dump(reg, allow_unicode=True, default_flow_style=False))
                changed = True
        return {"status": "ok", "cleaned": changed, "identity_deleted": deleted_identity}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ═══════════════════════════════════════════════
# 清除登录状态 API
# ═══════════════════════════════════════════════

@router.post("/accounts/{account_id}/clear-cookies")
def api_clear_cookies(account_id: str):
    """清除指定账号的登录状态（只清该平台 cookie，不影响同身份的其他平台）"""
    try:
        from matrix_mgmt import MatrixManager
        mgr = MatrixManager()
        acct = None
        for a in mgr.list_accounts():
            if a["id"] == account_id:
                acct = a
                break
        if not acct:
            return {"status": "error", "error": "账号不存在"}

        identity_dir = acct.get("identity_dir", account_id).replace("identities/", "")
        plat = acct.get("platform", "douyin")
        # 平台对应的域名模式
        domain_pattern = "%douyin%" if plat == "douyin" else "%xiaohongshu%"

        cookie_path = IDENTITIES_ROOT / identity_dir / "user_data" / "cookies.sqlite"
        if not cookie_path.exists():
            return {"status": "ok", "message": f"{plat} 无 cookie 可清除"}

        try:
            import sqlite3
            conn = sqlite3.connect(str(cookie_path), timeout=3)
            cur = conn.execute("DELETE FROM moz_cookies WHERE host LIKE ?", (domain_pattern,))
            deleted = cur.rowcount
            conn.commit()
            conn.close()
            return {"status": "ok", "message": f"已清除 {plat} 的 {deleted} 个 cookie", "deleted": deleted}
        except Exception as e:
            return {"status": "error", "error": f"清除失败: {e}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════════════
# 录制管理 API
# ═══════════════════════════════════════════════

RECORDINGS_DIR = AGENT_LOCAL / "tools" / "matrix" / "recordings"
_recording_process = None


@router.get("/recordings/stats")
def api_recording_stats():
    """按账号统计录制包数量"""
    try:
        from mc.recorder import RecordingSession
        recordings = RecordingSession.list_recordings()
        stats = {}
        for r in recordings:
            acct = r.get("account", "unknown")
            stats[acct] = stats.get(acct, 0) + 1
        return {"stats": stats}
    except Exception as e:
        return {"stats": {}, "error": str(e)}


@router.post("/recordings/start")
def api_recording_start(data: dict = None):
    """启动录制"""
    global _recording_process
    account = (data or {}).get("account", "douyin_test")
    platform = "douyin"
    try:
        from matrix_mgmt import MatrixManager
        mgr = MatrixManager()
        for a in mgr.list_accounts():
            if a["id"] == account:
                p = a.get("platform", "douyin")
                platform = {"douyin": "douyin", "xiaohongshu": "xiaohongshu"}.get(p, "douyin")
                break
    except: pass
    agent_python = str(HOME / ".workbuddy" / "binaries" / "python" / "envs" / "matrix" / "bin" / "python3")
    cmd = [agent_python, "-m", "mc.recorder", account, platform]
    import subprocess
    try:
        p = subprocess.Popen(cmd, cwd=str(SCRIPTS_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        import time; time.sleep(2)
        if p.poll() is not None:
            stderr = p.stderr.read().decode()[:200] if p.stderr else ""
            return {"status": "error", "error": f"录制进程退出 (code={p.returncode})", "detail": stderr}
        _recording_process = {"pid": p.pid, "account": account}
        return {"status": "ok", "pid": p.pid, "account": account, "message": "录制已启动"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/recordings/stop")
def api_recording_stop():
    """停止录制"""
    global _recording_process
    if _recording_process:
        import os, signal
        try:
            os.kill(_recording_process["pid"], signal.SIGTERM)
            import time; time.sleep(1)
        except: pass
        _recording_process = None
        return {"status": "ok", "message": "录制已停止"}
    return {"status": "ok", "message": "无运行中的录制"}


@router.get("/recordings/status")
def api_recording_status():
    """查看录制状态"""
    global _recording_process
    if _recording_process:
        import os
        try:
            os.kill(_recording_process["pid"], 0)
            return {"status": "running", "pid": _recording_process["pid"], "account": _recording_process["account"]}
        except: pass
        _recording_process = None
    return {"status": "idle"}


@router.get("/recordings")
def api_recordings_list():
    """列出录制包"""
    from mc.recorder import RecordingSession
    return {"recordings": RecordingSession.list_recordings()}


@router.get("/recordings/{name}")
def api_recording_analyze(name: str):
    """分析录制包"""
    from mc.analyzer import analyze_recording_file
    p = RECORDINGS_DIR / name
    if p.exists():
        return analyze_recording_file(str(p))
    return {"error": f"录制包不存在: {name}"}


@router.post("/recordings/{name}/export")
def api_recording_export(name: str):
    """导出录制包"""
    from mc.exporter import export_recording
    p = RECORDINGS_DIR / name
    if p.exists():
        return export_recording(str(p))
    return {"error": f"录制包不存在: {name}"}


@router.delete("/recordings/{name}")
def api_recording_delete(name: str):
    """删除录制包"""
    from mc.recorder import RecordingSession
    ok = RecordingSession.delete_recording(name)
    return {"deleted": ok}

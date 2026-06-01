"""
sms_proxy_api.py — 短信接收 + 代理管理 API

提供 Dashboard 接口，用于查看/测试短信API配置、代理状态。
版本: 1.0.0 | 更新: 2026-06-01
"""
import json, os, subprocess, sys
from pathlib import Path
from datetime import datetime

HOME = Path.home()
AGENT_SYNC = HOME / "workbuddy-agent-os" / "agent-sync"
AGENT_LOCAL = HOME / "workbuddy-agent-os" / "agent-local"

SCRIPTS_DIR = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts"
IDENTITIES_ROOT = AGENT_LOCAL / "tools" / "matrix" / "identities"

sys.path.insert(0, str(SCRIPTS_DIR))

SMS_YAML = SCRIPTS_DIR / "config" / "sms.yaml"


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
from fastapi import APIRouter

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

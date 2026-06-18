"""
proxy.py — 代理管理 CLI 模块

基于 sms_proxy_api.py 的 ProxyManager，提供 CLI 封装
"""
import json
import logging
import urllib.request
from datetime import datetime

log = logging.getLogger(__name__)


class ProxyCLI:
    """代理管理 CLI"""

    @staticmethod
    def list_all() -> list:
        """获取所有账号的代理配置"""
        try:
            from matrix_mgmt import MatrixManager
            mgr = MatrixManager()
            accounts = mgr.list_accounts()
        except Exception as e:
            return [{"error": str(e)}]

        from pathlib import Path
        IDENTITIES_ROOT = AGENT_LOCAL / "tools" / "matrix" / "identities"

        results = []
        for a in accounts:
            if not a.get("is_local"):
                continue
            aid = a["id"]
            config_path = IDENTITIES_ROOT / aid / "config.yaml"
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
                "proxy": proxy if proxy and str(proxy).strip() not in ("null", "None", "") else None,
                "has_proxy": bool(proxy and str(proxy).strip() not in ("null", "None", "")),
                "login_status": a.get("_status", "unknown"),
            })
        return results

    @staticmethod
    def test(proxy_str: str) -> dict:
        """测试代理连通性"""
        try:
            start = datetime.now()
            if proxy_str and str(proxy_str).strip() not in ("null", "None", ""):
                handler = urllib.request.ProxyHandler({"http": proxy_str, "https": proxy_str})
                opener = urllib.request.build_opener(handler)
                resp = opener.open("http://httpbin.org/ip", timeout=10)
                data = json.loads(resp.read().decode())
                elapsed = (datetime.now() - start).total_seconds()
                proxy_type = "HTTP"
                if proxy_str.startswith("socks5://") or proxy_str.startswith("socks://"):
                    proxy_type = "SOCKS5"
                return {
                    "status": "ok", "ip": data.get("origin", ""),
                    "type": proxy_type, "elapsed": f"{elapsed:.1f}s",
                    "speed": "快" if elapsed < 0.5 else ("中" if elapsed < 2 else "慢"),
                }
            else:
                resp = urllib.request.urlopen("http://httpbin.org/ip", timeout=10)
                data = json.loads(resp.read().decode())
                elapsed = (datetime.now() - start).total_seconds()
                return {"status": "ok", "ip": data.get("origin", ""), "elapsed": f"{elapsed:.1f}s", "direct": True}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def set_proxy(account_id: str, proxy_str: str) -> dict:
        """设置账号代理"""
        from pathlib import Path
        IDENTITIES_ROOT = AGENT_LOCAL / "tools" / "matrix" / "identities"

        config_path = IDENTITIES_ROOT / account_id / "config.yaml"
        if not config_path.exists():
            return {"status": "error", "error": f"账号 {account_id} 身份目录不存在"}

        try:
            import yaml
            data = yaml.safe_load(config_path.read_text()) or {}
            if "identity" not in data:
                data["identity"] = {}
            data["identity"]["proxy"] = proxy_str if proxy_str.strip() else None
            config_path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))
            return {"status": "ok", "account": account_id, "proxy": proxy_str}
        except Exception as e:
            return {"status": "error", "error": str(e)}

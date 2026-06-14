"""抖音插件实现 — 当前包装现有脚本"""

import json
import subprocess
import sys
from pathlib import Path

from platforms.base import BasePlatform

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
AGENT_LOCAL = Path.home() / "workbuddy-agent-os" / "agent-local"


class DouyinPlatform(BasePlatform):
    name = "douyin"
    display_name = "抖音"
    version = "1.0.0"
    description = "抖音账号管理: 登录/采集/养号"

    def _resolve_account(self, account_name: str) -> str:
        """通过手机号或账号ID找到 identity_dir"""
        try:
            sys.path.insert(0, str(SCRIPTS_DIR))
            from matrix_mgmt import MatrixManager
            mgr = MatrixManager()
            for a in mgr.list_accounts():
                if a.get("phone") == account_name or a["id"] == account_name:
                    if a.get("platform") == "douyin":
                        return a.get("identity_dir", a["id"]).replace("identities/", "")
        except: pass
        return account_name

    def collect(self, account_name: str) -> dict:
        """采集主页信息"""
        runner = SCRIPTS_DIR / "collect_homepage_info.py"
        identity = self._resolve_account(account_name)
        cmd = [sys.executable, str(runner), "--single", identity]
        try:
            p = subprocess.run(cmd, cwd=str(SCRIPTS_DIR), capture_output=True, text=True, timeout=180)
            return {"status": "ok" if p.returncode == 0 else "error", "output": p.stdout[-500:]}
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "采集超时"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def login(self, account_name: str, headless: bool = False) -> dict:
        """打开浏览器登录"""
        login_script = SCRIPTS_DIR / "login_identity.py"
        identity = self._resolve_account(account_name)
        cmd = [sys.executable, str(login_script), identity, "--platform", "douyin"]
        try:
            subprocess.Popen(cmd, cwd=str(SCRIPTS_DIR))
            return {"status": "ok", "message": f"浏览器已打开, 请扫码登录 {account_name}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def status(self, account_name: str) -> dict:
        """检查登录状态"""
        try:
            sys.path.insert(0, str(SCRIPTS_DIR))
            from auth_manager import check_login_by_cookie_sync, get_session_id
            from matrix_mgmt import MatrixManager
            mgr = MatrixManager()
            for a in mgr.list_accounts():
                if (a.get("phone") == account_name or a["id"] == account_name) and a.get("platform") == "douyin":
                    # 检查 Cookie
                    cookies_path = AGENT_LOCAL / "identities" / (a.get("identity_dir", a["id"]).replace("identities/", "")) / "user_data" / "cookies.sqlite"
                    if cookies_path.exists():
                        return {"status": "logged_in", "account": a["id"]}
                    return {"status": "no_cookie", "account": a["id"]}
            return {"status": "not_found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

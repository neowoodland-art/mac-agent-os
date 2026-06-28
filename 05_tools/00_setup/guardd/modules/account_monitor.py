"""
account_monitor.py — 本机账号登录状态采集 (guardd 模块)

职责:
  - 读取本机 identities/ 目录下所有账号的 cookies.sqlite
  - 返回 {account_id: status} 映射
  - 每次调用实时检测（不缓存）

状态定义：
  logged_in       — cookite 文件存在且含 session cookie
  no_cookie       — 身份目录存在但无 cookies.sqlite 文件
  empty_cookie    — cookies.sqlite 文件小于 100 字节
  no_session      — cookies.sqlite 存在但无 session 类型 cookie
  no_identity     — 身份目录不存在
  error           — 读取异常
"""
import json
import logging
import os
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger("guardd.account_monitor")

# ── 路径 ──────────────────────────────────────────────
AGENT_LOCAL = Path(os.environ.get(
    "AGENT_LOCAL",
    str(Path.home() / "workbuddy-agent-os" / "agent-local")
))
MATRIX_IDENTITIES = AGENT_LOCAL / "tools" / "matrix" / "identities"
OVERRIDE_PATH = AGENT_LOCAL / "tools" / "matrix" / "config" / "accounts.override.yaml"


class AccountMonitor:
    """本机账号登录状态实时采集器"""

    def __init__(self):
        self._identities_root = MATRIX_IDENTITIES
        self._override_path = OVERRIDE_PATH

    def collect_status(self) -> dict:
        """采集本机所有账号的登录状态

        读取 override.yaml 中的账号列表，逐一检查 cookie。
        如果 override.yaml 不存在，降级到扫描 identities/ 目录。

        Returns:
            {account_id: status_string, ...}
        """
        accounts = self._get_local_accounts()
        result = {}
        for account_id, identity_hint in accounts.items():
            status = self._check_login_status(identity_hint)
            result[account_id] = status
        return result

    def _get_local_accounts(self) -> dict:
        """获取本机账号列表 {account_id: identity_hint}"""
        # 优先级 1: override.yaml
        if self._override_path.exists():
            try:
                import yaml
                data = yaml.safe_load(self._override_path.read_text()) or {}
                accts = {}
                for a in data.get("accounts", []):
                    aid = a.get("id", "")
                    if not aid:
                        continue
                    hint = a.get("identity_dir") or a.get("identity_hint") or aid
                    hint = hint.replace("identities/", "")
                    accts[aid] = hint
                if accts:
                    return accts
            except Exception as e:
                logger.warning(f"读取 override.yaml 失败: {e}")

        # 优先级 2: 扫描 identities/ 目录（降级）
        if self._identities_root.exists():
            accts = {}
            for entry in sorted(self._identities_root.iterdir()):
                if entry.is_dir() and not entry.name.startswith("."):
                    accts[entry.name] = entry.name
            return accts

        return {}

    def _check_login_status(self, identity_hint: str) -> str:
        """检查单个身份目录的登录状态（逻辑同 matrix_mgmt._check_login_status_by_hint）"""
        if not identity_hint:
            return "no_identity"
        identity_path = self._identities_root / identity_hint
        if not identity_path.exists():
            return "no_identity"
        cookie_path = identity_path / "user_data" / "cookies.sqlite"
        if not cookie_path.exists():
            return "no_cookie"
        if cookie_path.stat().st_size < 100:
            return "empty_cookie"
        try:
            conn = sqlite3.connect(str(cookie_path), timeout=2)
            cur = conn.cursor()
            total = cur.execute("SELECT count(*) FROM moz_cookies").fetchone()[0]
            session = cur.execute(
                "SELECT count(*) FROM moz_cookies WHERE name LIKE '%session%'"
            ).fetchone()[0]
            conn.close()
            return "logged_in" if session > 0 else "no_session"
        except Exception as e:
            logger.debug(f"cookie 检查异常 {identity_hint}: {e}")
            return "error"

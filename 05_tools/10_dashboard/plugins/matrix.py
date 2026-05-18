"""
plugins/matrix.py — Matrix 账号矩阵插件 (v2)
显示各机器养号状态、账号列表、蓝图执行情况
版本: 1.0.0 | 更新: 2026-05-18
"""
import os, yaml
from pathlib import Path

from plugins.base import DashboardPlugin, AGENT_LOCAL, HOSTNAME, MACHINE_UID
from plugins._registry import get_machine_list, get_plugin_data


class MatrixPlugin(DashboardPlugin):
    name = "matrix"
    label = "账号矩阵"
    icon = "📱"
    version = "1.0.0"
    description = "Matrix 养号：账号 / 蓝图 / 执行状态"
    order = 30

    def _read_local_accounts(self):
        """读取本机矩阵账号配置"""
        config_paths = [
            AGENT_LOCAL / "tools" / "matrix" / "config" / "local.yaml",
            Path.home() / "workbuddy-agent-os" / "agent-sync" / "05_tools" / "07_matrix" / "local.yaml",
        ]
        for p in config_paths:
            if p.exists():
                try:
                    cfg = yaml.safe_load(p.read_text()) or {}
                    accounts = cfg.get("accounts", [])
                    if not accounts and "douyin" in cfg:
                        accounts = cfg["douyin"].get("accounts", [])
                    return accounts
                except:
                    pass
        return []

    def _read_blueprints(self):
        """读取蓝图列表"""
        bp_dir = Path.home() / "workbuddy-agent-os" / "agent-sync" / "05_tools" / "07_matrix" / "blueprints"
        blueprints = []
        if bp_dir.exists():
            for f in sorted(bp_dir.iterdir()):
                if f.suffix == ".yaml" or f.suffix == ".yml":
                    try:
                        bp = yaml.safe_load(f.read_text()) or {}
                        blueprints.append({
                            "name": bp.get("name", f.stem),
                            "steps": len(bp.get("steps", [])),
                            "file": f.name,
                        })
                    except:
                        pass
        return blueprints

    def summary(self, machines: list[str]) -> dict:
        accounts = self._read_local_accounts()
        blueprints = self._read_blueprints()
        online = sum(1 for a in accounts if a.get("status", "") in ("active", "online"))

        by_machine = {HOSTNAME: {
            "账号": len(accounts),
            "在线": online,
            "蓝图": len(blueprints),
        }}

        # 其他机器的数据
        for d in get_plugin_data(self.name):
            hn = d.get("hostname", "")
            if hn and hn != HOSTNAME:
                data = d.get("data", {})
                m = data.get("各机器", {}).get(hn, {})
                if m:
                    by_machine[hn] = m
                else:
                    by_machine[hn] = {"_note": "未接入"}

        return {
            "总账号": len(accounts),
            "在线": online,
            "蓝图": len(blueprints),
            "各机器": by_machine,
        }

    def detail(self, machine: str = "") -> dict:
        accounts = self._read_local_accounts()
        blueprints = self._read_blueprints()
        return {
            HOSTNAME: {
                "账号列表": accounts,
                "蓝图列表": blueprints,
                "配置路径": str(AGENT_LOCAL / "tools" / "matrix"),
            }
        }

    def actions(self) -> list[dict]:
        return [
            {"name": "刷新账号", "method": "POST", "endpoint": "/api/plugins/matrix/refresh"},
        ]

"""
plugins/matrix.py — Matrix 账号矩阵插件 (v2.1)
显示各机器养号状态、账号列表、蓝图列表、账号模板、操作指引
版本: 2.1.0 | 更新: 2026-05-18
"""
import os, yaml, json
from pathlib import Path

from plugins.base import DashboardPlugin, AGENT_SYNC, AGENT_LOCAL, HOSTNAME, MACHINE_UID
from plugins._registry import get_machine_list, get_plugin_data


class MatrixPlugin(DashboardPlugin):
    name = "matrix"
    label = "账号矩阵"
    icon = "📱"
    version = "2.1.0"
    description = "Matrix 养号：账号 / 蓝图 / 模板 / 配置指引"
    order = 30

    BLUEPRINT_MAP = {
        "browse": "浏览",
        "nurture": "养成",
        "comment": "评论",
        "search": "搜索",
        "interact": "互动",
    }

    def _read_local_accounts(self):
        config_paths = [
            AGENT_LOCAL / "tools" / "matrix" / "config" / "local.yaml",
            AGENT_SYNC / "05_tools" / "07_matrix" / "local.yaml",
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
        bp_dir = AGENT_SYNC / "05_tools" / "07_matrix" / "blueprints"
        blueprints = []
        if bp_dir.exists():
            for f in sorted(bp_dir.iterdir()):
                if f.suffix in (".yaml", ".yml", ".json"):
                    try:
                        if f.suffix == ".json":
                            bp = json.loads(f.read_text())
                        else:
                            bp = yaml.safe_load(f.read_text()) or {}
                        name = bp.get("name", bp.get("id", f.stem))
                        steps = bp.get("steps", bp.get("actions", []))
                        blueprints.append({
                            "name": name,
                            "steps": len(steps),
                            "file": f.name,
                            "type": f.name.split("_")[0] if "_" in f.name else "综合",
                        })
                    except:
                        pass
        return blueprints

    def _read_account_templates(self):
        """读取账号配置模板"""
        tmpl_dir = AGENT_SYNC / "05_tools" / "07_matrix" / "config_template"
        templates = []
        if tmpl_dir.exists():
            for f in sorted(tmpl_dir.iterdir()):
                if f.suffix == ".yaml":
                    templates.append({"name": f.stem, "file": f.name})
        return templates

    def summary(self, machines):
        accounts = self._read_local_accounts()
        blueprints = self._read_blueprints()
        templates = self._read_account_templates()
        online = sum(1 for a in accounts if a.get("status", "") in ("active", "online"))

        by_machine = {HOSTNAME: {
            "账号": len(accounts),
            "在线": online,
            "蓝图": len(blueprints),
            "模板": len(templates),
        }}

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
            "总账号": len(accounts) if accounts else 0,
            "在线": online,
            "蓝图": len(blueprints),
            "配置模板": len(templates),
            "各机器": by_machine,
        }

    def detail(self, machine=""):
        accounts = self._read_local_accounts()
        blueprints = self._read_blueprints()
        templates = self._read_account_templates()
        return {
            HOSTNAME: {
                "账号列表": accounts if accounts else [{"_note": "未配置账号, 请将 local.yaml 放入 agent-local/tools/matrix/config/"}],
                "蓝图列表": blueprints,
                "配置模板": templates,
                "配置路径": str(AGENT_LOCAL / "tools" / "matrix" / "config"),
                "模板路径": str(AGENT_SYNC / "05_tools" / "07_matrix" / "config_template"),
                "使用方式": "1. 复制 config_template/accounts.yaml 到 local.yaml → 2. 填入账号信息 → 3. 重启 Matrix",
            }
        }

    def actions(self) -> list[dict]:
        return [
            {"name": "刷新数据", "method": "POST", "endpoint": "/api/plugins/matrix/refresh"},
            {"name": "打开配置目录", "method": "GET", "endpoint": "/api/open/matrix-config"},
        ]

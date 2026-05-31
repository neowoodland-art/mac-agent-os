"""
plugins/matrix.py — Matrix 账号矩阵插件 (v3.0)
显示养号状态、账号管理、蓝图编排、导入导出
版本: 3.0.0 | 更新: 2026-05-31
"""
import os, yaml, json, subprocess, time
from pathlib import Path

from plugins.base import DashboardPlugin, AGENT_SYNC, AGENT_LOCAL, HOSTNAME, MACHINE_UID
from plugins._registry import get_machine_list, get_plugin_data

# 导入 Matrix 管理模块
MATRIX_MGMT = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts" / "matrix_mgmt.py"
sys_path_fix = "import sys; sys.path.insert(0, str(Path.home() / 'workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts'))"


def _run_mgmt(method: str, *args, **kwargs):
    """调用 matrix_mgmt 模块的方法并返回结果"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("matrix_mgmt", MATRIX_MGMT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mgr = mod.MatrixManager()
    fn = getattr(mgr, method)
    return fn(*args, **kwargs)


class MatrixPlugin(DashboardPlugin):
    name = "matrix"
    label = "矩阵养号"
    icon = "📱"
    version = "3.0.0"
    description = "Matrix 养号管理：账号 / 蓝图 / 原子操作 / 导入导出"
    order = 30

    def get_sub_views(self) -> list[dict]:
        return [
            {"key": "matrix-accounts", "label": "账号管理", "icon": "👤", "group": "matrix"},
            {"key": "matrix-blueprints", "label": "蓝图编排", "icon": "📋", "group": "matrix"},
            {"key": "matrix-atom-ops", "label": "原子操作", "icon": "⚡", "group": "matrix"},
            {"key": "matrix-export", "label": "导入导出", "icon": "📦", "group": "matrix"},
        ]

    def summary(self, machines):
        try:
            info = _run_mgmt("system_info")
            accounts = _run_mgmt("list_accounts")
        except Exception as e:
            return {"error": str(e)}

        by_machine = {HOSTNAME: {
            "总账号": info["total_accounts"],
            "启用": info["enabled_accounts"],
            "已登录": info["logged_in_accounts"],
            "身份目录": info["identity_dirs"],
            "蓝图": info["blueprints"],
        }}

        for d in get_plugin_data(self.name):
            hn = d.get("hostname", "")
            if hn and hn != HOSTNAME:
                data = d.get("data", {})
                m = data.get("各机器", {}).get(hn, {})
                by_machine[hn] = m if m else {"_note": "未接入"}

        return {
            "总账号": info["total_accounts"],
            "启用": info["enabled_accounts"],
            "已登录": info["logged_in_accounts"],
            "身份目录": info["identity_dirs"],
            "蓝图": info["blueprints"],
            "各机器": by_machine,
        }

    def detail(self, machine=""):
        try:
            info = _run_mgmt("system_info")
            accounts = _run_mgmt("list_accounts")
            blueprints = _run_mgmt("list_blueprints")
            ops = _run_mgmt("list_atomic_ops")
        except Exception as e:
            return {HOSTNAME: {"error": str(e)}}

        return {HOSTNAME: {
            "系统信息": info,
            "账号列表": accounts,
            "蓝图列表": blueprints,
            "原子操作": ops,
            "配置路径": str(AGENT_LOCAL / "tools" / "matrix" / "config"),
            "数据目录": str(AGENT_LOCAL / "tools" / "matrix"),
        }}

    def actions(self) -> list[dict]:
        return [
            {"name": "刷新数据", "method": "POST", "endpoint": "/api/plugins/matrix/refresh"},
            {"name": "账号管理面板", "method": "GET", "endpoint": "/api/matrix/accounts"},
            {"name": "蓝图管理面板", "method": "GET", "endpoint": "/api/matrix/blueprints"},
            {"name": "导出账号", "method": "GET", "endpoint": "/api/matrix/export"},
        ]

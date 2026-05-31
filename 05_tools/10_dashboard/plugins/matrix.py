"""
plugins/matrix.py — Matrix 账号矩阵插件 (v3.2)
跨机注册表: Registry(L0 Gitee) + Override(L1 local) + 运行时(L2 cross_machine)
版本: 3.2.0 | 更新: 2026-05-31
"""
import os, yaml, json, subprocess, time
from pathlib import Path

from plugins.base import DashboardPlugin, AGENT_SYNC, AGENT_LOCAL, HOSTNAME, MACHINE_UID
from plugins._registry import get_machine_list, get_plugin_data

MATRIX_MGMT = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts" / "matrix_mgmt.py"


def _run_mgmt(method: str, *args, **kwargs):
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
    version = "3.2.0"
    description = "Matrix: 跨机账号注册表 / 蓝图编排 / 原子操作 / 备份恢复"
    order = 30

    def get_sub_views(self) -> list[dict]:
        return [
            {"key": "matrix-accounts", "label": "账号管理", "icon": "👤", "group": "matrix"},
            {"key": "matrix-blueprints", "label": "蓝图编排", "icon": "📋", "group": "matrix"},
            {"key": "matrix-atom-ops", "label": "原子操作", "icon": "⚡", "group": "matrix"},
            {"key": "matrix-backup", "label": "备份恢复", "icon": "💾", "group": "matrix"},
            {"key": "matrix-export", "label": "导入导出", "icon": "📦", "group": "matrix"},
        ]

    def _build_machine_map(self) -> dict:
        """聚合 registry 中所有 assigned_machine 及本机/远程状态"""
        accounts = _run_mgmt("list_accounts")
        machines = {}
        for a in accounts:
            owner = a.get("owner_machine", "未分配")
            if owner not in machines:
                machines[owner] = {"总": 0, "本机": 0, "已启用": 0, "已登录": 0, "离线": 0}
            machines[owner]["总"] += 1
            if a.get("is_local"): machines[owner]["本机"] += 1
            if a.get("enabled"): machines[owner]["已启用"] += 1
            if a.get("_status") == "logged_in": machines[owner]["已登录"] += 1
            elif a.get("_status") == "remote": machines[owner]["离线"] += 1
        return machines

    def summary(self, machines):
        try:
            info = _run_mgmt("system_info")
            _run_mgmt("publish_status")  # 写 cross_machine
            accounts = _run_mgmt("list_accounts")
        except Exception as e:
            return {"error": str(e)}

        # 本机概览
        local = [a for a in accounts if a.get("is_local")]
        local_enabled = sum(1 for a in local if a.get("enabled"))
        local_logged = sum(1 for a in local if a.get("_status") == "logged_in")
        all_enabled = sum(1 for a in accounts if a.get("enabled"))

        machine_map = self._build_machine_map()

        # 聚合其他机器数据
        for d in get_plugin_data(self.name):
            hn = d.get("hostname", "")
            if hn and hn != HOSTNAME:
                data = d.get("data", {})
                if hn not in machine_map:
                    machine_map[hn] = data.get("account_summary", {"_note": "在线"})

        return {
            "注册表账号": info["total_accounts"],
            "本机": len(local),
            "本机已启用": local_enabled,
            "本机已登录": local_logged,
            "各机器": machine_map,
        }

    def detail(self, machine=""):
        try:
            _run_mgmt("publish_status")
            info = _run_mgmt("system_info")
            accounts = _run_mgmt("list_accounts")
            blueprints = _run_mgmt("list_blueprints")
            ops = _run_mgmt("list_atomic_ops")
        except Exception as e:
            return {HOSTNAME: {"error": str(e)}}

        # 按所有者分组
        by_owner = {}
        for a in accounts:
            owner = a.get("owner_machine", "未分配")
            if owner not in by_owner:
                by_owner[owner] = []
            by_owner[owner].append(a)

        return {HOSTNAME: {
            "系统信息": info,
            "注册表": accounts,          # 完整列表（含远程）
            "按机器分组": by_owner,       # 按 owner 分组更好展示
            "本机账号": [a for a in accounts if a.get("is_local")],
            "蓝图列表": blueprints,
            "原子操作": ops,
            "配置路径": str(AGENT_LOCAL / "tools" / "matrix" / "config"),
        }}

    def actions(self) -> list[dict]:
        return [
            {"name": "刷新数据", "method": "POST", "endpoint": "/api/plugins/matrix/refresh"},
            {"name": "注册表", "method": "GET", "endpoint": "/api/matrix/accounts"},
            {"name": "蓝图管理", "method": "GET", "endpoint": "/api/matrix/blueprints"},
            {"name": "导出账号", "method": "GET", "endpoint": "/api/matrix/export"},
        ]

"""
plugins/federation.py — 联邦管理插件 (v1.0)
显示联邦集群状态、机器列表、同步/对账操作
版本: 1.0.0 | 更新: 2026-06-16
"""
import json, subprocess
from pathlib import Path

from plugins.base import DashboardPlugin, AGENT_SYNC, AGENT_LOCAL, HOSTNAME, MACHINE_UID
from plugins._registry import get_machine_list, get_plugin_data


class FederationDashboardPlugin(DashboardPlugin):
    name = "federation"
    label = "联邦管理"
    icon = "🖥️"
    version = "1.0.0"
    description = "联邦管理：集群状态 / 同步 / 对账 / 远程Shell"
    order = 40

    def summary(self, machines: list[str]) -> dict:
        """返回联邦集群概览"""
        machine_list = get_machine_list()
        all_data = get_plugin_data("guardd")  # list of all machines' data
        online = 0
        for m in machine_list:
            for d in all_data:
                if d.get("hostname") == m or d.get("machine_name") == m:
                    if d.get("status") == "online":
                        online += 1
                    break
        return {
            "总机器": len(machine_list),
            "在线": online,
            "本机": HOSTNAME,
        }

    def detail(self, machine: str) -> dict:
        """返回指定机器的联邦详情"""
        all_data = get_plugin_data("guardd") or []
        data = {}
        for d in all_data:
            if d.get("hostname") == machine or d.get("machine_name") == machine:
                data = d
                break
        return {
            "hostname": data.get("hostname", machine),
            "status": data.get("status", "unknown"),
            "machine_uid": data.get("machine_uid", ""),
            "dashboard_online": data.get("dashboard_online", False),
        }

    def actions(self) -> list[dict]:
        """返回联邦管理可执行操作"""
        return [
            {"name": "sync", "label": "一键同步", "method": "POST",
             "endpoint": "/api/fleet/sync", "description": "Git同步所有机器"},
            {"name": "reconcile", "label": "对账检查", "method": "POST",
             "endpoint": "/api/fleet/reconcile", "description": "检查ORACLE合规性"},
        ]

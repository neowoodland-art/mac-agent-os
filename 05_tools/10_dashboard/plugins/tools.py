"""
plugins/tools.py — 工具集插件 (v1.0)
显示可用工具目录/安装状态
版本: 1.0.0 | 更新: 2026-06-16
"""
from pathlib import Path

from plugins.base import DashboardPlugin, AGENT_SYNC, AGENT_LOCAL, HOSTNAME, MACHINE_UID


class ToolsDashboardPlugin(DashboardPlugin):
    name = "tools"
    label = "工具集"
    icon = "🔧"
    version = "1.0.0"
    description = "工具集：可用工具目录/安装状态"
    order = 65

    def _scan_tools(self) -> list[dict]:
        tools = []
        tools_dir = AGENT_SYNC / "05_tools"
        if tools_dir.exists():
            for d in sorted(tools_dir.iterdir()):
                if d.is_dir() and d.name[0].isdigit():
                    tools.append({
                        "dir": d.name,
                        "path": str(d),
                        "files": len(list(d.glob("*.py"))) if d.exists() else 0,
                    })
        return tools

    def summary(self, machines: list[str]) -> dict:
        tools = self._scan_tools()
        return {
            "工具目录数": len(tools),
            "目录列表": [t["dir"] for t in tools],
        }

    def detail(self, machine: str = "") -> dict:
        return {"machine": machine or HOSTNAME, "tools": self._scan_tools()}

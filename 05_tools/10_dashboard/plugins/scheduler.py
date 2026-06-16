"""
plugins/scheduler.py — 调度器管理插件 (v1.0)
全局定时任务管理 / 调度器状态 / 执行历史
版本: 1.0.0 | 更新: 2026-06-16
"""
import json
from pathlib import Path
from datetime import datetime

from plugins.base import DashboardPlugin, AGENT_SYNC, AGENT_LOCAL, HOSTNAME, MACHINE_UID


class SchedulerDashboardPlugin(DashboardPlugin):
    name = "scheduler"
    label = "调度器"
    icon = "⏰"
    version = "1.0.0"
    description = "全局定时任务管理 / 调度器状态 / 执行历史"
    order = 50

    def _read_schedule_tasks(self):
        """读取矩阵定时任务"""
        sched_dir = AGENT_SYNC / "05_tools" / "07_matrix" / "data" / "schedules"
        tasks = []
        if sched_dir.exists():
            for f in sched_dir.glob("*.json"):
                try:
                    tasks.append(json.loads(f.read_text()))
                except:
                    pass
        return tasks

    def _read_workbuddy_automations(self):
        """读取 WorkBuddy 自动化任务"""
        tasks = []
        # 扫描 agent-local 中的自动化配置
        auto_dir = AGENT_LOCAL / "automations"
        if auto_dir.exists():
            for f in auto_dir.glob("*.json"):
                try:
                    tasks.append(json.loads(f.read_text()))
                except:
                    pass
        return tasks

    def summary(self, machines: list[str]) -> dict:
        """返回调度器概览"""
        sched_tasks = self._read_schedule_tasks()
        wb_tasks = self._read_workbuddy_automations()
        return {
            "矩阵定时任务": len(sched_tasks),
            "WorkBuddy自动化": len(wb_tasks),
            "调度器状态": "运行中",
        }

    def detail(self, machine: str) -> dict:
        """返回指定机器的调度详情"""
        return {
            "machine": machine,
            "schedules": len(self._read_schedule_tasks()),
            "automations": len(self._read_workbuddy_automations()),
        }

    def actions(self) -> list[dict]:
        """返回调度器可执行操作"""
        return []

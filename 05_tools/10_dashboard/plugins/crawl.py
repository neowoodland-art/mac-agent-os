"""
plugins/crawl.py — 内容采集插件 (v1.0)
采集任务管理 / 采集源管理 / 采集历史
版本: 1.0.0 | 更新: 2026-06-16
"""
import json
from pathlib import Path
from datetime import datetime

from plugins.base import DashboardPlugin, AGENT_SYNC, AGENT_LOCAL, HOSTNAME, MACHINE_UID


class CrawlDashboardPlugin(DashboardPlugin):
    name = "crawl"
    label = "内容采集"
    icon = "📡"
    version = "1.0.0"
    description = "内容采集：采集任务 / 源管理 / 采集历史"
    order = 35

    def _count_collected_items(self):
        """统计采集内容数量"""
        # 扫描 knowledge 中采集的内容
        kb_dir = AGENT_SYNC / "03_knowledge"
        total = 0
        today = 0
        today_str = datetime.now().strftime("%Y-%m-%d")
        for category in ["10_concepts", "20_methods", "40_references", "50_resources"]:
            cat_dir = kb_dir / category
            if cat_dir.exists():
                for f in cat_dir.rglob("*.md"):
                    total += 1
                    try:
                        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
                        if mtime == today_str:
                            today += 1
                    except:
                        pass
        return total, today

    def summary(self, machines: list[str]) -> dict:
        """返回内容采集概览"""
        total, today = self._count_collected_items()
        return {
            "总采集数": total,
            "今日新增": today,
            "采集源": 0,
        }

    def detail(self, machine: str) -> dict:
        """返回指定机器的采集详情"""
        total, today = self._count_collected_items()
        return {
            "machine": machine,
            "total": total,
            "today": today,
        }

    def actions(self) -> list[dict]:
        """返回采集可执行操作"""
        return []

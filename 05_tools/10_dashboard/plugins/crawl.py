"""
plugins/crawl.py — 内容采集插件 v1.1
采集任务管理 / 采集源管理 / 采集历史 / 数据库统计
版本: 1.1.0 | 更新: 2026-07-10
"""
import json, logging
from pathlib import Path
from datetime import datetime

from plugins.base import DashboardPlugin, AGENT_SYNC, AGENT_LOCAL, HOSTNAME, MACHINE_UID

logger = logging.getLogger("dashboard.plugins.crawl")


class CrawlDashboardPlugin(DashboardPlugin):
    name = "crawl"
    label = "内容采集"
    icon = "📡"
    version = "1.1.0"
    description = "内容采集：采集任务 / 源管理 / 采集历史"
    order = 35

    def _get_collect_stats(self):
        """从采集数据库获取统计"""
        try:
            from services.collect_db import CollectDB
            db = CollectDB()
            return {
                "total": sum(db.count_by_platform().values()),
                "today": db.count_today(),
                "sources": db.sources_count(),
            }
        except Exception as e:
            logger.warning(f"采集数据库不可用: {e}")
            return None

    def _count_knowledge_items(self):
        """统计知识库中采集的内容"""
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
        """返回内容采集概览（数据库统计优先）"""
        db_stats = self._get_collect_stats()
        if db_stats:
            return {
                "总采集数": db_stats["total"],
                "今日新增": db_stats["today"],
                "采集源": db_stats["sources"],
            }
        # 兜底：知识库统计
        total, today = self._count_knowledge_items()
        return {
            "总采集数": total,
            "今日新增": today,
            "采集源": 0,
        }

    def detail(self, machine: str) -> dict:
        """返回指定机器的采集详情"""
        db_stats = self._get_collect_stats()
        if db_stats:
            return {
                "machine": machine,
                "total": db_stats["total"],
                "today": db_stats["today"],
                "sources": db_stats["sources"],
            }
        total, today = self._count_knowledge_items()
        return {"machine": machine, "total": total, "today": today}

    def actions(self) -> list[dict]:
        """返回采集可执行操作"""
        return [
            {"label": "新建采集", "action": "switchView('collect')"},
            {"label": "采集管理", "action": "switchView('collect')"},
        ]

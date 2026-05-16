"""
plugins/guardd.py — 联邦状态监控插件 (guardd / 跨机器状态)

读取 cross_machine/status/ 下的所有心跳数据，展示多机联邦状态。
版本: 1.0.0 | 更新: 2026-05-16
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from plugins.base import DashboardPlugin

SYNC_ROOT = Path(__file__).resolve().parents[3]  # → agent-sync/
CROSS_MACHINE = SYNC_ROOT / "04_memory" / "cross_machine"
DIR_STATUS = CROSS_MACHINE / "status"
DIR_EVENTS = CROSS_MACHINE / "events"


class GuarddPlugin(DashboardPlugin):
    name = "guardd"
    label = "联邦状态"
    order = 10
    description = "跨机器联邦状态监控：心跳 / 事件 / 任务 / 加密通道"

    _machines_cache = None

    def _read_machines(self):
        """扫描所有机器的状态文件"""
        machines = []
        if not DIR_STATUS.exists():
            return machines
        for host_dir in sorted(DIR_STATUS.iterdir()):
            if not host_dir.is_dir():
                continue
            hb_path = host_dir / "heartbeat.json"
            if not hb_path.exists():
                continue
            try:
                data = json.loads(hb_path.read_text())
                last_seen = data.get("last_seen", "")
                # 判断是否在线（15分钟无心跳判离线）
                if last_seen:
                    try:
                        last_dt = datetime.fromisoformat(last_seen)
                        offline_threshold = datetime.now(timezone.utc).timestamp() - 900
                        is_online = last_dt.timestamp() > offline_threshold
                    except:
                        is_online = False
                else:
                    is_online = False

                machines.append({
                    "hostname": data.get("hostname", host_dir.name),
                    "status": "online" if is_online else "offline",
                    "last_seen": last_seen,
                    "os": data.get("os", ""),
                    "cpu_load": data.get("cpu", {}).get("load_1m", 0),
                    "disk_available_gb": data.get("disk", {}).get("available_gb", 0),
                    "guardd_version": data.get("guardd_version", ""),
                    "current_task": data.get("current_task"),
                })
            except:
                continue
        return machines

    def _count_events(self, days=7):
        """统计近期事件数"""
        total = 0
        if not DIR_EVENTS.exists():
            return total
        for d in DIR_EVENTS.iterdir():
            if d.is_dir():
                total += len(list(d.iterdir()))
        return total

    def is_available(self) -> bool:
        return DIR_STATUS.exists() and any(DIR_STATUS.iterdir())

    def get_summary(self) -> dict:
        machines = self._read_machines()
        online = sum(1 for m in machines if m["status"] == "online")
        return {
            "total_machines": len(machines),
            "online_machines": online,
            "offline_machines": len(machines) - online,
            "machines": machines,
            "events_7d": self._count_events(),
        }

    def get_productions(self, limit=50, offset=0, strategy=None, status=None):
        """返回各机器的详细状态"""
        machines = self._read_machines()
        for m in machines:
            m["guardd_version"] = m.get("guardd_version") or "unknown"
            m["task"] = m.get("current_task") or "none"
        return machines

    def get_production_detail(self, production_id: str) -> Optional[dict]:
        # production_id 就是 hostname
        machines = self._read_machines()
        for m in machines:
            if m["hostname"] == production_id:
                return m
        return None

    def get_sidebar_links(self) -> list:
        return [
            {"label": "联邦总览", "url": "/#/federation"},
            {"label": "在线机器", "url": "/#/federation?status=online"},
        ]

"""
heartbeat.py — 增强心跳上报 (guardd 模块)

职责:
  - 每15秒采集系统状态 + 任务状态 + 槽位状态
  - 上报到 Dashboard (POST /api/push/heartbeat)
  - 本地写入 status/{hostname}/heartbeat.json
"""
import json
import logging
import os
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from modules.task_store import TaskStore
from modules.slot_manager import BrowserSlotManager
from modules.scheduler import Scheduler

logger = logging.getLogger("guardd.heartbeat")


class HeartbeatReporter:
    """增强心跳上报器"""

    def __init__(self, task_store: TaskStore, slot_manager: BrowserSlotManager,
                 scheduler: Scheduler, hostname: str, machine_uid: str,
                 dashboard_url: str = None):
        self.task_store = task_store
        self.slot_manager = slot_manager
        self.scheduler = scheduler
        self.hostname = hostname
        self.machine_uid = machine_uid
        self.dashboard_url = dashboard_url or "http://127.0.0.1:9988"

    def collect(self) -> dict:
        """采集完整状态"""
        slot_usage = self.slot_manager.get_usage() if self.slot_manager else {"max": 0, "used": 0, "slots": []}

        # 收集任务状态
        active = self.scheduler.active_task
        queued = self.scheduler.queue.get_all() if hasattr(self.scheduler, 'queue') else []
        task_counts = self.task_store.count()

        # 系统状态
        cpu_load = -1
        try:
            cpu_load = round(os.getloadavg()[0], 2)
        except OSError:
            pass

        heartbeat = {
            "hostname": self.hostname,
            "machine_uid": self.machine_uid,
            "status": "online",
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "version": "4.3.0",
            "slots": slot_usage,
            "tasks": {
                "active": self._task_to_heartbeat(active) if active else None,
                "queued": [
                    {"task_id": q["task_id"], "priority": q.get("priority", 1),
                     "estimated_at": q.get("scheduled_at", 0)}
                    for q in queued[:20]
                ],
                "counts": task_counts,
            },
            "system": {
                "cpu_load_1m": cpu_load,
                "browsers_open": slot_usage.get("used", 0),
            },
        }
        return heartbeat

    def _task_to_heartbeat(self, task: dict) -> dict:
        """把 task dict 转成心跳用的紧凑格式"""
        if not task:
            return None
        return {
            "task_id": task.get("task_id", ""),
            "cmd_type": task.get("cmd_type", ""),
            "type": task.get("task_type", task.get("cmd_type", "")),
            "account": (task.get("accounts") or [""])[0],
            "blueprint": task.get("blueprint", ""),
            "status": task.get("status", ""),
            "started_at": task.get("started_at", 0),
            "elapsed_sec": int(time.time() - task.get("started_at", time.time())),
            "progress": {
                "current_step": task.get("current_step", ""),
                "step_index": task.get("step_index", 0),
                "total_steps": task.get("total_steps", 0),
            },
        }

    def send_to_dashboard(self, heartbeat: dict = None):
        """发送心跳到 Dashboard"""
        if heartbeat is None:
            heartbeat = self.collect()

        try:
            payload = json.dumps(heartbeat, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                f"{self.dashboard_url}/api/push/heartbeat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            logger.debug(f"心跳推送失败: {e}")

    def write_local(self, heartbeat: dict = None):
        """写入本地 heartbeat.json"""
        if heartbeat is None:
            heartbeat = self.collect()
        try:
            home = Path.home()
            status_dir = home / "workbuddy-agent-os" / "agent-local" / "runtime" / "guardd" / self.hostname
            status_dir.mkdir(parents=True, exist_ok=True)
            path = status_dir / "heartbeat.json"
            path.write_text(json.dumps(heartbeat, indent=2, ensure_ascii=False), encoding="utf-8")

            # also write live file
            live_dir = status_dir.parent / "live"
            live_dir.mkdir(parents=True, exist_ok=True)
            (live_dir / f"{self.machine_uid}.json").write_text(
                json.dumps(heartbeat, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"本地心跳写入失败: {e}")

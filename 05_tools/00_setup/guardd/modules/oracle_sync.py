"""
oracle_sync.py — ORACLE 定时任务同步 (guardd 模块)

职责:
  - guardd 启动时读取 ORACLE.yaml 的 schedules 节
  - 将定时任务导入到 task_store
  - 每6小时增量同步
"""
import logging
import time
from pathlib import Path
from modules.task_store import TaskStore, STATUS_SCHEDULED

logger = logging.getLogger("guardd.oracle_sync")
SYNC_INTERVAL = 6 * 3600  # 6小时


class OracleSync:
    """ORACLE.yaml 定时任务同步器"""

    def __init__(self, task_store: TaskStore):
        self.task_store = task_store
        self.last_sync = 0
        self.home = Path.home()
        self.oracle_path = self.home / "workbuddy-agent-os" / "agent-sync" / "ORACLE.yaml"

    def sync(self):
        """执行同步（启动时 + 周期调用）"""
        now = time.time()
        if now - self.last_sync < SYNC_INTERVAL:
            return
        self.last_sync = now

        if not self.oracle_path.exists():
            logger.info("  ORACLE.yaml 不存在，跳过定时任务同步")
            return

        try:
            import yaml
            oracle = yaml.safe_load(self.oracle_path.read_text())
            schedules = oracle.get("schedules", [])
            count = 0
            for s in schedules:
                task_id = f"oracle_{s['name']}_{int(now)}"
                # 检查是否已存在
                existing = self.task_store.get(task_id)
                if existing:
                    continue

                blueprint = s.get("action", "").replace("mc run", "").strip()
                if not blueprint:
                    blueprint = s.get("params", {}).get("blueprint", "douyin_daily")

                task = {
                    "task_id": task_id,
                    "cmd_type": "nurture",
                    "source": "oracle",
                    "accounts": s.get("accounts", "all"),
                    "machine": s.get("on_machines", "*"),
                    "priority": 1,
                    "schedule_type": "cron",
                    "cron_expr": s["schedule"],
                    "blueprint": blueprint,
                    "rounds": s.get("params", {}).get("rounds", 10),
                    "status": STATUS_SCHEDULED,
                    "created_at": now,
                }
                self.task_store.save(task)
                count += 1
                logger.info(f"  📅 [{task_id}] 导入定时任务: {s['schedule']} {blueprint}")

            if count:
                logger.info(f"  ✅ 导入 {count} 条定时任务")
            else:
                logger.debug("  没有新的定时任务需要导入")

        except Exception as e:
            logger.error(f"  ORACLE 同步异常: {e}")

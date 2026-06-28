"""
schedule_bridge.py — 定时任务桥接 (guardd 模块)

职责:
  - 读取 mc/scheduler 的 schedule.yaml
  - 检查到期的定时任务
  - 提交到 guardd scheduler 执行（P1 优先级）
  - 记录最后执行时间，防止重复触发

配置路径: 05_tools/07_matrix/scripts/config/schedule.yaml
"""
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from modules.task_store import TaskStore

logger = logging.getLogger("guardd.schedule_bridge")

HOME = Path.home()
SCRIPTS_DIR = HOME / "workbuddy-agent-os" / "agent-sync" / "05_tools" / "07_matrix" / "scripts"
SCHEDULE_YAML = SCRIPTS_DIR / "config" / "schedule.yaml"
LAST_RUN_FILE = HOME / "workbuddy-agent-os" / "agent-local" / "runtime" / "guardd" / "schedule_last_run.json"

CHECK_INTERVAL = 60  # 每 60 秒检查一次


class ScheduleBridge:
    """定时任务 → guardd 调度器桥接"""

    def __init__(self, task_store: TaskStore, scheduler=None, hostname: str = ""):
        self.task_store = task_store
        self.scheduler = scheduler
        self.hostname = hostname
        self.last_check = 0
        self._last_run_cache = {}

    def load_last_runs(self):
        """加载上次执行时间记录"""
        if LAST_RUN_FILE.exists():
            try:
                self._last_run_cache = json.loads(LAST_RUN_FILE.read_text())
            except Exception:
                self._last_run_cache = {}

    def save_last_runs(self):
        """保存上次执行时间"""
        LAST_RUN_FILE.parent.mkdir(parents=True, exist_ok=True)
        LAST_RUN_FILE.write_text(json.dumps(self._last_run_cache, indent=2))

    def check_schedules(self):
        """检查是否有定时任务到期"""
        now = time.time()
        if now - self.last_check < CHECK_INTERVAL:
            return 0
        self.last_check = now

        if not SCHEDULE_YAML.exists():
            return 0

        try:
            import yaml
            data = yaml.safe_load(SCHEDULE_YAML.read_text())
            schedules = data.get("schedules", {}) if data else {}
        except Exception as e:
            logger.warning(f"schedule.yaml 读取失败: {e}")
            return 0

        self.load_last_runs()
        triggered = 0
        now_dt = datetime.now()
        today_minutes = now_dt.hour * 60 + now_dt.minute
        weekday = now_dt.isoweekday()  # 1=周一..7=周日

        for sid, s in schedules.items():
            if not s.get("enabled", False):
                continue

            # 检查星期匹配
            days_str = s.get("days", "1,2,3,4,5,6,7")
            days = [int(d.strip()) for d in days_str.split(",") if d.strip()]
            if weekday not in days:
                continue

            # 检查时间匹配
            time_str = s.get("time", "")
            if not time_str:
                continue
            try:
                h, m = time_str.split(":")
                schedule_minutes = int(h) * 60 + int(m)
            except (ValueError, TypeError):
                continue

            # 允许 1 分钟误差（防止跳过）
            if abs(today_minutes - schedule_minutes) > 1:
                continue

            # 检查是否已触发过（防止重复）
            last_run = self._last_run_cache.get(sid, 0)
            if now - last_run < CHECK_INTERVAL * 2:
                continue

            # 提交到 guardd scheduler
            account = s.get("account", "")
            blueprint = s.get("blueprint", "douyin_daily")
            rounds = s.get("rounds", 3)

            task_id = f"schedule_{sid}_{int(now)}"
            task = {
                "task_id": task_id,
                "cmd_type": "nurture",
                "accounts": [account] if account else [],
                "blueprint": blueprint,
                "rounds": rounds,
                "priority": 1,  # P1 日常
                "source": "schedule",
                "schedule_id": sid,
                "params": {},
            }

            if self.scheduler and hasattr(self.scheduler, 'submit_task'):
                self.scheduler.submit_task(task)
                logger.info(f"  📅 [{task_id}] 定时任务触发: {sid} → {blueprint} @ {account}")
            else:
                logger.warning(f"  ⚠️ scheduler 不可用，定时任务 {sid} 无法提交")

            self._last_run_cache[sid] = now
            triggered += 1

        if triggered:
            self.save_last_runs()

        return triggered

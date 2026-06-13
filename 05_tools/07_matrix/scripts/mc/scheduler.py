"""
mc/scheduler.py — 定时任务调度器 v1.0

支持:
  - YAML 配置定时任务
  - 按 cron 表达式或间隔时间执行
  - 自动加载人设参数
  - 日志记录

配置文件: config/schedule.yaml
  格式:
    schedules:
      douyin_daily_morning:
        enabled: true
        account: douyin_test
        blueprint: douyin_daily
        rounds: 3
        time: "09:00"          # 每天固定时间
      xhs_daily_noon:
        enabled: true
        account: xhs_01
        blueprint: xhs_daily
        rounds: 2
        time: "12:30"
      douyin_search_evening:
        enabled: true
        account: douyin_test
        blueprint: douyin_search
        args:
          keyword: "@persona"   # 自动用人设关键词
        rounds: 1
        time: "18:00"
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

HOME = Path.home()
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = SCRIPTS_DIR / "config"
SCHEDULE_YAML = CONFIG_DIR / "schedule.yaml"
SCHEDULE_YAML.parent.mkdir(parents=True, exist_ok=True)

# 默认配置模板
DEFAULT_CONFIG = """# Matrix 定时任务配置
# time 格式: HH:MM（每天固定时间）
schedules:
  douyin_daily_morning:
    enabled: false
    account: douyin_test
    blueprint: douyin_daily
    rounds: 3
    time: "09:00"
  xhs_daily_noon:
    enabled: false
    account: xhs_01
    blueprint: xhs_daily
    rounds: 2
    time: "12:30"
  douyin_search_evening:
    enabled: false
    account: douyin_test
    blueprint: douyin_search
    rounds: 1
    time: "18:00"
"""


def load_schedules() -> list[dict]:
    """读取定时任务配置"""
    if not SCHEDULE_YAML.exists():
        SCHEDULE_YAML.write_text(DEFAULT_CONFIG)
        return []
    try:
        import yaml
        data = yaml.safe_load(SCHEDULE_YAML.read_text())
        schedules = data.get("schedules", {})
        result = []
        for sid, cfg in schedules.items():
            if cfg.get("enabled", False):
                cfg["id"] = sid
                result.append(cfg)
        return result
    except Exception as e:
        log.error(f"读取定时配置失败: {e}")
        return []


def save_schedules(schedules: dict):
    """保存定时任务配置"""
    import yaml
    SCHEDULE_YAML.write_text(yaml.dump(
        {"schedules": schedules}, allow_unicode=True, default_flow_style=False
    ))


def get_due_schedules() -> list[dict]:
    """获取当前时间到点的任务"""
    now = datetime.now().strftime("%H:%M")
    all_schedules = load_schedules()
    due = []
    for s in all_schedules:
        task_time = s.get("time", "")
        if task_time == now:
            due.append(s)
    return due


async def run_scheduled_task(schedule: dict) -> dict:
    """执行单个定时任务"""
    account = schedule.get("account", "")
    blueprint = schedule.get("blueprint", "")
    rounds = schedule.get("rounds", 1)
    args = schedule.get("args", {})

    # 解析 @persona 标记
    for k, v in args.items():
        if isinstance(v, str) and v == "@persona":
            try:
                from mc.corpus import CorpusManager
                cm = CorpusManager()
                kws = cm.get_search_keywords(account)
                if kws:
                    args[k] = kws[0]
            except:
                args[k] = "热门推荐"

    log.info(f"⏰ 执行定时任务: {account} → {blueprint} ({rounds}轮)")

    from mc.engine import BatchEngine
    engine = BatchEngine(
        accounts=[account],
        blueprints=[blueprint],
        rounds=rounds,
    )
    engine.task_params = args
    report = await engine.run()
    result = report.to_dict()
    result["schedule_id"] = schedule.get("id", "")
    result["scheduled_time"] = schedule.get("time", "")
    return result


async def scheduler_loop():
    """主循环：每分钟检查一次到点任务"""
    log.info("🕐 定时调度器已启动")
    last_minute = ""
    while True:
        now_minute = datetime.now().strftime("%H:%M")
        if now_minute != last_minute:
            last_minute = now_minute
            due = get_due_schedules()
            for s in due:
                log.info(f"⏰ [{now_minute}] 触发: {s.get('id','?')}")
                try:
                    result = await run_scheduled_task(s)
                    log.info(f"  ✅ 完成: {result.get('success',0)}/{result.get('total_steps',0)}")
                except Exception as e:
                    log.error(f"  ❌ 失败: {e}")
        await asyncio.sleep(30)


# ── CLI ──

def cmd_schedule_list():
    """列出所有定时任务"""
    scheds = load_schedules()
    if not scheds:
        print("暂无定时任务")
        print("配置位置: config/schedule.yaml")
        return
    print(f"\n{'ID':25s} {'账号':20s} {'蓝图':25s} {'时间':8s} {'轮数':4s}")
    print("-" * 85)
    for s in scheds:
        print(f"{s.get('id','?'):25s} {s.get('account','?'):20s} "
              f"{s.get('blueprint','?'):25s} {s.get('time','?'):8s} {s.get('rounds',1):4d}")


def cmd_schedule_add(sid: str, account: str, blueprint: str,
                     time_str: str, rounds: int = 1, args: str = ""):
    """添加定时任务"""
    import yaml
    data = {"schedules": {}} if not SCHEDULE_YAML.exists() else yaml.safe_load(SCHEDULE_YAML.read_text())
    data["schedules"][sid] = {
        "enabled": True,
        "account": account,
        "blueprint": blueprint,
        "rounds": rounds,
        "time": time_str,
    }
    if args:
        data["schedules"][sid]["args"] = {"keyword": args}
    save_schedules(data["schedules"])
    print(f"✅ 定时任务 '{sid}' 已添加")


def cmd_schedule_remove(sid: str):
    """删除定时任务"""
    import yaml
    if not SCHEDULE_YAML.exists():
        print("无配置")
        return
    data = yaml.safe_load(SCHEDULE_YAML.read_text())
    if sid in data.get("schedules", {}):
        del data["schedules"][sid]
        save_schedules(data["schedules"])
        print(f"✅ 定时任务 '{sid}' 已删除")
    else:
        print(f"❌ 未找到定时任务 '{sid}'")

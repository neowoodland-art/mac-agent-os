"""
mc/scheduler.py — 定时任务调度器 v2.0

完整功能:
  - YAML 配置定时任务（支持 time + days 星期过滤）
  - 历史执行记录（JSONL）+ 联邦同步
  - 自动加载人设参数
  - 日志记录

配置文件: config/schedule.yaml
  格式:
    schedules:
      douyin_daily:
        enabled: true
        account: douyin_test
        blueprint: douyin_daily
        rounds: 3
        time: "09:00"
        days: "1,2,3,4,5,6,7"   # 1=周一..7=周日

历史记录: agent-local/tools/matrix/logs/schedule_history.jsonl
联邦同步: 04_memory/cross_machine/data/matrix/schedule_results.json
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

HOME = Path.home()
from matrix_mgmt import AGENT_SYNC, AGENT_LOCAL

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = SCRIPTS_DIR / "config"
SCHEDULE_YAML = CONFIG_DIR / "schedule.yaml"
SCHEDULE_YAML.parent.mkdir(parents=True, exist_ok=True)

# 历史记录（本机）
HISTORY_DIR = AGENT_LOCAL / "tools" / "matrix" / "logs"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = HISTORY_DIR / "schedule_history.jsonl"

# 联邦同步
CROSS_MACHINE_MATRIX = AGENT_SYNC / "04_memory" / "cross_machine" / "data" / "matrix"
CROSS_MACHINE_MATRIX.mkdir(parents=True, exist_ok=True)
FEDERATION_FILE = CROSS_MACHINE_MATRIX / "schedule_results.json"

HOSTNAME = os.uname().nodename

DEFAULT_CONFIG = """# Matrix 定时任务配置
# time 格式: HH:MM（每天固定时间）
# days 格式: 1,2,3,4,5,6,7（1=周一..7=周日，默认每天）
schedules:
  douyin_daily_morning:
    enabled: false
    account: douyin_test
    blueprint: douyin_daily
    rounds: 3
    time: "09:00"
    days: "1,2,3,4,5,6,7"
  xhs_daily_noon:
    enabled: false
    account: xhs_01
    blueprint: xhs_daily
    rounds: 2
    time: "12:30"
    days: "1,2,3,4,5,6,7"
"""


# ── 配置读写 ──

def load_all_schedules() -> dict:
    """读取所有任务配置（含禁用）"""
    if not SCHEDULE_YAML.exists():
        SCHEDULE_YAML.write_text(DEFAULT_CONFIG)
        return {}
    try:
        import yaml
        data = yaml.safe_load(SCHEDULE_YAML.read_text())
        return data.get("schedules", {})
    except Exception as e:
        log.error(f"读取定时配置失败: {e}")
        return {}


def load_enabled_schedules() -> list[dict]:
    """读取启用的任务（含今天是否执行判断）"""
    all_s = load_all_schedules()
    today = datetime.now().isoweekday()  # 1=周一..7=周日
    result = []
    for sid, cfg in all_s.items():
        if not cfg.get("enabled", False):
            continue
        # days 过滤
        days_str = cfg.get("days", "1,2,3,4,5,6,7")
        try:
            days = [int(d.strip()) for d in days_str.split(",")]
        except:
            days = [1, 2, 3, 4, 5, 6, 7]
        if today not in days:
            continue
        cfg["id"] = sid
        result.append(cfg)
    return result


def save_all_schedules(schedules: dict):
    """保存全部任务配置"""
    import yaml
    SCHEDULE_YAML.write_text(yaml.dump(
        {"schedules": schedules}, allow_unicode=True, default_flow_style=False
    ))


# ── 历史记录 ──

def write_history(entry: dict):
    """追加一条历史记录"""
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_history(schedule_id: str = None, limit: int = 20) -> list[dict]:
    """读取历史记录，默认最近20条"""
    if not HISTORY_FILE.exists():
        return []
    entries = []
    for line in reversed(HISTORY_FILE.read_text().splitlines()):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            if schedule_id and e.get("schedule_id") != schedule_id:
                continue
            entries.append(e)
            if len(entries) >= limit:
                break
        except:
            pass
    return entries


def sync_to_federation(result: dict):
    """同步执行结果到联邦数据目录"""
    try:
        fed = {}
        if FEDERATION_FILE.exists():
            fed = json.loads(FEDERATION_FILE.read_text())
        host_data = fed.get(HOSTNAME, {})
        sid = result.get("schedule_id", "unknown")
        host_data[sid] = {
            "last_run": result.get("timestamp", datetime.now().isoformat()),
            "status": "success" if result.get("failed", 0) == 0 else "partial",
            "success": result.get("success", 0),
            "failed": result.get("failed", 0),
            "duration": result.get("duration", 0),
            "blueprint": result.get("blueprint", ""),
        }
        fed[HOSTNAME] = host_data
        FEDERATION_FILE.write_text(json.dumps(fed, ensure_ascii=False, indent=2))
    except Exception as e:
        log.error(f"联邦同步失败: {e}")


# ── 任务执行 ──

def get_due_schedules() -> list[dict]:
    """获取当前时间到点的任务"""
    now = datetime.now().strftime("%H:%M")
    return [s for s in load_enabled_schedules() if s.get("time", "") == now]


async def run_scheduled_task(schedule: dict) -> dict:
    """执行单个定时任务"""
    account = schedule.get("account", "")
    blueprint = schedule.get("blueprint", "")
    rounds = schedule.get("rounds", 1)
    args = dict(schedule.get("args", {}))

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
    result["timestamp"] = datetime.now().isoformat()
    result["hostname"] = HOSTNAME

    # 写入历史 + 联邦同步
    write_history(result)
    sync_to_federation(result)

    return result


async def scheduler_loop():
    """主循环：每30秒检查一次到点任务"""
    log.info("🕐 定时调度器已启动")
    last_minute = ""
    while True:
        now_minute = datetime.now().strftime("%H:%M")
        if now_minute != last_minute:
            last_minute = now_minute
            due = get_due_schedules()
            for s in due:
                sid = s.get("id", "?")
                log.info(f"⏰ [{now_minute}] 触发: {sid}")
                try:
                    result = await run_scheduled_task(s)
                    log.info(f"  ✅ {sid}: {result.get('success',0)}/{result.get('total_steps',0)} 步成功, 耗时{result.get('duration',0)}s")
                except Exception as e:
                    log.error(f"  ❌ {sid}: {e}")
                    write_history({
                        "schedule_id": sid, "scheduled_time": s.get("time", ""),
                        "timestamp": datetime.now().isoformat(), "hostname": HOSTNAME,
                        "status": "error", "error": str(e),
                    })
        await asyncio.sleep(30)


# ── CLI ──

def cmd_schedule_list():
    """列出所有定时任务"""
    all_s = load_all_schedules()
    if not all_s:
        print("暂无定时任务")
        print("配置位置: config/schedule.yaml")
        return
    print(f"\n{'ID':25s} {'账号':20s} {'蓝图':25s} {'时间':8s} {'轮数':4s} {'天数':12s} {'状态':6s}")
    print("-" * 100)
    for sid, cfg in all_s.items():
        enabled = "🟢" if cfg.get("enabled", False) else "⚪"
        days = cfg.get("days", "每天")
        print(f"{sid:25s} {cfg.get('account','?'):20s} "
              f"{cfg.get('blueprint','?'):25s} {cfg.get('time','?'):8s} "
              f"{cfg.get('rounds',1):4d} {days:12s} {enabled:6s}")


def cmd_schedule_add(sid: str, account: str, blueprint: str,
                     time_str: str, rounds: int = 1, days: str = "1,2,3,4,5,6,7",
                     args: str = ""):
    """添加定时任务"""
    all_s = load_all_schedules()
    all_s[sid] = {
        "enabled": True,
        "account": account,
        "blueprint": blueprint,
        "rounds": rounds,
        "time": time_str,
        "days": days,
    }
    if args:
        all_s[sid]["args"] = {"keyword": args}
    save_all_schedules(all_s)
    print(f"✅ 定时任务 '{sid}' 已添加（{time_str} 每天{days}）")


def cmd_schedule_remove(sid: str):
    """删除定时任务"""
    all_s = load_all_schedules()
    if sid in all_s:
        del all_s[sid]
        save_all_schedules(all_s)
        print(f"✅ 定时任务 '{sid}' 已删除")
    else:
        print(f"❌ 未找到定时任务 '{sid}'")


def cmd_schedule_history(sid: str = "", limit: int = 10):
    """查看历史记录"""
    entries = read_history(sid if sid else None, limit)
    if not entries:
        print("暂无历史记录")
        return
    print(f"\n最近 {len(entries)} 条执行记录{' ('+sid+')' if sid else ''}:")
    print(f"{'时间':20s} {'任务':25s} {'状态':10s} {'成功':6s} {'失败':6s} {'耗时':6s}")
    print("-" * 75)
    for e in entries:
        st = e.get("status", e.get("error", "?"))
        print(f"{e.get('timestamp','?'):20s} {e.get('schedule_id','?'):25s} "
              f"{st:10s} {str(e.get('success','?')):6s} {str(e.get('failed','?')):6s} "
              f"{str(e.get('duration','?')):6s}")

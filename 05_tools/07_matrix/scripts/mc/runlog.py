"""
mc/runlog.py — 结构化运行日志 v1.0

每次 mc run 执行后，将结果写入 JSONL 格式的结构化日志。
存储位置: agent-local/tools/matrix/logs/run_{date}_{account}.jsonl

供智能体和 Dashboard 读取分析。不依赖 print log。
"""
import json
from datetime import datetime
from pathlib import Path

HOME = Path.home()
from matrix_mgmt import AGENT_LOCAL
LOG_DIR = AGENT_LOCAL / "tools" / "matrix" / "logs"


def write_run_log(account_id: str, report: dict):
    """追加一条运行记录到当日 JSONL 日志"""
    log_path = LOG_DIR / f"run_{datetime.now().strftime('%Y%m%d')}_{account_id}.jsonl"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        **report,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_latest_log(account_id: str, date_str: str = None) -> list[dict]:
    """读取指定日期的运行日志（默认今天）"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    log_path = LOG_DIR / f"run_{date_str}_{account_id}.jsonl"
    if not log_path.exists():
        return []
    entries = []
    for line in log_path.read_text().splitlines():
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def get_today_summary() -> dict:
    """获取今日所有账号的运行摘要"""
    today = datetime.now().strftime("%Y%m%d")
    summary = {"date": today, "accounts": {}}
    for f in sorted(LOG_DIR.glob(f"run_{today}_*.jsonl")):
        account = f.stem.replace(f"run_{today}_", "")
        entries = read_latest_log(account, today)
        if entries:
            last = entries[-1]
            summary["accounts"][account] = {
                "runs": len(entries),
                "last_blueprint": last.get("blueprint", "?"),
                "last_success": last.get("success", 0),
                "last_failed": last.get("failed", 0),
                "last_time": last.get("timestamp", "?"),
            }
    return summary

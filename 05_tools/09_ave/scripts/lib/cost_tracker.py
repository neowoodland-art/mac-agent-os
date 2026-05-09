"""
AVE 成本追踪器

记录每次 API 调用的费用估算, 防止不知不觉扣费过多。

用法:
  from lib.cost_tracker import CostTracker
  tracker = CostTracker()
  tracker.log("OmniHuman", duration=4.04, resolution="480P")
  tracker.summary()
"""
import json
import os
from datetime import datetime
from pathlib import Path

# ── 已知价格 (元/秒) ───────────────────────────────────────
# 来源: 火山引擎即梦AI官方定价 (截至2026-05-09)
PRICING = {
    # OmniHuman 1.5
    "OmniHuman_480P": 0.5,     # ¥0.5/秒
    "OmniHuman_720P": 0.9,     # ¥0.9/秒
    # Wan2.2 (备用)
    "Wan2.2_480P": 0.5,
    "Wan2.2_720P": 0.9,
    # DreamActor M1 (估算, 与OmniHuman同级)
    "DreamActor_480P": 0.5,
    "DreamActor_720P": 0.9,
    # CosyVoice TTS (阿里云百炼, 按字符计费约 ¥0.002/字符)
    "CosyVoice_per_char": 0.002,
    # Pexels (免费)
    "Pexels": 0,
}

# ── 日志路径 ───────────────────────────────────────────────
LOG_DIR = Path(os.environ.get("AVE_LOCAL_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local"))) / "tools" / "ave" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "cost_log.jsonl"


class CostTracker:
    """API 成本追踪器"""

    def __init__(self):
        self._session_log: list[dict] = []

    def log(self, service: str, duration: float = 0, resolution: str = "480P",
            chars: int = 0, status: str = "success", note: str = ""):
        """
        记录一次 API 调用

        参数:
          service: API 服务名 (OmniHuman, DreamActor, CosyVoice, Pexels)
          duration: 视频/音频时长(秒)
          resolution: 分辨率 (480P/720P)
          chars: CosyVoice 字符数
          status: success/failed
          note: 备注
        """
        # 计算费用
        if service == "CosyVoice":
            unit_price = PRICING.get("CosyVoice_per_char", 0.002)
            cost = round(chars * unit_price, 4)
        elif service == "Pexels":
            cost = 0.0
        else:
            key = f"{service}_{resolution}"
            unit_price = PRICING.get(key, 0.5)
            cost = round(duration * unit_price, 4) if status == "success" else 0.0

        record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "service": service,
            "duration_s": duration,
            "resolution": resolution,
            "chars": chars,
            "status": status,
            "cost_yuan": cost,
            "note": note,
        }
        self._session_log.append(record)

        # 追加到日志文件
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # 实时输出
        if cost > 0:
            print(f"  💰 {service}: {duration:.1f}s × ¥{unit_price}/s = ¥{cost:.2f}")
        elif status == "failed":
            print(f"  💰 {service}: 失败, 不计费")
        else:
            print(f"  💰 {service}: 免费")

        return cost

    def summary(self) -> dict:
        """输出本次会话的费用汇总"""
        total = sum(r["cost_yuan"] for r in self._session_log)
        success_calls = sum(1 for r in self._session_log if r["status"] == "success")
        failed_calls = sum(1 for r in self._session_log if r["status"] == "failed")

        print("\n" + "=" * 40)
        print("💰 本次会话费用汇总")
        print("=" * 40)
        print(f"  成功调用: {success_calls} 次")
        print(f"  失败调用: {failed_calls} 次")
        print(f"  总费用:   ¥{total:.2f}")
        print(f"  账户余额:  未知 (请登录火山引擎控制台查看)")
        print("=" * 40)

        # 分服务统计
        by_service = {}
        for r in self._session_log:
            s = r["service"]
            if s not in by_service:
                by_service[s] = {"count": 0, "total_s": 0, "cost": 0.0}
            by_service[s]["count"] += 1
            by_service[s]["total_s"] += r["duration_s"] if r["status"] == "success" else 0
            by_service[s]["cost"] += r["cost_yuan"]

        if by_service:
            print("\n  按服务:")
            for s, info in sorted(by_service.items()):
                print(f"    {s:15s} {info['count']}次, {info['total_s']:.1f}s, ¥{info['cost']:.2f}")

        return {"total": total, "calls": success_calls + failed_calls}

    def get_session_log(self) -> list[dict]:
        return self._session_log


# ── 全局单例 (在 main.py 中使用) ────────────────────────────
_tracker: CostTracker | None = None


def get_tracker() -> CostTracker:
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
    return _tracker


def print_history(days: int = 7):
    """打印最近 N 天的费用历史"""
    if not LOG_FILE.exists():
        print("暂无费用记录")
        return

    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)
    total = 0.0
    count = 0
    with open(LOG_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                t = datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S")
                if t >= cutoff:
                    total += r["cost_yuan"]
                    count += 1
                    print(f"  [{r['time']}] {r['service']:15s} {r['duration_s']:5.1f}s ¥{r['cost_yuan']:.2f} {r['note']}")
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

    print(f"\n  近 {days} 天: {count} 次调用, 总费用 ¥{total:.2f}")

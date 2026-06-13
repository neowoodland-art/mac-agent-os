"""
ops/_base.py — 平台操作基类 v1.0

定义:
  - OpResult: 单个操作的结构化结果（供 RunLog 持久化）
  - PlatformOps: 所有平台操作类的抽象基类
  - ops_for(): 根据账号信息获取对应的 PlatformOps 实例

每平台一个子类（DouyinOps, XhsOps），实现此接口后即可被 engine.py 统一调用。
"""
import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class OpResult:
    """单个操作的结构化结果 — engine.py 和 RunLog 的共同数据格式"""
    op: str                         # 操作名 (如 "like", "goto_home")
    step_id: int = 0                # 蓝图步骤编号
    success: bool = True
    detail: str = ""                # 简短描述 (如 "👍", "profile_loaded", "no_btn")
    elapsed: float = 0.0            # 耗时(秒)
    error: str = ""                 # 失败原因

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self):
        icon = "✅" if self.success else "❌"
        extra = f" | {self.error}" if self.error else ""
        return f"{icon} [{self.step_id:2d}] {self.op:18s} → {self.detail[:25]} ({self.elapsed:.1f}s){extra}"


class PlatformOps(ABC):
    """平台操作基类 — 智能体通过 mc CLI 调用，不直接操作此类

    子类需要实现:
      - supported_ops() → list[str]
      - _execute(op, args) → OpResult  (内部实现单个操作)
    
    调用方用 execute() 获得统一入口，失败自动重试。
    """

    name: str = "base"              # 平台标识 (douyin / xiaohongshu)
    retry_count: int = 1            # 默认重试次数

    # ── 公开接口 ──────────────────────────────────────────────

    def supported_ops(self) -> list[str]:
        """返回支持的操作名列表，子类必须覆盖"""
        raise NotImplementedError

    async def execute(self, op: str, args: dict = None,
                      step_id: int = 0) -> OpResult:
        """执行单个操作，自动重试（统一入口，engine.py 调用此方法）

        Args:
            op: 操作名
            args: 操作参数
            step_id: 蓝图步骤编号

        Returns:
            OpResult — 始终返回，不抛异常
        """
        args = args or {}
        last_err = ""

        for attempt in range(self.retry_count + 1):
            t0 = time.time()
            try:
                result = await self._do_execute(op, args, step_id)
                if result is None:
                    result = OpResult(op, step_id, True, "ok", time.time() - t0)
                result.elapsed = round(time.time() - t0, 2)
                return result
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
                if attempt < self.retry_count:
                    await asyncio.sleep(1)

        elapsed = time.time() - t0
        return OpResult(op, step_id, False, "retry_exhausted", round(elapsed, 2), last_err)

    # ── 子类覆盖 ──────────────────────────────────────────────

    @abstractmethod
    async def _do_execute(self, op: str, args: dict, step_id: int) -> Optional[OpResult]:
        """子类实现具体的操作分发。返回 OpResult 或 None（None=成功，无额外信息）"""
        ...

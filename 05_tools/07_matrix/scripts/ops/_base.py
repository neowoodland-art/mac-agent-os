"""
ops/_base.py — 平台操作基类 v2.0

三段式操作模型 v2.0:
  每个原子操作 = 前置条件检查 + 执行动作 + 后置验证

  1. _capture_state() → PageState    操作前/后页面状态指纹
  2. _get_pre_conditions(op)         每个操作的前置条件
  3. _do_execute(op, args) → OpResult 执行动作（子类实现，与原来一样）
  4. _get_post_conditions(op)        每个操作的后置验证条件
  5. execute() 统一入口 → 三段式执行，返回完整 OpResult

改造目标:
  - 录制时能记录操作前后的状态指纹
  - Analyzer 通过状态差异推断操作类型 → 不再依赖坐标
  - Exporter 输出三段式 JSON 蓝图
"""
import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional


# ════════════════════════════════════════════════════════════
# PageState — 页面状态指纹
# ════════════════════════════════════════════════════════════

@dataclass
class PageState:
    """页面状态指纹 — 操作前后快照（供录制/分析/验证使用）

    url_pattern:  归一化 URL 模式（去掉动态参数，保留路径结构）
    page_mode:    grid / player / player_full / player_modal / search / profile / unknown
    selectors:    {CSS选择器: 是否可见} — 关键元素的可见性状态
    markers:      {标记名: 值} — 自定义状态标记（如 liked=true, like_count=1024）
    text_snippet: 页面文本片段（用于差异分析）
    """
    url_pattern: str = ""
    page_mode: str = "unknown"
    selectors: dict = field(default_factory=dict)
    markers: dict = field(default_factory=dict)
    text_snippet: str = ""

    def delta(self, other: 'PageState') -> dict:
        """对比两个 PageState，返回差异摘要"""
        diffs = {}

        if self.page_mode != other.page_mode:
            diffs["page_mode"] = f"{self.page_mode} → {other.page_mode}"

        # 选择器状态变化
        sel_diffs = {}
        all_keys = set(self.selectors) | set(other.selectors)
        for k in all_keys:
            v1 = self.selectors.get(k)
            v2 = other.selectors.get(k)
            if v1 != v2:
                sel_diffs[k] = f"{v1} → {v2}"
        if sel_diffs:
            diffs["selectors"] = sel_diffs

        # 标记变化
        mark_diffs = {}
        all_markers = set(self.markers) | set(other.markers)
        for k in all_markers:
            v1 = self.markers.get(k)
            v2 = other.markers.get(k)
            if v1 != v2:
                mark_diffs[k] = f"{v1} → {v2}"
        if mark_diffs:
            diffs["markers"] = mark_diffs

        return diffs

    def to_dict(self) -> dict:
        return asdict(self)


# ════════════════════════════════════════════════════════════
# Condition — 前置/后置条件
# ════════════════════════════════════════════════════════════

@dataclass
class Condition:
    """执行条件（前置条件 / 后置验证）

    条件类型 type:
      'page_mode'   — 页面模式匹配（如 page_mode == 'player'）
      'selector'    — DOM 元素可见性（如 '[data-e2e="digg"]' 可见）
      'marker'      — 状态标记匹配（如 liked == False）
      'marker_diff' — 状态标记变化（如 like_count 增加了）
    """
    type: str = "page_mode"
    target: str = ""            # 目标字段
    expected: any = None        # 期望值
    actual: any = None          # 运行时填充的实际值
    passed: bool = False        # 是否通过
    message: str = ""           # 检查结果描述

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "target": self.target,
            "expected": self.expected,
            "actual": self.actual,
            "passed": self.passed,
            "message": self.message,
        }


# ════════════════════════════════════════════════════════════
# OpResult — 操作结果（v2.0 加入三段式字段）
# ════════════════════════════════════════════════════════════

@dataclass
class OpResult:
    """单个操作的结构化结果（v2.0 新增 before/after 状态和条件检查）

    原有字段不变，新增:
      before_state:    操作前页面状态指纹
      after_state:     操作后页面状态指纹
      pre_conditions:  前置条件检查结果列表
      post_conditions: 后置验证检查结果列表
    """
    op: str                         # 操作名 (如 "like", "goto_home")
    step_id: int = 0                # 蓝图步骤编号
    success: bool = True
    detail: str = ""                # 简短描述 (如 "👍", "profile_loaded", "no_btn")
    elapsed: float = 0.0            # 耗时(秒)
    error: str = ""                 # 失败原因

    # v2.0 新增字段
    before_state: Optional[PageState] = None
    after_state: Optional[PageState] = None
    pre_conditions: Optional[list] = None
    post_conditions: Optional[list] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        # 将 Optional 字段中的 None 去掉，保持 JSON 简洁
        if self.pre_conditions is None:
            d.pop("pre_conditions", None)
        if self.post_conditions is None:
            d.pop("post_conditions", None)
        if self.before_state is None:
            d.pop("before_state", None)
        if self.after_state is None:
            d.pop("after_state", None)
        return d

    def __str__(self):
        icon = "✅" if self.success else "❌"
        extra = f" | {self.error}" if self.error else ""
        # 如果有条件检查结果，追加概要
        if self.pre_conditions:
            failed = [c for c in self.pre_conditions if not c.passed]
            if failed:
                extra += f" | pre_fail: {len(failed)}"
        if self.post_conditions:
            failed = [c for c in self.post_conditions if not c.passed]
            if failed:
                extra += f" | post_fail: {len(failed)}"
        return f"{icon} [{self.step_id:2d}] {self.op:18s} → {self.detail[:25]} ({self.elapsed:.1f}s){extra}"


# ════════════════════════════════════════════════════════════
# PlatformOps — 平台操作基类（v2.0 三段式）
# ════════════════════════════════════════════════════════════

class PlatformOps(ABC):
    """平台操作基类（v2.0 三段式）

    子类需要实现:
      - supported_ops() → list[str]
      - _do_execute(op, args, step_id) → OpResult  (原有，实现动作)
      - _get_pre_conditions(op) → list[Condition]  (新增，前置条件)
      - _get_post_conditions(op) → list[Condition] (新增，后置验证)

    基类提供:
      - execute() → 三段式统一入口（子类不需要覆盖）
      - _capture_state() → 页面状态指纹采集（子类可重写加强）
      - _check_conditions() → 条件检查引擎
    """

    name: str = "base"              # 平台标识 (douyin / xiaohongshu)
    retry_count: int = 1            # 默认重试次数

    # 关键选择器（子类可覆盖，用于状态采集）
    STATE_SELECTORS: list = []
    """状态采集时检查的关键元素选择器列表"""

    # ── 公开接口 ──────────────────────────────────────────────

    def supported_ops(self) -> list[str]:
        raise NotImplementedError

    async def execute(self, op: str, args: dict = None,
                      step_id: int = 0) -> OpResult:
        """三段式执行入口（v2.0）

        流程:
          1. 采集操作前状态（before_state）
          2. 检查前置条件（pre_conditions）
          3. 执行动作（_do_execute）
          4. 采集操作后状态（after_state）
          5. 检查后置条件（post_conditions）
          6. 返回完整 OpResult
        """
        args = args or {}
        last_err = ""
        t0_start = time.time()

        # 1. 采集操作前状态
        before = await self._capture_state()

        # 2. 检查前置条件
        pre_conds = self._get_pre_conditions(op)
        pre_results = await self._check_conditions(pre_conds, before)
        pre_all_pass = all(c.passed for c in pre_results)
        pre_detail = f"pre:{sum(1 for c in pre_results if c.passed)}/{len(pre_results)}"

        # 前置条件不满足 → 跳过（不是失败）
        if not pre_all_pass:
            elapsed = round(time.time() - t0_start, 2)
            result = OpResult(op, step_id, True, f"skipped({pre_detail})",
                              elapsed, before_state=before,
                              pre_conditions=pre_results)
            return result

        for attempt in range(self.retry_count + 1):
            t0 = time.time()
            try:
                # 3. 执行动作
                result = await self._do_execute(op, args, step_id)
                if result is None:
                    result = OpResult(op, step_id, True, "ok", time.time() - t0)
                result.elapsed = round(time.time() - t0, 2)

                # 4. 采集操作后状态
                result.after_state = await self._capture_state()

                # 5. 检查后置条件
                post_conds = self._get_post_conditions(op)
                result.post_conditions = await self._check_conditions(
                    post_conds, result.after_state, before)
                post_all_pass = all(c.passed for c in result.post_conditions)
                post_detail = f"post:{sum(1 for c in result.post_conditions if c.passed)}/{len(result.post_conditions)}"

                # 补充前置条件和 before_state
                result.pre_conditions = pre_results
                result.before_state = before

                # 后置条件不满足且还有重试次数 → 重试
                if not post_all_pass and attempt < self.retry_count:
                    result.success = False
                    result.detail = f"retry({post_detail})"
                    result.error = f"post_condition_failed: {post_detail}"
                    await asyncio.sleep(1)
                    continue

                # 最终判定：后置条件通过或已用完重试
                result.success = post_all_pass or (attempt >= self.retry_count and result.success)
                result.detail = post_detail if post_all_pass else result.detail
                return result

            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
                if attempt < self.retry_count:
                    await asyncio.sleep(1)

        elapsed = round(time.time() - t0_start, 2)
        return OpResult(op, step_id, False, "retry_exhausted", elapsed, last_err,
                        before_state=before, pre_conditions=pre_results)

    # ── 状态采集（基类实现，子类可加强）──

    async def _capture_state(self) -> PageState:
        """采集当前页面状态指纹

        子类可以重写此方法以加入平台特定的状态标记。
        基类实现采集:
          - URL 模式
          - 页面模式（通过 _detect_page_state）
          - 关键选择器的可见性
          - 页面文本片段
        """
        state = PageState()
        try:
            page = getattr(self, 'page', None)
            if page is None:
                return state

            # URL 模式
            url = page.url
            state.url_pattern = self._normalize_url(url)

            # 页面模式（子类通常有 _detect_page_state 方法）
            detect = getattr(self, '_detect_page_state', None)
            if detect:
                state.page_mode = await detect()
            elif hasattr(self, '_detect_page_mode'):
                state.page_mode = await self._detect_page_mode()

            # 关键选择器可见性
            for sel in self.STATE_SELECTORS:
                try:
                    el = page.locator(sel)
                    state.selectors[sel] = await el.count() > 0 and await el.first.is_visible()
                except Exception:
                    state.selectors[sel] = False

            # 页面文本片段
            try:
                text = await page.evaluate("(document.body.innerText || '').trim().slice(0, 2000)")
                state.text_snippet = text
            except Exception:
                pass

        except Exception:
            pass

        return state

    def _normalize_url(self, url: str) -> str:
        """归一化 URL，去掉动态参数，保留路径结构"""
        import re
        # 去掉查询参数
        url = re.sub(r'\?.*$', '', url)
        # 去掉 /video/ 后面的 ID
        url = re.sub(r'/video/[A-Za-z0-9]+', '/video/{id}', url)
        # 去掉 /user/ 后面的 ID
        url = re.sub(r'/user/[A-Za-z0-9]+', '/user/{id}', url)
        return url

    # ── 条件检查引擎 ──────────────────────────────────────────

    def _get_pre_conditions(self, op: str) -> list[Condition]:
        """每个操作的前置条件——子类覆盖返回

        默认返回空列表（不检查前置条件，兼容旧版）
        """
        return []

    def _get_post_conditions(self, op: str) -> list[Condition]:
        """每个操作的后置验证条件——子类覆盖返回

        默认返回空列表（不检查后置条件，兼容旧版）
        """
        return []

    async def _check_conditions(self, conditions: list[Condition],
                                state: PageState,
                                before_state: PageState = None) -> list[Condition]:
        """检查一组条件，填充 actual/passed/message 字段"""
        for cond in conditions:
            try:
                if cond.type == 'page_mode':
                    cond.actual = state.page_mode
                    cond.passed = (state.page_mode == cond.expected)
                    cond.message = f"page_mode={state.page_mode}" if cond.passed \
                        else f"期望={cond.expected}, 实际={state.page_mode}"

                elif cond.type == 'selector':
                    visible = state.selectors.get(cond.target, False)
                    cond.actual = visible
                    cond.passed = (visible == cond.expected)
                    cond.message = f"{cond.target} visible={visible}" if cond.passed \
                        else f"期望可见={cond.expected}, 实际={visible}"

                elif cond.type == 'marker':
                    val = state.markers.get(cond.target)
                    cond.actual = val
                    cond.passed = (val == cond.expected)
                    cond.message = f"{cond.target}={val}" if cond.passed \
                        else f"期望={cond.expected}, 实际={val}"

                elif cond.type == 'marker_diff' and before_state:
                    before_val = before_state.markers.get(cond.target)
                    after_val = state.markers.get(cond.target)
                    cond.actual = (before_val, after_val)
                    # marker_diff: expected 可以是 "increased"/"decreased"/"changed"
                    if cond.expected == "increased":
                        cond.passed = (isinstance(before_val, (int, float))
                                       and isinstance(after_val, (int, float))
                                       and after_val > before_val)
                    elif cond.expected == "decreased":
                        cond.passed = (isinstance(before_val, (int, float))
                                       and isinstance(after_val, (int, float))
                                       and after_val < before_val)
                    else:
                        cond.passed = (before_val != after_val)
                    cond.message = f"{cond.target}: {before_val} → {after_val}"

                else:
                    cond.passed = True
                    cond.message = f"unknown_condition({cond.type})"

            except Exception as e:
                cond.passed = False
                cond.message = f"检查异常: {e}"

        return conditions

    # ── 子类实现 ──────────────────────────────────────────────

    @abstractmethod
    async def _do_execute(self, op: str, args: dict, step_id: int) -> Optional[OpResult]:
        """子类实现具体的操作分发。返回 OpResult 或 None（None=成功，无额外信息）

        注意：execute() 方法在 _do_execute 之前/之后自动采集状态，
              所以 _do_execute 只需要做「动作」部分，不需要管条件检查。
        """
        ...

"""
流程控制器 (Pipeline Controller) — 漫剧视频工厂 v2.0

功能:
  - 状态机管理生产全生命周期
  - 五道审核关卡 (Gate 0/1/1.5/2/3)
      Gate 0: 角色定妆照/九宫格审核
      Gate 1: 脚本方向/风格/节奏审核
      Gate 1.5: 分镜提示词审核（角色适配后，视觉生成前）
      Gate 2: 分镜视觉审核
      Gate 3: 费用确认
  - BGM 选择集成
  - 定妆照/Character Sheet 生成集成
  - 状态持久化（断点续传）
  - CLI + API 双接口

状态流转:

  1. 角色阶段
  draft -> character_creating -> gate0_wait -> approve -> gate0_pass
                                               reject -> gate0_rej -> resubmit -> character_creating

  2. 脚本阶段
  gate0_pass -> [script] -> submit_gate1 -> gate1_wait -> approve -> gate1_pass
                                                         reject -> gate1_rej -> resubmit -> gate1_wait

  3. 分镜提示词阶段
  gate1_pass -> [storyboard prompts] -> submit_gate_1_5 -> gate1_5_wait -> approve -> gate1_5_pass
                                                                          reject -> gate1_5_rej -> resubmit -> gate1_5_wait

  4. 视觉+费用阶段
  gate1_5_pass -> submit_gate2 -> gate2_wait -> approve -> gate2_pass
                                               reject -> gate2_rej -> resubmit -> gate2_wait
  gate2_pass -> [BGM选择] -> submit_gate3 -> gate3_wait -> confirm -> gate3_confirmed -> generating -> composing -> completed
                                                         cancel -> gate3_cancelled -> resubmit -> gate2_wait

  任何状态可 -> cancelled

用法:
  from pipeline_controller import PipelineController
  pc = PipelineController()

  # 角色阶段
  prod = pc.create("文字灵感", "灵感内容", "标题", "八零后", "manhua")
  pc.start_character_creation(prod.id)
  pc.character_created(prod.id, {"portrait": "path/to/portrait.png"})
  pc.approve_gate(prod.id, gate=0)

  # 脚本阶段
  pc.set_script(prod.id, script)
  pc.submit_gate(prod.id, gate=1)
  pc.approve_gate(prod.id, gate=1)

  # 分镜提示词阶段
  pc.set_visual_storyboard(prod.id, storyboard_prompts)
  pc.submit_gate_1_5(prod.id)
  pc.approve_gate(prod.id, gate=1.5)

  # 视觉+费用
  pc.submit_gate(prod.id, gate=2)
  pc.approve_gate(prod.id, gate=2)
  pc.set_bgm(prod.id, bgm_id="枪火")
  pc.submit_gate(prod.id, gate=3)
  pc.confirm_cost(prod.id)
  pc.start_generation(prod.id)
"""

import os
import json
import time
import copy
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


# ═══════════════════════════════════════════════════════════
# 状态定义
# ═══════════════════════════════════════════════════════════

class ProductionState(str, Enum):
    DRAFT               = "draft"                # 草稿 — 初始状态
    CHARACTER_CREATING  = "character_creating"   # 角色定妆照生成中
    GATE0_WAITING       = "gate0_waiting"        # 等待角色审核 (Gate 0)
    GATE0_PASSED        = "gate0_passed"         # 角色审核通过
    GATE0_REJECTED      = "gate0_rejected"       # 角色审核打回
    GATE1_WAITING       = "gate1_waiting"        # 等待脚本审核 (Gate 1)
    GATE1_PASSED        = "gate1_passed"         # 脚本审核通过
    GATE1_REJECTED      = "gate1_rejected"       # 脚本审核打回
    GATE1_5_WAITING     = "gate1_5_waiting"      # 等待分镜提示词审核 (Gate 1.5)
    GATE1_5_PASSED      = "gate1_5_passed"       # 分镜提示词审核通过
    GATE1_5_REJECTED    = "gate1_5_rejected"     # 分镜提示词审核打回
    GATE2_WAITING       = "gate2_waiting"        # 等待分镜审核 (Gate 2)
    GATE2_PASSED        = "gate2_passed"         # 分镜审核通过
    GATE2_REJECTED      = "gate2_rejected"       # 分镜审核打回
    GATE3_WAITING       = "gate3_waiting"        # 等待费用确认 (Gate 3)
    GATE3_CONFIRMED     = "gate3_confirmed"      # 费用已确认
    GATE3_CANCELLED     = "gate3_cancelled"      # 费用取消（回 Gate 2）
    GENERATING          = "generating"           # 视觉生成中
    COMPOSING           = "composing"            # AVE 合成中
    COMPLETED           = "completed"            # 已完成
    CANCELLED           = "cancelled"            # 已取消

    @property
    def is_terminal(self) -> bool:
        return self in (ProductionState.COMPLETED, ProductionState.CANCELLED)

    @property
    def is_waiting_for_user(self) -> bool:
        return self in (
            ProductionState.GATE0_WAITING,
            ProductionState.GATE1_WAITING,
            ProductionState.GATE1_5_WAITING,
            ProductionState.GATE2_WAITING,
            ProductionState.GATE3_WAITING,
            ProductionState.GATE0_REJECTED,
            ProductionState.GATE1_REJECTED,
            ProductionState.GATE1_5_REJECTED,
            ProductionState.GATE2_REJECTED,
            ProductionState.GATE3_CANCELLED,
        )


# ═══════════════════════════════════════════════════════════
# 状态转换规则
# ═══════════════════════════════════════════════════════════

STATE_TRANSITIONS = {
    ProductionState.DRAFT: {
        "start_character_creation": ProductionState.CHARACTER_CREATING,
    },
    ProductionState.CHARACTER_CREATING: {
        "character_created": ProductionState.GATE0_WAITING,
        "fail": ProductionState.DRAFT,
    },
    ProductionState.GATE0_WAITING: {
        "approve": ProductionState.GATE0_PASSED,
        "reject": ProductionState.GATE0_REJECTED,
    },
    ProductionState.GATE0_PASSED: {
        "submit_gate1": ProductionState.GATE1_WAITING,
    },
    ProductionState.GATE0_REJECTED: {
        "resubmit": ProductionState.CHARACTER_CREATING,
        "cancel": ProductionState.CANCELLED,
    },
    ProductionState.GATE1_WAITING: {
        "approve": ProductionState.GATE1_PASSED,
        "reject": ProductionState.GATE1_REJECTED,
    },
    ProductionState.GATE1_PASSED: {
        "submit_gate_1_5": ProductionState.GATE1_5_WAITING,
    },
    ProductionState.GATE1_REJECTED: {
        "resubmit": ProductionState.GATE1_WAITING,
        "cancel": ProductionState.CANCELLED,
    },
    ProductionState.GATE1_5_WAITING: {
        "approve": ProductionState.GATE1_5_PASSED,
        "reject": ProductionState.GATE1_5_REJECTED,
    },
    ProductionState.GATE1_5_PASSED: {
        "submit_gate2": ProductionState.GATE2_WAITING,
    },
    ProductionState.GATE1_5_REJECTED: {
        "resubmit": ProductionState.GATE1_5_WAITING,
        "cancel": ProductionState.CANCELLED,
    },
    ProductionState.GATE2_WAITING: {
        "approve": ProductionState.GATE2_PASSED,
        "reject": ProductionState.GATE2_REJECTED,
    },
    ProductionState.GATE2_PASSED: {
        "submit_gate3": ProductionState.GATE3_WAITING,
    },
    ProductionState.GATE2_REJECTED: {
        "resubmit": ProductionState.GATE2_WAITING,
        "cancel": ProductionState.CANCELLED,
    },
    ProductionState.GATE3_WAITING: {
        "confirm": ProductionState.GATE3_CONFIRMED,
        "cancel_payment": ProductionState.GATE3_CANCELLED,
    },
    ProductionState.GATE3_CONFIRMED: {
        "start_generation": ProductionState.GENERATING,
    },
    ProductionState.GATE3_CANCELLED: {
        "resubmit": ProductionState.GATE2_WAITING,
        "cancel": ProductionState.CANCELLED,
    },
    ProductionState.GENERATING: {
        "complete_generation": ProductionState.COMPOSING,
        "fail": ProductionState.DRAFT,
    },
    ProductionState.COMPOSING: {
        "complete": ProductionState.COMPLETED,
        "fail": ProductionState.DRAFT,
    },
    # 任意状态可取消
}


# ═══════════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════════

@dataclass
class CostBreakdown:
    """费用明细"""
    path_type: str = "manhua"                              # manhua / realistic
    image_count: int = 0                                   # 图片/视频数量
    image_cost: float = 0.0                                # 图片生成费用
    video_cost: float = 0.0                                # 视频生成费用
    tts_cost: float = 0.5                                  # TTS 费用
    bgm_cost: float = 0.0                                  # BGM 费用
    total: float = 0.0                                     # 总计

    def calculate(self):
        if self.path_type == "manhua":
            self.image_cost = 0.3 * self.image_count
            self.video_cost = 0.0
        else:
            self.image_cost = 0.3 * self.image_count
            self.video_cost = 0.2 * 5 * self.image_count  # 每个片段5s
        self.total = self.image_cost + self.video_cost + self.tts_cost + self.bgm_cost
        return self

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Production:
    """生产任务"""
    id: str
    title: str = "未命名"
    state: ProductionState = ProductionState.DRAFT
    character: str = "小漫"
    character_description: str = ""          # 角色描述（用于生成定妆照/九宫格）
    character_sheet: dict = field(default_factory=dict)  # 角色定妆照参数图片路径
    visual_style: str = "manhua"             # manhua / realistic / mixed
    source_type: str = ""                    # 文字灵感 / 参考视频 / 外部剧本
    source_data: Any = ""                    # 原始输入
    bgm_id: str = ""                         # 选中的 BGM ID
    bgm_config: dict = field(default_factory=dict)
    cost: CostBreakdown = field(default_factory=CostBreakdown)
    script: dict = field(default_factory=dict)
    adapted_storyboard: list = field(default_factory=list)     # 角色适配后的分镜（含角色文本块）
    visual_storyboard: list = field(default_factory=list)      # Gate 1.5 分镜提示词（含角色块+场景+镜头）
    gate0_feedback: str = ""                 # Gate 0 打回理由
    gate1_feedback: str = ""                 # Gate 1 打回理由
    gate1_5_feedback: str = ""               # Gate 1.5 打回理由
    gate2_feedback: str = ""                 # Gate 2 打回理由
    created_at: str = ""
    updated_at: str = ""
    completed_at: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value
        d["cost"] = self.cost.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Production":
        cost_data = data.pop("cost", {})
        state = ProductionState(data.pop("state", "draft"))
        prod = cls(state=state, **data)
        prod.cost = CostBreakdown(**cost_data)
        return prod


# ═══════════════════════════════════════════════════════════
# 流程控制器
# ═══════════════════════════════════════════════════════════

class PipelineController:
    """流程控制器 — 管理生产任务生命周期"""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self._data_dir = Path(data_dir)
        else:
            self._data_dir = Path(os.environ.get(
                "AVE_DATA_DIR",
                str(Path.home() / "workbuddy-agent-os/agent-local/tools/ave/data/productions")
            ))
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._productions: dict[str, Production] = {}
        self._counter = 0
        self._load_all()

    # ── 创建 ──

    def create(self, source_type: str, source_data: Any,
               title: str = "", character: str = "小漫",
               character_description: str = "",
               visual_style: str = "manhua") -> Production:
        """创建一个新的生产任务"""
        self._counter += 1
        prod_id = f"PROD-{time.strftime('%Y%m%d')}-{self._counter:04d}"
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        prod = Production(
            id=prod_id,
            title=title or f"生产任务 #{self._counter}",
            state=ProductionState.DRAFT,
            character=character,
            character_description=character_description,
            visual_style=visual_style,
            source_type=source_type,
            source_data=source_data,
            created_at=now,
            updated_at=now,
        )
        self._productions[prod_id] = prod
        self._save(prod)
        return prod

    # ── 角色阶段 (Gate 0) ──

    def start_character_creation(self, prod_id: str) -> Production:
        """开始生成角色定妆照/九宫格"""
        prod = self._get(prod_id)
        self._transition(prod, "start_character_creation")
        prod.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save(prod)
        return prod

    def character_created(self, prod_id: str, character_sheet: dict) -> Production:
        """
        角色定妆照/九宫格已生成

        参数:
          prod_id: 生产任务 ID
          character_sheet: {
              "portrait": "path/to/portrait.png",    # 定妆照
              "grid": "path/to/grid.png",             # 九宫格
              "expressions": {"happy": "...", ...}    # 表情参考图
          }
        """
        prod = self._get(prod_id)
        prod.character_sheet = character_sheet
        self._transition(prod, "character_created")
        prod.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save(prod)
        return prod

    # ── Gate 操作 ──

    def submit_gate(self, prod_id: str, gate: int) -> dict:
        """
        提交审核到指定 Gate

        参数:
          prod_id: 生产任务 ID
          gate: 0 (角色审核) | 1 (脚本审核) | 2 (分镜审核) | 3 (费用确认)

        返回:
          当前生产状态和信息
        """
        prod = self._get(prod_id)
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        if gate == 0:
            # Gate 0 不需要 submit，而是由 character_created 自动进入 gate0_wait
            raise ValueError("Gate 0 无需手动 submit，完成角色定妆照后自动进入等待审核")
        elif gate == 1:
            self._transition(prod, "submit_gate1")
        elif gate == 2:
            # 进入 Gate 2 前自动生成视觉 storyboard（如果还没有）
            if not prod.visual_storyboard and prod.adapted_storyboard:
                prod.visual_storyboard = prod.adapted_storyboard
            self._transition(prod, "submit_gate2")
        elif gate == 3:
            cost = self._calculate_cost(prod)
            prod.cost = cost
            self._transition(prod, "submit_gate3")
        else:
            raise ValueError(f"无效 Gate: {gate}")

        prod.updated_at = now
        self._save(prod)
        return self._gate_response(prod, gate)

    def submit_gate_1_5(self, prod_id: str) -> dict:
        """提交 Gate 1.5 — 分镜提示词审核"""
        prod = self._get(prod_id)
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        # 如果还没有 visual_storyboard，从 adapted_storyboard 生成
        if not prod.visual_storyboard and prod.adapted_storyboard:
            prod.visual_storyboard = prod.adapted_storyboard

        self._transition(prod, "submit_gate_1_5")
        prod.updated_at = now
        self._save(prod)
        return self._gate_response(prod, 1.5)

    def approve_gate(self, prod_id: str, gate: int, notes: str = "") -> Production:
        """通过指定 Gate 的审核"""
        prod = self._get(prod_id)
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        action_map = {0: "approve", 1: "approve", 2: "approve", 3: "confirm"}
        action = action_map.get(gate)
        if action is None:
            # 处理 gate=1.5
            if gate in (1.5, "1.5"):
                action = "approve"
            else:
                raise ValueError(f"无效 Gate: {gate}")

        try:
            self._transition(prod, action)
        except ValueError as e:
            raise ValueError(f"Gate {gate} 审核不通过: {e}")

        prod.updated_at = now
        self._save(prod)
        return prod

    def reject_gate(self, prod_id: str, gate: int, feedback: str = "") -> Production:
        """打回指定 Gate 的审核"""
        prod = self._get(prod_id)
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        if gate == 0:
            self._transition(prod, "reject")
            prod.gate0_feedback = feedback
        elif gate == 1:
            self._transition(prod, "reject")
            prod.gate1_feedback = feedback
        elif gate in (1.5, "1.5"):
            self._transition(prod, "reject")
            prod.gate1_5_feedback = feedback
        elif gate == 2:
            self._transition(prod, "reject")
            prod.gate2_feedback = feedback
        elif gate == 3:
            self._transition(prod, "cancel_payment")
        else:
            raise ValueError(f"无效 Gate: {gate}")

        prod.updated_at = now
        self._save(prod)
        return prod

    def resubmit_gate(self, prod_id: str, gate: int) -> Production:
        """修改后重新提交审核"""
        prod = self._get(prod_id)
        self._transition(prod, "resubmit")
        prod.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save(prod)
        return prod

    # ── BGM 选择 ──

    def set_bgm(self, prod_id: str, bgm_id: str, bgm_config: Optional[dict] = None) -> Production:
        """设置生产任务的 BGM"""
        prod = self._get(prod_id)
        prod.bgm_id = bgm_id
        if bgm_config:
            prod.bgm_config = bgm_config
        prod.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save(prod)
        return prod

    # ── 生产执行 ──

    def confirm_cost(self, prod_id: str) -> Production:
        """确认费用（Gate 3 通过后的等效操作）"""
        prod = self._get(prod_id)
        self._transition(prod, "confirm")
        prod.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save(prod)
        return prod

    def start_generation(self, prod_id: str) -> Production:
        """开始视觉生成"""
        prod = self._get(prod_id)
        self._transition(prod, "start_generation")
        prod.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save(prod)
        return prod

    def complete_step(self, prod_id: str, step: str) -> Production:
        """完成某个生产步骤"""
        prod = self._get(prod_id)
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        if step == "generation":
            self._transition(prod, "complete_generation")
        elif step == "composition":
            self._transition(prod, "complete")
            prod.completed_at = now
        else:
            raise ValueError(f"未知步骤: {step}")

        prod.updated_at = now
        self._save(prod)
        return prod

    def fail_step(self, prod_id: str, step: str, error: str = "") -> Production:
        """生产步骤失败"""
        prod = self._get(prod_id)
        self._transition(prod, "fail")
        prod.error = error
        prod.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save(prod)
        return prod

    def cancel(self, prod_id: str) -> Production:
        """取消生产任务"""
        prod = self._get(prod_id)
        if prod.state.is_terminal:
            raise ValueError(f"任务 {prod_id} 已处于终态 {prod.state.value}")

        prod.state = ProductionState.CANCELLED
        prod.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save(prod)
        return prod

    # ── 脚本管理 ──

    def set_script(self, prod_id: str, script: dict) -> Production:
        """设置生产任务的脚本"""
        prod = self._get(prod_id)
        prod.script = script
        prod.title = script.get("meta", {}).get("title", prod.title)
        prod.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save(prod)
        return prod

    def set_adapted_storyboard(self, prod_id: str, storyboard: list) -> Production:
        """设置角色适配后的分镜列表"""
        prod = self._get(prod_id)
        prod.adapted_storyboard = storyboard
        prod.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save(prod)
        return prod

    def set_visual_storyboard(self, prod_id: str, storyboard: list) -> Production:
        """
        设置分镜提示词列表（Gate 1.5 审核内容）

        每个分镜包含完整的视觉 prompt：
        {
            "id": 1,
            "scene": "...",
            "visual_prompt": "角色块 + 场景描述 + 镜头指令...",
            "character_ref": "...",
            "reference_image": "path/to/ref.png",
            "emotion": "...",
            "duration_sec": 5,
        }
        """
        prod = self._get(prod_id)
        prod.visual_storyboard = storyboard
        prod.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save(prod)
        return prod

    # ── 查询 ──

    def get(self, prod_id: str) -> Optional[Production]:
        """获取生产任务"""
        return self._productions.get(prod_id)

    def list_all(self, state: Optional[str] = None) -> list[Production]:
        """列出所有生产任务，可按状态筛选"""
        prods = list(self._productions.values())
        if state:
            prods = [p for p in prods if p.state.value == state]
        return sorted(prods, key=lambda p: p.created_at, reverse=True)

    def list_active(self) -> list[Production]:
        """列出所有活跃（未完成/未取消）的任务"""
        return [p for p in self._productions.values()
                if not p.state.is_terminal]

    def list_waiting_for_review(self) -> list[Production]:
        """列出所有等待你审核的任务"""
        return [p for p in self._productions.values()
                if p.state.is_waiting_for_user]

    # ── 费用计算 ──

    def _calculate_cost(self, prod: Production) -> CostBreakdown:
        """计算生产费用"""
        segments = prod.adapted_storyboard or prod.script.get("segments", [])
        count = len(segments) or 10  # 默认为10格

        cost = CostBreakdown(
            path_type=prod.visual_style,
            image_count=count,
            tts_cost=0.5,
        )

        if prod.visual_style == "realistic":
            cost.video_cost = 0.2 * 5 * count
            cost.image_cost = 0.3 * count
        else:
            cost.image_cost = 0.3 * count

        cost.total = cost.image_cost + cost.video_cost + cost.tts_cost + cost.bgm_cost
        return cost

    def get_cost_breakdown(self, prod_id: str) -> dict:
        """获取费用明细"""
        prod = self._get(prod_id)
        cost = self._calculate_cost(prod)
        return cost.to_dict()

    # ── 内部方法 ──

    def _get(self, prod_id: str) -> Production:
        if prod_id not in self._productions:
            raise KeyError(f"未找到生产任务: {prod_id}")
        return self._productions[prod_id]

    def _transition(self, prod: Production, action: str):
        """执行状态转换"""
        transitions = STATE_TRANSITIONS.get(prod.state, {})
        if action not in transitions:
            raise ValueError(
                f"状态 {prod.state.value} 不允许操作 '{action}'。"
                f"允许的操作: {list(transitions.keys())}"
            )
        prod.state = transitions[action]

    def _gate_response(self, prod: Production, gate: int) -> dict:
        """生成审核展示信息"""
        result = {
            "production_id": prod.id,
            "state": prod.state.value,
            "gate": gate,
            "title": prod.title,
            "character": prod.character,
        }

        if gate == 0:
            result["character"] = prod.character
            result["character_description"] = prod.character_description
            result["character_sheet"] = prod.character_sheet
            result["prompt"] = (
                f"请审核角色「{prod.character}」的定妆照。\n"
                f"描述: {prod.character_description}\n"
                f"✅ 通过 → 进入脚本创作阶段\n"
                f"✏️ 修改 → 说明需要调整的内容\n"
                f"❌ 重做 → 修改角色描述后重新生成"
            )

        elif gate == 1:
            from script_schemas import generate_gate1_summary
            if prod.script:
                result["summary"] = generate_gate1_summary(prod.script)
            result["prompt"] = (
                f"请审核脚本《{prod.title}》的方向、风格和节奏。\n"
                f"✅ 通过 → 进入角色适配和分镜拆解\n"
                f"✏️ 修改 → 说明修改意见\n"
                f"❌ 重写 → 回到灵感阶段"
            )

        elif gate == 1.5:
            prompts = []
            for seg in prod.visual_storyboard:
                prompts.append({
                    "id": seg.get("id", 0),
                    "scene": seg.get("scene", ""),
                    "visual_prompt": seg.get("visual_prompt", seg.get("character_block", "")),
                    "reference_image": seg.get("reference_image", ""),
                    "emotion": seg.get("emotion", "中性"),
                    "duration_sec": seg.get("duration_sec", 5),
                })
            result["visual_prompts"] = prompts
            result["prompt"] = (
                f"请审核《{prod.title}》每个分镜的视觉提示词。\n"
                f"逐分镜检查角色块+场景+镜头是否准确，角色一致性是否保证。\n"
                f"✅ 全部通过 → 进入视觉生成\n"
                f"✏️ 修改某分镜 → 说明需调整的分镜及修改方向"
            )

        elif gate == 2:
            from script_schemas import generate_gate2_table
            if prod.adapted_storyboard:
                result["storyboard"] = prod.adapted_storyboard
            elif prod.script:
                result["storyboard"] = generate_gate2_table(prod.script)
            result["prompt"] = (
                f"请审核《{prod.title}》的每个分镜。\n"
                f"逐分镜检查场景/情绪/视觉风格是否合适。\n"
                f"✅ 全部通过 → 进入 BGM 选择\n"
                f"✏️ 修改某分镜 → 说明需调整的分镜"
            )

        elif gate == 3:
            result["cost"] = prod.cost.to_dict()
            result["bgm"] = prod.bgm_id
            result["prompt"] = (
                f"费用明细已生成，请确认是否执行。\n"
                f"✅ 确认 → 开始视觉生成（将消耗费用）\n"
                f"✏️ 切换路径（漫剧↔真人）→ 重新计算\n"
                f"❌ 取消 → 回到分镜审核"
            )

        return result

    def _save(self, prod: Production):
        """持久化生产任务到文件"""
        path = self._data_dir / f"{prod.id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(prod.to_dict(), f, indent=2, ensure_ascii=False)

    def _load_all(self):
        """从磁盘加载所有生产任务"""
        for f in sorted(self._data_dir.glob("PROD-*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                prod = Production.from_dict(data)
                self._productions[prod.id] = prod
                # 更新计数器
                parts = prod.id.split("-")
                if len(parts) == 3:
                    try:
                        n = int(parts[2])
                        self._counter = max(self._counter, n)
                    except ValueError:
                        pass
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"  ⚠️ 加载 {f.name} 失败: {e}")

    def __repr__(self) -> str:
        active = len(self.list_active())
        waiting = len(self.list_waiting_for_review())
        return f"<PipelineController: {len(self._productions)} tasks, {active} active, {waiting} waiting>"


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="漫剧视频工厂流程控制器 v2.0")
    parser.add_argument("action", nargs="?", default="list",
                        choices=["list", "create", "submit", "approve", "reject",
                                 "resubmit", "start_char", "char_done",
                                 "status", "cost", "bgm", "cancel"])
    parser.add_argument("--id", default="", help="生产任务ID")
    parser.add_argument("--gate", type=float, default=1, help="Gate编号 (0/1/1.5/2/3)")
    parser.add_argument("--title", default="", help="任务标题")
    parser.add_argument("--style", default="manhua", help="视觉风格")
    parser.add_argument("--character", default="小漫", help="角色名")
    parser.add_argument("--char-desc", default="", help="角色描述（用于定妆照生成）")
    parser.add_argument("--bgm", default="", help="BGM ID")
    parser.add_argument("--feedback", default="", help="审核反馈")
    parser.add_argument("--source-type", default="文字灵感", help="输入类型")
    parser.add_argument("--source", default="", help="输入内容")

    args = parser.parse_args()
    pc = PipelineController()

    if args.action == "list":
        prods = pc.list_all()
        print(f"Production task list ({len(prods)} total):")
        for prod in prods:
            state_dot = "W" if prod.state.is_waiting_for_user else " "
            print(f"  [{state_dot}] {prod.id:22s} | {prod.title:20s} | {prod.state.value:25s} | {prod.character}")
        waiting = pc.list_waiting_for_review()
        if waiting:
            print(f"\n  >>> {len(waiting)} task(s) waiting for your review:")

    elif args.action == "create":
        prod = pc.create(args.source_type, args.source, args.title,
                         args.character, args.char_desc, args.style)
        print(f"Created: {prod.id}")
        print(f"  Title:   {prod.title}")
        print(f"  Char:    {prod.character}")
        print(f"  Style:   {prod.visual_style}")
        print(f"  State:   {prod.state.value}")
        print(f"  Input:   {args.source_type}")
        print(f"  ---")
        print(f"  Next: run the following to generate character sheet:")
        print(f"    pc.start_character_creation('{prod.id}')")

    elif args.action == "start_char":
        if not args.id:
            print("Please specify --id")
            return
        prod = pc.start_character_creation(args.id)
        print(f"Character creation started: {prod.id} -> {prod.state.value}")

    elif args.action == "char_done":
        if not args.id:
            print("Please specify --id")
            return
        # Simulate: character sheet paths
        sheet = {
            "portrait": f"cache/character_sheet/{args.id}/portrait.png",
            "grid": f"cache/character_sheet/{args.id}/grid_2x3.png",
            "expressions": {},
        }
        prod = pc.character_created(args.id, sheet)
        print(f"Character sheet done: {prod.id} -> {prod.state.value}")
        print(f"  Portrait: {sheet['portrait']}")
        print(f"  Grid:     {sheet['grid']}")

    elif args.action == "submit":
        if not args.id:
            print("Please specify --id")
            return
        if args.gate == 1.5:
            result = pc.submit_gate_1_5(args.id)
        else:
            result = pc.submit_gate(args.id, int(args.gate))
        print(f"Submitted Gate {args.gate}:")
        print(f"  Task:  {result['production_id']}")
        print(f"  State: {result['state']}")
        print(f"\n{result.get('prompt', '')}")

    elif args.action == "approve":
        if not args.id:
            print("Please specify --id")
            return
        prod = pc.approve_gate(args.id, args.gate, args.feedback)
        print(f"Gate {args.gate} approved:")
        print(f"  Task:  {prod.id}")
        print(f"  State: {prod.state.value}")

    elif args.action == "reject":
        if not args.id:
            print("Please specify --id")
            return
        prod = pc.reject_gate(args.id, args.gate, args.feedback)
        print(f"Gate {args.gate} rejected:")
        print(f"  Task:  {prod.id}")
        print(f"  State: {prod.state.value}")
        fb_map = {0: prod.gate0_feedback, 1: prod.gate1_feedback,
                  1.5: prod.gate1_5_feedback, 2: prod.gate2_feedback}
        fb = fb_map.get(args.gate, "")
        if fb:
            print(f"  Feedback: {fb}")

    elif args.action == "resubmit":
        if not args.id:
            print("Please specify --id")
            return
        prod = pc.resubmit_gate(args.id, args.gate)
        print(f"Resubmitted Gate {args.gate}:")
        print(f"  Task:  {prod.id}")
        print(f"  State: {prod.state.value}")

    elif args.action == "status":
        prod = pc.get(args.id)
        if not prod:
            print(f"Task not found: {args.id}")
            return
        print(f"Task detail: {prod.id}")
        print(f"  Title:   {prod.title}")
        print(f"  State:   {prod.state.value}")
        print(f"  Char:    {prod.character}")
        print(f"  Style:   {prod.visual_style}")
        print(f"  Created: {prod.created_at}")
        print(f"  Updated: {prod.updated_at}")
        if prod.character_sheet:
            print(f"  Char Sheet: {prod.character_sheet}")
        if prod.completed_at:
            print(f"  Done:    {prod.completed_at}")
        if prod.error:
            print(f"  Error:   {prod.error}")
        seg_count = len(prod.script.get("segments", []))
        if seg_count:
            print(f"  Segments: {seg_count}")

    elif args.action == "cost":
        if not args.id:
            print("Please specify --id")
            return
        cost = pc.get_cost_breakdown(args.id)
        print(f"Cost breakdown: {args.id}")
        print(f"  Path:    {cost['path_type']}")
        print(f"  Images:  {cost['image_count']} x ¥{cost['image_cost']/max(cost['image_count'],1):.2f}")
        print(f"  Img fee: ¥{cost['image_cost']:.2f}")
        print(f"  Vid fee: ¥{cost['video_cost']:.2f}")
        print(f"  TTS fee: ¥{cost['tts_cost']:.2f}")
        print(f"  BGM fee: ¥{cost['bgm_cost']:.2f}")
        print(f"  ---------------------")
        print(f"  Total:   ¥{cost['total']:.2f}")

    elif args.action == "bgm":
        if not args.id or not args.bgm:
            print("Please specify --id and --bgm")
            return
        prod = pc.set_bgm(args.id, args.bgm)
        print(f"BGM set: {args.bgm}")
        print(f"  Task: {prod.id}")

    elif args.action == "cancel":
        if not args.id:
            print("Please specify --id")
            return
        prod = pc.cancel(args.id)
        print(f"Cancelled: {prod.id}")


if __name__ == "__main__":
    cli()

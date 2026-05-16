"""
AVE story_director/temporal_bridge — 场景过渡桥接

职责:
  为相邻场景生成过渡描述，确保视觉连续性。
  对比场景间的环境/角色/镜头/光线变化，生成一致性约束。

桥接策略:
  1. 同角色 + 同环境 → 连续（不标记差异）
  2. 同角色 + 换环境 → 过渡（标记环境变化，生成中间帧指引）
  3. 换角色 → 章节切换（硬切，视觉锚点）
  4. 同环境 + 换光线 → 过渡（光线渐变指引）

用法:
  from story_director.temporal_bridge import build_bridges
  scenes = build_bridges(scenes)
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from typing import Optional

from lib.logger import get_logger

logger = get_logger("temporal_bridge")


# ═══════════════════════════════════════════════════════════
# 桥接类型
# ═══════════════════════════════════════════════════════════

class BridgeType:
    CONTINUOUS = "continuous"           # 连续: 无差异, 可 xfade 平滑过渡
    ENVIRONMENT_CHANGE = "environment"  # 环境变化: 走→跑, 室内→室外
    MOOD_CHANGE = "mood"               # 光线/氛围变化
    CHARACTER_SWITCH = "switch"        # 角色切换: 硬切或演职人员字幕
    CHAPTER_BREAK = "chapter"          # 章节断点: 标题卡过渡


# ═══════════════════════════════════════════════════════════
# 场景桥接信息
# ═══════════════════════════════════════════════════════════

class BridgeInfo:
    """两个场景之间的过渡信息"""
    def __init__(
        self,
        from_scene_id: int,
        to_scene_id: int,
        bridge_type: str,
        description: str,
        transition_hint: str = "",
        continuity_elements: list[str] = None,
        changed_elements: list[str] = None,
    ):
        self.from_scene_id = from_scene_id
        self.to_scene_id = to_scene_id
        self.bridge_type = bridge_type
        self.description = description
        self.transition_hint = transition_hint
        self.continuity_elements = continuity_elements or []
        self.changed_elements = changed_elements or []

    def to_dict(self) -> dict:
        return {
            "from_scene": self.from_scene_id,
            "to_scene": self.to_scene_id,
            "type": self.bridge_type,
            "description": self.description,
            "transition_hint": self.transition_hint,
            "continuity": self.continuity_elements,
            "changes": self.changed_elements,
        }


# ═══════════════════════════════════════════════════════════
# 桥接引擎
# ═══════════════════════════════════════════════════════════

def build_bridges(
    scenes: list,
    character_block: str = "",
) -> list:
    """
    为场景列表构建桥接信息

    参数:
      scenes: Scene 对象列表（必须含 to_dict() 方法）
      character_block: 角色描述块（用于 Prompt 注入）

    返回:
      带 bridge_* 属性的 scenes（原地修改）
      另外通过 scenes_bridges() 可获取 BridgeInfo 列表
    """
    bridges = []

    for i in range(len(scenes) - 1):
        cur = scenes[i]
        nxt = scenes[i + 1]

        # 转为 dict（兼容 Scene 对象和普通 dict）
        cur_d = cur.to_dict() if hasattr(cur, "to_dict") else cur
        nxt_d = nxt.to_dict() if hasattr(nxt, "to_dict") else nxt

        bridge = _compare_scenes(cur_d, nxt_d, character_block)
        bridges.append(bridge)

        # 把桥接信息挂到两个场景上
        cur.bridge_to_next = bridge.to_dict() if hasattr(cur, "bridge_to_next") else None
        if hasattr(cur, "__dict__"):
            cur.__dict__["bridge_to_next"] = bridge.to_dict()
        if hasattr(nxt, "__dict__"):
            nxt.__dict__["bridge_from_prev"] = bridge.to_dict()

    logger.info(f"桥接完成: {len(bridges)} 个过渡")
    for b in bridges:
        logger.info(f"  [{b.from_scene_id}→{b.to_scene_id}] {b.bridge_type}: {b.description[:50]}")

    return scenes


def _compare_scenes(
    cur: dict,
    nxt: dict,
    character_block: str = "",
) -> BridgeInfo:
    """对比两个场景，生成桥接信息"""
    from_id = cur.get("scene_id", 0)
    to_id = nxt.get("scene_id", 0)
    continuity = []
    changes = []

    # ── 对比角色 ──
    cur_char = cur.get("character_ref", "") or ""
    nxt_char = nxt.get("character_ref", "") or ""

    char_changed = cur_char != nxt_char
    if char_changed:
        changes.append(f"character: {cur_char} → {nxt_char}")
    else:
        if cur_char:
            continuity.append(f"same character: {cur_char}")

    # ── 对比环境 ──
    cur_env = cur.get("environment", "")
    nxt_env = nxt.get("environment", "")
    env_changed = cur_env != nxt_env
    if env_changed:
        changes.append(f"environment: {cur_env} → {nxt_env}")
    else:
        if cur_env:
            continuity.append(f"same environment: {cur_env}")

    # ── 对比光线 ──
    cur_mood = cur.get("mood_lighting", "")
    nxt_mood = nxt.get("mood_lighting", "")
    mood_changed = cur_mood != nxt_mood
    if mood_changed:
        changes.append(f"lighting: mood shift")
    else:
        if cur_mood:
            continuity.append(f"consistent lighting")

    # ── 对比镜头运动 ──
    cur_cam = cur.get("camera_motion", "")
    nxt_cam = nxt.get("camera_motion", "")
    if cur_cam == nxt_cam:
        continuity.append(f"same camera: {cur_cam[:30]}")
    else:
        changes.append(f"camera: {cur_cam[:20]} → {nxt_cam[:20]}")

    # ── 判断桥接类型 ──
    if char_changed:
        bridge_type = BridgeType.CHARACTER_SWITCH
    elif env_changed:
        bridge_type = BridgeType.ENVIRONMENT_CHANGE
    elif mood_changed:
        bridge_type = BridgeType.MOOD_CHANGE
    else:
        bridge_type = BridgeType.CONTINUOUS

    # ── 生成描述 ──
    description = _build_bridge_description(cur, nxt, bridge_type, continuity, changes)
    transition_hint = _build_transition_hint(bridge_type, changes)

    return BridgeInfo(
        from_scene_id=from_id,
        to_scene_id=to_id,
        bridge_type=bridge_type,
        description=description,
        transition_hint=transition_hint,
        continuity_elements=continuity,
        changed_elements=changes,
    )


def _build_bridge_description(
    cur: dict,
    nxt: dict,
    bridge_type: str,
    continuity: list[str],
    changes: list[str],
) -> str:
    """生成自然语言过渡描述"""
    parts = []

    if bridge_type == BridgeType.CONTINUOUS:
        parts.append("Seamless continuous scene. The character and environment remain the same.")
        if continuity:
            parts.append(" ".join(continuity))
        parts.append("The camera smoothly transitions to the next angle.")

    elif bridge_type == BridgeType.ENVIRONMENT_CHANGE:
        cur_env = cur.get("environment", "current setting")
        nxt_env = nxt.get("environment", "next setting")
        parts.append(
            f"The character moves from {cur_env} to {nxt_env}. "
            "Show a transitional moment — the character walking through a door, "
            "a scene wipe, or a match cut that bridges the two locations."
        )

    elif bridge_type == BridgeType.MOOD_CHANGE:
        cur_mood = cur.get("mood_lighting", "current mood")
        nxt_mood = nxt.get("mood_lighting", "next mood")
        parts.append(
            f"The atmosphere shifts: from '{cur_mood[:40]}' "
            f"to '{nxt_mood[:40]}'. "
            "The lighting should crossfade naturally, with the same character "
            "remaining the focal point."
        )

    elif bridge_type == BridgeType.CHARACTER_SWITCH:
        cur_char = cur.get("character_ref", "first character")
        nxt_char = nxt.get("character_ref", "next character")
        parts.append(
            f"Scene transition: from {cur_char} to {nxt_char}. "
            "This is a narrative chapter break. Use a clear visual cut — "
            "a fade to black, title card, or a wide establishing shot "
            "that signals the new scene."
        )

    return " ".join(parts)


def _build_transition_hint(bridge_type: str, changes: list[str]) -> str:
    """生成 FFmpeg 过渡提示"""
    hints = {
        BridgeType.CONTINUOUS: "xfade=transition=fade:duration=0.5",
        BridgeType.ENVIRONMENT_CHANGE: "xfade=transition=fadeblack:duration=1.0",
        BridgeType.MOOD_CHANGE: "xfade=transition=fadewhite:duration=0.8",
        BridgeType.CHARACTER_SWITCH: "xfade=transition=fadeblack:duration=1.5",
        BridgeType.CHAPTER_BREAK: "xfade=transition=fadeblack:duration=2.0",
    }
    return hints.get(bridge_type, "xfade=transition=fade:duration=0.5")


# ═══════════════════════════════════════════════════════════
# 集成: 在场景导出时附加桥接信息
# ═══════════════════════════════════════════════════════════

def enrich_scenes_with_bridges(
    scenes: list,
    character_block: str = "",
) -> list[dict]:
    """
    构建桥接并导出为丰富场景列表（含 bridge 信息）

    返回: dict 列表（含 bridge_to_next 字段）
    """
    scenes = build_bridges(scenes, character_block=character_block)
    result = []
    for i, s in enumerate(scenes):
        d = s.to_dict() if hasattr(s, "to_dict") else s
        # 附加桥接信息
        bridge = getattr(s, "bridge_to_next", None) if hasattr(s, "bridge_to_next") else None
        if bridge:
            d["bridge_to_next"] = bridge
        result.append(d)
    return result


def cli(args: list[str] | None = None):
    import argparse
    parser = argparse.ArgumentParser(description="场景过渡桥接")
    parser.add_argument("--scenes", required=True, help="场景 JSON 路径（scene_planner 输出）")
    parser.add_argument("--output", default="/tmp/ave_bridged_scenes.json", help="输出 JSON 路径")
    parser.add_argument("--verbose", action="store_true", help="打印详细桥接信息")

    parsed = parser.parse_args(args)

    with open(parsed.scenes, encoding="utf-8") as f:
        scenes_data = json.load(f)

    # 包装为简易 Scene 对象
    class SimpleScene:
        def __init__(self, d):
            self.__dict__.update(d)
            self.scene_id = d.get("scene_id", 0)
        def to_dict(self):
            return self.__dict__

    scenes = [SimpleScene(s) for s in scenes_data]

    enriched = enrich_scenes_with_bridges(scenes)

    with open(parsed.output, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 桥接完成: {len(enriched)} 个场景")
    print(f"   输出: {parsed.output}")

    if parsed.verbose:
        for e in enriched:
            bridge = e.get("bridge_to_next", {})
            if bridge:
                print(f"\n--- {bridge.get('from_scene')} → {bridge.get('to_scene')} "
                      f"[{bridge.get('type')}] ---")
                print(f"   描述: {bridge.get('description', '')[:80]}...")
                print(f"   提示: {bridge.get('transition_hint', '')}")


if __name__ == "__main__":
    cli()

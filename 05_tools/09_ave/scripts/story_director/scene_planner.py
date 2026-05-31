"""
AVE story_director/scene_planner — 场景分解模块

职责:
  1. 读取导演脚本 YAML → 按语义/镜头/BGM/角色分组为场景
  2. 为每场景构建 Kling 文生视频 Prompt（含角色描述块注入）
  3. 输出结构化场景列表（供 batch_generator 消费）

场景分组规则:
  - 同一角色 + 同一 BGM section → 合并为一个场景
  - 角色切换 或 BGM section 切换 → 新场景
  - 每场景时长 = 合并段的总时长

用法:
  from story_director.scene_planner import plan_scenes
  scenes = plan_scenes("director_script.yaml", character_name="小明")
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import hashlib
from pathlib import Path
from typing import Optional

from lib.logger import get_logger

logger = get_logger("scene_planner")

# ── Kling Prompt 模板 ────────────────────────────────────

SCENE_PROMPT_TEMPLATE = (
    "{character_block}"
    "The scene takes place in {environment}. "
    "The character is {action}. "
    "Camera: {camera_motion}. "
    "Lighting and atmosphere: {mood_lighting}. "
    "Cinematic quality, photorealistic style, soft natural lighting, 4K resolution."
)

SCENE_PROMPT_TEMPLATE_ZH = (
    "{character_block}"
    "场景发生在{environment}。"
    "角色正在{action}。"
    "镜头: {camera_motion}。"
    "光线与氛围: {mood_lighting}。"
    "电影级画质，照片级真实感，柔和自然光线，4K分辨率。"
)


# ═══════════════════════════════════════════════════════════
# 场景结构定义
# ═══════════════════════════════════════════════════════════

class Scene:
    """单场景数据结构"""
    def __init__(
        self,
        scene_id: int,
        text: str,
        duration_sec: float,
        character_ref: Optional[str],
        environment: str,
        action: str,
        camera_motion: str,
        mood_lighting: str,
        bgm_section: str = "main",
        segment_ids: list[int] = None,
        transition_to_next: str = "fade",
    ):
        self.scene_id = scene_id
        self.text = text
        self.duration_sec = duration_sec
        self.character_ref = character_ref
        self.environment = environment
        self.action = action
        self.camera_motion = camera_motion
        self.mood_lighting = mood_lighting
        self.bgm_section = bgm_section
        self.segment_ids = segment_ids or []
        self.transition_to_next = transition_to_next

    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "text": self.text,
            "duration_sec": self.duration_sec,
            "character_ref": self.character_ref,
            "environment": self.environment,
            "action": self.action,
            "camera_motion": self.camera_motion,
            "mood_lighting": self.mood_lighting,
            "bgm_section": self.bgm_section,
            "segment_ids": self.segment_ids,
            "transition_to_next": self.transition_to_next,
        }

    def build_prompt(
        self,
        character_block: str = "",
        lang: str = "en",
    ) -> str:
        """
        构建 Kling 文生视频 Prompt

        参数:
          character_block: 角色描述块（跨场景一致性的特征锚点）
          lang: en/zh

        返回: 完整 Prompt 字符串
        """
        template = SCENE_PROMPT_TEMPLATE if lang == "en" else SCENE_PROMPT_TEMPLATE_ZH

        env = self.environment or "an undefined space"
        act = self.action or "standing"
        cam = self.camera_motion or "static"
        mood = self.mood_lighting or "neutral lighting"

        return template.format(
            character_block=character_block,
            environment=env,
            action=act,
            camera_motion=cam,
            mood_lighting=mood,
        )


# ═══════════════════════════════════════════════════════════
# 场景分解引擎
# ═══════════════════════════════════════════════════════════

def plan_scenes(
    script_path: str,
    character_name: Optional[str] = None,
    character_block: str = "",
    lang: str = "en",
    merge_same_section: bool = True,
) -> list[Scene]:
    """
    导演脚本 → 场景列表

    参数:
      script_path: 导演脚本 YAML 路径
      character_name: 角色名（可选，只保留此角色的场景）
      character_block: 角色描述块（从定妆照加载）
      lang: 生成 Prompt 的语言
      merge_same_section: 是否合并相邻同BGM section的段

    返回:
      Scene 列表（每 scene 含 build_prompt() 方法）
    """
    import yaml

    with open(script_path, encoding="utf-8") as f:
        script_data = yaml.safe_load(f)

    segments = script_data.get("segments", [])
    meta = script_data.get("meta", {})
    character_refs = {cr.get("name", ""): cr for cr in meta.get("character_refs", [])}

    if not segments:
        raise ValueError(f"脚本中无 segments: {script_path}")

    logger.info(f"脚本加载: {len(segments)} 段, {len(character_refs)} 个角色引用")

    # ── Step 1: 原始段 → 初步场景分组 ──
    raw_scenes = []
    current_group = None

    for seg in segments:
        seg_id = seg.get("id", 0)
        seg_char = seg.get("character_ref") or ""
        seg_bgm = seg.get("bgm_section", "main")
        seg_camera = seg.get("camera", "static")
        seg_text = seg.get("text", "")

        # 如果 segment 没有 character_ref, 但 script 的 meta 有 character_refs
        # 且传入了 character_name, 则使用 character_name
        effective_char = seg_char or character_name or ""

        # 检查是否应该新建场景
        should_new = (
            current_group is None
            or (effective_char and effective_char != current_group["character_ref"])
            or (merge_same_section and seg_bgm != current_group["bgm_section"])
        )

        if should_new:
            # 新场景
            current_group = {
                "id": len(raw_scenes) + 1,
                "texts": [seg_text],
                "duration_sec": seg.get("duration_sec", 10),
                "character_ref": effective_char,
                "camera": seg_camera,
                "bgm_section": seg_bgm,
                "segment_ids": [seg_id],
                "material_search": seg.get("material", {}).get("search", ""),
                "voice_emotion": seg.get("voice_emotion", "正常讲述"),
            }
            raw_scenes.append(current_group)
        else:
            # 合并到当前场景
            current_group["texts"].append(seg_text)
            current_group["duration_sec"] += seg.get("duration_sec", 10)
            current_group["segment_ids"].append(seg_id)

    # ── Step 2: 场景信息增强（从文案提取环境/动作/光线） ──
    # 使用规则从 material search + text 推断
    scenes = []
    for raw in raw_scenes:
        scene_id = raw["id"]
        text_combined = "\n".join(raw["texts"])
        character_ref = raw["character_ref"]

        # 从 material search 推断环境
        search = raw.get("material_search", "")
        environment = _infer_environment(search, raw["texts"])

        # 从 voice_emotion + material 推断光线氛围
        emotion = raw.get("voice_emotion", "正常讲述")
        mood_lighting = _infer_mood_lighting(emotion)

        # 从 camera 推断镜头运动
        camera = raw.get("camera", "static")
        camera_motion = _translate_camera(camera)

        # 从 text 推断动作
        action = _infer_action(search, text_combined)

        # 过渡: 最后一个场景用 fade, 其他用 dissolve
        is_last = (scene_id == len(raw_scenes))
        transition = "fade" if is_last else "dissolve"

        scene = Scene(
            scene_id=scene_id,
            text=text_combined,
            duration_sec=raw["duration_sec"],
            character_ref=character_ref,
            environment=environment,
            action=action,
            camera_motion=camera_motion,
            mood_lighting=mood_lighting,
            bgm_section=raw["bgm_section"],
            segment_ids=raw["segment_ids"],
            transition_to_next=transition,
        )
        scenes.append(scene)

    logger.info(f"场景分解完成: {len(scenes)} 个场景")
    for s in scenes:
        logger.info(f"  Scene {s.scene_id}: {s.duration_sec:.0f}s "
                    f"char={s.character_ref or 'none'} "
                    f"bgm={s.bgm_section}")

    return scenes


# ═══════════════════════════════════════════════════════════
# 信息推断辅助函数
# ═══════════════════════════════════════════════════════════

def _infer_environment(search: str, texts: list[str]) -> str:
    """从搜索词和文案推断场景环境描述（英文）"""
    # 合并搜索词与文案片段
    combined = f"{search} {' '.join(texts)}".lower()

    env_map = [
        ("outdoor", r"\b(outdoor|outside|street|city|park|garden|beach|mountain|forest|sky|nature|landscape|garden|river|field|road)\b"),
        ("indoor", r"\b(indoor|inside|room|living|kitchen|office|studio|bedroom|library|hall|classroom|basement|garage)\b"),
        ("futuristic", r"\b(future|sci-fi|cyber|tech|robot|ai|digital|virtual|space|futuristic|neon|hologram)\b"),
        ("historical", r"\b(ancient|historical|medieval|traditional|vintage|retro|old|classic|temple|palace|castle)\b"),
        ("abstract", r"\b(abstract|conceptual|magical|fantasy|dream|imagination|surreal|ethereal)\b"),
    ]

    import re
    matches = []
    for env, pattern in env_map:
        if re.search(pattern, combined):
            matches.append(env)

    if matches:
        return matches[0]

    # 默认: 从文本判断, 如果含"介绍""讲述""聊聊"等 → 室内演播室
    if any(kw in combined for kw in ["介绍", "讲述", "聊聊", "hello", "welcome", "大家好", "你们好"]):
        return "a cozy indoor studio with soft background"

    return "a clean neutral environment"


def _infer_action(search: str, text: str) -> str:
    """从搜索词和文案推断角色动作"""
    combined = f"{search} {text}".lower()

    action_map = [
        ("walking slowly and looking around thoughtfully", r"\b(walk|散步|漫步|行走|walking)\b"),
        ("talking to the camera with natural hand gestures", r"\b(talk|speak|讲述|说话|介绍|讲解|speaking|talking|explain|介绍)\b"),
        ("sitting at a desk working on a laptop", r"\b(sit|work|办公|写|码|code|writing|typing|work|办公|study)\b"),
        ("gesturing expressively while presenting", r"\b(present|演讲|发布会|presentation|stage|讲解|演示)\b"),
        ("reading a book or document quietly", r"\b(read|阅读|看书|read|book|document)\b"),
        ("running or moving quickly", r"\b(run|跑步|奔跑|跑|rush|急行|运动|sport)\b"),
    ]

    import re
    for action, pattern in action_map:
        if re.search(pattern, combined):
            return action

    return "standing in a relaxed posture, facing the camera"


def _infer_mood_lighting(voice_emotion: str) -> str:
    """从语音情绪推断光线氛围"""
    emotion = voice_emotion.lower()

    if any(kw in emotion for kw in ["悬念", "紧张", "神秘", "严肃", "suspense", "tense", "serious"]):
        return "dramatic side lighting with deep shadows, high contrast"
    if any(kw in emotion for kw in ["欢快", "开心", "阳光", "积极", "happy", "cheerful", "bright"]):
        return "warm golden hour lighting, bright and airy"
    if any(kw in emotion for kw in ["悲伤", "难过", "忧郁", "深沉", "sad", "melancholy", "nostalgic"]):
        return "soft cool blue lighting with gentle fog, slightly desaturated"
    if any(kw in emotion for kw in ["激情", "爆发", "激动", "热烈", "passion", "exciting", "energetic"]):
        return "dynamic colorful lighting with volumetric beams"
    if any(kw in emotion for kw in ["专业", "沉稳", "自信", "严肃", "professional", "calm", "confident"]):
        return "clean soft studio lighting with gentle rim light"

    return "soft natural lighting with moderate contrast"


def _translate_camera(camera: str) -> str:
    """翻译 camera 字段为 Kling Prompt 镜头描述"""
    camera_map = {
        "static": "static camera, locked down shot",
        "slow_zoom_in": "very slow gentle zoom in",
        "slow_zoom_out": "very slow gentle zoom out",
        "pan_left": "slow horizontal pan from right to left",
        "pan_right": "slow horizontal pan from left to right",
        "tilt_up": "slow tilt up revealing the scene",
        "tilt_down": "slow tilt down establishing the environment",
        "dolly_in": "smooth dolly forward, pushing into the scene",
        "dolly_out": "smooth dolly backward, pulling out of the scene",
        "tracking": "smooth tracking shot following the subject",
        "handheld": "subtle handheld camera movement, documentary style",
        "aerial": "aerial drone shot, top-down perspective",
        "crane_up": "crane shot rising upward",
        "crane_down": "crane shot descending downward",
    }
    return camera_map.get(camera, f"gentle {camera.replace('_', ' ')}")


# ═══════════════════════════════════════════════════════════
# 导出场景为 JSON
# ═══════════════════════════════════════════════════════════

def export_scenes(
    scenes: list[Scene],
    output_path: str,
    character_block: str = "",
    lang: str = "en",
    seed: int = 42,
):
    """
    导出场景列表为 JSON（供 batch_generator 消费）

    参数:
      scenes: Scene 列表
      output_path: 输出 JSON 路径
      character_block: 角色描述块
      lang: en/zh
      seed: 固定 seed（角色一致性）
    """
    export = []
    for scene in scenes:
        prompt = scene.build_prompt(character_block=character_block, lang=lang)
        scene_seed = seed + scene.scene_id  # 每场景不同但固定
        export.append({
            "scene_id": scene.scene_id,
            "text": scene.text,
            "duration_sec": scene.duration_sec,
            "prompt": prompt,
            "character_ref": scene.character_ref,
            "camera_motion": scene.camera_motion,
            "mood_lighting": scene.mood_lighting,
            "bgm_section": scene.bgm_section,
            "transition": scene.transition_to_next,
            "seed": scene_seed,
            "segment_ids": scene.segment_ids,
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export, f, indent=2, ensure_ascii=False)

    logger.info(f"场景已导出: {output_path} ({len(export)} 个场景)")
    return output_path


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def cli(args: list[str] | None = None):
    import argparse
    parser = argparse.ArgumentParser(description="场景分解")
    parser.add_argument("--script", required=True, help="导演脚本 YAML 路径")
    parser.add_argument("--character", default="", help="角色名")
    parser.add_argument("--block", default="", help="角色描述块（可选，否则从角色库加载）")
    parser.add_argument("--lang", default="en", choices=["en", "zh"], help="Prompt 语言")
    parser.add_argument("--output", default="/tmp/ave_scenes.json", help="场景 JSON 输出路径")
    parser.add_argument("--seed", type=int, default=42, help="固定 seed")
    parser.add_argument("--show-prompts", action="store_true", help="同时打印所有 Prompt")

    parsed = parser.parse_args(args)

    character_block = parsed.block
    if not character_block and parsed.character:
        # 从角色库加载
        from character_sheet import load_character
        char = load_character(parsed.character)
        if char:
            character_block = char.get("description", "")
            logger.info(f"从角色库加载 '{parsed.character}': {character_block[:50]}...")

    scenes = plan_scenes(
        script_path=parsed.script,
        character_name=parsed.character or None,
        character_block=character_block,
        lang=parsed.lang,
    )

    export_scenes(scenes, parsed.output, character_block=character_block,
                  lang=parsed.lang, seed=parsed.seed)

    print(f"\n✅ 场景分解完成: {len(scenes)} 个场景")
    print(f"   输出: {parsed.output}")
    if parsed.show_prompts:
        print()
        for s in scenes:
            prompt = s.build_prompt(character_block=character_block, lang=parsed.lang)
            print(f"--- Scene {s.scene_id} ({s.duration_sec:.0f}s) ---")
            print(prompt)
            print()


if __name__ == "__main__":
    cli()

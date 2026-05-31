"""
角色适配器 (Character Adapter) — 漫剧视频工厂

功能:
  - 接收脚本 + 角色注册中心的角色信息
  - 遍历脚本的每个 segment，注入角色描述块
  - 生成适配后的分镜列表（含角色参考信息）
  - 输出可用于 Gate 2 展示的数据

用法:
  from character_adapter import CharacterAdapter
  from character_registry import CharacterRegistry

  registry = CharacterRegistry()
  adapter = CharacterAdapter(registry)
  adapted = adapter.adapt(script)
"""

import copy
import os
from typing import Optional


# ── 表情映射 ──

EMOTION_MAP = {
    "中性": "neutral",
    "微笑": "smile",
    "开心": "happy",
    "愤怒": "angry",
    "悲伤": "sad",
    "害怕": "fear",
    "惊讶": "surprise",
    "厌恶": "disgust",
    "平静": "neutral",
    "喜悦": "happy",
    "激动": "excited",
    "忧郁": "sad",
    "冷漠": "neutral",
}


def _map_emotion(chinese_emotion: str) -> str:
    """将中文情绪映射为表情键名"""
    return EMOTION_MAP.get(chinese_emotion, "neutral")


class CharacterAdapter:
    """角色适配器 — 将脚本中的主角替换为注册角色的描述"""

    def __init__(self, registry=None):
        """
        参数:
          registry: CharacterRegistry 实例，None 则延迟初始化
        """
        self._registry = registry

    @property
    def registry(self):
        if self._registry is None:
            from character_registry import CharacterRegistry
            self._registry = CharacterRegistry()
        return self._registry

    # ── 核心方法 ──

    def adapt(self, script: dict) -> dict:
        """
        将脚本中的每个分镜适配为注册角色版本

        参数:
          script: 标准格式脚本字典

        返回:
          适配后的脚本（含 character_block 字段）
        """
        char = self.registry.get_active_character()
        adapted = copy.deepcopy(script)

        meta = adapted.get("meta", {})
        meta["adapted_character"] = char.name
        meta["adapt_time"] = __import__("time").strftime("%Y-%m-%d %H:%M:%S")

        for seg in adapted.get("segments", []):
            self._adapt_segment(seg, char)

        return adapted

    def adapt_to_storyboard(self, script: dict) -> list[dict]:
        """
        将脚本转换为适配后的分镜列表（展平，无 meta）

        返回:
          每个分镜包含角色描述块信息，供 Gate 2 展示和视觉生成使用
        """
        char = self.registry.get_active_character()
        result = []

        for seg in script.get("segments", []):
            adapted_seg = copy.deepcopy(seg)
            self._adapt_segment(adapted_seg, char)
            result.append(adapted_seg)

        return result

    def _adapt_segment(self, seg: dict, char) -> dict:
        """
        适配单个分镜 — 注入角色描述块

        对每个分镜:
          1. 生成角色描述块 (character_block)
          2. 在 scene/description 中确保角色名正确
          3. 注入角色参考信息
        """
        # 生成角色描述块
        seg["character_block"] = char.build_prompt_block(
            style=seg.get("visual_style", "manhua"),
            expression=seg.get("emotion", "中性"),
            scene=seg.get("scene", ""),
            camera_angle=seg.get("camera", "中景"),
        )

        # 注入角色参考信息
        seg["character_ref"] = char.to_storyboard_block()

        # 注入参考图路径（用于 Kling character_refs）
        ref_images = char.reference_images
        if ref_images.get("portrait"):
            seg["reference_image"] = ref_images["portrait"]
        elif ref_images.get("grid"):
            seg["reference_image"] = ref_images["grid"]

        # 注入表情参考图（根据 segment 的情绪）
        emotion = seg.get("emotion", "中性")
        expressions = ref_images.get("expressions", {})
        emotion_key = _map_emotion(emotion)
        if emotion_key in expressions and expressions[emotion_key]:
            seg["emotion_reference"] = expressions[emotion_key]

        # 确保场景描述中出现角色名（如果还没出现）
        if char.name not in seg.get("description", ""):
            seg["description"] = f"{char.name}{seg.get('description', '')}"

        return seg

    # ── 批量适配 ──

    def adapt_batch(self, scripts: list[dict]) -> list[dict]:
        """批量适配多个脚本"""
        return [self.adapt(s) for s in scripts]

    # ── 预览 ──

    def preview_adaptation(self, script: dict) -> dict:
        """
        预览适配效果（不修改原始脚本）

        返回:
          {
            "character": "小漫",
            "segments_before": [...],  # 适配前的 scene 列表
            "segments_after": [...]     # 适配后的 scene+character_block
          }
        """
        char = self.registry.get_active_character()
        before = []
        after = []

        for seg in script.get("segments", []):
            before.append({
                "id": seg.get("id"),
                "scene": seg.get("scene"),
                "description": seg.get("description"),
            })

            adapted = copy.deepcopy(seg)
            self._adapt_segment(adapted, char)
            after.append({
                "id": adapted.get("id"),
                "scene": adapted.get("scene"),
                "description": adapted.get("description"),
                "character_block": adapted.get("character_block", ""),
            })

        return {
            "character": char.name,
            "total_segments": len(script.get("segments", [])),
            "before": before,
            "after": after,
        }


    # ── Kling character_refs 构建 ──

    def build_kling_character_refs(self, name: str = "") -> list[dict]:
        """
        构建 Kling API 支持的 character_refs 格式

        Kling 图生视频支持传入 character_refs 数组来保持角色一致性:
        [{"image_url": "path/to/portrait.png", "image_type": "人物全身照"}]

        返回:
          [{"image_url": "...", "image_type": "人物全身照"}, ...]
        """
        char = self.registry.get_character(name) if name else self.registry.get_active_character()
        ref_images = char.reference_images
        refs = []

        # 优先级: portrait > grid > cells
        portrait = ref_images.get("portrait", "")
        grid = ref_images.get("grid", "")

        # 如果 portrait 可用 → 直接使用
        if portrait:
            refs.append({
                "image_url": _ensure_file_url(portrait),
                "image_type": "人物全身照",
            })
            # 添加表情参考
            expressions = ref_images.get("expressions", {})
            for emotion, img_path in expressions.items():
                if img_path:
                    refs.append({
                        "image_url": _ensure_file_url(img_path),
                        "image_type": f"表情_{emotion}",
                    })
        elif grid:
            refs.append({
                "image_url": _ensure_file_url(grid),
                "image_type": "人物全身照",
            })

        return refs

    def inject_character_refs(self, segments: list[dict], char_name: str = "") -> list[dict]:
        """
        将 character_refs 注入到每个 segment 中

        参数:
          segments: 分镜列表
          char_name: 角色名（可选，默认当前活跃角色）

        返回:
          注入 character_refs 后的分镜列表
        """
        char = self.registry.get_character(char_name) if char_name else self.registry.get_active_character()
        refs = self.build_kling_character_refs(char_name or char.name)

        result = []
        for seg in segments:
            adapted = copy.deepcopy(seg)
            # 注入 character_refs（每个分镜独立一份，方便逐帧控制）
            adapted["character_refs"] = refs
            result.append(adapted)

        return result

    # ── Visual Storyboard 构建（Gate 1.5 用） ──

    def build_visual_prompts(self, storyboard: list[dict]) -> list[dict]:
        """
        从适配后的分镜生成视觉提示词（Gate 1.5 审核内容）

        每个分镜包含完整视觉 prompt:
        - character_block: 角色描述块
        - scene: 场景描述
        - visual_prompt: 完整视觉 prompt = 角色块 + 场景 + 镜头
        - reference_image: 参考图路径
        - emotion: 情绪
        - duration_sec: 时长

        返回:
          视觉提示词列表
        """
        char = self.registry.get_active_character()
        char_block = char.build_prompt_block(style="manhua")

        result = []
        for seg in storyboard:
            # 构建完整 visual prompt
            scene_desc = seg.get("scene", "")
            camera = seg.get("camera", "中景")
            emotion = seg.get("emotion", "中性")
            duration = seg.get("duration_sec", 5)

            visual_prompt = (
                f"{char_block}\n"
                f"[场景] {scene_desc}\n"
                f"[镜头] {camera}\n"
                f"[表情] {emotion}"
            )

            entry = {
                "id": seg.get("id", 0),
                "scene": scene_desc,
                "visual_prompt": visual_prompt,
                "reference_image": seg.get("reference_image",
                    char.reference_images.get("portrait", "")),
                "emotion": emotion,
                "duration_sec": duration,
            }

            # 如果有关键词/台词
            if seg.get("narration") or seg.get("dialogue"):
                entry["narration"] = seg.get("narration", "")
                entry["dialogue"] = seg.get("dialogue", "")

            result.append(entry)

        return result


# ── 工具函数 ──

def _ensure_file_url(path: str) -> str:
    """确保路径以 file:// 开头（Kling API 需要 URL）"""
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://") or path.startswith("file://"):
        return path
    return f"file://{os.path.abspath(path)}"


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="角色适配器")
    parser.add_argument("action", nargs="?", default="preview",
                        choices=["adapt", "preview", "batch", "refs", "visual-prompts"])
    parser.add_argument("--script", default="", help="脚本 YAML 文件路径")
    parser.add_argument("--character", default="", help="指定角色（可选）")
    parser.add_argument("--output", default="", help="输出路径")

    args = parser.parse_args()
    from character_registry import CharacterRegistry
    from script_schemas import load_script

    registry = CharacterRegistry()
    adapter = CharacterAdapter(registry)

    # 如果有指定角色，切换过去
    if args.character:
        registry.switch_to(args.character)

    print(f"角色适配器: 当前角色 = {registry.get_active_name()}")
    print()

    if args.action in ("adapt", "preview"):
        if not args.script:
            print("❌ 请指定 --script")
            return

        script = load_script(args.script)

        if args.action == "preview":
            preview = adapter.preview_adaptation(script)
            print(f"预览适配 ({preview['total_segments']} 个分镜):")
            print(f"角色: {preview['character']}")
            for b, a in zip(preview["before"], preview["after"]):
                print(f"\n  #{b['id']} {b['scene']}")
                print(f"  适配前: {b['description'][:50]}...")
                print(f"  适配后: {a['description'][:50]}...")
                print(f"  角色块: {a['character_block'][:80]}...")
        else:
            adapted = adapter.adapt(script)
            if args.output:
                import yaml
                with open(args.output, "w", encoding="utf-8") as f:
                    yaml.dump({"script": adapted}, f, allow_unicode=True,
                               default_flow_style=False, sort_keys=False)
                print(f"✅ 已保存适配后脚本: {args.output}")
            else:
                print(json.dumps(adapted, indent=2, ensure_ascii=False))


    elif args.action == "refs":
        refs = adapter.build_kling_character_refs(args.character)
        print(f"Kling character_refs for {args.character or registry.get_active_name()}:")
        print(json.dumps(refs, indent=2, ensure_ascii=False))

    elif args.action == "visual-prompts":
        if not args.script:
            print("❌ 请指定 --script")
            return
        script = load_script(args.script)
        storyboard = adapter.adapt_to_storyboard(script)
        prompts = adapter.build_visual_prompts(storyboard)
        print(f"Visual prompts (Gate 1.5):")
        print(json.dumps(prompts, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    import json
    cli()

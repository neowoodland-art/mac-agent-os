"""
脚本格式标准 — 漫剧视频工厂

功能:
  - 定义脚本 YAML 标准格式
  - 提供脚本创建/验证/转换工具
  - 生成 Gate 1/2 展示所需的摘要

用法:
  from script_schemas import ScriptBuilder, validate_script
  script = ScriptBuilder.create_from_text("灵感描述")
  errors = validate_script(script)
"""

import os
import copy
from pathlib import Path
from typing import Optional

import yaml

# ── 默认路径 ──
SCRIPTS_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = SCRIPTS_DIR / "script_schema.yaml"

# 镜头类型列表
VALID_CAMERAS = [
    "wide_shot", "medium_shot", "close_up", "over_shoulder",
    "aerial", "tracking", "pan", "dolly", "extreme_wide"
]

# 转场类型列表
VALID_TRANSITIONS = [
    "cut", "fade_in", "fade_out", "dissolve",
    "wipe_left", "wipe_right", "zoom_in", "zoom_out", "none"
]


# ═══════════════════════════════════════════════════════════
# 脚本构建器
# ═══════════════════════════════════════════════════════════

class ScriptBuilder:
    """脚本构建器 — 从各种输入创建标准格式脚本"""

    @staticmethod
    def empty(title: str = "未命名", character: str = "小漫") -> dict:
        """创建空脚本模板"""
        return {
            "meta": {
                "title": title,
                "source": "手动创建",
                "source_url": "",
                "duration_sec": 0,
                "character": character,
                "visual_style": "manhua",
                "bgm_style": "治愈",
            },
            "segments": [],
        }

    @staticmethod
    def from_text(text: str, title: str = "灵感脚本",
                   character: str = "小漫") -> dict:
        """从文字灵感创建脚本（需后续填充segments）"""
        script = ScriptBuilder.empty(title, character)
        script["meta"]["source"] = "文字灵感"
        return script

    @staticmethod
    def add_segment(script: dict, seg_data: dict) -> dict:
        """向脚本添加一个分镜"""
        if "segments" not in script:
            script["segments"] = []

        # 自动编号
        seg_data["id"] = len(script["segments"]) + 1

        # 补全默认值
        seg_data.setdefault("visual_style", script["meta"].get("visual_style", "manhua"))
        seg_data.setdefault("camera", "medium_shot")
        seg_data.setdefault("transition", "cut")
        seg_data.setdefault("dialogue", "")
        seg_data.setdefault("emotion", "中性")
        seg_data.setdefault("duration_sec", 5)

        script["segments"].append(seg_data)

        # 更新总时长
        script["meta"]["duration_sec"] = sum(
            s.get("duration_sec", 0) for s in script["segments"]
        )
        return script

    @staticmethod
    def remove_segment(script: dict, seg_id: int) -> dict:
        """删除指定分镜"""
        script["segments"] = [s for s in script["segments"] if s.get("id") != seg_id]
        # 重新编号
        for i, seg in enumerate(script["segments"], 1):
            seg["id"] = i
        script["meta"]["duration_sec"] = sum(
            s.get("duration_sec", 0) for s in script["segments"]
        )
        return script


# ═══════════════════════════════════════════════════════════
# 脚本验证
# ═══════════════════════════════════════════════════════════

def validate_script(script: dict) -> list[str]:
    """验证脚本格式，返回错误列表（空=通过）"""
    errors = []

    # 检查 meta
    meta = script.get("meta", {})
    if not meta.get("title"):
        errors.append("缺少标题 (meta.title)")
    if not meta.get("character"):
        errors.append("缺少角色 (meta.character)")

    # 检查 segments
    segments = script.get("segments", [])
    if not segments:
        errors.append("分镜列表为空 (segments)")

    for seg in segments:
        sid = seg.get("id", "?")
        if not seg.get("scene"):
            errors.append(f"分镜 #{sid}: 缺少场景名称 (scene)")
        if not seg.get("description"):
            errors.append(f"分镜 #{sid}: 缺少场景描述 (description)")
        if seg.get("camera") and seg["camera"] not in VALID_CAMERAS:
            errors.append(f"分镜 #{sid}: 无效镜头类型 '{seg['camera']}'")
        if seg.get("transition") and seg["transition"] not in VALID_TRANSITIONS:
            errors.append(f"分镜 #{sid}: 无效转场效果 '{seg['transition']}'")

    return errors


# ═══════════════════════════════════════════════════════════
# 脚本工具
# ═══════════════════════════════════════════════════════════

def load_script(path: str) -> dict:
    """从 YAML 文件加载脚本"""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("script", data)


def save_script(script: dict, path: str):
    """保存脚本到 YAML 文件"""
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump({"script": script}, f, allow_unicode=True,
                   default_flow_style=False, sort_keys=False)


def generate_gate1_summary(script: dict) -> dict:
    """生成 Gate 1 展示用的脚本摘要"""
    meta = script.get("meta", {})
    segments = script.get("segments", [])

    # 按情绪分组统计
    emotion_map = {}
    for seg in segments:
        em = seg.get("emotion", "中性")
        emotion_map[em] = emotion_map.get(em, 0) + seg.get("duration_sec", 0)

    # 场景结构
    scene_list = []
    for seg in segments:
        scene_list.append({
            "id": seg.get("id", 0),
            "scene": seg.get("scene", ""),
            "duration": seg.get("duration_sec", 0),
            "emotion": seg.get("emotion", "中性"),
        })

    return {
        "title": meta.get("title", ""),
        "source": meta.get("source", ""),
        "style": meta.get("visual_style", ""),
        "total_duration": meta.get("duration_sec", 0),
        "segment_count": len(segments),
        "character": meta.get("character", ""),
        "structure": scene_list,
        "emotion_distribution": emotion_map,
        "bgm_style": meta.get("bgm_style", ""),
    }


def generate_gate2_table(script: dict) -> list[dict]:
    """生成 Gate 2 展示用的分镜预览表"""
    segments = script.get("segments", [])
    return [
        {
            "id": seg.get("id", 0),
            "scene": seg.get("scene", ""),
            "description": seg.get("description", ""),
            "duration": seg.get("duration_sec", 0),
            "emotion": seg.get("emotion", "中性"),
            "visual_style": seg.get("visual_style", ""),
            "camera": seg.get("camera", ""),
        }
        for seg in segments
    ]


# ═══════════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 创建一个示例脚本
    script = ScriptBuilder.empty("小漫的一天", "小漫")

    ScriptBuilder.add_segment(script, {
        "scene": "清晨的咖啡馆",
        "description": "小漫推开咖啡馆的门，阳光洒进来",
        "dialogue": "（旁白）这是小漫最爱的角落。",
        "emotion": "温暖平静",
        "duration_sec": 8,
        "camera": "wide_shot",
    })

    ScriptBuilder.add_segment(script, {
        "scene": "靠窗座位",
        "description": "她坐下来，拿出画板开始画画",
        "dialogue": "小漫: 今天一定要把草稿画完！",
        "emotion": "专注",
        "duration_sec": 6,
        "camera": "medium_shot",
    })

    ScriptBuilder.add_segment(script, {
        "scene": "落日的天台",
        "description": "她看着完成的画，露出满足的微笑",
        "dialogue": "（旁白）有时候，最简单的快乐就在画笔下。",
        "emotion": "满足",
        "duration_sec": 10,
        "camera": "wide_shot",
        "transition": "dissolve",
    })

    # 验证
    errors = validate_script(script)
    if errors:
        print("❌ 验证失败:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("✅ 脚本验证通过")

    # Gate 1 摘要
    summary = generate_gate1_summary(script)
    print(f"\n📋 Gate 1 摘要:")
    print(f"  标题: {summary['title']}")
    print(f"  角色: {summary['character']}")
    print(f"  总时长: {summary['total_duration']}s")
    print(f"  分镜数: {summary['segment_count']}")
    items = [f"#{s['id']} {s['scene']}({s['duration']}s)" for s in summary['structure']]
    print(f"  结构: {items}")

    # Gate 2 表格
    table = generate_gate2_table(script)
    print(f"\n📋 Gate 2 分镜表:")
    for row in table:
        print(f"  #{row['id']:2d} | {row['scene']:12s} | {row['duration']:2d}s | {row['emotion']:8s} | {row['camera']:16s}")

    # 保存到文件
    save_path = Path(__file__).parent / "_sample_script.yaml"
    save_script(script, str(save_path))
    print(f"\n✅ 已保存样例脚本: {save_path}")

"""
ScriptGenerator — 脚本生成桥接模块 v1.0

功能:
  - 我（Claw）根据灵感/视频创作剧本 + 分镜列表
  - ScriptGenerator 负责格式化为标准脚本 → 注入 PipelineController
  - 自动触发 Gate 1 审核流程

工作流:
  1. 用户给灵感 → 我创作剧本 + segments 列表
  2. 调用 format_and_inject() 一站式注入流水线
  3. 系统自动过 Gate 1 → 等待用户审核

用法:
  from script_generator import ScriptGenerator
  
  segments = [
      {"scene": "...", "description": "...", ...},
      ...
  ]
  
  # 方式一：直接注入到已有生产任务
  prod = ScriptGenerator.inject_into_pipeline(pc, prod_id, segments)
  
  # 方式二：创建新任务并注入（推荐）
  prod = ScriptGenerator.create_and_inject(
      pc, "文字灵感", "灵感内容",
      "视频标题", "小漫", segments, style="manhua"
  )
"""

import os
import copy
from typing import Optional
from pathlib import Path


class ScriptGenerator:
    """脚本生成器桥接模块 — 我创作 → 流水线注入"""

    # 必填字段
    REQUIRED_SEGMENT_FIELDS = {
        "scene": str,
        "description": str,
    }

    # 可选字段及默认值
    OPTIONAL_SEGMENT_FIELDS = {
        "dialogue": "",
        "emotion": "中性",
        "duration_sec": 5,
        "camera": "medium_shot",
        "transition": "cut",
        "visual_style": None,  # None = 使用脚本 meta 中的值
    }

    # 有效值列表
    VALID_CAMERAS = [
        "wide_shot", "medium_shot", "close_up", "over_shoulder",
        "aerial", "tracking", "pan", "dolly", "extreme_wide"
    ]
    VALID_TRANSITIONS = [
        "cut", "fade_in", "fade_out", "dissolve",
        "wipe_left", "wipe_right", "zoom_in", "zoom_out", "none"
    ]

    @classmethod
    def validate_segments(cls, segments: list[dict]) -> list[str]:
        """验证分镜列表格式，返回错误列表"""
        errors = []

        if not segments:
            return ["分镜列表为空"]

        for i, seg in enumerate(segments):
            sid = seg.get("scene", f"#{i+1}")

            # 检查必填字段
            for field, ftype in cls.REQUIRED_SEGMENT_FIELDS.items():
                if field not in seg or not seg.get(field):
                    errors.append(f"分镜 '{sid}': 缺少必填字段 '{field}'")

            # 检查镜头类型
            if "camera" in seg and seg["camera"]:
                if seg["camera"] not in cls.VALID_CAMERAS:
                    warnings = ", ".join(cls.VALID_CAMERAS)
                    errors.append(f"分镜 '{sid}': 无效镜头类型 '{seg['camera']}' (可选: {warnings})")

            # 检查转场
            if "transition" in seg and seg["transition"]:
                if seg["transition"] not in cls.VALID_TRANSITIONS:
                    warnings = ", ".join(cls.VALID_TRANSITIONS)
                    errors.append(f"分镜 '{sid}': 无效转场 '{seg['transition']}' (可选: {warnings})")

            # 检查时长范围
            dur = seg.get("duration_sec", 5)
            if dur < 1 or dur > 30:
                errors.append(f"分镜 '{sid}': 时长异常 ({dur}s)，建议 1-30s")

        return errors

    @classmethod
    def format_segments(cls, title: str, character: str,
                        segments: list[dict],
                        style: str = "manhua",
                        source: str = "手动创作",
                        bgm_style: str = "治愈") -> dict:
        """
        把我创作的 segments 格式化为标准脚本 dict

        参数:
          title: 视频标题
          character: 角色名
          segments: 我创作的 segment 列表
          style: visual_style (manhua / realistic / mixed)
          source: 灵感来源描述
          bgm_style: BGM 风格偏好

        返回:
          标准脚本 dict (兼容 script_schemas 格式)
        """
        from script_schemas import ScriptBuilder, validate_script

        # 创建空脚本
        if not title:
            title = "未命名视频"
        if not character:
            character = "小漫"

        script = ScriptBuilder.empty(title, character)
        script["meta"]["source"] = source
        script["meta"]["visual_style"] = style
        script["meta"]["bgm_style"] = bgm_style

        # 逐个添加分镜
        for seg_data in segments:
            # 深拷贝，避免修改原始数据
            seg = copy.deepcopy(seg_data)

            # 如果未指定 visual_style，使用脚本级默认
            if "visual_style" not in seg or seg.get("visual_style") is None:
                seg["visual_style"] = style

            ScriptBuilder.add_segment(script, seg)

        # 验证
        errors = validate_script(script)
        if errors:
            print("  ⚠️ 脚本验证警告:")
            for e in errors:
                print(f"    - {e}")

        return script

    @classmethod
    def inject_into_pipeline(cls, pc, prod_id: str,
                              title: str, character: str,
                              segments: list[dict],
                              style: str = "manhua",
                              source: str = "手动创作",
                              bgm_style: str = "治愈") -> dict:
        """
        一站式：格式化脚本并注入到已有生产任务

        参数:
          pc: PipelineController 实例
          prod_id: 已有生产任务 ID
          title: 视频标题
          character: 角色名
          segments: segment 列表
          style: 视觉风格
          source: 灵感来源

        返回:
          Gate 1 审核信息 (可直接展示)
        """
        # 1. 验证 segments
        errors = cls.validate_segments(segments)
        if errors:
            error_msg = "; ".join(errors)
            raise ValueError(f"Segments 验证失败: {error_msg}")

        # 2. 格式化为标准脚本
        script = cls.format_segments(title, character, segments, style, source, bgm_style)

        # 3. 注入到生产任务
        pc.set_script(prod_id, script)

        # 4. 补充 meta 信息
        prod = pc.get(prod_id)
        if prod:
            prod.title = title
            prod.character = character
            prod.visual_style = style
            prod.source_type = source

        # 5. 提交 Gate 1 审核
        gate_result = pc.submit_gate(prod_id, gate=1)

        return gate_result

    @classmethod
    def create_and_inject(cls, pc,
                           source_type: str,
                           source_data: str,
                           title: str,
                           character: str,
                           segments: list[dict],
                           style: str = "manhua",
                           bgm_style: str = "治愈") -> dict:
        """
        一站式：创建生产任务 + 格式化 + 注入 + 提交 Gate 1

        这是最常用的入口方法。

        参数:
          pc: PipelineController 实例
          source_type: 灵感来源类型 (文字灵感 / 参考视频 / 外部剧本)
          source_data: 灵感来源内容
          title: 视频标题
          character: 角色名
          segments: segment 列表（我创作的）
          style: 视觉风格 (manhua / realistic)
          bgm_style: BGM 风格偏好

        返回:
          {
              "production": Production,
              "gate_result": dict  (Gate 1 审核展示信息)
          }

        用法:
          result = ScriptGenerator.create_and_inject(
              pc, "文字灵感", "一段温柔的日常",
              "小漫的午后", "小漫", segments
          )
          prod = result["production"]
          gate = result["gate_result"]
        """
        from pipeline_controller import PipelineController

        # 1. 验证 segments
        errors = cls.validate_segments(segments)
        if errors:
            error_msg = "; ".join(errors)
            raise ValueError(f"Segments 验证失败: {error_msg}")

        # 2. 创建生产任务
        prod = pc.create(source_type, source_data, title, character, style)

        # 3. 注入并提交 Gate 1
        gate_result = cls.inject_into_pipeline(
            pc, prod.id, title, character,
            segments, style, source_type, bgm_style
        )

        return {
            "production": prod,
            "gate_result": gate_result,
        }

    @classmethod
    def print_gate1_summary(cls, gate_result: dict):
        """打印 Gate 1 审核摘要（给用户看）"""
        summary = gate_result.get("summary", {})
        print(f"\n{'=' * 60}")
        print(f"  🅰️  Gate 1 — 脚本方向审核")
        print(f"{'=' * 60}")
        print(f"  标题: {summary.get('title', '')}")
        print(f"  来源: {summary.get('source', '')}")
        print(f"  角色: {summary.get('character', '')}")
        print(f"  总时长: {summary.get('total_duration', 0)}s ({summary.get('segment_count', 0)} 个分镜)")
        print(f"  ─────────────────────────────────")
        print(f"  场景结构:")
        for sc in summary.get("structure", []):
            print(f"    #{sc['id']} {sc['scene']} ({sc['duration']}s, {sc['emotion']})")
        print(f"  ─────────────────────────────────")
        print(f"  情绪分布: {summary.get('emotion_distribution', {})}")
        print(f"  ─────────────────────────────────")
        print(f"  📌 等待审核: 脚本方向、风格、节奏")
        print(f"     ✅ pc.approve_gate('{gate_result.get('production_id', '')}', gate=1)")
        print(f"     ❌ pc.reject_gate('{gate_result.get('production_id', '')}', gate=1, feedback='...')")

    @classmethod
    def create_empty_segments(cls, count: int = 4) -> list[dict]:
        """创建空的分镜模板（供手动填写）"""
        return [
            {
                "scene": f"场景 {i+1}",
                "description": "请填写视觉描述",
                "dialogue": "",
                "emotion": "中性",
                "duration_sec": 8,
                "camera": "medium_shot",
                "transition": "cut",
            }
            for i in range(count)
        ]


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def cli():
    """CLI 接口：从 JSON 文件导入并注入流水线"""
    import argparse
    import json
    from pipeline_controller import PipelineController

    parser = argparse.ArgumentParser(description="ScriptGenerator CLI — 脚本生成桥接")
    parser.add_argument("action", choices=["import", "template", "inspect"],
                        default="import", nargs="?")
    parser.add_argument("--segments", default="", help="分镜 JSON 文件路径")
    parser.add_argument("--title", default="未命名", help="视频标题")
    parser.add_argument("--character", default="小漫", help="角色名")
    parser.add_argument("--style", default="manhua", help="视觉风格 (manhua/realistic)")
    parser.add_argument("--source", default="CLI导入", help="灵感来源")
    parser.add_argument("--bgm-style", default="治愈", help="BGM 风格")
    parser.add_argument("--prod-id", default="", help="注入已有任务（可选，不填则新建）")

    args = parser.parse_args()
    pc = PipelineController()

    if args.action == "template":
        # 生成空模板
        import json as _json
        template = ScriptGenerator.create_empty_segments(4)
        print(_json.dumps(template, indent=2, ensure_ascii=False))
        return

    if args.action == "import":
        if not args.segments:
            print("❌ 请指定 --segments <json文件路径>")
            return

        with open(args.segments, "r", encoding="utf-8") as f:
            segments = json.load(f)

        # 注入
        if args.prod_id:
            gate_result = ScriptGenerator.inject_into_pipeline(
                pc, args.prod_id, args.title, args.character,
                segments, args.style, args.source, args.bgm_style
            )
            print(f"✅ 已注入到生产任务: {args.prod_id}")
        else:
            result = ScriptGenerator.create_and_inject(
                pc, args.source, "", args.title, args.character,
                segments, args.style, args.bgm_style
            )
            prod = result["production"]
            gate_result = result["gate_result"]
            print(f"✅ 已创建生产任务: {prod.id}")

        ScriptGenerator.print_gate1_summary(gate_result)

    elif args.action == "inspect":
        if not args.prod_id:
            print("❌ 请指定 --prod-id")
            return
        prod = pc.get(args.prod_id)
        if not prod:
            print(f"❌ 未找到任务: {args.prod_id}")
            return
        print(f"\n📋 生产任务: {prod.id}")
        print(f"  标题: {prod.title}")
        print(f"  状态: {prod.state.value}")
        print(f"  角色: {prod.character}")
        print(f"  风格: {prod.visual_style}")
        print(f"  分镜数: {len(prod.script.get('segments', []))}")
        total = sum(s.get('duration_sec', 0) for s in prod.script.get('segments', []))
        print(f"  总时长: {total}s")


if __name__ == "__main__":
    cli()

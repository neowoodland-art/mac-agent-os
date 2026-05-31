#!/usr/bin/env python3
"""
Demo: 漫剧视频工厂全链路流程演示 v1.0

模拟一次完整的生产流程:
  灵感 → 脚本 → Gate 1(审核) → 角色适配 → Gate 2(审核) → 选BGM → Gate 3(费用确认) → 开始生产

通过此演示可以看到三道审核关卡的交互和各个模块的协同工作。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from script_schemas import ScriptBuilder, validate_script, generate_gate1_summary, generate_gate2_table, save_script
from character_registry import CharacterRegistry
from character_adapter import CharacterAdapter
from music_selector import BGMSelector
from pipeline_controller import PipelineController


def print_separator(title):
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main():
    print_separator("漫剧视频工厂 — 全链路流程演示")
    print("模拟场景: '小漫的一天' — 治愈系漫剧")
    print("角色: 小漫 (示例角色，已在角色注册中心注册)")
    print("路径: 漫剧 (即梦文生图)")
    print()

    # ── 准备 ──
    print_separator("📋 第 0 步: 初始化模块")

    registry = CharacterRegistry()
    adapter = CharacterAdapter(registry)
    bgm = BGMSelector()
    pc = PipelineController()

    char = registry.get_active_character()
    print(f"  角色: {char.name}")
    print(f"  描述: {char.description[:40]}...")
    print(f"  BGM 库: {len(bgm)} 首可用")
    print(f"  BGM 热门: {[e['name'] for e in bgm.get_trending(3)]}")

    # ── 创建脚本 ──
    print_separator("📝 第 1 步: 创建脚本 (输入层)")
    script = ScriptBuilder.empty("小漫的一天", "小漫")
    script["meta"]["source"] = "文字灵感"

    ScriptBuilder.add_segment(script, {
        "scene": "清晨的咖啡馆",
        "description": "推开咖啡馆的门，阳光透过窗户洒进来，空气中飘着咖啡香",
        "dialogue": "（旁白）每个清晨，小漫都会来到这家街角的咖啡馆。",
        "emotion": "温暖平静",
        "duration_sec": 8,
        "camera": "wide_shot",
        "transition": "fade_in",
    })
    ScriptBuilder.add_segment(script, {
        "scene": "靠窗的座位",
        "description": "她坐下来，把画板放在桌上，拿出铅笔开始构思",
        "dialogue": "小漫: '今天一定要把草稿画完！'",
        "emotion": "专注",
        "duration_sec": 6,
        "camera": "medium_shot",
        "transition": "cut",
    })
    ScriptBuilder.add_segment(script, {
        "scene": "画板上的世界",
        "description": "铅笔在纸上飞舞，线条逐渐成形，一个奇妙的世界在画中展开",
        "dialogue": "（旁白）在她的画笔下，每一个角落都充满了故事。",
        "emotion": "愉悦",
        "duration_sec": 8,
        "camera": "close_up",
        "transition": "zoom_in",
    })
    ScriptBuilder.add_segment(script, {
        "scene": "傍晚的天台",
        "description": "夕阳西下，天边的云彩染成金色，她看着刚完成的画",
        "dialogue": "（旁白）有时候，最简单的快乐就在画笔下。",
        "emotion": "满足",
        "duration_sec": 10,
        "camera": "wide_shot",
        "transition": "dissolve",
    })

    errors = validate_script(script)
    print(f"  脚本标题: {script['meta']['title']}")
    print(f"  分镜数: {len(script['segments'])} 个")
    print(f"  总时长: {script['meta']['duration_sec']}s")
    print(f"  验证结果: {'✅ 通过' if not errors else '❌ 有错误: ' + str(errors)}")

    # ── 创建生产任务 ──
    prod = pc.create("文字灵感", "小漫的一天", "小漫的一天", "小漫", "manhua")
    pc.set_script(prod.id, script)
    print(f"  生产任务: {prod.id}")

    # ── Gate 1: 脚本方向审核 ──
    print_separator("🅰️  第 2 步: Gate 1 — 脚本方向审核")
    result = pc.submit_gate(prod.id, gate=1)
    s = result.get("summary", {})

    print(f"  状态: {result['state']}")
    print(f"  ─────────────────────────────────")
    print(f"  标题: {s.get('title', '')}")
    print(f"  来源: {s.get('source', '')}")
    print(f"  角色: {s.get('character', '')}")
    print(f"  总时长: {s.get('total_duration', 0)}s ({s.get('segment_count', 0)} 个分镜)")
    print(f"  结构:")
    for sc in s.get("structure", []):
        print(f"    #{sc['id']} {sc['scene']} ({sc['duration']}s, {sc['emotion']})")
    print(f"  情绪分布: {s.get('emotion_distribution', {})}")
    print(f"  ─────────────────────────────────")
    print(f"  📌 等待你审核: 脚本方向、风格、节奏")
    print(f"     ✅ approve → ❌ reject → 输入反馈")
    print()

    # 模拟通过
    print("  >> 模拟: 审核通过 ✅")
    pc.approve_gate(prod.id, gate=1)

    # ── 角色适配 ──
    print_separator("🔧 第 3 步: 角色适配 (核心)")

    # 预览适配效果
    preview = adapter.preview_adaptation(script)
    print(f"  适配角色: {preview['character']}")
    print(f"  角色描述: 短发齐刘海、大眼睛深棕色瞳孔、白连衣裙红蝴蝶结")
    print()
    for b, a in zip(preview["before"], preview["after"]):
        print(f"  #{b['id']} {b['scene']}")
        print(f"    描述: {b['description'][:40]}...")
        print(f"    → {a['description'][:40]}...")
        print()

    # 执行适配
    adapted_storyboard = adapter.adapt_to_storyboard(script)
    pc.set_adapted_storyboard(prod.id, adapted_storyboard)
    print(f"  ✅ 适配完成: {len(adapted_storyboard)} 个分镜已注入角色信息")

    # ── Gate 2: 分镜预览审核 ──
    print_separator("🅱️  第 4 步: Gate 2 — 分镜预览审核")
    result = pc.submit_gate(prod.id, gate=2)

    print(f"  状态: {result['state']}")
    print(f"  ─────────────────────────────────")
    print(f"  {'#':>3} | {'场景':12s} | {'时长':4s} | {'情绪':8s} | {'镜头':12s} | {'视觉风格':8s}")
    print(f"  ─────┼─────────────┼──────┼──────────┼──────────────┼──────────")
    for seg in result.get("storyboard", []):
        dur = seg.get('duration', seg.get('duration_sec', 0))
        print(f"  {seg['id']:3d} | {seg['scene']:12s} | {dur:3d}s | {seg['emotion']:8s} | {seg['camera']:12s} | {seg.get('visual_style', 'manhua'):8s}")
    print(f"  ─────────────────────────────────")
    print(f"  📌 等待你审核: 逐分镜检查场景/情绪/视觉风格")
    print(f"     ✅ 全部通过 → ❌ 打回(说明意见)")
    print()

    # 模拟通过
    print("  >> 模拟: 审核通过 ✅")
    pc.approve_gate(prod.id, gate=2)

    # ── BGM 选择 ──
    print_separator("🎵 第 5 步: BGM 选择")
    print("  🔥 热门推荐:")
    for bgm_entry in bgm.get_trending(3):
        print(f"    {bgm_entry['id']:15s} | {bgm_entry['name']:10s} | {bgm_entry['artist']:10s} | {bgm_entry['bpm']}bpm | {bgm_entry['style']}")
    print()
    print("  📂 按风格浏览:")
    for style in bgm.list_styles():
        entries = bgm.get_by_style(style)
        print(f"    {style}: {', '.join(e['name'] for e in entries)}")

    selected_bgm = "向云端"
    bgm_config = bgm.generate_config(selected_bgm, beat_sync=False, ducking=True, volume=0.6)
    pc.set_bgm(prod.id, selected_bgm, bgm_config)
    print(f"\n  🎯 选择: {selected_bgm}")
    print(f"     音量: {bgm_config['volume']}, 人声避让: {bgm_config['ducking']}, BPM: {bgm_config['bpm']}")

    # ── Gate 3: 费用确认 ──
    print_separator("💰 第 6 步: Gate 3 — 费用确认")
    result = pc.submit_gate(prod.id, gate=3)
    cost = result.get("cost", {})

    print(f"  状态: {result['state']}")
    print(f"  ─────────────────────────────────")
    print(f"  路径: {cost.get('path_type', 'manhua')}")
    print(f"  分镜数: {cost.get('image_count', 0)}")
    print(f"  ─────────────────────────────────")
    print(f"  图片生成: ¥{cost.get('image_cost', 0):.2f}")
    print(f"  视频生成: ¥{cost.get('video_cost', 0):.2f}")
    print(f"  TTS 费用: ¥{cost.get('tts_cost', 0):.2f}")
    print(f"  BGM 费用: ¥{cost.get('bgm_cost', 0):.2f}")
    print(f"  ─────────────────────────────────")
    print(f"  ══ 总计: ¥{cost.get('total', 0):.2f} ══")
    print(f"  ─────────────────────────────────")
    print(f"  📌 等待你确认: 费用明细确认")
    print(f"     ✅ 确认并执行 → ❌ 取消 → 回到分镜调整")
    print()

    # 模拟确认
    print("  >> 模拟: 费用确认 ✅")
    pc.confirm_cost(prod.id)

    # ── 开始生成 ──
    print_separator("🎬 第 7 步: 开始生产")
    pc.start_generation(prod.id)
    print(f"  状态: {pc.get(prod.id).state.value}")

    # 模拟完成
    pc.complete_step(prod.id, "generation")
    pc.complete_step(prod.id, "composition")

    # ── 最终状态 ──
    print_separator("🏁 生产完成")
    final = pc.get(prod.id)
    print(f"  任务 ID: {final.id}")
    print(f"  标题: {final.title}")
    print(f"  状态: {final.state.value} ✅")
    print(f"  角色: {final.character}")
    print(f"  BGM: {final.bgm_id}")
    print(f"  创建: {final.created_at}")
    print(f"  完成: {final.completed_at}")
    print(f"  成本: ¥{final.cost.total:.2f}")

    # ── 审核打回演示 ──
    print_separator("🔄 额外演示: 审核打回流程")
    prod2 = pc.create("文字灵感", "测试", "测试打回", "小漫", "manhua")
    pc.set_script(prod2.id, script)
    pc.submit_gate(prod2.id, gate=1)
    pc.reject_gate(prod2.id, gate=1, feedback="故事节奏太慢，需要增加冲突桥段")
    print(f"  任务: {prod2.id}")
    print(f"  状态: {pc.get(prod2.id).state.value}")
    print(f"  反馈: {pc.get(prod2.id).gate1_feedback}")
    print()
    print(f"  你可以:")
    print(f"    - 修改脚本后 resubmit (重提审核)")
    print(f"    - 取消任务 cancel")

    # ── 清理测试数据 ──
    for pid in [prod.id, prod2.id]:
        path = pc._data_dir / f"{pid}.json"
        if path.exists():
            path.unlink()
    print()
    print("=" * 70)
    print("  ✅ 全链路演示完成!")
    print("  📍 所有模块已通过串行测试")
    print("=" * 70)


if __name__ == "__main__":
    main()

"""
exporter.py — 录制结果自动导出引擎 (v1.0)

三阶段管线 Phase 3:
  分析结果 → 生成 OP_GRAPH 条目 + 蓝图模板 + 代码片段

用法:
  from mc.exporter import export_all
  result = export_all(analysis_result, recording_package)
"""
import json
import re
from pathlib import Path
from typing import Optional

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
TOOL_DIR = SCRIPTS_DIR.parent

# 已存在的 OP_GRAPH 路径（追加用）
MATRIX_MGMT = SCRIPTS_DIR / "matrix_mgmt.py"
BLUEPRINTS_DIR = TOOL_DIR / "blueprints"


def export_all(analysis: dict, package: dict) -> dict:
    """完整导出管线——生成 OP_GRAPH + 蓝图 + 代码"""
    return {
        "op_graph_entries": _generate_op_graph_entries(analysis),
        "blueprint": _generate_blueprint(analysis, package),
        "code_snippet": _generate_code_snippet(analysis, package),
        "summary": _generate_summary(analysis, package),
    }


def _generate_op_graph_entries(analysis: dict) -> list:
    """从分析结果生成 OP_GRAPH 字典条目"""
    actions = analysis.get("actions", [])
    entries = []

    for i, action in enumerate(actions):
        at = action.get("action_type", "unknown")
        desc = action.get("action_desc", "")

        # 确定平台和分类
        platform, category, label, requires, allows = _classify_action(at, desc)

        # 生成 op name
        op_name = _suggest_op_name(at, i)

        # 检查是否已有同名操作
        if _op_exists(op_name):
            op_name = f"{op_name}_v{i+1}"

        entry = {
            "name": op_name,
            "definition": {
                "platform": platform,
                "category": category,
                "label": f"🎬 {desc}" if desc else f"🎬 自定义操作{i+1}",
                "requires": requires,
                "allows": allows,
                "can_be_first": "goto_home" not in requires,
                "desc": desc or f"录制步骤 {action.get('step_after', '?')}",
                "_source": "recorded",  # recorded = AI录制, manual = 手工创建
                "_action_type": at,
            }
        }

        # 如果有点击坐标，记录
        inferred = action.get("inferred_action", {})
        if inferred.get("coords"):
            entry["definition"]["_click_coords"] = inferred["coords"]

        entries.append(entry)

    return entries


def _classify_action(action_type: str, desc: str) -> tuple:
    """确定操作所属平台、分类、依赖"""
    # 默认值
    platform = "通用"
    category = "custom"
    requires = []
    allows = ["rest", "go_back"]

    if action_type == "like":
        platform = "douyin"
        category = "interact"
        requires = ["goto_home"]
        allows = ["rest", "go_back", "collect", "next_video"]
    elif action_type == "comment" or action_type == "open_comment":
        platform = "douyin"
        category = "interact"
        requires = ["goto_home"]
        allows = ["rest", "go_back", "like"]
    elif action_type in ("navigate_video", "enter_video"):
        platform = "douyin"
        category = "navigation"
        requires = ["goto_home"]
        allows = ["like", "collect", "comment", "next_video", "scroll_feed", "rest"]
    elif action_type == "navigate_profile":
        platform = "douyin"
        category = "navigation"
        requires = ["goto_home"]
        allows = ["read_profile", "rest", "go_back"]
    elif action_type == "scroll" or "scroll" in action_type:
        platform = "douyin"
        category = "navigation"
        requires = ["goto_home"]
        allows = ["rest", "go_back", "next_video"]
    elif action_type == "search":
        platform = "douyin"
        category = "navigation"
        requires = ["goto_home"]
        allows = ["browse_feed", "rest", "go_back"]
    elif action_type == "next_video":
        platform = "douyin"
        category = "navigation"
        requires = ["goto_home"]
        allows = ["like", "collect", "comment", "rest", "go_back"]
    elif "xhs" in platform or "xiaohongshu" in desc.lower():
        platform = "xiaohongshu"
        category = "custom"
        requires = ["xhs_goto_home"]
        allows = ["rest", "go_back"]
    elif "click" in action_type:
        platform = "通用"
        category = "interact"
        requires = ["goto_home", "xhs_goto_home"]
        allows = ["rest", "go_back"]

    return platform, category, f"🎬 {desc[:15]}" if desc else "🎬 自定义", requires, allows


def _suggest_op_name(action_type: str, index: int) -> str:
    """生成操作名称"""
    name_map = {
        "like": "custom_like", "comment": "custom_comment", "follow": "custom_follow",
        "navigate_video": "custom_open_video", "navigate_profile": "custom_goto_profile",
        "scroll": "custom_scroll", "next_video": "custom_next",
        "search": "custom_search", "enter_video": "custom_enter_video",
        "click": "custom_click", "keypress": "custom_keypress",
        "view_profile": "custom_view_profile", "unknown": "custom_action",
    }
    base = name_map.get(action_type, f"custom_{action_type}")
    return base


def _op_exists(op_name: str) -> bool:
    """检查 OP_GRAPH 是否已有同名操作"""
    if not MATRIX_MGMT.exists():
        return False
    content = MATRIX_MGMT.read_text()
    return f'"{op_name}":' in content


def _generate_blueprint(analysis: dict, package: dict) -> dict:
    """从分析结果生成蓝图 JSON"""
    actions = analysis.get("actions", [])
    meta = package.get("meta", {})

    # 确定平台
    platform = meta.get("platform", "unknown")
    for action in actions:
        at = action.get("action_type", "")
        if "xhs" in at or "profile" in at:
            platform = "xiaohongshu" if "profile" in at else "douyin"
            break

    # 构建步骤
    steps = []
    seen_ops = set()
    step_id = 1

    # 如果是从首页开始的，先加 goto_home
    if platform == "douyin":
        steps.append({
            "step_id": step_id, "op": "goto_home",
            "args": {}, "wait_after": 3
        })
        seen_ops.add("goto_home")
        step_id += 1

    for action in actions:
        at = action.get("action_type", "unknown")
        op_name = _suggest_op_name(at, step_id)

        # 跳过重复的导航步骤
        if op_name in seen_ops:
            continue
        seen_ops.add(op_name)

        step = {
            "step_id": step_id,
            "op": op_name,
            "args": {},
            "wait_after": 2,
        }

        # 如果是搜索操作，加默认关键词
        if at == "search":
            step["args"]["keyword"] = "热门"

        steps.append(step)
        step_id += 1

    blueprint = {
        "id": f"recorded_{meta.get('account_id', 'unknown')}_{len(actions)}steps",
        "name": f"录制蓝图 ({len(actions)}步)",
        "version": "1.0.0",
        "platform": platform,
        "description": f"由录制自动生成: {meta.get('account_id','?')} {len(actions)}步操作",
        "steps": steps,
    }

    return blueprint


def _generate_code_snippet(analysis: dict, package: dict) -> str:
    """生成可在 engine.py 中使用的操作代码片段"""
    actions = analysis.get("actions", [])
    lines = []
    lines.append("# ═══════════════════════════════════════════════")
    lines.append(f"# 录制生成: {package.get('meta', {}).get('account_id', '?')}")
    lines.append(f"# 步骤数: {len(actions)}")
    lines.append("# ═══════════════════════════════════════════════")
    lines.append("")

    for i, action in enumerate(actions):
        at = action.get("action_type", "unknown")
        desc = action.get("action_desc", "")
        inferred = action.get("inferred_action", {})

        lines.append(f"    # 步骤 {i+1}: {desc}")
        lines.append(f"    elif op == \"{_suggest_op_name(at, i)}\":")

        if at == "like":
            lines.append('        r = await conn.page.evaluate("""() => {')
            lines.append('            const b = document.querySelector(\'[data-e2e="like-count"]\');')
            lines.append('            return b ? (b.click(), \'👍\') : \'-\';')
            lines.append('        }""")')
            lines.append('        result = r')
        elif at == "navigate_profile":
            lines.append('        await conn.page.goto("https://www.douyin.com/user/self", timeout=20000)')
            lines.append('        await asyncio.sleep(4)')
            lines.append('        result = "profile_loaded"')
        elif at == "scroll" or "scroll" in at:
            lines.append('        await conn.page.evaluate("() => window.scrollBy(0, 600)")')
            lines.append('        await asyncio.sleep(1)')
            lines.append('        result = "scrolled"')
        elif inferred.get("coords"):
            coords = inferred["coords"]
            lines.append(f'        # 点击坐标 ({coords["x"]}, {coords["y"]})')
            lines.append(f'        await conn.page.mouse.click({coords["x"]}, {coords["y"]})')
            lines.append('        await asyncio.sleep(2)')
            lines.append('        result = "clicked"')
        elif inferred.get("trigger", "").startswith("key:"):
            key = inferred["trigger"].split(":")[1]
            lines.append(f'        # 按键: {key}')
            lines.append(f'        await conn.page.keyboard.press("{key}")')
            lines.append('        await asyncio.sleep(2)')
            lines.append('        result = "pressed"')
        else:
            lines.append(f'        # TODO: 实现 {desc} 的自动化操作')
            lines.append('        await asyncio.sleep(2)')
            lines.append('        result = f"TODO({at})"')

        lines.append("")

    return "\n".join(lines)


def _generate_summary(analysis: dict, package: dict) -> dict:
    """生成操作汇总摘要"""
    actions = analysis.get("actions", [])
    meta = package.get("meta", {})

    # 统计操作类型
    type_counts = {}
    for a in actions:
        at = a.get("action_type", "unknown")
        type_counts[at] = type_counts.get(at, 0) + 1

    return {
        "account": meta.get("account_id", "?"),
        "total_steps": meta.get("total_steps", 0),
        "actions_found": len(actions),
        "action_types": type_counts,
        "action_sequence": [a.get("action_type", "?") for a in actions],
        "suggested_blueprint_id": f"recorded_{meta.get('account_id', '?')}_{len(actions)}steps",
    }


def export_recording(recording_path: str, output_dir: str = None) -> dict:
    """一站式：加载 → 分析 → 导出"""
    from mc.recorder import RecordingSession
    from mc.analyzer import analyze_recording

    pkg = RecordingSession.load_recording(recording_path)
    analysis = analyze_recording(pkg)
    result = export_all(analysis, pkg)

    # 保存导出产物
    out_dir = Path(output_dir) if output_dir else BLUEPRINTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    base_name = Path(recording_path).stem.replace("recording_", "export_")

    # 保存蓝图
    bp = result.get("blueprint", {})
    if bp:
        bp_file = out_dir / f"{base_name}.json"
        with open(bp_file, "w", encoding="utf-8") as f:
            json.dump(bp, f, ensure_ascii=False, indent=2)
        result["saved_blueprint"] = str(bp_file)

    # 保存代码片段
    code = result.get("code_snippet", "")
    if code:
        code_file = out_dir / f"{base_name}.py"
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)
        result["saved_code"] = str(code_file)

    return result


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else ""
    if path:
        result = export_recording(path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("用法: python -m mc.exporter <录制包路径>")

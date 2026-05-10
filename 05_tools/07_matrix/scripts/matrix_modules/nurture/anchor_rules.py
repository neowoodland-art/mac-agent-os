"""
anchor_rules.py — 锚点检测引擎

从 anchor.db 读取规则，执行状态检测。
规则可动态更新（通过 anchor_db.py），无需修改代码。
"""
import re
import json
from . import anchor_db as db


# ── 运算符映射 ──

def _apply_op(field_value, operator, target_value):
    """对单个字段应用运算符比较（不区分大小写）"""
    if field_value is None:
        return False

    # 全部转字符串，不区分大小写
    fv = str(field_value).lower()
    tv = str(target_value).lower()

    if operator == 'eq':
        return fv == tv
    elif operator == 'neq':
        return fv != tv
    elif operator == 'gt':
        try:
            return float(fv) > float(tv)
        except (ValueError, TypeError):
            return False
    elif operator == 'gte':
        try:
            return float(fv) >= float(tv)
        except (ValueError, TypeError):
            return False
    elif operator == 'lt':
        try:
            return float(fv) < float(tv)
        except (ValueError, TypeError):
            return False
    elif operator == 'lte':
        try:
            return float(fv) <= float(tv)
        except (ValueError, TypeError):
            return False
    elif operator == 'contains':
        return tv in fv
    elif operator == 'not_contains':
        return tv not in fv
    elif operator == 'regex':
        try:
            return bool(re.search(tv, fv))
        except re.error:
            return False
    return False


# ── 核心检测逻辑 ──

def detect_state(anchors: dict, strict: bool = False) -> str:
    """检测当前页面状态

    Args:
        anchors: DOM 锚点数据字典
        strict: True=必须所有规则满足; False=按置信度选最佳匹配

    Returns:
        state_name 或 'UNKNOWN'
    """
    rules = db.get_rules()
    if not rules:
        return "UNKNOWN"

    # 按 state_name 分组
    state_rules = {}
    for r in rules:
        sn = r['state_name']
        if sn not in state_rules:
            state_rules[sn] = {}
        lg = r['logic_group']
        if lg not in state_rules[sn]:
            state_rules[sn][lg] = []
        state_rules[sn][lg].append(r)

    best_state = "UNKNOWN"
    best_score = 0

    # 检测优先级（子状态优先于父状态）
    PRIORITY = ['SEARCH_PLAYER', 'DETAIL', 'PLAYER', 'SEARCH', 'HOME', 'POPUP', 'LOGIN']
    state_groups = sorted(state_rules.items(),
                         key=lambda x: PRIORITY.index(x[0]) if x[0] in PRIORITY else 99)

    for state_name, groups in state_groups:
        # 每个 logic_group 内的规则 AND，不同 group 之间 OR
        group_results = []
        for group_id, group_rules in groups.items():
            all_match = all(
                _apply_op(anchors.get(r['field']), r['operator'], r['value'])
                for r in group_rules
            )
            group_results.append(all_match)

        # OR 连接：任一 group 通过即该状态匹配
        state_match = any(group_results)

        if strict:
            if state_match:
                return state_name
        else:
            # 非严格模式：计算匹配得分
            total_rules = sum(len(g) for g in groups.values())
            matched_rules = sum(
                sum(1 for r in g if _apply_op(anchors.get(r['field']), r['operator'], r['value']))
                for g in groups.values()
            )
            score = matched_rules / max(total_rules, 1)
            if state_match and score > best_score:
                best_score = score
                best_state = state_name
            elif not state_match and score > best_score:
                # 即使不完全匹配，高分也记录
                if score > 0.6:
                    best_score = score
                    best_state = f"{state_name}?"

    return best_state


def verify_op(op_name: str, anchors: dict) -> bool:
    """验证原子操作是否成功执行"""
    ops = db.get_ops(op_name)
    if not ops:
        return True  # 无验证规则默认通过
    op = ops[0]
    verify = op.get('verify_rule')
    if not verify:
        return True

    # 验证规则映射
    VERIFY_MAP = {
        'video_count_gte_3': lambda a: a.get('video_count', 0) >= 3,
        'video_src_change': lambda a: True,  # 需要前后对比
        'like_count_change': lambda a: True,
        'title_contains_搜索': lambda a: '搜索' in str(a.get('title', '')),
        'video_count_eq_1': lambda a: a.get('video_count', 0) == 1,
        'popup_gone': lambda a: not a.get('has_popup_close', False),
    }

    check = VERIFY_MAP.get(verify)
    if check:
        return check(anchors)
    return True


def log_and_check(identity: str, expected_state: str, anchors: dict,
                  screenshot_path: str = None) -> dict:
    """检测 + 记录 + 返回结果"""
    detected = detect_state(anchors)
    match = (detected == expected_state)

    db.log_detection(
        identity=identity,
        expected_state=expected_state,
        detected_state=detected,
        match=match,
        anchor_snapshot=anchors,
        screenshot_path=screenshot_path,
    )

    return {
        "expected": expected_state,
        "detected": detected,
        "match": match,
        "accuracy": db.get_recent_accuracy(identity),
        "needs_calibration": db.get_recent_failures(identity, threshold=5),
    }


# ── 便捷函数 ──

def list_rules(state_name: str = None) -> str:
    """以人类可读格式列出规则"""
    rules = db.get_rules(state_name)
    if not rules:
        return "暂无锚点规则"

    lines = []
    current_state = None
    for r in rules:
        if r['state_name'] != current_state:
            current_state = r['state_name']
            lines.append(f"\n[{current_state}]")
        lines.append(f"  {r['field']} {r['operator']} {r['value']} (group={r['logic_group']})")
    return '\n'.join(lines)


def list_ops() -> str:
    """列出所有原子操作"""
    ops = db.get_ops()
    if not ops:
        return "暂无原子操作"
    lines = []
    for op in ops:
        lines.append(f"  {op['op_name']:15s} | {op['action_type']:10s} | {op.get('target', ''):30s} | {op.get('verify_rule', '-')}")
    return '\n'.join(lines)


if __name__ == "__main__":
    # 测试：用采集数据验证规则
    import json
    summary_path = db.DB_DIR.parent.parent / "data" / "anchor_summary.json"
    if summary_path.exists():
        data = json.loads(summary_path.read_text())
        print("📊 用采集数据验证锚点规则:")
        for d in data:
            step = d['step']
            anchors = d['anchors']
            state = detect_state(anchors)
            print(f"  步{step}: {state:15s} | {d['url'][:40]}")
    print(f"\n📋 当前规则:\n{list_rules()}")
    print(f"\n📋 原子操作:\n{list_ops()}")

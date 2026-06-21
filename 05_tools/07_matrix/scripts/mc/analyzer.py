"""
analyzer.py — 录制步骤差异分析引擎 (v1.0)

三阶段管线 Phase 2:
  读取录制包 → 对比相邻步骤的 URL/DOM/事件 → 
  推断操作类型 → 生成结构化分析结果

用法:
  from mc.analyzer import analyze_recording
  result = analyze_recording(package)
"""
import json
import re
from pathlib import Path
from typing import Optional

# ── 抖音快捷键映射 ──
DY_HOTKEYS = {
    'z': 'like', 'x': 'comment', 'c': 'comment',
    'g': 'follow',
    'k': 'loop', 'm': 'mute', 'j': 'clear',
    'p': 'loop', 'h': 'fullscreen',
    'ArrowDown': 'next_video', 'ArrowUp': 'prev_video',
    ' ': 'play_pause',
}

# ── 点击坐标区域定义 ──
# (x_min, y_min, x_max, y_max, label)
KNOWN_REGIONS = {
    'dy_like_area':      (330, 400, 500, 600, '抖音点赞区域'),
    'dy_comment_area':   (350, 680, 500, 720, '抖音评论区触发'),
    'dy_search_bar':     (50, 50, 350, 90, '抖音搜索框'),
    'xhs_bottom_nav':    (0, 700, 400, 780, 'XHS底部导航'),
    'xhs_me_tab':        (300, 700, 400, 780, 'XHS"我"标签'),
}


def analyze_recording(package: dict) -> dict:
    """分析录制包，生成可导出的原子操作定义"""
    steps = package.get("steps", [])
    if len(steps) < 2:
        return {"error": "至少需要2个步骤才能分析", "steps_analyzed": 0}

    result = {
        "meta": package.get("meta", {}),
        "steps_analyzed": len(steps),
        "actions": [],
        "blueprint_suggestions": [],
    }

    # 分析相邻步骤对
    for i in range(len(steps) - 1):
        before = steps[i]
        after = steps[i+1]
        analysis = _analyze_step_pair(before, after)
        result["actions"].append(analysis)

    # 生成蓝图建议
    result["blueprint_suggestions"] = _suggest_blueprint(result["actions"])

    return result


def _analyze_step_pair(before: dict, after: dict) -> dict:
    """分析一对相邻步骤的变化"""
    bp = before.get("page", {})
    ap = after.get("page", {})
    events = before.get("events", [])

    # before_state 对比（三段式记录的状态指纹）
    bbs = before.get("before_state", {}) or {}
    abs = after.get("before_state", {}) or {}

    analysis = {
        "step_before": before["step"],
        "step_after": after["step"],
        "event_count": len(events),
        "page_url": ap.get("url", ""),
        "page_mode": ap.get("page_mode", "?"),
        "interactable_count": ap.get("interactable_count", 0),
    }

    # 0. before_state 选择器变化分析（优先级最高）
    sel_before = bbs.get("selectors", {})
    sel_after = abs.get("selectors", {})
    if sel_before and sel_after:
        sel_changes = {}
        all_keys = set(sel_before) | set(sel_after)
        for k in all_keys:
            v1 = sel_before.get(k, False)
            v2 = sel_after.get(k, False)
            if v1 != v2:
                sel_changes[k] = f"{'✅' if v1 else '❌'}→{'✅' if v2 else '❌'}"
        if sel_changes:
            analysis["selector_changes"] = sel_changes

        # 基于选择器变化推断操作
        op = _infer_op_from_selectors(sel_before, sel_after, bbs, abs)
        if op:
            analysis["action_type"] = op["type"]
            analysis["action_desc"] = op["desc"]
            analysis["confidence"] = op["confidence"]

    # 1. URL 变化分析
    url_before = bp.get("url", "")
    url_after = ap.get("url", "")
    if url_before != url_after:
        analysis["url_changed"] = True
        analysis["url_from"] = url_before[:80]
        analysis["url_to"] = url_after[:80]

        # URL 变化类型推断
        if "/video/" in url_after and "/video/" not in url_before:
            analysis["action_type"] = "navigate_video"
            analysis["action_desc"] = "进入视频播放页"
        elif "/user/profile/" in url_after:
            analysis["action_type"] = "navigate_profile"
            analysis["action_desc"] = "进入个人主页"
        elif "/search/" in url_after or "?keyword=" in url_after:
            analysis["action_type"] = "search"
            analysis["action_desc"] = "搜索"
        elif "/user/self" in url_after:
            analysis["action_type"] = "navigate_profile"
            analysis["action_desc"] = "进入抖音主页"
        else:
            analysis["action_type"] = "navigate"
            analysis["action_desc"] = "页面导航"
    else:
        analysis["url_changed"] = False

    # 2. 页面模式变化
    mode_before = bp.get("page_mode", "?")
    mode_after = ap.get("page_mode", "?")
    if mode_before != mode_after:
        analysis["mode_changed"] = f"{mode_before} → {mode_after}"
        if mode_before == "grid" and mode_after == "player":
            analysis["action_type"] = analysis.get("action_type", "enter_video")
            analysis["action_desc"] = analysis.get("action_desc", "进入视频播放")
        elif mode_before == "player" and mode_after == "grid":
            analysis["action_type"] = analysis.get("action_type", "exit_video")
            analysis["action_desc"] = analysis.get("action_desc", "退出视频")
        elif mode_after == "profile":
            analysis["action_type"] = analysis.get("action_type", "view_profile")
            analysis["action_desc"] = analysis.get("action_desc", "查看主页")

    # 3. 事件序列分析（从用户操作反推操作类型）
    if events:
        action = _infer_action_from_events(events)
        if action:
            analysis["inferred_action"] = action
            # 事件推断的优先级高于 URL 推断
            if action.get("type") and not analysis.get("action_type"):
                analysis["action_type"] = action["type"]
                analysis["action_desc"] = action.get("desc", "")

    # 4. 文本差异分析
    text_before = bp.get("text_snippet", "")
    text_after = ap.get("text_snippet", "")
    if text_before and text_after and text_before != text_after:
        analysis["text_changed"] = True
        # 检测文本中的关键变化
        added = _find_added_text(text_before, text_after)
        if added:
            analysis["text_added"] = added[:100]

    # 5. 标题变化
    title_before = bp.get("title", "")
    title_after = ap.get("title", "")
    if title_before != title_after:
        analysis["title_changed"] = f"{title_before[:30]} → {title_after[:30]}"

    # 6. 交互元素变化
    ia_before = set(e.get("e2e", "") or e.get("cls", "") for e in bp.get("interactables", []))
    ia_after = set(e.get("e2e", "") or e.get("cls", "") for e in ap.get("interactables", []))
    new_elements = ia_after - ia_before
    if new_elements:
        analysis["new_elements"] = list(new_elements)[:5]

    # 7. 生成特征码（可复现的自动化选择器建议）
    analysis["features"] = _suggest_features(bp, ap, events, analysis)

    # 8. 检测空步骤（连续两次 · 无操作）
    if not analysis.get("action_type"):
        no_events = len(events) <= 1  # 只有 · 键事件
        no_url_change = not analysis.get("url_changed", True)
        no_sel_change = not analysis.get("selector_changes")
        no_mode_change = not analysis.get("mode_changed")
        no_clicks = len([e for e in events if e.get('t') == 'click']) == 0
        no_scrolls = len([e for e in events if e.get('t') == 'scroll']) == 0
        if no_events and no_url_change and no_sel_change and no_mode_change:
            analysis["action_type"] = "skip"
            analysis["action_desc"] = "无有效操作（空步骤）"
            analysis["skip_reason"] = "no_change"

        # 9. 生成操作摘要
    if not analysis.get("action_type"):
        analysis["action_type"] = "unknown"
        analysis["action_desc"] = f"页面内容变化 ({len(events)} events)"

    return analysis


def _infer_op_from_selectors(sel_before: dict, sel_after: dict,
                              bbs: dict, abs: dict) -> Optional[dict]:
    """基于 before_state 的选择器变化推断具体操作"""
    # 抖音 like 按钮: [data-e2e="video-player-digg"]
    # 抖音 collect: [data-e2e="video-player-collect"]
    # 小红书 note: section.note-item
    digg_key = '[data-e2e="video-player-digg"]'
    collect_key = '[data-e2e="video-player-collect"]'
    search_key = '[data-e2e="searchbar-input"]'
    video_key = 'video'
    note_key = 'section.note-item'

    p_before = bbs.get("page_mode", "")
    p_after = abs.get("page_mode", "")

    # 检测抖音点赞操作
    digg_before = sel_before.get(digg_key, False)
    digg_after = sel_after.get(digg_key, False)
    if digg_before and not digg_after and p_before == "player":
        return {"type": "like", "desc": "点赞", "confidence": "high"}
    # 检测抖音取消点赞
    if not digg_before and digg_after and p_before == "player":
        liked_text_before = bbs.get("markers", {}).get("liked", "")
        liked_text_after = abs.get("markers", {}).get("liked", "")
        return {"type": "like", "desc": "点赞（按钮重显）", "confidence": "medium"}

    # 检测抖音收藏操作
    collect_before = sel_before.get(collect_key, False)
    collect_after = sel_after.get(collect_key, False)
    if collect_before and not collect_after and p_before == "player":
        return {"type": "collect", "desc": "收藏", "confidence": "high"}

    # 检测搜索操作
    search_before = sel_before.get(search_key, False)
    search_after = sel_after.get(search_key, False)
    if not search_before and search_after:
        return {"type": "search", "desc": "打开搜索", "confidence": "high"}
    if search_before and not search_after:
        return {"type": "go_back", "desc": "关闭搜索", "confidence": "medium"}

    # 检测进入小红书笔记
    note_before = sel_before.get(note_key, False)
    note_after = sel_after.get(note_key, False)
    if note_before and not note_after and p_before == "grid":
        return {"type": "xhs_click_note", "desc": "点击笔记", "confidence": "high"}
    if not note_before and note_after:
        return {"type": "go_back", "desc": "返回笔记列表", "confidence": "medium"}

    # 检测视频播放状态变化
    video_before = sel_before.get(video_key, False)
    video_after = sel_after.get(video_key, False)
    if not video_before and video_after:
        return {"type": "enter_video", "desc": "进入视频页", "confidence": "medium"}
    if video_before and not video_after:
        return {"type": "exit_video", "desc": "退出视频", "confidence": "medium"}

    return None


def _infer_action_from_events(events: list) -> Optional[dict]:
    """从 CDP 事件序列推断操作类型"""
    # 取关键事件：键盘 + 点击
    key_events = [e for e in events if e.get('t') == 'key']
    click_events = [e for e in events if e.get('t') == 'click']
    scroll_events = [e for e in events if e.get('t') == 'scroll']

    # 抖音快捷键识别
    for ke in key_events:
        k = ke.get('k', '').lower()
        if k in DY_HOTKEYS:
            action = DY_HOTKEYS[k]
            desc_map = {
                'like': '点赞', 'comment': '打开评论', 'follow': '关注',
                'loop': '连播', 'mute': '静音', 'clear': '清屏',
                'fullscreen': '全屏', 'next_video': '下一个视频',
                'prev_video': '上一个视频', 'play_pause': '播放/暂停',
            }
            return {"type": action, "desc": desc_map.get(action, action),
                    "trigger": f"key:{k}", "confidence": "high"}

    # 字母键识别
    for ke in key_events:
        k = ke.get('k', '')
        if len(k) == 1 and k.isalpha():
            return {"type": f"keypress_{k}", "desc": f"按键 {k}",
                    "trigger": f"key:{k}", "confidence": "medium"}

    # 点击事件分析
    if click_events:
        last_click = click_events[-1]
        x, y = last_click.get('x', 0), last_click.get('y', 0)
        target = last_click.get('target', '')

        # 检测区域
        for region_name, (x1, y1, x2, y2, label) in KNOWN_REGIONS.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                return {"type": f"click_{region_name}", "desc": label,
                        "trigger": f"click({x},{y})", "confidence": "medium",
                        "coords": {"x": x, "y": y}}

        return {"type": "click", "desc": f"点击 ({x},{y}) <{target}>",
                "trigger": f"click({x},{y})", "confidence": "medium",
                "coords": {"x": x, "y": y}}

    # 滚动事件
    if scroll_events and len(scroll_events) >= 2:
        total_dy = sum(e.get('dy', 0) for e in scroll_events)
        if total_dy > 200:
            return {"type": "scroll", "desc": f"下滚 (delta={total_dy})",
                    "trigger": "scroll", "confidence": "medium"}

    return None


def _find_added_text(old_text: str, new_text: str) -> str:
    """简单的文本差异检测——找出出现在新文本中但不在旧文本中的部分"""
    # 行级别 diff
    old_lines = set(old_text.split('\n'))
    new_lines = new_text.split('\n')
    added = [l.strip() for l in new_lines if l.strip() and l.strip() not in old_lines
             and len(l.strip()) > 3]
    return '\n'.join(added[:10]) if added else ''


def _suggest_features(before_page: dict, after_page: dict,
                      events: list, analysis: dict) -> list:
    """从事件和页面状态生成自动化特征码建议"""
    features = []
    key_events = [e for e in events if e.get('t') == 'key']
    click_events = [e for e in events if e.get('t') == 'click']

    # 来自推断操作的特征
    inferred = analysis.get("inferred_action", {})
    if inferred:
        trigger = inferred.get("trigger", "")
        if trigger.startswith("key:"):
            k = trigger.split(":")[1]
            features.append({
                "type": "keyboard",
                "selector": None,
                "description": f"按键 {k}",
                "code": f'await page.keyboard.press("{k}")',
                "confidence": inferred.get("confidence", "medium"),
            })
        elif "coords" in inferred:
            coords = inferred["coords"]
            # 尝试从 after_page 的 interactables 中找到最近的可点击元素
            closest = None
            for el in after_page.get("interactables", []):
                rect_str = el.get("rect", "")
                if rect_str and ',' in rect_str:
                    parts = rect_str.split()
                    if len(parts) >= 1:
                        xy = parts[0].split(',')
                        if len(xy) == 2:
                            try:
                                ex, ey = int(xy[0]), int(xy[1])
                                dist = (coords['x'] - ex) ** 2 + (coords['y'] - ey) ** 2
                                if dist < 5000 and (closest is None or dist < closest[0]):
                                    closest = (dist, el)
                            except:
                                pass
            if closest:
                el = closest[1]
                selector = el.get("e2e") or el.get("cls", "").split()[0] if el.get("cls") else None
                tag = el.get("tag", "")
                text = el.get("text", "")
                features.append({
                    "type": "click",
                    "selector": f'[data-e2e="{selector}"]' if selector else (f'{tag}:has-text("{text}")' if text else None),
                    "description": f'点击 <{tag}> "{text[:20]}"' if text else f'点击 <{tag}>',
                    "code": f'await page.locator("{selector or tag}").click()',
                    "confidence": "high" if selector else "medium",
                    "near_coords": f'({coords["x"]},{coords["y"]})',
                })
            else:
                features.append({
                    "type": "click_coords",
                    "selector": None,
                    "description": f"点击坐标 ({coords['x']},{coords['y']})",
                    "code": f'await page.mouse.click({coords["x"]}, {coords["y"]})',
                    "confidence": "medium",
                })

    # URL 变化特征
    if analysis.get("url_changed"):
        url_to = analysis.get("url_to", "")
        if "/video/" in url_to:
            features.append({
                "type": "navigation",
                "selector": 'a[href*="/video/"]',
                "description": "进入视频播放页",
                "code": 'await page.goto(video_url)',
                "confidence": "high",
            })
        elif "/user/profile/" in url_to:
            features.append({
                "type": "navigation",
                "selector": 'a[href*="/user/profile/"]',
                "description": "进入个人主页",
                "code": 'await page.goto(profile_url)',
                "confidence": "high",
            })

    # 页面模式变化的特征
    if analysis.get("mode_changed"):
        features.append({
            "type": "page_mode",
            "selector": None,
            "description": f"页面模式: {analysis['mode_changed']}",
            "code": None,
            "confidence": "high",
        })

    return features


def _suggest_blueprint(actions: list) -> list:
    """从分析结果生成蓝图建议"""
    suggestions = []
    for i, action in enumerate(actions):
        step_num = i + 1
        at = action.get("action_type", "unknown")

        # 操作名 → 建议的原子操作op名
        op_map = {
            "like": "like", "comment": "open_comment", "follow": "follow",
            "navigate_video": "open_video", "navigate_profile": "goto_profile",
            "scroll": "scroll_feed", "next_video": "next_video",
            "click_like_area": "like", "click_comment_area": "open_comment",
            "search": "search", "enter_video": "enter_video",
        }

        op = op_map.get(at, f"custom_{at}")
        suggestions.append({
            "step": step_num,
            "suggested_op": op,
            "action_type": at,
            "desc": action.get("action_desc", ""),
            "confidence": action.get("inferred_action", {}).get("confidence", "medium"),
        })
    return suggestions


# ── 快捷入口 ──
def analyze_recording_file(path: str) -> dict:
    """从文件路径加载并分析录制包"""
    from mc.recorder import RecordingSession
    pkg = RecordingSession.load_recording(path)
    return analyze_recording(pkg)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else ""
    if path:
        result = analyze_recording_file(path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("用法: python -m mc.analyzer <录制包路径>")

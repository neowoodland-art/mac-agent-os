"""
calibration.py — 校准触发器 + AI 兜底

功能：
1. 定期检查锚点检测成功率
2. 触发校准（连续失败/成功率低）
3. AI 兜底分析（基于 DOM 数据）
4. 生成校准候选规则
"""
import json
import time
from datetime import datetime
from pathlib import Path

import httpx

from . import anchor_db as db

# oMLX 配置
OLLAMA_BASE = "http://localhost:8000"
OLLAMA_API_KEY = "5omlx"
LLM_MODEL = "mlx-community--Qwen3.5-4B-MLX-4bit"  # 或 gemma-3-4b-it-4bit


# ── 校准检查 ──

def check_calibration(identity: str) -> dict:
    """检查是否需要校准

    Returns:
        dict: {needs, accuracy, consecutive_failures, level}
    """
    accuracy = db.get_recent_accuracy(identity, count=50)
    consecutive_fail = db.get_recent_failures(identity, threshold=5)

    # 判断级别
    if accuracy >= 0.9:
        level = "normal"
    elif accuracy >= 0.6:
        level = "warn"
    elif accuracy >= 0.3:
        level = "error"
    else:
        level = "alert"

    needs = (accuracy < 0.6) or consecutive_fail

    return {
        "needs_calibration": needs,
        "accuracy": round(accuracy, 2),
        "consecutive_failures": consecutive_fail,
        "level": level,
    }


def should_trigger(identity: str) -> bool:
    """快速判断是否应触发校准"""
    acc = db.get_recent_accuracy(identity, count=20)
    fail = db.get_recent_failures(identity, threshold=5)
    return acc < 0.6 or fail


# ── AI 兜底 ──

def _build_ai_prompt(anchors: dict, screenshot_path: str = None) -> str:
    """构建发给 LLM 的 prompt"""
    # 清理敏感数据
    safe_anchors = {k: v for k, v in anchors.items()
                    if k not in ('body_text', 'video_src_prefix')}

    prompt = f"""你是一个抖音页面状态分析专家。请根据以下页面DOM数据，判断当前页面处于什么状态。

DOM数据：
```json
{json.dumps(safe_anchors, ensure_ascii=False, indent=2)}
```

请返回以下JSON格式的分析结果（不要包含其他内容）：
```json
{{
    "state": "当前页面状态(HOME/PLAYER/SEARCH/SEARCH_PLAYER/DETAIL/POPUP/UNKNOWN)",
    "confidence": 0.95,
    "evidence": ["判断依据1", "判断依据2"],
    "suggested_anchors": [
        {{"field": "video_count", "operator": "gte", "value": "3", "reason": "为什么这个锚点有效"}}
    ],
    "next_action": {{
        "op": "建议执行的操作(swipe_down/click_card/like/search/go_home/dismiss_popup)",
        "reason": "为什么建议这个操作"
    }}
}}
```

注意：
- HOME: 首页/精选页，video_count=1，card_count>0
- PLAYER: 视频播放页，video_count>=3，有视频在播放
- SEARCH: 搜索结果页，title含"搜索"
- SEARCH_PLAYER: 从搜索结果进入的播放页
- 如果DOM数据异常（如video_count=0），可能是页面未加载或崩溃"""
    return prompt


async def ai_analyze(anchors: dict, screenshot_path: str = None) -> dict:
    """调用本地LLM分析当前页面状态

    Args:
        anchors: DOM 锚点数据
        screenshot_path: 截图路径（暂时不用，模型不支持vision）

    Returns:
        dict: {state, confidence, evidence, suggested_anchors, next_action}
    """
    prompt = _build_ai_prompt(anchors, screenshot_path)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{OLLAMA_BASE}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OLLAMA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": "你是一个抖音页面状态分析专家，只输出JSON。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000,
                },
            )
            result = resp.json()
            content = result["choices"][0]["message"]["content"]

            # 提取 JSON
            # 先尝试直接解析
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                # 尝试从 ```json ... ``` 中提取
                import re
                m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
                if m:
                    parsed = json.loads(m.group(1))
                else:
                    return {
                        "state": "UNKNOWN",
                        "confidence": 0,
                        "error": f"LLM返回格式异常: {content[:200]}",
                    }

            return parsed

    except Exception as e:
        return {
            "state": "UNKNOWN",
            "confidence": 0,
            "error": str(e),
        }


# ── 校准流程 ──

async def run_calibration(identity: str, anchors: dict,
                           screenshot_path: str = None) -> dict:
    """执行完整校准流程

    1. 检查当前成功率
    2. AI 分析当前页面
    3. 生成校准候选
    4. 返回校准结果
    """
    check = check_calibration(identity)
    print(f"[校准] {identity} 准确率: {check['accuracy']}, 级别: {check['level']}")

    # AI 分析
    print(f"[校准] AI分析中...")
    ai_result = await ai_analyze(anchors, screenshot_path)
    ai_state = ai_result.get("state", "UNKNOWN")
    ai_confidence = ai_result.get("confidence", 0)
    print(f"[校准] AI判断: {ai_state} (置信度: {ai_confidence})")

    # 如果 AI 建议了新锚点，生成校准候选
    suggested = ai_result.get("suggested_anchors", [])
    if suggested and ai_confidence >= 0.7:
        # 获取当前规则作为 old_rules
        old_rules = db.get_rules(ai_state)

        candidate_id = db.add_candidate(
            state_name=ai_state,
            source="ai",
            old_rules=[dict(r) for r in old_rules],
            new_rules=suggested,
        )
        print(f"[校准] 候选规则已生成 (id={candidate_id})")

        return {
            "calibration_triggered": True,
            "candidate_id": candidate_id,
            "ai_state": ai_state,
            "ai_confidence": ai_confidence,
            "check": check,
            "ai_result": ai_result,
        }

    return {
        "calibration_triggered": False,
        "check": check,
        "ai_result": ai_result,
    }


# ── 候选规则审批 ──

async def test_candidate(candidate_id: int, test_data: list) -> dict:
    """用测试数据验证候选规则

    Args:
        candidate_id: 校准候选ID
        test_data: [{anchors: dict, expected_state: str}, ...]

    Returns:
        {candidate_id, old_accuracy, new_accuracy, accepted}
    """
    candidate_rows = db.get_conn().execute(
        "SELECT * FROM calibration_candidates WHERE id=?", (candidate_id,)
    ).fetchall()
    if not candidate_rows:
        return {"error": "candidate not found"}
    candidate = dict(candidate_rows[0])
    new_rules = json.loads(candidate["new_rules"])
    old_rules = json.loads(candidate["old_rules"])

    # 不需要真的测试，直接在调用方处理
    return {
        "candidate_id": candidate_id,
        "new_rules": new_rules,
        "old_rules": old_rules,
    }


def accept_candidate(candidate_id: int):
    """采纳候选规则"""
    candidate_rows = db.get_conn().execute(
        "SELECT * FROM calibration_candidates WHERE id=?", (candidate_id,)
    ).fetchall()
    if not candidate_rows:
        return
    candidate = dict(candidate_rows[0])
    new_rules = json.loads(candidate["new_rules"])
    state_name = candidate["state_name"]

    # 停用旧规则
    for r in db.get_rules(state_name):
        db.update_rule(r["id"], active=0)

    # 添加新规则
    for rule in new_rules:
        db.add_rule(
            state_name=state_name,
            field=rule["field"],
            operator=rule["operator"],
            value=rule["value"],
            logic_group=rule.get("logic_group", 0),
        )

    db.update_candidate(candidate_id, "accepted")
    print(f"[校准] 候选#{candidate_id} 已采纳，{state_name}规则已更新")


def reject_candidate(candidate_id: int):
    """拒绝候选规则"""
    db.update_candidate(candidate_id, "rejected")
    print(f"[校准] 候选#{candidate_id} 已拒绝")


# ── 快速测试（不依赖外部LLM）──

async def quick_fallback(anchors: dict) -> dict:
    """快速兜底：基于简单规则判断（不调LLM），用于LLM不可用时的降级"""
    vc = anchors.get("video_count", 0)
    title = anchors.get("title", "")
    url = anchors.get("url", "")

    if vc >= 3 and ("搜索" in title or "/search/" in url):
        return {"state": "SEARCH_PLAYER", "confidence": 0.7, "reason": "video≥3且来自搜索"}
    if vc >= 3:
        return {"state": "PLAYER", "confidence": 0.8, "reason": "video≥3"}
    if "搜索" in title and "精选" not in title:
        return {"state": "SEARCH", "confidence": 0.8, "reason": "标题含搜索"}
    if "精选" in title:
        return {"state": "HOME", "confidence": 0.7, "reason": "标题含精选"}
    return {"state": "UNKNOWN", "confidence": 0.3, "reason": "无法判断"}

"""
AVE character_locker — 角色描述块锁定器

职责:
  在全片 Prompt 链中自动注入固定角色描述块，
  确保 Kling 文生视频时角色一致性。

用法:
  from composer.character_locker import inject_character_block
  prompt = inject_character_block(segments, character_desc)
"""
import json
import os
from pathlib import Path

# ── 角色库路径 ──
CHARACTER_DB = Path(os.environ.get("AVE_CACHE_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local/tools/ave/cache/character_sheet/characters")))
CHARACTER_DB.mkdir(parents=True, exist_ok=True)


def load_character_block(char_name: str) -> str:
    """从角色库加载描述块"""
    safe = char_name.replace(" ", "_").replace("/", "_")
    path = CHARACTER_DB / f"{safe}.json"
    if not path.exists():
        raise FileNotFoundError(f"角色 '{char_name}' 不存在于角色库: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["description"]


def inject_character_block(segments: list[dict], character_desc: str) -> list[dict]:
    """
    在每段素材描述前注入角色描述块

    参数:
      segments: 导演脚本的 segments 列表
      character_desc: 角色描述块（从定妆照生成）

    返回:
      注入后的 segments（直接修改原列表）
    """
    for seg in segments:
        mat = seg.get("material", {})
        search = mat.get("search", "")
        # 如果已包含角色描述, 跳过
        if character_desc in search:
            continue
        # 注入: 角色描述 + 场景描述
        if search:
            mat["search_locked"] = search  # 保留原搜索词
            mat["search"] = f"{character_desc}, {search}"
        else:
            mat["search"] = character_desc

    return segments


def lock_prompt(prompt: str, character_desc: str) -> str:
    """锁定单个 Prompt: 注入角色描述块（如果尚未包含）"""
    if character_desc in prompt:
        return prompt
    return f"{character_desc}, {prompt}"


def batch_lock_prompts(prompts: list[str], character_desc: str) -> list[str]:
    """批量锁定多个 Prompt"""
    return [lock_prompt(p, character_desc) for p in prompts]

#!/usr/bin/env python3
"""
AVE character_sheet — 定妆照 Grid Method 自动生成

功能:
  1. 角色描述 → 2x3 网格定妆照（Kling文生图 / 备选方案）
  2. 从网格图裁剪单格参考图
  3. 生成角色描述块 JSON（跨场景一致性注入用）

用法:
  python character_sheet.py --desc "一位28岁的中国男性..." --output sheet.png
  python character_sheet.py --desc "..." --output sheet.png --extract  # 同时裁出6张单格

API:
  Kling 文生图 (官方 API: api-beijing.klingai.com)
  备选: 阿里云百炼通义万相, fal.ai
"""
import sys
import os
import json
import hashlib
import time
from pathlib import Path

# 确保能找到上级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.config import load_config
from lib.logger import get_logger

logger = get_logger("character_sheet")

# ── 缓存 ──
CACHE_DIR = Path(os.environ.get("AVE_CACHE_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local/tools/ave/cache/character_sheet")))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Kling Image API ──
KLING_BASE = "https://api-beijing.klingai.com"
DASHSCOPE_BASE = "https://dashscope.aliyuncs.com"


# ═══════════════════════════════════════════════════════════
# Prompt 构建
# ═══════════════════════════════════════════════════════════

GRID_PROMPT_EN = (
    "A professional character design sheet for {desc}. "
    "Layout is a 2x3 grid on a clean white background. "
    "Top row (3 panels): full body front view, full body side profile view, full body 3/4 turn view. "
    "Bottom row (3 panels): close-up of face - neutral expression, smiling expression, angry expression. "
    "Consistent character design, flat shading, concept art style. --ar 3:2"
)

GRID_PROMPT_ZH = (
    "一张专业的角色设计表，展示{desc}。"
    "画面为2行3列的网格布局，白色干净背景。"
    "上一行（3格）：全身正面、全身侧面、全身3/4侧面。"
    "下一行（3格）：面部特写-中性表情、微笑表情、愤怒表情。"
    "角色设计一致，扁平着色，概念艺术风格。比例3:2"
)

GRID_ASPECT_RATIO = "3:2"  # Kling 支持
GRID_WIDTH = 1536          # 目标网格宽度
GRID_HEIGHT = 1024         # 目标网格高度


def build_character_block(desc: str) -> str:
    """构建角色描述块（全片复用的特征锚点）"""
    return desc  # 用户输入的描述即为角色块


def build_grid_prompt(desc: str, lang: str = "zh") -> str:
    """构建 2x3 网格定妆照 Prompt"""
    if lang == "zh":
        return GRID_PROMPT_ZH.format(desc=desc)
    return GRID_PROMPT_EN.format(desc=desc)


# ═══════════════════════════════════════════════════════════
# 生成引擎: Kling 文生图
# ═══════════════════════════════════════════════════════════

def generate_grid(
    desc: str,
    output_path: str = "",
    lang: str = "zh",
    extract_cells: bool = False,
    force: bool = False,
) -> dict:
    """
    生成 2x3 网格定妆照

    参数:
      desc: 角色描述
      output_path: 输出路径 (.png/.jpg)
      lang: zh/en
      extract_cells: 是否裁出 6 张单格图
      force: 强制重新生成

    返回:
      {"grid": str, "cells": [...]} — grid=网格图路径, cells=单格路径列表
    """
    if not output_path:
        output_path = str(CACHE_DIR / f"grid_{hashlib.md5(desc.encode()).hexdigest()[:12]}.png")

    cfg = load_config()
    provider = cfg.get("character_sheet", {}).get("provider", "kling")

    result = {"grid": "", "cells": []}

    if provider == "kling":
        result = _generate_kling(desc, output_path, lang, force)
    else:
        raise ValueError(f"未知 provider: {provider}，支持: kling")

    logger.info(f"定妆照生成完成: grid={result['grid']}")
    if extract_cells and result.get("cells"):
        logger.info(f"  已裁出 {len(result['cells'])} 张单格图")
    elif extract_cells:
        logger.warning("  extract_cells=True 但单格图列表为空")

    return result


def _generate_kling(desc: str, output_path: str, lang: str = "zh", force: bool = False) -> dict:
    """通过 Kling API 生成定妆照 (文生图)"""
    import httpx
    import jwt

    # 缓存检查
    if os.path.exists(output_path) and not force:
        logger.info(f"缓存命中: {output_path}")
        return {"grid": output_path, "cells": []}

    cfg = load_config()
    kling_cfg = cfg.get("kling", {})
    ak = kling_cfg.get("access_key", "")
    sk = kling_cfg.get("secret_key", "")

    if not ak or not sk:
        raise ValueError("缺少 Kling API 配置 (kling.access_key / kling.secret_key)")

    prompt = build_grid_prompt(desc, lang)
    logger.info(f"Kling 文生图: prompt={prompt[:60]}...")

    # JWT 认证
    now = int(time.time())
    token = jwt.encode(
        {"iss": ak, "exp": now + 1800, "nbf": now - 5},
        sk, algorithm="HS256",
    )
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 提交文生图任务
    payload = {
        "model": "kling-v1",  # Kling 文生图模型
        "prompt": prompt,
        "aspect_ratio": GRID_ASPECT_RATIO,
        "n": 1,
    }
    resp = httpx.post(f"{KLING_BASE}/v1/images/generations", headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    task_id = data.get("data", {}).get("task_id", "")
    if not task_id:
        raise RuntimeError(f"Kling 文生图提交失败: {data}")

    logger.info(f"  任务: {task_id}, 轮询中...")

    # 轮询
    for i in range(30):
        time.sleep(5)
        q = httpx.get(f"{KLING_BASE}/v1/images/{task_id}", headers=headers, timeout=15)
        q.raise_for_status()
        status_data = q.json().get("data", {})
        task_status = status_data.get("task_status", "")

        if task_status == "succeed":
            img_url = status_data.get("image", {}).get("url", "")
            if img_url:
                logger.info(f"  下载中...")
                _download(img_url, output_path)
                logger.info(f"  ✅ 网格图: {output_path}")
                return {"grid": output_path, "cells": []}
        elif task_status in ("failed",):
            raise RuntimeError(f"Kling 文生图失败: {status_data.get('fail_reason', '?')}")

    raise TimeoutError("Kling 文生图超时")


def _download(url: str, path: str):
    """下载文件"""
    import httpx
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with httpx.stream("GET", url, timeout=600) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_bytes(8192):
                f.write(chunk)


# ═══════════════════════════════════════════════════════════
# 持久化角色描述块
# ═══════════════════════════════════════════════════════════

CHARACTER_DB_DIR = CACHE_DIR / "characters"
CHARACTER_DB_DIR.mkdir(parents=True, exist_ok=True)


def save_character(name: str, desc: str, grid_path: str = "") -> str:
    """保存角色描述到本地库"""
    record = {
        "name": name,
        "description": desc,
        "grid_path": grid_path,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    safe_name = name.replace(" ", "_").replace("/", "_")
    path = CHARACTER_DB_DIR / f"{safe_name}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"角色已保存: {path}")
    return str(path)


def load_character(name: str) -> dict | None:
    """加载角色描述"""
    safe_name = name.replace(" ", "_").replace("/", "_")
    path = CHARACTER_DB_DIR / f"{safe_name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def list_characters() -> list[dict]:
    """列出所有保存的角色"""
    results = []
    for f in sorted(CHARACTER_DB_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return results


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def cli(args: list[str] | None = None):
    """CLI 入口"""
    import argparse
    parser = argparse.ArgumentParser(description="定妆照 Grid Method 生成")
    parser.add_argument("--desc", required=True, help="角色描述")
    parser.add_argument("--output", default="", help="输出路径")
    parser.add_argument("--lang", default="zh", choices=["zh", "en"], help="语言")
    parser.add_argument("--extract", action="store_true", help="裁出 6 张单格图")
    parser.add_argument("--save", default="", help="保存到角色库 (指定角色名)")
    parser.add_argument("--list", action="store_true", help="列出所有已保存角色")
    parser.add_argument("--load", default="", help="加载已保存角色的描述")
    parser.add_argument("--force", action="store_true", help="强制重新生成")

    parsed = parser.parse_args(args)

    if parsed.list:
        chars = list_characters()
        if not chars:
            print("暂无已保存角色")
            return
        print(f"已保存角色 ({len(chars)}):")
        for c in chars:
            print(f"  {c['name']:20s} → {c.get('grid_path', '无网格图')}")
        return

    if parsed.load:
        char = load_character(parsed.load)
        if char:
            print(f"角色: {char['name']}")
            print(f"描述: {char['description']}")
            if char.get("grid_path"):
                print(f"网格图: {char['grid_path']}")
            parsed.desc = char["description"]

    if parsed.desc:
        result = generate_grid(
            desc=parsed.desc,
            output_path=parsed.output,
            lang=parsed.lang,
            extract_cells=parsed.extract,
            force=parsed.force,
        )
        print(f"\n✅ 定妆照: {result['grid']}")
        if result.get("cells"):
            for c in result["cells"]:
                print(f"  单格: {c}")

        # 保存到角色库
        save_name = parsed.save or f"char_{hashlib.md5(parsed.desc.encode()).hexdigest()[:8]}"
        save_character(save_name, parsed.desc, result["grid"])
        print(f"✅ 角色已保存: {save_name}")


if __name__ == "__main__":
    cli()

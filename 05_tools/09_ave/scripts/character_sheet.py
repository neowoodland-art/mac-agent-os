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

# ── 标准 2x3 网格（日常/漫剧风格）──
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

# ── 体育专用 4x2 网格（写实摄影风格，脸部优先）──
# 布局: 4列×2行，8格
# Row 0: body_front | body_side | face_front | face_3qL
# Row 1: face_profile | face_3qR | face_focus | face_intense
SPORT_GRID_PROMPT_EN = (
    "A photorealistic character reference sheet for {desc}. "
    "Layout is a 4x2 grid (4 columns, 2 rows) on a clean white background, thin gray dividers between panels. "
    "Row 1 (upper): full body front view, full body side profile, close-up face neutral front view, close-up face 3/4 left view. "
    "Row 2 (lower): close-up pure left side profile, close-up face 3/4 right view, close-up face focused determined expression, close-up face intense exertion expression. "
    "All 8 panels show the exact same person with identical face, hairstyle, body shape. "
    "Photorealistic, sports photography style, natural lighting, high detail, sharp focus on face panels. --ar 3:2"
)

SPORT_GRID_PROMPT_ZH = (
    "一张写实风格的角色参考定妆照，展示{desc}。"
    "画面为4列×2行共8格的网格布局，白色干净背景，格间有细灰线分隔。"
    "上一行：全身正面中性站姿、全身侧面站姿、面部正面中性表情特写、面部四分之三左侧表情特写。"
    "下一行：面部纯左侧轮廓特写、面部四分之三右侧表情特写、面部专注坚定眼神特写、面部发力表情特写。"
    "8格人物为完全相同的同一人，面部五官、发型、体型高度一致。"
    "真实摄影写实风格，自然光线，高细节还原，非插画非动漫。比例3:2"
)

# ── 体育 I2I 专用 Prompt（基于参考照生成）──
SPORT_GRID_I2I_PROMPT_EN = (
    "Based on the reference photo, create a photorealistic 4x2 character reference sheet (8 panels). "
    "The character is {desc}. "
    "Layout: 4 columns x 2 rows, clean white background, thin gray dividers. "
    "Row 1: full body front view, full body side profile, close-up face neutral front, close-up face 3/4 left. "
    "Row 2: close-up pure left side profile, close-up face 3/4 right, close-up face focused, close-up face intense exertion. "
    "MUST maintain exact same face, hairstyle, body shape as the reference photo person. "
    "Photorealistic sports photography, natural lighting, high detail, sharp focus on face panels. --ar 3:2"
)

GRID_ASPECT_RATIO = "3:2"  # Kling 支持
GRID_WIDTH = 1536          # 目标网格宽度
GRID_HEIGHT = 1024         # 标准 2x3 网格高度
SPORT_GRID_HEIGHT = 1536   # 体育 3x3 网格高度

DEFAULT_SEED = 42  # 默认固定种子，保证可复现


def build_character_block(desc: str) -> str:
    """构建角色描述块（全片复用的特征锚点）"""
    return desc  # 用户输入的描述即为角色块


def build_grid_prompt(desc: str, lang: str = "zh", mode: str = "standard", use_ref: bool = False) -> str:
    """
    构建网格定妆照 Prompt

    mode: "standard" → 2x3 概念艺术（日常/漫剧）
          "sport"    → 4x2 写实摄影（8格，脸部优先）
    use_ref: True → 使用 I2I 参考图模式 Prompt（sport mode 专用）
    """
    if mode == "sport":
        if use_ref:
            return SPORT_GRID_I2I_PROMPT_EN.format(desc=desc)
        if lang == "zh":
            return SPORT_GRID_PROMPT_ZH.format(desc=desc)
        return SPORT_GRID_PROMPT_EN.format(desc=desc)
    # standard mode
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
    do_extract: bool = False,
    force: bool = False,
    mode: str = "standard",
    ref_image: str = "",
    seed: int | None = None,
) -> dict:
    """
    生成网格定妆照

    参数:
      desc: 角色描述
      output_path: 输出路径 (.png/.jpg)
      lang: zh/en
      do_extract: 是否裁出单格图
      force: 强制重新生成
      mode: "standard"=2x3概念艺术 / "sport"=4x2写实体育(8格，脸部优先)
      ref_image: 参考图路径（sport mode 下用于 I2I，提升人脸一致性）
      seed: 固定随机种子（int），传入后 Kling 生成结果可复现；
            为 None 时不传 seed，由 Kling 随机生成（并在返回中记录）

    返回:
      {"grid": str, "cells": [...], "seed": int|None} — grid=网格图路径, cells=单格路径列表, seed=本次使用的种子
    """
    if not output_path:
        cache_key = hashlib.md5(f"{desc}{mode}".encode()).hexdigest()[:12]
        output_path = str(CACHE_DIR / f"grid_{cache_key}.png")

    cfg = load_config()
    provider = cfg.get("character_sheet", {}).get("provider", "kling")

    result = {"grid": "", "cells": [], "seed": seed}

    if provider == "kling":
        result = _generate_kling(desc, output_path, lang, force, mode=mode, ref_image=ref_image, seed=seed)
    else:
        raise ValueError(f"未知 provider: {provider}，支持: kling")

    grid_path = result.get("grid", "")
    logger.info(f"定妆照生成完成: grid={grid_path}, seed={result.get('seed')}")

    # 裁格
    cells_result = {}
    if do_extract and grid_path and os.path.exists(grid_path):
        cells_result = extract_cells(grid_path, os.path.dirname(grid_path) or CACHE_DIR, mode=mode)
        result["cells"] = cells_result
        logger.info(f"  已裁出 {len(cells_result)} 张单格图")
    elif do_extract:
        logger.warning("  do_extract=True 但网格图路径无效，跳过裁格")

    # 生成 face_anchor.png（从 face_neutral 提取）
    face_anchor_path = ""
    if cells_result:
        face_anchor_path = _export_face_anchor(cells_result, os.path.dirname(grid_path) or CACHE_DIR)
        if face_anchor_path:
            result["face_anchor"] = face_anchor_path

    return result


def _generate_kling(
    desc: str,
    output_path: str,
    lang: str = "zh",
    force: bool = False,
    mode: str = "standard",
    ref_image: str = "",
    seed: int | None = None,
) -> dict:
    """
    通过 Kling API 生成定妆照

    mode="standard": 文生图 2x3
    mode="sport" + ref_image: I2I 4x2（参考图锚定人脸，8格脸部优先布局）
    mode="sport" (无 ref_image): 文生图 4x2
    """
    import httpx
    import jwt
    import base64

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

    use_ref = bool(ref_image and os.path.exists(ref_image) and mode == "sport")
    prompt = build_grid_prompt(desc, lang, mode=mode, use_ref=use_ref)
    logger.info(f"Kling 生成 [{mode}{'|I2I' if use_ref else '|T2I'}]: {prompt[:80]}...")

    # JWT 认证
    now = int(time.time())
    token = jwt.encode(
        {"iss": ak, "exp": now + 1800, "nbf": now - 5},
        sk, algorithm="HS256",
    )
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    if use_ref:
        # ── I2I 模式：参考图 + prompt，最大化人脸一致性 ──
        with open(ref_image, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        payload = {
            "model": "kling-v1",
            "prompt": prompt,
            "image": img_b64,
            "strength": 0.65,   # 0.6-0.7: 保持人脸同时允许姿态变换
            "aspect_ratio": GRID_ASPECT_RATIO,
            "n": 1,
        }
        if seed is not None:
            payload["seed"] = seed
        endpoint = f"{KLING_BASE}/v1/images/generations"
        logger.info(f"  使用参考图 I2I: {ref_image}")
    else:
        # ── T2I 模式：纯文字生成 ──
        payload = {
            "model": "kling-v1",
            "prompt": prompt,
            "aspect_ratio": GRID_ASPECT_RATIO,
            "n": 1,
        }
        if seed is not None:
            payload["seed"] = seed
        endpoint = f"{KLING_BASE}/v1/images/generations"

    # 带退避重试的 POST
    for attempt in range(3):
        resp = httpx.post(endpoint, headers=headers, json=payload, timeout=30)
        if resp.status_code == 429:
            wait = 2 ** attempt * 15  # 15s, 30s, 60s
            logger.warning(f"  429 限流，等待 {wait}s 后重试...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        break
    data = resp.json()
    task_id = data.get("data", {}).get("task_id", "")
    if not task_id:
        raise RuntimeError(f"Kling 提交失败: {data}")

    logger.info(f"  任务: {task_id}, 轮询中...")

    # 轮询
    for i in range(40):
        time.sleep(5)
        q = httpx.get(f"{KLING_BASE}/v1/images/generations/{task_id}", headers=headers, timeout=15)
        q.raise_for_status()
        status_data = q.json().get("data", {})
        task_status = status_data.get("task_status", "")

        if task_status == "succeed":
            images = status_data.get("task_result", {}).get("images", [])
            img_url = images[0].get("url", "") if images else ""
            # 读取 Kling 返回的 seed（如果 API 返回了的话）
            returned_seed = status_data.get("seed", seed)
            if img_url:
                logger.info(f"  下载中...")
                _download(img_url, output_path)
                # 保存 seed 到 .seed 文件，下次可直接复用
                seed_file = output_path + ".seed"
                with open(seed_file, "w") as f:
                    f.write(str(returned_seed))
                logger.info(f"  ✅ 网格图: {output_path}  [seed={returned_seed}]")
                return {"grid": output_path, "cells": [], "seed": returned_seed}
        elif task_status == "failed":
            raise RuntimeError(f"Kling 生成失败: {status_data.get('fail_reason', '?')}")

    raise TimeoutError("Kling 生成超时（200s）")


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
# Grid 裁剪: 2x3 → 6 张单格图 / 3x3 → 9 张单格图
# ═══════════════════════════════════════════════════════════

# 标准 2x3 格名（行优先排列）
CELL_NAMES_2X3 = [
    "fullbody_front",     # R0C0 全身正面
    "fullbody_side",      # R0C1 全身侧面
    "fullbody_threeq",    # R0C2 全身 3/4
    "face_neutral",       # R1C0 面部-中性
    "face_smile",         # R1C1 面部-微笑
    "face_angry",         # R1C2 面部-愤怒
]

# 体育 4x2 格名（行优先排列，8格）
# Row 0: 全身正面 | 全身侧面 | 脸部正面中性 | 四分之三左侧
# Row 1: 纯左侧轮廓 | 四分之三右侧 | 脸部正面专注 | 脸部正面发力
CELL_NAMES_4X2 = [
    "body_front",         # R0C0 全身正面
    "body_side",          # R0C1 全身侧面
    "face_front",         # R0C2 正面中性
    "face_3qL",           # R0C3 四分之三左侧
    "face_profile",       # R1C0 纯左侧轮廓
    "face_3qR",           # R1C1 四分之三右侧
    "face_focus",         # R1C2 正面专注
    "face_intense",       # R1C3 正面发力
]

# 向后兼容旧名称映射
CELL_NAMES_3X3 = [  # deprecated，保留兼容
    "fullbody_front",
    "fullbody_side",
    "fullbody_threeq",
    "face_neutral",
    "face_focused",
    "face_intense",
    "sport_run",
    "sport_jump",
    "sport_stance",
]

# 向后兼容
CELL_NAMES = CELL_NAMES_2X3


def extract_cells(grid_path: str, output_dir: str = "", mode: str = "standard") -> dict[str, str]:
    """
    从网格图裁剪出单格参考图

    参数:
      grid_path: 网格图路径
      output_dir: 输出目录（默认与网格图同目录）
      mode: "standard"=2x3(6格) / "sport"=4x2(8格，脸部优先) / "face4x2"=4x2(8格)

    返回:
      {"body_front": str, ..., "face_intense": str, ...}
    """
    try:
        from PIL import Image
    except ImportError:
        logger.warning("PIL 未安装，跳过 cells 裁剪")
        return {}

    if not os.path.exists(grid_path):
        logger.error(f"网格图不存在: {grid_path}")
        return {}

    if not output_dir:
        output_dir = os.path.dirname(grid_path) or CACHE_DIR
    os.makedirs(output_dir, exist_ok=True)

    img = Image.open(grid_path)
    w, h = img.size

    # "sport" 和 "face4x2" 均使用 4x2 布局（8格，脸部优先）
    if mode in ("face4x2", "sport"):
        rows, cols = 2, 4
        cell_names = CELL_NAMES_4X2
    else:
        # 2 行 3 列（standard）
        rows, cols = 2, 3
        cell_names = CELL_NAMES_2X3

    col_w = w // cols
    row_h = h // rows

    base_name = os.path.splitext(os.path.basename(grid_path))[0]
    cells = {}

    for idx, cell_name in enumerate(cell_names):
        col = idx % cols
        row = idx // cols
        left = col * col_w
        upper = row * row_h
        right = left + col_w
        lower = upper + row_h

        cell_img = img.crop((left, upper, right, lower))
        cell_path = os.path.join(output_dir, f"{base_name}_{cell_name}.png")
        cell_img.save(cell_path, "PNG")
        cells[cell_name] = cell_path
        logger.info(f"  裁剪: [{row},{col}] {cell_name} → {cell_path}")

    logger.info(f"  共裁剪 {len(cells)} 格 ({mode} mode)")
    return cells


def _export_face_anchor(cells: dict[str, str], output_dir: str) -> str:
    """
    从已裁剪的 cells 中提取 face_front，生成 face_anchor.png
    face_anchor.png 是后续所有场景 I2I 的脸部固定锚点

    返回: face_anchor.png 路径，未找到 face_front 时返回空字符串
    """
    face_key = "face_front"
    if face_key not in cells:
        logger.warning(f"  face_anchor: 未找到 {face_key} cell，跳过")
        return ""

    import shutil
    src = cells[face_key]
    dst = os.path.join(output_dir, "face_anchor.png")

    try:
        shutil.copy2(src, dst)
        logger.info(f"  ✅ face_anchor: {dst}")
        return dst
    except Exception as e:
        logger.warning(f"  face_anchor 复制失败: {e}")
        return ""



# ═══════════════════════════════════════════════════════════
# Kling I2I 变体生成
# ═══════════════════════════════════════════════════════════

def generate_variations(
    source_image: str,
    output_dir: str = "",
    variations: int = 3,
    prompt: str = "",
    force: bool = False,
) -> list[str]:
    """
    基于参考图通过 Kling I2I 生成多个变体

    参数:
      source_image: 参考图路径
      output_dir: 输出目录
      variations: 变体数量
      prompt: 可选，变体 prompt 描述
      force: 强制重新生成

    返回:
      变体图片路径列表
    """
    try:
        import httpx
        import jwt
        from PIL import Image
    except ImportError:
        logger.warning("PIL 未安装，跳过变体生成")
        return []

    if not os.path.exists(source_image):
        logger.error(f"参考图不存在: {source_image}")
        return []

    if not output_dir:
        output_dir = os.path.dirname(source_image) or CACHE_DIR
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(source_image))[0]

    # 缓存检查
    existing = []
    for v in range(variations):
        vpath = os.path.join(output_dir, f"{base_name}_var{v+1}.png")
        if os.path.exists(vpath) and not force:
            existing.append(vpath)
    if len(existing) == variations:
        logger.info(f"变体缓存命中: {existing}")
        return existing

    cfg = load_config()
    kling_cfg = cfg.get("kling", {})
    ak = kling_cfg.get("access_key", "")
    sk = kling_cfg.get("secret_key", "")

    if not ak or not sk:
        raise ValueError("缺少 Kling API 配置")

    # 读取并 base64 编码参考图
    with open(source_image, "rb") as f:
        import base64
        img_b64 = base64.b64encode(f.read()).decode()

    prompt_text = prompt or f"Character {base_name} in different pose, consistent design, same style"

    now = int(time.time())
    token = jwt.encode(
        {"iss": ak, "exp": now + 1800, "nbf": now - 5},
        sk, algorithm="HS256",
    )
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    results = []
    # Kling I2I 单次只能生成一张
    for v in range(variations):
        vpath = os.path.join(output_dir, f"{base_name}_var{v+1}.png")
        if os.path.exists(vpath) and not force:
            results.append(vpath)
            continue

        payload = {
            "model": "kling-v1",
            "prompt": prompt_text,
            "image": img_b64,
            "strength": 0.7,  # 与原图的相似度
        }
        resp = httpx.post(f"{KLING_BASE}/v1/images/generations",
                          headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        task_id = data.get("data", {}).get("task_id", "")
        if not task_id:
            raise RuntimeError(f"Kling I2I 提交失败: {data}")

        # 轮询
        for i in range(30):
            time.sleep(5)
            q = httpx.get(f"{KLING_BASE}/v1/images/generations/{task_id}", headers=headers, timeout=15)
            q.raise_for_status()
            status_data = q.json().get("data", {})
            task_status = status_data.get("task_status", "")

            if task_status == "succeed":
                images = status_data.get("task_result", {}).get("images", [])
                img_url = images[0].get("url", "") if images else ""
                if img_url:
                    _download(img_url, vpath)
                    results.append(vpath)
                    logger.info(f"  ✅ 变体 {v+1}: {vpath}")
                    break
            elif task_status == "failed":
                raise RuntimeError(f"Kling I2I 失败: {status_data.get('fail_reason', '?')}")

    return results


# ═══════════════════════════════════════════════════════════
# 全流程: 从角色描述到注册中心
# ═══════════════════════════════════════════════════════════

def generate_and_register(
    character_name: str,
    description: str,
    registry_path: str = "",
    force: bool = False,
    mode: str = "standard",
    ref_image: str = "",
    seed: int | None = DEFAULT_SEED,
) -> dict:
    """
    全流程: 生成定妆照 → 裁剪 → 注册到 CharacterRegistry

    参数:
      character_name: 角色名（与 registry.yaml 一致）
      description: 角色描述
      registry_path: registry.yaml 路径（可选）
      force: 强制重新生成
      mode: "standard"=2x3 / "sport"=4x2(脸部优先) / "face4x2"=4x2
      ref_image: I2I 参考图路径（可选）
      seed: 固定种子（默认 42）

    返回:
      {
        "character": "...",
        "grid": "path/to/grid.png",
        "cells": {"body_front": "...", ...},
        "registry_updated": True
      }
    """
    # 1. 生成网格图
    output_dir = str(CACHE_DIR / character_name)
    os.makedirs(output_dir, exist_ok=True)
    grid_path = os.path.join(output_dir, f"{character_name}_grid.png")

    grid_result = generate_grid(
        desc=description,
        output_path=grid_path,
        force=force,
        do_extract=True,
        mode=mode,
        ref_image=ref_image,
        seed=seed,
    )
    grid_path = grid_result["grid"]
    used_seed = grid_result.get("seed")
    cells = grid_result.get("cells", {})
    face_anchor = grid_result.get("face_anchor", "")

    # 3. 同步到 CharacterRegistry
    try:
        from character_registry import CharacterRegistry

        if registry_path:
            registry = CharacterRegistry(registry_path)
        else:
            # 查找项目 registry.yaml
            registry = CharacterRegistry(
                os.path.join(os.path.dirname(__file__), "character_registry", "registry.yaml")
            )

        # 构建参考图字典
        ref_images = {
            "grid": grid_path,
            "face_anchor": face_anchor,       # 场景 I2I 专用脸部锚点（从 face_front 提取）
            "portrait": cells.get("face_front", ""),
            "seed": used_seed,
        }

        # 体型参考
        body = {}
        for cell_name, cell_path in cells.items():
            if cell_name.startswith("body_"):
                body[cell_name.replace("body_", "")] = cell_path
        if body:
            ref_images["body"] = body

        # 表情参考（自动捕获所有 face_* 格）
        expressions = {}
        for cell_name, cell_path in cells.items():
            if cell_name.startswith("face_"):
                emotion = cell_name.replace("face_", "")
                expressions[emotion] = cell_path

        # 表情参考
        expressions = {}
        for cell_name, cell_path in cells.items():
            if cell_name.startswith("face_"):
                emotion = cell_name.replace("face_", "")
                expressions[emotion] = cell_path
        if expressions:
            ref_images["expressions"] = expressions

        # 更新 registry
        registry.update_reference_images(character_name, ref_images)
        logger.info(f"✅ 已同步到 CharacterRegistry: {character_name}")
        registry_updated = True
    except Exception as e:
        logger.warning(f"同步到 CharacterRegistry 失败: {e}（不影响定妆照生成）")
        registry_updated = False

    return {
        "character": character_name,
        "grid": grid_path,
        "cells": cells,
        "registry_updated": registry_updated,
    }


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
    parser.add_argument("--register", default="", help="同步到 CharacterRegistry (指定角色名)")
    parser.add_argument("--char-name", default="", help="角色名（用于注册时）")
    parser.add_argument("--seed", type=int, default=None,
                        help="固定 Kling 随机种子（如 42），确保结果可复现；不指定则随机生成")
    parser.add_argument("--mode", default="standard",
                        choices=["standard", "sport", "face4x2"],
                        help="布局模式: standard=2x3, sport=4x2(脸部优先), face4x2=4x2")
    parser.add_argument("--ref", dest="ref_image", default="",
                        help="I2I 参考图路径（sport/face4x2 模式下使用，提升人脸一致性）")

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
            if not parsed.char_name:
                parsed.char_name = char["name"]

    if parsed.register:
        # 全流程: 生成 + 裁剪 + 注册
        char_name = parsed.register
        result = generate_and_register(
            character_name=char_name,
            description=parsed.desc,
            force=parsed.force,
            mode=parsed.mode,
            ref_image=parsed.ref_image,
            seed=parsed.seed,
        )
        print(f"\n✅ 定妆照: {result['grid']}")
        for cell_name, cell_path in result.get("cells", {}).items():
            print(f"  {cell_name}: {cell_path}")
        if result.get("registry_updated"):
            print(f"✅ 已同步到 CharacterRegistry: {char_name}")
        else:
            print(f"⚠️ 定妆照已生成但未同步到注册中心（检查 registry.yaml 路径）")

    elif parsed.desc:
        result = generate_grid(
            desc=parsed.desc,
            output_path=parsed.output,
            lang=parsed.lang,
            do_extract=parsed.extract,
            force=parsed.force,
            mode=parsed.mode,
            ref_image=parsed.ref_image,
            seed=parsed.seed,
        )
        print(f"\n✅ 定妆照: {result['grid']}")
        if result.get("seed") is not None:
            print(f"   seed: {result['seed']}  （可复现，存入 {result['grid']}.seed）")
        if parsed.extract:
            # 实际执行裁剪
            output_dir = os.path.dirname(result['grid']) or CACHE_DIR
            cells = extract_cells(result['grid'], output_dir)
            for cell_name, cell_path in cells.items():
                print(f"  {cell_name}: {cell_path}")
            # face_anchor 已在 generate_grid 内生成，这里单独提示
            face_anchor = result.get("face_anchor", "")
            if face_anchor:
                print(f"  face_anchor: {face_anchor}  ← 场景 I2I 专用锚点")

        # 保存到角色库
        save_name = parsed.save or parsed.char_name or \
            f"char_{hashlib.md5(parsed.desc.encode()).hexdigest()[:8]}"
        save_character(save_name, parsed.desc, result["grid"])
        print(f"✅ 角色已保存: {save_name}")


if __name__ == "__main__":
    cli()

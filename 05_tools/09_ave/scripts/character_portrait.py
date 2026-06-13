"""
AVE character_portrait — 逐帧参考链定妆照生成（v2.0 重写）

核心原则:
  ⚠️ 前一轮的问题：所有角度共用同一张基准图作 I2I 参考 → 角色漂移 + 方向混乱
  ✅ 本方案：逐帧参考链（Sequential Reference Chain）
     图1(正面T2I) → 作为图2参考 → 图2(右半侧I2I) → 作为图3参考 → 图3(右侧面I2I) → 作为图4参考 → 图4(背面I2I)
     每一步只做"小幅姿态变化"，最大限度保持角色一致性

流程:
  Phase 1: Kling T2I (kling-v3, 高质量) 生成正面全身基准图
  Phase 2: 逐帧 I2I 参考链，小步幅递增
             图1(正面) → 图2(右侧45°半侧面, I2I参考图1)
             图2(右侧45°) → 图3(纯右侧面, I2I参考图2)
             图3(右侧面) → 图4(背面, I2I参考图3)
  Phase 3: 注册到 CharacterRegistry（face_anchor + 各角度图）

参考强度逐级递增：0.70 → 0.75 → 0.70（近端参考 = 更高一致性）

用法:
  python character_portrait.py --character "陆晨晖" --desc "..."

API调用:
  POST /api/characters/generate-portrait
  {"character_name": "陆晨晖", "description": "...", "force": false}
"""

import sys
import os
import json
import time
import base64
import hashlib
from pathlib import Path

path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, path)

from lib.config import load_config
from lib.logger import get_logger

logger = get_logger('character_portrait')

environ = os.environ.get
home = os.path.expanduser('~')

# ── 缓存目录 ──
CACHE_DIR = environ(
    'AVE_CACHE_DIR',
    os.path.join(home, 'workbuddy-agent-os/agent-local/tools/ave/cache/character_portrait'),
)
os.makedirs(CACHE_DIR, exist_ok=True)

# ── Kling API ──
KLING_BASE = 'https://api-beijing.klingai.com'
BASELINE_MODEL = 'kling-v3'
ANGLE_MODEL = 'kling-v1'
DEFAULT_SEED = 42

# Phase 2 参考链强度（逐级递增保持一致性）
REF_STRENGTH_CHAIN = (0.70, 0.75, 0.70)

# Phase 1: 基准图提示词模板
BASELINE_PROMPT_TEMPLATE = (
    '一张超写实全身人像定妆照，必须正面朝向镜头，如证件照构图。'
    '双脚自然分开与肩同宽，双手自然垂于身体两侧，面部正对相机，双耳左右对称可见。'
    '严禁身体转向侧面或半侧面，不得有角度偏移。'
    '{desc}'
    '干净的浅灰色无缝影棚背景，左右双柔光箱对称布光，面部无阴影，'
    '超高清8k，真实皮肤纹理，织物细节，发丝清晰可见，专业人像摄影质感。'
)

# Phase 2: 逐帧参考链定义
# 每帧: key(存储key), label(显示名), ref_source(参考图来源), strength(I2I强度), prompt(生成提示词)
ANGLE_CHAIN = [
    {
        'key': 'right_three_quarter',
        'label': '右侧45°半侧面',
        'ref_source': 'baseline',
        'strength': 0.70,
        'prompt': (
            '与参考图完全相同的人物。全身镜头，四分之三右侧面，身体转向右侧约45度。'
            '面部朝向镜头右前方，展现右侧面部特征。站姿放松自然。'
            '保持完全一致的着装、配饰、发型和面部特征。'
            '浅灰色影棚背景，超写实，专业人像布光，真实皮肤纹理，高清细节。'
        ),
    },
    {
        'key': 'right_side',
        'label': '纯右侧面',
        'ref_source': 'right_three_quarter',
        'strength': 0.75,
        'prompt': (
            '与参考图完全相同的人物。全身镜头，纯右侧面视角，人物面向右侧90度。'
            '镜头从人物正右侧拍摄，展现鼻梁、嘴唇和下颌线的侧面轮廓。'
            '着装与参考图完全一致，发型侧面层次清晰可见。'
            '浅灰色影棚背景，超写实，轮廓清晰，高清，侧光勾勒面部轮廓。'
        ),
    },
    {
        'key': 'back',
        'label': '背面',
        'ref_source': 'right_side',
        'strength': 0.70,
        'prompt': (
            '与参考图完全相同的人物。全身镜头，人物背对镜头，从正后方拍摄。'
            '展现后脑勺的发型层次感，肩背和腰线的服装贴合线条。'
            '从背面可见服装背面的褶皱纹理和鞋子的后跟细节。'
            '浅灰色影棚背景，超写实，真实皮肤纹理，高清8k。'
        ),
    },
]


# ══════════════════════════════════════════════════════
# Kling 辅助工具
# ══════════════════════════════════════════════════════

def _get_kling_credentials() -> dict:
    """从 AVE 配置加载 Kling API 凭据。

    Returns:
        {"access_key": str, "secret_key": str}

    Raises:
        ValueError: 缺少配置
    """
    cfg = load_config()
    kling_cfg = cfg.get('kling', {})
    ak = kling_cfg.get('access_key', '')
    sk = kling_cfg.get('secret_key', '')
    if not ak or not sk:
        raise ValueError('缺少 Kling API 配置 (kling.access_key / kling.secret_key)')
    return {'access_key': ak, 'secret_key': sk}


def _jwt_token(ak: str, sk: str) -> str:
    """生成 Kling JWT 认证 token。

    Args:
        ak: Access Key
        sk: Secret Key

    Returns:
        JWT token 字符串
    """
    try:
        import jwt as pyjwt
    except ImportError:
        raise ImportError('需要 PyJWT 库: pip install pyjwt')
    now = int(time.time())
    return pyjwt.encode(
        {'iss': ak, 'exp': now + 1800, 'nbf': now},
        sk,
        algorithm='HS256',
    )


def _download(url: str, path: str):
    """下载文件。

    Args:
        url: 下载 URL
        path: 保存路径
    """
    import httpx
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with httpx.stream('GET', url, timeout=600) as r:
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_bytes(8192):
                f.write(chunk)


# ══════════════════════════════════════════════════════
# Kling T2I / I2I 核心
# ══════════════════════════════════════════════════════

def _t2i(
    image_path: str,
    prompt: str,
    seed: int = 0,
    model: str = 'kling-v3',
    force: bool = False,
) -> dict:
    """Kling 文生图 (T2I)。

    参数:
        model: 默认 BASELINE_MODEL (kling-v3)，可覆盖
        force: 强制重新生成，跳过缓存

    返回: {"path": str, "seed": int}
    """
    # 检查缓存
    if not force and os.path.exists(image_path):
        seed_file = f'{image_path}.seed'
        used_seed = seed
        if os.path.exists(seed_file):
            used_seed = int(open(seed_file).read().strip())
        logger.info(f'T2I 缓存命中: {image_path}')
        return {'path': image_path, 'seed': used_seed}

    from lib.config import load_config
    import httpx
    import jwt

    # 鉴权
    creds = _get_kling_credentials()
    ak = creds['access_key']
    sk = creds['secret_key']
    token = _jwt_token(ak, sk)
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    # 请求
    model_name = model or BASELINE_MODEL
    payload = {
        'model': model_name,
        'prompt': prompt,
        'aspect_ratio': '9:16',
        'n': 1,
    }
    if seed:
        payload['seed'] = seed

    # 提交
    for attempt in range(3):
        try:
            resp = httpx.post(
                f'{KLING_BASE}/v1/images/generations',
                headers=headers,
                json=payload,
                timeout=30,
            )
            if resp.status_code == 429:
                wait = 15 * (attempt + 1)
                logger.warning(f'  429 限流，等待 {wait}s...')
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            task_id = data.get('data', {}).get('task_id', '')
            if not task_id:
                raise RuntimeError(f'Kling T2I 提交失败: {data}')
            break
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(5)
    else:
        raise RuntimeError('Kling T2I 提交失败（重试耗尽）')

    # 轮询
    for i in range(40):
        time.sleep(5)
        try:
            q = httpx.get(
                f'{KLING_BASE}/v1/images/generations/{task_id}',
                headers=headers,
                timeout=30,
            )
            q.raise_for_status()
            status_data = q.json()['data']
            task_status = status_data.get('task_status', '')

            if task_status == 'succeed':
                images = status_data.get('task_result', {}).get('images', [])
                if not images:
                    raise RuntimeError('Kling T2I 成功但无图像')
                img_url = images[0].get('url', '')
                returned_seed = images[0].get('seed', seed)

                # 下载
                logger.info(f'  T2I 完成，下载中...')
                _download(img_url, image_path)

                # 写种子文件
                with open(f'{image_path}.seed', 'w') as f:
                    f.write(str(returned_seed))

                logger.info(f'  ✅ 基准图: {image_path} [seed={returned_seed}]')
                return {'path': image_path, 'seed': returned_seed}

            elif task_status == 'failed':
                reason = status_data.get('fail_reason', '?')
                raise RuntimeError(f'T2I 生成失败: {reason}')

        except Exception as e:
            if '轮询' in str(e):
                logger.warning(f'  {e}')
                break
            logger.warning(f'  轮询异常: {e}')
            time.sleep(5)

    raise TimeoutError('T2I 生成超时（200s）')


def _i2i(
    output_path: str,
    ref_image: str,
    prompt: str,
    seed: int = 0,
    strength: float = 0.65,
    model: str = 'kling-v1',
    force: bool = False,
) -> dict:
    """Kling 图生图 (I2I)，基于参考图生成。

    参数:
        strength: 参考强度，默认 0.65
        model: 模型，默认 ANGLE_MODEL (kling-v1)
        force: 强制重新生成

    返回: {"path": str, "seed": int}
    """
    # 检查缓存
    if not force and os.path.exists(output_path):
        seed_file = f'{output_path}.seed'
        used_seed = seed
        if os.path.exists(seed_file):
            used_seed = int(open(seed_file).read().strip())
        logger.info(f'I2I 缓存命中: {output_path}')
        return {'path': output_path, 'seed': used_seed}

    import httpx
    import jwt

    # 鉴权
    creds = _get_kling_credentials()
    ak = creds['access_key']
    sk = creds['secret_key']
    token = _jwt_token(ak, sk)
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    # 读取参考图
    if not os.path.exists(ref_image):
        raise FileNotFoundError(f'I2I 参考图不存在: {ref_image}')
    with open(ref_image, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    model_name = model or ANGLE_MODEL
    ref_strength = strength or 0.7
    payload = {
        'model': model_name,
        'prompt': prompt,
        'image': img_b64,
        'strength': ref_strength,
        'aspect_ratio': '9:16',
        'n': 1,
    }
    if seed:
        payload['seed'] = seed

    # 提交
    for attempt in range(3):
        try:
            resp = httpx.post(
                f'{KLING_BASE}/v1/images/generations',
                headers=headers,
                json=payload,
                timeout=30,
            )
            if resp.status_code == 429:
                wait = 15 * (attempt + 1)
                logger.warning(f'  429 限流，等待 {wait}s...')
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            task_id = data.get('data', {}).get('task_id', '')
            if not task_id:
                raise RuntimeError(f'Kling I2I 提交失败: {data}')
            break
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(5)
    else:
        raise RuntimeError('Kling I2I 提交失败（重试耗尽）')

    # 轮询
    for i in range(40):
        time.sleep(5)
        try:
            q = httpx.get(
                f'{KLING_BASE}/v1/images/generations/{task_id}',
                headers=headers,
                timeout=30,
            )
            q.raise_for_status()
            status_data = q.json()['data']
            task_status = status_data.get('task_status', '')

            if task_status == 'succeed':
                images = status_data.get('task_result', {}).get('images', [])
                if not images:
                    raise RuntimeError('Kling I2I 成功但无图像')
                img_url = images[0].get('url', '')
                returned_seed = images[0].get('seed', seed)

                # 下载
                logger.info(f'  I2I 完成，下载中...')
                _download(img_url, output_path)

                # 写种子文件
                with open(f'{output_path}.seed', 'w') as f:
                    f.write(str(returned_seed))

                logger.info(f'  ✅ 角度图: {output_path} [seed={returned_seed}]')
                return {'path': output_path, 'seed': returned_seed}

            elif task_status == 'failed':
                reason = status_data.get('fail_reason', '?')
                raise RuntimeError(f'I2I 生成失败: {reason}')

        except Exception as e:
            if '轮询' in str(e):
                logger.warning(f'  {e}')
                break
            logger.warning(f'  轮询异常: {e}')
            time.sleep(5)

    raise TimeoutError('I2I 生成超时（200s）')


# ══════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════

def generate_baseline(
    description: str,
    char_name: str,
    force: bool = False,
    seed: int = 0,
    ref_image: str = '',
) -> dict:
    """Phase 1: 生成正面全身基准图。

    策略（v2.2）:
      1. 优先用真实照片 ref_image 做 I2I（真实照片→影棚风格，强度 0.85 保留面部）
      2. 无参考照时回退 T2I (kling-v3)

    参数:
      ref_image: 真实参考照路径。有则走 I2I，无则走 T2I

    返回:
      {"baseline": "path/to/baseline.png", "seed": int, "method": "i2i|t2i"}
    """
    output_dir = os.path.join(CACHE_DIR, char_name)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    baseline_path = os.path.join(output_dir, 'baseline.png')
    seed_file = f'{baseline_path}.seed'

    # 缓存检查
    if not force and os.path.exists(baseline_path):
        cached_seed = seed
        if os.path.exists(seed_file):
            cached_seed = int(open(seed_file).read().strip())
        logger.info(f'基准图缓存命中: {baseline_path}')
        return {'baseline': baseline_path, 'seed': cached_seed, 'method': 'cache'}

    if ref_image and os.path.exists(ref_image):
        # 策略 1: 真实照片 I2I → 影棚风格基准图
        logger.info(f'=== Phase 1: 参考照 I2I 生成基准图 ({char_name}) ===')
        logger.info(f'  参考照: {ref_image}')

        prompt = (
            '与参考照片完全相同的人物。全身镜头，正面站立直视镜头，如证件照构图。'
            '浅灰色无缝影棚背景，左右双柔光箱对称布光，面部无阴影。'
            '超高清8k，真实皮肤纹理，织物细节。'
        )

        result = _i2i(
            baseline_path,
            ref_image,
            prompt,
            seed=seed,
            strength=0.85,
            model=ANGLE_MODEL,
            force=force,
        )
        return {
            'baseline': result['path'],
            'seed': result['seed'],
            'method': 'i2i',
        }
    else:
        # 策略 2: 纯 T2I
        logger.info(f'=== Phase 1: T2I 生成基准图 ({char_name}) [kling-v3] ===')
        prompt = BASELINE_PROMPT_TEMPLATE.format(desc=description)

        result = _t2i(baseline_path, prompt, seed=seed, model=BASELINE_MODEL, force=force)
        return {
            'baseline': result['path'],
            'seed': result['seed'],
            'method': 't2i',
        }


def generate_sequential_chain(
    baseline_path: str,
    char_name: str,
    force: bool = False,
    seed: int = 0,
) -> dict:
    """Phase 2: 逐帧参考链生成多角度定妆照。

    v2.0 核心变更（对比 v1.0）:
      ❌ v1.0 问题: 所有角度都用同一张 baseline 作 I2I 参考
         → 从正面直接跳到90°侧面，姿态变化太大，角色容易漂移
      ✅ v2.0 方案: 逐帧参考链
         图1(正面) → 图2(右侧45°) → 图3(纯右侧面) → 图4(背面)
         每张图都用上一张图作 I2I 参考，只做小幅姿态变化

    返回:
      {
        "right_three_quarter": "path/to/angle_right_three_quarter.png",
        "right_side": "path/to/angle_right_side.png",
        "back": "path/to/angle_back.png",
        "chain": [步骤详情],
        "seed": int
      }
    """
    output_dir = os.path.join(CACHE_DIR, char_name, 'angles')
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    results = {}
    chain_log = []
    final_seed = seed

    # 构建参考映射: 每个步骤的参考图来源
    ref_map = {'baseline': baseline_path}
    for step in ANGLE_CHAIN:
        ref_map[step['key']] = os.path.join(output_dir, f'angle_{step["key"]}.png')

    for i, step in enumerate(ANGLE_CHAIN):
        output_path = ref_map[step['key']]
        ref_image = ref_map[step['ref_source']]
        step_strength = step['strength']
        step_prompt = step['prompt']

        logger.info(f'==================================================')
        logger.info(f'Phase 2 Step {i+1}/{len(ANGLE_CHAIN)}: {step["label"]}')
        logger.info(f'  参考图: {step["ref_source"]} → {step["key"]}')
        logger.info(f'  强度: {step_strength}')

        try:
            result = _i2i(
                output_path,
                ref_image,
                step_prompt,
                seed=seed,
                strength=step_strength,
                model=ANGLE_MODEL,
                force=force,
            )
            results[step['key']] = result['path']
            final_seed = result.get('seed', seed)
            logger.info(f'  ✅ {step["label"]} [seed={final_seed}]')

            chain_log.append({
                'step': i + 1,
                'label': step['label'],
                'ref_source': step['ref_source'],
                'strength': step_strength,
                'output': result['path'],
                'seed': final_seed,
            })
        except Exception as e:
            logger.warning(f'  ❌ {step["label"]} 生成失败: {e}')
            chain_log.append({
                'step': i + 1,
                'label': step['label'],
                'ref_source': step['ref_source'],
                'strength': step_strength,
                'output': None,
                'error': str(e),
            })

    # 写 chain meta
    meta_path = os.path.join(output_dir, '_chain_meta.json')
    meta = {
        'character': char_name,
        'method': 'sequential_reference_chain_v2',
        'baseline': baseline_path,
        'seed': final_seed,
        'chain': chain_log,
    }
    Path(meta_path).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')

    return {
        'right_three_quarter': results.get('right_three_quarter', ''),
        'right_side': results.get('right_side', ''),
        'back': results.get('back', ''),
        'chain': chain_log,
        'seed': final_seed,
    }


def register_portraits(
    char_name: str,
    baseline_path: str,
    angles: dict,
) -> bool:
    """Phase 3: 将定妆照注册到 CharacterRegistry。

    参数:
      char_name: 角色名
      baseline_path: 基准图路径
      angles: {"right_three_quarter": ..., "right_side": ..., "back": ...}

    返回: 是否成功
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from character_registry import CharacterRegistry

    try:
        registry_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'character_registry',
            'registry.yaml',
        )
        registry = CharacterRegistry()

        # 注册 face_anchor
        ref_images = {'face_anchor': [baseline_path], 'body': []}

        # 注册 body 各角度
        for key in ('right_three_quarter', 'right_side', 'back'):
            if key in angles and angles[key]:
                ref_images['body'].append({'path': angles[key], 'option': key, 'type': 'body'})

        registry.update_reference_images(char_name, ref_images)
        logger.info(f'✅ 已注册定妆照到 CharacterRegistry: {char_name}')
        return True

    except Exception as e:
        logger.warning(f'注册到 CharacterRegistry 失败: {e}')
        return False


def generate_and_register_portraits(
    character_name: str,
    description: str,
    force: bool = False,
    seed: int = 0,
    ref_image: str = '',
) -> dict:
    """全流程: 基准图 → 多角度 → 注册。

    参数:
      character_name: 角色名（与 registry.yaml 一致）
      description: 角色描述（自然语言）
      force: 强制重新生成
      seed: 固定种子
      ref_image: 真实参考照路径。有则 I2I 生成基准图，无则 T2I

    返回:
      {
        "character": "角色名",
        "baseline": "path/to/baseline.png",
        "angles": {"right_three_quarter": "...", "right_side": "...", "back": "..."},
        "registry_updated": True/False,
        "seed": 42,
      }
    """
    result = {
        'character': character_name,
        'baseline': '',
        'angles': {},
        'registry_updated': False,
        'seed': seed,
    }

    logger.info(f'==================================================')
    logger.info(f'🎯 定妆照全流程: {character_name}')

    # Phase 1: 基准图
    try:
        logger.info('📷 Phase 1/2: 生成基准图（正面全身定妆照）...')
        baseline_result = generate_baseline(
            description=description,
            char_name=character_name,
            force=force,
            seed=seed,
            ref_image=ref_image,
        )
        baseline_path = baseline_result.get('baseline', '')
        used_seed = baseline_result.get('seed', seed)
        result['baseline'] = baseline_path
        result['seed'] = used_seed
        logger.info(f'  基准图: {baseline_path}')
        logger.info(f'  seed: {used_seed}')
    except Exception as e:
        logger.error(f'  ❌ Phase 1 失败: {e}')
        result['error'] = f'Phase 1 (基准图) 失败: {str(e)}'
        return result

    # Phase 2: 逐帧参考链
    try:
        logger.info('📸 Phase 2/2: 逐帧参考链生成多角度定妆照...')
        logger.info('   参考链: 正面 → 右侧45°半侧面 → 纯右侧面 → 背面')
        logger.info('   每张以上一张为 I2I 参考，强度 0.70→0.75→0.70')
        angles = generate_sequential_chain(
            baseline_path=baseline_path,
            char_name=character_name,
            force=force,
            seed=used_seed,
        )
        result['angles'] = {
            'right_three_quarter': angles.get('right_three_quarter', ''),
            'right_side': angles.get('right_side', ''),
            'back': angles.get('back', ''),
        }
        logger.info(f'  右侧45°半侧面: {result["angles"]["right_three_quarter"][:50] if result["angles"]["right_three_quarter"] else "失败"}')
        logger.info(f'  纯右侧面:      {result["angles"]["right_side"][:50] if result["angles"]["right_side"] else "失败"}')
        logger.info(f'  背面:           {result["angles"]["back"][:50] if result["angles"]["back"] else "失败"}')
    except Exception as e:
        logger.error(f'  ❌ Phase 2 失败: {e}')
        result['warning'] = f'Phase 2 (多角度) 部分失败: {str(e)}'

    # Phase 3: 注册
    try:
        logger.info('📋 Phase 3/2: 注册到 CharacterRegistry...')
        reg_ok = register_portraits(
            char_name=character_name,
            baseline_path=baseline_path,
            angles=result['angles'],
        )
        result['registry_updated'] = reg_ok
        logger.info(f'  {"✅ 注册成功" if reg_ok else "⚠️ 注册失败"}')
    except Exception as e:
        logger.warning(f'  注册异常: {e}')
        result['registry_updated'] = False

    logger.info(f'✅ 定妆照生成完成: {character_name}')
    return result


# ══════════════════════════════════════════════════════
# CLI 入口
# ══════════════════════════════════════════════════════

def cli(args: list):
    """CLI 入口。"""
    import argparse

    parser = argparse.ArgumentParser(description='两阶段定妆照生成（观鱼方案）')
    parser.add_argument('--character', required=True, help='角色名')
    parser.add_argument('--desc', type=str, default='', help='角色描述（自然语言）')
    parser.add_argument('--force', action='store_true', default=False, help='强制重新生成')
    parser.add_argument('--seed', type=int, default=0, help='固定种子')
    parser.add_argument('--desc-file', type=str, default='', help='从文件读取角色描述')
    parser.add_argument('--ref', type=str, default='', help='真实参考照路径（推荐，代替T2I）')

    parsed = parser.parse_args(args)

    desc = parsed.desc
    if parsed.desc_file:
        desc_file = Path(parsed.desc_file)
        if desc_file.exists():
            desc = desc_file.read_text(encoding='utf-8').strip()

    result = generate_and_register_portraits(
        character_name=parsed.character,
        description=desc,
        force=parsed.force,
        seed=parsed.seed,
        ref_image=parsed.ref,
    )

    print()
    print('==================================================')
    print('✅ 定妆照生成结果:')
    print(f'  基准图: {result.get("baseline", "失败")}')
    if result.get('angles'):
        for key, label in [('right_three_quarter', '右侧45°半侧面'), ('right_side', '纯右侧面'), ('back', '背面')]:
            print(f'  {label}: {result["angles"].get(key, "失败")}')
    print(f'  seed: {result.get("seed", "N/A")}')
    print(f'  已注册: {"✅" if result.get("registry_updated") else "❌"}')

    if result.get('error'):
        print(f'  错误: {result["error"]}')
    if result.get('warning'):
        print(f'  警告: {result["warning"]}')


if __name__ == '__main__':
    import sys
    cli(sys.argv[1:])

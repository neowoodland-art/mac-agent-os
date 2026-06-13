"""
变体生成器 (VariantGenerator) — 按变体类型生成角色图像

使用 Kling API 批量生成各类变体图像：
  - front_face: 正面高清面部特写
  - full_body: 全身正面
  - multi_angle: 多角度全身（front/side/right_three_quarter/right_side/back）
  - expression: 表情变体（neutral/smile/focused/laugh/serious）
  - scene: 场景变体
  - sport_action: 运动姿态
  - grid: 网格定妆照（标准2×3/运动4×2）

每张生成结果以 {role_name}_{variant_type}_{variant_option}.png 命名和缓存
"""

import json
import hashlib
import time
import os
import sys
from pathlib import Path
from typing import Optional

path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, path)

from lib.config import load_config
from lib.logger import get_logger
from character_generator.prompt_assembler import PromptAssembler

logger = get_logger('variant_generator')

environ = os.environ.get
home = os.path.expanduser('~')

# 缓存目录
CACHE_DIR = environ(
    'AVE_CACHE_DIR',
    os.path.join(home, 'workbuddy-agent-os/agent-local/tools/ave/cache/character_portrait'),
)
os.makedirs(CACHE_DIR, exist_ok=True)

# Kling API 基础 URL
KLING_BASE = 'https://api-beijing.klingai.com'


class VariantGenerator:
    """使用 Kling API 批量生成角色变体图像。"""

    def __init__(self):
        self._assembler = PromptAssembler()
        self._cfg = load_config()

    # ══════════════════════════════════════════════════
    # 主入口
    # ══════════════════════════════════════════════════

    def generate(
        self,
        attrs: dict,
        variant_type: str,
        variant_option: str,
        lang: str = 'zh',
        force: bool = False,
        seed: int = 0,
    ) -> dict:
        """生成指定变体类型的图像。

        Args:
            attrs: 结构化属性字典
            variant_type: 变体类型 (front_face, full_body, multi_angle, expression, ...)
            variant_option: 变体选项（如 angle_name, expression_name 等）
            lang: 语言
            force: 强制重新生成
            seed: 固定种子

        Returns:
            {"path": str, "url": str, "seed": int, "prompt": str, "cached": bool}
        """
        # 组装提示词
        prompt = self._assembler.build(variant_type, variant_option, attrs)

        # 生成缓存 key
        opt_suffix = variant_option.replace(' ', '_')
        cache_key = f'{attrs.get("name", "char")}_{variant_type}_{opt_suffix}'
        output_path = os.path.join(CACHE_DIR, cache_key)
        Path(output_path).mkdir(parents=True, exist_ok=True)

        filename = f'{cache_key}_{seed if seed else "rand"}.png'
        filepath = os.path.join(output_path, filename)

        # 如果缓存命中且不强制，直接返回
        if not force and os.path.exists(filepath):
            logger.info(f'  缓存命中: {filepath}')
            return {'path': filepath, 'url': '', 'seed': seed, 'prompt': prompt, 'cached': True}

        # 调用 Kling API
        result = self._generate_kling(prompt, filepath, seed)
        result['prompt'] = prompt
        return result

    # ══════════════════════════════════════════════════
    # 批量生成
    # ══════════════════════════════════════════════════

    def generate_all_angles(
        self,
        attrs: dict,
        lang: str = 'zh',
        force: bool = False,
        seed: int = 0,
    ) -> dict:
        """生成所有角度的全身图。"""
        angles = ('front', 'side', 'right_three_quarter', 'right_side', 'back')
        results = {}
        for angle in angles:
            results[angle] = self.generate(attrs, 'multi_angle', angle, lang, force, seed)
        return results

    def generate_all_expressions(
        self,
        attrs: dict,
        lang: str = 'zh',
        force: bool = False,
        seed: int = 0,
    ) -> dict:
        """生成所有表情变体。"""
        expressions = ('neutral', 'smile', 'focused', 'laugh', 'serious')
        results = {}
        for expr in expressions:
            results[expr] = self.generate(attrs, 'expression', expr, lang, force, seed)
        return results

    def generate_baseline_portrait(
        self,
        attrs: dict,
        lang: str = 'zh',
        force: bool = False,
        seed: int = 0,
    ) -> dict:
        """生成正面基准肖像（用于 face_anchor）。"""
        return self.generate(attrs, 'front_face', 'baseline', lang, force, seed)

    def generate_grid_sheet(
        self,
        attrs: dict,
        mode: str = 'standard',
        lang: str = 'zh',
        force: bool = False,
        seed: int = 0,
        ref_image: str = '',
        prompt: str = '',
    ) -> dict:
        """生成网格定妆照。

        Args:
            attrs: 结构化属性
            mode: 网格模式 (standard=2x3, sport=4x2)
            lang: 语言
            force: 强制重新生成
            seed: 固定种子
            ref_image: 参考图路径（可选）
            prompt: 手动提示词（可选，为空则自动组装）
        """
        if not prompt:
            prompt = self._assembler.build('grid', mode, attrs, lang=lang)

        name = attrs.get('name', 'char')
        output_path = os.path.join(CACHE_DIR, 'grid', name)
        Path(output_path).mkdir(parents=True, exist_ok=True)

        filename = f'grid_{name}_{mode}_{seed if seed else "rand"}.png'
        filepath = os.path.join(output_path, filename)

        if not force and os.path.exists(filepath):
            logger.info(f'  网格缓存命中: {filepath}')
            return {'path': filepath, 'url': '', 'seed': seed, 'prompt': prompt, 'cached': True}

        result = self._generate_kling(prompt, filepath, seed, ref_image)
        result['prompt'] = prompt
        return result

    # ══════════════════════════════════════════════════
    # 辅助
    # ══════════════════════════════════════════════════

    def _get_option_key(self, variant_type: str) -> str:
        """将变体类型映射到配置中的选项 key。"""
        mapping = {
            'multi_angle': 'angles',
            'expression': 'expressions',
            'scene': 'scenes',
            'sport_action': 'actions',
            'outfit': 'outfits',
            'grid': 'grid_modes',
        }
        return mapping.get(variant_type, variant_type)

    # ══════════════════════════════════════════════════
    # Kling API 底层
    # ══════════════════════════════════════════════════

    def _generate_kling(
        self,
        prompt: str,
        output_path: str,
        seed: int = 0,
        ref_image: str = '',
    ) -> dict:
        """调用 Kling API 生成图像。

        支持 T2I（无 ref_image）和 I2I（有 ref_image）。

        Args:
            prompt: 生成提示词
            output_path: 输出文件路径
            seed: 固定种子（0 = 随机）
            ref_image: 参考图路径（可选，走 I2I）

        Returns:
            {"path": str, "seed": int, "filename": str}
            失败时返回 {"failed": True, "error": str}
        """
        import httpx

        # 加载 Kling 配置
        kling_cfg = self._cfg.get('kling', {})
        ak = kling_cfg.get('access_key', environ('KLING_ACCESS_KEY', ''))
        sk = kling_cfg.get('secret_key', environ('KLING_SECRET_KEY', ''))

        if not ak or not sk:
            raise ValueError('缺少 Kling API 配置 (kling.access_key / kling.secret_key)')

        # 生成 JWT token
        import jwt
        now = int(time.time())
        token = jwt.encode(
            {'iss': ak, 'exp': now + 1800, 'nbf': now},
            sk,
            algorithm='HS256',
        )
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

        # 判断是否用参考图（I2I）
        use_ref = bool(ref_image and os.path.exists(ref_image))

        if use_ref:
            with open(ref_image, 'rb') as f:
                import base64
                img_b64 = base64.b64encode(f.read()).decode('utf-8')

            payload = {
                'model': 'kling-v1',
                'prompt': prompt,
                'image': img_b64,
                'strength': 0.65,
                'aspect_ratio': '9:16',
                'n': 1,
            }
        else:
            payload = {
                'model': 'kling-v3',
                'prompt': prompt,
                'aspect_ratio': '9:16',
                'n': 1,
            }

        if seed:
            payload['seed'] = seed

        # 提交任务
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
                    raise RuntimeError(f'Kling 提交失败: {data}')
                break
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(5)
        else:
            raise RuntimeError('Kling API 提交失败（重试耗尽）')

        # 轮询任务状态
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
                        raise RuntimeError('Kling 生成成功但无图像')
                    img_url = images[0].get('url', '')
                    returned_seed = images[0].get('seed', seed)

                    # 下载图像
                    img_resp = httpx.get(img_url, timeout=30)
                    img_resp.raise_for_status()

                    Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(img_resp.content)

                    logger.info(f'  ✅ Kling 生成完成: {os.path.basename(output_path)} [seed={returned_seed}]')
                    return {
                        'path': output_path,
                        'seed': returned_seed,
                        'filename': os.path.basename(output_path),
                    }

                elif task_status == 'failed':
                    reason = status_data.get('fail_reason', '未知错误')
                    raise RuntimeError(f'Kling 生成失败: {reason}')

            except Exception as e:
                logger.warning(f'  轮询异常: {e}')
                time.sleep(5)

        raise TimeoutError('Kling 生成超时（200s）')


if __name__ == '__main__':
    gen = VariantGenerator()
    print('变体生成器初始化完成')
    available = gen.get_available_variants()
    print(f'可用变体: {list(available.keys())}')

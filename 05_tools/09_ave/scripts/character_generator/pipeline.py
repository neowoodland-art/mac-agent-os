"""
角色生成完整流水线 (CharacterGenerationPipeline)

完整流程:

  用户方向 (粗方向)
      ↓
  [DirectionExpander] — 调用本地 LLM 补充为完整自然语言描述
      ↓
  详细角色描述
      ↓
  [AttributeExtractor] — 提取结构化的面部/体型/服装/配件/性格
      ↓
  结构化属性
      ↓
  [PromptAssembler] — 按不同类型组装生成提示词
      ↓
  生成提示词
      ↓
  [VariantGenerator] — 调用 Kling API 生成各类变体
      ↓
  变体图像
      ↓
  [AssetRegistrar] — 写入 registry.yaml + 知识库
      ↓
  完成

用法:
  from character_generator.pipeline import CharacterGenerationPipeline
  pipeline = CharacterGenerationPipeline()
  
  # 完整流程：从粗方向开始
  result = pipeline.run_full("一个运动型中年男性", character_name="new_char")
  
  # 仅扩展描述（不生成图像）
  desc = pipeline.expand_direction("一个运动型中年男性")
  
  # 从已有描述开始（生成+注册）
  result = pipeline.run_from_description("详细描述...", character_name="new_char")
  
  # 仅生成定妆照网格
  result = pipeline.generate_portrait("角色名", force=True)
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional

path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, path)

from character_generator.direction_expander import DirectionExpander
from character_generator.attribute_extractor import AttributeExtractor
from character_generator.prompt_assembler import PromptAssembler
from character_generator.variant_generator import VariantGenerator
from character_generator.asset_registrar import AssetRegistrar
from lib.logger import get_logger

logger = get_logger('character_pipeline')


class CharacterGenerationPipeline:
    """角色生成完整流水线

    整合五个子模块，提供从粗方向到角色变体素材的一站式接口。
    """

    def __init__(self):
        self._expander = DirectionExpander()
        self._extractor = AttributeExtractor()
        self._assembler = PromptAssembler()
        self._generator = VariantGenerator()
        self._registrar = AssetRegistrar()

    # ──────────────────────────────────────────────
    # 主流程
    # ──────────────────────────────────────────────

    def run_full(
        self,
        direction: str,
        character_name: str = '',
        lang: str = 'zh',
        generate_variants: bool = True,
        seed: int = 0,
    ) -> dict:
        """完整流水线：从粗方向到注册完成。

        Args:
            direction: 用户输入的粗方向，如"一个运动型中年男性"
            character_name: 角色名（为空则自动生成）
            lang: 语言
            generate_variants: 是否生成变体图像
            seed: 固定种子（0=随机）

        Returns:
            {
                "name": str,
                "description": str,
                "attributes": dict,
                "baseline": dict or None,
                "angles": dict or None,
                "expressions": dict or None,
                "grid": dict or None,
                "registered": True,
            }
        """
        step_results = {}

        # [1/5] 扩展方向
        logger.info(f'[1/5] 扩展方向: {direction[:50]}...')
        description = self._expander.expand(direction)
        step_results['description'] = description

        # 自动生成角色名
        if not character_name:
            character_name = self._generate_name(direction, description)

        # [2/5] 提取属性
        logger.info(f'[2/5] 提取属性: {character_name}')
        attrs = self._extractor.extract(description, name=character_name)
        step_results['attributes'] = attrs

        # [3/5] 注册角色属性
        logger.info('[3/5] 注册角色属性')
        self._registrar.register_character_properties(character_name, attrs)

        # [4/5] 生成变体
        if generate_variants:
            generated = self._generate_all(attrs, lang, seed)
            step_results['generated'] = generated
        else:
            step_results['generated'] = {}

        # 注册定妆照到 registry
        generated = step_results.get('generated', {})
        baseline = generated.get('baseline', {}).get('path', '')
        angles = {
            k: v['path']
            for k, v in generated.get('angles', {}).items()
            if v.get('path')
        }
        expressions = {
            k: v['path']
            for k, v in generated.get('expressions', {}).items()
            if v.get('path')
        }

        if baseline or angles or expressions:
            self._registrar.register_portrait_set(
                character_name,
                attrs,
                baseline=baseline or None,
                angles=angles or None,
                expressions=expressions or None,
            )

        # [5/5] 更新知识库
        logger.info('[4/5] 注册素材到知识库')
        self._registrar.update_knowledge_base(character_name, attrs)

        return {
            'name': character_name,
            'description': description,
            'attributes': attrs,
            'baseline': generated.get('baseline', {}),
            'angles': generated.get('angles', {}),
            'expressions': generated.get('expressions', {}),
            'grid': generated.get('grid', {}),
            'registered': True,
        }

    # ──────────────────────────────────────────────
    # 从已有描述开始（跳过方向扩展）
    # ──────────────────────────────────────────────

    def run_from_description(
        self,
        description: str,
        character_name: str = '',
        lang: str = 'zh',
        seed: int = 0,
    ) -> dict:
        """从完整描述直接开始，绕过方向扩展步骤。

        Args:
            description: 完整的角色自然语言描述
            character_name: 角色名（为空则自动生成）
            lang: 语言
            seed: 固定种子

        Returns:
            同 run_full()
        """
        if not character_name:
            character_name = self._generate_name(description, description)

        attrs = self._extractor.extract(description, name=character_name)
        self._registrar.register_character_properties(character_name, attrs)

        generated = self._generate_all(attrs, lang, seed)

        # 注册定妆照到 registry
        baseline = generated.get('baseline', {}).get('path', '')
        angles = {
            k: v.get('path', '')
            for k, v in generated.get('angles', {}).items()
            if v.get('path')
        }
        expressions = {
            k: v.get('path', '')
            for k, v in generated.get('expressions', {}).items()
            if v.get('path')
        }

        self._registrar.register_portrait_set(
            character_name,
            attrs,
            baseline=baseline or None,
            angles=angles or None,
            expressions=expressions or None,
        )

        self._registrar.update_knowledge_base(character_name, attrs)

        return {
            'name': character_name,
            'description': description,
            'attributes': attrs,
            'baseline': generated.get('baseline', {}),
            'angles': generated.get('angles', {}),
            'expressions': generated.get('expressions', {}),
            'grid': generated.get('grid', {}),
            'registered': True,
        }

    # ──────────────────────────────────────────────
    # 仅生成定妆照
    # ──────────────────────────────────────────────

    def generate_portrait(self, character_name: str, force: bool = False, seed: int = 0) -> dict:
        """仅基于已注册的角色信息生成定妆照网格。

        需要角色已在 registry 中注册（有 attrs 属性）。

        Args:
            character_name: 角色名
            force: 强制重新生成
            seed: 固定种子

        Returns:
            变体生成结果 dict
        """
        from character_registry import CharacterRegistry

        registry = CharacterRegistry()
        char = registry.get_character(character_name)
        attrs = char.to_dict()

        generated = self._generate_all(attrs, 'zh', seed, force)

        # 注册定妆照
        baseline = generated.get('baseline', {}).get('path', '')
        if baseline:
            self._registrar.register_reference_images(
                character_name, 'face_anchor', baseline
            )

        for angle, path in generated.get('angles', {}).items():
            self._registrar.register_reference_images(
                character_name, 'body', path, option=angle
            )

        for expr, path in generated.get('expressions', {}).items():
            self._registrar.register_reference_images(
                character_name, 'expression', path, option=expr
            )

        return generated

    # ──────────────────────────────────────────────
    # 单步操作
    # ──────────────────────────────────────────────

    def expand_direction(self, direction: str) -> str:
        """仅扩展方向描述（不提取属性、不生成图像）。"""
        return self._expander.expand(direction)

    def extract_attributes(self, description: str, name: str = '') -> dict:
        """仅提取结构化属性（不生成图像、不注册）。"""
        return self._extractor.extract(description, name=name)

    # ──────────────────────────────────────────────
    # 内部：批量生成变体
    # ──────────────────────────────────────────────

    def _generate_all(
        self,
        attrs: dict,
        lang: str = 'zh',
        seed: int = 0,
        force: bool = False,
    ) -> dict:
        """调用 VariantGenerator 生成基准照 + 多角度 + 表情 + 网格。

        每个步骤独立 try/except，失败时记录 warning 并继续。
        保证不会因为单步失败而中断整个流程。

        Args:
            attrs: 结构化属性 dict
            lang: 语言
            seed: 固定种子
            force: 强制重新生成

        Returns:
            {
                "baseline": dict or {"error": str},
                "angles": dict or {"error": str},
                "expressions": dict or {"error": str},
                "grid": dict or {"error": str},
            }
        """
        logger.info(f'[5/5] 生成变体 (seed={seed if seed else "随机"})')
        result = {}

        # 1/4: 正面基准肖像
        try:
            logger.info('  1/4: 正面基准肖像...')
            result['baseline'] = self._generator.generate_baseline_portrait(
                attrs, lang, force, seed
            )
        except Exception as e:
            logger.warning(f'  ⚠ 基准照生成失败: {e}')
            result['baseline'] = {'error': str(e)}

        # 2/4: 多角度全身
        try:
            logger.info('  2/4: 多角度全身...')
            result['angles'] = self._generator.generate_all_angles(
                attrs, lang, force, seed
            )
        except Exception as e:
            logger.warning(f'  ⚠ 多角度生成失败: {e}')
            result['angles'] = {'error': str(e)}

        # 3/4: 表情变体
        try:
            logger.info('  3/4: 表情变体...')
            result['expressions'] = self._generator.generate_all_expressions(
                attrs, lang, force, seed
            )
        except Exception as e:
            logger.warning(f'  ⚠ 表情变体生成失败: {e}')
            result['expressions'] = {'error': str(e)}

        # 4/4: 网格定妆照
        try:
            mode = attrs.get('sheet_mode', 'standard')
            logger.info('  4/4: 网格定妆照...')
            result['grid'] = self._generator.generate_grid_sheet(
                attrs, mode, lang, force, seed
            )
        except Exception as e:
            logger.warning(f'  ⚠ 网格定妆照生成失败: {e}')
            result['grid'] = {'error': str(e)}

        return result

    # ──────────────────────────────────────────────
    # 内部：从方向/描述生成角色名
    # ──────────────────────────────────────────────

    def _generate_name(self, direction: str, description: str) -> str:
        """从方向/描述中提取角色名。

        策略：
        1. 在 direction 中查找 "XX岁的中/老/青年男性/女性" 模式
        2. 若未命中，查找 "[角色名]男/女" 模式
        3. 若仍未命中，取 direction 前 3 字
        4. 追加当前时间戳（%H%M）避免重名
        """
        import re

        m = re.search(r'(\d+岁)?[的]?([\u4e00-\u9fff]{2,4}(?:男性|女性|男生|女生|少年|少女|中年|老人))', direction)
        if not m:
            m = re.search(r'([\u4e00-\u9fff]{2,6})[男女人]', direction)

        if m:
            base = m.group(1)
            base = base.replace('的', '').replace('男性', '').replace('女性', '')
            name = base if len(base) <= 3 else base[:-3]
        else:
            name = direction[:3]

        from datetime import datetime
        timestamp = datetime.now().strftime('%H%M')
        return f'{name}_{timestamp}'


if __name__ == '__main__':
    pipeline = CharacterGenerationPipeline()

    print('\n=== 测试1: 方向扩展 ===')
    direction = '一个运动型中年男性，喜欢户外跑步和健身'
    desc = pipeline.expand_direction(direction)
    print(f'方向: {direction}')
    print(f'扩展: {desc}')

    print('\n=== 测试2: 属性提取 ===')
    attrs = pipeline.extract_attributes(desc, name='test_char')
    print(f'外观: {attrs.get("appearance", "N/A")}')
    print(f'面部: {attrs.get("face", "N/A")}')
    print(f'服装: {attrs.get("clothing", "N/A")}')
    print(f'配件: {attrs.get("accessories", "N/A")}')
    print(f'性格: {attrs.get("personality", "N/A")}')

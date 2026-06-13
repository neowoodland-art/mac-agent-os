"""
素材注册器 (AssetRegistrar) — 将生成的角色变体素材注册到 registry.yaml + 知识库

注册内容:
  - 更新 registry.yaml 中的 reference_images (face_anchor, body各角度, expressions)
  - 更新 outfit_presets（如果有自定义服装变体）
  - 生成标签元数据供 asset_manager 索引
  - 回写到 prompts/character_sheet_prompts.md（知识库）
"""

import json
import os
import sys
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional

path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, path)

from lib.logger import get_logger

logger = get_logger('asset_registrar')

# ── 路径 ──
SCRIPTS_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = SCRIPTS_DIR.parent / 'character_registry' / 'registry.yaml'
REGISTRY_BACKUP_DIR = SCRIPTS_DIR.parent / 'character_registry' / 'backups'
PROMPTS_DIR = SCRIPTS_DIR / 'prompts'
CHARACTER_SHEET_PROMPTS = PROMPTS_DIR / 'character_sheet_prompts.md'

# ── 变体标签映射 ──
VARIANT_TAGS = {
    'front_face': ('面部特写', '基准', '正面'),
    'multi_angle': {
        'default': ('全身', '正面', '体型'),
        'front': ('全身', '正面', '体型'),
        'side': ('全身', '侧面', '体型'),
        'right_three_quarter': ('全身', '右侧45°', '体型'),
        'right_side': ('全身', '纯右侧', '体型'),
        'back': ('全身', '背面', '体型'),
    },
    'expression': {
        'default': ('表情', '中性'),
        'neutral': ('表情', '中性'),
        'smile': ('表情', '微笑'),
        'focused': ('表情', '专注'),
        'laugh': ('表情', '大笑'),
        'serious': ('表情', '严肃'),
    },
    'scene': {
        'morning_run': ('场景', '晨跑', '运动'),
        'gym_workout': ('场景', '健身房', '力量训练'),
        'street_basketball': ('场景', '篮球', '街头'),
        'office_work': ('场景', '办公室', '工作'),
        'outdoor_fitness': ('场景', '户外', '健身'),
    },
    'sport_action': {
        'running': ('运动', '奔跑', '动态'),
        'jumping': ('运动', '跳跃', '动态'),
        'defensive': ('运动', '防守', '姿态'),
        'stretching': ('运动', '拉伸', '热身'),
    },
}


class AssetRegistrar:
    """将生成的角色素材注册到 registry.yaml + 知识库。"""

    def __init__(self):
        self._registry_data = self._load_registry()
        self._registry_path = REGISTRY_PATH

    # ══════════════════════════════════════════════════
    # 底层 IO
    # ══════════════════════════════════════════════════

    def _load_registry(self) -> dict:
        """从 registry.yaml 加载数据。"""
        if not REGISTRY_PATH.exists():
            return {'active_character': None, 'characters': {}}
        with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {'active_character': None, 'characters': {}}

    def _save_registry(self):
        """保存 registry.yaml（先备份再写入）。"""
        REGISTRY_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        if REGISTRY_PATH.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = REGISTRY_BACKUP_DIR / f'registry_{timestamp}.yaml'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(REGISTRY_PATH.read_text(encoding='utf-8'))

        with open(REGISTRY_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(
                self._registry_data,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )

    # ══════════════════════════════════════════════════
    # 注册角色属性
    # ══════════════════════════════════════════════════

    def register_character_properties(self, name: str, attrs: dict) -> bool:
        """注册/更新角色的属性信息到 registry.yaml。

        Args:
            name: 角色名
            attrs: 结构化属性字典

        Returns:
            是否成功
        """
        chars = self._registry_data['characters']
        if name not in chars:
            chars[name] = {}
        char = chars[name]

        # 写入永久属性
        for key in ('name', 'description', 'base', 'personality', 'voice_style', 'art_style'):
            if key in attrs and attrs[key]:
                char[key] = attrs[key]

        # 写入分层特征
        for category in ('appearance', 'face', 'body', 'clothing', 'accessories'):
            if category in attrs and attrs[category]:
                char[category] = attrs[category]

        self._save_registry()
        logger.info(f'  已注册角色属性: {name}')
        return True

    # ══════════════════════════════════════════════════
    # 注册参考图
    # ══════════════════════════════════════════════════

    def register_reference_images(
        self,
        name: str,
        ref_type: str,
        filepath: str,
        option: str = '',
    ) -> bool:
        """注册单张参考图到 registry。

        Args:
            name: 角色名
            ref_type: 类型 (face_anchor/baseline/body/expression/real_photo)
            filepath: 图片路径
            option: 选项（如 body 的 front/side, expression 的 smile/neutral）

        Returns:
            是否成功
        """
        chars = self._registry_data['characters']
        if name not in chars:
            chars[name] = {}
        char = chars[name]

        if 'reference_images' not in char:
            char['reference_images'] = {}

        refs = char['reference_images']
        if ref_type not in refs:
            refs[ref_type] = []

        entry = {'path': filepath}
        if option:
            entry['option'] = option

        refs[ref_type].append(entry)
        self._save_registry()
        return True

    # ══════════════════════════════════════════════════
    # 批量注册定妆照
    # ══════════════════════════════════════════════════

    def register_portrait_set(
        self,
        name: str,
        attrs: dict,
        baseline: Optional[str] = None,
        angles: Optional[dict] = None,
        expressions: Optional[dict] = None,
    ) -> bool:
        """批量注册一套完整的定妆照。

        Args:
            name: 角色名
            attrs: 结构化属性
            baseline: 基准照路径
            angles: {angle_name: filepath, ...}
            expressions: {expr_name: filepath, ...}

        Returns:
            是否成功
        """
        if baseline:
            self.register_reference_images(name, 'face_anchor', baseline)

        if angles:
            for angle, path in angles.items():
                self.register_reference_images(name, 'body', path, option=angle)

        if expressions:
            for expr, path in expressions.items():
                self.register_reference_images(name, 'expression', path, option=expr)

        return True

    # ══════════════════════════════════════════════════
    # 更新知识库
    # ══════════════════════════════════════════════════

    def update_knowledge_base(self, name: str, attrs: dict) -> bool:
        """将角色描述更新到 character_sheet_prompts.md。

        Args:
            name: 角色名
            attrs: 结构化属性

        Returns:
            是否成功
        """
        base = attrs.get('base', '')
        face = attrs.get('face', {})
        body = attrs.get('body', {})

        # 构建角色描述块
        char_block_parts = [f'### {name}']
        char_block_parts.append(f'- **描述**: {attrs.get("description", "")}')
        char_block_parts.append(
            f'- **面部**: 脸型={face.get("shape", "?")}, '
            f'眼睛={face.get("eyes", "?")}, '
            f'发型={face.get("hair", "?")}, '
            f'肤色={face.get("skin", "?")}'
        )
        char_block_parts.append(
            f'- **体型**: 体态={body.get("build", "?")}, '
            f'身高={body.get("height", "?")}'
        )
        char_block_parts.append(
            f'- **性格**: {attrs.get("personality", "?")}'
        )
        char_block_parts.append(
            f'- **语音**: {attrs.get("voice_style", "?")}'
        )

        char_block = '\n'.join(char_block_parts)
        new_section = f'\n\n{char_block}  # 自动注册）\n\n'

        # 写入 prompts/character_sheet_prompts.md
        PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
        if CHARACTER_SHEET_PROMPTS.exists():
            existing = CHARACTER_SHEET_PROMPTS.read_text(encoding='utf-8')
            if f'### {name}' not in existing:
                with open(CHARACTER_SHEET_PROMPTS, 'a', encoding='utf-8') as f:
                    f.write(new_section)
        else:
            with open(CHARACTER_SHEET_PROMPTS, 'w', encoding='utf-8') as f:
                f.write(f'# 角色定妆照提示词库\n{new_section}')

        logger.info(f'  已更新知识库: {name}')
        return True

    # ══════════════════════════════════════════════════
    # 标签工具
    # ══════════════════════════════════════════════════

    def get_variant_tags(self, variant_type: str, option: str = '') -> tuple:
        """获取变体类型的标签元数据。

        Args:
            variant_type: 变体类型
            option: 选项名

        Returns:
            标签元组
        """
        tags = VARIANT_TAGS.get(variant_type, {})
        if isinstance(tags, tuple):
            return tags
        if isinstance(tags, dict):
            return tags.get(option, tags.get('default', ()))
        return ()


if __name__ == '__main__':
    registrar = AssetRegistrar()
    print(f'素材注册器就绪, registry: {REGISTRY_PATH}')
    print(f'知识库: {CHARACTER_SHEET_PROMPTS}')

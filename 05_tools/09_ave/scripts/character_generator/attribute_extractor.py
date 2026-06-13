"""
属性提取器 (AttributeExtractor) — 从自然语言角色描述中提取结构化属性

输出结构:
  {
    "name": "角色名",
    "description": "完整自然语言描述",
    "base": "核心特征（不含服装的永久特征）",
    "appearance": ["特征1", "特征2", ...],       # 外观特征列表
    "face": {"shape": "国字脸", "eyes": "单眼皮", ...},
    "body": {"build": "健壮", "height": "175cm", ...},
    "clothing": {"top": "深灰夹克", "inner": "白色内衬", ...},
    "accessories": ["蓝牙耳机"],
    "personality": "沉稳内敛",
    "voice_style": "成熟稳重男声",
    "art_style": "写实摄影风格",
  }
"""

import json
import re
from typing import Optional

# ── 语音风格枚举 ──
VOICE_STYLES = (
    '活泼少女音',
    '温柔青年音',
    '成熟稳重男声',
    '清澈少年音',
    '低沉磁性',
    '甜美少女音',
    '知性女声',
    '治愈系',
    '默认',
)

# ── 画风枚举 ──
ART_STYLES = (
    '写实摄影风格',
    '日系漫画风格',
    '电影级摄影风格',
    '超写实风格',
    '赛博朋克风格',
    '水墨风格',
)


class AttributeExtractor:
    """从自然语言描述中提取结构化角色属性。"""

    # ══════════════════════════════════════════════════
    # 主入口
    # ══════════════════════════════════════════════════

    def extract(self, description: str, name: str = '') -> dict:
        """从自然语言描述中提取结构化属性。

        Args:
            description: 自然语言角色描述
            name: 角色名称

        Returns:
            结构化属性字典
        """
        if not description:
            return self._default_attributes(name)

        attrs = self._default_attributes(name)
        attrs['description'] = description

        attrs['base'] = self._extract_base(description)
        attrs['appearance'] = self._extract_appearance_list(description)
        attrs['face'] = self._extract_face(description)
        attrs['body'] = self._extract_body(description)
        attrs['clothing'] = self._extract_clothing(description)
        attrs['accessories'] = self._extract_accessories(description)
        attrs['personality'] = self._extract_personality(description)
        attrs['voice_style'] = self._extract_voice(description)
        attrs['art_style'] = self._extract_art_style(description)

        return attrs

    # ══════════════════════════════════════════════════
    # 默认值
    # ══════════════════════════════════════════════════

    def _default_attributes(self, name: str = '') -> dict:
        """返回默认空属性模板。"""
        return {
            'name': name or '未命名',
            'description': '',
            'base': '',
            'appearance': [],
            'face': {k: '' for k in ('shape', 'eyes', 'nose', 'lips', 'hair', 'skin', 'facial_hair', 'glasses', 'distinctive')},
            'body': {k: '' for k in ('build', 'height', 'posture', 'age_group')},
            'clothing': {k: '' for k in ('top', 'inner', 'bottom', 'shoes', 'style')},
            'accessories': [],
            'personality': '默认',
            'voice_style': '写实摄影风格',
        }

    # ══════════════════════════════════════════════════
    # 各类别提取
    # ══════════════════════════════════════════════════

    def _extract_base(self, desc: str) -> str:
        """提取核心特征（去服装、去场景的永久性特征）。"""
        base = re.sub(r'身穿[^，。]*', '', desc)
        base = re.sub(r'穿着[^，。]*', '', base)
        base = re.sub(r'（[^）]*）', '', base)
        base = base.replace('，', '').replace('。', '').replace(' ', '')
        return base.strip()

    def _extract_appearance_list(self, desc: str) -> list:
        """提取外观特征列表。

        按分类匹配模式，返回 ["脸型:国字脸", "眼部:单眼皮", ...]。
        """
        patterns = [
            ('(国字脸|圆脸|方脸|瓜子脸|长脸)', '脸型'),
            ('(单眼皮|双眼皮|内双|大眼睛|小眼睛|细长眼)', '眼部'),
            ('(黑色短发|黑短发|棕色短发|寸头|齐刘海|中长发|三七分|背头|卷发)', '发型'),
            ('(健壮|偏瘦|壮硕|匀称|标准|苗条|丰满|粗犷)', '体型'),
            ('(深灰[色]?[^，。]*夹克|浅灰[色]?[^，。]*卫衣|运动[^，。]*|连帽[^，。]*)', '服装'),
        ]
        features = []
        for pattern, category in patterns:
            m = re.search(pattern, desc)
            if m:
                matched = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
                feature = f'{category}:{matched}'
                if len(feature) <= 8:
                    features.append(feature)
        return features

    def _extract_face(self, desc: str) -> dict:
        """提取面部详细特征。"""
        face = {k: '' for k in ('shape', 'eyes', 'nose', 'lips', 'hair', 'skin', 'facial_hair', 'glasses', 'distinctive')}

        m = re.search(r'(国字脸|圆脸|方脸|瓜子脸|长脸|菱形脸)', desc)
        if m:
            face['shape'] = m.group(1)

        m = re.search(r'(单眼皮|双眼皮|内双|大眼睛|小眼睛|细长眼|眼尾[^，。]*)', desc)
        if m:
            face['eyes'] = m.group(1)

        m = re.search(r'(鼻梁[^，。]*?|鼻翼[^，。]*?|[^，。]*鼻[^，。]*)', desc)
        if m:
            face['nose'] = m.group(1)

        m = re.search(r'(嘴唇[^，。]*?|嘴角[^，。]*?)', desc)
        if m:
            face['lips'] = m.group(1)

        m = re.search(r'(黑[色]?[^，。]*发|棕[色]?[^，。]*发|寸头|平头|光头|卷发|直发|[^，。]*短发[^，。]*)', desc)
        if m:
            face['hair'] = m.group(1)

        m = re.search(r'(小麦色|白皙|健康[^，。]*|古铜色|偏[^，。]*[肤皮])', desc)
        if m:
            face['skin'] = m.group(1)

        m = re.search(r'(胡须|胡子|络腮胡|山羊胡|胡茬)', desc)
        if m:
            face['facial_hair'] = m.group(1)

        m = re.search(r'([^，。]*眼镜[^，。]*)', desc)
        if m:
            face['glasses'] = m.group(1)

        m = re.search(r'(耳[机塞][^，。]*|耳机|特殊特征[^，。]*)', desc)
        if m:
            face['distinctive'] = m.group(1)

        return face

    def _extract_body(self, desc: str) -> dict:
        """提取体型特征。"""
        body = {k: '' for k in ('build', 'height', 'posture', 'age_group')}

        m = re.search(r'(健壮|偏瘦|壮硕|匀称|标准|苗条|丰满|粗犷|肌肉[^，。]*)', desc)
        if m:
            body['build'] = m.group(1)

        m = re.search(r'(\d+cm|\d+m\d+)', desc)
        if m:
            body['height'] = m.group(1)

        m = re.search(r'(\d+岁)', desc)
        if m:
            body['age_group'] = m.group(1)

        m = re.search(r'(挺拔|微驼|笔直|自然)', desc)
        if m:
            body['posture'] = m.group(1)

        return body

    def _extract_clothing(self, desc: str) -> dict:
        """提取服装特征。"""
        clothing = {k: '' for k in ('top', 'inner', 'bottom', 'shoes', 'style')}

        m = re.search(r'([^，。]*?[夹克卫衣衬衫T恤外套][^，。]*)', desc)
        if m:
            clothing['top'] = m.group(1)

        m = re.search(r'([^，。]*?[内衬打底背心][^，。]*)', desc)
        if m:
            clothing['inner'] = m.group(1)

        m = re.search(r'([^，。]*?[裤子短裤牛仔裤][^，。]*)', desc)
        if m:
            clothing['bottom'] = m.group(1)

        m = re.search(r'(运动[^，。]*|商务[^，。]*|休闲[^，。]*|正式[^，。]*)', desc)
        if m:
            clothing['style'] = m.group(1)

        return clothing

    def _extract_accessories(self, desc: str) -> list:
        """提取配饰列表。"""
        accessories = []
        for m in re.finditer(r'(耳机|眼镜|手表|手环|项链|帽子|围巾|腰带|护腕|背包)', desc):
            accessories.append(m.group(1))
        return accessories

    def _extract_personality(self, desc: str) -> str:
        """提取性格特征。"""
        m = re.search(r'(性格[^，。]*|气质[^，。]*|性[^，。]*？)', desc)
        if m:
            text = m.group(1)
            keywords = ('沉稳', '开朗', '温和', '内敛', '专注', '活泼', '坚韧', '倔强')
            found = [k for k in keywords if k in text]
            if found:
                return '、'.join(found)
        return '默认'

    def _extract_voice(self, desc: str) -> str:
        """提取语音风格。"""
        m = re.search(r'([^，。]*[音声][^，。]*)', desc)
        if m:
            voice_text = m.group(1)
            # 关键词匹配
            if '音' in voice_text or '声' in voice_text:
                if '中年' in voice_text or '沉稳' in voice_text:
                    return '成熟稳重男声'
                elif '少女' in voice_text or '活泼' in voice_text:
                    return '活泼少女音'
                elif '青年' in voice_text or '温和' in voice_text:
                    return '温柔青年音'
        return '默认'

    def _extract_art_style(self, desc: str) -> str:
        """提取画风。"""
        m = re.search(r'([^，。]*?[风格][^，。]*)', desc)
        if m:
            style_text = m.group(1)
            if '风' in style_text or '格' in style_text:
                return '写实摄影风格'
        return '写实摄影风格'


if __name__ == '__main__':
    extractor = AttributeExtractor()

    test_desc = (
        '一位约42岁的中国男性，体型健壮肩宽，黑色短发利落，'
        '国字脸单眼皮眼尾微垂，鼻梁挺直，神态沉稳内敛，'
        '肤色健康自然。身穿深灰色拉链运动夹克配白色速干内衬，'
        '右耳戴着蓝色无线运动耳机。'
    )

    result = extractor.extract(test_desc, 'ghai_sports')
    print(json.dumps(result, indent=2, ensure_ascii=False))

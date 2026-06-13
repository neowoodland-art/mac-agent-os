"""
方向扩展器 (DirectionExpander) — 将用户给的粗方向补充为完整自然语言描述

流程:
  用户输入 → 调用本地 oMLX LLM (Qwen3.5) → 返回完整角色自然语言描述

扩展内容:
  - 面部特征（五官、发型、脸型、肤色）
  - 体型（身高、肩宽、体态）
  - 服装（上装、下装、鞋子）
  - 标志性配件/装饰
  - 性格/气质
  - 声音/语态
  - 画风/风格倾向

如果用户描述已经足够详细，则直接使用，不做过度补充。
"""

import json
import os
import sys
from pathlib import Path

path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, path)

from lib.config import load_config
from lib.logger import get_logger

logger = get_logger('direction_expander')

environ = os.environ.get
OMLX_BASE = environ('OMLX_BASE', 'http://localhost:8000/v1')
OMLX_MODEL = environ('OMLX_MODEL', 'Qwen3.5-4B-MLX-4bit')

SYSTEM_PROMPT = (
    "你是一个专业的角色设计师助理。用户会给你一个角色的\"粗方向\"（一两句话的粗略描述），\n"
    "你需要将它扩展为一段丰富、详细、可执行的自然语言角色描述。\n\n"
    "扩展规则：\n"
    "1. 保留用户原始描述中的所有信息，不得修改或扭曲\n"
    "2. 补充合理细节：面部特征（五官形态、脸型、肤质）、发型发色、体型、身高体态、服装风格、标志性配件\n"
    "3. 补充性格气质和声音特征\n"
    "4. 如果用户给出了具体的细节关键词（如\"国字脸\"\"单眼皮\"\"蓝牙耳机\"），保留并丰富它们\n"
    "5. 如果用户描述已经足够详细（超过80字），则基本照原样输出，仅微调润色\n"
    "6. 描述要写实，不要说\"动漫风格\"——写实角色以真人摄影为参照\n"
    "7. 输出**只有**角色描述本身，不要带任何前缀、标签或解释\n\n"
    "示例输入：\n"
    "\"一个运动型中年男性，喜欢户外跑步\"\n\n"
    "示例输出：\n"
    "\"一位约42岁的中国男性，体型健壮肩宽，黑色短发利落，国字脸单眼皮眼尾微垂，"
    "鼻梁挺直，神态沉稳内敛，肤色健康自然偏小麦色。"
    "身穿深灰色拉链运动夹克配白色速干内衬。"
    "整体气质坚毅沉稳，给人可靠踏实的感觉。声音偏向成熟稳重的中低音。\""
)


class DirectionExpander:
    """将粗方向扩展为详细自然语言描述"""

    def __init__(self):
        self._base_url = OMLX_BASE
        self._model = OMLX_MODEL

    def expand(self, direction: str) -> str:
        """将粗方向扩展为详细自然语言描述。

        Args:
            direction: 用户输入的粗方向，如"运动型中年男性"

        Returns:
            扩展后的完整角色描述字符串

        扩展策略:
        - 空输入 → 返回空字符串
        - 超过80字 → 已足够详细，直接使用（log info）
        - 80字以内 → 调用本地 LLM 扩展（异常时回退到原始方向）
        """
        if not direction or not direction.strip():
            return ''
        if len(direction) > 80:
            logger.info('方向描述已足够详细（>80字），直接使用')
            return direction.strip()
        try:
            return self._call_llm(direction)
        except Exception as e:
            logger.warning(f'LLM 扩展失败 ({e})，回退到直接使用原始方向')
            return direction.strip()

    def _call_llm(self, direction: str) -> str:
        """调用本地 oMLX LLM 扩展方向描述。

        Args:
            direction: 原始方向描述

        Returns:
            LLM 返回的角色详细描述，去除首尾空白

        Raises:
            网络/API/解析异常 — 由调用者处理
        """
        import httpx

        payload = {
            'model': self._model,
            'messages': [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': direction},
            ],
            'temperature': 0.7,
            'max_tokens': 500,
        }

        resp = httpx.post(
            f'{self._base_url}/chat/completions',
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        return content.strip()


if __name__ == '__main__':
    expander = DirectionExpander()
    test_inputs = [
        '一个运动型中年男性',
        '一位28岁的城市程序员，黑短发，戴细框金属眼镜',
    ]
    for inp in test_inputs:
        print(f'\n输入: {inp}')
        print(f'输出: {expander.expand(inp)}')

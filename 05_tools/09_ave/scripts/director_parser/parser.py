"""

AVE 01_director_parser — 文案 → 导演脚本 YAML

流程:
  1. 读取文案文本
  2. 调用本地 oMLX (Qwen3.5) 解析 → 结构化 segments
  3. 调用 schemas.py 校验
  4. 输出 director_script.yaml

本地 LLM: http://localhost:8000/v1/chat/completions
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import os
import yaml
from pathlib import Path
from typing import Optional

from lib.logger import get_logger
from .schemas import DirectorScript, validate_script

logger = get_logger("director_parser")

# 本地 oMLX 配置
OMLX_URL = "http://localhost:8000/v1/chat/completions"
OMLX_MODEL = "Qwen3.5-4B-MLX-4bit"
OMLX_API_KEY = "omlx"


def parse_script(
    script_path: str,
    style: str = "knowledge_lecture",
    output_path: str = "director_script.yaml",
    use_llm: bool = True,
) -> str:
    """
    文案 → 导演脚本 YAML

    - script_path: 文案文件路径 (.txt)
    - style: 视频风格 (knowledge_lecture | bedtime_story | funny_talk | tech_review)
    - output_path: 输出的 YAML 路径
    - use_llm: 是否使用本地 LLM 解析 (False = 手动模板)

    返回: 生成的 YAML 路径
    """
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"文案文件不存在: {script_path}")

    with open(script_path, "r", encoding="utf-8") as f:
        script_text = f.read().strip()

    if not script_text:
        raise ValueError(f"文案内容为空: {script_path}")

    if use_llm:
        # 用本地 oMLX 解析
        script_data = _parse_with_llm(script_text, style)
    else:
        # 手动模板: 整段文案作为单 segment
        script_data = _manual_parse(script_text, style)

    # Pydantic 校验
    validated = validate_script(script_data)

    # 输出 YAML
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(
            validated.model_dump(mode="json"),
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )

    logger.info(f"导演脚本已生成: {output_path} ({len(validated.segments)} 段)")
    return output_path


def _parse_with_llm(script_text: str, style: str) -> dict:
    """调用本地 oMLX 解析文案为结构化数据"""
    import httpx

    prompt = f"""你是一个视频导演脚本生成器。将以下文案解析为结构化导演脚本。

风格: {style}

要求:
1. 按自然语义停顿分段 (每段6-30秒)
2. 为每段分配情绪描述
3. 为每段设计视觉素材搜索词 (中文关键词)
4. 为每段指定 BGM 段落 (intro/main/climax/outro)
5. BGM结构: intro(0-8s) → main(8-50s) → climax(50-65s) → outro(65-75s)
6. 输出纯 JSON，不要 markdown 包裹

文案:
{script_text}

输出 JSON 格式:
{{
  "meta": {{
    "style": "{style}",
    "voice": {{"provider": "volcano", "voice_id": "default", "default_emotion": "专业沉稳"}},
    "bgm": {{
      "genre": "cinematic", "tempo": 110, "mood": "inspirational",
      "structure": [{{"section": "intro"}}, {{"section": "main"}}, {{"section": "climax"}}, {{"section": "outro"}}]
    }},
    "output": {{"resolution": "1080x1920", "fps": 30}}
  }},
  "segments": [
    {{
      "id": 1,
      "text": "分段文案",
      "duration_sec": 8,
      "voice_emotion": "开场悬念，压低声音",
      "camera": "slow_zoom_in",
      "bgm_section": "intro",
      "material": {{"source": "pexels", "search": "中文搜索关键词"}},
      "subtitles": true
    }}
  ]
}}"""

    try:
        resp = httpx.post(
            OMLX_URL,
            json={
                "model": OMLX_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4096,
            },
            headers={"Authorization": f"Bearer {OMLX_API_KEY}"},
            timeout=120,
        )
        resp.raise_for_status()
        result = resp.json()
        content = result["choices"][0]["message"]["content"]

        # 清理可能的 markdown 包裹
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        if content.startswith("json"):
            content = content[4:]

        data = json.loads(content)
        data["meta"]["style"] = style
        logger.info(f"oMLX 解析完成: {len(data.get('segments', []))} 段")
        return data

    except httpx.ConnectError:
        logger.warning("oMLX 未运行，降级到手动模板模式")
        return _manual_parse(script_text, style)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"LLM 解析失败 ({e})，降级到手动模板")
        return _manual_parse(script_text, style)


def _manual_parse(script_text: str, style: str) -> dict:
    """手动模板: 整段文案作为一个 segment（降级方案）"""
    return {
        "meta": {
            "style": style,
            "voice": {"provider": "volcano", "voice_id": "default", "default_emotion": "专业沉稳"},
            "bgm": {
                "genre": "cinematic" if style != "funny_talk" else "upbeat",
                "tempo": 110,
                "mood": "inspirational",
                "structure": [
                    {"section": "intro"},
                    {"section": "main"},
                    {"section": "climax"},
                    {"section": "outro"},
                ],
            },
            "output": {"resolution": "1080x1920", "fps": 30},
        },
        "segments": [
            {
                "id": 1,
                "text": script_text,
                "duration_sec": max(15, min(len(script_text) * 0.2, 120)),
                "voice_emotion": "正常讲述",
                "camera": "static",
                "bgm_section": "main",
                "material": {"source": "pexels", "search": style},
                "subtitles": True,
            }
        ],
    }

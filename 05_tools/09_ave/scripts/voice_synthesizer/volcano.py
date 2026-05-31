"""

AVE 02_voice_synthesizer — 火山引擎豆包语音 2.0 TTS

API 文档:
  豆包语音合成 2.0 (火山引擎)
  需 AK/SK 签名认证

注意:
  access_token 和 app_id 需从火山引擎语音控制台获取
  如果使用方舟(ARK)平台的 OpenAI 兼容接口，需创建 endpoint 获取 API Key
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

from lib.logger import get_logger

logger = get_logger("volcano")

CACHE_DIR = Path(os.environ.get("AVE_CACHE_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local/tools/ave/cache")))

# 火山引擎 TTS API
TTS_URL = "https://openspeech.bytedance.com/api/v1/tts"


def synthesize(
    text: str,
    output_path: str = "output.wav",
    access_key_id: str = "",
    secret_access_key: str = "",
    app_id: str = "",
    access_token: str = "",
    voice_type: str = "BV001_V2",  # 默认中文女声
    emotion: str = "happy",
    speed: float = 1.0,
    pitch: float = 1.0,
    volume: float = 1.0,
) -> str:
    """
    火山引擎豆包语音 TTS 合成

    参数:
      text: 合成文本
      output_path: 输出 WAV 路径
      access_key_id: 火山引擎 AK
      secret_access_key: 火山引擎 SK
      app_id: 语音合成应用 ID (控制台获取)
      access_token: 访问令牌 (控制台获取)
      voice_type: 音色
      emotion: 情绪 (happy/sad/angry/soothing/calm/...)
      speed: 语速 0.5-2.0
      pitch: 音调 0.5-2.0
      volume: 音量 0.0-1.0

    两种认证方式 (任选其一):
      方式A: app_id + access_token (简单令牌)
      方式B: access_key_id + secret_access_key (AK/SK 签名)

    返回: output_path
    """
    # 方式A: access_token 优先
    if access_token and app_id:
        return _synthesize_token(text, output_path, app_id, access_token, voice_type, emotion, speed, pitch, volume)

    # 方式B: AK/SK 签名
    if access_key_id and secret_access_key:
        return _synthesize_aksk(text, output_path, access_key_id, secret_access_key, voice_type, emotion, speed, pitch, volume)

    raise ValueError("缺少认证信息: 请提供 access_token+app_id 或 access_key_id+secret_access_key")


def _synthesize_token(
    text: str, output_path: str,
    app_id: str, access_token: str,
    voice_type: str, emotion: str,
    speed: float, pitch: float, volume: float,
) -> str:
    """使用 access_token 认证"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "app": {"appid": app_id, "token": access_token, "cluster": "volcano_tts"},
        "user": {"uid": "ave_user"},
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "text_type": "plain",
            "operation": "query",
            "voice_type": voice_type,
            "speed_ratio": speed,
            "pitch_ratio": pitch,
            "volume_ratio": volume,
            "emotion": emotion,
        },
    }

    try:
        resp = httpx.post(TTS_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 3000:
            logger.error(f"TTS 错误: {data.get('message', '')}")
            raise RuntimeError(f"TTS 失败: {data.get('code')} - {data.get('message')}")

        audio_data = data.get("data", "")
        if audio_data:
            import base64
            audio_bytes = base64.b64decode(audio_data)
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            logger.info(f"TTS 完成: {output_path} ({len(audio_bytes)//1024}KB)")
            return output_path
        else:
            raise RuntimeError("TTS 返回空音频数据")

    except httpx.HTTPStatusError as e:
        logger.error(f"TTS HTTP 错误: {e.response.status_code} - {e.response.text[:200]}")
        raise


def _synthesize_aksk(
    text: str, output_path: str,
    access_key_id: str, secret_access_key: str,
    voice_type: str, emotion: str,
    speed: float, pitch: float, volume: float,
) -> str:
    """使用 AK/SK 签名认证 (AWS SigV4 风格)"""
    # 火山引擎签名算法
    date_str = datetime.utcnow().strftime("%Y%m%d")
    body = json.dumps({
        "app": {"appid": "", "cluster": "volcano_tts"},
        "user": {"uid": "ave_user"},
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "text_type": "plain",
            "operation": "query",
            "voice_type": voice_type,
            "speed_ratio": speed,
            "pitch_ratio": pitch,
            "volume_ratio": volume,
            "emotion": emotion,
        },
    })

    # 构建签名
    timestamp = str(int(time.time()))
    # 简化版: 用 basic auth 编码 AK/SK
    import base64
    auth_str = base64.b64encode(f"{access_key_id}:{secret_access_key}".encode()).decode()

    headers = {
        "Authorization": f"Basic {auth_str}",
        "Content-Type": "application/json",
        "Content-MD5": hashlib.md5(body.encode()).hexdigest().upper(),
    }

    try:
        resp = httpx.post(TTS_URL, data=body, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 3000:
            logger.error(f"TTS 错误: {data.get('message','')}")
            raise RuntimeError(f"TTS 失败: {data.get('code')}")

        audio_data = data.get("data", "")
        if audio_data:
            audio_bytes = base64.b64decode(audio_data)
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            logger.info(f"TTS AK/SK 完成: {output_path} ({len(audio_bytes)//1024}KB)")
            return output_path

    except Exception as e:
        logger.error(f"TTS AK/SK 失败: {e}")
        raise

"""
AVE 02_voice_synthesizer — 阿里云 CosyVoice TTS

使用官方 dashscope SDK 调用
文档: https://help.aliyun.com/zh/model-studio/cosyvoice-python-sdk

模型: cosyvoice-v3.5-plus
音色: 复刻音色 (百炼控制台训练)
指令: 自然语言控制情感、语速等 (v3.5-plus 支持任意指令)

字级时间戳: synthesize_with_timestamps() 返回 (wav_path, word_timestamps)
  word_timestamps = [{"text": str, "begin_time": int(ms), "end_time": int(ms)}, ...]
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import os
from pathlib import Path

from lib.logger import get_logger

logger = get_logger("cosyvoice")

CACHE_DIR = Path(os.environ.get("AVE_CACHE_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local/tools/ave/cache")))


# ── 字级时间戳回调 ──────────────────────────────────────────

class _WordTimestampCollector:
    """收集 CosyVoice 回调中的字级时间戳"""

    def __init__(self):
        self.audio_chunks = []
        self.words = []
        self.sentences = []
        self._done = False

    def on_data(self, data: bytes):
        self.audio_chunks.append(data)

    def on_event(self, message: str):
        data = json.loads(message)
        sentence = data.get("payload", {}).get("output", {}).get("sentence", {})
        if not sentence:
            return
        self.sentences.append(sentence)
        self.words.extend(sentence.get("words", []))

    def on_complete(self):
        self._done = True

    def wait_done(self, timeout: float = 30.0):
        """等待合成完成"""
        import time
        for _ in range(int(timeout / 0.1)):
            if self._done:
                return
            time.sleep(0.1)

    def get_audio(self) -> bytes:
        return b"".join(self.audio_chunks)

    def get_word_timestamps(self) -> list[dict]:
        return [{"text": w["text"], "begin_time": w["begin_time"], "end_time": w["end_time"]}
                for w in self.words]


def synthesize(
    text: str,
    output_path: str = "output.wav",
    api_key: str = "",
    voice_id: str = "",
    emotion: str = "normal",
    speed: float = 1.0,
) -> str:
    """基础合成: 仅返回音频文件 (兼容旧接口)"""
    try:
        audio, _ = _synthesize_internal(text, api_key, voice_id, emotion, speed, enable_timestamps=False)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio)
        logger.info(f"✅ TTS 完成: {output_path} ({len(audio)//1024}KB)")
        return output_path
    except Exception as e:
        logger.error(f"CosyVoice TTS 失败: {e}")
        raise


def synthesize_with_timestamps(
    text: str,
    output_path: str = "output.wav",
    api_key: str = "",
    voice_id: str = "",
    emotion: str = "normal",
    speed: float = 1.0,
) -> tuple[str, list[dict]]:
    """
    合成 + 字级时间戳

    返回:
      (output_path, word_timestamps)
      word_timestamps = [{"text": "今", "begin_time": 80, "end_time": 200}, ...]
      begin/end_time 单位为毫秒
    """
    try:
        audio, collector = _synthesize_internal(
            text, api_key, voice_id, emotion, speed, enable_timestamps=True
        )
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio)

        words = collector.get_word_timestamps()
        logger.info(f"✅ TTS+时间戳: {output_path} ({len(audio)//1024}KB, {len(words)} 字)")
        return output_path, words
    except Exception as e:
        logger.error(f"CosyVoice TTS+时间戳 失败: {e}")
        raise


def _synthesize_internal(
    text: str, api_key: str, voice_id: str,
    emotion: str, speed: float, enable_timestamps: bool,
) -> tuple[bytes, _WordTimestampCollector | None]:
    """内部合成函数"""
    if not api_key:
        raise ValueError("阿里云 API Key 未配置")
    if not text.strip():
        raise ValueError("合成文本不能为空")

    instruction = _build_instruction(emotion, speed)
    logger.info(f"CosyVoice: {text[:30]}... (emotion={emotion}, speed={speed}, timestamps={enable_timestamps})")

    import dashscope
    from dashscope.audio.tts_v2 import SpeechSynthesizer, ResultCallback

    dashscope.api_key = api_key

    if enable_timestamps:
        collector = _WordTimestampCollector()

        class Callback(ResultCallback):
            def on_data(self, data: bytes):
                collector.on_data(data)
            def on_event(self, message: str):
                collector.on_event(message)
            def on_open(self): pass
            def on_complete(self):
                collector.on_complete()
            def on_error(self, msg: str):
                logger.error(f"TTS 错误: {msg}")
                collector._done = True
            def on_close(self): pass

        synth = SpeechSynthesizer(
            model="cosyvoice-v3.5-plus",
            voice=voice_id,
            callback=Callback(),
            instruction=instruction,
            additional_params={"word_timestamp_enabled": True},
        )
        synth.call(text)
        collector.wait_done()
        logger.debug(f"  TTS 收集完成: {len(collector.audio_chunks)} 块, {len(collector.words)} 字")
        return collector.get_audio(), collector
    else:
        synth = SpeechSynthesizer(
            model="cosyvoice-v3.5-plus",
            voice=voice_id,
            instruction=instruction,
        )
        audio = synth.call(text)
        return audio, None


def _build_instruction(emotion: str, speed: float) -> str:
    """构建情绪控制指令"""
    emotion_map = {
        "normal": "请用自然、平稳的语气讲述。",
        "happy": "请用开心、愉悦的语气，声音明亮。",
        "sad": "请用悲伤、低沉的语气，语速稍慢。",
        "angry": "请用愤怒、激动的语气，声音有力。",
        "soothing": "请用温和、舒缓的语气，像在讲睡前故事。",
        "excited": "请用兴奋、激昂的语气，充满能量。",
        "mystery": "请用悬疑、压低声音的语气，像在讲一个秘密。",
        "professional": "请用专业、沉稳的语气，语速适中。",
    }

    base = emotion_map.get(emotion, f"请用{emotion}的语气讲述。")

    if speed < 0.8:
        base += "语速放慢一些。"
    elif speed > 1.2:
        base += "语速加快一些。"

    # 限制 100 字符
    if len(base) > 100:
        base = base[:97] + "..."

    return base

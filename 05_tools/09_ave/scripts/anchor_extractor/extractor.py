"""

AVE 04_anchor_extractor — 双轨锚点提取

职责:
  1. 人声锚点: 检测人声活跃段(word-level timestamps)
  2. BGM 锚点: 检测节奏/情绪变化点(section boundaries)
  3. 输出 anchors.json: 供 composer 做画面切换时间参考

依赖:
  - librosa (本地 CPU 即可)
  - numpy
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from lib.logger import get_logger

logger = get_logger("anchor_extractor")


def extract_anchors(
    voice_path: str,
    bgm_path: str | None = None,
    output_path: str = "anchors.json",
) -> dict[str, Any]:
    """
    双轨锚点提取: 人声 + BGM → anchors.json

    - voice_path: 人声 WAV 路径
    - bgm_path: BGM 路径 (可选)
    - 返回: anchors dict

    anchors 格式:
    {
      "voice_anchors": [
        {"time": 1.2, "type": "word_start", "word": "今天"},
        {"time": 3.5, "type": "word_end", "word": "今天"},
        {"time": 5.0, "type": "silence", "duration": 0.3},
      ],
      "bgm_anchors": [
        {"time": 0.0, "section": "intro"},
        {"time": 8.0, "section": "main"},
        {"time": 50.0, "section": "climax"},
      ],
      "metadata": {
        "voice_duration_sec": 75.0,
        "bgm_duration_sec": 75.0,
        "sample_rate": 24000
      }
    }
    """
    import librosa

    anchors: dict[str, Any] = {
        "voice_anchors": [],
        "bgm_anchors": [],
        "metadata": {},
    }

    # ── 1. 人声锚点 ──
    if not os.path.exists(voice_path):
        raise FileNotFoundError(f"人声文件不存在: {voice_path}")

    y, sr = librosa.load(voice_path, sr=24000, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)
    anchors["metadata"]["voice_duration_sec"] = duration
    anchors["metadata"]["sample_rate"] = sr

    # 语音活动检测: 能量阈值法
    frame_length = int(sr * 0.025)  # 25ms 帧
    hop_length = int(sr * 0.010)    # 10ms 步进
    energy = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    threshold = np.mean(energy) * 0.3

    # 检测活跃段
    is_active = energy > threshold
    voice_anchors = []
    current_start = None

    for i, active in enumerate(is_active):
        time_sec = i * hop_length / sr
        if active and current_start is None:
            current_start = time_sec
            voice_anchors.append({"time": round(time_sec, 2), "type": "voice_start"})
        elif not active and current_start is not None:
            voice_anchors.append({"time": round(time_sec, 2), "type": "voice_end"})
            current_start = None

    if current_start is not None:
        voice_anchors.append({"time": round(duration, 2), "type": "voice_end"})

    anchors["voice_anchors"] = voice_anchors
    logger.info(f"人声锚点: {len(voice_anchors)} 个")

    # ── 2. BGM 锚点 (节奏变化检测) ──
    if bgm_path and os.path.exists(bgm_path):
        y_bgm, sr_bgm = librosa.load(bgm_path, sr=22050, mono=True)
        bgm_duration = librosa.get_duration(y=y_bgm, sr=sr_bgm)
        anchors["metadata"]["bgm_duration_sec"] = bgm_duration

        # 节奏检测 (tempo)
        tempo, beats = librosa.beat.beat_track(y=y_bgm, sr=sr_bgm)
        beat_times = librosa.frames_to_time(beats, sr=sr_bgm)

        bgm_anchors = [{"time": round(t, 2), "type": "beat"} for t in beat_times]
        anchors["bgm_anchors"] = bgm_anchors
        anchors["metadata"]["bgm_tempo"] = round(float(tempo), 1)
        logger.info(f"BGM 节奏: {float(tempo):.1f} BPM, {len(bgm_anchors)} 个拍点")
    else:
        logger.info("无 BGM 文件，跳过 BGM 锚点")

    # ── 写入文件 ──
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(anchors, f, ensure_ascii=False, indent=2)
    logger.info(f"锚点已写入: {output_path}")

    return anchors


def get_silence_periods(
    voice_path: str,
    min_silence_sec: float = 0.5,
) -> list[dict]:
    """
    检测人声中的静音段落 (可用于画面过渡时机)

    返回: [{"start": 1.0, "end": 1.5, "duration": 0.5}, ...]
    """
    import librosa

    y, sr = librosa.load(voice_path, sr=24000, mono=True)
    intervals = librosa.effects.split(
        y, top_db=30, frame_length=int(sr * 0.025), hop_length=int(sr * 0.010)
    )

    # intervals 是语音段，间隙就是静音段
    silence_periods = []
    prev_end = 0
    for start, end in intervals:
        gap = start / sr - prev_end
        if gap >= min_silence_sec:
            silence_periods.append({
                "start": round(prev_end, 2),
                "end": round(start / sr, 2),
                "duration": round(gap, 2),
            })
        prev_end = end / sr

    return silence_periods

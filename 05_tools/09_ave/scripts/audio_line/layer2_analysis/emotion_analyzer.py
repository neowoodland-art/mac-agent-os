"""
layer2_analysis/emotion_analyzer.py — 情绪/风格分析

输入：Stem 分离后的 vocals + 原曲
输出：情绪标签、风格描述、BPM 范围推荐
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import librosa
import numpy as np


@dataclass
class EmotionResult:
    """情绪分析结果"""
    mood: str = "neutral"                   # 主要情绪 (happy/sad/energetic/calm/neutral)
    energy: float = 0.5                     # 能量值 0~1
    valence: float = 0.5                    # 效价 (积极度) 0~1
    danceability: float = 0.5               # 舞曲性 0~1
    acousticness: float = 0.5               # 原声性 0~1
    tempo_category: str = "medium"          # 速度分类: slow/medium/fast
    description: str = ""                   # 自然语言风格描述
    dominant_frequencies: dict = field(default_factory=dict)  # 频率分布
    spectral_features: dict = field(default_factory=dict)     # 频谱特征


class EmotionAnalyzer:
    """
    音频情绪分析器

    基于频谱特征 + 节奏特征进行音乐情绪分类。
    纯 librosa 实现，不依赖外部模型。
    """

    def __init__(self):
        self.mood_map: dict[str, tuple[float, float, float]] = {
            # (energy_low, valence_low, dance_low) → label
            "energetic": (0.6, 0.5, 0.6),
            "happy": (0.4, 0.7, 0.5),
            "calm": (0.2, 0.4, 0.2),
            "sad": (0.2, 0.2, 0.2),
            "aggressive": (0.8, 0.3, 0.4),
            "neutral": (0.5, 0.5, 0.5),
        }

    def analyze(self, audio_path: str | Path, bpm: float = 0.0) -> EmotionResult:
        """
        分析音频情绪

        参数:
            audio_path: 音频路径 (可以是原始音频或 vocals stem)
            bpm: 可选的 BPM 值 (已检测到的)

        返回:
            EmotionResult
        """
        audio_path = Path(audio_path)
        print(f"  [emotion] 分析: {audio_path.name}")

        y, sr = librosa.load(str(audio_path), sr=None, mono=True)

        # — 1. 频谱特征 —
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]
        rms = librosa.feature.rms(y=y)[0]

        # — 2. 计算特征指标 —
        avg_centroid = float(np.mean(spectral_centroids))
        avg_rolloff = float(np.mean(spectral_rolloff))
        avg_bandwidth = float(np.mean(spectral_bandwidth))
        avg_zcr = float(np.mean(zero_crossing_rate))
        avg_rms = float(np.mean(rms))

        # — 3. 情绪分类 —
        # energy: RMS + ZCR + centroid
        energy = min(1.0, (avg_rms * 5 + avg_zcr * 2 + avg_centroid / 5000) / 3)
        energy = max(0.0, min(1.0, energy))

        # valence (积极度): ZCR 高 → 积极, centroid 高 → 明亮
        valence = min(1.0, (avg_zcr * 3 + avg_centroid / 3000) / 2)
        valence = max(0.0, min(1.0, valence))

        # danceability: 节奏清晰度 (BPM 在 100-130 之间最可舞)
        if bpm > 0:
            dance = 1.0 - abs(bpm - 120) / 80
        else:
            dance = 0.5 - abs(energy - 0.5) * 0.3
        danceability = max(0.0, min(1.0, dance))

        # acousticness: 原声性 (low bandwidth + low centroid)
        acousticness = max(0.0, 1.0 - (avg_bandwidth / 3000 + avg_centroid / 8000) / 2)

        # — 4. 情绪标签 —
        mood = self._classify_mood(energy, valence, danceability)

        # — 5. 速度分类 —
        if bpm > 0:
            tempo_category = "fast" if bpm >= 120 else ("slow" if bpm <= 80 else "medium")
        else:
            tempo_category = "medium"

        # — 6. 自然语言描述 —
        description = self._describe(mood, energy, tempo_category)

        # — 7. 频谱分布 —
        dominant_freqs = self._dominant_frequencies(spectral_centroids)
        spec_features = {
            "avg_centroid_hz": round(avg_centroid, 1),
            "avg_bandwidth_hz": round(avg_bandwidth, 1),
            "avg_zcr": round(float(avg_zcr), 4),
            "avg_rms": round(float(avg_rms), 4),
        }

        return EmotionResult(
            mood=mood,
            energy=round(energy, 3),
            valence=round(valence, 3),
            danceability=round(danceability, 3),
            acousticness=round(acousticness, 3),
            tempo_category=tempo_category,
            description=description,
            dominant_frequencies=dominant_freqs,
            spectral_features=spec_features,
        )

    # ---- 内部 ----

    def _classify_mood(self, energy: float, valence: float, dance: float) -> str:
        """基于能量/效价/舞曲性分类情绪"""
        scores = {}
        for label, (e_th, v_th, d_th) in self.mood_map.items():
            score = (
                (1.0 - abs(energy - e_th)) * 0.4 +
                (1.0 - abs(valence - v_th)) * 0.4 +
                (1.0 - abs(dance - d_th)) * 0.2
            )
            scores[label] = score
        return max(scores, key=scores.get)

    def _describe(self, mood: str, energy: float, tempo: str) -> str:
        """生成自然语言风格描述"""
        descs = {
            "energetic": f"充满活力的{tempo}速曲风，能量充沛",
            "happy": f"明快愉悦的{tempo}速曲风，情绪积极",
            "calm": f"舒缓平静的{tempo}速曲风，适合放松",
            "sad": f"忧伤低沉的{tempo}速曲风，情绪内敛",
            "aggressive": f"强劲有力的{tempo}速曲风，表现力强",
            "neutral": f"中性均衡的{tempo}速曲风",
        }
        return descs.get(mood, f"{mood}风格的{tempo}速曲风")

    def _dominant_frequencies(self, centroids: np.ndarray) -> dict:
        """分析频谱能量分布"""
        mean_c = float(np.mean(centroids))
        std_c = float(np.std(centroids))
        return {
            "mean_hz": round(mean_c, 1),
            "std_hz": round(std_c, 1),
            "range": f"{max(0, round(mean_c - std_c, 1))}-{round(mean_c + std_c, 1)} Hz",
        }

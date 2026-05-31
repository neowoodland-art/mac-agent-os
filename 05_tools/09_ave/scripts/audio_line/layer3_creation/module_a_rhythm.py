"""
layer3_creation/module_a_rhythm.py — 节奏重塑模块

功能：基于 Mubert/Mubert-like API 生成节奏/鼓点轨道
卡点改编的核心：原曲鼓点替换 → BPM 匹配 → 节奏增强
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RhythmResult:
    """节奏生成结果"""
    drum_track_path: str = ""               # 生成的鼓点音频路径
    bpm: float = 0.0                        # 实际 BPM
    genre: str = ""                          # 使用的风格
    duration: float = 0.0                    # 时长 (秒)
    api_used: str = ""                       # 使用的 API
    cost: float = 0.0                        # API 调用成本


class RhythmModule:
    """
    节奏重塑模块

    支持两种模式:
    1. Mubert API — 在线生成高质量鼓点 (需要 API key)
    2. 本地替代 — 用 librosa 节拍合成简单鼓点 (免费)
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.api_key = self.config.get("mubert", {}).get("api_key", "")
        self.base_url = self.config.get("mubert", {}).get(
            "base_url", "https://api.mubert.com/v2"
        )
        self.default_genre = self.config.get("mubert", {}).get(
            "default_genre", "electronic"
        )
        self.default_duration = self.config.get("mubert", {}).get(
            "default_duration", 30
        )
        self.timeout = self.config.get("mubert", {}).get("timeout", 60)

    def generate(
        self,
        bpm: float,
        genre: str = "",
        duration: float = 0.0,
        output_path: str | Path | None = None,
    ) -> RhythmResult:
        """
        生成节奏/鼓点轨道

        参数:
            bpm: 目标 BPM
            genre: 风格 (electronic/house/techno/hiphop/pop/rock)
            duration: 目标时长 (秒), 0=默认
            output_path: 输出路径

        返回:
            RhythmResult
        """
        genre = genre or self.default_genre
        duration = duration if duration > 0 else self.default_duration
        output_path = Path(output_path or f"./output/rhythm_{int(bpm)}_{genre}.wav")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"  [rhythm] 目标: BPM={bpm}  风格={genre}  时长={duration}s")

        if self.api_key:
            result = self._via_mubert(bpm, genre, duration, output_path)
        else:
            print(f"  [rhythm] 无 Mubert API key, 使用本地合成替代")
            result = self._local_fallback(bpm, duration, output_path)

        if output_path.exists():
            result.drum_track_path = str(output_path.resolve())
            size_mb = output_path.stat().st_size / 1_048_576
            print(f"  [rhythm] ✓ 输出: {output_path.name} ({size_mb:.1f} MB)")
        else:
            print(f"  [rhythm] ⚠ 输出文件不存在")

        return result

    # ---- Mubert API ----

    def _via_mubert(
        self, bpm: float, genre: str, duration: float, output_path: Path
    ) -> RhythmResult:
        """通过 Mubert API 生成"""
        result = RhythmResult(bpm=bpm, genre=genre, duration=duration, api_used="mubert")

        try:
            # Mubert API: POST /v2/track/render
            payload = json.dumps({
                "pat": self.api_key,
                "bpm": int(bpm),
                "genre": genre,
                "duration": int(duration),
                "format": "wav",
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self.base_url}/track/render",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            # 下载生成的音频
            if "data" in data and "url" in data["data"]:
                audio_url = data["data"]["url"]
                urllib.request.urlretrieve(audio_url, output_path)
                result.cost = data.get("data", {}).get("cost", 0.0)

        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
            print(f"  [rhythm] Mubert API 请求失败: {e}")
            print(f"  [rhythm] 回退到本地合成")
            return self._local_fallback(bpm, duration, output_path)

        return result

    # ---- 本地替代方案 ----

    def _local_fallback(
        self, bpm: float, duration: float, output_path: Path
    ) -> RhythmResult:
        """
        本地合成简单鼓点节奏

        用 librosa 的 clicks 功能生成节拍点击声，
        配合简单的频谱叠加模拟 kick + snare + hi-hat。
        """
        import librosa
        import numpy as np
        import soundfile as sf

        sr = 22050
        total_samples = int(duration * sr)
        beat_interval = int(60.0 / bpm * sr)  # 每拍采样数
        half_beat = beat_interval // 2

        # — 构建鼓点模式 (4/4 拍: kick on 1,3, snare on 2,4, hi-hat 8th notes) —
        audio = np.zeros(total_samples, dtype=np.float32)

        for beat_idx in range(int(duration * bpm / 60) + 1):
            pos = beat_idx * beat_interval
            if pos >= total_samples:
                break

            beat_in_bar = beat_idx % 4

            # Kick: beats 0, 2 (1st and 3rd beat)
            if beat_in_bar in (0, 2):
                kick = self._make_kick(sr, int(beat_interval * 0.4))
                end = min(pos + len(kick), total_samples)
                audio[pos:end] += kick[:end - pos] * 1.0

            # Snare: beats 1, 3 (2nd and 4th beat)
            if beat_in_bar in (1, 3):
                snare = self._make_snare(sr, int(beat_interval * 0.3))
                end = min(pos + len(snare), total_samples)
                audio[pos:end] += snare[:end - pos] * 0.8

            # Hi-hat: every half beat
            for off in (0, half_beat):
                hh_pos = pos + off
                if hh_pos < total_samples:
                    hh = self._make_hihat(sr, int(beat_interval * 0.15))
                    end = min(hh_pos + len(hh), total_samples)
                    audio[hh_pos:end] += hh[:end - hh_pos] * 0.3

        # 归一化
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak * 0.9

        sf.write(str(output_path), audio, sr)
        return RhythmResult(
            bpm=bpm,
            genre="local_fallback",
            duration=duration,
            drum_track_path=str(output_path.resolve()),
            api_used="local",
        )

    @staticmethod
    def _make_kick(sr: int, length: int) -> np.ndarray:
        """合成 kick 鼓声"""
        import numpy as np
        t = np.arange(length) / sr
        # 频率指数衰减 150→40Hz
        freq = 150 * np.exp(-t * 25)
        phase = 2 * np.pi * np.cumsum(freq) / sr
        return np.sin(phase) * np.exp(-t * 30)

    @staticmethod
    def _make_snare(sr: int, length: int) -> np.ndarray:
        """合成 snare 鼓声"""
        import numpy as np
        t = np.arange(length) / sr
        tone = np.sin(2 * np.pi * 200 * t)
        noise = np.random.randn(length) * 0.5
        return (tone + noise) * np.exp(-t * 20)

    @staticmethod
    def _make_hihat(sr: int, length: int) -> np.ndarray:
        """合成 hi-hat 声"""
        import numpy as np
        t = np.arange(length) / sr
        noise = np.random.randn(length)
        # 高通滤波
        filtered = noise * np.exp(-t * 60)
        return filtered * 0.5

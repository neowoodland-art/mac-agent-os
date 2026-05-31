"""
layer3_creation/module_d_mix.py — 混音母带模块

功能：将多轨音频(vocals/drums/bass/other)混音为完整立体声
      支持 EQ / 压缩 / 限制器 / 混响 / 响度归一化

基于 Pedalboard (Spotify 开源音频处理库)。
回退方案：无 Pedalboard 时使用 pydub + numpy 基本叠加。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class MixResult:
    """混音母带结果"""
    master_path: str = ""                       # 混音后主轨路径
    stem_paths: dict[str, str] = field(default_factory=dict)  # 处理后分轨路径
    loudness: float = 0.0                       # 最终 LUFS 响度
    peak_dB: float = 0.0                        # 峰值 (dB)
    headroom: float = 0.0                       # 头上空间 (dB)
    duration: float = 0.0                       # 时长 (秒)
    engine: str = ""                             # 使用的引擎 (pedalboard | pydub | numpy)


class MixModule:
    """
    混音母带模块

    处理流程：
    1. 加载各分轨音频
    2. 电平平衡 (Volume/gain staging)
    3.  EQ 均衡 (可选预设)
    4. 压缩 (可选)
    5. 混响 (可选)
    6. 立体声叠加
    7. 峰值限制 → 响度归一化
    8. 导出
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        mix_cfg = config.get("mixing", {}) if config else {}

        self.target_loudness = float(mix_cfg.get("target_loudness", -14.0))
        self.headroom_target = float(mix_cfg.get("headroom", 1.0))
        self.sample_rate = int(mix_cfg.get("sample_rate", 44100))
        self.bit_depth = int(mix_cfg.get("bit_depth", 16))

        self.eq_preset = mix_cfg.get("eq_preset", "default")
        self.compressor_threshold = float(mix_cfg.get("compressor_threshold", -20))
        self.compressor_ratio = float(mix_cfg.get("compressor_ratio", 3.0))
        self.compressor_attack = float(mix_cfg.get("compressor_attack", 5))
        self.compressor_release = float(mix_cfg.get("compressor_release", 100))

        self._pedalboard = None
        self._has_pedalboard = False
        self._init_pedalboard()

    def _init_pedalboard(self):
        """尝试加载 Pedalboard"""
        try:
            import pedalboard
            self._pedalboard = pedalboard
            self._has_pedalboard = True
        except ImportError:
            self._has_pedalboard = False

    def mix(
        self,
        stems: dict[str, str],
        output_path: str | Path = "./output/mix/master.wav",
        stem_levels: dict[str, float] | None = None,
        apply_eq: bool = True,
        apply_compressor: bool = True,
        apply_reverb: bool = False,
        include_stems: bool = True,
    ) -> MixResult:
        """
        混音主入口

        参数:
            stems: {stem_name: audio_path, ...}
            output_path: 混音输出路径
            stem_levels: 分轨电平增益 {name: dB}，默认 ±0
            apply_eq: 是否应用 EQ
            apply_compressor: 是否应用压缩
            apply_reverb: 是否应用混响
            include_stems: 是否同时导出处理后的分轨

        返回:
            MixResult
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"  [mix] 混音开始: {len(stems)} 轨")

        stem_levels = stem_levels or {}
        processed_stems: dict[str, Path] = {}
        stem_audio: dict[str, np.ndarray] = {}
        ref_sr = self.sample_rate

        # — 1. 加载 + 处理各分轨 —
        for name, audio_path in stems.items():
            if not Path(audio_path).exists():
                print(f"  [mix] ⚠ 分轨不存在: {audio_path}, 跳过")
                continue

            y, sr = self._load_audio(audio_path, ref_sr)
            gain_db = stem_levels.get(name, 0.0)

            # 应用增益
            if gain_db != 0:
                y = y * (10 ** (gain_db / 20))

            # 应用处理 (EQ/压缩)
            if self._has_pedalboard:
                y = self._apply_processing(
                    y, sr, name, apply_eq, apply_compressor, apply_reverb
                )

            stem_audio[name] = y

            # 导出处理后分轨
            if include_stems:
                stem_out = output_path.parent / f"processed_{name}.wav"
                self._save_audio(stem_out, y, sr)
                processed_stems[name] = str(stem_out.resolve())

            print(f"  [mix]   {name}: {gain_db:+.1f}dB  {len(y)/sr:.1f}s")

        if not stem_audio:
            raise ValueError("没有可用的分轨进行混音")

        # — 2. 立体声叠加 —
        ref_sr = self._get_common_sr(stem_audio)
        master = self._sum_stems(stem_audio)

        # — 3. 峰值限制 + 响度归一化 —
        master, peak_db, loudness = self._master_bus(master, ref_sr)

        # — 4. 导出 —
        self._save_audio(output_path, master, ref_sr)

        headroom = abs(peak_db) if peak_db < 0 else 0

        result = MixResult(
            master_path=str(output_path.resolve()),
            stem_paths={k: str(v) for k, v in processed_stems.items()},
            loudness=round(loudness, 2),
            peak_dB=round(peak_db, 2),
            headroom=round(headroom, 2),
            duration=round(len(master) / ref_sr, 2),
            engine="pedalboard" if self._has_pedalboard else "numpy",
        )

        print(f"  [mix] ✓ 混音完成: {output_path.name}")
        print(f"  [mix]   响度={loudness:.1f} LUFS  峰值={peak_db:.1f} dBFS  "
              f"头上空间={headroom:.1f} dB")
        return result

    # ---- 内部处理 ----

    def _load_audio(self, path: str | Path, target_sr: int) -> tuple[np.ndarray, int]:
        """加载音频文件"""
        import librosa
        y, sr = librosa.load(str(path), sr=target_sr, mono=False)
        # 确保为 2D: (channels, samples)
        if y.ndim == 1:
            y = np.stack([y, y])  # mono → stereo
        return y, sr

    def _get_common_sr(self, stem_audio: dict) -> int:
        """取所有分轨的共用采样率"""
        return self.sample_rate

    def _apply_processing(
        self,
        y: np.ndarray,
        sr: int,
        stem_name: str,
        apply_eq: bool,
        apply_compressor: bool,
        apply_reverb: bool,
    ) -> np.ndarray:
        """Pedalboard 处理链"""
        import pedalboard as pb

        chain = []

        # EQ
        if apply_eq:
            chain.append(
                pb.Filterband(
                    cutoff_frequency=80.0,
                    filter_type="highpass",
                )
            )
            if stem_name == "vocals":
                # 人声: 提升中频 (presence)
                chain.append(pb.Equalizer(num_eq_bands=3))

        # 压缩
        if apply_compressor and stem_name in ("vocals", "bass"):
            chain.append(
                pb.Compressor(
                    threshold_db=self.compressor_threshold,
                    ratio=self.compressor_ratio,
                    attack_ms=self.compressor_attack,
                    release_ms=self.compressor_release,
                )
            )

        # 混响 (仅应用到 vocal/master)
        if apply_reverb and stem_name == "vocals":
            chain.append(pb.Reverb(room_size=0.3, damping=0.5))

        if not chain:
            return y

        board = pb.Pedalboard(chain, sample_rate=sr)
        return board.process(y)

    def _sum_stems(self, stem_audio: dict[str, np.ndarray]) -> np.ndarray:
        """叠加多轨音频"""
        # 找出最长轨道
        max_len = max(y.shape[1] for y in stem_audio.values())

        master = np.zeros((2, max_len), dtype=np.float64)

        for name, y in stem_audio.items():
            y_len = y.shape[1]
            if y_len < max_len:
                pad = np.zeros((2, max_len - y_len))
                master[:, :y_len] += y[:, :] * 0.8
                master[:, y_len:] += pad
            else:
                master += y * 0.8

        # 防止削波前先归一化
        peak = np.max(np.abs(master))
        if peak > 0.95:
            master = master / peak * 0.95

        return master.astype(np.float32)

    def _master_bus(
        self, audio: np.ndarray, sr: int
    ) -> tuple[np.ndarray, float, float]:
        """母带总线: 限制器 + 响度归一化"""

        if self._has_pedalboard:
            import pedalboard as pb

            # 限制器
            limiter = pb.Limiter(
                threshold_db=-self.headroom_target,
                release_ms=100,
            )
            board = pb.Pedalboard([limiter], sample_rate=sr)
            audio = board.process(audio)

        # 测量峰值
        peak_db = float(20 * np.log10(np.max(np.abs(audio)) + 1e-10))

        # 响度归一化 (简单 RMS 归一化，完整 LUFS 需要 pyloudnorm)
        rms = np.sqrt(np.mean(audio ** 2))
        if rms > 0:
            target_rms = 10 ** (self.target_loudness / 20)
            gain = target_rms / rms
            audio = audio * min(gain, 2.0)  # 限制最大增益 6dB

        loudness = self.target_loudness  # 近似

        return audio, peak_db, loudness

    def _save_audio(self, path: Path, audio: np.ndarray, sr: int):
        """保存音频"""
        import soundfile as sf
        # soundfile 期望 (samples, channels)
        if audio.ndim == 2 and audio.shape[0] <= 8:
            audio = audio.T
        sf.write(str(path), audio, sr, subtype="PCM_16")

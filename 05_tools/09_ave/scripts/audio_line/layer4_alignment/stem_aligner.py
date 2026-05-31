"""
layer4_alignment/stem_aligner.py — 分轨时间对齐模块

功能：将各分轨时间伸缩到目标 BPM / 目标时长
核心场景：卡点改编时原曲 BPM -> 目标 BPM 的时间映射

支持方法:
1. librosa.effects.time_stretch (相位声码器)
2. 节拍网格对齐 (beat grid snapping)
3. 交叉淡入淡出连接 (拼接时)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np


@dataclass
class AlignResult:
    """对齐结果"""
    aligned_paths: dict[str, str] = field(default_factory=dict)  # {stem: path}
    original_duration: float = 0.0
    target_duration: float = 0.0
    stretch_ratios: dict[str, float] = field(default_factory=dict)  # {stem: ratio}
    method_used: str = ""

    @property
    def is_aligned(self) -> bool:
        return len(self.aligned_paths) > 0


class StemAligner:
    """
    分轨时间对齐器

    将分轨从原始节奏伸缩到目标节奏。
    支持独立对齐每轨或统一对齐。
    """

    STRETCH_METHODS: list[str] = ["phase_vocoder", "librosa", "wsola"]

    def __init__(
        self,
        method: str = "phase_vocoder",
        crossfade: float = 0.05,
        time_tolerance: float = 0.1,
    ):
        if method not in self.STRETCH_METHODS:
            raise ValueError(f"不支持的时间伸缩方法 '{method}', 可选: {self.STRETCH_METHODS}")
        self.method = method
        self.crossfade = crossfade
        self.time_tolerance = time_tolerance

    def align_to_bpm(
        self,
        stems: dict[str, str],
        source_bpm: float,
        target_bpm: float,
        output_dir: str | Path = "./output/aligned/",
        align_separately: bool = False,
    ) -> AlignResult:
        """
        按 BPM 比率对齐分轨

        参数:
            stems: {stem_name: audio_path}
            source_bpm: 原曲 BPM
            target_bpm: 目标 BPM
            output_dir: 输出目录
            align_separately: True=每轨独立比例, False=统一比例

        返回:
            AlignResult
        """
        if target_bpm <= 0 or source_bpm <= 0:
            raise ValueError("BPM 必须 > 0")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        ratio = target_bpm / source_bpm
        print(f"  [align] BPM 对齐: {source_bpm} → {target_bpm} (比率: {ratio:.4f})")

        return self._align(
            stems, ratio, output_dir, align_separately
        )

    def align_to_duration(
        self,
        stems: dict[str, str],
        source_duration: float,
        target_duration: float,
        output_dir: str | Path = "./output/aligned/",
        align_separately: bool = False,
    ) -> AlignResult:
        """
        按时长比例对齐分轨

        参数:
            stems: {stem_name: audio_path}
            source_duration: 原曲时长 (秒)
            target_duration: 目标时长 (秒)
            output_dir: 输出目录
            align_separately: True=每轨独立

        返回:
            AlignResult
        """
        if target_duration <= 0 or source_duration <= 0:
            raise ValueError("时长必须 > 0")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        ratio = target_duration / source_duration
        print(f"  [align] 时长对齐: {source_duration:.1f}s → {target_duration:.1f}s"
              f" (比率: {ratio:.4f})")

        return self._align(
            stems, ratio, output_dir, align_separately
        )

    def align_with_beats(
        self,
        stems: dict[str, str],
        source_beats: list[float],
        target_beats: list[float],
        output_dir: str | Path = "./output/aligned/",
    ) -> AlignResult:
        """
        按节拍网格对齐 (精确卡点)

        将源节拍映射到目标节拍位置，逐段伸缩。

        参数:
            stems: {stem_name: audio_path}
            source_beats: 原节奏拍列表 (秒)
            target_beats: 目标节拍列表 (秒)
            output_dir: 输出目录

        返回:
            AlignResult
        """
        if not source_beats or not target_beats:
            raise ValueError("节拍列表不能为空")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"  [align] 节拍网格对齐: {len(source_beats)} → {len(target_beats)} 拍")

        aligned = {}
        stretch_ratios = {}

        for stem_name, audio_path in stems.items():
            if not Path(audio_path).exists():
                print(f"  [align] ⚠ 分轨不存在: {audio_path}, 跳过")
                continue

            out_path = output_dir / f"aligned_{stem_name}.wav"
            result_path = self._beat_grid_stretch(
                str(audio_path), source_beats, target_beats, str(out_path)
            )
            if result_path:
                aligned[stem_name] = result_path
                stretch_ratios[stem_name] = len(target_beats) / len(source_beats)

        return AlignResult(
            aligned_paths=aligned,
            original_duration=source_beats[-1] if source_beats else 0,
            target_duration=target_beats[-1] if target_beats else 0,
            stretch_ratios=stretch_ratios,
            method_used="beat_grid",
        )

    # ---- 内部 ----

    def _align(
        self,
        stems: dict[str, str],
        ratio: float,
        output_dir: Path,
        separate: bool,
    ) -> AlignResult:
        """通用对齐"""
        aligned = {}
        stretch_ratios = {}

        # — 加载第一轨获取原时长 —
        first_path = next(iter(stems.values()))
        y_ref, sr_ref = self._load_audio(first_path)
        orig_duration = len(y_ref) / sr_ref

        for stem_name, audio_path in stems.items():
            if not Path(audio_path).exists():
                print(f"  [align] ⚠ 分轨不存在: {audio_path}, 跳过")
                continue

            out_path = output_dir / f"aligned_{stem_name}.wav"

            if separate:
                # 独立对齐：每轨先测实际时长再计算比例
                y, sr = self._load_audio(audio_path)
                actual_duration = len(y) / sr
                target_dur = actual_duration * ratio
                actual_ratio = target_dur / actual_duration
            else:
                actual_ratio = ratio

            result_path = self._time_stretch(
                str(audio_path), actual_ratio, str(out_path)
            )
            if result_path:
                aligned[stem_name] = result_path
                stretch_ratios[stem_name] = actual_ratio

        return AlignResult(
            aligned_paths=aligned,
            original_duration=orig_duration,
            target_duration=orig_duration * ratio,
            stretch_ratios=stretch_ratios,
            method_used=self.method,
        )

    def _time_stretch(self, input_path: str, ratio: float, output_path: str) -> str | None:
        """
        时间伸缩

        参数:
            input_path: 输入音频路径
            ratio: 伸缩比 (>1 变快/缩短, <1 变慢/拉长)
            output_path: 输出路径

        返回:
            输出路径，失败返回 None
        """
        if abs(ratio - 1.0) < 0.001:
            # 无需伸缩: 直接复制
            import shutil
            shutil.copy2(input_path, output_path)
            return output_path

        print(f"  [align]   伸缩: ratio={ratio:.4f}")

        try:
            y, sr = self._load_audio(input_path)

            if self.method == "librosa":
                import librosa
                y_stretched = librosa.effects.time_stretch(y, rate=ratio)
            elif self.method == "phase_vocoder":
                # 用相位声码器
                y_stretched = self._phase_vocoder_stretch(y, ratio)
            else:  # wsola
                y_stretched = self._wsola_stretch(y, ratio)

            self._save_audio(output_path, y_stretched, sr)
            return output_path

        except Exception as e:
            print(f"  [align] ⚠ 伸缩失败: {e}")
            # 回退: 复制原文件
            import shutil
            shutil.copy2(input_path, output_path)
            return output_path

    def _beat_grid_stretch(
        self,
        audio_path: str,
        source_beats: list[float],
        target_beats: list[float],
        output_path: str,
    ) -> str | None:
        """
        逐段节拍网格伸缩

        将源节拍分段，每段分别伸缩到目标节拍间隔。
        """
        try:
            y, sr = self._load_audio(audio_path)

            # 限制处理范围
            max_beats = min(len(source_beats), len(target_beats))
            if max_beats < 2:
                import shutil
                shutil.copy2(audio_path, output_path)
                return output_path

            segments = []
            for i in range(max_beats - 1):
                s_start = int(source_beats[i] * sr)
                s_end = int(source_beats[i + 1] * sr)
                t_len = target_beats[i + 1] - target_beats[i]
                s_len = source_beats[i + 1] - source_beats[i]

                if s_len <= 0 or t_len <= 0:
                    continue

                segment = y[..., s_start:s_end] if y.ndim == 1 else y[:, s_start:s_end]
                if segment.size == 0:
                    continue

                ratio = s_len / t_len  # 注意: librosa 的 stretch 反向
                stretched = librosa.effects.time_stretch(
                    np.asfortranarray(segment), rate=1/ratio
                )

                segments.append(stretched)

            if not segments:
                import shutil
                shutil.copy2(audio_path, output_path)
                return output_path

            # 拼接 (带交叉淡入淡出)
            result = self._crossfade_join(segments, sr)
            self._save_audio(output_path, result, sr)
            return output_path

        except Exception as e:
            print(f"  [align] ⚠ 节拍网格对齐失败: {e}")
            import shutil
            shutil.copy2(audio_path, output_path)
            return output_path

    def _phase_vocoder_stretch(self, y: np.ndarray, ratio: float) -> np.ndarray:
        """相位声码器实现的时间伸缩"""
        from librosa.core import phase_vocoder
        from librosa import stft, istft

        D = stft(y)
        D_stretched = phase_vocoder(D, rate=ratio)
        y_stretched = istft(D_stretched)
        return y_stretched

    def _wsola_stretch(self, y: np.ndarray, ratio: float) -> np.ndarray:
        """WSOLA 时间伸缩 (librosa 回退)"""
        import librosa
        return librosa.effects.time_stretch(y, rate=ratio)

    def _crossfade_join(
        self, segments: list[np.ndarray], sr: int
    ) -> np.ndarray:
        """带交叉淡入淡出的音频拼接"""
        if len(segments) == 1:
            return segments[0]

        fade_len = int(self.crossfade * sr)
        # 确保所有段 mono (1D)
        segments_1d = []
        for seg in segments:
            if seg.ndim > 1:
                seg = np.mean(seg, axis=0)
            segments_1d.append(seg)

        result = segments_1d[0]
        for seg in segments_1d[1:]:
            if len(result) < fade_len or len(seg) < fade_len:
                result = np.concatenate([result, seg])
                continue

            fade_out = np.linspace(1, 0, fade_len)
            fade_in = np.linspace(0, 1, fade_len)

            cross_start = len(result) - fade_len
            result[cross_start:] *= fade_out
            seg[:fade_len] *= fade_in

            result = np.concatenate([
                result[:cross_start],
                result[cross_start:] + seg[:fade_len],
                seg[fade_len:],
            ])

        return result

    @staticmethod
    def _load_audio(path: str) -> tuple[np.ndarray, int]:
        """加载音频"""
        import librosa
        return librosa.load(path, sr=None, mono=True)

    @staticmethod
    def _save_audio(path: str, y: np.ndarray, sr: int):
        """保存音频"""
        import soundfile as sf
        sf.write(path, y, sr)

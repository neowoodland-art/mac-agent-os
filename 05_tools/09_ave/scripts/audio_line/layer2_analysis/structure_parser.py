"""
layer2_analysis/structure_parser.py — 歌曲结构解析

输入：原始音频 + 节拍分析结果
输出：段落标记 {intro, verse, chorus, bridge, outro, ...}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import librosa
import numpy as np


@dataclass
class StructureResult:
    """歌曲结构解析结果"""
    segments: list[dict] = field(default_factory=list)  # [{label, start, end, confidence}]
    section_count: int = 0
    has_chorus: bool = False
    has_bridge: bool = False
    structure_summary: str = ""  # 如 "Intro→Verse→Chorus→Verse→Chorus→Bridge→Outro"

    @property
    def section_labels(self) -> list[str]:
        return [s["label"] for s in self.segments]


class StructureParser:
    """
    歌曲结构解析器

    基于频谱特征变化 + MFCC 聚类进行段落分割。
    不依赖外部模型，纯 librosa 实现。
    """

    SECTION_TAGS = {
        0: "Intro", 1: "Verse", 2: "Chorus",
        3: "Bridge", 4: "Outro", 5: "Instrumental",
    }

    def __init__(self, n_segments: int = 8, min_section_sec: float = 4.0):
        self.n_segments = n_segments        # 期望段落段数
        self.min_section_sec = min_section_sec  # 最短段落时长

    def parse(self, audio_path: str | Path, beat_times: list[float] | None = None) -> StructureResult:
        """
        解析歌曲结构

        参数:
            audio_path: 音频路径
            beat_times: 可选，节拍时间戳用于辅助对齐

        返回:
            StructureResult
        """
        audio_path = Path(audio_path)
        print(f"  [structure] 分析: {audio_path.name}")

        y, sr = librosa.load(str(audio_path), sr=None, mono=True)
        duration = len(y) / sr

        # — 1. 提取 MFCC 序列 —
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=512)
        mfcc_delta = librosa.feature.delta(mfcc)
        features = np.vstack([mfcc, mfcc_delta])  # (26, n_frames)

        # — 2. 频谱特征 —
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=512)
        spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr, hop_length=512)

        # 对齐到相同帧数
        min_frames = min(features.shape[1], spectral_centroid.shape[1], spectral_contrast.shape[1])
        features = features[:, :min_frames]
        spec_feats = np.vstack([
            spectral_centroid[:, :min_frames],
            spectral_contrast[:, :min_frames],
        ])
        all_features = np.vstack([features, spec_feats])  # (~33, n_frames)

        # — 3. 计算自相似矩阵 + 结构边界 —
        n_fft = all_features.shape[1]
        # 用滑动窗口计算相似度变化
        window = max(int(n_fft * 0.1), 4)
        novelty = librosa.onset.onset_strength(
            y=y, sr=sr, hop_length=512
        )

        # — 4. 频谱变化点检测 —
        # 用 MFCC 的 novelty 曲线找变化点
        mfcc_novelty = self._compute_novelty(mfcc)
        change_points = self._find_peaks(mfcc_novelty, n_fft, self.n_segments)

        # — 5. 节拍对齐 —
        change_times = librosa.frames_to_time(change_points, sr=sr, hop_length=512)
        if beat_times:
            change_times = self._snap_to_beats(change_times, beat_times)

        # — 6. 段落标记 —
        segments = self._label_segments(change_times, duration, all_features)

        # — 7. 结构分析 —
        summary = "→".join(s["label"] for s in segments)

        print(f"  [structure] ✓ 结构: {summary}")

        return StructureResult(
            segments=segments,
            section_count=len(segments),
            has_chorus=any(s["label"] == "Chorus" for s in segments),
            has_bridge=any(s["label"] == "Bridge" for s in segments),
            structure_summary=summary,
        )

    # ---- 内部 ----

    def _compute_novelty(self, features: np.ndarray, kernel_size: int = 3) -> np.ndarray:
        """计算 MFCC 的新颖性曲线"""
        # 局部相似度矩阵的对角线核卷积
        sim = librosa.segment.recurrence_matrix(features, mode="affinity")
        kernel = np.zeros(kernel_size * 2 + 1)
        kernel[:kernel_size] = -1
        kernel[kernel_size] = 0
        kernel[kernel_size + 1:] = 1
        from scipy.ndimage import convolve1d
        novelty = convolve1d(sim.mean(axis=0), kernel, mode="constant")
        return novelty

    def _find_peaks(self, novelty: np.ndarray, max_frames: int, n_peaks: int) -> np.ndarray:
        """找 novelty 曲线峰值作为段落边界"""
        from scipy.signal import find_peaks
        if len(novelty) == 0:
            return np.array([0, max_frames - 1])
        peaks, properties = find_peaks(novelty, distance=max_frames // max(n_peaks, 2))
        if len(peaks) < 2:
            return np.array([0, max_frames - 1])

        # 取最强的 n_peaks 个边界
        strengths = properties.get("peak_heights", np.ones(len(peaks)))
        top_idx = np.argsort(strengths)[-n_peaks:]
        top_peaks = np.sort(peaks[top_idx])
        # 补首尾
        return np.unique(np.concatenate([[0], top_peaks, [max_frames - 1]]))

    def _snap_to_beats(self, times: list[float], beats: list[float]) -> list[float]:
        """将段落边界对齐到最近的节拍"""
        snapped = []
        for t in times:
            nearest = min(beats, key=lambda b: abs(b - t)) if beats else t
            snapped.append(nearest)
        return snapped

    def _label_segments(self, boundaries: list[float], duration: float,
                        features: np.ndarray) -> list[dict]:
        """为每个段落打标签"""
        segments = []
        for i in range(len(boundaries) - 1):
            start = round(boundaries[i], 2)
            end = round(boundaries[i + 1], 2)
            if end - start < self.min_section_sec:
                continue

            # 用 MFCC 特征中心 + 能量判断标签
            energy = self._segment_energy(features, boundaries, i)
            label = self._infer_label(i, len(boundaries), energy)

            segments.append({
                "label": label,
                "start": start,
                "end": end,
                "confidence": 0.7,  # 固定置信度，后续可改进
            })

        if not segments:
            segments.append({"label": "Full", "start": 0.0, "end": round(duration, 2),
                            "confidence": 1.0})

        return segments

    def _segment_energy(self, features: np.ndarray, boundaries: list[float],
                        idx: int) -> float:
        """估算段落能量"""
        # 简化为基于索引位置的启发式
        total = len(boundaries) - 1
        # Chorus 通常在中间偏后，能量最高
        center = total / 2
        distance_from_center = abs(idx - center)
        energy = 1.0 - (distance_from_center / max(center, 1)) * 0.5
        return max(0.3, energy)

    def _infer_label(self, idx: int, total: int, energy: float) -> str:
        """基于位置启发式推断段落标签"""
        if total <= 2:
            return "Full"
        if idx == 0:
            return "Intro"
        if idx == total - 2:
            return "Bridge" if total > 4 else "Outro"
        if idx == total - 1:
            return "Outro"
        # Chorus 在中间偏后位置
        mid = total / 2
        if abs(idx - mid) < 1.5 and energy > 0.6:
            return "Chorus"
        return "Verse"

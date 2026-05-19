"""
layer2_analysis/beat_detector.py — 节拍/BPM 检测器

输入：原始音频路径
输出：BPM、节拍时间戳、重拍位置、节拍置信度
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import librosa


@dataclass
class BeatResult:
    """节拍分析结果"""
    bpm: float                              # 检测到的 BPM
    beats: list[float] = field(default_factory=list)       # 节拍时间戳 (秒)
    downbeats: list[float] = field(default_factory=list)   # 重拍时间戳 (秒)
    onset_frames: list[int] = field(default_factory=list)  # 起音帧
    onset_times: list[float] = field(default_factory=list) # 起音时间 (秒)
    beat_frames: list[int] = field(default_factory=list)   # 节拍帧索引
    confidence: float = 0.0                 # BPM 置信度 (0~1)
    tempo_stability: float = 0.0            # 节奏稳定性 (0~1)
    time_signature: str = "4/4"             # 拍号推断
    segment_bpms: list[dict] = field(default_factory=list) # [{start, end, bpm}, ...]

    @property
    def beat_count(self) -> int:
        return len(self.beats)

    @property
    def duration_sec(self) -> float:
        return self.beats[-1] if self.beats else 0.0


class BeatDetector:
    """Librosa 节拍检测器"""

    def __init__(
        self,
        min_bpm: float = 60,
        max_bpm: float = 200,
        onset_backend: str = "librosa",
    ):
        self.min_bpm = min_bpm
        self.max_bpm = max_bpm
        self.onset_backend = onset_backend

    def detect(self, audio_path: str | Path) -> BeatResult:
        """
        分析音频的 BPM / 节拍 / 重拍

        参数:
            audio_path: 音频文件路径

        返回:
            BeatResult 包含完整节拍分析
        """
        audio_path = Path(audio_path)
        print(f"  [beat_det] 分析: {audio_path.name}")

        # 加载音频 (librosa 自动重采样到 22050)
        y, sr = librosa.load(str(audio_path), sr=None, mono=True)

        # — 1. BPM 检测 —
        tempo, beat_frames = librosa.beat.beat_track(
            y=y, sr=sr,
            min_bpm=self.min_bpm,
            max_bpm=self.max_bpm,
            units="frames",
        )
        bpm = float(tempo)

        # — 2. 节拍时间戳 —
        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

        # — 3. 起音检测 —
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units="frames")
        onset_times = librosa.frames_to_time(onset_frames, sr=sr).tolist()

        # — 4. 重拍检测 (使用 librosa 的 beat tracker 中的第一拍检测) —
        #   librosa 不直接提供 downbeat, 我们通过 beat 强度和周期性估算
        #   方法：取每小节第一拍
        beat_strength = self._estimate_beat_strength(y, sr, beat_frames)
        downbeats = []
        if len(beat_times) > 4:
            # 取最强节拍作为小节的起始
            # 近似: 假设 4/4 拍，每 4 拍一个重拍
            period = self._estimate_bar_period(beat_times)
            downbeats = beat_times[::period] if period > 0 else []

        # — 5. 置信度 —
        confidence = self._calc_confidence(y, sr, bpm, onset_frames)

        # — 6. 节奏稳定性 —
        stability = self._calc_stability(beat_times)

        # — 7. 分段 BPM —
        seg_bpms = self._segment_bpm(y, sr, beat_times)

        print(f"  [beat_det] ✓ BPM={bpm:.1f}  节拍={len(beat_times)}  重拍={len(downbeats)}  "
              f"置信度={confidence:.2f}")

        return BeatResult(
            bpm=bpm,
            beats=beat_times,
            downbeats=downbeats,
            onset_frames=onset_frames.tolist(),
            onset_times=onset_times,
            beat_frames=beat_frames.tolist(),
            confidence=confidence,
            tempo_stability=stability,
            segment_bpms=seg_bpms,
        )

    # ---- 内部方法 ----

    def _estimate_beat_strength(self, y, sr, beat_frames) -> list[float]:
        """估算每个节拍的强度 (用频谱通量)"""
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        strengths = []
        for f in beat_frames:
            idx = min(f, len(onset_env) - 1)
            strengths.append(float(onset_env[idx]))
        return strengths

    def _estimate_bar_period(self, beat_times: list[float]) -> int:
        """估算每小节拍数"""
        if len(beat_times) < 8:
            return 4
        # 最差选择 4 (4/4 拍最常见)
        return 4

    def _calc_confidence(self, y, sr, bpm, onset_frames) -> float:
        """BPM 置信度评估"""
        # 更规则 → 更高置信度
        if len(onset_frames) < 5:
            return 0.3
        # 简单启发式: 起音密度接近 BPM/60
        duration = len(y) / sr
        onset_density = len(onset_frames) / duration if duration > 0 else 0
        expected_density = bpm / 60
        ratio = min(onset_density / expected_density, 1.0) if expected_density > 0 else 0.5
        return min(0.4 + 0.6 * ratio, 1.0)

    def _calc_stability(self, beat_times: list[float]) -> float:
        """节奏稳定性: 节拍间隔的变异系数"""
        if len(beat_times) < 4:
            return 0.5
        intervals = [beat_times[i+1] - beat_times[i] for i in range(len(beat_times)-1)]
        mean_interval = sum(intervals) / len(intervals)
        if mean_interval == 0:
            return 0.0
        variance = sum((i - mean_interval) ** 2 for i in intervals) / len(intervals)
        cv = (variance ** 0.5) / mean_interval
        return max(0.0, min(1.0, 1.0 - cv))

    def _segment_bpm(self, y, sr, beat_times: list[float],
                     segment_len: float = 10.0) -> list[dict]:
        """按时间窗口分段分析 BPM"""
        if len(beat_times) < 4:
            return []
        total_duration = len(y) / sr
        segments = []
        t = 0.0
        while t < total_duration:
            end = min(t + segment_len, total_duration)
            seg_beats = [b for b in beat_times if t <= b < end]
            if len(seg_beats) >= 4:
                intervals = [seg_beats[i+1] - seg_beats[i] for i in range(len(seg_beats)-1)]
                mean_int = sum(intervals) / len(intervals)
                seg_bpm = 60.0 / mean_int if mean_int > 0 else 0
            else:
                seg_bpm = 0
            segments.append({"start": round(t, 2), "end": round(end, 2), "bpm": round(seg_bpm, 1)})
            t = end
        return segments

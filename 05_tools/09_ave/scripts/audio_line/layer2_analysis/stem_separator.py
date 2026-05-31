"""
layer2_analysis/stem_separator.py — Demucs 音轨分离

输入：原始音频文件路径
输出：分离后的分轨字典 {vocals, drums, bass, other, ...}
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Literal


class StemSeparator:
    """Demucs 音轨分离器"""

    STEM_NAMES = ["vocals", "drums", "bass", "other"]
    MODEL_OPTIONS = ["htdemucs", "htdemucs_ft", "htdemucs_6s"]

    def __init__(
        self,
        model: str = "htdemucs_ft",
        device: str = "cpu",
        shifts: int = 2,
        overlap: float = 0.25,
        segments: str = "default",
        out_dir: str | Path | None = None,
    ):
        if model not in self.MODEL_OPTIONS:
            raise ValueError(f"不支持的模型 '{model}', 可选: {self.MODEL_OPTIONS}")
        self.model = model
        self.device = device
        self.shifts = shifts
        self.overlap = overlap
        self.segments = segments
        self.out_dir = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="demucs_"))

    def separate(self, audio_path: str | Path) -> dict[str, str]:
        """
        执行音轨分离

        参数:
            audio_path: 输入音频路径

        返回:
            {stem_name: output_path, ...}
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        print(f"  [stem_sep] 模型={self.model}  设备={self.device}")
        print(f"  [stem_sep] 输入: {audio_path}")

        # 构建 Demucs CLI 命令
        output_dir = self.out_dir / "separated" / self.model
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = (
            f"python3 -m demucs.separate"
            f" --name {self.model}"
            f" --device {self.device}"
            f" --shifts {self.shifts}"
            f" --overlap {self.overlap}"
            f" -o {self.out_dir.resolve()}"
            f" \"{audio_path.resolve()}\""
        )

        os.system(cmd)

        # Demucs 输出: {out_dir}/{model}/{input_stem}/
        input_stem = audio_path.stem
        track_dir = output_dir / input_stem

        # 收集分轨路径
        stems = {}
        for name in self.STEM_NAMES:
            stem_path = track_dir / f"{name}.wav"
            if stem_path.exists():
                stems[name] = str(stem_path.resolve())
            else:
                # 尝试 .mp3
                stem_path_mp3 = track_dir / f"{name}.mp3"
                if stem_path_mp3.exists():
                    stems[name] = str(stem_path_mp3.resolve())

        print(f"  [stem_sep] ✓ 分离完成: {len(stems)} 轨")
        for name, path in stems.items():
            size_mb = Path(path).stat().st_size / 1_048_576
            print(f"    {name}: {Path(path).name} ({size_mb:.1f} MB)")

        return stems

    @classmethod
    def available_models(cls) -> list[str]:
        """列出可用模型"""
        return cls.MODEL_OPTIONS

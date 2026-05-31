"""
AudioLine — 音频创作管线

独立于 AVE 视频工厂的音频处理线。
支持卡点改编、换词创作、风格迁移、Remix 等。

快速开始:
    from audio_line import AudioLine

    # 1. 初始化管线
    al = AudioLine(config_path="config.yaml")

    # 2. 从文件创建任务
    task = al.from_file("input.mp3", operation="cardio", target_bpm=128)

    # 3. 执行全管线
    result = al.run(task)

    # 4. 查看结果
    print(result.summary)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .orchestrator import AudioLineOrchestrator, AudioLineResult
from .layer1_input.collector import AudioTask, AudioSource, AudioCollector
from .layer2_analysis.beat_detector import BeatResult
from .layer2_analysis.structure_parser import StructureResult
from .layer2_analysis.emotion_analyzer import EmotionResult
from .layer3_creation.module_a_rhythm import RhythmResult
from .layer3_creation.module_b_lyrics import LyricsResult
from .layer3_creation.module_c_melody import MelodyResult
from .layer3_creation.module_d_mix import MixResult
from .layer4_alignment.lyric_aligner import LyricTimeline
from .layer5_output.exporter import ExportResult


class AudioLine:
    """
    AudioLine — 音频创作管线外部 API

    封装 AudioLineOrchestrator，提供简洁的接口。
    支持从文件/URL/指令创建任务并执行全管线。
    """

    def __init__(self, config_path: str | Path | None = None):
        """
        初始化管线

        参数:
            config_path: 配置文件路径 (YAML)
        """
        self._orchestrator = AudioLineOrchestrator(config_path)
        self._collector = self._orchestrator.collector

    # ---- 任务创建 ----

    def from_file(
        self,
        path: str | Path,
        operation: str = "auto",
        target_bpm: int = 0,
        target_key: str = "",
        style: str = "",
        topic: str = "",
        duration: float = 0.0,
        dry_run: bool = False,
        modules: set[str] | None = None,
        **kwargs,
    ) -> AudioTask:
        """
        从本地文件创建音频处理任务

        参数:
            path: 音频文件路径
            operation: 操作类型 (auto/remix/rewrite/speed_up/cardio)
            target_bpm: 目标 BPM (0=自动)
            target_key: 目标调性
            style: 目标风格
            topic: 歌词主题 (换词时使用)
            duration: 目标时长 (秒)
            dry_run: 仅分析不创作
            modules: 模块子集

        返回:
            AudioTask
        """
        return self._collector.from_file(path, {
            "operation": operation,
            "target_bpm": target_bpm,
            "target_key": target_key,
            "style": style,
            "topic": topic,
            "duration": duration,
            "dry_run": dry_run,
            "modules": modules or {"separation", "analysis", "rhythm", "lyrics", "mix", "alignment", "export"},
            **kwargs,
        })

    def from_url(
        self,
        url: str,
        **kwargs,
    ) -> AudioTask:
        """
        从 URL 下载并创建任务

        参数同 from_file()
        """
        return self._collector.from_url(url, kwargs)

    def from_command(self, text: str) -> AudioTask:
        """
        从自然语言指令创建任务

        参数:
            text: 如 "把这首歌改成128BPM的卡点版"
        """
        return self._collector.from_text_command(text)

    # ---- 管线执行 ----

    def run(self, task: AudioTask) -> AudioLineResult:
        """
        执行音频处理管线

        参数:
            task: AudioTask 任务对象

        返回:
            AudioLineResult
        """
        return self._orchestrator.run(task)

    def run_file(
        self,
        path: str | Path,
        **kwargs,
    ) -> AudioLineResult:
        """
        快速执行: 从文件到结果一步完成

        参数:
            path: 音频文件路径
            **kwargs: 传给 from_file() 的额外参数

        返回:
            AudioLineResult
        """
        task = self.from_file(path, **kwargs)
        return self._orchestrator.run(task)

    # ---- 单模块执行 ----

    @property
    def config(self) -> dict:
        """获取当前配置"""
        return self._orchestrator.config

    @property
    def stem_separator(self):
        """直接访问音轨分离器"""
        return self._orchestrator.stem_sep

    @property
    def beat_detector(self):
        """直接访问节拍检测器"""
        return self._orchestrator.beat_det

    @property
    def structure_parser(self):
        """直接访问结构解析器"""
        return self._orchestrator.structure_parser

    @property
    def emotion_analyzer(self):
        """直接访问情绪分析器"""
        return self._orchestrator.emotion_analyzer


__all__ = [
    "AudioLine",
    "AudioLineOrchestrator",
    "AudioLineResult",
    "AudioTask",
    "AudioSource",
    "BeatResult",
    "StructureResult",
    "EmotionResult",
    "RhythmResult",
    "LyricsResult",
    "MelodyResult",
    "MixResult",
    "LyricTimeline",
    "ExportResult",
]

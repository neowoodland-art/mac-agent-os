"""
orchestrator.py — 音频创作管线编排控制器

职责：串联所有 6 层模块，按顺序执行 AudioTask。
支持模块选择、dry-run、状态报告、错误恢复。
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

# Layer 1 — 输入
from layer1_input.collector import AudioTask, AudioSource, AudioCollector

# Layer 2 — 分析
from layer2_analysis.stem_separator import StemSeparator
from layer2_analysis.beat_detector import BeatDetector, BeatResult
from layer2_analysis.structure_parser import StructureParser, StructureResult
from layer2_analysis.emotion_analyzer import EmotionAnalyzer, EmotionResult

# Layer 3 — 创作
from layer3_creation.module_a_rhythm import RhythmModule, RhythmResult
from layer3_creation.module_b_lyrics import LyricsModule, LyricsResult
from layer3_creation.module_c_melody import MelodyModule, MelodyResult
from layer3_creation.module_d_mix import MixModule, MixResult

# Layer 4 — 对齐
from layer4_alignment.lyric_aligner import LyricAligner, LyricTimeline
from layer4_alignment.stem_aligner import StemAligner, AlignResult

# Layer 5 — 输出
from layer5_output.exporter import Exporter, ExportResult
from layer5_output.lyric_formatter import LyricFormatter, FormattedLyrics


# ---------------------------------------------------------------------------
# 结果数据类
# ---------------------------------------------------------------------------

@dataclass
class AudioLineResult:
    """完整管线输出"""
    task: AudioTask = field(default_factory=lambda: AudioTask(
        source=AudioSource(path="", source_type="command")
    ))

    # Layer 2 结果
    stems: dict[str, str] = field(default_factory=dict)
    beat: BeatResult | None = None
    structure: StructureResult | None = None
    emotion: EmotionResult | None = None

    # Layer 3 结果
    rhythm: RhythmResult | None = None
    lyrics: LyricsResult | None = None
    melody: MelodyResult | None = None
    mix: MixResult | None = None

    # Layer 4 结果
    lyric_timeline: LyricTimeline | None = None
    stem_alignment: AlignResult | None = None

    # Layer 5 结果
    export: ExportResult | None = None
    formatted_lyrics: FormattedLyrics | None = None

    # 状态
    modules_run: list[str] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)  # [{module, error}]
    timing: dict[str, float] = field(default_factory=dict)  # {module: elapsed_sec}
    success: bool = False

    @property
    def summary(self) -> str:
        """生成执行摘要"""
        lines = [
            f"任务: {self.task.operation} | 源: {self.task.source.original_filename or '(指令)'}",
            f"模块: {', '.join(self.modules_run) or '(无)'}",
        ]

        if self.beat:
            lines.append(f"BPM: {self.beat.bpm:.1f} | 情绪: {self.emotion.mood if self.emotion else 'N/A'}")
        if self.mix:
            lines.append(f"混音: {self.mix.master_path}")
        if self.export:
            lines.append(f"导出: {self.export.summary}")

        if self.errors:
            lines.append(f"错误: {len(self.errors)} 个")
            for e in self.errors[:3]:
                lines.append(f"  ⚠ {e['module']}: {e['error']}")

        lines.append(f"成功: {'✅' if self.success else '❌'}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 编排器
# ---------------------------------------------------------------------------

class AudioLineOrchestrator:
    """
    音频创作管线编排器

    按 AudioTask.modules 配置依次执行各层。
    跳过失败的模块（不阻塞整条管线）。
    """

    def __init__(self, config_path: str | Path | None = None):
        self.config = self._load_config(config_path)
        self.work_dir = Path(self.config.get("paths", {}).get("work_dir", "./work/audio_line"))
        self.output_dir = Path(self.config.get("paths", {}).get("output_dir", "./output/audio_line"))
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # — 初始化各层模块 —
        self.collector = AudioCollector(str(self.work_dir))

        sep_cfg = self.config.get("separation", {})
        self.stem_sep = StemSeparator(
            model=sep_cfg.get("model", "htdemucs_ft"),
            device=sep_cfg.get("device", "cpu"),
            shifts=sep_cfg.get("shifts", 2),
            overlap=sep_cfg.get("overlap", 0.25),
            out_dir=str(self.work_dir / "separated"),
        )

        beat_cfg = self.config.get("beat", {})
        self.beat_det = BeatDetector(
            min_bpm=beat_cfg.get("min_bpm", 60),
            max_bpm=beat_cfg.get("max_bpm", 200),
        )

        self.structure_parser = StructureParser()
        self.emotion_analyzer = EmotionAnalyzer()
        self.rhythm_module = RhythmModule(self.config)
        self.lyrics_module = LyricsModule(self.config)
        self.melody_module = MelodyModule(self.config)
        self.mix_module = MixModule(self.config)

        align_cfg = self.config.get("alignment", {})
        self.lyric_aligner = LyricAligner(
            tolerance=align_cfg.get("time_tolerance", 0.1),
        )
        self.stem_aligner = StemAligner(
            method=align_cfg.get("stretch_method", "phase_vocoder"),
            crossfade=align_cfg.get("crossfade", 0.05),
        )

        self.exporter = Exporter(self.config)
        self.lyric_formatter = LyricFormatter()

    def run(self, task: AudioTask) -> AudioLineResult:
        """
        执行管线

        参数:
            task: AudioTask — 由 AudioCollector 创建的标准化任务

        返回:
            AudioLineResult
        """
        result = AudioLineResult(task=task)
        print(f"\n{'='*60}")
        print(f"AudioLine 管线启动")
        print(f"  operation: {task.operation}")
        print(f"  source:    {task.source.path or '(指令模式)'}")
        print(f"  modules:   {', '.join(sorted(task.modules))}")
        print(f"{'='*60}\n")

        modules_to_run = self._plan_modules(task)

        for module_name, callable_fn, ctx_key in modules_to_run:
            if module_name not in task.modules:
                continue

            start = time.time()
            print(f"\n--- [{module_name}] ---")

            try:
                callable_fn(result)
                elapsed = time.time() - start
                result.modules_run.append(module_name)
                result.timing[module_name] = round(elapsed, 2)
                print(f"  [{module_name}] ✅ 完成 ({elapsed:.1f}s)")
            except Exception as e:
                elapsed = time.time() - start
                result.errors.append({"module": module_name, "error": str(e)})
                result.timing[module_name] = round(elapsed, 2)
                print(f"  [{module_name}] ❌ 失败: {e}")
                print(f"  [{module_name}] 跳过，继续下一步")

        result.success = len(result.errors) == 0

        print(f"\n{'='*60}")
        print(f"管线结束 | 模块: {len(result.modules_run)}/{len(modules_to_run)}"
              f" | 错误: {len(result.errors)} | 耗时: {sum(result.timing.values()):.1f}s")
        if result.success:
            print(f"状态: ✅ 成功")
        else:
            print(f"状态: ⚠ 部分成功 ({len(result.errors)} 个错误)")
        print(f"{'='*60}\n")

        return result

    # ---- 模块路由 ----

    def _plan_modules(self, task: AudioTask) -> list[tuple[str, Callable, str]]:
        """
        规划模块执行顺序

        返回: [(module_name, callable_fn, context_key)]
        """
        return [
            # Layer 2 — 分析
            ("separation", self._run_stem_separation, "stems"),
            ("analysis", self._run_analysis, "analysis"),

            # Layer 3 — 创作
            ("rhythm", self._run_rhythm, "rhythm"),
            ("lyrics", self._run_lyrics, "lyrics"),
            ("melody", self._run_melody, "melody"),
            ("mix", self._run_mix, "mix"),

            # Layer 4 — 对齐
            ("alignment", self._run_alignment, "alignment"),

            # Layer 5 — 输出
            ("export", self._run_export, "export"),
        ]

    # ---- Layer 2 ----

    def _run_stem_separation(self, result: AudioLineResult):
        """音轨分离"""
        task = result.task
        if not task.source.path:
            print("  [orchestrator] ⚠ 无音频源，跳过音轨分离")
            return

        result.stems = self.stem_sep.separate(task.source.path)

    def _run_analysis(self, result: AudioLineResult):
        """执行所有分析"""
        # 用原始音频或 vocals stem 分析
        audio_for_analysis = result.stems.get("vocals", "")
        if not audio_for_analysis or not Path(audio_for_analysis).exists():
            audio_for_analysis = result.task.source.path

        if not audio_for_analysis:
            print("  [orchestrator] ⚠ 无音频可用于分析")
            return

        # — BPM/节拍 —
        result.beat = self.beat_det.detect(audio_for_analysis)

        # — 结构解析 —
        result.structure = self.structure_parser.parse(
            audio_for_analysis, result.beat.beats
        )

        # — 情绪分析 —
        result.emotion = self.emotion_analyzer.analyze(
            audio_for_analysis, result.beat.bpm
        )

    # ---- Layer 3 ----

    def _run_rhythm(self, result: AudioLineResult):
        """节奏重塑"""
        task = result.task
        bpm = result.beat.bpm if result.beat else 120.0
        target_bpm = task.target_bpm or bpm

        output_dir = self.output_dir / "rhythm"
        output_dir.mkdir(parents=True, exist_ok=True)

        result.rhythm = self.rhythm_module.generate(
            bpm=target_bpm,
            genre=task.style,
            duration=task.duration or 30,
            output_path=str(output_dir / "drum_track.wav"),
        )

    def _run_lyrics(self, result: AudioLineResult):
        """歌词创作"""
        # 如果有原始歌词，从原曲分析获取
        original_lyrics = ""  # 默认空，需要时用户提供

        output_dir = self.output_dir / "lyrics"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 仅当有主题时执行改写
        if result.task.topic:
            result.lyrics = self.lyrics_module.rewrite(
                original_lyrics=original_lyrics,
                topic=result.task.topic,
                style=result.task.style,
                output_path=str(output_dir / "rewritten_lyrics.txt"),
            )
        else:
            print("  [orchestrator] ⚠ 无歌词主题，跳过歌词改写")

    def _run_melody(self, result: AudioLineResult):
        """旋律编曲"""
        audio_path = result.stems.get("vocals", "") or result.task.source.path
        if not audio_path:
            print("  [orchestrator] ⚠ 无音频源，跳过旋律编曲")
            return

        output_dir = self.output_dir / "melody"
        output_dir.mkdir(parents=True, exist_ok=True)

        result.melody = self.melody_module.remix(
            audio_path=audio_path,
            target_style=result.task.style,
            duration=result.task.duration or 0,
            output_path=str(output_dir / "remix.wav"),
        )

    def _run_mix(self, result: AudioLineResult):
        """混音母带"""
        if not result.stems:
            print("  [orchestrator] ⚠ 无分轨可供混音，跳过")
            return

        output_dir = self.output_dir / "mix"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 如果有生成的鼓点轨道，加入混音
        stems_to_mix = dict(result.stems)
        if result.rhythm and result.rhythm.drum_track_path:
            stems_to_mix["drum_track"] = result.rhythm.drum_track_path

        result.mix = self.mix_module.mix(
            stems=stems_to_mix,
            output_path=str(output_dir / "master.wav"),
            include_stems=True,
        )

    # ---- Layer 4 ----

    def _run_alignment(self, result: AudioLineResult):
        """对齐处理"""
        # — 歌词对齐 —
        if result.lyrics and result.beat:
            lyrics_text = result.lyrics.rewritten_lyrics or result.lyrics.original_lyrics
            sections = result.structure.segments if result.structure else None

            result.lyric_timeline = self.lyric_aligner.align(
                lyrics=lyrics_text,
                beats=result.beat.beats,
                sections=sections,
                total_duration=result.beat.duration_sec,
            )

        # — 分轨对齐 —
        if result.stems and result.beat:
            # 如果有目标 BPM，进行 BPM 对齐
            task = result.task
            target_bpm = task.target_bpm
            if target_bpm and target_bpm != result.beat.bpm:
                output_dir = self.output_dir / "aligned"
                output_dir.mkdir(parents=True, exist_ok=True)

                result.stem_alignment = self.stem_aligner.align_to_bpm(
                    stems=result.stems,
                    source_bpm=result.beat.bpm,
                    target_bpm=target_bpm,
                    output_dir=str(output_dir),
                )

    # ---- Layer 5 ----

    def _run_export(self, result: AudioLineResult):
        """导出"""
        output_dir = self.output_dir / "export"
        output_dir.mkdir(parents=True, exist_ok=True)

        # — 导出混音 —
        master_path = result.mix.master_path if result.mix else ""
        if master_path and Path(master_path).exists():
            result.export = self.exporter.export_master(
                master_path=master_path,
                output_dir=str(output_dir),
            )

            # — 导出带歌词版本 —
            if result.lyric_timeline:
                result.export = self.exporter.export_with_lyrics(
                    master_path=master_path,
                    lyric_timeline=result.lyric_timeline,
                    output_dir=str(output_dir),
                )

        # — 歌词格式化 —
        if result.lyric_timeline and result.lyric_timeline.entries:
            result.formatted_lyrics = self.lyric_formatter.format_all(
                entries=result.lyric_timeline.entries,
                total_duration=result.lyric_timeline.total_duration,
                title=f"AudioLine_{result.task.operation}",
            )
            result.formatted_lyrics.save_all(
                str(output_dir / "lyrics"),
                basename="lyrics",
            )

    # ---- 配置加载 ----

    @staticmethod
    def _load_config(config_path: str | Path | None) -> dict:
        """加载 YAML 配置"""
        if config_path and Path(config_path).exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

        # 尝试默认路径
        for path in [
            "./config.yaml",
            "./config/local.yaml",
        ]:
            p = Path(path)
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}

        print("[orchestrator] ⚠ 未找到配置文件，使用默认值")
        return {}

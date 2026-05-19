"""
layer1_input/collector.py — 输入收集模块

职责：接收各种来源的输入，标准化为统一的 AudioTask 数据类。
支持：本地文件 / URL下载 / 文本指令（如"把这首歌改成卡点版"）
"""
from __future__ import annotations

import os
import tempfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class AudioSource:
    """标准化音频源描述"""
    path: str                           # 本地路径
    original_filename: str = ""         # 原始文件名
    source_type: Literal["file", "url", "command"] = "file"
    duration: float = 0.0               # 时长 (秒)，预读取后填充
    sample_rate: int = 0                # 采样率，预读取后填充


@dataclass
class AudioTask:
    """完整的音频处理任务"""
    # ——— 源信息 ———
    source: AudioSource

    # ——— 创作参数 ———
    operation: Literal["remix", "rewrite", "speed_up", "cardio", "auto"] = "auto"
    target_bpm: int = 0                 # 0 = 自动
    target_key: str = ""                # 空 = 保持原调
    style: str = ""                     # 目标风格描述
    topic: str = ""                     # 歌词主题 (换词时使用)
    duration: float = 0.0               # 目标时长 (0 = 与原曲相同)

    # ——— 控制标记 ———
    modules: set[str] = field(default_factory=lambda: {
        "separation", "analysis", "rhythm", "lyrics", "mix"
    })   # 要执行的模块集合
    dry_run: bool = False               # 仅分析，不执行创作模块

    # ——— 元信息 ———
    task_id: str = ""
    created_at: str = ""
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 收集器
# ---------------------------------------------------------------------------

class AudioCollector:
    """输入收集器 — 接受文件/URL/命令 → AudioTask"""

    SUPPORTED_FORMATS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma"}

    def __init__(self, work_dir: str | Path = "./work/audio_line"):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self._upload_counter = 0

    # ---- 公开 API ----

    def from_file(self, path: str | Path, task_kwargs: dict | None = None) -> AudioTask:
        """从本地文件创建任务"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"音频文件不存在: {path}")
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(f"不支持的格式 '{path.suffix}', 支持: {self.SUPPORTED_FORMATS}")

        source = AudioSource(
            path=str(path.resolve()),
            original_filename=path.name,
            source_type="file",
        )
        return self._build_task(source, task_kwargs)

    def from_url(self, url: str, task_kwargs: dict | None = None) -> AudioTask:
        """从 URL 下载并创建任务"""
        self._upload_counter += 1
        ext = self._guess_ext_from_url(url)
        dest = self.work_dir / f"download_{self._upload_counter}{ext}"

        print(f"  [collector] 下载: {url}")
        urllib.request.urlretrieve(url, dest)
        print(f"  [collector] 已保存: {dest}")

        source = AudioSource(
            path=str(dest.resolve()),
            original_filename=dest.name,
            source_type="url",
        )
        return self._build_task(source, task_kwargs)

    def from_text_command(self, text: str) -> AudioTask:
        """从自然语言指令创建任务（不含音频源，需后续绑定）"""
        # 简单规则解析；生产环境可接入 LLM
        from ._parser import parse_command_text
        parsed = parse_command_text(text)
        return parsed

    # ---- 内部 ----

    def _build_task(self, source: AudioSource, kwargs: dict | None = None) -> AudioTask:
        kwargs = kwargs or {}
        return AudioTask(
            source=source,
            operation=kwargs.pop("operation", "auto"),
            target_bpm=kwargs.pop("target_bpm", 0),
            target_key=kwargs.pop("target_key", ""),
            style=kwargs.pop("style", ""),
            topic=kwargs.pop("topic", ""),
            duration=kwargs.pop("duration", 0.0),
            modules=kwargs.pop("modules", {"separation", "analysis", "rhythm", "lyrics", "mix"}),
            dry_run=kwargs.pop("dry_run", False),
            metadata=kwargs,
        )

    @staticmethod
    def _guess_ext_from_url(url: str) -> str:
        path = urllib.parse.urlparse(url).path
        ext = Path(path).suffix.lower()
        return ext if ext in AudioCollector.SUPPORTED_FORMATS else ".mp3"

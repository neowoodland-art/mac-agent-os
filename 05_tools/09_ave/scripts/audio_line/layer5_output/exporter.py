"""
layer5_output/exporter.py — 多格式输出导出模块

功能：将混音结果导出为多种格式
支持：WAV (PCM) / MP3 / FLAC / AAC
可选：整轨导出 / 分轨导出 / 带歌词时间轴导出
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExportResult:
    """导出结果"""
    exported_files: list[dict] = field(default_factory=list)   # [{format, path, size_kb}]
    formats_completed: list[str] = field(default_factory=list)
    total_size_kb: float = 0.0
    duration: float = 0.0
    has_lyrics: bool = False

    @property
    def summary(self) -> str:
        return f"{len(self.exported_files)} 文件, {self.total_size_kb:.0f} KB, " \
               f"{self.duration:.1f}s, 格式: {', '.join(self.formats_completed)}"


class Exporter:
    """
    多格式导出器

    支持格式:
    - WAV: 无损 PCM 16/24-bit
    - MP3: CBR/VBR, 支持 128k/192k/320k
    - FLAC: 无损压缩
    - AAC: 高效有损 (M4A)
    """

    SUPPORTED_FORMATS = {"wav", "mp3", "flac", "aac"}

    def __init__(
        self,
        config: dict | None = None,
    ):
        self.config = config or {}
        export_cfg = config.get("export", {}) if config else {}

        self.default_formats = export_cfg.get("formats", ["wav", "mp3"])
        self.mp3_bitrate = export_cfg.get("mp3_bitrate", "320k")
        self.include_stems = export_cfg.get("include_stems", True)
        self.stem_labels = export_cfg.get("stem_labels",
                                          ["vocals", "drums", "bass", "other", "full_mix"])

        self.sample_rate = int(config.get("mixing", {}).get("sample_rate", 44100)) if config else 44100
        self.bit_depth = int(config.get("mixing", {}).get("bit_depth", 16)) if config else 16

    def export_master(
        self,
        master_path: str | Path,
        output_dir: str | Path = "./output/export/",
        formats: list[str] | None = None,
        metadata: dict | None = None,
    ) -> ExportResult:
        """
        导出主混音

        参数:
            master_path: 主混音 WAV 路径
            output_dir: 输出目录
            formats: 目标格式列表 (默认 config 中的设置)
            metadata: 元数据 {title, artist, album, ...}

        返回:
            ExportResult
        """
        master_path = Path(master_path)
        if not master_path.exists():
            raise FileNotFoundError(f"主混音文件不存在: {master_path}")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        formats = formats or self.default_formats
        stem_name = master_path.stem

        print(f"  [export] 导出主轨: {master_path.name}")
        print(f"  [export] 目标格式: {formats}")

        exported = []
        for fmt in formats:
            fmt = fmt.lower().lstrip(".")
            if fmt not in self.SUPPORTED_FORMATS:
                print(f"  [export] ⚠ 不支持格式 '{fmt}', 跳过")
                continue

            out_path = output_dir / f"{stem_name}.{fmt}"
            success = self._convert(master_path, out_path, fmt, metadata)
            if success:
                size_kb = out_path.stat().st_size / 1024
                exported.append({
                    "format": fmt,
                    "path": str(out_path.resolve()),
                    "size_kb": round(size_kb, 1),
                })
                print(f"  [export]   {fmt}: {out_path.name} ({size_kb:.0f} KB)")

        if not exported:
            raise RuntimeError("所有格式导出均失败")

        # 获取时长
        duration = self._get_duration(master_path)

        return ExportResult(
            exported_files=exported,
            formats_completed=[e["format"] for e in exported],
            total_size_kb=sum(e["size_kb"] for e in exported),
            duration=duration,
        )

    def export_stems(
        self,
        stems: dict[str, str],
        output_dir: str | Path = "./output/export/",
        formats: list[str] | None = None,
    ) -> list[ExportResult]:
        """
        导出所有分轨

        参数:
            stems: {stem_name: audio_path, ...}
            output_dir: 输出目录
            formats: 目标格式

        返回:
            每轨的 ExportResult 列表
        """
        results = []
        for name, path in stems.items():
            result = self.export_master(
                Path(path), output_dir / name, formats
            )
            results.append(result)
        return results

    def export_with_lyrics(
        self,
        master_path: str | Path,
        lyric_timeline: Any,  # LyricTimeline
        output_dir: str | Path = "./output/export/",
        formats: list[str] | None = None,
    ) -> ExportResult:
        """
        导出带歌词的主混音

        同时导出音频 + LRC/SRT 歌词文件
        """
        output_dir = Path(output_dir)
        result = self.export_master(master_path, output_dir, formats)

        # 导出 LRC
        lrc_path = output_dir / f"{Path(master_path).stem}.lrc"
        lrc_content = lyric_timeline.to_lrc()
        lrc_path.write_text(lrc_content, encoding="utf-8")
        result.exported_files.append({
            "format": "lrc",
            "path": str(lrc_path.resolve()),
            "size_kb": round(lrc_path.stat().st_size / 1024, 1),
        })

        # 导出 SRT
        srt_path = output_dir / f"{Path(master_path).stem}.srt"
        srt_content = lyric_timeline.to_srt()
        srt_path.write_text(srt_content, encoding="utf-8")
        result.exported_files.append({
            "format": "srt",
            "path": str(srt_path.resolve()),
            "size_kb": round(srt_path.stat().st_size / 1024, 1),
        })

        result.has_lyrics = True
        result.formats_completed.extend(["lrc", "srt"])
        result.total_size_kb = sum(e["size_kb"] for e in result.exported_files)

        print(f"  [export]   歌词: LRC + SRT 已导出")
        return result

    # ---- 内部 ----

    def _convert(
        self,
        src: Path,
        dst: Path,
        fmt: str,
        metadata: dict | None = None,
    ) -> bool:
        """格式转换"""
        try:
            if fmt == "wav":
                return self._to_wav(src, dst)
            elif fmt == "mp3":
                return self._to_mp3(src, dst, metadata)
            elif fmt == "flac":
                return self._to_flac(src, dst)
            elif fmt == "aac":
                return self._to_aac(src, dst, metadata)
            return False
        except Exception as e:
            print(f"  [export]   {fmt} 转换失败: {e}")
            return False

    def _to_wav(self, src: Path, dst: Path) -> bool:
        """复制/重编码为 WAV (PCM 16-bit)"""
        import soundfile as sf
        y, sr = sf.read(str(src))
        sf.write(str(dst), y, sr, subtype="PCM_16")
        return dst.exists()

    def _to_mp3(self, src: Path, dst: Path, metadata: dict | None = None) -> bool:
        """转 MP3 (通过 ffmpeg)"""
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-codec:a", "libmp3lame",
            "-b:a", self.mp3_bitrate,
            "-ar", str(self.sample_rate),
        ]
        if metadata:
            if "title" in metadata:
                cmd += ["-metadata", f"title={metadata['title']}"]
            if "artist" in metadata:
                cmd += ["-metadata", f"artist={metadata['artist']}"]
        cmd.append(str(dst))

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0 and dst.exists()

    def _to_flac(self, src: Path, dst: Path) -> bool:
        """转 FLAC (通过 ffmpeg)"""
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-codec:a", "flac",
            "-ar", str(self.sample_rate),
            str(dst),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0 and dst.exists()

    def _to_aac(self, src: Path, dst: Path, metadata: dict | None = None) -> bool:
        """转 AAC/M4A (通过 ffmpeg)"""
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-codec:a", "aac",
            "-b:a", "256k",
            "-ar", str(self.sample_rate),
        ]
        if metadata:
            if "title" in metadata:
                cmd += ["-metadata", f"title={metadata['title']}"]
            if "artist" in metadata:
                cmd += ["-metadata", f"artist={metadata['artist']}"]
        cmd.append(str(dst))

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0 and dst.exists()

    @staticmethod
    def _get_duration(path: Path) -> float:
        """ffprobe 获取音频时长"""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        try:
            return round(float(result.stdout.strip()), 2)
        except (ValueError, TypeError):
            return 0.0

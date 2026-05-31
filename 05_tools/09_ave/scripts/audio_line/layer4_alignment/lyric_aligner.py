"""
layer4_alignment/lyric_aligner.py — 歌词-节拍对齐模块

功能：将歌词文本按段落结构对齐到节拍时间戳。
输出格式：[{start, end, text, section}] 时间轴，支持转 LRC/SRT。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LyricTimeline:
    """歌词时间轴"""
    entries: list[dict] = field(default_factory=list)  # [{start, end, text, section}]
    total_duration: float = 0.0
    sections: list[dict] = field(default_factory=list)  # [{label, start, end}]

    @property
    def lyric_count(self) -> int:
        return len(self.entries)

    def to_lrc(self) -> str:
        """转为 LRC 歌词格式"""
        lines = ["[ti:AudioLine LRC]", "[offset:0]"]
        for entry in self.entries:
            mm, ss = divmod(entry["start"], 60)
            cs = int((entry["start"] - int(entry["start"])) * 100)
            lines.append(f"[{int(mm):02d}:{int(ss):02d}.{cs:02d}]{entry['text']}")
        return "\n".join(lines)

    def to_srt(self) -> str:
        """转为 SRT 字幕格式"""
        blocks = []
        for i, entry in enumerate(self.entries, 1):
            start_srt = self._sec_to_srt(entry["start"])
            end_srt = self._sec_to_srt(entry["end"])
            blocks.append(f"{i}\n{start_srt} --> {end_srt}\n{entry['text']}\n")
        return "\n".join(blocks)

    @staticmethod
    def _sec_to_srt(sec: float) -> str:
        h, m = divmod(sec, 3600)
        m, s = divmod(m, 60)
        cs = int((s - int(s)) * 1000)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{cs:03d}"


class LyricAligner:
    """
    歌词-节拍对齐器

    将结构化的歌词段落匹配到分析出的节拍/段落边界。
    支持两种模式：
    1. 自动对齐 — 根据段落标签映射
    2. 手动指定 — 提供精确的时间偏移
    """

    def __init__(self, tolerance: float = 0.1):
        self.tolerance = tolerance  # 时间容差 (秒)

    def align(
        self,
        lyrics: str,
        beats: list[float],
        sections: list[dict] | None = None,
        total_duration: float = 0.0,
    ) -> LyricTimeline:
        """
        将对齐歌词到节拍

        参数:
            lyrics: 歌词文本 (含 [Intro][Verse] 等段落标记)
            beats: 节拍时间戳列表 (秒)
            sections: 段落结构 [{label, start, end}] (可选)
            total_duration: 总时长 (秒)

        返回:
            LyricTimeline
        """
        # — 1. 解析歌词段落 —
        parsed_sections = self._parse_lyric_sections(lyrics)

        if sections:
            # — 2a. 使用已分析的段落边界 —
            timeline = self._align_with_sections(
                parsed_sections, beats, sections, total_duration
            )
        else:
            # — 2b. 仅用节拍均匀分配 —
            timeline = self._align_by_beats(parsed_sections, beats, total_duration)

        return timeline

    def align_lines(
        self,
        lines: list[str],
        section: str,
        section_start: float,
        section_end: float,
        beats_in_section: list[float],
    ) -> list[dict]:
        """
        对齐单个段落内的歌词行到节拍

        参数:
            lines: 歌词行列表
            section: 段落标签
            section_start: 段落开始时间
            section_end: 段落结束时间
            beats_in_section: 段落内的节拍

        返回:
            [{start, end, text, section}]
        """
        if not lines:
            return []

        if not beats_in_section:
            # 无节拍: 均匀分配
            return self._distribute_evenly(lines, section, section_start, section_end)

        entries = []
        beats_per_line = max(len(beats_in_section) // len(lines), 1)

        for i, line in enumerate(lines):
            start_idx = i * beats_per_line
            end_idx = min((i + 1) * beats_per_line, len(beats_in_section))

            start = beats_in_section[start_idx] if start_idx < len(beats_in_section) else section_start
            end = beats_in_section[end_idx - 1] if end_idx <= len(beats_in_section) else section_end

            # 对最后一行: 用段落结束而不是最后一个节拍
            if i == len(lines) - 1:
                end = section_end

            entries.append({
                "start": round(start, 3),
                "end": round(end, 3),
                "text": line.strip(),
                "section": section,
            })

        return entries

    # ---- 内部 ----

    def _parse_lyric_sections(self, lyrics: str) -> list[dict[str, Any]]:
        """解析歌词中的段落标记"""
        sections = []
        # 匹配 [Intro], [Verse 1], [Chorus] 等标记
        pattern = r"\[(\w+(?:\s*\d*)?)\](.*?)(?=\[\w|$)"
        matches = re.findall(pattern, lyrics, re.DOTALL)

        if not matches:
            # 无标记: 整段视为一个段落
            lines = [l for l in lyrics.strip().split("\n") if l.strip()]
            sections.append({"label": "Full", "lines": lines})
        else:
            for label, content in matches:
                lines = [l.strip() for l in content.strip().split("\n") if l.strip()]
                if lines:
                    sections.append({"label": label.strip(), "lines": lines})

        return sections

    def _align_with_sections(
        self,
        parsed: list[dict],
        beats: list[float],
        sections: list[dict],
        total_duration: float,
    ) -> LyricTimeline:
        """基于段落结构对齐"""
        all_entries = []

        for ps in parsed:
            label = ps["label"]
            # 找对应的段落
            section = next(
                (s for s in sections if label.lower() in s.get("label", "").lower()),
                None,
            )

            if section:
                start = section["start"]
                end = section["end"]
                beats_in_sec = [b for b in beats if start <= b <= end]
            else:
                # 找不到: 用标签顺序估算位置
                idx = parsed.index(ps)
                total = len(parsed)
                start = (idx / total) * total_duration
                end = ((idx + 1) / total) * total_duration
                beats_in_sec = [b for b in beats if start <= b <= end]

            entries = self.align_lines(
                ps["lines"], label, start, end, beats_in_sec
            )
            all_entries.extend(entries)

        return LyricTimeline(
            entries=all_entries,
            total_duration=total_duration or (all_entries[-1]["end"] if all_entries else 0),
            sections=sections,
        )

    def _align_by_beats(
        self,
        parsed: list[dict],
        beats: list[float],
        total_duration: float,
    ) -> LyricTimeline:
        """仅基于节拍均匀分配"""
        if not beats:
            return self._fallback_linear(parsed, total_duration)

        all_entries = []
        total_lines = sum(len(ps["lines"]) for ps in parsed)
        if total_lines == 0:
            return LyricTimeline()

        beats_per_line = max(len(beats) // total_lines, 1)
        line_idx = 0

        for ps in parsed:
            for line in ps["lines"]:
                start_idx = line_idx * beats_per_line
                end_idx = min((line_idx + 1) * beats_per_line, len(beats))

                start = beats[start_idx] if start_idx < len(beats) else 0
                end = beats[end_idx - 1] if end_idx <= len(beats) else (total_duration or end + 2)

                all_entries.append({
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "text": line.strip(),
                    "section": ps["label"],
                })
                line_idx += 1

        return LyricTimeline(
            entries=all_entries,
            total_duration=total_duration or (all_entries[-1]["end"] if all_entries else 0),
        )

    def _distribute_evenly(
        self,
        lines: list[str],
        section: str,
        start: float,
        end: float,
    ) -> list[dict]:
        """均匀分配歌词行"""
        if not lines:
            return []
        if len(lines) == 1:
            return [{"start": round(start, 3), "end": round(end, 3),
                     "text": lines[0].strip(), "section": section}]

        duration = end - start
        line_duration = duration / len(lines)
        entries = []

        for i, line in enumerate(lines):
            line_start = start + i * line_duration
            line_end = line_start + line_duration
            entries.append({
                "start": round(line_start, 3),
                "end": round(line_end, 3),
                "text": line.strip(),
                "section": section,
            })

        return entries

    def _fallback_linear(
        self, parsed: list[dict], total_duration: float
    ) -> LyricTimeline:
        """无节拍时的回退方案"""
        if not total_duration:
            return LyricTimeline()

        all_lines = []
        for ps in parsed:
            for line in ps["lines"]:
                all_lines.append({"text": line.strip(), "section": ps["label"]})

        if not all_lines:
            return LyricTimeline()

        per_line = total_duration / len(all_lines)
        entries = [
            {
                "start": round(i * per_line, 3),
                "end": round((i + 1) * per_line, 3),
                "text": e["text"],
                "section": e["section"],
            }
            for i, e in enumerate(all_lines)
        ]

        return LyricTimeline(
            entries=entries,
            total_duration=total_duration,
        )

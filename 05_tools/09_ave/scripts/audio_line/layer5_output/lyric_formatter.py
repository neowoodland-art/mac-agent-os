"""
layer5_output/lyric_formatter.py — 歌词格式化模块

功能：将歌词时间轴输出为多种字幕/歌词格式
支持格式：
- LRC (LyRiCs) — 标准歌词格式
- SRT (SubRip) — 通用字幕格式
- ASS (Advanced SubStation Alpha) — 高级字幕 (带样式)
- TTML (Timed Text Markup Language) — WebVTT 替代
- plain text — 纯文本 (无时间戳)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FormattedLyrics:
    """格式化歌词结果"""
    lrc: str = ""
    srt: str = ""
    ass: str = ""
    ttml: str = ""
    plain: str = ""

    def save_all(self, output_dir: str | Path, basename: str = "lyrics") -> dict[str, str]:
        """保存所有格式到文件"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        saved = {}
        fmt_map = {
            "lrc": self.lrc,
            "srt": self.srt,
            "ass": self.ass,
            "ttml": self.ttml,
            "txt": self.plain,
        }

        for ext, content in fmt_map.items():
            if content:
                path = output_dir / f"{basename}.{ext}"
                path.write_text(content, encoding="utf-8")
                saved[ext] = str(path.resolve())

        return saved


class LyricFormatter:
    """
    歌词格式化器

    将时间轴条目(entries)转换为各种字幕格式。
    支持自定义 ASS 样式。
    """

    # ASS 默认样式
    DEFAULT_ASS_STYLE = (
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default, Arial, 24, &H00FFFFFF, &H000000FF, "
        "&H00000000, &H00000000, 0, 0, 0, 0, "
        "100, 100, 0, 0, 1, 1, 1, 2, 20, 20, 40, 1\n"
    )

    def format_all(
        self,
        entries: list[dict],
        total_duration: float = 0.0,
        title: str = "AudioLine",
        ass_style: str | None = None,
    ) -> FormattedLyrics:
        """
        生成所有格式的歌词

        参数:
            entries: [{start, end, text, section}] 时间轴条目
            total_duration: 总时长
            title: 标题
            ass_style: ASS 样式定义 (可选)

        返回:
            FormattedLyrics
        """
        return FormattedLyrics(
            lrc=self.to_lrc(entries, title),
            srt=self.to_srt(entries),
            ass=self.to_ass(entries, ass_style or self.DEFAULT_ASS_STYLE),
            ttml=self.to_ttml(entries, total_duration, title),
            plain=self.to_plain(entries),
        )

    # ---- LRC ----

    def to_lrc(self, entries: list[dict], title: str = "AudioLine") -> str:
        """转为 LRC 格式"""
        lines = [
            "[ti:{}]".format(title),
            "[offset:0]",
        ]

        last_section = ""
        for entry in entries:
            section = entry.get("section", "")
            if section and section != last_section:
                lines.append("")
                lines.append("[{: >8}]".format(section))
                last_section = section

            start = entry["start"]
            mm, ss = divmod(start, 60)
            cs = int((start - int(start)) * 100)
            lines.append("[{:02d}:{:02d}.{:02d}]{:s}".format(
                int(mm), int(ss), cs, entry["text"]
            ))

        return "\n".join(lines) + "\n"

    # ---- SRT ----

    def to_srt(self, entries: list[dict]) -> str:
        """转为 SRT 格式"""
        blocks = []
        for i, entry in enumerate(entries, 1):
            start_srt = self._sec_to_srt(entry["start"])
            end_srt = self._sec_to_srt(entry["end"])

            section = entry.get("section", "")
            text = entry["text"]
            if section:
                text = f"{text}\n({section})"

            blocks.append("{:d}\n{:s} --> {:s}\n{:s}\n".format(
                i, start_srt, end_srt, text
            ))

        return "\n".join(blocks)

    # ---- ASS ----

    def to_ass(self, entries: list[dict], style_block: str = "") -> str:
        """转为 ASS 格式"""
        style_block = style_block or self.DEFAULT_ASS_STYLE

        header = (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            "Title: AudioLine Lyrics\n"
            "WrapStyle: 2\n"
            "ScaledBorderAndShadow: yes\n"
        )

        body = ""
        for entry in entries:
            start_ass = self._sec_to_ass(entry["start"])
            end_ass = self._sec_to_ass(entry["end"])
            text = entry["text"].replace("\n", "\\N")

            section = entry.get("section", "")
            if section:
                text = f"{{\\i1}}{section}{{\\i0}} - {text}"

            body += "Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n".format(
                start=start_ass, end=end_ass, text=text
            )

        return header + style_block + "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" + body

    # ---- TTML ----

    def to_ttml(self, entries: list[dict], total_duration: float, title: str = "") -> str:
        """转为 TTML (类似 WebVTT) 格式"""
        lines = ["WEBVTT", f"Title: {title}"]
        if total_duration:
            lines.append(f"Duration: {self._sec_to_srt(total_duration)}")
        lines.append("")

        for entry in entries:
            start_vtt = self._sec_to_srt(entry["start"]).replace(",", ".")
            end_vtt = self._sec_to_srt(entry["end"]).replace(",", ".")
            lines.append("{:s} --> {:s}".format(start_vtt, end_vtt))
            lines.append(entry["text"])
            lines.append("")

        return "\n".join(lines)

    # ---- Plain ----

    def to_plain(self, entries: list[dict]) -> str:
        """转为纯文本"""
        last_section = ""
        lines = []

        for entry in entries:
            section = entry.get("section", "")
            if section and section != last_section:
                lines.append("")
                lines.append("[{}]".format(section))
                last_section = section
            lines.append(entry["text"])

        return "\n".join(lines).strip()

    # ---- 辅助 ----

    @staticmethod
    def _sec_to_srt(sec: float) -> str:
        """秒 → SRT 时间格式 (HH:MM:SS,mmm)"""
        h, rem = divmod(sec, 3600)
        m, s = divmod(rem, 60)
        ms = int((s - int(s)) * 1000)
        return "{:02d}:{:02d}:{:02d},{:03d}".format(int(h), int(m), int(s), ms)

    @staticmethod
    def _sec_to_ass(sec: float) -> str:
        """秒 → ASS 时间格式 (H:MM:SS.cc)"""
        h, rem = divmod(sec, 3600)
        m, s = divmod(rem, 60)
        cs = int((s - int(s)) * 100)
        return "{:d}:{:02d}:{:02d}.{:02d}".format(int(h), int(m), int(s), cs)

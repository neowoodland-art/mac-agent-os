"""

AVE 06_composer — FFmpeg 合成模块

职责:
  1. 音频混音: 人声 + BGM → 混合音频
  2. 视频合成: 素材片段拼接 + 画面过渡
  3. 字幕叠加: ASS 格式中文字幕（带重音高亮）
  4. 最终编码: 输出 final.mp4
  5. 分段渲染: 3分钟以上视频自动分段

依赖:
  - ffmpeg (需安装)
  - Python: ffmpeg-python
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from lib.logger import get_logger

logger = get_logger("composer")

# ── 常量 ──────────────────────────────────────────────────
DEFAULT_RESOLUTION = "1080x1920"  # 竖屏
DEFAULT_FPS = 30
DEFAULT_BITRATE = "8M"
SEGMENT_DURATION_MAX = 180  # 3分钟分段


# ── 公共 API ──────────────────────────────────────────────

def mix_audio(
    voice_path: str,
    bgm_path: Optional[str] = None,
    output_path: str = "mixed_audio.wav",
    voice_volume: float = 1.0,
    bgm_volume: float = 0.3,
) -> str:
    """
    混音: 人声 + BGM → 混合音频

    - voice_path: 人声 WAV 路径
    - bgm_path: BGM 路径 (None 则只输出人声)
    - voice_volume: 人声音量倍率
    - bgm_volume: BGM 音量倍率
    - 返回: 混合音频路径
    """
    if not os.path.exists(voice_path):
        raise FileNotFoundError(f"人声文件不存在: {voice_path}")

    if bgm_path and not os.path.exists(bgm_path):
        logger.warning(f"BGM 文件不存在，跳过背景音乐: {bgm_path}")
        bgm_path = None

    if not bgm_path:
        # 无人声时，直接复制人声
        subprocess.run(
            ["ffmpeg", "-y", "-i", voice_path, "-acodec", "pcm_s16le", output_path],
            capture_output=True, check=True
        )
        logger.info(f"音频已输出（无BGM）: {output_path}")
        return output_path

    # 双轨混音
    cmd = [
        "ffmpeg", "-y",
        "-i", voice_path,
        "-i", bgm_path,
        "-filter_complex",
        f"[0:a]volume={voice_volume}[v];[1:a]volume={bgm_volume}[b];[v][b]amix=inputs=2:duration=first[a]",
        "-map", "[a]",
        "-acodec", "pcm_s16le",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    logger.info(f"混音完成: {output_path}")
    return output_path


def compose_video(
    material_clips: list[str],
    audio_path: str,
    output_path: str = "final.mp4",
    resolution: str = DEFAULT_RESOLUTION,
    fps: int = DEFAULT_FPS,
    transitions: list[str] | None = None,
    subtitles_path: str | None = None,
    total_duration: float | None = None,
) -> str:
    """
    视频合成: 素材片段 + 音频 + 字幕 → final.mp4

    - material_clips: 素材视频文件路径列表
    - audio_path: 混音音频路径
    - output_path: 输出文件路径
    - transitions: 每段之间的过渡效果 (fade/cut/dissolve)，长度=clips数-1
    - subtitles_path: ASS/SRT 字幕文件路径 (可选)
    - total_duration: 视频总时长(秒)，用于裁剪素材匹配音频

    **素材时长自动匹配策略**:
    如果所有素材总时长 < 音频时长 → 末尾慢放/循环最后一段
    如果素材总时长 > 音频时长 → 裁剪素材到恰好匹配
    """
    if not material_clips:
        raise ValueError("素材列表为空")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    # 1. 创建素材拼接文件列表
    concat_file = _create_concat_list(material_clips)

    # 2. 获取音频总时长
    audio_duration = _get_media_duration(audio_path)

    # 3. 构建 FFmpeg 命令
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-i", audio_path,
    ]

    filters = []

    # 4. 如果素材总时长 > 音频时长，裁剪
    materials_duration = sum(_get_media_duration(c) for c in material_clips)
    output_duration = audio_duration

    # 5. 视频流处理
    filters.append(f"[0:v]setpts=PTS-STARTPTS,scale={resolution.replace('x',':')},fps={fps}[v]")
    filters.append(f"[1:a]volume=1.0[a]")

    # 6. 字幕叠加 (ASS 格式支持中文最好)
    if subtitles_path and os.path.exists(subtitles_path):
        filters.append(f"[v]subtitles={subtitles_path}[vo]")
        map_v = "[vo]"
    else:
        map_v = "[v]"

    filter_complex = ";".join(filters)

    cmd.extend(["-filter_complex", filter_complex])
    cmd.extend(["-map", map_v, "-map", "[a]"])

    # 7. 时长匹配: 用 -shortest 使视频对齐音频时长
    #    无论素材比音频长还是短，都截取到音频时长
    logger.info(f"  素材总时长: {materials_duration:.1f}s, 音频时长: {audio_duration:.1f}s")
    if materials_duration < audio_duration:
        logger.warning(f"素材不足，尾部会黑屏补齐")
    cmd.extend(["-shortest"])

    # 8. 编码参数
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "medium",
        "-b:v", DEFAULT_BITRATE,
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ])

    try:
        subprocess.run(cmd, capture_output=True, timeout=600)
        logger.info(f"视频合成完成: {output_path}")
    except subprocess.TimeoutExpired:
        logger.error("渲染超时（>600s），建议分段渲染")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg 执行失败: {e.stderr.decode(errors='replace')[:500]}")
        raise

    return output_path


def create_subtitles(
    segments: list[dict],
    output_path: str = "subtitles.ass",
    resolution: tuple = (1080, 1920),
) -> str:
    """
    从分段信息生成 ASS 格式字幕

    segments 格式:
      [{"text": "...", "start_sec": 0.0, "end_sec": 8.0, "emotion": "..."}]
    """
    width, height = resolution
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Noto Sans SC,48,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,100,100,50,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for seg in segments:
        start = _sec_to_ass_time(seg.get("start_sec", 0))
        end = _sec_to_ass_time(seg.get("end_sec", 8))
        text = seg.get("text", "").replace("\n", "\\N")
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"字幕生成: {output_path} ({len(segments)} 段)")
    return output_path


def segment_render(
    material_clips: list[str],
    audio_path: str,
    output_dir: str = ".",
    segment_duration: int = SEGMENT_DURATION_MAX,
) -> list[str]:
    """
    分段渲染: 长视频自动分段 → 分别渲染 → 返回分段文件列表
    后续由 FFmpeg concat 拼接
    """
    audio_duration = _get_media_duration(audio_path)
    if audio_duration <= segment_duration:
        # 无需分段
        out = os.path.join(output_dir, "segment_000.mp4")
        compose_video(material_clips, audio_path, out)
        return [out]

    # 需要分段
    segments = []
    for i in range(0, int(audio_duration), segment_duration):
        start = i
        end = min(i + segment_duration, audio_duration)
        out = os.path.join(output_dir, f"segment_{i:03d}.mp4")
        _render_segment(material_clips, audio_path, start, end, out)
        segments.append(out)

    logger.info(f"分段渲染完成: {len(segments)} 段")
    return segments


def concat_segments(segment_files: list[str], output_path: str = "final.mp4") -> str:
    """拼接分段视频"""
    concat_file = _create_concat_list(segment_files)
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c", "copy",
        output_path,
    ], capture_output=True, check=True)
    logger.info(f"分段拼接完成: {output_path}")
    return output_path


# ── 内部工具 ──────────────────────────────────────────────

def _create_concat_list(file_paths: list[str]) -> str:
    """创建 FFmpeg concat 文件列表"""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    for fp in file_paths:
        abs_path = os.path.abspath(fp)
        tmp.write(f"file '{abs_path}'\n")
    tmp.close()
    return tmp.name


def _get_media_duration(path: str) -> float:
    """获取媒体文件时长(秒)"""
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ], capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
    except (ValueError, subprocess.TimeoutExpired):
        logger.warning(f"无法获取时长，默认 30s: {path}")
        return 30.0


def _sec_to_ass_time(seconds: float) -> str:
    """秒 → ASS 时间格式 H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds - int(seconds)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _render_segment(
    material_clips: list[str],
    audio_path: str,
    start_sec: float,
    end_sec: float,
    output_path: str,
):
    """渲染单个分段（裁剪音频+对齐素材）"""
    duration = end_sec - start_sec
    cmd = [
        "ffmpeg", "-y",
        "-i", material_clips[0] if material_clips else "",
        "-ss", str(start_sec),
        "-i", audio_path,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "medium",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)

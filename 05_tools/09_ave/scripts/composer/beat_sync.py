"""
AVE 06_composer/beat_sync — BGM 节拍驱动的卡点视频合成

流程:
  1. BGM 节拍检测 (librosa beat_track)
  2. 按 N拍 分组 (默认 4拍/组)
  3. 每组分配素材 (Pexels搜索 或 用户提供)
  4. 精确裁剪到组时长
  5. xfade 过渡拼接 (≤8组避免 FFmpeg 崩溃)
  6. 文字/字幕叠加

用法:
  from composer.beat_sync import compose_beat_sync
  compose_beat_sync(bgm_path="bgm.wav", output="beat_sync.mp4")
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from lib.logger import get_logger

logger = get_logger("beat_sync")

CACHE_DIR = Path(os.environ.get("AVE_CACHE_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local/tools/ave/cache")))
BEAT_CACHE = CACHE_DIR / "beat_sync"
BEAT_CACHE.mkdir(parents=True, exist_ok=True)


def detect_beats(
    audio_path: str,
    group_size: int = 4,
) -> dict:
    """
    检测 BGM 节拍

    参数:
      audio_path: BGM 音频路径
      group_size: 每组节拍数 (默认4拍/组)

    返回:
      {
        "bpm": 120.0,
        "beat_times": [0.0, 0.5, 1.0, ...],
        "segments": [{"start": 0.0, "end": 2.0, "beats": 4}, ...],
        "total_duration": 30.0,
      }
    """
    import librosa
    import numpy as np

    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    # 节拍检测
    tempo_arr, beats = librosa.beat.beat_track(y=y, sr=sr)
    tempo_val = float(tempo_arr.item() if hasattr(tempo_arr, 'item') else tempo_arr)
    beat_times = librosa.frames_to_time(beats, sr=sr).tolist()

    # 如果没检测到拍点, 按 BPM 估算
    if len(beat_times) < 2:
        bpm = tempo_val if tempo_val > 0 else 120.0
        interval = 60.0 / bpm
        beat_times = [i * interval for i in range(int(duration / interval))]
        logger.info(f"  无拍点, 按 BPM={bpm:.0f} 估算 {len(beat_times)} 拍")
    else:
        logger.info(f"  检测到 BPM={tempo_val:.1f}, {len(beat_times)} 拍")

    # 按 N拍 分组
    segments = []
    for i in range(0, len(beat_times), group_size):
        start = beat_times[i]
        end = beat_times[min(i + group_size, len(beat_times) - 1)]
        actual_beats = min(group_size, len(beat_times) - i)
        if end - start > 0.3:
            segments.append({
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(end - start, 2),
                "beats": actual_beats,
            })

    # 最后一段: 最后一个拍点到音频结束
    if segments and segments[-1]["end"] < duration - 0.3:
        segments.append({
            "start": segments[-1]["end"],
            "end": round(duration, 2),
            "duration": round(duration - segments[-1]["end"], 2),
            "beats": 0,
        })

    # 限制 ≤8 组 (xfade 链限制)
    if len(segments) > 8:
        # 合并后段
        keep = segments[:7]
        remaining = segments[7:]
        keep.append({
            "start": keep[-1]["end"],
            "end": round(duration, 2),
            "duration": round(duration - keep[-1]["end"], 2),
            "beats": sum(s["beats"] for s in remaining),
        })
        segments = keep
        logger.info(f"  合并为 {len(segments)} 组 (≤8)")

    return {
        "bpm": tempo_val,
        "beat_count": len(beat_times),
        "segments": segments,
        "total_duration": round(duration, 2),
    }


def compose_beat_sync(
    bgm_path: str,
    output_path: str = "beat_sync.mp4",
    material_clips: list[str] | None = None,
    group_size: int = 4,
    resolution: str = "1080x1920",
    texts: list[str] | None = None,
    pexels_api_key: str = "",
    pexels_search: str = "",
) -> str:
    """
    BGM 节拍驱动的卡点视频合成

    参数:
      bgm_path: BGM 音频路径
      output_path: 输出视频路径
      material_clips: 素材视频/图片列表 (可选, 不提供则 Pexels 搜索)
      group_size: 每组节拍数
      resolution: 输出分辨率
      texts: 每段叠加的文字 (可选, 数量可少于段数)
      pexels_api_key: Pexels API Key (素材不够时搜索用)
      pexels_search: Pexels 搜索关键词 (素材不够时使用)

    返回: output_path
    """
    if not os.path.exists(bgm_path):
        raise FileNotFoundError(f"BGM 文件不存在: {bgm_path}")

    # 1. 节拍检测
    logger.info("=== Beat-Sync 卡点模式 ===")
    logger.info(f"BGM: {bgm_path}")
    beat_info = detect_beats(bgm_path, group_size)
    segments = beat_info["segments"]
    total_dur = beat_info["total_duration"]
    logger.info(f"BPM: {beat_info['bpm']}, {beat_info['beat_count']}拍, {len(segments)}组")

    # 2. 准备素材
    clips = material_clips or []
    if len(clips) < len(segments) and pexels_api_key:
        # 从 Pexels 补充
        from material_producer.pexels.search import search_videos
        needed = len(segments) - len(clips)
        logger.info(f"素材不足, 从 Pexels 搜索 {needed} 个...")
        kw = pexels_search or "background video"
        found = search_videos(kw, count=needed, api_key=pexels_api_key, orientation="portrait")
        for f in found:
            clips.append(f["path"])
        logger.info(f"  共 {len(clips)} 个素材")

    if not clips:
        raise ValueError("无可用素材")

    # 3. 为每组分配素材 (循环使用)
    seg_materials = []
    for i, seg in enumerate(segments):
        clip = clips[i % len(clips)]
        seg_materials.append((clip, seg["start"], seg["end"], seg["duration"]))

    logger.info(f"分配素材: {len(seg_materials)} 段, {len(clips)} 素材循环")

    # 4. 渲染每组为独立视频片段
    temp_dir = tempfile.mkdtemp(prefix="ave_beat_")
    seg_files = []
    for idx, (clip, start, end, dur) in enumerate(seg_materials):
        seg_file = os.path.join(temp_dir, f"seg_{idx:03d}.mp4")
        # 从素材中取一段
        clip_dur = _get_duration(clip)
        offset = (start * 17) % max(clip_dur - dur, 0.1) if clip_dur > dur else 0

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(offset),
            "-i", clip,
            "-t", str(dur),
            "-vf", f"scale={resolution.replace('x',':')},setsar=1,fps=30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-an",  # 不要素材的音频
            seg_file,
        ]
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
        seg_files.append(seg_file)

    # 5. xfade 过渡拼接 (≤8段)
    if len(seg_files) == 1:
        # 单段, 直接复制
        subprocess.run(["ffmpeg", "-y", "-i", seg_files[0], "-i", bgm_path,
                        "-shortest", "-c:v", "copy", "-c:a", "aac", output_path],
                       capture_output=True, check=True, timeout=60)
    else:
        fade_dur = min(0.4, seg_materials[0][3] * 0.3)
        cmd = ["ffmpeg", "-y"]
        for sf in seg_files:
            cmd += ["-i", sf]
        cmd += ["-i", bgm_path]

        # 构建 xfade 链
        filters = []
        prev_label = "0:v"
        offset_sec = 0.0
        n = len(seg_files)

        for i in range(1, n):
            # offset = 前一段结束 - 淡变时长
            prev_dur = seg_materials[i-1][3]
            fade_offset = offset_sec + prev_dur - fade_dur
            filters.append(
                f"[{prev_label}][{i}:v]xfade=transition=fade:duration={fade_dur}:offset={fade_offset:.2f}[v{i}]"
            )
            prev_label = f"v{i}"
            offset_sec += prev_dur

        # 音频: 直接使用 BGM
        filter_complex = ";".join(filters) + f";[{n}:a]acopy[a]"

        cmd += [
            "-filter_complex", filter_complex,
            "-map", f"[{prev_label}]", "-map", "[a]",
            "-shortest",
            "-c:v", "libx264", "-preset", "medium", "-b:v", "8M",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=300, check=True)
            logger.info(f"  xfade 拼接成功 ({n} 段)")
        except subprocess.CalledProcessError as e:
            logger.warning(f"  xfade 失败, 回落 concat: {e.stderr[:200]}")
            # 回落: 无过渡直接拼接
            concat_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w").name
            with open(concat_file, "w") as f:
                for sf in seg_files:
                    f.write(f"file '{sf}'\n")
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file, "-i", bgm_path,
                "-shortest", "-c:v", "libx264", "-preset", "medium",
                "-b:v", "8M", "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p", output_path,
            ], capture_output=True, check=True, timeout=300)

    # 6. 如果提供了文字, 叠加字幕
    if texts:
        _add_text_subtitles(output_path, texts, seg_materials, resolution)

    # 清理
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

    sz_mb = os.path.getsize(output_path) / 1024 / 1024
    logger.info(f"✅ Beat-Sync 完成: {output_path} ({sz_mb:.0f}MB, {total_dur:.0f}s)")
    return output_path


def _get_duration(path: str) -> float:
    """获取媒体文件时长"""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
                           capture_output=True, text=True, timeout=10)
        return float(r.stdout.strip())
    except Exception:
        return 30.0


def _add_text_subtitles(video_path: str, texts: list[str],
                        seg_materials: list, resolution: str):
    """为每段叠加文字 (ASS 字幕)"""
    width, height = (int(x) for x in resolution.split("x"))
    font_size = max(48, int(height * 0.05))
    margin_v = int(height * 0.3)

    lines = [
        "[Script Info]", "ScriptType: v4.00+",
        f"PlayResX: {width}", f"PlayResY: {height}",
        "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,Noto Sans SC,{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,100,100,{margin_v},1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for i, text in enumerate(texts):
        if i >= len(seg_materials):
            break
        start = seg_materials[i][1]
        end = seg_materials[i][2]
        h = int(start); m = int((start - h) * 60); s = int(start - h * 3600 - m * 60)
        he = int(end); me = int((end - he) * 60); se = int(end - he * 3600 - me * 60)
        lines.append(
            f"Dialogue: 0,{h}:{m:02d}:{s:02d}.00,{he}:{me:02d}:{se:02d}.00,Default,,0,0,0,,{text}"
        )

    ass_path = video_path.replace(".mp4", "_text.ass")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # 叠加字幕
    tmp = video_path.replace(".mp4", "_tmp.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"subtitles={ass_path}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy", "-pix_fmt", "yuv420p", tmp,
    ], capture_output=True, timeout=120, check=True)
    os.replace(tmp, video_path)
    os.remove(ass_path)

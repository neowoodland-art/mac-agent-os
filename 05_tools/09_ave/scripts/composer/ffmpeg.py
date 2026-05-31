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


def duck_bgm(
    voice_path: str,
    bgm_path: str,
    output_path: str = "ducked_bgm.wav",
    low_volume: float = 0.15,
    high_volume: float = 0.50,
    fade_ms: int = 300,
    word_timestamps: list | None = None,
) -> str:
    """
    BGM 音量避让 (Audio Ducking), 基于字级时间戳

    说话时 BGM 压低 (low_volume), 间隙时恢复 (high_volume)。
    使用 word_timestamps 精确控制每个字的避让区间,
    比 silencedetect 更准确 (CosyVoice 连续语音无停顿).

    参数:
      word_timestamps: [{begin_time, end_time}, ...] 单位毫秒
                       来自 synthesize_with_timestamps()
    """
    if not os.path.exists(voice_path):
        raise FileNotFoundError(f"人声文件不存在: {voice_path}")
    if not os.path.exists(bgm_path):
        raise FileNotFoundError(f"BGM 文件不存在: {bgm_path}")

    # 如果没有时间戳, 回退到固定音量
    if not word_timestamps:
        logger.info("  无时间戳, 使用固定音量 0.25")
        subprocess.run([
            "ffmpeg", "-y", "-i", bgm_path,
            "-af", f"volume={high_volume}",
            "-acodec", "pcm_s16le", output_path,
        ], capture_output=True, check=True, timeout=30)
        return output_path

    duration = _get_media_duration(voice_path)
    total_ms = duration * 1000
    fade_ms_f = fade_ms / 1000.0

    logger.info(f"BGM 避让: {low_volume}→{high_volume}, 基于 {len(word_timestamps)} 个字")

    # 构建音量区间: [(start_sec, end_sec, volume), ...]
    # 每个字的区间: 字开始前 fade_ms 开始压低, 字结束后 fade_ms 恢复
    segments = []
    # 先确定所有活跃区间 (字的时间范围 + 过渡)
    active_zones = []  # [(start, end), ...] 单位为秒
    for w in word_timestamps:
        w_start = max(0, (w["begin_time"] - 50) / 1000.0)  # 字前 50ms
        w_end = min(duration, (w["end_time"] + 50) / 1000.0)  # 字后 50ms
        active_zones.append((w_start, w_end))

    # 合并重叠的活跃区间
    active_zones.sort()
    merged = []
    for start, end in active_zones:
        if merged and start <= merged[-1][1] + 0.05:  # 50ms 内视为连续
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    # 构建音量分段: 活跃期低音量, 间隙期高音量
    prev_end = 0.0
    for a_start, a_end in merged:
        # 间隙: prev_end → a_start (高音量)
        if a_start > prev_end + 0.05:
            gap_mid = (prev_end + a_start) / 2
            segments.append((prev_end, gap_mid, high_volume))
            segments.append((gap_mid, a_start, high_volume))
        # 说话: a_start → a_end (低音量, 带过渡)
        segments.append((a_start, a_end, low_volume))
        prev_end = a_end
    # 最后间隙
    if duration > prev_end + 0.05:
        segments.append((prev_end, duration, high_volume))

    if not segments:
        logger.info("  无分段, 使用固定音量")
        subprocess.run([
            "ffmpeg", "-y", "-i", bgm_path,
            "-af", f"volume={high_volume}",
            "-acodec", "pcm_s16le", output_path,
        ], capture_output=True, check=True, timeout=30)
        return output_path

    # 渲染每段再拼接
    import tempfile, shutil
    seg_dir = tempfile.mkdtemp(prefix="ave_duck_")
    seg_wavs = []
    for idx, (st, en, vol) in enumerate(segments):
        dur = en - st
        if dur < 0.05:
            continue
        seg_out = os.path.join(seg_dir, f"seg_{idx:03d}.wav")
        fade_dur = min(fade_ms_f, dur / 3)
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(st), "-i", bgm_path,
            "-t", str(dur),
            "-af", f"volume={vol},afade=t=in:d={fade_dur},afade=t=out:st={dur-fade_dur}:d={fade_dur}",
            "-acodec", "pcm_s16le", seg_out,
        ], capture_output=True, timeout=60, check=True)
        seg_wavs.append(seg_out)

    # 拼接
    concat_file = _create_concat_list(seg_wavs)
    if len(seg_wavs) == 1:
        subprocess.run(["ffmpeg", "-y", "-i", seg_wavs[0], "-acodec", "pcm_s16le", output_path],
                       capture_output=True, check=True)
    else:
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", concat_file,
            "-acodec", "pcm_s16le", output_path,
        ], capture_output=True, check=True, timeout=60)
    shutil.rmtree(seg_dir, ignore_errors=True)

    logger.info(f"BGM 避让完成: {output_path} ({len(seg_wavs)} 段)")
    return output_path


def image_to_clip(
    input_path: str,
    output_path: str,
    duration: float = 5.0,
    resolution: str = DEFAULT_RESOLUTION,
    ken_burns: bool = True,
) -> str:
    """
    将静态图片转换为视频分镜（带 Ken Burns 动效）

    处理横图→竖屏转换（如 1248×832→1080×1920），用于 AVE 流水线中
    图片生成阶段→合成阶段之间的转换步骤。

    策略：先按目标高度等比缩放填满画面，然后 crop 到目标宽度，
    再添加 Ken Burns 式平滑平移动效。
    """
    target_w, target_h = [int(x) for x in resolution.split("x")]

    if ken_burns:
        # 使用 cos 实现平滑左右平移: 从右到左的平滑摆动
        filter_str = (
            f"scale='max({target_w},iw*{target_h}/ih)':{target_h}:flags=lanczos,"
            f"crop={target_w}:{target_h}:"
            f"'(iw-{target_w})*(0.5-0.45*cos(PI*t/{duration}))':'0',"
            f"setsar=1,fps={DEFAULT_FPS}"
        )
    else:
        # 无动效：居中裁剪
        filter_str = (
            f"scale='max({target_w},iw*{target_h}/ih)':{target_h}:flags=lanczos,"
            f"crop={target_w}:{target_h}:'(iw-{target_w})/2':'(ih-{target_h})/2',"
            f"setsar=1,fps={DEFAULT_FPS}"
        )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(duration),
        "-i", input_path,
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-pix_fmt", "yuv420p", "-an",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=300, check=True)
    logger.info(f"图片→视频分镜: {os.path.basename(input_path)} → {os.path.basename(output_path)} ({duration}s)")
    return output_path


def _apply_ken_burns(input_path: str, output_path: str, resolution: str = DEFAULT_RESOLUTION) -> str:
    """
    对视频素材施加随机 Ken Burns 效果（缩放+平移），让画面动起来。

    策略：先获取原始尺寸，判断横竖屏，选择合适的缩放+裁切方案。
    竖屏素材(720x1280等)：放大后以宽度为基准裁切到1080。
    """
    import random
    duration = _get_media_duration(input_path)
    if duration < 1.0:
        duration = 5.0

    target_w, target_h = [int(x) for x in resolution.split("x")]

    # 获取原视频尺寸
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=p=0", input_path],
        capture_output=True, text=True, timeout=10
    )
    parts = probe.stdout.strip().split(",")
    src_w, src_h = int(parts[0]), int(parts[1]) if len(parts) >= 2 else (target_w, target_h)

    # 判断方向
    is_portrait = src_h > src_w  # 竖屏

    if is_portrait and src_w >= target_w:
        # 竖屏且宽度够 → 只用缩放覆盖高度，平移只在竖直方向
        zoom = random.uniform(1.10, 1.25)
        d = f"max(t,0.001)/{max(duration,1)}"
        trajectory = random.choice(["center_zoom", "pan_up", "pan_down"])
        if trajectory == "center_zoom":
            x, y = f"(iw-{target_w})/2", f"(ih-{target_h})/2"
        elif trajectory == "pan_up":
            x, y = f"(iw-{target_w})/2", f"(ih-{target_h})*(1-{d})"
        else:  # pan_down
            x, y = f"(iw-{target_w})/2", f"(ih-{target_h})*{d}"
        kb_type = trajectory
    else:
        # 横屏或小尺寸 → 仅缩放填充，不做平移（避免负值）
        zoom = max(target_w / max(src_w, 1), target_h / max(src_h, 1)) * 1.05
        x, y = f"(iw-{target_w})/2", f"(ih-{target_h})/2"
        kb_type = "center"

    filter_str = (
        f"scale=iw*{zoom}:ih*{zoom}:flags=lanczos,"
        f"crop={target_w}:{target_h}:{x}:{y},"
        f"setsar=1,fps=30"
    )

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "25",
        "-an", output_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=300, check=True)
    logger.debug(f"Ken Burns [{kb_type} @ {zoom:.2f}x] → {output_path}")
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
    ken_burns: bool = True,
) -> str:
    """
    视频合成: 素材片段 + 音频 + 字幕 → final.mp4

    - material_clips: 素材视频文件路径列表
    - audio_path: 混音音频路径
    - output_path: 输出文件路径
    - transitions: 每段之间的过渡效果 (fade/cut/dissolve)，长度=clips数-1
    - subtitles_path: ASS/SRT 字幕文件路径 (可选)
    - total_duration: 视频总时长(秒)，用于裁剪素材匹配音频
    - ken_burns: 是否对每个素材施加随机缩放/平移动效（默认开启）

    **素材时长自动匹配策略**:
    如果所有素材总时长 < 音频时长 → 末尾慢放/循环最后一段
    如果素材总时长 > 音频时长 → 裁剪素材到恰好匹配
    """
    if not material_clips:
        raise ValueError("素材列表为空")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    # 1. 可选择对素材施加 Ken Burns 动效（逐素材预处理）
    final_clips = material_clips
    if ken_burns:
        import tempfile, shutil
        ken_dir = tempfile.mkdtemp(prefix="ave_kenburns_")
        processed = []
        for idx, clip in enumerate(material_clips):
            out = os.path.join(ken_dir, f"kb_{idx:03d}.mp4")
            _apply_ken_burns(clip, out, resolution)
            processed.append(out)
        final_clips = processed
        logger.info(f"Ken Burns 已应用于 {len(final_clips)} 个素材")

    # 2. 创建素材拼接文件列表
    concat_file = _create_concat_list(final_clips)

    # 3. 获取音频总时长
    audio_duration = _get_media_duration(audio_path)

    # 4. 构建 FFmpeg 命令
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-i", audio_path,
    ]

    filters = []

    # 5. 如果素材总时长 > 音频时长，裁剪
    materials_duration = sum(_get_media_duration(c) for c in final_clips)
    output_duration = audio_duration

    # 6. 视频流处理（Ken Burns 已预处理，这里只做字幕叠加）
    filters.append(f"[0:v]setpts=PTS-STARTPTS,fps={fps}[v]")
    filters.append("[1:a]volume=1.0[a]")

    # 7. 字幕叠加
    if subtitles_path and os.path.exists(subtitles_path):
        filters.append(f"[v]subtitles={subtitles_path}[vo]")
        map_v = "[vo]"
    else:
        map_v = "[v]"

    filter_complex = ";".join(filters)

    cmd.extend(["-filter_complex", filter_complex])
    cmd.extend(["-map", map_v, "-map", "[a]"])

    # 8. 时长匹配
    logger.info(f"  素材总时长: {materials_duration:.1f}s, 音频时长: {audio_duration:.1f}s")
    if materials_duration < audio_duration:
        logger.warning(f"素材不足，尾部会黑屏补齐")
    cmd.extend(["-shortest"])

    # 9. 编码参数
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

    # 清理临时文件
    if ken_burns:
        shutil.rmtree(ken_dir, ignore_errors=True)

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

    # 字幕位置: 由下往上 20% (竖屏 1080x1920)
    margin_v = int(height * 0.2)
    font_size = max(48, int(height * 0.044))  # 1920 → ~84px

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,Noto Sans SC,{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,100,100,{margin_v},1",
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
    subtitles_path: str | None = None,
    resolution: str = DEFAULT_RESOLUTION,
) -> list[str]:
    """
    分段渲染: 长视频自动分段 → 分别渲染 → 返回分段文件列表
    后续由 FFmpeg concat 拼接
    """
    audio_duration = _get_media_duration(audio_path)
    if audio_duration <= segment_duration:
        # 无需分段
        out = os.path.join(output_dir, "segment_000.mp4")
        compose_video(material_clips, audio_path, out,
                      subtitles_path=subtitles_path,
                      resolution=resolution)
        return [out]

    # 需要分段
    segments = []
    for i in range(0, int(audio_duration), segment_duration):
        start = i
        end = min(i + segment_duration, audio_duration)
        out = os.path.join(output_dir, f"segment_{i:03d}.mp4")
        _render_segment(material_clips, audio_path, start, end, out,
                        subtitles_path=subtitles_path,
                        resolution=resolution)
        segments.append(out)

    logger.info(f"分段渲染完成: {len(segments)} 段")
    return segments


def compose_with_anchors(
    material_clips: list[str],
    audio_path: str,
    output_path: str,
    silence_periods: list[dict],
    total_duration: float,
    subtitles_path: str | None = None,
    resolution: str = DEFAULT_RESOLUTION,
) -> str:
    """
    锚点驱动的画面切换合成

    在每段静音处切换素材片段，添加交叉淡变过渡。
    素材按顺序循环使用，避免单一素材贯穿全片。

    参数:
      material_clips: 素材视频列表
      audio_path: 混合音频路径
      silence_periods: [{"start": s, "end": e, "duration": d}, ...]
      total_duration: 音频总时长(秒)
    """
    num_clips = len(material_clips)
    if num_clips == 0:
        raise ValueError("素材列表为空")
    if not silence_periods:
        logger.info("无锚点，回落普通合成")
        return compose_video(material_clips, audio_path, output_path,
                             subtitles_path=subtitles_path, resolution=resolution)

    import tempfile

    # 1. 在静音中点附近切割素材段落
    transitions = [0.0]  # 每个切换点的时间(秒)
    for s in silence_periods:
        mid = (s["start"] + s["end"]) / 2
        if mid > transitions[-1] + 0.5:  # 至少间隔0.5s
            transitions.append(mid)
    transitions.append(total_duration)

    # 2. 为每段分配素材（循环使用）
    seg_info = []  # [(clip_path, start, end), ...]
    clip_idx = 0
    for i in range(len(transitions) - 1):
        seg_start = transitions[i]
        seg_end = transitions[i + 1]
        dur = seg_end - seg_start
        if dur < 0.3:
            continue  # 跳过过短段落
        seg_info.append((material_clips[clip_idx % num_clips], seg_start, seg_end))
        clip_idx += 1

    logger.info(f"锚点分段: {len(seg_info)} 段, 使用 {min(clip_idx, num_clips)}/{num_clips} 个素材")

    # 3. 渲染每段为独立视频
    temp_dir = tempfile.mkdtemp(prefix="ave_anchor_")
    seg_files = []
    for idx, (clip, seg_s, seg_e) in enumerate(seg_info):
        out = os.path.join(temp_dir, f"seg_{idx:03d}.mp4")
        dur = seg_e - seg_s
        # 从该素材中截取一段 (用素材的一部分，避免只用开头)
        clip_dur = _get_media_duration(clip)
        offset_in_clip = (seg_s * 15) % max(clip_dur, 1)  # 取素材中不同位置
        offset_in_clip = min(offset_in_clip, max(clip_dur - dur, 0))

        # 用 FFmpeg 截取该素材的一段
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(offset_in_clip),
            "-i", clip,
            "-t", str(dur),
            "-vf", f"scale={resolution.replace('x',':')},setsar=1,fps=30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            out,
        ], capture_output=True, timeout=120, check=True)
        seg_files.append(out)

    # 4. 简单 concat 拼接 (含交叉淡变的 xfade 链 >10段容易 FFmpeg 崩溃)
    #    用 concat demuxer 直接拼接，素材切换本身已提供视觉变化
    concat_list = _create_concat_list(seg_files)

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list,
        "-i", audio_path,
        "-af", "afade=t=in:d=1,afade=t=out:st={}:d=1".format(max(0, total_duration - 1)),
    ]

    if subtitles_path and os.path.exists(subtitles_path):
        cmd += ["-vf", f"subtitles={subtitles_path}"]

    cmd += ["-shortest", "-c:v", "libx264", "-preset", "medium", "-b:v", DEFAULT_BITRATE,
            "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", output_path]

    subprocess.run(cmd, capture_output=True, check=True, timeout=600)

    # 清理
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

    logger.info(f"锚点驱动合成完成: {output_path}")
    return output_path


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
    subtitles_path: str | None = None,
    resolution: str = DEFAULT_RESOLUTION,
):
    """渲染单个分段（裁剪音频+对齐素材）"""
    duration = end_sec - start_sec
    # 用 concat 合并所有素材作为视频源
    concat_file = _create_concat_list(material_clips)

    filters = [
        f"[0:v]setpts=PTS-STARTPTS,scale={resolution.replace('x',':')},fps=30[v]",
        f"[1:a]atrim=start={start_sec}:duration={duration},asetpts=PTS-STARTPTS[a]",
    ]

    if subtitles_path and os.path.exists(subtitles_path):
        filters.append(f"[v]subtitles={subtitles_path}[vo]")
        map_v = "[vo]"
    else:
        map_v = "[v]"

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-i", audio_path,
        "-filter_complex", ";".join(filters),
        "-map", map_v, "-map", "[a]",
        "-shortest",
        "-c:v", "libx264", "-preset", "medium", "-b:v", DEFAULT_BITRATE,
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=600)

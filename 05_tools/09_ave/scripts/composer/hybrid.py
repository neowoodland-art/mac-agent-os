"""
AVE hybrid — 口播+卡点融合管线

功能:
  将口播的语音锚点驱动画面切换 + 卡点的BGM能量驱动变速结合起来。
  人声决定"什么时候切画面", BGM决定"画面怎么动"。

流程:
  1. 检测人声锚点 (静音段 → 段边界)
  2. 检测 BGM 节拍 + 能量特征
  3. 混音 (人声+BGM, BGM 音量避让)
  4. 为每段分配素材 + 能量驱动变速
  5. 渲染每段 + 字幕叠加
  6. 帧锁定拼接

用法:
  from composer.hybrid import compose_hybrid

  compose_hybrid(
      voice_path="narration.wav",
      bgm_path="bgm.wav",
      output_path="hybrid.mp4",
      texts=["第一段文案", "第二段文案", ...],
  )
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from lib.logger import get_logger

logger = get_logger("hybrid")


def compose_hybrid(
    voice_path: str,
    bgm_path: str,
    output_path: str = "hybrid.mp4",
    material_clips: list[str] | None = None,
    resolution: str = "1080x1920",
    texts: list[str] | None = None,
    pexels_api_key: str = "",
    pexels_search: str = "",
    # 口播锚点参数
    min_silence_sec: float = 0.15,
    voice_volume: float = 1.0,
    bgm_volume: float = 0.35,
    # 卡点速度参数
    enable_speed_ramp: bool = True,
    base_speed: float = 1.0,
    high_speed: float = 1.5,
    low_speed: float = 0.7,
    # 节拍分组
    group_size: int = 4,
) -> str:
    """
    口播+卡点融合管线

    参数:
      voice_path: 人声 WAV 路径
      bgm_path: BGM 音频路径
      output_path: 输出视频路径
      material_clips: 素材视频/图片列表 (可选)
      resolution: 输出分辨率
      texts: 每段文字 (用于字幕, 可选)
      pexels_api_key: Pexels API Key (素材不够时补充)
      pexels_search: Pexels 搜索关键词
      min_silence_sec: 最小静音时长 (秒), 用于分割段
      voice_volume: 人声音量 (默认 1.0)
      bgm_volume: BGM 音量 (默认 0.35)
      enable_speed_ramp: 是否启用能量驱动变速
      base_speed: 基础速度
      high_speed: 高能段速度
      low_speed: 低能段速度
      group_size: BGM 节拍分组数

    返回: output_path
    """
    logger.info("=== 口播+卡点融合模式 ===")
    logger.info(f"人声: {voice_path}")
    logger.info(f"BGM:  {bgm_path}")

    # ── 1. 检测人声锚点 ──
    from anchor_extractor.extractor import get_silence_periods
    silences = get_silence_periods(voice_path, min_silence_sec=min_silence_sec)
    
    # 获取人声总时长
    voice_duration = _get_duration(voice_path)
    
    # 从静音段反推活跃段 (说话段)
    voice_segments = _silences_to_segments(silences, voice_duration)
    logger.info(f"  锚点检测: {len(silences)} 个静音 → {len(voice_segments)} 个说话段")

    # ── 2. 检测 BGM 节拍 (含能量) ──
    from composer.beat_sync import detect_beats
    beat_info = detect_beats(bgm_path, group_size=group_size, enable_energy=enable_speed_ramp)
    bgm_segments = beat_info["segments"]
    logger.info(f"  BPM: {beat_info['bpm']:.0f}, {beat_info['beat_count']}拍, {len(bgm_segments)}组")

    # ── 3. 混音 (人声+BGM, 避让) ──
    temp_dir = tempfile.mkdtemp(prefix="ave_hybrid_")
    mixed_audio = os.path.join(temp_dir, "mixed.wav")
    
    # BGM 避让: 说话时压低BGM
    mixed_audio = _duck_and_mix(
        voice_path, bgm_path, voice_segments, mixed_audio,
        voice_volume=voice_volume, bgm_volume=bgm_volume,
    )

    # ── 4. 准备素材 ──
    clips = list(material_clips) if material_clips else []
    if len(clips) < len(voice_segments) and pexels_api_key:
        from material_producer.pexels.search import search_videos
        needed = len(voice_segments) - len(clips)
        logger.info(f"  素材不足, 从 Pexels 搜索 {needed} 个...")
        kw = pexels_search or "background video"
        found = search_videos(kw, count=needed, api_key=pexels_api_key, orientation="portrait")
        for f in found:
            clips.append(f["path"])
        logger.info(f"  共 {len(clips)} 个素材")

    if not clips:
        raise ValueError("无可用素材")

    # ── 5. 为每段分配素材 + 计算速度 ──
    # 将 BGM 节拍能量映射到每个说话段上
    fps = 30
    seg_plans = []  # [(clip_path, adjusted_dur, speed), ...]
    
    for idx, vseg in enumerate(voice_segments):
        clip = clips[idx % len(clips)]
        v_start = vseg["start"]
        v_end = vseg["end"]
        v_dur = v_end - v_start

        if v_dur < 0.5:
            continue

        # 在该时间段内计算 BGM 平均能量
        avg_energy = _average_energy_in_range(bgm_segments, v_start, v_end)
        speed = base_speed
        if enable_speed_ramp:
            if avg_energy > 0.6:
                speed = base_speed + (high_speed - base_speed) * min((avg_energy - 0.6) / 0.4, 1.0)
            elif avg_energy < 0.3:
                speed = low_speed + (base_speed - low_speed) * (avg_energy / 0.3)
            speed = max(0.5, min(2.0, speed))

        # 帧锁定时长
        frames = round(v_dur * fps)
        dur_aligned = frames / fps
        
        seg_plans.append({
            "clip": clip,
            "start": v_start,
            "end": v_end,
            "duration": dur_aligned,
            "speed": speed,
            "energy": avg_energy,
        })

    logger.info(f"  分配 {len(seg_plans)} 段素材"
                + (f", 变速范围 {low_speed:.1f}~{high_speed:.1f}x" if enable_speed_ramp else ""))

    # ── 6. 渲染每段 ──
    seg_files = []
    for idx, plan in enumerate(seg_plans):
        clip = plan["clip"]
        dur = plan["duration"]
        speed = plan["speed"]
        mt = dur / max(speed, 0.01)  # 素材需要的时间长度

        seg_file = os.path.join(temp_dir, f"seg_{idx:03d}.mp4")

        # 从素材中截取一段 (考虑变速)
        clip_dur = _get_duration(clip)
        offset = (plan["start"] * 17) % max(clip_dur - mt, 0.1) if clip_dur > mt else 0

        raw_seg = os.path.join(temp_dir, f"seg_{idx:03d}_raw.mp4")
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(offset),
            "-i", clip,
            "-t", str(mt),
            "-vf", f"scale={resolution.replace('x',':')},setsar=1,fps={fps}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-an", raw_seg,
        ], capture_output=True, timeout=120, check=True)

        if speed != 1.0 and 0.5 <= speed <= 2.0:
            subprocess.run([
                "ffmpeg", "-y", "-i", raw_seg,
                "-filter_complex", f"setpts={1/speed}*PTS[v]",
                "-map", "[v]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-pix_fmt", "yuv420p", seg_file,
            ], capture_output=True, timeout=120, check=True)
        else:
            os.replace(raw_seg, seg_file)

        seg_files.append(seg_file)

    if not seg_files:
        raise RuntimeError("渲染失败: 无有效段")

    # ── 7. 拼接 ──
    if len(seg_files) == 1:
        cmd = ["ffmpeg", "-y", "-i", seg_files[0], "-i", mixed_audio,
               "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", output_path]
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
    else:
        _concat_hybrid_segments(seg_files, mixed_audio, output_path, seg_plans, fps)

    # ── 8. 字幕叠加 ──
    if texts and len(texts) > 0 and seg_plans:
        _add_text_subtitles(output_path, texts, seg_plans, resolution)

    # ── 9. 清理 ──
    shutil.rmtree(temp_dir, ignore_errors=True)

    final_size = os.path.getsize(output_path) / 1024 / 1024
    logger.info(f"✅ 融合完成: {output_path} ({final_size:.1f}MB, "
                f"{len(seg_files)} 段{', 能量变速' if enable_speed_ramp else ''})")
    return output_path


# ── 内部辅助函数 ──────────────────────────────────────────


def _silences_to_segments(silences: list[dict], total_duration: float) -> list[dict]:
    """从静音段反推人声活跃段"""
    if not silences:
        return [{"start": 0.0, "end": total_duration}]

    segments = []
    prev_end = 0.0

    for s in silences:
        s_start = s.get("start", 0)
        s_end = s.get("end", 0)
        if s_start > prev_end + 0.1:
            segments.append({"start": prev_end, "end": s_start})
        prev_end = s_end

    if prev_end < total_duration - 0.3:
        segments.append({"start": prev_end, "end": total_duration})

    if not segments:
        return [{"start": 0.0, "end": total_duration}]

    return segments


def _average_energy_in_range(bgm_segments: list[dict], start: float, end: float) -> float:
    """计算时间范围 [start, end] 内 BGM 的平均能量"""
    energies = []
    for seg in bgm_segments:
        seg_start = seg["start"]
        seg_end = seg["end"]
        # 检查重叠
        if seg_end < start or seg_start > end:
            continue
        energy = seg.get("energy", 0.5)
        overlap = min(seg_end, end) - max(seg_start, start)
        if overlap > 0:
            energies.append((energy, overlap))

    if not energies:
        return 0.5

    # 加权平均 (按重叠时长)
    total_weight = sum(w for _, w in energies) or 1.0
    avg = sum(e * w for e, w in energies) / total_weight
    return max(0.0, min(1.0, avg))


def _duck_and_mix(
    voice_path: str,
    bgm_path: str,
    voice_segments: list[dict],
    output_path: str,
    voice_volume: float = 1.0,
    bgm_volume: float = 0.35,
) -> str:
    """
    BGM 音量避让混音:
    - 说话时: BGM 音量降到 bgm_volume * 0.4
    - 间隙时: BGM 恢复到 bgm_volume
    """
    import numpy as np
    import soundfile as sf

    # 加载音频
    voice, sr_v = sf.read(voice_path)
    bgm, sr_b = sf.read(bgm_path)

    # 重采样 BGM 到相同 sr
    if sr_b != sr_v:
        import librosa
        bgm = librosa.resample(bgm, orig_sr=sr_b, target_sr=sr_v)

    # 补齐 BGM 到人声长度
    if len(bgm) < len(voice):
        repeats = int(np.ceil(len(voice) / len(bgm)))
        bgm = np.tile(bgm, repeats)
    bgm = bgm[:len(voice)]

    # 创建音量包络: 说话段压低 BGM
    bgm_envelope = np.ones(len(voice))
    for seg in voice_segments:
        s = int(seg["start"] * sr_v)
        e = int(seg["end"] * sr_v)
        bgm_envelope[s:e] = 0.4  # 说话时 BGM 降到 40%

    # 平滑过渡 (0.05s fade)
    fade_samples = int(0.05 * sr_v)
    for i in range(1, len(bgm_envelope) - fade_samples * 2):
        if bgm_envelope[i] != bgm_envelope[i - 1]:
            # 在变化点做淡变
            start = max(0, i - fade_samples)
            end = min(len(bgm_envelope), i + fade_samples)
            for j in range(start, end):
                frac = (j - start) / max(end - start, 1)
                bgm_envelope[j] = bgm_envelope[start] + frac * (bgm_envelope[end - 1] - bgm_envelope[start])

    # 混音
    voice_float = voice.astype(np.float32)
    bgm_float = bgm.astype(np.float32)

    # 归一化到 [-1, 1]
    voice_float /= max(np.max(np.abs(voice_float)), 0.001)
    bgm_float /= max(np.max(np.abs(bgm_float)), 0.001)

    mixed = voice_float * voice_volume + bgm_float * bgm_volume * bgm_envelope

    # 限制防止爆音
    peak = np.max(np.abs(mixed))
    if peak > 0.99:
        mixed /= peak * 1.02

    sf.write(output_path, mixed, sr_v)
    logger.debug(f"  混音完成: {output_path} ({sr_v}Hz, {len(voice)/sr_v:.1f}s)")
    return output_path


def _concat_hybrid_segments(
    seg_files: list[str],
    mixed_audio: str,
    output_path: str,
    seg_plans: list[dict],
    fps: int = 30,
) -> str:
    """帧锁定拼接混合音频"""
    if len(seg_files) == 1:
        cmd = ["ffmpeg", "-y", "-i", seg_files[0], "-i", mixed_audio,
               "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", output_path]
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
        return output_path

    # concat demuxer 拼接视频
    concat_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w").name
    with open(concat_file, "w") as f:
        for sf in seg_files:
            f.write(f"file '{os.path.abspath(sf)}'\n")

    video_only = output_path.replace(".mp4", "_novideo.mp4")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
           "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-an", video_only]
    subprocess.run(cmd, capture_output=True, timeout=300, check=True)

    # 叠加混合音频
    cmd2 = ["ffmpeg", "-y", "-i", video_only, "-i", mixed_audio,
            "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", output_path]
    subprocess.run(cmd2, capture_output=True, timeout=120, check=True)

    os.unlink(concat_file)
    if os.path.exists(video_only):
        os.unlink(video_only)

    logger.info(f"  ✅ 拼接完成: {len(seg_files)} 段")
    return output_path


def _add_text_subtitles(
    video_path: str,
    texts: list[str],
    seg_plans: list[dict],
    resolution: str,
):
    """为每段叠加文字字幕 (ASS 格式)"""
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
        if i >= len(seg_plans):
            break
        start = seg_plans[i]["start"]
        dur = seg_plans[i]["duration"]
        end = start + dur

        def _fmt_ts(sec: float) -> str:
            h = int(sec // 3600)
            m = int((sec % 3600) // 60)
            s = sec % 60
            return f"{h}:{m:02d}:{s:05.2f}"

        lines.append(
            f"Dialogue: 0,{_fmt_ts(start)},{_fmt_ts(end)},Default,,0,0,0,,{text}"
        )

    ass_path = video_path.replace(".mp4", "_hybrid_text.ass")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    tmp = video_path.replace(".mp4", "_tmp.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"subtitles={ass_path}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy", "-pix_fmt", "yuv420p", tmp,
    ], capture_output=True, timeout=120, check=True)
    os.replace(tmp, video_path)
    os.remove(ass_path)

    logger.info(f"  ✅ 字幕叠加: {len(texts)} 段")


def _get_duration(path: str) -> float:
    """获取媒体文件时长"""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
                           capture_output=True, text=True, timeout=10)
        return float(r.stdout.strip())
    except Exception:
        return 30.0

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
import shutil
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
    enable_energy: bool = False,
    detect_structure: bool = False,
) -> dict:
    """
    检测 BGM 节拍

    参数:
      audio_path: BGM 音频路径
      group_size: 每组节拍数 (默认4拍/组)
      enable_energy: 是否提取 RMS/频谱能量特征 (用于变速卡点)
      detect_structure: 是否检测歌曲结构 (Intro/Verse/Chorus/Bridge/Outro)

    返回:
      {
        "bpm": 120.0,
        "beat_times": [0.0, 0.5, 1.0, ...],
        "segments": [{"start": 0.0, "end": 2.0, "beats": 4, "energy": 0.8, ...}, ...],
        "structure": [{"label": "Intro", "start": 0.0, "end": 8.0, ...}],
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

    # 提取 RMS 和频谱能量
    rms_energy = None
    spectral_features = None
    if enable_energy:
        # 用短时傅立叶提取帧级能量
        hop_length = 512
        frame_dur = hop_length / sr
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        rms_energy = rms.tolist()
        logger.debug(f"  能量帧: {len(rms_energy)} 帧, 帧时长={frame_dur:.3f}s")

        # 频谱 flux
        spec = np.abs(librosa.stft(y, hop_length=hop_length))
        flux = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
        spectral_features = {
            "rms": rms_energy,
            "flux": flux.tolist() if hasattr(flux, 'tolist') else [],
            "hop_length": hop_length,
            "frame_duration": frame_dur,
        }

    # 歌曲结构检测
    song_structure = None
    if detect_structure:
        song_structure = _detect_song_structure(y, sr, duration)
        if song_structure:
            logger.info(f"  歌曲结构: {len(song_structure)} 段")
            for s in song_structure:
                logger.info(f"    {s['label']:8s} {s['start']:.0f}s→{s['end']:.0f}s")

    # 按 N拍 分组
    segments = []
    max_beats_per_seg = 0
    for i in range(0, len(beat_times), group_size):
        start = beat_times[i]
        end = beat_times[min(i + group_size, len(beat_times) - 1)]
        actual_beats = min(group_size, len(beat_times) - i)
        if end - start > 0.3:
            seg = {
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(end - start, 2),
                "beats": actual_beats,
            }
            # 计算该段平均能量
            if enable_energy and rms_energy is not None and spectral_features:
                seg["energy"] = _segment_energy(start, end, spectral_features)
            segments.append(seg)
            max_beats_per_seg = max(max_beats_per_seg, actual_beats)

    # 最后一段: 最后一个拍点到音频结束
    if segments and segments[-1]["end"] < duration - 0.3:
        seg = {
            "start": segments[-1]["end"],
            "end": round(duration, 2),
            "duration": round(duration - segments[-1]["end"], 2),
            "beats": 0,
        }
        if enable_energy and spectral_features:
            seg["energy"] = _segment_energy(seg["start"], seg["end"], spectral_features)
        segments.append(seg)

    # 限制 ≤8 组 (xfade 链限制)
    if len(segments) > 8:
        keep = segments[:7]
        remaining = segments[7:]
        merged = {
            "start": keep[-1]["end"],
            "end": round(duration, 2),
            "duration": round(duration - keep[-1]["end"], 2),
            "beats": sum(s["beats"] for s in remaining),
        }
        if enable_energy and "energy" in remaining[0]:
            merged["energy"] = sum(
                s.get("energy", 0) * s["duration"] for s in remaining
            ) / max(merged["duration"], 0.1)
        keep.append(merged)
        segments = keep
        logger.info(f"  合并为 {len(segments)} 组 (≤8)")

    result = {
        "bpm": tempo_val,
        "beat_count": len(beat_times),
        "segments": segments,
        "total_duration": round(duration, 2),
    }
    if song_structure:
        result["structure"] = song_structure
    if spectral_features:
        result["spectral"] = spectral_features

    return result


def _segment_energy(start_sec: float, end_sec: float,
                    spectral: dict) -> float:
    """计算某时间段的平均归一化能量 (基于 RMS + Flux)"""
    frame_dur = spectral["frame_duration"]
    rms = spectral.get("rms", [])
    flux = spectral.get("flux", [])

    if not rms:
        return 0.5

    start_frame = int(start_sec / max(frame_dur, 0.001))
    end_frame = int(end_sec / max(frame_dur, 0.001))
    start_frame = max(0, min(start_frame, len(rms) - 1))
    end_frame = max(start_frame + 1, min(end_frame, len(rms)))

    seg_rms = rms[start_frame:end_frame]
    if not seg_rms:
        return 0.5

    avg_rms = sum(seg_rms) / len(seg_rms) if seg_rms else 0
    avg_flux = sum(flux[start_frame:end_frame]) / len(seg_rms) if flux and len(seg_rms) > 0 else 0

    # 归一化: 用全局均值和 std
    rms_mean = sum(rms) / len(rms) if rms else 0.1
    rms_std = (sum((v - rms_mean)**2 for v in rms) / len(rms)) ** 0.5 if rms and len(rms) > 1 else rms_mean
    rms_std = max(rms_std, rms_mean * 0.01)

    energy = (avg_rms - rms_mean) / rms_std * 0.3 + 0.5
    return max(0.0, min(1.0, energy))


def _detect_song_structure(y, sr, duration) -> list[dict]:
    """
    检测歌曲结构段落

    基于 chroma 特征 + 自相似矩阵 + 时序聚类,
    输出: Intro / Verse / Chorus / Bridge / Outro
    """
    import numpy as np
    import librosa

    try:
        # 提取 chroma 特征
        hop_length = 2048
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
        frame_dur = hop_length / sr

        # 自相似矩阵 + 递归分割
        ssm = librosa.segment.recurrence_matrix(chroma, axis=0)
        bounds = librosa.segment.agglomerative(ssm, k=min(8, ssm.shape[0]))
        bounds_frames = librosa.segment.subsegment(ssm, bounds, n_segments=2)

        # 转换为时间
        boundaries = [0.0]
        for bf in bounds_frames:
            t = float(bf) * frame_dur
            if t < duration - 1:
                boundaries.append(round(t, 1))
        boundaries.append(round(duration, 1))

        # 按时间比例分配标签
        labels = _label_structure(boundaries, duration)

        result = []
        for i in range(len(boundaries) - 1):
            result.append({
                "label": labels[i] if i < len(labels) else "Section",
                "start": boundaries[i],
                "end": boundaries[i + 1],
                "duration": round(boundaries[i + 1] - boundaries[i], 1),
            })

        return result
    except Exception as e:
        logger.warning(f"  歌曲结构检测失败: {e}")
        return []


def _label_structure(boundaries: list[float], total_duration: float) -> list[str]:
    """根据段落在歌曲中的位置分配典型结构标签"""
    n = len(boundaries) - 1
    labels = []

    # 按位置比例分配
    positions = []
    for i in range(n):
        mid = (boundaries[i] + boundaries[i + 1]) / 2 / max(total_duration, 1)
        positions.append(mid)

    for i, pos in enumerate(positions):
        if i == 0 and pos < 0.05:
            labels.append("Intro")
        elif i >= n - 2 and pos > 0.85:
            labels.append("Outro")
        elif 0.15 <= pos <= 0.65:
            # 很可能在 Chorus 区
            labels.append("Chorus" if i % 2 == 1 else "Verse")
        elif pos < 0.15:
            labels.append("Verse")
        elif pos < 0.4:
            labels.append("Pre-Chorus" if i % 2 == 0 else "Chorus")
        else:
            labels.append("Bridge" if pos < 0.75 else "Outro")

    return labels


def compose_beat_sync(
    bgm_path: str,
    output_path: str = "beat_sync.mp4",
    material_clips: list[str] | None = None,
    group_size: int = 4,
    resolution: str = "1080x1920",
    texts: list[str] | None = None,
    pexels_api_key: str = "",
    pexels_search: str = "",
    enable_speed_ramp: bool = False,
    frame_locked: bool = True,
    base_speed: float = 1.0,
    high_speed: float = 1.5,
    low_speed: float = 0.7,
) -> str:
    """
    BGM 节拍驱动的卡点视频合成 (V2: 能量感知 + 帧锁定)

    参数:
      bgm_path: BGM 音频路径
      output_path: 输出视频路径
      material_clips: 素材视频/图片列表 (可选, 不提供则 Pexels 搜索)
      group_size: 每组节拍数
      resolution: 输出分辨率
      texts: 每段叠加的文字 (可选)
      pexels_api_key: Pexels API Key
      pexels_search: Pexels 搜索关键词
      enable_speed_ramp: 是否启用能量驱动变速 (高能加速, 低能减速)
      frame_locked: 是否启用帧锁定时间线 (消除 xfade 漂移)
      base_speed: 基础速度 (默认 1.0)
      high_speed: 高能段速度 (默认 1.5)
      low_speed: 低能段速度 (默认 0.7)

    返回: output_path
    """
    if not os.path.exists(bgm_path):
        raise FileNotFoundError(f"BGM 文件不存在: {bgm_path}")

    # 1. 节拍检测 (启用能量)
    logger.info("=== Beat-Sync 卡点模式 ===")
    logger.info(f"BGM: {bgm_path}")
    beat_info = detect_beats(bgm_path, group_size, enable_energy=enable_speed_ramp)
    segments = beat_info["segments"]
    total_dur = beat_info["total_duration"]
    logger.info(f"BPM: {beat_info['bpm']}, {beat_info['beat_count']}拍, {len(segments)}组")

    if enable_speed_ramp and "energy" in segments[0]:
        energies = [s.get("energy", 0.5) for s in segments]
        avg_e = sum(energies) / len(energies) if energies else 0.5
        logger.info(f"  能量感知变速: ON (均值 {avg_e:.2f}, 范围 {min(energies):.2f}~{max(energies):.2f})")

    # 2. 准备素材
    clips = material_clips or []
    if len(clips) < len(segments) and pexels_api_key:
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
    seg_materials = []  # [(clip_path, adjusted_start, adjusted_end, adjusted_duration, speed), ...]
    for i, seg in enumerate(segments):
        clip = clips[i % len(clips)]

        # 计算本段速度 (能量驱动变速)
        speed = base_speed
        if enable_speed_ramp:
            energy = seg.get("energy", 0.5)
            if energy > 0.6:
                speed = base_speed + (high_speed - base_speed) * min((energy - 0.6) / 0.4, 1.0)
            elif energy < 0.3:
                speed = low_speed + (base_speed - low_speed) * (energy / 0.3)
            speed = max(0.5, min(2.0, speed))

        # 调整时长 (变速后实际画面时长)
        orig_dur = seg["duration"]
        if frame_locked:
            # 帧锁定: 以 BGM 节拍为准, 用 fps 对齐到整帧
            fps = 30
            orig_frames = round(orig_dur * fps)
            adjusted_dur = orig_frames / fps  # 帧对齐后的时长
        else:
            adjusted_dur = orig_dur

        # 变速后的素材播放时长 = adjusted_dur / speed
        # 即: 如果加速 (speed>1), 需要更短的素材
        material_time_needed = adjusted_dur / speed if speed > 0 else adjusted_dur

        seg_materials.append((clip, seg["start"], seg["end"],
                              adjusted_dur, speed, material_time_needed))

    logger.info(f"分配素材: {len(seg_materials)} 段, {len(clips)} 素材循环"
                + (f", 变速范围 {low_speed:.1f}~{high_speed:.1f}x" if enable_speed_ramp else ""))

    # 4. 帧锁定: 预计算精确的 xfade 偏移
    if frame_locked:
        fps = 30
        # 精确计算每段的累计偏移
        cumulative_frames = 0
        for idx, (clip, start, end, dur, speed, mt) in enumerate(seg_materials):
            seg_frames = round(dur * fps)
            seg_materials[idx] = (clip, start, dur, speed, mt, seg_frames)
        logger.info(f"  帧锁定: ON (30fps)")

    # 5. 渲染每组为独立视频片段 (带变速)
    temp_dir = tempfile.mkdtemp(prefix="ave_beat_")
    seg_files = []
    for idx in range(len(seg_materials)):
        clip, start_orig, dur, speed, mt, *rest = seg_materials[idx]
        if frame_locked:
            seg_frames = rest[0] if rest else round(dur * 30)
            # 帧对齐时长
            dur_aligned = seg_frames / 30.0
        else:
            dur_aligned = dur
            seg_frames = 0

        seg_file = os.path.join(temp_dir, f"seg_{idx:03d}.mp4")

        # 从素材中取一段 (考虑变速需要)
        clip_dur = _get_duration(clip)
        offset = (start_orig * 17) % max(clip_dur - mt, 0.1) if clip_dur > mt else 0

        # 先截取素材, 再变速
        raw_seg = os.path.join(temp_dir, f"seg_{idx:03d}_raw.mp4")
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(offset),
            "-i", clip,
            "-t", str(mt),
            "-vf", f"scale={resolution.replace('x',':')},setsar=1,fps=30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-an", raw_seg,
        ], capture_output=True, timeout=120, check=True)

        if speed != 1.0 and speed >= 0.5 and speed <= 2.0:
            # 变速处理
            subprocess.run([
                "ffmpeg", "-y", "-i", raw_seg,
                "-filter_complex",
                f"setpts={1/speed}*PTS[v]",
                "-map", "[v]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-pix_fmt", "yuv420p",
                seg_file,
            ], capture_output=True, timeout=120, check=True)
        else:
            os.replace(raw_seg, seg_file)

        seg_files.append(seg_file)

    # 6. 使用帧锁定时间线拼接
    if len(seg_files) == 1:
        subprocess.run(["ffmpeg", "-y", "-i", seg_files[0], "-i", bgm_path,
                        "-shortest", "-c:v", "copy", "-c:a", "aac", output_path],
                       capture_output=True, check=True, timeout=60)
        return _finalize(output_path, texts, seg_materials, resolution, temp_dir)

    if frame_locked:
        return _concat_frame_locked(seg_files, bgm_path, seg_materials,
                                     output_path, texts, resolution, temp_dir)
    else:
        return _concat_xfade(seg_files, bgm_path, seg_materials,
                              output_path, texts, resolution, temp_dir)


def _concat_frame_locked(
    seg_files: list[str],
    bgm_path: str,
    seg_materials: list,
    output_path: str,
    texts: list[str] | None,
    resolution: str,
    temp_dir: str,
) -> str:
    """帧锁定拼接: 用 concat demuxer 精确拼接, 无 xfade 漂移"""
    if len(seg_files) == 1:
        # 只有一段, 直接合并 BGM
        cmd = ["ffmpeg", "-y", "-i", seg_files[0], "-i", bgm_path,
               "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", output_path]
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
        return _finalize(output_path, texts, seg_materials, resolution, temp_dir)

    # 用 concat demuxer 拼接 (帧精确, 无过渡)
    concat_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w").name
    with open(concat_file, "w") as f:
        for sf in seg_files:
            f.write(f"file '{os.path.abspath(sf)}'\n")

    # 先拼视频
    video_only = output_path.replace(".mp4", "_novideo.mp4")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
           "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-an", video_only]
    subprocess.run(cmd, capture_output=True, timeout=300, check=True)

    # 叠加 BGM
    cmd2 = ["ffmpeg", "-y", "-i", video_only, "-i", bgm_path,
            "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", output_path]
    subprocess.run(cmd2, capture_output=True, timeout=120, check=True)

    os.unlink(concat_file)
    os.unlink(video_only)

    logger.info(f"  ✅ 帧锁定拼接完成: {len(seg_files)} 段")
    return _finalize(output_path, texts, seg_materials, resolution, temp_dir)


def _concat_xfade(
    seg_files: list[str],
    bgm_path: str,
    seg_materials: list,
    output_path: str,
    texts: list[str] | None,
    resolution: str,
    temp_dir: str,
) -> str:
    """xfade 过渡拼接: ≤8 段, 逐段交叉淡入淡出"""
    if len(seg_files) == 1:
        cmd = ["ffmpeg", "-y", "-i", seg_files[0], "-i", bgm_path,
               "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", output_path]
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
        return _finalize(output_path, texts, seg_materials, resolution, temp_dir)

    # 构建 xfade 链
    # xfade=transition=fade:duration=0.5:offset=offset1
    # 每段重叠 0.5s, 累计偏移
    filter_parts = []
    inputs = []
    offset = 0.0
    prev_label = "v0"

    for i in range(len(seg_files)):
        inputs += ["-i", seg_files[i]]
        if i == 0:
            continue
        # 前一段的时长
        seg_dur = seg_materials[i - 1][2] if i - 1 < len(seg_materials) else 1.0
        offset += float(seg_dur) - 0.5  # 减去过渡重叠
        label = f"v{i}"
        filter_parts.append(
            f"[{prev_label}][{label}]xfade=transition=fade:duration=0.5:offset={offset:.2f}[v{i}]"
        )
        prev_label = f"v{i}"

    # 最终输出标签是 v{len(seg_files)-1}
    last_label = f"v{len(seg_files) - 1}"
    full_filter = ";".join(filter_parts)

    video_xfade = output_path.replace(".mp4", "_xfade.mp4")
    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", full_filter,
        "-map", f"[{last_label}]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        video_xfade,
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=300, check=True)
    except subprocess.CalledProcessError as e:
        logger.warning(f"  xfade 失败, 回落 concat: {e.stderr[:200]}")
        # 回落: concat demuxer
        concat_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w").name
        with open(concat_file, "w") as f:
            for sf in seg_files:
                f.write(f"file '{os.path.abspath(sf)}'\n")
        cmd_fb = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
                   "-c:v", "libx264", "-preset", "fast", "-crf", "23", video_xfade]
        subprocess.run(cmd_fb, capture_output=True, timeout=300, check=True)
        os.unlink(concat_file)

    # 叠加 BGM
    cmd2 = ["ffmpeg", "-y", "-i", video_xfade, "-i", bgm_path,
            "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", output_path]
    subprocess.run(cmd2, capture_output=True, timeout=120, check=True)
    os.unlink(video_xfade)

    logger.info(f"  ✅ xfade 拼接完成: {len(seg_files)} 段")
    return _finalize(output_path, texts, seg_materials, resolution, temp_dir)


def _finalize(
    output_path: str,
    texts: list[str] | None,
    seg_materials: list,
    resolution: str,
    temp_dir: str,
) -> str:
    """最终处理: 叠加文字字幕 + 清理临时目录"""
    import shutil

    # 叠加文字
    if texts and len(texts) > 0 and seg_materials:
        _add_text_subtitles(output_path, texts, seg_materials, resolution)
        logger.info(f"  ✅ 文字叠加: {len(texts)} 段")

    # 清理临时目录
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.debug(f"  临时目录已清理: {temp_dir}")

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

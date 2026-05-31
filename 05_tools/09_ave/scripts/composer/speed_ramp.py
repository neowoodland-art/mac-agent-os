"""
AVE speed_ramp — 变速卡点引擎

功能:
  1. 对视频/音频施加匀速变速
  2. 缓变速度曲线: 将视频分段, 每段不同速度, 组合成渐变效果
  3. 卡点策略集成: 根据能量/节拍密度生成动态速度曲线

核心: FFmpeg setpts(视频) + atempo(音频) 滤波器链

用法:
  from composer.speed_ramp import speed_ramp, speed_curve

  # 匀速 0.8x
  speed_ramp("input.mp4", "slow.mp4", speed=0.8)

  # 缓变 0.7→1.0→1.3 (6段渐变)
  speed_ramp("input.mp4", "ramp.mp4", curve=[0.7, 1.0, 1.3], segments=6)

  # 节拍驱动的变速 (高能段加速, 低能段减速)
  speed_by_energy("input.mp4", beat_info={"segments": [...]}, output="energy_ramp.mp4")
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from lib.logger import get_logger

logger = get_logger("speed_ramp")

# ── 常量 ──────────────────────────────────────────────────

# atempo 支持的范围: 0.5~2.0 (单次)
# 需要更极端的变速时, 级联多个 atempo
ATEMPO_MIN = 0.5
ATEMPO_MAX = 2.0


# ── 公共 API ──────────────────────────────────────────────

def speed_ramp(
    input_path: str,
    output_path: str = "speed_ramp.mp4",
    speed: float = 1.0,
    curve: list[float] | None = None,
    segments: int = 6,
    keep_audio: bool = True,
) -> str:
    """
    变速处理

    参数:
      input_path: 输入视频路径
      output_path: 输出视频路径
      speed: 匀速倍率 (curve 为空时使用)
      curve: 缓变速度曲线 [起点倍率, ..., 终点倍率] (优先于 speed)
             例: [0.7, 1.0, 1.3] 表示从 0.7x 渐变到 1.3x
      segments: 缓变分段数 (越多越平滑, 默认 6)
      keep_audio: 是否保留音频 (默认 True)

    返回: output_path
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    duration = _get_duration(input_path)

    if curve and len(curve) >= 2:
        return _apply_curve(input_path, output_path, curve, segments, duration, keep_audio)
    else:
        return _apply_constant(input_path, output_path, speed, duration, keep_audio)


def speed_by_energy(
    input_path: str,
    output_path: str = "energy_ramp.mp4",
    beat_segments: list[dict] | None = None,
    base_speed: float = 1.0,
    high_speed: float = 1.5,
    low_speed: float = 0.7,
    keep_audio: bool = True,
) -> str:
    """
    按节拍能量生成变速曲线

    beat_segments 格式: [{"start": 0.0, "end": 2.0, "beats": 4, "energy": 0.8}, ...]
    高能量(>0.6) → 加速, 低能量(<0.3) → 减速, 中间 → 基础速度

    返回: output_path
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    if not beat_segments:
        logger.warning("无节拍段落, 回落匀速")
        return _apply_constant(input_path, output_path, base_speed, _get_duration(input_path), keep_audio)

    # 按能量生成每段速度
    temp_dir = tempfile.mkdtemp(prefix="ave_spd_")
    seg_files = []
    total_duration = _get_duration(input_path)

    for idx, seg in enumerate(beat_segments):
        start = seg["start"]
        end = seg["end"]
        dur = end - start
        if dur < 0.3:
            continue

        # 根据能量决定速度 (线性插值)
        energy = seg.get("energy", 0.5)
        if energy > 0.6:
            spd = base_speed + (high_speed - base_speed) * min((energy - 0.6) / 0.4, 1.0)
        elif energy < 0.3:
            spd = low_speed + (base_speed - low_speed) * (energy / 0.3)
        else:
            spd = base_speed

        spd = max(ATEMPO_MIN, min(ATEMPO_MAX, spd))
        seg_out = os.path.join(temp_dir, f"seg_{idx:03d}.mp4")
        _apply_constant(input_path, seg_out, spd, dur, keep_audio, ss=start, t=dur)
        seg_files.append(seg_out)

    if not seg_files:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return _apply_constant(input_path, output_path, base_speed, total_duration, keep_audio)

    # 拼接
    _concat_segments(seg_files, output_path, keep_audio)
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

    logger.info(f"✅ 能量变速完成: {output_path} ({len(seg_files)} 段)")
    return output_path


def make_energy_curve(
    beat_info: dict,
    base_speed: float = 1.0,
    high_speed: float = 1.5,
    low_speed: float = 0.7,
) -> list[tuple[float, float, float]]:
    """
    从节拍检测结果生成能量驱动速度曲线

    返回: [(start_sec, end_sec, speed), ...]
    """
    segments = beat_info.get("segments", [])
    if not segments:
        return [(0, beat_info.get("total_duration", 30), base_speed)]

    # 计算每段的归一化能量 (基于拍点密度)
    max_beats = max(s.get("beats", 0) for s in segments) or 1
    curves = []
    for s in segments:
        dur = s["end"] - s["start"]
        if dur <= 0:
            continue
        # 拍点密度 → 能量
        density = s.get("beats", 0) / max(max_beats, 1)
        energy = max(0.0, min(1.0, density))

        if energy > 0.6:
            spd = base_speed + (high_speed - base_speed) * min((energy - 0.6) / 0.4, 1.0)
        elif energy < 0.3:
            spd = low_speed + (base_speed - low_speed) * (energy / 0.3)
        else:
            spd = base_speed
        spd = max(ATEMPO_MIN, min(ATEMPO_MAX, spd))
        curves.append((s["start"], s["end"], spd))

    return curves


# ── 内部实现 ──────────────────────────────────────────────

def _apply_constant(
    input_path: str,
    output_path: str,
    speed: float,
    duration: float | None = None,
    keep_audio: bool = True,
    ss: float = 0.0,
    t: float | None = None,
) -> str:
    """匀速变速"""
    speed = max(ATEMPO_MIN, min(ATEMPO_MAX, speed))
    vf = f"setpts={1/speed}*PTS"

    cmd = ["ffmpeg", "-y"]

    # 如果指定了裁剪区间
    if ss > 0:
        cmd += ["-ss", str(ss)]
    cmd += ["-i", input_path]
    if t is not None:
        cmd += ["-t", str(t)]

    if keep_audio:
        # atempo 不支持超出 [0.5, 2.0], 级联处理
        af = _build_atempo_filter(speed)
        cmd += ["-filter_complex", f"{vf}[v];{af}[a]"]
        cmd += ["-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-filter_complex", f"{vf}[v]", "-map", "[v]", "-an"]

    cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", output_path]

    try:
        subprocess.run(cmd, capture_output=True, timeout=300, check=True)
        logger.debug(f"  匀速 {speed:.2f}x → {output_path}")
    except subprocess.CalledProcessError as e:
        logger.warning(f"  变速失败: {e.stderr[:200]}")
        # 回落: 不变速
        subprocess.run(["ffmpeg", "-y", "-i", input_path,
                        "-c", "copy", output_path], capture_output=True, timeout=60, check=True)

    return output_path


def _apply_curve(
    input_path: str,
    output_path: str,
    curve: list[float],
    num_segments: int,
    total_duration: float,
    keep_audio: bool,
) -> str:
    """缓变速度曲线: 将输入切成 N 段, 每段按曲线插值变速, 再拼接"""
    # 生成每段的速度
    speeds = _interpolate_curve(curve, num_segments)
    seg_duration = total_duration / num_segments

    temp_dir = tempfile.mkdtemp(prefix="ave_curve_")
    seg_files = []

    for idx, spd in enumerate(speeds):
        seg_start = idx * seg_duration
        seg_out = os.path.join(temp_dir, f"seg_{idx:03d}.mp4")
        _apply_constant(input_path, seg_out, spd, seg_duration,
                        keep_audio, ss=seg_start, t=seg_duration)
        seg_files.append(seg_out)

    # 拼接
    _concat_segments(seg_files, output_path, keep_audio)
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

    logger.info(f"✅ 曲线变速完成: {output_path} ({len(speeds)} 段, "
                f"速度 {speeds[0]:.2f}→{speeds[-1]:.2f})")
    return output_path


def _interpolate_curve(curve: list[float], num_segments: int) -> list[float]:
    """在曲线控制点之间线性插值"""
    if len(curve) >= num_segments:
        return curve[:num_segments]

    # 在 curve 点之间均匀插值到 num_segments 个点
    result = []
    n_controls = len(curve) - 1
    for i in range(num_segments):
        # 映射到 [0, n_controls] 区间
        pos = i / (num_segments - 1) * n_controls if num_segments > 1 else 0
        idx_low = int(pos)
        idx_high = min(idx_low + 1, n_controls)
        frac = pos - idx_low
        # 线性插值
        val = curve[idx_low] * (1 - frac) + curve[idx_high] * frac
        result.append(max(ATEMPO_MIN, min(ATEMPO_MAX, val)))
    return result


def _build_atempo_filter(speed: float) -> str:
    """构建 atempo 滤波器链 (支持 [0.5, 2.0], 超范围级联)

    atempo 单次只能 [0.5, 2.0].
    例如 speed=3.0 → atempo=2.0, atempo=1.5
    例如 speed=0.4 → atempo=0.5, atempo=0.8
    """
    if ATEMPO_MIN <= speed <= ATEMPO_MAX:
        return f"[0:a]atempo={speed}[a]"

    # 级联: 分解为多个在范围内的 atempo
    factors = []
    remaining = speed
    if speed > ATEMPO_MAX:
        while remaining > ATEMPO_MAX:
            factors.append(ATEMPO_MAX)
            remaining /= ATEMPO_MAX
        if remaining >= ATEMPO_MIN:
            factors.append(remaining)
    elif speed < ATEMPO_MIN:
        while remaining < ATEMPO_MIN:
            factors.append(ATEMPO_MIN)
            remaining /= ATEMPO_MIN
        if remaining <= ATEMPO_MAX:
            factors.append(remaining)

    if not factors:
        factors = [speed]

    # 构建级联链: [0:a]atempo=f0[a0];[a0]atempo=f1[a1];...
    chain = []
    prev = "0:a"
    for i, f in enumerate(factors):
        label = f"a{i}"
        chain.append(f"[{prev}]atempo={f:.4f}[{label}]")
        prev = label
    return ";".join(chain)


def _concat_segments(seg_files: list[str], output_path: str, keep_audio: bool):
    """拼接变速后的视频段"""
    if len(seg_files) == 1:
        subprocess.run(["ffmpeg", "-y", "-i", seg_files[0],
                        "-c", "copy", output_path], capture_output=True, timeout=60, check=True)
        return

    # 用 concat demuxer
    concat_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w").name
    with open(concat_file, "w") as f:
        for sf in seg_files:
            f.write(f"file '{os.path.abspath(sf)}'\n")

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file]
    if keep_audio:
        cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p"]
    else:
        cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "23", "-an"]
    cmd += [output_path]

    try:
        subprocess.run(cmd, capture_output=True, timeout=300, check=True)
    except subprocess.CalledProcessError as e:
        logger.warning(f"  拼接失败, 回落 concat: {e.stderr[:200]}")
        # 回落: filter concat
        concat_filter = "".join(f"[{i}:v]" for i in range(len(seg_files)))
        cmd2 = ["ffmpeg", "-y"]
        for sf in seg_files:
            cmd2 += ["-i", sf]
        cmd2 += ["-filter_complex",
                 f"{concat_filter}concat=n={len(seg_files)}:v=1{'a=1' if keep_audio else '':1}[v]"
                 + (f";{concat_filter.replace(':v',':a')}concat=n={len(seg_files)}:v=0:a=1[a]"
                    if keep_audio else ""),
                 "-map", "[v]"]
        if keep_audio:
            cmd2 += ["-map", "[a]"]
        cmd2 += ["-c:v", "libx264", "-preset", "fast", "-crf", "23",
                 "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", output_path]
        subprocess.run(cmd2, capture_output=True, timeout=300, check=True)

    os.unlink(concat_file)


def _get_duration(path: str) -> float:
    """获取媒体文件时长"""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
                           capture_output=True, text=True, timeout=10)
        return float(r.stdout.strip())
    except Exception:
        return 30.0

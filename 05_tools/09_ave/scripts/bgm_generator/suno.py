"""

AVE 07_bgm_generator — 背景音乐生成模块 v3.0

版本: v3.0 | 更新: 2026-05-06

三阶路由策略:
  Tier 1: 本地 BGM 音乐库 (真实音乐，最高质量)
  Tier 2: mlx-audiocraft AI 生成 (本地 MLX，按需定制)
  Tier 3: FFmpeg 和弦垫音 (离线保障)

Tier 1 操作流程:
  1. 从 library.json 读取 mood→曲目映射
  2. 如果有匹配曲目 → 选择一首，用 FFmpeg 循环/截取到目标时长
  3. 应用淡入淡出过渡
  4. 混音时音量设为背景级 (0.15-0.25)

用法:
  generate_bgm(mood="funny", duration=60, output="/tmp/bgm.wav")
  generate_bgm(mood="happy", duration=30, output="/tmp/bgm.wav")
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import os
import subprocess
import tempfile
from pathlib import Path

from lib.logger import get_logger

logger = get_logger("bgm")

# ── 路径 ──
LIBRARY_DIR = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "ave" / "cache" / "bgm_library"
LIBRARY_CONFIG = LIBRARY_DIR / "library.json"
CACHE_DIR = Path(os.environ.get("AVE_CACHE_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local/tools/ave/cache/bgm")))
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def generate_bgm(
    mood: str = "normal",
    duration: float = 30.0,
    output: str = "bgm.wav",
    pixabay_key: str = "",
    style: str = "",
    use_mlx: bool = False,
) -> str:
    """
    三阶背景音乐生成 v3.0

    参数:
      mood: 情绪类型
      duration: 目标时长(秒)
      output: 输出路径
      pixabay_key: (保留，暂未用)
      style: 风格别名
      use_mlx: 是否尝试 mlx-audiocraft (需提前安装)

    返回:
      生成的 BGM 文件路径
    """
    if style and not mood:
        mood = _style_to_mood(style)

    effective_mood = mood or "normal"
    logger.info(f"BGM v3: mood={effective_mood}, duration={duration}s, output={output}")

    # ── Tier 1: 音乐库 ──
    result = _try_library(effective_mood, duration, output)
    if result:
        logger.info(f"✅ Tier 1 (音乐库) → {output}")
        return result

    # ── Tier 2: mlx-audiocraft (按需) ──
    if use_mlx:
        result = _try_mlx_audiocraft(effective_mood, duration, output)
        if result:
            logger.info(f"✅ Tier 2 (mlx-audiocraft) → {output}")
            return result
        logger.warning("mlx-audiocraft 回落 → Tier 3")

    # ── Tier 3: FFmpeg 和弦垫音 ──
    result = _chord_pad(effective_mood, duration, output)
    logger.info(f"✅ Tier 3 (和弦垫音) → {output}")
    return result


def _try_library(mood: str, duration: float, output: str) -> str | None:
    """Tier 1: 从本地音乐库载入 BGM 并匹配时长"""
    if not LIBRARY_CONFIG.exists():
        logger.info("  library.json 不存在，跳过 Tier 1")
        return None

    with open(LIBRARY_CONFIG, encoding="utf-8") as f:
        lib = json.load(f)

    tracks = lib.get("库", {}).get(mood, {}).get("曲目", [])
    valid = [t for t in tracks if t.get("文件名")]
    if not valid:
        logger.info(f"  [{mood}] 库中无曲目")
        return None

    # 选择曲目: 优先选最接近目标时长的，没有完美匹配就选最短的
    chosen = min(valid, key=lambda t: abs((t.get("时长") or 30) - duration))
    track_file = LIBRARY_DIR / mood / chosen["文件名"]

    if not track_file.exists():
        logger.warning(f"  曲目文件不存在: {track_file}")
        return None

    track_duration = chosen.get("时长", 30)
    title = chosen.get("标题", chosen["文件名"])
    logger.info(f"  [{mood}] 选用: {title} ({track_duration:.1f}s) → 适配 {duration:.0f}s")

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    # FFmpeg 循环/截取
    if track_duration >= duration:
        # 截取前段
        cmd = [
            "ffmpeg", "-y",
            "-i", str(track_file),
            "-t", str(duration),
            "-af", "afade=t=in:d=1,afade=t=out:st={}:d=2".format(max(0, duration - 2)),
            "-acodec", "pcm_s16le",
            output,
        ]
    else:
        # 循环补齐
        loops = int(duration / track_duration) + 1
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", str(loops),
            "-i", str(track_file),
            "-t", str(duration),
            "-af", "afade=t=in:d=1,afade=t=out:st={}:d=2".format(max(0, duration - 2)),
            "-acodec", "pcm_s16le",
            output,
        ]

    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=30)
        return output
    except subprocess.CalledProcessError as e:
        logger.warning(f"  FFmpeg 处理失败: {e.stderr[:200]}")
        return None


def _try_mlx_audiocraft(mood: str, duration: float, output: str) -> str | None:
    """Tier 2: 使用 mlx-audiocraft 生成音乐 (需 pip install mlx-audiocraft)

    注意事项:
      - 国内用户需设置 HF_ENDPOINT=https://hf-mirror.com 下载模型
      - 首次运行会下载 ~300MB 模型 (musicgen-small)
      - 模型缓存后二次加载约 15s
      - M1 上 10s 音乐生成约 46s
    """
    try:
        import mlx_audiocraft
    except ImportError:
        logger.info("  mlx-audiocraft 未安装，跳过 Tier 2")
        return None

    # mood→prompt 映射 (与 BGM_LIBRARY.md 同步)
    prompts = {
        "calm": "soft ambient piano, gentle pad, nature sounds, 60 BPM, no percussion, no vocals",
        "soothing": "warm ambient drone, slow strings, peaceful atmosphere, 50 BPM, no vocals",
        "happy": "bright ukulele, cheerful melody, acoustic guitar, 90 BPM, no vocals",
        "excited": "upbeat electronic, driving beat, synth pads, 120 BPM, no vocals",
        "sad": "melancholic piano, slow strings, emotional, 55 BPM, no vocals",
        "mystery": "dark ambient, deep synth pad, suspenseful, 60 BPM, no vocals",
        "angry": "intense orchestral, heavy drums, dramatic, 110 BPM, no vocals",
        "professional": "corporate soft jazz, clean piano, polished, 75 BPM, no vocals",
        "funny": "playful xylophone, quirky light music, cartoon style, 100 BPM, no vocals",
        "inspiring": "uplifting cinematic, building strings, triumphant, 85 BPM, no vocals",
        "normal": "soft background music, gentle, ambient, 70 BPM, no vocals",
        # ── BGM_LIBRARY.md 扩展 ──
        "epic": "epic orchestral, brass and strings, powerful drums, triumphant, building tension, 120 BPM, no vocals",
        "tech": "electronic futuristic, synth pads, pulsing beat, modern, innovative, 120 BPM, no vocals",
        "warm": "warm acoustic guitar, soft piano, gentle, cozy atmosphere, 80 BPM, no vocals",
        "cinematic": "cinematic ambient, orchestral swells, emotional strings, majestic, 80 BPM, no vocals",
        "documentary": "documentary style, soft piano, ambient strings, professional, serious, 90 BPM, no vocals",
    }
    prompt = prompts.get(mood, prompts["normal"])

    logger.info(f"  mlx-audiocraft: {prompt}")
    try:
        from mlx_audiocraft import MusicGen
        import os as _os

        # 设置国内镜像 (如果没设且连不上 huggingface)
        if "HF_ENDPOINT" not in _os.environ:
            _os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

        # 加载模型 (会缓存，第二次更快)
        gen_duration = min(duration, 15)  # 音乐生成最长 15s
        model = MusicGen.get_pretrained("facebook/musicgen-small")

        # 生成
        import mlx.core as mx
        wav = model.generate(
            descriptions=[prompt],
            progress=False,
        )
        # wav 是 mlx.core.array, shape=(1, samples), float32, 32000Hz
        audio = wav[0]  # shape: (samples,)
        sample_rate = model.sample_rate  # 32000

        # 转为 numpy
        import numpy as np
        audio_np = np.array(audio, dtype=np.float32)

        # 保存为 raw float -> FFmpeg 转 WAV (避免 soundfile/scipy 依赖问题)
        raw_path = str(CACHE_DIR / f"_mlx_raw_{mood}.f32")
        audio_np.tofile(raw_path)

        # 用 FFmpeg 转 44.1kHz WAV 并调整时长
        if duration <= gen_duration:
            # 截取
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "f32le", "-ar", str(sample_rate), "-ac", "1",
                "-i", raw_path,
                "-t", str(duration),
                "-ar", "44100",
                "-af", "afade=t=in:d=1,afade=t=out:st={}:d=2".format(max(0, duration - 2)),
                "-acodec", "pcm_s16le", output,
            ], capture_output=True, check=True, timeout=30)
        else:
            # 循环
            loops = int(duration / gen_duration) + 1
            subprocess.run([
                "ffmpeg", "-y",
                "-stream_loop", str(loops),
                "-f", "f32le", "-ar", str(sample_rate), "-ac", "1",
                "-i", raw_path,
                "-t", str(duration),
                "-ar", "44100",
                "-af", "afade=t=in:d=1,afade=t=out:st={}:d=2".format(max(0, duration - 2)),
                "-acodec", "pcm_s16le", output,
            ], capture_output=True, check=True, timeout=30)

        # 清理
        try: _os.remove(raw_path)
        except: pass

        return output
    except Exception as e:
        logger.warning(f"  mlx-audiocraft 失败: {e}")
        return None


def _chord_pad(mood: str, duration: float, output: str) -> str:
    """Tier 3: FFmpeg 和弦垫音 (v2 保留)"""
    from .chord_pad import generate_chord_pad
    return generate_chord_pad(mood, duration, output)


def _style_to_mood(style: str) -> str:
    s = style.lower()
    if "upbeat" in s or "playful" in s: return "happy"
    if "cinematic" in s or "dramatic" in s: return "mystery"
    if "jazz" in s or "corporate" in s: return "professional"
    if "nature" in s or "ambient" in s: return "calm"
    if "funny" in s or "cartoon" in s: return "funny"
    if "inspiring" in s or "motivational" in s: return "inspiring"
    return "normal"


def get_available_moods() -> list[str]:
    from .chord_pad import CHORD_PRESETS
    return list(CHORD_PRESETS.keys())

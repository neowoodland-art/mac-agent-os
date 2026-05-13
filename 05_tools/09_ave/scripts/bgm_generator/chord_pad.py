"""

AVE 07_bgm_generator — Tier 3 FFmpeg 和弦垫音

FFmpeg 和弦氛围音生成，作为离线保障 (v2 移植)

用法:
  generate_chord_pad("funny", 60, "/tmp/bgm.wav")
"""
import os
import subprocess
import tempfile
from pathlib import Path

from lib.logger import get_logger

logger = get_logger("bgm_chord")

CACHE_DIR = Path(os.environ.get("AVE_CACHE_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local/tools/ave/cache/bgm")))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── 和弦进行预设 ──
CHORD_PRESETS = {
    "calm": {
        "chords": [[220, 277, 330], [196, 247, 294], [261, 329, 392], [220, 277, 330]],
        "bpm": 60, "lowpass": 800, "reverb_decay": 0.6, "vol_factor": 0.08,
    },
    "soothing": {
        "chords": [[196, 233, 294], [220, 261, 330], [175, 220, 277], [196, 233, 294]],
        "bpm": 55, "lowpass": 700, "reverb_decay": 0.7, "vol_factor": 0.07,
    },
    "happy": {
        "chords": [[262, 330, 392], [330, 415, 523], [392, 494, 587], [440, 554, 659]],
        "bpm": 90, "lowpass": 1200, "reverb_decay": 0.3, "vol_factor": 0.06,
    },
    "excited": {
        "chords": [[294, 370, 440], [349, 440, 554], [392, 493, 587], [440, 554, 659]],
        "bpm": 110, "lowpass": 1500, "reverb_decay": 0.2, "vol_factor": 0.05,
    },
    "sad": {
        "chords": [[165, 196, 247], [147, 175, 220], [131, 165, 196], [147, 175, 220]],
        "bpm": 50, "lowpass": 600, "reverb_decay": 0.8, "vol_factor": 0.09,
    },
    "mystery": {
        "chords": [[165, 208, 262], [147, 185, 233], [131, 175, 220], [139, 185, 233]],
        "bpm": 50, "lowpass": 500, "reverb_decay": 0.9, "vol_factor": 0.10,
    },
    "angry": {
        "chords": [[131, 165, 196], [165, 208, 262], [147, 185, 233], [175, 220, 277]],
        "bpm": 130, "lowpass": 1000, "reverb_decay": 0.4, "vol_factor": 0.06,
    },
    "professional": {
        "chords": [[262, 330, 392], [392, 494, 587], [262, 330, 392], [330, 415, 523]],
        "bpm": 70, "lowpass": 1000, "reverb_decay": 0.4, "vol_factor": 0.06,
    },
    "normal": {
        "chords": [[220, 277, 330], [261, 329, 392], [196, 247, 294], [261, 329, 392]],
        "bpm": 70, "lowpass": 900, "reverb_decay": 0.5, "vol_factor": 0.07,
    },
    "funny": {
        "chords": [[523, 659, 784], [659, 784, 988], [784, 988, 1175], [523, 659, 784]],
        "bpm": 100, "lowpass": 1400, "reverb_decay": 0.25, "vol_factor": 0.04,
    },
    "inspiring": {
        "chords": [[262, 330, 392, 523], [294, 370, 440, 587], [330, 415, 523, 659], [392, 494, 587, 784]],
        "bpm": 80, "lowpass": 1200, "reverb_decay": 0.5, "vol_factor": 0.05,
    },
    # ── BGM_LIBRARY 扩展 ──
    "epic": {
        "chords": [[262, 330, 392], [330, 415, 523], [392, 494, 587], [440, 554, 659]],
        "bpm": 120, "lowpass": 1500, "reverb_decay": 0.3, "vol_factor": 0.06,
    },
    "tech": {
        "chords": [[294, 370, 440], [349, 440, 554], [392, 493, 587], [440, 554, 659]],
        "bpm": 120, "lowpass": 1800, "reverb_decay": 0.2, "vol_factor": 0.05,
    },
    "warm": {
        "chords": [[220, 277, 330], [196, 247, 294], [261, 329, 392], [220, 277, 330]],
        "bpm": 80, "lowpass": 700, "reverb_decay": 0.6, "vol_factor": 0.07,
    },
    "cinematic": {
        "chords": [[175, 220, 277], [196, 247, 294], [220, 277, 330], [261, 329, 392]],
        "bpm": 80, "lowpass": 900, "reverb_decay": 0.7, "vol_factor": 0.08,
    },
}


def generate_chord_pad(mood: str, duration: float, output: str) -> str:
    """生成和弦垫音 (Tier 3)"""
    preset = CHORD_PRESETS.get(mood, CHORD_PRESETS["normal"])
    chord_freqs_list = preset["chords"]
    bpm = preset["bpm"]
    lowpass_freq = preset["lowpass"]
    reverb_decay = preset["reverb_decay"]
    vol_factor = preset["vol_factor"]

    num_chords = len(chord_freqs_list)
    chord_duration = duration / num_chords
    transition = min(2.0, chord_duration * 0.3)

    logger.info(f"  Tier 3: {num_chords} 和弦 × {chord_duration:.1f}s, "
                f"低通={lowpass_freq}Hz, 混响={reverb_decay}")

    # 生成每个和弦
    chord_wavs = []
    for idx, freqs in enumerate(chord_freqs_list):
        part_file = str(CACHE_DIR / f"_chord_{mood}_{idx}.wav")
        if os.path.exists(part_file):
            try: os.remove(part_file)
            except: pass

        expressions = []
        for freq in freqs:
            for detune in [0.995, 1.000, 1.005]:
                expressions.append(f"sin(2*PI*{freq * detune}*t)")
        expr = f"({'+'.join(expressions)})/{len(expressions)}"

        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"aevalsrc={expr}:s=44100:c=mono",
            "-t", str(chord_duration),
            "-af", f"afade=t=in:ss=0:d={transition},"
                   f"afade=t=out:st={chord_duration - transition}:d={transition},"
                   f"volume={vol_factor}",
            "-acodec", "pcm_s16le", part_file,
        ], capture_output=True, timeout=120, check=True)
        chord_wavs.append(part_file)

    # 拼接
    concat_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w").name
    with open(concat_file, "w", encoding="utf-8") as f:
        for w in chord_wavs:
            f.write(f"file '{w}'\n")

    # 全局效果
    if reverb_decay < 0.5:
        delays = "50|80|110"
        gains = f"{reverb_decay*0.6}|{reverb_decay*0.4}|{reverb_decay*0.2}"
    else:
        delays = "60|100|150|200"
        gains = f"{reverb_decay*0.6}|{reverb_decay*0.4}|{reverb_decay*0.2}|{reverb_decay*0.1}"

    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
            "-af", f"lowpass=f={lowpass_freq},aecho=0.8:0.7:{delays}:{gains}",
            "-acodec", "pcm_s16le", output,
        ], capture_output=True, timeout=120, check=True)
    except subprocess.CalledProcessError:
        logger.warning("全局效果失败，回落无效果拼接")
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
            "-acodec", "pcm_s16le", output,
        ], capture_output=True, check=True)

    # 清理
    for w in chord_wavs:
        try: os.remove(w)
        except: pass
    try: os.remove(concat_file)
    except: pass

    return output

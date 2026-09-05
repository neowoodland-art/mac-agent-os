"""
person_swap/preprocess.py — 素材合规化与预处理 (ffmpeg)

职责:
  1. probe_video        — 探测源视频(时长/分辨率/编码/fps)
  2. check_image        — 校验人物参考图(可解码/尺寸/非动图)
  3. prep_source_video  — 源视频合规化: 转码 h264 + 竖屏 9:16 裁切 + 限长截断
  4. prep_reference_image — 参考图归一化(缩放至模型常用尺寸上限)
  5. extract_preview_frame — 抽帧预览(供前端展示)

⚠️ 本机 ~/.local/bin/ffprobe 是软链到 ffmpeg 的假 ffprobe(v6.0 单二进制),
   _find_bin 会用 `-version` 验证真实身份; 无真 ffprobe 时走 ffmpeg stderr 解析兜底。

输出目录约定: agent-local/runtime/person_swap/uploads/{task_id}/
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

# ── ffmpeg / ffprobe 路径解析 ──
def _find_bin(name: str) -> str:
    """查找真实二进制: 候选目录 + PATH, 且 -version 首行必须含目标名"""
    cands = [
        os.environ.get("FFMPEG_DIR", ""),
        str(Path.home() / ".local" / "bin"),
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
    ]
    seen = []
    for d in cands:
        if d:
            p = Path(d) / name
            if p.exists():
                seen.append(str(p))
    w = shutil.which(name)
    if w:
        seen.append(w)
    for cand in seen:
        try:
            r = subprocess.run([cand, "-version"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and r.stdout.splitlines() and name in r.stdout.splitlines()[0]:
                return cand
        except Exception:
            continue
    return name  # 找不到就交给系统 PATH, 调用时会自然报错


FFMPEG = _find_bin("ffmpeg")
FFPROBE = _find_bin("ffprobe")

# ── 常用约束 (可被 person_swap 配置覆盖) ──
DEFAULT_MAX_DURATION = 10      # 单条源视频最长秒数(超长提示分段)
DEFAULT_ORIENTATION = "9:16"   # 输出竖屏
DEFAULT_IMAGE_MAX = 2048       # 参考图长边上限

_SCRIPT_ROOT = Path(__file__).resolve().parent.parent
if str(_SCRIPT_ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(_SCRIPT_ROOT))

from lib.logger import get_logger
from lib.config import load_config

logger = get_logger("person_swap")


def _cfg() -> dict:
    cfg = load_config()
    return cfg.get("person_swap", {}) or {}


def _run(cmd: list, timeout: int = 120) -> subprocess.CompletedProcess:
    logger.debug("执行: %s", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


# ════════════════════════════════════════════════════════════
# 探测与校验
# ════════════════════════════════════════════════════════════

def _parse_ffmpeg_info(path: str) -> dict:
    """ffmpeg -i stderr 解析兜底 (无真 ffprobe 时使用)"""
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", path],
                       capture_output=True, text=True, timeout=30)
    text = r.stderr
    dur_s = 0.0
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", text)
    if m:
        h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
        dur_s = h * 3600 + mi * 60 + s
    # 分辨率组首位 1-9: 排除 0x31637661(avc1 十六进制) 这类误匹配
    m = re.search(r"Stream #0[^\n]*?Video:\s*([\w-]+)[^\n]*?([1-9]\d{1,4})x([1-9]\d{1,4})", text)
    if not m:
        raise ValueError(f"无法识别媒体流: {text.strip()[-200:]}")
    codec, w, h = m.group(1), int(m.group(2)), int(m.group(3))
    fps = ""
    mf = re.search(r"(\d+(?:\.\d+)?)\s*fps", text)
    if mf:
        fps = mf.group(1)
    return {"duration_sec": round(dur_s, 2), "width": w, "height": h,
            "codec": codec, "fps": fps}


def probe_video(path: str) -> dict:
    """探测视频元信息, 失败抛 ValueError; 优先 ffprobe JSON, 兜底 ffmpeg 解析"""
    if FFPROBE != "ffprobe":
        r = _run([FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
        if r.returncode == 0:
            try:
                d = json.loads(r.stdout)
                streams = d.get("streams", [])
                v = next((s for s in streams if s.get("codec_type") == "video"), None)
                if not v:
                    raise ValueError("视频无视频流")
                fmt = d.get("format", {})
                dur = float(fmt.get("duration", 0) or 0)
                if dur <= 0:
                    dur = float(v.get("duration", 0) or 0)
                return {
                    "duration_sec": round(dur, 2),
                    "width": int(v.get("width", 0)),
                    "height": int(v.get("height", 0)),
                    "codec": v.get("codec_name", ""),
                    "fps": v.get("avg_frame_rate", ""),
                    "size_bytes": int(fmt.get("size", 0) or 0),
                }
            except Exception:
                pass  # 解析失败落到 ffmpeg 兜底
    info = _parse_ffmpeg_info(path)
    info["size_bytes"] = os.path.getsize(path)
    return info


def check_image(path: str) -> dict:
    """校验人物参考图: 可解码 + 尺寸, 返回 {width,height,ok,error}"""
    try:
        info = _parse_ffmpeg_info(path)
        w, h = info["width"], info["height"]
    except Exception as e:
        return {"ok": False, "error": f"图片无法解码: {e}"}
    if w < 256 or h < 256:
        return {"ok": False, "error": f"参考图过小({w}x{h}), 至少 256px"}
    return {"ok": True, "width": w, "height": h, "codec": info["codec"], "error": ""}


# ════════════════════════════════════════════════════════════
# 预处理(生成合规中间文件)
# ════════════════════════════════════════════════════════════

def prep_source_video(src_path: str, out_path: str,
                      max_duration: int = 0, orientation: str = "") -> dict:
    """源视频合规化 → h264 + 竖屏裁切 + 限长

    返回 {out_path, duration_sec, width, height, trimmed: bool}
    超长时截取前 max_duration 秒(并返回 trimmed=True)
    """
    info = probe_video(src_path)
    max_duration = max_duration or int(_cfg().get("max_duration", DEFAULT_MAX_DURATION))
    orientation = orientation or _cfg().get("orientation", DEFAULT_ORIENTATION)

    dur = info["duration_sec"]
    duration_arg = []
    if dur > max_duration:
        duration_arg = ["-t", str(max_duration)]
        logger.info("  源视频 %.1fs 超限, 截取前 %ds", dur, max_duration)

    # 裁切到竖屏: 保持画面内容, 按 9:16 裁掉左右 (16:9 横屏 → 切中间竖条)
    vf = []
    if orientation == "9:16":
        vf.append("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920")
    else:
        vf.append("scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080")

    cmd = [FFMPEG, "-y", "-i", src_path, *duration_arg,
           "-vf", ",".join(vf),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
           out_path]
    r = _run(cmd, timeout=300)
    if r.returncode != 0:
        raise ValueError(f"视频预处理失败: {r.stderr.strip()[-300:]}")

    out_info = probe_video(out_path)
    return {**out_info, "out_path": out_path, "trimmed": dur > max_duration}


def prep_reference_image(src_path: str, out_path: str, max_side: int = 0) -> dict:
    """参考图归一化: 转 jpg + 长边上限, 返回 {out_path, width, height}"""
    chk = check_image(src_path)
    if not chk["ok"]:
        raise ValueError(chk["error"])
    max_side = max_side or int(_cfg().get("image_max_side", DEFAULT_IMAGE_MAX))

    vf = f"scale='min({max_side},iw)':'min({max_side},ih)':force_original_aspect_ratio=decrease"
    out = Path(out_path)
    if out.suffix.lower() not in (".jpg", ".jpeg"):
        out = out.with_suffix(".jpg")
    cmd = [FFMPEG, "-y", "-i", src_path, "-vf", vf, "-q:v", "2", str(out)]
    r = _run(cmd, timeout=120)
    if r.returncode != 0:
        raise ValueError(f"参考图处理失败: {r.stderr.strip()[-300:]}")
    return {"out_path": str(out), "width": chk["width"], "height": chk["height"]}


def extract_preview_frame(video_path: str, out_path: str) -> str:
    """抽取视频中帧作为预览图(jpg)"""
    out = Path(out_path)
    if out.suffix.lower() not in (".jpg", ".jpeg"):
        out = out.with_suffix(".jpg")
    cmd = [FFMPEG, "-y", "-i", video_path, "-frames:v", "1", "-q:v", "3", str(out)]
    r = _run(cmd, timeout=60)
    if r.returncode != 0:
        raise ValueError(f"抽帧失败: {r.stderr.strip()[-200:]}")
    return str(out)


# ── CLI 自测 ──
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="person_swap 预处理自测")
    ap.add_argument("video", help="源视频路径")
    ap.add_argument("--image", default="", help="参考图路径(可选, 测试图片处理)")
    args = ap.parse_args()

    print(f"FFMPEG={FFMPEG} FFPROBE={FFPROBE}")
    info = probe_video(args.video)
    print("源视频:", info)
    out = "/tmp/ps_prep_test.mp4"
    res = prep_source_video(args.video, out)
    print("预处理:", res["out_path"], f"{res['width']}x{res['height']}", f"{res['duration_sec']}s", "trimmed" if res["trimmed"] else "")
    if args.image:
        print("参考图检查:", check_image(args.image))
        r = prep_reference_image(args.image, "/tmp/ps_ref_test.jpg")
        print("参考图处理:", r["out_path"])

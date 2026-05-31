#!/usr/bin/env python3
"""
AVE lipsync — Kling LipSync 集成

功能:
  Audio→Video: 输入视频 + 语音音频 → 输出口型对齐的视频
  Text→Video: 输入视频 + 文本 → 输出口型对齐的视频 (TTS自动)

API:
  fal.ai endpoint （Kling LipSync 托管在 fal.ai）
  成本: $0.014/5s ≈ ¥0.10/秒 ≈ ¥0.50/5秒镜头

用法:
  python lipsync.py --video clip.mp4 --audio voice.wav --output synced.mp4
  python lipsync.py --video clip.mp4 --text "你好世界" --output synced.mp4

集成:
  作为口播策略后处理钩子, 在 video_factory.py 中调用
"""
import sys
import os
import json
import hashlib
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.config import load_config
from lib.cost_tracker import get_tracker
from lib.logger import get_logger

logger = get_logger("lipsync")

# ── 缓存 ──
CACHE_DIR = Path(os.environ.get("AVE_CACHE_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local/tools/ave/cache/lipsync")))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── fal.ai 端点 ──
# Kling LipSync 通过 fal.ai 提供
FAL_BASE = "https://fal.run"

ENDPOINTS = {
    "audio_to_video": f"{FAL_BASE}/fal-ai/kling-video/lipsync/audio-to-video",
    "text_to_video":  f"{FAL_BASE}/fal-ai/kling-video/lipsync/text-to-video",
}

# ═══════════════════════════════════════════════════════════
# 核心 API
# ═══════════════════════════════════════════════════════════

def lipsync_audio_to_video(
    video_path: str,
    audio_path: str,
    output_path: str = "",
    force: bool = False,
    api_key: str = "",
) -> str:
    """
    Audio→Video 唇形同步

    参数:
      video_path: 输入视频路径 (2-10s, 720p/1080p, ≤100MB)
      audio_path: 输入音频路径 (.mp3/.wav/.m4a, ≤5MB)
      output_path: 输出路径
      force: 强制重新生成
      api_key: fal.ai API Key

    返回:
      本地输出视频路径
    """
    if not output_path:
        joint = hashlib.md5(
            (video_path + audio_path).encode()
        ).hexdigest()[:16]
        output_path = str(CACHE_DIR / f"lipsync_{joint}.mp4")

    # 缓存
    if os.path.exists(output_path) and not force:
        logger.info(f"缓存命中: {output_path}")
        return output_path

    cfg = load_config()
    api_key = api_key or cfg.get("fal", {}).get("api_key", "")
    if not api_key:
        raise ValueError("缺少 fal.ai API Key (config fal.api_key)")

    logger.info(f"LipSync Audio→Video:")
    logger.info(f"  video: {video_path}")
    logger.info(f"  audio: {audio_path}")

    # 上传文件或传URL (fal.ai 支持直接传base64或文件URL)
    # 方案: 使用 fal.ai 的 upload 端点
    video_url = _upload_to_fal(video_path, api_key)
    audio_url = _upload_to_fal(audio_path, api_key)

    if not video_url or not audio_url:
        raise RuntimeError("上传文件到 fal.ai 失败")

    logger.info(f"  video_url: {video_url[:60]}...")
    logger.info(f"  audio_url: {audio_url[:60]}...")

    # 提交任务
    result = _submit_and_poll(
        endpoint=ENDPOINTS["audio_to_video"],
        payload={
            "video_url": video_url,
            "audio_url": audio_url,
        },
        api_key=api_key,
        timeout_sec=120,
    )

    # 下载结果
    video_url_res = result.get("video", {}).get("url", "") or result.get("output", "")
    if not video_url_res:
        raise RuntimeError(f"fal.ai 返回无视频URL: {json.dumps(result, ensure_ascii=False)[:200]}")

    logger.info(f"  下载结果中...")
    _download(video_url_res, output_path)

    # 费用
    tracker = get_tracker()
    try:
        dur = _get_media_duration(output_path)
    except Exception:
        dur = 5  # 默认5秒
    tracker.log("KlingLipSync", duration=dur, note=f"audio-to-video ¥0.014×{dur}s")

    sz_mb = os.path.getsize(output_path) / 1024 / 1024
    logger.info(f"  ✅ LipSync完成: {output_path} ({sz_mb:.1f}MB, {dur:.1f}s)")
    return output_path


def lipsync_text_to_video(
    video_path: str,
    text: str,
    voice_id: str = "default",
    output_path: str = "",
    force: bool = False,
    api_key: str = "",
) -> str:
    """
    Text→Video 唇形同步 (自动 TTS + 口型对齐, ≤120字)

    参数:
      video_path: 输入视频路径
      text: 口播文本 (≤120字)
      voice_id: 音色ID
      output_path: 输出路径
      force: 强制重新生成

    返回:
      本地输出视频路径
    """
    if len(text) > 120:
        logger.warning(f"文本过长 ({len(text)}字), 截断至120字")
        text = text[:120]

    if not output_path:
        joint = hashlib.md5(
            (video_path + text).encode()
        ).hexdigest()[:16]
        output_path = str(CACHE_DIR / f"lipsync_txt_{joint}.mp4")

    if os.path.exists(output_path) and not force:
        logger.info(f"缓存命中: {output_path}")
        return output_path

    cfg = load_config()
    api_key = api_key or cfg.get("fal", {}).get("api_key", "")
    if not api_key:
        raise ValueError("缺少 fal.ai API Key")

    logger.info(f"LipSync Text→Video: text={text[:40]}...")

    video_url = _upload_to_fal(video_path, api_key)
    if not video_url:
        raise RuntimeError("上传视频到 fal.ai 失败")

    result = _submit_and_poll(
        endpoint=ENDPOINTS["text_to_video"],
        payload={
            "video_url": video_url,
            "text": text,
            "voice_id": voice_id,
        },
        api_key=api_key,
        timeout_sec=180,
    )

    video_url_res = result.get("video", {}).get("url", "") or result.get("output", "")
    if not video_url_res:
        raise RuntimeError(f"fal.ai 返回无视频URL")

    _download(video_url_res, output_path)

    sz_mb = os.path.getsize(output_path) / 1024 / 1024
    logger.info(f"  ✅ LipSync Text→Video完成: {output_path} ({sz_mb:.1f}MB)")
    return output_path


# ═══════════════════════════════════════════════════════════
# 内部工具
# ═══════════════════════════════════════════════════════════

def _upload_to_fal(file_path: str, api_key: str) -> str:
    """上传文件到 fal.ai, 返回可访问的 URL"""
    import httpx
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    with open(file_path, "rb") as f:
        resp = httpx.post(
            f"{FAL_BASE}/fal-ai/upload",
            headers={
                "Authorization": f"Key {api_key}",
            },
            files={"file": f},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("url", "")


def _submit_and_poll(
    endpoint: str,
    payload: dict,
    api_key: str,
    timeout_sec: int = 120,
) -> dict:
    """提交 fal.ai 任务并轮询, 返回结果"""
    import httpx
    headers = {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json",
    }

    # 提交
    resp = httpx.post(
        endpoint.replace("/run", ""),  # 提交到非 /run 端点
        headers=headers,
        json=payload,
        timeout=30,
    )
    # fal.ai 的 submit API
    submit_url = endpoint
    resp = httpx.post(submit_url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # 检查是否直接返回结果（fal.ai 同步模式）
    if data.get("status") == "completed" or data.get("video"):
        return data

    # 获取请求ID进行轮询
    request_id = data.get("request_id", "")
    if not request_id:
        # 有的接口直接返回结果
        if data.get("video", {}).get("url"):
            return data
        raise RuntimeError(f"fal.ai 无 request_id: {json.dumps(data, ensure_ascii=False)[:200]}")

    status_url = f"{endpoint}/requests/{request_id}"
    logger.info(f"  轮询: {request_id}")

    start = time.time()
    for i in range(60):
        # 指数退避
        if i < 5:
            time.sleep(3)
        elif i < 15:
            time.sleep(5)
        else:
            time.sleep(10)

        elapsed = time.time() - start
        if elapsed > timeout_sec:
            raise TimeoutError(f"fal.ai 超时 ({timeout_sec}s)")

        try:
            q = httpx.get(status_url, headers=headers, timeout=15)
            q.raise_for_status()
            status_data = q.json()
            status = status_data.get("status", "")
            if status == "COMPLETED":
                return status_data
            elif status in ("FAILED", "ERROR"):
                raise RuntimeError(f"fal.ai 失败: {json.dumps(status_data, ensure_ascii=False)[:200]}")
            logger.debug(f"    [{i}] status={status}")
        except httpx.HTTPError as e:
            logger.debug(f"    [{i}] 查询失败: {e}")
            time.sleep(5)

    raise TimeoutError("fal.ai 轮询超时")


def _download(url: str, path: str):
    """下载文件"""
    import httpx
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with httpx.stream("GET", url, timeout=600) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_bytes(8192):
                f.write(chunk)


def _get_media_duration(path: str) -> float:
    """获取媒体时长 (秒)"""
    import subprocess
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, timeout=15,
    )
    return float(r.stdout.strip())


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def cli(args: list[str] | None = None):
    import argparse
    parser = argparse.ArgumentParser(description="Kling LipSync 唇形同步")
    sub = parser.add_subparsers(dest="mode", required=True)

    # audio → video
    p_av = sub.add_parser("audio-to-video", help="音频驱动唇形同步")
    p_av.add_argument("--video", required=True, help="输入视频")
    p_av.add_argument("--audio", required=True, help="输入音频")
    p_av.add_argument("--output", default="", help="输出路径")
    p_av.add_argument("--force", action="store_true", help="强制重新生成")

    # text → video
    p_tv = sub.add_parser("text-to-video", help="文本驱动唇形同步")
    p_tv.add_argument("--video", required=True, help="输入视频")
    p_tv.add_argument("--text", required=True, help="口播文本 (≤120字)")
    p_tv.add_argument("--voice-id", default="default", help="音色ID")
    p_tv.add_argument("--output", default="", help="输出路径")
    p_tv.add_argument("--force", action="store_true", help="强制重新生成")

    parsed = parser.parse_args(args)

    if parsed.mode == "audio-to-video":
        out = lipsync_audio_to_video(
            video_path=parsed.video,
            audio_path=parsed.audio,
            output_path=parsed.output,
            force=parsed.force,
        )
        print(f"\n✅ LipSync 完成: {out}")

    elif parsed.mode == "text-to-video":
        out = lipsync_text_to_video(
            video_path=parsed.video,
            text=parsed.text,
            voice_id=parsed.voice_id,
            output_path=parsed.output,
            force=parsed.force,
        )
        print(f"\n✅ LipSync 完成: {out}")


if __name__ == "__main__":
    cli()

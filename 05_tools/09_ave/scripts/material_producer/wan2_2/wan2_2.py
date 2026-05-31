"""

AVE 05_material_producer/wan2_2 — 阿里云 Wan2.2-S2V 数字人

功能:
  基于单张图片 + 音频 → 生成对口型数字人视频

API 文档:
  https://help.aliyun.com/zh/model-studio/wan-s2v-api
  定价: 480P ¥0.5/s, 720P ¥0.9/s (免费100s)

用法:
  from wan2_2 import generate_digital_human
  video_path = generate_digital_human(
      image_path="/path/to/avatar.jpg",
      audio_path="/tmp/voice.wav",
      text="关注我，一起聆听世界",
      api_key="sk-xxx",
  )
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional

import httpx

from lib.logger import get_logger

logger = get_logger("wan2_2")

# ── 常量 ──
CACHE_DIR = Path(os.environ.get("AVE_CACHE_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local/tools/ave/cache/wan2_2")))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

TASK_API = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image2video/video-synthesis/"
TASK_POLL_API = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
UPLOAD_API = "https://dashscope.aliyuncs.com/api/v1/uploads"

# Wan2.2 限制: 音频 ≤20s, <15MB
MAX_AUDIO_SEC = 20
MAX_AUDIO_BYTES = 15 * 1024 * 1024


# ═══════════════════════════════════════════════════════════
# 公共 API
# ═══════════════════════════════════════════════════════════

def generate_digital_human(
    image_path: str,
    audio_path: str,
    api_key: str,
    output_path: str = "digital_human.mp4",
    resolution: str = "480P",
    model: str = "wan2.2-s2v",
    force: bool = False,
    text: str = "",
) -> str:
    """
    生成数字人视频

    参数:
      image_path: 人物头像图片路径 (jpg/png)
      audio_path: 人声音频路径 (wav/mp3, ≤20s, <15MB)
      api_key: 阿里云百炼 API Key
      output_path: 输出视频路径
      resolution: 480P 或 720P
      model: 模型名
      force: 是否忽略缓存强制重新生成
      text: 文案文本 (用于缓存键, 避免不同文案用同一音频名导致误命中)

    返回:
      数字人视频文件路径
    """
    # 缓存检查 (相同图片+文案+分辨率)
    cache_key = _make_cache_key(image_path, text, resolution)
    cached = CACHE_DIR / f"{cache_key}.mp4"
    if cached.exists() and not force:
        logger.info(f"缓存命中: {cached}")
        # 复制到目标路径
        import shutil
        shutil.copy2(str(cached), output_path)
        return output_path

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"头像图片不存在: {image_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    _validate_audio(audio_path)

    # 1. 上传图片到临时存储
    logger.info("上传图片...")
    image_url = _upload_file(api_key, model, image_path)

    # 2. 上传音频到临时存储
    logger.info("上传音频...")
    audio_url = _upload_file(api_key, model, audio_path)

    # 3. 提交 Wan2.2 任务
    logger.info(f"提交 Wan2.2 任务 (resolution={resolution})...")
    task_id = _submit_task(api_key, model, image_url, audio_url, resolution)
    logger.info(f"  task_id: {task_id}")

    # 4. 轮询等待完成 (5-10分钟)
    logger.info("等待生成 (约5-10分钟)...")
    result_url = _poll_task(api_key, task_id)
    logger.info(f"  生成完成: {result_url}")

    # 5. 下载结果
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    _download_result(result_url, output_path)

    # 缓存
    import shutil
    shutil.copy2(output_path, str(cached))

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    logger.info(f"✅ 数字人视频: {output_path} ({size_mb:.1f}MB)")
    return output_path


def generate_opening(
    image_path: str,
    api_key: str,
    voice_synthesizer: callable,
    output_path: str = "opening.mp4",
    text: str = "今天我要给你讲一个有趣的故事。",
    resolution: str = "480P",
    force: bool = False,
) -> str:
    """
    生成片头数字人 (3-5s)

    - 先调用 voice_synthesizer 合成片头文案的音频
    - 再调用 Wan2.2 生成数字人视频
    - 结果缓存，重复使用
    """
    cache_key = _make_cache_key(image_path, text, resolution)
    cached = CACHE_DIR / f"opening_{cache_key}.mp4"
    if cached.exists() and not force:
        import shutil
        shutil.copy2(str(cached), output_path)
        logger.info(f"片头缓存命中: {output_path}")
        return output_path

    audio_path = f"/tmp/ave_opening_{cache_key}.wav"
    voice_synthesizer(text, audio_path)

    result = generate_digital_human(
        image_path, audio_path, api_key, output_path,
        resolution=resolution, force=force,
    )
    return result


def generate_closing(
    image_path: str,
    api_key: str,
    voice_synthesizer: callable,
    output_path: str = "closing.mp4",
    text: str = "关注我，一起聆听世界",
    resolution: str = "480P",
    force: bool = False,
) -> str:
    """
    生成片尾数字人 (3-5s, 固定文案)

    片尾文案固定，结果可永久缓存。
    - 首次: 生成音频 + 提交 Wan2.2 → 缓存
    - 后续: 直接加载缓存，0 成本 0 等待
    """
    return generate_opening(
        image_path, api_key, voice_synthesizer, output_path,
        text=text, resolution=resolution, force=force,
    )


# ═══════════════════════════════════════════════════════════
# 内部方法
# ═══════════════════════════════════════════════════════════

def _make_cache_key(*args) -> str:
    """生成缓存键"""
    raw = "|".join(str(a) for a in args)
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _validate_audio(audio_path: str):
    """验证音频符合 Wan2.2 要求"""
    # 时长检查
    import subprocess
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ], capture_output=True, text=True, timeout=15)
    lines = result.stdout.strip().split("\n")
    duration = float(lines[0]) if len(lines) > 0 else 0
    file_size = int(lines[1]) if len(lines) > 1 else 0

    if duration > MAX_AUDIO_SEC:
        raise ValueError(f"音频时长 {duration:.1f}s 超过限制 {MAX_AUDIO_SEC}s")
    if file_size > MAX_AUDIO_BYTES:
        raise ValueError(f"音频大小 {file_size/1024/1024:.1f}MB 超过限制 15MB")
    logger.debug(f"音频验证通过: {duration:.1f}s, {file_size/1024:.0f}KB")


def _upload_file(api_key: str, model: str, file_path: str) -> str:
    """上传文件到阿里云百炼临时存储，返回 oss:// URL

    流程:
      1. GET /api/v1/uploads?action=getPolicy → 获取上传凭证
      2. POST OSS → 上传文件 (multipart)
      3. 拼接 oss://upload_dir/filename
    """
    # 步骤1: 获取上传凭证
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    resp = httpx.get(
        UPLOAD_API,
        params={"action": "getPolicy", "model": model},
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()["data"]

    upload_host = data["upload_host"]
    upload_dir = data["upload_dir"]
    policy = data["policy"]
    signature = data["signature"]
    oss_key_id = data["oss_access_key_id"]
    obj_acl = data["x_oss_object_acl"]
    forbid_overwrite = data["x_oss_forbid_overwrite"]

    # 步骤2: 上传文件到 OSS
    filename = os.path.basename(file_path)
    key = f"{upload_dir}/{filename}"

    with open(file_path, "rb") as f:
        files = {
            "OSSAccessKeyId": (None, oss_key_id),
            "policy": (None, policy),
            "Signature": (None, signature),
            "key": (None, key),
            "x-oss-object-acl": (None, obj_acl),
            "x-oss-forbid-overwrite": (None, forbid_overwrite),
            "success_action_status": (None, "200"),
            "file": (filename, f, _get_mime(file_path)),
        }
        upload_resp = httpx.post(upload_host, files=files, timeout=120)
        upload_resp.raise_for_status()

    # 步骤3: 返回 oss:// URL
    oss_url = f"oss://{key}"
    logger.debug(f"  OSS URL: {oss_url}")
    return oss_url


def _get_mime(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".bmp": "image/bmp",
        ".webp": "image/webp",
        ".wav": "audio/wav", ".mp3": "audio/mpeg",
    }.get(ext, "application/octet-stream")


def _submit_task(
    api_key: str, model: str, image_url: str, audio_url: str, resolution: str
) -> str:
    """提交 Wan2.2 异步任务"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-DashScope-Async": "enable",
        "X-DashScope-OssResourceResolve": "enable",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "input": {
            "image_url": image_url,
            "audio_url": audio_url,
        },
        "parameters": {"resolution": resolution},
    }
    resp = httpx.post(TASK_API, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()["output"]["task_id"]


def _poll_task(api_key: str, task_id: str, interval: int = 15, timeout: int = 600) -> str:
    """轮询 Wan2.2 任务直到完成"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-DashScope-OssResourceResolve": "enable",
    }
    start = time.time()
    while time.time() - start < timeout:
        resp = httpx.get(
            TASK_POLL_API.format(task_id=task_id),
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data["output"]["task_status"]

        elapsed = int(time.time() - start)
        if status == "SUCCEEDED":
            video_url = data["output"]["results"]["video_url"]
            duration_sec = data.get("usage", {}).get("duration", 0)
            logger.info(f"  耗时: {elapsed}s, 视频时长: {duration_sec}s")
            return video_url
        elif status in ("FAILED", "CANCELED"):
            code = data["output"].get("code", "?")
            msg = data["output"].get("message", "?")
            raise RuntimeError(f"Wan2.2 任务失败 [{code}]: {msg}")

        logger.debug(f"  轮询 {elapsed}s... 状态: {status}")
        time.sleep(interval)

    raise TimeoutError(f"Wan2.2 任务超时 (>{timeout}s)")


def _download_result(url: str, output_path: str):
    """下载 Wan2.2 生成的视频"""
    with httpx.stream("GET", url, timeout=600) as resp:
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=8192):
                f.write(chunk)

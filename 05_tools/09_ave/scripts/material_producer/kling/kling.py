"""
AVE 05_material_producer/kling — 可灵 Kling AI 视频生成

功能:
  文生视频、图生视频，对接 Kling API（官方或阿里云百炼）

API 文档:
  https://klingai.com/document-api/apiReference/overview
  认证: JWT (HS256), AccessKey + SecretKey → Bearer Token

用法:
  from kling import text2video
  path = text2video("一只橘猫在窗台上晒太阳", api_key="xxx", secret_key="xxx")
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib, json, os, time
from pathlib import Path

import jwt
import httpx

from lib.logger import get_logger

logger = get_logger("kling")

# ── 缓存 ──
CACHE_DIR = Path(os.environ.get("AVE_CACHE_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local/tools/ave/cache/kling")))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── API 配置 ──
# 官方 Kling API (中国区)
KLING_BASE = "https://api-beijing.klingai.com"
# 也可通过阿里云百炼调用 (需开通服务)
DASHSCOPE_BASE = "https://dashscope.aliyuncs.com"

# ── 模型与成本 (最低→最高) ──
MODELS = {
    "turbo":   {"id": "kling-v2.5-turbo",  "cost_per_s": 0.04,  "desc": "最快, 最便宜"},
    "std":     {"id": "kling-v2.6-std",    "cost_per_s": 0.05,  "desc": "快速, 含音频"},
    "pro":     {"id": "kling-v2.6-pro",    "cost_per_s": 0.07,  "desc": "最佳质量, 含音频+运动控制"},
    "o1":      {"id": "kling-video-o1",    "cost_per_s": 0.08,  "desc": "统一多模态"},
}


def text2video(
    prompt: str,
    output_path: str = "",
    model: str = "turbo",
    duration: int = 5,
    aspect_ratio: str = "9:16",
    access_key: str = "",
    secret_key: str = "",
    use_dashscope: bool = False,
    dashscope_api_key: str = "",
) -> str:
    """
    文生视频

    参数:
      prompt: 提示词
      output_path: 输出视频路径 (默认自动生成)
      model: 模型名 (turbo/std/pro/o1)
      duration: 视频时长 (5或10秒)
      aspect_ratio: 比例 (9:16竖屏 / 16:9横屏 / 1:1)
      access_key: Kling Access Key
      secret_key: Kling Secret Key
      use_dashscope: 是否走阿里云百炼 (替代直接调用 Kling API)
      dashscope_api_key: 阿里云百炼 API Key

    返回:
      本地视频文件路径
    """
    if use_dashscope:
        return _text2video_dashscope(prompt, output_path, model, duration, aspect_ratio, dashscope_api_key)
    else:
        return _text2video_kling(prompt, output_path, model, duration, aspect_ratio, access_key, secret_key)


def _text2video_kling(prompt, output_path, model, duration, aspect_ratio, access_key, secret_key):
    """通过 Kling 官方 API 生成"""
    if not output_path:
        output_path = str(CACHE_DIR / f"kling_{hashlib.md5(prompt.encode()).hexdigest()[:12]}.mp4")

    # 缓存检查
    if os.path.exists(output_path):
        logger.info(f"缓存命中: {output_path}")
        return output_path

    model_id = MODELS.get(model, MODELS["turbo"])["id"]
    token = _generate_jwt(access_key, secret_key)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_id,
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
    }

    logger.info(f"Kling 文生视频: model={model_id}, prompt={prompt[:40]}..., duration={duration}s")
    resp = httpx.post(f"{KLING_BASE}/v1/videos/text2video", headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    task_id = data.get("data", {}).get("task_id", "")
    if not task_id:
        raise RuntimeError(f"Kling 提交失败: {data}")

    logger.info(f"  任务提交成功: {task_id}")
    logger.info(f"  轮询等待结果... (预计30-60s)")

    # 轮询
    for i in range(60):
        time.sleep(5)
        q = httpx.get(f"{KLING_BASE}/v1/videos/{task_id}", headers=headers, timeout=15)
        q.raise_for_status()
        status_data = q.json().get("data", {})

        task_status = status_data.get("task_status", "")
        if task_status == "succeed":
            video_url = status_data.get("video", {}).get("url", "")
            if video_url:
                logger.info(f"  生成成功! 下载中...")
                _download(video_url, output_path)
                logger.info(f"  ✅ 已保存: {output_path}")
                return output_path
        elif task_status in ("failed",):
            raise RuntimeError(f"Kling 生成失败: {status_data.get('fail_reason', '未知错误')}")

        logger.debug(f"  [{i*5}s] 状态: {task_status}")

    raise TimeoutError("Kling 生成超时")


def _text2video_dashscope(prompt, output_path, model, duration, aspect_ratio, api_key):
    """通过阿里云百炼调用 Kling"""
    if not output_path:
        output_path = str(CACHE_DIR / f"dashscope_{hashlib.md5(prompt.encode()).hexdigest()[:12]}.mp4")

    if os.path.exists(output_path):
        logger.info(f"缓存命中: {output_path}")
        return output_path

    model_map = {"turbo": "kling/kling-v3-video-generation", "pro": "kling/kling-v3-omni-video-generation"}
    model_id = model_map.get(model, model_map["turbo"])

    size_map = {"9:16": "1080*1920", "16:9": "1920*1080", "1:1": "1080*1080"}
    size = size_map.get(aspect_ratio, "1080*1920")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    payload = {
        "model": model_id,
        "input": {"prompt": prompt, "duration": duration},
        "parameters": {"size": size, "n": 1},
    }

    resp = httpx.post(f"{DASHSCOPE_BASE}/api/v1/services/aigc/video-generation/video-synthesis",
                       headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    task_id = resp.json()["output"]["task_id"]

    # 轮询
    for i in range(40):
        time.sleep(15)
        q = httpx.get(f"{DASHSCOPE_BASE}/api/v1/tasks/{task_id}",
                       headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
        status = q.json().get("output", {}).get("task_status", "")
        if status == "SUCCEEDED":
            out = q.json().get("output", {})
            video_url = out.get("video_url", "")
            if not video_url:
                # fallback: results array
                results = out.get("results", [])
                if isinstance(results, list) and len(results) > 0:
                    video_url = results[0].get("video_url", "")
                elif isinstance(results, dict):
                    video_url = results.get("video_url", "")
            if not video_url:
                raise RuntimeError(f"百炼 Kling 返回成功但无 video_url: {q.json()}")
            _download(video_url, output_path)
            return output_path
        elif status in ("FAILED",):
            raise RuntimeError(f"百炼 Kling 失败: {q.json().get('output',{}).get('message','')}")

    raise TimeoutError("百炼 Kling 超时")


def _generate_jwt(access_key: str, secret_key: str) -> str:
    """生成 Kling API 的 JWT Bearer Token (HS256)"""
    now = int(time.time())
    payload = {
        "iss": access_key,
        "exp": now + 1800,       # 30分钟
        "nbf": now - 5,
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def _download(url: str, output_path: str):
    """下载文件"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with httpx.stream("GET", url, timeout=600) as resp:
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=8192):
                f.write(chunk)


# ── CLI 测试 ──
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Kling 文生视频测试")
    parser.add_argument("--prompt", default="一只橘猫在窗台上晒太阳")
    parser.add_argument("--model", default="turbo", choices=list(MODELS.keys()))
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--output", default="")
    parser.add_argument("--access-key", default=os.environ.get("KLING_ACCESS_KEY", ""))
    parser.add_argument("--secret-key", default=os.environ.get("KLING_SECRET_KEY", ""))
    args = parser.parse_args()

    path = text2video(
        prompt=args.prompt,
        output_path=args.output,
        model=args.model,
        duration=args.duration,
        access_key=args.access_key,
        secret_key=args.secret_key,
    )
    print(f"\n✅ 视频: {path}")

"""
person_swap/api.py — 阿里云百炼 Wan2.2-Animate 人物置换异步任务封装

人物置换(全身身份替换, 非换脸):
    原视频(人物A表演/动作) + 目标人物参考图(人物B 形象/衣着) → 输出「人物B 保留 A 动作姿态」的新视频

DashScope 异步任务通用流程:
    1. POST /api/v1/uploads?model={model}   上传素材(参考图/源视频) → 拿文件 URL
    2. POST .../video-generation/video-synthesis (X-DashScope-Async: enable)
       提交 {model, input, parameters} → output.task_id
    3. GET /api/v1/tasks/{task_id} 轮询 → SUCCEEDED 取 video_url
    4. 下载成片到本地

⚠️ 状态说明(2026-09-05 实测):
    - 本机 key 可鉴权, 但账号 Arrearage(欠费) — 需在百炼控制台充值后恢复
    - model id 与 input 字段名待开通后校准: 豆包展示名 "Wan2.2-Animate(-mix-std/pro)"
      API id 疑似 wan2.2-animate-mix-std; 若报 Model not exist, 以控制台模型广场为准更新配置
"""
import sys, os, time
from pathlib import Path

import httpx

# ── 顶层目录约定: 本包位于 09_ave/scripts/person_swap/, 依赖 scripts/lib/* ──
_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from lib.logger import get_logger
from lib.config import load_config

logger = get_logger("person_swap")

DASHSCOPE_BASE = "https://dashscope.aliyuncs.com"
SYNTHESIS_URL = f"{DASHSCOPE_BASE}/api/v1/services/aigc/video-generation/video-synthesis"
TASK_URL = f"{DASHSCOPE_BASE}/api/v1/tasks/{{task_id}}"
UPLOAD_URL = f"{DASHSCOPE_BASE}/api/v1/uploads"


def get_api_key() -> str:
    """读取百炼 API key (local.yaml 的 aliyun.api_key, 优先环境变量覆盖)"""
    env = os.environ.get("DASHSCOPE_API_KEY", "")
    if env:
        return env
    cfg = load_config()
    return (cfg.get("aliyun", {}) or {}).get("api_key", "")


def get_model() -> str:
    """人物置换模型 id — 配置 person_swap.model (默认 wan2.2-animate-mix-std)"""
    cfg = load_config()
    ps = cfg.get("person_swap", {}) or {}
    return ps.get("model", "wan2.2-animate-mix-std")


# ════════════════════════════════════════════════════════════
# 账号状态探活 (供页面展示「账号是否可生成」)
# ════════════════════════════════════════════════════════════

def check_account_status() -> dict:
    """探测百炼账号可用性(最小真实调用, 零费用)

    注意: GET /models 在欠费账号下仍返回 200, 必须发一个最小 chat 请求才能探到
    Arrearage — 欠费账号连免费模型(qwen-turbo)都会被拒。

    返回: {"status": "ok"|"arrears"|"unconfigured"|"error", "detail": str, "model": str}
    """
    ak = get_api_key()
    if not ak or ak == "sk-xxx":
        return {"status": "unconfigured", "detail": "未配置百炼 API Key (agent-local/tools/ave/config/local.yaml → aliyun.api_key)"}
    try:
        # 最小 chat 请求(qwen-turbo 有免费额度; 欠费会 Arrearage)
        r = httpx.post(f"{DASHSCOPE_BASE}/compatible-mode/v1/chat/completions",
                       headers={"Authorization": f"Bearer {ak}", "Content-Type": "application/json"},
                       json={"model": "qwen-turbo",
                             "messages": [{"role": "user", "content": "hi"}],
                             "max_tokens": 1},
                       timeout=20)
        if r.status_code == 200:
            return {"status": "ok", "detail": "账号可用(qwen-turbo 探测通过)", "model": get_model()}
        body = r.text[:300]
        if "Arrearage" in body or "overdue" in body or "good standing" in body:
            return {"status": "arrears", "detail": "账号欠费/状态不良(Arrearage), 需到百炼控制台充值或解除冻结", "model": get_model()}
        return {"status": "error", "detail": f"HTTP {r.status_code}: {body}", "model": get_model()}
    except Exception as e:
        return {"status": "error", "detail": f"探测异常: {e}", "model": get_model()}


# ════════════════════════════════════════════════════════════
# 文件上传
# ════════════════════════════════════════════════════════════

def upload_file(api_key: str, file_path: str, model: str = "") -> str:
    """上传素材到百炼, 返回可用的 URL (data.uploaded_url)"""
    model = model or get_model()
    p = Path(file_path)
    with open(p, "rb") as f:
        r = httpx.post(f"{UPLOAD_URL}?model={model}",
                       headers={"Authorization": f"Bearer {api_key}"},
                       files={"file": (p.name, f, "application/octet-stream")},
                       timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"百炼上传失败 HTTP {r.status_code}: {r.text[:300]}")
    url = (r.json().get("data") or {}).get("uploaded_url", "")
    if not url:
        raise RuntimeError(f"百炼上传返回无 uploaded_url: {r.text[:300]}")
    logger.info("  上传成功: %s (%s)", p.name, url[:60])
    return url


# ════════════════════════════════════════════════════════════
# 任务提交 / 轮询 / 下载
# ════════════════════════════════════════════════════════════

def build_input(model: str, ref_image_url: str, source_video_url: str,
                prompt: str = "", duration: int = 0) -> dict:
    """构造人物置换 input — 字段名待模型开通后按官方文档校准

    Wan2.2-Animate 人物置换语义: 目标人物(参考图) + 动作来源(原视频)
    常用字段范式(以下为占位, 以实际 API 文档为准):
      image / character_image / reference_image → 人物参考图 URL
      video / source_video / motion_video        → 原视频 URL
    """
    cfg = load_config()
    ps = cfg.get("person_swap", {}) or {}
    img_key = ps.get("input_image_field", "image")
    vid_key = ps.get("input_video_field", "video")
    inp = {img_key: ref_image_url, vid_key: source_video_url}
    if prompt:
        inp["prompt"] = prompt
    return inp


def build_parameters(model: str, duration: int = 0, aspect_ratio: str = "9:16") -> dict:
    """构造 parameters — 分辨率/时长等随模型而定, 可配置"""
    cfg = load_config()
    ps = cfg.get("person_swap", {}) or {}
    size_map = {"9:16": "1080*1920", "16:9": "1920*1080", "1:1": "1080*1080"}
    params = {"size": ps.get("size", size_map.get(aspect_ratio, "1080*1920")), "n": 1}
    if duration and duration > 0:
        params["duration"] = duration
    return params


def submit_task(api_key: str, model: str, ref_image_url: str, source_video_url: str,
                prompt: str = "", duration: int = 0) -> str:
    """提交人物置换任务, 返回 task_id"""
    payload = {
        "model": model,
        "input": build_input(model, ref_image_url, source_video_url, prompt, duration),
        "parameters": build_parameters(model, duration),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    logger.info("提交人物置换: model=%s 时长=%ss prompt=%s", model, duration or "auto", (prompt or "")[:30])
    r = httpx.post(SYNTHESIS_URL, headers=headers, json=payload, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"百炼提交失败 HTTP {r.status_code}: {r.text[:400]}")
    task_id = (r.json().get("output") or {}).get("task_id", "")
    if not task_id:
        raise RuntimeError(f"百炼提交返回无 task_id: {r.text[:400]}")
    return task_id


def poll_task(api_key: str, task_id: str, timeout_sec: int = 900, interval: int = 10,
              progress_cb=None) -> dict:
    """轮询任务直到完成/失败/超时

    返回: {"status": "SUCCEEDED"|"FAILED"|"TIMEOUT", "video_url": str, "message": str}
    progress_cb(percent:int, note:str) 可选回调
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    deadline = time.time() + timeout_sec
    last_note = ""
    while time.time() < deadline:
        r = httpx.get(TASK_URL.format(task_id=task_id), headers=headers, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"查询任务失败 HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        out = data.get("output") or {}
        status = out.get("task_status", "")
        if status == "SUCCEEDED":
            video_url = out.get("video_url", "")
            if not video_url:
                results = out.get("results", [])
                if isinstance(results, list) and results:
                    video_url = results[0].get("video_url", "") or results[0].get("url", "")
                elif isinstance(results, dict):
                    video_url = results.get("video_url", "") or results.get("url", "")
            if progress_cb:
                progress_cb(100, "生成完成")
            return {"status": "SUCCEEDED", "video_url": video_url, "message": out.get("message", "")}
        if status == "FAILED":
            msg = out.get("message", "") or out.get("code", "") or "未知错误"
            if progress_cb:
                progress_cb(0, f"失败: {msg}")
            return {"status": "FAILED", "video_url": "", "message": msg}
        # 估算进度(无标准进度字段时用耗时粗估)
        pct = min(95, int((time.time() - (deadline - timeout_sec)) / timeout_sec * 100))
        note = out.get("task_status", status)
        if note != last_note:
            last_note = note
            logger.info("  [%s] 任务状态: %s", task_id[:8], status)
        if progress_cb:
            progress_cb(pct, f"生成中({status})")
        time.sleep(interval)
    return {"status": "TIMEOUT", "video_url": "", "message": f"轮询超时(>{timeout_sec}s)"}


def download_file(url: str, output_path: str) -> str:
    """下载成片到本地"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with httpx.stream("GET", url, timeout=600) as resp:
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=8192):
                f.write(chunk)
    return output_path


# ════════════════════════════════════════════════════════════
# 一站式: 上传×2 → 提交 → 轮询 → 下载
# ════════════════════════════════════════════════════════════

def run_swap(ref_image_path: str, source_video_path: str, output_path: str,
             prompt: str = "", duration: int = 0,
             model: str = "", api_key: str = "",
             timeout_sec: int = 900, progress_cb=None) -> str:
    """完整跑一次人物置换, 返回成片本地路径

    供 CLI / service worker / 调试脚本直接调用。
    """
    model = model or get_model()
    api_key = api_key or get_api_key()
    progress_cb = progress_cb or (lambda p, n: None)

    progress_cb(5, "上传参考图")
    img_url = upload_file(api_key, ref_image_path, model)
    progress_cb(15, "上传源视频")
    vid_url = upload_file(api_key, source_video_path, model)

    progress_cb(25, "提交生成任务")
    task_id = submit_task(api_key, model, img_url, vid_url, prompt, duration)

    progress_cb(30, "生成中(轮询)")
    result = poll_task(api_key, task_id, timeout_sec=timeout_sec,
                       progress_cb=lambda p, n: progress_cb(30 + int(p * 0.65), n))
    if result["status"] != "SUCCEEDED" or not result["video_url"]:
        raise RuntimeError(f"生成失败: {result['status']} {result['message']}")

    progress_cb(98, "下载成片")
    download_file(result["video_url"], output_path)
    progress_cb(100, "完成")
    return output_path


# ── CLI 冒烟测试 ──
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="百炼人物置换 CLI (需先处理欠费并校准模型id)")
    ap.add_argument("--image", required=True, help="人物参考图")
    ap.add_argument("--video", required=True, help="原视频(动作来源)")
    ap.add_argument("--prompt", default="", help="可选文字描述")
    ap.add_argument("--duration", type=int, default=5, help="成片时长(秒)")
    ap.add_argument("--model", default="", help="模型id(默认取配置)")
    ap.add_argument("--output", default="", help="成片输出路径")
    args = ap.parse_args()

    st = check_account_status()
    print("账号状态:", st["status"], "-", st["detail"])
    if st["status"] != "ok":
        print("⛔ 账号不可用, 无法生成。处理后重试。")
        sys.exit(1)

    out = args.output or str(Path.home() / "workbuddy-agent-os/agent-local/runtime/person_swap/outputs/smoke_test.mp4")
    path = run_swap(args.image, args.video, out, prompt=args.prompt,
                    duration=args.duration, model=args.model)
    print(f"\n✅ 成片: {path}")

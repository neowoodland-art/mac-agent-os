"""
AVE story_director/batch_generator — 批量 Kling 场景生成

职责:
  1. 读取 enriched scenes JSON（含 bridge 信息）
  2. 固定 seed + 角色描述块注入
  3. 批量提交 Kling 文生视频（支持并行 2 个任务）
  4. 轮询全部任务完成
  5. 成本跟踪 + Dashboard 埋点
  6. 返回生成视频路径列表 + 拼接脚本

用法:
  python batch_generator.py --scenes /tmp/ave_bridged_scenes.json --output-dir /tmp/ave_story
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import hashlib
import time
from pathlib import Path
from typing import Optional

from lib.logger import get_logger
from lib.config import load_config
from lib.cost_tracker import get_tracker, set_current_production_id

logger = get_logger("batch_generator")

# ── 缓存 ──
CACHE_DIR = Path(os.environ.get("AVE_CACHE_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local/tools/ave/cache/story")))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Kling API ──
KLING_BASE = "https://api-beijing.klingai.com"
DASHSCOPE_BASE = "https://dashscope.aliyuncs.com"

# 模型配置
MODELS = {
    "turbo": {"id": "kling/kling-v3-video-generation", "cost_per_s": 0.04, "desc": "最快, 百炼"},
    "pro":   {"id": "kling/kling-v3-omni-video-generation", "cost_per_s": 0.07, "desc": "百炼, 高质量"},
}
DEFAULT_MODEL = "turbo"
MAX_CONCURRENT = 2  # Kling 允许最大并行任务数


# ═══════════════════════════════════════════════════════════
# 单场景生成
# ═══════════════════════════════════════════════════════════

def generate_scene(
    scene: dict,
    output_dir: str,
    model: str = DEFAULT_MODEL,
    duration: int = 5,
    force: bool = False,
) -> str:
    """
    为一个场景生成 Kling 文生视频

    参数:
      scene: 场景字典（含 prompt, scene_id, seed, duration_sec 等）
      output_dir: 输出目录
      model: 模型名
      duration: 视频时长 (5 或 10 秒)
      force: 是否强制重新生成

    返回:
      本地视频路径（空字符串表示失败）
    """
    scene_id = scene.get("scene_id", 0)
    prompt = scene.get("prompt", "")
    seed = scene.get("seed", 42)
    duration_sec = scene.get("duration_sec", 10)

    if not prompt:
        logger.warning(f"Scene {scene_id}: 无 prompt, 跳过")
        return ""

    # 输出路径
    safe_name = hashlib.md5(prompt.encode()).hexdigest()[:12]
    output_path = os.path.join(output_dir, f"scene_{scene_id:02d}_{safe_name}.mp4")

    # 缓存检查
    if os.path.exists(output_path) and not force:
        logger.info(f"Scene {scene_id}: 缓存命中 {output_path}")
        return output_path

    cfg = load_config()

    # 优先使用 百炼 (dashscope)
    dashscope_key = cfg.get("aliyun", {}).get("api_key", "") or cfg.get("dashscope", {}).get("api_key", "")

    if dashscope_key:
        return _generate_via_dashscope(
            prompt=prompt,
            output_path=output_path,
            scene_id=scene_id,
            seed=seed,
            model=model,
            duration=duration,
            api_key=dashscope_key,
        )
    else:
        # 降级到 Kling 官方 API
        kling_cfg = cfg.get("kling", {})
        ak = kling_cfg.get("access_key", "")
        sk = kling_cfg.get("secret_key", "")
        if ak and sk:
            return _generate_via_kling(
                prompt=prompt,
                output_path=output_path,
                scene_id=scene_id,
                seed=seed,
                model=model,
                duration=duration,
                access_key=ak,
                secret_key=sk,
            )

    logger.error(f"Scene {scene_id}: 未配置 Kling API (dashscope 或 kling)")
    return ""


def _generate_via_dashscope(
    prompt: str,
    output_path: str,
    scene_id: int,
    seed: int,
    model: str,
    duration: int,
    api_key: str,
) -> str:
    """通过阿里云百炼调用 Kling 文生视频"""
    import httpx

    model_id = MODELS.get(model, MODELS[DEFAULT_MODEL])["id"]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    payload = {
        "model": model_id,
        "input": {"prompt": prompt, "duration": duration},
        "parameters": {
            "size": "1080*1920",
            "n": 1,
            "seed": seed,
        },
    }

    logger.info(f"Scene {scene_id}: 提交百炼 Kling (seed={seed})")
    logger.info(f"  prompt: {prompt[:60]}...")

    try:
        resp = httpx.post(
            f"{DASHSCOPE_BASE}/api/v1/services/aigc/video-generation/video-synthesis",
            headers=headers, json=payload, timeout=30,
        )
        resp.raise_for_status()
        task_id = resp.json()["output"]["task_id"]
    except Exception as e:
        logger.error(f"Scene {scene_id}: 提交失败: {e}")
        return ""

    # 轮询 (百炼 Kling 约 35s)
    for i in range(40):
        time.sleep(15)
        try:
            q = httpx.get(
                f"{DASHSCOPE_BASE}/api/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15,
            )
            data = q.json()
            status = data.get("output", {}).get("task_status", "")
        except Exception as e:
            logger.warning(f"Scene {scene_id}: 轮询失败 ({e}), 重试...")
            continue

        if status == "SUCCEEDED":
            out = data.get("output", {})
            video_url = out.get("video_url", "")
            if not video_url:
                results = out.get("results", [])
                if isinstance(results, list) and len(results) > 0:
                    video_url = results[0].get("video_url", "")
                elif isinstance(results, dict):
                    video_url = results.get("video_url", "")
            if video_url:
                _download(video_url, output_path)
                logger.info(f"Scene {scene_id}: ✅ 生成完成 ({os.path.getsize(output_path)//1024}KB)")
                # 成本跟踪
                get_tracker().log("Kling", duration=duration, resolution="1080P",
                                  status="success", note=f"scene_{scene_id}")
                return output_path
            else:
                logger.warning(f"Scene {scene_id}: 成功但无 video_url")
                return ""

        elif status in ("FAILED",):
            msg = data.get("output", {}).get("message", "未知错误")
            logger.error(f"Scene {scene_id}: 生成失败: {msg}")
            get_tracker().log("Kling", duration=duration, status="failed", note=f"scene_{scene_id}: {msg}")
            return ""

        logger.debug(f"Scene {scene_id}: [{i*15}s] {status}")

    logger.error(f"Scene {scene_id}: 超时 (40次轮询)")
    return ""


def _generate_via_kling(
    prompt: str,
    output_path: str,
    scene_id: int,
    seed: int,
    model: str,
    duration: int,
    access_key: str,
    secret_key: str,
) -> str:
    """通过 Kling 官方 API 直接调用"""
    import httpx
    import jwt

    model_id = MODELS.get(model, MODELS[DEFAULT_MODEL])["id"]
    # Kling 官方模型 ID 不同
    kling_model_map = {
        "turbo": "kling-v2.5-turbo",
        "pro": "kling-v2.6-pro",
    }
    kling_model_id = kling_model_map.get(model, kling_model_map["turbo"])

    # JWT 认证
    now = int(time.time())
    token = jwt.encode(
        {"iss": access_key, "exp": now + 1800, "nbf": now - 5},
        secret_key, algorithm="HS256",
    )
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = {
        "model": kling_model_id,
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": "9:16",
        "seed": seed,
    }

    logger.info(f"Scene {scene_id}: 提交 Kling 官方 API (seed={seed})")

    try:
        resp = httpx.post(f"{KLING_BASE}/v1/videos/text2video",
                          headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        task_id = resp.json().get("data", {}).get("task_id", "")
        if not task_id:
            raise RuntimeError(f"无 task_id: {resp.json()}")
    except Exception as e:
        logger.error(f"Scene {scene_id}: 提交失败: {e}")
        return ""

    # 轮询
    for i in range(60):
        time.sleep(5)
        try:
            q = httpx.get(f"{KLING_BASE}/v1/videos/{task_id}", headers=headers, timeout=15)
            status_data = q.json().get("data", {})
            task_status = status_data.get("task_status", "")
        except Exception as e:
            logger.warning(f"Scene {scene_id}: 轮询失败 ({e}), 重试...")
            continue

        if task_status == "succeed":
            video_url = status_data.get("video", {}).get("url", "")
            if video_url:
                _download(video_url, output_path)
                logger.info(f"Scene {scene_id}: ✅ 生成完成")
                get_tracker().log("Kling", duration=duration, resolution="1080P",
                                  status="success", note=f"scene_{scene_id}")
                return output_path
        elif task_status in ("failed",):
            reason = status_data.get("fail_reason", "未知错误")
            logger.error(f"Scene {scene_id}: 失败: {reason}")
            get_tracker().log("Kling", duration=duration, status="failed", note=f"scene_{scene_id}: {reason}")
            return ""

    logger.error(f"Scene {scene_id}: 超时 (60次轮询)")
    return ""


def _download(url: str, output_path: str):
    import httpx
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with httpx.stream("GET", url, timeout=600) as resp:
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=8192):
                f.write(chunk)


# ═══════════════════════════════════════════════════════════
# 批量生成
# ═══════════════════════════════════════════════════════════

def batch_generate(
    scenes_path: str,
    output_dir: str = "",
    model: str = DEFAULT_MODEL,
    duration: int = 5,
    force: bool = False,
) -> list[dict]:
    """
    批量生成所有场景视频

    参数:
      scenes_path: 场景 JSON 路径（含 bridge 信息）
      output_dir: 输出目录
      model: 模型名
      duration: 每场景视频时长 (5/10)
      force: 强制重新生成

    返回:
      [{"scene_id": 1, "path": "...", "status": "success/failed/skip", "duration_sec": 5}, ...]
    """
    with open(scenes_path, encoding="utf-8") as f:
        scenes = json.load(f)

    if not output_dir:
        output_dir = str(CACHE_DIR / f"batch_{int(time.time())}")
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"批量生成: {len(scenes)} 个场景, 模型={model}, duration={duration}s")
    logger.info(f"  输出目录: {output_dir}")

    results = []
    pending = list(scenes)
    in_flight = []  # [(scene_id, output_path), ...]
    completed_ids = set()

    # 并行池: 最多 MAX_CONCURRENT 个任务同时进行
    while pending or in_flight:
        # 填充空闲槽位
        while len(in_flight) < MAX_CONCURRENT and pending:
            scene = pending.pop(0)
            scene_id = scene.get("scene_id", 0)
            out_path = os.path.join(output_dir, f"scene_{scene_id:02d}.mp4")

            logger.info(f"  [{len(results)+1}/{len(scenes)}] Scene {scene_id}: 提交...")
            in_flight.append((scene, out_path))

        # 轮询所有 in_flight 任务
        still_in_flight = []
        for scene_data, out_path in in_flight:
            scene_id = scene_data["scene_id"]

            if scene_id in completed_ids:
                still_in_flight.append((scene_data, out_path))
                continue

            # 检查缓存
            if os.path.exists(out_path) and not force:
                logger.info(f"Scene {scene_id}: 缓存命中")
                results.append({
                    "scene_id": scene_id,
                    "path": out_path,
                    "status": "cached",
                    "duration_sec": scene_data.get("duration_sec", duration),
                    "seed": scene_data.get("seed", 42),
                })
                completed_ids.add(scene_id)
                continue

            # 执行生成
            video_path = generate_scene(
                scene_data,
                output_dir=output_dir,
                model=model,
                duration=duration,
                force=force,
            )

            if video_path:
                results.append({
                    "scene_id": scene_id,
                    "path": video_path,
                    "status": "success",
                    "duration_sec": scene_data.get("duration_sec", duration),
                    "seed": scene_data.get("seed", 42),
                })
            else:
                results.append({
                    "scene_id": scene_id,
                    "path": "",
                    "status": "failed",
                    "duration_sec": scene_data.get("duration_sec", duration),
                    "seed": scene_data.get("seed", 42),
                })
            completed_ids.add(scene_id)

        in_flight = still_in_flight

        if pending and not in_flight:
            # 全部完成或全失败
            break

    # 汇总
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    cached_count = sum(1 for r in results if r["status"] == "cached")

    logger.info(f"\n批量生成完成:")
    logger.info(f"  ✅ 成功: {success_count}")
    logger.info(f"  💾 缓存: {cached_count}")
    logger.info(f"  ❌ 失败: {failed_count}")
    logger.info(f"  📁 输出: {output_dir}")

    return results


# ═══════════════════════════════════════════════════════════
# 生成拼接脚本
# ═══════════════════════════════════════════════════════════

def build_concat_script(
    results: list[dict],
    scenes_path: str,
    output_path: str = "/tmp/ave_story_concat.sh",
) -> str:
    """
    生成 FFmpeg concat 拼接脚本

    参数:
      results: batch_generate 返回结果
      scenes_path: 场景 JSON 路径（用于读取 bridge 信息）
      output_path: 输出脚本路径

    返回:
      shell 脚本路径
    """
    with open(scenes_path, encoding="utf-8") as f:
        scenes = json.loads(f.read())

    # 构建 scene_id → scene dict 映射
    scene_map = {s.get("scene_id", 0): s for s in scenes}

    lines = ["#!/bin/bash", "# AVE 故事视频拼接脚本 (自动生成)", "", "set -e", ""]

    # 准备过渡参数
    transitions = []
    for r in sorted(results, key=lambda x: x.get("scene_id", 0)):
        sid = r.get("scene_id", 0)
        scene = scene_map.get(sid, {})
        bridge = scene.get("bridge_to_next", {})

        transition = bridge.get("transition_hint", "xfade=transition=fade:duration=0.5")
        video_path = r.get("path", "")
        if not video_path or not os.path.exists(video_path):
            logger.warning(f"Scene {sid}: 视频文件不存在，跳过拼接")
            continue

        transitions.append((sid, video_path, transition))

    if len(transitions) < 1:
        logger.warning("无可用视频，跳过拼接脚本生成")
        return ""

    # 生成 FFmpeg xfade 命令
    if len(transitions) == 1:
        sid, vpath, _ = transitions[0]
        lines.append(f"# 单场景: 直接输出")
        lines.append(f"cp '{vpath}' final_story.mp4")
    else:
        # 多场景 xfade 拼接
        # 提取所有视频路径
        input_videos = [t[1] for t in transitions]
        fade_durations = []

        for i, t in enumerate(transitions):
            sid, vpath, trans_hint = t
            # 解析过渡时长
            if "duration=" in trans_hint:
                dur = trans_hint.split("duration=")[1].split(")")[0]
            else:
                dur = "0.5"

            # 获取视频时长
            lines.append(f"# Scene {sid}: {vpath}")

            if i < len(transitions) - 1:
                fade_durations.append(dur)

        # 用 concat demuxer（最简单可靠的方式）
        filelist = "/tmp/ave_story_filelist.txt"
        lines.append("")
        lines.append(f"# 生成 concat file list")
        lines.append(f"cat > {filelist} << 'EOF'")
        for _, vpath, _ in transitions:
            lines.append(f"file '{os.path.abspath(vpath)}'")
        lines.append("EOF")
        lines.append("")
        lines.append("# FFmpeg 拼接")
        lines.append(f"ffmpeg -f concat -safe 0 -i {filelist} -c copy "
                     f"-movflags +faststart '{output_path.replace('.sh', '.mp4')}'")
        lines.append("")
        lines.append(f"echo '✅ 故事视频: {output_path.replace('.sh', '.mp4')}'")

    script = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(script + "\n")

    os.chmod(output_path, 0o755)
    logger.info(f"拼接脚本: {output_path}")
    return output_path


# ═══════════════════════════════════════════════════════════
# 完整管线: 场景 JSON → 批量生成 → 拼接脚本
# ═══════════════════════════════════════════════════════════

def run_story_pipeline(
    scenes_path: str,
    output_dir: str = "",
    model: str = DEFAULT_MODEL,
    duration: int = 5,
    force: bool = False,
) -> dict:
    """
    完整故事管线: 批量生成 + 拼接脚本

    返回:
      {"results": [...], "concat_script": "...", "output_dir": "..."}
    """
    # Dashboard 埋点
    try:
        from lib.dashboard import init_db, log_production, log_step, complete_production
        init_db()
        prod_id = log_production(
            strategy="故事",
            script_path=scenes_path,
            script_name=os.path.basename(scenes_path),
        )
        if prod_id > 0:
            set_current_production_id(prod_id)
    except Exception:
        prod_id = -1

    if not output_dir:
        output_dir = str(CACHE_DIR / f"story_{int(time.time())}")
    os.makedirs(output_dir, exist_ok=True)

    try:
        if prod_id > 0:
            log_step(prod_id, "batch_generate", "in_progress", detail=f"输出目录: {output_dir}")

        results = batch_generate(
            scenes_path=scenes_path,
            output_dir=output_dir,
            model=model,
            duration=duration,
            force=force,
        )

        if prod_id > 0:
            success_count = sum(1 for r in results if r["status"] == "success")
            failed_count = sum(1 for r in results if r["status"] == "failed")
            log_step(prod_id, "batch_generate", "completed",
                     detail=f"成功{success_count}/失败{failed_count}")

        concat_script = build_concat_script(results, scenes_path)
        concat_script_path = os.path.join(output_dir, "concat.sh")
        if concat_script:
            import shutil
            shutil.copy(concat_script, concat_script_path)

        if prod_id > 0:
            total_cost = get_tracker()._total_cost()
            complete_production(prod_id, status="completed", output_path=concat_script_path,
                                total_cost=total_cost)
            set_current_production_id(0)

        return {
            "results": results,
            "concat_script": concat_script_path,
            "output_dir": output_dir,
            "production_id": prod_id,
        }

    except Exception as e:
        logger.error(f"故事管线失败: {e}")
        if prod_id > 0:
            try:
                from lib.dashboard import complete_production
                complete_production(prod_id, status="failed")
                set_current_production_id(0)
            except Exception:
                pass
        raise


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def cli(args: list[str] | None = None):
    import argparse
    parser = argparse.ArgumentParser(description="批量 Kling 场景生成")
    parser.add_argument("--scenes", required=True, help="场景 JSON 路径")
    parser.add_argument("--output-dir", default="", help="输出目录 (默认自动生成)")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=list(MODELS.keys()), help="模型")
    parser.add_argument("--duration", type=int, default=5, choices=[5, 10], help="每场景时长(秒)")
    parser.add_argument("--force", action="store_true", help="强制重新生成")
    parser.add_argument("--dry-run", action="store_true", help="仅列出场景，不生成")

    parsed = parser.parse_args(args)

    # 加载场景
    with open(parsed.scenes, encoding="utf-8") as f:
        scenes = json.load(f)

    print(f"📋 场景清单 ({len(scenes)} 个):")
    print("=" * 60)
    for s in scenes:
        sid = s.get("scene_id", 0)
        prompt = s.get("prompt", "")[:50]
        seed = s.get("seed", 0)
        bridge = s.get("bridge_to_next", {})
        trans_type = bridge.get("type", "?") if bridge else "-"
        print(f"  Scene {sid:2d} | seed={seed:4d} | transition={trans_type:12s} | {prompt}...")

    if parsed.dry_run:
        print("\n⏸️  Dry-run 模式，未执行生成")
        return

    print(f"\n🚀 开始生成...")
    print(f"    模型: {parsed.model}")
    print(f"    时长: {parsed.duration}s")
    print(f"    输出: {parsed.output_dir or '自动'}")

    result = run_story_pipeline(
        scenes_path=parsed.scenes,
        output_dir=parsed.output_dir,
        model=parsed.model,
        duration=parsed.duration,
        force=parsed.force,
    )

    print(f"\n✅ 批量生成完成")
    print(f"   输出目录: {result['output_dir']}")
    print(f"   拼接脚本: {result['concat_script']}")

    for r in result["results"]:
        icon = "✅" if r["status"] == "success" else "💾" if r["status"] == "cached" else "❌"
        print(f"  {icon} Scene {r['scene_id']:2d}: {r.get('path', 'N/A')}")

    get_tracker().summary()


if __name__ == "__main__":
    cli()

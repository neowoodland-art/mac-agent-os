"""
AVE 07_service_layer — FastAPI 服务

将 AVE 全链路封装为 REST API，供其他工具/脚本调用。

启动:
  uvicorn service_layer.app:app --host 0.0.0.0 --port 8001 --reload

API:
  POST /ave/generate    — 提交视频生成任务
  GET  /ave/status/{id} — 查询任务状态
  GET  /ave/result/{id} — 下载结果视频
  GET  /health          — 健康检查
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from lib.config import load_config
from lib.logger import get_logger

logger = get_logger("ave_api")

app = FastAPI(title="AVE v2.0 API", version="2.3.0")

# ── 任务存储 (内存) ─────────────────────────────────────────
# 生产环境应改用 Redis/DB，当前 CLI 工具场景够用
_tasks: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


# ── Pydantic 模型 ──────────────────────────────────────────

class GenerateRequest(BaseModel):
    script: str                          # YAML 文件路径 或 脚本文本
    output: str = "/tmp/ave_api_out.mp4"
    clips_per_segment: int = 2
    bgm: str | None = None
    subtitles: bool = True


class TaskStatus(BaseModel):
    task_id: str
    status: str       # pending / running / done / error
    progress: str = ""
    output: str | None = None
    error: str | None = None


# ── API ────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "AVE v2.0", "version": "2.3.0"}


@app.post("/ave/generate", response_model=TaskStatus)
def generate(req: GenerateRequest):
    """提交视频生成任务"""
    import yaml

    task_id = uuid.uuid4().hex[:12]

    # 确定脚本文件路径
    script_path = req.script
    if not os.path.exists(script_path):
        # 可能是内联 YAML 文本，写入临时文件
        try:
            yaml.safe_load(req.script)  # 验证 YAML 合法性
            tmp = f"/tmp/ave_script_{task_id}.yaml"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(req.script)
            script_path = tmp
        except yaml.YAMLError:
            raise HTTPException(status_code=400, detail="script 既不是有效路径，也不是有效 YAML")

    with _lock:
        _tasks[task_id] = {
            "status": "pending",
            "progress": "排队中",
            "output": req.output,
            "error": None,
        }

    # 后台线程执行
    thread = threading.Thread(
        target=_run_generate,
        args=(task_id, script_path, req.output, req.clips_per_segment, req.bgm, req.subtitles),
        daemon=True,
    )
    thread.start()

    return TaskStatus(task_id=task_id, status="pending", progress="已提交")


@app.get("/ave/status/{task_id}", response_model=TaskStatus)
def get_status(task_id: str):
    """查询任务状态"""
    with _lock:
        task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return TaskStatus(task_id=task_id, **task)


@app.get("/ave/result/{task_id}")
def get_result(task_id: str):
    """下载结果视频"""
    with _lock:
        task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    if task["status"] != "done":
        raise HTTPException(status_code=400, detail=f"任务状态: {task['status']}, 尚未完成")
    output = task["output"]
    if not output or not os.path.exists(output):
        raise HTTPException(status_code=404, detail=f"输出文件不存在: {output}")
    return FileResponse(output, filename=os.path.basename(output))


# ── 后台任务 ────────────────────────────────────────────────

def _run_generate(
    task_id: str,
    script_path: str,
    output: str,
    clips_per_segment: int,
    bgm: str | None,
    subtitles: bool,
):
    """在后台线程中执行 generate 流程"""
    _update_task(task_id, "running", "加载配置...")

    try:
        cfg = load_config()
        import yaml

        # 1. 读取脚本
        _update_task(task_id, "running", "读取脚本...")
        if script_path.endswith((".yaml", ".yml")):
            with open(script_path, encoding="utf-8") as f:
                script_data = yaml.safe_load(f)
        else:
            from director_parser.parser import parse_script
            script_path = parse_script(script_path, style="knowledge_lecture")
            with open(script_path, encoding="utf-8") as f:
                script_data = yaml.safe_load(f)

        segments = script_data.get("segments", [])
        total_duration = sum(s.get("duration_sec", 10) for s in segments)
        _update_task(task_id, "running", f"脚本: {len(segments)} 段, 预计 {total_duration}s")

        # 2. TTS 人声 (带字级时间戳)
        _update_task(task_id, "running", "合成人声...")
        from voice_synthesizer.aliyun import synthesize_with_timestamps
        ak = cfg.get("aliyun", {}).get("api_key", "")
        vid = cfg.get("aliyun", {}).get("voice_id", "")
        text_all = "\n".join(s["text"] for s in segments)
        voice_path, word_ts = synthesize_with_timestamps(
            text_all, "/tmp/ave_api_voice.wav",
            api_key=ak, voice_id=vid,
        )

        # 3. 搜索素材
        _update_task(task_id, "running", "搜索素材...")
        from material_producer.pexels.search import search_videos
        mat_cfg = cfg.get("pexels", {})
        all_clips = []
        for seg in segments:
            keyword = seg.get("material", {}).get("search", "")
            if not keyword:
                continue
            clips = search_videos(
                keyword, count=clips_per_segment,
                api_key=mat_cfg.get("api_key", ""), orientation="portrait",
            )
            all_clips.extend((c["path"], c["duration"]) for c in clips)

        if not all_clips:
            raise RuntimeError("无素材，无法合成")

        clip_paths = [c[0] for c in all_clips]
        _update_task(task_id, "running", f"素材: {len(clip_paths)} 个")

        # 4. 混音
        _update_task(task_id, "running", "混音...")
        from composer.ffmpeg import mix_audio
        if bgm and os.path.exists(bgm):
            mixed_audio = mix_audio(voice_path, bgm, bgm_volume=0.35)
        else:
            mixed_audio = voice_path

        # 5. 字幕
        subtitles_path = None
        if subtitles and segments and word_ts:
            from composer.ffmpeg import create_subtitles
            char_positions = []
            acc = 0
            for w in word_ts:
                char_positions.append(acc)
                acc += len(w["text"])
            full_text_from_ts = "".join(w["text"] for w in word_ts)

            cursor = 0
            for seg in segments:
                seg_text = seg["text"]
                try:
                    pos = full_text_from_ts.index(seg_text, cursor)
                    char_end = pos + len(seg_text)
                    seg_indices = [i for i in range(len(word_ts))
                                   if char_positions[i] >= pos
                                   and char_positions[i] + len(word_ts[i]["text"]) <= char_end]
                    seg_words = [word_ts[i] for i in seg_indices] if seg_indices else []
                except ValueError:
                    seg_words = []

                if seg_words:
                    seg["start_sec"] = seg_words[0]["begin_time"] / 1000.0
                    seg["end_sec"] = seg_words[-1]["end_time"] / 1000.0
                else:
                    total_ms = word_ts[-1]["end_time"]
                    seg["start_sec"] = (pos / max(len(full_text_from_ts), 1)) * total_ms / 1000.0
                    seg["end_sec"] = (char_end / max(len(full_text_from_ts), 1)) * total_ms / 1000.0
                cursor = pos + len(seg_text)

            subtitles_path = "/tmp/ave_api_subtitles.ass"
            create_subtitles(segments, subtitles_path)

        # 6. 合成视频
        _update_task(task_id, "running", "合成视频...")
        from composer.ffmpeg import compose_video, segment_render, concat_segments, _get_media_duration
        audio_duration = _get_media_duration(mixed_audio)

        if audio_duration > 180:
            import tempfile, shutil
            seg_dir = tempfile.mkdtemp(prefix="ave_api_seg_")
            seg_files = segment_render(clip_paths, mixed_audio, output_dir=seg_dir,
                                       subtitles_path=subtitles_path)
            if len(seg_files) > 1:
                concat_segments(seg_files, output)
                shutil.rmtree(seg_dir, ignore_errors=True)
            else:
                shutil.move(seg_files[0], output)
                shutil.rmtree(seg_dir, ignore_errors=True)
        else:
            compose_video(clip_paths, mixed_audio, output,
                          resolution="1080x1920", subtitles_path=subtitles_path)

        _update_task(task_id, "done", f"完成: {output}")
        logger.info(f"✅ Task {task_id} 完成: {output}")

    except Exception as e:
        logger.error(f"❌ Task {task_id} 失败: {e}")
        _update_task(task_id, "error", str(e))


def _update_task(task_id: str, status: str, progress: str, error: str | None = None):
    """更新任务状态（线程安全）"""
    with _lock:
        if task_id in _tasks:
            _tasks[task_id].update({"status": status, "progress": progress})
            if error:
                _tasks[task_id]["error"] = error

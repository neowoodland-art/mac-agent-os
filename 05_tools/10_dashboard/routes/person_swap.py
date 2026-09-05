"""
routes/person_swap.py — 人物置换 API（相对独立的业务模块）

前缀: /api/person-swap
功能: 上传(原视频+人物参考图) → 任务队列 → 轮询状态 → 预览/成片访问
后端: person_swap service (AVE scripts 下独立包, SQLite + 后台 worker)

说明:
  - 本模块是业务功能, 不经过 command_bus(不占养号槽位), 独立队列
  - 账号欠费时页面给出明确提示, 任务会 failed 且不烧重试
  - 文件服务只读 agent-local/runtime/person_swap/ 下受控路径(路径取自任务DB, 不接用户输入)
"""
import logging
import sys
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

logger = logging.getLogger("dashboard.person_swap")

# ── 定位 AVE scripts (person_swap 包所在) ──
_AVE_SCRIPTS = Path(__file__).resolve().parent.parent.parent / "09_ave" / "scripts"
if str(_AVE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_AVE_SCRIPTS))

router = APIRouter(prefix="/api/person-swap", tags=["person_swap"])

_RUNTIME = Path.home() / "workbuddy-agent-os" / "agent-local" / "runtime" / "person_swap"
_RAW_DIR = _RUNTIME / "raw"
_RAW_DIR.mkdir(parents=True, exist_ok=True)

_ALLOW_VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}
_ALLOW_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
_MAX_VIDEO_MB = 300
_MAX_IMAGE_MB = 20


def _get_service():
    from person_swap.service import get_service
    return get_service()


def _safe_path(path: str) -> Path:
    """仅允许 agent-local/runtime/person_swap 下的文件"""
    p = Path(path).resolve()
    root = _RUNTIME.resolve()
    try:
        p.relative_to(root)
    except ValueError:
        raise HTTPException(400, detail="非法路径")
    if not p.exists():
        raise HTTPException(404, detail="文件不存在")
    return p


# ════════════════════════════════════════════════════════════
# 状态与配置
# ════════════════════════════════════════════════════════════

@router.get("/status")
def api_ps_status():
    """整体状态: 账号可用性 + 模型 + 队列 + 月费用(页面顶部卡片)"""
    from person_swap.api import check_account_status, get_model
    svc = _get_service()
    acct = check_account_status()
    active = [t for t in svc.list_tasks(100)
              if t["status"] in ("queued", "processing")]
    return {
        "account": acct,
        "model": acct.get("model", get_model()),
        "queue_active": len(active),
        "monthly": svc.monthly_cost(),
        "limits": {"max_duration": 10, "orientation": "9:16"},  # 与 config person_swap 对齐的显示值
        "version": "0.1.0",
    }


# ════════════════════════════════════════════════════════════
# 任务 CRUD
# ════════════════════════════════════════════════════════════

@router.get("/tasks")
def api_ps_tasks(limit: int = 50, status: str = ""):
    """任务列表(按时间倒序) + 附加预览/成片是否可访问标记"""
    svc = _get_service()
    tasks = svc.list_tasks(limit=min(limit, 200), status=status)
    return {"tasks": tasks, "monthly": svc.monthly_cost()}


@router.get("/tasks/{task_id}")
def api_ps_task(task_id: str):
    svc = _get_service()
    t = svc.get_task(task_id)
    if not t:
        raise HTTPException(404, detail="任务不存在")
    return t


@router.post("/tasks")
async def api_ps_create(
    video: UploadFile = File(...),
    image: UploadFile = File(...),
    prompt: str = Form(""),
    character_name: str = Form(""),
    duration_sec: int = Form(0),
):
    """创建人物置换任务(multipart): video=原视频, image=人物参考图"""
    from person_swap import preprocess as pp

    vname = video.filename or "source.bin"
    iname = image.filename or "ref.bin"
    vext = Path(vname).suffix.lower()
    iext = Path(iname).suffix.lower()
    if vext not in _ALLOW_VIDEO_EXT:
        raise HTTPException(400, detail=f"视频格式不支持: {vext} (支持 {sorted(_ALLOW_VIDEO_EXT)})")
    if iext not in _ALLOW_IMAGE_EXT:
        raise HTTPException(400, detail=f"图片格式不支持: {iext} (支持 {sorted(_ALLOW_IMAGE_EXT)})")
    if duration_sec and not (1 <= duration_sec <= 30):
        raise HTTPException(400, detail="duration_sec 需在 1~30 之间(0=模型默认)")

    batch = uuid.uuid4().hex[:8]
    vpath = _RAW_DIR / f"{batch}_video{vext}"
    ipath = _RAW_DIR / f"{batch}_image{iext}"

    # 流式落盘 + 大小校验
    v_size, i_size = 0, 0
    with open(vpath, "wb") as f:
        while chunk := await video.read(1024 * 1024):
            v_size += len(chunk)
            if v_size > _MAX_VIDEO_MB * 1024 * 1024:
                vpath.unlink(missing_ok=True)
                raise HTTPException(413, detail=f"视频超过 {_MAX_VIDEO_MB}MB 上限")
            f.write(chunk)
    with open(ipath, "wb") as f:
        while chunk := await image.read(1024 * 1024):
            i_size += len(chunk)
            if i_size > _MAX_IMAGE_MB * 1024 * 1024:
                vpath.unlink(missing_ok=True)
                ipath.unlink(missing_ok=True)
                raise HTTPException(413, detail=f"图片超过 {_MAX_IMAGE_MB}MB 上限")
            f.write(chunk)

    # 预检(时长/图片可解码) — 失败即删文件并报错
    try:
        svc = _get_service()
        task = svc.create_task(str(vpath), str(ipath),
                               prompt=prompt.strip(),
                               character_name=character_name.strip(),
                               duration_sec=duration_sec)
    except Exception as e:
        vpath.unlink(missing_ok=True)
        ipath.unlink(missing_ok=True)
        raise HTTPException(400, detail=str(e))
    return {"task": task}


@router.post("/tasks/{task_id}/cancel")
def api_ps_cancel(task_id: str):
    svc = _get_service()
    try:
        t = svc.cancel_task(task_id)
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
    return {"task": t}


# ════════════════════════════════════════════════════════════
# 文件访问(受控: 预览/成片, 路径取自任务DB)
# ════════════════════════════════════════════════════════════

@router.get("/tasks/{task_id}/file/{kind}")
def api_ps_file(task_id: str, kind: str):
    """kind: preview(源视频预览帧) | output(成片) | source(原始上传视频) | image(人物参考图)"""
    svc = _get_service()
    t = svc.get_task(task_id)
    if not t:
        raise HTTPException(404, detail="任务不存在")
    key = {"preview": "preview_path", "output": "output_path",
           "source": "source_orig", "image": "image_orig"}.get(kind)
    if not key:
        raise HTTPException(400, detail="kind 必须是 preview/output/source/image")
    path = t.get(key, "")
    if not path:
        raise HTTPException(404, detail="该任务暂无此文件")
    p = _safe_path(path)
    media_type = "video/mp4" if kind in ("output", "source") else "image/jpeg"
    return FileResponse(str(p), media_type=media_type,
                        filename=f"{task_id}_{kind}{p.suffix}")

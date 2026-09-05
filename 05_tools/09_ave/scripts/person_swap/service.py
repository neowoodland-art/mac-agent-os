"""
person_swap/service.py — 人物置换任务管理 (SQLite + 后台单worker)

设计:
  - 任务持久化: agent-local/runtime/person_swap/tasks.db (程序运行时自建)
  - 单 worker 线程顺序处理队列(账号并发受限, 避免撞限流)
  - 状态机: queued → processing(内含 preprocessing/submitting/generating) → succeeded|failed|cancelled
  - 失败自动重试(损耗系数建模: 重试多耗一轮生成, 由费用护栏兜底)
  - 费用护栏: 单价(配置, 实测后填)×时长 估算; 月度累计超预算 → 新任务 blocked
  - Dashboard 重启恢复: processing → queued 重新整跑(远端已提交任务可能浪费一次, MVP 接受的局限)

线程安全: worker 独占写状态; 查询接口直接读 sqlite(每次新连接)。
"""
import json
import os
import sqlite3
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_ROOT = Path(__file__).resolve().parent.parent
if str(_SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_ROOT))

from lib.logger import get_logger

logger = get_logger("person_swap")

# ── 运行时目录(agent-local, 程序自建, 非人工修改) ──
_RUNTIME = Path.home() / "workbuddy-agent-os" / "agent-local" / "runtime" / "person_swap"
_UPLOAD_DIR = _RUNTIME / "uploads"
_OUTPUT_DIR = _RUNTIME / "outputs"
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = _RUNTIME / "tasks.db"

STATUS_QUEUED = "queued"
STATUS_PROCESSING = "processing"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"
STATUS_BLOCKED = "blocked"   # 预算/账号不可用等业务拦截

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id            TEXT PRIMARY KEY,
    status        TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    source_orig   TEXT NOT NULL,
    image_orig    TEXT NOT NULL,
    source_prep   TEXT DEFAULT '',
    image_prep    TEXT DEFAULT '',
    preview_path  TEXT DEFAULT '',
    prompt        TEXT DEFAULT '',
    character_name TEXT DEFAULT '',
    duration_sec  INTEGER DEFAULT 0,
    model         TEXT DEFAULT '',
    output_path   TEXT DEFAULT '',
    error         TEXT DEFAULT '',
    retries       INTEGER DEFAULT 0,
    cost_est      REAL DEFAULT 0,
    progress      INTEGER DEFAULT 0,
    note          TEXT DEFAULT '',
    cancel_requested INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(_DB_PATH), timeout=15)
    con.row_factory = sqlite3.Row
    return con


def _cfg() -> dict:
    from lib.config import load_config
    return (load_config().get("person_swap", {}) or {})


# ════════════════════════════════════════════════════════════
# 任务服务
# ════════════════════════════════════════════════════════════

class PersonSwapService:
    """单例任务服务: create/list/get/cancel + 后台 worker 消费队列"""

    _instance = None

    @classmethod
    def get(cls) -> "PersonSwapService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        con = _connect()
        con.executescript(_SCHEMA)
        con.commit()
        con.close()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run_worker, name="ps-worker", daemon=True)
        self._thread.start()
        # 启动恢复: processing → queued (Dashboard 重启后自动续跑)
        con = _connect()
        con.execute("UPDATE tasks SET status=?, note='服务重启, 任务重新排队' WHERE status=?",
                    (STATUS_QUEUED, STATUS_PROCESSING))
        con.commit()
        con.close()
        logger.info("person_swap service 启动, worker=%s", self._thread.name)

    # ── 查询 ──

    def list_tasks(self, limit: int = 50, status: str = "") -> list:
        con = _connect()
        sql = "SELECT * FROM tasks"
        args = []
        if status:
            sql += " WHERE status=?"
            args.append(status)
        sql += " ORDER BY created_at DESC LIMIT ?"
        args.append(int(limit))
        rows = [dict(r) for r in con.execute(sql, args).fetchall()]
        con.close()
        return rows

    def get_task(self, task_id: str) -> dict:
        con = _connect()
        row = con.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        con.close()
        return dict(row) if row else {}

    def monthly_cost(self) -> dict:
        """本月费用估算与预算"""
        cfg = _cfg()
        budget = float(cfg.get("monthly_budget", 300))
        con = _connect()
        row = con.execute(
            "SELECT COALESCE(SUM(cost_est),0) AS used FROM tasks "
            "WHERE status=? AND substr(created_at,1,7)=strftime('%Y-%m','now')",
            (STATUS_SUCCEEDED,)).fetchone()
        con.close()
        used = round(float(row["used"]), 2) if row else 0.0
        return {"used": used, "budget": budget, "remaining": round(budget - used, 2)}

    # ── 创建/取消 ──

    def create_task(self, source_path: str, image_path: str,
                    prompt: str = "", character_name: str = "",
                    duration_sec: int = 0) -> dict:
        """登记任务(先做基础校验), 返回任务 dict; 超预算返回 blocked 任务"""
        source_path = str(source_path)
        image_path = str(image_path)
        if not os.path.exists(source_path):
            raise ValueError(f"源视频不存在: {source_path}")
        if not os.path.exists(image_path):
            raise ValueError(f"参考图不存在: {image_path}")

        # 素材预检(时长/尺寸) — 快速失败, 不进队列
        from person_swap import preprocess as pp
        try:
            vinfo = pp.probe_video(source_path)
            ichk = pp.check_image(image_path)
        except Exception as e:
            raise ValueError(f"素材预检失败: {e}")
        if not ichk["ok"]:
            raise ValueError(ichk["error"])

        # 预算护栏
        mc = self.monthly_cost()
        if mc["remaining"] <= 0:
            raise ValueError(f"月度预算已用尽(¥{mc['used']}/{mc['budget']}), 请调整 person_swap.monthly_budget")

        # 超长提示(仍允许入队, worker 会截取)
        max_dur = int(_cfg().get("max_duration", 10))
        trimmed_note = ""
        if vinfo["duration_sec"] > max_dur:
            trimmed_note = f"源视频{vinfo['duration_sec']}s 超过{max_dur}s, 将截取前{max_dur}s"

        task_id = uuid.uuid4().hex[:12]
        now = _now()
        model = ""
        try:
            from person_swap.api import get_model
            model = get_model()
        except Exception:
            pass
        task = {
            "id": task_id, "status": STATUS_QUEUED, "created_at": now, "updated_at": now,
            "source_orig": source_path, "image_orig": image_path,
            "prompt": prompt or "", "character_name": character_name or "",
            "duration_sec": int(duration_sec or 0), "model": model,
            "note": trimmed_note or "排队中", "progress": 0,
        }
        con = _connect()
        con.execute("INSERT INTO tasks (id,status,created_at,updated_at,source_orig,image_orig,prompt,character_name,duration_sec,model,note) "
                    "VALUES (:id,:status,:created_at,:updated_at,:source_orig,:image_orig,:prompt,:character_name,:duration_sec,:model,:note)",
                    task)
        con.commit()
        con.close()
        logger.info("新任务 %s queued (视频 %.1fs %dx%d)", task_id, vinfo["duration_sec"], vinfo["width"], vinfo["height"])
        self._wake.set()
        task["video_info"] = vinfo
        return task

    def cancel_task(self, task_id: str) -> dict:
        task = self.get_task(task_id)
        if not task:
            raise ValueError("任务不存在")
        if task["status"] in (STATUS_SUCCEEDED, STATUS_FAILED, STATUS_CANCELLED):
            return task
        con = _connect()
        con.execute("UPDATE tasks SET cancel_requested=1, note='取消请求已登记(生成中任务远端可能继续跑完)' WHERE id=?",
                    (task_id,))
        con.commit()
        con.close()
        self._wake.set()
        return self.get_task(task_id)

    # ── worker ──

    def _run_worker(self):
        while not self._stop.is_set():
            task = self._dequeue()
            if task is None:
                self._wake.wait(timeout=5)
                self._wake.clear()
                continue
            try:
                self._process(task)
            except Exception as e:
                logger.exception("任务 %s 处理异常", task["id"])
                self._update(task["id"], status=STATUS_FAILED, error=str(e)[:500], note="内部异常")
            # 让出, 检查下一个
            time.sleep(1)

    def _dequeue(self) -> dict:
        con = _connect()
        row = con.execute("SELECT * FROM tasks WHERE status=? AND cancel_requested=0 "
                          "ORDER BY created_at ASC LIMIT 1", (STATUS_QUEUED,)).fetchone()
        if row:
            con.execute("UPDATE tasks SET status=?, updated_at=? WHERE id=?",
                        (STATUS_PROCESSING, _now(), row["id"]))
            con.commit()
        con.close()
        return dict(row) if row else None

    def _update(self, task_id: str, **kw):
        cols = ", ".join(f"{k}=?" for k in kw)
        vals = list(kw.values())
        con = _connect()
        con.execute(f"UPDATE tasks SET {cols}, updated_at=? WHERE id=?",
                    vals + [_now(), task_id])
        con.commit()
        con.close()

    def _process(self, task: dict):
        tid = task["id"]
        cfg = _cfg()

        def setp(p: int, note: str):
            self._update(tid, progress=p, note=note)
            logger.info("  [%s] %d%% %s", tid, p, note)

        # ── 阶段0: 账号可用性预检(欠费直接失败, 不烧重试) ──
        from person_swap.api import check_account_status, get_api_key
        st = check_account_status()
        if st["status"] != "ok":
            reason = "账号不可用: " + st["detail"]
            self._update(tid, status=STATUS_FAILED, error=reason, note="账号不可用", progress=0)
            logger.warning("任务 %s 失败: %s", tid, reason)
            return

        # ── 阶段1: 预处理 ──
        setp(3, "预处理素材(转码/裁切/归一化)")
        from person_swap import preprocess as pp
        work_dir = _UPLOAD_DIR / tid
        work_dir.mkdir(parents=True, exist_ok=True)

        prep_src = work_dir / "source_prep.mp4"
        try:
            sr = pp.prep_source_video(task["source_orig"], str(prep_src))
        except Exception as e:
            return self._handle_fail(task, f"视频预处理失败: {e}")
        prep_img = work_dir / "ref_prep.jpg"
        try:
            ir = pp.prep_reference_image(task["image_orig"], str(prep_img))
        except Exception as e:
            return self._handle_fail(task, f"参考图处理失败: {e}")
        preview = work_dir / "preview.jpg"
        try:
            pp.extract_preview_frame(sr["out_path"], str(preview))
        except Exception:
            preview = Path("")
        self._update(tid, source_prep=sr["out_path"], image_prep=ir["out_path"],
                     preview_path=str(preview))

        # ── 阶段2: 生成(重试循环, 损耗系数由费用护栏兜底) ──
        from person_swap import api
        max_retries = int(cfg.get("max_retries", 2))
        timeout_sec = int(cfg.get("timeout_sec", 900))
        output_path = str(_OUTPUT_DIR / f"{tid}.mp4")
        attempt = 0
        while True:
            if self._is_cancel_requested(tid):
                self._update(tid, status=STATUS_CANCELLED, note="已取消", progress=0)
                return
            attempt += 1
            setp(20, f"提交百炼生成(第{attempt}次)")
            try:
                api.run_swap(
                    ref_image_path=ir["out_path"],
                    source_video_path=sr["out_path"],
                    output_path=output_path,
                    prompt=task["prompt"],
                    duration=task["duration_sec"],
                    model=task["model"] or api.get_model(),
                    api_key=get_api_key(),
                    timeout_sec=timeout_sec,
                    progress_cb=lambda p, n: self._update(tid, progress=max(p, self.get_task(tid)["progress"]), note=n)
                        if not self._is_cancel_requested(tid) else None,
                )
                # 成功
                cost = self._estimate_cost(task, sr["duration_sec"])
                self._update(tid, status=STATUS_SUCCEEDED, output_path=output_path,
                             cost_est=cost, progress=100, note="✅ 生成完成")
                logger.info("任务 %s 完成: %s (费用≈¥%.3f)", tid, output_path, cost)
                return
            except Exception as e:
                msg = str(e)[:500]
                logger.warning("任务 %s 第%d次失败: %s", tid, attempt, msg)
                if attempt > max_retries or self._is_cancel_requested(tid):
                    return self._handle_fail(task, f"生成失败(重试{attempt-1}次后): {msg}")
                self._update(tid, note=f"失败, 自动重试({attempt}/{max_retries+1}): {msg[:80]}")
                time.sleep(3)  # 重试前喘息

    def _handle_fail(self, task: dict, reason: str):
        self._update(task["id"], status=STATUS_FAILED, error=reason[:500],
                     note="❌ " + reason[:100])

    def _is_cancel_requested(self, task_id: str) -> bool:
        con = _connect()
        row = con.execute("SELECT cancel_requested FROM tasks WHERE id=?", (task_id,)).fetchone()
        con.close()
        return bool(row and row["cancel_requested"])

    def _estimate_cost(self, task: dict, actual_duration: float) -> float:
        """费用估算: 单价(元/秒) × 实际生成时长(含损耗系数)"""
        cfg = _cfg()
        price = float(cfg.get("price_per_sec", 0.0) or 0.0)
        if price <= 0:
            return 0.0
        gen_dur = task["duration_sec"] or actual_duration
        # 损耗系数: 每次重试多耗一轮; 用 1 + 0.4*retries 简化(行业 ~1.4)
        loss = 1 + 0.4 * int(cfg.get("max_retries", 2))
        return round(price * gen_dur * loss, 3)


def get_service() -> PersonSwapService:
    return PersonSwapService.get()


# ── CLI 自测 ──
if __name__ == "__main__":
    svc = get_service()
    print("任务数:", len(svc.list_tasks(limit=100)))
    print("本月费用:", svc.monthly_cost())

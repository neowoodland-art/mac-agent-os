"""
collect_engine.py — 采集系统核心引擎 v1

职责：
  1. URL 解析 → 标准化目标
  2. 适配器路由（按平台选择适配器）
  3. 工具降级执行
  4. 结果入库（SQLite，去重）
  5. 多机分发（通过 command_bus）
  6. 异步任务管理（大量目标用轮询）
"""
import asyncio, json, logging, os, time, uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from services.collect_db import CollectDB
from services.adapters.douyin_collect import DouyinCollectAdapter
from services.adapters.xhs_collect import XhsCollectAdapter

logger = logging.getLogger("dashboard.collect.engine")

_THIS_DIR = Path(__file__).resolve().parent


class CollectEngine:
    """采集引擎"""

    def __init__(self):
        self.db = CollectDB()
        self._adapters = {}
        self._tasks = {}           # 异步任务缓存 {run_id: status}

    def _get_adapter(self, platform: str):
        """获取/缓存适配器实例"""
        if platform not in self._adapters:
            if platform == "douyin":
                self._adapters[platform] = DouyinCollectAdapter()
            elif platform in ("xiaohongshu", "xhs"):
                self._adapters[platform] = XhsCollectAdapter()
            else:
                raise ValueError(f"不支持的平台: {platform}")
        return self._adapters[platform]

    # ── URL 解析 ──

    def resolve_target(self, raw: str) -> dict:
        """解析单个目标 → 标准化格式"""
        raw = raw.strip()
        # 抖音短链: v.douyin.com/xxx
        if "v.douyin.com" in raw:
            return {"input": raw, "platform": "douyin", "type": "shortlink",
                    "status": "pending"}
        # 抖音视频页: douyin.com/video/{id}
        if "douyin.com/video/" in raw:
            import re
            m = re.search(r'/video/(\d+)', raw)
            return {"input": raw, "platform": "douyin", "type": "video",
                    "target_id": m.group(1) if m else raw, "status": "resolved"}
        # 抖音用户主页: douyin.com/user/{sec_uid}
        if "douyin.com/user/" in raw:
            sec_uid = raw.split("/user/")[-1].split("?")[0]
            return {"input": raw, "platform": "douyin", "type": "user",
                    "target_id": sec_uid, "status": "resolved"}
        # 小红书: xiaohongshu.com/explore/{id}
        if "xiaohongshu.com" in raw:
            import re
            m = re.search(r'/explore/([a-f0-9]+)', raw)
            if m:
                return {"input": raw, "platform": "xiaohongshu", "type": "note",
                        "target_id": m.group(1), "status": "resolved"}
        # 纯 sec_uid（抖音）
        if raw.startswith("MS4w") or len(raw) > 20:
            return {"input": raw, "platform": "douyin", "type": "user",
                    "target_id": raw, "status": "resolved"}
        # 纯数字（可能是 aweme_id）
        if raw.isdigit() and len(raw) >= 15:
            return {"input": raw, "platform": "douyin", "type": "video",
                    "target_id": raw, "status": "resolved"}
        return {"input": raw, "platform": "unknown", "type": "unknown",
                "status": "unresolved"}

    def resolve_urls(self, targets: list) -> list[dict]:
        """批量解析 URL"""
        return [self.resolve_target(t) for t in targets]

    # ── URL 短链解析 ──

    def _resolve_shortlink(self, url: str) -> Optional[str]:
        """解析抖音短链 → aweme_id"""
        import subprocess, re
        try:
            result = subprocess.run(
                ["curl", "-sI", url],
                capture_output=True, text=True, timeout=10
            )
            loc = ""
            for line in result.stdout.split("\n"):
                if line.lower().startswith("location:"):
                    loc = line.split(":", 1)[1].strip()
                    break
            if loc:
                m = re.search(r'/video/(\d+)', loc)
                if m:
                    return m.group(1)
                # iesdouyin.com 格式
                m = re.search(r'/share/video/(\d+)', loc)
                if m:
                    return m.group(1)
            return None
        except:
            return None

    # ── 核心执行 ──

    async def run(self, request: dict) -> dict:
        """
        执行采集任务

        request:
          targets: [str]         — 目标列表
          platform: str          — 自动识别时留空
          depth: "light"         — "light"/"deep"
          tool_level: int        — 1/2/3
          machine: str           — 指定机器（空=本机）
          multi_machine: bool    — 是否多机协同
          async_mode: bool       — 是否异步（大量目标用）
        """
        t0 = time.time()
        targets = request.get("targets", [])
        platform = request.get("platform", "auto")
        depth = request.get("depth", "light")
        tool_level = request.get("tool_level", 2)
        machine = request.get("machine", "")
        multi_machine = request.get("multi_machine", False)
        async_mode = request.get("async_mode", False) or len(targets) > 50

        # 1. 解析目标
        resolved = self.resolve_urls(targets)
        unresolved = [r for r in resolved if r["status"] == "unresolved"]
        shortlinks = [r for r in resolved if r["type"] == "shortlink"]

        # 2. 解析短链
        for sl in shortlinks:
            aweme_id = self._resolve_shortlink(sl["input"])
            if aweme_id:
                sl["type"] = "video"
                sl["target_id"] = aweme_id
                sl["platform"] = "douyin"
                sl["status"] = "resolved"
            else:
                sl["status"] = "unresolved"

        ready = [r for r in resolved if r["status"] == "resolved"]

        # 3. 异步模式 → 创建后台任务
        if async_mode:
            run_id = str(uuid.uuid4())[:8]
            self._tasks[run_id] = {
                "id": run_id, "status": "running",
                "total": len(ready), "completed": 0,
                "results": [], "errors": [],
                "created_at": datetime.now().isoformat(),
            }
            asyncio.create_task(self._run_async(run_id, ready, platform,
                                                depth, tool_level))
            return {
                "status": "async",
                "run_id": run_id,
                "total": len(ready),
                "message": f"异步任务已创建（{len(ready)} 个目标）",
            }

        # 4. 同步模式（目标少，直接执行）
        task_id = self.db.create_task(
            "single", platform or "auto",
            json.dumps([t["input"] for t in targets], ensure_ascii=False),
            depth, tool_level, machine, len(ready)
        )
        results = []
        errors = []
        for target in ready:
            try:
                result = await self._collect_one(
                    target, platform or target["platform"],
                    depth, tool_level
                )
                if result:
                    # 入库
                    db_id = self.db.insert_item(
                        task_id=task_id,
                        platform=result.get("platform", ""),
                        item_id=result.get("item_id", ""),
                        url=result.get("url", ""),
                        title=result.get("title", ""),
                        author_name=result.get("author_name", ""),
                        author_id=result.get("author_id", ""),
                        published_at=result.get("published_at", ""),
                        text_content=result.get("text_content", ""),
                        tags=result.get("tags", []),
                        stats=result.get("stats", {}),
                        extra=result.get("extra", {}),
                        media=result.get("media", []),
                    )
                    # 评论独立入库
                    comments = result.get("comments", [])
                    if comments and db_id:
                        self.db.insert_comments(db_id, comments)
                    # 移除冗余字段
                    result.pop("comments", None)
                    results.append(result)
            except Exception as e:
                errors.append({"target": target["input"], "error": str(e)})

        self.db.update_task_status(task_id, "completed" if not errors else "completed",
                                    summary=json.dumps({"success": len(results),
                                                         "errors": len(errors)},
                                                        ensure_ascii=False))

        return {
            "status": "completed",
            "task_id": task_id,
            "duration": round(time.time() - t0, 1),
            "total": len(ready),
            "success": len(results),
            "errors": errors,
            "data": results,
        }

    async def _collect_one(self, target: dict, platform: str,
                           depth: str, tool_level: int) -> Optional[dict]:
        """采集单个目标"""
        try:
            adapter = self._get_adapter(platform)
        except ValueError:
            logger.warning(f"  ⚠️ 不支持的平台: {platform}")
            return None

        try:
            if target["type"] == "user":
                items = await adapter.collect_user(target["target_id"])
                if items:
                    return items[0]  # 返回第一个
                return None
            elif target["type"] == "video":
                return await adapter.collect_item(target["target_id"],
                                                  depth, tool_level)
            elif target["type"] == "note":
                return await adapter.collect_item(target["target_id"],
                                                  depth, tool_level)
            else:
                return None
        except Exception as e:
            logger.error(f"  ❌ 采集失败 [{target['input']}]: {e}")
            return None

    async def _run_async(self, run_id: str, targets: list, platform: str,
                         depth: str, tool_level: int):
        """异步执行大量目标"""
        task_data = self._tasks.get(run_id, {})
        for target in targets:
            try:
                result = await self._collect_one(
                    target, platform or target["platform"],
                    depth, tool_level
                )
                if result:
                    task_data["results"].append(result)
            except Exception as e:
                task_data["errors"].append({"target": target["input"], "error": str(e)})
            task_data["completed"] += 1
        task_data["status"] = "completed"

    def get_async_result(self, run_id: str) -> Optional[dict]:
        """查询异步任务结果"""
        return self._tasks.get(run_id)

    # ── 统计 ──

    def get_stats(self) -> dict:
        return {
            "total": sum(self.db.count_by_platform().values()),
            "today": self.db.count_today(),
            "sources": self.db.sources_count(),
            "by_platform": self.db.count_by_platform(),
            "tasks": self.db.task_stats(),
        }

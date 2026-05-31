"""
asset_manager/tags — 标签系统 + 素材搜索

职责:
  1. 自动标签: 根据文件属性和路径生成标签 (复用 index.py 的 _infer_tags)
  2. 标签管理: 查看所有标签、标签频次、批量标记
  3. 搜素引擎: 按名称/路径/标签/类型/来源 多维度过滤
  4. 搜索结果格式化输出 (表格/JSON)

用法:
  from asset_manager.tags import AssetSearch
  srch = AssetSearch()

  # 搜索
  results = srch.search("人物", tags=["video"])
  results = srch.search_by_tag("pexels", limit=20)

  # 标签管理
  srch.tag_stats()           # 所有标签频次
  srch.tag_asset(42, ["人物", "户外"])  # 给资产打标签
"""
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from lib.logger import get_logger

logger = get_logger("asset_tags")

# ── 全局路径 ─────────────────────────────────────────────
_LOCAL_ROOT = Path(os.environ.get(
    "AVE_LOCAL_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local"),
))
_DB_PATH = _LOCAL_ROOT / "tools" / "ave" / "data" / "ave.db"


# ═══════════════════════════════════════════════════════════
# 搜索类
# ═══════════════════════════════════════════════════════════

class AssetSearch:
    """素材搜索引擎 (基于 SQLite LIKE + 标签过滤)"""

    def __init__(self, db_path: Union[str, Path] = _DB_PATH):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    # ── 搜索 ─────────────────────────────────────────────

    def search(
        self,
        keyword: str = "",
        *,
        asset_type: Optional[str] = None,
        source: Optional[str] = None,
        tags: Optional[list[str]] = None,
        min_size: int = 0,
        max_size: int = 0,
        min_duration: float = 0.0,
        max_duration: float = 0.0,
        production_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "id DESC",
    ) -> list[dict]:
        """
        多维度素材搜索。

        参数:
          keyword:      关键字 (模糊匹配 name/file_path)
          asset_type:   文件类型 (video/audio/image/other)
          source:       来源 (materials/kling/wan2_2/bgm/...)
          tags:         标签列表 (AND 逻辑, 需同时命中)
          min_size:     最小文件大小 (bytes)
          max_size:     最大文件大小 (0 = 不限制)
          min_duration: 最小时长 (秒)
          max_duration: 最大时长 (0 = 不限制)
          production_id:关联 production ID
          limit/offset: 分页
          order_by:     排序 (SQL 片段, 如 "file_size DESC")

        返回:
          [{
            "id", "asset_type", "name", "file_path", "file_size",
            "hash", "source", "meta", "tags", "created_at",
            "production_id"
          }, ...]
        """
        conn = self._connect()
        try:
            where = []
            params: list = []

            # 关键字
            if keyword:
                like = f"%{keyword}%"
                where.append("(a.name LIKE ? OR a.file_path LIKE ?)")
                params.extend([like, like])

            # 类型
            if asset_type:
                where.append("a.asset_type = ?")
                params.append(asset_type)

            # 来源
            if source:
                where.append("a.source = ?")
                params.append(source)

            # 标签 (AND: 需要所有指定标签)
            if tags:
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append(
                        "EXISTS (SELECT 1 FROM asset_tags WHERE asset_id = a.id AND tag = ?)"
                    )
                    params.append(tag.lower())
                where.append("(" + " AND ".join(tag_conditions) + ")")

            # 文件大小
            if min_size > 0:
                where.append("a.file_size >= ?")
                params.append(min_size)
            if max_size > 0:
                where.append("a.file_size <= ?")
                params.append(max_size)

            # 时长 (meta_json 中的 duration_sec)
            if min_duration > 0:
                where.append(
                    "json_extract(a.meta_json, '$.duration_sec') >= ?"
                )
                params.append(min_duration)
            if max_duration > 0:
                where.append(
                    "json_extract(a.meta_json, '$.duration_sec') <= ?"
                )
                params.append(max_duration)

            # production
            if production_id is not None:
                where.append("a.production_id = ?")
                params.append(production_id)

            # 排除内部记录
            where.append("a.asset_type != '__meta__'")

            where_clause = " AND ".join(where) if where else "1=1"

            # 安全校验 order_by (防止 SQL 注入)
            allowed_orders = {
                "id", "id DESC", "id ASC",
                "file_size", "file_size DESC", "file_size ASC",
                "created_at", "created_at DESC", "created_at ASC",
                "name", "name DESC", "name ASC",
            }
            safe_order = order_by if order_by in allowed_orders else "id DESC"

            rows = conn.execute(
                f"""SELECT a.*, GROUP_CONCAT(at.tag, ',') as tag_list
                    FROM assets a
                    LEFT JOIN asset_tags at ON at.asset_id = a.id
                    WHERE {where_clause}
                    GROUP BY a.id
                    ORDER BY {safe_order}
                    LIMIT ? OFFSET ?""",
                params + [limit, offset],
            ).fetchall()

            results = []
            for r in rows:
                d = dict(r)
                # 解析 meta_json
                try:
                    d["meta"] = json.loads(d.pop("meta_json", "{}") or "{}")
                except json.JSONDecodeError:
                    d["meta"] = {}
                # 标签列表
                d["tags"] = d.pop("tag_list", "").split(",") if d.get("tag_list") else []
                d["file_size_human"] = _human_size(d.get("file_size", 0))
                results.append(d)

            return results

        except Exception as e:
            logger.error(f"search 失败: {e}")
            return []
        finally:
            conn.close()

    # ── 标签搜索 ─────────────────────────────────────────

    def search_by_tag(self, tag: str, limit: int = 50) -> list[dict]:
        """按单个标签搜索"""
        return self.search(tags=[tag], limit=limit)

    def search_by_type(self, asset_type: str, limit: int = 50) -> list[dict]:
        """按类型搜索"""
        return self.search(asset_type=asset_type, limit=limit)

    # ── 标签管理 ─────────────────────────────────────────

    def tag_stats(self) -> list[dict]:
        """返回所有标签及出现频次, 按频次降序"""
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT tag, COUNT(*) as count
                   FROM asset_tags
                   GROUP BY tag
                   ORDER BY count DESC"""
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def tag_asset(self, asset_id: int, tags: list[str]) -> bool:
        """给指定资产打标签"""
        conn = self._connect()
        try:
            for tag in tags:
                tag_clean = tag.strip().lower()
                if tag_clean:
                    conn.execute(
                        "INSERT OR IGNORE INTO asset_tags (asset_id, tag) VALUES (?, ?)",
                        (asset_id, tag_clean),
                    )
            conn.commit()
            logger.info(f"资产 {asset_id} 标记: {tags}")
            return True
        except Exception as e:
            logger.error(f"标记失败 asset {asset_id}: {e}")
            return False
        finally:
            conn.close()

    def untag_asset(self, asset_id: int, tags: list[str]) -> bool:
        """移除标签"""
        conn = self._connect()
        try:
            for tag in tags:
                conn.execute(
                    "DELETE FROM asset_tags WHERE asset_id = ? AND tag = ?",
                    (asset_id, tag.strip().lower()),
                )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"移除标签失败: {e}")
            return False
        finally:
            conn.close()

    def print_results(self, results: list[dict], show_meta: bool = False):
        """打印搜索结果表格"""
        if not results:
            print("  未找到匹配的素材")
            return

        print(f"\n  {'ID':>4s} {'类型':8s} {'来源':12s} {'大小':10s} {'名称'}")
        print(f"  {'-'*80}")
        for r in results:
            print(f"  {r['id']:>4d} {r['asset_type']:8s} {r['source'] or '?':12s} "
                  f"{r.get('file_size_human', ''):>10s} {r['name'] or '?'}")
            if show_meta and r.get("meta"):
                meta = r["meta"]
                parts = []
                if meta.get("duration_sec"):
                    parts.append(f"dur={meta['duration_sec']}s")
                if meta.get("width"):
                    parts.append(f"{meta['width']}x{meta['height']}")
                if meta.get("fps"):
                    parts.append(f"{meta['fps']}fps")
                if parts:
                    print(f"  {'':>4s} {'':8s} {'':12s} {'':10s} [{', '.join(parts)}]")
            if r.get("tags"):
                print(f"  {'':>4s} {'':8s} {'':12s} {'':10s} #{', #'.join(r['tags'][:5])}")
        print(f"  {'-'*80}")
        print(f"  共 {len(results)} 条结果\n")

    def print_tag_cloud(self):
        """打印标签云"""
        stats = self.tag_stats()
        if not stats:
            print("  暂无标签")
            return
        max_count = max(s["count"] for s in stats) if stats else 1

        print(f"\n  {'标签':24s} {'频次':>6s}  分布")
        print(f"  {'-'*60}")
        for s in stats:
            bar_len = int(s["count"] / max_count * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            print(f"  {s['tag']:24s} {s['count']:>6d}  {bar}")
        print(f"  共 {len(stats)} 个标签\n")


# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════

def _human_size(bytes_: int) -> str:
    if bytes_ < 1024:
        return f"{bytes_} B"
    elif bytes_ < 1024**2:
        return f"{bytes_/1024:.1f} KB"
    elif bytes_ < 1024**3:
        return f"{bytes_/(1024**2):.1f} MB"
    return f"{bytes_/(1024**3):.2f} GB"

"""
asset_manager/cache — 缓存管理与自动入库

职责:
  1. 增量扫描: 跟踪目录 mtime, 只扫描新文件
  2. 自动入库: 发现新文件 → 调用 AssetIndex 入库
  3. 缓存清理: 按策略清理孤立/过期文件
  4. 生产者钩子: Pexels/Kling 下载完成后自动通知

用法:
  from asset_manager.cache import CacheManager
  cm = CacheManager()
  cm.scan_new()               # 扫描所有目录的新文件
  cm.cleanup(days=30)         # 清理 30 天前无关联的素材
  cm.register_scan("/tmp/")   # 注册额外扫描目录

设计原则:
  - 无持续进程/守护: 每次 CLI 调用时触发扫描
  - mtime 记录在 SQLite meta_json 中, 跨会话持久
  - 重要素材 (有 production_id 关联) 不会被清理
"""
import json
import os
import shutil
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional, Union

from lib.logger import get_logger
from asset_manager.index import AssetIndex

logger = get_logger("asset_cache")

# ── 全局路径 (复用 index.py) ─────────────────────────────
_LOCAL_ROOT = Path(os.environ.get(
    "AVE_LOCAL_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local"),
))
_CACHE_DIR = _LOCAL_ROOT / "tools" / "ave" / "cache"
_DB_PATH = _LOCAL_ROOT / "tools" / "ave" / "data" / "ave.db"


# ═══════════════════════════════════════════════════════════
# 核心类
# ═══════════════════════════════════════════════════════════

class CacheManager:
    """缓存管理器

    属性:
      index:         AssetIndex 实例 (共享 DB)
      scan_records: {dir_path: last_mtime} 记录上次扫描时间
    """

    def __init__(self, cache_dir: Union[str, Path] = _CACHE_DIR,
                 db_path: Union[str, Path] = _DB_PATH):
        self.cache_dir = Path(cache_dir)
        self.db_path = Path(db_path)
        self.index = AssetIndex(cache_dir=cache_dir, db_path=db_path)
        # 额外扫描目录注册表: {路径: 回调函数}
        self._extra_scans: list[tuple[str, Optional[Callable]]] = []

    # ── 注册额外扫描目录 ─────────────────────────────────

    def register_scan(self, directory: str,
                      callback: Optional[Callable] = None):
        """注册额外目录到扫描列表 (如外部导入的素材目录)"""
        self._extra_scans.append((directory, callback))
        logger.info(f"注册扫描目录: {directory}")

    # ── 增量扫描 ─────────────────────────────────────────

    def _load_scan_record(self, subdir: str) -> float:
        """从 meta_json 读取上次扫描记录的 mtime"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            # 用特殊 hash 值 '_scan_record' 标记扫描记录
            row = conn.execute(
                "SELECT meta_json FROM assets WHERE hash = ? AND source = ?",
                (f"_scan_{subdir}", "__cache_mgr__"),
            ).fetchone()
            if row:
                rec = json.loads(row[0])
                return float(rec.get("last_mtime", 0))
        except Exception:
            pass
        finally:
            conn.close()
        return 0.0

    def _save_scan_record(self, subdir: str, mtime: float):
        """持久化扫描记录到 DB"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            # 先删除旧记录
            conn.execute(
                "DELETE FROM assets WHERE hash = ? AND source = ?",
                (f"_scan_{subdir}", "__cache_mgr__"),
            )
            conn.execute(
                """INSERT INTO assets (asset_type, name, file_path, file_size, hash, source, meta_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("__meta__", f"scan_record_{subdir}", "",
                 0, f"_scan_{subdir}", "__cache_mgr__",
                 json.dumps({"last_mtime": mtime, "updated_at": datetime.now().isoformat()})),
            )
            conn.commit()
        except Exception as e:
            logger.debug(f"保存扫描记录失败: {e}")
        finally:
            conn.close()

    def scan_new(self, force_rescan: bool = False) -> dict:
        """
        增量扫描: 只扫描 mtime 超过上次记录的文件。

        参数:
          force_rescan: 强制全量重新扫描

        返回:
          {"total_new": int, "per_dir": {subdir: new_count}}
        """
        from asset_manager.index import WATCHED_SUBDIRS, EXT_TYPE_MAP

        results: dict = {"total_new": 0, "per_dir": {}}
        valid_exts = set(EXT_TYPE_MAP.keys())

        for subdir in WATCHED_SUBDIRS:
            target = self.cache_dir / subdir
            if not target.is_dir():
                continue

            last_mtime = 0.0 if force_rescan else self._load_scan_record(subdir)
            new_count = 0

            for fpath in sorted(target.rglob("*")):
                if not fpath.is_file():
                    continue
                if fpath.suffix.lower() not in valid_exts:
                    continue

                file_mtime = fpath.stat().st_mtime
                if file_mtime > last_mtime:
                    ret = self.index.index_file(str(fpath))
                    if ret > 0:
                        new_count += 1

            # 更新扫描记录 (用当前最大 mtime)
            current_max = 0.0
            for fpath in target.rglob("*"):
                if fpath.is_file():
                    current_max = max(current_max, fpath.stat().st_mtime)
            self._save_scan_record(subdir, current_max)

            if new_count > 0:
                logger.info(f"  [{subdir}] 新增 {new_count} 个素材")
            results["per_dir"][subdir] = new_count
            results["total_new"] += new_count

        # 额外扫描目录
        for extra_dir, callback in self._extra_scans:
            extra_path = Path(extra_dir)
            if not extra_path.is_dir():
                continue
            for fpath in extra_path.rglob("*"):
                if not fpath.is_file():
                    continue
                if fpath.suffix.lower() not in valid_exts:
                    continue
                ret = self.index.index_file(str(fpath))
                if ret > 0:
                    results["total_new"] += 1
                    if callback:
                        try:
                            callback(str(fpath))
                        except Exception as e:
                            logger.warning(f"回调失败 {fpath}: {e}")

        logger.info(f"增量扫描完成, 共新增 {results['total_new']} 个素材")
        return results

    # ── 全量扫描 ─────────────────────────────────────────

    def scan_all(self, production_id: int = 0) -> dict:
        """全量扫描并重置所有扫描记录"""
        results = self.index.scan_all(production_id)

        # 重置扫描记录为最新 mtime
        from asset_manager.index import WATCHED_SUBDIRS
        for subdir in WATCHED_SUBDIRS:
            target = self.cache_dir / subdir
            if target.is_dir():
                current_max = max(
                    (f.stat().st_mtime for f in target.rglob("*") if f.is_file()),
                    default=0.0,
                )
                self._save_scan_record(subdir, current_max)

        return results

    # ── 缓存清理 ─────────────────────────────────────────

    def cleanup(self, days: int = 30, dry_run: bool = False) -> dict:
        """
        清理过期缓存。

        清理规则:
          - 无 production_id 关联
          - 文件创建时间 > days 天前
          - 保留有 production 引用的素材

        参数:
          days:    保留天数
          dry_run: 仅预览不删除

        返回:
          {"deleted": int, "freed_bytes": int, "files": [路径]}
        """
        conn = sqlite3.connect(str(self.db_path))
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        result: dict = {"deleted": 0, "freed_bytes": 0, "files": []}

        try:
            # 查找无关联的旧资产
            rows = conn.execute(
                """SELECT id, file_path, file_size FROM assets
                   WHERE production_id IS NULL
                     AND created_at < ?
                     AND asset_type != '__meta__'
                   ORDER BY created_at ASC""",
                (cutoff,),
            ).fetchall()

            for row in rows:
                aid, fpath, fsize = row["id"], row["file_path"], row["file_size"] or 0

                if dry_run:
                    result["deleted"] += 1
                    result["freed_bytes"] += fsize
                    result["files"].append(f"{fpath} ({_human_size(fsize)})")
                    continue

                # 删除磁盘文件
                if fpath and os.path.isfile(fpath):
                    try:
                        os.remove(fpath)
                        logger.debug(f"  删除文件: {fpath}")
                    except OSError as e:
                        logger.warning(f"  删除失败: {fpath}: {e}")

                # 删除 DB 记录
                conn.execute("DELETE FROM asset_tags WHERE asset_id = ?", (aid,))
                conn.execute("DELETE FROM production_assets WHERE asset_id = ?", (aid,))
                conn.execute("DELETE FROM assets WHERE id = ?", (aid,))

                result["deleted"] += 1
                result["freed_bytes"] += fsize
                result["files"].append(fpath)

            conn.commit()
        except Exception as e:
            logger.error(f"cleanup 失败: {e}")
        finally:
            conn.close()

        action = "预览" if dry_run else "清理"
        logger.info(f"缓存{action}: {result['deleted']} 个文件, "
                     f"释放 {_human_size(result['freed_bytes'])}")
        return result

    # ── 目录统计 ─────────────────────────────────────────

    def disk_usage(self) -> dict:
        """统计每个缓存目录的磁盘占用"""
        usage: dict = {}
        for subdir in os.listdir(self.cache_dir):
            target = self.cache_dir / subdir
            if not target.is_dir():
                continue
            total = 0
            count = 0
            for fpath in target.rglob("*"):
                if fpath.is_file():
                    total += fpath.stat().st_size
                    count += 1
            usage[subdir] = {
                "count": count,
                "size_bytes": total,
                "size_human": _human_size(total),
            }
        return usage

    def print_disk_usage(self):
        """打印磁盘占用表"""
        usage = self.disk_usage()
        print(f"\n{'='*50}")
        print(f"  缓存磁盘占用")
        print(f"{'='*50}")
        print(f"  {'目录':20s} {'文件数':>8s} {'大小':>12s}")
        print(f"  {'-'*40}")
        total_size = 0
        for subdir, info in sorted(usage.items(), key=lambda x: -x[1]["size_bytes"]):
            print(f"  {subdir:20s} {info['count']:>8d} {info['size_human']:>12s}")
            total_size += info["size_bytes"]
        print(f"  {'-'*40}")
        print(f"  {'总计':20s} {'':>8s} {_human_size(total_size):>12s}")
        print(f"{'='*50}\n")


# ═══════════════════════════════════════════════════════════
# 生产者自动入库钩子
# ═══════════════════════════════════════════════════════════

def auto_index_on_download(file_path: str, production_id: int = 0) -> int:
    """
    生产者在下载/生成素材后, 调用此函数自动入库。

    用法:
      from asset_manager.cache import auto_index_on_download

      path = pexels_search.download(url)
      auto_index_on_download(path, production_id=pid)
    """
    idx = AssetIndex()
    return idx.index_file(file_path, production_id=production_id)


def index_output_video(output_path: str, production_id: int) -> int:
    """
    最终成片入库 (特殊标记 source=output)。
    """
    if not os.path.isfile(output_path):
        return -1
    idx = AssetIndex()
    # 强制标记 source 为 output
    conn = sqlite3.connect(str(idx.db_path))
    try:
        # 先通过 index_file 入库
        aid = idx.index_file(output_path, production_id=production_id)
        if aid > 0:
            # 覆盖 source
            conn.execute(
                "UPDATE assets SET source = 'production_output' WHERE id = ?",
                (aid,),
            )
            conn.commit()
            return aid
        return aid
    except Exception as e:
        logger.error(f"index_output 失败: {e}")
        return -1
    finally:
        conn.close()


# ── 辅助函数 ─────────────────────────────────────────────

def _human_size(bytes_: int) -> str:
    if bytes_ < 1024:
        return f"{bytes_} B"
    elif bytes_ < 1024**2:
        return f"{bytes_/1024:.1f} KB"
    elif bytes_ < 1024**3:
        return f"{bytes_/(1024**2):.1f} MB"
    return f"{bytes_/(1024**3):.2f} GB"

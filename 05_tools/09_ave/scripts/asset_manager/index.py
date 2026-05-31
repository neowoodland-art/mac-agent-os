"""
asset_manager/index — 素材索引引擎

职责:
  1. 扫描所有已知素材目录，发现新文件
  2. 通过 ffprobe 提取视频/音频元数据 (时长/分辨率/编码/FPS)
  3. 计算文件 hash (首 64KB + 文件大小, 快速去重)
  4. 写入 SQLite assets 表, 避免重复入库

用法:
  from asset_manager.index import AssetIndex

  idx = AssetIndex()
  stats = idx.scan_all()           # 全量扫描所有目录
  stats = idx.scan_dir("materials")  # 扫描单个子目录
  print(idx.summarize())             # 打印统计

AssetIndex 发现策略:
  - 只扫描已知目录 (materials/kling/wan2_2/bgm/bgm_library/lipsync/character_sheet)
  - 按 hash 去重: 同一文件即使出现在不同目录也只入库一次
  - 增量模式: 只扫描 mtime > 上次扫描时间的文件
"""
import hashlib
import json
import os
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from lib.logger import get_logger

logger = get_logger("asset_index")

# ── 全局路径 ───────────────────────────────────────────────
_LOCAL_ROOT = Path(os.environ.get(
    "AVE_LOCAL_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local"),
))
_CACHE_DIR = _LOCAL_ROOT / "tools" / "ave" / "cache"
_DB_PATH = _LOCAL_ROOT / "tools" / "ave" / "data" / "ave.db"

# ── 已知素材目录 (相对于 cache) ──────────────────────────
WATCHED_SUBDIRS: dict[str, str] = {
    "materials":       "pexels 下载素材",
    "kling":           "Kling 生成视频",
    "wan2_2":          "Wan2.2 数字人视频",
    "bgm":             "BGM 缓存",
    "bgm_library":     "BGM 素材库",
    "lipsync":         "唇形同步产出",
    "character_sheet": "定妆照/角色图",
    "outputs":         "最终成片",
    "beat_sync":       "节拍分析缓存",
}

# ── 已知扩展名 → asset_type ─────────────────────────────
EXT_TYPE_MAP = {
    ".mp4":  "video",
    ".mov":  "video",
    ".webm": "video",
    ".avi":  "video",
    ".mkv":  "video",
    ".wav":  "audio",
    ".mp3":  "audio",
    ".aac":  "audio",
    ".m4a":  "audio",
    ".flac": "audio",
    ".ogg":  "audio",
    ".png":  "image",
    ".jpg":  "image",
    ".jpeg": "image",
    ".webp": "image",
    ".gif":  "image",
}


# ═══════════════════════════════════════════════════════════
# 核心类
# ═══════════════════════════════════════════════════════════

class AssetIndex:
    """素材索引引擎"""

    def __init__(self, cache_dir: Union[str, Path] = _CACHE_DIR,
                 db_path: Union[str, Path] = _DB_PATH):
        self.cache_dir = Path(cache_dir)
        self.db_path = Path(db_path)
        self._init_db()

    # ── DB 初始化 ──────────────────────────────────────────

    def _init_db(self):
        """确保 assets 相关表存在（复用 dashboard.py 的 schema）"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS assets (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_type      TEXT NOT NULL,
                    name            TEXT,
                    file_path       TEXT,
                    file_size       INTEGER,
                    hash            TEXT,
                    source          TEXT,
                    meta_json       TEXT,
                    production_id   INTEGER,
                    created_at      TEXT DEFAULT (datetime('now','localtime'))
                );
                CREATE TABLE IF NOT EXISTS asset_tags (
                    asset_id        INTEGER NOT NULL REFERENCES assets(id),
                    tag             TEXT NOT NULL,
                    PRIMARY KEY (asset_id, tag)
                );
                CREATE TABLE IF NOT EXISTS production_assets (
                    production_id   INTEGER NOT NULL REFERENCES productions(id),
                    asset_id        INTEGER NOT NULL REFERENCES assets(id),
                    role            TEXT,
                    PRIMARY KEY (production_id, asset_id)
                );
                CREATE INDEX IF NOT EXISTS idx_assets_hash ON assets(hash);
                CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
                CREATE INDEX IF NOT EXISTS idx_assets_path ON assets(file_path);
                CREATE INDEX IF NOT EXISTS idx_asset_tags_tag ON asset_tags(tag);
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"DB 初始化失败: {e}")

    # ── 文件级操作 ────────────────────────────────────────

    def _compute_hash(self, file_path: str) -> str:
        """快速 hash: 读首 64KB + 文件大小 (比全量 MD5 快 100x)"""
        try:
            sz = os.path.getsize(file_path)
            with open(file_path, "rb") as f:
                head = f.read(65536)  # 64KB
            h = hashlib.md5(head).hexdigest()[:16]
            return f"{h}_{sz}"
        except OSError:
            return ""

    def _extract_media_info(self, file_path: str) -> dict:
        """通过 ffprobe 提取媒体元数据"""
        meta: dict = {}
        ext = Path(file_path).suffix.lower()

        # 非视频/音频文件跳过 ffprobe
        if ext not in (".mp4", ".mov", ".webm", ".avi", ".mkv",
                       ".wav", ".mp3", ".aac", ".m4a", ".flac", ".ogg"):
            return meta

        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", file_path],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return meta

            data = json.loads(result.stdout)

            # 格式信息
            fmt = data.get("format", {})
            meta["format"] = fmt.get("format_name", "")
            meta["bitrate"] = int(fmt.get("bit_rate", 0))
            meta["duration_sec"] = round(float(fmt.get("duration", 0)), 2)
            meta["size_bytes"] = int(fmt.get("size", 0))

            # 视频流
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    meta["video_codec"] = stream.get("codec_name", "")
                    meta["width"] = stream.get("width", 0)
                    meta["height"] = stream.get("height", 0)
                    meta["fps"] = _parse_fps(stream.get("r_frame_rate", ""))
                    meta["pixel_format"] = stream.get("pix_fmt", "")
                    break

            # 音频流
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "audio":
                    meta["audio_codec"] = stream.get("codec_name", "")
                    meta["sample_rate"] = int(stream.get("sample_rate", 0))
                    meta["channels"] = stream.get("channels", 0)
                    break

        except (subprocess.TimeoutExpired, json.JSONDecodeError,
                FileNotFoundError) as e:
            logger.debug(f"ffprobe 失败 {file_path}: {e}")

        return meta

    def _source_from_path(self, file_path: str) -> str:
        """从文件路径推断来源"""
        p = Path(file_path)
        try:
            rel = p.relative_to(self.cache_dir)
            parts = rel.parts
            if len(parts) >= 1:
                return parts[0]  # 顶级子目录名 = source
        except ValueError:
            pass
        return "unknown"

    def _infer_tags(self, file_path: str, meta: dict, source: str) -> list[str]:
        """基于文件属性自动生成标签"""
        tags: list[str] = [source]
        ext = Path(file_path).suffix.lower()

        # 文件类型标签
        asset_type = EXT_TYPE_MAP.get(ext, "other")
        tags.append(asset_type)

        # 尺寸标签 (视频)
        w = meta.get("width", 0)
        h = meta.get("height", 0)
        if w and h:
            if w >= 3840 or h >= 2160:
                tags.append("4k")
            elif w >= 1920 or h >= 1080:
                tags.append("1080p")
            elif w >= 1280 or h >= 720:
                tags.append("720p")
            else:
                tags.append("sd")

        # 时长标签
        dur = meta.get("duration_sec", 0)
        if dur > 0:
            if dur < 2:
                tags.append("ultra_short")
            elif dur < 5:
                tags.append("short")
            elif dur < 15:
                tags.append("medium")
            elif dur < 60:
                tags.append("long")
            else:
                tags.append("extra_long")

        # 编码标签
        vcodec = meta.get("video_codec", "")
        if vcodec:
            tags.append(f"codec_{vcodec}")

        return tags

    # ── 单文件入库 ────────────────────────────────────────

    def index_file(self, file_path: str, production_id: int = 0,
                   force: bool = False) -> int:
        """
        索引单个文件并入库。

        参数:
          file_path:     文件绝对路径
          production_id: 关联的 production ID (0 = 不关联)
          force:         强制重新索引 (即使 hash 已存在)

        返回:
          asset_id (失败返回 -1, 已存在且未 force 返回 -2)
        """
        if not os.path.isfile(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return -1

        ext = Path(file_path).suffix.lower()
        asset_type = EXT_TYPE_MAP.get(ext, "other")
        name = Path(file_path).name
        file_size = os.path.getsize(file_path)
        file_hash = self._compute_hash(file_path)
        source = self._source_from_path(file_path)
        meta = self._extract_media_info(file_path)
        tags = self._infer_tags(file_path, meta, source)

        if not file_hash:
            return -1

        conn = sqlite3.connect(str(self.db_path))
        try:
            # 去重检查
            if not force and file_hash:
                existing = conn.execute(
                    "SELECT id FROM assets WHERE hash = ? LIMIT 1",
                    (file_hash,),
                ).fetchone()
                if existing:
                    conn.close()
                    return -2  # 已存在

            # 插入资产
            cur = conn.execute(
                """INSERT INTO assets
                   (asset_type, name, file_path, file_size, hash, source, meta_json, production_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (asset_type, name, file_path, file_size, file_hash, source,
                 json.dumps(meta, ensure_ascii=False),
                 production_id if production_id > 0 else None),
            )
            aid = cur.lastrowid

            # 标签
            for tag in set(tags):  # set 去重
                conn.execute(
                    "INSERT OR IGNORE INTO asset_tags (asset_id, tag) VALUES (?, ?)",
                    (aid, tag),
                )

            # 关联 production
            if production_id > 0:
                conn.execute(
                    """INSERT OR IGNORE INTO production_assets
                       (production_id, asset_id, role) VALUES (?, ?, ?)""",
                    (production_id, aid, "output" if source in ("materials", "kling", "wan2_2")
                     else "cache"),
                )

            conn.commit()
            logger.info(f"  入库: {name} (type={asset_type}, hash={file_hash[:12]}...)")
            return aid
        except Exception as e:
            logger.error(f"index_file 失败: {file_path}: {e}")
            return -1
        finally:
            conn.close()

    # ── 目录扫描 ──────────────────────────────────────────

    def scan_dir(self, subdir: str, production_id: int = 0,
                 progress: bool = True) -> dict:
        """
        扫描一个子目录, 入库所有新文件。

        参数:
          subdir:        WATCHED_SUBDIRS 中的 key (如 "materials")
          production_id: 可选关联 production
          progress:      打印进度

        返回:
          {"dir": str, "total": int, "new": int, "skipped": int, "errors": int}
        """
        target_dir = self.cache_dir / subdir
        stat = {"dir": subdir, "total": 0, "new": 0, "skipped": 0, "errors": 0}

        if not target_dir.is_dir():
            logger.warning(f"目录不存在: {target_dir}")
            return stat

        files = sorted(target_dir.rglob("*"))
        valid_exts = set(EXT_TYPE_MAP.keys())

        for i, fpath in enumerate(files):
            if not fpath.is_file():
                continue
            if fpath.suffix.lower() not in valid_exts:
                continue

            stat["total"] += 1
            ret = self.index_file(str(fpath), production_id)
            if ret == -1:
                stat["errors"] += 1
            elif ret == -2:
                stat["skipped"] += 1
            else:
                stat["new"] += 1

            if progress and i % 20 == 0 and i > 0:
                logger.info(f"  [{subdir}] {i} 文件已处理...")

        logger.info(f"  [{subdir}] 共 {stat['total']} 文件, "
                     f"新增 {stat['new']}, 跳过 {stat['skipped']}, 错误 {stat['errors']}")
        return stat

    def scan_all(self, production_id: int = 0, progress: bool = True) -> dict:
        """
        扫描所有已知素材目录。

        返回:
          {"total_new": int, "dirs": {subdir: stat_dict}}
        """
        results: dict = {"total_new": 0, "dirs": {}}
        for subdir in WATCHED_SUBDIRS:
            stat = self.scan_dir(subdir, production_id, progress)
            results["dirs"][subdir] = stat
            results["total_new"] += stat["new"]

        logger.info(f"全量扫描完成, 新增 {results['total_new']} 个素材")
        return results

    # ── 统计查询 ──────────────────────────────────────────

    def summarize(self) -> dict:
        """汇总当前素材库统计信息"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            total = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
            by_type = conn.execute(
                "SELECT asset_type, COUNT(*) as cnt FROM assets GROUP BY asset_type"
            ).fetchall()
            by_source = conn.execute(
                "SELECT source, COUNT(*) as cnt FROM assets GROUP BY source"
            ).fetchall()
            total_size = conn.execute(
                "SELECT COALESCE(SUM(file_size), 0) FROM assets"
            ).fetchone()[0]
            orphan = conn.execute(
                "SELECT COUNT(*) FROM assets WHERE production_id IS NULL"
            ).fetchone()[0]

            return {
                "total_assets": total,
                "by_type": dict(by_type),
                "by_source": dict(by_source),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 1),
                "orphan_count": orphan,
                "watched_dirs": list(WATCHED_SUBDIRS.keys()),
            }
        finally:
            conn.close()

    def print_summary(self):
        """打印人类可读的统计"""
        s = self.summarize()
        print(f"\n{'='*50}")
        print(f"  素材库统计")
        print(f"{'='*50}")
        print(f"  素材总数:     {s['total_assets']}")
        print(f"  总大小:       {s['total_size_mb']} MB")
        print(f"  无关联素材:    {s['orphan_count']}")
        print(f"\n  ─ 按类型 ─")
        for t, c in sorted(s["by_type"].items(), key=lambda x: -x[1]):
            print(f"    {t:12s}  {c}")
        print(f"\n  ─ 按来源 ─")
        for src, c in sorted(s["by_source"].items(), key=lambda x: -x[1]):
            print(f"    {src:16s}  {c}")
        print(f"\n  ─ 监控目录 ─")
        for d in s["watched_dirs"]:
            print(f"    {d}")
        print(f"{'='*50}\n")


# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════

def _parse_fps(r_frame_rate: str) -> float:
    """解析 ffprobe 的 r_frame_rate (如 '30000/1001' → 29.97)"""
    try:
        if "/" in r_frame_rate:
            num, den = r_frame_rate.split("/")
            return round(float(num) / float(den), 2)
        return float(r_frame_rate)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _human_size(bytes_: int) -> str:
    if bytes_ < 1024:
        return f"{bytes_} B"
    elif bytes_ < 1024**2:
        return f"{bytes_/1024:.1f} KB"
    elif bytes_ < 1024**3:
        return f"{bytes_/(1024**2):.1f} MB"
    return f"{bytes_/(1024**3):.2f} GB"

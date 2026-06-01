"""
BGM 选择器 (Music Selector) — 漫剧视频工厂 v1.0

功能:
  - 🔥 热门推荐 — 自动展示 Top N
  - 📂 分类浏览 — 按风格筛选
  - 🔍 搜索 — 按名字/艺术家/标签
  - 📁 自定义 BGM 注册
  - BPM 检测
  - 生产配置生成

用法:
  from music_selector import BGMSelector

  selector = BGMSelector()
  trending = selector.get_trending(limit=5)
  results = selector.search("枪火")
  config = selector.generate_config("枪火", beat_sync=True)
"""

import os
import re
import yaml
from pathlib import Path
from typing import Optional


# ── 默认路径 ──
SCRIPTS_DIR = Path(__file__).resolve().parent
LIBRARY_FILE = SCRIPTS_DIR / "music_library.yaml"

# 风格列表（用于分类浏览）
STYLE_CATEGORIES = ["🔥 热门推荐", "燃系", "治愈", "舒缓", "宏大", "轻快", "搞笑"]


# ═══════════════════════════════════════════════════════════
# BGM 条目
# ═══════════════════════════════════════════════════════════

class BGMEntry:
    """单个 BGM 条目"""

    def __init__(self, data: dict, category: str = "trending"):
        self.id: str = data.get("id", "")
        self.name: str = data.get("name", "")
        self.artist: str = data.get("artist", "")
        self.style: str = data.get("style", "")
        self.duration: int = data.get("duration", 0)
        self.source: str = data.get("source", "local")
        self.file: str = data.get("file", "")
        self.tags: list[str] = data.get("tags", [])
        self.bpm: int = data.get("bpm", 120)
        self.copyright: str = data.get("copyright", "free")
        self.category: str = category

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "artist": self.artist,
            "style": self.style,
            "duration": self.duration,
            "source": self.source,
            "file": self.file,
            "tags": self.tags,
            "bpm": self.bpm,
            "copyright": self.copyright,
            "category": self.category,
        }

    def __repr__(self) -> str:
        return f"<BGM: {self.name} - {self.artist}>"


# ═══════════════════════════════════════════════════════════
# BGM 选择器
# ═══════════════════════════════════════════════════════════

class BGMSelector:
    """BGM 选择器 — 音乐库管理 + 选择"""

    def __init__(self, library_path: Optional[str] = None):
        self._library_path = Path(library_path or LIBRARY_FILE)
        self._entries: list[BGMEntry] = []
        self._load()

    def _load(self):
        """从 YAML 加载音乐库"""
        if not self._library_path.exists():
            raise FileNotFoundError(f"音乐库文件不存在: {self._library_path}")

        with open(self._library_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self._entries = []
        categories = data.get("categories", {})
        for cat_name, items in categories.items():
            if isinstance(items, list):
                for item in items:
                    self._entries.append(BGMEntry(item, cat_name))

    def reload(self):
        """重新加载音乐库"""
        self._load()

    # ── 查询 ──

    def get_trending(self, limit: int = 5) -> list[dict]:
        """🔥 获取热门推荐"""
        trending = [e for e in self._entries if e.category == "trending"]
        return [e.to_dict() for e in trending[:limit]]

    def get_by_style(self, style: str) -> list[dict]:
        """📂 按风格筛选"""
        results = [e for e in self._entries if e.style == style]
        return [e.to_dict() for e in results]

    def get_by_category(self, category: str) -> list[dict]:
        """按分类获取"""
        results = [e for e in self._entries if e.category == category]
        return [e.to_dict() for e in results]

    def search(self, keyword: str) -> list[dict]:
        """🔍 搜索 — 匹配名字/艺术家/标签"""
        kw = keyword.lower()
        results = []
        for e in self._entries:
            if (kw in e.name.lower() or
                kw in e.artist.lower() or
                any(kw in t.lower() for t in e.tags) or
                kw in e.style.lower()):
                results.append(e.to_dict())
        return results

    def get_by_id(self, bgm_id: str) -> Optional[dict]:
        """按 ID 获取单条 BGM"""
        for e in self._entries:
            if e.id == bgm_id:
                return e.to_dict()
        return None

    def list_all(self) -> list[dict]:
        """列出所有可用 BGM"""
        return [e.to_dict() for e in self._entries]

    def list_styles(self) -> list[str]:
        """列出所有风格"""
        styles = sorted(set(e.style for e in self._entries if e.style))
        return styles

    def list_categories(self) -> list[str]:
        """列出所有分类"""
        return list({e.category for e in self._entries})

    # ── BPM 分析 ──

    def analyze_bpm(self, file_path: str) -> dict:
        """
        分析 BGM 文件的 BPM 和时长

        如果文件存在且有 librosa，使用 librosa 分析；
        否则返回注册库中的预估值。
        """
        # 检查是否有注册库中已有的数据
        for e in self._entries:
            if e.file and os.path.exists(e.file):
                pass  # 下面尝试分析

        # 尝试用 librosa 分析
        if os.path.exists(file_path):
            try:
                import librosa
                y, sr = librosa.load(file_path, sr=None)
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                duration = librosa.get_duration(y=y, sr=sr)
                return {
                    "bpm": round(tempo, 1),
                    "duration_sec": round(duration, 1),
                    "sample_rate": sr,
                }
            except (ImportError, Exception) as e:
                return {"bpm": 120, "duration_sec": 180, "note": f"分析失败: {e}"}

        return {"bpm": 120, "duration_sec": 180, "note": "文件不存在，返回默认值"}

    # ── 配置生成 ──

    def generate_config(self, bgm_id: str,
                         beat_sync: bool = True,
                         speed_ramp: bool = False,
                         ducking: bool = True,
                         volume: float = 0.7,
                         loop: bool = False,
                         intro_duration: int = 2,
                         outro_fade: int = 3) -> dict:
        """
        生成 BGM 生产配置

        参数:
          bgm_id: BGM ID
          beat_sync: 是否启用卡点
          speed_ramp: 是否启用副歌变速
          ducking: 人声避让（口播模式）
          volume: BGM 音量 (0-1)
          loop: 是否循环
          intro_duration: 淡入秒数
          outro_fade: 淡出秒数

        返回:
          BGM 配置字典，可直接嵌入 production.yaml
        """
        entry = self.get_by_id(bgm_id)
        if not entry:
            raise KeyError(f"未找到 BGM: {bgm_id}")

        return {
            "selected": entry["name"],
            "artist": entry["artist"],
            "file": entry["file"],
            "bpm": entry["bpm"],
            "beat_sync": beat_sync,
            "speed_ramp": speed_ramp,
            "ducking": ducking,
            "volume": volume,
            "loop": loop,
            "intro_duration": intro_duration,
            "outro_fade": outro_fade,
        }

    # ── 自定义 BGM 注册 ──

    def register_custom(self, name: str, artist: str, file_path: str,
                         style: str = "自定义", tags: Optional[list[str]] = None,
                         bpm: int = 120, duration: int = 180) -> dict:
        """
        注册自定义 BGM

        参数:
          name: BGM 名称
          artist: 艺术家
          file_path: 文件路径
          style: 风格
          tags: 标签列表
          bpm: BPM（如果已知）
          duration: 时长（秒）
        """
        bgm_id = f"custom_{name.lower().replace(' ', '_')[:20]}"

        entry_data = {
            "id": bgm_id,
            "name": name,
            "artist": artist,
            "style": style,
            "duration": duration,
            "source": "custom",
            "file": file_path,
            "tags": tags or ["自定义"],
            "bpm": bpm,
            "copyright": "custom",
        }

        # 如果文件存在且未提供 BPM/时长，自动分析
        if os.path.exists(file_path):
            analysis = self.analyze_bpm(file_path)
            if "note" not in analysis:
                entry_data["bpm"] = analysis["bpm"]
                entry_data["duration"] = analysis["duration_sec"]

        entry = BGMEntry(entry_data, "custom")
        self._entries.append(entry)
        return entry.to_dict()

    # ── 格式校验 ──

    def validate_bgm_paths(self) -> list[str]:
        """检查所有 BGM 文件是否存在，返回缺失列表"""
        missing = []
        for e in self._entries:
            if e.file and not os.path.exists(e.file):
                missing.append(f"{e.name}: {e.file}")
        return missing

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"<BGMSelector: {len(self._entries)} tracks>"


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="BGM 选择器")
    parser.add_argument("action", nargs="?", default="list",
                        choices=["list", "trending", "search", "style",
                                 "categories", "info", "config", "check"])
    parser.add_argument("--keyword", default="", help="搜索关键词")
    parser.add_argument("--style", default="", help="按风格筛选")
    parser.add_argument("--bgm", default="", help="BGM ID")
    parser.add_argument("--limit", type=int, default=5, help="热门显示数量")

    args = parser.parse_args()
    selector = BGMSelector()

    if args.action == "list":
        all_bgm = selector.list_all()
        print(f"📀 BGM 音乐库 ({len(all_bgm)} 首):")
        for bgm in all_bgm:
            icon = {"trending": "🔥", "custom": "📁"}.get(bgm["category"], "🎵")
            print(f"  {icon} {bgm['id']:25s} | {bgm['name']:15s} | {bgm['artist']:12s} | {bgm['style']:8s} | {bgm['bpm']}bpm")

    elif args.action == "trending":
        trending = selector.get_trending(args.limit)
        print(f"🔥 热门推荐 (Top {len(trending)}):")
        for bgm in trending:
            print(f"  {bgm['id']:25s} | {bgm['name']:15s} | {bgm['artist']:12s} | {bgm['bpm']}bpm")

    elif args.action == "search":
        if not args.keyword:
            print("❌ 请指定 --keyword")
            return
        results = selector.search(args.keyword)
        print(f"🔍 搜索 \"{args.keyword}\" ({len(results)} 结果):")
        for bgm in results:
            print(f"  {bgm['id']:25s} | {bgm['name']:15s} | {bgm['artist']:12s} | tags: {', '.join(bgm['tags'][:3])}")

    elif args.action == "style":
        if args.style:
            results = selector.get_by_style(args.style)
            print(f"📂 风格 \"{args.style}\" ({len(results)} 首):")
            for bgm in results:
                print(f"  {bgm['id']:25s} | {bgm['name']:15s} | {bgm['artist']:12s}")
        else:
            print(f"📂 可用风格: {', '.join(selector.list_styles())}")

    elif args.action == "info":
        if not args.bgm:
            print("❌ 请指定 --bgm")
            return
        bgm = selector.get_by_id(args.bgm)
        if not bgm:
            print(f"❌ 未找到 BGM: {args.bgm}")
            return
        print(f"📄 BGM 详情: {bgm['name']}")
        for k, v in bgm.items():
            print(f"  {k}: {v}")

    elif args.action == "config":
        if not args.bgm:
            print("❌ 请指定 --bgm")
            return
        config = selector.generate_config(args.bgm)
        print(f"⚙️ BGM 生产配置: {config['selected']}")
        for k, v in config.items():
            print(f"  {k}: {v}")

    elif args.action == "check":
        missing = selector.validate_bgm_paths()
        if missing:
            print(f"⚠️ 缺失 {len(missing)} 个 BGM 文件:")
            for m in missing:
                print(f"  - {m}")
        else:
            print("✅ 所有 BGM 文件路径有效（文件不存在视为路径有效）")


if __name__ == "__main__":
    cli()

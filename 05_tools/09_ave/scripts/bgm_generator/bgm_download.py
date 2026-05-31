#!/usr/bin/env python3
"""
AVE BGM 音乐库助手 v1.0
下载 Pixabay Music 免费可商用 BGM 到本地库

用法:
  python bgm_download.py search --mood calm
  python bgm_download.py list
  python bgm_download.py scan    # 扫描已下载文件更新 library.json
  python bgm_download.py import --file /path/to/music.mp3 --mood happy

注意:
  Pixabay Music 没有公开 API，本脚本提供两种方式添加音乐:
  1. 打开 https://pixabay.com/music/ 手动下载 → 放到对应情绪目录
  2. 运行 scan 自动扫描目录更新 library.json
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))

from lib.logger import get_logger

logger = get_logger("bgm_lib")

# ── 常量 ──
LIBRARY_DIR = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "ave" / "cache" / "bgm_library"
LIBRARY_CONFIG = LIBRARY_DIR / "library.json"

MOODS = ["calm", "soothing", "happy", "excited", "sad", "mystery",
         "professional", "funny", "inspiring", "normal"]


def main():
    setup()
    parser = argparse.ArgumentParser(description="BGM 音乐库助手")
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    sub.add_parser("list", help="列出库中所有音乐")

    # scan
    sub.add_parser("scan", help="扫描文件系统更新 library.json")

    # search (open browser)
    p_search = sub.add_parser("search", help="打开浏览器搜索指定情绪的 BGM")
    p_search.add_argument("--mood", default="calm", choices=MOODS, help="情绪")

    # import
    p_import = sub.add_parser("import", help="手动导入一个音乐文件")
    p_import.add_argument("--file", required=True, help="音乐文件路径")
    p_import.add_argument("--mood", required=True, choices=MOODS, help="情绪分类")
    p_import.add_argument("--title", default="", help="曲目标题")
    p_import.add_argument("--source", default="manual", help="来源")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list()
    elif args.command == "scan":
        cmd_scan()
    elif args.command == "search":
        cmd_search(args.mood)
    elif args.command == "import":
        cmd_import(args.file, args.mood, args.title, args.source)
    else:
        parser.print_help()


def setup():
    """确保目录结构存在"""
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    for m in MOODS:
        (LIBRARY_DIR / m).mkdir(parents=True, exist_ok=True)
    if not LIBRARY_CONFIG.exists():
        logger.info("初始化 library.json")
        cfg = {"库": {m: {"曲目": [], "说明": ""} for m in MOODS}}
        cfg["基础路径"] = str(LIBRARY_DIR)
        cfg["版本"] = "v1.0"
        with open(LIBRARY_CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)


def cmd_list():
    """列出所有已导入的音乐"""
    cfg = load_config()
    total = 0
    for mood in MOODS:
        tracks = cfg.get("库", {}).get(mood, {}).get("曲目", [])
        valid = [t for t in tracks if t.get("文件名")]
        if valid:
            print(f"\n  [{mood}] ({len(valid)} 首)")
            for t in valid:
                fname = t.get("文件名", "?")
                title = t.get("标题", fname)
                duration = t.get("时长", 0)
                print(f"    {title:30s}  {duration:4.1f}s  {fname}")
            total += len(valid)
    print(f"\n  共 {total} 首 BGM")


def cmd_scan():
    """扫描目录更新 library.json"""
    cfg = load_config()
    new_count = 0
    for mood in MOODS:
        mood_dir = LIBRARY_DIR / mood
        if not mood_dir.exists():
            continue
        existing = {t.get("文件名") for t in cfg["库"][mood]["曲目"]}
        for f in sorted(mood_dir.iterdir()):
            if f.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg", ".flac"):
                if f.name not in existing:
                    duration = get_duration(str(f))
                    cfg["库"][mood]["曲目"].append({
                        "文件名": f.name,
                        "标题": f.stem,
                        "时长": duration,
                        "源": "scan_import",
                    })
                    new_count += 1
                    print(f"  ✅ 新增 [{mood}] {f.name} ({duration:.1f}s)")

    save_config(cfg)
    print(f"\n扫描完成，新增 {new_count} 首")


def cmd_search(mood: str):
    """打开浏览器搜索 Pixabay Music"""
    urls = {
        "calm": "https://pixabay.com/music/search/calm/",
        "soothing": "https://pixabay.com/music/search/relaxing/",
        "happy": "https://pixabay.com/music/search/upbeat/",
        "excited": "https://pixabay.com/music/search/energetic/",
        "sad": "https://pixabay.com/music/search/sad/",
        "mystery": "https://pixabay.com/music/search/cinematic/",
        "professional": "https://pixabay.com/music/search/corporate/",
        "funny": "https://pixabay.com/music/search/playful/",
        "inspiring": "https://pixabay.com/music/search/inspiring/",
        "normal": "https://pixabay.com/music/search/background/",
    }
    url = urls.get(mood, urls["normal"])
    print(f"  打开浏览器: {url}")
    print(f"  操作: 试听 → 免费下载 → 放入 bgm_library/{mood}/ 目录")
    print(f"  然后运行: python bgm_download.py scan 自动入库")
    subprocess.run(["open", url])


def cmd_import(file_path: str, mood: str, title: str, source: str):
    """导入一个音乐文件"""
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return

    dest = LIBRARY_DIR / mood / os.path.basename(file_path)
    if os.path.exists(dest):
        logger.warning(f"文件已存在: {dest}")
        return

    import shutil
    shutil.copy2(file_path, dest)
    duration = get_duration(str(dest))

    cfg = load_config()
    cfg["库"][mood]["曲目"].append({
        "文件名": dest.name,
        "标题": title or dest.stem,
        "时长": duration,
        "源": source,
    })
    save_config(cfg)
    print(f"✅ 导入完成: {dest.name} ({duration:.1f}s) → [{mood}]")


def get_duration(file_path: str) -> float:
    """用 ffprobe 获取音频时长"""
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path,
        ], capture_output=True, text=True, timeout=15)
        return round(float(result.stdout.strip()), 1)
    except Exception:
        return 30.0


def load_config() -> dict:
    if LIBRARY_CONFIG.exists():
        with open(LIBRARY_CONFIG, encoding="utf-8") as f:
            return json.load(f)
    return {"库": {}}


def save_config(cfg: dict):
    with open(LIBRARY_CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

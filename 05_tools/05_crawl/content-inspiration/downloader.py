"""
口播素材系统 - 媒体下载脚本
用法：python downloader.py [--limit N] [--all]

功能：
  1. 查询所有 download_status='pending' 的素材
  2. 使用 yt-dlp 下载视频/音频
  3. 保存到 ~/workbuddy-agent-os/agent-local/materials/video/ 或 audio/
  4. 更新数据库中的 local_files 和 download_status

前置条件：
  - yt-dlp 已安装：pip install yt-dlp
  - ffmpeg 已安装（音频提取需要）

注意：
  - 抖音/小红书链接有时效性，采集后尽快下载
  - 下载速率限制默认 1MB/s，防止 IP 封禁
"""

import os
import sys
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_config, get_db, init_db, setup_logger, truncate_text, PROJECT_ROOT


def download_one(material: dict, config: dict, logger) -> dict:
    """
    下载单条素材的视频/音频

    返回：{"video": "path", "audio": "path"} 或 None
    """
    url = material.get("url", "")
    if not url:
        logger.warning(f"素材 {material['id']} 无 URL，跳过")
        return None
    
    try:
        from yt_dlp import YoutubeDL
    except ImportError:
        logger.error("yt-dlp 未安装，请执行：pip install yt-dlp")
        return None
    
    platform = material["platform"]
    title = material.get("title", "untitled")
    author = material.get("author", "unknown")
    
    # 确定输出路径
    media_dir = os.path.expanduser(config["storage"].get("media_dir", "~/workbuddy-agent-os/agent-local/materials/video"))
    os.makedirs(media_dir, exist_ok=True)
    
    # 文件名
    safe_title = truncate_text(title, 20)
    safe_author = truncate_text(author, 15)
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{platform}_{safe_author}_{safe_title}_{date_str}"
    
    outtmpl = os.path.join(media_dir, filename + ".%(ext)s")
    
    # yt-dlp 配置
    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "best[ext=mp4]/best",  # 优先 mp4
        "max_filesize": 500 * 1024 * 1024,  # 500MB 上限
        "retries": config["download"].get("retries", 3),
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        # 速率限制
        "ratelimit": 1024 * 1024,  # 1MB/s
    }
    
    result_files = {"video": None, "audio": None}
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if info:
                downloaded_file = ydl.prepare_filename(info)
                # yt-dlp 可能修改了扩展名
                if os.path.exists(downloaded_file):
                    result_files["video"] = downloaded_file
                    logger.info(f"下载成功: {os.path.basename(downloaded_file)}")
                else:
                    # 查找实际下载的文件
                    for ext in ["mp4", "flv", "webm", "mkv"]:
                        candidate = os.path.join(media_dir, f"{filename}.{ext}")
                        if os.path.exists(candidate):
                            result_files["video"] = candidate
                            break
        
        return result_files if result_files["video"] else None
        
    except Exception as e:
        logger.error(f"下载失败 [{material['id']}]: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="口播素材媒体下载")
    parser.add_argument("--limit", "-n", type=int, default=0, help="下载数量上限，0=全部")
    parser.add_argument("--all", action="store_true", help="下载所有 worth_downloading=yes 的素材")
    parser.add_argument("--url", "-u", help="手动指定 URL 下载（不查数据库）")
    args = parser.parse_args()
    
    config = load_config()
    logger = setup_logger("download")
    
    db_path = init_db()
    db = get_db(db_path)
    
    if args.url:
        # 手动 URL 下载
        material = {
            "id": 0,
            "url": args.url,
            "platform": "manual",
            "title": "手动下载",
            "author": "manual",
        }
        result = download_one(material, config, logger)
        if result:
            print(f"[OK] 下载完成: {result}")
        else:
            print("[FAIL] 下载失败")
        db.close()
        return
    
    # 查询待下载记录
    if args.all:
        # 下载所有 AI 推荐的
        query = """
            SELECT m.* FROM materials m
            JOIN analysis a ON m.id = a.material_id
            WHERE a.worth_downloading = 'yes' AND m.download_status = 'none'
        """
    else:
        query = "SELECT * FROM materials WHERE download_status = 'pending'"
    
    if args.limit > 0:
        query += f" LIMIT {args.limit}"
    
    materials = db.execute(query).fetchall()
    materials = [dict(m) for m in materials]
    
    if not materials:
        print("[OK] 没有待下载的素材")
        db.close()
        return
    
    print(f"[INFO] 待下载: {len(materials)} 条")
    
    success = 0
    failed = 0
    
    for i, material in enumerate(materials, 1):
        print(f"[{i}/{len(materials)}] 下载: {material['title'][:40]}")
        
        # 标记为下载中
        db.execute("UPDATE materials SET download_status = 'downloading' WHERE id = ?", (material["id"],))
        db.commit()
        
        result = download_one(material, config, logger)
        
        if result and result.get("video"):
            db.execute("""
                UPDATE materials 
                SET download_status = 'done', local_files = ?
                WHERE id = ?
            """, (json.dumps(result, ensure_ascii=False), material["id"]))
            db.commit()
            success += 1
        else:
            db.execute("UPDATE materials SET download_status = 'failed' WHERE id = ?", (material["id"],))
            db.commit()
            failed += 1
    
    db.close()
    print(f"\n[DONE] 下载完成: 成功 {success}, 失败 {failed}, 共 {len(materials)} 条")


if __name__ == "__main__":
    main()

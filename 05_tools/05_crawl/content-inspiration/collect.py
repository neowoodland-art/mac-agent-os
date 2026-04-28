"""
口播素材系统 - 采集脚本
用法：python collect.py [--platform xiaohongshu] [--keyword "关键词"]

功能：
  1. 读取 config.yaml 中的平台和关键词配置
  2. 调用 MediaCrawler 抓取内容元数据
  3. 去重后写入 JSONL 文件和 SQLite 数据库

前置条件：
  - MediaCrawler 已安装到 config.yaml 中 crawler.project_path 指定的目录
  - 对应平台的 Cookie 已配置（参见 MediaCrawler 文档）
"""

import os
import sys
import json
import argparse
from datetime import datetime

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_config, get_db, init_db, setup_logger, parse_jsonl, save_jsonl, PROJECT_ROOT


def collect_by_mediacrawler(platform: str, keyword: str, max_count: int, config: dict, logger) -> list[dict]:
    """
    通过 MediaCrawler 采集内容
    
    参数：
        platform: 平台名称（xiaohongshu / douyin / bilibili）
        keyword: 搜索关键词
        max_count: 最大采集数
        config: 配置字典
        logger: 日志器
    
    返回：
        采集到的内容列表
    """
    crawler_path = config["crawler"].get("project_path", "")
    if not crawler_path:
        logger.error("MediaCrawler 项目路径未配置，请设置 config.yaml 中 crawler.project_path")
        logger.error("安装方式：cd ~/agent-os/05_tools/05_crawl && git clone https://github.com/NanmiCoder/MediaCrawler.git")
        return []
    
    crawler_path = os.path.expanduser(crawler_path)
    if not os.path.exists(crawler_path):
        logger.error(f"MediaCrawler 项目不存在: {crawler_path}")
        return []
    
    import subprocess
    
    # MediaCrawler CLI 参数映射
    platform_map = {
        "xiaohongshu": "xhs",
        "douyin": "dy",
        "bilibili": "bili",
    }
    
    short_name = platform_map.get(platform, platform)
    
    logger.info(f"开始采集: 平台={platform}, 关键词={keyword}, 最大数量={max_count}")
    
    # 构建 MediaCrawler 命令
    cmd = [
        sys.executable,
        os.path.join(crawler_path, "main.py"),
        "--platform", short_name,
        "--lt", "qrcode",       # 登录类型：扫码
        "--type", "search",
        "--keywords", keyword,
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5分钟超时
            cwd=crawler_path,
        )
        
        if result.returncode != 0:
            logger.error(f"MediaCrawler 执行失败: {result.stderr[:500]}")
            return []
        
        # 解析输出（MediaCrawler 的输出格式需要根据实际版本调整）
        # 通常结果会保存在 MediaCrawler 自己的输出目录中
        output_dir = os.path.join(crawler_path, "output")
        records = []
        
        if os.path.exists(output_dir):
            for f in os.listdir(output_dir):
                if f.endswith(".json"):
                    with open(os.path.join(output_dir, f), "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                        if isinstance(data, list):
                            records.extend(data[:max_count])
                        elif isinstance(data, dict):
                            records.append(data)
        
        logger.info(f"采集完成: 获得 {len(records)} 条记录")
        return records
        
    except subprocess.TimeoutExpired:
        logger.error("采集超时（5分钟）")
        return []
    except Exception as e:
        logger.error(f"采集异常: {e}")
        return []


def normalize_record(record: dict, platform: str) -> dict:
    """
    将 MediaCrawler 的原始数据规范化为统一格式
    不同平台的字段名不同，这里做统一映射
    """
    # 根据平台映射字段（需要根据实际 MediaCrawler 输出调整）
    platform_fields = {
        "xiaohongshu": {
            "original_id": "note_id",
            "title": "title",
            "description": "desc",
            "author": "nickname",
            "author_id": "user_id",
            "cover_url": "image_list",
            "music_name": "music_name",
            "like_count": "liked_count",
            "collect_count": "collected_count",
            "comment_count": "comment_count",
            "share_count": "share_count",
        },
        "douyin": {
            "original_id": "aweme_id",
            "title": "desc",
            "description": "desc",
            "author": "nickname",
            "author_id": "uid",
            "cover_url": "video_cover",
            "music_name": "music_name",
            "like_count": "digg_count",
            "collect_count": "collect_count",
            "comment_count": "comment_count",
            "share_count": "share_count",
        },
        "bilibili": {
            "original_id": "bvid",
            "title": "title",
            "description": "description",
            "author": "author",
            "author_id": "mid",
            "cover_url": "pic",
            "music_name": "",
            "like_count": "like",
            "collect_count": "favorite",
            "comment_count": "comment",
            "share_count": "share",
        },
    }
    
    fields = platform_fields.get(platform, platform_fields["xiaohongshu"])
    
    normalized = {"platform": platform}
    
    for target_key, source_key in fields.items():
        value = record.get(source_key, "")
        if isinstance(value, list):
            value = value[0] if value else ""
        normalized[target_key] = value
    
    # 补充 URL
    url_map = {
        "xiaohongshu": f"https://www.xiaohongshu.com/explore/{normalized.get('original_id', '')}",
        "douyin": f"https://www.douyin.com/video/{normalized.get('original_id', '')}",
        "bilibili": f"https://www.bilibili.com/video/{normalized.get('original_id', '')}",
    }
    normalized["url"] = url_map.get(platform, "")
    
    return normalized


def save_to_db(records: list[dict], db, logger):
    """将采集记录写入数据库（去重）"""
    inserted = 0
    skipped = 0
    for rec in records:
        try:
            # 检查是否已存在
            existing = db.execute(
                "SELECT id FROM materials WHERE platform=? AND original_id=?",
                (rec["platform"], rec["original_id"])
            ).fetchone()
            if existing:
                skipped += 1
                continue
            
            db.execute("""
                INSERT INTO materials (platform, original_id, url, title, description,
                    author, author_id, cover_url, music_name, like_count, collect_count,
                    comment_count, share_count, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec["platform"], rec["original_id"], rec.get("url"),
                rec.get("title", ""), rec.get("description", ""),
                rec.get("author", ""), rec.get("author_id", ""),
                rec.get("cover_url", ""), rec.get("music_name", ""),
                rec.get("like_count", 0), rec.get("collect_count", 0),
                rec.get("comment_count", 0), rec.get("share_count", 0),
                json.dumps(rec, ensure_ascii=False)
            ))
            inserted += 1
        except Exception as e:
            logger.error(f"写入失败 [{rec.get('original_id', '?')}]: {e}")
    
    db.commit()
    logger.info(f"写入数据库: 新增 {inserted} 条, 跳过重复 {skipped} 条")
    return inserted


def main():
    parser = argparse.ArgumentParser(description="口播素材采集")
    parser.add_argument("--platform", "-p", help="采集平台（xiaohongshu/douyin/bilibili）")
    parser.add_argument("--keyword", "-k", help="搜索关键词")
    parser.add_argument("--count", "-n", type=int, help="采集数量上限")
    parser.add_argument("--init-db", action="store_true", help="仅初始化数据库")
    args = parser.parse_args()
    
    config = load_config()
    logger = setup_logger("collect")
    
    # 初始化数据库
    db_path = init_db()
    logger.info(f"数据库: {db_path}")
    
    if args.init_db:
        print("[OK] 数据库初始化完成")
        return
    
    db = get_db(db_path)
    
    # 确定采集参数
    platforms = [args.platform] if args.platform else config.get("platforms", ["xiaohongshu"])
    keywords = [args.keyword] if args.keyword else config.get("keywords", [])
    max_count = args.count if args.count else config.get("max_count", 20)
    
    if not keywords:
        logger.error("未指定关键词，请在 config.yaml 中配置或通过 --keyword 参数传入")
        return
    
    total_inserted = 0
    
    for platform in platforms:
        for keyword in keywords:
            # 采集
            records = collect_by_mediacrawler(platform, keyword, max_count, config, logger)
            
            if not records:
                logger.info(f"无数据: {platform}/{keyword}")
                continue
            
            # 规范化
            normalized = [normalize_record(r, platform) for r in records]
            
            # 保存 JSONL
            date_str = datetime.now().strftime("%Y-%m-%d")
            raw_dir = config["storage"].get("raw_dir", "data/raw")
            if not os.path.isabs(raw_dir):
                raw_dir = str(PROJECT_ROOT / raw_dir)
            jsonl_path = os.path.join(raw_dir, f"{date_str}_{platform}_{keyword}.jsonl")
            save_jsonl(normalized, jsonl_path)
            logger.info(f"JSONL 已保存: {jsonl_path}")
            
            # 写入数据库
            inserted = save_to_db(normalized, db, logger)
            total_inserted += inserted
    
    db.close()
    print(f"\n[DONE] 采集完成，共新增 {total_inserted} 条素材")


if __name__ == "__main__":
    main()

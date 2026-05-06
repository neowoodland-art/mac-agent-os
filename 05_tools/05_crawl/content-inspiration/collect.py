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
        logger.error("安装方式：cd ~/workbuddy-agent-os/agent-sync/05_tools/05_crawl && git clone https://github.com/NanmiCoder/MediaCrawler.git")
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


def search_web(keyword: str, platform: str = "douyin", max_results: int = 15) -> list[dict]:
    """
    搜索平台内容，只返回元数据（不下载任何文件）
    使用 httpx 直接请求 + 移动端伪装，不经过浏览器。
    
    Args:
        keyword: 搜索关键词
        platform: douyin / xiaohongshu / zhihu / baidu
        max_results: 最大返回条数
    
    Returns:
        [{url, title, author, brief, platform}, ...]
    """
    import re, json
    
    try:
        import httpx
    except ImportError:
        print("[WARN] httpx 未安装，回退到 agent-browser")
        return _search_agent_browser(keyword, platform, max_results)
    
    # 移动端伪装头
    mobile_headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.baidu.com/",
    }
    
    search_configs = {
        "douyin": {
            "url": f"https://www.douyin.com/search/{keyword}?type=general",
            "mobile_ua": True,
            "parser": "douyin_json",
        },
        "xiaohongshu": {
            "url": f"https://www.xiaohongshu.com/search_result?keyword={keyword}",
            "mobile_ua": False,
            "parser": "xhs_html",
        },
        "zhihu": {
            "url": f"https://www.zhihu.com/search?type=content&q={keyword}",
            "mobile_ua": True,
            "parser": "zhihu_html",
        },
        "baidu": {
            "url": f"https://www.baidu.com/s?wd={keyword}&ie=utf-8",
            "mobile_ua": False,
            "parser": "baidu_html",
        },
    }
    
    cfg = search_configs.get(platform, search_configs["douyin"])
    url = cfg["url"]
    
    headers = mobile_headers.copy()
    if cfg.get("mobile_ua"):
        headers["User-Agent"] = mobile_headers["User-Agent"]
    else:
        headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    try:
        resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=15)
        html = resp.text
    except Exception as e:
        print(f"[WARN] httpx 请求失败 ({e})，回退到 agent-browser")
        return _search_agent_browser(keyword, platform, max_results)
    
    results = []
    parser = cfg["parser"]
    
    if parser == "douyin_json":
        # 抖音：尝试找 JSON 数据
        json_match = re.search(r'window\._ROUTER_DATA\s*=\s*({.*?});', html, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                # 遍历找到视频列表
                def _extract(obj, depth=0):
                    items = []
                    if depth > 5:
                        return items
                    if isinstance(obj, dict):
                        if obj.get("type") == "video" and obj.get("aweme_id"):
                            items.append({
                                "url": f"https://www.douyin.com/video/{obj['aweme_id']}",
                                "title": (obj.get("desc") or obj.get("title") or "")[:40],
                                "author": (obj.get("author_info", {}) or {}).get("nickname", ""),
                                "brief": "",
                                "platform": "douyin",
                            })
                        for v in obj.values():
                            items.extend(_extract(v, depth + 1))
                    elif isinstance(obj, list):
                        for v in obj:
                            items.extend(_extract(v, depth + 1))
                    return items
                results = _extract(data)
            except:
                pass
        
        if not results:
            # 备用：正则提取链接+标题
            links = re.findall(r'https?://[^\s"\'<>]*(?:douyin\.com/video/\d+)[^\s"\'<>]*', html)
            texts = re.findall(r'[\u4e00-\u9fff]{8,}', html)
            texts = [t for t in texts if not any(kw in t for kw in ['登录','下载','关注','点赞','协议','评论','分享'])]
            seen = set()
            for i, link in enumerate(links):
                clean = link.split('?')[0]
                if clean not in seen:
                    seen.add(clean)
                    results.append({
                        "url": clean,
                        "title": texts[len(results)] if len(results) < len(texts) else keyword,
                        "author": "", "brief": "", "platform": "douyin",
                    })
                    if len(results) >= max_results:
                        break
    
    elif parser == "xhs_html":
        # 小红书：提取笔记链接 + 文本
        links = re.findall(r'https?://[^\s"\'<>]*(?:xiaohongshu\.com/explore/[^?&\s<>]+)', html)
        texts = re.findall(r'[\u4e00-\u9fff]{10,}', html)
        texts = [t for t in texts if not any(kw in t for kw in ['登录','下载','关注','点赞','注册','手机','验证码'])]
        seen = set()
        for i, link in enumerate(links[:max_results]):
            clean = link.split('?')[0] if '?' in link else link
            if clean not in seen:
                seen.add(clean)
                results.append({
                    "url": clean,
                    "title": texts[len(results)] if len(results) < len(texts) else keyword,
                    "author": "", "brief": "", "platform": "xiaohongshu",
                })
    
    elif parser == "zhihu_html":
        links = re.findall(r'https?://[^\s"\'<>]*(?:zhihu\.com/question/\d+|zhihu\.com/answer/\d+|zhihu\.com/zvideo/\d+)[^\s"\'<>]*', html)
        texts = re.findall(r'[\u4e00-\u9fff]{10,}', html)
        texts = [t for t in texts if not any(kw in t for kw in ['登录','下载','关注','赞同','评论','手机','验证码'])]
        seen = set()
        for i, link in enumerate(links[:max_results]):
            clean = link.split('?')[0]
            if clean not in seen:
                seen.add(clean)
                results.append({
                    "url": clean,
                    "title": texts[len(results)] if len(results) < len(texts) else keyword,
                    "author": "", "brief": "", "platform": "zhihu",
                })
    
    elif parser == "baidu_html":
        # 百度搜索：提取搜索结果
        items = re.findall(r'<div[^>]*class="[^"]*result[^"]*"[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
        if not items:
            # 通用提取
            links = re.findall(r'https?://[^\s"\'<>]+', html)
            titles = re.findall(r'[\u4e00-\u9fff]{10,}', html)
            titles = [t for t in titles if not any(kw in t for kw in ['登录','下载','注册','百度'])]
            for i, t in enumerate(titles[:max_results]):
                results.append({
                    "url": links[i] if i < len(links) else "",
                    "title": t[:40], "author": "", "brief": "", "platform": "baidu",
                })
        else:
            for href, title in items[:max_results]:
                results.append({
                    "url": href, "title": re.sub(r'<[^>]+>', '', title).strip()[:40],
                    "author": "", "brief": "", "platform": "baidu",
                })
    
    return results[:max_results]


def _search_agent_browser(keyword: str, platform: str, max_results: int) -> list[dict]:
    """回退方案：使用 agent-browser（保留原有逻辑）"""
    import subprocess, re, shutil, time
    
    npx = shutil.which("npx", path="/Users/chengzige/.workbuddy/binaries/node/versions/22.12.0/bin:/usr/bin:/bin")
    if not npx:
        return []
    
    search_urls = {
        "douyin": f"https://www.douyin.com/search/{keyword}?type=general",
        "zhihu": f"https://www.zhihu.com/search?type=content&q={keyword}",
    }
    url = search_urls.get(platform, search_urls.get("douyin", ""))
    if not url:
        return []
    
    env = os.environ.copy()
    for k in ["HTTP_PROXY", "HTTPS_PROXY"]:
        env.pop(k, None)
    env.pop("NODE_OPTIONS", None)
    
    try:
        subprocess.run([npx, "agent-browser", "open", url], env=env, capture_output=True, timeout=25)
        time.sleep(3)
        r = subprocess.run([npx, "agent-browser", "snapshot"], env=env, capture_output=True, timeout=15, text=True)
        subprocess.run([npx, "agent-browser", "close"], env=env, capture_output=True, timeout=8)
        
        html = r.stdout
        links = re.findall(r'https?://[^\s"\'<>]*(?:video/\d+|\?q=)[^\s"\'<>]*', html)
        texts = re.findall(r'[\u4e00-\u9fff]{8,}', html)
        texts = [t for t in texts if not any(kw in t for kw in ['登录','下载','关注','点赞'])]
        
        results = []
        seen = set()
        for i, link in enumerate(links[:max_results]):
            clean = link.split('?')[0]
            if clean not in seen:
                seen.add(clean)
                results.append({
                    "url": clean,
                    "title": texts[len(results)] if len(results) < len(texts) else keyword,
                    "author": "", "brief": "", "platform": platform,
                })
        return results
    except:
        return []


if __name__ == "__main__":
    main()

"""

AVE 05_material_producer/pexels — Pexels 素材搜索 v1.1

API 文档: https://www.pexels.com/api/documentation/
版本: v1.1 | 更新: 2026-05-06

改进:
  - 中文→英文关键词自动映射 (70+ 常用词)
  - 多关键词回落搜索 (最多 3 轮)
  - portrait/landscape 自适应筛选
  - 优先选取竖屏高质量视频

用法:
  search_videos("sunset beach", count=3, api_key="xxx")
    → 返回下载后的本地文件路径列表

回落策略:
  1. 精确搜索 (按 query)
  2. 简化关键词搜索 (去掉形容词/场景词)
  3. 核心词搜索 (保留名词/动词)
  4. 返回空列表 (由 caller 用 fallback 兜底)
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib
import os
import time
from pathlib import Path
from typing import Optional

import httpx

from lib.logger import get_logger

logger = get_logger("pexels")

PEXELS_BASE = "https://api.pexels.com/videos"
CACHE_DIR = (
    Path(os.environ.get("AVE_CACHE_DIR",
        str(Path.home() / "workbuddy-agent-os/agent-local/tools/ave/cache/materials")))
)

# ── 中文→英文关键词映射 ────────────────────────────────────
ZH_TO_EN = {
    "猫": "cat", "狗狗": "dog", "狗": "dog", "猫咪": "cat",
    "日出": "sunrise", "日落": "sunset",
    "大海": "ocean", "沙滩": "beach", "海滩": "beach",
    "森林": "forest", "树木": "trees", "绿叶": "green leaves",
    "河流": "river", "湖泊": "lake", "山川": "mountains",
    "星空": "night sky stars", "银河": "milky way",
    "城市": "city", "夜景": "city night", "街道": "city street",
    "雪山": "snow mountain", "云海": "clouds mountain",
    "瀑布": "waterfall", "彩虹": "rainbow",
    "花海": "flower field", "樱花": "cherry blossoms",
    "草原": "meadow", "草地": "grass field",
    "海浪": "ocean waves", "雨滴": "rain drops",
    "美食": "food cooking", "咖啡": "coffee cafe",
    "书本": "books reading", "写字": "writing pen",
    "瑜伽": "yoga meditation", "冥想": "meditation calm",
    "跑步": "running jogging", "健身": "fitness gym",
    "舞蹈": "dancing", "弹琴": "piano playing",
    "茶道": "tea ceremony", "书法": "calligraphy",
    "太极": "tai chi", "武术": "martial arts",
    "烟花": "fireworks", "灯笼": "lanterns",
    "古镇": "traditional town", "寺庙": "temple",
    "海岛": "tropical island", "椰子树": "palm tree beach",
    "汽车": "driving car", "火车": "train railway",
    "飞机": "airplane sky", "轮船": "sailing ship",
    "建筑": "architecture building", "桥梁": "bridge",
    "天空": "sky clouds", "白云": "white clouds",
    "下雨": "rain falling", "下雪": "snow falling",
    "春天": "spring nature", "夏天": "summer sunny",
    "秋天": "autumn leaves", "冬天": "winter snow",
    "工作": "office work", "开会": "meeting business",
    "微笑": "smiling happy", "牵手": "couple holding hands",
    "小孩": "child playing", "老人": "elderly portrait",
    "情侣": "couple romantic", "家庭": "family together",
    "宠物": "pet dog cat", "小鸟": "bird flying",
    "金鱼": "fish aquarium", "蝴蝶": "butterfly",
    "月亮": "moon night", "阳光": "sunlight",
}


def _translate_query(query: str) -> str:
    """将中文关键词翻译为英文，Pexels 英文搜索更精准"""
    result = query
    for zh, en in ZH_TO_EN.items():
        if zh in result:
            result = result.replace(zh, en)
    return result.strip()


def search_videos(
    query: str,
    count: int = 3,
    api_key: str = "",
    min_duration: int = 5,
    orientation: str = "portrait",
) -> list[dict]:
    """
    搜索并下载 Pexels 视频素材 v1.1

    改进:
      - 自动将中文关键词翻译为英文再搜索
      - 3轮回落搜索策略，提升命中率
      - portrait 模式优先竖屏高质量视频

    参数:
      query: 搜索关键词 (支持中文，自动翻译)
      count: 需要的视频数量
      api_key: Pexels API Key
      min_duration: 最短视频时长(秒)
      orientation: portrait(竖屏) | landscape(横屏) | square

    返回:
      [{"path": "/local/file.mp4", "duration": 15.0, "width": 1080, "height": 1920, "url": "原始链接"}, ...]
    """
    if not api_key:
        logger.error("Pexels API Key 未配置")
        return []

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # 翻译关键词
    en_query = _translate_query(query)
    logger.info(f"搜索关键词: {query!r} → {en_query!r}")

    # 多轮回落搜索
    keywords_to_try = _generate_fallback_keywords(en_query)
    for kw in keywords_to_try:
        videos = _search_api(kw, count * 2, api_key, orientation)
        if videos:
            logger.info(f"  ✅ 命中关键词: {kw} ({len(videos)} 个候选)")
            break
        logger.warning(f"  ⏳ 关键词无结果，回落: {kw}")
    else:
        logger.warning(f"Pexels 所有关键词均无结果: {query}")
        return []

    # 过滤 + 下载
    results = []
    for vid in videos:
        if len(results) >= count:
            break
        duration = vid.get("duration", 0)
        if duration < min_duration:
            continue

        # 取最高分辨率视频文件
        video_files = vid.get("video_files", [])
        best = _pick_best_file(video_files, orientation)
        if not best:
            continue

        local_path = _download(best["link"], api_key, kw)
        if local_path:
            results.append({
                "path": local_path,
                "duration": duration,
                "width": best.get("width", 0),
                "height": best.get("height", 0),
                "url": vid.get("url", ""),
            })

    logger.info(f"Pexels 下载完成: {len(results)}/{count} 个 (原始:{query})")
    return results


def _generate_fallback_keywords(query: str) -> list[str]:
    """生成回落关键词列表，最多3轮"""
    keywords = [query]

    # 第1轮回落: 去掉形容词和场景词，保留核心名词
    # 例如 "sunset beach calm" → "beach sunset" / "beach"
    words = query.split()
    # 去掉常见形容词
    adj_strip = [w for w in words if w.lower() not in (
        "calm", "peaceful", "beautiful", "lovely", "nice", "serene",
        "tranquil", "golden", "warm", "cool", "soft", "bright",
        "dramatic", "mystic", "dreamy", "ethereal", "vibrant",
    )]
    if len(adj_strip) >= 2 and len(keywords) < 2:
        keywords.append(" ".join(adj_strip))
    elif len(adj_strip) >= 1 and len(keywords) < 2:
        keywords.append(adj_strip[0])

    # 第2轮回落: 只保留核心名词
    core = [w for w in words if w.lower() not in (
        "calm", "peaceful", "beautiful", "lovely", "nice", "serene",
        "tranquil", "golden", "warm", "cool", "soft", "bright",
        "dramatic", "mystic", "dreamy", "ethereal", "vibrant",
        "sky", "view", "scene", "footage", "video", "clip",
    )]
    if core and len(keywords) < 3:
        keywords.append(core[0])

    return keywords[:3]


def _search_api(
    query: str, per_page: int, api_key: str, orientation: str
) -> list[dict]:
    """调用 Pexels 搜索 API"""
    params = {
        "query": query,
        "per_page": min(per_page, 80),
        "orientation": orientation,
        "size": "large",
    }
    try:
        resp = httpx.get(
            f"{PEXELS_BASE}/search",
            params=params,
            headers={"Authorization": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("videos", [])
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning("Pexels 速率限制，等待 1 秒重试")
            time.sleep(1)
            return _search_api(query, per_page, api_key, orientation)
        logger.error(f"Pexels 搜索失败 [{e.response.status_code}]: {query}")
        return []
    except Exception as e:
        logger.error(f"Pexels 搜索异常: {e}")
        return []


def _pick_best_file(video_files: list[dict], orientation: str) -> Optional[dict]:
    """选择最佳视频文件 v1.1

    优先策略:
      portrait: 竖屏(9:16) > 接近竖屏 > 横屏中最高质量
      竖屏判定: height > width 且 height >= 720
    """
    if not video_files:
        return None

    def quality_score(f):
        w = f.get("width", 0)
        h = f.get("height", 0)
        file_size = f.get("file_size", 0)
        fps = f.get("fps", 30)

        # 竖屏优先 (height > width 且 h >= 720)
        if orientation == "portrait" and h > w and h >= 720:
            # 竖屏得分: 高度越高越好
            return h * 10 + fps + (file_size // 1024 // 1024)
        elif orientation == "landscape" and w > h and w >= 1280:
            return w * 10 + fps
        elif orientation == "square" and abs(w - h) < max(w, h) * 0.2:
            return min(w, h) * 10
        else:
            # 无匹配时选最高质量
            return max(w, h) * 5

    video_files.sort(key=quality_score, reverse=True)
    chosen = video_files[0]
    logger.debug(f"  选片: {chosen.get('width')}x{chosen.get('height')} @ {chosen.get('fps')}fps")
    return chosen


def _download(url: str, api_key: str, query: str) -> Optional[str]:
    """下载视频文件到本地缓存"""
    # 缓存键: URL 的 hash
    cache_key = hashlib.md5(url.encode()).hexdigest()[:16]
    ext = ".mp4"
    local_path = str(CACHE_DIR / f"{cache_key}{ext}")

    if os.path.exists(local_path):
        logger.debug(f"缓存命中: {local_path}")
        return local_path

    try:
        resp = httpx.get(url, headers={"Authorization": api_key}, timeout=60, follow_redirects=True)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(resp.content)
        logger.info(f"下载完成: {local_path} ({len(resp.content)//1024}KB)")
        return local_path
    except Exception as e:
        logger.warning(f"下载失败: {e}")
        return None

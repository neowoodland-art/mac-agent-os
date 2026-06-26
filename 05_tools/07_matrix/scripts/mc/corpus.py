"""
corpus.py — 评论语料库管理

双平台隔离: 抖音/小红书 各自独立语料
每个平台下分多个分类，含权重、启用状态

文件结构:
  corpus/
  ├── douyin.yaml       ← 抖音语料
  └── xiaohongshu.yaml  ← 小红书语料

YAML 格式:
  version: "1.0"
  categories:
    赞美:
      weight: 30
      enabled: true
      label: "赞美评论"
      comments:
        - "讲得太好了，受益匪浅！"
        - "这个观点很新颖，学习了"
    搞笑:
      weight: 20
      enabled: true
      label: "搞笑评论"
      comments:
        - "笑死我了哈哈哈哈哈"
"""
import asyncio
import json
import logging
import os
import random
import re
from pathlib import Path
from typing import List, Optional

import yaml

log = logging.getLogger(__name__)

TOOL_DIR = Path(__file__).resolve().parent.parent.parent
CORPUS_DIR = TOOL_DIR / "corpus"
CONFIG_DIR = TOOL_DIR / "config"

# 项目根目录（agent-sync/05_tools/.. 的上一层，即 workbuddy-agent-os）
PROJECT_ROOT = TOOL_DIR.parent.parent.parent
PROFILES_PATH = PROJECT_ROOT / "agent-local/tools/matrix/data/profiles.json"

# ── 关键词 → 方向 映射 ──────────────────────────────────────────
KEYWORD_CATEGORY_MAP = [
    (["科技", "数码", "手机"], ["称赞", "提问"]),
    (["美食", "做饭", "菜"], ["称赞", "共鸣"]),
    (["旅游", "风景", "旅行"], ["称赞", "提问"]),
    (["情感", "生活", "感悟"], ["共鸣", "安慰"]),
    (["知识", "科普", "教育"], ["提问", "补充"]),
]

# 方向名称 → 实际分类名称（兼容两个平台已有的分类）
DIRECTION_TO_CATEGORY = {
    "称赞": "赞美",
    "正面": "赞美",
    "提问": "提问",
    "共鸣": "感慨",
    "安慰": "感慨",
    "补充": "客观",
}

# 默认方向标签（用于 fallback）
ALL_DIRECTIONS = list(DIRECTION_TO_CATEGORY.keys())
CORPUS_DIR.mkdir(parents=True, exist_ok=True)

# 默认跨平台通用分类
DEFAULT_DOUYIN_COMMENTS = {
    "赞美": {
        "weight": 30, "enabled": True, "label": "赞美评论",
        "comments": [
            "讲得太好了，受益匪浅！",
            "这个观点很新颖，学习了",
            "说得真是振聋发聩",
            "干货满满，感谢分享",
            "条理清晰，逻辑严密",
            "每一句话都说到了心坎里",
        ],
        "templates": ["关于{keyword}的观点很到位", "感谢分享{keyword}的心得", "说得太好了，{keyword}这部分启发很大"],
    },
    "搞笑": {
        "weight": 20, "enabled": True, "label": "搞笑评论",
        "comments": ["哈哈哈哈哈笑死", "有才，这评论比视频还精彩", "笑不活了家人们", "你要把我笑死"],
        "templates": ["{keyword}这个梗笑死我了", "哈哈哈哈{keyword}太有才了"],
    },
    "客观": {
        "weight": 15, "enabled": True, "label": "客观评价",
        "comments": ["比较客观", "抛开立场看，说得有道理", "中肯的评价", "理性分析，值得一读"],
        "templates": ["关于{keyword}的分析很客观", "理性的声音，{keyword}这部分说得好"],
    },
    "提问": {
        "weight": 10, "enabled": True, "label": "提问互动",
        "comments": ["请问这是在哪里？", "能分享一下具体方法吗？", "新手想问一下怎么入门", "这个需要什么工具？"],
        "templates": ["{keyword}具体怎么操作？", "能详细讲讲{keyword}吗？"],
    },
    "感慨": {
        "weight": 10, "enabled": True, "label": "生活感慨",
        "comments": ["生活不易，且行且珍惜", "每个人都有自己的故事", "看得我热泪盈眶", "这就是生活啊"],
        "templates": ["看到{keyword}想起了自己", "{keyword}真的太真实了"],
    },
}

# 小红书专属分类
DEFAULT_XHS_COMMENTS = {
    "穿搭": {
        "weight": 25, "enabled": True, "label": "穿搭评论",
        "comments": ["这套搭配好好看！", "求链接！", "色系搭配太舒服了", "超有气质", "这个风格很适合你"],
        "templates": ["{keyword}这套太好看了", "求{keyword}的链接"],
    },
    "美妆": {
        "weight": 20, "enabled": True, "label": "美妆评论",
        "comments": ["这个妆面好干净", "求粉底色号", "口红颜色太美了", "教程很详细，收藏了"],
        "templates": ["{keyword}这个妆容好干净", "{keyword}是什么色号"],
    },
    "种草": {
        "weight": 20, "enabled": True, "label": "种草评论",
        "comments": ["种草了！", "我也买了同款，真的不错", "已加购物车", "求推荐更多好物"],
        "templates": ["被{keyword}种草了", "{keyword}已加入清单"],
    },
    "美食": {
        "weight": 15, "enabled": True, "label": "美食评论",
        "comments": ["看着好好吃", "求地址", "收藏了，周末去试试", "这个做法很简单，明天就试"],
        "templates": ["{keyword}看着好好吃", "求{keyword}的店名"],
    },
    "家居": {
        "weight": 10, "enabled": True, "label": "家居评论",
        "comments": ["布置得好温馨", "求家具链接", "这个风格好喜欢", "家的感觉真好"],
        "templates": ["{keyword}的布置好温馨", "求{keyword}的链接"],
    },
}


# ═══════════════════════════════════════════════════════════════
# AI 评论生成器
# ═══════════════════════════════════════════════════════════════

class AIGenerator:
    """AI 评论生成器（OpenAI 兼容 API）

    使用简单的 HTTP 请求，不依赖 openai 库。
    没有配置 API key 时跳过，不影响现有功能。
    """

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        config = self._load_config()

        raw_key = api_key or config.get("api_key", "") or os.environ.get("OPENAI_API_KEY", "")
        self.api_key = raw_key.strip() if raw_key else ""

        self.base_url = (base_url or config.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        self.model = model or config.get("model") or "gpt-4o-mini"
        self.temperature = config.get("temperature", 0.8)

    # ── 配置加载 ────────────────────────────────────────────

    @staticmethod
    def _load_config() -> dict:
        """从 config/ai.yaml 加载配置"""
        path = CONFIG_DIR / "ai.yaml"
        if path.exists():
            try:
                raw = yaml.safe_load(path.read_text())
                return (raw or {}).get("ai", {})
            except Exception as exc:
                log.warning("  ⚠️  ai.yaml 解析失败: %s", exc)
        return {}

    # ── 公共 API ────────────────────────────────────────────

    @property
    def available(self) -> bool:
        """是否有 API key 可用"""
        return bool(self.api_key)

    async def generate_comment(
        self,
        video_title: str,
        video_desc: str = "",
        direction: str = "称赞",
        persona: dict = None,
    ) -> Optional[str]:
        """根据视频标题和方向生成评论

        Args:
            video_title: 视频标题
            video_desc:  视频描述（可选）
            direction:   评论方向（称赞/提问/共鸣/补充/搞笑）
            persona:     账号人设字典（可选）

        Returns:
            生成的评论文本，失败返回 None
        """
        if not self.available:
            log.debug("  ⏭️  AI 生成跳过（未配置 API key）")
            return None

        prompt = self._build_prompt(video_title, video_desc, direction, persona)
        text = await self._call_api(prompt)
        return text

    # ── 内部方法 ────────────────────────────────────────────

    def _build_prompt(self, video_title: str, video_desc: str, direction: str, persona: dict = None) -> str:
        """构建 prompt"""
        style_hint = f"（风格要求：{direction}）"

        persona_hint = ""
        if persona:
            parts = []
            if persona.get("age_group"):
                parts.append(f"年龄层: {persona['age_group']}")
            if persona.get("gender"):
                parts.append(f"性别: {persona['gender']}")
            if persona.get("interests"):
                parts.append(f"兴趣: {'、'.join(persona['interests'])}")
            if persona.get("comment_style"):
                parts.append(f"评论风格: {'、'.join(persona['comment_style'])}")
            if parts:
                persona_hint = f"\n账号人设: {'; '.join(parts)}"

        desc_part = f"\n视频描述: {video_desc}" if video_desc else ""

        return (
            f"你是一个短视频平台的活跃用户。请根据以下视频信息写一条 {direction} 方向的评论{style_hint}。"
            f"{persona_hint}"
            f"\n视频标题: {video_title}"
            f"{desc_part}"
            "\n\n要求："
            "\n- 语言自然，像真实用户的评论"
            "\n- 长度 10~50 字"
            "\n- 不要用 emoji"
            "\n- 直接输出评论内容，不要加引号或前缀"
        )

    async def _call_api(self, prompt: str) -> Optional[str]:
        """调用 OpenAI 兼容 API 生成文本"""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": self.temperature,
                        "max_tokens": 150,
                    },
                )
                if resp.status_code != 200:
                    log.warning("  ⚠️  AI API 返回 %s: %s", resp.status_code, resp.text[:200])
                    return None
                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    return None
                text = choices[0].get("message", {}).get("content", "").strip()
                return text if text else None
        except Exception as exc:
            log.warning("  ⚠️  AI API 调用失败: %s", exc)
            return None


# ═══════════════════════════════════════════════════════════════
# 语料库管理器
# ═══════════════════════════════════════════════════════════════

class CorpusManager:
    """语料库管理器"""

    def __init__(self):
        self._cache = {}
        self._personas = {}  # account_id → persona dict
        self._ai_gen = None  # AIGenerator 懒实例化
        self._ensure_files()

    # ── 语料文件管理 ────────────────────────────────────────

    def _ensure_files(self):
        """确保语料库 YAML 文件存在"""
        for platform, data in [("douyin", DEFAULT_DOUYIN_COMMENTS), ("xiaohongshu", DEFAULT_XHS_COMMENTS)]:
            path = CORPUS_DIR / f"{platform}.yaml"
            if not path.exists():
                content = {"version": "1.0", "categories": data}
                path.write_text(yaml.dump(content, default_flow_style=False, allow_unicode=True, sort_keys=False))
                log.info(f"  📝 创建语料文件: {path.name} ({sum(1 for c in data.values() for _ in c.get('comments',[]))} 条)")

    def _load(self, platform: str) -> dict:
        """加载指定平台的语料"""
        if platform not in self._cache:
            path = CORPUS_DIR / f"{platform}.yaml"
            if path.exists():
                self._cache[platform] = yaml.safe_load(path.read_text()) or {}
            else:
                self._cache[platform] = {"version": "1.0", "categories": {}}
        return self._cache[platform]

    # ── 人设管理 ──────────────────────────────────────────

    def load_personas(self) -> dict:
        """从 profiles.json 加载所有人设，返回 account_id → persona dict"""
        log.info(f"  📂 加载人设数据: {PROFILES_PATH}")
        try:
            if PROFILES_PATH.exists():
                raw = json.loads(PROFILES_PATH.read_text())
                self._personas = {}
                for account_id, profile in raw.items():
                    persona = profile.get("persona")
                    if persona:
                        self._personas[account_id] = persona
                log.info(f"  ✅ 加载 {len(self._personas)} 个人设")
            else:
                log.warning("  ⚠️  人设文件不存在: %s", PROFILES_PATH)
                self._personas = {}
        except Exception as exc:
            log.warning("  ⚠️  加载人设失败: %s", exc)
            self._personas = {}
        return self._personas

    def get_persona(self, account_id: str) -> Optional[dict]:
        """获取指定账号的人设

        Args:
            account_id: 账号 ID

        Returns:
            人设字典，或 None
        """
        if not self._personas:
            self.load_personas()
        persona = self._personas.get(account_id)
        if persona is None:
            log.debug(f"  ℹ️  账号 %s 无人设", account_id)
        return persona

    def get_search_keywords(self, account_id: str) -> list:
        """获取账号人设中的搜索关键词

        Args:
            account_id: 账号 ID

        Returns:
            关键词列表（无人设时返回空列表）
        """
        persona = self.get_persona(account_id)
        if persona:
            return persona.get("search_keywords", [])
        return []

    # ── v2 格式支持 ────────────────────────────────────────

    def list_personas(self) -> list:
        """列出所有身份（v2格式）"""
        result = []
        for platform in ["douyin", "xiaohongshu"]:
            data = self._load(platform)
            for pid, info in data.get("personas", {}).items():
                result.append({
                    "platform": platform,
                    "id": pid,
                    "name": info.get("name", pid),
                    "tags": info.get("tags", []),
                    "style": info.get("style", ""),
                })
        return result

    def list_scenes(self, persona_id: str = None) -> list:
        """列出所有场景（v2格式）"""
        scenes_set = {}
        for platform in ["douyin", "xiaohongshu"]:
            data = self._load(platform)
            for pid, pinfo in data.get("personas", {}).items():
                if persona_id and pid != persona_id:
                    continue
                for scene_id, sinfo in data.get("scenes", {}).items():
                    key = f"{pid}.{scene_id}"
                    if key not in scenes_set:
                        scenes_set[key] = {
                            "persona": pid,
                            "id": scene_id,
                            "label": sinfo.get("label", scene_id),
                            "rounds": sinfo.get("rounds", 1),
                        }
        return list(scenes_set.values())

    def get_comment_for_scene(self, persona: str, scene: str,
                               keyword: str = "", round_num: int = 1) -> Optional[str]:
        """根据身份和场景获取评论（v2格式）

        Args:
            persona: 身份ID（如 health_lover）
            scene: 场景ID（如 first_comment）
            keyword: 关键词
            round_num: 多轮对话第几轮

        Returns:
            评论文本，或 None
        """
        for platform in ["douyin", "xiaohongshu"]:
            data = self._load(platform)
            content = data.get("content", {})
            # 尝试精确匹配 persona.scene
            key = f"{persona}.{scene}"
            if key in content:
                items = content[key]
                if isinstance(items, list):
                    return random.choice(items).replace("{keyword}", keyword) if items else None
                # 多轮格式
                round_key = f"round_{round_num}"
                if isinstance(items, dict) and round_key in items:
                    round_items = items[round_key]
                    if round_items:
                        return random.choice(round_items).replace("{keyword}", keyword)
            # 尝试匹配 scene 但不限定 persona
            for ck, cv in content.items():
                if ck.endswith(f".{scene}"):
                    if isinstance(cv, list) and cv:
                        return random.choice(cv).replace("{keyword}", keyword)
        return None

    # ── 语料查询 ──────────────────────────────────────────

    def list_categories(self) -> list:
        """列出所有平台的分类"""
        result = []
        for platform in ["douyin", "xiaohongshu"]:
            data = self._load(platform)
            for name, info in data.get("categories", {}).items():
                count = len(info.get("comments", [])) + len(info.get("templates", []))
                result.append({
                    "platform": platform,
                    "name": name,
                    "weight": info.get("weight", 0),
                    "enabled": info.get("enabled", True),
                    "count": count,
                    "label": info.get("label", name),
                })
        return result

    def get_comments(self, categories: List[str] = None, platform: str = None, count: int = 20) -> List[str]:
        """获取评论列表

        Args:
            categories: 指定分类（None = 所有启用分类）
            platform: 指定平台（None = 所有平台）
            count: 最多返回数量

        Returns:
            评论文本列表
        """
        results = []
        platforms = [platform] if platform else ["douyin", "xiaohongshu"]

        for p in platforms:
            data = self._load(p)
            for name, info in data.get("categories", {}).items():
                # 筛选分类
                if categories and name not in categories:
                    continue
                if not info.get("enabled", True):
                    continue
                if info.get("weight", 0) <= 0:
                    continue

                # 取评论
                comments = info.get("comments", [])
                templates = info.get("templates", [])
                combined = comments + templates
                # 按权重比例取
                take = max(1, int(count * info.get("weight", 10) / 100))
                results.extend(random.sample(combined, min(take, len(combined))))

        random.shuffle(results)
        return results[:count]

    def add_comment(self, category: str, text: str, platform: str = "douyin"):
        """添加一条评论到指定平台指定分类"""
        data = self._load(platform)
        cats = data.get("categories", {})
        if category not in cats:
            cats[category] = {"weight": 10, "enabled": True, "label": category, "comments": [], "templates": []}
        if "comments" not in cats[category]:
            cats[category]["comments"] = []
        cats[category]["comments"].append(text)
        data["categories"] = cats

        path = CORPUS_DIR / f"{platform}.yaml"
        path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False))
        self._cache.pop(platform, None)  # 清除缓存
        log.info(f"  ✅ 已添加评论到 [{platform}/{category}]: {text}")

    def delete_comment(self, category: str, index: int, platform: str = "douyin"):
        """删除指定索引的评论"""
        data = self._load(platform)
        cats = data.get("categories", {}).get(category, {})
        comments = cats.get("comments", [])
        if 0 <= index < len(comments):
            removed = comments.pop(index)
            cats["comments"] = comments
            path = CORPUS_DIR / f"{platform}.yaml"
            path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False))
            self._cache.pop(platform, None)
            log.info(f"  🗑 已删除评论 [{platform}/{category}]: {removed}")

    def update_category(self, platform: str, category: str, **kwargs):
        """更新分类设置（weight/enabled/label 等）"""
        data = self._load(platform)
        cats = data.get("categories", {})
        if category not in cats:
            cats[category] = {"weight": 10, "enabled": True, "label": category, "comments": [], "templates": []}
        for k, v in kwargs.items():
            if k in ("weight", "enabled", "label"):
                cats[category][k] = v
        data["categories"] = cats
        path = CORPUS_DIR / f"{platform}.yaml"
        path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False))
        self._cache.pop(platform, None)
        log.info(f"  ✅ 已更新分类 [{platform}/{category}]: {kwargs}")

    # ── 账号上下文 ──────────────────────────────────────────

    def set_account_id(self, account_id: str):
        """设置当前账号 ID，方便后续跟踪上下文"""
        self._account_id = account_id
        log.info(f"  👤 设置账号: {account_id}")

    # ── AI 生成器 ──────────────────────────────────────────

    def _get_ai_generator(self) -> AIGenerator:
        """懒获取 AI 生成器实例"""
        if self._ai_gen is None:
            self._ai_gen = AIGenerator()
        return self._ai_gen

    # ── 视频标题匹配 → 评论 ──────────────────────────────────

    @staticmethod
    def _extract_first_keyword(video_title: str) -> Optional[str]:
        """从视频标题中提取第一个匹配的关键词"""
        for keywords, _ in KEYWORD_CATEGORY_MAP:
            for kw in keywords:
                if kw in video_title:
                    return kw
        # fallback: 取标题第一个有意义的词
        words = re.findall(r'[\w\u4e00-\u9fff]{2,}', video_title)
        return words[0] if words else ""

    @staticmethod
    def _match_keywords(video_title: str) -> list:
        """根据视频标题匹配关键词，返回匹配到的方向列表"""
        matched_directions = []
        for keywords, directions in KEYWORD_CATEGORY_MAP:
            for kw in keywords:
                if kw in video_title:
                    matched_directions.extend(directions)
                    break  # 一个关键词组只匹配一次
        return matched_directions

    def _get_comment_from_categories(self, category_names: list, platform: str = None) -> Optional[str]:
        """从指定的分类名列表中随机取一条评论（遍历所有平台）"""
        platforms = [platform] if platform else ["douyin", "xiaohongshu"]
        candidates = []

        for p in platforms:
            data = self._load(p)
            for cat_name, info in data.get("categories", {}).items():
                if cat_name not in category_names:
                    continue
                if not info.get("enabled", True):
                    continue
                comments = info.get("comments", []) + info.get("templates", [])
                candidates.extend(comments)

        if candidates:
            return random.choice(candidates)
        return None

    def _get_random_comment(self, platform: str = None) -> Optional[str]:
        """从所有启用分类中随机取一条评论"""
        platforms = [platform] if platform else ["douyin", "xiaohongshu"]
        all_comments = []

        for p in platforms:
            data = self._load(p)
            for name, info in data.get("categories", {}).items():
                if not info.get("enabled", True):
                    continue
                if info.get("weight", 0) <= 0:
                    continue
                comments = info.get("comments", []) + info.get("templates", [])
                all_comments.extend(comments)

        if all_comments:
            return random.choice(all_comments)
        return None

    def get_comment_for_video(
        self,
        video_title: str,
        direction: str = None,
        account_id: str = None,
    ) -> Optional[str]:
        """根据视频标题（和可选方向/账号人设）从语料库中匹配一条评论

        Args:
            video_title: 视频标题文本
            direction:   可选，指定方向，如 "称赞"/"提问"/"共鸣"/"补充"
            account_id:  可选，账号 ID，用于根据人设的 comment_style 优先选择方向

        Returns:
            匹配到的评论文本，或 None
        """
        # 0) 有人设 → 优先用人设的 comment_style 作为方向
        persona = None
        if account_id:
            persona = self.get_persona(account_id)
            if persona and not direction:
                # 如果未指定 direction，用人设的第一个 comment_style
                styles = persona.get("comment_style", [])
                if styles:
                    # 先用 comment_style 去匹配，最后 fallback 到随机
                    pass  # 后面有具体逻辑

        # 1) 从标题匹配关键词，得到方向列表
        matched_directions = self._match_keywords(video_title)

        # 2) 如果用户指定了 direction，优先使用
        if direction and direction in DIRECTION_TO_CATEGORY:
            if direction in matched_directions:
                matched_directions.remove(direction)
            matched_directions = [direction] + matched_directions
        elif direction:
            pass

        # 2.5) 如果有人设且未指定 direction，把人设的 comment_style 优先排列
        if persona and not direction:
            styles = persona.get("comment_style", [])
            # 把人设风格中在 matched_directions 里的提到最前面
            for style in reversed(styles):
                if style in matched_directions:
                    matched_directions.remove(style)
                    matched_directions = [style] + matched_directions
                elif style in DIRECTION_TO_CATEGORY:
                    # 人设风格虽未匹配到关键词，也尝试作为候选方向
                    matched_directions = [style] + matched_directions

        # 3) 有匹配的方向 → 尝试依次取对应分类的评论
        if matched_directions:
            for d in matched_directions:
                cat = DIRECTION_TO_CATEGORY.get(d)
                if not cat:
                    continue
                comment = self._get_comment_from_categories([cat])
                if comment:
                    kw = self._extract_first_keyword(video_title)
                    if kw:
                        comment = comment.replace("{keyword}", kw)
                    return comment

        # 4) 没有语料匹配 → fallback: 尝试 AI 生成
        ai = self._get_ai_generator()
        if ai.available:
            try:
                # 同步上下文执行异步 AI 调用
                comment = asyncio.run(
                    ai.generate_comment(
                        video_title=video_title,
                        direction=direction or (persona.get("comment_style", [""])[0] if persona else "称赞"),
                        persona=persona,
                    )
                )
                if comment:
                    log.info("  🤖 AI 生成评论: %s", comment[:40])
                    return comment
            except Exception as exc:
                log.warning("  ⚠️  AI 生成失败: %s", exc)

        # 5) 最后兜底 → 随机返回一条
        comment = self._get_random_comment()
        if comment and "{keyword}" in comment:
            kw = self._extract_first_keyword(video_title)
            if kw:
                comment = comment.replace("{keyword}", kw)
        return comment

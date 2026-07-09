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
        - text: "讲得太好了，受益匪浅！"
          role: sharer
        - text: "这个观点很新颖，学习了"
          role: sharer
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

# ── 行业关键词映射 ──────────────────────────────────────────
# 每个行业的关键词列表，用于匹配视频标题 → 判断视频所属行业
INDUSTRY_TAGS = {
    "medical":   ["医生","医院","药","健康","养生","中医","体检","症状","治疗",
                  "康复","营养","饮食","锻炼","专家","手术","门诊","看病","诊断",
                  "痔疮","肛肠","肠胃","胃镜","肠镜"],
    "finance":   ["股票","基金","理财","投资","经济","A股","财经","金融","保险"],
    "tech":      ["手机","数码","电脑","科技","AI","人工智能","评测","机器人"],
    "food":      ["美食","做饭","菜谱","餐厅","好吃","探店","烹饪","烘焙"],
}

# ── 通用方向（用于万能兜底，不匹配任何行业时使用）──
UNIVERSAL_DIRECTIONS = ["称赞", "提问", "共鸣"]

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
        """根据视频标题和方向生成评论"""
        if not self.available:
            log.debug("  ⏭️  AI 生成跳过（未配置 API key）")
            return None

        prompt = self._build_prompt(video_title, video_desc, direction, persona)
        text = await self._call_api(prompt)
        return text

    async def generate_comment_by_role(
        self,
        video_title: str,
        video_desc: str = "",
        role: str = "sharer",
        role_label: str = "分享型",
        is_long: bool = False,
    ) -> Optional[str]:
        """根据视频 + 角色生成评论（含长评模式）

        Args:
            video_title: 视频标题
            video_desc: 视频描述
            role: 角色标识（sharer/questioner/sympathizer/skeptic/sufferer/filler/expert_ref）
            role_label: 角色中文标签
            is_long: 是否生成讲故事的长评
        """
        if not self.available:
            return None

        length_desc = "写一条50~200字的故事型评论，像在分享亲身经历，有细节有情感" if is_long else "写一条10~30字的短评论，自然口语化"
        role_desc_map = {
            "sharer": "你是一个热心分享的人，在评论区分享自己的经验或观点",
            "questioner": "你是一个好奇的提问者，对视频内容感兴趣并追问细节",
            "sympathizer": "你是一个善于共情的人，表达理解、安慰和支持",
            "skeptic": "你是一个理性客观的人，对内容保持审慎和独立思考",
            "sufferer": "你是一个有相同经历的人，讲述自己遇到的类似问题",
            "filler": "你是一个普通用户，用简短的话互动",
            "expert_ref": "你是一个有经验的人，推荐特定的专家或方案",
        }
        role_hint = role_desc_map.get(role, "你是一个普通抖音用户")

        desc_part = f"\n视频描述: {video_desc}" if video_desc else ""

        prompt = (
            f"你是一个抖音用户。{role_hint}。"
            f"\n视频标题: {video_title}"
            f"{desc_part}"
            f"\n\n请{length_desc}。"
            "\n- 语言自然口语化"
            "\n- 不要用 emoji"
            "\n- 不要用引号"
            "\n- 直接输出评论内容"
        )
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
                        "max_tokens": 300,
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
        """获取指定账号的人设"""
        if not self._personas:
            self.load_personas()
        persona = self._personas.get(account_id)
        if persona is None:
            log.debug(f"  ℹ️  账号 %s 无人设", account_id)
        return persona

    def get_search_keywords(self, account_id: str) -> list:
        """获取账号人设中的搜索关键词"""
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
        result = []
        for platform in ["douyin", "xiaohongshu"]:
            data = self._load(platform)
            scenes = data.get("scenes", {})
            for sid, info in scenes.items():
                scene_persona = info.get("persona", "")
                if persona_id and scene_persona != persona_id:
                    continue
                result.append({
                    "platform": platform,
                    "scene": sid,
                    "persona": scene_persona,
                    "category": info.get("category", ""),
                    "comments": info.get("comments", []),
                })
        return result

    def get_comment_for_scene(self, persona: str, scene: str,
                               keyword: str = "", round_num: int = 1) -> Optional[str]:
        """根据身份和场景获取评论（v2格式）"""
        for platform in ["douyin", "xiaohongshu"]:
            data = self._load(platform)
            scenes = data.get("scenes", {})
            if scene in scenes:
                info = scenes[scene]
                if info.get("persona", "") != persona:
                    continue
                comments = info.get("comments", [])
                if comments:
                    idx = (round_num - 1) % len(comments)
                    comment = comments[idx]
                    if "{keyword}" in comment and keyword:
                        comment = comment.replace("{keyword}", keyword)
                    return comment
                templates = info.get("templates", [])
                if templates:
                    idx = (round_num - 1) % len(templates)
                    comment = templates[idx]
                    if "{keyword}" in comment and keyword:
                        comment = comment.replace("{keyword}", keyword)
                    return comment
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
                    "accessible": info.get("accessible", []),
                })
        return result

    def get_comments(self, categories: List[str] = None, platform: str = None, count: int = 20) -> List[str]:
        """获取评论列表"""
        results = []
        platforms = [platform] if platform else ["douyin", "xiaohongshu"]

        for p in platforms:
            data = self._load(p)
            for name, info in data.get("categories", {}).items():
                if categories and name not in categories:
                    continue
                if not info.get("enabled", True):
                    continue
                if info.get("weight", 0) <= 0:
                    continue

                comments = info.get("comments", [])
                templates = info.get("templates", [])
                combined = comments + templates
                take = max(1, int(count * info.get("weight", 10) / 100))
                results.extend(random.sample(combined, min(take, len(combined))))

        random.shuffle(results)
        return results[:count]

    def add_comment(self, category: str, text: str, platform: str = "douyin"):
        """添加一条评论到指定分类（追加模式）"""
        data = self._load(platform)
        cats = data.get("categories", {})
        if category not in cats:
            cats[category] = {"weight": 10, "enabled": True, "label": category, "comments": []}
        cats[category].setdefault("comments", []).append({"text": text, "role": "filler"})
        path = CORPUS_DIR / f"{platform}.yaml"
        path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False))
        self._cache.pop(platform, None)
        log.info(f"  ✅ 已添加评论到 {platform}/{category}: {text[:30]}")

    def get_comment_for_video(
        self,
        video_title: str,
        direction: str = None,
        account_id: str = None,
    ) -> Optional[str]:
        """根据视频标题和账号行业，从语料库匹配评论"""
        if not direction:
            direction = random.choice(UNIVERSAL_DIRECTIONS)

        account_industry = self._get_account_industry(account_id) if account_id else "general"
        video_industry = self._classify_video(video_title)

        log.info(f"  📋 视频行业={video_industry} 账号行业={account_industry} 方向={direction}")

        if video_industry == account_industry and account_industry != "general":
            comment = self._pick_comment(video_industry, account_industry, direction)
            if comment:
                log.info(f"  ✅ 行业池匹配: {comment[:40]}")
                return comment

        comment = self._pick_comment("general", account_industry, direction)
        if comment:
            log.info(f"  ✅ 万能池: {comment[:40]}")
            return comment

        comment = self._get_random_comment()
        if comment and "{keyword}" in comment:
            kw = self._extract_first_keyword(video_title)
            if kw:
                comment = comment.replace("{keyword}", kw)
        return comment

    # ── 角色化评论（v3）────────────────────────────────────

    def get_roles(self, platform: str = "douyin") -> dict:
        """返回语料库中可用的角色列表及每角色的评论数"""
        data = self._load(platform)
        roles = {}
        for cat_name, cat_info in data.get("categories", {}).items():
            for comment in cat_info.get("comments", []):
                if isinstance(comment, dict):
                    role = comment.get("role", "filler")
                else:
                    role = "filler"
                if role not in roles:
                    roles[role] = {"label": role, "count": 0, "examples": []}
                roles[role]["count"] += 1
                if len(roles[role]["examples"]) < 3:
                    text = comment["text"] if isinstance(comment, dict) else comment
                    roles[role]["examples"].append(text)
            for template in cat_info.get("templates", []):
                if isinstance(template, dict):
                    role = template.get("role", "filler")
                else:
                    role = "filler"
                if role not in roles:
                    roles[role] = {"label": role, "count": 0, "examples": []}
                roles[role]["count"] += 1
        return roles

    def get_role_label(self, role: str) -> str:
        """角色标识 → 中文标签"""
        labels = {
            "sharer": "分享型", "questioner": "提问型", "sympathizer": "共情型",
            "skeptic": "质疑型", "sufferer": "患者型", "filler": "灌水型",
            "expert_ref": "推荐型",
        }
        return labels.get(role, role)

    def batch_get_comments_by_roles(
        self,
        role_distribution: dict,
        platform: str = "douyin",
        video_title: str = "",
        video_industry: str = None,
        total: int = 30,
        ai_enhance: bool = False,
        long_ratio: float = 0.0,
    ) -> list:
        """按角色比例批量抽取评论，可选 AI 增强和长评

        Args:
            role_distribution: {"filler": 0.3, "questioner": 0.17, ...}
            platform: 平台
            video_title: 视频标题（用于模板替换）
            video_industry: 视频行业，如 "health" — 只取 accessible 匹配的分类；None=不过滤
            total: 总共取多少条
            ai_enhance: 是否用 AI 改写每条评论
            long_ratio: 长评占比（0~1）

        Returns:
            [{"text": "...", "role": "...", "role_label": "...", "is_long": bool}, ...]
        """
        all_by_role = {}
        data = self._load(platform)
        for cat_name, cat_info in data.get("categories", {}).items():
            # 行业过滤
            # - 有 accessible 的分类：只对匹配行业的视频开放
            # - 无 accessible 的分类：所有视频通用
            # - video_industry = None（自动识别失败）：只取通用分类
            accessible = cat_info.get("accessible", [])
            if accessible:
                if not video_industry or video_industry not in accessible:
                    continue
            for comment in cat_info.get("comments", []):
                if isinstance(comment, dict):
                    c_role = comment.get("role", "filler")
                    text = comment.get("text", "")
                else:
                    c_role = "filler"
                    text = str(comment)
                all_by_role.setdefault(c_role, []).append(text)
            for template in cat_info.get("templates", []):
                if isinstance(template, dict):
                    c_role = template.get("role", "filler")
                    text = template.get("text", "")
                else:
                    c_role = "filler"
                    text = str(template)
                all_by_role.setdefault(c_role, []).append(text)

        result = []
        for role, proportion in role_distribution.items():
            pool = all_by_role.get(role, [])
            if not pool:
                continue
            take = max(1, int(total * proportion))
            sampled = random.sample(pool, min(take, len(pool)))
            for text in sampled:
                if "{keyword}" in text and video_title:
                    kw = self._extract_first_keyword(video_title)
                    if kw:
                        text = text.replace("{keyword}", kw)
                is_long = random.random() < long_ratio
                result.append({
                    "text": text,
                    "role": role,
                    "role_label": self.get_role_label(role),
                    "is_long": is_long,
                })

        random.shuffle(result)
        result = result[:total]

        # AI 增强
        if ai_enhance and video_title:
            import asyncio as _asyncio
            try:
                loop = _asyncio.get_event_loop()
            except RuntimeError:
                loop = _asyncio.new_event_loop()
            for item in result:
                try:
                    enhanced = loop.run_until_complete(
                        self._ai_gen.generate_comment_by_role(
                            video_title=video_title,
                            role=item["role"],
                            role_label=item["role_label"],
                            is_long=item["is_long"],
                        )
                    ) if self._ai_gen else None
                    if enhanced:
                        item["text"] = enhanced
                except Exception:
                    pass

        return result

    # ── 内部方法 ────────────────────────────────────────────

    def _get_account_industry(self, account_id: str) -> str:
        """从 profiles.json 读取账号行业"""
        try:
            if PROFILES_PATH.exists():
                profiles = json.loads(PROFILES_PATH.read_text())
                profile = profiles.get(account_id, {})
                return profile.get("industry", "general")
        except Exception:
            pass
        return "general"

    def _classify_video(self, title: str) -> str:
        """从标题判断视频行业"""
        title_lower = title.lower()
        for industry, keywords in INDUSTRY_TAGS.items():
            for kw in keywords:
                if kw in title_lower or kw in title:
                    return industry
        return "general"

    def _extract_first_keyword(self, title: str) -> Optional[str]:
        """从标题提取第一个行业关键词"""
        title_lower = title.lower()
        for industry, keywords in INDUSTRY_TAGS.items():
            for kw in keywords:
                if kw in title_lower or kw in title:
                    return kw
        return None

    def _pick_comment(self, video_industry: str, account_industry: str, direction: str) -> Optional[str]:
        """从行业池取一条评论"""
        cat_name = DIRECTION_TO_CATEGORY.get(direction)
        if not cat_name:
            return None

        for platform in ["douyin", "xiaohongshu"]:
            data = self._load(platform)
            cat_info = data.get("categories", {}).get(cat_name)
            if not cat_info:
                continue

            accessible = cat_info.get("accessible", [])
            if accessible and video_industry not in accessible:
                continue

            candidates = []
            for comment in cat_info.get("comments", []):
                if isinstance(comment, dict):
                    candidates.append(comment.get("text", ""))
                else:
                    candidates.append(comment)
            if candidates:
                return random.choice(candidates)
        return None

    def _get_random_comment(self) -> Optional[str]:
        """兜底：从所有平台随机取一条评论"""
        for platform in ["douyin", "xiaohongshu"]:
            data = self._load(platform)
            for cat_info in data.get("categories", {}).values():
                comments = cat_info.get("comments", [])
                if comments:
                    c = random.choice(comments)
                    return c if isinstance(c, str) else c.get("text", "")
        return None

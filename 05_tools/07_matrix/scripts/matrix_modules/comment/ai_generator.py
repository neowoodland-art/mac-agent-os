"""
🎯 AI 评论生成器 — 基于本地 oMLX 模型

通过本地 oMLX API (localhost:8000) 生成小红书风格 AI 评论。
作为静态语料库的增强替代，支持上下文感知（基于笔记标题/内容）。

用法:
  from matrix_modules.comment.ai_generator import AICommentGenerator

  gen = AICommentGenerator()
  comment = gen.generate(topic="美食", style="种草")
  comment = gen.generate_with_context(note_title="周末去苏州旅游攻略")
  comment = gen.generate_from_note(page=page)  # 从当前页面提取内容
"""

import json
import random
import time
import urllib.request
import re
from typing import Optional, List

# 默认 oMLX API 地址
OLLAMA_BASE = "http://localhost:8000/v1"
API_KEY = "5omlx"

# 系统提示词 — 小红书风格评论生成
SYSTEM_PROMPT = """你是一个小红书重度用户，正在给笔记写评论。

你的评论风格要求：
1. 亲切自然，像真人用户的真实感受（不是营销号）
2. 长度10-25字，简洁但有信息量
3. 可以带少量 emoji（但要自然，不要堆砌）
4. 语气因人而异：种草类热情、经验类实用、旅行美景类温暖
5. 避免重复、套路化的表达

你生成的每条评论必须：
- 与笔记主题相关（基于给定的主题/标题/内容）
- 语气自然真实
- 不营销、不推销、不带链接
- 不涉及政治、色情、暴力

只输出评论文本本身，不要加引号、前缀或其他格式。"""


def _call_omlx(messages: list, max_tokens: int = 64,
               temperature: float = 0.9, timeout: int = 10) -> Optional[str]:
    """
    调用 oMLX 本地 API 生成文本。

    Args:
        messages: OpenAI 格式的消息列表
        max_tokens: 最大生成 token 数
        temperature: 生成温度 (0-1)
        timeout: 超时秒数

    Returns:
        生成的文本，失败返回 None
    """
    payload = json.dumps({
        "model": "Qwen3.5-4B-MLX-4bit",  # 可用模型
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
        "max_completion_tokens": 100,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_BASE}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        method="POST",
    )

    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            text = result["choices"][0]["message"]["content"].strip()
            # 清理可能的引号
            text = text.strip("\"'「」『』")
            return text
    except Exception as e:
        print(f"  ⚠️ oMLX 调用失败: {e}")
        return None


# ════════════════════════════════════════════════════════════
# 主类
# ════════════════════════════════════════════════════════════

class AICommentGenerator:
    """AI 评论生成器 — 基于 oMLX 本地模型"""

    def __init__(self, base_url: str = OLLAMA_BASE, api_key: str = API_KEY,
                 model: str = "Qwen3.5-4B-MLX-4bit"):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self._used_comments: set = set()  # 会话级去重

    def set_url(self, url: str, key: str):
        """设置 oMLX 地址和密钥"""
        self.base_url = url
        self.api_key = key

    def reset_session(self):
        """重置去重记录"""
        self._used_comments.clear()

    def _is_duplicate(self, text: str) -> bool:
        """检查是否与已用评论重复"""
        text_clean = text.strip().lower()
        if text_clean in self._used_comments:
            return True
        # 相似度检查：如果已有的评论包含当前文本或反之
        for used in self._used_comments:
            if text_clean in used or used in text_clean:
                return True
        return False

    def generate(self, topic: str = "",
                 style: str = "general",
                 max_tokens: int = 64,
                 temperature: float = 0.9,
                 retries: int = 3) -> str:
        """
        生成一条小红书风格评论。

        Args:
            topic: 评论主题（空字符串则随机）
            style: 风格 (general, zhongcao/种草, tips/技巧, travel/旅行, food/美食)
            max_tokens: 生成长度
            temperature: 生成温度
            retries: 失败重试次数

        Returns:
            评论文本（失败时 fallback 到随机静态语料）
        """
        style_desc = {
            "general": "日常评论，语气自然亲切",
            "zhongcao": "种草风，热情推荐，简短有力",
            "tips": "实用技术型，分享经验感受",
            "travel": "旅行/风景类，温暖治愈",
            "food": "美食类，表达馋了/想尝试",
        }.get(style, "日常评论，语气自然亲切")

        for attempt in range(retries):
            content = f"生成一条小红书评论。\n"
            if topic:
                content += f"主题: {topic}\n"
            content += f"风格: {style_desc}\n"
            content += "只输出评论文本，不要加任何前缀或格式。"

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ]

            text = _call_omlx(messages, max_tokens=max_tokens,
                              temperature=temperature)
            if text and not self._is_duplicate(text):
                self._used_comments.add(text.strip().lower())
                return text

            time.sleep(0.3)

        # 所有重试失败，fallback 到静态语料
        return self._fallback_comment()

    def generate_with_context(self, note_title: str = "",
                              note_content: str = "",
                              style: str = "general") -> str:
        """
        基于笔记上下文生成相关评论。

        Args:
            note_title: 笔记标题
            note_content: 笔记内容摘要
            style: 评论风格

        Returns:
            评论文本
        """
        context = "根据以下笔记内容生成一条评论：\n"
        if note_title:
            context += f"标题: {note_title}\n"
        if note_content:
            context += f"内容: {note_content[:200]}\n"
        context += "评论要基于笔记内容，像是真实用户的自然感受。"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ]

        text = _call_omlx(messages, max_tokens=80, temperature=0.85)
        if text and not self._is_duplicate(text):
            self._used_comments.add(text.strip().lower())
            return text

        return self._fallback_comment(topic=note_title[:20]
                                      if note_title else "")

    async def generate_from_note(self, page) -> str:
        """
        从当前页面提取笔记内容并生成评论。

        Args:
            page: Playwright Page 对象

        Returns:
            评论文本
        """
        try:
            note_info = await page.evaluate("""
            () => {
                const title = document.querySelector('.title, h1, [class*=note-title]');
                const content = document.querySelector('.content, .desc, [class*=content]');
                return {
                    title: title ? title.textContent.trim().substring(0, 100) : '',
                    content: content ? content.textContent.trim().substring(0, 200) : '',
                };
            }
            """)
        except Exception:
            note_info = {"title": "", "content": ""}

        return self.generate_with_context(
            note_title=note_info.get("title", ""),
            note_content=note_info.get("content", ""),
        )

    def _fallback_comment(self, topic: str = "") -> str:
        """静态语料 fallback"""
        from matrix_modules.comment.xhs.corpus import get_comment
        return get_comment(length="medium")


# ════════════════════════════════════════════════════════════
# 便捷函数（与 comment_corpus.py 接口一致）
# ════════════════════════════════════════════════════════════

_global_generator: AICommentGenerator = None


def _get_generator() -> AICommentGenerator:
    """获取全局生成器实例"""
    global _global_generator
    if _global_generator is None:
        _global_generator = AICommentGenerator()
    return _global_generator


def ai_comment(topic: str = "", style: str = "general") -> str:
    """获取一条 AI 生成的小红书评论"""
    return _get_generator().generate(topic=topic, style=style)


def reset_ai_session():
    """重置 AI 评论去重记录"""
    _get_generator().reset_session()


# ════════════════════════════════════════════════════════════
# 测试入口
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🎯 AI 评论生成器测试\n")

    gen = AICommentGenerator()

    # 测试：不同主题
    for topic in ["美食探店心得", "周末旅行攻略", "护肤好物分享", "穿搭技巧总结"]:
        comment = gen.generate(topic=topic)
        print(f"  📝 [{topic}] → {comment}")

    # 测试：上下文感知
    print()
    comment = gen.generate_with_context(
        note_title="在苏州发现一家宝藏咖啡馆",
        note_content="周末和朋友去了平江路一家新开的咖啡馆，环境超好，咖啡也很棒！",
    )
    print(f"  📝 [上下文] → {comment}")

    # 测试：oMLX 不可用时 fallback
    print()
    gen.set_url("http://localhost:9999", "invalid_key")
    fallback = gen.generate(topic="测试")
    print(f"  📝 [fallback] → {fallback}")

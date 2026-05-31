"""
layer3_creation/module_b_lyrics.py — 歌词创作模块

功能：基于 oMLX 本地 LLM 进行歌词创作
核心场景：换词 (rewrite) — 保持原曲结构，替换内容
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LyricsResult:
    """歌词创作结果"""
    original_lyrics: str = ""                      # 原歌词
    rewritten_lyrics: str = ""                     # 改写后歌词
    structure: list[dict] = field(default_factory=list)  # [{section, lines}]
    analysis: dict = field(default_factory=dict)          # 段落分析 JSON
    model_used: str = ""                           # 使用的模型
    token_count: int = 0                           # 消耗 token 数


class LyricsModule:
    """
    歌词创作模块

    使用 oMLX 本地 LLM 进行:
    - 歌词分析 (结构/押韵/情感)
    - 歌词改写 (换词创作)
    - 风格迁移
    """

    DEFAULT_PROMPTS = {
        "rewrite": (
            "你是一位专业歌词改编者。请根据以下要求对原曲歌词进行二次创作：\n"
            "主题: {topic}\n风格: {style}\n"
            "保留原曲的段落结构(Intro/Verse/Chorus/Bridge/Outro)和押韵模式。\n"
            "输出格式: 每段以[Intro][Verse][Chorus]标记开头。"
        ),
        "analyze": (
            "分析以下歌词的段落结构、押韵模式和情感走向。\n"
            "输出 JSON 格式，包含: sections, rhyme_scheme, emotion_flow。"
        ),
    }

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.llm_url = self.config.get("lyrics", {}).get(
            "llm_url", "http://localhost:8000/v1"
        )
        self.llm_model = self.config.get("lyrics", {}).get(
            "llm_model", "Qwen3-8B"
        )
        self.max_tokens = self.config.get("lyrics", {}).get("max_tokens", 1024)
        self.temperature = self.config.get("lyrics", {}).get("temperature", 0.8)
        self.rewrite_template = self.config.get(
            "lyrics", {}
        ).get("rewrite_prompt", self.DEFAULT_PROMPTS["rewrite"])

    def rewrite(
        self,
        original_lyrics: str,
        topic: str = "",
        style: str = "",
        output_path: str | Path | None = None,
    ) -> LyricsResult:
        """
        歌词改写

        参数:
            original_lyrics: 原歌词文本
            topic: 新主题
            style: 目标风格
            output_path: 输出路径 (可选)

        返回:
            LyricsResult
        """
        print(f"  [lyrics] 改写创作: topic='{topic}' style='{style}'")

        prompt = self.rewrite_template.format(topic=topic or "相同主题", style=style or "原风格")
        messages = [
            {"role": "system", "content": "你是专业歌词作家。只输出歌词内容，不要额外解释。"},
            {"role": "user", "content": f"{prompt}\n\n原歌词:\n{original_lyrics}"},
        ]
        rewritten = self._call_llm(messages)

        result = LyricsResult(
            original_lyrics=original_lyrics,
            rewritten_lyrics=rewritten,
            model_used=self.llm_model,
        )

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(rewritten)
            print(f"  [lyrics] ✓ 已保存: {output_path}")

        print(f"  [lyrics] ✓ 改写完成 ({len(rewritten)} 字符)")
        return result

    def analyze(self, lyrics: str) -> LyricsResult:
        """
        分析歌词结构

        返回 JSON 格式的段落分析
        """
        print(f"  [lyrics] 分析结构")

        messages = [
            {"role": "system", "content": "你是一个歌词分析专家。只输出 JSON。"},
            {"role": "user", "content": f"{self.DEFAULT_PROMPTS['analyze']}\n\n歌词:\n{lyrics}"},
        ]

        response = self._call_llm(messages)

        analysis = {}
        try:
            # 尝试解析 JSON
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                analysis = json.loads(response[start:end])
        except (json.JSONDecodeError, ValueError):
            analysis = {"raw": response}

        return LyricsResult(
            original_lyrics=lyrics,
            analysis=analysis,
            model_used=self.llm_model,
        )

    # ---- LLM 调用 ----

    def _call_llm(self, messages: list[dict]) -> str:
        """调用 oMLX API"""
        payload = json.dumps({
            "model": self.llm_model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                f"{self.llm_url}/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            content = data["choices"][0]["message"]["content"]
            self._last_tokens = data.get("usage", {}).get("total_tokens", 0)
            return content

        except (urllib.error.HTTPError, urllib.error.URLError,
                json.JSONDecodeError, KeyError) as e:
            print(f"  [lyrics] oMLX API 调用失败: {e}")
            print(f"  [lyrics] 请确保 oMLX Server 已启动 (localhost:8000)")
            return ""

    @property
    def last_tokens(self) -> int:
        """上次调用的 token 数"""
        return getattr(self, "_last_tokens", 0)

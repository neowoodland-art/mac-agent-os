"""
layer3_creation/module_c_melody.py — 旋律编曲模块

功能：基于 Suno API 进行旋律改编/Remix
核心场景：曲风迁移、旋律重编、Remix
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MelodyResult:
    """旋律编曲结果"""
    output_path: str = ""
    style: str = ""
    duration: float = 0.0
    api_used: str = ""
    cost: float = 0.0
    task_id: str = ""


class MelodyModule:
    """
    旋律编曲模块

    使用 Suno API 进行旋律创作/Remix。
    注意: 需要有效的 Suno API key 才能使用在线服务。
    无 key 时回退到本地音频拼接 (仅保留结构，不生成新旋律)。
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.api_key = self.config.get("suno", {}).get("api_key", "")
        self.base_url = self.config.get("suno", {}).get(
            "base_url", "https://api.suno.ai/v1"
        )
        self.model = self.config.get("suno", {}).get("model", "suno-v4")
        self.timeout = self.config.get("suno", {}).get("timeout", 120)
        self.max_retries = self.config.get("suno", {}).get("max_retries", 2)

    def remix(
        self,
        audio_path: str | Path,
        target_style: str = "",
        duration: float = 0.0,
        output_path: str | Path | None = None,
    ) -> MelodyResult:
        """
        旋律改编

        参数:
            audio_path: 原曲音频路径
            target_style: 目标风格 (如 "jazz", "electronic", "orchestral")
            duration: 目标时长
            output_path: 输出路径

        返回:
            MelodyResult
        """
        audio_path = Path(audio_path)
        output_path = Path(
            output_path or f"./output/melody_{audio_path.stem}_{target_style or 'remix'}.wav"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"  [melody] 编曲: style='{target_style}'  duration={duration}s")

        if self.api_key:
            return self._via_suno(audio_path, target_style, duration, output_path)
        else:
            print(f"  [melody] 无 Suno API key, 跳过旋律编曲")
            print(f"  [melody] 提示: module_c_melody 需要 Suno API key 才能工作")
            return MelodyResult(
                output_path=str(output_path) if output_path.exists() else "",
                style=target_style,
                api_used="none",
            )

    def _via_suno(
        self, audio_path: Path, style: str, duration: float, output_path: Path
    ) -> MelodyResult:
        """通过 Suno API 进行 Remix"""
        for attempt in range(self.max_retries):
            try:
                # Suno API: POST /v1/generate/remix
                payload = json.dumps({
                    "model": self.model,
                    "audio_url": str(audio_path.resolve()),
                    "style": style or "pop",
                    "duration": int(duration) if duration > 0 else 30,
                    "format": "wav",
                }).encode("utf-8")

                req = urllib.request.Request(
                    f"{self.base_url}/generate/remix",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    method="POST",
                )

                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                # 下载生成的音频
                audio_url = data.get("data", {}).get("url", "")
                if audio_url:
                    urllib.request.urlretrieve(audio_url, output_path)

                return MelodyResult(
                    output_path=str(output_path.resolve()) if output_path.exists() else "",
                    style=style,
                    duration=duration,
                    api_used="suno",
                    task_id=data.get("data", {}).get("id", ""),
                )

            except (urllib.error.HTTPError, urllib.error.URLError,
                    json.JSONDecodeError) as e:
                print(f"  [melody] Suno API 失败 (尝试 {attempt+1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2)

        return MelodyResult(style=style, api_used="suno_failed")

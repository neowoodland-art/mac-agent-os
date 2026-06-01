"""
AVE 07_bgm_generator — 背景音乐生成 (三阶路由)

用法:
  from bgm_generator.suno import generate_bgm, get_available_moods
  generate_bgm(mood="calm", duration=30, output="/tmp/bgm.wav")
"""
from .suno import generate_bgm, get_available_moods

__all__ = ["generate_bgm", "get_available_moods"]

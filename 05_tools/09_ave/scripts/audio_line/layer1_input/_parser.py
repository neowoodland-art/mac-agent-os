"""
layer1_input/_parser.py — 自然语言指令解析

将用户的口语化指令（如"把这首歌改快一点、加卡点"）解析为 AudioTask。
当前用规则匹配，后续可接入 LLM 增强。
"""
from .collector import AudioTask, AudioSource


def parse_command_text(text: str) -> AudioTask:
    """解析自然语言指令 → AudioTask (不含音频源)"""
    text = text.strip().lower()

    modules = {"separation", "analysis", "rhythm", "lyrics", "mix"}
    operation = "auto"
    target_bpm = 0

    # — 检测操作类型 —
    if any(kw in text for kw in ["卡点", "变速", "改快", "改慢"]):
        operation = "cardio"
    elif any(kw in text for kw in ["换词", "改词", "填词", "翻唱"]):
        operation = "rewrite"
    elif any(kw in text for kw in ["remix", "改编", "混音"]):
        operation = "remix"
    elif any(kw in text for kw in ["加速", "慢速", "变速度"]):
        operation = "speed_up"

    # — 检测 BPM —
    import re
    bpm_match = re.search(r"(\d+)\s*bpm", text)
    if bpm_match:
        target_bpm = int(bpm_match.group(1))

    # — 模块选择 —
    if "只分析" in text or "仅分析" in text:
        modules = {"separation", "analysis"}

    # — 主题/风格提取 (简单规则) —
    style = ""
    for kw, st in [("可爱", "可爱"), ("伤感", "伤感"), ("燃", "燃系"), ("DJ", "电音"),
                   ("古风", "古风"), ("摇滚", "摇滚"), ("爵士", "爵士")]:
        if kw in text:
            style = st
            break

    return AudioTask(
        source=AudioSource(path="", source_type="command"),
        operation=operation,
        target_bpm=target_bpm,
        style=style,
        modules=modules,
    )

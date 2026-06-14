"""小红书平台插件"""

from .plugin import XiaohongshuPlatform


def register_platform():
    return "xiaohongshu", XiaohongshuPlatform()

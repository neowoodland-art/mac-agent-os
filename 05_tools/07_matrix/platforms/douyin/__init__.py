"""抖音平台插件"""

from .plugin import DouyinPlatform


def register_platform():
    return "douyin", DouyinPlatform()

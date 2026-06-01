"""
ops/douyin — 抖音平台操作集

按操作类型分文件：
  browse.py    浏览类（首页、视频、feed流）
  interact.py  交互类（点赞、收藏、评论、滑动）
  search.py    搜索类（预留）
  profile.py   个人页类（预留）
"""

from .browse import goto_home, goto_video, scroll_feed
from .interact import like, collect, comment, next_video

__all__ = [
    "goto_home", "goto_video", "scroll_feed",
    "like", "collect", "comment", "next_video",
]

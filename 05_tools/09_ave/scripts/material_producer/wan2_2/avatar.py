"""
AVE 数字人配置

avatar 配置存储在 agent-local, 不提交到 Git
"""
import os
from pathlib import Path

LOCAL_DIR = Path(os.environ.get("AVE_LOCAL_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local")))

# 头像图片: 用户通过微信发送到这里
AVATAR_DIR = LOCAL_DIR / "tools" / "ave" / "avatar"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

# 数字人视频缓存
DIGITAL_HUMAN_CACHE = LOCAL_DIR / "tools" / "ave" / "cache" / "wan2_2"
DIGITAL_HUMAN_CACHE.mkdir(parents=True, exist_ok=True)

# 片尾默认文案
CLOSING_TEXT = "关注我，一起聆听世界"

# 默认参数
DEFAULT_RESOLUTION = "480P"
MAX_AUDIO_SEC = 20

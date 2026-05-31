"""
AVE 日志工具
"""
import logging
import sys
from pathlib import Path

LOG_DIR = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "ave" / "cache"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def get_logger(name: str = "ave") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # 控制台
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console)

    # 文件
    fh = logging.FileHandler(LOG_DIR / "ave.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(fh)

    return logger

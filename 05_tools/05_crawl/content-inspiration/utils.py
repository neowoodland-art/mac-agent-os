"""
口播素材系统 - 通用工具函数
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# 项目根目录（本文件所在目录的父级）
PROJECT_ROOT = Path(__file__).parent.resolve()


def load_config() -> dict:
    """加载 config.yaml 配置文件"""
    import yaml
    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    # 展开路径中的 ~
    for key in ("media_dir", "audio_dir", "raw_dir", "db_path", "logs_dir"):
        if key in config.get("storage", {}):
            config["storage"][key] = os.path.expanduser(config["storage"][key])
    return config


def get_db_path(config: dict = None) -> str:
    """获取数据库文件路径"""
    if config is None:
        config = load_config()
    db_path = config["storage"]["db_path"]
    if not os.path.isabs(db_path):
        db_path = str(PROJECT_ROOT / db_path)
    return db_path


def get_db(db_path: str = None) -> sqlite3.Connection:
    """获取数据库连接（开启 WAL 模式）"""
    if db_path is None:
        db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = None):
    """初始化数据库（执行 schema.sql）"""
    if db_path is None:
        db_path = get_db_path()
    schema_path = PROJECT_ROOT / "schema.sql"
    conn = get_db(db_path)
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.close()
    return db_path


def setup_logger(name: str, log_file: str = None, config: dict = None) -> logging.Logger:
    """配置日志"""
    if config is None:
        config = load_config()
    if log_file is None:
        logs_dir = config["storage"].get("logs_dir", "logs")
        if not os.path.isabs(logs_dir):
            logs_dir = str(PROJECT_ROOT / logs_dir)
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, f"{name}_{datetime.now():%Y%m%d}.log")

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    # 避免重复添加 handler
    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    sh.setLevel(logging.INFO)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def parse_jsonl(file_path: str) -> list[dict]:
    """逐行读取 JSONL 文件，返回字典列表"""
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"[WARN] JSONL 第 {line_no} 行解析失败: {e}")
    return records


def save_jsonl(records: list[dict], file_path: str, append: bool = True):
    """写入 JSONL 文件"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    mode = "a" if append else "w"
    with open(file_path, mode, encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def truncate_text(text: str, max_len: int = 20, ellipsis: str = "") -> str:
    """截断文本用于文件名"""
    if not text:
        return ""
    text = text.replace("/", "_").replace("\\", "_").replace(" ", "_")
    # 去除不合法文件名字符
    import re
    text = re.sub(r'[<>:"|?*]', '', text)
    if len(text) > max_len:
        return text[:max_len] + ellipsis
    return text


def check_omlx(config: dict = None) -> bool:
    """检查 oMLX 是否可用"""
    if config is None:
        config = load_config()
    import httpx
    try:
        resp = httpx.get(
            f"{config['llm']['base_url']}/models",
            headers={"Authorization": f"Bearer {config['llm']['api_key']}"},
            timeout=5
        )
        if resp.status_code == 200:
            models = [m["id"] for m in resp.json().get("data", [])]
            target = config["llm"]["model"]
            if target in models:
                print(f"[OK] oMLX 可用，模型: {target}")
                return True
            else:
                print(f"[WARN] oMLX 可用但缺少模型 {target}，已有: {models}")
                return False
    except Exception as e:
        print(f"[WARN] oMLX 不可用: {e}")
    return False

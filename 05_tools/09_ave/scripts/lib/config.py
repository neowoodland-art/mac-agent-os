"""
AVE 配置加载器
优先级: local.yaml > config.yaml > 默认值
"""
import os
from pathlib import Path
from typing import Any

import yaml

SYNC_ROOT = Path(__file__).resolve().parents[4]  # agent-sync/
LOCAL_ROOT = SYNC_ROOT.parent / "agent-local"     # agent-local/


def load_config() -> dict[str, Any]:
    """加载配置，local.yaml 覆盖 config.yaml 的对应字段"""
    config: dict[str, Any] = {}

    # 1. 模板配置
    template_path = SYNC_ROOT / "05_tools" / "09_ave" / "config.yaml"
    if template_path.exists():
        with open(template_path) as f:
            config.update(yaml.safe_load(f) or {})

    # 2. 本地配置（覆盖）
    local_path = LOCAL_ROOT / "tools" / "ave" / "config" / "local.yaml"
    if local_path.exists():
        with open(local_path) as f:
            local = yaml.safe_load(f) or {}
        _deep_merge(config, local)

    return config


def _deep_merge(base: dict, override: dict) -> None:
    """递归合并字典"""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def get_api_config(service: str) -> dict:
    """获取指定服务的 API 配置"""
    cfg = load_config()
    return cfg.get(service, {})

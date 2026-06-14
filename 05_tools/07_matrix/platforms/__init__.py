"""MC 平台插件 — 自动发现与注册"""

import importlib
import pkgutil
from pathlib import Path

_registry = {}


def discover_platforms():
    """自动扫描 platforms/ 目录下的所有插件"""
    global _registry
    _registry = {}
    here = Path(__file__).parent
    for entry in here.iterdir():
        if not entry.is_dir() or entry.name.startswith("__"):
            continue
        init_file = entry / "__init__.py"
        if not init_file.exists():
            continue
        try:
            mod = importlib.import_module(f"platforms.{entry.name}")
            if hasattr(mod, "register_platform"):
                name, instance = mod.register_platform()
                _registry[name] = instance
        except Exception as e:
            print(f"  ⚠️  插件 {entry.name} 加载失败: {e}")
    return _registry


def get_platform(name):
    if not _registry:
        discover_platforms()
    return _registry.get(name)


def list_platforms():
    if not _registry:
        discover_platforms()
    return dict(_registry)

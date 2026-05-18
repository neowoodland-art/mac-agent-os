# plugins/__init__.py
# Dashboard v4.0 插件自动发现与加载
# 扫描 plugins/ 目录下所有 plugin.py, 自动注册

import importlib, pkgutil, logging
from pathlib import Path

logger = logging.getLogger("dashboard.plugins")

# 插件白名单 (排除非插件文件)
_SKIP = {"base.py", "_registry.py", "__init__.py"}


def discover_plugins() -> dict[str, object]:
    """扫描 plugins/ 目录, 实例化所有 DashboardPlugin 子类"""
    plugins = {}
    pkg_dir = Path(__file__).parent

    for f in sorted(pkg_dir.iterdir()):
        if f.suffix != ".py" or f.name in _SKIP:
            continue
        mod_name = f"plugins.{f.stem}"
        try:
            mod = importlib.import_module(mod_name)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and attr.__name__ != "DashboardPlugin":
                    # 检查是否是 DashboardPlugin 的子类
                    from .base import DashboardPlugin as Base
                    if issubclass(attr, Base) and attr is not Base:
                        instance = attr()
                        if instance.name:
                            plugins[instance.name] = instance
                            logger.info(f"  ✅ 插件已加载: {instance.icon} {instance.label} (v{instance.version})")
        except Exception as e:
            logger.warning(f"  ⚠️ 插件加载失败: {f.name} — {e}")

    return plugins

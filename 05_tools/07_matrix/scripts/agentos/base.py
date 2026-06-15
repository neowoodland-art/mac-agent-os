"""
AgentOS 插件基类

所有领域插件继承此类，实现 register() 方法注册子命令。
插件放在 plugins/ 目录下，自动发现。
"""

import argparse
from pathlib import Path


class AgentOSPlugin:
    """领域插件基类"""

    name: str = ""          # 插件名称（对应子命令名）
    description: str = ""   # 插件描述
    nav: dict = None        # 看板导航定义
    """
    nav 格式:
    {
        'group': '社交矩阵',
        'icon': '📡',
        'order': 1,              # 排序，小的在前
        'items': [
            {'view': 'matrix-accounts', 'label': '账号管理'},
            {'view': 'matrix-exec', 'label': '运维执行'},
        ]
    }
    """

    def register(self, subparsers) -> argparse.ArgumentParser:
        """注册插件的子命令解析器
        
        Args:
            subparsers: 父解析器的子解析器组
            
        Returns:
            创建的 ArgumentParser 实例
        """
        raise NotImplementedError
    
    def dispatch(self, args: argparse.Namespace) -> int:
        """分发并执行命令
        
        Args:
            args: 解析后的参数
            
        Returns:
            退出码 (0=成功, 非0=失败)
        """
        raise NotImplementedError


def discover_plugins() -> list:
    """自动发现 plugins/ 目录下的所有插件
    
    扫描 plugins/ 目录，查找继承 AgentOSPlugin 的类。
    约定: 每个 .py 文件定义一个同名的 Plugin 类
          (如 matrix.py → MatrixPlugin)
    """
    import importlib
    import inspect
    
    plugins_dir = Path(__file__).parent / "plugins"
    if not plugins_dir.exists():
        return []
    
    discovered = []
    for f in sorted(plugins_dir.glob("*.py")):
        if f.name.startswith("_"):
            continue
        module_name = f"agentos.plugins.{f.stem}"
        try:
            module = importlib.import_module(module_name)
            # 查找模块中继承 AgentOSPlugin 的类
            for name, cls in inspect.getmembers(module, inspect.isclass):
                if (issubclass(cls, AgentOSPlugin) and cls is not AgentOSPlugin 
                    and hasattr(cls, 'name') and cls.name):
                    discovered.append(cls)
                    break
        except Exception as e:
            print(f"  ⚠️ 加载插件 {f.name} 失败: {e}")
    
    return discovered

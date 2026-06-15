"""
agentos matrix — 社交矩阵（抖音/小红书运营）

继承自 mc 所有功能，作为 agentos 的一个插件。
mc 命令保留为 agentos matrix 的快捷方式。
"""

import sys
from pathlib import Path

from agentos.base import AgentOSPlugin

# mc 模块路径（复用现有代码）
MC_DIR = Path(__file__).resolve().parent.parent.parent / "mc"
sys.path.insert(0, str(MC_DIR.parent))


class MatrixPlugin(AgentOSPlugin):
    name = "matrix"
    description = "社交矩阵 — 抖音/小红书账号运营、养号、采集、发布"

    def register(self, subparsers):
        """委托给 mc 的 build_parser()"""
        from mc.cli import build_parser
        return build_parser(subparsers, plugin_name="matrix")

    def dispatch(self, args):
        """委托给 mc 的命令分发"""
        if hasattr(args, 'func'):
            return args.func(args)
        print("未知命令，请使用 --help 查看帮助")
        return 1

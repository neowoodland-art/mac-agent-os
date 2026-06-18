"""
agentos matrix — 社交矩阵（抖音/小红书运营）

通过 mc CLI 的 build_parser 委托方式，继承全部 mc 命令。
mc 的账号/养号/采集/登录/评论/点赞/蓝图/语料库/发布等全部命令通过此插件暴露。

用法:
  agentos matrix run --accounts A,B --blueprints X --rounds 10
  agentos matrix collect --all
  agentos matrix account list
  agentos matrix publish douyin --account x --file video.mp4
"""

import sys
from pathlib import Path

from agentos.base import AgentOSPlugin

# 添加 scripts 目录到路径（复用现有代码）
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))


class MatrixPlugin(AgentOSPlugin):
    name = "matrix"
    description = "社交矩阵 — 抖音/小红书账号运营、养号、采集、发布"
    nav = {
        'group': '社交矩阵',
        'icon': '📡',
        'order': 2,
        'items': [
            {'view': 'matrix-sms-proxy', 'label': '账号管理'},
            {'view': 'matrix-commands', 'label': '运维执行'},
            {'view': 'matrix-blueprints', 'label': '内容编排'},
            {'view': 'matrix-c2', 'label': '任务调度'},
            {'view': 'matrix-settings', 'label': '系统设置'},
        ]
    }

    def register(self, subparsers):
        """委托给 mc 的 build_parser()，挂载全部子命令"""
        from mc.cli import build_parser as mc_build_parser
        return mc_build_parser(subparsers, plugin_name="matrix")

    def dispatch(self, args):
        """委托给 mc 的命令分发"""
        if hasattr(args, 'func'):
            return args.func(args)
        print(f"未知 matrix 命令，请使用: agentos matrix --help")
        return 1

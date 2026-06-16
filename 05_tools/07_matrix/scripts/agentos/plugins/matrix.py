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
        """委托给 mc 的 build_parser()，再加 publish 子命令"""
        import subprocess
        from mc.cli import build_parser
        parser = build_parser(subparsers, plugin_name="matrix")

        # 在 matrix 下添加 publish 子命令
        if parser and hasattr(parser, 'add_subparsers'):
            pub_parsers = parser.add_subparsers(dest="matrix_publish_action")
            p_pub = pub_parsers.add_parser("publish", help="视频/图文发布")
            p_pub.add_argument("platform", choices=["douyin", "xiaohongshu"], help="平台")
            p_pub.add_argument("--account", required=True, help="账号ID")
            p_pub.add_argument("--file", required=True, help="文件路径")
            p_pub.add_argument("--title", help="标题")
            p_pub.add_argument("--desc", help="描述")
            p_pub.set_defaults(matrix_publish_func=self.cmd_publish)

        return parser

    def dispatch(self, args):
        """委托给 mc 的命令分发 + publish 命令"""
        if hasattr(args, 'matrix_publish_func'):
            return args.matrix_publish_func(args)
        if hasattr(args, 'func'):
            return args.func(args)
        print("未知命令，请使用 --help 查看帮助")
        return 1

    def cmd_publish(self, args):
        """调用 publish_video.py 发布内容"""
        import subprocess, sys
        publish_script = MC_DIR.parent / "publish_video.py"
        if not publish_script.exists():
            print(f"发布脚本不存在: {publish_script}")
            return 1
        cmd = [sys.executable, str(publish_script), args.platform,
               "--account", args.account, "--file", args.file]
        if args.title:
            cmd += ["--title", args.title]
        if args.desc:
            cmd += ["--desc", args.desc]
        print(f"📤 发布到 {args.platform}: {args.file}")
        result = subprocess.run(cmd)
        return result.returncode

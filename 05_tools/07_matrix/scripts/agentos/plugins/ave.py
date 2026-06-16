"""
agentos ave — 视频工厂（渲染/脚本/素材/模板）

功能:
  render      视频渲染/生成
  script      脚本/文案生成
  material    素材管理
  template    模板管理
"""

import argparse
from pathlib import Path

from agentos.base import AgentOSPlugin

AGENT_SYNC = Path(__file__).resolve().parent.parent.parent.parent.parent


class AvePlugin(AgentOSPlugin):
    name = "ave"
    description = "视频工厂 — 渲染/脚本/素材/模板"
    nav = {
        'group': '视频工厂',
        'icon': '🎬',
        'order': 3,
        'items': [
            {'view': 'ave-render', 'label': '渲染任务'},
            {'view': 'ave-script', 'label': '脚本生成'},
            {'view': 'ave-materials', 'label': '素材库'},
            {'view': 'ave-templates', 'label': '模板'},
        ]
    }

    def register(self, subparsers):
        p = subparsers.add_parser("ave", help=self.description)
        p_sub = p.add_subparsers(dest="ave_action", help="视频工厂操作")

        # render
        pr = p_sub.add_parser("render", help="视频渲染/生成")
        pr.add_argument("--strategy", default="oral", help="策略: oral/beat-sync/digital-human")
        pr.add_argument("--script", help="脚本路径")
        pr.add_argument("--count", type=int, default=1, help="生成数量")
        pr.set_defaults(ave_func=self.cmd_render)

        # script
        ps = p_sub.add_parser("script", help="脚本/文案生成")
        ps.add_argument("action", nargs="?", default="list",
                       choices=["list", "generate", "edit"],
                       help="操作")
        ps.set_defaults(ave_func=self.cmd_script)

        # material
        pm = p_sub.add_parser("material", help="素材管理")
        pm.add_argument("action", nargs="?", default="list",
                       choices=["list", "search", "add"],
                       help="操作")
        pm.add_argument("--tag", help="标签过滤")
        pm.set_defaults(ave_func=self.cmd_material)

        # template
        pt = p_sub.add_parser("template", help="模板管理")
        pt.add_argument("action", nargs="?", default="list",
                       choices=["list", "create", "edit"],
                       help="操作")
        pt.set_defaults(ave_func=self.cmd_template)

        return p

    def dispatch(self, args):
        if hasattr(args, 'ave_func'):
            return args.ave_func(args)
        print("未知视频工厂命令，使用 agentos ave --help")
        return 1

    def cmd_render(self, args):
        print(f"🎬 渲染任务: strategy={args.strategy}, count={args.count}")
        print("(功能开发中，敬请期待 - 需要封装 AVE CLI)")
        return 0

    def cmd_script(self, args):
        print(f"📝 脚本 {args.action}")
        print("(功能开发中，敬请期待 - 需要封装 AVE CLI)")
        return 0

    def cmd_material(self, args):
        print(f"📦 素材 {args.action}" + (f" tag={args.tag}" if args.tag else ""))
        print("(功能开发中，敬请期待 - 需要封装 AVE CLI)")
        return 0

    def cmd_template(self, args):
        print(f"📋 模板 {args.action}")
        print("(功能开发中，敬请期待 - 需要封装 AVE CLI)")
        return 0

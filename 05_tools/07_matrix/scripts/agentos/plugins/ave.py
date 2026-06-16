"""
agentos ave — 视频工厂（渲染/脚本/素材/模板）

封装 09_ave/scripts/ 目录下的 96 个脚本，提供 CLI 统一入口。
"""

import argparse
import subprocess
import sys
from pathlib import Path

from agentos.base import AgentOSPlugin

AGENT_SYNC = Path(__file__).resolve().parent.parent.parent.parent.parent
AVE_SCRIPTS = AGENT_SYNC / "05_tools" / "09_ave" / "scripts"


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

    def _run_script(self, script_name: str, args: list[str] = None) -> int:
        """运行 AVE scripts 目录下的 Python 脚本"""
        script_path = AVE_SCRIPTS / script_name
        if not script_path.exists():
            print(f"脚本不存在: {script_path}")
            return 1
        cmd = [sys.executable, str(script_path)] + (args or [])
        result = subprocess.run(cmd, cwd=str(AVE_SCRIPTS))
        return result.returncode

    def register(self, subparsers):
        p = subparsers.add_parser("ave", help=self.description)
        p_sub = p.add_subparsers(dest="ave_action", help="视频工厂操作")

        # render - 视频渲染
        pr = p_sub.add_parser("render", help="视频渲染/生成")
        pr.add_argument("--strategy", default="oral", help="策略: oral/beat-sync/digital-human")
        pr.add_argument("--script", help="脚本路径")
        pr.add_argument("--count", type=int, default=1, help="生成数量")
        pr.set_defaults(ave_func=self.cmd_render)

        # script - 脚本/文案生成
        ps = p_sub.add_parser("script", help="脚本/文案生成")
        ps.add_argument("action", nargs="?", default="list",
                       choices=["list", "generate", "edit"],
                       help="操作")
        ps.add_argument("--topic", help="主题/方向")
        ps.add_argument("--style", help="风格: 口播/卡点/叙事")
        ps.set_defaults(ave_func=self.cmd_script)

        # material - 素材管理
        pm = p_sub.add_parser("material", help="素材管理")
        pm.add_argument("action", nargs="?", default="list",
                       choices=["list", "search", "add", "stats"],
                       help="操作")
        pm.add_argument("--tag", help="标签过滤")
        pm.add_argument("--type", dest="mat_type", help="素材类型: bgm/clip/character")
        pm.set_defaults(ave_func=self.cmd_material)

        # template - 模板管理
        pt = p_sub.add_parser("template", help="模板管理")
        pt.add_argument("action", nargs="?", default="list",
                       choices=["list", "create", "edit", "apply"],
                       help="操作")
        pt.set_defaults(ave_func=self.cmd_template)

        # character - 角色管理（包装 character_portrait.py）
        pch = p_sub.add_parser("character", help="角色管理")
        pch.add_argument("action", nargs="?", default="list",
                        choices=["list", "create", "generate"],
                        help="操作")
        pch.set_defaults(ave_func=self.cmd_character)

        # workflow - 工作流（包装 workflow 模块）
        pwf = p_sub.add_parser("workflow", help="工作流管理")
        pwf.add_argument("action", nargs="?", default="list",
                        choices=["list", "run", "status"],
                        help="操作")
        pwf.set_defaults(ave_func=self.cmd_workflow)

        return p

    def dispatch(self, args):
        if hasattr(args, 'ave_func'):
            return args.ave_func(args)
        print("未知视频工厂命令，使用 agentos ave --help")
        return 1

    def cmd_render(self, args):
        print(f"🎬 渲染任务: strategy={args.strategy}")
        if args.strategy == "oral":
            return self._run_script("01_director_parser/run.py", [f"--strategy={args.strategy}"])
        print(f"  调用 06_composer 模块 (strategy={args.strategy}, count={args.count})")
        return self._run_script("06_composer/run.py", [f"--strategy={args.strategy}", f"--count={args.count}"])

    def cmd_script(self, args):
        if args.action == "generate":
            print(f"📝 生成脚本: topic={args.topic or '(自动)'}, style={args.style or '口播'}")
            return self._run_script("01_director_parser/run.py",
                                    ["--action=generate_script"] +
                                    (["--topic", args.topic] if args.topic else []) +
                                    (["--style", args.style] if args.style else []))
        print(f"📝 脚本 {args.action}")
        return self._run_script("01_director_parser/run.py", [f"--action={args.action}"])

    def cmd_material(self, args):
        print(f"📦 素材 {args.action}" + (f" (tag={args.tag})" if args.tag else ""))
        return self._run_script("asset_manager/run.py",
                                [f"--action={args.action}"] +
                                (["--tag", args.tag] if args.tag else []) +
                                (["--type", args.mat_type] if args.mat_type else []))

    def cmd_template(self, args):
        print(f"📋 模板 {args.action}")
        if args.action == "list":
            return self._run_script("07_service_layer/template_manager.py", ["list"])
        elif args.action == "apply":
            print("(模板应用需要指定模板ID，功能开发中)")
        return 0

    def cmd_character(self, args):
        print(f"🧑 角色 {args.action}")
        return self._run_script("character_portrait.py", [f"--action={args.action}"])

    def cmd_workflow(self, args):
        print(f"🔧 工作流 {args.action}")
        return self._run_script("07_service_layer/workflow_engine.py", [f"--action={args.action}"])

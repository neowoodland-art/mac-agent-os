"""
agentos serve — 服务管理（MCP/Dashboard/调度）

功能:
  mcp         启动 MCP Server
  dashboard   启动/停止 Dashboard
  schedule    全局定时调度器
"""

import argparse
import subprocess
import sys
from pathlib import Path

from agentos.base import AgentOSPlugin

AGENT_SYNC = Path(__file__).resolve().parent.parent.parent.parent.parent


class ServePlugin(AgentOSPlugin):
    name = "serve"
    description = "服务管理 — MCP/Dashboard/调度"

    def register(self, subparsers):
        p = subparsers.add_parser("serve", help=self.description)
        p_sub = p.add_subparsers(dest="serve_action", help="服务操作")

        # dashboard
        pd = p_sub.add_parser("dashboard", help="启动/管理 Dashboard")
        pd.add_argument("action", nargs="?", default="start",
                       choices=["start", "stop", "restart", "status"],
                       help="操作")
        pd.add_argument("--port", type=int, default=9988, help="端口")
        pd.set_defaults(serve_func=self.cmd_dashboard)

        # mcp
        pm = p_sub.add_parser("mcp", help="启动 MCP Server")
        pm.set_defaults(serve_func=self.cmd_mcp)

        # schedule
        psc = p_sub.add_parser("schedule", help="定时任务管理")
        psc.add_argument("action", nargs="?", default="list",
                        choices=["list", "add", "remove"],
                        help="操作")
        psc.set_defaults(serve_func=self.cmd_schedule)

        return p

    def dispatch(self, args):
        if hasattr(args, 'serve_func'):
            return args.serve_func(args)
        print("未知服务命令，使用 agentos serve --help")
        return 1

    def cmd_dashboard(self, args):
        dashboard_dir = AGENT_SYNC / "05_tools" / "10_dashboard"
        run_py = dashboard_dir / "run.py"
        
        if not run_py.exists():
            print(f"Dashboard 不存在: {run_py}")
            return 1

        if args.action == "start":
            pid_file = dashboard_dir / ".dashboard.pid"
            if pid_file.exists():
                print("Dashboard 已在运行")
                return 0
            subprocess.Popen(
                [sys.executable, str(run_py), str(args.port)],
                cwd=str(dashboard_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"Dashboard 已启动 (port {args.port})")
        elif args.action == "stop":
            import subprocess
            subprocess.run(["pkill", "-f", f"run.py {args.port}"])
            print(f"Dashboard (port {args.port}) 已停止")
        elif args.action == "status":
            import subprocess
            r = subprocess.run(
                ["curl", "-s", "--connect-timeout", "2", 
                 f"http://localhost:{args.port}/api/identity"],
                capture_output=True, text=True)
            if r.returncode == 0 and r.stdout:
                print(f"Dashboard 运行中 (port {args.port})")
            else:
                print(f"Dashboard 未运行 (port {args.port})")
        return 0

    def cmd_mcp(self, args):
        print("MCP Server 启动中...")
        print("(功能开发中，敬请期待)")
        return 0

    def cmd_schedule(self, args):
        print(f"定时任务 {args.action}")
        print("(功能开发中，敬请期待)")
        return 0

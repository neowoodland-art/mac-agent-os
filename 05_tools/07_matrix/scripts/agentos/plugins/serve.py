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

AGENT_SYNC = Path(__file__).resolve().parent.parent.parent.parent.parent.parent  # x6 → agent-sync/


class ServePlugin(AgentOSPlugin):
    name = "serve"
    description = "服务管理 — MCP/Dashboard/调度"
    nav = {
        'group': '系统设置',
        'icon': '⚙️',
        'order': 5,
        'items': [
            {'view': 'kb', 'label': '知识库'},
        ]
    }

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

        # guardd
        pg = p_sub.add_parser("guardd", help="系统自愈守护进程")
        pg.add_argument("action", nargs="?", default="start",
                       choices=["start", "stop", "status"],
                       help="操作")
        pg.add_argument("--daemon", action="store_true", help="后台运行")
        pg.set_defaults(serve_func=self.cmd_guardd)

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

    def cmd_guardd(self, args):
        """系统自愈守护进程"""
        import subprocess, os
        from pathlib import Path

        SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent
        guardd_script = str(SCRIPTS_DIR / "guardd.py")

        if args.action == "start":
            if args.daemon:
                log_file = os.path.expanduser(
                    "~/workbuddy-agent-os/agent-local/runtime/guardd/daemon.log")
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                pid = subprocess.Popen(
                    [sys.executable, guardd_script],
                    stdout=open(log_file, 'w'), stderr=subprocess.STDOUT,
                ).pid
                print(f"🛡️  guardd 已后台启动 (PID: {pid})")
                print(f"   日志: {log_file}")
            else:
                os.execvp(sys.executable, [sys.executable, guardd_script])
        elif args.action == "stop":
            try:
                subprocess.run(["pkill", "-f", "guardd.py"], capture_output=True, timeout=5)
                print("⏹  guardd 已停止")
            except Exception as e:
                print(f"❌ 停止失败: {e}")
        elif args.action == "status":
            sf = os.path.expanduser(
                "~/workbuddy-agent-os/agent-local/runtime/guardd/status.json")
            if os.path.exists(sf):
                import json
                try:
                    d = json.loads(open(sf).read())
                    print(f"🛡️  guardd 状态")
                    print(f"   最后检查: {d.get('last_check','?')}")
                    print(f"   孤儿进程: {d.get('orphans',0)}")
                    print(f"   磁盘: {d.get('disk_gb','?')}GB")
                    print(f"   浏览器: {d.get('browsers',0)}")
                    if d.get('events'):
                        print(f"   事件: {'; '.join(d['events'])}")
                except:
                    print("🛡️  guardd 状态文件损坏")
            else:
                print("🛡️  guardd 未运行")
        return 0

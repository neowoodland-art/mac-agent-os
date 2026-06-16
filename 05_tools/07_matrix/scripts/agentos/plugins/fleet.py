"""
agentos fleet — 联邦管理（多机协同）

功能:
  sync       一键同步所有机器
  reconcile  对账检查
  exec       远程执行命令
  status     集群状态
"""

import argparse
import subprocess
import sys
from pathlib import Path

from agentos.base import AgentOSPlugin

AGENT_SYNC = Path(__file__).resolve().parent.parent.parent.parent.parent


class FleetPlugin(AgentOSPlugin):
    name = "fleet"
    description = "联邦管理 — 多机协同、同步、对账"
    nav = {
        'group': '联邦管理',
        'icon': '🖥️',
        'order': 4,
        'items': [
            {'view': 'matrix-summary', 'label': '集群概览'},
            {'view': 'machines', 'label': '机器状态'},
        ]
    }

    def register(self, subparsers):
        p = subparsers.add_parser("fleet", help=self.description)
        p_sub = p.add_subparsers(dest="fleet_action", help="联邦操作")

        # sync
        ps = p_sub.add_parser("sync", help="一键同步所有机器")
        ps.set_defaults(fleet_func=self.cmd_sync)

        # reconcile
        pr = p_sub.add_parser("reconcile", help="对账检查")
        pr.set_defaults(fleet_func=self.cmd_reconcile)

        # exec
        pe = p_sub.add_parser("exec", help="在远程机器执行命令")
        pe.add_argument("host", help="目标机器名或 Tailscale IP")
        pe.add_argument("command", nargs="+", help="要执行的命令")
        pe.set_defaults(fleet_func=self.cmd_exec)

        # status
        ps2 = p_sub.add_parser("status", help="集群状态")
        ps2.set_defaults(fleet_func=self.cmd_status)

        return p

    def dispatch(self, args):
        if hasattr(args, 'fleet_func'):
            return args.fleet_func(args)
        print("未知联邦命令，使用 agentos fleet --help")
        return 1

    def cmd_sync(self, args):
        fleet_sh = AGENT_SYNC / "00_bootstrap" / "fleet_sync.sh"
        if fleet_sh.exists():
            subprocess.run(["bash", str(fleet_sh)])
        else:
            print(f"fleet_sync.sh 不存在: {fleet_sh}")
        return 0

    def cmd_reconcile(self, args):
        rec_sh = AGENT_SYNC / "00_bootstrap" / "fleet_reconcile.sh"
        if rec_sh.exists():
            subprocess.run(["bash", str(rec_sh)])
        else:
            print(f"fleet_reconcile.sh 不存在: {rec_sh}")
        return 0

    def cmd_exec(self, args):
        """执行远程命令（委托给 mc remote exec）"""
        from mc.cli import cmd_remote, _lookup_machines, _ssh_call
        # 构造 args 对象
        class FakeArgs:
            remote_action = "exec"
            host = args.host
            command = args.command
            via = "ssh"
            json = False
        cmd_remote(FakeArgs())
        return 0

    def cmd_status(self, args):
        from mc.cli import cmd_remote, _lookup_machines
        class FakeArgs:
            remote_action = "status"
            host = ""
            json = False
        cmd_remote(FakeArgs())
        return 0

    def cmd_cleanup(self, args):
        """清理所有机器残留的 Playwright 驱动进程"""
        import subprocess
        machines = [
            ("本机", "127.0.0.1", ""),
            ("5kechengdeAir", "100.72.182.121", "5kecheng"),
            ("7kecheng", "100.65.35.28", "7kecheng"),
        ]
        for name, ip, user in machines:
            print(f"\n  → {name} ({ip})...")
            if name == "本机":
                result = subprocess.run(
                    ["pkill", "-f", "playwright/driver/node"], 
                    capture_output=True, text=True)
                print(f"    已清理" if result.returncode == 0 else "    无残留")
            else:
                result = subprocess.run(
                    ["ssh", user, ip, "pkill -f playwright/driver/node"],
                    capture_output=True, text=True)
                print(f"    已清理" if result.returncode == 0 else "    无残留")
        print("\n  ✅ 清理完成")
        return 0

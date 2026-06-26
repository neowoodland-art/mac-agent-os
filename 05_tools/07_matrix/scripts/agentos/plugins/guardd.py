"""
agentos guardd — 节点代理管理

功能:
  status    查看 guardd 运行状态
  restart   重启 guardd
  logs      查看 guardd 日志
  install   安装/更新 guardd plist
  tasks     列出运行中任务
  stop      停止指定任务
"""

import argparse, json, os, subprocess, time, urllib.request, urllib.error
from pathlib import Path

from agentos.base import AgentOSPlugin

AGENT_SYNC = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
GUARDD_PORT = 9090


def _guardd_api(path: str) -> dict:
    """调用本地 guardd HTTP API"""
    try:
        r = urllib.request.urlopen(f"http://localhost:{GUARDD_PORT}{path}", timeout=5)
        return json.loads(r.read().decode())
    except Exception:
        return {}


class GuarddPlugin(AgentOSPlugin):
    name = "guardd"
    description = "节点代理管理 — 部署/监控/任务管理"

    def register(self, subparsers):
        p = subparsers.add_parser("guardd", help=self.description)
        p_sub = p.add_subparsers(dest="guardd_action", help="操作")

        ps = p_sub.add_parser("status", help="查看 guardd 运行状态")
        ps.set_defaults(guardd_func=self.cmd_status)

        pr = p_sub.add_parser("restart", help="重启 guardd")
        pr.set_defaults(guardd_func=self.cmd_restart)

        pl = p_sub.add_parser("logs", help="查看 guardd 日志")
        pl.add_argument("--tail", type=int, default=30, help="显示行数")
        pl.set_defaults(guardd_func=self.cmd_logs)

        pi = p_sub.add_parser("install", help="安装/更新 guardd plist 并重启")
        pi.set_defaults(guardd_func=self.cmd_install)

        pt = p_sub.add_parser("tasks", help="列出运行中任务")
        pt.set_defaults(guardd_func=self.cmd_tasks)

        pk = p_sub.add_parser("stop", help="停止指定任务")
        pk.add_argument("run_id", help="任务 ID")
        pk.set_defaults(guardd_func=self.cmd_stop)

        return p

    def dispatch(self, args):
        if hasattr(args, 'guardd_func'):
            return args.guardd_func(args)
        print("未知 guardd 命令，使用 agentos guardd --help")
        return 1

    def cmd_status(self, args):
        """查看 guardd 状态"""
        # launchctl 状态
        r = subprocess.run(
            ["launchctl", "print", f"gui/{os.getuid()}/com.agentos.guardd"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            for line in r.stdout.split("\n"):
                if "state = " in line:
                    print(f"  launchd: 🟢 {line.strip()}")
        else:
            print("  launchd: ❌ 未运行")

        # HTTP 健康检查
        health = _guardd_api("/health")
        if health:
            print(f"  HTTP:   🟢 运行中 (端口 {GUARDD_PORT})")
            print(f"  版本:   {health.get('version', '?')}")
            print(f"  运行:   {health.get('uptime_sec', 0)}s")
            print(f"  任务:   {health.get('running_tasks', 0)} 运行中 / {health.get('total_tasks', 0)} 总计")
        else:
            print(f"  HTTP:   ❌ 无法连接 (localhost:{GUARDD_PORT})")
        return 0

    def cmd_restart(self, args):
        """重启 guardd"""
        print("  ⏹ 停止 guardd...")
        subprocess.run(["launchctl", "unload", str(Path.home() / "Library/LaunchAgents/com.agentos.guardd.plist")],
                       capture_output=True, timeout=5)
        time.sleep(1)
        print("  🚀 启动 guardd...")
        subprocess.run(["launchctl", "load", str(Path.home() / "Library/LaunchAgents/com.agentos.guardd.plist")],
                       capture_output=True, timeout=5)
        time.sleep(2)
        health = _guardd_api("/health")
        print(f"  {'✅ guardd 已重启' if health else '❌ guardd 启动失败'}")
        return 0

    def cmd_logs(self, args):
        """查看 guardd 日志"""
        log_file = Path.home() / "workbuddy-agent-os" / "agent-local" / "runtime" / "guardd" / "guardd.log"
        if log_file.exists():
            lines = log_file.read_text().splitlines()
            tail = lines[-args.tail:]
            print(f"  📋 guardd.log (最后 {args.tail} 行):\n")
            for line in tail:
                print(f"    {line}")
        else:
            print("  ❌ 日志文件不存在")
        return 0

    def cmd_install(self, args):
        """安装/更新 guardd plist"""
        plist_src = AGENT_SYNC / "05_tools" / "00_setup" / "guardd" / "com.agentos.guardd.plist"
        plist_dst = Path.home() / "Library/LaunchAgents" / "com.agentos.guardd.plist"
        if not plist_src.exists():
            print(f"  ❌ 源 plist 不存在: {plist_src}")
            return 1
        # 替换 __HOME__ 占位符
        content = plist_src.read_text().replace("__HOME__", str(Path.home()))
        plist_dst.write_text(content)
        print(f"  ✅ plist 已安装: {plist_dst}")
        return self.cmd_restart(args)

    def cmd_tasks(self, args):
        """列出 guardd 任务"""
        tasks = _guardd_api("/tasks")
        if not isinstance(tasks, list):
            print("  ❌ 无法获取任务列表（guardd HTTP 不可用）")
            return 1
        if not tasks:
            print("  📭 无任务记录")
            return 0
        print(f"  📋 共 {len(tasks)} 个任务:\n")
        for t in tasks:
            status = t.get("status", "?")
            icon = {"running": "🟢", "completed": "✅", "failed": "❌", "cancelled": "⏹"}.get(status, "❓")
            cmd = t.get("cmd", "")[:60]
            pid = t.get("pid", "?")
            elapsed = ""
            if t.get("start_time"):
                import datetime
                st = datetime.datetime.fromisoformat(t["start_time"])
                elapsed = f"{(datetime.datetime.now(datetime.timezone.utc) - st).total_seconds():.0f}s"
            print(f"    {icon} {t.get('run_id','?')[:12]} | {status:10s} | PID={pid} | {elapsed:>6s} | {cmd}")
        return 0

    def cmd_stop(self, args):
        """停止任务"""
        result = _guardd_api(f"/task/{args.run_id}/stop")
        if result.get("status") in ("stopped", "already_stopped"):
            print(f"  ⏹ 任务 {args.run_id} 已停止")
        else:
            print(f"  ❌ 停止失败: {result.get('error', '未知错误')}")
        return 0

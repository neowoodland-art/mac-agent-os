"""
agentos crawl — 内容采集（网页/视频/提取/调度）

封装 05_crawl/ 目录下的采集脚本 + web_crawler 技能。
"""

import argparse
import subprocess
import sys
from pathlib import Path

from agentos.base import AgentOSPlugin

AGENT_SYNC = Path(__file__).resolve().parent.parent.parent.parent.parent
CRAWL_DIR = AGENT_SYNC / "05_tools" / "05_crawl"


class CrawlPlugin(AgentOSPlugin):
    name = "crawl"
    description = "内容采集 — 网页/视频/提取/调度"
    nav = {
        'group': '内容采集',
        'icon': '📡',
        'order': 4,
        'items': [
            {'view': 'crawl-tasks', 'label': '采集任务'},
            {'view': 'crawl-sources', 'label': '源管理'},
            {'view': 'crawl-history', 'label': '采集历史'},
        ]
    }

    def _run_script(self, script_name: str, args: list[str] = None) -> int:
        """运行 crawl 目录下的 Python 脚本"""
        script_path = CRAWL_DIR / script_name
        if not script_path.exists():
            print(f"脚本不存在: {script_path}")
            return 1
        cmd = [sys.executable, str(script_path)] + (args or [])
        result = subprocess.run(cmd, cwd=str(CRAWL_DIR))
        return result.returncode

    def register(self, subparsers):
        p = subparsers.add_parser("crawl", help=self.description)
        p_sub = p.add_subparsers(dest="crawl_action", help="采集操作")

        # web - 网页抓取
        pw = p_sub.add_parser("web", help="网页内容抓取")
        pw.add_argument("url", nargs="?", help="目标 URL")
        pw.add_argument("--output", help="输出文件路径")
        pw.add_argument("--depth", type=int, default=1, help="抓取深度")
        pw.set_defaults(crawl_func=self.cmd_web)

        # video - 视频下载
        pv = p_sub.add_parser("video", help="视频下载")
        pv.add_argument("url", nargs="?", help="视频 URL")
        pv.add_argument("--format", default="mp4", help="输出格式")
        pv.set_defaults(crawl_func=self.cmd_video)

        # extract - 信息提取
        pe = p_sub.add_parser("extract", help="信息提取")
        pe.add_argument("file", nargs="?", help="目标文件路径")
        pe.add_argument("--fields", help="提取字段 (逗号分隔)")
        pe.add_argument("--url", help="从 URL 提取")
        pe.set_defaults(crawl_func=self.cmd_extract)

        # schedule - 定时采集
        psc = p_sub.add_parser("schedule", help="采集定时任务")
        psc.add_argument("action", nargs="?", default="list",
                        choices=["list", "add", "remove"],
                        help="操作")
        psc.set_defaults(crawl_func=self.cmd_schedule)

        # source - 采集源管理
        ps = p_sub.add_parser("source", help="采集源管理")
        ps.add_argument("action", nargs="?", default="list",
                       choices=["list", "add", "remove", "test"],
                       help="操作")
        ps.add_argument("--name", help="源名称")
        ps.add_argument("--url", dest="src_url", help="源URL")
        ps.add_argument("--type", dest="src_type",
                       choices=["rss", "web", "api", "social"],
                       help="源类型")
        ps.set_defaults(crawl_func=self.cmd_source)

        # content-inspiration - 内容灵感采集
        pci = p_sub.add_parser("inspiration", help="内容灵感采集")
        pci.add_argument("action", nargs="?", default="daily",
                        choices=["daily", "trending", "search"],
                        help="操作")
        pci.add_argument("--keyword", help="搜索关键词")
        pci.set_defaults(crawl_func=self.cmd_inspiration)

        return p

    def dispatch(self, args):
        if hasattr(args, 'crawl_func'):
            return args.crawl_func(args)
        print("未知采集命令，使用 agentos crawl --help")
        return 1

    def cmd_web(self, args):
        print(f"🌐 网页抓取: {args.url or '(交互模式)'}")
        if args.url:
            return self._run_script("content-inspiration/run.py",
                                    ["web", args.url] +
                                    (["--output", args.output] if args.output else []))
        print("请提供 URL: agentos crawl web <url>")
        return 1

    def cmd_video(self, args):
        print(f"🎥 视频下载: {args.url or '(交互模式)'}")
        if args.url:
            return self._run_script("content-inspiration/run.py",
                                    ["video", args.url, "--format", args.format])
        print("请提供视频 URL: agentos crawl video <url>")
        return 1

    def cmd_extract(self, args):
        print(f"🔍 信息提取: {args.file or '(交互模式)'}")
        if args.file:
            cmd = ["extract", args.file]
            if args.fields:
                cmd += ["--fields", args.fields]
            return self._run_script("content-inspiration/run.py", cmd)
        if args.url:
            return self._run_script("content-inspiration/run.py", ["extract", "--url", args.url])
        print("请指定文件或URL: agentos crawl extract <file> 或 --url <url>")
        return 1

    def cmd_schedule(self, args):
        print(f"⏰ 采集定时任务 {args.action}")
        return self._run_script("content-inspiration/run.py", ["schedule", args.action])

    def cmd_source(self, args):
        print(f"📡 采集源 {args.action}")
        cmd = ["source", args.action]
        if args.name:
            cmd += ["--name", args.name]
        if args.src_url:
            cmd += ["--url", args.src_url]
        if args.src_type:
            cmd += ["--type", args.src_type]
        return self._run_script("content-inspiration/run.py", cmd)

    def cmd_inspiration(self, args):
        print(f"💡 内容灵感 {args.action}")
        cmd = ["inspiration", args.action]
        if args.keyword:
            cmd += ["--keyword", args.keyword]
        return self._run_script("content-inspiration/run.py", cmd)

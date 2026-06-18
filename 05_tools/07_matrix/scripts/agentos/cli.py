"""
agentos CLI — 主分发器

自动发现 plugins/ 目录下的插件，注册为子命令。
"""

import argparse
import sys

from agentos.base import discover_plugins
from agentos import __version__


BANNER = """
╔══════════════════════════════════════╗
║   AgentOS v%s                  ║
║   联邦智能体统一命令入口              ║
╚══════════════════════════════════════╝
""" % __version__


def build_parser():
    parser = argparse.ArgumentParser(
        prog="agentos",
        description="AgentOS — 联邦智能体统一命令入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
领域:
  matrix    社交矩阵 — 抖音/小红书账号运营
  ave       视频工厂 — 视频制作与编辑
  crawl     内容采集 — 互联网内容抓取
  fleet     联邦管理 — 多机协同
  serve     服务管理 — MCP/Dashboard/调度

示例:
  agentos matrix run --accounts douyin_01 --blueprints douyin_daily
  agentos matrix collect --all
  agentos fleet sync
  agentos serve mcp
  agentos --help
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("--json", action="store_true", help="JSON 输出格式")
    parser.add_argument("--version", action="store_true", help="显示版本号")
    
    sub = parser.add_subparsers(dest="domain", help="领域")

    # 自动发现并注册插件
    plugins = discover_plugins()
    for plugin_cls in plugins:
        plugin = plugin_cls()
        plugin.register(sub)

    return parser, plugins


def main():
    parser, plugins = build_parser()
    # 用 parse_known_args 允许未知参数（如 --account --file）透传到子命令
    args, _unknown = parser.parse_known_args()

    if args.version:
        print(f"AgentOS v{__version__}")
        return

    if not args.domain:
        parser.print_help()
        return

    # 查找对应的插件并分发
    for plugin_cls in plugins:
        plugin = plugin_cls()
        if args.domain == plugin.name:
            sys.exit(plugin.dispatch(args))

    # 没找到插件
    print(f"未知领域: {args.domain}")
    print("可用领域: " + ", ".join(p.name for _, p in 
          [(None, p()) for p in plugins]))
    sys.exit(1)


if __name__ == "__main__":
    main()

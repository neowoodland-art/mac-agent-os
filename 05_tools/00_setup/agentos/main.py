#!/usr/bin/env python3
"""
agentos — AgentOS 系统管理 CLI 主入口

用法:
    agentos                   显示帮助
    agentos init              换机一键初始化
    agentos sync              双机增量同步
    agentos skill <子命令>    技能管理
    agentos tool <子命令>     工具管理
    agentos check             全系统健康检查
    agentos backup            备份 agent-local/
    agentos restore <路径>    从备份还原
"""

import sys
import argparse

from .const import __version__
from .utils import banner


def main():
    parser = argparse.ArgumentParser(
        prog="agentos",
        description="AgentOS 系统管理 CLI — 初始化 / 同步 / 技能管理 / 备份还原 / 健康检查",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    agentos init                换机一键初始化
    agentos skill list          列出所有技能
    agentos skill build my_skill  打包技能
    agentos backup              备份本地数据
    agentos check               全系统健康检查
        """,
    )
    parser.add_argument(
        "--version", action="version", version=f"agentos v{__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # ---- init ----
    p_init = subparsers.add_parser(
        "init", help="换机一键初始化：目录/依赖/技能/MCP/自动化"
    )
    p_init.add_argument("--dry-run", action="store_true", help="仅预览，不执行")
    p_init.add_argument("--skip-deps", action="store_true", help="跳过依赖安装")

    # ---- sync ----
    p_sync = subparsers.add_parser(
        "sync", help="双机增量同步：检测差异并更新本地 WorkBuddy"
    )
    p_sync.add_argument("--dry-run", action="store_true", help="仅报告差异，不执行")
    p_sync.add_argument("--force", action="store_true", help="强制全量覆盖")

    # ---- skill ----
    p_skill = subparsers.add_parser("skill", help="技能管理")
    skill_sub = p_skill.add_subparsers(dest="skill_cmd", help="技能子命令")

    p_skill_list = skill_sub.add_parser("list", help="列出所有可用技能")
    p_skill_list.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")

    skill_sub.add_parser("install", help="安装/更新所有技能到 WorkBuddy")
    skill_sub.add_parser("check", help="检查技能一致性")

    p_skill_build = skill_sub.add_parser("build", help="打包技能为 .skill 压缩包")
    p_skill_build.add_argument("skill_name", help="技能名称（对应 02_skills/ 下的目录名）")
    p_skill_build.add_argument("--output", "-o", default=None, help="输出路径（默认: 07_migration/exports/）")

    p_skill_search = skill_sub.add_parser("search", help="搜索技能")
    p_skill_search.add_argument("keyword", help="搜索关键词")

    p_skill_rm = skill_sub.add_parser("uninstall", help="从 WorkBuddy 卸载技能")
    p_skill_rm.add_argument("skill_name", help="技能名称")

    # ---- tool ----
    p_tool = subparsers.add_parser("tool", help="工具管理")
    tool_sub = p_tool.add_subparsers(dest="tool_cmd", help="工具子命令")
    tool_sub.add_parser("list", help="列出所有可用工具")

    # ---- config ----
    from . import config_mgr as config_mod
    config_mod.setup_parser(subparsers)

    # ---- check ----
    p_check = subparsers.add_parser("check", help="全系统健康检查")
    p_check.add_argument("--quick", action="store_true", help="快速检查（仅核心项）")

    # ---- backup ----
    p_backup = subparsers.add_parser("backup", help="备份 agent-local/（materials + memory/raw）")
    p_backup.add_argument("--output", "-o", default=None, help="输出目录（默认: 当前目录）")
    p_backup.add_argument("--full", action="store_true", help="打包 agent-sync/ + agent-local/ 全量")

    # ---- upgrade ----
    from . import upgrade as upgrade_mod
    upgrade_mod.setup_parser(subparsers)

    # ---- restore ----
    p_restore = subparsers.add_parser("restore", help="从备份文件还原 agent-local/")
    p_restore.add_argument("backup_path", help="备份文件路径（.tar.gz）")
    p_restore.add_argument("--force", action="store_true", help="覆盖现有文件")

    # ---- rebuild-vector ----
    p_vector = subparsers.add_parser("rebuild-vector", help="本地重建向量数据库（升级后执行）")
    p_vector.add_argument("--track", choices=["local", "global", "both"], default="both",
                         help="重建范围 (默认 both)")
    p_vector.add_argument("--incremental", action="store_true", help="增量模式")
    p_vector.add_argument("--dry-run", action="store_true", help="仅预览，不执行")

    # ---- localize ----
    p_localize = subparsers.add_parser("localize", help="从模板生成本机身份配置")

    # ---- register ----
    p_register = subparsers.add_parser("register", help="注册本机到集群注册表")

    # ---- cluster-status ----
    p_cs = subparsers.add_parser("cluster-status", help="查看集群所有机器状态")

    # ---- cluster-cleanup ----
    p_cc = subparsers.add_parser("cluster-cleanup", help="清理过期注册条目")

    # ---- 解析 ----
    args = parser.parse_args()

    # 无参数 → 显示帮助
    if not args.command:
        banner()
        parser.print_help()
        print()
        print("  输入 agentos <command> --help 查看子命令详情")
        print()
        return

    # 路由到各子模块
    if args.command == "init":
        from . import init as mod
        mod.do_init(args)
    elif args.command == "sync":
        from . import sync as mod
        mod.run(args)
    elif args.command == "skill":
        from . import skill_mgr as mod
        mod.run(args)
    elif args.command == "tool":
        from . import tool_mgr as mod
        mod.run(args)
    elif args.command == "config":
        from . import config_mgr as mod
        mod.run(args)
    elif args.command == "check":
        from . import check as mod
        mod.cmd_run(args)
    elif args.command == "backup":
        from . import backup as mod
        mod.run(args)
    elif args.command == "upgrade":
        from . import upgrade as mod
        mod.do_upgrade(args)
    elif args.command == "restore":
        from . import backup as mod
        mod.run_restore(args)
    elif args.command == "rebuild-vector":
        from . import upgrade as mod
        mod.do_rebuild_vector(args)
    elif args.command == "localize":
        from . import init as mod
        mod.do_localize(args)
    elif args.command == "register":
        from . import upgrade as mod
        mod.do_cluster_register(args)
    elif args.command == "cluster-status":
        from . import upgrade as mod
        mod.do_cluster_status(args)
    elif args.command == "cluster-cleanup":
        from . import upgrade as mod
        mod.do_cluster_cleanup(args)


if __name__ == "__main__":
    main()

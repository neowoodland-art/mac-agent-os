#!/usr/bin/env python3
"""
agentos — AgentOS 统一命令入口

系统管理:
    agentos init              换机一键初始化
    agentos sync              双机增量同步
    agentos skill <子命令>    技能管理
    agentos tool <子命令>     工具管理
    agentos config <子命令>   配置管理
    agentos check             全系统健康检查
    agentos backup            备份 agent-local/
    agentos upgrade           模块升级
    agentos restore <路径>    从备份还原
    agentos rebuild-vector    重建向量数据库
    agentos localize          生成本机身份
    agentos register          注册到集群
    agentos cluster-status    集群状态
    agentos cluster-cleanup   清理集群

联邦管理（来自 07_matrix/scripts/agentos/plugins/）:
    agentos matrix            社交矩阵 — 抖音/小红书运营
    agentos ave               视频工厂 — 视频制作与编辑
    agentos crawl             内容采集 — 互联网内容抓取
    agentos fleet             联邦管理 — 多机协同
    agentos serve             服务管理 — MCP/Dashboard/调度
"""

import sys
import argparse
import importlib.util
from pathlib import Path

from .const import __version__
from .utils import banner, get_sync_root


def _load_federation_plugins():
    """从 07_matrix/scripts/agentos/ 加载联邦插件"""
    sync_root = get_sync_root()
    plugin_base = sync_root / "05_tools" / "07_matrix" / "scripts" / "agentos" / "plugins"
    if not plugin_base.exists():
        return []

    # 动态加载 agentos.base 模块
    agentos_pkg = plugin_base.parent
    spec = importlib.util.spec_from_file_location(
        "agentos.base",
        agentos_pkg / "base.py",
        submodule_search_locations=[str(agentos_pkg)]
    )
    if not spec or not spec.loader:
        return []

    base_mod = importlib.util.module_from_spec(spec)
    sys.modules["agentos.base"] = base_mod
    spec.loader.exec_module(base_mod)

    # 扫描 plugins/ 下的每个 .py 文件
    plugins = []
    for f in sorted(plugin_base.iterdir()):
        if f.name.startswith("_") or f.suffix != ".py":
            continue
        # 动态加载插件模块
        mod_name = f"agentos.plugins.{f.stem}"
        spec = importlib.util.spec_from_file_location(
            mod_name, f,
            submodule_search_locations=[str(plugin_base)]
        )
        if not spec or not spec.loader:
            continue
        mod = importlib.util.module_from_spec(spec)
        # 让模块中的 `from agentos.base import ...` 能找到 base
        sys.modules["agentos"] = type(sys)("agentos")
        sys.modules["agentos"].plugins = type(sys)("plugins")
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)

        # 查找 AgentOSPlugin 子类
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if isinstance(attr, type) and issubclass(attr, base_mod.AgentOSPlugin) and attr is not base_mod.AgentOSPlugin:
                plugins.append(attr())

    return plugins, base_mod


def main():
    parser = argparse.ArgumentParser(
        prog="agentos",
        description="AgentOS 统一命令入口 — 系统管理 + 联邦管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
系统管理:
    agentos init / sync / skill / tool / config / check
    agentos backup / restore / upgrade / rebuild-vector
    agentos register / cluster-status / cluster-cleanup

联邦管理:
    agentos matrix / ave / crawl / fleet / serve

参见:
    agentos <command> --help
        """,
    )
    parser.add_argument(
        "--version", action="version", version=f"agentos v{__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # ---- 系统管理命令 ----
    p_init = subparsers.add_parser(
        "init", help="换机一键初始化：目录/依赖/技能/MCP/自动化"
    )
    p_init.add_argument("--dry-run", action="store_true", help="仅预览，不执行")
    p_init.add_argument("--skip-deps", action="store_true", help="跳过依赖安装")

    p_sync = subparsers.add_parser(
        "sync", help="双机增量同步：检测差异并更新本地 WorkBuddy"
    )
    p_sync.add_argument("--dry-run", action="store_true", help="仅报告差异，不执行")
    p_sync.add_argument("--force", action="store_true", help="强制全量覆盖")

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

    p_tool = subparsers.add_parser("tool", help="工具管理")
    tool_sub = p_tool.add_subparsers(dest="tool_cmd", help="工具子命令")
    tool_sub.add_parser("list", help="列出所有可用工具")
    p_tool_trae = tool_sub.add_parser("trae", help="Trae Agent AI 编程助手")
    trae_sub = p_tool_trae.add_subparsers(dest="trae_cmd", help="trae 子命令")
    p_trae_run = trae_sub.add_parser("run", help="执行任务")
    p_trae_run.add_argument("task", nargs="*", help="任务描述")
    p_trae_run.add_argument("-p", "--provider", help="LLM 提供商")
    p_trae_run.add_argument("-m", "--model", help="模型名称")
    p_trae_run.add_argument("-f", "--file", help="从文件读取任务")
    trae_sub.add_parser("interactive", help="交互式模式")
    trae_sub.add_parser("config", help="查看配置")
    trae_sub.add_parser("install", help="安装 trae-agent")

    from . import config_mgr as config_mod
    config_mod.setup_parser(subparsers)

    p_check = subparsers.add_parser("check", help="全系统健康检查")
    p_check.add_argument("--quick", action="store_true", help="快速检查（仅核心项）")

    p_backup = subparsers.add_parser("backup", help="备份 agent-local/（materials + memory/raw）")
    p_backup.add_argument("--output", "-o", default=None, help="输出目录（默认: 当前目录）")
    p_backup.add_argument("--full", action="store_true", help="打包 agent-sync/ + agent-local/ 全量")

    from . import upgrade as upgrade_mod
    upgrade_mod.setup_parser(subparsers)

    p_restore = subparsers.add_parser("restore", help="从备份文件还原 agent-local/")
    p_restore.add_argument("backup_path", help="备份文件路径（.tar.gz）")
    p_restore.add_argument("--force", action="store_true", help="覆盖现有文件")

    p_vector = subparsers.add_parser("rebuild-vector", help="本地重建向量数据库（升级后执行）")
    p_vector.add_argument("--track", choices=["local", "global", "both"], default="both", help="重建范围 (默认 both)")
    p_vector.add_argument("--incremental", action="store_true", help="增量模式")
    p_vector.add_argument("--dry-run", action="store_true", help="仅预览，不执行")

    subparsers.add_parser("localize", help="从模板生成本机身份配置")
    subparsers.add_parser("register", help="注册本机到集群注册表")
    subparsers.add_parser("cluster-status", help="查看集群所有机器状态")
    subparsers.add_parser("cluster-cleanup", help="清理过期注册条目")

    # ---- 联邦管理命令（从 07_matrix/ 插件自动加载）----
    fed_plugins = []
    fed_base_mod = None
    try:
        fed_plugins, fed_base_mod = _load_federation_plugins()
        for plugin in fed_plugins:
            plugin.register(subparsers)
    except Exception:
        pass  # 插件加载失败不影响系统命令

    # ---- 解析 ----
    args = parser.parse_args()

    if not args.command:
        banner()
        parser.print_help()
        print()
        print("  输入 agentos <command> --help 查看子命令详情")
        print()
        return

    # ---- 路由到系统管理模块 ----
    sys_commands = {
        "init":         (".init", "do_init"),
        "sync":         (".sync", "run"),
        "skill":        (".skill_mgr", "run"),
        "tool":         (".tool_mgr", "run"),
        "config":       (".config_mgr", "run"),
        "check":        (".check", "cmd_run"),
        "backup":       (".backup", "run"),
        "upgrade":      (".upgrade", "do_upgrade"),
        "restore":      (".backup", "run_restore"),
        "rebuild-vector": (".upgrade", "do_rebuild_vector"),
        "localize":     (".init", "do_localize"),
        "register":     (".upgrade", "do_cluster_register"),
        "cluster-status":  (".upgrade", "do_cluster_status"),
        "cluster-cleanup": (".upgrade", "do_cluster_cleanup"),
    }

    if args.command in sys_commands:
        mod_path, func_name = sys_commands[args.command]
        import importlib
        mod = importlib.import_module(mod_path, "agentos")
        getattr(mod, func_name)(args)
        return

    # ---- 路由到联邦插件 ----
    for plugin in fed_plugins:
        if args.command == plugin.name:
            sys.exit(plugin.dispatch(args))

    # 未识别的命令
    print(f"未知命令: {args.command}")
    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()

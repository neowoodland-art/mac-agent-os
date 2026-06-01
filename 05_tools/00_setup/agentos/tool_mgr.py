"""
agentos tool — 工具管理

子命令: list, trae
"""

import os
import subprocess
import sys
from pathlib import Path

from .utils import get_sync_root, info, ok, warn, err, banner


TOOL_CATEGORIES = {
    "00_setup": "安装部署",
    "01_system": "系统诊断与健康检查",
    "02_browser": "浏览器自动化",
    "03_ocr": "OCR 识别",
    "04_media": "媒体处理",
    "05_crawl": "网页抓取与爬虫",
    "06_mobile": "移动端工具",
    "07_matrix": "矩阵养号",
    "08_trae_agent": "Trae AI 编程助手",
}


def _get_trae_script() -> Path:
    """查找 trae_agent.sh 脚本路径"""
    sync_root = get_sync_root()
    candidates = [
        sync_root / "05_tools" / "08_trae_agent" / "trae_agent.sh",
        sync_root / "05_tools" / "08_trae_agent" / "trae_agent.sh",
    ]
    for p in candidates:
        if p.exists():
            return p
    # Fallback: 直接使用 agent-local 路径
    fallback = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "trae-agent"
    script = fallback.parent.parent / "agent-sync" / "05_tools" / "08_trae_agent" / "trae_agent.sh"
    if script.exists():
        return script
    return candidates[0]


def cmd_list():
    """列出所有可用工具"""
    banner()
    tools_root = get_sync_root() / "05_tools"

    if not tools_root.exists():
        warn(f"工具目录不存在: {tools_root}")
        return

    total = 0
    for category_dir in sorted(tools_root.iterdir()):
        if not category_dir.is_dir() or category_dir.name.startswith("."):
            continue

        cat_name = TOOL_CATEGORIES.get(category_dir.name, category_dir.name)
        scripts = sorted(category_dir.rglob("*.py")) + sorted(category_dir.rglob("*.sh"))

        # 过滤掉 __pycache__ 和 __init__.py
        scripts = [s for s in scripts if "__pycache__" not in s.parts and s.name != "__init__.py"]

        if not scripts:
            continue

        print(f"\n{cat_name} ({category_dir.name}/):")
        for s in scripts:
            rel = s.relative_to(tools_root)
            # 显示简要描述（读取文件第一行注释）
            desc = ""
            try:
                with open(s) as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("#"):
                        desc = first_line.lstrip("# ").strip()
                    elif first_line.startswith('"""'):
                        desc = s.read_text().split('"""')[1].strip().split("\n")[0].strip()
            except Exception:
                pass
            desc = desc[:50] if desc else ""
            print(f"  📄 {rel}")
            if desc:
                print(f"      {desc}")
            total += 1

    print(f"\n共 {total} 个工具脚本")
    print()


def cmd_trae_install():
    """安装 trae-agent"""
    sync_root = get_sync_root()
    install_script = sync_root / "05_tools" / "08_trae_agent" / "install_trae_agent.sh"
    if not install_script.exists():
        err(f"安装脚本不存在: {install_script}")
        return
    info("正在安装 trae-agent...")
    result = subprocess.run(["bash", str(install_script)], cwd=str(install_script.parent))
    if result.returncode == 0:
        ok("trae-agent 安装完成")
    else:
        err("安装失败")


def cmd_trae_run(args):
    """执行 trae-agent 任务"""
    script = _get_trae_script()
    if not script.exists():
        err(f"trae_agent.sh 不存在: {script}")
        err("请先运行: agentos tool trae install")
        return

    # 绕过系统代理（macOS 系统代理端口 6478 会拦截本地 LLM 请求）
    env = {**subprocess._clean_environ() if hasattr(subprocess, '_clean_environ') else {}, **os.environ}
    env["NO_PROXY"] = "localhost,127.0.0.1,::1"
    env["no_proxy"] = "localhost,127.0.0.1,::1"

    cmd = ["bash", str(script), "run"]
    if args.provider:
        cmd.extend(["-p", args.provider])
    if args.model:
        cmd.extend(["-m", args.model])
    if args.file:
        cmd.extend(["-f", args.file])
    if args.task:
        cmd.append(" ".join(args.task))

    result = subprocess.run(cmd, env=env)
    sys.exit(result.returncode)


def cmd_trae_interactive():
    """启动 trae-agent 交互模式"""
    script = _get_trae_script()
    if not script.exists():
        err(f"trae_agent.sh 不存在: {script}")
        err("请先运行: agentos tool trae install")
        return
    subprocess.run(["bash", str(script), "interactive"])


def cmd_trae_config():
    """查看 trae-agent 配置"""
    script = _get_trae_script()
    if not script.exists():
        err("trae-agent 未安装")
        return
    subprocess.run(["bash", str(script), "show-config"])


def run(args):
    cmd = args.tool_cmd
    if not cmd:
        banner()
        print("agentos tool 子命令: list, trae")
        print()
        return
    if cmd == "list":
        cmd_list()
    elif cmd == "trae":
        trae_cmd = getattr(args, "trae_cmd", None)
        if not trae_cmd:
            banner()
            print("agentos tool trae 子命令: run, interactive, config, install")
            print()
            return
        if trae_cmd == "run":
            cmd_trae_run(args)
        elif trae_cmd == "interactive":
            cmd_trae_interactive()
        elif trae_cmd == "config":
            cmd_trae_config()
        elif trae_cmd == "install":
            cmd_trae_install()

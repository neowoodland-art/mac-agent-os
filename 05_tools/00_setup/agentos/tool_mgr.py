"""
agentos tool — 工具管理

子命令: list
"""

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
}


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


def run(args):
    cmd = args.tool_cmd
    if not cmd:
        banner()
        print("agentos tool 子命令: list")
        print()
        return
    if cmd == "list":
        cmd_list()

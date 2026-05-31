"""
agentos skill — 技能管理

子命令: list / install / check / build / search / uninstall
"""

import sys
import json
import shutil
import tarfile
from pathlib import Path
from datetime import datetime

from .utils import (
    get_sync_root, get_local_root, get_python,
    info, ok, warn, err, run, banner
)


# ──────────────────────────────────────────
# 内部函数
# ──────────────────────────────────────────

def get_skill_dirs(skills_root: Path) -> list:
    """从 skills_root 扫描所有技能目录"""
    if not skills_root.exists():
        return []
    result = []
    for d in sorted(skills_root.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            result.append(d)
    return result


def read_skill_card(skill_dir: Path) -> dict:
    """读取 SKILL_CARD.yaml 或 SKILL.md 中的元数据"""
    card = {"name": skill_dir.name, "version": "?", "status": "?", "description": ""}

    # 优先读 SKILL_CARD.yaml
    yaml_path = skill_dir / "SKILL_CARD.yaml"
    if yaml_path.exists():
        try:
            import yaml
            with open(yaml_path) as f:
                data = yaml.safe_load(f) or {}
            card["version"] = data.get("version", "?")
            card["status"] = data.get("status", "?")
            card["description"] = data.get("description", "")
        except Exception:
            pass

    # 从 SKILL.md 提取触发词
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        content = skill_md.read_text()
        triggers = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                triggers.append(line[2:])
        card["triggers"] = triggers[:5]  # 最多取前5个

    return card


def get_workbuddy_skills_dir() -> Path:
    """获取 WorkBuddy 技能目录"""
    return Path.home() / ".workbuddy" / "skills"


# ──────────────────────────────────────────
# 子命令
# ──────────────────────────────────────────

def cmd_list(verbose: bool):
    """列出所有可用技能"""
    banner()
    sync_root = get_sync_root()
    skills_root = sync_root / "02_skills"

    dirs = get_skill_dirs(skills_root)
    if not dirs:
        info(f"技能目录为空: {skills_root}")
        return

    print(f"{'技能名':<22} {'版本':<8} {'状态':<10} {'描述'}")
    print("-" * 70)
    for d in dirs:
        card = read_skill_card(d)
        desc = card.get("description") or ""
        if isinstance(desc, dict):
            desc = desc.get("short", "")
        desc = desc[:40] if isinstance(desc, str) else ""
        print(f"{d.name:<22} {card['version']:<8} {card['status']:<10} {desc}")

    print(f"\n共 {len(dirs)} 个技能 ({skills_root})")
    print()

    if verbose:
        print("触发词详情:")
        for d in dirs:
            card = read_skill_card(d)
            triggers = card.get("triggers", [])
            if triggers:
                print(f"  {d.name}: {' | '.join(triggers)}")


def cmd_install():
    """安装所有技能到 WorkBuddy"""
    banner()
    sync_root = get_sync_root()
    skills_root = sync_root / "02_skills"
    wb_skills = get_workbuddy_skills_dir()
    wb_skills.mkdir(parents=True, exist_ok=True)

    dirs = get_skill_dirs(skills_root)
    if not dirs:
        warn(f"没有可安装的技能: {skills_root}")
        return

    installed = 0
    updated = 0
    for d in dirs:
        dest = wb_skills / d.name
        if dest.exists():
            shutil.rmtree(str(dest))
            updated += 1
        shutil.copytree(str(d), str(dest), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        installed += 1

    ok(f"技能安装完成: 新增 {installed}，更新 {updated}")
    info(f"目标目录: {wb_skills}")
    info("重启 WorkBuddy 后新技能将生效")


def install_all(skills_root: Path):
    """(被 init 调用) 安装所有技能"""
    wb_skills = get_workbuddy_skills_dir()
    wb_skills.mkdir(parents=True, exist_ok=True)

    dirs = get_skill_dirs(skills_root)
    for d in dirs:
        dest = wb_skills / d.name
        if dest.exists():
            shutil.rmtree(str(dest))
        shutil.copytree(str(d), str(dest), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        ok(f"  技能已安装: {d.name}")


def cmd_check():
    """检查技能一致性"""
    banner()
    sync_root = get_sync_root()
    wb_skills = get_workbuddy_skills_dir()

    source_dirs = {d.name: d for d in get_skill_dirs(sync_root / "02_skills")}
    wb_dirs = {d.name: d for d in get_skill_dirs(wb_skills)}

    # 检查源有但 WB 没有的
    missing = set(source_dirs.keys()) - set(wb_dirs.keys())
    if missing:
        for name in sorted(missing):
            warn(f"技能未安装到 WorkBuddy: {name}")

    # 检查版本差异
    diffs = []
    for name in set(source_dirs.keys()) & set(wb_dirs.keys()):
        src_card = read_skill_card(source_dirs[name])
        wb_card = read_skill_card(wb_dirs[name])
        if src_card["version"] != wb_card["version"]:
            diffs.append((name, src_card["version"], wb_card["version"]))

    if diffs:
        for name, sv, wv in diffs:
            info(f"版本差异: {name} (源: {sv} vs WB: {wv})")

    if not missing and not diffs:
        ok("所有技能一致，无差异")
    else:
        info("运行 agentos skill install 以同步")


def cmd_build(skill_name: str, output_path: str = None):
    """打包技能为 .skill 压缩包"""
    banner()
    skills_root = get_sync_root() / "02_skills"
    skill_dir = skills_root / skill_name

    if not skill_dir.exists() or not (skill_dir / "SKILL.md").exists():
        err(f"技能不存在: {skill_name} ({skill_dir})")
        sys.exit(1)

    # 读取版本号
    card = read_skill_card(skill_dir)
    version = card["version"]

    # 确定输出路径
    if output_path:
        out_dir = Path(output_path)
    else:
        out_dir = get_sync_root() / "07_migration" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    archive_name = f"{skill_name}_v{version}.tar.gz"
    archive_path = out_dir / archive_name

    with tarfile.open(str(archive_path), "w:gz") as tar:
        tar.add(str(skill_dir), arcname=skill_name)

    file_size = archive_path.stat().st_size / 1024
    ok(f"技能包已创建: {archive_path} ({file_size:.1f} KB)")
    info(f"安装命令: agentos skill install (放到新机后)")
    info(f"手动安装: 解压到 ~/.workbuddy/skills/{skill_name}/")


def cmd_search(keyword: str):
    """搜索技能"""
    banner()
    skills_root = get_sync_root() / "02_skills"
    keyword_lower = keyword.lower()

    results = []
    for d in get_skill_dirs(skills_root):
        card = read_skill_card(d)
        desc = card.get("description", "").lower()
        name = d.name.lower()
        triggers = " ".join(card.get("triggers", [])).lower()

        if keyword_lower in name or keyword_lower in desc or keyword_lower in triggers:
            results.append((d.name, card["version"], card.get("description", "")))

    if results:
        print(f"找到 {len(results)} 个匹配技能:")
        for name, ver, desc in results:
            print(f"  {name:<20} v{ver:<6} {desc[:50]}")
    else:
        info(f"未找到匹配 '{keyword}' 的技能")


def cmd_uninstall(skill_name: str):
    """从 WorkBuddy 卸载技能"""
    wb_dir = get_workbuddy_skills_dir() / skill_name
    if not wb_dir.exists():
        err(f"技能未安装: {skill_name}")
        sys.exit(1)

    shutil.rmtree(str(wb_dir))
    ok(f"技能已卸载: {skill_name}")
    info("重启 WorkBuddy 后生效")


# ──────────────────────────────────────────
# 路由
# ──────────────────────────────────────────

def run(args):
    cmd = args.skill_cmd
    if not cmd:
        banner()
        print("agentos skill 子命令: list | install | check | build | search | uninstall")
        print()
        return

    if cmd == "list":
        cmd_list(verbose=args.verbose)
    elif cmd == "install":
        cmd_install()
    elif cmd == "check":
        cmd_check()
    elif cmd == "build":
        cmd_build(args.skill_name, args.output)
    elif cmd == "search":
        cmd_search(args.keyword)
    elif cmd == "uninstall":
        cmd_uninstall(args.skill_name)

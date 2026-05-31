#!/usr/bin/env python3
"""
skill_scanner.py — 技能状态扫描器

扫描所有 SKILL_CARD.yaml，报告每个技能的状态：
  - 是否有身份证（SKILL_CARD.yaml）
  - 入口脚本是否存在
  - 核心依赖是否已安装
  - 主机角色是否匹配（只在 master_editor 机器上写入）

使用：
  python3 skill_scanner.py
  python3 skill_scanner.py --root ~/workbuddy-agent-os/agent-sync
  python3 skill_scanner.py --check-deps    # 同时检查 pip 依赖
  python3 skill_scanner.py --json          # JSON格式输出
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="AgentOS 技能状态扫描器")
    parser.add_argument("--root", default="~/workbuddy-agent-os/agent-sync", help="agent-os 根目录")
    parser.add_argument("--local", default="~/workbuddy-agent-os/agent-local", help="~/workbuddy-agent-os/agent-local")
    parser.add_argument("--check-deps", action="store_true", help="检查 pip 依赖是否已安装")
    parser.add_argument("--json", action="store_true", dest="json_output", help="JSON 格式输出")
    return parser.parse_args()


def load_yaml_simple(file_path: Path) -> dict:
    """简单 YAML 解析（不依赖 pyyaml）"""
    data = {}
    current_key = None
    current_list = None
    current_section = data

    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return {}

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        # 列表项
        if stripped.startswith("- "):
            if current_list is not None:
                current_list.append(stripped[2:].strip().strip('"'))
            continue

        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")

            if val:
                if indent == 0:
                    data[key] = val
                    current_section = data
                    current_list = None
                else:
                    current_section[key] = val
                    current_list = None
            else:
                # 嵌套块或列表开始
                if indent == 0:
                    data[key] = {}
                    current_section = data[key]
                    current_list = None
                elif key:
                    parent = current_section
                    parent[key] = []
                    current_list = parent[key]

    return data


def get_host_id(local_root: Path) -> str:
    """读取本机 HOST_ID"""
    # 从 machine_info.json 读取
    machine_info = local_root / "machine_info.json"
    if machine_info.exists():
        try:
            info = json.loads(machine_info.read_text(encoding="utf-8"))
            return info.get("machine", {}).get("id", "unknown")
        except Exception:
            pass
    # 从 HOST_ID.md 读取
    host_id_md = local_root.parent / "agent-os" / "01_core" / "HOST_ID.md"
    # 已知路径
    for path in [Path("~/workbuddy-agent-os/agent-sync/01_core/HOST_ID.md").expanduser()]:
        if path.exists():
            content = path.read_text(encoding="utf-8")
            import re
            m = re.search(r'`([^`]+_(?:master|maintainer|node))`', content)
            if m:
                return m.group(1)
    return "unknown"


def check_pip_installed(packages: list) -> dict:
    """检查 pip 包是否已安装"""
    results = {}
    for pkg in packages:
        pkg_name = pkg.split(">=")[0].split("==")[0].split("[")[0].strip()
        try:
            result = subprocess.run(
                [sys.executable, "-c", f"import {pkg_name.replace('-', '_')}"],
                capture_output=True, timeout=5
            )
            results[pkg] = result.returncode == 0
        except Exception:
            results[pkg] = False
    return results


def scan_skill(skill_dir: Path, check_deps: bool, host_id: str) -> dict:
    """扫描单个技能目录"""
    name = skill_dir.name
    result = {
        "name": name,
        "path": str(skill_dir),
        "has_skill_md": (skill_dir / "SKILL.md").exists(),
        "has_skill_card": (skill_dir / "SKILL_CARD.yaml").exists(),
        "has_entry": False,
        "entry_point": None,
        "status": "unknown",
        "version": "?",
        "category": "?",
        "master_editor": "?",
        "is_master": False,
        "deps_ok": None,
        "missing_deps": [],
        "issues": []
    }

    # 读取 SKILL_CARD.yaml
    card_path = skill_dir / "SKILL_CARD.yaml"
    if card_path.exists():
        card = load_yaml_simple(card_path)
        skill_info = card.get("skill", {})
        result["version"] = skill_info.get("version", "?")
        result["status"] = skill_info.get("status", "?")
        result["category"] = skill_info.get("category", "?")

        # 读取 ownership
        ownership = card.get("ownership", {})
        result["master_editor"] = ownership.get("master_editor", "?")
        result["is_master"] = host_id != "unknown" and host_id == result["master_editor"]

        # 读取入口脚本
        usage = card.get("usage", {})
        entry = usage.get("entry_point", "")
        if entry:
            result["entry_point"] = entry
            result["has_entry"] = (skill_dir / entry).exists()
            if not result["has_entry"]:
                result["issues"].append(f"入口脚本不存在: {entry}")

        # 检查依赖
        if check_deps:
            env_info = card.get("environment", {})
            pip_deps = env_info.get("pip_dependencies", [])
            if isinstance(pip_deps, list) and pip_deps:
                dep_results = check_pip_installed(pip_deps)
                missing = [pkg for pkg, ok in dep_results.items() if not ok]
                result["deps_ok"] = len(missing) == 0
                result["missing_deps"] = missing
                if missing:
                    result["issues"].append(f"缺失依赖: {', '.join(missing)}")
    else:
        result["issues"].append("缺少 SKILL_CARD.yaml")

    # 没有 SKILL.md 也标记
    if not result["has_skill_md"]:
        result["issues"].append("缺少 SKILL.md")

    return result


STATUS_ICON = {
    "active":       "✅",
    "inactive":     "⏸ ",
    "experimental": "🧪",
    "unknown":      "❓",
    "?":            "❓",
}


def print_report(skills: list, host_id: str):
    """打印扫描报告"""
    print("=" * 65)
    print(f"AgentOS 技能状态报告  (本机: {host_id})")
    print("=" * 65)

    has_card = [s for s in skills if s["has_skill_card"]]
    no_card = [s for s in skills if not s["has_skill_card"]]

    if has_card:
        print("\n📋 已注册技能（有 SKILL_CARD.yaml）:\n")
        for s in has_card:
            icon = STATUS_ICON.get(s["status"], "❓")
            master_tag = " 🔑[主机]" if s["is_master"] else ""
            issues_tag = f" ⚠️ {'; '.join(s['issues'])}" if s["issues"] else ""
            entry_tag = f" → {s['entry_point']}" if s["entry_point"] else ""
            print(f"  {icon} {s['name']:<22} v{s['version']:<8} [{s['category']}]{master_tag}{entry_tag}{issues_tag}")

    if no_card:
        print("\n📂 未注册技能（无 SKILL_CARD.yaml）:\n")
        for s in no_card:
            print(f"  ❓ {s['name']}")

    print(f"\n统计: 共 {len(skills)} 个技能，"
          f"已注册 {len(has_card)}，"
          f"未注册 {len(no_card)}，"
          f"本机主机 {sum(1 for s in skills if s['is_master'])} 个")

    issues_all = [s for s in skills if s["issues"]]
    if issues_all:
        print(f"\n⚠️  需要处理的问题:\n")
        for s in issues_all:
            for issue in s["issues"]:
                print(f"  [{s['name']}] {issue}")

    print("\n图例: ✅=活跃  ⏸=暂停  🧪=实验性  🔑=本机主编辑")


def main():
    args = parse_args()
    root = Path(args.root).expanduser()
    local_root = Path(args.local).expanduser()
    skills_dir = root / "02_skills"

    if not skills_dir.exists():
        print(f"[ERROR] 技能目录不存在: {skills_dir}")
        sys.exit(1)

    host_id = get_host_id(local_root)
    skills = []

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        if skill_dir.name.startswith(("_", ".")):
            continue
        skill = scan_skill(skill_dir, args.check_deps, host_id)
        skills.append(skill)

    if args.json_output:
        print(json.dumps(skills, ensure_ascii=False, indent=2))
    else:
        print_report(skills, host_id)


if __name__ == "__main__":
    main()

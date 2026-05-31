"""
agentos sync — 双机增量同步

检查 agent-sync/ 与本地 WorkBuddy 的差异并增量更新:
1. 技能差异检测（对比版本号和文件变化）
2. MCP 配置差异检测
3. 自动化任务差异检测
4. 增量修复差异项
"""

import sys
import json
import shutil
import hashlib
from pathlib import Path

from .utils import (
    get_sync_root, get_local_root, get_python,
    info, ok, warn, err, run, banner
)
from . import skill_mgr


def file_hash(path: Path) -> str:
    """计算文件 SHA256"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def diff_skills(dry_run: bool) -> list:
    """检测技能差异"""
    sync_root = get_sync_root()
    wb_skills = Path.home() / ".workbuddy" / "skills"
    source_dir = sync_root / "02_skills"

    changes = []
    source_dirs = {d.name: d for d in skill_mgr.get_skill_dirs(source_dir)}
    wb_dirs = {d.name: d for d in skill_mgr.get_skill_dirs(wb_skills)} if wb_skills.exists() else {}

    for name, src_dir in source_dirs.items():
        if name not in wb_dirs:
            changes.append({"type": "missing", "name": name, "action": "install"})
            continue

        src_card = skill_mgr.read_skill_card(src_dir)
        wb_card = skill_mgr.read_skill_card(wb_dirs[name])

        if src_card["version"] != wb_card["version"]:
            changes.append({
                "type": "version_diff",
                "name": name,
                "action": "update",
                "src_version": src_card["version"],
                "wb_version": wb_card["version"],
            })

    for name in wb_dirs:
        if name not in source_dirs:
            changes.append({"type": "extra", "name": name, "action": "uninstall"})

    return changes


def diff_mcp(dry_run: bool) -> list:
    """检测 MCP 配置差异"""
    sync_root = get_sync_root()
    src = sync_root / "01_core" / "mcp.json"
    dst = Path.home() / ".workbuddy" / "mcp.json"

    changes = []
    if not src.exists():
        return changes

    if not dst.exists():
        changes.append({"type": "missing", "name": "mcp.json", "action": "deploy"})
    else:
        src_hash = file_hash(src)
        dst_hash = file_hash(dst)
        if src_hash != dst_hash:
            changes.append({"type": "content_diff", "name": "mcp.json", "action": "update"})

    return changes


def diff_automations(dry_run: bool) -> list:
    """检测自动化任务差异"""
    sync_root = get_sync_root()
    automations_file = sync_root / "01_core" / "automations.yaml"
    if not automations_file.exists():
        return []
    return [{"type": "info", "name": "automations.yaml", "action": "需手动在 WorkBuddy 中比对"}]


def apply_changes(changes: list, dry_run: bool, force: bool):
    """执行差异修复"""
    if dry_run:
        return

    for ch in changes:
        action = ch["action"]

        if action == "install":
            info(f"  安装技能: {ch['name']}")
            src_dir = get_sync_root() / "02_skills" / ch["name"]
            skill_mgr.install_all(get_sync_root() / "02_skills")

        elif action == "update":
            info(f"  更新技能: {ch['name']} ({ch.get('src_version', '?')})")
            skill_mgr.install_all(get_sync_root() / "02_skills")

        elif action == "uninstall":
            warn(f"  agent-sync 中已移除: {ch['name']}（建议手动清理 WorkBuddy）")

        elif action == "deploy":
            info(f"  部署 MCP 配置")
            src = get_sync_root() / "01_core" / "mcp.json"
            dst = Path.home() / ".workbuddy" / "mcp.json"
            if dst.exists():
                dst.rename(dst.with_suffix(".json.syncbak"))
            shutil.copy2(str(src), str(dst))
            ok("  MCP 配置已更新")

        elif action == "update" and ch["name"] == "mcp.json":
            info(f"  更新 MCP 配置")
            src = get_sync_root() / "01_core" / "mcp.json"
            dst = Path.home() / ".workbuddy" / "mcp.json"
            dst.rename(dst.with_suffix(".json.syncbak"))
            shutil.copy2(str(src), str(dst))
            ok("  MCP 配置已更新")


def run(args):
    dry_run = args.dry_run
    force = args.force

    banner()
    info("双机增量同步" + (" [DRY-RUN]" if dry_run else ""))
    print()

    # 1. 检测技能差异
    print("📦 技能差异:")
    skill_changes = diff_skills(dry_run)
    if not skill_changes:
        ok("  无差异")
    else:
        for ch in skill_changes:
            action_icon = {"install": "➕", "update": "🔄", "uninstall": "🗑️"}.get(ch["action"], "?")
            if ch["type"] == "missing":
                warn(f"  {action_icon} 新增技能: {ch['name']}")
            elif ch["type"] == "version_diff":
                info(f"  {action_icon} 版本变更: {ch['name']} ({ch['wb_version']} → {ch['src_version']})")
            elif ch["type"] == "extra":
                warn(f"  {action_icon} 多余的: {ch['name']}（源目录已移除）")

    print()

    # 2. MCP 差异
    print("🔧 MCP 配置差异:")
    mcp_changes = diff_mcp(dry_run)
    if not mcp_changes:
        ok("  无差异")
    else:
        for ch in mcp_changes:
            if ch["action"] == "deploy":
                warn(f"  缺失: {ch['name']}（待部署）")
            elif ch["action"] == "update":
                info(f"  内容变更: {ch['name']}（待更新）")

    print()

    # 3. 自动化差异
    print("⏰ 自动化任务差异:")
    auto_changes = diff_automations(dry_run)
    if not auto_changes:
        ok("  无自动化配置文件（无差异检测）")
    else:
        for ch in auto_changes:
            info(f"  {ch['name']}: {ch['action']}")

    print()

    # 汇总
    all_changes = skill_changes + mcp_changes + [c for c in auto_changes if c["action"] != "需手动在 WorkBuddy 中比对"]
    if not all_changes:
        ok("完全一致，无需同步")
        return

    print(f"共 {len(all_changes)} 项差异")

    if dry_run:
        info("添加 --force 参数执行同步")
    else:
        # 执行同步
        info("执行同步...")
        apply_changes(all_changes, dry_run, force)
        ok("同步完成，请重启 WorkBuddy 使更改生效")

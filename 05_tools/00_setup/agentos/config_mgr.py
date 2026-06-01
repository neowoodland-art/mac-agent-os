"""
agentos config — 配置管理模块 (v1.0.0)

管理 01_core/ ←→ ~/.workbuddy/ 的配置同步。
三类配置：
  A: 自动覆盖（内核身份文件）
  B: 对比选择（服务配置，diff 后用户选择）
  C: 仅报告（本机个性化，不同步）

子命令:
    agentos config status      查看配置状态
    agentos config diff        查看差异详情
    agentos config apply       应用配置更新
    agentos config rollback    回滚到备份

最后更新: 2026-05-02
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .const import __agent_sync_root__, __agent_local_root__, __version__

SYNC_ROOT = Path(__agent_sync_root__)
MANIFEST_PATH = SYNC_ROOT / "01_core" / "CONFIG_MANIFEST.yaml"


# ══════════════════════════════════════════════════════════════
# 配置清单解析
# ══════════════════════════════════════════════════════════════

def load_manifest() -> list:
    """解析 CONFIG_MANIFEST.yaml，返回配置项列表"""
    import yaml
    if not MANIFEST_PATH.exists():
        print(f"❌ 未找到配置清单: {MANIFEST_PATH}")
        return []
    with open(MANIFEST_PATH) as f:
        data = yaml.safe_load(f)
    return data.get("configs", [])


def resolve_path(path_str: str) -> Optional[Path]:
    """将 ~/ 开头的路径解析为绝对路径"""
    if not path_str:
        return None
    path_str = path_str.replace("~", str(Path.home()))
    p = Path(path_str)
    return p if p.exists() else p  # 即使不存在也返回路径对象


# ══════════════════════════════════════════════════════════════
# 状态检查
# ══════════════════════════════════════════════════════════════

def check_status() -> list:
    """检查所有配置项状态，返回状态列表"""
    items = load_manifest()
    if not items:
        return []

    results = []
    for item in items:
        cat = item["category"]
        name = item["file"]
        source = resolve_path(item.get("source"))
        target = resolve_path(item.get("target"))

        status = {
            "name": name,
            "category": cat,
            "source": str(source) if source else "—",
            "target": str(target) if target else "—",
            "exists_source": source and source.exists(),
            "exists_target": target and target.exists(),
            "identical": False,
            "diff_lines": 0,
        }

        # 比较内容
        if status["exists_source"] and status["exists_target"]:
            try:
                s_content = source.read_bytes()
                t_content = target.read_bytes()
                status["identical"] = s_content == t_content
                if not status["identical"]:
                    # 粗略统计差异行数
                    s_lines = s_content.decode().splitlines()
                    t_lines = t_content.decode().splitlines()
                    status["diff_lines"] = abs(len(s_lines) - len(t_lines))
            except Exception:
                status["identical"] = False

        results.append(status)

    return results


# ══════════════════════════════════════════════════════════════
# 差异显示
# ══════════════════════════════════════════════════════════════

def show_diff(item: dict):
    """显示指定配置项的 diff"""
    source = resolve_path(item.get("source"))
    target = resolve_path(item.get("target"))

    if not source or not source.exists():
        print(f"  ⚠️  源文件不存在: {source}")
        return
    if not target or not target.exists():
        print(f"  ⚠️  目标文件不存在: {target}")
        print(f"  → 将创建: {target}")
        return

    try:
        result = subprocess.run(
            ["diff", "-u", str(source), str(target)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"  ✅ 文件一致，无差异")
        else:
            diff_out = result.stdout
            lines = diff_out.splitlines()
            # 只显示前 30 行
            display = lines[:30]
            if len(lines) > 30:
                display.append(f"  ... (还有 {len(lines)-30} 行差异)")
            for line in display:
                marker = " "
                if line.startswith("+"):
                    marker = "+"
                elif line.startswith("-"):
                    marker = "-"
                elif line.startswith("@@"):
                    marker = "@"
                print(f"    {marker} {line}")
    except Exception as e:
        print(f"  ❌ diff 失败: {e}")


# ══════════════════════════════════════════════════════════════
# 备份
# ══════════════════════════════════════════════════════════════

def backup_targets(items: list) -> Optional[Path]:
    """备份所有目标文件到时间戳目录"""
    backup_dir = Path.home() / ".workbuddy" / f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    count = 0
    for item in items:
        if item["category"] == "C":
            continue
        target = resolve_path(item.get("target"))
        if target and target.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(target), str(backup_dir / target.name))
            count += 1
    if count > 0:
        print(f"  💾 已备份 {count} 个文件到: {backup_dir}")
        return backup_dir
    return None


# ══════════════════════════════════════════════════════════════
# 应用配置
# ══════════════════════════════════════════════════════════════

def apply_config(item: dict) -> bool:
    """应用单个配置项"""
    cat = item["category"]
    name = item["file"]
    source = resolve_path(item.get("source"))
    target = resolve_path(item.get("target"))

    if not target:
        print(f"  ⚠️  {name}: 目标路径为空，跳过")
        return False

    if cat == "A":
        # A类: 自动覆盖
        if not source or not source.exists():
            print(f"  ⚠️  {name}: 源文件不存在 ({source})，跳过")
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source), str(target))
        print(f"  ✅ {name}: 已部署（A类自动覆盖）")
        return True

    elif cat == "B":
        # B类: 对比后选择
        if not source or not source.exists():
            print(f"  ⚠️  {name}: 源文件不存在 ({source})，跳过")
            return False
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            # 检查是否一致
            try:
                s_content = source.read_bytes()
                t_content = target.read_bytes()
                if s_content == t_content:
                    print(f"  ✅ {name}: 一致，无需更新")
                    return True
            except Exception:
                pass

            # 有差异，尝试交互（非交互环境自动跳过）
            print(f"\n  📋 {name}: 源与目标存在差异")
            print(f"    源: {source}")
            print(f"    目标: {target}")
            show_diff(item)
            print()
            try:
                choice = input(f"    选择 [K]保留本地  [N]用新版  [D]查看差异  [S]跳过: ").strip().upper()
            except (EOFError, OSError):
                print(f"  ⏭️  {name}: 非交互环境，跳过（运行 agentos config diff {name} 手动处理）")
                return False
            while True:
                if choice == "K":
                    print(f"  ⏭️  {name}: 保留本地版本")
                    return False
                elif choice == "N":
                    shutil.copy2(str(source), str(target))
                    print(f"  ✅ {name}: 已更新为新版")
                    return True
                elif choice == "D":
                    show_diff(item)
                    break
                elif choice == "S":
                    print(f"  ⏭️  {name}: 跳过")
                    return False
                else:
                    break
        else:
            # 目标不存在，直接部署
            shutil.copy2(str(source), str(target))
            print(f"  ✅ {name}: 已创建（首次部署）")
            return True

    elif cat == "C":
        print(f"  ⏭️  {name}: C类本机配置，不同步")
        return False

    return False


# ══════════════════════════════════════════════════════════════
# CLI 命令
# ══════════════════════════════════════════════════════════════

def cmd_status(args):
    """agentos config status — 查看配置状态"""
    results = check_status()
    if not results:
        print("❌ 无法读取配置清单")
        return

    print(f"\n{'='*60}")
    print(f"  📋 AgentOS 配置状态")
    print(f"{'='*60}\n")

    for r in results:
        cat = r["category"]
        name = r["name"]
        tag = {"A": "🔵 A-自动", "B": "🟡 B-选择", "C": "⚪ C-本地"}.get(cat, "?")

        if cat == "C":
            exists = r["exists_target"]
            print(f"  {tag}  {name:20s}  {'✅ 存在' if exists else '⏹️  不存在'}")
        elif r["identical"]:
            print(f"  {tag}  {name:20s}  ✅ 一致")
        elif r["exists_source"] and r["exists_target"]:
            print(f"  {tag}  {name:20s}  ⚠️  有差异（~{r['diff_lines']}行不同）")
        elif r["exists_source"] and not r["exists_target"]:
            print(f"  {tag}  {name:20s}  📋 待部署（目标不存在）")
        elif not r["exists_source"]:
            print(f"  {tag}  {name:20s}  ❌ 源文件不存在")
        else:
            print(f"  {tag}  {name:20s}  ❓ 未知")

    print(f"\n{'─'*60}")
    a_count = sum(1 for r in results if r["category"] == "A" and not r["identical"])
    b_count = sum(1 for r in results if r["category"] == "B" and not r["identical"])
    if a_count + b_count > 0:
        print(f"  ⚠️  {a_count} 个 A类 + {b_count} 个 B类 待处理")
        print(f"  运行: agentos config apply")
    else:
        print(f"  ✅ 所有配置一致")
    print()


def cmd_diff(args):
    """agentos config diff — 查看所有差异"""
    results = check_status()
    if not results:
        return

    items = load_manifest()
    for i, r in enumerate(results):
        if r["identical"] or r["category"] == "C":
            continue
        if r["exists_source"] and r["exists_target"]:
            print(f"\n{'='*60}")
            print(f"  📄 {r['name']}")
            print(f"{'='*60}")
            show_diff(items[i])
    print()


def cmd_apply(args):
    """agentos config apply — 应用配置更新"""
    items = load_manifest()
    if not items:
        return

    print(f"\n{'='*60}")
    print(f"  🔄 AgentOS 配置更新")
    print(f"{'='*60}\n")

    # 先备份
    print(f"▶ 备份现有配置...")
    backup_dir = backup_targets(items)
    if backup_dir:
        print(f"  回滚命令: agentos config rollback {backup_dir.name}")
    print()

    # 逐项应用
    changed = 0
    for item in items:
        if item["category"] == "C":
            continue
        ok = apply_config(item)
        if ok:
            changed += 1

    print(f"\n{'─'*60}")
    if changed > 0:
        print(f"  ✅ 已更新 {changed} 个配置项")
        print(f"  提示: 如果 WorkBuddy 正在运行，可能需要重启生效")
    else:
        print(f"  ⏭️  无变更")
    print()


def cmd_rollback(args):
    """agentos config rollback — 回滚配置"""
    backup_name = getattr(args, "backup_name", None)

    backup_base = Path.home() / ".workbuddy"
    if backup_name:
        backup_dir = backup_base / backup_name
    else:
        # 找最近的备份
        backups = sorted(backup_base.glob("config_backup_*"))
        if not backups:
            print("❌ 未找到备份")
            return
        backup_dir = backups[-1]
        print(f"  使用最近备份: {backup_dir.name}")

    if not backup_dir.exists():
        print(f"❌ 备份目录不存在: {backup_dir}")
        return

    files = list(backup_dir.iterdir())
    if not files:
        print(f"❌ 备份目录为空: {backup_dir}")
        return

    print(f"\n{'='*60}")
    print(f"  ↩️  回滚配置")
    print(f"{'='*60}\n")
    print(f"  从: {backup_dir}")
    print()

    for f in files:
        target = Path.home() / ".workbuddy" / f.name
        shutil.copy2(str(f), str(target))
        print(f"  ✅ {f.name}: 已恢复")

    print(f"\n  共恢复 {len(files)} 个文件")
    print()


# ══════════════════════════════════════════════════════════════
# 子命令注册
# ══════════════════════════════════════════════════════════════

def setup_parser(subparsers):
    """向主 CLI 注册 config 子命令"""
    p = subparsers.add_parser("config", help="配置管理：状态查看 / 差异对比 / 部署 / 回滚")

    config_sub = p.add_subparsers(dest="config_cmd", help="配置子命令")

    config_sub.add_parser("status", help="查看配置状态（哪些文件有差异）")
    config_sub.add_parser("diff", help="查看配置差异详情")
    config_sub.add_parser("apply", help="应用配置更新（A类自动 / B类选择）")

    p_rollback = config_sub.add_parser("rollback", help="回滚到上次备份")
    p_rollback.add_argument("backup_name", nargs="?", default=None,
                            help="备份目录名（可选，默认使用最近备份）")


def run(args):
    cmd = args.config_cmd
    if not cmd:
        print("agentos config 子命令: status | diff | apply | rollback")
        return

    if cmd == "status":
        cmd_status(args)
    elif cmd == "diff":
        cmd_diff(args)
    elif cmd == "apply":
        cmd_apply(args)
    elif cmd == "rollback":
        cmd_rollback(args)

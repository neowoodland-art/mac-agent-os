#!/usr/bin/env python3
"""
sync_manager.py — 知识库备份、导出、同步状态检查

模式：
  backup  — 全量备份 03_knowledge/ + 04_memory/long_term/ 到 memory_backup/
  export  — 导出可分发知识包（可按领域/标签过滤）
  status  — 检查坚果云同步路径状态

使用：
  python3 sync_manager.py --mode backup
  python3 sync_manager.py --mode backup --keep 5
  python3 sync_manager.py --mode export --domain 10_concepts 20_methods
  python3 sync_manager.py --mode export --tag AI工具
  python3 sync_manager.py --mode status
  python3 sync_manager.py --mode backup --dry-run
"""

import argparse
import os
import re
import shutil
import sys
import tarfile
from datetime import datetime
from pathlib import Path


# ── 配置 ──────────────────────────────────────────────────────────────────────

BACKUP_SOURCES = [
    "03_knowledge",
    "04_memory/long_term",
]

KNOWLEDGE_DOMAINS = [
    "10_concepts", "20_methods", "30_facts",
    "40_references", "50_resources", "60_opinions",
]

DEFAULT_NUTSTORE_PATH = "~/NutstoreCloudBridge"
DEFAULT_KEEP = 10


# ── 参数解析 ───────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="AgentOS 同步管理器")
    parser.add_argument("--root", default="~/workbuddy-agent-os/agent-sync", help="agent-os 根目录")
    parser.add_argument("--mode", choices=["backup", "export", "status"], required=True,
                        help="运行模式")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP,
                        help="备份模式：保留最近N份（默认10）")
    parser.add_argument("--domain", nargs="+", default=None,
                        help="导出模式：只导出指定领域目录（如 10_concepts 20_methods）")
    parser.add_argument("--tag", default=None,
                        help="导出模式：只导出含有指定 tag 的文件")
    parser.add_argument("--nutstore", default=DEFAULT_NUTSTORE_PATH,
                        help="坚果云同步路径（用于 status 模式）")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不实际写入")
    return parser.parse_args()


# ── 工具函数 ───────────────────────────────────────────────────────────────────

def ensure_dir(path: Path, dry_run: bool = False):
    if not dry_run:
        path.mkdir(parents=True, exist_ok=True)


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes //= 1024
    return f"{size_bytes:.1f} TB"


def get_md_tag(file_path: Path) -> list:
    """从 frontmatter 提取 tags 列表"""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        if not content.startswith("---"):
            return []
        end = content.find("\n---", 3)
        if end == -1:
            return []
        frontmatter = content[3:end]
        # 匹配 tags: [a, b] 或多行列表
        m = re.search(r'tags\s*:\s*\[([^\]]+)\]', frontmatter)
        if m:
            return [t.strip().strip('"\'') for t in m.group(1).split(",")]
        # 多行格式
        tags = []
        in_tags = False
        for line in frontmatter.splitlines():
            if re.match(r'\s*tags\s*:', line):
                in_tags = True
                continue
            if in_tags:
                if line.strip().startswith("- "):
                    tags.append(line.strip()[2:].strip())
                elif line.strip() and not line.startswith(" "):
                    break
        return tags
    except Exception:
        return []


# ── backup 模式 ────────────────────────────────────────────────────────────────

def run_backup(root: Path, keep: int, dry_run: bool):
    backup_dir = root / "04_memory" / "memory_backup"
    ensure_dir(backup_dir, dry_run)

    now = datetime.now()
    filename = f"kb_backup_{now.strftime('%Y-%m-%d_%H%M')}.tar.gz"
    output_path = backup_dir / filename

    sources = []
    for src in BACKUP_SOURCES:
        p = root / src
        if p.exists():
            sources.append(p)
        else:
            print(f"  [跳过] {p} 不存在")

    if not sources:
        print("[ERROR] 没有找到任何备份源")
        sys.exit(1)

    total_files = sum(
        sum(1 for _ in src.rglob("*") if _.is_file())
        for src in sources
    )
    total_size = sum(
        sum(f.stat().st_size for f in src.rglob("*") if f.is_file())
        for src in sources
    )

    print(f"备份目标: {', '.join(str(s.relative_to(root)) for s in sources)}")
    print(f"文件数量: {total_files}  预计大小: {format_size(total_size)}")
    print(f"输出路径: {output_path}")

    if dry_run:
        print("[dry-run] 跳过实际打包")
        return

    with tarfile.open(output_path, "w:gz") as tar:
        for src in sources:
            tar.add(src, arcname=src.relative_to(root))

    actual_size = output_path.stat().st_size
    print(f"✅ 备份完成: {filename}  ({format_size(actual_size)})")

    # 清理旧备份
    _prune_backups(backup_dir, keep)


def _prune_backups(backup_dir: Path, keep: int):
    """保留最近 keep 份，删除更旧的"""
    pattern = re.compile(r"kb_backup_\d{4}-\d{2}-\d{2}_\d{4}\.tar\.gz")
    backups = sorted(
        [f for f in backup_dir.iterdir() if f.is_file() and pattern.match(f.name)],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    to_delete = backups[keep:]
    if to_delete:
        print(f"清理旧备份（保留最近{keep}份）:")
        for f in to_delete:
            print(f"  删除: {f.name}")
            f.unlink()
    else:
        print(f"备份数量: {len(backups)} 份，无需清理")


# ── export 模式 ────────────────────────────────────────────────────────────────

def run_export(root: Path, domains: list, tag: str, dry_run: bool):
    now = datetime.now()
    suffix = f"_tag-{tag}" if tag else ""
    suffix += f"_dom-{'_'.join(domains)}" if domains else ""
    filename = f"kb_export_{now.strftime('%Y-%m-%d_%H%M')}{suffix}.tar.gz"
    export_dir = root / "04_memory" / "memory_backup"
    ensure_dir(export_dir, dry_run)
    output_path = export_dir / filename

    # 确定要导出的目录
    kb_root = root / "03_knowledge"
    if domains:
        scan_dirs = [kb_root / d for d in domains if (kb_root / d).exists()]
        missing = [d for d in domains if not (kb_root / d).exists()]
        if missing:
            print(f"[警告] 以下领域目录不存在: {', '.join(missing)}")
    else:
        scan_dirs = [kb_root / d for d in KNOWLEDGE_DOMAINS if (kb_root / d).exists()]

    # 收集文件
    all_files = []
    for d in scan_dirs:
        for f in d.rglob("*.md"):
            if tag:
                if tag in get_md_tag(f):
                    all_files.append(f)
            else:
                all_files.append(f)

    if not all_files:
        print("[ERROR] 没有找到符合条件的文件")
        sys.exit(1)

    total_size = sum(f.stat().st_size for f in all_files)
    filter_desc = f"  标签过滤: {tag}" if tag else ""
    domain_desc = f"  领域: {', '.join(domains)}" if domains else "  领域: 全部"
    print(f"导出范围: {domain_desc}{filter_desc}")
    print(f"文件数量: {len(all_files)}  预计大小: {format_size(total_size)}")
    print(f"输出路径: {output_path}")

    if dry_run:
        print("[dry-run] 跳过实际打包")
        for f in all_files[:5]:
            print(f"  示例: {f.relative_to(root)}")
        if len(all_files) > 5:
            print(f"  ... 共 {len(all_files)} 个文件")
        return

    with tarfile.open(output_path, "w:gz") as tar:
        for f in all_files:
            tar.add(f, arcname=f.relative_to(root))

    actual_size = output_path.stat().st_size
    print(f"✅ 导出完成: {filename}  ({format_size(actual_size)}，{len(all_files)} 个文件)")


# ── status 模式 ────────────────────────────────────────────────────────────────

def run_status(root: Path, nutstore_path: str):
    print("=" * 50)
    print("AgentOS 同步状态检查")
    print("=" * 50)

    # 1. 本地知识库状态
    kb_root = root / "03_knowledge"
    facts_db = root / "04_memory" / "long_term" / "facts.db"
    backup_dir = root / "04_memory" / "memory_backup"

    if kb_root.exists():
        md_count = sum(1 for _ in kb_root.rglob("*.md"))
        kb_size = sum(f.stat().st_size for f in kb_root.rglob("*") if f.is_file())
        print(f"\n📚 知识库: {md_count} 个 MD 文件  ({format_size(kb_size)})")
    else:
        print(f"\n📚 知识库: ❌ 目录不存在 ({kb_root})")

    if facts_db.exists():
        facts_mtime = datetime.fromtimestamp(facts_db.stat().st_mtime)
        facts_size = facts_db.stat().st_size
        print(f"🧠 facts.db: {format_size(facts_size)}  最后修改: {facts_mtime.strftime('%Y-%m-%d %H:%M')}")
    else:
        print(f"🧠 facts.db: ❌ 不存在")

    # 2. 备份状态
    if backup_dir.exists():
        pattern = re.compile(r"kb_backup_\d{4}-\d{2}-\d{2}_\d{4}\.tar\.gz")
        backups = sorted(
            [f for f in backup_dir.iterdir() if f.is_file() and pattern.match(f.name)],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if backups:
            latest = backups[0]
            latest_time = datetime.fromtimestamp(latest.stat().st_mtime)
            print(f"\n💾 最新备份: {latest.name}")
            print(f"   时间: {latest_time.strftime('%Y-%m-%d %H:%M')}  大小: {format_size(latest.stat().st_size)}")
            print(f"   共 {len(backups)} 份备份")
        else:
            print(f"\n💾 备份: ❌ 暂无备份文件")
    else:
        print(f"\n💾 备份目录: ❌ 不存在")

    # 3. 坚果云同步状态
    nutstore = Path(nutstore_path).expanduser()
    print(f"\n☁️  坚果云同步路径: {nutstore}")
    if nutstore.exists():
        all_files = [f for f in nutstore.rglob("*") if f.is_file()]
        if all_files:
            latest_sync = max(all_files, key=lambda f: f.stat().st_mtime)
            sync_time = datetime.fromtimestamp(latest_sync.stat().st_mtime)
            sync_size = sum(f.stat().st_size for f in all_files)
            print(f"   状态: ✅ 路径存在")
            print(f"   文件数: {len(all_files)}  总大小: {format_size(sync_size)}")
            print(f"   最近同步: {sync_time.strftime('%Y-%m-%d %H:%M')}  ({latest_sync.name})")
        else:
            print(f"   状态: ⚠️  路径存在但为空")
    else:
        print(f"   状态: ❌ 路径不存在（坚果云未挂载或未安装）")

    print()


# ── 入口 ───────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    root = Path(args.root).expanduser()

    if not root.exists():
        print(f"[ERROR] agent-os 根目录不存在: {root}")
        sys.exit(1)

    if args.mode == "backup":
        run_backup(root, args.keep, args.dry_run)
    elif args.mode == "export":
        run_export(root, args.domain or [], args.tag, args.dry_run)
    elif args.mode == "status":
        run_status(root, args.nutstore)


if __name__ == "__main__":
    main()

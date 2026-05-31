"""
agentos backup / restore — 备份与还原 agent-local/

备份内容:
  - materials/        (采集的原始素材)
  - memory/raw/       (L3 记忆原文)
  + 备份清单 manifest.json

不备份:
  - vector_db/        (可重建)
  - runtime/cache/    (临时缓存)
"""

import sys
import json
import tarfile
import shutil
from pathlib import Path
from datetime import datetime

from .utils import get_sync_root, get_local_root, info, ok, warn, err, banner


def build_manifest(local_root: Path, backup_dirs: list) -> dict:
    """生成备份清单"""
    manifest = {
        "created_at": datetime.now().isoformat(),
        "hostname": __import__("platform").node(),
        "agentos_version": "1.0.0",
        "items": [],
    }
    total_size = 0
    entry_count = 0
    for rel in backup_dirs:
        path = local_root / rel
        if not path.exists():
            continue
        if path.is_dir():
            for f in path.rglob("*"):
                if f.is_file() and f.name != ".DS_Store":
                    stat = f.stat()
                    total_size += stat.st_size
                    entry_count += 1
                    manifest["items"].append({
                        "path": str(f.relative_to(local_root)),
                        "size": stat.st_size,
                        "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
        else:
            stat = path.stat()
            total_size += stat.st_size
            entry_count += 1
            manifest["items"].append({
                "path": str(path.relative_to(local_root)),
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

    manifest["total_size"] = total_size
    manifest["entry_count"] = entry_count
    return manifest


def cmd_backup(output_path: str = None, full: bool = False):
    """执行备份"""
    banner()
    local_root = get_local_root()
    hostname = __import__("platform").node()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not local_root.exists():
        err(f"agent-local 目录不存在: {local_root}")
        sys.exit(1)

    # 确定备份目录
    if full:
        sync_root = get_sync_root()
        backup_dirs = ["."]  # 打包整个 agent-local/
        archive_name = f"agentos_full_{hostname}_{timestamp}.tar.gz"
    else:
        backup_dirs = ["materials", "memory/raw"]
        archive_name = f"agentos_local_{hostname}_{timestamp}.tar.gz"

    # 输出路径
    if output_path:
        out_dir = Path(output_path)
    else:
        out_dir = Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = out_dir / archive_name

    # 构建 manifest
    info("扫描备份内容...")
    manifest = build_manifest(local_root, backup_dirs)

    if manifest["entry_count"] == 0:
        warn("没有需要备份的文件")
        return

    print(f"  📊 待备份: {manifest['entry_count']} 个文件, {manifest['total_size'] / 1024 / 1024:.1f} MB")
    print(f"  📁 来源: {local_root}")

    # 创建 tar.gz
    info("打包中...")
    with tarfile.open(str(archive_path), "w:gz") as tar:
        # 添加 manifest
        manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
        import io
        manifest_file = io.BytesIO(manifest_bytes)
        tarinfo = tarfile.TarInfo(name="manifest.json")
        tarinfo.size = len(manifest_bytes)
        tar.addfile(tarinfo, manifest_file)

        # 添加备份目录
        for rel in backup_dirs:
            path = local_root / rel
            if path.exists():
                tar.add(str(path), arcname=rel)

    file_size_mb = archive_path.stat().st_size / 1024 / 1024
    ok(f"备份完成: {archive_path} ({file_size_mb:.1f} MB)")
    info(f"还原命令: agentos restore {archive_path}")
    print()


def run_restore(args):
    """执行还原"""
    banner()
    backup_path = Path(args.backup_path)
    if not backup_path.exists():
        err(f"备份文件不存在: {backup_path}")
        sys.exit(1)

    local_root = get_local_root()
    force = args.force

    info(f"从备份还原: {backup_path}")
    info(f"目标目录: {local_root}")

    # 读取 manifest
    manifest = None
    with tarfile.open(str(backup_path), "r:gz") as tar:
        try:
            mf = tar.extractfile("manifest.json")
            if mf:
                manifest = json.loads(mf.read().decode("utf-8"))
        except KeyError:
            pass

    if manifest:
        print(f"  📊 备份信息: {manifest['entry_count']} 个文件, {manifest['total_size'] / 1024 / 1024:.1f} MB")
        print(f"  🖥️  来源机器: {manifest.get('hostname', '?')}")
        print(f"  🕐 备份时间: {manifest.get('created_at', '?')}")
    else:
        info("  备份文件无 manifest.json（旧版本备份）")

    # 冲突检查
    conflicts = []
    if manifest and not force:
        for item in manifest["items"]:
            dest = local_root / item["path"]
            if dest.exists():
                conflicts.append(item["path"])

        if conflicts:
            print(f"\n⚠️  发现 {len(conflicts)} 个已存在的文件: (使用 --force 覆盖)")
            for c in conflicts[:10]:
                print(f"    {c}")
            if len(conflicts) > 10:
                print(f"    ... 还有 {len(conflicts) - 10} 个")
            print()

    # 确认
    if not force:
        reply = input("是否继续还原？(y/N): ").strip().lower()
        if reply != "y":
            info("已取消")
            return

    # 执行还原
    info("还原中...")
    with tarfile.open(str(backup_path), "r:gz") as tar:
        tar.extractall(path=str(local_root), filter="data")

    ok("还原完成")
    info("后续操作:")
    info("  1. 运行 agentos check 验证状态")
    info("  2. 如果向量库未一起还原，运行 agentos init 重建")
    print()


def run(args):
    cmd_backup(output_path=args.output, full=args.full)

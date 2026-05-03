"""
agentos check — 全系统健康检查
"""

import sys
import subprocess
from pathlib import Path

from .utils import (
    get_sync_root, get_local_root, get_python, get_npx,
    info, ok, warn, err, run, banner
)


def check_item(name: str, status: str, detail: str = ""):
    """输出检查项"""
    icon = {"ok": "✅", "warn": "⚠️ ", "fail": "❌"}
    label = {"ok": "通过", "warn": "警告", "fail": "失败"}
    print(f"  {icon.get(status, '❓')} [{label.get(status, '未知')}] {name}")
    if detail:
        print(f"      {detail}")


def cmd_check(quick: bool = False):
    """执行全系统健康检查"""
    banner()
    sync_root = get_sync_root()
    local_root = get_local_root()

    print("=" * 60)
    print("  全系统健康检查")
    print("=" * 60)
    print()

    # 1. 目录结构
    print("📁 目录结构:")
    check_item("agent-sync 根目录", "ok" if sync_root.exists() else "fail", str(sync_root))
    check_item("agent-local 根目录", "ok" if local_root.exists() else "fail", str(local_root))

    sync_skills = sync_root / "02_skills"
    sync_skills_count = len([d for d in sync_skills.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]) if sync_skills.exists() else 0
    check_item(f"技能目录 ({sync_skills_count} 个)", "ok" if sync_skills_count > 0 else "warn")

    local_materials = local_root / "materials" if local_root.exists() else None
    local_raw = local_root / "memory/raw" if local_root.exists() else None
    materials_exist = local_materials and local_materials.exists()
    raw_exist = local_raw and local_raw.exists()
    check_item("materials/", "ok" if materials_exist else "warn", "采集素材目录")
    check_item("memory/raw/", "ok" if raw_exist else "warn", "L3 记忆原文目录")

    # 2. 软链接
    print("\n🔗 软链接:")
    symlinks_to_check = [
        ("04_memory/long_term/raw", local_root / "memory/raw"),
        ("04_memory/vector_db", local_root / "memory/vector_db"),
        ("06_runtime/cache", local_root / "runtime/cache"),
    ]
    for link_rel, target in symlinks_to_check:
        link_path = sync_root / link_rel
        if link_path.is_symlink():
            actual = link_path.resolve()
            expected = target.resolve()
            if actual == expected:
                check_item(f"{link_rel} → OK", "ok")
            else:
                check_item(f"{link_rel} → 指向错误", "warn", f"实际: {actual}, 期望: {expected}")
        elif link_path.exists():
            check_item(f"{link_rel} → 真实目录", "ok")
        else:
            check_item(f"{link_rel} → 不存在", "fail")

    # 3. Python 环境
    print("\n🐍 Python 环境:")
    py = get_python()
    if Path(py).exists():
        result = run([py, "--version"])
        check_item("Python 版本", "ok" if result.returncode == 0 else "fail", result.stdout.strip() if result.returncode == 0 else "")
    else:
        check_item("Python 可执行文件", "fail", py)

    # 关键依赖检查
    deps = ["chromadb", "trafilatura", "feedparser", "sqlite_utils"]
    for dep in deps:
        result = run([py, "-c", f"import {dep}"])
        check_item(f"依赖: {dep}", "ok" if result.returncode == 0 else "fail")

    if quick:
        print("\n" + "=" * 60)
        ok("快速检查完成")
        return

    # 4. oMLX
    print("\n🤖 本地 LLM 引擎:")
    try:
        import json, urllib.request
        data = json.dumps({"model": "Qwen3-Embedding-0.6B-4bit-DWQ", "input": ["test"]}).encode()
        req = urllib.request.Request(
            "http://localhost:8000/v1/embeddings",
            data=data,
            headers={"Authorization": "Bearer omlx", "Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=5)
        check_item("oMLX Embedding API", "ok" if resp.status == 200 else "fail", f"状态码 {resp.status}")
    except Exception as e:
        check_item("oMLX Embedding API", "fail", str(e))

    # 音频转文字能力检查
    print("\n🎙️  音频转文字:")
    ffmpeg = run(["which", "ffmpeg"])
    if ffmpeg.returncode == 0:
        check_item("ffmpeg（系统工具）", "ok", "已安装")
    else:
        check_item("ffmpeg（系统工具）", "warn", "未安装，音频转文字不可用。运行: brew install ffmpeg")
    
    whisper_check = run([py, "-m", "pip", "show", "openai-whisper"])
    if whisper_check.returncode == 0:
        import re
        ver_match = re.search(r"Version:\s*(\S+)", whisper_check.stdout)
        ver = ver_match.group(1) if ver_match else "?"
        check_item("openai-whisper（Python包）", "ok", f"v{ver}")
        # 检查模型是否已下载
        import os as _os
        whisper_cache = _os.path.expanduser("~/.cache/whisper")
        if _os.path.exists(whisper_cache):
            models = [f for f in _os.listdir(whisper_cache) if f.endswith(('.pt', '.bin'))]
            if models:
                model_sizes = [_os.path.getsize(_os.path.join(whisper_cache, m)) / 1024 / 1024 for m in models]
                detail = ", ".join([f"{m} ({s:.0f}MB)" for m, s in zip(models, model_sizes)])
                check_item("Whisper 模型权重", "ok", f"已缓存: {detail}")
            else:
                check_item("Whisper 模型权重", "warn", "首次使用时会自动下载（~1.5GB）")
        else:
            check_item("Whisper 模型权重", "warn", "未下载，首次运行自动下载（~1.5GB）")
    else:
        check_item("openai-whisper（Python包）", "fail", "未安装，运行: pip install openai-whisper")

    # 5. facts.db
    print("\n🗄️  记忆层:")
    facts_db = sync_root / "04_memory" / "long_term" / "facts.db"
    if facts_db.exists():
        size_kb = facts_db.stat().st_size / 1024
        result = run([py, "-c", f"""
import sqlite3
conn = sqlite3.connect('{facts_db}')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM facts")
count = c.fetchone()[0]
c.execute("SELECT COUNT(DISTINCT subject) FROM facts")
subjects = c.fetchone()[0]
conn.close()
print(f"条目: {{count}}, 主题: {{subjects}}")
"""])
        check_item(f"facts.db ({size_kb:.1f} KB)", "ok", result.stdout.strip() if result.returncode == 0 else "读取异常")
    else:
        check_item("facts.db", "warn", "不存在（首次初始化正常）")

    # 6. 向量库
    vector_db = local_root / "vector_db" / "global" / "chroma"
    if vector_db.exists():
        chroma_files = list(vector_db.glob("*.sqlite3"))
        check_item("global 向量库", "ok" if chroma_files else "warn", f"目录存在但无 .sqlite3 文件" if not chroma_files else "")
    else:
        check_item("global 向量库", "warn", "未建，运行 agentos init 或 vector_db_rebuild.py 重建")

    # 7. WorkBuddy 技能注册
    print("\n📦 技能注册状态:")
    wb_skills = Path.home() / ".workbuddy" / "skills"
    sync_skills_dir = sync_root / "02_skills"
    if wb_skills.exists() and sync_skills_dir.exists():
        wb_names = {d.name for d in wb_skills.iterdir() if d.is_dir()}
        src_names = {d.name for d in sync_skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()}
        missing = src_names - wb_names
        extra = wb_names - src_names
        if missing:
            check_item(f"未注册到 WorkBuddy ({len(missing)} 个)", "warn", ", ".join(sorted(missing)))
        if extra:
            check_item(f"WB 中多余的 ({len(extra)} 个)", "warn", ", ".join(sorted(extra)))
        if not missing and not extra:
            check_item(f"技能一致性 ({len(src_names)} 个)", "ok", "源目录与 WB 注册一致")

    # 8. 磁盘
    print("\n💾 磁盘空间:")
    import shutil
    usage = shutil.disk_usage(str(Path.home()))
    free_gb = usage.free / (1024 ** 3)
    total_gb = usage.total / (1024 ** 3)
    pct = usage.free / usage.total * 100
    status = "ok" if pct > 10 else "warn"
    check_item(f"磁盘剩余", status, f"{free_gb:.0f} GB / {total_gb:.0f} GB ({pct:.0f}%)")

    print()
    print("=" * 60)
    ok("健康检查完成")
    print()


def install_deps(dry_run: bool = False):
    """安装 Python 依赖（被 init 调用）"""
    py = get_python()
    req_file = get_sync_root() / "requirements.txt"
    if not req_file.exists():
        warn(f"requirements.txt 不存在: {req_file}")
        return

    if dry_run:
        info(f"  [DRY-RUN] pip install -r {req_file}")
        return

    info("安装 Python 依赖...")
    result = run([py, "-m", "pip", "install", "-r", str(req_file), "--quiet"])
    if result.returncode == 0:
        ok("Python 依赖安装完成")
    else:
        warn(f"部分依赖安装失败:\n{result.stderr[:200]}")

    # 检查并提示安装 ffmpeg（音频转文字需要）
    ffmpeg = run(["which", "ffmpeg"])
    if ffmpeg.returncode != 0:
        print()
        warn("音频转文字功能需要 ffmpeg 系统工具")
        info("  运行以下命令安装:")
        info("    brew install ffmpeg")
        print()


def cmd_run(args):
    cmd_check(quick=args.quick)

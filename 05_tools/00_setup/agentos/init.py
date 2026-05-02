"""
agentos init — 换机一键初始化

流程:
1. 创建 agent-local/ 目录结构
2. 建立软链接
3. 安装 Python/Node 依赖
4. 注册技能到 WorkBuddy
5. 部署 MCP 配置
6. 创建自动化任务
7. 重建向量库
8. 环境验证
"""

import os
import sys
import shutil
from pathlib import Path

from .utils import (
    get_sync_root, get_local_root, get_python, get_npx,
    info, ok, warn, err, run, banner
)
from . import skill_mgr

# 本机专属目录结构
LOCAL_DIRS = [
    "memory/raw",
    "runtime/cache",
    "materials/web",
    "materials/video",
    "materials/audio",
    "materials/screenshots",
    "materials/refined_for_inbox/clipping",
    "materials/refined_for_inbox/feed",
    "materials/refined_for_inbox/personal",
    "materials/refined_for_inbox/memory",
]

# 软链接映射 {相对路径: 目标路径}
SYMLINKS = {
    "04_memory/long_term/raw": "memory/raw",
    "04_memory/vector_db": "memory/vector_db",
    "06_runtime/cache": "runtime/cache",
}

# 自动化任务定义 (name, prompt, rrule, schedule_type)
AUTOMATIONS = [
    {
        "name": "AgentOS 每日记忆提炼",
        "schedule_type": "recurring",
        "rrule": "FREQ=DAILY;BYHOUR=2;BYMINUTE=0",
        "prompt": f"""执行 AgentOS 每日记忆提炼任务。
先读取自动化记忆文件（如存在）了解历史。
执行命令:
{get_python()} {get_sync_root() / '02_skills/memory_manager/daily_digest.py'} --root {get_sync_root()}
汇报结果：新增了几条事实、去重了几条、冲突了几条。
写执行摘要到自动化记忆文件。""",
    },
    {
        "name": "AgentOS 收件箱汇聚",
        "schedule_type": "recurring",
        "rrule": "FREQ=DAILY;BYHOUR=2;BYMINUTE=30",
        "prompt": f"""执行 AgentOS 收件箱汇聚任务：扫描知识库各分类目录中的文件，提取主要内容生成标准化 MD 文件放入 00_inbox/。
执行命令：
{get_python()} {get_sync_root() / '02_skills/collect_to_inbox/collect_to_inbox.py'} --root {get_sync_root()}
汇报结果：扫描了几个目录、处理了几个文件、新增了几个收件箱文件。""",
    },
    {
        "name": "AgentOS 收件箱提纯",
        "schedule_type": "recurring",
        "rrule": "FREQ=DAILY;BYHOUR=3;BYMINUTE=0",
        "prompt": f"""执行 AgentOS 收件箱提纯任务：每日将 00_inbox/ 中的内容分类归档到知识库，更新首页统计和变更日志。
执行命令：
{get_python()} {get_sync_root() / '02_skills/inbox_refine/inbox_refine.py'} --root {get_sync_root()}
汇报结果：处理了几个收件箱文件、归档到了哪个分类目录。""",
    },
]


def step_local_dirs(dry_run: bool):
    """步骤1: 创建 agent-local/ 目录结构"""
    local_root = get_local_root()
    info(f"创建本地目录结构: {local_root}")
    for subdir in LOCAL_DIRS:
        target = local_root / subdir
        if not target.exists():
            if dry_run:
                info(f"  [DRY-RUN] 创建: {target}")
            else:
                target.mkdir(parents=True, exist_ok=True)
                ok(f"  创建: {subdir}")
        else:
            ok(f"  已存在: {subdir}")


def step_symlinks(dry_run: bool):
    """步骤2: 重建软链接"""
    sync_root = get_sync_root()
    local_root = get_local_root()
    info("重建软链接...")
    for link_rel, target_rel in SYMLINKS.items():
        link_path = sync_root / link_rel
        target_path = local_root / target_rel
        if dry_run:
            info(f"  [DRY-RUN] 软链: {link_rel} → {target_path}")
            continue
        if link_path.is_symlink():
            current_target = os.readlink(str(link_path))
            if current_target == str(target_path):
                ok(f"  软链正确: {link_rel}")
                continue
            info(f"  更新软链: {link_rel} → {target_path}")
            link_path.unlink()
        elif link_path.exists():
            warn(f"  {link_rel} 是真实目录，保留不动")
            continue
        link_path.parent.mkdir(parents=True, exist_ok=True)
        link_path.symlink_to(target_path)
        ok(f"  创建软链: {link_rel} → {target_path}")


def step_install_skills(dry_run: bool):
    """步骤3: 注册技能到 WorkBuddy"""
    if dry_run:
        info("  [DRY-RUN] 安装所有技能到 WorkBuddy")
        return
    info("安装技能到 WorkBuddy...")
    skill_mgr.install_all(get_sync_root() / "02_skills")


def step_deploy_mcp(dry_run: bool):
    """步骤4: 部署 MCP 配置"""
    sync_root = get_sync_root()
    mcp_src = sync_root / "01_core" / "mcp.json"
    mcp_dst = Path.home() / ".workbuddy" / "mcp.json"

    if not mcp_src.exists():
        warn(f"MCP 配置源文件不存在: {mcp_src}")
        return

    if dry_run:
        info(f"  [DRY-RUN] 部署 MCP: {mcp_src} → {mcp_dst}")
        return

    # 备份现有配置
    if mcp_dst.exists():
        backup_dst = mcp_dst.with_suffix(".json.bak")
        shutil.copy2(str(mcp_dst), str(backup_dst))
        info(f"  备份旧 MCP 配置: {backup_dst}")

    shutil.copy2(str(mcp_src), str(mcp_dst))
    ok(f"MCP 配置已部署: {mcp_dst}")


def step_create_automations(dry_run: bool):
    """步骤5: 创建自动化任务"""
    if dry_run:
        info(f"  [DRY-RUN] 创建 {len(AUTOMATIONS)} 个自动化任务")
        return
    # 自动化任务通过 WorkBuddy 自动化工具创建
    # 当前方案：在 init 完成后提示用户手动在 WorkBuddy 中配置
    info("自动化任务定义:")
    for a in AUTOMATIONS:
        info(f"  📋 {a['name']} — {a['rrule']}")
    info("请在新机 WorkBuddy 中配置自动化任务，或运行 agentos sync 同步")


def step_rebuild_vector_db(dry_run: bool):
    """步骤6: 重建向量库"""
    py = get_python()
    script = get_sync_root() / "02_skills/kb_manager/vector_db_rebuild.py"
    if not script.exists():
        warn(f"向量库重建脚本不存在: {script}，跳过")
        return
    if dry_run:
        info(f"  [DRY-RUN] 重建向量库: {py} {script}")
        return
    info("重建向量库...")
    result = run([
        py, str(script),
        "--root", str(get_sync_root()),
        "--local", str(get_local_root()),
        "--track", "both",
    ])
    if result.returncode == 0:
        ok("向量库重建完成")
    else:
        warn(f"向量库重建失败:\n{result.stderr}")


def step_verify(dry_run: bool):
    """步骤7: 环境验证"""
    if dry_run:
        info("  [DRY-RUN] 环境验证跳过")
        return
    info("验证环境...")

    # 验证 Python
    py = get_python()
    result = run([py, "--version"])
    ok(f"Python: {result.stdout.strip()}" if result.returncode == 0 else "Python: 异常")

    # 验证 oMLX
    import json, urllib.request
    try:
        data = json.dumps({"model": "mlx-community--Qwen3-Embedding-0.6B-4bit-DWQ", "input": ["test"]}).encode()
        req = urllib.request.Request(
            "http://localhost:8000/v1/embeddings",
            data=data,
            headers={"Authorization": "Bearer 5omlx", "Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=5)
        if resp.status == 200:
            ok("oMLX Embedding API: 正常")
        else:
            warn(f"oMLX Embedding API: 状态码 {resp.status}")
    except Exception as e:
        warn(f"oMLX Embedding API: 连接失败 ({type(e).__name__})")

    # 验证 facts.db
    facts_db = get_sync_root() / "04_memory/long_term/facts.db"
    if facts_db.exists():
        size_kb = facts_db.stat().st_size / 1024
        ok(f"facts.db: {size_kb:.1f} KB")
    else:
        warn("facts.db 不存在（首次初始化正常）")


def step_check_path(dry_run: bool):
    """检查 agentos CLI 是否在 PATH 中，不在则添加"""
    local_bin = Path.home() / ".local" / "bin"
    if not local_bin.exists():
        return
    if not (local_bin / "agentos").exists():
        return

    path_str = os.environ.get("PATH", "")
    local_bin_str = str(local_bin)
    if local_bin_str in path_str:
        info(f"agentos CLI 已在 PATH 中: {local_bin}/agentos")
        return

    shell_rc = None
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        shell_rc = Path.home() / ".zshrc"
    elif "bash" in shell:
        shell_rc = Path.home() / ".bash_profile"

    if shell_rc and shell_rc.exists():
        export_line = f'\nexport PATH="$HOME/.local/bin:$PATH"\n'
        if dry_run:
            info(f"[DRY-RUN] 将添加 PATH 到 {shell_rc}")
            return
        with open(shell_rc, "a") as f:
            f.write(export_line)
        ok(f"已添加 ~/.local/bin 到 PATH ({shell_rc})")
        info(f"执行以下命令生效: source {shell_rc.name}")
    else:
        warn(f"~/.local/bin 未在 PATH 中")
        info(f"手动添加: echo 'export PATH=\"$HOME/.local/bin:\$PATH\"' >> ~/.zshrc")


def do_init(args):
    """执行 init 流程"""
    dry_run = args.dry_run
    skip_deps = args.skip_deps

    banner()
    info("开始换机一键初始化" + (" [DRY-RUN]" if dry_run else ""))
    print()

    # 依次执行各步骤
    step_local_dirs(dry_run)
    print()
    step_symlinks(dry_run)
    print()
    if not skip_deps:
        from . import check as check_mod
        check_mod.install_deps(dry_run)
    print()
    step_install_skills(dry_run)
    print()
    step_deploy_mcp(dry_run)
    print()
    step_create_automations(dry_run)
    print()
    step_rebuild_vector_db(dry_run)
    print()
    step_verify(dry_run)

    # 检查 agentos CLI 是否在 PATH 中
    step_check_path(dry_run)

    print()
    print("=" * 60)
    if dry_run:
        info("DRY-RUN 完成，以上为即将执行的操作")
    else:
        ok("初始化完成！请重启 WorkBuddy 使更改生效。")
        info("后续操作：")
        info("  1. 重启 WorkBuddy")
        info("  2. 如有旧机备份，运行: agentos restore <备份文件>")
        info("  3. 运行: agentos upgrade 统一升级所有模块")
        info("  4. 运行: agentos check 验证系统状态")
        info("  5. 运行: agentos localize 生成本机身份配置")
    print()


def do_localize(args):
    """从模板生成本机身份配置"""
    from pathlib import Path
    from .utils import get_sync_root, get_local_root, info, ok, warn

    sync_root = get_sync_root()
    local_root = get_local_root()
    identity_dir = local_root / "identity"
    identity_dir.mkdir(parents=True, exist_ok=True)

    templates = {
        sync_root / "01_core" / "IDENTITY.tpl.md": identity_dir / "IDENTITY.md",
        sync_root / "01_core" / "USER.tpl.md": identity_dir / "USER.md",
        sync_root / "01_core" / "HOST_ID.tpl.md": identity_dir / "HOST_ID.md",
    }

    dry_run = getattr(args, "dry_run", False)

    print()
    print("=" * 60)
    print("  🆔 AgentOS 本机身份生成")
    print("=" * 60)
    print()

    for src, dst in templates.items():
        if not src.exists():
            warn(f"模板文件不存在: {src}")
            continue
        if dry_run:
            info(f"[DRY-RUN] 生成: {dst}")
            continue
        if dst.exists():
            ok(f"  ✓ {dst.name} (跳过，已存在)")
            continue
        import shutil
        shutil.copy2(str(src), str(dst))
        ok(f"  ✓ {dst.name}")

    host_id = identity_dir / "HOST_ID.md"
    if host_id.exists() and not dry_run:
        print()
        info("HOST_ID.md 已生成，默认角色为 node（最低权限）。")
        info("如需提升权限，编辑角色字段：")
        print(f"  文件路径: {host_id}")
        print()
        print("  可选角色: master, maintainer, node")
        print("    master     → 知识提纯/记忆汇总/核心维护")
        print("    maintainer → 内容采集/本地记忆/提交有价值内容")
        print("    node       → 信息采集/素材上传（默认）")
        print()
        info("安全建议：先以 node 运行，确认无误后再提升权限。")
        print()

    ok("本机身份文件生成完成")
    info(f"身份目录: {identity_dir}")
    info("可手动编辑 HOST_ID.md 修改角色和能力开关")

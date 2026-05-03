"""
agentos upgrade — 统一模块升级引擎 (v1.0.0)

扫描 agent-sync/ 下所有模块，对每个模块执行标准化 4 步升级：
  1. 检测模块状态（有 MODULE.md？install.sh？）
  2. 运行 install.sh（建目录 + 写 local.yaml）
  3. 安装 Python 依赖（pip install -r requirements.txt）
  4. 运行 check 脚本（验证配置 + 环境完整性）

用法:
    agentos upgrade               全量升级所有模块
    agentos upgrade --module matrix  只升级指定模块

最后更新: 2026-05-01
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .const import __agent_sync_root__, __agent_local_root__

# 模块类型
MODULE_TYPES = {
    "02_skills": "skill",
    "05_tools": "tool",
    "03_knowledge": "knowledge",
    "04_memory": "memory",
}

# 模块扫描目录（按优先级排序）
SCAN_DIRS = ["05_tools", "02_skills"]


class ModuleInfo:
    """解析后的模块信息"""

    def __init__(self, path: Path, rel_path: str):
        self.path = path                 # 模块目录绝对路径
        self.rel_path = rel_path         # 相对 agent-sync/ 的路径
        self.name = path.name
        self.type = self._detect_type()
        self.has_module_md = (path / "MODULE.md").exists()
        self.has_install_sh = (path / "install.sh").exists()
        self.has_requirements = (path / "requirements.txt").exists()
        self.has_check_sh = (path / "check.sh").exists()
        self.has_config_template = (path / "config_template").exists()
        self.local_dir = self._calc_local_dir()

    def _detect_type(self) -> str:
        for prefix, mtype in MODULE_TYPES.items():
            if self.rel_path.startswith(prefix):
                return mtype
        return "unknown"

    def _calc_local_dir(self) -> Optional[Path]:
        """计算对应的 agent-local 目录路径"""
        if self.type == "tool":
            # 05_tools/07_matrix  →  agent-local/tools/matrix
            parts = self.rel_path.split("/")
            if len(parts) >= 2:
                return Path(__agent_local_root__) / "tools" / "_".join(parts[1:])
        return None

    def __repr__(self):
        return f"<{self.type}:{self.name}>"


# ══════════════════════════════════════════════════════════════
# 模块扫描
# ══════════════════════════════════════════════════════════════

def scan_modules(target: str = None) -> list:
    """扫描 agent-sync/ 下所有可用模块
    
    参数:
        target: 指定模块名（可选）
    
    返回:
        list[ModuleInfo]: 模块列表
    """
    sync_root = Path(__agent_sync_root__)
    modules = []

    for scan_dir in SCAN_DIRS:
        scan_path = sync_root / scan_dir
        if not scan_path.exists():
            continue
        for item in sorted(scan_path.iterdir()):
            if not item.is_dir():
                continue
            # 跳过隐藏目录和 __pycache__
            if item.name.startswith(".") or item.name == "__pycache__":
                continue
            # 如果是 05_tools，跳过 00_setup（agentos 自身）和单文件目录
            if scan_dir == "05_tools":
                parts = item.name.split("_", 1)
                if len(parts) < 2 or not parts[0].isdigit():
                    continue

            rel = f"{scan_dir}/{item.name}"
            module = ModuleInfo(item, rel)

            if target and target != module.name:
                continue

            modules.append(module)

    return modules


# ══════════════════════════════════════════════════════════════
# 升级步骤
# ══════════════════════════════════════════════════════════════

def _run(cmd: list, cwd: Path = None, timeout: int = 120) -> tuple:
    """运行命令并返回 (ok, stdout_preview)"""
    try:
        result = subprocess.run(
            cmd, cwd=cwd or Path.cwd(),
            capture_output=True, text=True, timeout=timeout
        )
        ok = result.returncode == 0
        out = (result.stdout or result.stderr or "").strip()[:200]
        return ok, out
    except Exception as e:
        return False, str(e)


def step_git_pull() -> tuple:
    """Step 0: 拉取最新代码"""
    sync_root = Path(__agent_sync_root__)
    if not (sync_root / ".git").exists():
        return "skipped", "非 Git 仓库，跳过"
    ok, out = _run(["git", "pull", "origin", "main"], cwd=sync_root)
    return ("ok" if ok else "fail"), out


def step_install(module: ModuleInfo) -> tuple:
    """Step 1: 运行 install.sh（如果有）"""
    install_path = module.path / "install.sh"
    if not install_path.exists():
        return "skipped", "无 install.sh"

    # 传入 managed Python 路径（所有机器统一版本，避免差异）
    from .utils import get_python
    env = os.environ.copy()
    env["WORKBUDDY_PYTHON"] = get_python()

    try:
        result = subprocess.run(
            ["bash", str(install_path)],
            capture_output=True, text=True, timeout=120,
            env=env
        )
        ok = result.returncode == 0
        out = (result.stdout or result.stderr or "").strip()[:200]
        status = "ok" if ok else "fail"
        return status, out
    except subprocess.TimeoutExpired:
        return "fail", "安装超时（网络慢？可稍后手动安装）"
    except Exception as e:
        return "fail", str(e)


def step_pip(module: ModuleInfo) -> tuple:
    """Step 2: 安装 Python 依赖"""
    req_path = module.path / "requirements.txt"
    if not req_path.exists():
        return "skipped", "无 requirements.txt"

    # 使用统一 managed Python（所有机器保持同一版本，避免差异）
    from .utils import get_python
    python = get_python()
    ok, out = _run([python, "-m", "pip", "install", "-r", str(req_path), "-q"])
    status = "ok" if ok else "fail"
    return status, out


def step_check(module: ModuleInfo) -> tuple:
    """Step 3: 运行 check 脚本（如果有）"""
    check_path = module.path / "check.sh"
    if not check_path.exists():
        return "skipped", "无 check.sh"

    ok, out = _run(["bash", str(check_path)])
    status = "ok" if ok else "fail"
    return status, out


def step_environ(module: ModuleInfo) -> list:
    """Step 4: 环境完整性检查（不执行，只报告）"""
    notes = []

    # 检查 local 目录
    if module.local_dir:
        if not module.local_dir.exists():
            notes.append("⚠️  agent-local 目录未创建，需要 install.sh")
        else:
            subdirs = ["config", "data", "logs", "profiles"]
            missing = [d for d in subdirs if not (module.local_dir / d).exists()]
            if missing:
                notes.append(f"⚠️  缺少子目录: {', '.join(missing)}")

    # 检查 config_template
    if module.has_config_template:
        target_conf = module.local_dir / "config" if module.local_dir else None
        if target_conf:
            has_config = any(target_conf.glob("*.yaml")) or any(target_conf.glob("*.yml"))
            if not has_config:
                notes.append("📋  需配置: cp config_template/*.yaml → agent-local/config/")

    return notes


# ══════════════════════════════════════════════════════════════
# 主升级流程
# ══════════════════════════════════════════════════════════════

def do_upgrade(args):
    """执行升级流程"""
    target = getattr(args, "module", None)
    dry_run = getattr(args, "dry_run", False)

    print(f"\n{'='*60}")
    print(f"  🔄 AgentOS 统一升级")
    print(f"  {'(dry-run)' if dry_run else '(执行模式)'}")
    print(f"{'='*60}\n")

    # Step 0: 拉取代码
    print(f"▶ git pull")
    status, detail = step_git_pull()
    print(f"  {_icon(status)} {detail}")

    # 扫描模块
    modules = scan_modules(target)
    if not modules:
        print(f"\n  ❌ 未找到模块" + (f" (匹配: {target})" if target else ""))
        return

    print(f"\n  扫描到 {len(modules)} 个模块:")
    for m in modules:
        print(f"    {m.type:6s}  {m.name:25s}  {m.rel_path}")
    print()

    # 逐模块升级
    results = {}
    for module in modules:
        # 判断模块层级
        has_local_needs = module.has_install_sh or module.has_requirements or module.has_config_template
        if not has_local_needs:
            # L1 纯代码模块
            print(f"  📦 {module.name} ({module.type}) — 纯代码模块，无需本地部署")
            module_results = {"install": ("skipped", ""), "pip": ("skipped", ""), "check": ("skipped", "")}
            print(f"  install:  ⏭️ 无本地依赖")
            print(f"  pip:      ⏭️ 无 Python 依赖")
            print(f"  check:    ⏭️ 无检查脚本")
        else:
            print(f"{'─'*60}")
            print(f"  📦 {module.name} ({module.type})")
            print(f"{'─'*60}")

            module_results = {}

            # Step 1: install.sh
            s, d = step_install(module)
            module_results["install"] = (s, d)
            print(f"  install:  {_icon(s)} {d[:80]}")

            # Step 2: pip install
            s, d = step_pip(module)
            module_results["pip"] = (s, d)
            print(f"  pip:      {_icon(s)} {d[:80]}")

            # Step 3: check.sh
            s, d = step_check(module)
            module_results["check"] = (s, d)
            print(f"  check:    {_icon(s)} {d[:80]}")

        # Step 4: 环境检查
        notes = step_environ(module)
        module_results["environ"] = notes
        for n in notes:
            print(f"  {n}")

        results[module.name] = module_results
        print()

    # 如果有 Skill 模块，自动注册到 WorkBuddy
    has_skills = any(m.type == "skill" for m in modules)
    if has_skills and not dry_run:
        print(f"{'─'*60}")
        print(f"  🔗 注册技能到 WorkBuddy...")
        from . import skill_mgr
        try:
            skill_mgr.run(argparse.Namespace(skill_cmd="install"))
            print(f"  ✅ 技能注册完成")
        except Exception as e:
            print(f"  ⚠️  技能注册失败: {e}")
            print(f"     可稍后手动执行: agentos skill install")
        print()

    # 自动注册到集群
    if not dry_run:
        print(f"{'─'*60}")
        print(f"  📡 自动注册到集群...")
        try:
            import subprocess
            sync_root = get_sync_root()
            script = str(sync_root / "05_tools" / "01_system" / "cluster_registry.py")
            result = subprocess.run(
                [sys.executable, script, "register"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                print(f"  ✅ 集群注册完成")
            else:
                print(f"  ⚠️  集群注册失败: {result.stderr.strip()}")
        except Exception as e:
            print(f"  ⚠️  集群注册异常: {e}")
            print(f"     可稍后手动执行: agentos register")
        print()

    # 汇总报告
    _print_report(results, modules)


def _icon(status: str) -> str:
    return {"ok": "✅", "fail": "❌", "skipped": "⏭️"}.get(status, "❓")


def _print_report(results: dict, modules: list):
    """打印升级报告"""
    print(f"{'='*60}")
    print(f"  📋 升级报告")
    print(f"{'='*60}\n")

    # 按层级分组统计
    l1_count = sum(1 for m in modules if not m.has_install_sh and not m.has_requirements)
    l2_count = sum(1 for m in modules if m.has_install_sh or m.has_requirements)
    ok_count = 0
    warn_count = 0

    for module in modules:
        r = results.get(module.name, {})
        install_s = r.get("install", ("skipped", ""))[0]
        pip_s = r.get("pip", ("skipped", ""))[0]
        check_s = r.get("check", ("skipped", ""))[0]
        notes = r.get("environ", [])

        has_local = module.has_install_sh or module.has_requirements
        module_ok = all(s == "ok" or s == "skipped" for s in [install_s, pip_s, check_s])

        if module_ok:
            ok_count += 1
        else:
            warn_count += 1

        if has_local:
            print(f"  📦 {module.name:25s}  {_icon(install_s)} install  {_icon(pip_s)} pip  {_icon(check_s)} check")
        else:
            print(f"  📦 {module.name:25s}  ⏭️ 纯代码模块（无本地依赖）")
        for n in notes:
            print(f"  {'':25s}  {n}")

    print(f"\n  L1 纯代码模块: {l1_count} 个（自动跳过，无需部署）")
    print(f"  L2 本地数据模块: {l2_count} 个（已执行 install/pip/check）")
    print()
    print(f"{'-'*60}")
    if warn_count == 0:
        print(f"  ✅ 全部 {ok_count} 个模块检查完成")
    else:
        print(f"  ⚠️  {ok_count} 个正常, {warn_count} 个需关注")
    print(f"{'-'*60}")
    print()

    # 手动操作提示
    manual_steps = []
    for module in modules:
        if module.name == "matrix":
            manual_steps.append(f"  ☐ Matrix: 配置 {__agent_local_root__}/tools/matrix/config/accounts.yaml")
            manual_steps.append(f"  ☐ Matrix: 运行 switch_account.py --method profile 重新登录")
    if manual_steps:
        print(f"  需手动操作:")
        for s in manual_steps:
            print(s)
        print()


def setup_parser(subparsers):
    """向主 CLI 注册 upgrade 子命令"""
    p = subparsers.add_parser("upgrade", help="统一升级：拉取代码 + 安装依赖 + 环境检查")
    p.add_argument("--module", "-m", type=str, default=None,
                   help="只升级指定模块（如 matrix）")
    p.add_argument("--dry-run", action="store_true",
                   help="仅预览，不执行实际操作")
    p.set_defaults(func=do_upgrade)


def do_rebuild_vector(args):
    """重建本地向量数据库"""
    import subprocess as sp
    from pathlib import Path
    from .utils import get_sync_root, get_local_root, get_python

    sync_root = get_sync_root()
    local_root = get_local_root()
    python = get_python()

    track = getattr(args, "track", "both")
    dry_run = getattr(args, "dry_run", False)
    incremental = getattr(args, "incremental", False)

    script = sync_root / "02_skills" / "kb_manager" / "vector_db_rebuild.py"
    if not script.exists():
        print(f"❌ 向量重建脚本不存在: {script}")
        return

    cmd = [
        str(python),
        str(script),
        "--root", str(sync_root),
        "--local", str(local_root),
        "--track", track,
    ]
    if incremental:
        cmd.append("--incremental")
    if dry_run:
        cmd.append("--dry-run")

    print(f"🔄 重建向量数据库 ({track})")
    result = sp.run(cmd, cwd=str(sync_root))
    if result.returncode == 0:
        print("✅ 向量数据库重建完成")
    else:
        print(f"❌ 向量数据库重建失败 (rc={result.returncode})")


def _run_cluster_script(args, subcommand: str):
    """运行集群注册表脚本"""
    import subprocess as sp
    from pathlib import Path
    from .utils import get_sync_root

    sync_root = get_sync_root()
    script = sync_root / "05_tools" / "01_system" / "cluster_registry.py"
    if not script.exists():
        print(f"❌ 集群脚本不存在: {script}")
        return

    result = sp.run(
        [sys.executable, str(script), subcommand],
        cwd=str(sync_root)
    )
    return result.returncode


def do_cluster_register(args):
    """注册本机到集群"""
    _run_cluster_script(args, "register")


def do_cluster_status(args):
    """查看集群状态"""
    _run_cluster_script(args, "status")


def do_cluster_cleanup(args):
    """清理过期注册条目"""
    _run_cluster_script(args, "cleanup")

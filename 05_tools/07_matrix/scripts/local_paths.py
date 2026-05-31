"""
路径配置模块 — 统一管理本机数据目录路径

通过读取 07_matrix/local.yaml 获取本机数据根目录，
所有 Python 脚本通过本模块获取路径，不再依赖软链接。

本模块为代码层（参与坚果云同步），local.yaml 为数据层（每台机器自生成，不参与同步）。

用法:
    from local_paths import config_path, data_path, logs_path, profiles_path, screenshots_path, code_dir

    accounts = config_path("accounts.yaml")       # → agent-local/.../config/accounts.yaml
    db       = data_path("matrix.db")              # → agent-local/.../data/matrix.db
    logfile  = logs_path("task.log")               # → agent-local/.../logs/task.log
    profile  = profiles_path("douyin_01")          # → agent-local/.../profiles/douyin_01
    screenshot = screenshots_path("snap.png")      # → agent-local/.../screenshots/snap.png
    blueprint = code_dir() / "blueprints" / "xxx.json"  # 代码目录下的文件
"""

from pathlib import Path
import sys

# 代码根目录 (07_matrix/)
CODE_DIR = Path(__file__).resolve().parent.parent

# 本地配置文件路径
_LOCAL_CONF = CODE_DIR / "local.yaml"

# 延迟加载缓存
_LOCAL_ROOT = None


def _load_config() -> dict:
    """读取 local.yaml 配置"""
    if not _LOCAL_CONF.exists():
        print(
            f"\n"
            f"❌ local.yaml 不存在，请先运行安装脚本:\n"
            f"   bash {CODE_DIR / 'install.sh'}\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # 用内置方式解析 YAML（只读 matrix.local_data_root，避免依赖 pyyaml）
    with open(_LOCAL_CONF, encoding="utf-8") as f:
        content = f.read()

    for line in content.splitlines():
        line = line.strip()
        if line.startswith("local_data_root:"):
            value = line.split(":", 1)[1].strip().strip('"').strip("'")
            return {"matrix": {"local_data_root": value}}

    print(
        f"❌ local.yaml 中缺少 local_data_root 配置\n",
        file=sys.stderr,
    )
    sys.exit(1)


def _get_local_root() -> Path:
    """获取本机数据根目录（延迟加载 + 缓存）"""
    global _LOCAL_ROOT
    if _LOCAL_ROOT is not None:
        return _LOCAL_ROOT

    cfg = _load_config()
    root_str = cfg.get("matrix", {}).get("local_data_root", "")
    if not root_str:
        print("❌ local.yaml 中缺少 local_data_root 配置", file=sys.stderr)
        sys.exit(1)

    _LOCAL_ROOT = Path(root_str).expanduser().resolve()
    _LOCAL_ROOT.mkdir(parents=True, exist_ok=True)
    return _LOCAL_ROOT


def code_dir() -> Path:
    """返回代码根目录 (07_matrix/)"""
    return CODE_DIR


def _local_subdir(name: str, *parts) -> Path:
    """获取本机数据目录下的子目录/文件路径，自动创建父目录"""
    root = _get_local_root()
    target = root / name / Path(*parts) if parts else root / name

    # 如果有子路径（文件），只创建父目录
    if parts:
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        target.mkdir(parents=True, exist_ok=True)

    return target


def config_path(*parts) -> Path:
    """→ agent-local/.../config/[*parts]"""
    return _local_subdir("config", *parts)


def data_path(*parts) -> Path:
    """→ agent-local/.../data/[*parts]"""
    return _local_subdir("data", *parts)


def logs_path(*parts) -> Path:
    """→ agent-local/.../logs/[*parts]"""
    return _local_subdir("logs", *parts)


def profiles_path(*parts) -> Path:
    """→ agent-local/.../profiles/[*parts]"""
    return _local_subdir("profiles", *parts)


def screenshots_path(*parts) -> Path:
    """→ agent-local/.../screenshots/[*parts]"""
    return _local_subdir("screenshots", *parts)

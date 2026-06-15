# plugins/base.py
# Dashboard v4.0 插件基类 — 联邦控制中心规范
# 版本: 2.0.0 | 更新: 2026-05-18

import json, os, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any

# ── 路径常量（所有插件用这些, 禁止硬编码）──────────────────
# 优先级: 环境变量 > Path.home()
# 其他机器只需 export AGENT_SYNC=... 和 AGENT_LOCAL=... 即可
HOME = Path.home()
AGENT_SYNC = Path(os.environ.get("AGENT_SYNC", str(HOME / "workbuddy-agent-os" / "agent-sync")))
AGENT_LOCAL = Path(os.environ.get("AGENT_LOCAL", str(HOME / "workbuddy-agent-os" / "agent-local")))
CROSS_MACHINE = AGENT_SYNC / "04_memory" / "cross_machine"
DASHBOARD_LOCAL = AGENT_LOCAL / "runtime" / "dashboard"

# ── 本机身份 ───────────────────────────────────────────────
HOSTNAME_FILE = AGENT_LOCAL / "identity" / "cached_hostname"
UID_FILE = AGENT_LOCAL / "identity" / "machine_uid"

def resolve_hostname() -> str:
    if HOSTNAME_FILE.exists():
        return HOSTNAME_FILE.read_text().strip()
    return os.uname().nodename

def resolve_uid() -> str:
    if UID_FILE.exists():
        return UID_FILE.read_text().strip()
    return "unknown"

HOSTNAME = resolve_hostname()
MACHINE_UID = resolve_uid()


class DashboardPlugin:
    """插件基类 v2.0

    每个系统模块实现此基类, 自动注册到联邦控制中心。
    插件实例化后, summary() 数据自动写入 cross_machine/data/{name}/{uid}.json
    供所有机器的 Dashboard 读取展示。

    子类必须定义:
        name, label, icon, version, description, order

    子类必须实现:
        summary(machines) — 返回概览数据 (含各机器分区)
        detail(machine)   — 返回指定机器的详细数据

    子类可选实现:
        actions()         — 返回可执行操作列表
    """

    # ── 元信息 (子类必须定义) ───────────────────────────────
    name: str = ""              # 唯一标识, 如 "matrix"
    label: str = ""             # 中文名, 如 "账号矩阵"
    icon: str = "📦"           # 图标
    version: str = "1.0.0"     # 插件版本
    description: str = ""      # 简要说明
    order: int = 99            # 排序 (值越小越靠前)

    # ── 核心接口 (子类必须实现) ─────────────────────────────

    def summary(self, machines: list[str]) -> dict:
        """
        概览数据。machines: 当前所有在线机器 hostname 列表。
        返回结构示例:
        {
            "总账号": 8,
            "在线": 6,
            "各机器": {
                "chengzigedeAir": {"账号":5, "在线":4},
                "Redmi-12C": {"账号":3, "在线":2},
                "7kechengdeAir": {"_note": "未接入此模块"},
            }
        }
        某机器未接入此模块时, 返回 {"_note": "未接入此模块"}
        """
        raise NotImplementedError

    def detail(self, machine: str = "") -> dict:
        """
        详细面板数据。machine="" 返回所有机器汇总; 否则返回指定机器。
        返回结构由各插件自定义。
        """
        raise NotImplementedError

    # ── 可选覆写 ────────────────────────────────────────────

    def actions(self) -> list[dict]:
        """可执行操作列表, 用于 Dashboard 操作面板"""
        return []

    def get_sub_views(self) -> list[dict]:
        """返回该插件下的子视图列表
        每个子视图: {"key": "characters", "label": "角色管理", "icon": "🧑", "group":"ave"}
        返回空列表表示该插件没有子视图（仅使用主视图）
        group: 用于前端侧边栏分组
        """
        return []

    def health_check(self) -> bool:
        """健康检查"""
        return self.is_available()

    # ── 数据写入 ────────────────────────────────────────────

    def write_shared(self):
        """将 summary() 数据写入 cross_machine, 供其他机器读取"""
        from ._registry import get_machine_list
        machines = get_machine_list()
        try:
            data = self.summary(machines)
        except Exception as e:
            data = {"_error": str(e)}
        out = {
            "plugin": self.name,
            "version": self.version,
            "machine_uid": MACHINE_UID,
            "hostname": HOSTNAME,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        path = CROSS_MACHINE / "data" / self.name
        path.mkdir(parents=True, exist_ok=True)
        (path / f"{MACHINE_UID}.json").write_text(
            json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── 兼容旧版 ────────────────────────────────────────────

    def is_available(self) -> bool:
        """旧版兼容"""
        return True

    def get_summary(self) -> dict:
        """旧版兼容 — 转为 summary(machines)"""
        from ._registry import get_machine_list
        return self.summary(get_machine_list())

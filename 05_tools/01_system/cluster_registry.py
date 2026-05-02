#!/usr/bin/env python3
"""
AgentOS 多机注册表与冲突检测

每台机器在 agent-sync/04_memory/cross_machine/registry/ 下有一个注册文件，
Git 同步后所有机器可见。

核心功能：
1. agentos register   → 更新/创建本机注册（角色、状态、时间戳）
2. agentos cluster-status → 查看所有在线机器的角色和状态
3. pre_task_check()  → 执行任务前检测冲突（入口供 role_check.py 调用）
"""
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 路径
SYNC_ROOT = Path.home() / "workbuddy-agent-os" / "agent-sync"
LOCAL_ROOT = Path.home() / "workbuddy-agent-os" / "agent-local"
REGISTRY_DIR = SYNC_ROOT / "04_memory" / "cross_machine" / "registry"
LOCAL_HOST_ID = LOCAL_ROOT / "identity" / "HOST_ID.md"
HOSTNAME = os.uname().nodename if hasattr(os, 'uname') else os.environ.get('HOSTNAME', 'unknown')
try:
    HOSTNAME = os.uname().nodename
except AttributeError:
    HOSTNAME = os.environ.get('COMPUTERNAME', 'unknown').lower()


def get_host_display_name() -> str:
    """获取可读的主机显示名"""
    import subprocess
    try:
        result = subprocess.run(
            ["scutil", "--get", "LocalHostName"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return HOSTNAME


def get_my_role() -> str:
    """从本机 HOST_ID.md 读取角色"""
    if not LOCAL_HOST_ID.exists():
        return "unknown"
    try:
        content = LOCAL_HOST_ID.read_text(encoding="utf-8")
        for line in content.split("\n"):
            if "角色:" in line:
                role = line.split("角色:")[-1].strip()
                if role:
                    return role
    except Exception:
        pass
    return "unknown"


def get_my_status() -> str:
    """检测本机状态：online / idle / error"""
    return "online"


def my_entry() -> dict:
    """生成本机注册条目"""
    return {
        "hostname": get_host_display_name(),
        "system_hostname": HOSTNAME,
        "role": get_my_role(),
        "status": get_my_status(),
        "last_seen": datetime.now(timezone.utc).isoformat(),
    }


def read_all_entries() -> list:
    """扫描 registry/ 目录，读取所有机器的注册"""
    if not REGISTRY_DIR.exists():
        REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        return []
    
    entries = []
    for f in sorted(REGISTRY_DIR.glob("*.json")):
        try:
            entries.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return entries


def write_my_entry():
    """将本机注册写入 registry/"""
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    entry = my_entry()
    filepath = REGISTRY_DIR / f"{get_host_display_name()}.json"
    filepath.write_text(
        json.dumps(entry, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return entry


def detect_conflicts(entries: list = None) -> list:
    """
    检测集群冲突。
    返回冲突列表，每条包含 type, severity, description。
    """
    if entries is None:
        entries = read_all_entries()
    
    conflicts = []
    my_host = get_host_display_name()
    
    # 检查是否注册了自己
    my_entry_found = any(e.get("hostname") == my_host for e in entries)
    if not my_entry_found:
        conflicts.append({
            "type": "unregistered",
            "severity": "warn",
            "description": f"本机 {my_host} 未在集群中注册。运行: agentos register"
        })
    
    # 检查双重 master
    masters = [e for e in entries if e.get("role") == "master"]
    active_masters = [
        m for m in masters
        if not is_stale(m.get("last_seen", ""))
    ]
    if len(active_masters) > 1:
        names = [m["hostname"] for m in active_masters]
        conflicts.append({
            "type": "dual_master",
            "severity": "error",
            "description": f"检测到 {len(active_masters)} 台机器都设为 master: {', '.join(names)}。"
                          f"同一时间只能有一台 master。请修改其中一台的 HOST_ID.md 角色。"
        })
    elif len(active_masters) == 0 and len(masters) > 0:
        # 所有 master 都离线了
        conflicts.append({
            "type": "no_active_master",
            "severity": "warn",
            "description": f"所有 master 都已离线（最后上线时间超过 24h）。"
                          f"如果你确信没有其他在线 master，可将本机提升为 master。"
        })
    
    # 检查 stale 条目
    for e in entries:
        if is_stale(e.get("last_seen", "")):
            conflicts.append({
                "type": "stale_entry",
                "severity": "info",
                "description": f"机器 {e['hostname']} 已超过 24h 未上线（角色: {e['role']}）。"
                              f"registry 文件: {REGISTRY_DIR / e['hostname']}.json"
            })
    
    return conflicts


def is_stale(last_seen_str: str) -> bool:
    """判断注册条目是否已过期（超过 24h）"""
    if not last_seen_str:
        return True
    try:
        last = datetime.fromisoformat(last_seen_str)
        age = datetime.now(timezone.utc) - last
        return age > timedelta(hours=24)
    except Exception:
        return True


def pre_task_check(allowed_roles: list = None) -> bool:
    """
    任务执行前调用。
    检查角色 + 集群冲突，有冲突则打印警告并返回 False。
    返回 True = 可以执行，False = 应跳过。
    """
    from role_check import read_host_id, check_role
    
    # 1. 基础角色检查
    local_info = read_host_id()
    my_role = local_info.get("role", "unknown")
    
    if allowed_roles and my_role not in allowed_roles:
        print(f"[cluster] ⛔ 本机角色={my_role}，需要角色={allowed_roles}，跳过")
        return False
    
    # 2. 如果我是 master，检查是否有其他 master
    entries = read_all_entries()
    conflicts = detect_conflicts(entries)
    
    error_conflicts = [c for c in conflicts if c["severity"] == "error"]
    warn_conflicts = [c for c in conflicts if c["severity"] == "warn"]
    
    if error_conflicts:
        for c in error_conflicts:
            print(f"[cluster] ❌ {c['description']}")
        print("[cluster] ⛔ 存在严重冲突，任务已中止。请手动解决冲突后重试。")
        return False
    
    if warn_conflicts:
        for c in warn_conflicts:
            print(f"[cluster] ⚠️ {c['description']}")
        # 警告不阻止执行
    
    return True


def cmd_register():
    """agentos register：注册本机到集群"""
    entry = write_my_entry()
    my_host = get_host_display_name()
    print(f"✅ 已注册: {my_host}")
    print(f"   角色: {entry['role']}")
    print(f"   时间: {entry['last_seen']}")
    
    # 注册后自动检测冲突
    conflicts = detect_conflicts()
    if conflicts:
        print()
        print("⚠️ 检测到以下问题：")
        for c in conflicts:
            icon = {"error": "❌", "warn": "⚠️", "info": "ℹ️"}.get(c["severity"], "?")
            print(f"   {icon} [{c['type']}] {c['description']}")
    
    print()
    print("💡 建议: git add -A && git commit -m \"[registry] update\" && git push")


def cmd_status():
    """agentos cluster-status：查看集群状态"""
    entries = read_all_entries()
    
    # 先注册自己
    my_entry = write_my_entry()
    my_host = get_host_display_name()
    
    print()
    print("=" * 60)
    print("  🌐 AgentOS 集群状态")
    print("=" * 60)
    print()
    
    if not entries:
        print("  (无其他注册机器)")
    else:
        print(f"  {'主机名':24s} {'角色':12s} {'状态':8s} {'上次上线':25s}")
        print(f"  {'-'*24} {'-'*12} {'-'*8} {'-'*25}")
        for e in entries:
            host = e.get("hostname", "?")
            role = e.get("role", "?")
            status = e.get("status", "?")
            last = e.get("last_seen", "?")
            is_me = "← 本机" if host == my_host else ""
            stale = " [离线]" if is_stale(last) else ""
            print(f"  {host:24s} {role:12s} {status:8s} {last[:19]:19s}{stale} {is_me}")
    
    print()
    
    # 冲突检测
    print("=" * 60)
    print("  冲突检测结果")
    print("=" * 60)
    print()
    conflicts = detect_conflicts(entries)
    if not conflicts:
        print("  ✅ 无冲突")
    else:
        for c in conflicts:
            icon = {"error": "❌", "warn": "⚠️", "info": "ℹ️"}.get(c["severity"], "?")
            print(f"  {icon} [{c['type']}] {c['description']}")
    
    print()
    print(f"  本机: {my_host} (角色: {my_entry['role']})")
    if my_entry['role'] == 'node':
        print("  📌 当前为最低权限角色。如需提升，编辑 HOST_ID.md")
    print()


def cmd_cleanup():
    """清理过期的注册条目（超过 7 天未上线）"""
    entries = read_all_entries()
    now = datetime.now(timezone.utc)
    removed = 0
    for e in entries:
        last_str = e.get("last_seen", "")
        if last_str:
            try:
                last = datetime.fromisoformat(last_str)
                if now - last > timedelta(days=7):
                    fp = REGISTRY_DIR / f"{e['hostname']}.json"
                    if fp.exists():
                        fp.unlink()
                        print(f"  🗑️ 移除离线机器: {e['hostname']}（最后上线: {last_str[:10]}）")
                        removed += 1
            except Exception:
                pass
    if removed == 0:
        print("  无过期条目需清理")
    print()
    print("💡 建议: git add -A && git commit -m \"[registry] cleanup\" && git push")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "register":
            cmd_register()
        elif cmd == "status":
            cmd_status()
        elif cmd == "cleanup":
            cmd_cleanup()
        else:
            print(f"未知命令: {cmd}")
            print("可用: register, status, cleanup")
    else:
        cmd_status()

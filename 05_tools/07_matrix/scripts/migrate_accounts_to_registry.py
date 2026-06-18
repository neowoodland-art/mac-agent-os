#!/usr/bin/env python3
"""
migrate_accounts_to_registry.py — 从本地 accounts.yaml 迁移到 registry + override
执行: python3 migrate_accounts_to_registry.py

作用:
  1. 读取本机 agent-local/tools/matrix/config/accounts.yaml
  2. 写入 agent-sync/05_tools/07_matrix/accounts_registry.yaml (含脱敏)
  3. 写入 agent-local/tools/matrix/config/accounts.override.yaml (含手机号/代理)
  4. 保留原 accounts.yaml 作为 old/backup
"""
import yaml, shutil, os
from pathlib import Path
from datetime import datetime

HOME = Path.home()
from matrix_mgmt import AGENT_SYNC, AGENT_LOCAL

HOSTNAME_FILE = AGENT_LOCAL / "identity" / "cached_hostname"
HOSTNAME = HOSTNAME_FILE.read_text().strip() if HOSTNAME_FILE.exists() else os.uname().nodename

SRC = AGENT_LOCAL / "tools" / "matrix" / "config" / "accounts.yaml"
REGISTRY = AGENT_SYNC / "05_tools" / "07_matrix" / "accounts_registry.yaml"
OVERRIDE = AGENT_LOCAL / "tools" / "matrix" / "config" / "accounts.override.yaml"
BACKUP = AGENT_LOCAL / "tools" / "matrix" / "config" / "accounts.yaml.old"

def mask_phone(phone: str) -> str:
    p = str(phone).strip()
    if len(p) == 11:
        return p[:3] + "****" + p[-4:]
    return p[:3] + "****" if len(p) > 3 else p

def migrate():
    if not SRC.exists():
        print(f"❌ 源文件不存在: {SRC}")
        return

    # 读取
    raw = yaml.safe_load(SRC.read_text()) or {}
    accounts = raw.get("accounts", [])
    print(f"📖 读取 {len(accounts)} 个账号配置")

    # 构建 registry & override
    registry_accounts = []
    override_accounts = []
    for acct in accounts:
        aid = acct.get("id", "")
        platform = acct.get("platform", "unknown")
        phone = str(acct.get("phone", ""))
        identity_dir = acct.get("identity_dir", "")
        identity_hint = identity_dir.split("/")[-1] if identity_dir else ""
        proxy = acct.get("proxy", "")
        enabled = acct.get("enabled", True)
        win = acct.get("window", [702, 783])
        pos = acct.get("window_position", [0, 0])
        notes = acct.get("notes", "")

        # Registry (脱敏)
        registry_accounts.append({
            "id": aid,
            "platform": platform,
            "phone_mask": mask_phone(phone),
            "assigned_machine": HOSTNAME,
            "identity_hint": identity_hint,
            "window": win,
            "window_position": pos,
            "notes": notes,
        })

        # Override (完整手机号+代理)
        o = {"id": aid, "phone": phone}
        if proxy:
            o["proxy"] = proxy
        o["enabled"] = enabled
        override_accounts.append(o)

    # 写 Registry
    reg_data = {
        "version": "1.0",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "accounts": registry_accounts,
    }
    REGISTRY.write_text(yaml.dump(reg_data, default_flow_style=False, allow_unicode=True, sort_keys=False))
    print(f"✅ Registry 写入: {REGISTRY} ({len(registry_accounts)} 账号)")

    # 写 Override
    ovr_data = {"version": "1.0", "hostname": HOSTNAME, "accounts": override_accounts}
    OVERRIDE.parent.mkdir(parents=True, exist_ok=True)
    OVERRIDE.write_text(yaml.dump(ovr_data, default_flow_style=False, allow_unicode=True, sort_keys=False))
    print(f"✅ Override 写入: {OVERRIDE} ({len(override_accounts)} 账号)")

    # 备份原文件
    shutil.copy2(SRC, BACKUP)
    print(f"✅ 原文件备份: {BACKUP}")

    print("\n🎉 迁移完成!")
    print(f"   请编辑 {REGISTRY} 调整 assigned_machine (如有多机)")
    print(f"   请编辑 {OVERRIDE} 确认手机号和代理")
    print("   git add accounts_registry.yaml && git commit && git push")

if __name__ == "__main__":
    migrate()

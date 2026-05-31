#!/usr/bin/env python3
"""修复注册表: 从插件数据读取真实 hostname, 清理错误条目"""
import json
from pathlib import Path

CROSS = Path("/Users/chengzige/workbuddy-agent-os/agent-sync/04_memory/cross_machine")
live_dir = CROSS / "status" / "live"

# 3 台正确机器
machines = {
    "4cf443bc-ff14-4ed9-885b-b04c5326304d": {
        "_hostname": "chengzigedeAir",
        "_received_at": "2026-05-19T05:16:39+00:00",
        "os": "macOS 26.4",
        "cpu": {"load_1m": 0},
        "disk": {"total_gb": 245, "used_gb": 225},
        "guardd_version": "2.0.0",
    },
    "d19759cf-2159-4fe7-b6ff-db14ccf379f5": {
        "_hostname": "7kecheng",
        "_received_at": "2026-05-19T05:01:36+00:00",
        "os": "macOS",
        "cpu": {"load_1m": 0},
        "disk": {"total_gb": 228, "used_gb": 12},
        "guardd_version": "1.0.0",
    },
    "f13b03d1-731f-453f-accb-8b8edbd6413a": {
        "_hostname": "5kechengdeAir",
        "_received_at": "2026-05-19T05:57:58+00:00",
        "os": "macOS",
        "cpu": {"load_1m": 0},
        "disk": {"total_gb": 0, "used_gb": 0},
        "guardd_version": "1.0.0",
    },
}

# 清理 live 目录
for f in list(live_dir.iterdir()):
    if f.suffix != ".json" or f.name.startswith("_"):
        continue
    uid = f.name.replace(".json", "")
    if uid not in machines:
        f.unlink()
        print(f"  删除错误条目: {f.name}")

# 写入正确数据
for uid, data in machines.items():
    path = live_dir / f"{uid}.json"
    path.write_text(json.dumps({"_uid": uid, **data}, indent=2, ensure_ascii=False))
    print(f"  写入: {data['_hostname']} ({uid[:12]}...)")

# 重建注册表
reg = {}
for uid, data in machines.items():
    reg[uid] = {"hostname": data["_hostname"], "uid": uid, "status": "registered"}
(live_dir / "_registry.json").write_text(json.dumps(reg, indent=2, ensure_ascii=False))

print(f"\n完成! 共 {len(machines)} 台机器:")
for uid, data in machines.items():
    print(f"  {data['_hostname']} ({uid[:12]}...)")

#!/usr/bin/env python3
"""重建 status/live/ 注册表, 从 registry/ + data/ 补齐所有机器"""
import json
from pathlib import Path

CROSS = Path("/Users/chengzige/workbuddy-agent-os/agent-sync/04_memory/cross_machine")
live_dir = CROSS / "status" / "live"
live_dir.mkdir(parents=True, exist_ok=True)

# Redmi-12C from cross_machine/data/ (UID: d19759cf-...)
rmc = {
    "_uid": "d19759cf-2159-4fe7-b6ff-db14ccf379f5",
    "_hostname": "Redmi-12C",
    "_received_at": "2026-05-19T01:45:07+00:00",
    "os": "macOS 26.4",
    "cpu": {"load_1m": 0},
    "disk": {"total_gb": 228, "used_gb": 12, "available_gb": 161},
    "guardd_version": "1.0.0",
}
(live_dir / "d19759cf-2159-4fe7-b6ff-db14ccf379f5.json").write_text(json.dumps(rmc, indent=2, ensure_ascii=False))

# 5kecheng from registry/5kecheng.json
(live_dir / "5kecheng.json").write_text(json.dumps({
    "_uid": "5kecheng", "_hostname": "5kecheng",
    "_received_at": "2026-05-16T08:34:43+00:00", "os": "macOS",
    "cpu": {"load_1m": 0}, "disk": {"total_gb": 0, "used_gb": 0},
}, indent=2, ensure_ascii=False))

# 7kecheng from registry/7kecheng.json
(live_dir / "7kecheng.json").write_text(json.dumps({
    "_uid": "7kecheng", "_hostname": "7kechengdeAir",
    "_received_at": "2026-05-03T10:35:38+00:00", "os": "macOS",
    "cpu": {"load_1m": 0}, "disk": {"total_gb": 0, "used_gb": 0},
}, indent=2, ensure_ascii=False))

# Rebuild _registry.json
reg = {}
for f in sorted(live_dir.iterdir()):
    if f.suffix != ".json" or f.name.startswith("_"):
        continue
    d = json.loads(f.read_text())
    uid = f.name.replace(".json", "")
    reg[uid] = {"hostname": d.get("_hostname", uid), "uid": uid,
                "last_seen": d.get("_received_at", ""), "status": "registered"}

(live_dir / "_registry.json").write_text(json.dumps(reg, indent=2, ensure_ascii=False))
print(f"重建完成: {len(reg)} 台机器")
for uid in sorted(reg):
    print(f"  {uid[:12]}... → {reg[uid]['hostname']}")

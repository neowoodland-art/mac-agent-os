#!/usr/bin/env python3
"""Clean up duplicates in registry and live/"""
import json
from pathlib import Path
import re

CROSS = Path("/Users/chengzige/workbuddy-agent-os/agent-sync/04_memory/cross_machine")
live_dir = CROSS / "status" / "live"
reg_dir = CROSS / "registry"

# Clean live directory: remove IP-based entries and duplicates
for f in list(live_dir.iterdir()):
    if f.suffix != ".json" or f.name.startswith("_"):
        continue
    if re.match(r'^\d+\.\d+\.\d+\.\d+', f.name):
        f.unlink()
        print(f"  removed: {f.name} (IP-based)")

# We want: 4cf443bc-... (chengzigedeAir), d19759cf-... (Redmi-12C), 5kecheng, 7kechengdeAir
want_uids = {"4cf443bc-ff14-4ed9-885b-b04c5326304d", "d19759cf-2159-4fe7-b6ff-db14ccf379f5", "5kecheng", "7kechengdeAir"}
for f in list(live_dir.iterdir()):
    if f.suffix != ".json" or f.name.startswith("_"):
        continue
    uid = f.name.replace(".json", "")
    if uid not in want_uids:
        f.unlink()
        print(f"  removed: {f.name} (duplicate)")

# Clean registry: remove IP-based entries
for f in list(reg_dir.iterdir()):
    if f.suffix != ".json":
        continue
    try:
        d = json.loads(f.read_text())
        hn = d.get("hostname", "")
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', hn):
            f.unlink()
            print(f"  removed registry/{f.name} (IP hostname)")
    except:
        pass

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
print(f"\n重建后 {len(reg)} 台机器:")
for uid in sorted(reg):
    print(f"  {uid[:12]}... → {reg[uid]['hostname']}")

#!/usr/bin/env python3
"""Fix the 7kecheng live entry"""
import json
from pathlib import Path

d = {
    "_uid": "7kecheng",
    "_hostname": "7kechengdeAir",
    "_received_at": "2026-05-03T10:35:38+00:00",
    "os": "macOS",
    "cpu": {"load_1m": 0},
    "disk": {"total_gb": 0, "used_gb": 0},
}
live_dir = Path("/Users/chengzige/workbuddy-agent-os/agent-sync/04_memory/cross_machine/status/live")
(live_dir / "7kechengdeAir.json").write_text(json.dumps(d, indent=2))
print("done")

"""
plugins/guardd.py — 联邦状态监控插件 (v3)
单一数据源: status/live/ + 补充 registry/ + data/
版本: 3.0.0 | 更新: 2026-05-19
"""
import json, os
from datetime import datetime, timezone
from pathlib import Path

from plugins.base import DashboardPlugin, CROSS_MACHINE, MACHINE_UID, HOSTNAME
from plugins._registry import get_machine_list


class GuarddPlugin(DashboardPlugin):
    name = "guardd"
    label = "联邦机器"
    icon = "🖥"
    version = "3.0.0"
    description = "跨机器联邦状态监控：心跳/注册/插件数据三源合一"
    order = 10

    def _read_live_data(self):
        """主数据源: status/live/{uid}.json"""
        live_dir = CROSS_MACHINE / "status" / "live"
        data = {}
        if not live_dir.exists():
            return data
        for f in live_dir.iterdir():
            if f.suffix != ".json" or f.name.startswith("_"):
                continue
            try:
                uid = f.name.replace(".json", "")
                data[uid] = json.loads(f.read_text())
            except:
                pass
        return data

    def _read_registry(self):
        """补充数据源1: cross_machine/registry/{name}.json"""
        reg_dir = CROSS_MACHINE / "registry"
        machines = []
        if reg_dir.exists():
            for f in sorted(reg_dir.iterdir()):
                if f.suffix == ".json":
                    try:
                        d = json.loads(f.read_text())
                        machines.append({
                            "hostname": d.get("hostname", f.stem),
                            "uid": d.get("uid", ""),
                            "role": d.get("role", ""),
                            "source": "registry",
                        })
                    except:
                        pass
        return machines

    def _read_plugin_data(self):
        """补充数据源2: cross_machine/data/*/{uid}.json 扫描所有机器UID"""
        data_dir = CROSS_MACHINE / "data"
        machines = {}
        if data_dir.exists():
            for plugin_dir in data_dir.iterdir():
                if not plugin_dir.is_dir():
                    continue
                for f in plugin_dir.iterdir():
                    if f.suffix == ".json":
                        try:
                            d = json.loads(f.read_text())
                            uid = d.get("machine_uid", "")
                            hn = d.get("hostname", "")
                            if uid and hn:
                                if uid not in machines:
                                    machines[uid] = {"hostname": hn, "uid": uid, "source": "plugin_data"}
                        except:
                            pass
        return list(machines.values())

    def summary(self, machines: list[str]) -> dict:
        live = self._read_live_data()
        now = datetime.now(timezone.utc)

        all_uids = set(live.keys())
        by_machine = {}

        for uid, l in live.items():
            hn = l.get("_hostname", uid[:8])
            received = l.get("_received_at", "")
            online = False
            realtime = False
            if received:
                try:
                    delta = (now - datetime.fromisoformat(received)).total_seconds()
                    online = delta < 300
                    realtime = delta < 120
                except:
                    pass
            by_machine[hn] = {
                "在线": online,
                "实时推送": realtime,
                "guardd版本": l.get("guardd_version", ""),
            }

        return {
            "总机器": len(by_machine),
            "在线": sum(1 for m in by_machine.values() if m["在线"]),
            "实时": sum(1 for m in by_machine.values() if m["实时推送"]),
            "各机器": by_machine,
        }

    def detail(self, machine: str = "") -> dict:
        live = self._read_live_data()
        now = datetime.now(timezone.utc)

        if machine:
            for uid, l in live.items():
                if l.get("_hostname") == machine:
                    return self._build_machine_detail(machine, uid, l, now)
            return {"_note": "未找到该机器数据"}

        result = {}
        seen = set()
        for uid, l in sorted(live.items(), key=lambda x: x[1].get("_hostname", "")):
            hn = l.get("_hostname", uid[:8])
            if hn in seen:
                continue
            seen.add(hn)
            result[hn] = self._build_machine_detail(hn, uid, l, now)
        return result

    def _build_machine_detail(self, hostname, uid, live, now):
        received = live.get("_received_at", "")
        delta = 999
        entry = {
            "hostname": hostname,
            "_uid": uid[:8]+"..." if uid else "",
            "status": "offline",
            "last_seen": received,
            "os": live.get("os", ""),
            "cpu_load": 0,
            "disk_used_gb": 0,
            "disk_total_gb": 0,
            "disk_avail_gb": 0,
            "guardd_version": live.get("guardd_version", ""),
            "current_task": live.get("current_task", ""),
            "minutes_ago": 999,
            "_live": False,
            "_last_push_sec": 0,
        }
        if received:
            try:
                delta = (now - datetime.fromisoformat(received)).total_seconds()
                entry["_live"] = delta < 120
                entry["_last_push_sec"] = round(delta)
                entry["minutes_ago"] = round(delta / 60)
                entry["status"] = "online" if delta < 300 else ("recent" if delta < 3600 else "offline")
            except:
                pass
        cpu = live.get("cpu", {})
        entry["cpu_load"] = cpu.get("load_1m", 0)
        disk = live.get("disk", {})
        entry["disk_used_gb"] = disk.get("used_gb", 0)
        entry["disk_total_gb"] = disk.get("total_gb", 0)
        entry["disk_avail_gb"] = disk.get("available_gb", 0)
        entry["guardd_version"] = live.get("guardd_version", "")
        return entry

    def actions(self) -> list[dict]:
        machines = get_machine_list()
        return [
            {"name": f"唤醒 {hn}", "method": "POST", "endpoint": f"/api/wakeup/{hn}"}
            for hn in machines
        ]

    def get_productions(self, limit=50, offset=0, strategy=None, status=None):
        result = self.detail()
        return list(result.values())

    def get_summary(self) -> dict:
        return self.summary(get_machine_list())

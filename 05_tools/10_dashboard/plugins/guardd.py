"""
plugins/guardd.py — 联邦状态监控插件 (v2)
读取 cross_machine/status/ 下的心跳数据 + 推送数据
版本: 2.0.0 | 更新: 2026-05-18
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
    version = "2.0.0"
    description = "跨机器联邦状态监控：心跳 / 事件 / 任务"
    order = 10

    def _read_live_data(self):
        """读取所有机器的实时推送数据"""
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

    def _read_git_heartbeats(self):
        """读取 Git 持久层心跳"""
        import json
        status_dir = CROSS_MACHINE / "status"
        machines = {}
        for d in status_dir.iterdir():
            if not d.is_dir() or d.name == "live":
                continue
            hb = d / "heartbeat.json"
            if hb.exists():
                try:
                    data = json.loads(hb.read_text())
                    hostname = data.get("hostname", d.name)
                    machines[hostname] = data
                except:
                    pass
        return machines

    def summary(self, machines: list[str]) -> dict:
        live = self._read_live_data()
        git = self._read_git_heartbeats()
        now = datetime.now(timezone.utc)

        all_hostnames = list(git.keys())
        for uid, l in live.items():
            hn = l.get("_hostname", "")
            if hn and hn not in all_hostnames:
                all_hostnames.append(hn)

        machine_names = all_hostnames if all_hostnames else [HOSTNAME]
        by_machine = {}
        for hn in machine_names:
            online = False
            realtime = False
            matched = False
            for uid, l in live.items():
                if l.get("_hostname") == hn:
                    received = l.get("_received_at", "")
                    if received:
                        try:
                            delta = (now - datetime.fromisoformat(received)).total_seconds()
                            online = delta < 300
                            realtime = delta < 120
                        except:
                            pass
                    matched = True
                    break
            if not matched and hn in git:
                last_seen = git[hn].get("last_seen", "")
                if last_seen:
                    try:
                        delta = (now - datetime.fromisoformat(last_seen)).total_seconds()
                        online = delta < 900
                    except:
                        pass
            by_machine[hn] = {
                "在线": online,
                "实时推送": realtime,
                "guardd版本": git.get(hn, {}).get("guardd_version", ""),
            }

        return {
            "总机器": len(machine_names),
            "在线": sum(1 for m in by_machine.values() if m["在线"]),
            "实时": sum(1 for m in by_machine.values() if m["实时推送"]),
            "各机器": by_machine,
        }

    def detail(self, machine: str = "") -> dict:
        live = self._read_live_data()
        git = self._read_git_heartbeats()
        now = datetime.now(timezone.utc)

        if machine:
            # 返回指定机器
            for uid, l in live.items():
                if l.get("_hostname") == machine:
                    return self._build_machine_detail(machine, uid, l, git.get(machine, {}), now)
            if machine in git:
                return self._build_machine_detail(machine, "", {}, git[machine], now)
            return {"_note": "未找到该机器数据"}

        # 返回所有机器
        result = {}
        seen = set()
        for uid, l in sorted(live.items(), key=lambda x: x[1].get("_hostname", "")):
            hn = l.get("_hostname", "")
            if hn in seen:
                continue
            seen.add(hn)
            result[hn] = self._build_machine_detail(hn, uid, l, git.get(hn, {}), now)
        for hn, hb in sorted(git.items()):
            if hn not in seen:
                result[hn] = self._build_machine_detail(hn, "", {}, hb, now)
        return result

    def _build_machine_detail(self, hostname, uid, live, git_hb, now):
        entry = {
            "hostname": hostname,
            "_uid": uid[:8]+"..." if uid else "",
            "status": "offline",
            "last_seen": "",
            "os": "",
            "cpu_load": 0,
            "disk_used_gb": 0,
            "disk_total_gb": 0,
            "disk_avail_gb": 0,
            "guardd_version": git_hb.get("guardd_version", ""),
            "current_task": git_hb.get("current_task"),
            "minutes_ago": 999,
            "_live": False,
            "_last_push_sec": 0,
            "minutes_ago": 999,
        }
        if live:
            received = live.get("_received_at", "")
            if received:
                try:
                    delta = (now - datetime.fromisoformat(received)).total_seconds()
                    entry["_live"] = delta < 120
                    entry["_last_push_sec"] = round(delta)
                    entry["minutes_ago"] = round(delta / 60)
                    entry["status"] = "online" if delta < 300 else ("recent" if delta < 3600 else "offline")
                    entry["last_seen"] = received
                except:
                    pass
            cpu = live.get("cpu", {})
            entry["cpu_load"] = cpu.get("load_1m", 0)
            disk = live.get("disk", {})
            entry["disk_used_gb"] = disk.get("used_gb", 0)
            entry["disk_total_gb"] = disk.get("total_gb", 0)
            entry["disk_avail_gb"] = disk.get("available_gb", 0)
            entry["os"] = live.get("os", "")
            entry["guardd_version"] = live.get("guardd_version", "")
        elif git_hb:
            entry["last_seen"] = git_hb.get("last_seen", "")
            entry["cpu_load"] = git_hb.get("cpu_load", 0)
            entry["disk_used_gb"] = git_hb.get("disk_used_gb", 0)
            entry["disk_total_gb"] = git_hb.get("disk_total_gb", 0)
            entry["disk_avail_gb"] = git_hb.get("disk_avail_gb", 0)
            entry["os"] = git_hb.get("os", "")
            if git_hb.get("last_seen"):
                try:
                    delta = (now - datetime.fromisoformat(git_hb["last_seen"])).total_seconds()
                    entry["minutes_ago"] = round(delta / 60)
                    entry["status"] = "online" if delta < 900 else "offline"
                except:
                    pass
        return entry

    def actions(self) -> list[dict]:
        machines = get_machine_list()
        return [
            {"name": f"唤醒 {hn}", "method": "POST", "endpoint": f"/api/wakeup/{hn}"}
            for hn in machines
        ]

    # ── 兼容旧版 ────────────────────────────────────────────
    def get_productions(self, limit=50, offset=0, strategy=None, status=None):
        """旧版兼容 — 返回机器列表"""
        result = self.detail()
        return list(result.values())

    def get_summary(self) -> dict:
        return self.summary(get_machine_list())

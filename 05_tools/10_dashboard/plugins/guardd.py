"""
plugins/guardd.py — 联邦状态监控插件 (v3.1)
WPRA v2.0: 优先 machines/*/heartbeat.json, 降级 status/live/
版本: 3.1.0 | 更新: 2026-05-31
"""
import json, os
from datetime import datetime, timezone
from pathlib import Path

from plugins.base import DashboardPlugin, CROSS_MACHINE, MACHINE_UID, HOSTNAME, AGENT_LOCAL
from plugins._registry import get_machine_list

# ── WPRA v2.0 路径 ────────────────────────────────
MACHINES_DIR = CROSS_MACHINE / "machines"

# ── 人工维护的 IP→hostname 映射（旧版兼容）───────────
_MACHINE_ALIASES: dict[str, str] = {
    "192.168.31.95":               "7kecheng",
    "7kechengdeAir":               "7kecheng",
    "7kechengdeMacBook-Air.local": "7kecheng",
    "Redmi-12C":                   "7kecheng",
    "192.168.31.96":               "chengzigedeAir",
}


class GuarddPlugin(DashboardPlugin):
    name = "guardd"
    label = "联邦机器"
    icon = "🖥"
    version = "3.1.0"
    description = "跨机器联邦状态监控：WPRA v2.0 心跳聚合"
    order = 10

    # ═══════════════════════════════════════════════════════
    # WPRA v2.0: machines/*/heartbeat.json (主数据源)
    # ═══════════════════════════════════════════════════════

    def _read_wpra_heartbeats(self):
        """主数据源: machines/*/heartbeat.json

        WPRA v2.0: 每台机器只写自己的 machines/{uid}/heartbeat.json
        统一字段名映射到旧格式，保持 _build_machine_detail 兼容。
        """
        data = {}
        if not MACHINES_DIR.exists():
            return data
        for md in sorted(MACHINES_DIR.iterdir()):
            if not md.is_dir():
                continue
            uid = md.name
            hb_file = md / "heartbeat.json"
            if not hb_file.exists():
                continue
            try:
                hb = json.loads(hb_file.read_text())

                # 统一字段名映射 (新→旧格式兼容)
                machine_name = hb.get("machine_name", uid[:8])
                updated_at = hb.get("updated_at", "")
                mapped = {
                    "_hostname": machine_name,
                    "_uid": uid,
                    "hostname": machine_name,
                    "_received_at": updated_at,
                    "status": hb.get("status", "offline"),
                    "guardd_version": hb.get("guardd_version", ""),
                    "current_task": hb.get("current_task", None),
                    # 从 WPRA 扁平字段转为旧版嵌套格式
                    "cpu": {"load_1m": hb.get("cpu_load", 0)},
                    "disk": {
                        "available_gb": hb.get("disk_avail_gb", 0),
                        "total_gb": hb.get("disk_total_gb", 0),
                        "used_gb": hb.get("disk_used_gb", 0),
                    },
                    "memory": {"percent": hb.get("memory_pct", 0)},
                    "os": "",
                    "_live": bool(updated_at),
                    "_last_push_sec": 0,
                    "_source": "wpra_heartbeat",
                }

                # 计算 _last_push_sec
                if updated_at:
                    try:
                        delta = (datetime.now(timezone.utc) -
                                 datetime.fromisoformat(updated_at.replace("Z", "+00:00"))).total_seconds()
                        mapped["_last_push_sec"] = round(delta)
                        mapped["_live"] = delta < 120
                    except:
                        pass

                data[uid] = mapped
            except Exception:
                continue
        return data

    # ═══════════════════════════════════════════════════════
    # 旧版: status/live/{uid}.json (降级)
    # ═══════════════════════════════════════════════════════

    def _read_live_data(self):
        """WPRA v2.0: 优先 machines/*/, 降级 status/live/"""
        # WPRA 优先
        wpra = self._read_wpra_heartbeats()
        if wpra:
            return wpra

        # 降级: 旧 status/live/{uid}.json
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
        """补充数据源: cross_machine/registry/{name}.json"""
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
        """补充数据源: 本机 guardd 状态 (local) + 旧 cross_machine/data/ (兼容)"""
        # 新: 本机 local 目录
        local_guardd = AGENT_LOCAL / "runtime" / "guardd" / "data"
        machines = {}
        if local_guardd.exists():
            for plugin_dir in local_guardd.iterdir():
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
                                    machines[uid] = {"hostname": hn, "uid": uid, "source": "local_guardd"}
                        except: pass
        # 旧: cross_machine/data/ (兼容旧数据)
        data_dir = CROSS_MACHINE / "data"
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
                            if uid and hn and uid not in machines:
                                machines[uid] = {"hostname": hn, "uid": uid, "source": "legacy_cross_machine"}
                        except: pass
        return list(machines.values())

    # ═══════════════════════════════════════════════════════
    # 概览 / 详情
    # ═══════════════════════════════════════════════════════

    def summary(self, machines: list[str]) -> dict:
        live = self._read_live_data()
        now = datetime.now(timezone.utc)

        by_machine = {}
        for uid, l in live.items():
            hn = l.get("_hostname", uid[:8])
            received = l.get("_received_at", "")
            online = False
            realtime = False
            if received:
                try:
                    delta = (now - datetime.fromisoformat(
                        received.replace("Z", "+00:00"))).total_seconds()
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
                delta = (now - datetime.fromisoformat(
                    received.replace("Z", "+00:00"))).total_seconds()
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

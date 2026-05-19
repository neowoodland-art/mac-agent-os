"""
plugins/guardd.py — 联邦状态监控插件 (v2.1)
读取 cross_machine/status/ 下的心跳数据 + 推送数据
版本: 2.1.0 | 更新: 2026-05-19
"""
import json, os, re
from datetime import datetime, timezone
from pathlib import Path

from plugins.base import DashboardPlugin, CROSS_MACHINE, MACHINE_UID, HOSTNAME
from plugins._registry import get_machine_list

# ── 人工维护的 IP→hostname 映射 ───────────────────────────
# 旧版 guardd(v1.0/v1.1) 未写 UID，心跳被存为 IP/hostname/hostname.local 多种命名。
# 这些映射将 IP 或 .local 变体归并到规范 hostname。
# 如果新增机器发现重复，在此追加。
_MACHINE_ALIASES: dict[str, str] = {
    "192.168.31.95":               "7kechengdeAir",
    "7kechengdeMacBook-Air.local": "7kechengdeAir",
    "192.168.31.96":               "chengzigedeAir",
}


class GuarddPlugin(DashboardPlugin):
    name = "guardd"
    label = "联邦机器"
    icon = "🖥"
    version = "2.1.0"
    description = "跨机器联邦状态监控：心跳 / 事件 / 任务"
    order = 10

    def _build_hostname_aliases(self) -> dict[str, str]:
        """构建 hostname 别名映射表

        将同一台机器的不同标识形式（IP、hostname、hostname.local）
        统一归并到规范 hostname。

        来源（按优先级）:
        1. _MACHINE_ALIASES — 人工维护的 IP→hostname 映射
        2. registry — hostname ↔ system_hostname 映射
        3. .local 后缀自动剥离
        """
        alias_map: dict[str, str] = {}

        # 1. 人工映射（最高优先级）
        alias_map.update(_MACHINE_ALIASES)

        # 2. 自动检测 .local 后缀并映射到基础名
        #    （registry 中的 hostname/system_hostname 映射不可靠，
        #     因为 hostname 可能被填成用户名而非真实机器名）
        status_dir = CROSS_MACHINE / "status"
        if status_dir.exists():
            dir_names = [
                d.name for d in status_dir.iterdir()
                if d.is_dir() and d.name != "live"
            ]
            for name in dir_names:
                if name.endswith(".local"):
                    base = name[:-6]  # strip .local
                    if base in dir_names:
                        alias_map.setdefault(name, base)

        return alias_map

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
        """读取 Git 持久层心跳 (v2.1 — 别名合并去重)"""
        import json
        alias_map = self._build_hostname_aliases()
        status_dir = CROSS_MACHINE / "status"
        machines: dict[str, dict] = {}
        for d in status_dir.iterdir():
            if not d.is_dir() or d.name == "live":
                continue
            hb = d / "heartbeat.json"
            if not hb.exists():
                continue
            try:
                data = json.loads(hb.read_text())
                dir_name = d.name
                # 通过别名映射解析规范 hostname
                canonical = alias_map.get(dir_name, dir_name)
                # 规范名已存在时略过（取第一个写入的）
                if canonical not in machines:
                    data["_canonical_hostname"] = canonical
                    data["_resolved_from"] = dir_name
                    machines[canonical] = data
                else:
                    # 标记为被合并，可用于日志/调试
                    existing = machines[canonical]
                    existing.setdefault("_merged_aliases", []).append(dir_name)
            except Exception:
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
            # git 心跳数据在嵌套结构中：disk.used_gb, cpu.load_1m
            _disk = git_hb.get("disk", {})
            entry["disk_used_gb"] = _disk.get("used_gb", 0)
            entry["disk_total_gb"] = _disk.get("total_gb", 0)
            entry["disk_avail_gb"] = _disk.get("available_gb", 0)
            _cpu = git_hb.get("cpu", {})
            entry["cpu_load"] = _cpu.get("load_1m", 0)
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

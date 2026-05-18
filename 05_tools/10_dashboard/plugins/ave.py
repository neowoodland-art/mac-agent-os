"""
plugins/ave.py — AVE 视频工厂插件 (v2)
显示生产管线状态、生产记录、费用统计
版本: 2.0.0 | 更新: 2026-05-18
"""
import json, os
from pathlib import Path
from datetime import datetime, timezone

from plugins.base import DashboardPlugin, AGENT_SYNC, AGENT_LOCAL, CROSS_MACHINE, HOSTNAME, MACHINE_UID
from plugins._registry import get_machine_list, get_plugin_data


class AVEDashboardPlugin(DashboardPlugin):
    name = "ave"
    label = "视频工厂"
    icon = "🎬"
    version = "2.0.0"
    description = "AVE 视频工厂：管线状态 / 生产记录 / 费用"
    order = 20

    def _read_local_productions(self):
        """读取本机 AVE 生产记录"""
        log_dirs = [
            AGENT_LOCAL / "runtime" / "ave" / "productions",
            AGENT_LOCAL / "logs" / "ave",
        ]
        records = []
        for d in log_dirs:
            if d.exists():
                for f in sorted(d.iterdir())[-50:]:
                    if f.suffix in (".json", ".log"):
                        try:
                            records.append({"file": f.name, "size": f.stat().st_size, "mtime": f.stat().st_mtime})
                        except:
                            pass
        return records

    def _read_production_logs(self):
        """读取 AVE 生产日志获取管线统计"""
        log_path = AGENT_LOCAL / "runtime" / "ave" / "production.json"
        if log_path.exists():
            try:
                return json.loads(log_path.read_text())
            except:
                pass
        return {"productions": [], "total_cost": 0}

    def summary(self, machines: list[str]) -> dict:
        # 本机数据
        local = self._read_production_logs() or {}
        prods = local.get("productions", [])
        strategies = {}
        for p in prods:
            s = p.get("strategy", "未知")
            strategies[s] = strategies.get(s, 0) + 1

        by_machine = {HOSTNAME: {
            "管线数": 6,
            "总生产": len(prods),
            "今日": sum(1 for p in prods if p.get("created_at","").startswith(datetime.now().strftime("%Y-%m-%d"))),
            "策略分布": strategies,
            "费用": local.get("total_cost", 0),
        }}

        # 读取其他机器的共享数据
        for d in get_plugin_data(self.name):
            hn = d.get("hostname", "")
            if hn and hn != HOSTNAME:
                data = d.get("data", {})
                m = data.get("各机器", {}).get(hn, {})
                if m:
                    by_machine[hn] = m

        return {
            "总管线": 6,
            "各机器": by_machine,
        }

    def detail(self, machine: str = "") -> dict:
        result = {}
        # 本机详情
        logs = self._read_production_logs()
        prods = logs.get("productions", [])[-20:]  # 最近20条
        result[HOSTNAME] = {
            "管线": [
                {"name": "口播", "status": "ready", "desc": "文案→TTS→素材→字幕"},
                {"name": "卡点", "status": "ready", "desc": "BGM→节拍→素材→xfade"},
                {"name": "数字人", "status": "ready", "desc": "OmniHuman/DreamActor"},
                {"name": "口播+卡点", "status": "ready", "desc": "人声锚点+变速拼接"},
                {"name": "故事", "status": "ready", "desc": "剧本→Kling批量→角色一致"},
                {"name": "变速卡点", "status": "ready", "desc": "速度曲线+拍点对齐"},
            ],
            "最近生产": prods[-10:] if prods else [],
            "总费用": logs.get("total_cost", 0),
        }
        return result

    def actions(self) -> list[dict]:
        return [
            {"name": "刷新缓存", "method": "POST", "endpoint": "/api/plugins/ave/refresh"},
        ]

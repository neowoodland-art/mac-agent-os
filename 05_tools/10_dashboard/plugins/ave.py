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

        # 检测 API 配置状态
        config = AGENT_LOCAL / "tools" / "ave" / "config" / "local.yaml"
        api_configured = config.exists()
        api_services = []
        if api_configured:
            try:
                import yaml
                cfg = yaml.safe_load(config.read_text()) or {}
                for svc in ["volcano","aliyun","pexels","llm"]:
                    if svc in cfg and cfg[svc].get("api_key","") not in ("", "sk-xxx"):
                        api_services.append(svc)
            except:
                pass

        by_machine = {HOSTNAME: {
            "管线数": 6,
            "总生产": len(prods),
            "今日": sum(1 for p in prods if p.get("created_at","").startswith(datetime.now().strftime("%Y-%m-%d"))),
            "API已配置": api_configured,
            "API服务": api_services,
            "策略分布": strategies if strategies else {"未生产": 0},
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
        """返回生产记录格式 (兼容前端)"""
        result = {}
        logs = self._read_production_logs()
        prods = logs.get("productions", [])[-20:]

        # 如果没有真实生产记录, 返回空列表而不是管线结构
        records = []
        for p in prods:
            records.append({
                "id": p.get("id", 0),
                "strategy": p.get("strategy", ""),
                "script_name": p.get("script_name", ""),
                "status": p.get("status", "unknown"),
                "total_cost": p.get("total_cost", 0),
                "duration_sec": p.get("duration_sec", 0),
                "created_at": p.get("created_at", ""),
            })

        result[HOSTNAME] = {
            "productions": records,
            "total_cost": logs.get("total_cost", 0),
            "today": sum(1 for p in prods if p.get("created_at","").startswith(datetime.now().strftime("%Y-%m-%d"))),
        }
        return result

    def actions(self) -> list[dict]:
        return [
            {"name": "刷新缓存", "method": "POST", "endpoint": "/api/plugins/ave/refresh"},
        ]

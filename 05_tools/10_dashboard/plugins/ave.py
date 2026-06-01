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

    def get_sub_views(self) -> list[dict]:
        return [
            {"key": "characters", "label": "角色管理", "icon": "🧑", "group": "ave"},
            {"key": "capabilities", "label": "原子能力", "icon": "⚡", "group": "ave"},
        ]

    def get_characters(self) -> dict:
        """列出所有已注册角色"""
        try:
            from character_registry import CharacterRegistry
            registry = CharacterRegistry()
            chars = {}
            for name in registry.list_characters():
                char = registry.get_character(name)
                chars[name] = char.to_dict()
            return {
                "characters": chars,
                "active": registry.get_active_name(),
                "total": len(chars),
            }
        except Exception as e:
            return {"characters": {}, "active": "", "total": 0, "error": str(e)}

    def get_capabilities(self) -> dict:
        """解析 AVE_ARCHITECTURE_PLAN.md 中的原子能力"""
        _SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "09_ave" / "scripts"
        plan_path = _SCRIPTS_DIR / "AVE_ARCHITECTURE_PLAN.md"
        if not plan_path.exists():
            return {"groups": [], "error": "架构文档不存在"}

        try:
            content = plan_path.read_text(encoding="utf-8")
            return self._parse_capabilities(content)
        except Exception as e:
            return {"groups": [], "error": str(e)}

    def _parse_capabilities(self, content: str) -> dict:
        """从 markdown 中提取原子能力表格"""
        groups = []
        current_group = None
        current_items = []
        headers = []

        # 定义要提取的 section 范围
        sections = {
            "音频原子能力": "音频原子能力|3.1 音频",
            "视觉原子能力": "视觉原子能力|3.2 视觉",
            "动作迁移原子能力": "动作迁移原子能力|3.3 动作",
            "角色原子能力": "角色原子能力|3.4 角色",
            "通用基础能力": "通用基础能力|3.5 通用",
        }
        current_section_tag = None

        for line in content.split("\n"):
            # 检测 section 标题
            for tag, patterns in sections.items():
                for p in patterns.split("|"):
                    if p in line:
                        if current_group and current_items:
                            groups.append({"name": current_group, "items": current_items})
                        current_group = tag
                        current_items = []
                        headers = []
                        current_section_tag = tag
                        break
            if current_section_tag is None:
                continue

            # 检测表格行
            if line.startswith("|") and line.endswith("|"):
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if not cells or len(cells) < 2:
                    continue
                # 跳过表头分隔行
                if all(c.strip().replace("-", "").replace(":", "") == "" for c in cells):
                    continue
                # 第一行是表头
                if not headers:
                    headers = cells
                    continue
                current_items.append(dict(zip(headers, cells + [""] * (len(headers) - len(cells)))))

        if current_group and current_items:
            groups.append({"name": current_group, "items": current_items})

        # 提取交叉能力矩阵
        matrix = self._parse_matrix(content)

        return {"groups": groups, "matrix": matrix, "total_items": sum(len(g["items"]) for g in groups)}

    def _parse_matrix(self, content: str) -> list:
        """提取交叉能力矩阵表格"""
        in_matrix = False
        headers = []
        rows = []
        for line in content.split("\n"):
            if "交叉能力矩阵" in line or "## 6." in line:
                in_matrix = True
                continue
            if in_matrix and line.startswith("|") and line.endswith("|"):
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if not cells or len(cells) < 2:
                    continue
                if all(c.strip().replace("-", "").replace(":", "") == "" for c in cells):
                    continue
                if not headers:
                    headers = cells
                    continue
                name = cells[0].strip()
                usages = {}
                for i, cell in enumerate(cells[1:], 1):
                    if i < len(headers):
                        usages[headers[i]] = cell.strip()
                rows.append({"name": name, "usages": usages})
            if in_matrix and not line.startswith("|") and rows:
                break
        return rows

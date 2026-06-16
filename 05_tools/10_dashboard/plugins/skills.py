"""
plugins/skills.py — 技能树插件 (v1.0)
显示已安装技能列表/状态/版本
版本: 1.0.0 | 更新: 2026-06-16
"""
from pathlib import Path

from plugins.base import DashboardPlugin, AGENT_SYNC, AGENT_LOCAL, HOSTNAME, MACHINE_UID


class SkillsDashboardPlugin(DashboardPlugin):
    name = "skills"
    label = "技能树"
    icon = "🧩"
    version = "1.0.0"
    description = "技能树：已安装技能列表/状态/版本"
    order = 60

    def _scan_skills(self) -> list[dict]:
        """扫描所有技能"""
        skills = []
        skills_dirs = [
            AGENT_SYNC / "02_skills",
            Path.home() / ".workbuddy" / "skills",
        ]
        for sd in skills_dirs:
            if sd.exists():
                for d in sd.iterdir():
                    if d.is_dir() and (d / "SKILL.md").exists():
                        skills.append({
                            "name": d.name,
                            "path": str(d),
                            "has_skill_md": True,
                        })
        return skills

    def summary(self, machines: list[str]) -> dict:
        skills = self._scan_skills()
        return {
            "总技能": len(skills),
            "技能列表": [s["name"] for s in skills[:20]],
        }

    def detail(self, machine: str = "") -> dict:
        return {"machine": machine or HOSTNAME, "skills": self._scan_skills()}

"""
plugins/collector.py — 内容采集插件 (v2)
版本: 1.0.0 | 更新: 2026-05-18
"""
from pathlib import Path
from plugins.base import DashboardPlugin, AGENT_SYNC, AGENT_LOCAL, CROSS_MACHINE, HOSTNAME
from plugins._registry import get_plugin_data

class CollectorPlugin(DashboardPlugin):
    name = "collector"
    label = "内容采集"
    icon = "📡"
    version = "1.0.0"
    description = "采集进度 / 待处理收件箱"
    order = 40

    def _count_submissions(self):
        inbox = AGENT_SYNC / "03_knowledge" / "01_submissions"
        total = 0
        if inbox.exists():
            for f in inbox.rglob("*.md"):
                total += 1
        return total

    def summary(self, machines):
        subs = self._count_submissions()
        return {"各机器": {HOSTNAME: {"待处理": subs, "今日": 0}}}

    def detail(self, machine=""):
        return {HOSTNAME: {"收件箱路径": str(AGENT_SYNC / "03_knowledge" / "01_submissions")}}


class SkillsPlugin(DashboardPlugin):
    name = "skills"
    label = "技能树"
    icon = "🧩"
    version = "1.0.0"
    description = "所有已安装技能的清单和版本"
    order = 50

    def _scan_skills(self):
        skills_dir = Path.home() / ".workbuddy" / "skills"
        result = []
        if skills_dir.exists():
            for d in sorted(skills_dir.iterdir()):
                if d.is_dir():
                    sk = d / "SKILL.md"
                    ver = ""
                    desc = ""
                    if sk.exists():
                        for line in sk.read_text().split("\n"):
                            if line.startswith("version:"):
                                ver = line.split(":")[1].strip().strip('"')
                            if line.startswith("description:"):
                                desc = line.split(":")[1].strip().strip('"')[:40]
                    result.append({"name": d.name, "version": ver or "-", "description": desc})
        return result

    def summary(self, machines):
        skills = self._scan_skills()
        custom = sum(1 for s in skills if s["version"] != "-")
        return {
            "总技能": len(skills),
            "自定义": custom,
            "各机器": {HOSTNAME: {"技能数": len(skills), "自定义": custom}},
        }

    def detail(self, machine=""):
        return {HOSTNAME: {"技能列表": self._scan_skills()}}


class KnowledgePlugin(DashboardPlugin):
    name = "knowledge"
    label = "知识库"
    icon = "📚"
    version = "1.0.0"
    description = "知识库分仓统计"
    order = 60

    def _count_knowledge(self):
        kb = AGENT_SYNC / "03_knowledge"
        stats = {}
        for d in sorted(kb.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                count = len(list(d.rglob("*.md")))
                if count > 0:
                    stats[d.name] = count
        return stats

    def summary(self, machines):
        stats = self._count_knowledge()
        total = sum(stats.values())
        return {"总知识": total, "各机器": {HOSTNAME: {"分类数": len(stats), "总文件": total}}}

    def detail(self, machine=""):
        return {HOSTNAME: {"统计": self._count_knowledge()}}


class AutomationPlugin(DashboardPlugin):
    name = "automation"
    label = "自动化任务"
    icon = "⏰"
    version = "1.0.0"
    description = "定时任务列表和执行历史"
    order = 70

    def _read_tasks(self):
        task_dir = CROSS_MACHINE / "tasks"
        stats = {"pending": 0, "completed": 0}
        for status in ["pending", "completed"]:
            d = task_dir / status
            if d.exists():
                for f in d.iterdir():
                    if f.suffix == ".json":
                        stats[status] += 1
        return stats

    def _read_pending_tasks(self):
        task_dir = CROSS_MACHINE / "tasks" / "pending"
        tasks = []
        if task_dir.exists():
            for f in sorted(task_dir.iterdir()):
                if f.suffix == ".json":
                    try:
                        import json
                        tasks.append(json.loads(f.read_text()))
                    except:
                        pass
        return tasks

    def summary(self, machines):
        stats = self._read_tasks()
        pending = self._read_pending_tasks()
        by_machine = {}
        for t in pending:
            target = t.get("target_host", "未知")
            if target not in by_machine:
                by_machine[target] = 0
            by_machine[target] += 1
        return {"待处理": stats.get("pending", 0), "已完成": stats.get("completed", 0), "各机器": by_machine}

    def detail(self, machine=""):
        return {HOSTNAME: {"待处理任务": self._read_pending_tasks()}}


class ToolsPlugin(DashboardPlugin):
    name = "tools"
    label = "工具集"
    icon = "🔧"
    version = "1.0.0"
    description = "05_tools/ 目录下的所有工具模块"
    order = 80

    def _scan_tools(self):
        tools_dir = AGENT_SYNC / "05_tools"
        result = []
        if tools_dir.exists():
            for d in sorted(tools_dir.iterdir()):
                if d.is_dir() and not d.name.startswith("."):
                    readme = d / "README.md"
                    desc = ""
                    if readme.exists():
                        for line in readme.read_text().split("\n")[:3]:
                            if line.strip() and not line.startswith("#"):
                                desc = line.strip()[:50]
                                break
                    result.append({"name": d.name, "description": desc})
        return result

    def summary(self, machines):
        tools = self._scan_tools()
        return {"总工具": len(tools), "各机器": {HOSTNAME: {"工具数": len(tools)}}}

    def detail(self, machine=""):
        return {HOSTNAME: {"工具列表": self._scan_tools()}}


class SystemPlugin(DashboardPlugin):
    name = "system"
    label = "系统核心"
    icon = "⚙️"
    version = "1.0.0"
    description = "Git仓库/版本/磁盘/运行时间"
    order = 90

    def summary(self, machines):
        import subprocess, shutil
        git_ver = ""
        try:
            r = subprocess.run(["git","log","-1","--format=%h %s"], capture_output=True, text=True,
                              timeout=5, cwd=str(AGENT_SYNC))
            git_ver = r.stdout.strip()
        except: pass
        disk = shutil.disk_usage(str(AGENT_SYNC))
        return {
            "各机器": {HOSTNAME: {
                "Git版本": git_ver[:30] if git_ver else "-",
                "磁盘总GB": round(disk.total / 1e9, 1),
                "磁盘可用GB": round(disk.free / 1e9, 1),
                "AgentOS路径": str(AGENT_SYNC),
            }}
        }

    def detail(self, machine=""):
        import subprocess, shutil, os
        git_log = []
        try:
            r = subprocess.run(["git","log","--oneline","-5"], capture_output=True, text=True,
                              timeout=5, cwd=str(AGENT_SYNC))
            git_log = [l.strip() for l in r.stdout.strip().split("\n") if l]
        except: pass
        remotes = []
        try:
            r = subprocess.run(["git","remote","-v"], capture_output=True, text=True,
                              timeout=5, cwd=str(AGENT_SYNC))
            remotes = [l.strip() for l in r.stdout.strip().split("\n") if l]
        except: pass
        disk = shutil.disk_usage(str(AGENT_SYNC))
        return {HOSTNAME: {
            "Git仓库": remotes,
            "最近提交": git_log,
            "磁盘": {"总": round(disk.total/1e9,1), "已用": round((disk.total-disk.free)/1e9,1), "可用": round(disk.free/1e9,1)},
            "机器UID": MACHINE_UID,
            "Python": os.popen("python3 --version 2>/dev/null").read().strip() or "-",
            "Node": os.popen("node --version 2>/dev/null").read().strip() or "-",
        }}

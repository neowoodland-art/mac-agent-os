"""
plugins/system_plugins.py — 系统级插件合集 (v2)
包含: Collector / Skills / Knowledge / Automation / Tools / System
版本: 2.0.0 | 更新: 2026-05-18
"""
from pathlib import Path
import json
from plugins.base import DashboardPlugin, AGENT_SYNC, AGENT_LOCAL, CROSS_MACHINE, HOSTNAME, MACHINE_UID
from plugins._registry import get_plugin_data


class CollectorPlugin(DashboardPlugin):
    name = "collector"
    label = "内容采集"
    icon = "📡"
    version = "2.0.0"
    description = "采集工具 / 收件箱 / 使用统计"
    order = 40

    MANUAL_DESC = {
        "doubao_driver": "豆包浏览器驱动 — 抖音视频文字提取/分析",
        "analyze": "AI分析 — 口播素材内容解析与分类",
        "collect": "搜索采集 — OpenCLI桥接/百度HTTP双模式",
        "app": "Web界面 — Gradio交互式素材管理中心",
        "downloader": "下载器 — 视频/音频/图片批量下载",
        "script_factory": "脚本工厂 — 自动生成采集脚本",
        "utils": "工具函数 — Cookie管理/缓存/日志",
    }

    def _scan_tools(self):
        """扫描现有采集工具"""
        tools_dir = AGENT_SYNC / "05_tools" / "05_crawl" / "content-inspiration"
        tools = []
        if tools_dir.exists():
            for f in sorted(tools_dir.iterdir()):
                if f.suffix == ".py" and not f.name.startswith("_"):
                    desc = self.MANUAL_DESC.get(f.stem, "")
                    if not desc:
                        content = f.read_text(encoding="utf-8").split("\n")
                        for line in content[:8]:
                            s = line.strip().strip('"').strip("'")
                            if s and not s.startswith("usage") and not s.startswith("用法"):
                                desc = s[:60]
                                break
                    tools.append({"name": f.stem, "desc": desc or "采集脚本"})
        return tools

    def _count_inbox(self):
        inbox = AGENT_SYNC / "03_knowledge" / "00_inbox"
        subs = AGENT_SYNC / "03_knowledge" / "01_submissions"
        return {
            "收件箱": len(list(inbox.rglob("*.md"))) if inbox.exists() else 0,
            "提交箱": len(list(subs.rglob("*.md"))) if subs.exists() else 0,
        }

    def summary(self, machines):
        cnt = self._count_inbox()
        tools = self._scan_tools()
        return {
            "采集工具": len(tools),
            "待处理": cnt["收件箱"],
            "提交箱": cnt["提交箱"],
            "各机器": {HOSTNAME: {
                "工具数": len(tools),
                "待处理": cnt["收件箱"],
            }}
        }

    def detail(self, machine=""):
        return {HOSTNAME: {
            "采集工具": self._scan_tools(),
            "收件箱统计": self._count_inbox(),
            "收件箱路径": str(AGENT_SYNC / "03_knowledge" / "00_inbox"),
        }}


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
                                desc = line.split(":")[1].strip().strip('"')[:60]
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
    version = "2.0.0"
    description = "分仓统计 / 浓缩卡片 / 教科书体系"
    order = 60

    CATEGORY_LABELS = {
        "00_inbox": "待提纯",
        "01_submissions": "提交箱",
        "10_concepts": "概念",
        "20_methods": "方法",
        "30_facts": "事实",
        "40_references": "参考",
        "50_resources": "素材",
        "60_opinions": "观点",
        "90_archive": "归档",
        "99_system": "系统",
    }

    def _count_knowledge(self):
        kb = AGENT_SYNC / "03_knowledge"
        stats = {}
        for d in sorted(kb.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                count = len(list(d.rglob("*.md")))
                if count > 0:
                    label = self.CATEGORY_LABELS.get(d.name, d.name)
                    stats[d.name] = {"label": label, "count": count}
        return stats

    def _get_textbook_info(self):
        """AI视频教科书信息"""
        textbook_dir = AGENT_SYNC / "03_knowledge" / "20_methods"
        chapters = []
        if textbook_dir.exists():
            for f in sorted(textbook_dir.iterdir()):
                if f.suffix == ".md" and not f.name.startswith("_"):
                    chapters.append(f.stem)
        ai_dir = textbook_dir / "ai-video-system"
        ai_files = 0
        if ai_dir.exists():
            ai_files = len(list(ai_dir.rglob("*.md")))
        return {
            "教材章节": len(chapters),
            "AI视频教科书": f"{len(chapters)}个文件",
            "Kling知识": ai_files,
        }

    def summary(self, machines):
        stats = self._count_knowledge()
        total = sum(v["count"] for v in stats.values())
        textbook = self._get_textbook_info()
        return {
            "总知识": total,
            "分类": len(stats),
            "AI视频教材": textbook.get("AI视频教科书", ""),
            "各机器": {HOSTNAME: {
                "分类数": len(stats),
                "总文件": total,
                "教材章节": textbook.get("教材章节", 0),
            }}
        }

    def detail(self, machine=""):
        stats = self._count_knowledge()
        textbook = self._get_textbook_info()
        return {HOSTNAME: {
            "分类统计": stats,
            "教科书": textbook,
            "README路径": str(AGENT_SYNC / "03_knowledge" / "README.md"),
        }}


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
            by_machine.setdefault(target, 0)
            by_machine[target] += 1
        return {"待处理": stats.get("pending", 0), "已完成": stats.get("completed", 0), "各机器": by_machine}

    def detail(self, machine=""):
        return {HOSTNAME: {"待处理任务": self._read_pending_tasks()}}


class ToolsPlugin(DashboardPlugin):
    name = "tools"
    label = "工具集"
    icon = "🔧"
    version = "2.0.0"
    description = "05_tools/ 工具模块清单 + 说明 + 路径"
    order = 80

    CATEGORY_MAP = {
        "00_setup": "系统设置",
        "01_system": "系统",
        "02_browser": "浏览器",
        "03_ocr": "OCR",
        "04_ai": "AI",
        "04_media": "媒体",
        "05_crawl": "采集",
        "06_mobile": "移动端",
        "07_matrix": "矩阵",
        "08_trae_agent": "Trae代理",
        "09_ave": "视频工厂",
        "10_dashboard": "看板",
    }

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
                                desc = line.strip()[:60]
                                break
                    cat = self.CATEGORY_MAP.get(d.name, "其他")
                    result.append({"name": d.name, "cat": cat, "desc": desc, "path": str(d)})
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
    version = "2.0.0"
    description = "AgentOS内核 / AI引擎 / 记忆系统 / 知识库"
    order = 90

    def _get_kernel_info(self):
        import subprocess, json
        
        agentos_ver = "v2.1.0"
        arch_ver = "联邦版 (2026-05)"
        llm_engine = "oMLX v0.3.6 (Apple MLX)"
        llm_models = []
        models_dir = Path.home() / ".omlx" / "models"
        if models_dir.exists():
            for m in sorted(models_dir.iterdir()):
                llm_models.append(m.name)
        
        memory = {
            "架构": "四层记忆 + 自然语言知识库 双轨",
            "L0 硬约束": "SOUL.md (~3KB), 不可绕过",
            "L1 关键词索引": "keyword_index.json + ChromaDB 语义向量库",
            "L2 结构化事实": "facts.db (SQLite), 结构化三元组",
            "L3 原文": "raw/ 目录, 按需加载",
            "检索引擎": "BM25 + ChromaDB 向量 + RRF 融合",
            "向量维度": "1024 (Qwen3-Embedding-0.6B)",
        }
        
        kb_dirs = AGENT_SYNC / "03_knowledge"
        kb_stats = {}
        if kb_dirs.exists():
            for d in sorted(kb_dirs.iterdir()):
                if d.is_dir() and not d.name.startswith("."):
                    count = len(list(d.rglob("*.md")))
                    if count > 0:
                        kb_stats[d.name] = count
        
        skills_dir = Path.home() / ".workbuddy" / "skills"
        skill_count = 0
        if skills_dir.exists():
            skill_count = len([d for d in skills_dir.iterdir() if d.is_dir()])
        
        machine_count = 0
        try:
            r = subprocess.run(["curl","-s","http://localhost:9988/api/machines"], 
                             capture_output=True, text=True, timeout=3)
            if r.stdout:
                d = json.loads(r.stdout)
                machine_count = d.get("total", 0)
        except: pass
        
        return {
            "AgentOS 版本": agentos_ver,
            "架构版本": arch_ver,
            "LLM引擎": llm_engine,
            "已加载模型": llm_models,
            "记忆系统": memory,
            "知识库规模": kb_stats,
            "技能总数": skill_count,
            "联邦机器数": machine_count,
            "仓库": "mac-agent-os (Gitee + GitHub 双同步)",
            "运行主机": HOSTNAME,
        }

    def summary(self, machines):
        import subprocess, shutil
        git_ver = ""
        try:
            r = subprocess.run(["git","log","-1","--format=%h %s"], capture_output=True, text=True,
                              timeout=5, cwd=str(AGENT_SYNC))
            git_ver = r.stdout.strip()
        except: pass
        disk = shutil.disk_usage(str(AGENT_SYNC))
        kernel = self._get_kernel_info()
        return {
            "各机器": {HOSTNAME: {
                "AgentOS版本": kernel.get("AgentOS 版本", "-"),
                "LLM引擎": kernel.get("LLM引擎", "-"),
                "模型数": len(kernel.get("已加载模型", [])),
                "记忆层级": "L0+L1+L2+L3",
                "技能数": kernel.get("技能总数", 0),
                "知识库": sum(kernel.get("知识库规模", {}).values()),
                "Git版本": git_ver[:25] if git_ver else "-",
                "磁盘总GB": round(disk.total / 1e9, 1),
                "磁盘可用GB": round(disk.free / 1e9, 1),
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
        kernel = self._get_kernel_info()
        return {HOSTNAME: {
            "AI内核": kernel,
            "Git仓库": remotes,
            "最近提交": git_log,
            "磁盘": {"总": round(disk.total/1e9,1), "已用": round((disk.total-disk.free)/1e9,1), "可用": round(disk.free/1e9,1)},
            "运行时": {
                "Python": os.popen("python3 --version 2>/dev/null").read().strip() or "-",
                "Node": os.popen("node --version 2>/dev/null").read().strip() or "-",
                "Playwright": "✅ 已安装",
                "AgentOS路径": str(AGENT_SYNC),
                "机器UID": MACHINE_UID,
                "主机名": HOSTNAME,
            },
        }}

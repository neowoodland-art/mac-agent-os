#!/usr/bin/env python3
"""
kb_api.py — 知识库管理 API 模块

集中管理知识库的所有操作，供 Dashboard 调用。
每个操作都有参数配置 + 日志记录。

版本: 1.0.0 | 更新: 2026-05-31
"""
import json, os, sys, subprocess, re, shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

HOME = Path.home()
AGENT_SYNC = Path(os.environ.get("AGENT_SYNC", str(HOME / "workbuddy-agent-os" / "agent-sync")))
AGENT_LOCAL = Path(os.environ.get("AGENT_LOCAL", str(HOME / "workbuddy-agent-os" / "agent-local")))
KNOWLEDGE = AGENT_SYNC / "03_knowledge"
TASKS_DIR = AGENT_SYNC / "04_memory" / "cross_machine" / "tasks"

# 知识库分类目录
KB_CATEGORIES = {
    "00_inbox": "待提纯",
    "00_stream": "流式",
    "01_daily": "日志",
    "01_submissions": "提交箱",
    "04_ops": "运维",
    "10_concepts": "概念",
    "20_methods": "方法",
    "30_facts": "事实",
    "40_references": "参考",
    "50_resources": "素材",
    "60_opinions": "观点",
    "90_archive": "归档",
    "99_system": "系统",
}


class KBManager:
    """知识库管理——所有操作集中入口"""

    def __init__(self):
        self._log_path = AGENT_LOCAL / "runtime" / "kb_ops.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    # ═══════════════════════════════════════════════════════
    # 统计
    # ═══════════════════════════════════════════════════════

    def get_stats(self) -> dict:
        """返回知识库各目录统计"""
        stats = {}
        total = 0
        cat_order = []
        for d in sorted(KNOWLEDGE.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                count = len(list(d.rglob("*.md")))
                label = KB_CATEGORIES.get(d.name, d.name)
                stats[d.name] = {"label": label, "count": count}
                total += count
                cat_order.append(d.name)
        return {
            "categories": stats,
            "total": total,
            "order": cat_order,
            "updated_at": datetime.now().isoformat(),
        }

    # ═══════════════════════════════════════════════════════
    # 操作：提纯收件箱 / 汇聚 / 入库 / 搜索 / 备份 / 同步
    # ═══════════════════════════════════════════════════════

    def run_refine(self, params: dict = None) -> dict:
        """执行 inbox_refine 提纯

        params:
          - auto_classify: bool (默认True)
          - target_dirs: list[str] (默认["00_inbox"])
        """
        params = params or {}
        self._log_op("refine", params, "started")
        try:
            # 调用 inbox_refine 脚本
            script = AGENT_SYNC / "05_tools" / "01_system" / "inbox_refine.py"
            cmd = [sys.executable, str(script)]
            if not params.get("auto_classify", True):
                cmd.append("--no-classify")

            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                              cwd=str(script.parent))
            result = {
                "status": "ok" if r.returncode == 0 else "error",
                "stdout": r.stdout[-1000:],
                "stderr": r.stderr[-500:],
                "returncode": r.returncode,
            }
            self._log_op("refine", params, result["status"], result)
            return result
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "执行超时(120s)"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def run_collect_to_inbox(self, params: dict = None) -> dict:
        """执行 collect_to_inbox 汇聚

        params:
          - source_dirs: list[str] (默认全部目录)
        """
        params = params or {}
        self._log_op("collect_to_inbox", params, "started")
        try:
            script = AGENT_SYNC / "05_tools" / "01_system" / "collect_to_inbox.py"
            cmd = [sys.executable, str(script)]
            sources = params.get("source_dirs", [])
            for s in sources:
                cmd.extend(["--source", s])

            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180,
                              cwd=str(script.parent))
            result = {
                "status": "ok" if r.returncode == 0 else "error",
                "stdout": r.stdout[-1000:],
                "stderr": r.stderr[-500:],
                "returncode": r.returncode,
            }
            self._log_op("collect_to_inbox", params, result["status"], result)
            return result
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "执行超时(180s)"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def run_ingest(self, params: dict) -> dict:
        """知识入库

        params:
          - source: str (URL 或文本)
          - category: str (目标分类目录)
          - tags: str (逗号分隔的标签)
          - title: str (可选标题)
        """
        params = params or {}
        source = params.get("source", "")
        if not source:
            return {"status": "error", "error": "需要提供 URL 或文本"}
        self._log_op("ingest", params, "started")
        try:
            # 调用 kb_manager 脚本
            script = AGENT_SYNC / "05_tools" / "01_system" / "kb_ingest.py"
            if script.exists():
                cmd = [sys.executable, str(script), source]
            else:
                # 降级: 直接生成 markdown 文件
                cmd = self._fallback_ingest(source, params)

            if isinstance(cmd, dict):
                result = cmd
            else:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                                  cwd=str(script.parent))
                result = {
                    "status": "ok" if r.returncode == 0 else "error",
                    "stdout": r.stdout[-500:],
                    "stderr": r.stderr[-300:],
                }
            self._log_op("ingest", params, result["status"], result)
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _fallback_ingest(self, source: str, params: dict) -> dict:
        """降级入库: 直接写 markdown 文件"""
        cat = params.get("category", "00_inbox")
        tags = params.get("tags", "")
        title = params.get("title", source[:40])
        target_dir = KNOWLEDGE / cat
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = re.sub(r'[^\w\u4e00-\u9fff]+', '_', title)[:50] + ".md"
        filepath = target_dir / filename

        content = f"""---
title: "{title}"
created: {datetime.now().isoformat()}
tags: [{tags}]
source: "{source[:200]}"
---

# {title}

{source}
"""
        filepath.write_text(content, encoding="utf-8")
        return {"status": "ok", "file": str(filepath), "method": "fallback"}

    def search(self, params: dict) -> dict:
        """全文搜索知识库

        params:
          - query: str (搜索关键词)
          - category: str (可选, 限制目录)
          - limit: int (最多结果)
        """
        query = (params or {}).get("query", "")
        if not query:
            return {"status": "error", "error": "需要搜索关键词"}
        category = (params or {}).get("category", "")
        limit = (params or {}).get("limit", 20)

        results = []
        search_dir = KNOWLEDGE / category if category else KNOWLEDGE
        if not search_dir.exists():
            return {"status": "ok", "results": []}

        for f in search_dir.rglob("*.md"):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
                if query.lower() in text.lower():
                    # 提取匹配上下文
                    idx = text.lower().index(query.lower())
                    start = max(0, idx - 60)
                    end = min(len(text), idx + len(query) + 60)
                    context = text[start:end].replace("\n", " ")
                    results.append({
                        "file": str(f.relative_to(KNOWLEDGE)),
                        "category": f.parent.name,
                        "context": context,
                    })
                    if len(results) >= limit:
                        break
            except:
                continue

        return {"status": "ok", "results": results, "total": len(results)}

    def backup(self, params: dict = None) -> dict:
        """备份知识库"""
        params = params or {}
        label = params.get("label", f"kb_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self._log_op("backup", params, "started")
        try:
            backup_dir = AGENT_LOCAL / "backups" / "knowledge" / label
            backup_dir.mkdir(parents=True, exist_ok=True)

            # 排除 .git 和 __pycache__
            shutil.copytree(KNOWLEDGE, backup_dir,
                          ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
                          dirs_exist_ok=True)
            count = len(list(backup_dir.rglob("*.md")))
            result = {"status": "ok", "path": str(backup_dir), "files": count}
            self._log_op("backup", params, "ok", result)
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def git_sync(self, params: dict = None) -> dict:
        """Git 同步"""
        params = params or {}
        self._log_op("git_sync", params, "started")
        try:
            cmds = [
                ["git", "add", "03_knowledge/"],
                ["git", "status", "--porcelain", "03_knowledge/"],
                ["git", "commit", "-m", "kb: auto sync"],
                ["git", "push"],
            ]
            outputs = []
            for cmd in cmds:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                                  cwd=str(AGENT_SYNC))
                if r.returncode != 0 and cmd[1] == "commit":
                    if "nothing to commit" in r.stderr:
                        outputs.append("nothing to commit")
                        continue
                outputs.append(r.stdout[-200:] or r.stderr[-200:])

            result = {"status": "ok", "outputs": outputs[-3:]}
            self._log_op("git_sync", params, "ok", result)
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ═══════════════════════════════════════════════════════
    # 记忆库管理
    # ═══════════════════════════════════════════════════════

    def get_memory_stats(self) -> dict:
        """返回记忆库各层统计"""
        stats = {"l1_keywords": 0, "l2_facts": 0, "l3_files": 0, "vector_count": 0}

        # L1 关键词
        kw_path = AGENT_LOCAL / "memory" / "vector_db" / "keyword_index.json"
        if kw_path.exists():
            try:
                import json
                kw = json.loads(kw_path.read_text())
                stats["l1_keywords"] = len(kw) if isinstance(kw, (list, dict)) else 0
            except:
                pass

        # L2 facts.db
        l2_path = AGENT_SYNC / "04_memory" / "long_term" / "facts.db"
        if l2_path.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(l2_path))
                c = conn.cursor()
                c.execute("SELECT count(*) FROM facts")
                stats["l2_facts"] = c.fetchone()[0]
                conn.close()
            except:
                pass

        # L3 原文
        l3_dir = AGENT_LOCAL / "memory" / "raw" / "04_memory"
        if l3_dir.exists():
            stats["l3_files"] = len([f for f in l3_dir.iterdir() if f.suffix == ".md"])

        # Chroma 向量
        chroma_dir = AGENT_LOCAL / "memory" / "vector_db" / "chroma"
        if chroma_dir.exists():
            stats["vector_count"] = len(list(chroma_dir.rglob("*.bin"))) + len(list(chroma_dir.rglob("*.pickle")))

        return stats

    def get_l2_facts(self, limit: int = 100, offset: int = 0, search: str = "") -> dict:
        """返回 L2 事实列表"""
        l2_path = AGENT_SYNC / "04_memory" / "long_term" / "facts.db"
        if not l2_path.exists():
            return {"total": 0, "facts": []}
        import sqlite3
        conn = sqlite3.connect(str(l2_path))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        if search:
            c.execute("SELECT count(*) FROM facts WHERE content LIKE ?", (f"%{search}%",))
            total = c.fetchone()[0]
            c.execute("SELECT rowid, * FROM facts WHERE content LIKE ? ORDER BY rowid DESC LIMIT ? OFFSET ?",
                     (f"%{search}%", limit, offset))
        else:
            total = c.execute("SELECT count(*) FROM facts").fetchone()[0]
            c.execute("SELECT rowid, * FROM facts ORDER BY rowid DESC LIMIT ? OFFSET ?", (limit, offset))
        facts = [dict(r) for r in c.fetchall()]
        conn.close()
        return {"total": total, "facts": facts}

    def update_l2_fact(self, rowid: int, content: str, category: str = "") -> dict:
        """更新 L2 事实"""
        l2_path = AGENT_SYNC / "04_memory" / "long_term" / "facts.db"
        if not l2_path.exists():
            return {"status": "error", "error": "facts.db 不存在"}
        import sqlite3
        conn = sqlite3.connect(str(l2_path))
        c = conn.cursor()
        try:
            if category:
                c.execute("UPDATE facts SET content=?, category=? WHERE rowid=?", (content, category, rowid))
            else:
                c.execute("UPDATE facts SET content=? WHERE rowid=?", (content, rowid))
            conn.commit()
            conn.close()
            return {"status": "ok", "updated": rowid}
        except Exception as e:
            conn.close()
            return {"status": "error", "error": str(e)}

    def get_l3_files(self) -> list[dict]:
        """返回 L3 原文文件列表"""
        l3_dir = AGENT_LOCAL / "memory" / "raw"
        if not l3_dir.exists():
            return []
        files = []
        for f in sorted(l3_dir.iterdir()):
            if f.suffix == ".md":
                files.append({
                    "name": f.name,
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "updated": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
        return files

    def get_l3_file_content(self, filename: str) -> dict:
        """读取 L3 原文文件内容"""
        l3_dir = AGENT_LOCAL / "memory" / "raw"
        filepath = l3_dir / filename
        if not filepath.exists() or not filename.endswith(".md"):
            return {"status": "error", "error": "文件不存在"}
        return {"status": "ok", "name": filename, "content": filepath.read_text(encoding="utf-8", errors="ignore")}

    def get_l1_keywords(self) -> list:
        """返回 L1 关键词列表"""
        kw_path = AGENT_LOCAL / "memory" / "vector_db" / "keyword_index.json"
        if not kw_path.exists():
            return []
        try:
            import json
            data = json.loads(kw_path.read_text())
            if isinstance(data, dict):
                return [{"word": k, "freq": v.get("freq", v) if isinstance(v, dict) else v} for k, v in data.items()]
            return data if isinstance(data, list) else []
        except:
            return []

    def get_system_docs(self) -> list[dict]:
        """返回联邦系统文档目录"""
        sys_dir = KNOWLEDGE / "99_system"
        if not sys_dir.exists():
            return []
        docs = []
        for f in sorted(sys_dir.iterdir()):
            if f.suffix == ".md" and not f.name.startswith("."):
                docs.append({
                    "name": f.name.replace(".md", ""),
                    "title": f.read_text(encoding="utf-8", errors="ignore").split("\n")[0].replace("#", "").strip()[:60],
                    "size_kb": round(f.stat().st_size / 1024, 1),
                })
        return docs

    def get_system_doc_content(self, name: str) -> dict:
        """读取系统文档内容"""
        sys_dir = KNOWLEDGE / "99_system"
        filepath = sys_dir / (name + ".md")
        if not filepath.exists():
            # try without .md
            filepath = sys_dir / name
        if not filepath.exists() or not filepath.suffix == ".md":
            return {"status": "error", "error": "文档不存在"}
        return {"status": "ok", "name": name, "content": filepath.read_text(encoding="utf-8", errors="ignore")[:5000]}

    def get_skills_catalog(self) -> list[dict]:
        """返回已安装技能目录"""
        skills_dir = Path.home() / ".workbuddy" / "skills"
        if not skills_dir.exists():
            return []
        skills = []
        for d in sorted(skills_dir.iterdir()):
            if d.is_dir():
                sk = d / "SKILL.md"
                if sk.exists():
                    content = sk.read_text(encoding="utf-8", errors="ignore")
                    name = ""
                    desc = ""
                    triggers = []
                    for line in content.split("\n"):
                        if line.startswith("name:"):
                            name = line.split(":", 1)[1].strip().strip('"').strip("'")
                        elif line.startswith("description:"):
                            desc = line.split(":", 1)[1].strip().strip('"').strip("'")
                        elif "trigger" in line.lower() and "-" in line:
                            t = line.split("-", 1)[1].strip().strip('"').strip("'")
                            if t:
                                triggers.append(t)
                    skills.append({
                        "name": name or d.name,
                        "dir": d.name,
                        "description": desc[:80],
                        "triggers": triggers[:5],
                    })
        return skills

    def get_tools_catalog(self) -> list[dict]:
        """返回工具目录"""
        tools_dir = AGENT_SYNC / "05_tools"
        if not tools_dir.exists():
            return []
        tools = []
        for d in sorted(tools_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                tools.append({
                    "name": d.name,
                    "path": str(d.relative_to(AGENT_SYNC)),
                    "items": len([f for f in d.rglob("*") if f.is_file() and f.suffix in (".py",".sh",".md")]),
                })
        return tools

    # ═══════════════════════════════════════════════════════
    # 操作日志
    # ═══════════════════════════════════════════════════════

    def get_logs(self, limit: int = 20) -> list[dict]:
        """返回最近操作日志"""
        if not self._log_path.exists():
            return []
        logs = []
        with open(self._log_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        logs.append(json.loads(line))
                    except:
                        pass
        return logs[-limit:]

    def _log_op(self, op: str, params: dict, status: str, result: dict = None):
        """记录操作日志"""
        entry = {
            "op": op,
            "params": params,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if result:
            entry["result"] = {k: v for k, v in result.items()
                             if k in ("status", "files", "returncode", "file")}
        with open(self._log_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ═══════════════════════════════════════════════════════
# FastAPI router (挂载到 Dashboard app.py)
# ═══════════════════════════════════════════════════════
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/kb", tags=["knowledge"])
_kb = KBManager()


@router.get("/stats")
def api_kb_stats():
    return _kb.get_stats()


@router.post("/refine")
def api_kb_refine(data: dict = None):
    return _kb.run_refine(data or {})


@router.post("/collect")
def api_kb_collect(data: dict = None):
    return _kb.run_collect_to_inbox(data or {})


@router.post("/ingest")
def api_kb_ingest(data: dict):
    return _kb.run_ingest(data)


@router.post("/search")
def api_kb_search(data: dict):
    return _kb.search(data)


@router.post("/backup")
def api_kb_backup(data: dict = None):
    return _kb.backup(data or {})


@router.post("/git-sync")
def api_kb_git_sync(data: dict = None):
    return _kb.git_sync(data or {})


@router.get("/logs")
def api_kb_logs(limit: int = 20):
    return {"logs": _kb.get_logs(limit)}


# ═══════════════════════════════════════════════════════
# 记忆库 API
# ═══════════════════════════════════════════════════════

@router.get("/memory/stats")
def api_memory_stats():
    return _kb.get_memory_stats()


@router.get("/memory/l2")
def api_memory_l2(limit: int = 100, offset: int = 0, search: str = ""):
    return _kb.get_l2_facts(limit, offset, search)


@router.put("/memory/l2/{rowid}")
def api_memory_l2_update(rowid: int, data: dict):
    return _kb.update_l2_fact(rowid, data.get("content", ""), data.get("category", ""))


@router.get("/memory/l3")
def api_memory_l3():
    return {"files": _kb.get_l3_files()}


@router.get("/memory/l3/{filename}")
def api_memory_l3_read(filename: str):
    return _kb.get_l3_file_content(filename)


@router.get("/memory/l1")
def api_memory_l1():
    return {"keywords": _kb.get_l1_keywords()}


# ═══════════════════════════════════════════════════════
# 联邦系统文档 API
# ═══════════════════════════════════════════════════════

@router.get("/system/docs")
def api_system_docs():
    return {"docs": _kb.get_system_docs()}


@router.get("/system/docs/{name}")
def api_system_doc_content(name: str):
    return _kb.get_system_doc_content(name)


# ═══════════════════════════════════════════════════════
# 技能与工具 API
# ═══════════════════════════════════════════════════════

@router.get("/skills")
def api_skills():
    return {"skills": _kb.get_skills_catalog()}


@router.get("/tools")
def api_tools():
    return {"tools": _kb.get_tools_catalog()}


# ═══════════════════════════════════════════════════════
# 自动化任务 API
# ═══════════════════════════════════════════════════════

@router.get("/automations")
def api_automations():
    """返回所有机器的自动化任务"""
    import sqlite3
    tasks = {}

    # 本机 WorkBuddy 自动化
    wb_db = Path.home() / ".workbuddy" / "workbuddy.db"
    if wb_db.exists():
        try:
            conn = sqlite3.connect(str(wb_db))
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT id, name, prompt, rrule, scheduleType, scheduledAt, status, cwds FROM automations ORDER BY id")
            local = []
            for row in c.fetchall():
                d = dict(row)
                d["source"] = _kb._local_hostname
                d["source_type"] = "workbuddy"
                local.append(d)
            if local:
                tasks[_kb._local_hostname] = local
            conn.close()
        except:
            pass

    # 其他机器: 从 cross_machine/data/automation/ 读取
    auto_dir = CROSS_MACHINE / "data" / "automation"
    if auto_dir.exists():
        for f in sorted(auto_dir.iterdir()):
            if f.suffix == ".json":
                try:
                    data = json.loads(f.read_text())
                    hn = data.get("hostname", f.stem)
                    if hn not in tasks:
                        tasks[hn] = []
                    tasks[hn].append({
                        "source": hn,
                        "source_type": "guardd_heartbeat",
                        "guardd_version": data.get("guardd_version", ""),
                        "last_seen": data.get("timestamp", ""),
                    })
                except:
                    pass

    # 加上 C2 命令历史
    c2_dir = CROSS_MACHINE / "tasks" / "completed"
    c2_history = []
    if c2_dir.exists():
        for f in sorted(c2_dir.iterdir(), reverse=True)[:20]:
            if f.suffix == ".json":
                try:
                    d = json.loads(f.read_text())
                    c2_history.append({
                        "type": d.get("type", ""),
                        "target": d.get("target_machine", ""),
                        "status": d.get("status", ""),
                        "time": (d.get("completed_at") or d.get("created_at") or "").replace("T", " ")[:19],
                        "output": str(d.get("output", {}))[:100],
                    })
                except:
                    pass

    return {"machines": tasks, "history": c2_history}


@router.post("/automations")
def api_create_automation(data: dict):
    """创建 WorkBuddy 自动化任务"""
    target = data.get("target", "")
    prompt = data.get("prompt", "")
    command_type = data.get("type", "")
    params = data.get("params", "")
    schedule = data.get("schedule_at", "")
    rrule = data.get("rrule", "")

    if not prompt and not command_type:
        return {"status": "error", "error": "需要 prompt 或命令类型"}

    # 如果是跨机任务, 通过 C2 发送
    if target and target != _kb._local_hostname:
        try:
            import importlib.util
            c2_path = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts" / "c2" / "command_bus.py"
            spec = importlib.util.spec_from_file_location("cb", c2_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            bus = mod.CommandBus()
            result = bus.send(target, command_type, json.loads(params) if params else {}, schedule)
            return {"status": "ok", "channel": "c2", "command_id": result.get("command_id")}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # 本机任务: 写入 WorkBuddy sqlite
    return _create_workbuddy_automation(prompt, rrule, schedule)


def _create_workbuddy_automation(prompt: str, rrule: str = "", schedule_at: str = "") -> dict:
    """写入本机 WorkBuddy 自动化"""
    import sqlite3, uuid
    wb_db = Path.home() / ".workbuddy" / "workbuddy.db"
    if not wb_db.exists():
        return {"status": "error", "error": "WorkBuddy DB 不存在"}
    try:
        conn = sqlite3.connect(str(wb_db))
        c = conn.cursor()
        aid = str(uuid.uuid4())[:8]
        schedule_type = "once" if schedule_at else ("recurring" if rrule else "recurring")
        c.execute(
            "INSERT OR IGNORE INTO automations (id, name, prompt, rrule, scheduleType, scheduledAt, status, cwds) VALUES (?,?,?,?,?,?,?,?)",
            (aid, prompt[:30], prompt, rrule, schedule_type, schedule_at, "ACTIVE", "")
        )
        conn.commit()
        conn.close()
        return {"status": "ok", "id": aid, "prompt": prompt[:30]}
    except Exception as e:
        return {"status": "error", "error": str(e)}

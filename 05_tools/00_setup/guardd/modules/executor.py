"""
executor.py — 任务执行器 (guardd 模块 同步版)

职责:
  - 调 mc run / mc interact 等命令
  - 实时解析 stdout 提取进度
  - 超时控制
  - 执行结果写入 task_store
"""
import os
import re
import signal
import subprocess
import time
from typing import Optional
from modules.task_store import TaskStore, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED


class Executor:
    """任务执行器（同步版本）"""

    def __init__(self, task_store: TaskStore, slot_manager=None):
        self.task_store = task_store
        self.slot_manager = slot_manager
        self._running_procs = {}  # task_id → proc

    def execute(self, task: dict) -> dict:
        """执行一个任务，实时解析输出，返回结果"""
        task_id = task["task_id"]
        account_id = task.get("accounts", [""])[0] if task.get("accounts") else ""
        identity_dir = task.get("identity_dir", account_id)

        cmd = self._build_cmd(task)
        if not cmd:
            task["status"] = STATUS_FAILED
            task["error"] = "无法构建执行命令"
            self.task_store.save(task)
            return {"success": False, "error": "无法构建执行命令"}

        task["status"] = STATUS_RUNNING
        task["started_at"] = time.time()
        self.task_store.save(task)

        # 获取槽位（含 nickname + platform）
        slot = None
        if self.slot_manager:
            try:
                # 从任务参数或账号信息查询昵称和平台
                nickname = task.get("nickname", "")
                platform = task.get("platform", "")
                if not platform and account_id:
                    # 通过 account_id 推断平台
                    platform = "xiaohongshu" if account_id.startswith("xhs_") else "douyin"
                if not nickname:
                    # 尝试从 profiles.json 读取昵称
                    try:
                        import json
                        home = os.path.expanduser("~")
                        pf = os.path.join(home, "workbuddy-agent-os", "agent-local", "tools", "matrix", "data", "profiles.json")
                        if os.path.exists(pf):
                            profiles = json.loads(open(pf).read())
                            if account_id in profiles:
                                nickname = profiles[account_id].get("nickname", "")
                    except Exception:
                        pass
                slot = self.slot_manager.acquire(account_id, identity_dir, nickname, platform)
            except Exception as e:
                task["status"] = STATUS_FAILED
                task["error"] = str(e)
                self.task_store.save(task)
                return {"success": False, "error": str(e)}

        log_lines = []
        try:
            proc = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )
            if slot:
                self.slot_manager.set_pid(slot["browser_id"], proc.pid)
            self._running_procs[task_id] = proc

            max_execution_sec = task.get("max_execution_sec", 7200)
            start_time = time.time()

            # 实时读取输出
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    text = line.decode("utf-8", errors="replace").strip()
                    log_lines.append(text)
                    self._parse_and_update(task_id, account_id, identity_dir, text)

                # 超时检查
                if time.time() - start_time > max_execution_sec:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    except Exception:
                        proc.kill()
                    task["status"] = STATUS_FAILED
                    task["error"] = f"超时 ({max_execution_sec}s)"
                    self.task_store.save(task)
                    return {"success": False, "error": task["error"]}

            exit_code = proc.wait()
            success = exit_code == 0
            task["status"] = STATUS_COMPLETED if success else STATUS_FAILED
            task["completed_at"] = time.time()
            task["exit_code"] = exit_code
            self.task_store.save(task)
            return {"success": success, "exit_code": exit_code, "task_id": task_id}

        except Exception as e:
            task["status"] = STATUS_FAILED
            task["error"] = str(e)
            task["completed_at"] = time.time()
            self.task_store.save(task)
            return {"success": False, "error": str(e)}

        finally:
            if slot:
                self.slot_manager.release(slot["browser_id"])
            self._running_procs.pop(task_id, None)

    def _build_cmd(self, task: dict) -> Optional[str]:
        """根据任务类型构建 shell 命令"""
        cmd_type = task.get("cmd_type", "")
        accounts = ",".join(task.get("accounts", []))
        blueprint = task.get("blueprint", "")
        rounds = task.get("rounds", 1)
        home = __import__("pathlib").Path.home()
        scripts_dir = f"{home}/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts"
        python_path = f"{home}/.workbuddy/binaries/python/envs/agent-os/bin/python3"

        if cmd_type == "nurture":
            return (f"cd {scripts_dir} && PYTHONPATH={scripts_dir} {python_path} -m mc run "
                    f"--accounts={accounts} --blueprints={blueprint} --rounds={rounds} --mix --interval=45-90")
        elif cmd_type in ("interact", "comment"):
            url = task.get("params", {}).get("url", "")
            direction = task.get("params", {}).get("direction", "")
            return (f"cd {scripts_dir} && PYTHONPATH={scripts_dir} {python_path} -m mc run "
                    f"--accounts={accounts} --blueprints={blueprint} --rounds=1 "
                    f"--url={url} --direction={direction}")
        elif cmd_type == "collect":
            return (f"cd {scripts_dir} && PYTHONPATH={scripts_dir} {python_path} -m mc run "
                    f"--accounts={accounts} --blueprints={blueprint} --rounds=1")
        elif cmd_type == "login":
            return (f"cd {scripts_dir} && PYTHONPATH={scripts_dir} {python_path} -m mc smart-login {accounts}")
        return None

    def _parse_and_update(self, task_id: str, account_id: str, browser_id: str, line: str):
        """解析一行日志，更新任务/槽位进度"""
        if not self.slot_manager:
            return
        m = re.search(r"📱\s+(\S+)\s+", line)
        if m:
            blueprint = m.group(1)
            self.slot_manager.update_step(browser_id, f"start:{blueprint}", 0)
        m = re.search(r"([✅❌])\s+\[\s*(\d+)\]\s+(\S+)\s*→", line)
        if m:
            step_index = int(m.group(2))
            step_name = m.group(3)
            self.slot_manager.update_step(browser_id, step_name, step_index)
        if "📊" in line:
            self.slot_manager.update_step(browser_id, "completed")

    def kill(self, task_id: str):
        """强制终止任务"""
        proc = self._running_procs.get(task_id)
        if proc:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                proc.kill()

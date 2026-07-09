#!/usr/bin/env python3
"""
executor.py — 任务执行器 (guardd 模块 同步版)

职责:
  - 调 mc run / mc interact 等命令
  - 实时解析 stdout 提取进度
  - 超时控制（含 60 秒无输出检测）
  - 执行结果写入 task_store
  - shell=False（不再通过 /bin/sh 启动，避免僵尸 shell PID）
"""
import os
import re
import shlex
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional
import logging
from modules.task_store import TaskStore, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED

logger = logging.getLogger("guardd.executor")

HOME = Path.home()
SCRIPTS_DIR = HOME / "workbuddy-agent-os" / "agent-sync" / "05_tools" / "07_matrix" / "scripts"
PYTHON_PATH = HOME / ".workbuddy" / "binaries" / "python" / "envs" / "agent-os" / "bin" / "python3"


class Executor:
    """任务执行器（同步版本，shell=False）"""

    def __init__(self, task_store: TaskStore, slot_manager=None):
        self.task_store = task_store
        self.slot_manager = slot_manager
        self._running_procs = {}  # task_id → proc

    def execute(self, task: dict) -> dict:
        """执行一个任务，实时解析输出，返回结果"""
        task_id = task["task_id"]
        account_id = task.get("accounts", [""])[0] if task.get("accounts") else ""
        identity_dir = task.get("identity_dir", account_id)

        cmd_info = self._build_cmd(task)
        if not cmd_info:
            task["status"] = STATUS_FAILED
            task["error"] = "无法构建执行命令"
            self.task_store.save(task)
            return {"success": False, "error": "无法构建执行命令"}

        logger.info(f"  ▶️ executor: task_id={task.get('task_id','')} accounts={task.get('accounts',[])} cmd_type={task.get('cmd_type','')}")
        logger.info(f"  ▶️ cmd: {' '.join(cmd_info['args'])[:200] if cmd_info.get('args') else 'NONE'}")

        task["status"] = STATUS_RUNNING
        task["started_at"] = time.time()
        self.task_store.save(task)

        # 获取槽位
        slot = None
        if self.slot_manager:
            try:
                nickname = task.get("nickname", "")
                platform = task.get("platform", "")
                if not platform and account_id:
                    platform = "xiaohongshu" if account_id.startswith("xhs_") else "douyin"
                if not nickname:
                    try:
                        import json
                        pf = HOME / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix" / "data" / "profiles.json"
                        if pf.exists():
                            profiles = json.loads(pf.read_text())
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
        # 任务日志文件
        log_path = HOME / "workbuddy-agent-os" / "agent-local" / "runtime" / "guardd" / "tasks" / f"{task_id}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_fh = open(log_path, "w", encoding="utf-8")
        try:
            # shell=False：直接启动 python3 -m ...，不经过 /bin/sh
            proc = subprocess.Popen(
                cmd_info["args"],
                cwd=cmd_info.get("cwd"),
                env=cmd_info.get("env"),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )
            if slot:
                self.slot_manager.set_pid(slot["browser_id"], proc.pid)
            self._running_procs[task_id] = proc

            max_execution_sec = task.get("max_execution_sec", 7200)
            cmd_type = task.get("cmd_type", "")
            # 登录任务允许更长静默等待（5分钟），给用户留够扫码/输手机号的时间
            idle_timeout = 300 if cmd_type in ("login", "smart-login") else 60
            start_time = time.time()
            last_output_time = time.time()

            import select as _select

            # 实时读取输出（非阻塞版）
            while True:
                now = time.time()
                elapsed = now - start_time

                # 浏览器启动超时：登录任务 5 分钟无输出，其他任务 60 秒无输出
                if elapsed > idle_timeout and (now - last_output_time) > idle_timeout:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    except Exception:
                        proc.kill()
                    task["status"] = STATUS_FAILED
                    task["error"] = "浏览器启动超时（60秒无输出）"
                    task["completed_at"] = time.time()
                    self.task_store.save(task)
                    logger.warning(f"  ⏰ [{task_id}] 浏览器启动超时（60秒无输出）")
                    return {"success": False, "error": "浏览器启动超时"}

                if elapsed > max_execution_sec:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    except Exception:
                        proc.kill()
                    task["status"] = STATUS_FAILED
                    task["error"] = f"超时 ({max_execution_sec:.0f}s)"
                    task["completed_at"] = time.time()
                    self.task_store.save(task)
                    logger.warning(f"  ⏰ [{task_id}] 超时 ({elapsed:.0f}s > {max_execution_sec}s)")
                    return {"success": False, "error": task["error"]}

                r, _, _ = _select.select([proc.stdout], [], [], 2.0)
                if r:
                    line = proc.stdout.readline()
                    if not line:
                        if proc.poll() is not None:
                            break
                        continue
                    text = line.decode("utf-8", errors="replace").strip()
                    log_lines.append(text)
                    log_fh.write(text + "\n")
                    log_fh.flush()
                    last_output_time = time.time()
                    self._parse_and_update(task_id, account_id, identity_dir, text)
                else:
                    if proc.poll() is not None:
                        break

            exit_code = proc.wait()
            if exit_code != 0 and task.get("cmd_type") in ("collect", "nurture"):
                try:
                    import json
                    pf = HOME / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix" / "data" / "profiles.json"
                    if pf.exists():
                        mtime = pf.stat().st_mtime
                        started = task.get("started_at", 0)
                        if mtime >= started - 5:
                            logger.info(f"  ✅ [{task_id}] profiles.json 已更新 (mtime={mtime:.0f} >= start={started:.0f})")
                            exit_code = 0
                except Exception:
                    pass
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
            try:
                log_fh.close()
            except Exception:
                pass

    def _build_cmd(self, task: dict) -> Optional[dict]:
        """构建执行命令（返回 args/cwd/env 字典，shell=False）"""
        scripts_dir = str(SCRIPTS_DIR)
        python_path = str(PYTHON_PATH)
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{scripts_dir}:{env.get('PYTHONPATH', '')}"

        cmd_line = task.get("command_line", "")
        if cmd_line:
            # command_line 形如: mc task comment --account=X --url=Y -y
            # 也有旧格式: mc run --accounts=X --blueprints=Y ...
            args = [python_path, "-m"] + shlex.split(cmd_line)
            return {"args": args, "cwd": scripts_dir, "env": env}

        cmd_type = task.get("cmd_type", "")
        accounts = ",".join(task.get("accounts", []))
        blueprint = task.get("blueprint", "")
        rounds = task.get("rounds", 1)

        if cmd_type == "nurture":
            args = [python_path, "-m", "mc", "run",
                    f"--accounts={accounts}", f"--blueprints={blueprint}",
                    f"--rounds={rounds}", "--mix", "--interval=45-90"]
            return {"args": args, "cwd": scripts_dir, "env": env}
        elif cmd_type in ("interact", "comment"):
            url = task.get("params", {}).get("url", "")
            direction = task.get("params", {}).get("direction", "")
            args = [python_path, "-m", "mc", "run",
                    f"--accounts={accounts}", f"--blueprints={blueprint}",
                    "--rounds=1", f"--url={url}", f"--direction={direction}"]
            interval = task.get("interval", 0)
            if interval:
                args.append(f"--interval={interval}")
            return {"args": args, "cwd": scripts_dir, "env": env}
        elif cmd_type == "collect":
            args = [python_path, "-m", "mc", "run",
                    f"--accounts={accounts}", f"--blueprints={blueprint}", "--rounds=1"]
            return {"args": args, "cwd": scripts_dir, "env": env}
        elif cmd_type == "login":
            args = [python_path, "-m", "mc", "smart-login", accounts]
            return {"args": args, "cwd": scripts_dir, "env": env}
        elif cmd_type == "record":
            platform = task.get("params", {}).get("platform", "douyin")
            args = [python_path, "-m", "mc", "record", "start",
                    f"--accounts={accounts}", f"--platform={platform}"]
            return {"args": args, "cwd": scripts_dir, "env": env}
        return None

    def _parse_and_update(self, task_id: str, account_id: str, browser_id: str, line: str):
        """解析一行日志，更新任务/槽位进度"""
        if not self.slot_manager:
            return
        # 更新 step
        for pattern, step_name in [
            (r"(?:正在|开始|执行)\s*([\u4e00-\u9fa5_]+)", None),
            (r"step:\s*(\S+)", None),
        ]:
            m = re.search(pattern, line)
            if m:
                self.slot_manager.update_step(browser_id, m.group(1))
                break
        # 更新 step_index（从 blueprint progress 提取）
        m = re.search(r"(?:步骤|step)\s*(\d+)\s*[/|]\s*(\d+)", line)
        if m:
            self.slot_manager.update_step(browser_id, line[:40],
                                          step_index=int(m.group(1)), total_steps=int(m.group(2)))

    def kill(self, task_id: str) -> bool:
        proc = self._running_procs.get(task_id)
        if proc:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                proc.kill()
            return True
        return False

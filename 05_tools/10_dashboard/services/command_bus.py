"""
command_bus.py — 统一命令传输层 v6

设计原则:
  v5 (2026-06-23): 按机器分组，每台机器只发一条命令（含多个账号）
  v6 (2026-06-25): 每台机器一个执行队列，串行执行

核心机制:
  1. 路由层不拆解命令 — 传全部账号，由 MC 引擎按 identity 分组
  2. 每台机器一个队列 — MachineSession.is_busy 判断是否可发新命令
  3. 新命令 → 机器忙 → 排队等待（status=queued）
  4. 当前命令完成 → 自动启动下一条
  5. 强制停止 → cancel() 杀进程+清浏览器+启动下一条
  6. MC 引擎内部 Semaphore(3) + identity 分组控制并发
  7. 不同机器之间并行执行（互不影响）

架构:
  Dashboard → API → CommandBus → MachineSession(队列) → mc run → 引擎 → Camoufox
"""

import asyncio, json, logging, os, subprocess, sys, time, threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("dashboard.command_bus")

_THIS_DIR = Path(__file__).resolve().parent.parent
AGENT_SYNC = Path(os.environ.get("AGENT_SYNC", str(Path.home() / "workbuddy-agent-os" / "agent-sync")))
AGENT_LOCAL = Path(os.environ.get("AGENT_LOCAL", str(Path.home() / "workbuddy-agent-os" / "agent-local")))
ORACLE_PATH = AGENT_SYNC / "ORACLE.yaml"

from utils.identity import resolve_hostname

HOSTNAME = resolve_hostname()

class CommandStatus(str, Enum):
    QUEUED = "queued"
    PREFLIGHTING = "preflighting"
    PREFLIGHT_FAILED = "preflight_failed"
    DISPATCHING = "dispatching"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CRASHED = "crashed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in (CommandStatus.COMPLETED, CommandStatus.FAILED,
                        CommandStatus.TIMED_OUT, CommandStatus.CRASHED,
                        CommandStatus.CANCELLED, CommandStatus.PREFLIGHT_FAILED)

    @property
    def is_active(self) -> bool:
        return self in (CommandStatus.PREFLIGHTING, CommandStatus.DISPATCHING, CommandStatus.RUNNING)


class Command:
    """一条命令的完整生命周期（v5：支持多账号）"""

    def __init__(self, cmd_type: str, accounts: list, machine: str,
                 command_line: str, run_id: str, params: dict = None):
        self.cmd_type = cmd_type
        self.accounts = accounts              # [str] — 账号ID列表
        self.machine = machine
        self.command_line = command_line
        self.run_id = run_id
        self.params = params or {}

        self.status = CommandStatus.QUEUED
        self.pid = None
        self.message = ""
        self.result = None

        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.last_poll_at = None
        self.log_path = None

    @property
    def account_display(self) -> str:
        """显示用：'douyin_test,xhs_01' 或 'douyin_test'"""
        return ",".join(self.accounts)

    @property
    def elapsed_sec(self) -> float:
        if self.started_at is None:
            return 0
        end = self.completed_at or time.time()
        return end - self.started_at

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "type": self.cmd_type,
            "accounts": self.accounts,
            "account": self.accounts[0] if self.accounts else "",
            "machine": self.machine,
            "status": self.status.value,
            "command": self.command_line,
            "pid": self.pid,
            "message": self.message,
            "elapsed_sec": round(self.elapsed_sec, 1),
            "created_at": datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat(),
            "started_at": datetime.fromtimestamp(self.started_at, tz=timezone.utc).isoformat() if self.started_at else None,
            "completed_at": datetime.fromtimestamp(self.completed_at, tz=timezone.utc).isoformat() if self.completed_at else None,
            "result": self.result,
            "log_path": str(self.log_path) if self.log_path else None,
        }


_ORACLE_MACHINES = None

def _get_machine_info(machine_name: str) -> dict:
    global _ORACLE_MACHINES
    if _ORACLE_MACHINES is None:
        if ORACLE_PATH.exists():
            import yaml
            _ORACLE_MACHINES = yaml.safe_load(ORACLE_PATH.read_text()).get("machines", {})
        else:
            _ORACLE_MACHINES = {}
    for name, info in _ORACLE_MACHINES.items():
        if name == machine_name or info.get("hostname") == machine_name:
            return {"name": name, "hostname": info.get("hostname", name),
                    "ip": info.get("tailscale_ip", ""), "user": info.get("ssh_user", "")}
    return {}


class MachineSession:
    """单台机器的命令执行会话（v6: 每台机器一个队列）"""

    _sessions = {}

    def __init__(self, machine: str):
        self.machine = machine
        self.is_local = (machine == HOSTNAME)
        self.commands: list[Command] = []     # 全部命令（含历史）
        self.current_cmd: Optional[Command] = None  # 正在执行的命令
        self.queued_cmds: list[Command] = []  # 排队等待的命令
        self.max_history = 50
        self._lock = threading.Lock()
        self.machine_info = _get_machine_info(machine) if not self.is_local else {}
        self.ssh_target = None
        if not self.is_local and self.machine_info.get("ip"):
            u = self.machine_info.get("user", "")
            self.ssh_target = f"{u}@{self.machine_info['ip']}" if u else self.machine_info["ip"]

    @property
    def is_busy(self) -> bool:
        """机器是否正在执行命令"""
        return self.current_cmd is not None and self.current_cmd.status.is_active

    @classmethod
    def get(cls, machine: str) -> "MachineSession":
        if machine not in cls._sessions:
            cls._sessions[machine] = cls(machine)
        return cls._sessions[machine]

    def graceful_exit(self, account_id: str = None):
        """优雅退出：执行前清理同机残留进程"""
        for cmd in self.commands[:]:
            if cmd.status.is_active and (account_id is None or account_id in cmd.accounts):
                self.cancel(cmd)
        # 额外清理：pkill 同账号进程
        if self.is_local:
            target = account_id or ""
            try:
                subprocess.run(["pkill", "-f", f"mc run.*{target}"], capture_output=True, timeout=3)
                subprocess.run(["pkill", "-f", f"mc task.*{target}"], capture_output=True, timeout=3)
                subprocess.run(["pkill", "-f", f"mc collect.*{target}"], capture_output=True, timeout=3)
                subprocess.run(["pkill", "-f", f"mc smart-login.*{target}"], capture_output=True, timeout=3)
            except:
                pass
        elif self.ssh_target:
            target = account_id or ""
            try:
                subprocess.run(
                    ["ssh", "-o", "ConnectTimeout=5", self.ssh_target,
                     f"pkill -f 'mc (run|collect|smart-login|task).*{target}' 2>/dev/null; true"],
                    capture_output=True, timeout=5
                )
            except:
                pass

    def preflight(self) -> dict:
        with self._lock:
            active = [c for c in self.commands if c.status.is_active]
            # L3 不限制命令数（一个命令可能涉及多个身份→多个浏览器）
            # 浏览器数限制由 L2 (mc/engine.py) 在开 Camoufox 前检查
            if not self.is_local and self.ssh_target:
                try:
                    r = subprocess.run(
                        ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
                         self.ssh_target, "echo ok"],
                        capture_output=True, text=True, timeout=8
                    )
                    if r.returncode != 0:
                        return {"ok": False, "message": f"机器 {self.machine} SSH 不可达", "running": len(active)}
                except Exception as e:
                    return {"ok": False, "message": f"机器 {self.machine} 连接失败: {e}", "running": len(active)}
            return {"ok": True, "message": "就绪", "running": len(active)}

    def send(self, cmd: Command) -> dict:
        with self._lock:
            # 机器已经在执行命令 → 排队
            if self.is_busy:
                cmd.status = CommandStatus.QUEUED
                cmd.message = f"排队中（当前有任务在执行: {self.current_cmd.run_id}）"
                self.queued_cmds.append(cmd)
                self.commands.insert(0, cmd)
                self._trim_history()
                return {"status": "queued", "message": cmd.message, "run_id": cmd.run_id}

            # 机器空闲 → 立即执行
            if self.is_local:
                result = self._send_local(cmd)
            else:
                result = self._send_remote(cmd)
            if "error" not in result:
                self.current_cmd = cmd
            return result

    def _send_local(self, cmd: Command) -> dict:
        # 系统级安全检查（仅保留警戒线，杀掉异常过多的 mc 进程）
        try:
            mc_count = int(subprocess.run(
                ["pgrep", "-f", "python3.*-m mc"], capture_output=True, text=True, timeout=3
            ).stdout.strip() or "0") or 0
            if mc_count > 600:
                subprocess.run(["pkill", "-f", "python3.*-m mc"], capture_output=True, timeout=3)
                time.sleep(1)
                return {"error": f"系统 mc 进程数过高 ({mc_count})，已自动清理，请重试"}
        except:
            pass

        # ⚠️ 并发控制：CommandBus 只转发，由 MC engine 内部 Semaphore 控制
        # 同一台机器只会发一条命令（路由层已合并），引擎内按 identity 分组 + Semaphore(3)

        scripts_dir = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts"
        log_dir = AGENT_LOCAL / "runtime" / "commands"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{cmd.run_id}.log"
        cmd.log_path = log_path
        log_fh = open(log_path, "w")

        if cmd.cmd_type == "nurture":
            wrapper = str(AGENT_SYNC / "05_tools" / "10_dashboard" / "services" / "nurture_runner.sh")
            accts = ",".join(cmd.accounts)
            bp = cmd.params.get("blueprint") or "douyin_daily"
            rounds = cmd.params.get("rounds") or 10
            p = subprocess.Popen(
                ["bash", wrapper, accts, bp, str(rounds), cmd.run_id],
                stdout=log_fh, stderr=subprocess.STDOUT
            )
        else:
            python_path = f"{Path.home()}/.workbuddy/binaries/python/envs/agent-os/bin/python3"
            full_cmd = f"cd {scripts_dir} && PYTHONPATH='{scripts_dir}' {python_path} -m {cmd.command_line}"
            p = subprocess.Popen(
                full_cmd,
                shell=True, stdout=log_fh, stderr=subprocess.STDOUT
            )

        cmd.pid = p.pid
        cmd.status = CommandStatus.DISPATCHING
        cmd.started_at = time.time()
        self.commands.insert(0, cmd)
        self._trim_history()
        return {"pid": cmd.pid, "log_path": str(log_path)}

    def _send_remote(self, cmd: Command) -> dict:
        if not self.ssh_target:
            cmd.status = CommandStatus.PREFLIGHT_FAILED
            cmd.message = f"机器 {self.machine} 连接信息不存在"
            return {"error": cmd.message}

        py_discover = 'PY=$(ls $HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3 2>/dev/null || which python3); '
        scripts_dir = "$AGENT_SYNC/05_tools/07_matrix/scripts"
        env_setup = f"export AGENT_SYNC=\"$HOME/workbuddy-agent-os/agent-sync\"; export AGENT_LOCAL=\"$HOME/workbuddy-agent-os/agent-local\"; export MC_PYTHON=\"$PY\"; export PYTHONPATH={scripts_dir}:$PYTHONPATH; "

        if cmd.cmd_type == "nurture":
            accts = ",".join(cmd.accounts)
            _bp = cmd.params.get("blueprint") or "douyin_daily"
            _rd = cmd.params.get("rounds") or 10
            wrapper_cmd = f"bash $AGENT_SYNC/05_tools/10_dashboard/services/nurture_runner.sh {accts} {_bp} {_rd} {cmd.run_id}"
            full_cmd = f"{py_discover} {env_setup} nohup {wrapper_cmd} > /tmp/nurture_{cmd.run_id}.log 2>&1 &"
        else:
            full_cmd = f"{py_discover} {env_setup} nohup cd $AGENT_SYNC/05_tools/07_matrix/scripts && $MC_PYTHON -m {cmd.command_line} > /tmp/ops_{cmd.run_id}.log 2>&1 &"

        try:
            subprocess.run(
                ["ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no",
                 self.ssh_target, full_cmd],
                capture_output=True, text=True, timeout=15
            )
            cmd.status = CommandStatus.DISPATCHING
            cmd.started_at = time.time()
            cmd.message = "命令已发送到远程机器"
            self.commands.insert(0, cmd)
            self._trim_history()
            return {"status": "sent"}
        except Exception as e:
            cmd.status = CommandStatus.FAILED
            cmd.message = f"远程发送失败: {e}"
            return {"error": str(e)}

    def _remote_poll_result(self, cmd: Command) -> bool:
        """远程检查：SSH 到远端机器读取 result 文件"""
        if not self.ssh_target:
            return False
        try:
            if cmd.cmd_type == "nurture":
                check = f"cat $AGENT_LOCAL/runtime/nurture/results/{cmd.run_id}.json 2>/dev/null"
            else:
                check = f"cat $AGENT_LOCAL/runtime/results/{cmd.run_id}.json 2>/dev/null; cat /tmp/ops_{cmd.run_id}.log 2>/dev/null"
            r = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
                 self.ssh_target,
                 f"export AGENT_LOCAL=\"$HOME/workbuddy-agent-os/agent-local\"; {check}"],
                capture_output=True, text=True, timeout=8
            )
            if r.returncode == 0 and r.stdout.strip():
                # 尝试解析 JSON（nurture 结果文件）
                try:
                    data = json.loads(r.stdout)
                    cmd.result = data
                    s = data.get("status", "running")
                    if s == "completed":
                        cmd.status = CommandStatus.COMPLETED
                        cmd.completed_at = time.time()
                        cmd.message = f"远程执行完成"
                        return True
                    elif s == "failed":
                        cmd.status = CommandStatus.FAILED
                        cmd.completed_at = time.time()
                        cmd.message = f"远程执行失败: {data.get('error','')}"
                        return True
                    else:
                        steps = data.get("steps", {})
                        cmd.message = f"运行中 (已完成 {steps.get('success', 0)}/{steps.get('total', '?')} 步)"
                        cmd.status = CommandStatus.RUNNING
                        return True
                except ValueError:
                    # 不是 JSON — 可能是日志内容，检查是否包含完成标记
                    if "completed" in r.stdout.lower() or "done" in r.stdout.lower():
                        cmd.status = CommandStatus.COMPLETED
                        cmd.completed_at = time.time()
                        cmd.message = "远程执行完成"
                        return True
                    if "error" in r.stdout.lower() or "traceback" in r.stdout.lower():
                        cmd.status = CommandStatus.FAILED
                        cmd.completed_at = time.time()
                        cmd.message = "远程执行失败"
                        return True
                    # 有输出但未完成 — 运行中
                    if len(r.stdout.strip()) > 20:
                        cmd.status = CommandStatus.RUNNING
                        cmd.message = f"远程进程输出中 ({len(r.stdout)}bytes)"
                        return True
            return False
        except:
            return False

    def poll(self, cmd: Command) -> CommandStatus:
        with self._lock:
            if cmd.status.is_terminal:
                return cmd.status
            cmd.last_poll_at = time.time()

            # 按 cmd_type 获取轮询策略
            strategy = CMD_POLL_STRATEGY.get(cmd.cmd_type, DEFAULT_POLL_STRATEGY)
            grace_period = strategy.get("grace_period", 30)
            max_timeout = cmd.params.get("timeout", strategy.get("timeout", 600))
            check_process = strategy.get("check_process", True)
            check_log_completed = strategy.get("check_log_completed", [])

            # 远程命令：通过 SSH 读取结果
            if not self.is_local and self.ssh_target:
                if self._remote_poll_result(cmd):
                    return cmd.status

            # 本机命令：优先读统一结果文件（mc/engine.py 写入）
            if self.is_local:
                _result_file = AGENT_LOCAL / "runtime" / "results" / f"{cmd.run_id}.json"
                if _result_file.exists():
                    try:
                        _data = json.loads(_result_file.read_text())
                        cmd.result = _data
                        s = _data.get("status", "running")
                        if s == "completed":
                            cmd.status = CommandStatus.COMPLETED
                            cmd.message = _data.get("message", "执行完成")
                            cmd.completed_at = time.time()
                        elif s == "failed":
                            cmd.status = CommandStatus.FAILED
                            cmd.message = _data.get("error", _data.get("message", "执行失败"))
                            cmd.completed_at = time.time()
                        elif s == "crashed":
                            cmd.status = CommandStatus.CRASHED
                            cmd.message = _data.get("error", "进程崩溃")
                            cmd.completed_at = time.time()
                        elif s == "cancelled":
                            cmd.status = CommandStatus.CANCELLED
                            cmd.completed_at = time.time()
                        else:
                            cmd.status = CommandStatus.RUNNING
                            steps = _data.get("steps", {})
                            cmd.message = f"运行中 (已完成 {steps.get('success', 0)}/{steps.get('total', '?')} 步)"
                        return cmd.status
                    except:
                        pass

                # 兼容旧路径: runtime/nurture/results/
                if cmd.cmd_type == "nurture":
                    result_dir = AGENT_LOCAL / "runtime" / "nurture" / "results"
                    result_file = result_dir / f"{cmd.run_id}.json"
                    if result_file.exists():
                        try:
                            data = json.loads(result_file.read_text())
                            s = data.get("status", "running")
                            cmd.result = data
                            if s == "completed":
                                cmd.status = CommandStatus.COMPLETED
                                cmd.completed_at = time.time()
                            elif s == "failed":
                                cmd.status = CommandStatus.FAILED
                                cmd.completed_at = time.time()
                            else:
                                cmd.status = CommandStatus.RUNNING
                                steps = data.get("steps", {})
                                cmd.message = f"运行中 (已完成 {steps.get('success', 0)}/{steps.get('total', '?')} 步)"
                            return cmd.status
                        except:
                            pass

            # 根据策略决定是否检测进程存活
            alive = False
            if check_process:
                alive = self._is_alive(cmd)
                if alive:
                    cmd.status = CommandStatus.RUNNING
                    cmd.message = "进程运行中"
                    return cmd.status
            else:
                # check_process=False：不依赖进程存活判断（login/logout 快速命令）
                # 检查日志中是否有完成标记
                if check_log_completed and cmd.log_path and cmd.log_path.exists():
                    log_text = cmd.log_path.read_text(encoding="utf-8", errors="replace")
                    for marker in check_log_completed:
                        if marker in log_text:
                            cmd.status = CommandStatus.COMPLETED
                            cmd.message = f"检测到完成标记: {marker}"
                            cmd.completed_at = time.time()
                            return cmd.status

            elapsed = cmd.elapsed_sec
            if elapsed < grace_period:
                cmd.status = CommandStatus.RUNNING
                cmd.message = f"{'远程' if not self.is_local else ''}进程启动中 ({int(elapsed)}s/{grace_period}s)"
                return cmd.status

            if elapsed > max_timeout:
                cmd.status = CommandStatus.TIMED_OUT
                cmd.message = f"执行超时 ({int(elapsed)}s > {max_timeout}s)"
                cmd.completed_at = time.time()
                return cmd.status

            if cmd.log_path and cmd.log_path.exists():
                tail = cmd.log_path.read_text().strip()
                if tail:
                    cmd.status = CommandStatus.COMPLETED
                    cmd.message = "进程已结束，无异常"
                    cmd.completed_at = time.time()
                    return cmd.status

            # 远程：检查是否有任何输出（即使进程已退出）
            if not self.is_local and self.ssh_target:
                try:
                    r = subprocess.run(
                        ["ssh", "-o", "ConnectTimeout=5", self.ssh_target,
                         f"cat /tmp/ops_{cmd.run_id}.log 2>/dev/null | wc -c"],
                        capture_output=True, text=True, timeout=5
                    )
                    if r.returncode == 0 and r.stdout.strip().isdigit() and int(r.stdout.strip()) > 0:
                        cmd.status = CommandStatus.COMPLETED
                        cmd.message = "远程进程已完成"
                        cmd.completed_at = time.time()
                        return cmd.status
                except:
                    pass

            cmd.status = CommandStatus.CRASHED
            cmd.message = "进程已消失，无输出"
            cmd.completed_at = time.time()
            return cmd.status

    def _is_alive(self, cmd: Command) -> bool:
        if self.is_local:
            if cmd.pid:
                try:
                    os.kill(cmd.pid, 0)
                    return True
                except OSError:
                    return False
            return False
        if self.ssh_target:
            # 先按 run_id 查（log 文件重定向包含 run_id）
            patterns = [cmd.run_id]
            # 再按进程名查（实际进程可能不包含 run_id）
            type_patterns = {
                "collect": ["mc run.*douyin_read_profile", "mc run.*xiaohongshu_read_profile"],
                "nurture": ["mc run", "camoufox.*-no-remote"],
                "login": ["smart-login", "mc smart-login"],
                "comment": ["task comment", "mc task"],
                "like": ["mc task like"],
            }
            patterns.extend(type_patterns.get(cmd.cmd_type, []))
            try:
                for p in patterns:
                    r = subprocess.run(
                        ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
                         self.ssh_target, f"pgrep -f '{p}'"],
                        capture_output=True, text=True, timeout=8
                    )
                    if r.returncode == 0:
                        return True
            except:
                pass
        return False

    def cancel(self, cmd: Command) -> dict:
        with self._lock:
            if cmd.status.is_terminal:
                return {"error": "命令已结束"}

            # 杀掉进程 + 清理浏览器
            if self.is_local and cmd.pid:
                try:
                    os.kill(cmd.pid, 15)
                    time.sleep(0.5)
                    os.kill(cmd.pid, 9)
                except:
                    pass
                # 清理残留 Camoufox 进程（所有账号）
                for aid in cmd.accounts:
                    try:
                        subprocess.run(["pkill", "-f", aid], capture_output=True, timeout=3)
                    except:
                        pass
            elif not self.is_local and self.ssh_target:
                try:
                    subprocess.run(
                        ["ssh", self.ssh_target, f"pkill -f '{cmd.run_id}' 2>/dev/null"],
                        capture_output=True, text=True, timeout=5
                    )
                except:
                    pass

            cmd.status = CommandStatus.CANCELLED
            cmd.message = "用户取消"
            cmd.completed_at = time.time()

            # 如果是当前正在执行的命令 → 启动下一条
            if self.current_cmd is cmd:
                self._start_next()

            return {"ok": True}

    def _cleanup_zombies(self):
        """清理僵尸进程：进程已死但状态未更新的命令"""
        for cmd in self.commands[:]:
            if cmd.status.is_active:
                if not self._is_alive(cmd):
                    if cmd.log_path and cmd.log_path.exists() and cmd.log_path.stat().st_size > 0:
                        cmd.status = CommandStatus.COMPLETED
                        cmd.message = "进程已结束"
                    else:
                        cmd.status = CommandStatus.CRASHED
                        cmd.message = "进程已消失"
                    cmd.completed_at = time.time()

        # 命令刚完成 → 启动队列下一条
        if cmd.status.is_terminal and self.current_cmd is cmd:
            self._start_next()

    def _start_next(self):
        """当前命令完成后，启动队列中的下一条"""
        self.current_cmd = None
        if self.queued_cmds:
            next_cmd = self.queued_cmds.pop(0)
            logger.info(f"  ⏩ 启动队列下一条: {next_cmd.run_id} ({next_cmd.cmd_type})")
            if self.is_local:
                r = self._send_local(next_cmd)
            else:
                r = self._send_remote(next_cmd)
            if "error" not in r:
                self.current_cmd = next_cmd

    def _trim_history(self):
        while len(self.commands) > self.max_history:
            self.commands.pop()

    def get_active_commands(self) -> list[Command]:
        return [c for c in self.commands if c.status.is_active]

    def get_queue_info(self) -> dict:
        """返回队列状态"""
        return {
            "busy": self.is_busy,
            "current_run_id": self.current_cmd.run_id if self.current_cmd else None,
            "current_type": self.current_cmd.cmd_type if self.current_cmd else None,
            "current_status": self.current_cmd.status.value if self.current_cmd else None,
            "queued_count": len(self.queued_cmds),
            "queued": [{"run_id": c.run_id, "type": c.cmd_type, "accounts": c.accounts}
                       for c in self.queued_cmds],
        }

    def get_recent_commands(self, limit: int = 20) -> list[dict]:
        return [c.to_dict() for c in self.commands[:limit]]


# ── 操作注册表（统一 cmd_type → 命令模板映射）───────────────
# 本注册表是整个系统通往执行层的唯一映射表。
# 新增操作类型只需在这里加一行，不需要改 dispatch 逻辑。
#
# 注册表字段说明:
#   template        — 命令模板，用 {ids} {blueprint} {rounds} 等变量渲染
#   defaults        — 参数默认值（前端不传 params 时使用）
#   auto_blueprint  — 是否根据账号 platform 字段自动选择采集蓝图
#   blueprint_map   — platform → blueprint 映射表
#   runner          — shell 包装器路径（nurture 专用）
#   single_account  — 是否一次只处理一个账号
#   required_params — 必填参数列表（缺失则报错）
#
# 前端调用示例:
#   POST /api/ops/run {type:'collect', accounts:['douyin_01'], params:{rounds:1}}
#   → CMD_REGISTRY["collect"] → "mc run --accounts=douyin_01 --blueprints=douyin_read_profile --rounds=1"
CMD_REGISTRY = {
    "nurture": {
        "runner": "nurture_runner.sh",            # shell 包装器
        "defaults": {"blueprint": "douyin_daily", "rounds": 10},
        "auto_blueprint": False,
    },
    "collect": {
        "template": "mc run --accounts={ids} --blueprints={blueprint} --rounds={rounds}",
        "defaults": {"rounds": 1},
        "auto_blueprint": True,
        "blueprint_map": {
            "douyin": "douyin_read_profile",
            "xiaohongshu": "xiaohongshu_read_profile",
        },
    },
    "login": {
        "template": "mc smart-login {ids}",
        "single_account": True,
    },
    "logout": {
        "template": "mc run --accounts={ids} --blueprints=douyin_daily --rounds=1 --engine=auto",
    },
    "comment": {
        "template": "mc task comment --account={ids} --url={url} --direction={direction}",
        "required_params": ["url"],
    },
    "like": {
        "template": "mc run --accounts={ids} --blueprints=douyin_daily --rounds=1",
    },
    "interact": {
        "template": "mc run --accounts={ids} --blueprints={blueprint} --rounds=1",
        "defaults": {"blueprint": "interact_comment", "rounds": 1},
        "required_params": ["url"],
    },
}


# ── 命令轮询策略（按 cmd_type 设定不同的超时/检测方式）────────
# 解决：登录进程退出后 poll 不知道它已完成的问题
CMD_POLL_STRATEGY = {
    "login": {
        "grace_period": 15,       # 登录通常15秒内完成启动
        "timeout": 120,            # 登录超时2分钟
        "check_process": False,    # smart-login 启动浏览器后进程退出
        "check_log_completed": ["登录成功", "SMS验证码已发送", "浏览器已打开"],
    },
    "collect": {
        "grace_period": 30,
        "timeout": 600,
        "check_process": True,
        "check_log_completed": ["📊 执行完成", "✅ 采集完成"],
    },
    "nurture": {
        "grace_period": 60,
        "timeout": 1800,
        "check_process": True,
        "check_log_completed": ["📊 执行完成", "✅ 全部"],
    },
    "comment": {
        "grace_period": 20,
        "timeout": 300,
        "check_process": True,
        "check_log_completed": ["评论已发送", "✅ 完成"],
    },
    "like": {
        "grace_period": 20,
        "timeout": 300,
        "check_process": True,
        "check_log_completed": ["✅ 执行完成"],
    },
    "logout": {
        "grace_period": 15,
        "timeout": 120,
        "check_process": False,
        "check_log_completed": ["已退出"],
    },
}
DEFAULT_POLL_STRATEGY = {"grace_period": 30, "timeout": 600, "check_process": True, "check_log_completed": []}


# ── 命令总线 ────────────────────────────────────────────────
class CommandBus:
    """全局命令总线 — 所有操作的统一入口"""

    @classmethod
    def dispatch(cls, cmd_type: str, accounts: list, params: dict = None, wait: bool = False) -> dict:
        """主入口：按机器分组后分发
        之前: 每个账号一条命令
        现在: 每台机器一条命令（含多个账号）
        """
        params = params or {}
        force_machine = params.get("machine", "")
        dry_run = params.get("dry_run", False)
        now_ts = int(time.time())

        # ── 前置校验 ──
        if not cmd_type:
            return {"status": "error", "message": "type 必填 (login/logout/nurture/comment/like/collect)", "errors": [{"message": "type 必填"}]}
        if not accounts:
            return {"status": "error", "message": "accounts 必填 (至少一个账号ID)", "errors": [{"message": "accounts 为空"}]}
        if not isinstance(accounts, list):
            accounts = [accounts]

        # 获取所有账号信息
        try:
            from matrix_mgmt import MatrixManager
            mgr = MatrixManager()
            all_accts = {a["id"]: a for a in mgr.list_accounts()}
        except Exception as e:
            return {"status": "error", "message": f"加载账号失败: {e}", "errors": [{"message": str(e)}]}

        # ── 加载 ORACLE 宪法（账号→机器映射表）──
        oracle_map = {}  # account_id → assigned_machine
        try:
            oracle_path = AGENT_SYNC / "ORACLE.yaml"
            if oracle_path.exists():
                import yaml
                oracle = yaml.safe_load(oracle_path.read_text())
                for entry in oracle.get("accounts", []):
                    machine = entry.get("machine", "")
                    for plat, acct_id in entry.get("platforms", {}).items():
                        oracle_map[acct_id] = machine
        except:
            pass  # ORACLE 文件不存在时不阻断执行

        # ── 逐个账号校验 ──
        errors = []
        warnings = []
        machine_groups = {}
        for aid in accounts:
            acct = all_accts.get(aid) if isinstance(aid, str) else aid
            if not acct:
                errors.append({"account": str(aid), "message": "账号不存在"})
                continue
            machine = force_machine or acct.get("owner_machine", "")
            if not machine:
                errors.append({"account": aid, "message": f"账号 {aid} 未分配机器 (owner_machine 为空)"})
                continue
            # ORACLE 合规检查
            oracle_machine = oracle_map.get(aid)
            if oracle_machine and oracle_machine != machine:
                warnings.append({"account": aid, "message": f"账号 {aid} 按 ORACLE 应在机器 {oracle_machine}，实际发往 {machine}"})
            elif not oracle_machine:
                warnings.append({"account": aid, "message": f"账号 {aid} 未在 ORACLE 登记，建议 git pull 同步后执行 fleet_reconcile"})
            if machine not in machine_groups:
                machine_groups[machine] = []
            machine_groups[machine].append(acct)

        results = []

        # 第二步：按机器分组构建命令任务
        # 返回 list[dict] = {machine, cmd_type, ids_str, is_local, cmd_line, params, run_id}
        tasks = []
        for machine, accts in machine_groups.items():
            is_local = (machine == HOSTNAME)
            all_ids = ",".join(a["id"] for a in accts)

            if cmd_type == "nurture":
                plat_groups = {}
                for a in accts:
                    p = a.get("platform", "douyin")
                    plat_groups.setdefault(p, []).append(a)
                for platform, plat_accts in plat_groups.items():
                    ids_str = ",".join(a["id"] for a in plat_accts)
                    bp = params.get("blueprint") or {"douyin": "douyin_daily", "xiaohongshu": "xhs_daily"}.get(platform, "douyin_daily")
                    r = params.get("rounds", 10)
                    tasks.append({
                        "machine": machine, "cmd_type": cmd_type,
                        "ids_str": ids_str, "is_local": is_local,
                        "cmd_line": f"mc run --accounts={ids_str} --blueprints={bp} --rounds={r} --mix --interval=45-90",
                        "run_id": f"{cmd_type}_{now_ts}_{machine}_{platform}",
                    })
            else:
                # 从操作注册表读取模板
                cmd_config = CMD_REGISTRY.get(cmd_type)
                if not cmd_config:
                    errors.append({"account": all_ids, "message": f"不支持的操作: {cmd_type}"})
                    continue

                template = cmd_config.get("template", "")
                defaults = cmd_config.get("defaults", {})
                auto_bp = cmd_config.get("auto_blueprint", False)
                bp_map = cmd_config.get("blueprint_map", {})

                # 合并参数：params 覆盖 defaults
                merged = dict(defaults)
                merged.update(params)

                # Auto-blueprint: 根据账号平台自动选择采集蓝图（多平台用逗号分隔）
                if auto_bp and not merged.get("blueprint"):
                    platforms = set(a.get("platform", "douyin") for a in accts)
                    bp_list = [bp_map.get(p, "douyin_read_profile") for p in sorted(platforms)]
                    merged["blueprint"] = ",".join(bp_list)

                # 模板渲染：安全处理，缺失的模板变量用空字符串代替
                try:
                    cmd_line = template.format(ids=all_ids, ids_str=all_ids, **merged)
                except KeyError:
                    # 兼容旧代码：对 comment 等类型，缺失变量用空字符串
                    safe_kw = {k: merged.get(k, "") for k in
                              [p[1] for p in __import__("string").Formatter().parse(template) if p[1]]}
                    safe_kw.update({"ids": all_ids, "ids_str": all_ids})
                    cmd_line = template.format(**safe_kw)
                if not cmd_line:
                    errors.append({"account": all_ids, "message": f"不支持的操作: {cmd_type}"})
                    continue
                tasks.append({
                    "machine": machine, "cmd_type": cmd_type,
                    "ids_str": all_ids, "is_local": is_local,
                    "cmd_line": cmd_line,
                    "run_id": f"{cmd_type}_{now_ts}_{machine}",
                })

        # 第三步：并行分发到各台机器
        dispatched_cmds = []
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _do_send(t):
            return cls._execute_one(
                t["cmd_type"], t["ids_str"], t["machine"],
                t["is_local"], t["cmd_line"], params,
                t["run_id"], results, errors, dry_run
            )

        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = [ex.submit(_do_send, t) for t in tasks]
            for f in as_completed(futures):
                try:
                    cmd = f.result()
                    if cmd:
                        dispatched_cmds.append(cmd)
                except Exception as e:
                    logger.error(f"并行分发异常: {e}")

        # 第四步：等待执行结果（仅 wait=True 时）
        per_machine = {}
        if wait and dispatched_cmds:
            deadline = time.time() + params.get("timeout", 600)
            while time.time() < deadline:
                all_terminal = True
                for cmd in dispatched_cmds:
                    session = MachineSession.get(cmd.machine)
                    session.poll(cmd)
                    if not cmd.status.is_terminal:
                        all_terminal = False
                if all_terminal:
                    break
                time.sleep(15)

            # 聚合每台机器结果
            for cmd in dispatched_cmds:
                m = cmd.machine
                if m not in per_machine:
                    per_machine[m] = {"accounts": [], "status": "running",
                                       "success": 0, "failed": 0, "duration": 0}
                per_machine[m]["accounts"].extend(cmd.accounts)
                per_machine[m]["status"] = cmd.status.value
                per_machine[m]["duration"] = max(per_machine[m]["duration"], cmd.elapsed_sec)
                result_data = cmd.result or {}
                steps = result_data.get("steps", {}) or {}
                per_machine[m]["success"] += steps.get("success", 0) if steps else 0
                per_machine[m]["failed"] += steps.get("failed", 0) if steps else 0

            # 若全部完成则标记总状态
            all_terminal = all(cmd.status.is_terminal for cmd in dispatched_cmds)
            for m in per_machine:
                per_machine[m]["status"] = per_machine[m]["status"] if all_terminal else "running"

        total_success = sum(pm["success"] for pm in per_machine.values())
        total_failed = sum(pm["failed"] for pm in per_machine.values())
        total_accounts = sum(len(pm["accounts"]) for pm in per_machine.values())

        return {
            "status": "completed" if (wait and all_terminal) else ("accepted" if not dry_run else "plan"),
            "total_accounts": total_accounts or None,
            "total_success": total_success or None,
            "total_failed": total_failed or None,
            "commands": results,
            "per_machine": per_machine if per_machine else None,
            "errors": errors if errors else None,
            "warnings": warnings if warnings else None,
        }

    @classmethod
    def _execute_one(cls, cmd_type, ids_str, machine, is_local, cmd_line, params, run_id, results, errors, dry_run):
        """执行单条命令，返回 Command 对象（供调用方追踪结果）"""
        acct_ids = ids_str.split(",")
        if dry_run:
            results.append({
                "accounts": acct_ids, "account": ids_str,
                "machine": machine, "is_local": is_local, "command": cmd_line,
            })
            return None

        cmd = Command(
            cmd_type=cmd_type, accounts=acct_ids, machine=machine,
            command_line=cmd_line, run_id=run_id, params=params
        )

        session = MachineSession.get(machine)
        cmd.status = CommandStatus.PREFLIGHTING
        pf = session.preflight()
        if not pf["ok"]:
            cmd.status = CommandStatus.PREFLIGHT_FAILED
            cmd.message = pf["message"]
            errors.append({"account": ids_str, "message": pf["message"]})
            results.append(cmd.to_dict())
            return cmd

        for a in acct_ids:
            session.graceful_exit(a)

        session.send(cmd)
        results.append(cmd.to_dict())
        return cmd

    @classmethod
    def get_status(cls, machine: str = None, account: str = None) -> list[dict]:
        results = []
        for m_name, session in MachineSession._sessions.items():
            if machine and m_name != machine:
                continue
            for c in session.commands:
                if account and account not in c.accounts:
                    continue
                session.poll(c)
                results.append(c.to_dict())
        return results

    @classmethod
    def cancel(cls, run_id: str) -> dict:
        for session in MachineSession._sessions.values():
            for c in session.commands:
                if c.run_id == run_id:
                    return session.cancel(c)
        return {"error": f"未找到命令: {run_id}"}

    @classmethod
    def get_machine_status(cls, machine: str) -> dict:
        session = MachineSession.get(machine)
        active = session.get_active_commands()
        from services.browser_orchestrator import check_running_browsers
        browsers = check_running_browsers(machine)
        return {
            "machine": machine,
            "is_local": session.is_local,
            "active_commands": len(active),
            "browsers_running": len(browsers),
            "browser_list": browsers,
            "reachable": session.ssh_target is not None or session.is_local,
            "queue": session.get_queue_info(),
        }

    @classmethod
    def get_all_machines_status(cls) -> dict:
        from services.browser_orchestrator import check_running_browsers
        machines = {}
        for m_name in list(MachineSession._sessions.keys()):
            machines[m_name] = cls.get_machine_status(m_name)
        if HOSTNAME not in machines:
            machines[HOSTNAME] = cls.get_machine_status(HOSTNAME)
        try:
            import yaml
            oracle = yaml.safe_load(ORACLE_PATH.read_text())
            for m_name in oracle.get("machines", {}):
                if m_name not in machines:
                    machines[m_name] = {"machine": m_name, "is_local": False,
                        "active_commands": 0, "browsers_running": 0,
                        "browser_list": [], "reachable": False}
        except:
            pass
        return {"machines": machines}


# ── Poll 守卫线程（自动轮询所有活跃命令）───────────────────
# 每15秒检查一次，防止远程命令卡在 running 状态
def _start_poll_guard():
    """后台守护线程：自动轮询所有活跃命令的状态"""
    def _loop():
        while True:
            time.sleep(15)
            try:
                for name, session in list(MachineSession._sessions.items()):
                    if session.current_cmd and not session.current_cmd.status.is_terminal:
                        old_status = session.current_cmd.status.value
                        new_status = session.poll(session.current_cmd)
                        if old_status != new_status.value:
                            logger.info(f"  ⏱ poll守卫: {session.current_cmd.run_id[:30]} {old_status} → {new_status.value}")
            except Exception:
                pass
    thread = threading.Thread(target=_loop, name="poll-guard", daemon=True)
    thread.start()
    logger.info("  ✅ Poll 守卫线程已启动 (15s周期)")

_start_poll_guard()


def cleanup_stale_commands() -> int:
    """清理所有僵尸命令：进程已死但状态为 running 的标记为 CRASHED"""
    count = 0
    for name, session in MachineSession._sessions.items():
        for cmd in session.commands:
            if cmd.status.is_active:
                # 先 poll 一下看能否自动判定
                session.poll(cmd)
                if cmd.status.is_active:
                    strategy = CMD_POLL_STRATEGY.get(cmd.cmd_type, DEFAULT_POLL_STRATEGY)
                    gp = strategy.get("grace_period", 30)
                    if cmd.elapsed_sec > (gp + 5):
                        cmd.status = CommandStatus.CRASHED
                        cmd.message = "僵尸清理: 进程已消失"
                        cmd.completed_at = time.time()
                        count += 1
                        logger.info(f"  🧹 清理僵尸: {cmd.run_id[:30]} ({cmd.cmd_type})")
        # 如果当前命令被清理了，启动下一条
        if session.current_cmd and session.current_cmd.status.is_terminal:
            session._start_next()
    return count

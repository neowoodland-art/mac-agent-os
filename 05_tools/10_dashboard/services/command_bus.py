"""
command_bus.py — 统一命令传输层 v5

核心变更 v5: 按机器分组，每台机器只发一条命令（含多个账号）
  之前: 每个账号一条命令
  现在: 每台机器一条命令，accounts=["a","b","c"] 批量参数
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

def _resolve_hostname() -> str:
    cached = AGENT_LOCAL / "identity" / "cached_hostname"
    if cached.exists():
        return cached.read_text().strip()
    return os.uname().nodename

HOSTNAME = _resolve_hostname()

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
    """单台机器的命令执行会话"""

    _sessions = {}

    def __init__(self, machine: str):
        self.machine = machine
        self.is_local = (machine == HOSTNAME)
        self.commands: list[Command] = []
        self.max_history = 50
        self._lock = threading.Lock()
        self.machine_info = _get_machine_info(machine) if not self.is_local else {}
        self.ssh_target = None
        if not self.is_local and self.machine_info.get("ip"):
            u = self.machine_info.get("user", "")
            self.ssh_target = f"{u}@{self.machine_info['ip']}" if u else self.machine_info["ip"]

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
            if self.is_local:
                return self._send_local(cmd)
            else:
                return self._send_remote(cmd)

    # 并发上限（统一来自 mc.execution_policy）
    MAX_ACTIVE_PROCESSES = 3

    def _send_local(self, cmd: Command) -> dict:
        # 系统级进程数检查（查实际 mc 进程，不依赖内存状态）
        try:
            mc_count = int(subprocess.run(
                ["pgrep", "-f", "python3.*-m mc"], capture_output=True, text=True, timeout=3
            ).stdout.strip() or "0") or 0
            if mc_count > 600:  # 系统级警戒线：每个mc task约210子进程(浏览器引擎)
                subprocess.run(["pkill", "-f", "python3.*-m mc"], capture_output=True, timeout=3)
                time.sleep(1)
                return {"error": f"系统 mc 进程数过高 ({mc_count})，已自动清理，请重试"}
        except:
            pass

        # 浏览器并发预检（统一通道，仅在需要浏览器的操作时）
        if cmd.cmd_type in ('nurture', 'collect', 'login', 'comment', 'like'):
            try:
                from mc.execution_policy import preflight as _browser_preflight
                _pf = _browser_preflight()
                if not _pf["ok"]:
                    logger.warning(f"浏览器预检未通过: {_pf['message']}")
                    return {"error": _pf["message"], "policy": _pf}
            except:
                pass

        # 限制并发进程数
        active_count = len([c for c in self.commands if c.status.is_active])
        if active_count >= self.MAX_ACTIVE_PROCESSES:
            # 先清理最老的 zombie
            self._cleanup_zombies()
            active_count = len([c for c in self.commands if c.status.is_active])
            if active_count >= self.MAX_ACTIVE_PROCESSES:
                return {"error": f"并发进程数已达上限 ({active_count}/{self.MAX_ACTIVE_PROCESSES})，请等待当前任务完成"}

        scripts_dir = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts"
        log_dir = AGENT_LOCAL / "runtime" / "commands"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{cmd.run_id}.log"
        cmd.log_path = log_path
        log_fh = open(log_path, "w")

        if cmd.cmd_type == "nurture":
            wrapper = str(AGENT_SYNC / "05_tools" / "10_dashboard" / "services" / "nurture_runner.sh")
            accts = ",".join(cmd.accounts)
            bp = cmd.params.get("blueprint", "douyin_daily")
            rounds = cmd.params.get("rounds", 10)
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
            wrapper_cmd = f"bash $AGENT_SYNC/05_tools/10_dashboard/services/nurture_runner.sh {accts} {cmd.params.get('blueprint','douyin_daily')} {cmd.params.get('rounds',10)} {cmd.run_id}"
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
                check = f"cat $AGENT_LOCAL/runtime/commands/{cmd.run_id}.json 2>/dev/null; cat /tmp/ops_{cmd.run_id}.log 2>/dev/null"
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

            # 远程命令：通过 SSH 读取结果
            if not self.is_local and self.ssh_target:
                if self._remote_poll_result(cmd):
                    return cmd.status

            # 本机命令：读本地 result 文件
            if self.is_local:
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

            alive = self._is_alive(cmd)
            if alive:
                cmd.status = CommandStatus.RUNNING
                cmd.message = "进程运行中"
                return cmd.status

            elapsed = cmd.elapsed_sec
            # 远程命令需要更长等待时间（SSH + 进程启动开销）
            grace_period = 30 if not self.is_local else 5
            if elapsed < grace_period:
                cmd.status = CommandStatus.RUNNING
                cmd.message = f"{'远程' if not self.is_local else ''}进程启动中 ({int(elapsed)}s/{grace_period}s)"
                return cmd.status

            max_timeout = cmd.params.get("timeout", 600)
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
            if self.is_local and cmd.pid:
                try:
                    os.kill(cmd.pid, 15)
                    time.sleep(0.5)
                    os.kill(cmd.pid, 9)
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

    def _trim_history(self):
        while len(self.commands) > self.max_history:
            self.commands.pop()

    def get_active_commands(self) -> list[Command]:
        return [c for c in self.commands if c.status.is_active]

    def get_recent_commands(self, limit: int = 20) -> list[dict]:
        return [c.to_dict() for c in self.commands[:limit]]


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

        # ── 执行策略预检（统一通道：浏览器数/磁盘/槽位）──
        try:
            scripts_dir = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts"
            sys.path.insert(0, str(scripts_dir))
            from mc.execution_policy import preflight as _policy_preflight
            _pf = _policy_preflight()
            if not _pf["ok"]:
                return {"status": "error", "message": _pf["message"],
                        "policy": _pf, "errors": [{"message": _pf["message"]}]}
        except ImportError:
            pass  # 策略模块不可用时不阻断
        except Exception:
            pass

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
                templates = {
                    "collect": "mc run --accounts={ids_str} --blueprints=douyin_read_profile --rounds=1",
                    "login": f"mc smart-login {all_ids} --skip-check",
                    "logout": f"mc run --accounts={all_ids} --blueprints=douyin_daily --rounds=1 --engine=auto",
                    "comment": f"mc task comment --account={all_ids} --url={params.get('url','')} -y" + (f" --direction={params.get('direction','')}" if params.get('direction') else ""),
                    "like": f"mc run --accounts={all_ids} --blueprints=douyin_daily --rounds=1",
                }
                cmd_line = templates.get(cmd_type, "")
                if cmd_type == "collect":
                    cmd_line = cmd_line.replace("{ids_str}", all_ids)
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

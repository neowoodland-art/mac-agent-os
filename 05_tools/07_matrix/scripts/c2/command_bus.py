#!/usr/bin/env python3
"""
command_bus.py — AgentOS 联邦命令总线 v1.0

三通道自动降级:
  通道A (HTTP直连) → 通道B (Git异步) → 通道C (事件日志)

用法:
  from c2.command_bus import CommandBus
  bus = CommandBus()
  result = bus.send("5kechengdeAir", "nurture_run", {"accounts":["douyin_01"], "rounds":10})
  
版本: 1.0.0 | 更新: 2026-05-31
"""
import json, os, time, uuid, subprocess, socket, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

HOME = Path.home()
AGENT_SYNC = HOME / "workbuddy-agent-os" / "agent-sync"
AGENT_LOCAL = HOME / "workbuddy-agent-os" / "agent-local"

# ── 路径常量 ──────────────────────────────────────────────
CROSS_MACHINE = AGENT_SYNC / "04_memory" / "cross_machine"
DIR_TASKS_PENDING = CROSS_MACHINE / "tasks" / "pending"
DIR_TASKS_COMPLETED = CROSS_MACHINE / "tasks" / "completed"
DIR_MACHINES = CROSS_MACHINE / "machines"
CMD_LOG_DIR = AGENT_LOCAL / "runtime" / "c2"

# ── 已知机器映射 (hostname → IP:port) ────────────────────
# 同一局域网下可直接 HTTP 访问，不在网络时走 Git
MACHINE_ENDPOINTS: dict[str, str] = {
    "chengzigedeAir": "192.168.31.225:9988",
    "5kechengdeAir":  "192.168.31.172:9988",
    "7kecheng":       "192.168.31.95:9988",
}


class CommandBus:
    """联邦命令总线——跨机器命令分发与执行"""

    # ── 命令类型注册表 ────────────────────────────────────
    COMMAND_TYPES = {
        "nurture_run": {
            "label": "启动养号",
            "target_required": True,
            "params": ["accounts", "rounds", "blueprint"],
        },
        "nurture_stop": {
            "label": "停止养号",
            "target_required": True,
            "params": ["accounts"],
        },
        "check_environment": {
            "label": "环境检查",
            "target_required": True,
            "params": [],
        },
        "refresh_profiles": {
            "label": "刷新资料",
            "target_required": True,
            "params": ["accounts"],
        },
        "sync_only": {
            "label": "仅同步",
            "target_required": False,
            "params": [],
        },
        "run_script": {
            "label": "执行脚本",
            "target_required": True,
            "params": ["script", "args"],
        },
    }

    def __init__(self):
        self._local_uid = self._resolve_uid()
        self._local_hostname = self._resolve_hostname()
        CMD_LOG_DIR.mkdir(parents=True, exist_ok=True)
        DIR_TASKS_PENDING.mkdir(parents=True, exist_ok=True)
        DIR_TASKS_COMPLETED.mkdir(parents=True, exist_ok=True)

    # ═══════════════════════════════════════════════════════
    # 对外接口
    # ═══════════════════════════════════════════════════════

    def send(self, target: str, command_type: str,
             params: dict = None, schedule_at: str = None) -> dict:
        """发送命令到目标机器

        Args:
            target: 目标机器 hostname
            command_type: 命令类型 (见 COMMAND_TYPES)
            params: 命令参数
            schedule_at: ISO 8601 定时执行 (可选)

        Returns:
            {"status": "ok"|"queued"|"error", "command_id": "...", "channel": "http"|"git", ...}
        """
        if command_type not in self.COMMAND_TYPES:
            return {"status": "error", "error": f"未知命令类型: {command_type}"}

        cmd_id = str(uuid.uuid4())
        command = {
            "command_id": cmd_id,
            "type": command_type,
            "target_machine": target,
            "source_machine": self._local_hostname,
            "source_uid": self._local_uid,
            "params": params or {},
            "schedule_at": schedule_at,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }

        # 如果指定了定时执行，直接走 Git 通道
        if schedule_at:
            return self._route_via_git(command)

        # 通道A: 尝试 HTTP 直连
        if target != self._local_hostname:
            result = self._route_via_http(command)
            if result.get("status") != "unreachable":
                return result

        # 通道B: Git 异步
        return self._route_via_git(command)

    def send_to_all(self, command_type: str, params: dict = None,
                    exclude_self: bool = True) -> dict:
        """向所有已知机器广播命令"""
        results = {}
        for machine in MACHINE_ENDPOINTS:
            if exclude_self and machine == self._local_hostname:
                continue
            results[machine] = self.send(machine, command_type, params)
        return results

    def check_status(self, command_id: str) -> Optional[dict]:
        """查询命令执行状态"""
        # 先查 completed
        for f in DIR_TASKS_COMPLETED.glob(f"{command_id}*.json"):
            try:
                return json.loads(f.read_text())
            except:
                pass
        # 再查 pending
        for f in DIR_TASKS_PENDING.glob(f"{command_id}*.json"):
            try:
                return json.loads(f.read_text())
            except:
                pass
        return None

    def list_recent_commands(self, limit: int = 20) -> list[dict]:
        """列出最近完成的命令"""
        results = []
        if DIR_TASKS_COMPLETED.exists():
            for f in sorted(DIR_TASKS_COMPLETED.iterdir(), reverse=True)[:limit]:
                if f.suffix == ".json":
                    try:
                        results.append(json.loads(f.read_text()))
                    except:
                        pass
        return results

    def list_pending_commands(self) -> list[dict]:
        """列出待处理的命令"""
        results = []
        if DIR_TASKS_PENDING.exists():
            for f in sorted(DIR_TASKS_PENDING.iterdir()):
                if f.suffix == ".json":
                    try:
                        results.append(json.loads(f.read_text()))
                    except:
                        pass
        return results

    # ═══════════════════════════════════════════════════════
    # 接收端 (由 Dashboard API / guardd 调用)
    # ═══════════════════════════════════════════════════════

    def receive_and_execute(self, command: dict) -> dict:
        """接收并执行命令 (由本地 Dashboard API 调用)"""
        cmd_type = command.get("type", "")
        if cmd_type not in self.COMMAND_TYPES:
            return self._fail(command, f"不支持的命令类型: {cmd_type}")

        # 更新状态
        command["status"] = "running"
        command["received_at"] = datetime.now(timezone.utc).isoformat()
        command["executed_by"] = self._local_hostname

        # 根据命令类型路由到执行器
        try:
            result = self._execute(command)
        except Exception as e:
            result = self._fail(command, str(e))

        # 写入完成目录
        self._write_completed(result)
        return result

    def ping(self) -> dict:
        """健康检查 (供远程机器调用)"""
        return {
            "status": "alive",
            "hostname": self._local_hostname,
            "uid": self._local_uid,
            "time": datetime.now(timezone.utc).isoformat(),
            "guardd_running": self._check_guardd(),
        }

    # ═══════════════════════════════════════════════════════
    # 通道实现
    # ═══════════════════════════════════════════════════════

    def _route_via_http(self, command: dict) -> dict:
        """通道A: HTTP 直连"""
        endpoint = MACHINE_ENDPOINTS.get(command["target_machine"])
        if not endpoint:
            return {"status": "unreachable", "error": f"未知机器: {command['target_machine']}"}

        url = f"http://{endpoint}/api/c2/command"
        try:
            payload = json.dumps(command).encode("utf-8")
            req = urllib.request.Request(url, data=payload,
                headers={"Content-Type": "application/json"},
                method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                data["_channel"] = "http"
                data["_latency_ms"] = round(resp.headers.get("X-Response-Time", 0))
                return data
        except (urllib.error.URLError, socket.timeout, ConnectionRefusedError) as e:
            return {"status": "unreachable", "error": str(e)[:100], "_channel": "http_failed"}

    def _route_via_git(self, command: dict) -> dict:
        """通道B: Git 异步写入 tasks/pending/"""
        cmd_file = DIR_TASKS_PENDING / f"{command['command_id']}.json"

        # 记录本机作为源
        command["_channel"] = "git"
        command["_delivery"] = "async"
        command["queued_at"] = datetime.now(timezone.utc).isoformat()

        cmd_file.write_text(
            json.dumps(command, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 触发 git push（如果 guardd 会做就不重复）
        self._try_git_push()

        self._log_event("command_queued", {
            "command_id": command["command_id"],
            "type": command["type"],
            "target": command["target_machine"],
        })

        return {
            "status": "queued",
            "command_id": command["command_id"],
            "_channel": "git",
            "message": f"命令已通过 Git 队列发送到 {command['target_machine']}",
        }

    def _execute(self, command: dict) -> dict:
        """执行命令 (路由到具体处理器)"""
        cmd_type = command["type"]
        params = command.get("params", {})

        if cmd_type == "check_environment":
            return self._exec_check_environment(command)
        elif cmd_type == "nurture_run":
            return self._exec_nurture_run(command, params)
        elif cmd_type == "nurture_stop":
            return self._exec_nurture_stop(command, params)
        elif cmd_type == "refresh_profiles":
            return self._exec_refresh_profiles(command, params)
        elif cmd_type == "sync_only":
            return self._exec_sync_only(command)
        elif cmd_type == "run_script":
            return self._exec_run_script(command, params)
        else:
            return self._fail(command, f"未实现处理器: {cmd_type}")

    # ═══════════════════════════════════════════════════════
    # 命令处理器
    # ═══════════════════════════════════════════════════════

    def _exec_check_environment(self, command: dict) -> dict:
        """检查本机环境"""
        result = {
            "hostname": self._local_hostname,
            "uid": self._local_uid,
            "guardd_running": self._check_guardd(),
            "camoufox_available": self._check_camoufox(),
            "proxy_running": self._check_proxy(),
            "matrix_accounts": self._count_matrix_accounts(),
            "disk_avail_gb": self._check_disk(),
            "uptime": self._get_uptime(),
        }
        return self._ok(command, result)

    def _exec_nurture_run(self, command: dict, params: dict) -> dict:
        """启动养号 (委托给 matrix_nurture)"""
        accounts = params.get("accounts", [])
        rounds = params.get("rounds", 5)
        blueprint = params.get("blueprint", "default")

        if not accounts:
            return self._fail(command, "未指定账号")

        # 委托给 matrix_nurture 脚本
        try:
            from matrix_modules.nurture_runner import run_nurture
            result = run_nurture(accounts, rounds, blueprint)
            return self._ok(command, {"accounts": accounts, "rounds": rounds, "result": result})
        except ImportError:
            # 降级: 调用 matrix.py CLI
            matrix_cli = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts" / "matrix.py"
            cmd = f"cd {matrix_cli.parent} && python3 {matrix_cli} nurture run -a {' -a '.join(accounts)} -r {rounds}"
            subprocess.Popen(cmd, shell=True)
            return self._ok(command, {"accounts": accounts, "rounds": rounds,
                                       "started": True, "method": "cli"})

    def _exec_nurture_stop(self, command: dict, params: dict) -> dict:
        """停止养号"""
        accounts = params.get("accounts", [])
        # 查找并终止 nurturer 进程
        killed = []
        for proc_file in Path("/tmp").glob("matrix_mgmt_nurture_*"):
            killed.append(str(proc_file.name))
            proc_file.unlink(missing_ok=True)
        return self._ok(command, {"stopped": True, "killed_processes": len(killed)})

    def _exec_refresh_profiles(self, command: dict, params: dict) -> dict:
        """刷新账号主页资料"""
        accounts = params.get("accounts", [])
        try:
            from c2.profile_scraper import ProfileScraper
            scraper = ProfileScraper()
            results = scraper.refresh(accounts) if accounts else scraper.refresh_all()
            return self._ok(command, {"refreshed": len(results), "details": results})
        except ImportError:
            return self._fail(command, "profile_scraper 模块未安装")

    def _exec_sync_only(self, command: dict) -> dict:
        """仅执行 Git 同步"""
        try:
            subprocess.run(["git", "pull"], capture_output=True, timeout=30,
                          cwd=str(AGENT_SYNC))
            return self._ok(command, {"synced": True})
        except Exception as e:
            return self._fail(command, str(e))

    def _exec_run_script(self, command: dict, params: dict) -> dict:
        """执行任意脚本 (安全受限)"""
        script = params.get("script", "")
        args = params.get("args", "")
        if not script:
            return self._fail(command, "未指定脚本")
        try:
            r = subprocess.run(script.split() + args.split(),
                             capture_output=True, text=True, timeout=120)
            return self._ok(command, {
                "returncode": r.returncode,
                "stdout": r.stdout[-1000:],
                "stderr": r.stderr[-500:],
            })
        except subprocess.TimeoutExpired:
            return self._fail(command, "脚本执行超时")
        except Exception as e:
            return self._fail(command, str(e))

    # ═══════════════════════════════════════════════════════
    # 辅助
    # ═══════════════════════════════════════════════════════

    def _ok(self, command: dict, data: dict) -> dict:
        return {
            **command,
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "output": data,
        }

    def _fail(self, command: dict, error: str) -> dict:
        return {
            **command,
            "status": "failed",
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "error": str(error),
        }

    def _write_completed(self, result: dict):
        path = DIR_TASKS_COMPLETED / f"{result['command_id']}.json"
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    def _log_event(self, event_type: str, payload: dict):
        try:
            from guardd import _write_machine_event
            _write_machine_event(event_type, payload)
        except ImportError:
            pass

    def _try_git_push(self):
        try:
            subprocess.run(["git", "add", "04_memory/cross_machine/tasks/"],
                         capture_output=True, timeout=10, cwd=str(AGENT_SYNC))
            r = subprocess.run(["git", "status", "--porcelain"],
                             capture_output=True, text=True, timeout=10, cwd=str(AGENT_SYNC))
            if r.stdout.strip():
                subprocess.run(["git", "commit", "-m",
                    f"c2: command {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
                    capture_output=True, timeout=15, cwd=str(AGENT_SYNC))
            subprocess.run(["git", "push"], capture_output=True, timeout=30, cwd=str(AGENT_SYNC))
        except:
            pass

    def _check_guardd(self) -> bool:
        try:
            r = subprocess.run(["launchctl", "list", "com.agentos.guardd"],
                             capture_output=True, text=True, timeout=5)
            return r.returncode == 0
        except:
            return False

    def _check_camoufox(self) -> bool:
        try:
            r = subprocess.run(["which", "camoufox"], capture_output=True, text=True, timeout=5)
            return bool(r.stdout.strip())
        except:
            return False

    def _check_proxy(self) -> bool:
        try:
            r = subprocess.run(["launchctl", "list", "com.agentos.socks5-forwarder"],
                             capture_output=True, text=True, timeout=5)
            return r.returncode == 0
        except:
            return False

    def _count_matrix_accounts(self) -> int:
        try:
            from matrix_mgmt import MatrixManager
            mgr = MatrixManager()
            return len(mgr.list_accounts())
        except:
            return 0

    def _check_disk(self) -> float:
        try:
            st = os.statvfs(str(HOME))
            return round(st.f_bavail * st.f_frsize / 1e9, 1)
        except:
            return 0

    def _get_uptime(self) -> float:
        try:
            with open("/proc/uptime") as f:
                return float(f.read().split()[0])
        except:
            return 0

    def _resolve_uid(self) -> str:
        uid_file = AGENT_LOCAL / "identity" / "machine_uid"
        if uid_file.exists():
            return uid_file.read_text().strip()
        return os.uname().nodename

    def _resolve_hostname(self) -> str:
        hn_file = AGENT_LOCAL / "identity" / "cached_hostname"
        if hn_file.exists():
            return hn_file.read_text().strip()
        return os.uname().nodename


# ═══════════════════════════════════════════════════════════
# CLI 入口（测试用）
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    bus = CommandBus()

    if len(sys.argv) < 2:
        print("用法: python command_bus.py <command> [target] [params_json]")
        print("示例: python command_bus.py check_environment 5kechengdeAir")
        print("      python command_bus.py nurture_run 5kechengdeAir '{\"accounts\":[\"douyin_01\"],\"rounds\":10}'")
        sys.exit(1)

    cmd_type = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else ""
    params = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}

    if cmd_type == "ping":
        result = bus.ping()
    elif cmd_type == "list":
        result = {"recent": bus.list_recent_commands(), "pending": bus.list_pending_commands()}
    elif target:
        result = bus.send(target, cmd_type, params)
    else:
        result = {"error": "需要指定目标机器"}

    print(json.dumps(result, indent=2, ensure_ascii=False))

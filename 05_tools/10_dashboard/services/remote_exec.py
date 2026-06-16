"""
远程执行引擎

通过 SSH 在远程机器执行命令，返回执行结果。
机器信息从 ORACLE.yaml 读取。
"""

import logging, subprocess, sys
from pathlib import Path

logger = logging.getLogger("dashboard.remote_exec")

_THIS_DIR = Path(__file__).resolve().parent.parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

ORACLE_PATH = _THIS_DIR.parent.parent / "ORACLE.yaml"
_MACHINE_CACHE = None


def _get_machine_info(machine_name: str) -> dict:
    """从 ORACLE 查找机器信息"""
    import yaml, os
    global _MACHINE_CACHE
    
    if not ORACLE_PATH.exists():
        return {}
    
    if _MACHINE_CACHE is None:
        with open(ORACLE_PATH) as f:
            _MACHINE_CACHE = yaml.safe_load(f)
    
    for name, info in _MACHINE_CACHE.get("machines", {}).items():
        if name == machine_name or info.get("hostname") == machine_name:
            return {
                "name": name,
                "hostname": info.get("hostname", name),
                "ip": info.get("tailscale_ip", ""),
                "user": info.get("ssh_user", ""),
            }
    return {}


def exec_remote(machine: str, command: str, timeout: int = 60, fire_and_forget: bool = False) -> dict:
    """在远程机器执行命令
    
    Args:
        machine: 机器名（对应 ORACLE 中的定义）
        command: 要执行的命令
        timeout: 超时秒数
        fire_and_forget: 是否立即返回（适合浏览器交互类命令）
    
    Returns:
        {"status": "ok"/"error", "stdout": "...", "stderr": "...", "returncode": 0}
    """
    info = _get_machine_info(machine)
    if not info or not info.get("ip"):
        return {"status": "error", "message": f"未知机器: {machine}"}
    
    user = info.get("user", "")
    ip = info["ip"]
    ssh_target = f"{user}@{ip}" if user else ip
    
    # 自动设置环境变量 + PYTHON 路径发现
    py_discover = 'PY=$(ls $HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3 2>/dev/null || which python3); '
    env_setup = "export AGENT_SYNC=\"$HOME/workbuddy-agent-os/agent-sync\"; "
    env_setup += "export AGENT_LOCAL=\"$HOME/workbuddy-agent-os/agent-local\"; "
    env_setup += "export MC_PYTHON=\"$PY\"; "
    
    if fire_and_forget:
        # 立即返回，不等待远程命令完成（适用浏览器登录等交互命令）
        full_cmd = f"{py_discover} {env_setup} nohup {command} > /tmp/remote_exec.log 2>&1 &"
        try:
            subprocess.run(
                ["ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no",
                 ssh_target, full_cmd],
                capture_output=True, text=True, timeout=15
            )
            return {"status": "ok", "message": "命令已发送", "fire_and_forget": True}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    full_cmd = f"{py_discover} {env_setup} {command}"
    try:
        r = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no",
             ssh_target, full_cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return {
            "status": "ok" if r.returncode == 0 else "error",
            "returncode": r.returncode,
            "stdout": r.stdout[:5000],
            "stderr": r.stderr[:500],
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": f"执行超时 ({timeout}s)"}
    except FileNotFoundError:
        return {"status": "error", "message": "ssh 命令未找到"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def exec_nurture(machine: str, accounts: list, blueprints: list, rounds: int = 3) -> dict:
    """在远程机器启动养号"""
    accts = ",".join(accounts)
    bps = ",".join(blueprints)
    cmd = f"cd $AGENT_SYNC/05_tools/07_matrix/scripts && python3 -m mc run --accounts={accts} --blueprints={bps} --rounds={rounds} --mix --interval=45-90"
    return exec_remote(machine, cmd, timeout=30)


def exec_collect(machine: str, phone: str = "") -> dict:
    """在远程机器启动采集"""
    cmd = f"cd $AGENT_SYNC/05_tools/07_matrix/scripts && $MC_PYTHON -m mc collect"
    if phone:
        cmd += f" --phone {phone}"
    else:
        cmd += " --all"
    return exec_remote(machine, cmd, timeout=30)


def exec_login(machine: str, account_id: str) -> dict:
    """在远程机器智能登录（全自动，立即返回）"""
    cmd = f"cd $AGENT_SYNC/05_tools/07_matrix/scripts && $MC_PYTHON -m mc smart-login {account_id}"
    return exec_remote(machine, cmd, timeout=120, fire_and_forget=True)


def exec_logout(machine: str, account_id: str) -> dict:
    """在远程机器清除账号登录状态"""
    cmd = f"cd $AGENT_SYNC/05_tools/07_matrix/scripts && $MC_PYTHON -m mc account logout {account_id}"
    return exec_remote(machine, cmd, timeout=30)


def exec_comment(machine: str, account_id: str, url: str, direction: str = "") -> dict:
    """在远程机器执行定向评论"""
    dir_flag = f" --direction {direction}" if direction else ""
    cmd = f"cd $AGENT_SYNC/05_tools/07_matrix/scripts && $MC_PYTHON -m mc task comment --account={account_id} --url={url}{dir_flag}"
    return exec_remote(machine, cmd, timeout=120)


def exec_nurture_stop(machine: str) -> dict:
    """停止远程机器的养号任务"""
    cmd = "pkill -f 'mc run' 2>/dev/null; pkill -f camoufox 2>/dev/null; echo 'stopped'"
    return exec_remote(machine, cmd, timeout=15)


def exec_status(machine: str) -> dict:
    """获取远程机器的完整状态"""
    cmd = "echo '---guardd---'; pgrep -f guardd && echo 'running' || echo 'stopped'; echo '---camoufox---'; pgrep -f camoufox && echo 'running' || echo 'stopped'; echo '---disk---'; df -h / | tail -1 | awk '{print $3 \"/\" $2 \" (\" $5 \")\"}'; echo '---load---'; uptime | awk -F'load averages:' '{print $2}'"
    return exec_remote(machine, cmd, timeout=10)

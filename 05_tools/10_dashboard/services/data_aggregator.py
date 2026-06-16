"""
联邦数据聚合器

从所有在线机器拉取数据并合并，供 Dashboard 展示。
所有机器通过 Tailscale 网络互联，端口统一 9988。
"""

import json, logging, sys
from pathlib import Path

logger = logging.getLogger("dashboard.federation")

# 确保能找到 ORACLE.yaml
_THIS_DIR = Path(__file__).resolve().parent.parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

ORACLE_PATH = _THIS_DIR.parent.parent / "ORACLE.yaml"


def _get_machines():
    """从 ORACLE.yaml 读取所有机器信息（排除本机）"""
    import yaml
    import os, socket, subprocess, re
    
    if not ORACLE_PATH.exists():
        return []
    
    with open(ORACLE_PATH) as f:
        oracle = yaml.safe_load(f)
    
    # 获取本机所有 IP（包括 Tailscale）
    try:
        output = subprocess.run(['ifconfig'], capture_output=True, text=True, timeout=5)
        local_ips = set(re.findall(r'inet (\d+\.\d+\.\d+\.\d+)', output.stdout))
    except:
        local_ips = {"127.0.0.1"}
    local_ips.add("127.0.0.1")
    
    machines = []
    for name, info in oracle.get("machines", {}).items():
        machine_ip = info.get("tailscale_ip", "")
        if machine_ip in local_ips:
            continue  # 跳过本机
        machines.append({
            "name": name,
            "hostname": info.get("hostname", name),
            "ip": info.get("tailscale_ip", ""),
            "port": info.get("dashboard_port", 9988),
            "user": info.get("ssh_user", ""),
        })
    return machines


def fetch_machine_data(machine: dict, path: str, timeout: int = 5) -> dict:
    """从指定机器拉取数据（使用 urllib，无外部依赖）"""
    import urllib.request, urllib.error
    
    url = f"http://{machine['ip']}:{machine['port']}{path}"
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        if r.status == 200:
            return json.loads(r.read().decode())
        return {"error": f"HTTP {r.status}"}
    except urllib.error.URLError as e:
        return {"error": f"连接失败: {e.reason}"}
    except TimeoutError:
        return {"error": "超时"}
    except Exception as e:
        return {"error": str(e)}


def aggregate_accounts():
    """聚合所有机器的账号列表（含本机）"""
    from plugins.base import HOSTNAME
    machines = _get_machines()
    all_accounts = []
    
    # 先加本机数据（只取本机账号）
    try:
        import urllib.request, json as _json
        local_resp = urllib.request.urlopen("http://localhost:9988/api/matrix/accounts", timeout=5)
        local_data = _json.loads(local_resp.read())
        if isinstance(local_data, list):
            for acct in local_data:
                if acct.get("owner_machine", "") != HOSTNAME:
                    continue
                acct["_source_machine"] = HOSTNAME
                acct["is_local"] = True
                all_accounts.append(acct)
    except Exception:
        pass
    
    # 去重集合: (machine, account_id)
    seen = set()
    
    for m in machines:
        data = fetch_machine_data(m, "/api/matrix/accounts")
        if isinstance(data, list):
            for acct in data:
                # 只取该机器自己的账号（去重）
                if acct.get("owner_machine", "") != m["name"]:
                    continue
                key = m["name"] + "|" + acct.get("id", "")
                if key in seen:
                    continue
                seen.add(key)
                acct["_source_machine"] = m["name"]
                acct["is_local"] = False
                all_accounts.append(acct)
        elif isinstance(data, dict) and "error" not in data:
            accts = data.get("data", data.get("accounts", []))
            if isinstance(accts, list):
                for acct in accts:
                    if acct.get("owner_machine", "") != m["name"]:
                        continue
                    key = m["name"] + "|" + acct.get("id", "")
                    if key in seen:
                        continue
                    seen.add(key)
                    acct["_source_machine"] = m["name"]
                    acct["is_local"] = False
                    all_accounts.append(acct)
        else:
            all_accounts.append({
                "_source_machine": m["name"],
                "_error": data.get("error", "未知错误"),
                "machine_ip": m.get("ip", ""),
                "is_local": False,
            })
    
    return all_accounts


def aggregate_health():
    """聚合所有机器的健康状态（含本机）"""
    from plugins.base import HOSTNAME
    machines = _get_machines()
    results = {}
    
    # 先加本机健康
    try:
        import urllib.request, json as _json
        local_resp = urllib.request.urlopen("http://localhost:9988/api/health", timeout=3)
        results[HOSTNAME] = _json.loads(local_resp.read())
    except Exception as e:
        results[HOSTNAME] = {"status": "ok", "note": "本机直连"}
    
    for m in machines:
        data = fetch_machine_data(m, "/api/health")
        results[m["name"]] = data
    
    return results


def aggregate_status():
    """聚合所有机器的详细状态（含本机）"""
    from plugins.base import HOSTNAME
    machines = _get_machines()
    results = {}
    
    # 本机状态
    try:
        import urllib.request, json as _json
        lh = urllib.request.urlopen("http://localhost:9988/api/health", timeout=3)
        local_health = _json.loads(lh.read())
        ls = None
        try:
            ls_resp = urllib.request.urlopen("http://localhost:9988/api/machine/status", timeout=3)
            ls = _json.loads(ls_resp.read())
        except:
            pass
        results[HOSTNAME] = {
            "status": "online",
            "hostname": HOSTNAME,
            "ip": "127.0.0.1",
            "health": local_health,
            "detail": ls,
        }
    except:
        results[HOSTNAME] = {"status": "online", "hostname": HOSTNAME, "ip": "127.0.0.1"}
    
    for m in machines:
        health = fetch_machine_data(m, "/api/health", timeout=3)
        if "error" in health:
            results[m["name"]] = {
                "status": "offline",
                "error": health["error"],
                "hostname": m["hostname"],
                "ip": m["ip"],
            }
            continue
        status = fetch_machine_data(m, "/api/machine/status", timeout=5)
        results[m["name"]] = {
            "status": "online",
            "hostname": m["hostname"],
            "ip": m["ip"],
            "health": health,
            "detail": status if "error" not in status else None,
        }
    
    return results

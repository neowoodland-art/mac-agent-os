"""
fleet_collector.py — 联邦信息采集聚合器

职责：
  主控机通过 SSH 定期从各工作机拉取采集数据（homepage_info.json + profiles.json），
  合并后供 Dashboard 统一展示。

架构：
  工作机只需要：
    - guardd 正常运行（已在做）
    - SSH 可达（Tailscale）
    - 本地有 homepage_info.json（采集后自动生成）
  
  主控机负责：
    - SSH 拉取各机器数据
    - 按来源机器缓存
    - 聚合 API 返回合并结果
"""

import json
import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("dashboard.fleet_collector")

_THIS_DIR = Path(__file__).resolve().parent
AGENT_LOCAL = Path(os.environ.get("AGENT_LOCAL", str(Path.home() / "workbuddy-agent-os" / "agent-local")))
AGENT_SYNC = Path(os.environ.get("AGENT_SYNC", str(Path.home() / "workbuddy-agent-os" / "agent-sync")))

# 缓存目录：agent-local/runtime/fleet_collector/{hostname}/
CACHE_DIR = AGENT_LOCAL / "runtime" / "fleet_collector"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 已知工作机列表（从 ORACLE.yaml 读取）
_KNOWN_WORKERS_CACHE = None
_KNOWN_WORKERS_CACHE_TIME = 0


def _get_workers() -> list[dict]:
    """从 ORACLE.yaml 读取所有工作机信息"""
    global _KNOWN_WORKERS_CACHE, _KNOWN_WORKERS_CACHE_TIME
    now = time.time()
    if _KNOWN_WORKERS_CACHE and now - _KNOWN_WORKERS_CACHE_TIME < 300:
        return _KNOWN_WORKERS_CACHE

    oracle_path = AGENT_SYNC / "ORACLE.yaml"
    if not oracle_path.exists():
        return []

    try:
        import yaml
        oracle = yaml.safe_load(oracle_path.read_text())
        machines = oracle.get("machines", {})
        workers = []
        for name, info in machines.items():
            workers.append({
                "name": name,
                "hostname": info.get("hostname", name),
                "ip": info.get("tailscale_ip", ""),
                "user": info.get("ssh_user", ""),
                "role": info.get("role", ""),
            })
        _KNOWN_WORKERS_CACHE = workers
        _KNOWN_WORKERS_CACHE_TIME = now
        return workers
    except Exception as e:
        logger.warning(f"读取 ORACLE.yaml 工作机列表失败: {e}")
        return []


def _ssh_read_file(hostname: str, remote_path: str, timeout: int = 15) -> Optional[str]:
    """通过 SSH 读取远程文件内容"""
    workers = _get_workers()
    target = None
    for w in workers:
        if w["name"] == hostname or w["hostname"] == hostname:
            target = w
            break
    if not target or not target.get("ip") or not target.get("user"):
        logger.warning(f"未知工作机: {hostname}")
        return None

    ssh_target = f"{target['user']}@{target['ip']}"
    try:
        r = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no",
             ssh_target, f"cat {remote_path} 2>/dev/null || echo '__FILE_NOT_FOUND__'"],
            capture_output=True, text=True, timeout=timeout
        )
        if r.returncode == 0 and "__FILE_NOT_FOUND__" not in r.stdout:
            return r.stdout
        return None
    except Exception as e:
        logger.debug(f"SSH 读取 {hostname}:{remote_path} 失败: {e}")
        return None


def collect_single(hostname: str) -> dict:
    """从单台工作机拉取采集数据，写入缓存

    Returns:
        {"hostname": str, "collected": bool, "homepage": dict, "profiles": dict, "error": str}
    """
    result = {"hostname": hostname, "collected": False, "homepage": {}, "profiles": {}, "error": ""}

    # 读取远程 homepage_info.json
    remote_hp = "~/workbuddy-agent-os/agent-local/tools/matrix/data/homepage_info.json"
    hp_content = _ssh_read_file(hostname, remote_hp)
    if hp_content:
        try:
            hp_data = json.loads(hp_content)
            result["homepage"] = hp_data
        except json.JSONDecodeError as e:
            result["error"] += f"homepage_info 解析失败: {e}; "

    # 读取远程 profiles.json
    remote_pf = "~/workbuddy-agent-os/agent-local/tools/matrix/data/profiles.json"
    pf_content = _ssh_read_file(hostname, remote_pf)
    if pf_content:
        try:
            pf_data = json.loads(pf_content)
            result["profiles"] = pf_data
        except json.JSONDecodeError as e:
            result["error"] += f"profiles 解析失败: {e}; "

    # 写入本地缓存
    machine_dir = CACHE_DIR / hostname
    machine_dir.mkdir(parents=True, exist_ok=True)

    if result["homepage"]:
        (machine_dir / "homepage_info.json").write_text(
            json.dumps(result["homepage"], indent=2, ensure_ascii=False)
        )
    if result["profiles"]:
        (machine_dir / "profiles.json").write_text(
            json.dumps(result["profiles"], indent=2, ensure_ascii=False)
        )

    # 写入采集时间戳
    (machine_dir / "collected_at.txt").write_text(
        datetime.now(timezone.utc).isoformat()
    )

    result["collected"] = bool(hp_content or pf_content)
    if not result["collected"]:
        result["error"] += "未获取到任何采集数据"
    logger.info(f"  采集 {hostname}: {'✅' if result['collected'] else '❌'} {result['error']}")
    return result


def collect_all() -> list[dict]:
    """遍历所有工作机拉取采集数据"""
    workers = _get_workers()
    results = []
    for w in workers:
        if w["role"] == "master" or w["name"] == os.uname().nodename:
            continue  # 跳过本机
        # 也跳过 cached_hostname 匹配本机的情况
        cached_hn = AGENT_LOCAL / "identity" / "cached_hostname"
        if cached_hn.exists() and cached_hn.read_text().strip() == w["name"]:
            continue
        result = collect_single(w["name"])
        results.append(result)
    return results


def get_merged_homepage() -> dict:
    """返回合并后的所有机器 homepage 数据

    读取本机 + 所有缓存的工作机数据，合并为一个列表
    """
    all_results = []

    # 1. 本机数据
    local_hp = AGENT_LOCAL / "tools" / "matrix" / "data" / "homepage_info.json"
    if local_hp.exists():
        try:
            data = json.loads(local_hp.read_text())
            for entry in data.get("results", []):
                entry["_source_machine"] = "local"
                all_results.append(entry)
        except Exception:
            pass

    # 2. 各工作机缓存
    if CACHE_DIR.exists():
        for machine_dir in sorted(CACHE_DIR.iterdir()):
            if not machine_dir.is_dir():
                continue
            hp_file = machine_dir / "homepage_info.json"
            if hp_file.exists():
                try:
                    data = json.loads(hp_file.read_text())
                    for entry in data.get("results", []):
                        entry["_source_machine"] = machine_dir.name
                        all_results.append(entry)
                except Exception:
                    pass

    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "total_identities": len(all_results),
        "results": all_results,
    }


def get_cached_profiles(hostname: Optional[str] = None) -> dict:
    """获取缓存的 profiles 数据"""
    all_profiles = {}

    # 本机
    local_pf = AGENT_LOCAL / "tools" / "matrix" / "data" / "profiles.json"
    if local_pf.exists() and (hostname is None or hostname == "local"):
        try:
            all_profiles.update(json.loads(local_pf.read_text()))
        except Exception:
            pass

    # 工作机缓存
    if CACHE_DIR.exists():
        for machine_dir in sorted(CACHE_DIR.iterdir()):
            if not machine_dir.is_dir():
                continue
            if hostname and machine_dir.name != hostname:
                continue
            pf_file = machine_dir / "profiles.json"
            if pf_file.exists():
                try:
                    all_profiles.update(json.loads(pf_file.read_text()))
                except Exception:
                    pass

    return all_profiles

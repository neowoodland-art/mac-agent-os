"""
account_service.py — 统一账号数据聚合层 (Dashboard)

职责:
  - 联邦账号中心的数据后端
  - ORACLE.yaml → 账号归属映射（只读）
  - 所有机器统一走 guardd HTTP API (port 9090) 查询登录状态
  - 合并 profile 数据 (profiles.json + fleet_collector)

设计原则:
  - ORACLE.yaml 是权威来源，账号归属从 ORACLE 读
  - 所有机器对等，本机不特殊对待
  - 远程状态有 30 秒 TTL 缓存，避免频繁 HTTP 调用
  - 离线机器显示 last_known 状态 + offline 标记
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Optional
from services.command_bus import _guardd_api
from pathlib import Path

logger = logging.getLogger("dashboard.account_service")

_THIS_DIR = Path(__file__).resolve().parent.parent
AGENT_SYNC = Path(os.environ.get("AGENT_SYNC",
    str(Path.home() / "workbuddy-agent-os" / "agent-sync")))
AGENT_LOCAL = Path(os.environ.get("AGENT_LOCAL",
    str(Path.home() / "workbuddy-agent-os" / "agent-local")))
GUARDD_PORT = 9090

# ── 本机身份 ──
try:
    sys.path.insert(0, str(AGENT_SYNC / "05_tools" / "10_dashboard"))
    from utils.identity import resolve_hostname
    HOSTNAME = resolve_hostname()
except Exception:
    HOSTNAME = os.uname().nodename


class AccountService:
    """账户统一聚合服务"""

    def __init__(self):
        self._oracle = None
        self._oracle_loaded = 0
        # 远程状态缓存 {machine_name: {"accounts": {...}, "cached_at": ts}}
        self._remote_cache = {}
        self._cache_ttl = 300  # 秒（5 分钟）

    # ═══════════════════════════════════════════════════════════
    # 公开 API
    # ═══════════════════════════════════════════════════════════

    def get_all_accounts(self) -> list[dict]:
        """获取所有机器上所有账号的统一视图

        Returns:
            list[dict]: 每个 dict 包含完整账号信息
        """
        oracle = self._load_oracle()
        machines = oracle.get("machines", {})
        oracle_accounts = oracle.get("accounts", [])

        # 1. 构建 ORACLE 账号→机器映射
        #    {account_id: {phone, machine, platforms, identity_dir}}
        oracle_map = {}
        for entry in oracle_accounts:
            identity = entry.get("identity", "")
            phone = entry.get("phone", "")
            machine = entry.get("machine") or entry.get("assigned_machine", "")
            platforms = entry.get("platforms", {})
            # 旧格式兼容：platforms 是 {platform: account_id}
            for plat, aid in platforms.items():
                oracle_map[aid] = {
                    "phone": phone,
                    "identity": identity,
                    "machine": machine,
                    "platform": plat,
                }

        # 2. 从本机 MatrixManager 获取本地账号的完整信息（含 profiles）
        local_accounts = self._get_local_accounts_full()
        local_map = {a["id"]: a for a in local_accounts}

        # 3. 并行查询所有机器的 guardd 状态（含本机）
        all_machines = set()
        for entry in oracle_accounts:
            machine = entry.get("machine") or entry.get("assigned_machine", "")
            if machine:
                all_machines.add(machine)
        # 确保本机也在列表中（用实际 hostname 而非空字符串）
        local_machine = HOSTNAME or "chengzigedeAir"
        all_machines.add(local_machine)
        self._prefetch_remote_statuses(list(all_machines))

        # 4. 聚合所有账号
        seen = set()
        results = []

        # 先处理 ORACLE 中定义的所有账号（权威列表）
        for aid, entry in oracle_map.items():
            if aid in seen:
                continue
            seen.add(aid)
            machine = entry["machine"]
            is_local = (machine == HOSTNAME or not machine)

            acct = {
                "id": aid,
                "phone": entry["phone"],
                "platform": entry["platform"],
                "identity_dir": f"identities/{entry['identity']}" if entry.get("identity") else "",
                "owner_machine": machine or HOSTNAME,
                "is_local": is_local,
            }

            # 登录状态
            if is_local:
                # 本机：从 guardd 本地端点获取状态（更可靠）
                local = local_map.get(aid, {})
                local_statuses = self._get_all_remote_statuses(HOSTNAME)
                acct["login_status"] = local_statuses.get(aid, local.get("_status", "unknown"))
                acct["nickname"] = local.get("nickname", "")
                acct["fans"] = local.get("fans", "")
                acct["following"] = local.get("following", "")
                acct["likes"] = local.get("likes", "")
                acct["posts"] = local.get("posts", "")
                acct["avatar"] = local.get("avatar", "")
                acct["_banned"] = local.get("_banned", False)
                acct["_identity_dir_exists"] = local.get("_identity_dir_exists", False)
            else:
                # 远程：从 guardd 缓存或即时查询
                remote_status = self._get_remote_account_status(machine, aid)
                acct["login_status"] = remote_status
                # profile 数据从联邦采集数据补
                profile = self._get_profile_for_account(aid, machine)
                acct.update(profile)

            results.append(acct)

        # 5. 补全 ORACLE 中没有但本机有的账号（兼容过渡期）
        for local_acct in local_accounts:
            aid = local_acct["id"]
            if aid not in seen:
                seen.add(aid)
                local_acct["is_local"] = True
                local_acct["login_status"] = local_acct.get("_status", "unknown")
                local_acct["_identity_dir_exists"] = local_acct.get("_identity_dir_exists", False)
                results.append(local_acct)

        # 排序：按机器→平台→账号ID
        machine_order = ["chengzigedeAir", "5kechengdeAir", "7kecheng"]
        def sort_key(a):
            m = a.get("owner_machine", "")
            try:
                mi = machine_order.index(m)
            except ValueError:
                mi = 99
            plat = 0 if a.get("platform") == "douyin" else 1
            return (mi, plat, a["id"])
        results.sort(key=sort_key)

        return results

    def get_account_detail(self, account_id: str) -> dict | None:
        """获取单个账号完整详情（含任务历史、代理信息等）"""
        results = self.get_all_accounts()
        for a in results:
            if a["id"] == account_id:
                return a
        return None

    def batch_refresh_status(self, account_ids: list[str] = None) -> dict:
        """强制刷新指定账号（或全部账号）的状态

        Args:
            account_ids: 如果为 None，刷新所有账号

        Returns:
            {account_id: status, ...}
        """
        oracle = self._load_oracle()
        machines = oracle.get("machines", {})

        # 按机器分组
        by_machine = {}
        for aid in (account_ids or []):
            machine = self._get_account_machine(aid)
            if machine not in by_machine:
                by_machine[machine] = []
            by_machine[machine].append(aid)

        results = {}
        for machine, aids in by_machine.items():
            if machine == HOSTNAME or not machine:
                # 本机：用 MatrixManager
                try:
                    sys.path.insert(0, str(AGENT_SYNC / "05_tools" / "07_matrix" / "scripts"))
                    from matrix_mgmt import MatrixManager
                    mgr = MatrixManager()
                    for aid in aids:
                        acct = mgr.get_account(aid)
                        results[aid] = acct.get("_status", "unknown") if acct else "unknown"
                except Exception as e:
                    logger.warning(f"本机刷新状态失败: {e}")
                    for aid in aids:
                        results[aid] = "unknown"
            else:
                # 远程：清缓存 + 重新查询
                self._remote_cache.pop(machine, None)
                statuses = self._query_remote_statuses(machine)
                for aid in aids:
                    results[aid] = statuses.get(aid, "offline")

        return results

    # ═══════════════════════════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════════════════════════

    def _load_oracle(self) -> dict:
        """读取 ORACLE.yaml（只读）"""
        now = time.time()
        if self._oracle and now - self._oracle_loaded < 60:
            return self._oracle
        path = AGENT_SYNC / "ORACLE.yaml"
        if not path.exists():
            logger.warning("ORACLE.yaml 不存在")
            self._oracle = {"machines": {}, "accounts": []}
            self._oracle_loaded = now
            return self._oracle
        try:
            import yaml
            self._oracle = yaml.safe_load(path.read_text()) or {}
            self._oracle_loaded = now
            return self._oracle
        except Exception as e:
            logger.warning(f"ORACLE.yaml 解析失败: {e}")
            return self._oracle or {"machines": {}, "accounts": []}

    def _get_account_machine(self, account_id: str) -> str:
        """从 ORACLE 查账号归属机器"""
        oracle = self._load_oracle()
        for entry in oracle.get("accounts", []):
            platforms = entry.get("platforms", {})
            for plat, aid in platforms.items():
                if aid == account_id:
                    return entry.get("machine") or entry.get("assigned_machine", "")
            # 也检查 identity 字段
            if entry.get("identity", "").replace("phone_", "") == account_id.replace("douyin_", "").replace("xhs_", ""):
                return entry.get("machine") or entry.get("assigned_machine", "")
        return HOSTNAME

    def _get_local_accounts_full(self) -> list[dict]:
        """获取本机账号完整信息（从 MatrixManager）"""
        try:
            sys.path.insert(0, str(AGENT_SYNC / "05_tools" / "07_matrix" / "scripts"))
            from matrix_mgmt import MatrixManager
            mgr = MatrixManager()
            accounts = mgr.list_accounts()

            # 合并 profiles.json（通过 guardd API，对等原则）
            profiles = {}
            try:
                data = _guardd_api("GET", "/accounts/profiles")
                if isinstance(data, dict):
                    profiles = data.get("profiles", {})
            except Exception:
                pass

            for acct in accounts:
                aid = acct.get("id", "")
                pid = acct.get("identity_dir", "").replace("identities/", "")
                profile = profiles.get(aid) or profiles.get(pid) or {}
                if profile:
                    acct.setdefault("nickname", profile.get("nickname", ""))
                    acct.setdefault("fans", profile.get("fans", ""))
                    acct.setdefault("avatar", profile.get("avatar", ""))
                    acct.setdefault("following", profile.get("following", ""))
                    acct.setdefault("likes", profile.get("likes", ""))
                    acct.setdefault("posts", profile.get("posts", ""))
                    if profile.get("status") == "banned":
                        acct["_banned"] = True
            return accounts
        except Exception as e:
            logger.warning(f"获取本机账号失败: {e}")
            return []

    def _get_remote_account_status(self, machine: str, account_id: str) -> str:
        """获取单个远程账号的登录状态（走缓存或即时查询）"""
        statuses = self._get_all_remote_statuses(machine)
        return statuses.get(account_id, "unknown")

    def _prefetch_remote_statuses(self, machines: list[str]):
        """并行预取远程机器状态

        使用 ThreadPoolExecutor 并行查询所有远程机器，
        避免逐个查询导致的总延迟累加。
        """
        if not machines:
            return
        now = time.time()
        # 只查缓存过期或未缓存的机器
        to_fetch = [m for m in machines
                    if m not in self._remote_cache
                    or now - self._remote_cache[m].get("cached_at", 0) >= self._cache_ttl]
        if not to_fetch:
            return

        logger.info(f"并行查询远程状态: {to_fetch}")
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=len(to_fetch)) as pool:
            future_map = {pool.submit(self._query_remote_statuses, m): m for m in to_fetch}
            for future in as_completed(future_map):
                machine = future_map[future]
                try:
                    statuses = future.result()
                    self._remote_cache[machine] = {
                        "accounts": statuses,
                        "cached_at": now,
                    }
                    logger.debug(f"远程状态已缓存: {machine} ({len(statuses)} 个账号)")
                except Exception as e:
                    logger.debug(f"远程状态查询失败 {machine}: {e}")
                    # 缓存为空结果，避免后续一直重试
                    self._remote_cache[machine] = {
                        "accounts": {},
                        "cached_at": now,
                    }

    def _get_all_remote_statuses(self, machine: str) -> dict:
        """获取一台远程机器上所有账号的状态
        使用 30 秒 TTL 缓存
        """
        now = time.time()
        cached = self._remote_cache.get(machine)
        if cached and now - cached.get("cached_at", 0) < self._cache_ttl:
            return cached.get("accounts", {})

        statuses = self._query_remote_statuses(machine)
        self._remote_cache[machine] = {
            "accounts": statuses,
            "cached_at": now,
        }
        return statuses

    def _query_remote_statuses(self, machine: str) -> dict:
        """通过 guardd HTTP API 查询远程机器账号状态

        使用 raw socket 方式（同 command_bus._guardd_api），
        urllib 在 Dashboard 环境下有兼容问题（502 Bad Gateway）。
        """
        if not machine:
            return {}

        from services.command_bus import _guardd_api
        # 统一走 command_bus 的 guardd API 客户端（本机/远程无差别）
        data = _guardd_api("GET", "/accounts/status", machine=machine)
        return data.get("accounts", {}) if isinstance(data, dict) else {}

    def _get_profile_for_account(self, account_id: str, machine: str) -> dict:
        """通过 guardd HTTP API 获取账号 profile 数据（本机+远程统一路径，遵守联邦对等原则）"""
        try:
            data = _guardd_api("GET", "/accounts/profiles", machine=machine)
            if isinstance(data, dict):
                profiles = data.get("profiles", {})
                p = profiles.get(account_id, {})
                if p and p.get("nickname"):
                    return {
                        "nickname": p.get("nickname", ""),
                        "fans": str(p.get("fans", "")),
                        "avatar": p.get("avatar", ""),
                        "following": str(p.get("following", "")),
                        "likes": str(p.get("likes", "")),
                        "posts": str(p.get("posts", "")),
                    }
        except Exception:
            pass
        return {"nickname": "", "fans": "", "following": "", "likes": "", "posts": "", "avatar": ""}

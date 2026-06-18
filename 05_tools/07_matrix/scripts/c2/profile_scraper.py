#!/usr/bin/env python3
"""
⚠️ 已废弃 — 请使用 Dashboard 采集 API 替代。
   本文件保留以供 douyin_login.py 引用，新代码禁止导入。

profile_scraper.py — 账号主页资料自动采集引擎 v1.0

功能:
  - 对每个已登录的 Camoufox 账号
  - 打开平台个人主页
  - 提取: 昵称 / 粉丝 / 关注 / 简介 / 作品数 / 最热视频
  - 存储到 machines/{uid}/profiles/{account_id}.json
  - 集成到养号流程 (每次养号后自动刷新)

版本: 1.0.0 | 更新: 2026-05-31
"""
import json, os, asyncio, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

HOME = Path.home()
AGENT_SYNC = HOME / "workbuddy-agent-os" / "agent-sync"
AGENT_LOCAL = HOME / "workbuddy-agent-os" / "agent-local"

PROFILES_DIR = AGENT_SYNC / "04_memory" / "cross_machine" / "machines"
LOCAL_PROFILES = AGENT_LOCAL / "runtime" / "profiles"

# ── 平台主页 URL 模板 (按平台扩展) ─────────────────────
# 格式: platform → (url_pattern, selectors)
PLATFORM_PROFILES = {
    "douyin": {
        "url": "https://www.douyin.com/user/self",
        "selectors": {
            "display_name": ".nickname, .account-info .name, h1",
            "followers": ".follower-count, .follower-num, span[class*=follower]",
            "following": ".following-count, .following-num",
            "bio": ".signature, .desc, .bio",
            "video_count": ".video-count, .post-count, span[class*=video]",
            "likes_received": ".like-count, .total-favorited",
        }
    },
    "xiaohongshu": {
        "url": "https://www.xiaohongshu.com/user/profile",
        "selectors": {
            "display_name": ".username, .user-name, h1",
            "followers": ".follower-count, span[class*=fans]",
            "following": ".following-count, span[class*=follow]",
            "bio": ".desc, .user-desc, .introduction",
            "video_count": ".note-count, .post-count",
            "collects_received": ".collected-count",
        }
    },
    "kuaishou": {
        "url": "https://www.kuaishou.com/profile",
        "selectors": {
            "display_name": ".name, .username",
            "followers": ".fans, .follower-count",
            "following": ".follow, .following-count",
            "bio": ".description, .signature",
            "video_count": ".works-count, .video-count",
        }
    },
}


class ProfileScraper:
    """账号主页资料采集器"""

    def __init__(self):
        self._local_uid = self._resolve_uid()
        self._local_hostname = self._resolve_hostname()
        LOCAL_PROFILES.mkdir(parents=True, exist_ok=True)

    def refresh_all(self) -> list[dict]:
        """刷新所有本机已登录账号的资料"""
        try:
            from matrix_mgmt import MatrixManager
            mgr = MatrixManager()
            accounts = mgr.list_accounts()
            local = [a for a in accounts if a.get("is_local") and a.get("_status") == "logged_in"]
        except ImportError:
            return [{"error": "matrix_mgmt not available"}]

        results = []
        for acct in local:
            try:
                result = self._scrape_one(acct)
                results.append(result)
            except Exception as e:
                results.append({"account": acct["id"], "error": str(e)})
        return results

    def refresh(self, account_ids: list[str]) -> list[dict]:
        """刷新指定账号的资料"""
        try:
            from matrix_mgmt import MatrixManager
            mgr = MatrixManager()
            accounts = mgr.list_accounts()
            targets = [a for a in accounts if a["id"] in account_ids]
        except ImportError:
            return [{"error": "matrix_mgmt not available"}]

        results = []
        for acct in targets:
            try:
                result = self._scrape_one(acct)
                results.append(result)
            except Exception as e:
                results.append({"account": acct["id"], "error": str(e)})
        return results

    def _scrape_one(self, acct: dict) -> dict:
        """采集单个账号的主页资料

        实际执行时通过 matrix_nurture 的 Camoufox 实例完成。
        此处为框架接口——Camoufox 操作由 nurture_runner 调用。
        """
        platform = acct.get("platform", "")
        profile_config = PLATFORM_PROFILES.get(platform)
        if not profile_config:
            return {"account": acct["id"], "error": f"不支持的平台: {platform}"}

        # 构建结果框架
        result = {
            "account_id": acct["id"],
            "platform": platform,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }

        # 采集流程:
        # 1. 启动 Camoufox (用该账号的 identity_dir)
        # 2. 导航到 platform.url
        # 3. 等待页面加载 + 提取 selectors
        # 4. 关闭浏览器
        # 5. 存储结果

        # 待 Camoufox API 就绪后实现具体采集逻辑
        # 当前返回框架占位
        result["_status"] = "pending_implementation"
        result["_note"] = "采集逻辑待 Camoufox API 集成"

        # 写入本地存储
        self._save_profile(result)
        return result

    def _save_profile(self, data: dict):
        """存储采集到的资料到 machines/{uid}/profiles/{account_id}.json"""
        profiles_dir = PROFILES_DIR / self._local_uid / "profiles"
        profiles_dir.mkdir(parents=True, exist_ok=True)
        path = profiles_dir / f"{data['account_id']}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_profile(self, account_id: str) -> Optional[dict]:
        """读取已存储的账号资料"""
        path = PROFILES_DIR / self._local_uid / "profiles" / f"{account_id}.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except:
                pass
        return None

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


if __name__ == "__main__":
    scraper = ProfileScraper()
    results = scraper.refresh_all()
    print(json.dumps(results, indent=2, ensure_ascii=False))

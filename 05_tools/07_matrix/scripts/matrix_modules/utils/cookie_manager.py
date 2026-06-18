"""
cookie_manager.py — Cookie 安全备份与恢复模块 v1.0

核心问题：XHS 和 Douyin 共享 identity_dir（douyin_01_camo = douyin_01 + xhs_01）
清 XHS cookie 时容易误删抖音 session。

解决方案：
1. 每次操作前自动全量备份 cookies.sqlite（带平台+时间戳标签）
2. 跨平台操作时自动保护对方平台 cookie（备份后再操作）
3. 支持按平台精准恢复（只恢复某个平台的 cookie 行）

文件结构：
    backups/cookies/{identity_dir_name}/
        cookies.{timestamp}.{platform}.bak          ← 全量备份
        cookies.{timestamp}.restore_point.bak        ← 操作前检查点

使用：
    from matrix_modules.utils.cookie_manager import CookieGuard

    guard = CookieGuard("douyin_01_camo")
    guard.backup(platform="douyin")        # 备份当前状态
    guard.protect("douyin")                 # 保护抖音（=备份后操作其他平台）
    guard.restore(platform="douyin")        # 恢复抖音 cookie
"""
import shutil
import os
import time
import sqlite3
from pathlib import Path
from typing import Optional, List
import glob

from matrix_mgmt import AGENT_LOCAL
LOCAL_ROOT = AGENT_LOCAL / "tools" / "matrix"
IDENTITIES_DIR = LOCAL_ROOT / "identities"
BACKUP_DIR = LOCAL_ROOT / "backups" / "cookies"

# 共享 identity_dir → 涉及的平台映射
SHARED_MAP = {
    "douyin_01_camo": ["douyin", "xiaohongshu"],
    "douyin_02_camo": ["douyin", "xiaohongshu"],
    "douyin_camo01":  ["douyin", "xiaohongshu"],
}


class CookieGuard:
    """Cookie 安全防护工具"""

    def __init__(self, identity_dir_name: str):
        """
        Args:
            identity_dir_name: identity 目录名, 如 "douyin_01_camo"
        """
        self.identity_name = identity_dir_name
        self.user_data_dir = IDENTITIES_DIR / identity_dir_name / "user_data"
        self.cookie_file = self.user_data_dir / "cookies.sqlite"
        self.backup_subdir = BACKUP_DIR / identity_dir_name
        self.backup_subdir.mkdir(parents=True, exist_ok=True)

    # ──────────────── 公共 API ────────────────

    def backup(self, platform: str = None, label: str = "") -> str:
        """
        全量备份 cookies.sqlite

        Args:
            platform: 平台标签（douyin/xiaohongshu），用于标识
            label: 额外标签（如 "pre_xhs_clear"）

        Returns:
            备份文件路径，失败返回空字符串
        """
        if not self.cookie_file.exists():
            return ""

        ts = time.strftime("%Y%m%d_%H%M%S")
        parts = ["cookies", ts]
        if platform:
            parts.append(platform)
        if label:
            parts.append(label)
        bak_name = ".".join(parts) + ".bak"

        bak_path = self.backup_subdir / bak_name
        try:
            shutil.copy2(str(self.cookie_file), str(bak_path))
            return str(bak_path)
        except Exception as e:
            return ""

    def restore(self, backup_file: str = None, platform: str = None) -> bool:
        """
        恢复 cookies.sqlite 到目标目录

        Args:
            backup_file: 指定备份文件路径；None 时自动找最新的
            platform: 指定按平台恢复（仅恢复该平台的 cookie 行）
                      None 时全量恢复

        Returns:
            True=成功
        """
        if not backup_file:
            latest = self._find_latest_backup(platform)
            if not latest:
                return False
            backup_file = str(latest)

        src = Path(backup_file)
        if not src.exists():
            return False

        if platform:
            # ── 按平台精准恢复（只覆盖指定平台的 cookie 行） ──
            return self._restore_platform_only(src, platform)
        else:
            # ── 全量恢复 ──
            try:
                # 先备份当前文件（万一恢复错了还能回退）
                current_bak = self.backup(platform=platform, label="pre_restore")
                # 复制备份覆盖
                shutil.copy2(str(src), str(self.cookie_file))
                return True
            except Exception:
                return False

    def protect(self, platform_to_protect: str) -> str:
        """
        保护指定平台的 cookie：操作其他平台前先调用

        例如 protect("douyin") 会在清 XHS cookie 前，
        先备份当前 cookies.sqlite（含抖音 session）。

        Args:
            platform_to_protect: 要保护的平台 ("douyin" 或 "xiaohongshu")

        Returns:
            备份文件路径
        """
        return self.backup(platform=platform_to_protect, label="protected")

    def delete_platform_cookies_safe(self, platform: str) -> bool:
        """
        安全删除指定平台的 cookie（自动备份对方平台）

        Args:
            platform: 要删除的平台 ("douyin" 或 "xiaohongshu")

        Returns:
            bool: True=删除成功
        """
        # 1. 先保护对方平台
        other = self._get_other_platform(platform)
        if other:
            self.protect(other)

        # 2. 再全量备份当前状态
        self.backup(platform=platform, label="pre_delete")

        # 3. 执行删除
        return self._delete_platform_cookies(platform)

    def list_backups(self, platform: str = None) -> List[str]:
        """列出可用备份"""
        pattern = f"cookies.*{platform + '.' if platform else ''}*.bak"
        files = sorted(self.backup_subdir.glob(pattern), reverse=True)
        return [str(f) for f in files]

    # ──────────────── 内部方法 ────────────────

    def _find_latest_backup(self, platform: str = None):
        """找最新的备份文件"""
        pattern = f"cookies.*{platform + '.' if platform else ''}*.bak"
        files = sorted(self.backup_subdir.glob(pattern), reverse=True)
        return files[0] if files else None

    def _get_other_platform(self, platform: str) -> Optional[str]:
        """获取共享 identity 中的对方平台名"""
        platforms = SHARED_MAP.get(self.identity_name, [])
        for p in platforms:
            if p != platform:
                return p
        return None

    def _delete_platform_cookies(self, platform: str) -> bool:
        """通过 sqlite3 删除指定平台的 cookie"""
        domain_patterns = {
            "douyin": "%douyin.com%",
            "xiaohongshu": "%xiaohongshu%",
        }
        pattern = domain_patterns.get(platform, f"%{platform}%")

        if not self.cookie_file.exists():
            return False

        try:
            conn = sqlite3.connect(str(self.cookie_file))
            c = conn.cursor()
            c.execute("DELETE FROM moz_cookies WHERE host LIKE ?", (pattern,))
            deleted = c.rowcount
            conn.commit()
            conn.close()
            # 删除 -wal 和 -shm 文件（Firefox 可能未正常关闭）
            for ext in ["-wal", "-shm"]:
                f = str(self.cookie_file) + ext
                if os.path.exists(f):
                    os.remove(f)
            return deleted > 0
        except Exception:
            return False

    def _restore_platform_only(self, src: Path, platform: str) -> bool:
        """
        精准恢复：从备份文件中提取指定平台的 cookie 行，
        合并到当前 cookies.sqlite

        流程：
        1. 从备份文件读取指定平台的 cookie 行
        2. 从当前文件删除该平台的旧 cookie 行
        3. 将备份中的行插入当前文件
        """
        domain_patterns = {
            "douyin": "%douyin.com%",
            "xiaohongshu": "%xiaohongshu%",
        }
        pattern = domain_patterns.get(platform, f"%{platform}%")

        if not self.cookie_file.exists():
            return False

        try:
            # 连接备份文件，读取目标平台的 cookie 行
            src_conn = sqlite3.connect(str(src))
            src_c = src_conn.cursor()
            rows = src_c.execute(
                "SELECT * FROM moz_cookies WHERE host LIKE ?", (pattern,)
            ).fetchall()
            columns = [d[0] for d in src_c.description]
            src_conn.close()

            if not rows:
                return False

            # 连接当前文件，删除旧行后插入
            dst_conn = sqlite3.connect(str(self.cookie_file))
            dst_c = dst_conn.cursor()

            # 删除该平台旧 cookie
            dst_c.execute("DELETE FROM moz_cookies WHERE host LIKE ?", (pattern,))

            # 构造 INSERT 语句
            placeholders = ",".join(["?"] * len(columns))
            col_names = ",".join(columns)
            dst_c.executemany(
                f"INSERT INTO moz_cookies ({col_names}) VALUES ({placeholders})",
                rows
            )
            dst_conn.commit()
            dst_conn.close()

            # 清理 wal/shm
            for ext in ["-wal", "-shm"]:
                f = str(self.cookie_file) + ext
                if os.path.exists(f):
                    os.remove(f)

            return True
        except Exception:
            return False


# ──────────────── 简便函数（不用实例化） ────────────────

def backup_all_identities(platform: str = None, label: str = "") -> dict:
    """备份所有账号的 cookie"""
    results = {}
    for identity in SHARED_MAP:
        guard = CookieGuard(identity)
        path = guard.backup(platform=platform, label=label)
        results[identity] = path
    return results


def quick_backup(identity_dir_name: str, platform: str = None) -> str:
    """快速备份单个账号"""
    guard = CookieGuard(identity_dir_name)
    return guard.backup(platform=platform)

#!/usr/bin/env python3
"""
matrix_mgmt.py — Matrix 账号管理系统后端 (v1.0)
提供账号CRUD、蓝图编排、原子操作查询、导入导出等管理能力，
供 Dashboard 插件和前端调用。

用法:
  from matrix_mgmt import MatrixManager
  mgr = MatrixManager()
  mgr.list_accounts()
  mgr.create_account({...})
"""
import json, os, yaml, shutil, tempfile, zipfile, sqlite3, time, subprocess, glob
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

HOME = Path.home()
_AGENT_SYNC_ENV = os.environ.get("AGENT_SYNC", "")
_AGENT_LOCAL_ENV = os.environ.get("AGENT_LOCAL", "")
AGENT_SYNC = Path(_AGENT_SYNC_ENV) if _AGENT_SYNC_ENV else HOME / "workbuddy-agent-os" / "agent-sync"
AGENT_LOCAL = Path(_AGENT_LOCAL_ENV) if _AGENT_LOCAL_ENV else HOME / "workbuddy-agent-os" / "agent-local"

MATRIX_CODE = AGENT_SYNC / "05_tools" / "07_matrix"
MATRIX_SCRIPTS = MATRIX_CODE / "scripts"
MATRIX_LOCAL = AGENT_LOCAL / "tools" / "matrix"
MATRIX_IDENTITIES = MATRIX_LOCAL / "identities"
MATRIX_ACCOUNTS_CFG = MATRIX_LOCAL / "config" / "accounts.yaml"
MATRIX_BACKUPS = MATRIX_LOCAL / "backups"
MATRIX_BLUEPRINTS = MATRIX_CODE / "blueprints"
MATRIX_CONFIG_TEMPLATE = MATRIX_CODE / "config_template"
MATRIX_ACCOUNT_WORKSPACES = MATRIX_LOCAL / "accounts"

PYTHON = str(HOME / ".workbuddy" / "binaries" / "python" / "envs" / "agent-os" / "bin" / "python3")
MATRIX_CLI = str(MATRIX_SCRIPTS / "matrix.py")


class MatrixManager:

    # ═══════════════════════════════════════════════════════════
    # 账号管理
    # ═══════════════════════════════════════════════════════════

    def list_accounts(self) -> list[dict]:
        """列出所有已配置账号及实时状态"""
        accounts = self._read_accounts_yaml()
        result = []
        for acct in accounts:
            if not acct.get("enabled", False):
                acct["_status"] = "disabled"
            else:
                acct["_status"] = self._check_login_status(acct)
            acct["_identity_dir_exists"] = self._identity_exists(acct)
            result.append(acct)
        return result

    def get_account(self, account_id: str) -> Optional[dict]:
        """获取单个账号详情"""
        accounts = self._read_accounts_yaml()
        for acct in accounts:
            if acct["id"] == account_id:
                acct["_status"] = self._check_login_status(acct)
                acct["_identity_dir_exists"] = self._identity_exists(acct)
                acct["_cookie_backups"] = self._count_backups(acct)
                return acct
        return None

    def create_account(self, data: dict) -> dict:
        """创建新账号（添加到 accounts.yaml）"""
        required = ["id", "platform"]
        for field in required:
            if field not in data:
                raise ValueError(f"缺少必填字段: {field}")

        accounts = self._read_accounts_yaml()
        # 检查重名
        if any(a["id"] == data["id"] for a in accounts):
            raise ValueError(f"账号 {data['id']} 已存在")

        # 同手机号已有身份？复用，不新建
        phone = data.get("phone", "")
        existing_identity = ""
        if phone:
            for a in accounts:
                if a.get("phone") == phone and a.get("identity_dir"):
                    existing_identity = a["identity_dir"]
                    break
            if not existing_identity:
                # 也查 override
                hostname, override = self._read_override()
                for a in override:
                    if a.get("phone") == phone and a.get("identity_dir"):
                        existing_identity = a["identity_dir"]
                        break

        new_identity = data.get("identity_dir", existing_identity or f"identities/{data['id']}")
        new_acct = {
            "id": data["id"],
            "platform": data["platform"],
            "phone": phone,
            "identity_dir": new_identity,
            "window": [702, 783],
            "window_position": data.get("window_position", [0, 0]),
            "proxy": data.get("proxy", None),
            "enabled": data.get("enabled", True),
            "notes": data.get("notes", ""),
        }
        accounts.append(new_acct)
        self._write_accounts_yaml(accounts)

        # ── WPRA v2.0: 同步写入 machines/{uid}/accounts.yaml ──
        self._write_self_accounts()

        # 创建身份目录
        identity_dir_name = new_acct["identity_dir"].replace("identities/", "")
        identity_path = MATRIX_IDENTITIES / identity_dir_name
        identity_path.mkdir(parents=True, exist_ok=True)
        # 只有当 config.yaml 不存在时才创建（避免覆盖已有的 identity/指纹配置）
        config_file = identity_path / "config.yaml"
        if not config_file.exists():
            config_file.write_text(
                yaml.dump({
                    "window": [702, 783],
                    "screen": {"width": 702, "height": 783},
                    "identity": {
                        "name": identity_dir_name,
                        "platform": data.get("platform", "douyin"),
                        "created_at": datetime.now().isoformat(),
                        "notes": data.get("notes", ""),
                    },
                }, default_flow_style=False),
                encoding="utf-8",
            )

        return {"status": "ok", "account": new_acct}

    def update_account(self, account_id: str, data: dict) -> dict:
        """更新账号配置"""
        # 写入 Registry (notes 等元数据)
        reg = self._read_registry()
        reg_found = None
        for acct in reg:
            if acct["id"] == account_id:
                reg_found = acct
                break
        if not reg_found:
            # fallback: 旧版 accounts.yaml
            accounts = self._read_accounts_yaml()
            found = None
            for acct in accounts:
                if acct["id"] == account_id:
                    found = acct
                    break
            if not found:
                raise ValueError(f"账号 {account_id} 不存在")
            for key in ["phone", "window", "window_position", "proxy", "enabled", "notes", "platform"]:
                if key in data:
                    found[key] = data[key]
            self._write_accounts_yaml(accounts)
        else:
            for key in ["notes", "window", "window_position", "platform"]:
                if key in data:
                    reg_found[key] = data[key]
            self.REGISTRY_PATH.write_text(
                yaml.dump({"version": "1.0", "accounts": reg}, default_flow_style=False, allow_unicode=True, sort_keys=False)
            )

        # 写入 Override (phone, proxy, enabled 等敏感字段)
        hostname, override = self._read_override()
        ovr_found = None
        for acct in override:
            if acct["id"] == account_id:
                ovr_found = acct
                break
        if ovr_found is None:
            override.append({"id": account_id})
            ovr_found = override[-1]

        for key in ["phone", "proxy", "enabled"]:
            if key in data:
                ovr_found[key] = data[key]

        ovr_data = {"version": "1.0", "hostname": hostname or self._local_hostname(), "accounts": override}
        self.OVERRIDE_PATH.write_text(
            yaml.dump(ovr_data, default_flow_style=False, allow_unicode=True, sort_keys=False)
        )

        return {"status": "ok", "account_id": account_id}

    def delete_account(self, account_id: str, delete_identity: bool = False) -> dict:
        """删除账号配置，可选同时删除身份目录"""
        accounts = self._read_accounts_yaml()
        found = None
        for acct in accounts:
            if acct["id"] == account_id:
                found = acct
                break
        if not found:
            raise ValueError(f"账号 {account_id} 不存在")

        # 从配置中移除
        accounts.remove(found)
        self._write_accounts_yaml(accounts)

        # ── WPRA v2.0: 同步写入 machines/{uid}/accounts.yaml ──
        self._write_self_accounts()

        # 可选删除身份目录（谨慎操作）
        result = {"status": "ok", "removed_from_config": True, "identity_deleted": False}
        if delete_identity:
            identity_dir_name = found.get("identity_dir", "").replace("identities/", "")
            if identity_dir_name:
                identity_path = MATRIX_IDENTITIES / identity_dir_name
                if identity_path.exists():
                    shutil.rmtree(identity_path)
                    result["identity_deleted"] = True

        return result

    # ═══════════════════════════════════════════════════════════
    # 身份管理（v5.2 新增）
    # ═══════════════════════════════════════════════════════════

    def get_identities(self) -> list[dict]:
        """返回本机所有身份的聚合视图
        
        一个身份 = 一个 identity_dir，可包含多个平台账号
        按 身份目录 分组，展示手机号/平台账号/登录状态
        """
        accounts = self.list_accounts()
        # 只聚合本机账号
        local_accounts = [a for a in accounts if a.get("is_local")]
        
        # 按 identity_dir 分组
        groups = {}
        for a in local_accounts:
            aid = a["id"]
            identity_dir = None
            
            # 从本地 accounts.yaml 读 identity_dir
            legacy_accounts = self._read_accounts_yaml()
            for la in legacy_accounts:
                if la["id"] == aid:
                    id_dir = la.get("identity_dir", "")
                    if id_dir:
                        identity_dir = id_dir.replace("identities/", "")
                    break
            
            if not identity_dir:
                identity_dir = a.get("identity_hint", aid)
            
            if identity_dir not in groups:
                groups[identity_dir] = {
                    "identity_dir": identity_dir,
                    "phone": "",
                    "accounts": [],
                    "has_cookie": False,
                }
            
            phone = a.get("phone", a.get("phone_mask", ""))
            if phone and not groups[identity_dir]["phone"]:
                groups[identity_dir]["phone"] = phone
            
            # 检查身份目录是否存在和有 Cookie
            id_path = MATRIX_IDENTITIES / identity_dir
            cookie_file = id_path / "user_data" / "cookies.sqlite"
            has_cookie = cookie_file.exists() and cookie_file.stat().st_size > 0
            if has_cookie:
                groups[identity_dir]["has_cookie"] = True
            
            groups[identity_dir]["accounts"].append({
                "id": aid,
                "platform": a.get("platform", ""),
                "status": a.get("_status", "unknown"),
                "phone": a.get("phone", a.get("phone_mask", "")),
            })
        
        return list(groups.values())

    def unbind_account(self, account_id: str) -> dict:
        """从身份中解绑单个平台账号（保留 Cookie/身份目录）
        
        适用场景: 同一身份下有多个平台账号，只想移除其中一个
        """
        accounts = self._read_accounts_yaml()
        found = None
        for acct in accounts:
            if acct["id"] == account_id:
                found = acct
                break
        if not found:
            raise ValueError(f"账号 {account_id} 不存在")
        
        # 从本机配置移除
        accounts.remove(found)
        self._write_accounts_yaml(accounts)
        
        # 同步 WPRA
        self._write_self_accounts()
        
        return {
            "status": "ok",
            "account_id": account_id,
            "identity_preserved": True,
            "note": "账号已解绑，身份目录和Cookie已保留",
        }

    def delete_identity(self, identity_dir: str) -> dict:
        """删除整个身份（身份目录 + 旗下所有账号）
        
        适用场景: 彻底移除一个手机号的所有账号和浏览器指纹
        """
        # 1. 获取该身份下的所有账号
        accounts = self._read_accounts_yaml()
        to_remove = []
        for acct in accounts:
            id_dir = acct.get("identity_dir", "").replace("identities/", "")
            if id_dir == identity_dir or acct["id"] == identity_dir:
                to_remove.append(acct)
        
        removed_ids = [a["id"] for a in to_remove]
        
        # 2. 从配置中移除
        accounts = [a for a in accounts if a["id"] not in removed_ids]
        self._write_accounts_yaml(accounts)
        
        # 3. 同步 WPRA
        self._write_self_accounts()
        
        # 4. 删除身份目录
        id_path = MATRIX_IDENTITIES / identity_dir
        identity_deleted = False
        if id_path.exists():
            shutil.rmtree(id_path)
            identity_deleted = True
        
        # 5. 删除 Cookie 备份
        backup_dir = MATRIX_BACKUPS / "cookies" / identity_dir
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        
        return {
            "status": "ok",
            "identity_dir": identity_dir,
            "removed_accounts": removed_ids,
            "account_count": len(to_remove),
            "identity_deleted": identity_deleted,
        }

    # ═══════════════════════════════════════════════════════════
    # 账号操作
    # ═══════════════════════════════════════════════════════════

    def run_nurture(self, accounts: list[str], rounds: int = 10, daemon: bool = False) -> dict:
        """启动养号"""
        args = [PYTHON, MATRIX_CLI, "nurture", "run"]
        for a in accounts:
            args.extend(["-a", a])
        args.extend(["-r", str(rounds)])
        if daemon:
            args.append("--daemon")
        else:
            args.append("--no-daemon")

        log_file = f"/tmp/matrix_mgmt_nurture_{int(time.time())}.log"
        cmd_str = " ".join(str(a) for a in args) + f" > {log_file} 2>&1 &"
        subprocess.Popen(
            " ".join(str(a) for a in args),
            shell=True,
            stdout=open(log_file, "w"),
            stderr=subprocess.STDOUT,
        )
        return {"status": "started", "command": " ".join(str(a) for a in args), "log": log_file}

    def check_login_status(self, account_id: str) -> dict:
        """检查指定账号的登录状态"""
        acct = self.get_account(account_id)
        if not acct:
            return {"status": "unknown", "error": "账号不存在"}
        return {"account": account_id, "status": acct["_status"]}

    # ═══════════════════════════════════════════════════════════
    # 蓝图（原子操作编排）
    # ═══════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════
    # 原子操作依赖模型 v2.0 — 严格按平台隔离
    # ═══════════════════════════════════════════════════════════
    # 每个操作定义:
    #   platform:  所属平台 (douyin / xiaohongshu / 通用)
    #   category:  操作类别 (navigation/browse/interact/utility)
    #   requires:  前置操作（必须至少一个在此列表中）
    #   allows:    可选的后继操作（"*" 表示任意）
    #   can_be_first: 是否可作为第一个步骤
    #
    # 核心规则:
    #   - requires/allows 只引用同平台或"通用"的操作
    #   - 跨平台编排=不合法（蓝图验证会拦截）
    #   - 每个操作只能属于一个平台
    #
    # 新增操作:
    #   account_check_status — 检查账号登录状态
    #   account_read_info    — 读取账号信息（粉丝数/作品数等）
    # ═══════════════════════════════════════════════════════════

    OP_GRAPH = {
        # ═══════════════════════════════════════════════════
        # 🎵 抖音专用
        # ═══════════════════════════════════════════════════

        "goto_home": {
            "platform": "douyin", "category": "navigation", "label": "🏠 回到推荐页",
            "requires": [], "allows": ["browse_feed", "dy_enter_video", "dy_scroll_feed", "dy_search", "dy_goto_profile", "rest", "go_back", "dy_like", "dy_collect"],
            "can_be_first": True, "desc": "回到抖音推荐页，固定起点"
        },
        "browse_feed": {
            "platform": "douyin", "category": "browse", "label": "📱 浏览推荐流",
            "requires": ["goto_home", "go_back", "rest"], "allows": ["dy_enter_video", "dy_scroll_feed", "dy_search", "dy_like", "dy_collect", "rest", "go_back"],
            "can_be_first": True, "desc": "浏览推荐页视频流，自动滑视频"
        },
        "dy_scroll_feed": {
            "platform": "douyin", "category": "browse", "label": "⬇ 下滑加载",
            "requires": ["browse_feed", "dy_enter_video", "goto_home", "go_back", "rest"],
            "allows": ["dy_enter_video", "dy_scroll_feed", "dy_like", "dy_collect", "rest", "go_back"],
            "can_be_first": False, "desc": "抖音瀑布流下滑加载更多"
        },
        "dy_enter_video": {
            "platform": "douyin", "category": "browse", "label": "▶ 进入播放页",
            "requires": ["browse_feed", "dy_scroll_feed", "dy_search", "rest"],
            "allows": ["dy_like", "dy_collect", "dy_follow", "dy_comment_a", "dy_comment_b", "dy_scroll_feed", "dy_next_video", "dy_prev_video", "rest", "go_back"],
            "can_be_first": False, "desc": "从推荐页点击卡片进入视频播放页"
        },
        "dy_like": {
            "platform": "douyin", "category": "interact", "label": "👍 点赞",
            "requires": ["dy_enter_video", "browse_feed"], "allows": ["dy_collect", "dy_follow", "dy_comment_a", "dy_comment_b", "dy_scroll_feed", "dy_next_video", "dy_prev_video", "rest", "go_back"],
            "can_be_first": False, "desc": "点赞当前视频（KeyZ）"
        },
        "dy_collect": {
            "platform": "douyin", "category": "interact", "label": "⭐ 收藏",
            "requires": ["dy_enter_video"], "allows": ["dy_like", "dy_follow", "dy_comment_a", "dy_comment_b", "dy_scroll_feed", "dy_next_video", "dy_prev_video", "rest", "go_back"],
            "can_be_first": False, "desc": "收藏当前视频到收藏夹"
        },
        "dy_follow": {
            "platform": "douyin", "category": "interact", "label": "➕ 关注",
            "requires": ["dy_enter_video"], "allows": ["dy_like", "dy_collect", "dy_comment_a", "dy_comment_b", "dy_scroll_feed", "dy_next_video", "dy_prev_video", "rest", "go_back"],
            "can_be_first": False, "desc": "关注当前视频作者"
        },
        "dy_comment_a": {
            "platform": "douyin", "category": "interact", "label": "💬 评论(Path A)",
            "requires": ["dy_enter_video"], "allows": ["dy_like", "dy_collect", "dy_follow", "dy_scroll_feed", "dy_next_video", "dy_prev_video", "rest", "go_back"],
            "can_be_first": False, "desc": "弹窗覆盖层评论 (KeyX→pbcopy→Enter)"
        },
        "dy_comment_b": {
            "platform": "douyin", "category": "interact", "label": "💬 评论(Path B)",
            "requires": ["dy_enter_video"], "allows": ["dy_like", "dy_collect", "dy_follow", "dy_scroll_feed", "rest", "go_back"],
            "can_be_first": False, "desc": "全屏视频页评论 (scroll→click→Enter)"
        },
        "dy_next_video": {
            "platform": "douyin", "category": "interact", "label": "⏭ 下一个视频",
            "requires": ["dy_enter_video", "dy_like", "dy_collect", "dy_follow", "dy_comment_a"],
            "allows": ["dy_like", "dy_collect", "dy_follow", "dy_comment_a", "dy_comment_b", "dy_scroll_feed", "rest", "go_back"],
            "can_be_first": False, "desc": "切换到下一个视频"
        },
        "dy_prev_video": {
            "platform": "douyin", "category": "interact", "label": "⏮ 上一个视频",
            "requires": ["dy_enter_video"], "allows": ["dy_like", "dy_collect", "dy_follow", "dy_comment_a", "dy_comment_b", "rest", "go_back"],
            "can_be_first": False, "desc": "切换到上一个视频"
        },
        "dy_search": {
            "platform": "douyin", "category": "interact", "label": "🔍 抖音搜索",
            "requires": ["goto_home", "browse_feed", "rest", "go_back"], "allows": ["dy_enter_video", "dy_scroll_feed", "rest", "go_back"],
            "can_be_first": True, "desc": "在抖音搜索关键词并打开搜索结果页"
        },

        # ── 主页信息读取类（导航+读取7项）──
        "dy_goto_profile": {
            "platform": "douyin", "category": "browse", "label": "👤 进入个人主页",
            "requires": ["goto_home", "rest", "go_back"],
            "allows": ["dy_read_nickname", "dy_read_douyin_id", "dy_read_following", "dy_read_fans", "dy_read_likes", "dy_read_posts", "dy_read_bio", "rest", "go_back"],
            "can_be_first": False, "desc": "导航到当前账号的个人主页 /user/self"
        },
        "dy_read_nickname": {
            "platform": "douyin", "category": "interact", "label": "📝 读取昵称",
            "requires": ["dy_goto_profile"], "allows": ["dy_read_douyin_id", "dy_read_following", "dy_read_fans", "dy_read_likes", "dy_read_posts", "dy_read_bio", "rest", "go_back"],
            "can_be_first": False, "desc": "从个人主页读取账号昵称"
        },
        "dy_read_douyin_id": {
            "platform": "douyin", "category": "interact", "label": "🔢 读取抖音号",
            "requires": ["dy_goto_profile"], "allows": ["dy_read_nickname", "dy_read_following", "dy_read_fans", "dy_read_likes", "dy_read_posts", "dy_read_bio", "rest", "go_back"],
            "can_be_first": False, "desc": "从个人主页读取抖音号（数字ID）"
        },
        "dy_read_following": {
            "platform": "douyin", "category": "interact", "label": "👥 读取关注数",
            "requires": ["dy_goto_profile"], "allows": ["dy_read_nickname", "dy_read_douyin_id", "dy_read_fans", "dy_read_likes", "dy_read_posts", "dy_read_bio", "rest", "go_back"],
            "can_be_first": False, "desc": "从个人主页读取关注人数"
        },
        "dy_read_fans": {
            "platform": "douyin", "category": "interact", "label": "👥 读取粉丝数",
            "requires": ["dy_goto_profile"], "allows": ["dy_read_nickname", "dy_read_douyin_id", "dy_read_following", "dy_read_likes", "dy_read_posts", "dy_read_bio", "rest", "go_back"],
            "can_be_first": False, "desc": "从个人主页读取粉丝数"
        },
        "dy_read_likes": {
            "platform": "douyin", "category": "interact", "label": "👍 读取获赞数",
            "requires": ["dy_goto_profile"], "allows": ["dy_read_nickname", "dy_read_douyin_id", "dy_read_following", "dy_read_fans", "dy_read_posts", "dy_read_bio", "rest", "go_back"],
            "can_be_first": False, "desc": "从个人主页读取获赞总数"
        },
        "dy_read_posts": {
            "platform": "douyin", "category": "interact", "label": "📹 读取作品数",
            "requires": ["dy_goto_profile"], "allows": ["dy_read_nickname", "dy_read_douyin_id", "dy_read_following", "dy_read_fans", "dy_read_likes", "dy_read_bio", "rest", "go_back"],
            "can_be_first": False, "desc": "从个人主页读取作品（视频）数量"
        },
        "dy_read_bio": {
            "platform": "douyin", "category": "interact", "label": "📄 读取简介",
            "requires": ["dy_goto_profile"], "allows": ["dy_read_nickname", "dy_read_douyin_id", "dy_read_following", "dy_read_fans", "dy_read_likes", "dy_read_posts", "rest", "go_back"],
            "can_be_first": False, "desc": "从个人主页读取个人简介"
        },

        # ═══════════════════════════════════════════════════
        # 📕 小红书专用
        # ═══════════════════════════════════════════════════

        "xhs_goto_home": {
            "platform": "xiaohongshu", "category": "navigation", "label": "🏠 回到首页",
            "requires": [], "allows": ["xhs_browse", "xhs_scroll_feed", "xhs_search", "xhs_goto_profile", "rest", "go_back"],
            "can_be_first": True, "desc": "回到小红书首页，固定起点"
        },
        "xhs_browse": {
            "platform": "xiaohongshu", "category": "browse", "label": "📕 瀑布流浏览",
            "requires": ["xhs_goto_home", "rest", "go_back"], "allows": ["xhs_click_note", "xhs_scroll_feed", "xhs_search", "xhs_like", "rest", "go_back"],
            "can_be_first": True, "desc": "小红书首页瀑布流浏览推荐笔记"
        },
        "xhs_scroll_feed": {
            "platform": "xiaohongshu", "category": "browse", "label": "⬇ 下滑加载",
            "requires": ["xhs_browse", "xhs_goto_home", "go_back", "rest"],
            "allows": ["xhs_click_note", "xhs_scroll_feed", "xhs_like", "rest", "go_back"],
            "can_be_first": False, "desc": "小红书瀑布流下滑加载更多笔记"
        },
        "xhs_click_note": {
            "platform": "xiaohongshu", "category": "browse", "label": "📕 点击笔记",
            "requires": ["xhs_browse", "xhs_scroll_feed", "rest"], "allows": ["xhs_like", "xhs_comment", "rest", "go_back", "xhs_scroll_feed"],
            "can_be_first": False, "desc": "小红书点击笔记卡片进入详情页"
        },
        "xhs_like": {
            "platform": "xiaohongshu", "category": "interact", "label": "📕 点赞",
            "requires": ["xhs_click_note"], "allows": ["xhs_comment", "rest", "go_back", "xhs_scroll_feed"],
            "can_be_first": False, "desc": "小红书点赞当前笔记"
        },
        "xhs_comment": {
            "platform": "xiaohongshu", "category": "interact", "label": "📕 评论",
            "requires": ["xhs_click_note", "xhs_like"], "allows": ["rest", "go_back", "xhs_scroll_feed"],
            "can_be_first": False, "desc": "小红书评论当前笔记"
        },
        "xhs_search": {
            "platform": "xiaohongshu", "category": "interact", "label": "📕 小红书搜索",
            "requires": ["xhs_goto_home", "xhs_browse", "rest", "go_back"], "allows": ["xhs_click_note", "xhs_scroll_feed", "rest", "go_back"],
            "can_be_first": True, "desc": "在小红书搜索关键词"
        },
        "xhs_follow": {
            "platform": "xiaohongshu", "category": "interact", "label": "📕 关注",
            "requires": ["xhs_click_note"], "allows": ["xhs_like", "xhs_comment", "rest", "go_back"],
            "can_be_first": False, "desc": "小红书关注当前笔记作者"
        },
        "xhs_collect": {
            "platform": "xiaohongshu", "category": "interact", "label": "📕 收藏",
            "requires": ["xhs_click_note"], "allows": ["xhs_like", "xhs_comment", "rest", "go_back"],
            "can_be_first": False, "desc": "小红书收藏当前笔记"
        },

        # ── 主页信息读取类 ──
        "xhs_goto_profile": {
            "platform": "xiaohongshu", "category": "browse", "label": "👤 进入个人主页",
            "requires": ["xhs_goto_home", "rest", "go_back"],
            "allows": ["xhs_read_nickname", "xhs_read_user_id", "xhs_read_following", "xhs_read_fans", "xhs_read_likes", "xhs_read_bio", "rest", "go_back"],
            "can_be_first": False, "desc": "点击底部导航「我」进入小红书个人主页"
        },
        "xhs_read_nickname": {
            "platform": "xiaohongshu", "category": "interact", "label": "📝 读取昵称",
            "requires": ["xhs_goto_profile"], "allows": ["xhs_read_user_id", "xhs_read_following", "xhs_read_fans", "xhs_read_likes", "xhs_read_bio", "rest", "go_back"],
            "can_be_first": False, "desc": "从个人主页读取用户昵称"
        },
        "xhs_read_user_id": {
            "platform": "xiaohongshu", "category": "interact", "label": "🔢 读取小红书号",
            "requires": ["xhs_goto_profile"], "allows": ["xhs_read_nickname", "xhs_read_following", "xhs_read_fans", "xhs_read_likes", "xhs_read_bio", "rest", "go_back"],
            "can_be_first": False, "desc": "从个人主页读取小红书号（数字ID）"
        },
        "xhs_read_following": {
            "platform": "xiaohongshu", "category": "interact", "label": "👥 读取关注数",
            "requires": ["xhs_goto_profile"], "allows": ["xhs_read_nickname", "xhs_read_user_id", "xhs_read_fans", "xhs_read_likes", "xhs_read_bio", "rest", "go_back"],
            "can_be_first": False, "desc": "从个人主页读取关注人数"
        },
        "xhs_read_fans": {
            "platform": "xiaohongshu", "category": "interact", "label": "👥 读取粉丝数",
            "requires": ["xhs_goto_profile"], "allows": ["xhs_read_nickname", "xhs_read_user_id", "xhs_read_following", "xhs_read_likes", "xhs_read_bio", "rest", "go_back"],
            "can_be_first": False, "desc": "从个人主页读取粉丝数"
        },
        "xhs_read_likes": {
            "platform": "xiaohongshu", "category": "interact", "label": "👍 读取获赞数",
            "requires": ["xhs_goto_profile"], "allows": ["xhs_read_nickname", "xhs_read_user_id", "xhs_read_following", "xhs_read_fans", "xhs_read_bio", "rest", "go_back"],
            "can_be_first": False, "desc": "从个人主页读取获赞与收藏总数"
        },
        "xhs_read_bio": {
            "platform": "xiaohongshu", "category": "interact", "label": "📄 读取简介",
            "requires": ["xhs_goto_profile"], "allows": ["xhs_read_nickname", "xhs_read_user_id", "xhs_read_following", "xhs_read_fans", "xhs_read_likes", "rest", "go_back"],
            "can_be_first": False, "desc": "从个人主页读取个人简介"
        },
        # ═══════════════════════════════════════════════════
        # ⚙️ 通用工具（所有平台可用）
        # ═══════════════════════════════════════════════════

        "go_back": {
            "platform": "通用", "category": "utility", "label": "⬅ 返回",
            "requires": ["*"], "allows": ["*"],
            "can_be_first": False, "desc": "浏览器后退，回到上一页"
        },
        "rest": {
            "platform": "通用", "category": "utility", "label": "⏳ 休息",
            "requires": [], "allows": ["*"],
            "can_be_first": True, "desc": "随机休息 5~20秒，模拟真人操作间隔"
        },
        "account_check_status": {
            "platform": "通用", "category": "utility", "label": "📊 检查登录状态",
            "requires": ["goto_home", "xhs_goto_home", "rest"],
            "allows": ["goto_home", "xhs_goto_home", "browse_feed", "xhs_browse", "rest", "go_back"],
            "can_be_first": True, "desc": "检测当前账号登录状态是否正确（页面级验证）"
        },
        "account_read_info": {
            "platform": "通用", "category": "utility", "label": "📋 读取账号信息",
            "requires": ["goto_home", "xhs_goto_home", "account_check_status"],
            "allows": ["goto_home", "xhs_goto_home", "rest", "go_back"],
            "can_be_first": False, "desc": "读取账号基础信息（昵称/粉丝数/作品数等），输出到日志"
        },
    }

    def list_atomic_ops(self) -> list[dict]:
        """列出所有可用原子操作（含依赖约束）"""
        # 从 douyin_ops.py 和 ops/xhs_ops.py 提取异步函数
        parsed_ops = []
        import ast

        scan_configs = [
            ("douyin_ops.py", "douyin"),
            ("ops/xhs_ops.py", "xiaohongshu"),
        ]

        for rel_path, platform in scan_configs:
            try:
                ops_file = MATRIX_SCRIPTS / rel_path
                if not ops_file.exists():
                    continue
                tree = ast.parse(ops_file.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.AsyncFunctionDef) and not node.name.startswith("_"):
                        doc = ast.get_docstring(node) or ""
                        name = node.name
                        if name not in self.OP_GRAPH:
                            parsed_ops.append({
                                "name": name,
                                "type": platform,
                                "doc": doc.split("\n")[0] if doc else "",
                                "source": ops_file.name,
                                "category": "auto",
                                "platform": platform,
                                "requires": [],
                                "allows": ["*"],
                                "can_be_first": True,
                                "label": name,
                                "desc": doc.split("\n")[0] if doc else "",
                            })
            except:
                pass

        # 合并手动定义的标准操作
        result = {op["name"]: op for op in parsed_ops}
        for name, info in self.OP_GRAPH.items():
            result[name] = {
                "name": name,
                "type": info["category"],
                "doc": info["desc"],
                "source": "graph",
                "platform": info.get("platform", "通用"),
                "category": info["category"],
                "label": info["label"],
                "desc": info["desc"],
                "requires": info["requires"],
                "allows": info["allows"],
                "can_be_first": info["can_be_first"],
            }

        return sorted(result.values(), key=lambda x: (x.get("category", "z"), x["name"]))

    def validate_blueprint_steps(self, steps: list[dict]) -> dict:
        """校验蓝图的步骤编排合法性
        新增平台一致性检查：抖音操作不能和小红书操作混排
        """
        errors = []
        warnings = []
        detected_platform = None

        for i, step in enumerate(steps):
            name = step.get("name", "")
            info = self.OP_GRAPH.get(name)
            if not info:
                continue

            step_platform = info.get("platform", "通用")

            # 平台一致性
            if step_platform != "通用":
                if detected_platform is None:
                    detected_platform = step_platform
                elif detected_platform != step_platform:
                    errors.append({
                        "step": i + 1, "op": name,
                        "msg": f'跨平台操作: 蓝图已用"{detected_platform}"，步骤{i+1}"{info["label"]}"属于"{step_platform}"'
                    })

            # 首步检查
            if i == 0 and not info["can_be_first"]:
                errors.append({"step": i + 1, "op": name, "msg": f'"{info["label"]}" 不能作为首步'})

            # 前置约束
            if i > 0 and info["requires"] and info["requires"] != ["*"]:
                prev_names = [s.get("name", "") for s in steps[:i]]
                if not any(r in prev_names for r in info["requires"] if r != "*"):
                    errors.append({"step": i + 1, "op": name, "msg": f'"{info["label"]}" 前置未满足: {info["requires"]}'})

            # 后继允许
            if i > 0:
                prev_info = self.OP_GRAPH.get(steps[i - 1].get("name", ""))
                if prev_info and prev_info["allows"] != ["*"] and name not in prev_info["allows"]:
                    errors.append({"step": i + 1, "op": name, "msg": f'上一步"{prev_info["label"]}"不能接"{info["label"]}"'})

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def list_blueprints(self) -> list[dict]:
        """列出所有已保存蓝图"""
        blueprints = []
        if MATRIX_BLUEPRINTS.exists():
            for f in sorted(MATRIX_BLUEPRINTS.iterdir()):
                if f.suffix in (".yaml", ".yml", ".json"):
                    try:
                        bp = yaml.safe_load(f.read_text()) if f.suffix != ".json" else json.loads(f.read_text())
                        if isinstance(bp, dict):
                            blueprints.append({
                                "name": bp.get("name", bp.get("id", f.stem)),
                                "file": f.name,
                                "steps": bp.get("steps", bp.get("actions", [])),
                                "step_count": len(bp.get("steps", bp.get("actions", []))),
                                "type": f.name.split("_")[0],
                                "platform": bp.get("platform", "douyin"),
                                "description": bp.get("description", ""),
                            })
                    except:
                        pass
        return blueprints

    def save_blueprint(self, name: str, data: dict) -> dict:
        """保存蓝图（新建或覆盖）"""
        blueprint = {
            "name": name,
            "id": name,
            "version": "1.0",
            "platform": data.get("platform", "douyin"),
            "description": data.get("description", ""),
            "steps": data.get("steps", []),
            "actions": data.get("steps", []),
            "created_at": datetime.now().isoformat(),
        }
        file_path = MATRIX_BLUEPRINTS / f"{name}.json"
        file_path.write_text(json.dumps(blueprint, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"status": "ok", "file": str(file_path), "steps": len(blueprint["steps"])}

    def delete_blueprint(self, name: str) -> dict:
        """删除蓝图"""
        for suffix in [".json", ".yaml", ".yml"]:
            f = MATRIX_BLUEPRINTS / f"{name}{suffix}"
            if f.exists():
                f.unlink()
                return {"status": "ok", "deleted": str(f)}
        raise ValueError(f"蓝图 {name} 不存在")

    def execute_blueprint(self, blueprint_name: str, account_id: str) -> dict:
        """对指定账号执行蓝图"""
        acct = self.get_account(account_id)
        if not acct:
            raise ValueError(f"账号 {account_id} 不存在")

        # 查找蓝图文件
        bp_file = None
        for suffix in [".json", ".yaml", ".yml"]:
            f = MATRIX_BLUEPRINTS / f"{blueprint_name}{suffix}"
            if f.exists():
                bp_file = f
                break
        if not bp_file:
            raise ValueError(f"蓝图 {blueprint_name} 不存在")

        log_file = f"/tmp/matrix_mgmt_bp_{blueprint_name}_{account_id}_{int(time.time())}.log"
        cmd = f"cd {MATRIX_SCRIPTS} && {PYTHON} task_engine.py --blueprint {bp_file.stem} --account {account_id} > {log_file} 2>&1 &"
        subprocess.Popen(cmd, shell=True)
        return {"status": "started", "blueprint": blueprint_name, "account": account_id, "log": log_file}

    # ═══════════════════════════════════════════════════════════
    # 导入导出
    # ═══════════════════════════════════════════════════════════

    def export_accounts(self, output_path: str = None) -> str:
        """导出账号配置 + Cookie 为 ZIP"""
        if not output_path:
            output_path = f"/tmp/matrix_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. 账号配置
            if MATRIX_ACCOUNTS_CFG.exists():
                zf.write(MATRIX_ACCOUNTS_CFG, "config/accounts.yaml")

            # 2. Cookie 文件 + 身份配置
            for identity_dir in MATRIX_IDENTITIES.iterdir():
                if not identity_dir.is_dir():
                    continue
                # config.yaml
                cfg = identity_dir / "config.yaml"
                if cfg.exists():
                    zf.write(cfg, f"identities/{identity_dir.name}/config.yaml")
                # fingerprint.pkl
                fp = identity_dir / "fingerprint.pkl"
                if fp.exists():
                    zf.write(fp, f"identities/{identity_dir.name}/fingerprint.pkl")
                # cookies.sqlite
                ck = identity_dir / "user_data" / "cookies.sqlite"
                if ck.exists():
                    zf.write(ck, f"identities/{identity_dir.name}/cookies.sqlite")

        return output_path

    def import_accounts(self, zip_path: str, overwrite: bool = False) -> dict:
        """从 ZIP 导入账号配置 + Cookie"""
        result = {"accounts_imported": 0, "identities_imported": 0, "warnings": []}

        with zipfile.ZipFile(zip_path, "r") as zf:
            # 1. 导入账号配置
            if "config/accounts.yaml" in zf.namelist():
                target = MATRIX_ACCOUNTS_CFG
                if target.exists() and not overwrite:
                    result["warnings"].append("accounts.yaml 已存在（使用 overwrite=True 覆盖）")
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    zf.extract("config/accounts.yaml", target.parent)
                    result["accounts_imported"] = 1

            # 2. 导入身份和 Cookie
            for name in zf.namelist():
                if name.startswith("identities/") and name.endswith("cookies.sqlite"):
                    parts = name.split("/")
                    if len(parts) >= 3:
                        identity_name = parts[1]
                        target_dir = MATRIX_IDENTITIES / identity_name / "user_data"
                        target_dir.mkdir(parents=True, exist_ok=True)
                        zf.extract(name, target_dir.parent)
                        result["identities_imported"] += 1

                elif name.startswith("identities/") and name.endswith(("config.yaml", "fingerprint.pkl")):
                    target_path = MATRIX_IDENTITIES / "/".join(name.split("/")[1:])
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    zf.extract(name, MATRIX_IDENTITIES.parent)
                    if name.endswith("config.yaml"):
                        result["identities_imported"] = result.get("identities_imported", 0) + 0.5

        return result

    # ═══════════════════════════════════════════════════════════
    # 备份恢复
    # ═══════════════════════════════════════════════════════════

    def list_backups(self) -> list[dict]:
        """列出所有可用的备份快照"""
        backups = []
        backup_root = MATRIX_BACKUPS / "cookies"
        if not backup_root.exists():
            return backups
        for identity_dir in sorted(backup_root.iterdir()):
            if not identity_dir.is_dir():
                continue
            files = sorted(identity_dir.glob("*.bak"), key=lambda f: f.stat().st_mtime, reverse=True)
            for f in files:
                # 文件名格式: cookies.{timestamp}.{platform}.{label}.bak
                parts = f.stem.split(".")
                ts_str = parts[1] if len(parts) > 1 else "00000000_000000"
                platform = parts[2] if len(parts) > 2 else "unknown"
                label = ".".join(parts[3:]) if len(parts) > 3 else ""
                try:
                    ts = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                    time_str = ts.strftime("%m-%d %H:%M")
                except:
                    time_str = ts_str
                backups.append({
                    "identity": identity_dir.name,
                    "file": f.name,
                    "path": str(f),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "timestamp": ts_str,
                    "time_str": time_str,
                    "platform": platform,
                    "label": label,
                })
        return backups

    def create_backup(self, label: str = "manual") -> dict:
        """创建全量备份（调用 cookie_manager 的 backup_all_identities）"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "cookie_manager",
                MATRIX_SCRIPTS / "matrix_modules" / "utils" / "cookie_manager.py"
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.backup_all_identities(platform="dashboard", label=label)
            count = sum(1 for v in result.values() if v)
            return {"status": "ok", "backup_count": count, "details": result}
        except Exception as e:
            # fallback: 手动复制 cookie 文件
            count = 0
            for identity_dir in MATRIX_IDENTITIES.iterdir():
                if not identity_dir.is_dir():
                    continue
                cookie = identity_dir / "user_data" / "cookies.sqlite"
                if cookie.exists():
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_dir = MATRIX_BACKUPS / "cookies" / identity_dir.name
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(cookie, backup_dir / f"cookies.{ts}.dashboard.{label}.bak")
                    count += 1
            return {"status": "ok", "backup_count": count, "method": "manual_copy"}

    def restore_backup(self, identity: str, backup_path: str) -> dict:
        """从备份文件恢复指定身份的 Cookie"""
        target_cookie = MATRIX_IDENTITIES / identity / "user_data" / "cookies.sqlite"
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise ValueError(f"备份文件不存在: {backup_path}")
        if not target_cookie.parent.exists():
            raise ValueError(f"身份目录不存在: {identity}")

        # 先创建当前状态的备份（安全保护）
        if target_cookie.exists():
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_bak = MATRIX_BACKUPS / "cookies" / identity / f"cookies.{ts}.pre_restore.bak"
            safe_bak.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(target_cookie, safe_bak)

        # 恢复
        import shutil
        shutil.copy2(backup_file, target_cookie)
        return {
            "status": "ok",
            "identity": identity,
            "restored_from": str(backup_file),
            "size_kb": round(backup_file.stat().st_size / 1024, 1),
        }

    # ═══════════════════════════════════════════════════════════
    # 跨机注册表: Registry (L0) + Override (L1) 双源读取
    # ═══════════════════════════════════════════════════════════

    REGISTRY_PATH = MATRIX_CODE / "accounts_registry.yaml"
    OVERRIDE_PATH = MATRIX_LOCAL / "config" / "accounts.override.yaml"
    LEGACY_PATH = MATRIX_LOCAL / "config" / "accounts.yaml"
    CROSS_MACHINE_DIR = AGENT_SYNC / "04_memory" / "cross_machine" / "data" / "matrix"

    # ── WPRA v2.0: 写分区·读聚合路径 ──
    MACHINES_DIR = AGENT_SYNC / "04_memory" / "cross_machine" / "machines"

    def _local_uid(self) -> str:
        """读取本机 machine_uid"""
        uid_file = AGENT_LOCAL / "identity" / "machine_uid"
        if uid_file.exists():
            return uid_file.read_text().strip()
        return self._local_hostname()  # 降级

    def _my_machine_dir(self) -> Path:
        """本机 WPRA 命名空间目录"""
        d = self.MACHINES_DIR / self._local_uid()
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _read_all_machines_accounts(self) -> list[dict]:
        """WPRA: 遍历所有机器的 accounts.yaml，聚合完整账号注册表

        替代旧的 accounts_registry.yaml 单文件。
        每台机器只写自己的 accounts.yaml，不存在则跳过。
        """
        all_accounts = []
        if not self.MACHINES_DIR.exists():
            return all_accounts

        for machine_dir in sorted(self.MACHINES_DIR.iterdir()):
            if not machine_dir.is_dir():
                continue
            acct_file = machine_dir / "accounts.yaml"
            if not acct_file.exists():
                continue
            try:
                data = yaml.safe_load(acct_file.read_text()) or {}
                accounts = data.get("accounts", [])
                source_uid = data.get("machine_uid", machine_dir.name)
                source_name = data.get("machine_name", source_uid[:8])
                for acct in accounts:
                    acct["_source_machine_uid"] = source_uid
                    acct["_source_machine_name"] = source_name
                    acct["_source_machine_host"] = data.get("machine_name", source_uid[:8])
                    # 兼容旧字段名
                    if "assigned_machine" not in acct:
                        acct["assigned_machine"] = source_name
                    all_accounts.append(acct)
            except Exception as e:
                print(f"  跳过 {machine_dir.name}/accounts.yaml: {e}")
                continue

        return all_accounts

    def _write_self_accounts(self):
        """WPRA: 将本机管理的账号写入 machines/{uid}/accounts.yaml

        只写 assigned_machine == 本机 的账号，不碰其他机器的。
        每台机器只写自己的文件，永不冲突。
        """
        # 从 override 读取本机账号
        hostname, override = self._read_override()
        override_map = {a["id"]: a for a in override}
        local_hostname = self._local_hostname()

        # 从 registry 获取完整账号列表，筛选属于本机的
        registry = self._read_registry()
        my_accounts = []
        for acct in registry:
            am = acct.get("assigned_machine", "")
            is_local = (am == local_hostname) or (acct["id"] in override_map)
            if not is_local:
                continue
            ovr = override_map.get(acct["id"], {})
            merged = {
                "id": acct["id"],
                "platform": acct.get("platform", ""),
                "phone_mask": ovr.get("phone", acct.get("phone_mask", "")),
                "assigned_machine": local_hostname,
                "identity_hint": ovr.get("identity_hint", acct.get("identity_hint", acct["id"])),
                "enabled": ovr.get("enabled", acct.get("enabled", True)),
                "notes": ovr.get("notes", acct.get("notes", "")),
            }
            my_accounts.append(merged)

        # 兜底: 如果 registry 不存在（accounts_registry.yaml 已废弃），
        # 直接用 override 作为本机账号列表
        if not my_accounts and override_map:
            for oid, ovr_acct in override_map.items():
                identity_hint = ovr_acct.get("identity_dir", ovr_acct.get("identity_hint", oid)).replace("identities/", "")
                my_accounts.append({
                    "id": oid,
                    "platform": ovr_acct.get("platform", "douyin"),
                    "phone_mask": ovr_acct.get("phone", ""),
                    "assigned_machine": local_hostname,
                    "identity_hint": identity_hint,
                    "enabled": ovr_acct.get("enabled", True),
                    "notes": ovr_acct.get("notes", ""),
                })

        # 兜底: 扫描本地 accounts.yaml，把本机有身份目录的账号都写进去
        # 每台机器独立声明，不查其他机器的数据（WPRA 读聚合时再处理重复）
        if self.LEGACY_PATH.exists():
            try:
                legacy_data = yaml.safe_load(self.LEGACY_PATH.read_text()) or {}
                legacy_accounts = legacy_data.get("accounts", [])
                existing_ids = {a["id"] for a in my_accounts}
                for acct in legacy_accounts:
                    aid = acct.get("id", "")
                    if not aid or aid in existing_ids:
                        continue
                    existing_ids.add(aid)
                    my_accounts.append({
                        "id": aid,
                        "platform": acct.get("platform", ""),
                        "phone_mask": acct.get("phone", acct.get("phone_mask", "")),
                        "assigned_machine": local_hostname,
                        "identity_hint": acct.get("identity_dir", aid).replace("identities/", ""),
                        "enabled": acct.get("enabled", True),
                        "notes": acct.get("notes", "本地账号 (来自 legacy accounts.yaml)"),
                    })
            except Exception as e:
                print(f"  读取本地 accounts.yaml 兜底失败: {e}")

        # WPRA 格式写入
        output = {
            "schema_version": "2.0",
            "file_schema": "accounts-v2",
            "machine_uid": self._local_uid(),
            "machine_name": local_hostname,
            "updated_at": datetime.now().isoformat(),
            "accounts": my_accounts,
        }
        target = self._my_machine_dir() / "accounts.yaml"
        target.write_text(
            yaml.dump(output, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def _read_registry(self) -> list:
        """读取 L0 注册表 (Gitee 同步, 所有账号定义)"""
        if not self.REGISTRY_PATH.exists():
            return []
        try:
            data = yaml.safe_load(self.REGISTRY_PATH.read_text()) or {}
            return data.get("accounts", [])
        except Exception as e:
            print(f"读取 registry 失败: {e}")
            return []

    def _read_override(self) -> tuple[str, list]:
        """读取 L1 覆写 (agent-local, 本机敏感字段)
        返回 (hostname, accounts_list)
        """
        path = self.OVERRIDE_PATH
        if not path.exists():
            return ("", [])
        try:
            data = yaml.safe_load(path.read_text()) or {}
            return (data.get("hostname", ""), data.get("accounts", []))
        except:
            return ("", [])

    def _local_hostname(self) -> str:
        """优先读取缓存的 hostname, fallback os.uname"""
        hn_file = AGENT_LOCAL / "identity" / "cached_hostname"
        if hn_file.exists():
            return hn_file.read_text().strip()
        return os.uname().nodename

    def list_accounts(self) -> list[dict]:
        """合并 Registry + Override 输出完整账号列表

        WPRA v2.0: 优先读取 machines/*/accounts.yaml (写分区数据)
        如果不存在，降级到旧的 accounts_registry.yaml (向后兼容)
        同时检查本机身份目录和登录状态

        去重规则: 同一 account_id 出现在多台机器时:
          1. 优先保留 assigned_machine == source_machine 的权威声明
          2. 否则保留本地机器的版本
          3. 否则保留最新时间戳的版本
        """
        # ── WPRA v2.0: 优先读取所有机器的 accounts.yaml ──
        wpra_accounts = self._read_all_machines_accounts()
        if wpra_accounts:
            registry = wpra_accounts
        else:
            # 降级: 旧 accounts_registry.yaml
            registry = self._read_registry()
        hostname, override = self._read_override()
        override_map = {a["id"]: a for a in override}
        local_hostname = self._local_hostname()

        # ── 去重: 同一 ID 多机器时只保留权威版本 ──
        deduped = {}
        for acct in registry:
            aid = acct["id"]
            src_machine = acct.get("_source_machine_name", "") or acct.get("assigned_machine", "")
            am = acct.get("assigned_machine", "")

            if aid not in deduped:
                deduped[aid] = acct
                continue

            # 冲突! 同一 ID 出现在多台机器
            existing = deduped[aid]
            existing_src = existing.get("_source_machine_name", "") or existing.get("assigned_machine", "")
            existing_am = existing.get("assigned_machine", "")

            # 规则1: 权威声明优先 (assigned_machine == source)
            current_authoritative = (am == src_machine)
            existing_authoritative = (existing_am == existing_src)

            if current_authoritative and not existing_authoritative:
                deduped[aid] = acct
            elif current_authoritative == existing_authoritative:
                # 规则2: 本机版本优先
                if src_machine == local_hostname:
                    deduped[aid] = acct
                elif existing_src == local_hostname:
                    pass  # keep existing
                else:
                    # 规则3: 最新时间戳
                    cur_ts = acct.get("updated_at", "")
                    ext_ts = existing.get("updated_at", "")
                    if cur_ts > ext_ts:
                        deduped[aid] = acct

        # ── 补充: override 中有但 wpra/registry 中没有的账号（新创建）──
        for oid, ovr_acct in override_map.items():
            if oid not in deduped:
                deduped[oid] = ovr_acct

        # 是否为当前机器:
        # 1) assigned_machine == 本机
        # 2) override 中有配置
        # 3) 同时在本地有身份目录 + Cookie (兜底)
        def is_local(acct: dict) -> bool:
            am = acct.get("assigned_machine", "")
            if am == local_hostname:
                return True
            if acct["id"] in override_map:
                # ORACLE 如果已将本账号分配给其他机器，以 ORACLE 为准
                if am and am != local_hostname:
                    return False
                return True
            # 兜底: 仅当其他机器都没声明此 ID 时才用身份目录判断
            # (避免 xhs_01 被 5kecheng 声明了却在本机显示为 local)
            for other_aid, other_amt in _all_assignments.items():
                if other_aid == acct["id"] and other_amt != local_hostname and other_amt:
                    return False
            # 检查本地身份目录
            candidates = [acct["id"],
                          acct.get("identity_hint", ""),
                          acct.get("identity_dir", "").replace("identities/", "")]
            for hint in candidates:
                if not hint:
                    continue
                if self._identity_exists_by_hint(hint):
                    status = self._check_login_status_by_hint(hint)
                    if status == "logged_in":
                        return True
            return False

        # ── ORACLE.yaml 权威源: 覆盖 owner_machine ──
        try:
            ORACLE_PATH = AGENT_SYNC / "ORACLE.yaml"
            if ORACLE_PATH.exists():
                import yaml
                oracle = yaml.safe_load(ORACLE_PATH.read_text())
                oracle_map = {}
                for entry in oracle.get("accounts", []):
                    machine = entry.get("assigned_machine", "") or entry.get("machine", "")
                    for plat, acct_id in entry.get("platforms", {}).items():
                        oracle_map[acct_id] = machine
                for acct in deduped.values():
                    oid = acct["id"]
                    if oid in oracle_map:
                        acct["assigned_machine"] = oracle_map[oid]
                        acct["owner_machine"] = oracle_map[oid]
        except Exception:
            pass

        # 构建所有机器的 assignment 映射 (用于 is_local 兜底判断)
        _all_assignments = {a["id"]: a.get("assigned_machine", "") for a in deduped.values()}

        result = []
        for acct in deduped.values():
            aid = acct["id"]
            ovr = override_map.get(aid, {})

            # 合并字段: Registry 为基础, Override 覆写
            merged = dict(acct)
            merged["phone"] = str(ovr.get("phone", acct.get("phone_mask", "")) or "")
            merged["phone_mask"] = str(acct.get("phone_mask", ""))
            merged["proxy"] = ovr.get("proxy", acct.get("proxy", None))
            merged["enabled"] = ovr.get("enabled", acct.get("enabled", True))
            merged["is_local"] = is_local(acct)
            merged["owner_machine"] = acct.get("assigned_machine", "")

            # identity_dir 解析: 优先 override, 再 registry hint
            identity_hint = acct.get("identity_hint", aid)
            if ovr.get("identity_dir"):
                merged["identity_dir"] = ovr["identity_dir"]
            else:
                merged["identity_dir"] = f"identities/{identity_hint}"

            # 状态
            if not merged["enabled"]:
                merged["_status"] = "disabled"
            elif not merged["is_local"]:
                merged["_status"] = "remote"
            else:
                merged["_status"] = self._check_login_status_by_hint(identity_hint)
                # 兜底: 如果 registry 的 identity_hint 不匹配本地目录，
                # 用 account id 作为 hint 重试 (如 xhs_01)
                if merged["_status"] in ("no_cookie", "no_identity") and identity_hint != aid:
                    alt_status = self._check_login_status_by_hint(aid)
                    if alt_status == "logged_in":
                        merged["_status"] = alt_status
                        merged["identity_hint"] = aid
                        merged["identity_dir"] = f"identities/{aid}"
                # 上次执行日志详情（不读 SQLite，零锁竞争）
                merged["_log_detail"] = self._get_log_detail(identity_hint)
                if merged["_status"] == "no_cookie" and identity_hint != aid:
                    merged["_log_detail"] = self._get_log_detail(aid)
            merged["_identity_dir_exists"] = self._identity_exists_by_hint(identity_hint) or self._identity_exists_by_hint(aid)

            result.append(merged)

        # 兜底: 合并本地 accounts.yaml 中全所未有的孤儿账号
        # 避免 xhs_01 这种已经被其他机器声明的情况重复
        result_ids = {a["id"] for a in result}
        if self.LEGACY_PATH.exists():
            try:
                legacy_data = yaml.safe_load(self.LEGACY_PATH.read_text()) or {}
                for acct in legacy_data.get("accounts", []):
                    aid = acct.get("id", "")
                    if not aid or aid in result_ids:
                        continue
                    result_ids.add(aid)
                    identity_hint = acct.get("identity_dir", aid).replace("identities/", "")
                    merged = {
                        "id": aid,
                        "platform": acct.get("platform", ""),
                        "phone": acct.get("phone", ""),
                        "phone_mask": acct.get("phone_mask", ""),
                        "enabled": acct.get("enabled", True),
                        "notes": acct.get("notes", "本地未注册"),
                        "is_local": True,
                        "owner_machine": local_hostname,
                        "identity_hint": identity_hint,
                        "identity_dir": acct.get("identity_dir", f"identities/{identity_hint}"),
                        "_status": self._check_login_status_by_hint(identity_hint),
                        "_identity_dir_exists": self._identity_exists_by_hint(identity_hint),
                        "_source": "legacy_local",
                    }
                    result.append(merged)
            except Exception:
                pass

        return result

    def _check_login_status_by_hint(self, hint: str) -> str:
        """通过 identity_hint 检查账号状态（不读 SQLite，不卡锁）

        核心原则：
          - 不打开 cookies.sqlite（零锁竞争）
          - 用文件存在性 + 上次任务日志判断状态
          - 兼容前端已有的 _status 取值（'logged_in'/'no_cookie'/'remote'/'disabled'）

        状态映射：
          cookies.sqlite 文件存在 + 上次日志成功结束 → logged_in（兼容旧逻辑）
          cookies.sqlite 文件存在 + 日志触发短信跳过  → logged_in（仍标为可操作）
          cookies.sqlite 文件存在 + 日志失败          → logged_in（兜底）
          cookies.sqlite 文件不存在或为空              → no_cookie
        """
        if not hint:
            return "no_identity"
        cookie_path = MATRIX_IDENTITIES / hint / "user_data" / "cookies.sqlite"
        if not cookie_path.exists() or cookie_path.stat().st_size < 100:
            return "no_cookie"
        # 尽量兼容旧逻辑：有 cookie 文件就算 logged_in（前端不影响）
        # 同时通过 _log_status 字段传递更丰富的状态信息
        return "logged_in"

    def _get_log_detail(self, hint: str) -> dict:
        """获取该账号上次执行日志的详细信息（供前端展示）

        Returns:
          {"exists": true/false, "last_status": "success"|"sms_skip"|"failed"|"unknown",
           "last_time": "2026-07-12 20:08", "last_cmd": "nurture"}
        """
        result = {"exists": False, "last_status": "unknown", "last_time": "", "last_cmd": ""}
        log_dir = Path.home() / "workbuddy-agent-os" / "agent-local" / "runtime" / "guardd" / "tasks"
        if not log_dir.exists():
            return result
        # 缓存日志文件列表（只 stat 一次，避免重复 syscall）
        if not hasattr(self, "_log_files_cache"):
            self._log_files_cache = {}
            try:
                for f in log_dir.iterdir():
                    if f.name.endswith(".log"):
                        try:
                            self._log_files_cache[f.name] = f.stat().st_mtime
                        except OSError:
                            pass
            except PermissionError:
                return result
        candidate = None
        for fname, mtime in self._log_files_cache.items():
            if hint not in fname:
                continue
            if candidate is None or mtime > candidate[0]:
                candidate = (mtime, fname)
        if not candidate:
            return result
        mtime, fname = candidate
        result["exists"] = True
        result["last_time"] = datetime.fromtimestamp(mtime).strftime("%m-%d %H:%M")
        # 从文件名取 cmd_type
        parts = Path(fname).stem.split("_")
        result["last_cmd"] = parts[0] if parts else ""
        try:
            text = (log_dir / fname).read_text(encoding="utf-8", errors="replace")
            # 先检测短信触发（优先级最高：多条日志可能同时有 ✅ 和 短信验证）
            if any(kw in text for kw in ["短信验证", "auto_verify 返回 False", "需手动登录", "sms_login", "SmsRecovery"]):
                result["last_status"] = "sms_skip"
            # 再检测完成状态
            elif "✅" in text and "🛑 浏览器已关闭" in text:
                if "skip_sms" in text or "跳过短信" in text:
                    result["last_status"] = "sms_skip"
                else:
                    result["last_status"] = "success"
            # 失败
            elif "❌" in text or "Error" in text or "failed" in text.lower():
                result["last_status"] = "failed"
            # 兜底
            else:
                result["last_status"] = "running"
        except Exception:
            pass
        return result

    def _identity_exists_by_hint(self, hint: str) -> bool:
        if not hint:
            return False
        return (MATRIX_IDENTITIES / hint).exists()

    # ── 向后兼容（保留对旧 accounts.yaml 的支持）──

    def _read_accounts_yaml(self) -> list:
        """向后兼容: 合并 override + 旧版 accounts.yaml（override 优先）"""
        # 先读 override（最完整，包含本机所有账号）
        try:
            if self.OVERRIDE_PATH.exists():
                data = yaml.safe_load(self.OVERRIDE_PATH.read_text()) or {}
                override_accounts = data.get("accounts", [])
                override_ids = {a["id"] for a in override_accounts if "id" in a}
            else:
                override_accounts, override_ids = [], set()
        except:
            override_accounts, override_ids = [], set()

        # 再读 legacy，补上没有的
        if self.LEGACY_PATH.exists():
            try:
                legacy_data = yaml.safe_load(self.LEGACY_PATH.read_text()) or {}
                for acct in legacy_data.get("accounts", []):
                    if acct.get("id") and acct["id"] not in override_ids:
                        override_accounts.append(acct)
                        override_ids.add(acct["id"])
            except:
                pass

        if override_accounts:
            return override_accounts
        # fallback: registry + override 合成
        return self.list_accounts()

    def _write_accounts_yaml(self, accounts: list):
        """向后兼容: 写回 override (不再是 accounts.yaml)"""
        if self.OVERRIDE_PATH.exists():
            existing = yaml.safe_load(self.OVERRIDE_PATH.read_text()) or {}
        else:
            existing = {"version": "1.0", "hostname": self._local_hostname()}
        existing["accounts"] = accounts
        self.OVERRIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.OVERRIDE_PATH.write_text(
            yaml.dump(existing, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def _check_login_status(self, acct: dict) -> str:
        return self._check_login_status_by_hint(
            acct.get("identity_hint", acct.get("identity_dir", acct["id"])).replace("identities/", "")
        )

    def _identity_exists(self, acct: dict) -> bool:
        return self._identity_exists_by_hint(
            acct.get("identity_hint", acct.get("identity_dir", acct["id"])).replace("identities/", "")
        )

    def _count_backups(self, acct: dict) -> int:
        hint = acct.get("identity_hint", acct.get("identity_dir", acct["id"])).replace("identities/", "")
        if not hint:
            return 0
        backup_dir = MATRIX_BACKUPS / "cookies" / hint
        if backup_dir.exists():
            return len(list(backup_dir.glob("*.bak")))
        return 0

    # ═══════════════════════════════════════════════════════════
    # L2 运行时状态推送到 cross_machine (供 Dashboard 聚合)
    # ═══════════════════════════════════════════════════════════

    def publish_status(self) -> dict:
        """将本机各账号状态写入 cross_machine/data/matrix/{uid}.json
        供其他机器的 Dashboard 读取展示
        """
        accounts = self.list_accounts()
        local = [a for a in accounts if a.get("is_local")]

        status = {
            "hostname": self._local_hostname(),
            "timestamp": datetime.now().isoformat(),
            "total_accounts": len(accounts),
            "total_local": len(local),
            "accounts": {},
        }
        for a in accounts:
            status["accounts"][a["id"]] = {
                "platform": a.get("platform", ""),
                "phone_mask": a.get("phone_mask", ""),
                "owner_machine": a.get("owner_machine", ""),
                "is_local": a.get("is_local", False),
                "status": a.get("_status", "unknown"),
                "enabled": a.get("enabled", False),
            }

        # 写入 cross_machine
        import json
        uid_file = AGENT_LOCAL / "identity" / "machine_uid"
        uid = uid_file.read_text().strip() if uid_file.exists() else "unknown"
        self.CROSS_MACHINE_DIR.mkdir(parents=True, exist_ok=True)
        (self.CROSS_MACHINE_DIR / f"{uid}.json").write_text(
            json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # ── WPRA v2.0: 同步写入 machines/{uid}/accounts.yaml ──
        self._write_self_accounts()

        return status

    # ═══════════════════════════════════════════════════════════
    # 系统信息
    # ═══════════════════════════════════════════════════════════

    def system_info(self) -> dict:
        """返回系统概览信息"""
        accounts = self._read_accounts_yaml()
        enabled = sum(1 for a in accounts if a.get("enabled", False))
        logged_in = sum(1 for a in accounts if self._check_login_status(a) == "logged_in")
        identity_count = len([d for d in MATRIX_IDENTITIES.iterdir() if d.is_dir()])
        bp_count = len([f for f in MATRIX_BLUEPRINTS.iterdir() if f.suffix in (".json", ".yaml")])

        return {
            "total_accounts": len(accounts),
            "enabled_accounts": enabled,
            "logged_in_accounts": logged_in,
            "identity_dirs": identity_count,
            "blueprints": bp_count,
            "matrix_version": "4.2",
            "python": PYTHON,
            "matrix_cli": MATRIX_CLI,
            "data_root": str(MATRIX_LOCAL),
            "code_root": str(MATRIX_CODE),
        }

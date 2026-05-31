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
AGENT_SYNC = HOME / "workbuddy-agent-os" / "agent-sync"
AGENT_LOCAL = HOME / "workbuddy-agent-os" / "agent-local"

MATRIX_CODE = AGENT_SYNC / "05_tools" / "07_matrix"
MATRIX_SCRIPTS = MATRIX_CODE / "scripts"
MATRIX_LOCAL = AGENT_LOCAL / "tools" / "matrix"
MATRIX_IDENTITIES = MATRIX_LOCAL / "identities"
MATRIX_ACCOUNTS_CFG = MATRIX_LOCAL / "config" / "accounts.yaml"
MATRIX_BACKUPS = MATRIX_LOCAL / "backups"
MATRIX_BLUEPRINTS = MATRIX_CODE / "blueprints"
MATRIX_CONFIG_TEMPLATE = MATRIX_CODE / "config_template"
MATRIX_ACCOUNT_WORKSPACES = MATRIX_LOCAL / "accounts"

PYTHON = "/Users/5kecheng/.workbuddy/binaries/python/envs/agent-os/bin/python3"
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

        new_acct = {
            "id": data["id"],
            "platform": data["platform"],
            "phone": data.get("phone", ""),
            "identity_dir": data.get("identity_dir", f"identities/{data['id']}"),
            "window": [702, 783],
            "window_position": data.get("window_position", [0, 0]),
            "proxy": data.get("proxy", None),
            "enabled": data.get("enabled", True),
            "notes": data.get("notes", ""),
        }
        accounts.append(new_acct)
        self._write_accounts_yaml(accounts)

        # 创建身份目录
        identity_dir_name = new_acct["identity_dir"].replace("identities/", "")
        identity_path = MATRIX_IDENTITIES / identity_dir_name
        identity_path.mkdir(parents=True, exist_ok=True)
        (identity_path / "config.yaml").write_text(
            yaml.dump({"window": [702, 783], "screen": {"width": 702, "height": 783}}, default_flow_style=False),
            encoding="utf-8",
        )

        return {"status": "ok", "account": new_acct}

    def update_account(self, account_id: str, data: dict) -> dict:
        """更新账号配置"""
        accounts = self._read_accounts_yaml()
        found = None
        for acct in accounts:
            if acct["id"] == account_id:
                found = acct
                break
        if not found:
            raise ValueError(f"账号 {account_id} 不存在")

        for key in ["phone", "window", "window_position", "proxy", "enabled", "notes", "platform", "identity_dir"]:
            if key in data:
                found[key] = data[key]

        self._write_accounts_yaml(accounts)
        return {"status": "ok", "account": found}

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

    def list_atomic_ops(self) -> list[dict]:
        """列出所有可用原子操作"""
        ops = []

        # 从 douyin_ops.py 提取（基于函数名和文档）
        try:
            import ast
            ops_file = MATRIX_SCRIPTS / "douyin_ops.py"
            if ops_file.exists():
                tree = ast.parse(ops_file.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.AsyncFunctionDef) and not node.name.startswith("_"):
                        doc = ast.get_docstring(node) or ""
                        ops.append({
                            "name": node.name,
                            "type": "douyin",
                            "doc": doc.split("\n")[0] if doc else "",
                            "source": "douyin_ops.py",
                        })
        except:
            pass

        # 手动定义的核心操作
        core_ops = [
            {"name": "browse_feed", "type": "douyin", "doc": "浏览推荐视频流 (滑视频)", "source": "browse.py"},
            {"name": "like_video", "type": "douyin", "doc": "点赞当前视频", "source": "interact.py"},
            {"name": "collect_video", "type": "douyin", "doc": "收藏当前视频", "source": "interact.py"},
            {"name": "comment_video_a", "type": "douyin", "doc": "评论(PATH A:弹窗覆盖层 KeyX)", "source": "runner.py"},
            {"name": "comment_video_b", "type": "douyin", "doc": "评论(PATH B:全屏页 scroll+click)", "source": "runner.py"},
            {"name": "follow_user", "type": "douyin", "doc": "关注当前视频作者", "source": "interact.py"},
            {"name": "search_keyword", "type": "douyin", "doc": "搜索关键词并打开结果", "source": "browse.py"},
            {"name": "scroll_feed", "type": "douyin", "doc": "馈流下滑加载更多", "source": "browse.py"},
            {"name": "enter_video", "type": "douyin", "doc": "从推荐页点击进入视频播放页", "source": "browse.py"},
            {"name": "xhs_browse", "type": "xhs", "doc": "小红书瀑布流浏览", "source": "runner.py"},
            {"name": "xhs_click_note", "type": "xhs", "doc": "小红书点击笔记卡片", "source": "runner.py"},
            {"name": "xhs_like", "type": "xhs", "doc": "小红书点赞笔记", "source": "runner.py"},
            {"name": "xhs_comment", "type": "xhs", "doc": "小红书评论笔记", "source": "runner.py"},
            {"name": "xhs_search", "type": "xhs", "doc": "小红书搜索", "source": "runner.py"},
            {"name": "rest", "type": "通用", "doc": "随机休息 (5~20秒)", "source": "behavior.py"},
        ]

        # 去重
        seen = set()
        for op in ops:
            seen.add(op["name"])
        for op in core_ops:
            if op["name"] not in seen:
                ops.append(op)
                seen.add(op["name"])

        return ops

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
    # 内部工具
    # ═══════════════════════════════════════════════════════════

    def _read_accounts_yaml(self) -> list:
        if not MATRIX_ACCOUNTS_CFG.exists():
            return []
        try:
            data = yaml.safe_load(MATRIX_ACCOUNTS_CFG.read_text()) or {}
            return data.get("accounts", [])
        except Exception as e:
            print(f"读取 accounts.yaml 失败: {e}")
            return []

    def _write_accounts_yaml(self, accounts: list):
        # 保持现有格式，仅更新 accounts 字段
        if MATRIX_ACCOUNTS_CFG.exists():
            existing = yaml.safe_load(MATRIX_ACCOUNTS_CFG.read_text()) or {}
        else:
            existing = {
                "viewport": {"width": 702, "height": 783, "mobile": False},
                "camoufox": {"screen": {"width": 702, "height": 783}},
            }
        existing["accounts"] = accounts
        MATRIX_ACCOUNTS_CFG.parent.mkdir(parents=True, exist_ok=True)
        MATRIX_ACCOUNTS_CFG.write_text(
            yaml.dump(existing, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def _check_login_status(self, acct: dict) -> str:
        """检查账号登录状态"""
        identity_dir_name = acct.get("identity_dir", "").replace("identities/", "")
        if not identity_dir_name:
            return "no_identity"
        cookie_path = MATRIX_IDENTITIES / identity_dir_name / "user_data" / "cookies.sqlite"
        if not cookie_path.exists():
            return "no_cookie"
        if cookie_path.stat().st_size < 100:
            return "empty_cookie"
        try:
            conn = sqlite3.connect(str(cookie_path), timeout=2)
            cur = conn.cursor()
            platform = acct.get("platform", "douyin")
            if platform in ("douyin", "xiaohongshu"):
                like = "%douyin%" if platform == "douyin" else "%xiaohongshu%"
                count = cur.execute(
                    "SELECT count(*) FROM moz_cookies WHERE host LIKE ? AND name LIKE '%session%'",
                    (like,),
                ).fetchone()[0]
            else:
                count = cur.execute("SELECT count(*) FROM moz_cookies").fetchone()[0]
            conn.close()
            return "logged_in" if count > 0 else "no_session"
        except:
            return "error"

    def _identity_exists(self, acct: dict) -> bool:
        identity_dir_name = acct.get("identity_dir", "").replace("identities/", "")
        if not identity_dir_name:
            return False
        return (MATRIX_IDENTITIES / identity_dir_name).exists()

    def _count_backups(self, acct: dict) -> int:
        identity_dir_name = acct.get("identity_dir", "").replace("identities/", "")
        if not identity_dir_name:
            return 0
        backup_dir = MATRIX_BACKUPS / "cookies" / identity_dir_name
        if backup_dir.exists():
            return len(list(backup_dir.glob("*.bak")))
        return 0

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

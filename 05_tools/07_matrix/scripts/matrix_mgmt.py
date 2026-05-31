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

    # ═══════════════════════════════════════════════════════════
    # 原子操作依赖模型（防止错误编排）
    # ═══════════════════════════════════════════════════════════
    # 每个操作定义:
    #   category:  操作类别 (navigation/browse/interact/utility/xhs)
    #   requires:  前置操作（必须至少一个在此列表中 或 [] 表示无要求）
    #   allows:    可选的后继操作（"*" 表示任意）
    #   can_be_first: 是否可作为第一个步骤
    #   desc:      简短描述
    # ═══════════════════════════════════════════════════════════

    OP_GRAPH = {
        # ── 导航类 (entry points) ──
        "goto_home": {
            "category": "navigation", "label": "🏠 回到推荐页",
            "requires": [], "allows": ["browse_feed", "enter_video", "scroll_feed", "search_keyword", "xhs_browse", "rest", "go_back", "like", "collect"],
            "can_be_first": True, "desc": "回到抖音推荐页，固定起点"
        },
        "goto_url": {
            "category": "navigation", "label": "🔗 导航到URL",
            "requires": [], "allows": ["enter_video", "like", "collect", "follow", "comment_video_b", "scroll_feed", "rest", "go_back"],
            "can_be_first": True, "desc": "直接打开指定视频/用户URL"
        },
        "go_back": {
            "category": "navigation", "label": "⬅ 返回",
            "requires": ["*"], "allows": ["browse_feed", "enter_video", "search_keyword", "scroll_feed", "xhs_browse", "xhs_click_note", "rest", "go_back"],
            "can_be_first": False, "desc": "浏览器后退，回到上一页"
        },

        # ── 浏览类 (创建上下文) ──
        "browse_feed": {
            "category": "browse", "label": "📱 浏览推荐流",
            "requires": ["goto_home", "go_back", "rest"], "allows": ["enter_video", "scroll_feed", "search_keyword", "like", "collect", "rest", "go_back"],
            "can_be_first": True, "desc": "浏览推荐页视频流，自动滑视频"
        },
        "scroll_feed": {
            "category": "browse", "label": "⬇ 下滑加载",
            "requires": ["browse_feed", "enter_video", "goto_home", "xhs_browse", "go_back", "rest"],
            "allows": ["enter_video", "scroll_feed", "like", "collect", "rest", "go_back", "xhs_click_note"],
            "can_be_first": False, "desc": "瀑布流/视频流下滑加载更多内容"
        },
        "enter_video": {
            "category": "browse", "label": "▶ 进入播放页",
            "requires": ["browse_feed", "scroll_feed", "goto_url", "search_keyword", "rest"],
            "allows": ["like", "collect", "follow", "comment_video_a", "comment_video_b", "scroll_feed", "next_video", "prev_video", "rest", "go_back"],
            "can_be_first": False, "desc": "从推荐页点击卡片进入视频播放页"
        },

        # ── 交互类 (需视频上下文) ──
        "like": {
            "category": "interact", "label": "👍 点赞",
            "requires": ["enter_video", "xhs_click_note", "browse_feed"], "allows": ["collect", "follow", "comment_video_a", "comment_video_b", "scroll_feed", "next_video", "prev_video", "rest", "go_back"],
            "can_be_first": False, "desc": "点赞当前视频（KeyZ或点击选择器）"
        },
        "collect": {
            "category": "interact", "label": "⭐ 收藏",
            "requires": ["enter_video", "xhs_click_note"], "allows": ["like", "follow", "comment_video_a", "comment_video_b", "scroll_feed", "next_video", "prev_video", "rest", "go_back"],
            "can_be_first": False, "desc": "收藏当前视频到收藏夹"
        },
        "follow": {
            "category": "interact", "label": "➕ 关注",
            "requires": ["enter_video", "xhs_click_note"], "allows": ["like", "collect", "comment_video_a", "comment_video_b", "scroll_feed", "next_video", "prev_video", "rest", "go_back"],
            "can_be_first": False, "desc": "关注当前视频作者"
        },
        "comment_video_a": {
            "category": "interact", "label": "💬 评论(Path A)",
            "requires": ["enter_video"], "allows": ["like", "collect", "follow", "scroll_feed", "next_video", "prev_video", "rest", "go_back"],
            "can_be_first": False, "desc": "弹窗覆盖层评论 (KeyX→pbcopy→Enter)"
        },
        "comment_video_b": {
            "category": "interact", "label": "💬 评论(Path B)",
            "requires": ["enter_video", "goto_url"], "allows": ["like", "collect", "follow", "scroll_feed", "rest", "go_back"],
            "can_be_first": False, "desc": "全屏视频页评论 (scroll→click→Enter)"
        },
        "next_video": {
            "category": "interact", "label": "⏭ 下一个视频",
            "requires": ["enter_video", "like", "collect", "follow", "comment_video_a"], "allows": ["like", "collect", "follow", "comment_video_a", "comment_video_b", "scroll_feed", "rest", "go_back"],
            "can_be_first": False, "desc": "切换到下一个视频"
        },
        "prev_video": {
            "category": "interact", "label": "⏮ 上一个视频",
            "requires": ["enter_video"], "allows": ["like", "collect", "follow", "comment_video_a", "comment_video_b", "rest", "go_back"],
            "can_be_first": False, "desc": "切换到上一个视频"
        },
        "search_keyword": {
            "category": "interact", "label": "🔍 搜索",
            "requires": ["goto_home", "browse_feed", "rest", "go_back"], "allows": ["enter_video", "scroll_feed", "rest", "go_back"],
            "can_be_first": True, "desc": "搜索关键词并打开搜索结果页"
        },

        # ── 小红书专用 ──
        "xhs_browse": {
            "category": "xhs", "label": "📕 瀑布流浏览",
            "requires": ["goto_home", "rest", "go_back"], "allows": ["xhs_click_note", "scroll_feed", "xhs_search", "xhs_like", "rest", "go_back"],
            "can_be_first": True, "desc": "小红书首页瀑布流浏览"
        },
        "xhs_click_note": {
            "category": "xhs", "label": "📕 点击笔记",
            "requires": ["xhs_browse", "scroll_feed", "rest"], "allows": ["xhs_like", "xhs_comment", "rest", "go_back", "scroll_feed"],
            "can_be_first": False, "desc": "小红书点击笔记卡片进入详情页"
        },
        "xhs_like": {
            "category": "xhs", "label": "📕 点赞",
            "requires": ["xhs_click_note", "enter_video"], "allows": ["xhs_comment", "rest", "go_back", "scroll_feed"],
            "can_be_first": False, "desc": "小红书点赞当前笔记"
        },
        "xhs_comment": {
            "category": "xhs", "label": "📕 评论",
            "requires": ["xhs_click_note", "xhs_like"], "allows": ["rest", "go_back", "scroll_feed"],
            "can_be_first": False, "desc": "小红书评论当前笔记"
        },
        "xhs_search": {
            "category": "xhs", "label": "📕 搜索",
            "requires": ["xhs_browse", "goto_home", "rest", "go_back"], "allows": ["xhs_click_note", "scroll_feed", "rest", "go_back"],
            "can_be_first": True, "desc": "小红书搜索关键词"
        },

        # ── 通用工具 ──
        "rest": {
            "category": "utility", "label": "⏳ 休息",
            "requires": [], "allows": ["*"],
            "can_be_first": True, "desc": "随机休息 5~20秒，模拟真人操作间隔"
        },
    }

    def list_atomic_ops(self) -> list[dict]:
        """列出所有可用原子操作（含依赖约束）"""
        # 先尝试从 douyin_ops.py 提取异步函数
        parsed_ops = []
        try:
            import ast
            ops_file = MATRIX_SCRIPTS / "douyin_ops.py"
            if ops_file.exists():
                tree = ast.parse(ops_file.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.AsyncFunctionDef) and not node.name.startswith("_"):
                        doc = ast.get_docstring(node) or ""
                        name = node.name
                        if name not in self.OP_GRAPH:
                            parsed_ops.append({
                                "name": name,
                                "type": "douyin",
                                "doc": doc.split("\n")[0] if doc else "",
                                "source": "douyin_ops.py",
                                "category": "auto",
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
        返回: {"valid": bool, "errors": [{"step": idx, "msg": str}, ...], "warnings": [...]}
        """
        errors = []
        warnings = []
        for i, step in enumerate(steps):
            name = step.get("name", "")
            info = self.OP_GRAPH.get(name)
            if not info:
                continue

            # 检查第一个步骤能否作为起点
            if i == 0 and not info["can_be_first"]:
                errors.append({"step": i + 1, "op": name, "msg": f'"{info["label"]}" 不能作为第一个步骤，前置需要: {info["requires"]}'})

            # 检查前置约束
            if i > 0 and info["requires"]:
                prev_name = steps[i - 1].get("name", "")
                # requires=["*"] 表示任意前置皆可
                if info["requires"] != ["*"]:
                    # requires 列表中的操作必须出现在前面的步骤中（不一定是紧邻）
                    prev_names = [s.get("name", "") for s in steps[:i]]
                    if not any(r in prev_names for r in info["requires"] if r != "*"):
                        errors.append({
                            "step": i + 1, "op": name,
                            "msg": f'"{info["label"]}" 的前置操作未满足。需要: {info["requires"]}，当前已有: {prev_names}'})

            # 检查前一步骤能否接当前步骤
            if i > 0:
                prev_name = steps[i - 1].get("name", "")
                prev_info = self.OP_GRAPH.get(prev_name)
                if prev_info and prev_info["allows"] != ["*"]:
                    if name not in prev_info["allows"]:
                        errors.append({
                            "step": i + 1, "op": name,
                            "msg": f'上一步骤 "{prev_info["label"]}" 不能接 "{info["label"]}"。{prev_info["label"]} 的后继可选: {prev_info["allows"]}'})

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

#!/usr/bin/env python3
"""
matrix — 多平台社交账号自动化管理系统 统一入口

用法:
  matrix account list                         列出所有账号
  matrix account create <name>                创建新身份
  matrix account login <name>                 首次登录
  matrix account status [name]                查看登录状态
  matrix account delete <name>                删除身份
  matrix account export <name>                导出身份
  matrix account import <path>                导入身份

  matrix nurture run -a <name> -r 10          循环养号
  matrix nurture schedule [cron]              设置定时任务
  matrix nurture stop <task_id>               停止任务

  matrix config show                          查看全局配置
  matrix config blueprint list                列出蓝图
  matrix config blueprint show <name>         查看蓝图

  matrix status                               全局状态一览
  matrix status browsers                      浏览器运行状态
  matrix status accounts                      账号登录状态

全局参数:
  -a, --account     指定账号（可多次: -a a -a b）
  -b, --blueprint   指定蓝图
  -e, --engine      引擎 (chrome/camoufox/auto)
  -r, --rounds      循环轮数
      --headless    无头模式
      --behavior    行为配置JSON
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

# ── 路径 ──
SCRIPTS_DIR = Path(__file__).parent
from matrix_mgmt import AGENT_LOCAL
LOCAL_ROOT = AGENT_LOCAL / "tools" / "matrix"
sys.path.insert(0, str(SCRIPTS_DIR))


# ════════════════════════════════════════════════════════════
#  account 域
# ════════════════════════════════════════════════════════════

def cmd_account_list(args):
    """列出所有已启用的账号"""
    import yaml
    config_path = LOCAL_ROOT / "config" / "accounts.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    accounts = [a for a in data.get("accounts", []) if a.get("enabled")]

    print(f"\n{'='*55}")
    print(f" 📋 账号列表 ({len(accounts)} 个)")
    print(f"{'='*55}")
    for a in accounts:
        acct_id = a["id"]
        platform = a.get("platform", "?")
        engine = a.get("browser_type", "chrome")
        notes = a.get("notes", "")
        identity = a.get("identity_dir", "-")
        phone = a.get("phone", "")
        phone_str = f" 📞{phone}" if phone else ""
        print(f"  • {acct_id:15s} | {platform:8s} | {engine:10s}{phone_str} | {notes}")
        if identity != "-":
            ud = LOCAL_ROOT / identity / "user_data"
            files = len(list(ud.glob("*"))) if ud.exists() else 0
            print(f"                    身份: {identity} ({files} files)")
    print()


def cmd_account_create(args):
    """创建新身份"""
    from create_identity import create_identity
    create_identity(name=args.name, platform=args.platform or "douyin")


def cmd_account_login(args):
    """首次登录"""
    from login_identity import login_identity
    asyncio.run(login_identity(args.name))


def cmd_account_status(args):
    """查看账号登录状态"""
    import yaml
    config_path = LOCAL_ROOT / "config" / "accounts.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    if args.name:
        accounts = [a for a in data.get("accounts", [])
                    if a["id"] == args.name and a.get("enabled")]
    else:
        accounts = [a for a in data.get("accounts", []) if a.get("enabled")]

    for a in accounts:
        acct_id = a["id"]
        identity = a.get("identity_dir")
        if identity:
            ud = LOCAL_ROOT / identity / "user_data"
            # 简单判断：user_data 目录有文件且不是空的
            has_state = ud.exists() and len(list(ud.glob("*"))) > 2
            phone = a.get("phone", "")
            phone_str = f" 📞{phone}" if phone else ""
            print(f"  {'✅' if has_state else '❌'} {acct_id:15s} | {'已初始化' if has_state else '未登录'}{phone_str} | {identity}")
        else:
            print(f"  ⚪ {acct_id:15s} | 使用 Chrome Profile")


# ════════════════════════════════════════════════════════════
#  nurture 域
# ════════════════════════════════════════════════════════════

def cmd_nurture_run(args):
    """执行养号（支持抖音/小红书平台自动路由）"""
    import yaml
    config_path = LOCAL_ROOT / "config" / "accounts.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    identities = args.account or []
    if not identities:
        # 未指定账号时，根据 platform 参数或默认取抖音
        platform = getattr(args, 'platform', 'douyin')
        identities = [
            a["id"] for a in data.get("accounts", [])
            if a.get("enabled") and a.get("platform") == platform
        ]

    if not identities:
        print("❌ 没有指定账号, 可用: matrix account list")
        sys.exit(1)

    # 按平台分组
    douyin_ids = []
    xhs_ids = []
    for a in data.get("accounts", []):
        if a["id"] in identities:
            if a.get("platform") == "xiaohongshu":
                xhs_ids.append(a["id"])
            else:
                douyin_ids.append(a["id"])

    # 自动判断引擎
    engines = {}
    for a in data.get("accounts", []):
        if a["id"] in identities:
            if a.get("identity_dir"):
                engines[a["id"]] = "camoufox"
            else:
                bt = a.get("browser_type", "chrome")
                engines[a["id"]] = "camoufox" if bt == "camoufox" else "chrome"

    behavior_config = None
    if args.behavior:
        try:
            behavior_config = json.loads(args.behavior)
        except json.JSONDecodeError as e:
            print(f"❌ 行为配置 JSON 解析错误: {e}")
            sys.exit(1)

    import time

    # ── Cookie 全量备份（防误删，共享 identity_dir 防护）──
    if xhs_ids or douyin_ids:
        print(" 💾 养号前全量 Cookie 备份...")
        try:
            from matrix_modules.utils.cookie_manager import backup_all_identities
            bak = backup_all_identities(platform='nurture', label='pre_run')
            for k, v in bak.items():
                if v:
                    print(f"    ✅ {k}")
        except Exception as e:
            print(f"    ⚠️ Cookie 备份: {e}")

    # ── 小红书养号 ──
    if xhs_ids:
        print(f"\n{'='*55}")
        print(f" 📕 小红书养号 ({len(xhs_ids)} 个账号) — 并行执行")
        print(f"{'='*55}")
        from matrix_modules.nurture.runner import nurture_xhs_loop

        async def _run_all_xhs():
            tasks = []
            for xhs_id in xhs_ids:
                tasks.append(nurture_xhs_loop(
                    identity_name=xhs_id,
                    rounds=args.rounds or 10,
                    headless=args.headless or False,
                    behavior_config=behavior_config,
                    daemon=args.daemon if args.daemon is not None else False,
                    use_ai_comments=getattr(args, 'ai_comments', False),
                ))
            await asyncio.gather(*tasks)

        asyncio.run(_run_all_xhs())

    # ── 抖音养号 ──
    if douyin_ids:
        print(f"\n{'='*55}")
        print(f" 🎵 抖音养号 ({len(douyin_ids)} 个账号)")
        print(f"{'='*55}")
        from matrix_modules.nurture.runner import nurture_multi
        nurture_multi._t_start = time.time()
        asyncio.run(nurture_multi(
            identities=douyin_ids,
            blueprint_name=args.blueprint or "douyin_browse_v2",
            rounds=args.rounds or 10,
            headless=args.headless or False,
            engines=engines,
            daemon=args.daemon if args.daemon is not None else True,
        ))


def cmd_nurture_schedule(args):
    """设置定时任务（预留）"""
    print("📅 定时任务功能开发中...")
    print(f"   Cron: {args.cron or '未指定'}")


def cmd_nurture_stop(args):
    """停止 daemon 养号（发送 SIGTERM）"""
    import subprocess, os, signal
    result = subprocess.run(
        ["ps", "aux"], capture_output=True, text=True, timeout=5
    )
    for line in result.stdout.split("\n"):
        if "matrix.py" in line and "nurture" in line and args.name in line and "stop" not in line:
            parts = line.split()
            if parts:
                pid = int(parts[1])
                os.kill(pid, signal.SIGTERM)
                print(f"⏹ 已发送停止信号: {args.name} (PID {pid})")
                return
    print(f"❌ 未找到运行中的 daemon: {args.name}")


# ════════════════════════════════════════════════════════════
#  config 域
# ════════════════════════════════════════════════════════════

def cmd_config_show(args):
    """查看配置"""
    import yaml
    print(f"\n{'='*55}")
    print(" 📋 全局配置")
    print(f"{'='*55}")

    # accounts.yaml
    config_path = LOCAL_ROOT / "config" / "accounts.yaml"
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f)
        viewport = data.get("viewport", {})
        print(f"   视口: {viewport.get('width', '?')}x{viewport.get('height', '?')}")
        enabled = [a["id"] for a in data.get("accounts", []) if a.get("enabled")]
        print(f"   已启用账号: {', '.join(enabled) if enabled else '无'}")

    # 蓝图
    bp_dir = SCRIPTS_DIR.parent / "blueprints"
    bps = sorted(bp_dir.glob("*.json"))
    print(f"   可用蓝图: {len(bps)} 个")
    for bp in bps:
        print(f"     • {bp.stem}")
    print()


def cmd_config_blueprint_list(args):
    """列出蓝图"""
    bp_dir = SCRIPTS_DIR.parent / "blueprints"
    import json
    print(f"\n{'='*55}")
    print(" 📋 蓝图列表")
    print(f"{'='*55}")
    for bp in sorted(bp_dir.glob("*.json")):
        data = json.loads(bp.read_text())
        steps = len(data.get("steps", []))
        desc = data.get("description", "")
        print(f"  • {bp.stem:30s} | {steps}步 | {desc[:40]}")
    print()


def cmd_config_blueprint_show(args):
    """查看蓝图详情"""
    bp_dir = SCRIPTS_DIR.parent / "blueprints"
    bp_file = bp_dir / f"{args.name}.json"
    if not bp_file.exists():
        print(f"❌ 蓝图不存在: {args.name}")
        print(f"   可用: matrix config blueprint list")
        sys.exit(1)
    import json
    data = json.loads(bp_file.read_text())
    print(f"\n{'='*55}")
    print(f" 📋 蓝图: {args.name}")
    print(f"{'='*55}")
    print(f"   描述: {data.get('description', '无')}")
    print(f"   步骤: {len(data.get('steps', []))} 步")
    for s in data.get("steps", []):
        sid = s.get("step_id", "?")
        op = s.get("op", "?")
        args_str = s.get("args", {})
        print(f"     [{sid:2d}] {op:15s} args={args_str}")
    print()


# ════════════════════════════════════════════════════════════
#  status 域
# ════════════════════════════════════════════════════════════

def cmd_status(args):
    """全局状态"""
    import yaml, json, subprocess

    print(f"\n{'='*55}")
    print(" 📊 全局状态")
    print(f"{'='*55}")

    # 浏览器状态
    print(f"\n  🌐 浏览器:")
    for port in [9222, 9223]:
        import urllib.request
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(f"http://localhost:{port}/json/version", timeout=2) as r:
                info = json.loads(r.read())
            print(f"    ✅ Chrome :{port} — {info.get('Browser', '?')[:30]}")
        except:
            print(f"    ❌ Chrome :{port} — 未运行")

    # Camoufox
    import subprocess
    result = subprocess.run(
        ["ps", "aux"], capture_output=True, text=True, timeout=5
    )
    camou_count = result.stdout.count("camoufox")
    if camou_count > 0:
        print(f"    ✅ Camoufox — 运行中 ({camou_count} 进程)")
    else:
        print(f"    ❌ Camoufox — 未运行")

    # 账号状态
    print(f"\n  👤 账号:")
    config_path = LOCAL_ROOT / "config" / "accounts.yaml"
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f)
        for a in data.get("accounts", []):
            if not a.get("enabled"):
                continue
            acct_id = a["id"]
            identity = a.get("identity_dir")
            if identity:
                ud = LOCAL_ROOT / identity / "user_data"
                has_state = ud.exists() and len(list(ud.glob("*"))) > 2
                print(f"    {'✅' if has_state else '❌'} {acct_id:15s} | {'已登录' if has_state else '未登录'}")
            else:
                print(f"    ⚪ {acct_id:15s} | Chrome Profile")
    print()


def cmd_status_browsers(args):
    """浏览器状态（详细）"""
    import json, urllib.request

    for port in [9222, 9223]:
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(f"http://localhost:{port}/json/version", timeout=2) as r:
                info = json.loads(r.read())
            print(f"\n🌐 Chrome :{port}")
            print(f"   版本: {info.get('Browser', '?')}")
            print(f"   User-Agent: {info.get('User-Agent', '?')[:60]}...")

            # 获取页面列表
            with opener.open(f"http://localhost:{port}/json", timeout=2) as r:
                pages = json.loads(r.read())
            print(f"   页面: {len(pages)} 个")
            for p in pages[:3]:
                print(f"     • {p.get('title', '?')[:40]}")
        except Exception as e:
            print(f"\n❌ Chrome :{port} — {type(e).__name__}")


def cmd_status_accounts(args):
    """账号状态"""
    cmd_account_status(args)


# ════════════════════════════════════════════════════════════
#  CLI 路由
# ════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="matrix — 多平台社交账号自动化管理系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  matrix account list                     列出账号
  matrix nurture run -a douyin_01 -r 10   养号10轮
  matrix nurture run -a douyin_01 -a douyin_02  双号并发
  matrix status                           全局状态
  matrix config blueprint list            查看蓝图
        """,
    )
    sub = parser.add_subparsers(dest="domain", help="功能域")

    # ── account ──
    p_acct = sub.add_parser("account", help="账号管理")
    acct_sub = p_acct.add_subparsers(dest="action", help="操作")

    p_acct_list = acct_sub.add_parser("list", help="列出所有账号")
    p_acct_list.set_defaults(func=cmd_account_list)

    p_acct_create = acct_sub.add_parser("create", help="创建新身份")
    p_acct_create.add_argument("name", help="身份名称")
    p_acct_create.add_argument("--platform", "-p", default="douyin", help="平台")
    p_acct_create.set_defaults(func=cmd_account_create)

    p_acct_login = acct_sub.add_parser("login", help="首次登录")
    p_acct_login.add_argument("name", help="身份名称")
    p_acct_login.set_defaults(func=cmd_account_login)

    p_acct_status = acct_sub.add_parser("status", help="登录状态")
    p_acct_status.add_argument("name", nargs="?", help="账号ID")
    p_acct_status.set_defaults(func=cmd_account_status)

    # ── nurture ──
    p_nur = sub.add_parser("nurture", help="养号执行")
    nur_sub = p_nur.add_subparsers(dest="action", help="操作")

    p_nur_run = nur_sub.add_parser("run", help="运行养号")
    p_nur_run.add_argument("-a", "--account", action="append", help="账号ID (可多次)")
    p_nur_run.add_argument("-b", "--blueprint", default="douyin_browse_v2", help="蓝图名称")
    p_nur_run.add_argument("-r", "--rounds", type=int, default=10, help="循环轮数")
    p_nur_run.add_argument("--headless", action="store_true", help="无头模式")
    p_nur_run.add_argument("--behavior", help="行为配置JSON")
    p_nur_run.add_argument("--daemon", action=argparse.BooleanOptionalAction, default=None, help="完成后保持浏览器连接不退出（抖音默认开启，小红书默认关闭）")
    p_nur_run.add_argument("--platform", default="douyin", help="平台: douyin | xiaohongshu")
    p_nur_run.add_argument("--ai-comments", action="store_true", help="使用 AI 生成评论（需 oMLX 模型运行中）")
    p_nur_run.set_defaults(func=cmd_nurture_run)

    p_nur_sched = nur_sub.add_parser("schedule", help="设置定时任务")
    p_nur_sched.add_argument("cron", nargs="?", help="cron表达式")
    p_nur_sched.set_defaults(func=cmd_nurture_schedule)

    p_nur_stop = nur_sub.add_parser("stop", help="停止 daemon 养号")
    p_nur_stop.add_argument("name", help="账号ID")
    p_nur_stop.set_defaults(func=cmd_nurture_stop)

    # ── config ──
    p_cfg = sub.add_parser("config", help="配置管理")
    cfg_sub = p_cfg.add_subparsers(dest="action", help="操作")

    p_cfg_show = cfg_sub.add_parser("show", help="查看配置")
    p_cfg_show.set_defaults(func=cmd_config_show)

    p_cfg_bp = cfg_sub.add_parser("blueprint", help="蓝图管理")
    bp_sub = p_cfg_bp.add_subparsers(dest="bp_action", help="操作")

    p_bp_list = bp_sub.add_parser("list", help="列出蓝图")
    p_bp_list.set_defaults(func=cmd_config_blueprint_list)

    p_bp_show = bp_sub.add_parser("show", help="查看蓝图")
    p_bp_show.add_argument("name", help="蓝图名称")
    p_bp_show.set_defaults(func=cmd_config_blueprint_show)

    # ── status ──
    p_st = sub.add_parser("status", help="状态监控")
    st_sub = p_st.add_subparsers(dest="action", help="操作")

    p_st_all = st_sub.add_parser("all", help="全局状态")
    p_st_all.set_defaults(func=cmd_status)

    p_st_br = st_sub.add_parser("browsers", help="浏览器状态")
    p_st_br.set_defaults(func=cmd_status_browsers)

    p_st_ac = st_sub.add_parser("accounts", help="账号状态")
    p_st_ac.set_defaults(func=cmd_status_accounts)

    # ── 无子命令时默认显示 status ──
    parser.set_defaults(func=lambda a: parser.print_help())

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

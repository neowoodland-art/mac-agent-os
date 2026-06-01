#!/usr/bin/env python3
"""
cli.py — mc 命令解析与路由

用法:
  mc run --accounts A,B --blueprints X --rounds 10 [options]
  mc account list|create|login|status|export
  mc blueprint list|create|edit|delete
  mc corpus list|add|select
  mc proxy list|test|set
  mc sms config|test
  mc status all|accounts|browsers
  mc record start|stop|export (预留)

全局选项:
  --log FILE          日志输出路径
  --json              输出 JSON (供程序调用)
  -v, --verbose       详细输出
"""
import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ── 路径 ──
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
TOOL_DIR = SCRIPTS_DIR.parent
AGENT_SYNC = Path.home() / "workbuddy-agent-os" / "agent-sync"
AGENT_LOCAL = Path.home() / "workbuddy-agent-os" / "agent-local"
sys.path.insert(0, str(SCRIPTS_DIR))

__version__ = "1.0.0"


# ════════════════════════════════════════════════════════════
# 帮助
# ════════════════════════════════════════════════════════════

def print_banner():
    print(f"╔══════════════════════════════════════╗")
    print(f"║   Matrix Console v{__version__}            ║")
    print(f"║   统一命令入口 · 批量执行 · 稳定可靠   ║")
    print(f"╚══════════════════════════════════════╝")


# ════════════════════════════════════════════════════════════
# 工具函数
# ════════════════════════════════════════════════════════════

def setup_log(path: str = None):
    """设置日志文件"""
    if path:
        fh = logging.FileHandler(path, mode='a', encoding='utf-8')
        fh.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))
        logging.getLogger().addHandler(fh)

def log(msg: str):
    """统一日志输出"""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

import logging


# ════════════════════════════════════════════════════════════
# Account 域
# ════════════════════════════════════════════════════════════

def cmd_account(args):
    """账号管理"""
    from matrix_mgmt import MatrixManager
    mgr = MatrixManager()

    if args.action == "list":
        accounts = mgr.list_accounts()
        print(f"\n📋 账号列表 ({len(accounts)}):")
        print(f"{'ID':<16} {'平台':<12} {'状态':<12} {'手机':<12} {'本机':<6}")
        print("-" * 60)
        for a in accounts:
            status = "🟢 已登录" if a.get("_status") == "logged_in" else \
                     "🔴 离线" if a.get("_status") == "remote" else \
                     "⏸ 停用" if a.get("_status") == "disabled" else \
                     f"⚠️ {a.get('_status','?')}"
            local = "本机" if a.get("is_local") else "远程"
            phone = (a.get("phone") or a.get("phone_mask") or "-")[:11]
            print(f"  {a['id']:<14} {a.get('platform','?'):<10} {status:<12} {phone:<12} {local:<6}")

    elif args.action == "login":
        from login_identity import login_identity
        asyncio.run(login_identity(args.name))
        log(f"✅ {args.name} 登录完成")

    elif args.action == "status":
        if args.name:
            log(f"检查 {args.name} 登录状态...")
            print(json.dumps(mgr.check_login_status(args.name), indent=2, ensure_ascii=False))
        else:
            cmd_account(argparse.Namespace(action="list", name=None, json=args.json, verbose=args.verbose))

    elif args.action == "export":
        result = mgr.export_accounts()
        log(f"📦 导出完成: {result['path']} ({result['size_kb']}KB)")

    elif args.action == "import":
        result = mgr.import_accounts(args.path or "")
        log(f"📥 导入完成: 配置{result.get('accounts_imported',0)} 身份{result.get('identities_imported',0)}")


# ════════════════════════════════════════════════════════════
# Run 域 (批量执行引擎)
# ════════════════════════════════════════════════════════════

def cmd_run(args):
    """批量执行引擎"""
    from mc.run import BatchRunner
    setup_log(args.log)

    # 解析参数
    accounts = [a.strip() for a in args.accounts.split(",") if a.strip()]
    blueprints = [b.strip() for b in args.blueprints.split(",") if b.strip()]
    corpus = [c.strip() for c in (args.corpus or "").split(",") if c.strip()] if args.corpus else []
    mix_mode = args.mix           # True = 混合随机模式

    log(f"🚀 mc run 启动")
    log(f"   账号: {accounts}")
    log(f"   蓝图: {blueprints}")
    log(f"   轮数: {args.rounds} | 间隔: {args.interval}s | 模式: {'混合随机' if mix_mode else '顺序'}")
    if corpus:
        log(f"   语料: {corpus}")
    if args.daemon:
        log(f"   后台运行: 是")
    log(f"   引擎: {args.engine}")

    runner = BatchRunner(
        accounts=accounts,
        blueprints=blueprints,
        rounds=args.rounds,
        interval_range=tuple(int(x) for x in args.interval.split("-")),
        mix=mix_mode,
        corpus=corpus,
        engine=args.engine,
        daemon=args.daemon,
    )

    try:
        report = asyncio.run(runner.run())
        log(f"\n📊 执行完成")
        log(f"   总步骤: {report.get('total_steps', 0)}")
        log(f"   成功: {report.get('success', 0)}")
        log(f"   失败: {report.get('failed', 0)}")
        log(f"   耗时: {report.get('duration', 0):.1f}s")
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
    except KeyboardInterrupt:
        log("\n⏹ 用户中断")


# ════════════════════════════════════════════════════════════
# Blueprint 域
# ════════════════════════════════════════════════════════════

def cmd_blueprint(args):
    """蓝图管理"""
    from matrix_mgmt import MatrixManager
    mgr = MatrixManager()

    if args.action == "list":
        bps = mgr.list_blueprints()
        print(f"\n📋 蓝图 ({len(bps)}):")
        for b in bps:
            print(f"  • {b['name']:25s} ({b['step_count']}步) {b.get('platform','douyin'):12s} {b.get('description','')[:30]}")
    elif args.action == "show":
        bps = mgr.list_blueprints()
        bp = next((b for b in bps if b['name'] == args.name), None)
        if bp:
            print(json.dumps(bp, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 蓝图 {args.name} 不存在")


# ════════════════════════════════════════════════════════════
# Corpus 域
# ════════════════════════════════════════════════════════════

def cmd_corpus(args):
    """语料库管理"""
    from mc.corpus import CorpusManager
    cm = CorpusManager()

    if args.action == "list":
        cats = cm.list_categories()
        print(f"\n📚 语料库分类:")
        print(f"{'平台':<12} {'分类':<16} {'权重':<6} {'条数':<6} {'启用':<6}")
        print("-" * 50)
        for c in cats:
            print(f"  {c['platform']:<10} {c['name']:<14} {c['weight']:<5} {c['count']:<5} {'✅' if c['enabled'] else '⏸'}")

    elif args.action == "add":
        cm.add_comment(args.category, args.text)
        log(f"✅ 已添加评论到 [{args.category}]: {args.text}")


# ════════════════════════════════════════════════════════════
# Proxy 域
# ════════════════════════════════════════════════════════════

def cmd_proxy(args):
    """代理管理"""
    from mc.proxy import ProxyCLI
    pcli = ProxyCLI()

    if args.action == "list":
        proxies = pcli.list_all()
        print(f"\n🌐 代理列表:")
        print(f"{'账号':<16} {'代理':<36} {'状态':<10}")
        print("-" * 65)
        for p in proxies:
            status = "🟢" if p.get("has_proxy") else "⏸"
            proxy_str = str(p.get("proxy") or "none")[:34]
            print(f"  {p['account']:<14} {proxy_str:<34} {status:<10}")

    elif args.action == "test":
        if args.proxy:
            r = pcli.test(args.proxy)
            if r.get("status") == "ok":
                log(f"✅ 代理正常: {r.get('ip','')} ({r.get('elapsed','')})")
            else:
                log(f"❌ 代理失败: {r.get('error','')}")
        else:
            log("   请指定 --proxy 'socks5://127.0.0.1:7890'")


# ════════════════════════════════════════════════════════════
# SMS 域
# ════════════════════════════════════════════════════════════

def cmd_sms(args):
    """短信管理"""
    if args.action == "config":
        from dashboard_plugins.sms_proxy_api import SMSManager
        cfg = SMSManager.get_config()
        print(f"\n📱 SMS 配置:")
        print(json.dumps(cfg, indent=2, ensure_ascii=False))

    elif args.action == "test":
        from dashboard_plugins.sms_proxy_api import SMSManager
        r = SMSManager.test_receive(args.phone or "")
        if r.get("status") == "ok":
            log(f"✅ 短信API正常: {r.get('total',0)} 条消息")
            for m in r.get("messages", [])[:3]:
                log(f"   {m.get('time','')} {m.get('content','')[:50]}")
        else:
            log(f"❌ {r.get('error','')}")


# ════════════════════════════════════════════════════════════
# Status 域
# ════════════════════════════════════════════════════════════

def cmd_status(args):
    """状态检查"""
    from matrix_mgmt import MatrixManager
    mgr = MatrixManager()

    if args.action in ("all", "accounts"):
        info = mgr.system_info()
        print(f"\n📊 系统状态:")
        print(f"   总账号: {info['total_accounts']}")
        print(f"   已启用: {info['enabled_accounts']}")
        print(f"   已登录: {info['logged_in_accounts']}")
        print(f"   身份目录: {info['identity_dirs']}")
        print(f"   蓝图: {info['blueprints']}")

    if args.action in ("all", "browsers"):
        # 检查残留浏览器进程
        import subprocess
        result = subprocess.run(["pgrep", "-fl", "camoufox|firefox"], capture_output=True, text=True)
        procs = [l for l in result.stdout.split("\n") if l.strip()]
        print(f"\n🌐 浏览器进程 ({len(procs)}):")
        for p in procs:
            print(f"  {p[:80]}")

    if args.action == "log":
        log_path = args.log_file or "/tmp/mc_run.log"
        if os.path.exists(log_path):
            with open(log_path) as f:
                lines = f.readlines()
                print(f"\n📝 日志 ({log_path}):")
                for l in lines[-30:]:
                    print(l.rstrip())
        else:
            print(f"❌ 日志文件不存在: {log_path}")


# ════════════════════════════════════════════════════════════
# Record 域 (预留)
# ════════════════════════════════════════════════════════════

def cmd_record(args):
    """操作录制（预留）"""
    log(f"📹 操作录制功能将在后续版本实现")
    log(f"   预留命令: mc record start|stop|export")
    log(f"   当前请使用看板手动创建原子操作")


# ════════════════════════════════════════════════════════════
# 主解析器
# ════════════════════════════════════════════════════════════

def build_parser():
    parser = argparse.ArgumentParser(
        prog="mc",
        description="Matrix Console — 矩阵养号统一命令入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  mc run --accounts douyin_01,douyin_04 --blueprints browse_v2 --rounds 10
  mc run --accounts douyin_01 --blueprints browse_v2,comment --rounds 5 --mix
  mc account list
  mc account login douyin_04
  mc status all
  mc proxy list
  mc corpus list
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("--json", action="store_true", help="JSON 输出格式")
    parser.add_argument("--log", default="", help="日志文件路径")
    sub = parser.add_subparsers(dest="command", required=True)

    # ── run ──
    p_run = sub.add_parser("run", help="批量执行养号任务")
    p_run.add_argument("--accounts", required=True, help="账号ID列表，逗号分隔")
    p_run.add_argument("--blueprints", required=True, help="蓝图ID列表，逗号分隔")
    p_run.add_argument("--rounds", type=int, default=10, help="每轮循环次数")
    p_run.add_argument("--interval", default="30-60", help="操作间隔范围(秒)")
    p_run.add_argument("--corpus", default="", help="语料分类，逗号分隔")
    p_run.add_argument("--engine", default="auto", choices=["chrome", "camoufox", "auto"], help="浏览器引擎")
    p_run.add_argument("--mix", action="store_true", help="混合随机模式(每轮随机选蓝图)")
    p_run.add_argument("--daemon", action="store_true", help="后台运行")
    p_run.add_argument("--proxy", default="auto", help="代理策略")
    p_run.set_defaults(func=cmd_run)

    # ── account ──
    p_acct = sub.add_parser("account", help="账号管理")
    p_acct.add_argument("action", choices=["list", "login", "status", "export", "import"])
    p_acct.add_argument("name", nargs="?", default="", help="账号ID")
    p_acct.add_argument("--path", default="", help="导入ZIP路径 (import)")
    p_acct.set_defaults(func=cmd_account)

    # ── blueprint ──
    p_bp = sub.add_parser("blueprint", help="蓝图管理")
    p_bp.add_argument("action", choices=["list", "show"])
    p_bp.add_argument("name", nargs="?", default="", help="蓝图名称")
    p_bp.set_defaults(func=cmd_blueprint)

    # ── corpus ──
    p_corpus = sub.add_parser("corpus", help="语料库管理")
    p_corpus.add_argument("action", choices=["list", "add"])
    p_corpus.add_argument("--category", default="", help="分类名称")
    p_corpus.add_argument("--text", default="", help="评论文本")
    p_corpus.set_defaults(func=cmd_corpus)

    # ── proxy ──
    p_proxy = sub.add_parser("proxy", help="代理管理")
    p_proxy.add_argument("action", choices=["list", "test", "set"])
    p_proxy.add_argument("--proxy", default="", help="代理地址")
    p_proxy.add_argument("--account", default="", help="账号ID")
    p_proxy.set_defaults(func=cmd_proxy)

    # ── sms ──
    p_sms = sub.add_parser("sms", help="短信管理")
    p_sms.add_argument("action", choices=["config", "test"])
    p_sms.add_argument("--phone", default="", help="手机号")
    p_sms.set_defaults(func=cmd_sms)

    # ── status ──
    p_status = sub.add_parser("status", help="状态检查")
    p_status.add_argument("action", choices=["all", "accounts", "browsers", "log"])
    p_status.add_argument("--log-file", default="", help="日志文件路径")
    p_status.set_defaults(func=cmd_status)

    # ── record (预留) ──
    p_rec = sub.add_parser("record", help="操作录制（预留）")
    p_rec.add_argument("action", choices=["start", "stop", "export"])
    p_rec.set_defaults(func=cmd_record)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # ── 关闭 FastAPI logger 的噪音 ──
    logging.getLogger().setLevel(logging.INFO if args.verbose else logging.WARNING)

    print_banner()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

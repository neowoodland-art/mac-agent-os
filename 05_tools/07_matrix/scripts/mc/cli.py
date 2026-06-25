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
AGENT_SYNC = Path(os.environ.get("AGENT_SYNC", str(Path.home() / "workbuddy-agent-os" / "agent-sync")))
AGENT_LOCAL = Path(os.environ.get("AGENT_LOCAL", str(Path.home() / "workbuddy-agent-os" / "agent-local")))
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
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(message)s',
        datefmt='%H:%M:%S',
        force=True,
    )
    if path:
        fh = logging.FileHandler(path, mode='a', encoding='utf-8')
        fh.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))
        fh.setLevel(logging.INFO)
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

    elif args.action == "create":
        from create_identity import create_identity
        create_identity(name=args.name, platform=args.platform)
        log(f"✅ 身份已创建: {args.name}")

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
        stagger=getattr(args, 'stagger', '15-30'),
        keep_open=getattr(args, 'keep', False),
        max_browsers=getattr(args, 'max_browsers', 3),
        url=getattr(args, 'url', ''),
        comment_text=getattr(args, 'comment_text', ''),
        reply_text=getattr(args, 'reply_text', ''),
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
# Task 域
# ════════════════════════════════════════════════════════════

def cmd_task(args):
    """智能任务调度"""
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    if args.list:
        print("""
可用任务类型:
  comment  — 定向评论：给链接+方向 → 打开视频 → 评论
    必填: --url        视频链接
    选填: --direction  评论方向 (正面/提问/共鸣/感慨)
          --comment    指定评论内容
          --account    指定账号

  search   — 搜索浏览：给关键词 → 搜索 → 随机浏览/点赞
    必填: --keyword    搜索关键词
    选填: --rounds     浏览几个视频

  collect  — 信息采集：给博主名 → 搜索 → 采集主页信息
    必填: --keyword    博主名称

  reply    — 作者回复：打开自己视频 → 读评论 → 回复
    必填: --account    你的账号
    选填: --comment    回复内容（默认自动生成）

示例:
  mc task comment --url https://v.douyin.com/xxx --direction 正面
  mc task search --keyword 美食探店 --rounds 5
  mc task collect --keyword 张三说科技
  mc task reply --account douyin_test
""")
        return

    if not args.task_type:
        print("请指定任务类型: comment / search / collect / reply")
        print("查看帮助: mc task --list")
        return

    from mc.task import Task, run_task
    import asyncio

    task = Task(
        type=args.task_type,
        url=args.url,
        keyword=args.keyword,
        direction=args.direction,
        comment_text=args.comment,
        account=args.account,
        rounds=args.rounds,
    )

    errors = task.validate()
    if errors:
        print("❌ 参数错误:")
        for e in errors:
            print(f"   - {e}")
        print("\n查看帮助: mc task --list")
        return

    task.auto_fill()
    print(f"\n📋 任务: {task.summary()}")
    print(f"    蓝图: {task.blueprint}")
    print(f"    参数: {task.to_task_params()}")

    if not args.yes:
        confirm = input("\n⏎ 确认执行？(Y/n): ").strip().lower()
        if confirm not in ("", "y", "yes"):
            print("已取消")
            return

    result = asyncio.run(run_task(task))
    print(f"\n{'='*50}")
    if result.get("status") == "error":
        print(f"❌ 失败: {result.get('errors', result.get('error', 'unknown'))}")
    else:
        print(f"✅ 完成: {result.get('success', 0)}/{result.get('total_steps', 0)} 步成功")
        if result.get("failed"):
            print(f"⚠️  {result['failed']} 步失败")
    print(f"耗时: {result.get('duration', 0)}s")


# ════════════════════════════════════════════════════════════
# Schedule 域
# ════════════════════════════════════════════════════════════

def cmd_schedule(args):
    """定时任务管理"""
    if args.action == "list":
        from mc.scheduler import cmd_schedule_list
        cmd_schedule_list()
    elif args.action == "add":
        from mc.scheduler import cmd_schedule_add
        cmd_schedule_add(args.id, args.account, args.blueprint, args.time,
                         args.rounds, getattr(args, 'days', '1,2,3,4,5,6,7'), args.args)
    elif args.action == "remove":
        from mc.scheduler import cmd_schedule_remove
        cmd_schedule_remove(args.id)
    elif args.action == "history":
        from mc.scheduler import cmd_schedule_history
        cmd_schedule_history(getattr(args, 'id', ''))
    elif args.action == "start":
        import asyncio
        import logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
        from mc.scheduler import scheduler_loop
        print("🕐 定时调度器启动中...")
        asyncio.run(scheduler_loop())


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

    # 读取主页采集信息
    hp_path = AGENT_LOCAL / "tools" / "matrix" / "data" / "homepage_info.json"
    hp_data = {}
    if hp_path.exists():
        try:
            hp_data = json.loads(hp_path.read_text())
        except: pass

    info = mgr.system_info()
    
    if args.json:
        # JSON 输出: 整合系统信息 + 采集信息 + 账号列表
        result = {
            "system": info,
            "collected_at": hp_data.get("collected_at", ""),
            "accounts": mgr.list_accounts(),
            "homepage": hp_data.get("results", []),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 文本输出
    if args.action in ("all", "accounts"):
        print(f"\n📊 系统状态:")
        print(f"   总账号: {info['total_accounts']}")
        print(f"   已启用: {info['enabled_accounts']}")
        print(f"   已登录: {info['logged_in_accounts']}")
        print(f"   身份目录: {info['identity_dirs']}")
        print(f"   蓝图: {info['blueprints']}")
        if hp_data.get("collected_at"):
            print(f"   最后采集: {hp_data['collected_at'][:19]}")

    if args.action in ("all", "browsers"):
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
# Record 域 — 原子操作录制
# ════════════════════════════════════════════════════════════

def cmd_record(args):
    """操作录制入口"""
    action = args.record_action if hasattr(args, 'record_action') else ""

    if action == "start":
        _cmd_record_start(args)
    elif action == "analyze":
        _cmd_record_analyze(args)
    elif action == "export":
        _cmd_record_export(args)
    elif action == "delete":
        _cmd_record_delete(args)
    elif action == "list":
        _cmd_record_list()
    else:
        log(f" 可用: mc record start, mc record analyze <path>, mc record export <path>, mc record list")


def _cmd_record_start(args):
    account = getattr(args, 'account', None) or "douyin_01"
    platform = getattr(args, 'platform', None) or "auto"
    # "auto" 时从账号解析平台
    if platform == "auto":
        try:
            from matrix_mgmt import MatrixManager
            mgr = MatrixManager()
            for a in mgr.list_accounts():
                if a["id"] == account:
                    p = a.get("platform", "")
                    if p in ("douyin", "xiaohongshu"):
                        platform = p
                    break
        except: pass
    log(f"🎬 开始录制 account={account} platform={platform}")
    import asyncio
    from mc.recorder import _run_interactive
    try:
        asyncio.run(_run_interactive(account, platform))
    except KeyboardInterrupt:
        log("\n👋 录制已中断")
    except Exception as e:
        log(f"❌ 录制异常: {e}")


def _cmd_record_analyze(args):
    path = getattr(args, 'recording_path', None)
    if not path:
        log("❌ 用法: mc record analyze <录制包路径>")
        return
    from mc.analyzer import analyze_recording_file
    log(f"🔍 分析 {path}")
    result = analyze_recording_file(path)
    for i, a in enumerate(result.get("actions", [])):
        at = a.get("action_type", "?")
        desc = a.get("action_desc", "")
        log(f"  {'✅' if at != 'unknown' else '❌'} 步骤{i+1}: [{at}] {desc}")
    if getattr(args, 'json', False):
        import json; print(json.dumps(result, ensure_ascii=False, indent=2))


def _cmd_record_export(args):
    path = getattr(args, 'recording_path', None)
    if not path:
        log("❌ 用法: mc record export <录制包路径>")
        return
    from mc.exporter import export_recording
    log(f"📦 导出 {path}")
    result = export_recording(path)
    if result.get("saved_blueprint"):
        log(f"  ✅ 蓝图: {result['saved_blueprint']}")
    if result.get("saved_code"):
        log(f"  ✅ 代码: {result['saved_code']}")
    seq = result.get("summary", {}).get("action_sequence", [])
    log(f"  操作序列: {' → '.join(seq)}")


def _cmd_record_delete(args):
    path = getattr(args, 'recording_path', None)
    if not path:
        log("❌ 用法: mc record delete <录制包路径>")
        return
    from mc.recorder import RecordingSession
    if RecordingSession.delete_recording(path):
        log(f"✅ 已删除: {path}")
    else:
        log(f"❌ 删除失败: {path}")


def _cmd_record_list():
    from mc.recorder import RecordingSession
    rs = RecordingSession.list_recordings()
    if not rs:
        log("📭 没有录制包")
        return
    for r in rs:
        log(f"  📹 {r['account']:15s} {r['steps']:2d}步 {r['duration']:5.0f}s {r.get('created','')[:16]} ({r['file']})")


# ════════════════════════════════════════════════════════════
# Op 域 — 原子操作注册/删除
# ════════════════════════════════════════════════════════════

def cmd_op(args):
    """原子操作管理"""
    action = args.op_action if hasattr(args, 'op_action') else ""

    if action == "register":
        _cmd_op_register(args)
    elif action == "delete":
        _cmd_op_delete(args)
    elif action == "list":
        _cmd_op_list(args)


def _cmd_op_register(args):
    """注册蓝图为原子操作"""
    name = getattr(args, 'name', '')
    source = getattr(args, 'source', 'recorded')
    blueprint_name = getattr(args, 'from_blueprint', '')

    if not name:
        log("❌ 用法: mc op register --name <操作名> --from <蓝点名> [--source recorded|manual]")
        return

    log(f"📝 注册原子操作: {name} (source={source})")

    from matrix_mgmt import MatrixManager
    mgr = MatrixManager()

    # 如果指定了蓝图，先验证蓝图存在
    if blueprint_name:
        bps = mgr.list_blueprints()
        bp = next((b for b in bps if b['name'] == blueprint_name), None)
        if not bp:
            log(f"❌ 蓝图 {blueprint_name} 不存在")
            return

    # 注册到 OP_GRAPH
    try:
        # 构建 OP_GRAPH 条目
        entry = {
            "name": name,
            "platform": getattr(args, 'platform', '通用'),
            "category": "custom",
            "label": f"🎬 {name}",
            "requires": [],
            "allows": ["rest", "go_back"],
            "can_be_first": True,
            "desc": f"原子操作 (source={source})",
            "_source": source,
        }
        # 通过 MatrixManager 注册
        result = mgr.register_atomic_op(entry)
        log(f"✅ 已注册: {name}")
    except Exception as e:
        log(f"❌ 注册失败: {e}")


def _cmd_op_delete(args):
    """删除原子操作"""
    name = getattr(args, 'name', '')
    if not name:
        log("❌ 用法: mc op delete --name <操作名>")
        return
    from matrix_mgmt import MatrixManager
    mgr = MatrixManager()
    try:
        mgr.delete_atomic_op(name)
        log(f"✅ 已删除: {name}")
    except Exception as e:
        log(f"❌ 删除失败: {e}")


def _cmd_op_list(args):
    """列出所有原子操作"""
    from matrix_mgmt import MatrixManager
    mgr = MatrixManager()
    ops = mgr.list_atomic_ops()
    log(f"📋 原子操作 ({len(ops)}):")
    for op in ops:
        source = op.get("_source", "manual")
        source_tag = "🤖" if source == "recorded" else "✋"
        log(f"  {source_tag} {op['name']:25s} {op.get('platform','?'):12s} {op.get('desc','')[:30]}")


# ════════════════════════════════════════════════════════════
# 采集命令
# ════════════════════════════════════════════════════════════

def cmd_collect(args):
    """mc collect — 主页信息采集（通过 mc run + 蓝图）"""
    import asyncio

    # 解析账号
    account_ids = []
    if args.all:
        # 采集所有启用的账号
        from matrix_mgmt import MatrixManager
        mgr = MatrixManager()
        for a in mgr.list_accounts():
            if a.get("enabled") != False:
                account_ids.append(a["id"])
        if not account_ids:
            print("⚠️ 没有找到启用的账号")
            return
        log(f"📋 采集所有 {len(account_ids)} 个账号")
    elif args.phone:
        # 按手机号查找账号ID
        from matrix_mgmt import MatrixManager
        mgr = MatrixManager()
        for a in mgr.list_accounts():
            if a.get("phone") == args.phone and a.get("platform") == "douyin":
                account_ids.append(a["id"])
        if not account_ids:
            print(f"⚠️ 手机号 {args.phone} 未找到对应账号")
            return
    elif args.account:
        account_ids = [args.account]
    elif args.status:
        # 查看采集状态
        status_path = AGENT_LOCAL / "tools" / "matrix" / "data" / "collect_progress.json"
        if status_path.exists():
            print(json.dumps(json.loads(status_path.read_text()), indent=2, ensure_ascii=False))
        else:
            print("⏸️ 当前无采集任务")
        return
    else:
        print("⚠️ 请指定 --all（全部）/ --phone（手机号）/ --account（账号ID）")
        print("   或使用: mc run --accounts=A,B --blueprints=douyin_read_profile --rounds=1")
        return
    
    from mc.run import BatchRunner
    runner = BatchRunner(
        accounts=account_ids,
        blueprints=["douyin_read_profile"],
        rounds=1,
        interval_range=(5, 10),
    )
    report_dict = asyncio.run(runner.run())
    if args.json:
        print(json.dumps(report_dict, ensure_ascii=False, indent=2))
    else:
        print(f"✅ 采集完成: 成功{report_dict.get('success',0)} 失败{report_dict.get('failed',0)} 耗时{report_dict.get('duration',0):.0f}s")


# ════════════════════════════════════════════════════════════
# 蒸馏命令
# ════════════════════════════════════════════════════════════

def cmd_distill(args):
    """mc distill — 内容蒸馏（元数据提取 + 关键词索引）"""
    import json
    from pathlib import Path
    from datetime import datetime

    # 解析路径
    source_dir = Path(args.source)
    if not source_dir.is_absolute():
        source_dir = AGENT_SYNC / source_dir
    if not source_dir.exists():
        print(f"❌ 源目录不存在: {source_dir}")
        return

    output_dir = Path(args.output) if args.output else AGENT_LOCAL / "memory" / "long_term"
    if not output_dir.is_absolute():
        output_dir = AGENT_LOCAL / output_dir

    mode = args.mode
    batch_size = args.batch_size

    print(f"📋 蒸馏模式: {mode}")
    print(f"📂 源目录: {source_dir}")
    print(f"📂 输出目录: {output_dir}")

    # 扫描所有 .md 文件
    files = sorted(source_dir.glob("*.md"))
    print(f"📄 找到 {len(files)} 篇投稿")

    if mode == "extract":
        # ── extract 模式：提取元数据 + 关键词索引 ──
        entries = []
        for f in files:
            name = f.stem  # e.g. 20260518_yuan_benchu_经济分析_008
            parts = name.split("_")
            date_str = parts[0] if len(parts) > 0 else ""
            author = parts[1] if len(parts) > 1 else "unknown"
            category = parts[-2] if len(parts) >= 4 else "unknown"
            seq = parts[-1] if len(parts) >= 4 else ""

            # 格式化日期
            try:
                dt = datetime.strptime(date_str, "%Y%m%d")
                formatted_date = dt.strftime("%Y-%m-%d")
            except:
                formatted_date = date_str

            # 读取 front matter 和正文
            content = f.read_text(encoding="utf-8")
            lines = content.split("\n")

            # 提取 front matter 中的标签
            keywords = []
            in_front = False
            for line in lines:
                if line.startswith("---"):
                    in_front = not in_front
                    continue
                if in_front:
                    if "tag" in line.lower() or "标签" in line:
                        val = line.split(":", 1)[-1].strip().strip('"').strip("'")
                        for kw in val.replace("#", "").replace("，", ",").split(","):
                            kw = kw.strip()
                            if kw:
                                keywords.append(kw)
                elif line.strip().startswith("> **标签**"):
                    # Markdown 正文标签行：> **标签**: #tag1 #tag2
                    tag_line = line.split("**:", 1)[-1] if "**: " in line else line.split("**:", 1)[-1]
                    for tag in tag_line.replace("#", "").split():
                        tag = tag.strip()
                        if tag and tag not in keywords:
                            keywords.append(tag)

            # 计算字数（不含 front matter）
            body_start = 0
            fm_count = 0
            for line in lines:
                if line.startswith("---"):
                    fm_count += 1
                    if fm_count == 2:
                        body_start = lines.index(line) + 1
                        break
            body = "\n".join(lines[body_start:])
            char_count = len(body.strip())
            word_count = len(body.strip().replace(" ", ""))

            entry = {
                "file": f.name,
                "date": formatted_date,
                "author": author,
                "category": category,
                "seq": seq,
                "keywords": keywords,
                "char_count": char_count,
                "line_count": len(lines),
                "summary": body[:80].strip().replace("\n", " ") + "..." if len(body) > 80 else body.strip(),
            }
            entries.append(entry)

        # 按分类统计
        categories = {}
        for e in entries:
            cat = e["category"]
            if cat not in categories:
                categories[cat] = {"count": 0, "total_chars": 0, "tags": set()}
            categories[cat]["count"] += 1
            categories[cat]["total_chars"] += e["char_count"]
            for kw in e["keywords"]:
                categories[cat]["tags"].add(kw)

        # 输出 JSON
        result = {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "source_dir": str(source_dir),
            "total_files": len(files),
            "total_chars": sum(e["char_count"] for e in entries),
            "categories": {k: {
                "count": v["count"],
                "total_chars": v["total_chars"],
                "tags": sorted(v["tags"]),
            } for k, v in sorted(categories.items())},
            "entries": entries,
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"keyword_index_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"✅ 提取完成: {len(entries)} 篇, {len(categories)} 分类")
            for cat, info in sorted(categories.items()):
                print(f"   {cat}: {info['count']}篇, {info['total_chars']}字符, {len(info['tags'])}个标签")
            print(f"📄 输出: {output_path}")

    elif mode == "llm":
        # ── llm 模式：按分类生成摘要报告 ──
        # 先提取元数据
        categories = {}
        for f in files:
            name = f.stem
            parts = name.split("_")
            category = parts[-2] if len(parts) >= 4 else "unknown"
            if category not in categories:
                categories[category] = []
            categories[category].append(f)

        print(f"\n📊 分类分布（共 {len(categories)} 类）:")
        for cat, cat_files in sorted(categories.items()):
            print(f"   {cat}: {len(cat_files)}篇")
            if args.json:
                for f in cat_files[:10]:
                    print(f"     - {f.name}")

        total_batches = (len(files) + batch_size - 1) // batch_size
        print(f"\n📦 批次数: {total_batches}（batch_size={batch_size}）")

        # 分组输出（每批一个 JSON）
        batches = []
        for i in range(0, len(files), batch_size):
            batch_files = files[i:i + batch_size]
            batch = []
            for f in batch_files:
                content = f.read_text(encoding="utf-8")
                name = f.stem
                parts = name.split("_")
                batch.append({
                    "file": f.name,
                    "date": parts[0] if len(parts) > 0 else "",
                    "category": parts[-2] if len(parts) >= 4 else "",
                    "char_count": len(content),
                    "preview": content[:200],
                })
            batches.append(batch)

        # 输出摘要报告
        report = {
            "version": "1.0.0",
            "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "source_dir": str(source_dir),
            "mode": "llm",
            "total_files": len(files),
            "total_batches": total_batches,
            "categories": {cat: len(cat_files) for cat, cat_files in sorted(categories.items())},
            "batches": batches,
            "note": "AI 摘要生成需要 LLM 集成，当前为元数据聚合版本。",
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"submission_report_{datetime.now().strftime('%Y%m%d')}.json"
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"\n📄 报告输出: {output_path}")
            print("⚠️  注意: AI 摘要生成需要 LLM 集成。当前为元数据聚合版本。")

    print("✅ 蒸馏完成")


# ════════════════════════════════════════════════════════════
# 互动命令
# ════════════════════════════════════════════════════════════

def cmd_interact(args):
    """mc interact — 评论互动编排"""
    from mc.interact import InteractOrchestrator

    accounts = [a.strip() for a in args.accounts.split(",") if a.strip()]
    interval_parts = args.interval.split("-")
    interval = {"min": int(interval_parts[0]), "max": int(interval_parts[1])}

    orchestrator = InteractOrchestrator(
        accounts=[{"id": a, "platform": "douyin", "machine": ""} for a in accounts],
        params={
            "url": args.url,
            "strategy": args.strategy,
            "direction": args.direction,
            "corpus": args.corpus,
            "blueprint": args.blueprint,
            "rounds": 1,
            "interval": interval,
            "dry_run": args.dry_run,
        },
    )

    if args.dry_run:
        plan = orchestrator.plan()
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return

    import asyncio
    result = asyncio.run(orchestrator.run())
    print(json.dumps(result, indent=2, ensure_ascii=False))


# ════════════════════════════════════════════════════════════
# 登录命令
# ════════════════════════════════════════════════════════════

def cmd_login(args):
    """mc login — 打开浏览器登录账号"""
    import subprocess
    login_script = SCRIPTS_DIR / "login_identity.py"
    
    if args.account:
        target = args.account
    elif args.phone:
        # 从账号注册表查找
        try:
            from matrix_mgmt import MatrixManager
            mgr = MatrixManager()
            for a in mgr.list_accounts():
                if a.get("phone") == args.phone:
                    target = a.get("identity_dir", a["id"]).replace("identities/", "")
                    break
            else:
                print(f"❌ 手机号 {args.phone} 未找到")
                return
        except:
            target = args.phone
    else:
        print("❌ 请指定 --account 或 --phone")
        return
    
    platform = args.platform
    cmd = [sys.executable, str(login_script), target, "--platform", platform]
    print(f"🚀 打开登录: {' '.join(cmd)}")
    subprocess.Popen(cmd, cwd=str(SCRIPTS_DIR))


# ═══════════════════════════════════════════════════════════════
# 智能登录路由
# ═══════════════════════════════════════════════════════════════

def cmd_smart_login(args):
    """mc smart-login — 智能全自动登录（自动匹配平台 + 前置检测）"""
    account_id = args.account_id
    phone = args.phone
    timeout = args.timeout
    skip_check = args.skip_check
    
    # ── 前置检测: 从账号信息获取 platform 和 phone ──
    platform = "douyin"  # 默认
    try:
        from matrix_mgmt import MatrixManager
        mgr = MatrixManager()
        for a in mgr.list_accounts():
            if a["id"] == account_id:
                p = a.get("platform", "")
                if p in ("douyin", "xiaohongshu"):
                    platform = p
                if not phone:
                    phone = a.get("phone", "")
                break
    except Exception:
        pass
    
    print(f"{'='*55}")
    print(f" 🔐 智能登录: {account_id}")
    print(f"    平台: {platform}")
    print(f"    手机: {phone or '从配置读取'}")
    print(f"{'='*55}")
    
    # ── 前置检测: 检查是否已登录（非强制登录时）──
    if not skip_check:
        try:
            # 检查本地 cookie 状态
            from pathlib import Path
            home = Path.home()
            identities_root = home / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix" / "identities"
            
            # 查找该账号的 identity_dir
            acct_identity = account_id
            try:
                for a in mgr.list_accounts():
                    if a["id"] == account_id:
                        acct_identity = (a.get("identity_dir") or a.get("identity_hint") or account_id).replace("identities/", "")
                        break
            except Exception:
                pass
            
            identity_path = identities_root / acct_identity / "user_data"
            cookie_file = identity_path / "cookies.sqlite"
            
            if cookie_file.exists():
                import sqlite3
                try:
                    conn = sqlite3.connect(str(cookie_file), timeout=3)
                    cur = conn.execute(
                        "SELECT count(*) FROM moz_cookies WHERE name LIKE '%session%'"
                    )
                    session_count = cur.fetchone()[0]
                    conn.close()
                    
                    if session_count > 0:
                        print(f"\n  ✅ 已检测到登录态 (session cookie x{session_count})")
                        print(f"     如需重新登录请使用 --skip-check 参数")
                        return
                except Exception:
                    pass
        except Exception:
            pass
    
    # ── 根据平台选择登录方式 ──
    if platform == "xiaohongshu":
        # 小红书：全自动 SMS 登录
        xhs_script = SCRIPTS_DIR / "matrix_modules" / "account" / "xiaohongshu_login.py"
        if not xhs_script.exists():
            print(f"❌ 小红书登录脚本不存在: {xhs_script}")
            return
        print(f"\n📕 小红书全自动登录: {account_id}")
        import subprocess
        xhs_args = [sys.executable, str(xhs_script), account_id, "--force"]
        if phone:
            xhs_args.extend(["--phone", phone])
        subprocess.run(xhs_args, cwd=str(SCRIPTS_DIR))
    else:
        # 抖音：login_identity.py 开浏览器手动登录
        login_script = SCRIPTS_DIR / "login_identity.py"
        if not login_script.exists():
            print(f"❌ 登录脚本不存在: {login_script}")
            return
        print(f"\n🚀 打开浏览器: {account_id}")
        import subprocess
        subprocess.run([sys.executable, str(login_script), account_id], cwd=str(SCRIPTS_DIR))


# ════════════════════════════════════════════════════════════
# 平台插件命令路由
# ════════════════════════════════════════════════════════════

def cmd_platform(args, plat_name, plat_inst):
    """路由 mc [platform] [action] 到插件实现"""
    action = args.action
    account = args.account or "default"
    
    # 参数映射
    kwargs = {"account_name": account}
    if action == "publish":
        kwargs["file_path"] = args.file
        kwargs["title"] = args.title
        kwargs["desc"] = args.desc
    if action == "nurture":
        kwargs["blueprint"] = args.blueprint
    
    # 调用插件方法
    method = getattr(plat_inst, action, None)
    if not method:
        print(f"❌ {plat_name} 不支持 {action}")
        return
    
    result = method(**kwargs)
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        status = result.get("status", "error")
        icon = "✅" if status == "ok" else "❌"
        msg = result.get("message") or result.get("output", "")[:100] or status
        print(f"{icon} [{plat_name}] {action}: {msg}")


# ════════════════════════════════════════════════════════════
# 远程多机命令
# ════════════════════════════════════════════════════════════

def _lookup_machines():
    """读取机器注册表, 返回 {hostname: {ip, user, ...}}
    
    数据来源 (优先级):
    1. agent-local/runtime/machines.json  (手动注册)
    2. ORACLE.yaml (联邦宪法，机器定义的一级来源)
    3. 04_memory/cross_machine/machines/ (git 同步的心跳数据)
    """
    machines = {}
    
    # 来源1: 本机注册表
    local_reg = AGENT_LOCAL / "runtime" / "machines.json"
    if local_reg.exists():
        try:
            machines.update(json.loads(local_reg.read_text()))
        except: pass
    
    # 来源2: ORACLE.yaml (最高优先级的机器定义)
    oracle_path = _find_oracle()
    if oracle_path:
        try:
            import yaml
            with open(oracle_path) as f:
                oracle = yaml.safe_load(f)
            for name, info in oracle.get("machines", {}).items():
                hn = info.get("hostname", name)
                if hn not in machines:
                    machines[hn] = {
                        "hostname": hn,
                        "ip": info.get("tailscale_ip", ""),
                        "port": info.get("dashboard_port", 9988),
                        "user": info.get("ssh_user", ""),
                        "via": "ssh",
                        "oracle_name": name,
                    }
        except Exception:
            pass  # ORACLE 可选的，无报错
    
    # 来源3: cross_machine 目录 (从 Gitee 同步的远程心跳信息)
    cross_dir = AGENT_SYNC / "04_memory" / "cross_machine" / "machines"
    if cross_dir.exists():
        for uid_dir in sorted(cross_dir.iterdir()):
            if uid_dir.is_dir():
                hb = uid_dir / "heartbeat.json"
                if hb.exists():
                    try:
                        d = json.loads(hb.read_text())
                        hn = d.get("machine_name", d.get("hostname", ""))
                        if hn and hn not in machines:
                            machines[hn] = {
                                "hostname": hn,
                                "machine_uid": d.get("machine_uid", ""),
                                "ip": "127.0.0.1",
                                "port": 9988,
                                "user": d.get("ssh_user", d.get("user", "")),
                                "status": d.get("status", "unknown"),
                            }
                    except: pass
    
    # 没找到则返回本机
    if not machines:
        import socket
        hn = socket.gethostname()
        machines[hn] = {
            "hostname": hn,
            "ip": "127.0.0.1",
            "port": 9988,
            "user": os.environ.get("USER", ""),
        }
    
    return machines


def _find_oracle():
    """查找 ORACLE.yaml 文件位置"""
    # 尝试多个可能的位置
    candidates = [
        AGENT_SYNC / "ORACLE.yaml",
        AGENT_SYNC / "oracle.yaml",
        Path.home() / "workbuddy-agent-os" / "agent-sync" / "ORACLE.yaml",
    ]
    # 如果 AGENT_SYNC 未设置，也尝试工作目录的父目录
    if not AGENT_SYNC:
        cwd = Path.cwd()
        for p in [cwd, cwd.parent, cwd.parent.parent]:
            candidates.insert(0, p / "ORACLE.yaml")
    
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def _http_call(host_info, path, method="GET", data=None):
    """通过 HTTP API 调用远程机器 (Tailscale/局域网)"""
    try:
        import requests as req_lib
    except ImportError:
        return {"status": "error", "message": "requests 库未安装, 请 pip install requests"}
    
    ip = host_info.get("ip", host_info.get("hostname", "localhost"))
    port = host_info.get("port", 9988)
    url = f"http://{ip}:{port}{path}"
    
    try:
        # 绕过系统代理 (SOCKS5 代理可能导致 502)
        no_proxy = {"http": "", "https": ""}
        headers = {"User-Agent": "mc-remote/1.0"}
        
        if method == "GET":
            r = req_lib.get(url, timeout=10, proxies=no_proxy, headers=headers)
        else:
            r = req_lib.post(url, json=data, timeout=10, proxies=no_proxy, headers=headers)
        
        if r.status_code == 200:
            return r.json()
        return {"status": "error", "message": f"HTTP {r.status_code}: {r.text[:200]}"}
    except req_lib.exceptions.ConnectionError:
        return {"status": "error", "message": "连接失败 (Connection refused)"}
    except req_lib.exceptions.Timeout:
        return {"status": "error", "message": "超时 (10s)"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _ssh_call(host_info, command):
    """通过 SSH 在远程机器执行命令"""
    import subprocess
    
    user = host_info.get("user", "")
    ip = host_info.get("ip", host_info.get("hostname", ""))
    ssh_target = f"{user}@{ip}" if user else ip
    
    # 自动设置环境变量（每台机器可能不同，从 ORACLE 获取路径）
    # 远程运行时会先 source 环境变量再执行命令
    env_setup = "export AGENT_SYNC=\"$HOME/workbuddy-agent-os/agent-sync\"; "
    env_setup += "export AGENT_LOCAL=\"$HOME/workbuddy-agent-os/agent-local\"; "
    wrapped_cmd = f"{env_setup} {command}"
    
    full_cmd = ["ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no",
                ssh_target, wrapped_cmd]
    
    try:
        r = subprocess.run(full_cmd, capture_output=True, text=True, timeout=60)
        return {
            "status": "ok" if r.returncode == 0 else "error",
            "returncode": r.returncode,
            "stdout": r.stdout[:5000],
            "stderr": r.stderr[:500],
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "SSH 超时 (60s)"}
    except FileNotFoundError:
        return {"status": "error", "message": "ssh 命令未找到"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_remote(args):
    """mc remote — 远程多机管理"""
    
    if args.remote_action == "list":
        machines = _lookup_machines()
        if args.json:
            print(json.dumps(machines, ensure_ascii=False, indent=2))
            return
        
        print(f"\n📡 已注册机器 ({len(machines)}):")
        for hn, info in machines.items():
            ip = info.get("ip", "?")
            port = info.get("port", 9988)
            user = info.get("user", "")
            via = info.get("via", "http")
            print(f"  {hn:20s}  {user:10s}  {ip:15s}:{port}  (via {via})")
        return
    
    if args.remote_action == "ping":
        machines = _lookup_machines()
        if args.host:
            machines = {k: v for k, v in machines.items()
                       if args.host in k or args.host in v.get("ip", "")}
        
        results = {}
        for hn, info in machines.items():
            r = _http_call(info, "/api/health")
            results[hn] = {
                "reachable": r.get("status") == "ok",
                "response": r.get("hostname", ""),
            }
        
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return
        
        print(f"\n📡 连通性测试 ({len(results)}):")
        for hn, r in results.items():
            icon = "✅" if r["reachable"] else "❌"
            echo = r.get("response", "")[:20]
            print(f"  {icon} {hn:20s}  {echo}")
        return
    
    if args.remote_action == "status":
        machines = _lookup_machines()
        if args.host:
            machines = {k: v for k, v in machines.items()
                       if args.host in k or args.host in v.get("ip", "")}
        
        results = {}
        for hn, info in machines.items():
            r = _http_call(info, "/api/machine/status")
            results[hn] = r
        
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return
        
        print(f"\n📊 多机状态 ({len(results)}):")
        for hn, r in results.items():
            status_icon = "✅" if r.get("status") == "ok" or "hostname" in r else "❌"
            mat = r.get("matrix", {})
            hp = r.get("homepage_info", {})
            disk = r.get("disk", {})
            guardd = r.get("guardd", {})
            guardd_icon = "🟢" if guardd.get("running") else "🔴"
            collected = hp.get("collected_at", "")[:16] if hp.get("collected_at") else "未采集"
            print(f"  {status_icon} {hn:20s} {'v'+r.get('version','?'):10s}"
                  f" 账号:{mat.get('total_accounts','?')} 已登录:{mat.get('logged_in_accounts','?')}")
            print(f"      {guardd_icon} guardd  | 🕐 {collected} | 💾 {disk.get('free_gb','?')}G 剩余")
        return
    
    if args.remote_action == "exec":
        command = " ".join(args.command)
        host = args.host
        via = args.via
        
        machines = _lookup_machines()
        host_info = None
        for hn, info in machines.items():
            if host in hn or host in info.get("ip", ""):
                host_info = info
                break
        
        if not host_info:
            host_info = {"ip": host, "port": 9988, "via": "http"}
        
        # HTTP 方式 (Tailscale/局域网)
        if via in ("auto", "http"):
            result = _http_call(host_info, "/api/machine/exec", method="POST",
                              data={"command": command})
            if result.get("status") == "ok" or "stdout" in result:
                if args.json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    out = result.get("stdout", "")
                    err = result.get("stderr", "")
                    if out:
                        print(out[:5000])
                    if err:
                        print(f"⚠️ stderr: {err}")
                return
            elif via == "http":
                print(f"❌ HTTP 执行失败: {result.get('message','')}")
                return
        
        # SSH 方式
        if via in ("auto", "ssh"):
            result = _ssh_call(host_info, command)
            if result.get("status") == "ok" or result.get("returncode") == 0:
                if args.json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    print(result.get("stdout", "")[:5000])
                    if result.get("stderr", ""):
                        print(f"⚠️ stderr: {result['stderr'][:500]}")
                return
            elif via == "ssh":
                print(f"❌ SSH 执行失败: {result.get('message','')}")
                return
        
        print(f"❌ 无法连接到 {host}: HTTP 和 SSH 均失败")


# ════════════════════════════════════════════════════════════
# publish — 发布内容
# ════════════════════════════════════════════════════════════

def cmd_publish(args):
    """mc publish — 发布视频/图文到平台"""
    import subprocess
    publish_script = SCRIPTS_DIR / "publish_video.py"
    if not publish_script.exists():
        print(f"❌ 发布脚本不存在: {publish_script}")
        return 1
    
    cmd = [sys.executable, str(publish_script), args.platform,
           "--account", args.account, "--file", args.file]
    if args.title:
        cmd += ["--title", args.title]
    if args.desc:
        cmd += ["--desc", args.desc]
    
    print(f"📤 发布到 {args.platform}: {args.file}")
    result = subprocess.run(cmd, cwd=str(SCRIPTS_DIR))
    return result.returncode


def cmd_config(args):
    """mc config — 查看系统配置"""
    import yaml
    print(f"\n{'='*55}")
    print(" 📋 系统配置")
    print(f"{'='*55}")
    
    # 蓝图
    bp_dir = TOOL_DIR / "blueprints"
    bps = sorted(bp_dir.glob("*.json"))
    print(f"\n   蓝图 ({len(bps)} 个):")
    for bp in bps:
        import json
        try:
            d = json.loads(bp.read_text())
            steps = len(d.get("steps", []))
            plat = d.get("platform", "?")
            print(f"     • {bp.stem:25s} ({plat:12s} {steps}步)")
        except:
            print(f"     • {bp.stem} (读取失败)")
    
    # 身份
    from matrix_mgmt import AGENT_LOCAL
    identities_root = AGENT_LOCAL / "tools" / "matrix" / "identities"
    idents = sorted([d.name for d in identities_root.iterdir() if d.is_dir()]) if identities_root.exists() else []
    print(f"\n   本地身份 ({len(idents)} 个):")
    for name in idents:
        ud = identities_root / name / "user_data"
        has_cookie = len(list(ud.glob("*.sqlite"))) > 0 if ud.exists() else False
        print(f"     {'✅' if has_cookie else '⬜'} {name}")
    
    print()


# ════════════════════════════════════════════════════════════
# 主解析器
# ════════════════════════════════════════════════════════════

def build_parser(subparsers=None, plugin_name="mc"):
    """构建参数解析器
    
    Args:
        subparsers: 如果提供，作为 agentos 插件的子命令注册
        plugin_name: 插件名（默认 mc）
    """
    if subparsers:
        parser = subparsers.add_parser(
            plugin_name,
            help="Matrix Console — 矩阵养号统一命令入口",
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
    else:
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
    p_run.add_argument("--interval", default="30-60", help="轮间隔范围(秒)")
    p_run.add_argument("--stagger", default="15-30", help="身份组间错峰延迟(秒)")
    p_run.add_argument("--max-browsers", type=int, default=3, help="最大同时浏览器数(默认3)")
    p_run.add_argument("--corpus", default="", help="语料分类，逗号分隔")
    p_run.add_argument("--url", default="", help="视频链接（互动蓝图用）")
    p_run.add_argument("--comment-text", default="", help="评论内容（互动蓝图用，支持@corpus）")
    p_run.add_argument("--reply-text", default="", help="回复内容（互动蓝图用）")
    p_run.add_argument("--engine", default="auto", choices=["chrome", "camoufox", "auto"], help="浏览器引擎")
    p_run.add_argument("--mix", action="store_true", help="混合随机模式(每轮随机选蓝图)")
    p_run.add_argument("--daemon", action="store_true", help="后台运行")
    p_run.add_argument("--keep", action="store_true", help="执行完毕后保留浏览器不关闭")
    p_run.add_argument("--proxy", default="auto", help="代理策略")
    p_run.set_defaults(func=cmd_run)

    # ── account ──
    p_acct = sub.add_parser("account", help="账号管理")
    p_acct.add_argument("action", choices=["list", "login", "status", "export", "import", "create"])
    p_acct.add_argument("name", nargs="?", default="", help="账号ID")
    p_acct.add_argument("--platform", default="douyin", choices=["douyin", "xiaohongshu"], help="平台")
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

    # ── record — 原子操作录制 ──
    p_rec = sub.add_parser("record", help="原子操作录制/分析/导出")
    rec_sub = p_rec.add_subparsers(dest="record_action")

    p_rec_start = rec_sub.add_parser("start", help="开始录制")
    p_rec_start.add_argument("--account", default="douyin_01", help="账号ID")
    p_rec_start.add_argument("--platform", default="auto", choices=["auto", "douyin", "xiaohongshu"], help="平台")
    p_rec_start.set_defaults(func=cmd_record)

    p_rec_analyze = rec_sub.add_parser("analyze", help="分析录制包")
    p_rec_analyze.add_argument("recording_path", help="录制包路径")
    p_rec_analyze.set_defaults(func=cmd_record)

    p_rec_export = rec_sub.add_parser("export", help="导出录制包为蓝图+代码")
    p_rec_export.add_argument("recording_path", help="录制包路径")
    p_rec_export.set_defaults(func=cmd_record)

    p_rec_list = rec_sub.add_parser("list", help="列出所有录制包")
    p_rec_list.set_defaults(func=cmd_record)

    p_rec_delete = rec_sub.add_parser("delete", help="删除录制包")
    p_rec_delete.add_argument("recording_path", help="录制包路径")
    p_rec_delete.set_defaults(func=cmd_record)

    p_rec.set_defaults(func=cmd_record)

    # ── task — 智能任务 ──
    p_task = sub.add_parser("task", help="智能任务：自动选账号/蓝图/填参数")
    p_task.add_argument("task_type", nargs="?", choices=["comment", "search", "collect", "reply"],
                        help="任务类型")
    p_task.add_argument("--url", default="", help="视频链接（定向评论用）")
    p_task.add_argument("--keyword", default="", help="搜索/采集关键词")
    p_task.add_argument("--direction", default="", help="评论方向：正面/提问/共鸣/感慨")
    p_task.add_argument("--comment", default="", help="指定评论内容（默认自动生成）")
    p_task.add_argument("--account", default="", help="指定账号（默认自动选）")
    p_task.add_argument("--rounds", type=int, default=1, help="执行轮数")
    p_task.add_argument("--list", action="store_true", help="列出可选任务类型")
    p_task.add_argument("-y", "--yes", action="store_true", help="跳过确认直接执行")
    p_task.set_defaults(func=cmd_task)

    # ── schedule — 定时任务 ──
    p_sched = sub.add_parser("schedule", help="定时任务管理")
    p_sched.add_argument("action", choices=["list", "add", "remove", "start", "history"],
                         help="list=列出 add=添加 remove=删除 start=启动调度器 history=查看历史")
    p_sched.add_argument("--id", default="", help="任务ID")
    p_sched.add_argument("--account", default="", help="账号")
    p_sched.add_argument("--blueprint", default="", help="蓝图")
    p_sched.add_argument("--time", default="09:00", help="执行时间 HH:MM")
    p_sched.add_argument("--days", default="1,2,3,4,5,6,7", help="运行日 1=周一..7=周日,逗号分隔")
    p_sched.add_argument("--rounds", type=int, default=1, help="轮数")
    p_sched.add_argument("--args", default="", help="额外参数 keyword=xxx")
    p_sched.set_defaults(func=cmd_schedule)

    # ── op — 原子操作注册/删除 ──
    p_op = sub.add_parser("op", help="原子操作注册/删除")
    op_sub = p_op.add_subparsers(dest="op_action")

    p_op_reg = op_sub.add_parser("register", help="注册原子操作")
    p_op_reg.add_argument("--name", required=True, help="操作名")
    p_op_reg.add_argument("--from-blueprint", default="", help="从蓝图导入")
    p_op_reg.add_argument("--source", default="recorded", choices=["recorded", "manual"], help="来源标记")
    p_op_reg.add_argument("--platform", default="通用", help="平台")
    p_op_reg.set_defaults(func=cmd_op)

    p_op_del = op_sub.add_parser("delete", help="删除原子操作")
    p_op_del.add_argument("--name", required=True, help="操作名")
    p_op_del.set_defaults(func=cmd_op)

    p_op_list = op_sub.add_parser("list", help="列出所有原子操作")
    p_op_list.set_defaults(func=cmd_op)

    # ── collect — 主页信息采集 ──
    p_collect = sub.add_parser("collect", help="采集账号主页信息")
    p_collect.add_argument("--all", action="store_true", help="采集所有身份")
    p_collect.add_argument("--phone", default="", help="按手机号采集")
    p_collect.add_argument("--account", default="", help="按账号ID采集")
    p_collect.add_argument("--status", action="store_true", help="查看采集进度")
    p_collect.set_defaults(func=cmd_collect)

    # ── distill — 内容蒸馏 ──
    p_distill = sub.add_parser("distill", help="蒸馏 01_submissions 为结构化报告")
    p_distill.add_argument("--mode", choices=["extract", "llm"], default="extract",
                          help="extract=元数据提取 llm=AI摘要生成")
    p_distill.add_argument("--source", default="01_submissions", help="源目录")
    p_distill.add_argument("--output", default="", help="输出目录")
    p_distill.add_argument("--batch-size", type=int, default=10, help="每批篇数（llm模式）")
    p_distill.set_defaults(func=cmd_distill)

    # ── interact — 评论互动 ──
    p_interact = sub.add_parser("interact", help="评论互动：定向评论/三级接力/点赞/热评")
    p_interact.add_argument("--url", required=True, help="目标视频链接")
    p_interact.add_argument("--accounts", required=True, help="账号ID，逗号分隔")
    p_interact.add_argument("--strategy", choices=["comment","chain","like","hot"], default="comment",
                          help="互动策略（默认定向评论）")
    p_interact.add_argument("--direction", default="", help="评论方向：称赞/提问/共鸣/感慨")
    p_interact.add_argument("--corpus", default="", help="语料分类")
    p_interact.add_argument("--blueprint", default="", help="蓝图名（覆盖自动选择）")
    p_interact.add_argument("--interval", default="300-600", help="步间间隔秒数（默认300-600）")
    p_interact.add_argument("--dry-run", action="store_true", help="仅预览不执行")
    p_interact.set_defaults(func=cmd_interact)

    # ── login — 账号登录 ──
    p_login = sub.add_parser("login", help="打开浏览器登录账号")
    p_login.add_argument("--phone", default="", help="按手机号登录")
    p_login.add_argument("--account", default="", help="按账号ID登录")
    p_login.add_argument("--platform", default="auto", choices=["auto", "douyin", "xiaohongshu"], help="平台")
    p_login.set_defaults(func=cmd_login)

    # ── smart-login — 智能登录（自动检测平台+状态+全自动）──
    p_smart = sub.add_parser("smart-login", help="智能登录: 自动检测平台+状态+全自动")
    p_smart.add_argument("account_id", help="账号 ID (如 douyin_01 / xhs_01)")
    p_smart.add_argument("--phone", "-p", default="", help="手机号（选填）")
    p_smart.add_argument("--timeout", "-t", type=int, default=30,
                         help="浏览器超时自动关闭分钟数（默认 30）")
    p_smart.add_argument("--skip-check", action="store_true",
                         help="跳过登录态前置检测（强制重新登录）")
    p_smart.set_defaults(func=cmd_smart_login)

    # ── remote — 远程多机命令 ──
    p_remote = sub.add_parser("remote", help="远程多机管理 (通过 Tailscale/SSH/HTTP)")
    remote_sub = p_remote.add_subparsers(dest="remote_action")

    p_remote_exec = remote_sub.add_parser("exec", help="在远程机器执行命令")
    p_remote_exec.add_argument("host", help="远程机器 hostname 或 Tailscale IP")
    p_remote_exec.add_argument("command", nargs="+", help="要执行的命令, 如 'mc status --json'")
    p_remote_exec.add_argument("--via", default="auto", choices=["auto", "http", "ssh"],
                               help="通信方式: auto/http/ssh")
    p_remote_exec.set_defaults(func=cmd_remote)

    p_remote_status = remote_sub.add_parser("status", help="查看所有/指定机器状态")
    p_remote_status.add_argument("host", nargs="?", default="", help="指定机器 (默认全部)")
    p_remote_status.add_argument("--via", default="auto", choices=["auto", "http", "ssh"],
                                 help="通信方式")
    p_remote_status.set_defaults(func=cmd_remote)

    p_remote_ping = remote_sub.add_parser("ping", help="测试机器连通性")
    p_remote_ping.add_argument("host", nargs="?", default="", help="指定机器 (默认全部)")
    p_remote_ping.set_defaults(func=cmd_remote)

    p_remote_list = remote_sub.add_parser("list", help="列出已注册机器")
    p_remote_list.set_defaults(func=cmd_remote)

    # ══════════════════════════════════════════════════════
    # 动态发现平台插件: mc [platform] [action] --account <name>
    # ══════════════════════════════════════════════════════
    try:
        TOOL_DIR = SCRIPTS_DIR.parent
        sys.path.insert(0, str(TOOL_DIR))
        from platforms import discover_platforms
        platforms = discover_platforms()
        for plat_name, plat_inst in platforms.items():
            p_plat = sub.add_parser(plat_name, help=f"{plat_inst.display_name} 操作")
            p_plat.add_argument("action", choices=["login", "collect", "status", "publish", "nurture"],
                                help="操作类型")
            p_plat.add_argument("--account", default="", help="账号ID或手机号")
            p_plat.add_argument("--file", default="", help="发布文件路径")
            p_plat.add_argument("--title", default="", help="发布标题")
            p_plat.add_argument("--desc", default="", help="发布描述")
            p_plat.add_argument("--blueprint", default="daily", help="养号蓝图")
            p_plat.set_defaults(func=lambda a, pn=plat_name, pi=plat_inst: cmd_platform(a, pn, pi))
    except Exception as e:
        pass  # 插件加载失败不影响其他命令

    # ── publish — 发布内容到平台 ──
    p_publish = sub.add_parser("publish", help="发布视频/图文到平台")
    p_publish.add_argument("platform", choices=["douyin", "xiaohongshu"], help="目标平台")
    p_publish.add_argument("--account", required=True, help="账号ID")
    p_publish.add_argument("--file", required=True, help="文件路径")
    p_publish.add_argument("--title", default="", help="标题")
    p_publish.add_argument("--desc", default="", help="描述")
    p_publish.set_defaults(func=cmd_publish)

    # ── config — 配置展示 ──
    p_config = sub.add_parser("config", help="查看系统配置")
    p_config.add_argument("action", choices=["show"])
    p_config.set_defaults(func=cmd_config)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # ── 检测是否可以通过 agentos 执行 ──
    # agentos 是最终目标 CLI，mc 是过渡桥接
    # 当 agentos 可用时，转发命令到 agentos，mc 只做壳
    if hasattr(args, 'subcommand') or hasattr(args, 'func'):
        try:
            _try_forward_to_agentos(args)
        except Exception:
            pass  # 转发失败，回退到 mc 执行

    # ── 关闭 FastAPI logger 的噪音 ──
    logging.getLogger().setLevel(logging.INFO if args.verbose else logging.WARNING)

    if not args.json:
        print_banner()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


# ════════════════════════════════════════════════════════════
# agentos 转发
# ════════════════════════════════════════════════════════════

# mc 子命令 → agentos domain 映射表
_AGENTOS_DOMAIN_MAP = {
    'run': 'matrix', 'account': 'matrix',
    'blueprint': 'matrix', 'corpus': 'matrix',
    'login': 'matrix', 'smart-login': 'matrix',
    'publish': 'matrix', 'task': 'matrix', 'op': 'matrix', 'record': 'matrix',
    'distill': 'knowledge',
    'interact': 'matrix',
    'status': 'fleet', 'remote': 'fleet',
    'schedule': 'serve', 'proxy': 'serve', 'sms': 'serve',
}


def _try_forward_to_agentos(args):
    """尝试将 mc 命令转发到 agentos"""
    import subprocess, sys
    from pathlib import Path
    
    # 确定 mc 的子命令（从 args 或 func 名）
    mc_cmd = None
    if hasattr(args, 'subcommand') and args.subcommand:
        mc_cmd = args.subcommand
    elif hasattr(args, 'remote_action') and args.remote_action:
        mc_cmd = 'remote'
    elif hasattr(args, 'func'):
        fn = args.func.__name__
        if fn.startswith('cmd_'):
            mc_cmd = fn[4:]
    
    if not mc_cmd or mc_cmd not in _AGENTOS_DOMAIN_MAP:
        return  # 无法映射到 agentos 领域
    
    domain = _AGENTOS_DOMAIN_MAP[mc_cmd]
    
    # 构建 python -m agentos 命令
    # sys.argv = ['mc', '<subcommand>', '<args>...']
    # → ['python', '-m', 'agentos', '<domain>', '<subcommand>', '<args>...']
    python = sys.executable
    agentos_args = [python, '-m', 'agentos', domain] + sys.argv[1:]
    
    try:
        result = subprocess.run(agentos_args, capture_output=False)
        if result.returncode == 0:
            sys.exit(0)
        # agentos 执行失败，回退到 mc
    except Exception:
        pass  # 走 mc 原始逻辑


if __name__ == "__main__":
    main()

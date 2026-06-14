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
        stagger=getattr(args, 'stagger', '15-30'),
        keep_open=getattr(args, 'keep', False),
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
    """mc collect — 主页信息采集"""
    import subprocess
    runner = SCRIPTS_DIR / "collect_batch_runner.py"
    if not runner.exists():
        runner = SCRIPTS_DIR / "collect_homepage_info.py"
    
    cmd = [sys.executable, str(runner)]
    if args.phone:
        cmd += ["--single", args.phone]
    elif args.account:
        cmd += ["--single", args.account]
    # --all: 不加参数, 默认全部
    
    if not args.status:
        print(f"🚀 启动采集: {' '.join(cmd)}")
        p = subprocess.Popen(cmd, cwd=str(SCRIPTS_DIR))
        if args.json:
            print(json.dumps({"status": "started", "pid": p.pid}))
    else:
        # 查进度
        progress_file = AGENT_LOCAL / "tools" / "matrix" / "data" / "collect_progress.json"
        if progress_file.exists():
            data = json.loads(progress_file.read_text())
            if args.json:
                print(json.dumps(data, ensure_ascii=False))
            else:
                s = data.get("status", "unknown")
                done = data.get("completed", 0)
                total = data.get("total_identities", 0)
                print(f"状态: {s} | {done}/{total} 完成")
        else:
            print("暂无采集进度")


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
    p_run.add_argument("--interval", default="30-60", help="轮间隔范围(秒)")
    p_run.add_argument("--stagger", default="15-30", help="身份组间错峰延迟(秒)")
    p_run.add_argument("--corpus", default="", help="语料分类，逗号分隔")
    p_run.add_argument("--engine", default="auto", choices=["chrome", "camoufox", "auto"], help="浏览器引擎")
    p_run.add_argument("--mix", action="store_true", help="混合随机模式(每轮随机选蓝图)")
    p_run.add_argument("--daemon", action="store_true", help="后台运行")
    p_run.add_argument("--keep", action="store_true", help="执行完毕后保留浏览器不关闭")
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

    # ── login — 账号登录 ──
    p_login = sub.add_parser("login", help="打开浏览器登录账号")
    p_login.add_argument("--phone", default="", help="按手机号登录")
    p_login.add_argument("--account", default="", help="按账号ID登录")
    p_login.add_argument("--platform", default="auto", choices=["auto", "douyin", "xiaohongshu"], help="平台")
    p_login.set_defaults(func=cmd_login)

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

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # ── 关闭 FastAPI logger 的噪音 ──
    logging.getLogger().setLevel(logging.INFO if args.verbose else logging.WARNING)

    if not args.json:
        print_banner()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

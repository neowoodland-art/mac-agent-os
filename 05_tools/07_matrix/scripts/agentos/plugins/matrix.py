"""
agentos matrix — 社交矩阵（抖音/小红书运营）

混合模式：
  - 简单命令：原生实现（不依赖 mc）
  - 复杂命令：完整前置检查后委托 mc（含并发/预检/优雅退出）

执行约束（源自 99_system/ARCHITECTURE_CONSTITUTION.md）：
  - MAX_CONCURRENT = 3    每台机器最多3个浏览器
  - LAUNCH_STAGGER = 15s  浏览器启动间隔
  - AUTO_SHUTDOWN = 30min 超时自动关闭
  - MIN_DISK_GB = 5       最小磁盘空间
"""

import sys, os, argparse, json, subprocess, time, asyncio, shutil, glob
from pathlib import Path

from agentos.base import AgentOSPlugin

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

# ═══════════════════════════════════════════════
# 执行约束常量（与 99_system 协定一致）
# ═══════════════════════════════════════════════

MAX_CONCURRENT = 3          # 每台机器最多3个浏览器
LAUNCH_STAGGER = 15         # 每个浏览器启动间隔秒数
AUTO_SHUTDOWN_MIN = 30      # 30分钟超时自动关闭
MIN_DISK_GB = 5             # 最小磁盘空间要求
GRACE_PERIOD_LOCAL = 5      # 本机进程启动宽限期(秒)
GRACE_PERIOD_REMOTE = 30    # 远程进程启动宽限期(秒)
MAX_TIMEOUT = 600           # 命令最大超时(秒)

# 需要浏览器的操作
BROWSER_COMMANDS = {'run', 'collect', 'login', 'smart-login', 'nurture', 'publish'}

# 窗口槽位（与 browser_orchestrator.py SLOTS 一致）
SLOTS = [
    {"id": 1, "position": (0, 0),   "size": (702, 783)},
    {"id": 2, "position": (100, 0), "size": (702, 783)},
    {"id": 3, "position": (200, 0), "size": (702, 783)},
]


class MatrixPlugin(AgentOSPlugin):
    name = "matrix"
    description = "社交矩阵 — 抖音/小红书账号运营、养号、采集、发布"

    def register(self, subparsers):
        """注册 matrix 子命令 — 全部通过 nargs='*' 捕获，dispatch 手动路由"""
        parser = subparsers.add_parser("matrix", help=self.description)
        parser.add_argument("args", nargs="*", help="子命令及参数")
        return parser

    def dispatch(self, args):
        # 不从 args.args 读取，直接从 sys.argv 获取原始参数
        # sys.argv = ['agentos', 'matrix', 'publish', 'douyin', '--account', 'x', ...]
        raw = sys.argv[:]
        # 找到 'matrix' 之后的所有参数
        try:
            idx = raw.index('matrix')
            raw = raw[idx + 1:]
        except ValueError:
            raw = getattr(args, 'args', [])

        if not raw:
            print("请指定子命令: account / blueprint / corpus / status\n"
                  "或 mc 命令: run / collect / login / publish ...")
            return 1

        cmd = raw[0]
        rest = raw[1:]

        if cmd == 'account':    return self.cmd_account_list(rest)
        elif cmd == 'blueprint': return self.cmd_blueprint_list(rest)
        elif cmd == 'corpus':   return self.cmd_corpus_list(rest)
        elif cmd == 'status':   return self.cmd_status_all(rest)
        elif cmd == 'collect':  return self.cmd_collect(rest)
        elif cmd in ('login', 'smart-login'): return self.cmd_login(rest)
        elif cmd == 'logout':   return self.cmd_logout(rest)
        elif cmd == 'publish':  return self.cmd_publish(rest)
        else:
            return self._execute_with_guards(cmd)
    # ═══════════════════════════════════════════════
    # 原生命令（接收 rest 参数列表）
    # ═══════════════════════════════════════════════

    def cmd_account_list(self, rest):
        """agentos matrix account [list]"""
        show_json = '--json' in rest or '-j' in rest
        try:
            from matrix_mgmt import MatrixManager
            accounts = MatrixManager().list_accounts()
            if not accounts:
                print("📋 暂无账号"); return 0
            if show_json:
                print(json.dumps(accounts, ensure_ascii=False, indent=2))
                return 0
            print(f"\n📋 账号列表 ({len(accounts)}):")
            print(f"{'ID':20s} {'平台':15s} {'状态':10s} {'手机':15s} {'本机':8s}")
            print("-" * 70)
            for a in accounts:
                pid = a.get("id", "?")
                plat = a.get("platform", "?")
                plat_icon = "🎵" if plat == "douyin" else "📕"
                status_raw = a.get("_status", "")
                cookie = "🟢 已登录" if status_raw == "logged_in" else "🔴 离线"
                phone = a.get("phone", "")[:11]
                local = "本机" if a.get("is_local") else "远程"
                print(f"  {pid:20s} {plat_icon:<5s} {cookie:<10s} {phone:<15s} {local:<8s}")
            return 0
        except Exception as e:
            print(f"❌ 加载账号失败: {e}")
            return 1

    def cmd_blueprint_list(self, rest):
        try:
            from matrix_mgmt import MatrixManager
            bps = MatrixManager().list_blueprints()
        except Exception as e:
            print(f"❌ 加载蓝图失败: {e}"); return 1
        if not bps: print("📋 暂无蓝图"); return 0
        print(f"\n📋 蓝图 ({len(bps)}):")
        for bp in bps:
            name = bp.get("name", "?")
            steps = len(bp.get("steps", []))
            platform = bp.get("platform", "通用")
            desc = bp.get("description", "")[:50]
            print(f"  • {name:<25s} ({steps}步) {platform:<12s} {desc}")
        return 0

    def cmd_corpus_list(self, rest):
        try:
            from matrix_modules.nurture.comment_corpus import get_categories
            cats = get_categories()
        except Exception:
            cats = []
        if not cats: print("📋 语料分类: 暂无"); return 0
        print(f"\n📋 语料分类 ({len(cats)}):")
        for c in cats:
            name = c.get("name", "?") if isinstance(c, dict) else str(c)
            print(f"  • {name}")
        return 0

    def cmd_status_all(self, rest):
        try:
            r = subprocess.run(["curl", "-s", "--max-time", "5",
                "http://localhost:9988/api/machines"], capture_output=True, text=True, timeout=8)
            data = json.loads(r.stdout)
            machines = data.get("machines", []) if isinstance(data, dict) else data
        except Exception:
            machines = []
        print(f"\n📊 多机状态 ({len(machines)}):")
        for m in (machines if isinstance(machines, list) else []):
            name = m.get("hostname", m.get("name", "?"))
            online = m.get("status") == "online"
            browsers = m.get("browsers_running", 0)
            print(f"  {'✅' if online else '🔴'} {name} 浏览器:{browsers}/{MAX_CONCURRENT}")
            if m.get("_last_push_sec"):
                s = m["_last_push_sec"]
                print(f"      🕐 最后通信: {s}s前 ({'在线' if s < 300 else '超时'})")
        print(f"\n  约束: MAX_CONCURRENT={MAX_CONCURRENT} STAGGER={LAUNCH_STAGGER}s "
              f"TIMEOUT={MAX_TIMEOUT}s SHUTDOWN={AUTO_SHUTDOWN_MIN}min")
        return 0

    # ═══════════════════════════════════════════════
    # collect — 原生实现
    # ═══════════════════════════════════════════════

    def cmd_collect(self, rest):
        """agentos matrix collect [--phone PHONE] [--account ACCT] [--all] [--status]"""
        # 解析参数
        phone = ''
        account = ''
        show_status = False
        collect_all = False
        
        i = 0
        while i < len(rest):
            if rest[i] == '--phone' and i + 1 < len(rest):
                phone = rest[i + 1]; i += 2
            elif rest[i] == '--account' and i + 1 < len(rest):
                account = rest[i + 1]; i += 2
            elif rest[i] == '--all':
                collect_all = True; i += 1
            elif rest[i] == '--status':
                show_status = True; i += 1
            else:
                i += 1

        # --status: 查看进度（调用 mc 进度API）
        if show_status:
            return self._collect_status()

        # 构建执行命令
        runner = SCRIPTS_DIR / "collect_batch_runner.py"
        if not runner.exists():
            runner = SCRIPTS_DIR / "collect_homepage_info.py"
        
        cmd = [sys.executable, str(runner)]
        if phone:
            cmd += ["--single", phone]
        elif account:
            cmd += ["--single", account]
        # --all: 不加参数，默认执行全部

        return self._run_collect(cmd)

    def _collect_status(self) -> int:
        """查看采集进度"""
        try:
            from collect_batch_runner import PROGRESS_FILE
            import json
            if PROGRESS_FILE.exists():
                data = json.loads(PROGRESS_FILE.read_text())
                print(f"📊 采集进度: {data.get('completed',0)}/{data.get('total_identities','?')}")
                print(f"   成功: {data.get('success',0)}, 失败: {data.get('failed',0)}")
                print(f"   状态: {data.get('status','?')}")
                if data.get('finished_at'):
                    print(f"   完成时间: {data['finished_at']}")
            else:
                print("📊 无正在执行的采集任务")
        except Exception as e:
            print(f"❌ 读取进度失败: {e}")
        return 0

    def _run_collect(self, cmd: list) -> int:
        """执行采集（走完整保护流程）"""
        cmd_str = ' '.join(str(c) for c in cmd[:4]) + '...'
        print(f"🚀 启动采集: {cmd_str}")
        print(f"   runner: {cmd[1]}")

        # 保护：通过 _execute_with_guards 但收集结果
        needs_browser = True
        self._cleanup_stale()
        self._check_disk()
        if not self._check_concurrent():
            return 1
        
        running = self._count_browsers()
        stagger = running * LAUNCH_STAGGER
        if stagger > 0:
            print(f"   ⏳ 错峰: 等待 {stagger}s")
            time.sleep(min(stagger, 30))

        # 执行
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{SCRIPTS_DIR}:{env.get('PYTHONPATH', '')}"
        env['AGENT_SYNC'] = str(SCRIPTS_DIR.parent.parent)
        env['AGENT_LOCAL'] = str(Path.home() / "workbuddy-agent-os" / "agent-local")

        log_dir = Path(env['AGENT_LOCAL']) / "runtime" / "commands"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"collect_{int(time.time())}.log"

        with open(log_file, 'w') as f:
            p = subprocess.Popen(cmd, env=env, cwd=str(SCRIPTS_DIR),
                                stdout=f, stderr=subprocess.STDOUT)
        print(f"   PID {p.pid}")
        print(f"   日志: {log_file}")
        return 0

    # ═══════════════════════════════════════════════
    # login/logout — 带警告的 mc 委托
    # ═══════════════════════════════════════════════

    def cmd_login(self, rest):
        """agentos matrix login <account_id> [--phone X] — 委托 mc 执行"""
        account_id = rest[0] if rest else ''
        if not account_id:
            print("❌ 请指定账号ID: agentos matrix login <account_id>")
            return 1

        print(f"\n⚠️  即将启动浏览器登录: {account_id}")
        print(f"   此操作会打开真实浏览器窗口，约 30-60 秒")
        confirm = input("   确认执行? (y/N): ").strip().lower()
        if confirm != 'y':
            print("   已取消")
            return 0

        # 走 mc 委托（带完整执行保护）
        return self._delegate_to_mc('smart-login', needs_browser=True)

    def cmd_logout(self, rest):
        """agentos matrix logout <account_id> — 原生实现"""
        account_id = rest[0] if rest else ''
        if not account_id:
            print("❌ 请指定账号ID: agentos matrix logout <account_id>")
            return 1
        print(f"🔓 清除 {account_id} 的登录状态...")
        try:
            from matrix_mgmt import MatrixManager
            result = MatrixManager().unbind_account(account_id)
            msg = result.get('message', '操作完成')
            print(f"   ✅ {msg}" if result.get("ok") else f"   ⚠️ {msg}")
        except Exception as e:
            print(f"   ❌ 失败: {e}")
        return 0

    # ═══════════════════════════════════════════════
    # publish — 原生实现
    # ═══════════════════════════════════════════════

    def cmd_publish(self, rest):
        """agentos matrix publish <platform> --account X --file Y [--title T] [--desc D]"""
        platform = rest[0] if rest and not rest[0].startswith('--') else ''
        account = file_path = title = desc = ''
        i = 1 if platform else 0
        while i < len(rest):
            if rest[i] == '--account' and i + 1 < len(rest): account = rest[i+1]; i += 2
            elif rest[i] == '--file' and i + 1 < len(rest): file_path = rest[i+1]; i += 2
            elif rest[i] == '--title' and i + 1 < len(rest): title = rest[i+1]; i += 2
            elif rest[i] == '--desc' and i + 1 < len(rest): desc = rest[i+1]; i += 2
            else: i += 1
        if not platform or not account or not file_path:
            print("❌ 参数不足\n   用法: agentos matrix publish <douyin|xiaohongshu> --account X --file Y [--title T]")
            return 1
        print(f"📤 发布到 {platform}: {file_path}")
        cmd = [sys.executable, str(SCRIPTS_DIR / "publish_video.py"), platform,
               "--account", account, "--file", file_path]
        if title: cmd += ["--title", title]
        if desc:  cmd += ["--desc", desc]
        result = subprocess.run(cmd, cwd=str(SCRIPTS_DIR),
            env={**os.environ, 'PYTHONPATH': str(SCRIPTS_DIR)})
        return result.returncode

    # ═══════════════════════════════════════════════
    # 执行保护（前置检查 + 并发控制 + 优雅退出）
    # ═══════════════════════════════════════════════

    def _execute_with_guards(self, cmd_name: str) -> int:
        """带完整保护的执行入口"""
        needs_browser = cmd_name in BROWSER_COMMANDS

        if needs_browser:
            print(f"\n🔍 预检: {cmd_name}")
            # 1. 清理残留
            self._cleanup_stale()
            # 2. 磁盘检查
            self._check_disk()
            # 3. 并发检查
            if not self._check_concurrent():
                return 1
            # 4. 执行前最后检查
            running = self._count_browsers()
            stagger = running * LAUNCH_STAGGER
            if stagger > 0:
                print(f"   ⏳ 错峰: 等待 {stagger}s（已有 {running} 个浏览器）")
                time.sleep(min(stagger, 30))

        return self._delegate_to_mc(cmd_name, needs_browser)

    def _cleanup_stale(self):
        """复位：杀残留 + 清理临时文件（对标 preflight.py）"""
        killed = 0
        for pat in ["camoufox.*orphan", "playwright"]:
            try:
                r = subprocess.run(["pkill", "-f", pat], capture_output=True, timeout=5)
                if r.returncode == 0: killed += 1
            except: pass
        # 清理临时目录
        for pat in ["/tmp/camoufox_*", "/tmp/playwright_*"]:
            for fp in glob.glob(pat):
                try: shutil.rmtree(fp, ignore_errors=True)
                except: pass
        if killed:
            print(f"   🧹 已清理 {killed} 个残留进程")

    def _check_disk(self):
        """检查磁盘空间（对标 preflight.py check_disk_space）"""
        try:
            r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
            parts = r.stdout.strip().split("\n")[1].split()
            avail = parts[3] if len(parts) >= 4 else "0"
            avail_gb = 0
            if avail.endswith("G"): avail_gb = float(avail[:-1])
            elif avail.endswith("M"): avail_gb = float(avail[:-1]) / 1024
            elif avail.endswith("T"): avail_gb = float(avail[:-1]) * 1024
            if avail_gb < MIN_DISK_GB:
                print(f"   ⚠️ 磁盘空间不足: {avail} ({avail_gb:.1f}GB < {MIN_DISK_GB}GB)")
        except: pass

    def _count_browsers(self) -> int:
        """统计当前运行浏览器数量（对标 browser_orchestrator.check_running_browsers）"""
        try:
            r = subprocess.run(
                ["pgrep", "-f", "camoufox.*-no-remote|HeadlessShell|chrome.*--remote-debugging"],
                capture_output=True, text=True, timeout=5
            )
            return len([p for p in r.stdout.strip().split("\n") if p.strip()])
        except: return 0

    def _check_concurrent(self) -> bool:
        """并发检查（对标 browser_orchestrator.preflight）"""
        running = self._count_browsers()
        if running >= MAX_CONCURRENT:
            print(f"   ❌ 已达到最大并发数: {running}/{MAX_CONCURRENT}")
            print(f"      等待其他任务完成或手动清理: pkill -f camoufox")
            return False
        print(f"   ✅ 浏览器: {running}/{MAX_CONCURRENT}")
        return True

    # ═══════════════════════════════════════════════
    # mc 委托执行
    # ═══════════════════════════════════════════════

    def _get_rest_args(self, cmd_name: str) -> list:
        """从 sys.argv 提取 cmd_name 后面的参数"""
        try:
            idx = sys.argv.index(cmd_name)
            return sys.argv[idx + 1:]
        except ValueError:
            return []

    def _delegate_to_mc(self, cmd_name: str, needs_browser: bool = False) -> int:
        """委托 mc 执行"""
        python = sys.executable
        # 重建 mc 命令: 从当前 args 动态构建
        # raw args = ['agentos', 'matrix', 'run', '--accounts', 'X']
        # → mc args = ['python', '-m', 'mc', 'run', '--accounts', 'X']
        mc_argv = [python, '-m', 'mc', cmd_name] + self._get_rest_args(cmd_name)

        env = os.environ.copy()
        env['PYTHONPATH'] = f"{SCRIPTS_DIR}:{env.get('PYTHONPATH', '')}"
        env['AGENT_SYNC'] = str(SCRIPTS_DIR.parent.parent)
        env['AGENT_LOCAL'] = str(Path.home() / "workbuddy-agent-os" / "agent-local")

        # 浏览器操作：Popen 后台运行 + 跟踪 PID
        if needs_browser:
            log_dir = Path(env['AGENT_LOCAL']) / "runtime" / "commands"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"{cmd_name}_{int(time.time())}.log"
            
            with open(log_file, 'w') as f:
                p = subprocess.Popen(
                    mc_argv, env=env, cwd=str(SCRIPTS_DIR),
                    stdout=f, stderr=subprocess.STDOUT
                )
            
            print(f"   🚀 PID {p.pid} | 日志: {log_file}")
            print(f"   📋 并发: {self._count_browsers()}/{MAX_CONCURRENT}")
            print(f"   ⏱️  超时: {AUTO_SHUTDOWN_MIN}min 自动关闭")
            print(f"   ℹ️   检查: ps aux | grep {p.pid}")
            return 0

        # 非浏览器操作：同步等待
        result = subprocess.run(mc_argv, env=env, cwd=str(SCRIPTS_DIR))
        return result.returncode

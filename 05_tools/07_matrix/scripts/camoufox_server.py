#!/usr/bin/env python3
"""
Camoufox Server 启动器 — 绕过 CLI proxy bug

直接调用 camoufox.server.launch_server() 传递完整参数，
避免 CLI 路径中 __main__.py 不传参数导致的 proxy: null 错误。
"""
import sys
import os
import json
import base64
import subprocess
import time
import threading
import signal
from pathlib import Path


def launch_camoufox_server(
    account_id: str,
    port: int,
    profile_dir: str,
    window: tuple = (702, 783),
    locale: list = None,
    proxy: dict = None,
    headless: bool = False,
):
    """
    启动 Camoufox Server（绕过 CLI bug）
    
    方案：直接调用 launch_options() 生成配置，清洗 proxy: None，
    然后手动启动 Node.js 进程（复制 server.py 的逻辑）。
    """
    if locale is None:
        locale = ['zh-CN']
    
    print(f"🚀 启动 Camoufox Server（账号: {account_id}，端口: {port}）")
    print(f"   窗口: {window[0]}x{window[1]}")
    print(f"   语言: {locale}")
    if proxy:
        print(f"   代理: {proxy}")
    else:
        print(f"   代理: 无")
    
    # 构建 launch_options 参数
    launch_kwargs = {
        'headless': headless,
        'window': window,
        'locale': locale,
        'args': [f'--remote-debugging-port={port}'],
        'persistent_context': True,
        'user_data_dir': str(profile_dir),
    }
    if proxy:
        launch_kwargs['proxy'] = proxy
    
    # 获取 launch_options 配置
    try:
        from camoufox.utils import launch_options
        config = launch_options(**launch_kwargs)
    except Exception as e:
        print(f"❌ launch_options 失败: {e}")
        return None
    
    # 🔑 关键修复：移除 proxy: None，避免 Node.js 端收到 null
    if config.get('proxy') is None:
        del config['proxy']
        print(f"   已修复：移除 proxy: None（避免 Node.js null 错误）")
    
    # 移除其他 None 值
    config = {k: v for k, v in config.items() if v is not None}
    
    print(f"   配置键: {list(config.keys())}")
    
    # 转换为 camelCase（与 server.py 一致）
    def to_camel_case(snake_str: str) -> str:
        if len(snake_str) < 2:
            return snake_str
        cc = ''.join(x.capitalize() for x in snake_str.lower().split('_'))
        return cc[0].lower() + cc[1:]
    
    camel_config = {to_camel_case(k): v for k, v in config.items()}
    
    # 获取 Node.js 路径和 launchServer.js 路径
    try:
        from camoufox.server import get_nodejs
        from camoufox.pkgman import LOCAL_DATA
        nodejs = get_nodejs()
        launch_script = LOCAL_DATA / "launchServer.js"
    except Exception as e:
        print(f"❌ 获取 Node.js 路径失败: {e}")
        return None
    
    # 编码配置
    config_json = json.dumps(camel_config)
    config_b64 = base64.b64encode(config_json.encode()).decode()
    
    # 启动 Node.js 进程
    try:
        process = subprocess.Popen(
            [nodejs, str(launch_script)],
            cwd=Path(nodejs).parent / "package",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        
        # 发送配置到 stdin
        process.stdin.write(config_b64)
        process.stdin.close()
        
        print(f"   等待 Server 启动...")
        
    except Exception as e:
        print(f"❌ 启动 Node.js 进程失败: {e}")
        return None
    
    return process


if __name__ == '__main__':
    import argparse
    
    # 加载账号配置
    from local_paths import config_path, data_path, profiles_path
    CONFIG_PATH = config_path("accounts.yaml")
    
    try:
        import yaml
        with open(CONFIG_PATH, encoding='utf-8') as f:
            data = yaml.safe_load(f)
        accounts = data.get('accounts', [])
        camoufox_cfg = data.get('camoufox', {})
    except ImportError:
        print("❌ 需要 PyYAML: pip install pyyaml")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description='Camoufox Server 启动器')
    parser.add_argument('--launch', type=str, help='启动指定账号')
    parser.add_argument('--stop', type=str, help='停止指定账号')
    parser.add_argument('--status', type=str, help='检查账号状态')
    parser.add_argument('--list', action='store_true', help='列出所有 Camoufox 账号')
    args = parser.parse_args()
    
    # PID 管理
    pid_dir = data_path("camoufox_pids")
    
    def get_account(account_id):
        for acc in accounts:
            if acc.get('id') == account_id:
                return acc
        return None
    
    def save_pid(account_id, pid):
        pid_file = pid_dir / f"{account_id}.pid"
        with open(pid_file, 'w') as f:
            f.write(str(pid))
    
    def read_pid(account_id):
        pid_file = pid_dir / f"{account_id}.pid"
        if not pid_file.exists():
            return None
        try:
            with open(pid_file, 'r') as f:
                return int(f.read().strip())
        except (ValueError, OSError):
            return None
    
    def is_process_alive(pid):
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    
    if args.list:
        camo_accounts = [a for a in accounts if a.get('browser_type') == 'camoufox']
        print(f"\n📋 Camoufox 账号（共 {len(camo_accounts)} 个）")
        for acc in camo_accounts:
            pid = read_pid(acc['id'])
            status = "🟢 运行中" if pid and is_process_alive(pid) else "⚪ 已停止"
            print(f"  {acc['id']:20s} | 端口 {acc.get('port', '?'):5} | {status}")
        sys.exit(0)
    
    if args.stop:
        account_id = args.stop
        pid = read_pid(account_id)
        if not pid:
            print(f"❌ 未找到 PID（账号: {account_id}）")
            sys.exit(1)
        if not is_process_alive(pid):
            print(f"⚪ 进程已终止（PID {pid}）")
            (pid_dir / f"{account_id}.pid").unlink(missing_ok=True)
            sys.exit(0)
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"🛑 已发送 SIGTERM 到 PID {pid}")
            for _ in range(10):
                if not is_process_alive(pid):
                    break
                time.sleep(0.5)
            (pid_dir / f"{account_id}.pid").unlink(missing_ok=True)
            print(f"✅ 已停止（账号: {account_id}）")
        except OSError as e:
            print(f"❌ 停止失败: {e}")
        sys.exit(0)
    
    if args.status:
        account_id = args.status
        pid = read_pid(account_id)
        if pid and is_process_alive(pid):
            print(f"🟢 运行中（PID {pid}）")
        else:
            print(f"⚪ 未运行")
            if pid:
                (pid_dir / f"{account_id}.pid").unlink(missing_ok=True)
        sys.exit(0)
    
    if args.launch:
        account = get_account(args.launch)
        if not account:
            print(f"❌ 账号 {args.launch} 不存在")
            sys.exit(1)
        
        # 检查是否已在运行
        pid = read_pid(args.launch)
        if pid and is_process_alive(pid):
            print(f"⚠️  已在运行（PID {pid}），如需重启请先 --stop")
            sys.exit(0)
        
        # 合并配置
        screen = account.get('screen', camoufox_cfg.get('screen', {'width': 702, 'height': 783}))
        geo = account.get('geo', camoufox_cfg.get('geo', {'timezone': 'Asia/Shanghai', 'locale': 'zh-CN'}))
        proxy_val = account.get('proxy')
        profile_dir = profiles_path(account.get('profile_dir', account['id']))
        
        # 启动 Server
        process = launch_camoufox_server(
            account_id=account['id'],
            port=account['port'],
            profile_dir=str(profile_dir),
            window=(screen['width'], screen['height']),
            locale=[geo.get('locale', 'zh-CN')],
            proxy={'server': proxy_val} if isinstance(proxy_val, str) else (proxy_val if proxy_val else None),
        )
        
        if not process:
            print("❌ 启动失败")
            sys.exit(1)
        
        # 等待启动
        time.sleep(5)
        
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"❌ Server 启动后立即退出")
            if stdout:
                print(f"   stdout: {stdout[:500]}")
            if stderr:
                print(f"   stderr: {stderr[:500]}")
            sys.exit(1)
        
        # 保存 PID
        save_pid(args.launch, process.pid)
        
        print(f"\n✅ Camoufox Server 启动成功！")
        print(f"   PID:  {process.pid}")
        print(f"   端口: {account['port']}")
        print(f"   停止: python {__file__} --stop {args.launch}")
        print(f"   状态: python {__file__} --status {args.launch}")
        print(f"   连接: python camoufox_manager.py --connect {account['port']}")
        print(f"\n   ⚠️  请勿关闭此终端，Server 将在此运行\n")
        
        # 后台读取输出
        def read_output(pipe, label):
            try:
                for line in iter(pipe.readline, ''):
                    if line.strip():
                        print(f"   [{label}] {line.rstrip()}")
            except:
                pass
        
        threading.Thread(target=read_output, args=(process.stdout, 'out'), daemon=True).start()
        threading.Thread(target=read_output, args=(process.stderr, 'err'), daemon=True).start()
        
        # 主线程等待
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n🛑 用户中断，停止 Server...")
            process.terminate()
            process.wait()
            (pid_dir / f"{args.launch}.pid").unlink(missing_ok=True)
            print("✅ 已停止")
        
        sys.exit(0)
    
    parser.print_help()

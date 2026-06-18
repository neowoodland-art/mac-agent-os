#!/usr/bin/env python3
"""
douyin_login.py — 抖音账号登录接入（手机号 + SMS 验证码）

流程:
  1. 准备浏览器身份目录（自动创建）
  2. 启动 Camoufox，加载身份目录
  3. 导航到抖音首页
  4. 检测登录面板 → 点击"一键登录"
  5. ApiSMSHandler 自动轮询获取验证码
  6. 填入验证码 → 确认 → 验证登录态
  7. Cookie 自动持久化（Camoufox 持久化目录）
  8. 刷新 Dashboard 账号状态

用法:
  python douyin_login.py douyin_137                    # 用默认手机号
  python douyin_login.py douyin_137 --phone 13754826808 # 指定手机号

版本: 1.0.0 | 更新: 2026-06-01
"""
import argparse, asyncio, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from cdp_connector import CDPConnector
from browser_utils import GracefulBrowser
from matrix_modules.account.sms_login import sms_login, has_login_panel
from matrix_modules.account.sms import ApiSMSHandler

HOME = Path.home()

IDENTITIES_ROOT = AGENT_LOCAL / "tools" / "matrix" / "identities"
LOG_FILE = AGENT_LOCAL / "runtime" / "login_log.jsonl"


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def write_op_log(account_id: str, platform: str, status: str, detail: str = ""):
    entry = {"op": f"{platform}_login", "account": account_id, "status": status, "detail": detail, "timestamp": datetime.now(timezone.utc).isoformat()}
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def douyin_login(account_id: str, phone: str = "", timeout_minutes: int = 30):
    # ── 自动更新 SMS API 配置 ──
    if phone:
        sms_yaml_path = SCRIPTS_DIR / "config" / "sms.yaml"
        if sms_yaml_path.exists():
            try:
                import yaml
                cfg = yaml.safe_load(sms_yaml_path.read_text()) or {}
                if "sms" not in cfg: cfg["sms"] = {}
                cfg["sms"]["phone"] = phone
                sms_yaml_path.write_text(yaml.dump(cfg, default_flow_style=False, allow_unicode=True))
                log(f"📝 SMS API 已切换到手机号: {phone}")
            except Exception as e:
                log(f"⚠️ 更新 sms.yaml 失败: {e}")
        else:
            log(f"⚠️ sms.yaml 不存在，跳过配置更新")

    identity_dir = str(IDENTITIES_ROOT / account_id)
    Path(identity_dir).mkdir(parents=True, exist_ok=True)
    log(f"📁 身份目录: {identity_dir}")

    log("🚀 启动浏览器...")
    conn = CDPConnector(identity_dir=identity_dir, headless=False,
                        window=(702, 783), window_position=(0, 0))
    
    # 用 GracefulBrowser 包装（优雅退出 + 前置检查）
    gb = GracefulBrowser(conn, account_id=account_id,
                         timeout_minutes=timeout_minutes)
    await gb.setup(check_running=True)
    
    try:
        await conn.connect()
    except Exception as e:
        write_op_log(account_id, "douyin", "failed", f"浏览器启动失败: {e}")
        log(f"❌ 浏览器连接失败: {e}")
        return False
    await conn.page.set_viewport_size({"width": 702, "height": 783})
    log("✅ 浏览器就绪")

    log("🌐 打开抖音首页...")
    await conn.page.goto("https://www.douyin.com/", timeout=30000, wait_until="domcontentloaded")
    await asyncio.sleep(6)

    log("📱 检测登录面板...")
    # 多轮检测: 自动检测失败后等用户手动操作
    panel_detected = False
    for attempt in range(3):
        if await has_login_panel(conn.page):
            panel_detected = True
            break
        # 也可能已经登录了
        if await conn.page.evaluate('() => !!document.querySelector("[data-e2e=user-avatar]")'):
            log("✅ 已登录，跳过")
            write_op_log(account_id, "douyin", "already_logged_in")
            return True
        if attempt == 0:
            log("⏳ 未检测到登录面板，请在浏览器上手动点击「登录」按钮...")
            log("   (等待 15 秒)")
        await asyncio.sleep(5)

    if not panel_detected:
        log("⏳ 尝试导航到登录页面...")
        await conn.page.goto("https://www.douyin.com/", timeout=20000)
        await asyncio.sleep(4)
        for attempt in range(3):
            if await has_login_panel(conn.page):
                panel_detected = True
                break
            await asyncio.sleep(3)

    if not panel_detected:
        log("❌ 未检测到登录面板，请手动在浏览器上操作")
        log("   点击「登录」或「一键登录」后，脚本会自动处理验证码")
        log("   (等待 30 秒)...")
        await asyncio.sleep(30)
        # 最后检查一次登录态
        if await conn.page.evaluate('() => !!document.querySelector("[data-e2e=user-avatar]")'):
            log("✅ 已手动登录成功")
            write_op_log(account_id, "douyin", "success")
            return True

    ok = await sms_login(conn.page, account_name=account_id, log_func=log)
    if ok:
        log("🎉 抖音登录成功！")
        write_op_log(account_id, "douyin", "success")
        try:
            from c2.profile_scraper import ProfileScraper
            scraper = ProfileScraper()
            scraper.refresh([account_id])
            log("📊 资料已采集")
        except Exception as e:
            log(f"⚠️ 资料采集失败: {e}")
    else:
        log("❌ 登录失败")
        write_op_log(account_id, "douyin", "failed", "登录流程未完成")

    log("\n💡 浏览器保持打开，超时自动关闭")
    gb.start_auto_shutdown_timer()
    
    # 等待直到超时自动关闭或被信号中断
    while not gb._shutdown_flag:
        await asyncio.sleep(10)

    return logged_in


def main():
    parser = argparse.ArgumentParser(description="抖音账号登录接入")
    parser.add_argument("account_id", help="账号 ID（如 douyin_137）")
    parser.add_argument("--phone", "-p", default="", help="手机号（选填，默认从 accounts.yaml 读取）")
    parser.add_argument("--timeout", "-t", type=int, default=30,
                        help="超时自动关闭分钟数（默认 30）")
    args = parser.parse_args()
    print(f"\n{'='*55}\n 📱 抖音登录接入: {args.account_id}\n{'='*55}\n")
    asyncio.run(douyin_login(args.account_id, args.phone, args.timeout))

if __name__ == "__main__":
    main()

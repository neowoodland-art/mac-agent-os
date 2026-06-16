#!/usr/bin/env python3
"""
xiaohongshu_login.py — 小红书账号登录接入（手机号 + SMS 验证码）

流程:
  1. 准备浏览器身份目录
  2. 优雅退出检查 + 前置浏览器检测 (browser_utils)
  3. 启动 Camoufox，加载身份目录
  4. 导航到小红书首页
  5. 检测登录面板 → 触发短信验证码登录
  6. ApiSMSHandler 自动轮询获取验证码
  7. 填入验证码 → 确认 → 验证登录态
  8. Cookie 自动持久化（Camoufox 持久化目录）
  9. 优雅退出/超时自动关闭

用法:
  python xiaohongshu_login.py xhs_01                    # 用默认手机号
  python xiaohongshu_login.py xhs_01 --phone 13754826808 # 指定手机号
  python xiaohongshu_login.py xhs_01 --timeout 60        # 60分钟超时自动关闭

版本: 1.0.0 | 更新: 2026-06-16
"""
import argparse, asyncio, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from cdp_connector import CDPConnector
from browser_utils import GracefulBrowser

HOME = Path.home()
AGENT_LOCAL = HOME / "workbuddy-agent-os" / "agent-local"
IDENTITIES_ROOT = AGENT_LOCAL / "tools" / "matrix" / "identities"
LOG_FILE = AGENT_LOCAL / "runtime" / "login_log.jsonl"


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def write_op_log(account_id: str, platform: str, status: str, detail: str = ""):
    entry = {"op": f"{platform}_login", "account": account_id, "status": status,
             "detail": detail, "timestamp": datetime.now(timezone.utc).isoformat()}
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def xiaohongshu_login(account_id: str, phone: str = "", timeout_minutes: int = 30):
    """小红书全自动登录"""
    # ── 确认账号平台是小程序 ──
    # 从矩阵管理获取账号信息
    platform = "xiaohongshu"
    try:
        from matrix_mgmt import MatrixManager
        mgr = MatrixManager()
        for a in mgr.list_accounts():
            if a["id"] == account_id:
                if not phone:
                    phone = a.get("phone", "")
                break
    except Exception:
        pass

    identity_dir = str(IDENTITIES_ROOT / account_id)
    Path(identity_dir).mkdir(parents=True, exist_ok=True)
    log(f"📁 身份目录: {identity_dir}")

    # ── 启动浏览器（带优雅退出和前置检查）──
    log("🚀 启动浏览器...")
    conn = CDPConnector(identity_dir=identity_dir, headless=False,
                        window=(702, 783), window_position=(652, 0))
    
    # 用 GracefulBrowser 包装
    gb = GracefulBrowser(conn, account_id=account_id,
                         timeout_minutes=timeout_minutes)
    await gb.setup(check_running=True)
    
    try:
        await conn.connect()
    except Exception as e:
        write_op_log(account_id, platform, "failed", f"浏览器启动失败: {e}")
        log(f"❌ 浏览器连接失败: {e}")
        return False
    
    await conn.page.set_viewport_size({"width": 702, "height": 783})
    log("✅ 浏览器就绪")

    # ── 导航到小红书首页 ──
    log("🌐 打开小红书首页...")
    await conn.page.goto("https://www.xiaohongshu.com/explore",
                         timeout=30000, wait_until="domcontentloaded")
    await asyncio.sleep(6)

    # ── 检测登录状态 ──
    log("🔍 检测登录状态...")
    try:
        # 小红书登录态 DOM 检测
        logged_in = await conn.page.evaluate(
            '() => !!document.querySelector(".user-avatar, .reds-count, [class*=avatar]")'
        )
        if logged_in:
            log("✅ 已登录，跳过登录流程")
            write_op_log(account_id, platform, "already_logged_in")
            log("\n💡 浏览器保持打开，超时自动关闭")
            gb.start_auto_shutdown_timer()
            return True
    except Exception:
        pass

    # ── 检测登录面板 ──
    log("📱 检测登录面板...")
    panel_detected = False
    
    # 小红书登录面板可能通过点击"登录"按钮触发
    # 尝试多种方式定位登录入口
    for attempt in range(5):
        # 方式1: 检测登录弹窗/面板
        panel_found = await conn.page.evaluate("""() => {
            var selectors = [
                '.login-container', '.login-dialog', '.login-panel',
                '[class*=login]', '#login-panel', '.auth-container',
                'div[class*=login]', '.phone-login', '.sms-login',
                'input[placeholder*=\"手机\"]', 'input[type=\"tel\"]',
                // 小红书特有的登录弹窗
                '.reds-login', '.login-modal', '.login-wrapper'
            ];
            for (var s of selectors) {
                var el = document.querySelector(s);
                if (el && el.offsetParent) return s;
            }
            return null;
        }""")
        
        if panel_found:
            panel_detected = True
            log(f"  ✅ 检测到登录面板: {panel_found}")
            break
        
        # 方式2: 尝试点击页面上的"登录"按钮
        if attempt == 0:
            log("  🔍 尝试点击登录按钮...")
        login_clicked = await conn.page.evaluate("""() => {
            var all = document.querySelectorAll('span, div, a, button');
            for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent.trim();
                if ((t === '登录' || t === '登录/注册') && all[i].offsetParent) {
                    all[i].click();
                    return true;
                }
            }
            return false;
        }""")
        
        if login_clicked:
            log("  ✅ 已点击登录按钮，等待面板出现...")
            await asyncio.sleep(3)
        else:
            log("  ⏳ 等待登录面板...")
            await asyncio.sleep(3)
    
    if not panel_detected:
        log("❌ 未检测到登录面板")
        log("   ⏳ 等待 60 秒，请手动在浏览器上点击「登录」...")
        log("   (脚本检测到登录面板后会自动处理验证码)")
        
        for _ in range(12):
            await asyncio.sleep(5)
            if await conn.page.evaluate("""() => {
                var s = document.querySelector('input[placeholder*=\"手机\"], input[type=\"tel\"]');
                return s && s.offsetParent ? true : false;
            }"""):
                panel_detected = True
                log("  ✅ 检测到登录面板（手动触发）")
                break
        
        if not panel_detected:
            # 最后检查: 是否已经登录了
            final_check = await conn.page.evaluate(
                '() => !!document.querySelector(".user-avatar, .reds-count")'
            )
            if final_check:
                log("✅ 已登录成功")
                write_op_log(account_id, platform, "success")
                return True
            log("❌ 登录面板未出现，请手动完成登录")
            return False

    # ── 执行 SMS 验证码登录 ──
    log("📱 执行短信验证码登录...")
    
    # 检测是否有手机号输入框，填入手机号
    has_phone_input = await conn.page.evaluate(
        '() => !!document.querySelector("input[placeholder*=\"手机\"], input[type=\"tel\"]")'
    )
    if has_phone_input and phone:
        log(f"  📞 填入手机号: {phone}")
        await conn.page.evaluate(f"""() => {{
            var inp = document.querySelector('input[placeholder*=\"手机\"], input[type=\"tel\"]');
            if (inp) {{ 
                inp.value = '{phone}';
                inp.dispatchEvent(new Event('input', {{bubbles: true}}));
            }}
        }}""")
        await asyncio.sleep(1)
        
        # 点击"获取验证码"按钮
        log("  📬 点击获取验证码...")
        await conn.page.evaluate("""() => {
            var all = document.querySelectorAll('button, span, div, a');
            for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent.trim();
                if ((t.includes('验证码') || t.includes('发送') || t.includes('获取')) && all[i].offsetParent) {
                    all[i].click();
                    return true;
                }
            }
            return false;
        }""")
        await asyncio.sleep(2)
    
    # 等待验证码输入框
    has_code_input = await conn.page.evaluate(
        '() => !!document.querySelector("input[placeholder*=\"验证码\"], input[placeholder*=\"code\"]")'
    )
    
    if not has_code_input:
        log("  ⏳ 等待验证码输入框...")
        for _ in range(10):
            await asyncio.sleep(2)
            has_code_input = await conn.page.evaluate(
                '() => !!document.querySelector("input[placeholder*=\"验证码\"], input[placeholder*=\"code\"]")'
            )
            if has_code_input:
                break
    
    if not has_code_input:
        log("❌ 未检测到验证码输入框")
        return False
    
    log("  ✅ 验证码输入框已出现")
    
    # 轮询获取验证码
    log("  📡 等待验证码...")
    from matrix_modules.account.sms import ApiSMSHandler
    handler = ApiSMSHandler(phone=phone) if phone and phone.strip() else ApiSMSHandler()
    
    code = ''
    for attempt in range(3):
        code = await handler.wait(f"小红书登录 {account_id}", timeout=60)
        if code and len(code) in (4, 5, 6):
            log(f"  ✅ 获取到验证码: {code}")
            break
        log(f"  ⏰ 第{attempt+1}次超时，尝试重新发送...")
        # 重新发送
        await conn.page.evaluate("""() => {
            var all = document.querySelectorAll('button, span, div, a');
            for (var i = 0; i < all.length; i++) {
                var t = all[i].textContent.trim();
                if ((t.includes('重新') || t.includes('重发')) && all[i].offsetParent) {
                    all[i].click(); return true;
                }
            }
            return false;
        }""")
        await asyncio.sleep(2)
    
    if not code or len(code) not in (4, 5, 6):
        log("❌ 获取验证码失败")
        return False
    
    # 填入验证码
    log(f"  📝 填入验证码 {code}")
    await conn.page.evaluate(f"""() => {{
        var inp = document.querySelector('input[placeholder*=\"验证码\"], input[placeholder*=\"code\"]');
        if (inp) {{
            inp.value = '{code}';
            inp.dispatchEvent(new Event('input', {{bubbles: true}}));
        }}
    }}""")
    await asyncio.sleep(0.5)
    
    # 点确认/登录按钮
    log("  🔘 点击确认...")
    confirm_ok = await conn.page.evaluate("""() => {
        var texts = ['确认', '提交', '验证', '登录', '确定', '下一步', '立即登录'];
        var all = document.querySelectorAll('button, span, div, a');
        for (var i = 0; i < all.length; i++) {
            if (!all[i].offsetParent) continue;
            for (var t = 0; t < texts.length; t++) {
                if (all[i].textContent.includes(texts[t])) {
                    all[i].click(); return true;
                }
            }
        }
        return false;
    }""")
    await asyncio.sleep(3)
    
    # ── 验证登录 ──
    logged_in = await conn.page.evaluate(
        '() => !!document.querySelector(".user-avatar, .reds-count, [class*=avatar]")'
    )
    
    if logged_in:
        log("🎉 小红书登录成功！")
        write_op_log(account_id, platform, "success")
    else:
        log("⚠️ 登录可能未完成，检查页面状态")
        write_op_log(account_id, platform, "failed", "登录后验证未通过")
    
    # ── 保持浏览器打开，启动超时自动关闭 ──
    log("\n💡 浏览器保持打开，超时自动关闭")
    gb.start_auto_shutdown_timer()
    
    # 等待直到超时自动关闭或被信号中断
    while not gb._shutdown_flag:
        await asyncio.sleep(10)
    
    return logged_in


def main():
    parser = argparse.ArgumentParser(description="小红书账号登录接入")
    parser.add_argument("account_id", help="账号 ID（如 xhs_01）")
    parser.add_argument("--phone", "-p", default="", help="手机号（选填）")
    parser.add_argument("--timeout", "-t", type=int, default=30,
                        help="超时自动关闭分钟数（默认 30）")
    args = parser.parse_args()
    print(f"\n{'='*55}\n 📕 小红书登录接入: {args.account_id}\n{'='*55}\n")
    asyncio.run(xiaohongshu_login(args.account_id, args.phone, args.timeout))


if __name__ == "__main__":
    main()

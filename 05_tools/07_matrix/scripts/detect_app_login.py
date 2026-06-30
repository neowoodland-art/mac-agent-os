#!/usr/bin/env python3
"""
探测脚本：检测抖音SMS登录被"必须使用App登录"拦截的场景

用法（在 5kecheng 上远程执行）:
  python3 detect_app_login.py --phone=15370108283 --max-attempts=4 --interval=600

输出:
  /tmp/detect_login_result.json — 包含捕捉到的红色提示文字、截图路径等
"""

import argparse
import asyncio
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# ── 确保能找到项目的 SMS API ──
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent.parent  # → agent-sync/
sys.path.insert(0, str(_SCRIPT_DIR / "matrix_modules"))
sys.path.insert(0, str(_SCRIPT_DIR))


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


async def detect_once(phone: str, attempt: int, output_dir: str) -> dict:
    """执行一次完整的 SMS 登录探测，返回捕捉到的页面信息"""
    result = {
        "attempt": attempt,
        "timestamp": datetime.now().isoformat(),
        "phone": phone,
        "sms_sent": False,
        "sms_received": False,
        "code_filled": False,
        "login_clicked": False,
        "red_texts": [],
        "error_texts": [],
        "near_login_texts": [],
        "page_url_after_login": "",
        "page_title_after_login": "",
        "screenshot_path": "",
        "full_text_snippet": "",
        "found_app_login": False,
        "error": None,
    }

    from camoufox.async_api import AsyncCamoufox

    screenshot_path = os.path.join(output_dir, f"login_attempt_{attempt}.png")

    try:
        # 启动 Camoufox（用临时身份，不污染现有cookie）
        log(f"[尝试 {attempt}] 启动 Camoufox 浏览器...")
        fox = AsyncCamoufox(
            headless=False,
            locale="zh-CN",
            os="windows",
            humanize=1.5,
            viewport={"width": 1280, "height": 800},
        )
        browser = await fox.start()
        if browser.contexts:
            context = browser.contexts[0]
        else:
            context = await browser.new_context()
        if context.pages:
            page = context.pages[0]
        else:
            page = await context.new_page()

            # ── 1. 导航到登录页 ──
            log("导航到抖音登录页...")
            await page.goto(
                "https://www.douyin.com/passport/sso/login/",
                timeout=30000, wait_until="domcontentloaded"
            )
            await asyncio.sleep(4)

            # ── 2. 找手机号输入框 ──
            log("查找手机号输入框...")
            phone_input = None
            for sel in [
                'input[placeholder*="手机"]',
                'input[type="tel"]',
                'input[name="mobile"]',
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.count() > 0 and await el.is_visible():
                        phone_input = el
                        break
                except:
                    continue

            if not phone_input:
                # JS 兜底：遍历所有 input
                log("CSS 选择器没找到手机号输入框，用 JS 兜底...")
                try:
                    await page.evaluate(f"""() => {{
                        const inputs = document.querySelectorAll('input');
                        for (const inp of inputs) {{
                            if (inp.offsetParent !== null && inp.value === '') {{
                                inp.focus();
                                inp.value = '{phone}';
                                inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                                return true;
                            }}
                        }}
                        return false;
                    }}""")
                    await asyncio.sleep(1)
                    result["code_filled"] = True
                    log("JS 填手机号成功")
                except Exception as e:
                    result["error"] = f"无法填写手机号: {e}"
                    await browser.close()
                    return result
            else:
                await phone_input.click()
                await asyncio.sleep(0.5)
                await phone_input.fill(phone)
                await asyncio.sleep(1)
                result["code_filled"] = True
                log(f"已填入手机号: {phone}")

            # ── 3. 点击"获取验证码" ──
            log("点击获取验证码...")
            get_code_clicked = False
            for text in ["获取验证码", "获取"]:
                try:
                    btn = page.locator(f'button:has-text("{text}"), span:has-text("{text}")').first
                    if await btn.count() > 0 and await btn.is_visible():
                        await btn.click()
                        get_code_clicked = True
                        log(f"点击 '{text}' 成功")
                        break
                except:
                    continue

            if not get_code_clicked:
                # JS 兜底
                try:
                    await page.evaluate("""() => {
                        const all = document.querySelectorAll('button, span, div');
                        for (const el of all) {
                            if (el.offsetParent === null) continue;
                            const t = el.textContent.trim();
                            if (t.includes('获取验证码') || t.includes('获取')) {
                                el.click(); return true;
                            }
                        }
                        return false;
                    }""")
                    get_code_clicked = True
                    log("JS 点击获取验证码成功")
                except:
                    pass

            if not get_code_clicked:
                result["error"] = "无法点击获取验证码"
                await browser.close()
                return result

            result["sms_sent"] = True
            sms_start_time = time.time()
            log(f"等待短信验证码 (60s超时)...")

            # ── 4. 获取 SMS 验证码 ──
            code = ""
            try:
                from matrix_modules.account.sms.api import ApiSMSHandler
                handler = ApiSMSHandler(phone=phone)
                code = await handler.wait(platform="抖音登录", timeout=60, after_time=sms_start_time - 5)
            except Exception as e:
                log(f"SMS API 调用失败: {e}")
                # 兜底：手动输入
                log("等待手动输入验证码 (60秒)...")
                for _ in range(60):
                    try:
                        code_input = page.locator('input[placeholder*="验证码"]').first
                        if await code_input.count() > 0:
                            val = await code_input.input_value()
                            if len(val) >= 4:
                                code = val
                                log(f"检测到已填入验证码: {code}")
                                break
                    except:
                        pass
                    await asyncio.sleep(1)

            if not code:
                result["error"] = "未获取到短信验证码"
                await browser.close()
                return result

            result["sms_received"] = True
            log(f"✅ 获取到验证码: {code}")

            # ── 5. 填入验证码 ──
            code_input = None
            for sel in [
                'input[placeholder*="验证码"]',
                'input[type="tel"]',
                '.uc-ui-verify_sms-verify_input input',
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.count() > 0:
                        code_input = el
                        break
                except:
                    continue

            if code_input:
                await code_input.click()
                await asyncio.sleep(0.3)
                await code_input.fill(code)
                log("验证码已填入")
            else:
                # JS 兜底
                try:
                    await page.evaluate(f"""() => {{
                        const inputs = document.querySelectorAll('input');
                        for (const inp of inputs) {{
                            if (inp.offsetParent !== null && inp.value === '') {{
                                inp.focus();
                                inp.value = '{code}';
                                inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                                return true;
                            }}
                        }}
                        return false;
                    }}""")
                    log("验证码已填入 (JS)")
                except Exception as e:
                    result["error"] = f"填入验证码失败: {e}"
                    await browser.close()
                    return result

            await asyncio.sleep(1)

            # ── 6. 点击登录按钮 ──
            log("点击登录按钮...")
            login_clicked = False
            for text in ["登录", "确认", "同意并登录", "确认登录", "提交", "下一步"]:
                try:
                    btn = page.locator(f'button:has-text("{text}"), span:has-text("{text}"), div:has-text("{text}")').first
                    if await btn.count() > 0 and await btn.is_visible():
                        await btn.click()
                        login_clicked = True
                        log(f"点击 '{text}' 按钮")
                        break
                except:
                    continue

            if not login_clicked:
                await page.keyboard.press("Enter")
                login_clicked = True
                log("按 Enter 提交")

            result["login_clicked"] = True

            # ── 7. 关键捕捉：等待页面响应 ──
            await asyncio.sleep(5)

            # 截图
            try:
                await page.screenshot(path=screenshot_path, full_page=False)
                result["screenshot_path"] = screenshot_path
                log(f"截图已保存: {screenshot_path}")
            except Exception as e:
                log(f"截图失败: {e}")

            # 记录 URL 和标题
            result["page_url_after_login"] = page.url
            result["page_title_after_login"] = await page.title()

            # ── 8. 核心：捕捉所有红色文字 ──
            log("正在捕捉页面上的红色文字...")
            try:
                red_texts = await page.evaluate("""() => {
                    const results = [];
                    const all = document.querySelectorAll('*');
                    for (const el of all) {
                        if (el.offsetParent === null) continue;
                        const style = window.getComputedStyle(el);
                        const color = style.color;
                        const isRed = color.includes('rgb(255,') || color === 'red' ||
                                     color.includes('rgb(231') || color.includes('#e') ||
                                     color.includes('#f') || color.includes('#d');
                        if (isRed && el.textContent.trim().length > 1) {
                            results.push({
                                text: el.textContent.trim().substring(0, 200),
                                color: color,
                                tag: el.tagName,
                                id: el.id || '',
                                class: (el.className || '').substring(0, 80),
                                rect: el.getBoundingClientRect()
                            });
                        }
                    }
                    return results;
                }""")
                # 去重（按文本内容）
                seen = set()
                for rt in red_texts:
                    t = rt["text"][:50]
                    if t not in seen:
                        seen.add(t)
                        result["red_texts"].append(rt)
                log(f"找到 {len(result['red_texts'])} 条红色文字")
            except Exception as e:
                log(f"捕捉红色文字失败: {e}")

            # ── 9. 捕捉登录按钮附近的错误提示 ──
            try:
                near_login = await page.evaluate("""() => {
                    const results = [];
                    // 找所有可能包含错误提示的容器
                    const containers = document.querySelectorAll(
                        '.error, .tip, .msg, .toast, .hint, [class*="error"], ' +
                        '[class*="tip"], [class*="msg"], [class*="hint"], ' +
                        '[class*="warn"], [class*="alert"], [class*="notice"]'
                    );
                    for (const c of containers) {
                        if (c.offsetParent !== null && c.textContent.trim().length > 0) {
                            results.push({
                                text: c.textContent.trim().substring(0, 300),
                                class: (c.className || '').substring(0, 100),
                                tag: c.tagName,
                                visible: true
                            });
                        }
                    }
                    // 也检查页面底部和登录按钮下方的所有可见文本
                    const allText = document.body.innerText || '';
                    results.push({text: '(全页文本前3000字)', full_text_snippet: allText.substring(0, 3000)});
                    return results;
                }""")
                result["near_login_texts"] = near_login
            except Exception as e:
                log(f"捕捉附近文字失败: {e}")

            # ── 10. 检测是否包含"App登录"相关关键词 ──
            full_text = await page.evaluate("document.body.innerText") or ""
            result["full_text_snippet"] = full_text[:2000]

            app_keywords = [
                "App", "app", "APP", "应用",
                "抖音App", "客户端",
                "扫一扫", "扫码",
                "请使用", "请打开",
                "打开抖音",
            ]
            for kw in app_keywords:
                if kw in full_text:
                    result["found_app_login"] = True
                    log(f"⚠️ 检测到关键词 '{kw}' — 可能是 App 登录要求")
                    # 找到关键词附近的内容
                    idx = full_text.find(kw)
                    if idx >= 0:
                        nearby = full_text[max(0, idx-30):idx+80]
                        log(f"   附近内容: ...{nearby}...")

            # 关闭浏览器
            await browser.close()

            # 检查是否还有 passport/login 在 URL 中（仍在登录页 = 登录被拦截）
            current_url = result.get("page_url_after_login", "")
            if "passport" in current_url.lower() or "login" in current_url.lower():
                log("⚠️ 登录后仍在登录页 — 登录被拦截")
                result["found_app_login"] = True

            log(f"尝试 {attempt} 完成")
            return result

    except Exception as e:
        tb = traceback.format_exc()
        result["error"] = f"{type(e).__name__}: {e}\n{tb[:300]}"
        log(f"❌ 尝试 {attempt} 异常: {e}")
        try:
            await browser.close()
        except:
            pass
        return result


async def main():
    parser = argparse.ArgumentParser(description="探测抖音 App 登录要求")
    parser.add_argument("--phone", default="15370108283", help="手机号")
    parser.add_argument("--max-attempts", type=int, default=4, help="最多尝试次数")
    parser.add_argument("--interval", type=int, default=600, help="间隔秒数")
    parser.add_argument("--output-dir", default="/tmp", help="输出目录")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    all_results = []
    for attempt in range(1, args.max_attempts + 1):
        log(f"\n{'='*50}")
        log(f"开始第 {attempt}/{args.max_attempts} 次探测")
        log(f"{'='*50}")

        result = await detect_once(args.phone, attempt, args.output_dir)
        all_results.append(result)

        # 保存每次结果
        result_file = os.path.join(args.output_dir, "detect_login_result.json")
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump({"all_attempts": all_results, "total": attempt}, f,
                      ensure_ascii=False, indent=2)
        log(f"结果已保存: {result_file}")

        # 如果找到了 App 登录特征，提前结束
        if result.get("found_app_login"):
            log("\n✅ 已检测到 App 登录要求！停止后续尝试。")
            break

        # 如果还有下一次，等待间隔
        if attempt < args.max_attempts:
            log(f"\n等待 {args.interval} 秒后进行第 {attempt+1} 次尝试...")
            await asyncio.sleep(args.interval)

    # 输出摘要
    log("\n" + "="*50)
    log("探测完成")
    log(f"总尝试次数: {len(all_results)}")

    # 找到有 app_login 特征的尝试
    for r in all_results:
        if r.get("found_app_login"):
            log(f"\n尝试 {r['attempt']}: ✅ 检测到 App 登录要求")
            for rt in r.get("red_texts", [])[:10]:
                log(f"  红色文字: {rt.get('text', '')[:100]}")
            if r.get("near_login_texts"):
                for nt in r["near_login_texts"]:
                    t = nt.get("text", "")
                    if len(t) > 5 and "full_text" not in t:
                        log(f"  提示文本: {t[:200]}")
                    if "full_text_snippet" in nt:
                        log(f"\n  全页文本片段:")
                        print(nt["full_text_snippet"][:800])
            break
    else:
        log("⚠️ 所有尝试均未检测到 App 登录特征")
        # 打印最后一次的红色文字作为参考
        if all_results:
            last = all_results[-1]
            log(f"\n最后一次尝试的红色文字:")
            for rt in last.get("red_texts", [])[:10]:
                log(f"  {rt.get('text', '')[:100]}")


if __name__ == "__main__":
    asyncio.run(main())

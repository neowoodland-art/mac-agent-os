#!/usr/bin/env python3
"""
探测脚本 v2：检测抖音SMS登录被"必须使用App登录"拦截

v2 核心变化：不需要 SMS 验证码！
  因为账号被标记后，抖音可能根本不发短信。
  我们只要导航到登录页、填入手机号、点击获取验证码，
  观察页面是否立即出现"必须使用App"的提示。

用法:
  python3 detect_app_login.py --phone=15370108283

输出:
  /tmp/detect_login_result.json — 包含红色提示文字和截图
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

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR / "matrix_modules"))
sys.path.insert(0, str(_SCRIPT_DIR))


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


async def detect(phone: str, output_dir: str) -> dict:
    """执行一次登录探测，不需要验证码"""
    result = {
        "timestamp": datetime.now().isoformat(),
        "phone": phone,
        "steps": [],
        "red_texts": [],
        "hint_texts": [],
        "near_login_texts": [],
        "page_url": "",
        "page_title": "",
        "screenshot_path": "",
        "full_text_snippet": "",
        "found_app_login": False,
        "app_keyword_context": [],
        "error": None,
    }

    from camoufox.async_api import AsyncCamoufox
    screenshot_path = os.path.join(output_dir, "login_detect.png")

    try:
        fox = AsyncCamoufox(
            headless=False,
            persistent_context=False,
            locale="zh-CN",
            os="windows",
            humanize=1.5,
        )
        browser = await fox.start()
        if browser.contexts:
            context = browser.contexts[0]
        else:
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800}
            )
        page = context.pages[0] if context.pages else await context.new_page()

        # ── Step 1: 导航到登录页 ──
        log("导航到抖音登录页...")
        await page.goto(
            "https://www.douyin.com/passport/sso/login/",
            timeout=30000, wait_until="domcontentloaded"
        )
        await asyncio.sleep(4)
        result["steps"].append("navigate_login")
        result["page_url"] = page.url
        result["page_title"] = await page.title()

        # ── Step 2: 找手机号输入框并填号 ──
        log("查找手机号输入框...")
        phone_filled = False
        for sel in [
            'input[placeholder*="手机"]',
            'input[type="tel"]',
            'input[name="mobile"]',
        ]:
            try:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible():
                    await el.click()
                    await asyncio.sleep(0.3)
                    await el.fill(phone)
                    phone_filled = True
                    log(f"已填入手机号: {phone}")
                    break
            except:
                continue

        if not phone_filled:
            # JS 兜底
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
                phone_filled = True
                log("JS 填手机号成功")
            except Exception as e:
                result["error"] = f"无法填手机号: {e}"
                await browser.close()
                return result

        result["steps"].append("filled_phone")
        await asyncio.sleep(2)

        # ── Step 3: 截图（填写手机号后的页面状态）──
        try:
            await page.screenshot(path=screenshot_path, full_page=False)
            result["screenshot_path"] = screenshot_path
        except:
            pass

        # ── Step 4: 捕捉"点击获取验证码"前的页面状态 ──
        log("捕捉页面上现有文本...")
        try:
            full_text = await page.evaluate("document.body.innerText") or ""
            result["full_text_snippet"] = full_text[:2000]
            # 搜索 App 相关关键词
            for kw in ["App", "app", "APP", "应用", "抖音App", "客户端", "扫一扫",
                       "请使用", "请打开", "打开抖音", "扫码"]:
                idx = full_text.find(kw)
                if idx >= 0:
                    nearby = full_text[max(0, idx-20):idx+80]
                    result["app_keyword_context"].append(nearby)
                    log(f"⚠️ 关键词 '{kw}': ...{nearby}...")
        except:
            pass

        # ── Step 5: 点击获取验证码 ──
        log("点击获取验证码...")
        clicked = False
        for text in ["获取验证码", "获取"]:
            try:
                btn = page.locator(f'button:has-text("{text}"), span:has-text("{text}")').first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    clicked = True
                    log(f"点击 '{text}'")
                    break
            except:
                continue

        if not clicked:
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
                clicked = True
                log("JS 点击获取验证码")
            except:
                pass

        if not clicked:
            result["error"] = "无法点击获取验证码"
            await browser.close()
            return result

        result["steps"].append("clicked_get_code")

        # ── Step 6: 等待页面响应（关键！捕捉错误提示）──
        await asyncio.sleep(5)

        # 截图（点击获取验证码后的页面）
        try:
            await page.screenshot(path=screenshot_path.replace(".png", "_after_code.png"))
        except:
            pass

        result["page_url"] = page.url

        # ── Step 7: 全面捕捉页面文本 ──
        log("捕捉页面文本...")

        full_text = ""
        try:
            full_text = await page.evaluate("document.body.innerText") or ""
        except:
            pass
        result["full_text_snippet"] = full_text[:2000]

        # 搜索 App 关键词
        app_kws = ["App", "app", "APP", "应用", "抖音App", "客户端", "扫一扫",
                   "请使用", "请打开", "打开抖音", "扫码", "下载", "安装"]
        for kw in app_kws:
            idx = full_text.find(kw)
            if idx >= 0:
                nearby = full_text[max(0, idx-20):idx+80]
                result["app_keyword_context"].append(nearby)
                result["found_app_login"] = True
                log(f"✅ 关键词 '{kw}': ...{nearby}...")

        # ── Step 8: 捕捉红色文字 ──
        try:
            red_texts = await page.evaluate("""() => {
                const results = [];
                const all = document.querySelectorAll('*');
                for (const el of all) {
                    if (el.offsetParent === null) continue;
                    const style = window.getComputedStyle(el);
                    const color = style.color;
                    if (color.includes('rgb(255,') || color === 'red' ||
                        color.includes('#e5') || color.includes('#f0') ||
                        color.includes('#d32')) {
                        const t = el.textContent.trim();
                        if (t.length > 2 && t.length < 200) {
                            results.push({
                                text: t,
                                color: color,
                                tag: el.tagName,
                                class: (el.className || '').substring(0, 80)
                            });
                        }
                    }
                }
                return results;
            }""")
            seen = set()
            for rt in red_texts:
                t = rt["text"][:40]
                if t not in seen:
                    seen.add(t)
                    result["red_texts"].append(rt)
            if result["red_texts"]:
                log(f"找到 {len(result['red_texts'])} 条红色文字:")
                for rt in result["red_texts"][:10]:
                    log(f"  ⛔ {rt['text'][:100]}")
        except Exception as e:
            log(f"红色文字捕捉异常: {e}")

        # ── Step 9: 捕捉提示/错误信息容器 ──
        try:
            hints = await page.evaluate("""() => {
                const results = [];
                const containers = document.querySelectorAll(
                    '.error, .tip, .msg, .toast, .hint, [class*="error"], ' +
                    '[class*="tip"], [class*="msg"], [class*="warn"], ' +
                    '[class*="alert"], [class*="notice"]'
                );
                for (const c of containers) {
                    if (c.offsetParent !== null && c.textContent.trim().length > 0) {
                        results.push({
                            text: c.textContent.trim().substring(0, 300),
                            class: (c.className || '').substring(0, 100),
                            tag: c.tagName
                        });
                    }
                }
                return results;
            }""")
            result["hint_texts"] = hints
            if hints:
                log(f"找到 {len(hints)} 个提示容器:")
                for h in hints[:10]:
                    log(f"  📋 {h['text'][:120]}")
        except:
            pass

        # ── Step 10: 检测登录框状态 ──
        # 如果 URL 仍然是登录页，说明没有自动登录成功
        current_url = page.url
        result["page_url"] = current_url
        still_on_login = "passport" in current_url.lower() or "login" in current_url.lower()
        if still_on_login:
            log("⚠️ 仍在登录页 — 登录被拦截")
            result["found_app_login"] = True

        await browser.close()
        log("探测完成")
        return result

    except Exception as e:
        tb = traceback.format_exc()
        result["error"] = f"{type(e).__name__}: {e}\n{tb[:300]}"
        log(f"❌ 异常: {e}")
        try:
            await browser.close()
        except:
            pass
        return result


async def main():
    parser = argparse.ArgumentParser(description="探测抖音 App 登录要求 (v2, 不需要SMS)")
    parser.add_argument("--phone", default="15370108283", help="手机号")
    parser.add_argument("--output-dir", default="/tmp", help="输出目录")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    log(f"开始探测: phone={args.phone}")
    log(f"注意: 此版本不需要 SMS 验证码，只观察页面响应")

    result = await detect(args.phone, args.output_dir)

    result_file = os.path.join(args.output_dir, "detect_login_result.json")
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log(f"结果已保存: {result_file}")

    # 输出摘要
    log("\n" + "=" * 60)
    if result.get("found_app_login"):
        log("✅ 结论: 检测到 App 登录要求!")
        for ctx in result.get("app_keyword_context", []):
            log(f"  关键词上下文: {ctx}")
    else:
        log("⚠️ 未检测到 App 登录特征")
        log("可能是账号还可以正常 SMS 登录，或需要实际获得验证码才能触发")

    if result.get("red_texts"):
        log("\n所有红色文字:")
        for rt in result["red_texts"]:
            log(f"  ⛔ {rt['text']}")
    if result.get("hint_texts"):
        log("\n所有提示容器:")
        for h in result["hint_texts"]:
            log(f"  📋 {h['text']}")


if __name__ == "__main__":
    asyncio.run(main())

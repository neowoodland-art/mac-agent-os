#!/usr/bin/env python3
"""LongCat 每日免费额度自动领取 v3.3
Camoufox persistent_context 模式，Cookie 持久化到 Profile 目录。
"""

import asyncio
import argparse
import sys
from pathlib import Path

from camoufox import AsyncCamoufox

# 领取按钮匹配关键词
CLAIM_KEYWORDS = ['立即申请', '申请', '领取', 'claim', '获取额度']
# 点击策略：每 300ms 轮询，持续 65 秒
CLICK_INTERVAL_MS = 300
CLICK_DURATION_S = 65


async def claim(args: argparse.Namespace) -> int:
    profile_dir = Path(args.profile)
    if not profile_dir.is_absolute():
        profile_dir = Path.cwd() / profile_dir
    profile_dir.mkdir(parents=True, exist_ok=True)
    headless = args.auto

    print(f"[LongCat Claimer v3.3]")
    print(f"  Profile: {profile_dir}")
    print(f"  Headless: {headless}")

    exit_code = 1

    async with AsyncCamoufox(
        headless=headless,
        persistent_context=True,
        user_data_dir=str(profile_dir),
        proxy={'server': 'socks5://127.0.0.1:10800'},
    ) as ctx:
        page = await ctx.new_page()

        try:
            # 1. 打开 longcat.chat
            print("[1/3] 打开 longcat.chat ...")
            await page.goto('https://longcat.chat', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)

            # 2. 检查登录状态
            content = await page.content()
            if 'Log In' in content and 'Log Out' not in content:
                print("[FAIL] 未登录 — Cookie 已过期，需手动登录 longcat.chat")
                # 截图留档
                await page.screenshot(path=str(profile_dir / 'login_fail.png'))
                return 1

            login_indicators = ['登录', 'Sign In', 'signin']
            if any(ind in content for ind in login_indicators) and '开始对话' not in content:
                print("[FAIL] 检测到登录页面，Cookie 已失效")
                await page.screenshot(path=str(profile_dir / 'login_fail.png'))
                return 1

            print("[OK] 已登录")

            # 3. 激进点击策略
            print(f"[2/3] 开始点击领取（{CLICK_DURATION_S}s 内每 {CLICK_INTERVAL_MS}ms 轮询）...")
            clicked = False
            total_ticks = int(CLICK_DURATION_S * 1000 / CLICK_INTERVAL_MS)

            for i in range(total_ticks):
                for kw in CLAIM_KEYWORDS:
                    try:
                        btn = page.locator(f'button:has-text("{kw}")').first
                        if await btn.is_visible(timeout=100):
                            await btn.click(force=True)
                            print(f"[3/3] ✅ 已点击 '{kw}' 按钮！")
                            clicked = True
                            exit_code = 0
                            break
                    except Exception:
                        pass

                    try:
                        # 也尝试 a 标签和 div 按钮
                        el = page.locator(f'a:has-text("{kw}"), div:has-text("{kw}")').first
                        if await el.is_visible(timeout=50):
                            await el.click(force=True)
                            print(f"[3/3] ✅ 已点击 '{kw}' 元素！")
                            clicked = True
                            exit_code = 0
                            break
                    except Exception:
                        pass

                if clicked:
                    break

                if i % 20 == 0 and i > 0:
                    print(f"  已轮询 {i * CLICK_INTERVAL_MS / 1000:.0f}s ...")
                await asyncio.sleep(CLICK_INTERVAL_MS / 1000)

            if not clicked:
                print("[FAIL] 未找到任何领取按钮")
                await page.screenshot(path=str(profile_dir / 'no_button.png'))

            await asyncio.sleep(2)

        except Exception as e:
            print(f"[ERROR] {e}")
            await page.screenshot(path=str(profile_dir / 'error.png'))
            exit_code = 1

    return exit_code


def main():
    parser = argparse.ArgumentParser(description='LongCat 每日免费额度自动领取')
    parser.add_argument('--auto', action='store_true', help='无头模式（自动化运行）')
    parser.add_argument('--account', default='longcat_185', help='账号名（对应 profiles/<account>/）')
    parser.add_argument('--profile', default=None, help='自定义 Profile 路径')
    args = parser.parse_args()

    if args.profile is None:
        args.profile = f'profiles/{args.account}'

    exit_code = asyncio.run(claim(args))
    sys.exit(exit_code)


if __name__ == '__main__':
    main()

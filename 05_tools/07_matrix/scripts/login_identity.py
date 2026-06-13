#!/usr/bin/env python3
"""
身份登录 — 首次手动登录，登录态保存到持久化目录

用法:
  python login_identity.py <identity_name> [--platform douyin|xiaohongshu]

流程:
  1. 通过 cdp_connector.CDPConnector(identity_dir=...) 启动 Camoufox 持久化
  2. 用户手动登录
  3. 按 Enter 触发 → 状态自动保存

支持平台:
  - douyin       → douyin.com
  - xiaohongshu  → xiaohongshu.com/explore
"""
import argparse
import asyncio
import sys
from pathlib import Path

IDENTITIES_ROOT = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix" / "identities"

# ── 平台 URL 映射 ──
PLATFORM_URLS = {
    "douyin": "https://www.douyin.com/",
    "xiaohongshu": "https://www.xiaohongshu.com/explore",
}

PLATFORM_NAMES = {
    "douyin": "抖音",
    "xiaohongshu": "小红书",
}


async def login_identity(identity_name: str, platform: str = "auto"):
    """执行首次手动登录
    Args:
        identity_name: 账号ID
        platform: "auto" 时从 accounts.yaml 自动解析
    """
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))

    # 从账号注册表读取 identity_dir 和 platform
    acct_info = {}
    try:
        from matrix_mgmt import MatrixManager
        mgr = MatrixManager()
        for a in mgr.list_accounts():
            if a["id"] == identity_name:
                acct_info = a
                break
    except: pass

    # 身份目录：优先用 accounts.yaml 中的 identity_dir，否则用账号ID
    acct_identity = acct_info.get("identity_dir") or acct_info.get("identity_hint") or identity_name
    acct_identity = acct_identity.replace("identities/", "")
    identity_dir = str(IDENTITIES_ROOT / acct_identity)

    # 平台：auto 时从账号信息解析
    if platform == "auto":
        p = acct_info.get("platform", "douyin")
        platform = p if p in ("douyin", "xiaohongshu") else "douyin"

    signal_file = Path(f"/tmp/login_identity_{identity_name}.signal")
    platform_url = PLATFORM_URLS.get(platform, PLATFORM_URLS["douyin"])
    platform_name = PLATFORM_NAMES.get(platform, platform)

    # 前置检查
    if not Path(identity_dir).exists():
        print(f"❌ 身份 '{identity_name}' 不存在")
        print(f"   请先运行: python create_identity.py {identity_name}")
        sys.exit(1)

    # 清理旧信号
    if signal_file.exists():
        signal_file.unlink()

    from cdp_connector import CDPConnector

    print(f"\n{'='*55}")
    print(f" 🔐 {platform_name} 身份登录: {identity_name}")
    print(f"{'='*55}")
    print(f"   持久化目录: {identity_dir}/user_data/")

    # 通过 cdp_connector 启动持久化 Camoufox
    conn = CDPConnector(
        identity_dir=identity_dir,
        headless=False,
        window=(702, 783),
    )

    try:
        await conn.connect()
    except Exception as e:
        print(f"❌ 浏览器连接失败: {e}")
        sys.exit(1)

    # 设置视口
    try:
        await conn.page.set_viewport_size({"width": 702, "height": 783})
    except Exception:
        pass

    # 导航到平台首页
    print(f"   📍 打开 {platform_name} 首页...")
    try:
        await conn.page.goto(platform_url, timeout=30000, wait_until="domcontentloaded")
    except Exception:
        print(f"   ⚠️ 页面加载超时，但浏览器已打开，请手动导航")
    print(f"   🌐 当前页面: {conn.page.url}")

    # 创建信号文件表示浏览器已就绪
    signal_file.write_text("ready")

    print(f"\n   🟡 请手动登录账号 [{identity_name}] ({platform_name})")
    print(f"      Camoufox 窗口已打开（Windows 平板模式 702×783）")
    print(f"      {'💡 打开小红书后如果出现登录弹窗，先手动关闭' if platform == 'xiaohongshu' else ''}")
    print(f"      登录完成后，在终端按 Enter 键确认")
    print(f"      或: touch {signal_file}")
    print()

    # 轮询等待信号
    while signal_file.exists() and signal_file.read_text().strip() == "ready":
        await asyncio.sleep(2)

    print(f"\n   ✅ 登录态准备保存")

    # 验证登录状态
    print(f"   🔍 验证登录状态...")
    await asyncio.sleep(2)

    cookies = await conn.context.cookies()
    platform_cookies = [c for c in cookies if platform.replace("_", "").replace("hongshu", "") in c.get('domain', '')]
    
    # 使用 auth_manager 的规则检测
    from auth_manager import check_login_by_cookie_sync, get_session_id
    logged_in = check_login_by_cookie_sync(cookies, platform)
    session_val = get_session_id(cookies, platform)

    if logged_in:
        cnt = len(platform_cookies)
        print(f"      登录: ✅ 检测到 {platform_name} session cookie")
        if session_val:
            print(f"      session: {session_val[:20]}...")
    else:
        print(f"      登录: ⚠️ 未检测到 {platform_name} session cookie")
        print(f"      平台 Cookie 数: {len(platform_cookies)}")
        print(f"      请确认是否已成功登录（全部 Cookie: {len(cookies)} 个）")
        # 兜底：只要平台 cookie 够多就认为登录了
        if len(platform_cookies) > 30:
            print(f"      → 平台 Cookie 数量充足，判定为已登录 ✅")
            logged_in = True

    print(f"\n{'='*55}")
    if logged_in:
        print(f" ✅ 身份 '{identity_name}' 登录完成！")
    else:
        print(f" ⚠️ 身份 '{identity_name}' 登录状态不确定")
        print(f"    Cookie 已保存，可尝试运行养号查看效果")
    print(f"   浏览器保持运行，可进行养号操作")
    print(f"{'='*55}")

    # 保持浏览器运行（不调用 conn.close()）


def main():
    parser = argparse.ArgumentParser(description="身份登录 — 首次手动登录")
    parser.add_argument("identity_name", help="身份名称 (如 douyin_01)")
    parser.add_argument("--platform", "-p", default="douyin",
                        choices=["douyin", "xiaohongshu"],
                        help="平台 (douyin/xiaohongshu)")
    args = parser.parse_args()
    asyncio.run(login_identity(args.identity_name, args.platform))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
身份登录 — 首次手动登录，登录态保存到持久化目录

用法:
  python login_identity.py <identity_name>

流程:
  1. 通过 cdp_connector.CDPConnector(identity_dir=...) 启动 Camoufox 持久化
  2. 用户手动登录
  3. 按 Enter/信号触发 → 状态自动保存
"""
import argparse
import asyncio
import sys
from pathlib import Path

IDENTITIES_ROOT = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix" / "identities"


async def login_identity(identity_name: str):
    """执行首次手动登录"""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))

    identity_dir = str(IDENTITIES_ROOT / identity_name)
    signal_file = Path(f"/tmp/login_identity_{identity_name}.signal")

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
    print(f" 🔐 身份登录: {identity_name}")
    print(f"{'='*55}")
    print(f"   持久化目录: {identity_dir}/user_data/")

    # 通过 cdp_connector 启动持久化 Camoufox
    conn = CDPConnector(
        identity_dir=identity_dir,
        headless=False,
        window=(702, 783),
    )

    await conn.connect()

    # 设置视口
    await conn.page.set_viewport_size({"width": 702, "height": 783})

    # 导航到抖音
    print(f"   📍 打开抖音首页...")
    try:
        await conn.page.goto("https://www.douyin.com/",
                             timeout=30000, wait_until="domcontentloaded")
    except Exception:
        print(f"   ⚠️ 页面加载超时，但浏览器已打开，请手动导航")
    print(f"   🌐 当前页面: {conn.page.url}")

    # 创建信号文件表示浏览器已就绪
    signal_file.write_text("ready")

    print(f"\n   🟡 请手动登录账号 [{identity_name}]")
    print(f"      Camoufox 窗口已打开（Windows 平板模式 702×783）")
    print(f"      登录完成后，在对话中告诉我 '登好了'")
    print(f"      信号文件: {signal_file}")
    print()

    # 轮询等待信号
    while signal_file.exists() and signal_file.read_text().strip() == "ready":
        await asyncio.sleep(2)

    print(f"\n   ✅ 登录态已保存")

    # 验证登录状态
    print(f"   🔍 验证登录状态...")
    await asyncio.sleep(2)

    cookies = await conn.context.cookies()
    douyin_cookies = [c for c in cookies if 'douyin' in c.get('domain', '')]
    session_cookies = [c for c in douyin_cookies
                       if 'session' in c.get('name', '').lower()
                       or 'sid' in c.get('name', '').lower()
                       or 'token' in c.get('name', '').lower()]

    if session_cookies:
        print(f"      登录: ✅ {len(session_cookies)} 个 session cookie")
    else:
        print(f"      登录: ⚠️ 未检测到 session cookie")
        print(f"      请确认是否已成功登录")

    print(f"\n{'='*55}")
    print(f" ✅ 身份 '{identity_name}' 登录完成！")
    print(f"   浏览器保持运行，可进行养号操作")
    print(f"{'='*55}")

    # 保持浏览器运行（不调用 conn.close()）
    # 进程需要手动停止


def main():
    parser = argparse.ArgumentParser(description="身份登录 — 首次手动登录")
    parser.add_argument("identity_name", help="身份名称 (如 douyin_01)")
    args = parser.parse_args()
    asyncio.run(login_identity(args.identity_name))


if __name__ == "__main__":
    main()

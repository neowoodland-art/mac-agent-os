#!/usr/bin/env python3
"""
comment_video.py — 自动评论指定抖音视频

用法:
  python comment_video.py <account_id> <video_url> [评论内容] [--keep-open]

示例:
  python comment_video.py douyin_01 "https://v.douyin.com/xxx" "好内容"

流程:
  1. 打开账号浏览器（持久化身份，带登录态）
  2. 导航到视频页
  3. 激活评论区 → 粘贴 → Enter发送
  4. 回精选页

默认评论后 5s 自动关闭浏览器。加 --keep-open 保持打开供查看。
"""
import asyncio, os, sys, yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def log(m):
    print(m, flush=True)

async def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    account_id = sys.argv[1]
    video_url = sys.argv[2]
    comment_text = sys.argv[3] if len(sys.argv) > 3 else "好内容"
    keep_open = "--keep-open" in sys.argv

    # 加载配置

    # 加载配置
    acct_file = os.path.expanduser("~/workbuddy-agent-os/agent-local/tools/matrix/config/accounts.yaml")
    with open(acct_file) as f:
        data = yaml.safe_load(f)

    acct = None
    for a in data["accounts"]:
        if a["id"] == account_id and a.get("enabled", True):
            acct = a
            break

    if not acct:
        log(f"❌ 账号 {account_id} 不存在或已禁用")
        sys.exit(1)

    pos = acct.get("window_position", [0, 0])
    ID_DIR = os.path.expanduser(f"~/workbuddy-agent-os/agent-local/tools/matrix/{acct.get('identity_dir', 'identities/' + account_id)}")

    log(f"🚀 账号: {account_id}")
    log(f"📄 视频: {video_url}")
    log(f"💬 评论: {comment_text}")

    from cdp_connector import CDPConnector
    from atom_ops import AtomOps

    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=tuple(pos))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()

    ops = AtomOps(page)

    # 登录检测
    has_session = any(
        c["name"] == "sessionid" and c.get("value")
        for c in await page.context.cookies()
        if "douyin" in c.get("domain", "")
    )
    if not has_session:
        log("❌ 未登录或登录态过期，请在浏览器中重新登录")
        try:
            while True:
                await asyncio.sleep(10)
        except:
            pass
        return

    log("✅ 登录正常")

    # 执行评论
    result = await ops.comment_on_video_url(video_url, comment_text)
    log(f"结果: {result}")

    if result.success:
        log(f"\n🎉 评论完成！已回精选页")
    else:
        log(f"\n⚠️ 评论未完成: {result.detail}")

    if keep_open:
        log("\n✅ 浏览器保持打开供查看")
        try:
            while True:
                await asyncio.sleep(10)
        except:
            pass
    else:
        log("🔒 评论完成，3 秒后自动关闭浏览器...")
        await asyncio.sleep(3)
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())

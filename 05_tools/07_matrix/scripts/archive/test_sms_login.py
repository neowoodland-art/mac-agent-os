#!/usr/bin/env python3
"""测试 SMS 登录完整流程"""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector
from matrix_modules.account.sms_login import sms_login

LOG = '/tmp/sms_login_test.log'
def log(m):
    with open(LOG,'a') as f: f.write(m+'\n')
    print(m, flush=True)

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_02_camo')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(0,0))
    await conn.connect(); page = conn.page; await conn.init_anti_detection()
    await page.goto('https://www.douyin.com/', timeout=30000, wait_until='domcontentloaded')
    await asyncio.sleep(6)

    log('🚀 浏览器就绪，开始 SMS 登录测试')
    # douyin_02 的 account_id，用于从 accounts.yaml 查手机号
    ok = await sms_login(page, account_name='douyin_02', log_func=log)

    if ok:
        log('\n🎉 登录成功！')
    else:
        log('\n❌ 登录失败')
    
    log('\n✅ 浏览器保持打开')
    while True: await asyncio.sleep(10)

asyncio.run(main())

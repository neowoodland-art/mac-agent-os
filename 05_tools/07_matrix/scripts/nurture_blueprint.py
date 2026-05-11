"""
nurture_blueprint.py — 养号蓝图：浏览+点赞+收藏+评论

蓝图 = 操作序列，每步 = (op_name, fn, pre_state, post_state, prob)

操作 fn 是单行 lambda，执行后返回状态码。
"""
import asyncio, random, subprocess, time, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

LOG = '/tmp/nurture.log'
def log(m):
    with open(LOG, 'a') as f: f.write(f'[{time.strftime("%H:%M:%S")}] {m}\n')
    print(m, flush=True)

# ═══════════════════════════════════════════════
# 原子操作层（每行一个，极简）
# ═══════════════════════════════════════════════

async def activate():
    for _ in range(3):
        subprocess.run(['osascript','-e',
            'tell application "System Events" to set frontmost of every process whose name contains "camoufox" to true'],
            capture_output=True, timeout=3); time.sleep(0.3)

async def read_state(p):
    return await p.evaluate("""() => {
        var ae=document.activeElement; var ed=document.querySelector('.public-DraftEditor-content');
        return {
            url:(location.href||'').slice(0,50), vc:document.querySelectorAll('video').length,
            hasCL:!!document.querySelector('[data-e2e="comment-list"]'),
            hasEd:!!ed, aeIsEd:!!(ae&&(ae.isContentEditable||ae.getAttribute('contenteditable')==='true')),
            edText:(ed?.textContent||'').trim().slice(0,20),
            hasVerify:!!document.querySelector('input[placeholder*="验证码"]'),
            aeRect:ae?(function(){var r=ae.getBoundingClientRect();return{x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};})():null,
            likeState:(document.querySelector('[data-e2e="video-player-digg"]')?.getAttribute('data-e2e-state')||''),
        };
    }""")

async def op_goto_home(p):
    await p.goto('https://www.douyin.com/',timeout=20000); await asyncio.sleep(4)
    return 'HOME'

async def op_enter_video(p):
    c = p.locator('.discover-video-card-item').first
    await c.click(force=True); await asyncio.sleep(1.5)
    v = p.locator('video').first
    if await v.count()>0: await v.click(); await asyncio.sleep(1); await v.click(); await asyncio.sleep(4)
    s = await read_state(p)
    return 'PLAYER' if s['vc']>=2 else 'HOME'

async def op_swipe_down(p):
    await p.mouse.wheel(0,800); await asyncio.sleep(1)
    await p.keyboard.press('ArrowDown'); await asyncio.sleep(3)
    return 'PLAYER'

async def op_like(p):
    b = p.locator('[data-e2e="video-player-digg"]').first
    if await b.count()>0:
        await b.click(); await asyncio.sleep(1)
        return 'LIKED'
    return 'PLAYER'

async def op_watch(p):
    t = random.uniform(5,12)
    await asyncio.sleep(t)
    return 'PLAYER'

async def op_comment(p, text='好内容'):
    # 1. 开评论（前置锚点：检查是否已打开）
    s = await read_state(p)
    if s['hasCL']:
        log('  评论区已开，跳过')
    else:
        v = p.locator('video').first
        if await v.count()>0:
            bx = await v.bounding_box()
            if bx: await p.mouse.click(bx['x']+bx['width']//2,bx['y']+bx['height']//3)
        await asyncio.sleep(0.5)
        await p.keyboard.press('x'); await asyncio.sleep(2)
        s = await read_state(p)
        if not s['hasCL']:
            await p.evaluate("""()=>{var b=document.querySelector('[data-e2e="video-comment-count"]')||document.querySelector('[data-e2e="feed-comment-icon"]');if(b)b.click();}""")
            await asyncio.sleep(2)

    # 2. 激活编辑器（缓慢移动到479,687→单击）
    for step in range(8):
        await p.mouse.move(10+(479-10)*(step+1)/8, 10+(687-10)*(step+1)/8); await asyncio.sleep(0.1)
    await asyncio.sleep(0.5)
    await p.mouse.click(479,687); await asyncio.sleep(1)
    s = await read_state(p)
    if not s['aeIsEd']:
        await p.mouse.click(479,687); await asyncio.sleep(1)  # 双击兜底
    s = await read_state(p)

    # 3. 粘贴中文
    if s['aeIsEd']:
        subprocess.run(['osascript','-e',f'set the clipboard to "{text}"'], timeout=5); time.sleep(0.3)
        await p.keyboard.press('Meta+v'); await asyncio.sleep(2)
        s = await read_state(p)
        if s['edText']:
            # 4. Alt+Enter 发送
            subprocess.run(['osascript','-e','tell application "System Events" to key code 36 using option down'], timeout=5)
            await asyncio.sleep(3)
            s = await read_state(p)
            if s['hasVerify']: log('  📱 触发验证码')
            # 5. 关评论区
            if s['hasCL']:
                await p.keyboard.press('x'); await asyncio.sleep(1)
                log('  🅧 评论区已关闭')
            return 'COMMENTED'
    return 'PLAYER'

async def op_close_comments(p):
    """关闭评论区（前置锚点：hasCL=True）"""
    s = await read_state(p)
    if s['hasCL']:
        await p.keyboard.press('x'); await asyncio.sleep(1)
        return 'PLAYER'
    return 'PLAYER'

# ═══════════════════════════════════════════════
# 蓝图定义
# ═══════════════════════════════════════════════

# 每个步骤: (名称, 操作函数, 可选参数, 执行概率)
BLUEPRINT_NURTURE = [
    ("进入视频",    op_enter_video, {}, 1.0),
    ("观看",        op_watch,       {}, 1.0),
    ("点赞",        op_like,        {}, 0.4),  # 40% 概率
    ("下滑",        op_swipe_down,  {}, 1.0),
    ("观看",        op_watch,       {}, 1.0),
    ("点赞",        op_like,        {}, 0.3),
    ("下滑",        op_swipe_down,  {}, 1.0),
    ("观看",        op_watch,       {}, 1.0),
    ("评论",        op_comment,     {'text':'好内容，已三连'}, 0.5),  # 50% 概率评论
    ("下滑",        op_swipe_down,  {}, 1.0),
    ("观看",        op_watch,       {}, 1.0),
    ("点赞",        op_like,        {}, 0.3),
    ("评论",        op_comment,     {'text':'涨知识了'}, 0.5),
]

# ═══════════════════════════════════════════════
# 执行引擎
# ═══════════════════════════════════════════════

async def run_blueprint(page, blueprint):
    state = 'HOME'
    log(f'执行蓝图 ({len(blueprint)}步)')
    for i, (name, fn, kwargs, prob) in enumerate(blueprint):
        if random.random() > prob:
            log(f'  [{i+1}] {name} → 跳过(概率{prob})')
            continue
        log(f'  [{i+1}] {name}...')
        try:
            state = await fn(page, **kwargs)
        except Exception as e:
            log(f'  ⚠️ {name}异常: {str(e)[:30]}')
            state = await read_state(page)
            state = 'PLAYER' if state.get('vc',0)>=2 else 'HOME'
        log(f'    → {state}')
        await asyncio.sleep(random.uniform(0.5,1.5))
    log(f'蓝图完成，最终状态: {state}')

# ═══════════════════════════════════════════════
# 启动
# ═══════════════════════════════════════════════

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect(); p = conn.page; await conn.init_anti_detection()

    await op_goto_home(p)
    log('🏠 首页就绪')

    await run_blueprint(p, BLUEPRINT_NURTURE)

    log('\n✅ 完成，浏览器保持打开')
    while True: await asyncio.sleep(10)

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: log('👋')
    except Exception as e: import traceback; traceback.print_exc()

#!/usr/bin/env python3
"""
矩阵养号 - 多账号主页信息采集器 v2.2

策略:
  - 顺序执行，一次一个身份
  - 每台浏览器: 抖音首页取信息 → 小红书首页/个人页取信息 → 关闭
  - 关键改进: 用 DOM 精准提取，不用 URL 跳转

用法:
  python collect_homepage_info.py [--single PHONE]

输出: ~/agent-local/tools/matrix/data/homepage_info.json
"""

import asyncio, json, re, sys, traceback
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

AGENT_LOCAL = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix"
CONFIG_FILE = AGENT_LOCAL / "config" / "accounts.yaml"
IDENTITIES_ROOT = AGENT_LOCAL / "identities"
OUTPUT_FILE = AGENT_LOCAL / "data" / "homepage_info.json"
SCREENSHOTS_DIR = AGENT_LOCAL / "screenshots" / "homepage"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
from cdp_connector import CDPConnector

DOUYIN_URL = "https://www.douyin.com/"
XHS_URL = "https://www.xiaohongshu.com/explore"

def load_accounts():
    import yaml
    with open(CONFIG_FILE) as f:
        data = yaml.safe_load(f)
    return [a for a in data.get("accounts", []) if a.get("enabled", True)]

def group_by_identity(accounts):
    groups = {}
    for acct in accounts:
        identity = acct.get("identity_dir", acct["id"])
        if identity not in groups:
            groups[identity] = {"identity_dir": identity,
                "display_name": acct.get("display_name", identity),
                "phone": acct.get("phone", ""), "accounts": []}
        groups[identity]["accounts"].append(acct)
    for g in groups.values():
        g["accounts"].sort(key=lambda a: 0 if a["platform"]=="douyin" else 1)
    return list(groups.values())

async def safe_goto(page, url, timeout=45000):
    try:
        await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        return True
    except: return False

async def take_screenshot(page, prefix, identity_name):
    """拍截屏"""
    ts = datetime.now().strftime("%H%M%S")
    safe = identity_name.replace("phone_", "")
    path = SCREENSHOTS_DIR / f"{prefix}_{safe}_{ts}.png"
    try:
        await page.screenshot(path=str(path))
        print(f"   📸 {path.name}")
    except: pass

# ── 抖音：主页提取全部信息（不跳转个人页） ──

async def extract_douyin(page, identity_name, phone):
    info = {"platform":"douyin","phone":phone,"status":"pending","url":"",
            "nickname":"","fans":"","following":"","likes":"","posts":"","bio":""}
    try:
        print(f"   📍 抖音首页...")
        ok = await safe_goto(page, DOUYIN_URL)
        if not ok: info["status"]="nav_error"; return info
        await asyncio.sleep(5)
        info["url"] = page.url
        await take_screenshot(page, "dy", identity_name)

        # 1. 深度 DOM 扫描：提取所有可见文本+属性
        dom_data = await page.evaluate("""() => {
            const results = {texts:[], profile:{}, links:[], stats:[]};
            // 所有可见文本
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            let n; while(n=walker.nextNode()){
                const t=n.textContent.trim();
                if(t){let el=n.parentElement; if(el&&el.offsetParent!==null) results.texts.push(t);}
            }
            // 所有链接
            document.querySelectorAll('a').forEach(a=>{
                if(a.href && a.offsetParent!==null) results.links.push({href:a.href,text:a.textContent.trim()});
            });
            // 找统计数字
            document.querySelectorAll('span,div,p,strong').forEach(el=>{
                const t=el.textContent.trim();
                if(/^\\d+[.,\\d]*[万wW]?$/.test(t) && t.length<=12 && el.offsetParent!==null)
                    results.stats.push(t);
            });
            // 找我的信息
            const myInfo = document.querySelector('[class*="user-info"], [class*="profile-info"], [class*="my-info"], [class*="personal"], [class*="header-info"]');
            if(myInfo) results.profile.html = myInfo.innerHTML.slice(0,5000);
            return results;
        }""")

        all_text = "\n".join(dom_data.get("texts", []))
        lines = [l.strip() for l in all_text.split("\n") if l.strip()]

        try: info["_title"] = await page.title()
        except: pass

        # 昵称 — 从 DOM 深度扫描或者文本里找
        # 先看 page.evaluate 的 text 前面部分（通常 nickname 在页面靠前位置）
        nickname = ""
        skip_words = {"精选","推荐","搜索","关注","朋友","我的","直播","放映厅","短剧",
                     "小游戏","抖音","首页","通知","私信","投稿","登录","开启读屏标签",
                     "读屏标签已关闭","未登录","壁纸","更多","热点",
                     "登录后即可观看喜欢、收藏作品","登录后即可查看收藏、点赞"}
        for line in lines[:80]:
            line = line.strip()
            if 1 < len(line) <= 18 and line not in skip_words and \
               not line.startswith("@") and not line.startswith("http") and \
               not re.match(r'^[\d:,.万w]+$', line) and \
               line not in ("全部","公开课","游戏","二次元","音乐","影视","美食",
                           "知识","小剧场","生活vlog","体育","旅行","亲子","动物",
                           "三农","汽车","美妆穿搭"):
                nickname = line
                break

        info["nickname"] = nickname

        # 统计数字 — 从文本和 stats list 里找
        text_for_nums = "\n".join(lines[:200])

        # 按标签找
        for pat, key in [(r'(?:粉丝?)\s*[：:]\s*([\d,.万wW]+)', "fans"),
                         (r'(?:关注)\s*[：:]\s*([\d,.万wW]+)', "following"),
                         (r'(?:获赞|点赞)\s*[：:]\s*([\d,.万wW]+)', "likes"),
                         (r'(?:作品)\s*[：:]\s*([\d,.万wW]+)', "posts")]:
            m = re.search(pat, text_for_nums)
            if m: info[key] = m.group(1)

        # 备用：找 "粉丝 数字" 的模式
        if not info["fans"]:
            m = re.search(r'粉丝\s*(\d+[\.\d]*[万w]?)', text_for_nums)
            if m: info["fans"] = m.group(1)
        if not info["following"]:
            m = re.search(r'关注\s*(\d+[\.\d]*[万w]?)', text_for_nums)
            if m: info["following"] = m.group(1)

        # 最后手段：找数组匹配
        stats = dom_data.get("stats", [])
        links = dom_data.get("links", [])

        info["_raw_len"] = len(lines)
        info["_stats_found"] = stats[:20]
        info["status"] = "loaded"
        print(f"   ✅ 抖音: {info['nickname'] or '?'}  粉丝:{info['fans'] or '?'}  关注:{info.get('following','?')}")
        if not info["fans"] and not info["nickname"]:
            print(f"   ⚠️ 可能未登录或页面结构异常 (lines={len(lines)})")
        return info
    except Exception as e:
        print(f"   ❌ 抖音异常: {e}")
        info["status"]="error"; info["_error"]=str(e)
        return info

# ── 小红书：主页提取 ──

async def extract_xiaohongshu(page, identity_name, phone):
    info = {"platform":"xiaohongshu","phone":phone,"status":"pending","url":"",
            "nickname":"","fans":"","following":"","notes":"","bio":""}
    try:
        print(f"   📍 小红书首页...")
        ok = await safe_goto(page, XHS_URL, timeout=60000)
        if not ok: info["status"]="nav_error"; return info
        # 小红书在 Firefox 中加载极慢，多等一会儿
        await asyncio.sleep(10)
        info["url"] = page.url
        await take_screenshot(page, "xhs", identity_name)

        # 深度 DOM 扫描（首次：探索页，看看有没有已登录用户信息）
        dom_data = await page.evaluate("""() => {
            const results = {texts:[], links:[], stats:[]};
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            let n; while(n=walker.nextNode()){
                const t=n.textContent.trim();
                if(t){let el=n.parentElement; if(el&&el.offsetParent!==null) results.texts.push(t);}
            }
            document.querySelectorAll('a').forEach(a=>{
                if(a.href && a.offsetParent!==null) results.links.push({href:a.href,text:a.textContent.trim()});
            });
            document.querySelectorAll('span,div,p,strong').forEach(el=>{
                const t=el.textContent.trim();
                if(/^\\d+[.,\\d]*[万wW]?$/.test(t) && t.length<=12 && el.offsetParent!==null)
                    results.stats.push(t);
            });
            return results;
        }""")

        texts = dom_data.get("texts", [])
        all_text = "\n".join(texts[:500])

        try: info["_title"] = await page.title()
        except: pass

        # 第1步: 先在探索页提取（已登录时右上角有用户信息）
        skip_words = {"探索","发现","首页","推荐","关注","附近","消息","我","笔记","收藏",
                     "赞过","编辑资料","创作中心","小红书","登录","注册","发布","直播",
                     "打开App","打开小红书","问点点"}
        for line in texts[:80]:
            line = line.strip()
            if 1 < len(line) <= 18 and line not in skip_words and \
               not re.match(r'^[\d,.万w]+$', line) and \
               not line.startswith("@") and not line.startswith("http"):
                info["nickname"] = line
                break

        # 从探索页直接找统计数字
        for pat, key in [(r'(?:粉丝)\s*[：:]?\s*([\d,.万wW]+)', "fans"),
                         (r'(?:关注)\s*[：:]?\s*([\d,.万wW]+)', "following"),
                         (r'(?:笔记|作品)\s*[：:]?\s*([\d,.万wW]+)', "notes")]:
            m = re.search(pat, all_text)
            if m: info[key] = m.group(1)

        # 第2步: 尝试进入个人主页（多种方法）
        if not info["nickname"]:
            print(f"   📍 探索页未找到昵称，尝试进入个人页...")
            for method in range(4):
                try:
                    if method == 0:
                        # 方法0: 点击"我"文字
                        await page.evaluate("""()=>{
                            const els=document.querySelectorAll('a,span,div');
                            for(const e of els){
                                if(e.textContent.trim()==='我'&&e.offsetParent!==null){e.click();return true;}
                            } return false;
                        }""")
                        await asyncio.sleep(6)
                    elif method == 1:
                        # 方法1: 找 user/profile 链接
                        await page.evaluate("""()=>{
                            const a=document.querySelector('a[href*="user/profile"], a[href*="profile"]');
                            if(a){a.click();return true;} return false;
                        }""")
                        await asyncio.sleep(6)
                    elif method == 2:
                        # 方法2: 直接导航到 self profile
                        await page.goto("https://www.xiaohongshu.com/user/profile/self",
                                       timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(8)
                    elif method == 3:
                        # 方法3: 用 edith 域名（移动版）
                        await page.goto("https://edith.xiaohongshu.com/",
                                       timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(8)
                    # 每次尝试后检查是否有效
                    new_url = page.url
                    if "profile" in new_url or "user" in new_url:
                        print(f"   ✅ 进入个人页: {new_url[:60]}")
                        break
                except: pass

        info["url"] = page.url
        await take_screenshot(page, "xhs_me", identity_name)

        # 第3步: 再次深度扫描提取数据
        dom_data2 = await page.evaluate("""() => {
            const results = {texts:[], stats:[]};
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            let n; while(n=walker.nextNode()){
                const t=n.textContent.trim();
                if(t){let el=n.parentElement; if(el&&el.offsetParent!==null) results.texts.push(t);}
            }
            document.querySelectorAll('span,div,p,strong').forEach(el=>{
                const t=el.textContent.trim();
                if(/^\\d+[.,\\d]*[万wW]?$/.test(t) && t.length<=12 && el.offsetParent!==null)
                    results.stats.push(t);
            });
            return results;
        }""")

        lines2 = [l.strip() for l in dom_data2.get("texts", []) if l.strip()]
        stats = dom_data2.get("stats", [])
        text_for_nums = "\n".join(lines2[:400])

        # 如果还没找到昵称，再次扫描
        if not info["nickname"]:
            for line in lines2[:80]:
                line = line.strip()
                if 1 < len(line) <= 18 and line not in skip_words and \
                   not re.match(r'^[\d,.万w]+$', line) and \
                   not line.startswith("@") and not line.startswith("http"):
                    info["nickname"] = line
                    break

        # 找粉丝/关注/笔记数
        for pat, key in [(r'(?:粉丝)\s*[：:]?\s*([\d,.万wW]+)', "fans"),
                         (r'(?:关注)\s*[：:]?\s*([\d,.万wW]+)', "following"),
                         (r'(?:笔记|作品)\s*[：:]?\s*([\d,.万wW]+)', "notes")]:
            m = re.search(pat, text_for_nums)
            if m: info[key] = m.group(1)

        # 兜底: 用 stats 数组
        if not info["fans"] and stats:
            small = [s for s in stats if 1 <= int(''.join(c for c in s if c.isdigit() or c=='.').split('.')[0]) <= 99999]
            if len(small) >= 2:
                info["following"] = small[0]
                info["fans"] = small[1]

        info["_raw_len"] = len(lines2)
        info["status"] = "loaded"
        print(f"   ✅ 小红书: {info['nickname'] or '?'}  粉丝:{info['fans'] or '?'}  关注:{info.get('following','?')}")
        if not info["fans"] and not info["nickname"]:
            print(f"   ⚠️ 可能未登录 (lines={len(lines2)}, url={page.url[:60]})")
        return info
    except Exception as e:
        print(f"   ❌ 小红书异常: {e}")
        import traceback; traceback.print_exc()
        info["status"]="error"; info["_error"]=str(e)
        return info

# ── 单身份流程 ──

async def process_identity(group):
    idir, name, phone = group["identity_dir"], group["display_name"], group["phone"]
    accounts = group["accounts"]
    print(f"\n{'='*55}\n 🔄 [{name}] ({phone})\n{'='*55}")
    result = {"identity_dir":idir,"display_name":name,"phone":phone,"douyin":None,"xiaohongshu":None}

    conn = None
    try:
        conn = CDPConnector(identity_dir=str(IDENTITIES_ROOT/idir), headless=False,
                           window=(802,783), locale=["zh-CN"])
        print(f" 🦊 启动 Camoufox...")
        await conn.connect()
        print(f" ✅ 浏览器就绪: {conn.page.url}")
        try: await conn.page.set_viewport_size({"width":802,"height":783})
        except: pass

        if any(a["platform"]=="douyin" for a in accounts):
            print(f"\n {'─'*40}\n 🎵 抖音...")
            result["douyin"] = await extract_douyin(conn.page, idir, phone)

        if any(a["platform"]=="xiaohongshu" for a in accounts):
            print(f"\n {'─'*40}\n 📕 小红书...")
            result["xiaohongshu"] = await extract_xiaohongshu(conn.page, idir, phone)

        print(f" ✅ {name} 完成")
    except Exception as e:
        print(f" ❌ 严重: {e}"); traceback.print_exc()
        result["_error"]=str(e)
    finally:
        if conn:
            try: await conn.close()
            except: pass
            # 兜底：杀 Firefox 进程
            import subprocess
            try:
                subprocess.run(["pkill","-f","firefox"],capture_output=True,timeout=5)
            except: pass
            await asyncio.sleep(2)
            print(f" 🚫 浏览器关闭")
    return result

# ── 主函数 ──

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", help="只处理单个身份 (phone)")
    args = parser.parse_args()

    print(f"\n{'='*60}\n 📊 矩阵养号 - 主页信息采集器 v2.2\n{'='*60}")
    accounts = load_accounts()
    groups = group_by_identity(accounts)

    if args.single:
        groups = [g for g in groups if args.single in g["phone"] or args.single in g["identity_dir"]]
        if not groups: print(f" ❌ 未找到: {args.single}"); return

    print(f"\n 📋 {len(accounts)} 账号, {len(groups)} 身份")
    for g in groups:
        plats = ", ".join(a["platform"] for a in g["accounts"])
        print(f"   - {g['display_name']} ({g['phone']}): {plats}")

    all_results = []
    for idx, g in enumerate(groups, 1):
        print(f"\n\n{'#'*60}\n # [{idx}/{len(groups)}] {g['display_name']}\n{'#'*60}")
        try:
            result = await process_identity(g)
        except Exception as e:
            print(f" ❌ 严重: {e}"); traceback.print_exc()
            result = {"identity_dir":g["identity_dir"],"display_name":g["display_name"],
                     "phone":g["phone"],"douyin":None,"xiaohongshu":None,"_error":str(e)}
        all_results.append(result)

        output = {"collected_at":datetime.now().isoformat(),"total_identities":len(groups),
                 "total_accounts":len(accounts),"results":all_results}
        with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
            json.dump(output,f,ensure_ascii=False,indent=2)
        print(f" 💾 已保存 ({idx}/{len(groups)})")

    print(f"\n\n{'='*60}\n 📊 全部完成！\n{'='*60}")
    for r in all_results:
        print(f"\n {'─'*45}\n 📱 {r['display_name']} ({r['phone']})")
        for k,label in [("douyin","🎵 抖音"),("xiaohongshu","📕 小红书")]:
            d = r.get(k)
            if d:
                s = "✅" if d["status"]=="loaded" else "⚠️"
                print(f"   {s} {label}: {d.get('nickname','?')}  粉丝:{d.get('fans','?')}  关注:{d.get('following','?')}")
    print(f"\n ✅ 结果: {OUTPUT_FILE}\n 📸 截屏: {SCREENSHOTS_DIR}\n")

if __name__ == "__main__":
    asyncio.run(main())

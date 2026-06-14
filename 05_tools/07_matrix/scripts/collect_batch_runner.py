#!/usr/bin/env python3
"""
批量主页信息采集器 — 分批并行版 (v1.2)

采集规则（所有机器通用）:
  1. 按身份分组，每批最多 3 个身份
  2. 同一批内，每个身份间隔 15 秒启动浏览器（避免同时开 3 个导致卡顿）
  3. 同一个身份的两个平台（抖音+小红书）共用同一浏览器，只换网址
  4. 一个身份采集完 → 关闭浏览器 → 再进行下一个
  5. 一批全部完成后才启动下一批

用法:
  python collect_batch_runner.py

输出:
  data/collect_progress.json  (实时进度)
  data/homepage_info.json     (最终结果, 含 collected_at 时间戳)
"""

import asyncio, json, re, sys, time, traceback
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

AGENT_LOCAL = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix"
CONFIG_FILE = AGENT_LOCAL / "config" / "accounts.yaml"
IDENTITIES_ROOT = AGENT_LOCAL / "identities"
PROGRESS_FILE = AGENT_LOCAL / "data" / "collect_progress.json"
OUTPUT_FILE = AGENT_LOCAL / "data" / "homepage_info.json"
SCREENSHOTS_DIR = AGENT_LOCAL / "screenshots" / "homepage"
HISTORY_DIR = AGENT_LOCAL / "data" / "homepage" / "history"
TIMELINE_FILE = HISTORY_DIR / "timeline.json"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

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

async def read_text(page):
    try:
        return await page.evaluate("""()=>{
            const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null,false);
            let t=[];let n;
            while(n=w.nextNode()){let s=n.textContent.trim();if(s){let el=n.parentElement;if(el&&el.offsetParent!==null)t.push(s)}}
            return t.slice(0,800).join('\\n');
        }""")
    except: return ""

async def safe_goto(page, url, timeout=45000):
    try:
        await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        return True
    except: return False

async def take_screenshot(page, prefix, identity_name):
    ts = datetime.now().strftime("%H%M%S")
    safe = identity_name.replace("phone_","")
    try:
        await page.screenshot(path=str(SCREENSHOTS_DIR/f"{prefix}_{safe}_{ts}.png"))
    except: pass

async def extract_douyin(page, identity_name, phone):
    info = {"platform":"douyin","phone":phone,"status":"pending","url":"",
            "nickname":"","fans":"","following":"","likes":"","posts":"","bio":""}
    try:
        print(f"     📍 抖音...")
        ok = await safe_goto(page, DOUYIN_URL)
        if not ok: info["status"]="nav_error"; return info
        await asyncio.sleep(6)  # 多等一会儿让统计数字渲染
        info["url"] = page.url
        await take_screenshot(page, "dy", identity_name)
        body_text = await read_text(page)
        if not body_text: info["status"]="no_text"; return info
        lines = [l.strip() for l in body_text.split("\n") if l.strip()]
        all_text = "\n".join(lines[:300])
        try: info["_title"] = await page.title()
        except: pass
        skip_words = {"精选","推荐","搜索","关注","朋友","我的","直播","放映厅","短剧",
                     "小游戏","抖音","首页","通知","私信","投稿","登录","开启读屏标签",
                     "读屏标签已关闭","未登录","壁纸","更多","热点"}
        for line in lines[:50]:
            line = line.strip()
            if 1 < len(line) <= 18 and line not in skip_words and \
               not line.startswith("@") and not line.startswith("http") and \
               not re.match(r'^[\d:,.万w]+$', line):
                info["nickname"] = line; break
        for pat, key in [(r'(?:粉丝?)\s*[：:]\s*([\d,.万wW]+)',"fans"),
                         (r'(?:关注)\s*[：:]\s*([\d,.万wW]+)',"following")]:
            m = re.search(pat, all_text)
            if m: info[key] = m.group(1)
        # 兜底: 找 "粉丝 数字" 或 "关注 数字" (中间没冒号)
        if not info["fans"]:
            m = re.search(r'粉丝\s*(\d+[\.\d]*[万w]?)', all_text)
            if m: info["fans"] = m.group(1)
        if not info["following"]:
            m = re.search(r'关注\s*(\d+[\.\d]*[万w]?)', all_text)
            if m: info["following"] = m.group(1)
        # 再兜底: 从 _stats_found 里找合理的数字 (靠近文本前面的小数字通常是用户统计)
        if not info["fans"] and not info["following"]:
            stats = re.findall(r'\b(\d+)\b', all_text[:1500])
            # 找排除视频播放量(万级)后的小数字
            small_nums = [s for s in stats if 1 <= int(s) <= 99999]
            if len(small_nums) >= 2:
                # 通常关注数在前,粉丝数在后
                info["following"] = small_nums[0]
                info["fans"] = small_nums[1]
        info["status"] = "loaded"
        log = f"     ✅ 抖音: {info['nickname'] or '?'}  粉丝:{info['fans'] or '?'}  关注:{info.get('following','?')}"
        print(log)
        return info
    except Exception as e:
        print(f"     ❌ 抖音异常: {e}")
        info["status"]="error"; info["_error"]=str(e)
        return info

async def extract_xiaohongshu(page, identity_name, phone):
    info = {"platform":"xiaohongshu","phone":phone,"status":"pending","url":"",
            "nickname":"","fans":"","following":"","notes":"","bio":""}
    try:
        print(f"     📍 小红书...")
        ok = await safe_goto(page, XHS_URL, timeout=45000)
        if not ok: info["status"]="nav_error"; return info
        await asyncio.sleep(4)
        info["url"] = page.url
        await take_screenshot(page, "xhs", identity_name)
        for method in range(3):
            try:
                if method == 0:
                    await page.evaluate("""()=>{
                        const els=document.querySelectorAll('a,span,div');
                        for(const e of els){
                            if(e.textContent.trim()==='我'&&e.offsetParent!==null){e.click();return true;}
                        } return false;
                    }""")
                    await asyncio.sleep(4)
                elif method == 1:
                    await page.evaluate("""()=>{
                        const a=document.querySelector('a[href*="user/profile"],a[href*="profile"]');
                        if(a){a.click();return true;}
                        return false;
                    }""")
                    await asyncio.sleep(4)
                elif method == 2:
                    await page.goto("https://www.xiaohongshu.com/user/profile/self", timeout=15000, wait_until="domcontentloaded")
                    await asyncio.sleep(4)
                break
            except: pass
        info["url"] = page.url
        body_text = await read_text(page)
        if not body_text: info["status"]="no_text"; return info
        lines = [l.strip() for l in body_text.split("\n") if l.strip()]
        text_for_nums = "\n".join(lines[:400])
        skip_words = {"探索","发现","首页","推荐","关注","附近","消息","我","笔记","收藏",
                     "赞过","编辑资料","创作中心","小红书","登录","注册","发布","直播"}
        for line in lines[:80]:
            line = line.strip()
            if 1 < len(line) <= 18 and line not in skip_words and \
               not re.match(r'^[\d,.万w]+$', line) and \
               not line.startswith("@") and not line.startswith("http"):
                info["nickname"] = line; break
        for pat, key in [(r'(?:粉丝)\s*[：:]?\s*([\d,.万wW]+)',"fans"),
                         (r'(?:关注)\s*[：:]?\s*([\d,.万wW]+)',"following"),
                         (r'(?:笔记|作品)\s*[：:]?\s*([\d,.万wW]+)',"notes")]:
            m = re.search(pat, text_for_nums)
            if m: info[key] = m.group(1)
        info["status"] = "loaded"
        print(f"     ✅ 小红书: {info['nickname'] or '?'}  粉丝:{info['fans'] or '?'}  关注:{info.get('following','?')}")
        return info
    except Exception as e:
        print(f"     ❌ 小红书异常: {e}")
        info["status"]="error"; info["_error"]=str(e)
        return info

async def process_identity(group, progress_data, window_index=0):
    """处理一个身份的所有账号（先抖音后小红书，共用同一浏览器）
    
    Args:
        group: 身份分组数据
        progress_data: 进度数据（未使用，保留兼容）
        window_index: 在同一批次中的序号，用于错开窗口位置 (0,1,2)
    """
    idir, name, phone = group["identity_dir"], group["display_name"], group["phone"]
    accounts = group["accounts"]
    result = {"identity_dir":idir,"display_name":name,"phone":phone,"douyin":None,"xiaohongshu":None}
    
    # 窗口位置 X 轴错开 150px，避免左右遮挡
    win_w, win_h = 802, 783
    win_x = 150 * window_index
    win_y = 30
    
    print(f"\n   🔄 [{name}] ({phone})...")
    print(f"   🪟 窗口位置: ({win_x}, {win_y}) 尺寸: {win_w}×{win_h}")
    conn = None
    try:
        conn = CDPConnector(identity_dir=str(IDENTITIES_ROOT/idir), headless=False,
                           window=(win_w, win_h), locale=["zh-CN"],
                           window_position=(win_x, win_y))
        try: await conn.page.set_viewport_size({"width":802,"height":783})
        except: pass
        if any(a["platform"]=="douyin" for a in accounts):
            result["douyin"] = await extract_douyin(conn.page, idir, phone)
        if any(a["platform"]=="xiaohongshu" for a in accounts):
            result["xiaohongshu"] = await extract_xiaohongshu(conn.page, idir, phone)
        print(f"   ✅ {name} 完成")
    except Exception as e:
        print(f"   ❌ {name} 异常: {e}")
        result["_error"]=str(e)
    finally:
        if conn:
            try: await conn.close()
            except: pass
            import subprocess
            try: subprocess.run(["pkill","-f","firefox"],capture_output=True,timeout=5)
            except: pass
            await asyncio.sleep(1)
    return result

def write_progress(progress):
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    except: pass

async def main():
    print(f"\n{'='*60}")
    print(f" 📊 批量主页信息采集器 (分批并行 v1.0)")
    print(f" {'='*60}")

    accounts = load_accounts()
    groups = group_by_identity(accounts)
    BATCH_SIZE = 3
    total = len(groups)
    batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    print(f" 📋 {len(accounts)} 账号, {total} 身份, {batches} 批次(每批最多{BATCH_SIZE})")
    for g in groups:
        plats = ", ".join(a["platform"] for a in g["accounts"])
        print(f"   - {g['display_name']} ({g['phone']}): {plats}")

    # 初始化进度
    progress = {
        "started_at": datetime.now().isoformat(),
        "total_identities": total,
        "completed": 0,
        "success": 0,
        "failed": 0,
        "current_batch": 0,
        "total_batches": batches,
        "status": "running",
        "results": [],
    }
    write_progress(progress)

    all_results = []

    for batch_idx in range(0, total, BATCH_SIZE):
        batch = groups[batch_idx:batch_idx + BATCH_SIZE]
        batch_num = batch_idx // BATCH_SIZE + 1
        print(f"\n\n{'#'*55}")
        print(f" # 批次 {batch_num}/{batches} ({len(batch)} 个身份)")
        print(f" {'#'*55}")

        progress["current_batch"] = batch_num
        write_progress(progress)

        # ══════════════════════════════════════════════════════
        # 分批启动：每批内身份间隔 15s 启动，避免同时开浏览器导致卡顿
        # 同身份内两个平台共用同一浏览器（先抖音后小红书，只换网址）
        # ══════════════════════════════════════════════════════
        batch_results = [None] * len(batch)

        async def launch_with_stagger(idx, g):
            """每个身份延迟 idx*15 秒后启动，窗口位置按 idx 错开"""
            if idx > 0:
                await asyncio.sleep(15 * idx)
            result = await process_identity(g, progress, window_index=idx)
            batch_results[idx] = result
            # 每完成一个就写一次进度
            done = sum(1 for r in batch_results if r is not None)
            progress["results"] = [r for r in batch_results if r is not None]
            progress["completed"] = done
            progress["success"] = sum(1 for r in batch_results if r and
                ((r.get("douyin") and r["douyin"]["status"]=="loaded" and r["douyin"].get("nickname") and not "登录后" in r["douyin"]["nickname"])
                or (r.get("xiaohongshu") and r["xiaohongshu"]["status"]=="loaded" and r["xiaohongshu"].get("nickname") and not "问点点" in r["xiaohongshu"]["nickname"] and not "推荐" in r["xiaohongshu"]["nickname"])))
            progress["failed"] = done - progress["success"]
            write_progress(progress)
            print(f" 📊 批次进度: {done}/{len(batch)} 完成 (成功{progress['success']}, 失败{progress['failed']})")

        # 使用 asyncio.gather 同时启动所有带延迟的任务
        # 每个任务在 launch_with_stagger 内部等待 idx*15s，不会同时启动
        tasks = [launch_with_stagger(i, g) for i, g in enumerate(batch)]
        await asyncio.gather(*tasks)

        all_results.extend(batch_results)
        print(f"\n 📊 批次完成: 累计 {len(all_results)}/{total}")

    # 先写输出文件（保证前端轮询到 completed 时数据已就绪）
    output = {
        "collected_at": datetime.now().isoformat(),
        "total_identities": total,
        "total_accounts": len(accounts),
        "results": all_results,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # ── 归档历史快照 ──
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    snapshot_file = HISTORY_DIR / f"homepage_info_{ts}.json"
    try:
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        # 追加到时间线
        timeline_entry = {
            "snapshot": f"homepage_info_{ts}.json",
            "collected_at": now.isoformat(),
            "total_identities": total,
            "total_accounts": len(accounts),
            "success": progress["success"],
            "failed": progress["failed"],
        }
        timeline = []
        if TIMELINE_FILE.exists():
            try:
                timeline = json.loads(TIMELINE_FILE.read_text())
            except: pass
        timeline.append(timeline_entry)
        # 最多保留 200 条
        if len(timeline) > 200:
            timeline = timeline[-200:]
        with open(TIMELINE_FILE, "w", encoding="utf-8") as f:
            json.dump(timeline, f, ensure_ascii=False, indent=2)
        print(f" 📜 历史: {snapshot_file}")
    except Exception as e:
        print(f" ⚠️ 历史归档失败: {e}")

    # 再标记完成（避免 race condition：前端看到 completed 但文件还没写好）
    progress["status"] = "completed"
    progress["finished_at"] = datetime.now().isoformat()
    write_progress(progress)

    # 汇总
    print(f"\n\n{'='*60}")
    print(f" 📊 全部完成!")
    print(f" {'='*60}")
    print(f" ✅ 成功: {progress['success']}")
    print(f" ❌ 失败: {progress['failed']}")
    for r in all_results:
        dy = r.get("douyin")
        xhs = r.get("xiaohongshu")
        dy_ok = dy and dy["status"]=="loaded" and dy.get("nickname") and "登录后" not in dy["nickname"]
        xhs_ok = xhs and xhs["status"]=="loaded" and xhs.get("nickname") and "问点点" not in xhs["nickname"] and "推荐" not in xhs["nickname"]
        s = "✅" if dy_ok or xhs_ok else "❌"
        print(f"   {s} {r['display_name']}: 抖音{'✅' if dy_ok else '❌'} 小红书{'✅' if xhs_ok else '❌'}")
    print(f"\n ✅ 结果: {OUTPUT_FILE}")
    print(f" 📸 截屏: {SCREENSHOTS_DIR}\n")

if __name__ == "__main__":
    asyncio.run(main())

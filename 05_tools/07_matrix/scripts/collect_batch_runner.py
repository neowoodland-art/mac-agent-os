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

AGENT_LOCAL = None  # will be set by init_paths()

def init_paths():
    global AGENT_LOCAL, CONFIG_FILE, IDENTITIES_ROOT, PROGRESS_FILE, OUTPUT_FILE, SCREENSHOTS_DIR, HISTORY_DIR, TIMELINE_FILE
    try:
        from matrix_mgmt import AGENT_LOCAL as _AL, MATRIX_LOCAL
        AGENT_LOCAL = _AL / "tools" / "matrix"
    except ImportError:
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

init_paths()

from cdp_connector import CDPConnector

# 导入已验证的提取函数（来自 collect_homepage_info.py 成功方案）
from collect_homepage_info import extract_douyin, extract_xiaohongshu

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
    ts = datetime.now().strftime("%H%M%S")
    safe = identity_name.replace("phone_","")
    try:
        await page.screenshot(path=str(SCREENSHOTS_DIR/f"{prefix}_{safe}_{ts}.png"))
    except: pass


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
        await conn.connect()
        if conn.page:
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

    # 支持 --phone 只采集单个身份
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--phone", default="", help="只采集指定手机号的身份")
    parser.add_argument("--account", default="", help="只采集指定账号ID")
    args, _ = parser.parse_known_args()

    accounts = load_accounts()
    groups = group_by_identity(accounts)

    # 过滤：只保留指定 phone 或 account
    if args.phone:
        groups = [g for g in groups if g["phone"] == args.phone]
    elif args.account:
        groups = [g for g in groups if any(a["id"] == args.account for a in g["accounts"])]

    if not groups:
        print(" ⚠️ 没有匹配的身份，跳过")
        return

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
    # 保留旧数据：如果某个平台新数据为空，保留旧值
    old_data = {}
    if OUTPUT_FILE.exists():
        try: old_data = json.loads(OUTPUT_FILE.read_text())
        except: pass
    old_results = {r.get("phone",""): r for r in old_data.get("results", [])}

    for r in all_results:
        phone = r.get("phone", "")
        old = old_results.get(phone, {})
        for plat in ["douyin", "xiaohongshu"]:
            new_plat = r.get(plat) or {}
            # 如果新数据为空（无昵称），且旧数据有值，保留旧的
            if not new_plat.get("nickname"):
                old_plat = old.get(plat) or {}
                if old_plat.get("nickname"):
                    r[plat] = old_plat
                    print(f"   ↩️ 保留旧数据: {phone} {plat} = {old_plat['nickname']}")

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
    # 文件名加上成功数，方便辨认
    suc = progress.get("success", 0)
    snapshot_file = HISTORY_DIR / f"homepage_{ts}_ok{suc}({total}).json"
    try:
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        # 追加到时间线
        timeline_entry = {
            "snapshot": f"homepage_{ts}_ok{suc}({total}).json",
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

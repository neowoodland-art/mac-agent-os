#!/usr/bin/env python3
"""
日常养号调度器 v1.0

规则:
  1. 最多 3 个浏览器并行，每个间隔 15 秒启动
  2. 步骤顺序每次随机打乱
  3. 每身份每平台约运行 10 分钟
  4. 身份完成后休息 30 秒
  5. 动作池: 浏览/搜索/点赞/收藏/评论/关注

用法:
  python nurture_daily.py                     # 所有身份按规则开始养号
  python nurture_daily.py --dry-run           # 只看计划，不执行
  python nurture_daily.py --phone 185xxx      # 只养指定手机号
"""

import argparse, asyncio, json, random, subprocess, sys, time
from datetime import datetime
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = TOOL_DIR / "scripts"
BP_DIR = TOOL_DIR / "blueprints"
LOCAL_ROOT = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix"
CONFIG_DIR = LOCAL_ROOT / "config"
sys.path.insert(0, str(SCRIPTS_DIR))

# ── 配置 ──
MAX_BROWSERS = 3          # 最大并发浏览器
STAGGER_SECS = 15         # 启动间隔
SESSION_MINS = 10         # 每身份每平台预计分钟
REST_SECS = 30            # 身份间休息
WATCH_MIN = 6             # 浏览最小时长(秒)
WATCH_MAX = 25            # 浏览最大时长(秒)
GAUSS_JITTER = 0.3        # 高斯抖动系数

# ── 搜索关键词池（每次随机选） ──
KEYWORDS_DOUYIN = [
    "美食推荐", "旅行日记", "搞笑视频", "电影解说", "宠物日常",
    "穿搭分享", "美妆教程", "健身打卡", "音乐现场", "游戏解说",
    "科技数码", "汽车评测", "家居装修", "户外运动", "亲子日常",
    "职场干货", "学习技巧", "手工制作", "摄影教程", "美食探店",
]

KEYWORDS_XHS = [
    "穿搭推荐", "美妆教程", "旅行攻略", "美食打卡", "家居好物",
    "护肤心得", "读书笔记", "运动打卡", "育儿经验", "摄影技巧",
]


def gaussian_sleep(base):
    """base 秒 ±30% 高斯抖动"""
    delay = base * (1 + random.uniform(-GAUSS_JITTER, GAUSS_JITTER))
    return max(2, delay)


def load_accounts():
    import yaml
    with open(CONFIG_DIR / "accounts.yaml") as f:
        data = yaml.safe_load(f)
    return [a for a in data.get("accounts", []) if a.get("enabled", True)]


def load_blueprints():
    """加载所有蓝图"""
    bps = {}
    for f in sorted(BP_DIR.glob("*.json")):
        try:
            bp = json.loads(f.read_text())
            name = bp.get("name", bp.get("id", f.stem))
            platform = bp.get("platform", bp.get("type", "douyin"))
            steps = bp.get("steps", [])
            if steps:
                bps[name] = {"name": name, "platform": platform, "steps": steps}
        except: pass
    return bps


def group_by_identity(accounts):
    """按手机号分组"""
    groups = {}
    for a in accounts:
        phone = a.get("phone", "")
        if not phone:
            continue
        if phone not in groups:
            groups[phone] = {
                "phone": phone,
                "display_name": a.get("display_name", phone),
                "accounts": [],
            }
        groups[phone]["accounts"].append(a)
    return list(groups.values())


def shuffle_steps(steps, platform="douyin"):
    """随机打乱步骤顺序 + 关键词替换 + 时间抖动"""
    shuffled = steps.copy()
    random.shuffle(shuffled)

    # 替换 @keyword 和 @corpus
    keywords = KEYWORDS_DOUYIN if platform == "douyin" else KEYWORDS_XHS
    for s in shuffled:
        args = s.get("args", {})
        for k, v in args.items():
            if isinstance(v, str) and "@keyword" in v:
                args[k] = random.choice(keywords)
            elif isinstance(v, str) and "@corpus" in v:
                # 评论语料
                texts = [
                    "这个太棒了！", "学到了学到了", "收藏了～",
                    "好厉害！", "这是什么神仙", "太实用了吧",
                    "爱了爱了", "求教程！", "这个真的绝",
                    "已收藏慢慢看", "讲得太清楚了", "干货满满",
                ]
                args[k] = random.choice(texts)

        # 等待时长加抖动
        if "seconds" in args and args["seconds"] and isinstance(args["seconds"], (int, float)):
            args["seconds"] = round(gaussian_sleep(args["seconds"]), 1)

    # 控制步数在 15-30 步之间（保证约10分钟）
    target_steps = random.randint(15, 30)
    if len(shuffled) > target_steps:
        shuffled = shuffled[:target_steps]

    return shuffled


def pick_blueprint(blueprints, platform):
    """为平台选一个合适的蓝图"""
    candidates = [b for b in blueprints.values() if b["platform"] == platform]
    if not candidates:
        candidates = [b for b in blueprints.values()]  # 不限平台
    if not candidates:
        return None
    return random.choice(candidates)


def build_nurture_command(phone, display_name, account, blueprint_name, rounds=1):
    """构建养号命令"""
    runner = SCRIPTS_DIR / "yanghao_runner.py"
    return [
        sys.executable, str(runner),
        "--account", account["id"],
        "--blueprint", blueprint_name,
        "--rounds", str(rounds),
    ]


async def run_nurture_session(identity, blueprints, session_id):
    """运行一个身份的养号"""
    phone = identity["phone"]
    name = identity["display_name"]
    accounts = identity["accounts"]
    results = []

    print(f"\n{'='*55}")
    print(f" 📱 [{name}]({phone}) 开始养号")
    print(f" {'='*55}")

    for acct in accounts:
        platform = acct.get("platform", "douyin")
        bp = pick_blueprint(blueprints, platform)
        if not bp:
            print(f"   ⚠️ {platform} 无可用蓝图，跳过")
            continue

        # 选蓝图并随机打乱步骤
        shuffled = shuffle_steps(bp["steps"], platform)
        bp_name = bp["name"]

        # 预估时长
        est_secs = len(shuffled) * 20 + 30  # 每步~20s + 缓冲
        est_min = round(est_secs / 60, 1)

        print(f"   🎯 {acct['id']} ({platform})")
        print(f"      蓝图: {bp_name} → 打乱后 {len(shuffled)} 步")
        print(f"      预计: ~{est_min}分钟")

        results.append({
            "account": acct["id"],
            "platform": platform,
            "blueprint": bp_name,
            "steps": len(shuffled),
            "estimated_min": est_min,
        })

        # 实际执行（通过 yanghao_runner）
        cmd = build_nurture_command(phone, name, acct, bp_name, rounds=random.randint(1, 3))
        print(f"      执行: {' '.join(cmd[:6])}...")
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            results[-1]["returncode"] = p.returncode
            results[-1]["stdout_len"] = len(p.stdout)
        except subprocess.TimeoutExpired:
            print(f"       ⏰ {acct['id']} 超时")
            results[-1]["returncode"] = -1
        except Exception as e:
            print(f"       ❌ {e}")
            results[-1]["error"] = str(e)

    return results


async def main():
    parser = argparse.ArgumentParser(description="日常养号调度器")
    parser.add_argument("--dry-run", action="store_true", help="只看计划，不执行")
    parser.add_argument("--phone", default="", help="只养指定手机号")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f" 📊 日常养号调度器 v1.0")
    print(f" {'='*60}")
    print(f" 规则:")
    print(f"   - 最多 {MAX_BROWSERS} 个浏览器并行")
    print(f"   - 每个间隔 {STAGGER_SECS} 秒启动")
    print(f"   - 步骤顺序随机打乱")
    print(f"   - 每身份约 {SESSION_MINS} 分钟")
    if args.dry_run:
        print(f"   - 🔍 仅查看计划 (--dry-run)")

    accounts = load_accounts()
    blueprints = load_blueprints()
    groups = group_by_identity(accounts)

    if args.phone:
        groups = [g for g in groups if g["phone"] == args.phone]

    print(f"\n 📋 账号: {len(accounts)} | 蓝图: {len(blueprints)} | 身份: {len(groups)}")

    if not groups:
        print(" ❌ 没有匹配的身份")
        return

    # 排期表
    print(f"\n{'='*60}")
    print(f" 📅 排期表")
    print(f" {'='*60}")

    total_est_min = 0
    for i, g in enumerate(groups):
        batch = i // MAX_BROWSERS + 1
        pos = i % MAX_BROWSERS
        start_delay = pos * STAGGER_SECS + (batch - 1) * (SESSION_MINS * 60 + REST_SECS * MAX_BROWSERS)
        start_min = round(start_delay / 60, 1)

        plats = ", ".join(a["platform"] for a in g["accounts"])
        bps = []
        for a in g["accounts"]:
            bp = pick_blueprint(blueprints, a["platform"])
            bps.append(bp["name"] if bp else "无蓝图")

        est = SESSION_MINS
        total_est_min += est

        print(f" 批次{batch}#{pos+1} | +{start_min}min | {g['display_name']:16s} | {plats:20s} | ~{est}min")

    total_min = round(total_est_min / MAX_BROWSERS + (len(groups) / MAX_BROWSERS) * 0.5, 1)
    print(f"\n 📊 预估总耗时: ~{total_min} 分钟 ({round(total_min/60,1)} 小时)")
    print(f"    身份数: {len(groups)} | 批次: {(len(groups)+MAX_BROWSERS-1)//MAX_BROWSERS}")

    if args.dry_run:
        print(f"\n 🔍 这是计划预览，加 --dry-run 去掉就是实际执行")
        return

    # 实际执行
    print(f"\n{'='*60}")
    print(f" 🚀 开始执行 ({datetime.now().strftime('%H:%M')})")
    print(f" {'='*60}")

    all_results = []
    batch_num = 0

    for i in range(0, len(groups), MAX_BROWSERS):
        batch = groups[i:i + MAX_BROWSERS]
        batch_num += 1

        print(f"\n--- 批次 {batch_num} ({len(batch)} 个身份) ---")

        # 用 asyncio.gather 错开启动
        async def launch_with_stagger(idx, g):
            if idx > 0:
                await asyncio.sleep(STAGGER_SECS * idx)
            return await run_nurture_session(g, blueprints, f"b{batch_num}p{idx+1}")

        tasks = [launch_with_stagger(idx, g) for idx, g in enumerate(batch)]
        batch_results = await asyncio.gather(*tasks)
        all_results.extend(batch_results)

        # 批次间休息
        if i + MAX_BROWSERS < len(groups):
            print(f"\n ⏸️  批次 {batch_num} 完成，休息 {REST_SECS}s...")
            await asyncio.sleep(REST_SECS)

    # 汇总
    print(f"\n{'='*60}")
    print(f" ✅ 全部完成! ({datetime.now().strftime('%H:%M')})")
    print(f" {'='*60}")
    ok = sum(1 for r in all_results for rr in r if rr.get("returncode") == 0)
    total = sum(len(r) for r in all_results)
    print(f" 成功: {ok}/{total}")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
赛博AI批量采集工具 — 每日定量抽取创作者视频内容

用法:
  python3 batch_douyin_collector.py <sec_uid> [每日数量]

流程:
  1. 通过 OpenCLI 打开创作者主页
  2. 滚动加载视频列表
  3. 逐条打开视频 → 提取文字 → 推送豆包分析
  4. 结果写入 03_knowledge/01_submissions/{hostname}/{creator_name}/
  5. 记录已处理ID, 避免重复

版本: 1.0.0 | 更新: 2026-05-17
"""
import json, os, re, subprocess, sys, time, uuid
from datetime import datetime
from pathlib import Path

# ── 配置 ───────────────────────────────────────────────────
AGENT_SYNC = Path.home() / "workbuddy-agent-os" / "agent-sync"
AGENT_LOCAL = Path.home() / "workbuddy-agent-os" / "agent-local"
OPENCLI = os.path.expanduser("~/.workbuddy/binaries/node/versions/22.12.0/bin/opencli")
HOSTNAME = os.uname().nodename
DAILY_LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 10

# ── 工具函数 ────────────────────────────────────────────────
def oc(args, timeout=15):
    env = {**os.environ, "NODE_OPTIONS": ""}
    for k in ["HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy"]:
        env.pop(k, None)
    try:
        r = subprocess.run([OPENCLI] + args, capture_output=True, text=True, timeout=timeout, env=env)
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except:
        return ""

def get_video_list(sec_uid, max_count=200):
    """从创作者主页获取视频ID列表"""
    url = f"https://www.douyin.com/user/{sec_uid}"
    oc(["browser", "douyin", "open", url], timeout=15)
    time.sleep(6)
    # 滚动加载
    for _ in range(5):
        oc(["browser", "douyin", "scroll", "down"], timeout=5)
        time.sleep(2)
    # 提取视频链接
    raw = oc(["browser", "douyin", "eval",
        f"JSON.stringify(Array.from(document.querySelectorAll('a[href*=\"/video/\"]')).slice(0,{max_count}).map(a=>a.href))"],
        timeout=10)
    try:
        urls = json.loads(raw)
        return list(dict.fromkeys(urls))  # 去重
    except:
        return []

def get_creator_name(sec_uid):
    """获取创作者名称"""
    raw = oc(["browser", "douyin", "eval",
        "document.querySelector('[class*=nickname]')?.textContent?.trim() || ''"], timeout=8)
    return raw.strip() or f"creator_{sec_uid[:8]}"

def extract_video_text(video_url):
    """从单个视频页提取文字"""
    oc(["browser", "douyin", "open", video_url], timeout=12)
    time.sleep(4)
    raw = oc(["browser", "douyin", "eval", "document.body.innerText"], timeout=8)
    if not raw:
        return []
    skip = ["开启读屏","读屏标签","精选","推荐","搜索","关注","朋友","我的","直播",
            "放映厅","下载抖音","京ICP","京公网安","广播电","增值电","网络文化",
            "互联网宗教","药品","互联网新闻","网络谣言","违法和不良","算法推荐",
            "广告投放","用户服务","隐私政策","账号找回","加入我们","营业执照",
            "友情链接","站点地图","抖音电商"]
    useful = [l.strip() for l in raw.split("\n")
              if len(l.strip()) > 5 and not any(k in l for k in skip)]
    return useful

def save_result(creator_name, video_url, text_lines, vid):
    """保存抽取结果到 submissions 目录"""
    today = datetime.now().strftime("%Y%m%d")
    out_dir = AGENT_SYNC / "03_knowledge" / "01_submissions" / HOSTNAME / f"batch_{creator_name}"
    out_dir.mkdir(parents=True, exist_ok=True)
    # 提取标题
    title = "未命名"
    for line in text_lines:
        if len(line) > 10 and not line.startswith("00:") and not line.startswith("20"):
            title = line[:40].replace("/","_").replace('"',"'")
            break
    out_path = out_dir / f"{today}_{vid[:12]}_{title[:20]}.md"
    content = f"# {title}\n> 来源: {video_url}\n> 采集: {datetime.now().isoformat()}\n\n"
    content += "```\n" + "\n".join(text_lines[:40]) + "\n```\n"
    out_path.write_text(content, encoding="utf-8")
    return out_path

def log_processed(vid):
    """记录已处理的视频ID, 避免重复"""
    log_file = AGENT_LOCAL / "runtime" / "batch_collector" / "processed.json"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    processed = []
    if log_file.exists():
        try:
            processed = json.loads(log_file.read_text())
        except:
            pass
    if vid not in processed:
        processed.append(vid)
        log_file.write_text(json.dumps(processed, ensure_ascii=False), encoding="utf-8")

def get_processed():
    """获取已处理ID列表"""
    log_file = AGENT_LOCAL / "runtime" / "batch_collector" / "processed.json"
    if log_file.exists():
        try:
            return set(json.loads(log_file.read_text()))
        except:
            pass
    return set()

# ═══════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════

def main():
    sec_uid = sys.argv[1] if len(sys.argv) > 1 else ""
    if not sec_uid:
        print("用法: python3 batch_douyin_collector.py <sec_uid> [每日数量]")
        print("示例: python3 batch_douyin_collector.py MS4wLjABAAAAiAMOl8TqmkkrRHkrgfOiOHR_KXuJ5lhaw_htNVVVPpc 10")
        sys.exit(1)

    print(f"🚀 批量采集启动 — UID={sec_uid[:20]}... 每日上限={DAILY_LIMIT}")
    processed = get_processed()
    print(f"📋 已处理: {len(processed)} 条")

    # 1. 获取视频列表
    print("📡 获取视频列表...")
    urls = get_video_list(sec_uid)
    print(f"  找到 {len(urls)} 个视频")

    # 2. 获取创作者名称
    creator = get_creator_name(sec_uid)
    print(f"👤 创作者: {creator}")

    # 3. 过滤未处理的
    pending = [u for u in urls if u.split("/")[-1] not in processed]
    print(f"⏳ 待处理: {len(pending)} 条 (今日上限{DAILY_LIMIT})")

    # 4. 逐条处理
    today_count = 0
    for url in pending:
        if today_count >= DAILY_LIMIT:
            print(f"  已达日上限 {DAILY_LIMIT}, 停止")
            break
        vid = url.split("/")[-1].split("?")[0]
        print(f"\n  [{today_count+1}/{min(DAILY_LIMIT, len(pending))}] {vid[:12]}...")
        text = extract_video_text(url)
        if text:
            path = save_result(creator, url, text, vid)
            log_processed(vid)
            today_count += 1
            print(f"    ✅ {len(text)}行 → {path.name}")
        else:
            print(f"    ⚠️ 提取失败")
        time.sleep(2)

    print(f"\n✅ 今日完成: {today_count} 条")
    print(f"📊 累计: {len(processed) + today_count} / {len(urls)}")

if __name__ == "__main__":
    main()

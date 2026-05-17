#!/usr/bin/env python3
"""
袁本初 方案A 采集器 — 使用 doubao_driver.py 的稳定等待法
路径: submissions → inbox → 后续提纯入库
"""
import json, os, re, sys, time, subprocess
from datetime import datetime
from pathlib import Path

AGENT_SYNC = Path.home() / "workbuddy-agent-os" / "agent-sync"
OPENCLI = os.path.expanduser("~/.workbuddy/binaries/node/versions/22.12.0/bin/opencli")
HOSTNAME = os.uname().nodename
OUT_DIR = AGENT_SYNC / "03_knowledge" / "01_submissions" / HOSTNAME / "yuan_benchu"

TODAY = datetime.now().strftime("%Y%m%d")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 已知的视频列表（从搜索结果中获取）
VIDEOS = [
    ("7635155906066952906", "当代中国社会治理第一集: AI与生产关系"),
    ("7625933432249721434", "当代中国社会治理第四集: 法优先or政优先"),
    ("7619535186783795636", "社会治理与政治秩序: 情感劳动概念"),
    ("7640402490651793023", "当代中国社会治理第二集: 就业失业创业"),
]

def oc(args, t=10):
    env = {**os.environ, "NODE_OPTIONS": ""}
    for k in ["HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy"]: env.pop(k,None)
    try:
        return subprocess.run([OPENCLI]+args, capture_output=True, text=True, timeout=t, env=env).stdout.strip()
    except: return ""

def extract_video(url, title):
    vid = url.split("/")[-1].split("?")[0]
    oc(["browser","douyin","open",url], t=12)
    time.sleep(5)
    raw = oc(["browser","douyin","eval","document.body.innerText"], t=10)
    if not raw: return None
    
    skip = ["开启读屏","读屏标签","精选","推荐","搜索","关注","朋友","我的","直播",
            "放映厅","下载抖音","京ICP","京公网安","广播电","增值电","网络文化",
            "互联网宗教","药品","互联网新闻","网络谣言","违法不良","算法推荐",
            "广告投放","用户服务","隐私政策","账号找回","加入我们","营业执照",
            "友情链接","站点地图","抖音电商","2026","2025","请先登录","登录后"]
    useful = [l.strip() for l in raw.split("\n") 
              if len(l.strip())>5 and not any(k in l for k in skip)]
    
    fname = f"{TODAY}_yuan_benchu_{vid[:10]}.md"
    content = f"# {title}\n> 来源: {url}\n> 采集: {datetime.now().isoformat()}\n\n"
    content += "\n".join(useful[:60])
    (OUT_DIR / fname).write_text(content, encoding="utf-8")
    return len(useful)

print(f"🚀 袁本初采集 — 方案A, {len(VIDEOS)}条")
for i, (vid, title) in enumerate(VIDEOS):
    url = f"https://www.douyin.com/video/{vid}"
    print(f"  [{i+1}/{len(VIDEOS)}] {title[:25]}...", end=" ", flush=True)
    n = extract_video(url, title)
    if n:
        print(f"✅ {n}行")
    else:
        print("⚠️ 失败")
    time.sleep(2)
print(f"\n✅ 完成! 存放: {OUT_DIR}")

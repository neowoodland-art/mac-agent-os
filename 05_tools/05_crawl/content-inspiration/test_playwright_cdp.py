#!/usr/bin/env python3
"""基于 Playwright CDP 的第一条采集测试"""
import json, os, re, sys, time
from playwright.sync_api import sync_playwright

SEC_UID = "MS4wLjABAAAAiAMOl8TqmkkrRHkrgfOiOHR_KXuJ5lhaw_htNVVVPpc"
CDP_URL = "http://localhost:9222"

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP_URL)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    
    print("1. 打开创作者主页...")
    page.goto(f"https://www.douyin.com/user/{SEC_UID}", wait_until="domcontentloaded", timeout=30000)
    time.sleep(5)
    
    # 获取创作者名称
    title = page.title()
    print(f"   页面标题: {title}")
    
    # 获取视频列表
    print("2. 获取视频列表...")
    for i in range(3):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
    
    links = page.evaluate("""() => {
        const items = document.querySelectorAll('a[href*="/video/"]');
        return Array.from(new Map(Array.from(items).map(a => [a.href, a.href])).values()).slice(0, 170);
    }""")
    print(f"   找到 {len(links)} 个视频")
    
    if len(links) < 5:
        print("   视频太少，可能是页面未加载完整，等待更多...")
        time.sleep(5)
        links = page.evaluate("""() => {
            const items = document.querySelectorAll('a[href*="/video/"]');
            return Array.from(new Map(Array.from(items).map(a => [a.href, a.href])).values()).slice(0, 170);
        }""")
        print(f"   重试后: {len(links)} 个")
    
    print(f"\n前5个视频:")
    for i, url in enumerate(links[:5]):
        vid = url.split("/")[-1].split("?")[0]
        print(f"  {i+1}. {vid}")

    # 分析第1条视频
    first_url = links[1] if len(links) > 1 else links[0]
    print(f"\n3. 分析第1条视频: {first_url[:60]}...")
    page.goto(first_url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(4)
    
    text = page.evaluate("document.body.innerText")
    
    # 清理
    skip = ["开启读屏","读屏标签","精选","推荐","搜索","关注","朋友","我的",
            "直播","放映厅","下载抖音","京ICP","京公网安","广播电","增值电",
            "网络文化","互联网宗教","药品","互联网新闻","网络谣言","违法和不良",
            "算法推荐","广告投放","用户服务","隐私政策","账号找回","加入我们",
            "营业执照","友情链接","站点地图","抖音电商","2026 ©"]
    useful = [l.strip() for l in text.split("\n")
              if len(l.strip()) > 5 and not any(k in l for k in skip)]
    
    print(f"\n=== 提取结果 ({len(useful)} 行) ===")
    for line in useful[:20]:
        print(f"  {line[:100]}")
    
    print(f"\n... (共 {len(useful)} 行, 显示前20行)")
    
    browser.close()

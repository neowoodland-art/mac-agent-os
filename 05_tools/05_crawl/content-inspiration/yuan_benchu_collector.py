#!/usr/bin/env python3
"""
袁本初 视频批量采集与分类工具
内容方向: 时政 / 哲学 / 社会学 / 政治学
存放位置: 03_knowledge/10_concepts/yuan_benchu/
分类: 政治分析 社会观察 哲学思考 历史解读

用法: python3 yuan_benchu_collector.py [数量]
"""
import os, re, sys, time, json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

SEC_UID = "MS4wLjABAAAAiAMOl8TqmkkrRHkrgfOiOHR_KXuJ5lhaw_htNVVVPpc"
CDP = "http://localhost:9222"
DAILY = int(sys.argv[1]) if len(sys.argv) > 1 else 10

# 路径
AGENT_SYNC = Path.home() / "workbuddy-agent-os" / "agent-sync"
OUT_DIR = AGENT_SYNC / "03_knowledge" / "10_concepts" / "yuan_benchu"
PROCESSED_FILE = Path.home() / "workbuddy-agent-os" / "agent-local" / "runtime" / "batch_collector" / "yuan_benchu_processed.json"

# 分类关键词
CATEGORIES = {
    "政治": ["政治","政策","制度","政府","国家","主权","外交","国际","美国","中国","日本","俄罗斯","欧盟","军事","战争","冲突","制裁","选举","议会"],
    "哲学": ["哲学","思想","认知","逻辑","本质","存在","价值","道德","伦理","理性","自由","平等","正义","权力","真理","意识","思维"],
    "社会": ["社会","文化","文明","阶层","群体","组织","制度","教育","家庭","性别","种族","民族","传统","现代","城市化"],
    "历史": ["历史","古代","近代","现代","王朝","革命","战争","起源","演变","传统"],
    "经济": ["经济","市场","资本","贸易","金融","货币","通胀","就业","产业","全球化"],
}

def classify(title, text):
    """根据标题和内容自动分类"""
    combined = (title + " " + text[:500]).lower()
    scores = {}
    for cat, keywords in CATEGORIES.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > 0:
            scores[cat] = score
    if scores:
        return max(scores, key=scores.get)
    return "综合"

def load_processed():
    if PROCESSED_FILE.exists():
        try:
            return set(json.loads(PROCESSED_FILE.read_text()))
        except:
            pass
    return set()

def save_processed(vid):
    processed = load_processed()
    processed.add(vid)
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_FILE.write_text(json.dumps(list(processed), ensure_ascii=False))

def extract_video_info(page, url):
    """从单个视频页提取结构化的内容"""
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(4)
    text = page.evaluate("document.body.innerText")
    
    skip = ["开启读屏","读屏标签","精选","推荐","搜索","关注","朋友","我的",
            "直播","放映厅","下载抖音","京ICP","京公网安","广播电","增值电",
            "网络文化","互联网宗教","药品","互联网新闻","网络谣言","违法和不良",
            "算法推荐","广告投放","用户服务","隐私政策","账号找回","加入我们",
            "营业执照","友情链接","站点地图","抖音电商","2026 ©","2025 ©",
            "请先登录","登录后即可"]
    useful = [l.strip() for l in text.split("\n")
              if len(l.strip()) > 5 and not any(k in l for k in skip)]
    
    # 提取标题（取第一条有意义的行）
    title = "未命名"
    for line in useful:
        if len(line) > 8 and not line.startswith("00:") and not line.startswith("20"):
            title = line[:60].replace("/","_").replace('"',"'")
            break
    
    # 提取发布时间
    pub_time = ""
    for line in useful:
        m = re.search(r"发布时间：(\d{4}[-/]\d{2}[-/]\d{2})", line)
        if m:
            pub_time = m.group(1)
            break
    
    # 提取核心观点（跳过互动评论部分）
    content_lines = []
    in_comment = False
    for line in useful:
        if any(k in line for k in ["登录后即可参与","展开","条回复","回复","分享"]):
            in_comment = True
        if not in_comment:
            content_lines.append(line)
    
    cat = classify(title, " ".join(content_lines[:10]))
    
    return {
        "title": title,
        "url": url,
        "pub_time": pub_time,
        "category": cat,
        "content": content_lines,
        "raw_lines": len(content_lines),
    }

def main():
    print(f"🚀 袁本初 批量采集 — 每日上限={DAILY}")
    processed = load_processed()
    print(f"📋 已处理: {len(processed)} 条")
    
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        
        # 1. 打开主页获取全部视频
        print("📡 加载创作者主页...")
        page.goto(f"https://www.douyin.com/user/{SEC_UID}", wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)
        
        # 2. 滚动加载全部视频
        print("📜 滚动加载视频...")
        last_count = 0
        same_count_rounds = 0
        for i in range(20):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            links = page.evaluate("""() => {
                const items = document.querySelectorAll('a[href*="/video/"]');
                return Array.from(new Map(Array.from(items).map(a => [a.href, a.href])).values());
            }""")
            if len(links) == last_count:
                same_count_rounds += 1
            else:
                same_count_rounds = 0
            last_count = len(links)
            if same_count_rounds >= 3:
                print(f"  已加载全部: {len(links)} 条")
                break
            if (i+1) % 5 == 0:
                print(f"  滚动第{i+1}次... 当前{len(links)}条")
        
        # 3. 过滤已处理的
        all_urls = list(dict.fromkeys(links))
        pending = [u for u in all_urls if u.split("/")[-1].split("?")[0] not in processed]
        print(f"⏳ 待处理: {len(pending)} 条 (今日上限{DAILY})")
        
        if not pending:
            print("🎉 全部视频已处理完毕!")
            browser.close()
            return
        
        # 4. 逐条处理
        today_count = 0
        results_by_cat = {}
        
        for url in pending[:DAILY]:
            vid = url.split("/")[-1].split("?")[0]
            print(f"\n  [{today_count+1}/{min(DAILY, len(pending))}] {vid[:12]}...", end=" ", flush=True)
            
            info = extract_video_info(page, url)
            if info["content"]:
                cat = info["category"]
                cat_dir = OUT_DIR / cat
                cat_dir.mkdir(parents=True, exist_ok=True)
                
                today = datetime.now().strftime("%Y%m%d")
                safe_title = re.sub(r'[\\/:*?"<>|]', '_', info["title"])[:25]
                fname = f"{today}_{vid[:10]}_{safe_title}.md"
                fpath = cat_dir / fname
                
                content = f"# {info['title']}\n"
                content += f"> 来源: {info['url']}\n"
                content += f"> 采集: {datetime.now().isoformat()}\n"
                content += f"> 分类: {cat}\n"
                if info["pub_time"]:
                    content += f"> 发布时间: {info['pub_time']}\n"
                content += "\n---\n\n"
                content += "\n".join(info["content"][:50])
                fpath.write_text(content, encoding="utf-8")
                
                save_processed(vid)
                today_count += 1
                results_by_cat.setdefault(cat, 0)
                results_by_cat[cat] += 1
                print(f"✅ [{cat}] {len(info['content'])}行")
            else:
                print("⚠️ 空内容")
            time.sleep(1)
        
        # 5. 打印统计
        print(f"\n{'='*40}")
        print(f"✅ 今日完成: {today_count} 条")
        print(f"📊 累计: {len(processed) + today_count} 条")
        print(f"📁 存放: 10_concepts/yuan_benchu/")
        if results_by_cat:
            print(f"📂 分类统计:")
            for cat, count in sorted(results_by_cat.items()):
                print(f"    {cat}: {count} 条 → {OUT_DIR/cat}/")
        
        browser.close()

if __name__ == "__main__":
    main()

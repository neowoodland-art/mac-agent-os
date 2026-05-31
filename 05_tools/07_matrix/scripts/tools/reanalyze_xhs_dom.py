#!/usr/bin/env python3
"""
小红书登录后 DOM 重分析工具
============================

用途：登录小红书后重新分析 DOM 结构，验证当前选择器是否仍然有效，
     输出结构化报告指导选择器更新。

用法:
  python tools/reanalyze_xhs_dom.py <identity_name>
  python tools/reanalyze_xhs_dom.py xhs_01 --full-dump   # 输出完整 DOM 快照
  python tools/reanalyze_xhs_dom.py xhs_01 --explore-url https://www.xiaohongshu.com/explore  # 自定义 URL

流程:
  1. 通过 Camoufox 连接身份目录（复用登录态）
  2. 导航到小红书 explore 首页
  3. 等待渲染稳定
  4. Dump 关键区域的 DOM 结构（保留选择器相关特征）
  5. 验证当前 selectors.py 中的每个选择器是否仍能匹配
  6. 输出结构化的重分析报告
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

LOCAL_ROOT = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix"
IDENTITIES_ROOT = LOCAL_ROOT / "identities"


async def analyze(identity_name: str, full_dump: bool = False, explore_url: str = None):
    """主分析流程"""
    print(f"\n{'='*60}")
    print(f" 🔍 小红书 DOM 重分析工具")
    print(f" {'='*60}")
    print(f"    身份: {identity_name}")
    print(f"    模式: {'完整快照' if full_dump else '选择器验证'}")
    print()

    # ── 1. 确定身份目录 ──
    # 优先从 accounts.yaml 读取
    import yaml
    config_path = LOCAL_ROOT / "config" / "accounts.yaml"
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
        acct = None
        for a in data.get("accounts", []):
            if a["id"] == identity_name:
                acct = a
                break
    except:
        acct = None

    if acct:
        identity_dir_str = acct.get("identity_dir", identity_name)
        if not identity_dir_str.startswith("/"):
            identity_dir_str = str(LOCAL_ROOT / identity_dir_str)
    else:
        identity_dir_str = str(IDENTITIES_ROOT / identity_name)

    # 清理锁文件
    import glob
    for lock_file in glob.glob(f"{identity_dir_str}/user_data/**/.parentlock", recursive=True):
        try:
            os.remove(lock_file)
        except:
            pass
    for lock_file in glob.glob(f"{identity_dir_str}/user_data/**/lock", recursive=True):
        try:
            os.remove(lock_file)
        except:
            pass

    # ── 2. 连接浏览器 ──
    from cdp_connector import CDPConnector
    conn = CDPConnector(
        identity_dir=identity_dir_str,
        headless=False,
        window=(702, 783),
    )
    print(f"   🚀 连接浏览器: {identity_dir_str}")
    try:
        await conn.connect()
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        sys.exit(1)
    print(f"      ✅ 浏览器已连接")
    print(f"      📐 视口: 702×783")

    # 反检测
    try:
        await conn.init_anti_detection()
    except Exception:
        pass

    # ── 3. 导航到小红书 ──
    target_url = explore_url or "https://www.xiaohongshu.com/explore"
    print(f"\n   🌐 导航到: {target_url}")
    for attempt in range(1, 4):
        try:
            await conn.page.goto(target_url, timeout=20000, wait_until="domcontentloaded")
            print(f"      ✅ 导航成功 (第{attempt}次)")
            break
        except Exception as e:
            print(f"      ⚠️ 导航失败 (第{attempt}次): {e}")
            if attempt < 3:
                await asyncio.sleep(3)
            else:
                print(f"      ❌ 导航最终失败")
                await conn.close()
                return

    # ── 等待渲染 ──
    print(f"\n   ⏳ 等待页面渲染...")
    await asyncio.sleep(5)

    # 关闭登录弹窗
    try:
        await conn.page.evaluate("""
        () => {
            document.querySelectorAll('[class*=modal], [class*=dialog], [class*=mask], [role=dialog]').forEach(m => {
                m.style.display = 'none';
            });
        }
        """)
    except:
        pass
    await asyncio.sleep(1)

    # ── 4. 检测登录状态 ──
    print(f"\n   🔐 登录状态检测")
    try:
        from auth_manager import check_login_by_cookie_sync, count_platform_cookies
        cookies = await conn.context.cookies()
        logged_in = check_login_by_cookie_sync(cookies, "xiaohongshu")
        cookie_cnt = count_platform_cookies(cookies, "xiaohongshu")
        print(f"      Cookie 检测: {'✅ 已登录' if logged_in else '❌ 未登录'}")
        print(f"      平台 Cookie 数: {cookie_cnt}")
    except Exception as e:
        print(f"      ⚠️ 登录检测异常: {e}")

    # ── 5. 检查页面基本结构 ──
    print(f"\n   📄 页面基本结构")
    page_info = await conn.page.evaluate("""
    () => {
        return {
            url: location.href,
            title: document.title,
            app_present: !!document.querySelector('#app'),
            body_children: document.body ? document.body.children.length : 0,
            viewport: {w: window.innerWidth, h: window.innerHeight},
            scroll: {x: window.scrollX, y: window.scrollY},
        };
    }
    """)
    print(f"      URL: {page_info.get('url', '?')}")
    print(f"      Title: {page_info.get('title', '?')}")
    print(f"      #app: {'✅' if page_info.get('app_present') else '❌'}")
    print(f"      body children: {page_info.get('body_children', '?')}")

    # ── 6. 验证 selectors.py 中的选择器 ──
    print(f"\n{'='*60}")
    print(f"   📋 选择器验证")
    print(f"   {'='*60}")

    # 导入当前选择器
    sys.path.insert(0, str(SCRIPTS_DIR / "matrix_modules" / "ops" / "xhs"))
    from selectors import (
        NOTE_CARD, NOTE_CARD_COVER, NOTE_CARD_IMG,
        SEARCH_INPUT, SEARCH_BUTTON,
        FEED_CONTAINER, LOGIN_MODAL, LOGIN_MODAL_CLOSE,
        LIKE_BUTTON, COLLECT_BUTTON, FOLLOW_BUTTON,
        COMMENT_ENTRY, COMMENT_INPUT, COMMENT_SEND,
        ANCHORS,
    )

    selector_tests = {
        "首页/瀑布流": [
            ("瀑布流容器", FEED_CONTAINER),
            ("笔记卡片", NOTE_CARD),
            ("卡片封面链接", NOTE_CARD_COVER),
            ("卡片图片", NOTE_CARD_IMG),
        ],
        "搜索": [
            ("搜索框", SEARCH_INPUT),
            ("搜索按钮", SEARCH_BUTTON),
        ],
        "弹窗": [
            ("登录弹窗", LOGIN_MODAL),
            ("关闭按钮", LOGIN_MODAL_CLOSE),
        ],
        "互动(详情页)": [
            ("点赞按钮", LIKE_BUTTON),
            ("收藏按钮", COLLECT_BUTTON),
            ("关注按钮", FOLLOW_BUTTON),
            ("评论入口", COMMENT_ENTRY),
            ("评论输入框", COMMENT_INPUT),
            ("发送按钮", COMMENT_SEND),
        ],
    }

    all_ok = True
    for category, selectors in selector_tests.items():
        print(f"\n   【{category}】")
        js_code = "var sel = arguments[0]; return document.querySelector(sel) ? document.querySelector(sel).outerHTML.substring(0, 200) : null;"
        for name, sel in selectors:
            try:
                count = await conn.page.evaluate(f"document.querySelectorAll('{sel.replace(chr(39), chr(92) + chr(39))}').length")
                first_match = None
                if count > 0:
                    first_match = await conn.page.evaluate(f"try {{ let el = document.querySelector('{sel.replace(chr(39), chr(92) + chr(39))}'); return el ? el.tagName + (el.className ? '.' + el.className.split(' ')[0] : '') : 'N/A'; }} catch(e) {{ return 'JS_ERR'; }}")
                status = "✅" if count > 0 else "⚠️"
                if count == 0:
                    all_ok = False
                print(f"      {status} {name}: \"{sel}\"")
                if count > 0:
                    print(f"         匹配 {count} 个元素, 首元素: {first_match}")
            except Exception as e:
                print(f"      ❌ {name}: JS 异常 - {e}")
                all_ok = False

    # ── 7. 锚点验证 ──
    print(f"\n   【锚点验证】")
    for anchor_name, anchor_sel in ANCHORS.items():
        try:
            count = await conn.page.evaluate(f"document.querySelectorAll('{anchor_sel.replace(chr(39), chr(92) + chr(39))}').length")
            status = "✅" if count > 0 else "⚠️"
            if count == 0:
                all_ok = False
            print(f"      {status} {anchor_name}: \"{anchor_sel}\" → {count} 个")
        except Exception as e:
            print(f"      ❌ {anchor_name}: {e}")

    # ── 8. 完整 DOM 快照（可选）──
    if full_dump:
        print(f"\n{'='*60}")
        print(f"   📸 完整 DOM 快照")
        print(f"   {'='*60}")
        print(f"   正在保存到文件...")

        # 获取关键区域的 HTML
        dom_snapshot = await conn.page.evaluate("""
        () => {
            const areas = {};

            // #app 容器
            const app = document.querySelector('#app');
            if (app) areas.app = app.outerHTML.substring(0, 5000);

            // 瀑布流区域
            const layout = document.querySelector('.layout, [class*=layout]');
            if (layout) areas.layout = layout.outerHTML.substring(0, 3000);

            // 检查是否有详情页（如果有多个 section.note-item 说明在首页）
            const notes = document.querySelectorAll('section.note-item');
            if (notes.length > 0) {
                areas.note_first = notes[0].outerHTML.substring(0, 2000);
                areas.note_count = notes.length;
            }

            // 记录当前页面上的所有 class 名（去重）
            const allClasses = new Set();
            document.querySelectorAll('*').forEach(el => {
                if (el.className && typeof el.className === 'string') {
                    el.className.split(/\\s+/).forEach(c => {
                        if (c && c.length > 1) allClasses.add(c);
                    });
                }
            });
            areas.all_classes = [...allClasses].sort();

            // 关键 URL 和 meta
            areas.meta = {
                url: location.href,
                title: document.title,
                links_count: document.querySelectorAll('a').length,
                buttons_count: document.querySelectorAll('button').length,
                img_count: document.querySelectorAll('img').length,
                video_count: document.querySelectorAll('video').length,
            };

            return areas;
        }
        """)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        dump_path = SCRIPTS_DIR / "data" / f"xhs_dom_dump_{timestamp}.json"
        dump_path.parent.mkdir(parents=True, exist_ok=True)

        # 简化输出：移除过长内容
        output = {}
        for k, v in dom_snapshot.items():
            if isinstance(v, str) and len(v) > 500:
                output[k] = v[:500] + f"\n... [截断, 全文 {len(v)} 字符]"
            else:
                output[k] = v

        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"      📁 已保存: {dump_path}")
        print(f"      页面元素: links={dom_snapshot.get('meta', {}).get('links_count','?')}, "
              f"buttons={dom_snapshot.get('meta', {}).get('buttons_count','?')}, "
              f"img={dom_snapshot.get('meta', {}).get('img_count','?')}")
        if dom_snapshot.get('note_count'):
            print(f"      笔记卡片数: {dom_snapshot.get('note_count')}")
        print(f"      页面 class 数: {len(dom_snapshot.get('all_classes', []))}")

    # ── 9. 截图 ──
    print(f"\n   📸 截图")
    screenshot_path = SCRIPTS_DIR / "data" / f"xhs_reanalyze_{time.strftime('%Y%m%d_%H%M%S')}.png"
    try:
        await conn.page.screenshot(path=str(screenshot_path))
        print(f"      ✅ 截图: {screenshot_path}")
    except:
        print(f"      ⚠️ 截图失败")

    # ── 10. 总结 ──
    print(f"\n{'='*60}")
    print(f"   📊 分析总结")
    print(f"   {'='*60}")
    if all_ok:
        print(f"      ✅ 所有选择器均匹配当前 DOM")
        print(f"      → 当前 selectors.py 无需更新")
    else:
        print(f"      ⚠️ 部分选择器未匹配到元素")
        print(f"      → 建议更新 selectors.py 中的不匹配选择器")
        print(f"      → 参考完整 DOM 快照了解最新结构")
    print(f"\n   💡 提示: 如果是登录后分析，对比登录前后的选择器差异")
    print(f"         尝试在探索页和笔记详情页分别运行此工具")
    print(f"{'='*60}")

    # 保持浏览器运行供检查
    print(f"\n   🔄 浏览器保持运行，关闭终端即退出")
    try:
        while True:
            await asyncio.sleep(30)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        try:
            await conn.close()
        except:
            pass


def main():
    parser = argparse.ArgumentParser(
        description="小红书登录后 DOM 重分析工具"
    )
    parser.add_argument("identity_name", help="身份名称 (如 xhs_01)")
    parser.add_argument("--full-dump", "-f", action="store_true",
                        help="输出完整 DOM 快照到 JSON 文件")
    parser.add_argument("--explore-url", "-u", default=None,
                        help="自定义分析 URL (默认: /explore)")
    args = parser.parse_args()

    asyncio.run(analyze(args.identity_name, args.full_dump, args.explore_url))


if __name__ == "__main__":
    main()

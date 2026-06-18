#!/usr/bin/env python3
"""
视频/图文发布脚本 — 通过 Camoufox 浏览器自动化上传

用法:
  python publish_video.py douyin --account my_name --file video.mp4 --title "标题" --desc "描述"
  python publish_video.py xiaohongshu --account my_name --file image.jpg --title "标题"

  # 也可调用 social-auto-upload CLI (需先安装)
  python publish_video.py douyin --account my_name --file video.mp4 --title "标题" --sau
"""

import sys, os, json, asyncio, argparse, logging, subprocess
from pathlib import Path

# 路径
from matrix_mgmt import AGENT_SYNC, AGENT_LOCAL

SCRIPTS_DIR = AGENT_SYNC / "05_tools" / "07_matrix" / "scripts"
IDENTITIES_ROOT = AGENT_LOCAL / "identities"

sys.path.insert(0, str(SCRIPTS_DIR))
from cdp_connector import CDPConnector

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("publish")

# ── 平台上传页 URL ──
UPLOAD_URLS = {
    "douyin": "https://www.douyin.com/upload/",
    "xiaohongshu": "https://www.xiaohongshu.com/upload/",
}

# ── 默认等待时间 ──
WAIT_SHORT = 3
WAIT_MEDIUM = 5
WAIT_LONG = 10


def gaussian_jitter(base, min_val=None, max_val=None):
    """高斯抖动: base 秒 ±30% 随机"""
    import random
    jitter = base * random.uniform(-0.3, 0.3)
    result = base + jitter
    if min_val is not None:
        result = max(result, min_val)
    if max_val is not None:
        result = min(result, max_val)
    return max(0.5, result)  # 至少 0.5s


async def publish_douyin(conn, file_path, title, desc):
    """在已打开的 Camoufox 中上传抖音视频"""
    page = conn.page
    log.info(f"  📤 导航到上传页: {UPLOAD_URLS['douyin']}")
    await page.goto(UPLOAD_URLS["douyin"], timeout=30000)
    await asyncio.sleep(gaussian_jitter(WAIT_MEDIUM))

    # 等待上传页面加载
    try:
        await page.wait_for_selector("input[type=file]", timeout=15000)
    except:
        log.warning("  ⚠️ 未找到文件上传 input，尝试备用选择器")
        try:
            await page.wait_for_selector(".upload-btn, .upload-file, [class*=upload]", timeout=10000)
        except:
            log.error("  ❌ 找不到上传按钮，请检查页面")
            return {"status": "error", "message": "找不到上传入口"}

    # 选择文件
    file_abs = str(Path(file_path).resolve())
    if not os.path.exists(file_abs):
        return {"status": "error", "message": f"文件不存在: {file_abs}"}

    log.info(f"  📎 选择文件: {file_abs}")
    try:
        file_input = await page.query_selector("input[type=file]")
        if file_input:
            await file_input.set_input_files(file_abs)
        else:
            # 有些平台的 file input 是隐藏的，需要通过 JS 触发
            await page.evaluate("""(path) => {
                const input = document.querySelector('input[type=file]');
                if (input) {
                    const dt = new DataTransfer();
                    input.files = dt.files;
                }
            }""", file_abs)
            log.warning("  ⚠️ 直接 set_input_files 可能不生效")
    except Exception as e:
        return {"status": "error", "message": f"文件选择失败: {e}"}

    # 等待上传
    await asyncio.sleep(gaussian_jitter(WAIT_LONG, min_val=5))

    # 填写标题
    if title:
        try:
            title_input = await page.query_selector(
                "[placeholder*=标题], [placeholder*=title], .title-input, input[name*=title]"
            )
            if title_input:
                await title_input.click()
                await asyncio.sleep(gaussian_jitter(1))
                await title_input.fill(title)
                log.info(f"  ✏️ 标题已填写")
        except Exception as e:
            log.warning(f"  ⚠️ 填写标题失败: {e}")

    # 填写描述
    if desc:
        try:
            desc_input = await page.query_selector(
                "[placeholder*=描述], [placeholder*=简介], .desc-input, textarea"
            )
            if desc_input:
                await desc_input.click()
                await asyncio.sleep(gaussian_jitter(1))
                await desc_input.fill(desc)
                log.info(f"  ✏️ 描述已填写")
        except Exception as e:
            log.warning(f"  ⚠️ 填写描述失败: {e}")

    # 等待手动操作或自动发布
    log.info(f"  ⏳ 等待上传完成 (30s)...")
    await asyncio.sleep(gaussian_jitter(30, min_val=10))

    # 尝试点击发布按钮
    publish_btn_selectors = [
        "button:has-text('发布')", "button:has-text('上传')",
        ".publish-btn", "[class*=publish]", "[class*=submit]",
        "//button[contains(text(), '发布')]"
    ]
    for selector in publish_btn_selectors:
        try:
            btn = await page.query_selector(selector)
            if btn:
                await btn.click()
                log.info(f"  🚀 点击发布按钮")
                await asynleep(gaussian_jitter(5))
                break
        except:
            continue

    return {"status": "ok", "message": "发布流程已启动，请在浏览器中确认最终结果"}


async def publish_xiaohongshu(conn, file_path, title, desc):
    """小红书发布笔记"""
    page = conn.page
    log.info(f"  📤 导航到发布页: {UPLOAD_URLS['xiaohongshu']}")
    await page.goto(UPLOAD_URLS["xiaohongshu"], timeout=30000)
    await asyncio.sleep(gaussian_jitter(WAIT_MEDIUM))

    # 上传图片
    file_abs = str(Path(file_path).resolve())
    if not os.path.exists(file_abs):
        return {"status": "error", "message": f"文件不存在: {file_abs}"}

    try:
        file_input = await page.query_selector("input[type=file]")
        if file_input:
            await file_input.set_input_files(file_abs)
            log.info(f"  📎 已选择文件")
    except Exception as e:
        return {"status": "error", "message": f"文件选择失败: {e}"}

    await asyncio.sleep(gaussian_jitter(WAIT_LONG, min_val=5))

    # 填写标题
    if title:
        try:
            title_input = await page.query_selector(
                "[placeholder*=标题], .title-input, input[name*=title]"
            )
            if title_input:
                await title_input.fill(title)
        except: pass

    # 填写正文
    if desc:
        try:
            desc_input = await page.query_selector(
                "[placeholder*=正文], .note-text, .ql-editor, [contenteditable=true]"
            )
            if desc_input:
                await desc_input.fill(desc)
        except: pass

    await asyncio.sleep(gaussian_jitter(WAIT_MEDIUM))

    return {"status": "ok", "message": "发布流程已启动，请在浏览器中确认"}


# ═══════════════════════════════════════════════════════════════
# social-auto-upload 集成 (sau CLI 调用)
# ═══════════════════════════════════════════════════════════════

def _find_sau():
    """查找 sau 可执行文件"""
    # 1. 本地 path
    import shutil
    sau = shutil.which("sau") or shutil.which("sau_cli")
    if sau:
        return sau
    # 2. pip 安装的脚本
    for p in [Path(sys.prefix) / "bin" / "sau",
              Path(sys.prefix) / "Scripts" / "sau.exe",
              Path.home() / ".local" / "bin" / "sau"]:
        if p.exists():
            return str(p)
    return None


async def publish_via_sau(args):
    """通过 social-auto-upload CLI 发布"""
    sau_path = _find_sau()
    if not sau_path:
        return {"status": "error", "message": "social-auto-upload 未安装 (需要: cd social-auto-upload && pip install -e .)"}

    # 构建命令
    platform_map = {"douyin": "douyin", "xiaohongshu": "xiaohongshu"}
    action_map = {".mp4": "upload-video", ".avi": "upload-video", ".mov": "upload-video",
                  ".jpg": "upload-note", ".jpeg": "upload-note", ".png": "upload-note", ".gif": "upload-note"}

    ext = Path(args.file).suffix.lower()
    action = action_map.get(ext, "upload-video")
    plat = platform_map.get(args.platform, args.platform)

    cmd = [sys.executable, sau_path, plat, action,
           "--account", args.account,
           "--file", args.file if action == "upload-video" else None,
           "--images", args.file if action == "upload-note" else None,
           "--title", args.title or "无标题"]

    # 清理 None 参数
    cmd = [c for c in cmd if c is not None]

    if args.desc:
        cmd += ["--note" if action == "upload-note" else "--desc", args.desc]

    log.info(f"  🚀 通过 social-auto-upload 发布 ({plat} {action})")
    log.info(f"  command: {' '.join(str(c) for c in cmd[:8])}...")

    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        out = p.stdout[-1000:] if p.stdout else ""
        err = p.stderr[-500:] if p.stderr else ""
        if p.returncode == 0:
            return {"status": "ok", "output": out}
        return {"status": "error", "message": err or out or f"退出码 {p.returncode}"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "发布超时 (600s)"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def main():
    parser = argparse.ArgumentParser(description="视频/图文发布")
    parser.add_argument("platform", choices=["douyin", "xiaohongshu"], help="平台")
    parser.add_argument("--account", required=True, help="账号身份目录名")
    parser.add_argument("--file", required=True, help="要上传的文件路径")
    parser.add_argument("--title", default="", help="标题")
    parser.add_argument("--desc", default="", help="描述/正文")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--sau", action="store_true", help="使用 social-auto-upload 引擎 (代替 Camoufox)")
    args = parser.parse_args()

    # 如果启用 social-auto-upload，调用 sau CLI
    if args.sau:
        return await publish_via_sau(args)

    identity_dir = IDENTITIES_ROOT / args.account
    if not identity_dir.exists():
        # 尝试从账号注册表查找
        try:
            sys.path.insert(0, str(SCRIPTS_DIR))
            from matrix_mgmt import MatrixManager
            mgr = MatrixManager()
            for a in mgr.list_accounts():
                if a.get("phone") == args.account or a["id"] == args.account:
                    idir = a.get("identity_dir", "")
                    if idir:
                        identity_dir = IDENTITIES_ROOT / idir.replace("identities/", "")
                        break
        except: pass

    if not identity_dir.exists():
        result = {"status": "error", "message": f"身份目录不存在: {identity_dir}"}
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"❌ {result['message']}")
        return

    log.info(f"\n🚀 发布到 {args.platform}")
    log.info(f"   账号: {args.account}")
    log.info(f"   文件: {args.file}")
    log.info(f"   标题: {args.title[:30]}...")

    conn = None
    try:
        conn = CDPConnector(identity_dir=str(identity_dir), headless=False,
                           window=(802, 783), locale=["zh-CN"])
        await conn.connect()
        await asyncio.sleep(gaussian_jitter(WAIT_SHORT))

        if args.platform == "douyin":
            result = await publish_douyin(conn, args.file, args.title, args.desc)
        else:
            result = await publish_xiaohongshu(conn, args.file, args.title, args.desc)

        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            s = result.get("status")
            icon = "✅" if s == "ok" else "❌"
            print(f"\n{icon} {result.get('message', '')}")

    except Exception as e:
        result = {"status": "error", "message": str(e)}
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"\n❌ 发布失败: {e}")
    finally:
        if conn:
            try:
                await conn.close()
            except: pass


if __name__ == "__main__":
    asyncio.run(main())

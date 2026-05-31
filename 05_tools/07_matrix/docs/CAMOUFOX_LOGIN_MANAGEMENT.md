# Camoufox 登录管理方案

## 背景
当前矩阵养号系统基于 Chrome + Profile 切换（方案A）与 Cookie 注入（方案B）。为提升反检测能力、支持多浏览器内核，计划引入 **Camoufox**（Firefox 内核反检测浏览器）作为新的登录管理方式。

## 目标
1. 提供 Camoufox 的安装、配置指南
2. 扩展账号配置，支持 `browser_type` 字段（`chrome` / `camoufox`）
3. 实现 Camoufox 实例的启动、指纹注入、CDP 连接
4. 提供登录状态验证与 Cookie 管理
5. 演示如何添加两个新账号并尝试 Camoufox 登录

## 1. 安装与配置

### 1.1 安装 Python 包
```bash
# 已安装的 camoufox 包可能需要更新
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 -m pip install -U camoufox[geoip]
```

### 1.2 下载 Camoufox 浏览器
```bash
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 -m camoufox fetch
```
这将把浏览器可执行文件下载到 `~/Library/Caches/camoufox/`。

### 1.3 验证安装
```bash
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 -m camoufox path
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 -c "import camoufox; print(camoufox.__version__)"
```

## 2. 账号配置扩展

### 2.1 修改 `config/accounts.yaml`
在现有配置基础上增加 `browser_type` 字段，并为 Camoufox 账号指定独立端口（建议从 9300 开始，避免与 Chrome 端口冲突）。

```yaml
# 新增全局配置块
camoufox:
  # Camoufox 可执行文件路径（自动检测）
  executable: ~/Library/Caches/camoufox/camoufox
  # 默认视口（Camoufox 使用 screen 参数）
  screen:
    width: 702
    height: 783
  # 默认地理设置
  geo:
    timezone: Asia/Shanghai
    locale: zh-CN

# 视口配置（Chrome 用）
viewport:
  width: 702
  height: 783
  mobile: false

accounts:
  # ── 原有 Chrome 账号 ──
  - id: douyin_01
    platform: douyin
    phone: "18513308610"
    port: 9222
    browser_type: chrome
    profile_dir: account_01
    enabled: true
    notes: 抖音主号（Chrome）

  # ── 新增 Camoufox 账号（两个） ──
  - id: douyin_camo01
    platform: douyin
    phone: ""   # 待填写
    port: 9301
    browser_type: camoufox
    profile_dir: camoufox_01   # 对应 ~/matrix/profiles/camoufox_01
    proxy: socks5://127.0.0.1:7890  # 可选，推荐使用静态住宅IP
    screen:   # 覆盖全局 screen 设置
      width: 702
      height: 783
    geo:
      timezone: Asia/Shanghai
      locale: zh-CN
    enabled: true
    notes: Camoufox 测试账号1

  - id: douyin_camo02
    platform: douyin
    phone: ""
    port: 9302
    browser_type: camoufox
    profile_dir: camoufox_02
    proxy: null
    screen:
      width: 702
      height: 783
    geo:
      timezone: Asia/Shanghai
      locale: zh-CN
    enabled: true
    notes: Camoufox 测试账号2
```

### 2.2 创建 Profile 目录
```bash
mkdir -p ~/matrix/profiles/camoufox_01
mkdir -p ~/matrix/profiles/camoufox_02
```

## 3. Camoufox 管理器脚本

创建 `~/matrix/scripts/camoufox_manager.py`，提供以下功能：

- 启动/停止 Camoufox 实例（指定端口、Profile、代理）
- 通过 CDP 连接已启动的实例
- 注入指纹（Camoufox 内置，无需额外注入）
- 验证登录状态
- 导出/导入 Cookie

### 3.1 脚本骨架
```python
#!/usr/bin/env python3
"""
Camoufox 管理器 — 启动、连接、登录验证
"""
import asyncio
import json
import os
import subprocess
import time
from pathlib import Path

from camoufox import AsyncCamoufox

PROJECT_DIR = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_DIR / "config" / "accounts.yaml"
PROFILES_DIR = PROJECT_DIR / "profiles"
COOKIE_STORAGE = PROJECT_DIR / "data" / "cookies"

def load_account_config(account_id: str) -> dict:
    """从 accounts.yaml 加载指定账号配置"""
    # 实现略，参考 switch_account.py 的 get_account
    pass

async def launch_camoufox(account: dict) -> bool:
    """启动 Camoufox 实例"""
    profile_dir = PROFILES_DIR / account.get('profile_dir', account['id'])
    profile_dir.mkdir(parents=True, exist_ok=True)

    # 从配置中读取 screen 和 geo
    screen = account.get('screen', {'width': 702, 'height': 783})
    geo = account.get('geo', {'timezone': 'Asia/Shanghai', 'locale': 'zh-CN'})
    proxy = account.get('proxy')  # 如 "socks5://127.0.0.1:7890"

    print(f"🚀 启动 Camoufox（账号: {account['id']}，端口: {account['port']}）")
    try:
        async with AsyncCamoufox(
            headless=False,
            proxy=proxy,
            user_data_dir=str(profile_dir),
            screen=screen,
            geo=geo,
            # 以下参数为 Camoufox 特有
            cdp_port=account['port'],          # 指定 CDP 端口
            disable_automation=True,           # 隐藏自动化标记
            disable_webdriver=True,
            disable_canvas_noise=False,        # 启用 Canvas 噪声
            disable_font_fingerprinting=False, # 启用字体指纹伪造
            disable_webgl_fingerprinting=False,
            disable_audio_fingerprinting=False,
        ) as browser:
            # 保持浏览器运行（实际会阻塞，需要多进程）
            # 这里我们只启动，然后通过 CDP 连接
            pass
    except Exception as e:
        print(f"❌ Camoufox 启动失败: {e}")
        return False
    return True

async def connect_via_cdp(port: int):
    """通过 CDP 连接已启动的 Camoufox 实例"""
    import urllib.request
    import json
    from patchright.async_api import async_playwright

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f"http://localhost:{port}/json/version", timeout=5) as r:
        info = json.loads(r.read())
        ws_url = info["webSocketDebuggerUrl"]

    pw = await async_playwright().start()
    try:
        # 注意：Camoufox 是 Firefox 内核，需使用 p.firefox 连接
        browser = await pw.firefox.connect_over_cdp(ws_url)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        return page
    finally:
        await pw.stop()

async def verify_login(page) -> bool:
    """验证抖音登录状态"""
    await page.goto('https://www.douyin.com/', wait_until='domcontentloaded', timeout=15000)
    await asyncio.sleep(3)
    avatar = page.locator("[data-e2e='user-avatar']")
    logged_in = await avatar.count() > 0
    return logged_in

async def export_cookies(account_id: str, port: int):
    """导出 Cookie 到文件"""
    page = await connect_via_cdp(port)
    cookies = await page.context.cookies()
    cookie_file = COOKIE_STORAGE / f"{account_id}_camoufox_cookies.json"
    cookie_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cookie_file, 'w') as f:
        json.dump(cookies, f, indent=2)
    print(f"✅ 导出 {len(cookies)} 个 Cookie → {cookie_file}")

async def main():
    """CLI 入口"""
    import argparse
    parser = argparse.ArgumentParser(description='Camoufox 管理器')
    parser.add_argument('--launch', type=str, help='启动指定账号')
    parser.add_argument('--connect', type=int, help='连接指定端口')
    parser.add_argument('--export', type=str, help='导出 Cookie（账号ID）')
    args = parser.parse_args()

    if args.launch:
        account = load_account_config(args.launch)
        await launch_camoufox(account)
    elif args.connect:
        page = await connect_via_cdp(args.connect)
        print(f"✅ 已连接页面: {page.url}")
    elif args.export:
        account = load_account_config(args.export)
        await export_cookies(args.export, account['port'])

if __name__ == '__main__':
    asyncio.run(main())
```

### 3.2 集成到现有切换器
修改 `switch_account.py`，增加 `--browser` 参数，支持 `chrome`（默认）和 `camoufox`。或者，直接创建一个新的入口脚本 `switch_browser.py`，统一管理两种浏览器。

## 4. 登录流程

### 4.1 首次登录
1. 启动 Camoufox 账号：
   ```bash
   python scripts/camoufox_manager.py --launch douyin_camo01
   ```
2. 手动登录抖音（扫码/密码）。
3. 登录后导出 Cookie：
   ```bash
   python scripts/camoufox_manager.py --export douyin_camo01
   ```
4. 关闭浏览器（Ctrl+C），后续可通过 CDP 连接使用 Cookie 恢复登录。

### 4.2 后续切换
使用 Cookie 注入方式快速切换（类似方案B）：
- 读取该账号的 Cookie 文件
- 通过 CDP 注入到已启动的 Camoufox 实例
- 刷新页面验证登录

## 5. 踩坑经验（预判）

1. **CDP 端口冲突**：Camoufox 默认 CDP 端口可能与 Chrome 冲突，建议使用 9300+ 端口范围。
2. **Firefox CDP 协议差异**：Playwright 连接 Firefox CDP 时，部分 API 与 Chromium 不同，需测试兼容性。
3. **代理配置**：Camoufox 的 `proxy` 参数格式需为 `socks5://ip:port` 或 `http://ip:port`。
4. **Profile 目录权限**：确保 `~/matrix/profiles/` 目录 Camoufox 可写。
5. **浏览器下载失败**：网络问题可能导致 `camoufox fetch` 失败，可手动下载并放置到缓存目录。

## 6. 后续优化方向

1. **Docker 容器化**：将 Camoufox 打包为 Docker 镜像，实现更彻底的隔离。
2. **多账号并行**：使用多个 Camoufox 容器同时运行多个账号。
3. **指纹池**：为每个账号配置不同的指纹模板（屏幕尺寸、时区、语言等）。
4. **自动化登录**：结合短信验证码平台实现全自动登录。

## 7. 快速开始（两个新账号）

1. **编辑配置**：在 `accounts.yaml` 中添加 `douyin_camo01` 和 `douyin_camo02`（如上所示）。
2. **创建目录**：执行 `mkdir -p ~/matrix/profiles/camoufox_{01,02}`。
3. **启动第一个账号**：
   ```bash
   cd ~/matrix
   python scripts/camoufox_manager.py --launch douyin_camo01
   ```
4. **手动登录**，然后导出 Cookie。
5. **关闭浏览器**，测试 Cookie 注入恢复登录。
6. **重复**步骤3-5 用于第二个账号。

---

**下一步**：确认方案后，可开始实施脚本编写与配置更新。
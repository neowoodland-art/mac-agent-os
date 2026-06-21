---
name: cloakbrowser_controller
version: 1.0.0
status: archived
archived_date: 2026-06-21
description: [已归档] CloakBrowser 反爬浏览器设计，无实现代码
triggers: []
---

# CloakBrowser Controller Skill

## 概述

源码级修改的 Chromium 分发版，49项 C++ 补丁修改指纹，30/30反爬检测全部通过。
**只替换浏览器操作层，不涉及 Matrix 养号的 Camoufox（已深度适配）。**

## 安装

```bash
# agent-os venv（本机）
/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3 -m pip install cloakbrowser

# 首次运行自动下载 ~350MB Chromium 二进制到 ~/.cloakbrowser/
# 二进制位置: ~/.cloakbrowser/chromium-145.0.7632.109.2/Chromium.app
```

## 验证

```python
from cloakbrowser import launch
b = launch(humanize=True)
page = b.new_page()
page.goto("https://www.baidu.com")
print(page.title())  # → "百度一下，你就知道"
b.close()
```

### 代理环境

如使用代理，需在 Python 代码中设置环境变量：

```python
import os
os.environ['HTTPS_PROXY'] = 'socks5://127.0.0.1:6478'   # SOCKS5
os.environ['HTTP_PROXY'] = 'socks5://127.0.0.1:6478'     # 或 http 代理
```

### 预下载二进制

```python
from cloakbrowser.download import ensure_binary, binary_info
info = binary_info()
print(info["installed"])          # 是否已下载
ensure_binary()                   # 预下载 Chromium 二进制
```

## API 用法（与 Playwright 完全兼容）

```python
# 旧：Playwright（易被检测）
# from playwright.sync_api import sync_playwright

# 新：CloakBrowser（30/30通过）
from cloakbrowser import launch

browser = launch(humanize=True)   # humanize 启用人类行为模拟
page = browser.new_page()
page.goto("https://protected-site.com")
# ... 标准的 Playwright API
browser.close()
```

## 在系统中的应用

### 1. web_crawler 高级引擎

替换 Playwright stealth 引擎：

```python
# web_crawler 引擎选择
反爬级别 → 引擎
低（静态）→ Scrapling（最快）
高（Cloudflare等）→ CloakBrowser（新增，默认）
```

### 2. content-inspiration 采集引擎

替换 agent-browser 进行抖音/网页内容采集：

```python
# collect.py 采集引擎
platform == "douyin" 且需要浏览器 → CloakBrowser（优先）
platform == "douyin" 且 CloakBrowser 失败 → 回退 OpenCLI
```

## 注意事项

- **Matrix 养号的 Camoufox 不动** — 账号适配已完成，换内核需重写
- CloakBrowser 首次启动会下载 ~200MB 二进制，需等待
- 建议与 Scrapling 配合使用：静态页走 Scrapling，高反爬走 CloakBrowser
- 与 Peekaboo 无冲突：CloakBrowser 做浏览器操作，Peekaboo 做桌面GUI/OCR

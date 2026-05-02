---
id: method-20260501-camoufox-fix
title: Camoufox 集成修复记录
type: method
tags: [camoufox, 反检测, 指纹, 中文乱码, matrix]
collected_by: Redmi-12C
created: 2026-05-01
confidence: 0.9
nature: fact
---

# Camoufox 集成修复记录

## 正确启动方式
使用 `CDPConnector(browser_type="camoufox")`，**不要**使用 `camoufox_manager.py --launch` 或 `camoufox_server.py --launch`。

## 修复清单

### 1. 操作系统指纹（P1）
**问题**: Camoufox 默认从 `[windows, macos, linux]` 随机，导致手机端扫码有时显示"登录macOS"。
**修复**: 添加 `os='windows'` 固定参数。
**文件**: `cdp_connector.py:_launch_camoufox()`

### 2. 中文乱码（P1）
**问题**: Camoufox/Firefox 不加载系统字体，抖音页面中文显示乱码。
**修复**: 添加 `fonts=['STHeiti', 'Heiti SC', 'PingFang SC', 'Noto Sans CJK SC']` 和 `humanize=1.5`。
**文件**: `cdp_connector.py:_launch_camoufox()`

### 3. 登录检测（P0）
**问题**: `switch_account.py` 用 DOM 头像元素检测，桌面端不可见。
**修复**: 改用 `auth_manager` 模块的 Cookie 检测（sessionid 主方案 + DOM 备选）。
**文件**: `switch_account.py` + `auth_manager.py`（新建）

### 4. 登录持久化
Camoufox 登录态不靠浏览器 Profile 持久化，而通过 Cookie 文件注入：
```
Chrome 登录 → export_cookies() → douyin_01_cookies.json
Camoufox 启动 → inject_cookies() → 从 Cookie 文件恢复登录
```

## 已知限制
- Camoufox (Firefox) 使用 Juggler 管道通信，非标准 Chrome CDP HTTP 端点
- 无法通过 `camoufox_server.py` 的端口 9301 进行标准 CDP 控制
- Python 脚本生命周期与浏览器绑定（脚本退出 → 浏览器关闭）

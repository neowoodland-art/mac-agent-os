---
title: "Camoufox 集成修复记录"
source_dir: 03_knowledge/20_methods
source_file: Redmi-12C_20260501_camoufox_fix.md
date: 2026-05-03
collected_date: 2026-05-03
tags: [camoufox, 反检测, 指纹, 中文乱码, matrix]
nature: method
domain: general
status: inbox
---

# Camoufox 集成修复记录

> 来源：03_knowledge/20_methods

# Camoufox 集成修复记录
## 正确启动方式
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

---
id: KB-20260514-002
title: "CloakBrowser 源码级反爬浏览器"
type: system
status: active
nature: reference
domain: system
subdomain: [反爬, 浏览器自动化, 采集]
tags: [cloakbrowser, 反爬, 浏览器指纹, web_crawler]
confidence: 0.85
source: "系统集成落地验证"
date_created: 2026-05-14
date_modified: 2026-05-14
version: 1
summary: "源码级修改的 Chromium 分发版，49项 C++ 补丁修改指纹，30/30反爬检测全部通过。API兼容 Playwright，改一行 import 即可迁移。"

collected: true
collected_date: 2026-05-16---

# CloakBrowser 源码级反爬浏览器

## 基本信息

- 版本: v0.3.28
- 安装: `pip install cloakbrowser`
- 二进制: 首次运行自动下载 ~200MB Chromium

## 核心原理

直接修改 Chromium 的 C++ 源码再编译，不是 JS 注入或配置修改。

| 修改项 | 做法 |
|--------|------|
| Canvas 指纹 | 修改 GPU 渲染行为 |
| WebGL 指纹 | 修改驱动信息 |
| 自动化信号 | 修改 CDP `webdriver` 属性 |
| Audio 指纹 | 修改音频层随机化种子 |
| 字体指纹 | 修改字体枚举逻辑 |

## 检测通过率

- 30/30 全部通过
- reCAPTCHA v3: 0.9（人类级别）
- Cloudflare Turnstile: 通过
- FingerprintJS: 通过

## 系统集成

- 技能: `02_skills/cloakbrowser_controller/SKILL.md`
- web_crawler 引擎: v1.2.0，高反爬走 CloakBrowser

## 不涉及的模块

- Matrix 养号（Camoufox）— 已深度适配，不更换内核
- OpenCLI — 不变
- Scrapling — 不变（低反爬页面仍用它）

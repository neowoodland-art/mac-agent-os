---
title: "2026-05-17_CloakBrowser_源码级反爬浏览器"
source_dir: 03_knowledge/40_references
source_file: 2026-05-17_CloakBrowser_源码级反爬浏览器.md
date: 2026-05-20
collected_date: 2026-05-20
tags: ["待补充"]
nature: reference
domain: general
status: inbox
---

# 2026-05-17_CloakBrowser_源码级反爬浏览器

> 来源：03_knowledge/40_references

# CloakBrowser 源码级反爬浏览器

> 来源：03_knowledge/40_references

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

- 技能: `02

...（内容已截断，完整内容见源文件）

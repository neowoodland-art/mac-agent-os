---
name: web_crawler
version: 1.2.0
status: archived
archived_date: 2026-06-21
description: [已归档] 网页抓取设计，无实现代码
triggers: []
---

# Web Crawler Skill（网页抓取+反爬）

## 概述

使用 Scrapling + Crawl4AI 进行结构化网页抓取，绕过 Cloudflare 等高级反爬。

## 抓取引擎选择

| 反爬级别 | 引擎 | 说明 |
|----------|------|------|
| 低（静态页面） | Scrapling 静态模式 | 最快，无需浏览器 |
| 中（动态渲染） | Scrapling 动态模式 | Camoufox 隐身浏览器 |
| 高（Cloudflare 等） | **CloakBrowser** | 源码级反爬，30/30检测通过（2026-05 新增） |

> **2026-05-14 更新**：Playwright + Stealth 已替换为 CloakBrowser。
> CloakBrowser 是源码级修改的 Chromium，49项 C++ 补丁修改指纹，
> 通过率远高于 JS 注入方案。安装：`pip install cloakbrowser`

## 执行流程

```
1. 解析目标 URL，判断反爬级别
2. 选择最优引擎
3. 抓取内容，Crawl4AI 过滤广告/导航 → 生成干净 Markdown
4. 输出到指定路径或直接传给 kb_manager 入库
5. 失败自动重试（最多 3 次），引擎自动降级
```

## 使用场景

- 网页内容抓取 → 传给 content_processor / kb_manager
- 网页变化监控 → 配合 auto_collector 定时检查
- 数据采集 → 结构化提取

## 依赖

| 包 | 用途 | 安装状态 |
|---|---|---|
| scrapling | 三引擎自适应抓取 | ✅ 已安装 |
| crawl4ai | LLM 友好结构化输出 | ✅ 已安装 |
| playwright | 浏览器控制 | ✅ 已安装 |
| playwright-stealth | 反检测 | ✅ 已安装 |
| Playwright Chromium | 浏览器引擎 | ⚠️ 需下载（网络问题待解决） |

## 注意事项

- Playwright Chromium 浏览器需下载，运行 `playwright install chromium`
- 如果 Playwright 不可用，fallback 到 Scrapling 静态/动态模式
- 抓取频率过高可能被目标网站封禁，建议设置合理间隔

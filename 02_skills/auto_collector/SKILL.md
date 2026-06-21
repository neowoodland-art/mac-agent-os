---
name: auto_collector
version: 1.0.0
status: archived
archived_date: 2026-06-21
description: [已归档] 24小时自动信息收集设计，无实现代码
triggers: []
---

# Auto Collector Skill（24h 自动信息收集）

## 概述

24小时自动监控多平台信息源，发现新内容后自动抓取、分类、入库、通知。

## 触发词

| 触发词 | 动作 |
|--------|------|
| 开始收集 | 启动定时监控任务 |
| 停止收集 | 暂停所有定时任务 |
| 收集状态 | 返回当前监控列表、最近采集时间、今日采集数量 |
| 收集报告 | 生成今日采集摘要 |
| 添加监控 [URL/博主名] | 新增监控源 |
| 删除监控 [名称] | 移除监控源 |

## 监控频率与工具

| 信息源 | 监控频率 | 采集工具 | 备注 |
|--------|----------|----------|------|
| B站/YouTube 订阅更新 | 每 30 分钟 | BiliNote API | 需 BiliNote Docker |
| 小红书指定博主 | 每 2 小时 | TikOmni Skills | ✅ 已安装 |
| 抖音指定账号 | 每 2 小时 | TikOmni Skills | ✅ 已安装 |
| RSS 订阅源 | 每 15 分钟 | feedparser | ✅ 已安装 |
| 指定网页监控 | 每 1 小时 | Crawl4AI | ✅ 已安装 |

## 采集流程

```
定时触发
  → 检查信息源是否有新内容
    ├─ 无新内容 → 记录日志，等待下一轮
    └─ 有新内容 → 自动抓取
         ├─ 视频 → bilinote 技能生成笔记
         ├─ 图文 → web-clipper 技能提取正文
         ├─ 社交帖子 → social-collector 技能结构化提取
         └─ 音频/RSS → 提取全文
       → kb_manager 自动入库（写入 03_knowledge/00_inbox/）
       → 标记标签：#自动采集 #平台名 #日期
       → 凌晨 2:00 汇总日报 → 写入 Obsidian 01_daily/
```

## 定时任务配置

### WorkBuddy 自动化配置

| 任务 | 频率 | 说明 |
|------|------|------|
| RSS 检查 | FREQ=HOURLY;INTERVAL=1 | 检查所有 RSS 源 |
| 社交平台检查 | FREQ=HOURLY;INTERVAL=2 | 小红书/抖音博主 |
| 网页变化检查 | FREQ=HOURLY;INTERVAL=1 | 指定网页监控 |
| 采集日报 | FREQ=DAILY;BYHOUR=23 | 每日 23:00 汇总 |

### macOS cron 授权

```bash
# 系统设置 → 隐私与安全性 → 完全磁盘访问权限 → 添加 /usr/sbin/cron
```

## 配置文件

监控源列表存储在：`~/workbuddy-agent-os/agent-sync/02_skills/auto_collector/sources.json`

```json
{
  "rss": [
    {"name": "示例RSS", "url": "https://example.com/feed.xml", "last_checked": null}
  ],
  "xiaohongshu": [
    {"name": "博主A", "user_id": "xxx", "last_checked": null}
  ],
  "douyin": [
    {"name": "账号B", "user_id": "xxx", "last_checked": null}
  ],
  "web_pages": [
    {"name": "目标网页", "url": "https://example.com", "last_hash": null}
  ]
}
```

## 依赖

| 包 | 版本 | 用途 | 安装状态 |
|---|---|---|---|
| feedparser | latest | RSS 解析 | ✅ 已安装 |
| schedule | latest | 定时任务 | ✅ 已安装 |
| @tikomni/skills | latest | 小红书/抖音采集 | ✅ 已安装 |
| crawl4ai | latest | 网页抓取 | ✅ 已安装 |
| chromadb | latest | 向量存储（可选） | ✅ 已安装 |

## 注意事项

- BiliNote 需要 Docker 运行，首次使用前需手动部署
- 社交平台采集可能需要登录态，TikOmni 已处理
- 网页变化检测基于内容哈希对比
- 所有采集内容先入 `00_inbox/`，由 `collect_to_inbox` 每日 2:30 提取各目录内容转入收件箱，再由 `inbox_refine` 技能每日凌晨 3:00 自动提纯归档
- 采集日报写入 `01_daily/`，由 `memory_manager` 每日凌晨 2:00 汇总

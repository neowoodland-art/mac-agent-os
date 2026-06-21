---
name: content_processor
version: 2.0.0
status: archived
archived_date: 2026-06-21
description: [已归档] 统一内容采集入口设计，无实现代码
triggers: []
---

# Content Processor Skill（统一内容采集入口）

## 概述

统一的内容采集入口技能。**两个入口命令**：

| 你说 | 含义 | purpose | 去向 |
|------|------|---------|------|
| `收集这个...` | 知识收集 | knowledge | → 01_submissions/ → 提纯入库 |
| `收集素材...` | 素材分析 | material | → materials/ + AI 分析结果 |

### 知识类路由（"收集这个..."）

| 你说 | collect_type | collect_subtype | 提取方式 |
|------|-------------|----------------|----------|
| 收集这个视频 | douyin-video | default | 标题+描述+标签 |
| 收集这个视频的字幕 | douyin-video | subtitle | 字幕全文 |
| 总结这个视频 | douyin-video | summary | AI 总结核心观点 |
| 收集这个链接 | webpage | default | 标题+正文摘要 |
| 收集这篇文章 | webpage / wechat-article | default | 标题+正文 |
| 收集这个音频 | audio | transcription | 语音转文字 |

### 素材类路由（"收集素材..."）

| 你说 | collect_type | collect_subtype | AI 分析内容 |
|------|-------------|----------------|-------------|
| 收集素材 | douyin-video | default | 仅保存原视频 |
| 收集素材，视频结构 | douyin-video | video-structure | 起承转合、节奏分段、框架 |
| 收集素材，拍摄脚本 | douyin-video | shooting-script | 分镜描述、拍摄手法 |
| 收集素材，镜头运镜 | douyin-video | camera-movement | 推拉摇移跟、构图方式 |
| 收集素材，前三秒钩子 | douyin-video | opening-hook | 开头吸引点、悬念设置 |
| 收集素材，悬疑点 | douyin-video | suspense-points | 悬疑设计、反转点 |
| 收集素材，文案结构 | douyin-video | copy-structure | 黄金圈、痛点-方案框架 |
| 收集素材 | audio | raw | 仅保存音频文件 |
| 收集素材 | image | default | 保存原图 |

## 输出规则

### 知识类 → `01_submissions/`

```markdown
---
title: "原标题"
collect_type: "douyin-video"
collect_subtype: "default"
purpose: "knowledge"
source_url: "链接"
source_author: "作者"
source_date: "日期"
collected_by: "{机器名}"
collected_date: "{日期}"
status: submitted
tags: []
---
```

### 素材类 → `agent-local/materials/{type}/`

```
materials/
├── audios/      ← 背景音乐、音频原文件
├── screenshots/ ← 截图
├── images/      ← 原图
└── videos/      ← 视频片段
```

## 即时 vs 批量

| 你说 | 模式 |
|------|------|
| `收集这个视频` | 批量 → 进提交箱等待 |
| `收集这个视频并提纯` | 即时 → 进提交箱 → 立即提纯 → 返回 |
| `提纯这个` | 即时 → 对刚收集的内容立即提纯 |

## 子技能依赖

| 子技能 | 说明 |
|--------|------|
| agent-browser | 抖音/网页内容抓取 |
| voice-summary | 语音转文字（Whisper） |
| web-crawler | 爬虫/反爬 |
| @tikomni/skills | 社交平台采集 |

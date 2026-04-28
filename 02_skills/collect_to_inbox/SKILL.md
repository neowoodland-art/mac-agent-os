---
name: collect_to_inbox
version: 1.0.0
description: 知识库各分类目录内容提取→收件箱。扫描 03_knowledge/ 下各分类目录（50_resources/、01_daily/、20_methods/、40_references/ 等）中的文件，提取主要内容生成标准化 MD 文件放入 00_inbox/，供 inbox_refine 后续提纯归档。
triggers:
  - 收集到收件箱
  - 汇聚收件箱
  - 收集入库
  - collect inbox
  - 归集
---

# Collect to Inbox —— 分类目录内容汇聚收件箱

## 概述

将知识库各分类目录中散落的内容提取主要信息，转为标准化 Markdown 文件放入 `00_inbox/` 收件箱。这是 **收件箱提纯的前置步骤**。

## 设计背景

各收集类技能按内容类型保存到不同分类目录：
- `50_resources/视频笔记/` — bilinote 转笔记
- `50_resources/字幕存档/` — bilinote 摘字幕
- `50_resources/阅读笔记/` — web-clipper 剪藏
- `50_resources/全文存档/` — web-clipper 摘抄
- `50_resources/翻译存档/` — web-clipper 翻译
- `50_resources/灵感素材/` — social-collector 采集
- `50_resources/语音转写/` — voice-summary 转文字
- `20_methods/` — web-clipper 提炼
- `01_daily/闪念笔记/` — voice-summary 语音摘要
- `40_references/` — content_processor 网页剪藏

本技能负责将这些目录中的文件提取主要内容，生成统一格式的 MD 放入收件箱。

## 扫描目录配置

| 源目录 | 来源技能 | 提取策略 |
|--------|----------|----------|
| `50_resources/视频笔记/` | bilinote | 提取核心摘要 + 关键结论 |
| `50_resources/字幕存档/` | bilinote | 提取前 500 字摘要 |
| `50_resources/阅读笔记/` | web-clipper | 提取标题 + 核心观点 |
| `50_resources/全文存档/` | web-clipper | 提取前 500 字摘要 |
| `50_resources/翻译存档/` | web-clipper | 提取标题 + 3 句话概括 |
| `50_resources/灵感素材/` | social-collector | 提取核心内容 + 互动数据 |
| `50_resources/语音转写/` | voice-summary | 提取关键要点 |
| `20_methods/` | web-clipper 提炼 | 提取方法名 + 步骤 |
| `01_daily/闪念笔记/` | voice-summary | 提取要点 + 标签 |
| `40_references/` | content_processor | 提取标题 + 核心观点 |

> 注意：`00_inbox/` 目录本身不扫描（避免重复处理），`99_system/` 不扫描（系统文件）。

## 执行步骤

1. 扫描上述所有源目录，查找 `.md` 文件
2. 对每个文件：
   a. 读取 Frontmatter 提取元数据（title, date, tags, source 等）
   b. 读取正文，根据提取策略生成摘要
   c. 检查 `00_inbox/` 中是否已有同名文件（去重）
   d. 如无重复，生成标准化 MD 文件写入 `00_inbox/`
   e. 在原文件 Frontmatter 中标记 `collected: true` 和 `collected_date`
3. 输出统计报告（扫描数、提取数、跳过数、重复数）

## 提取后生成的 MD 格式

```markdown
---
title: {原标题}
source_dir: {原目录相对路径}
source_file: {原文件名}
date: {原始日期}
collected_date: {收集日期}
tags: {原始标签}
nature: {推断的属性：concept/method/fact/reference/resource/opinion}
domain: {推断的领域}
status: inbox
---

# {原标题}

> 来源：{原目录路径}

{提取的主要内容摘要}
```

## 去重规则

- 同名文件跳过（`00_inbox/` 中已存在同文件名）
- 同标题文件跳过（Frontmatter title 匹配）
- 已标记 `collected: true` 的源文件跳过

## 前置依赖

| 依赖 | 说明 |
|------|------|
| Python 3 | 运行脚本 |
| 03_knowledge/ 目录 | 知识库根目录 |

## 自动化

- 每日凌晨 2:30 自动执行（WorkBuddy automation）
- 在 `inbox_refine`（3:00）之前运行，确保收件箱有内容可提纯
- 也可手动触发：说"归集"或"收集到收件箱"

## 与其他技能的关系

```
收集技能 → 各分类目录（视频笔记/阅读笔记/灵感素材/...）
                    ↓
          collect_to_inbox（每日 2:30）
                    ↓
          00_inbox/（收件箱，标准化 MD）
                    ↓
          inbox_refine（每日 3:00）
                    ↓
          按属性+领域分类归档 → 最终目录 + 更新首页
```

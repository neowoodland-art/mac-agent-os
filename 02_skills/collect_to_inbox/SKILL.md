---
name: collect_to_inbox
version: 1.0.0
status: legacy
description: [降级] 扫描旧目录的文件转入 00_inbox/。注：v2.0 设计（以 01_submissions/ 为主入口）尚未实现。当前实际代码扫描的是 50_resources/、20_methods/、01_daily/、40_references/ 等旧目录。
triggers:
  - 归集
  - 归集收件箱
  - 收集到收件箱
  - 汇聚收件箱
  - collect inbox
---

# Collect to Inbox —— 提交箱 → 收件箱

## 概述

将 `01_submissions/`（提交箱）中的采集内容转入 `00_inbox/`（待提纯收件箱）。
这是 **收件箱提纯的前置步骤**，v2.0 以 `01_submissions/` 为主入口。

## 设计背景（v2.0）

根据 [内容收集全链路规范 v2.0](../99_system/pipelines/content-collection-pipeline.md)：

```
所有机器统一流程
  ↓
收集内容 → 01_submissions/（提交箱）
  ↓
collect_to_inbox（归集）
  ↓
00_inbox/（待提纯）
  ↓
inbox_refine（提纯）→ 分类入库
```

## 扫描目录配置（按优先级）

| 优先级 | 源目录 | 说明 | 提取策略 |
|--------|--------|------|----------|
| **1** | `01_submissions/` | **v2.0 主入口**，所有新建采集内容 | 读取 frontmatter 直接转存，无需重新提取 |
| 2 | `50_resources/` | 旧版兼容，历史遗留内容 | 提取核心摘要 |
| 3 | `20_methods/` | 旧版兼容 | 提取方法名 + 步骤 |
| 4 | `40_references/` | 旧版兼容 | 提取标题 + 核心观点 |
| 5 | `01_daily/闪念笔记/` | 旧版兼容 | 提取要点 + 标签 |

## 执行步骤（v2.0）

```
1. 扫描 01_submissions/ 下所有 status:submitted 的 .md 文件
   ↓
2. 读取 frontmatter：
   ├── collect_type + collect_subtype 决定提取策略
   ├── purpose 判断知识类/素材类
   └── 素材类 → 跳过（已直存 materials/）
   ↓
3. 检查 00_inbox/ 中是否已有同名条目（按 title 去重）
   ↓
4. 无重复 → 复制到 00_inbox/{filename}，追加字段：
   ├── staged_date: 归集日期
   └── status: inbox
   ↓
5. 更新源文件 status → staged
   ↓
6. 输出统计报告
```

## 兼容旧目录

保留对 `50_resources/`、`20_methods/` 等旧目录的扫描能力，
但优先级低于 `01_submissions/`。旧目录内容同等转入 `00_inbox/`。

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

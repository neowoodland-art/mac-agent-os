---
name: kb_manager
version: 1.1.0
description: 知识库管理技能——新增知识入库、清洗、标签分类、属性变更移动、搜索、备份
triggers:
  - 知识库管理
  - 入库
  - 保存知识
  - 知识入库
  - 知识分类
  - 查知识库
  - 知识检索
  - 知识备份
  - 知识属性变更
  - 知识重分类
  - ingest
  - kb
---

# KB Manager 技能

## 概述

管理 AgentOS 的 Obsidian 知识库（03_knowledge/），负责知识入库、清洗、分类、属性变更移动、搜索和备份。

## 核心能力

### 1. 知识入库（kb_ingest）
- 输入：网页 URL 或纯文本
- 流程：
  1. 抓取/接收原始内容
  2. 清洗（去广告、去导航、提取正文）
  3. 写入 `03_knowledge/00_inbox/` 作为待提纯内容
  4. 由 `collect_to_inbox` 每日 2:30 提取各目录内容转入收件箱，再由 `inbox_refine` 技能每日凌晨 3:00 自动提纯归档
  5. 或手动说"提纯"立即执行

### 2. 知识重分类（reclassify）
- 当知识的 nature 属性变更时（如 opinion → fact）：
  1. 更新 Frontmatter 中 nature 和 status
  2. 将文件从旧目录移动到新目录
  3. 自动更新 Obsidian 内链
  4. 记录到 04_memory/logs/kb_reclassify.log

### 3. 知识检索（kb_query）
- 检索流程：
  1. 先在 L2 摘要层检索（SQLite 索引）
  2. 命中后按需加载知识文件指定行号片段
  3. 不加载整个文件，节省 token

### 4. 知识备份（kb_backup）
- 全量备份 03_knowledge/ 目录到指定位置
- 支持增量备份（仅备份变更文件）

## 入库规范

### Frontmatter 必填字段

```yaml
---
id: KB-YYYYMMDD-NNN
title: "知识标题"
type: concept|method|fact|reference|resource|opinion
status: draft|review|published|archived
nature: fact|opinion|method|regulation|reference|data|quote|axiom
domain: [领域1, 领域2]
confidence: 0.0-1.0
source: "原始来源 URL"
date_created: YYYY-MM-DD
date_modified: YYYY-MM-DD
version: 1
---
```

### 可选字段

```yaml
subdomain: [子领域]
tags: [标签列表]
author: 作者
source_type: personal_exp|literature|webpage|conversation|code|observation
related: [KB-ID 列表]
previous_version: KB-ID
superseded_by: KB-ID
aliases: [别称]
keywords: [关键词]
summary: 一句话摘要
```

## 预定义领域列表

计算机科学, 人工智能, 金融, 法律, 医学, 物理, 数学, 心理学, 哲学, 历史, 工程, 设计, 商业, 个人管理, 个人洞见, 其他

> 当"其他"类别超过 5% 时，memory_manager 技能会提示新增领域

## 文件结构

```
kb_manager/
├── SKILL.md
├── kb_ingest.py           # 知识入库脚本
├── kb_query.py            # 知识检索脚本
├── kb_backup.py           # 知识备份脚本
├── kb_reclassify.py       # 知识重分类脚本
└── version.json
```

## 依赖

| 包 | 用途 | 安装状态 |
|---|---|---|
| trafilatura | 网页内容提取 | ✅ 已安装 |
| chromadb | 向量存储（备选语义检索） | ✅ 已安装 |
| sqlite-utils | 数据库操作 | ✅ 已安装 |

## 自动分类标准

- nature 字段：fact / opinion / method / regulation / reference / data / quote / axiom
- domain 字段：从预定义领域列表选择 1-3 个
- confidence 评分：官方文档 0.8+、个人博客 0.4-0.6、推测 < 0.4

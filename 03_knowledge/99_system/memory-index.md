---
id: KB-SYS-MEMORY
title: "记忆系统索引"
type: reference
date_created: 2026-05-03
date_modified: 2026-05-03
description: "AgentOS 记忆系统结构总览——所有记忆组件的入口"
---

# 🧠 记忆系统索引

> 记忆系统位于 `04_memory/`，本文档提供从 Obsidian 访问记忆的入口。
> 每日记忆摘要已通过软链接同步到 `01_daily/memory/`，可在 Obsidian 直接全文搜索。

---

## 一、记忆组件一览

| 组件 | 位置 | 格式 | 说明 | 可搜索？ |
|------|------|------|------|---------|
| **每日摘要** | [[01_daily/memory/]] | Markdown | 每日对话提炼的关键事实 | ✅ Obsidian全文搜索 |
| **跨机器注册表** | `04_memory/cross_machine/registry/` | JSON | 各机器的注册信息 | ❌ 
| **L1 关键词索引** | `04_memory/long_term/` | JSON | BM25 关键词索引 | ❌ 
| **L2 结构化事实** | `04_memory/long_term/facts.db` | SQLite | 带置信度的事实数据 | ❌ 
| **L3 原文存档** | `agent-local/memory/raw/` | Markdown | 原始对话记录 | ❌（不同步）|
| **错误日志** | `04_memory/logs/` | 文本 | 错误记录 | ❌ |
| **工作日志** | `04_memory/daily_logs/` | Markdown | 夜间自动化执行记录 | ⏳ 规划中 |

---

## 二、每日摘要索引

| 日期 | 摘要 | 状态 |
|------|------|------|
| 2026-05-03 | — | ⏳ 今夜自动化生成 |

---

## 三、在 Obsidian 中搜索记忆

### 方式1：全文搜索（Obsidian 原生）

```
搜索范围: 01_daily/memory/ 下的所有 .md 文件
操作方法: Cmd+Shift+F → 输入关键词
搜索对象: 每日摘要中的关键事实
```

### 方式2：语义搜索（对话中发起）

```
说: "搜一下记忆，关于[关键词]"
底层: ChromaDB 向量检索 + BM25 关键词
效果: 理解语义，搜到相关记忆条目
```

### 方式3：查看索引

```
本页面提供全部记忆组件的链接和说明。
可以直接点击 [[01_daily/memory/]] 浏览所有每日摘要。
```

---

## 四、记忆系统架构

详见 [[99_system/architecture/loading-architecture|加载与检索架构]]（管道④：记忆系统分层检索）

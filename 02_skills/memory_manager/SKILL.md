---
name: memory_manager
version: 1.2.0
description: 智能体记忆管理技能——每日对话提炼、去重、冲突检测、版本管理、记忆导入导出、语义检索
triggers:
  - 记忆管理
  - 记忆更新
  - 每日摘要
  - 每日提炼
  - 对话提炼
  - 整理记忆
  - 记忆去重
  - 冲突检测
  - 知识版本
  - 记忆备份
  - 记忆导出
  - 记忆检查
  - 查记忆
  - 语义检索
  - 记忆搜索
  - 搜索记忆
  - update memory
---

# Memory Manager 技能

## 概述

管理 AgentOS 的 L0→L1→L1_vec→L2→L3 五级记忆体系统，负责每日对话提炼、去重、冲突消解、版本管理、语义检索和记忆导入导出。

## 核心能力

### 1. 每日对话提炼（daily_digest）
- 触发方式：每日凌晨 2:00 自动执行，或手动触发
- 输入：昨日所有对话记录
- 处理流程：
  1. 提取关键事实（who/what/when/where/decision）
  2. 去重（对比 L2 已有事实，相似度 > 0.9 则跳过）
  3. 冲突检测（新事实与旧事实矛盾？→ 标记 OVERRIDE 或提示用户确认）
  4. 生成摘要（100-200 字/条）
  5. 更新 L1 关键词索引（仅写入 L2 成功的事实，避免孤儿索引）
  6. 更新 L1_vec 向量索引（ChromaDB + oMLX embedding，新事实自动向量化）
  7. 关键对话原文 → 压缩后写入 L3
- 输出：
  - 更新 04_memory/daily_summaries/YYYY-MM-DD.md
  - 更新 04_memory/long_term/facts.db
  - 更新 04_memory/vector_db/keyword_index.json
  - 更新 04_memory/vector_db/chroma/（ChromaDB 向量库）
  - 发送摘要到 Obsidian 01_daily/ 日记

### 2. 冲突消解（memory_cleanup）
- 冲突检测优先级：新事实 > 旧事实，用户明确修正 > 系统推断
- 三种变化处理：
  - 硬事实改变 → 更新原卡片，旧值写入 previous_version
  - 软升级/延伸 → 保留 V1，新建 V2，通过 related 双向链接
  - 观点→事实 → 更新 nature 字段，通知 kb_manager 移动文件

### 3. 记忆导入导出
- export_memories.py：将记忆打包为 JSON + Markdown 压缩包
- import_memories.py：从压缩包恢复记忆，合并时智能去重

### 4. 语义检索（semantic_search）
- BM25 关键词检索 + 向量语义检索 + RRF 加权融合
- 向量引擎：ChromaDB（持久化）+ oMLX Qwen3-Embedding-0.6B（1024维）
- 融合策略：Reciprocal Rank Fusion (RRF)，BM25 权重 0.4 / 向量权重 0.6
- CLI 用法：
  - 检索：`python3 semantic_search.py search --root ~/agent-os --query "查询内容" --top-k 5`
  - 回填：`python3 semantic_search.py backfill --root ~/agent-os`
  - 重建：`python3 semantic_search.py rebuild --root ~/agent-os`
  - 测试：`python3 semantic_search.py embed --root ~/agent-os --text "测试"`

## 文件结构

```
memory_manager/
├── SKILL.md                 # 本文件
├── daily_digest.py          # 每日对话提炼脚本
├── semantic_search.py       # BM25 + 向量语义混合检索
├── memory_cleanup.py        # 冲突消解与过期记忆清理
├── agent_memory_init.py     # 首次初始化记忆体
├── bootstrap_from_memory.py # 冷启动：历史数据全量导入
├── export_memories.py       # 记忆导出（JSON + L3 原文）
├── import_memories.py       # 记忆导入（智能去重合并）
└── version.json
```

## 使用说明

> **Python 路径**：所有脚本使用 agent-os 专用虚拟环境
> `/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3`

1. 初始化：`python3 agent_memory_init.py --root ~/agent-os`
2. 冷启动：`python3 bootstrap_from_memory.py --root ~/agent-os`
3. 每日提炼：`python3 daily_digest.py --root ~/agent-os --date YYYY-MM-DD`
4. 冲突清理：`python3 memory_cleanup.py --root ~/agent-os`
5. 导出记忆：`python3 export_memories.py --root ~/agent-os --output ~/backup/`
6. 导入记忆：`python3 import_memories.py --root ~/agent-os --input ~/backup/memories.zip`

## 数据源

| 数据源 | 路径 | 说明 |
|--------|------|------|
| Claw 工作日志 | `~/WorkBuddy/Claw/.workbuddy/memory/YYYY-MM-DD.md` | 每次对话后自动写入 |
| WorkBuddy 系统画像 | `~/.workbuddy/memery/*.md` | 系统自动维护 |
| 上轮摘要 | `04_memory/daily_summaries/YYYY-MM-DD.md` | 防丢失兜底 |

## 自动化

- WorkBuddy 自动化「AgentOS 每日记忆提炼」已配置：每日凌晨 2:00 执行
- 命令：`/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3 ~/agent-os/02_skills/memory_manager/daily_digest.py --root ~/agent-os`

## 依赖

| 包 | 用途 | 安装状态 |
|---|---|---|
| sqlite3 | L2 事实库 | ✅ 标准库 |
| sqlite-utils | SQLite 增强 | ✅ 已安装 |
| rank_bm25 | BM25 关键词检索 | ✅ 已安装 |
| chromadb | 向量存储与检索 | ✅ 1.5.8 |
| numpy | 向量计算 | ✅ 2.4.4 |
| requests | HTTP 客户端（embedding API） | ✅ 已安装 |
| json/re/os/argparse | 基础 | ✅ 标准库 |

## 向量检索依赖

| 组件 | 说明 |
|------|------|
| oMLX API | localhost:8000/v1/embeddings |
| 模型 | Qwen3-Embedding-0.6B（1024 维） |
| 向量库 | ChromaDB，持久化到 04_memory/vector_db/chroma/ |

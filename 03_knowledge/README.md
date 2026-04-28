---
id: KB-HOME
title: "AgentOS 知识库"
type: homepage
date_created: 2026-04-25
date_modified: 2026-04-25
description: "AgentOS 智能体操作系统知识库首页——中文映射 + 目录导览"
---

# 📚 AgentOS 知识库

> 本知识库采用**英文目录 + 中文映射**体系，按知识属性分层存储。
> Vault 路径：`~/agent-os/03_knowledge/` | Obsidian 已绑定此目录

---

## 🗂 目录结构

| 英文目录 | 中文名称 | 说明 | 知识属性 |
|----------|----------|------|----------|
| [[00_inbox]] | 📥 收件箱 | 0 | — |
| 📅 日记 | 0 | — |
| 💡 概念层 | 1 | 2026-04-28 |
| 🔧 方法层 | 0 | — |
| 📋 事实层 | 0 | — |
| 📎 参考层 | 0 | — |
| 🛠 资源层 | 0 | — |
| 💭 观点层 | 0 | — |
| 🗄 归档层 | 0 | — |
| **总计** | **1** | — |

---

## 🏷 知识属性分类

| nature 值 | 中文名 | 目标目录 | 可信度 |
|-----------|--------|----------|--------|
| fact | 事实 | 30_facts/ | 1.0 |
| method | 方法 | 20_methods/ | 1.0 |
| concept | 概念 | 10_concepts/ | 0.8 |
| regulation | 规章 | 30_facts/ | 1.0 |
| reference | 参考 | 40_references/ | 0.7 |
| data | 数据 | 30_facts/ | 0.9 |
| opinion | 观点 | 60_opinions/ | 0.5 |
| quote | 引用 | 60_opinions/ | 0.6 |
| axiom | 公理 | 10_concepts/ | 1.0 |

---

## 🌍 领域分类

| 英文目录名 | 中文名 | 典型子领域 |
|------------|--------|-----------|
| cs | 计算机科学 | 数据库、前端、后端、运维、安全 |
| ai | 人工智能 | NLP、CV、强化学习、RAG、Agent |
| finance | 金融 | 量化交易、价值投资、宏观经济 |
| law | 法律 | 民法、商法、知识产权 |
| medicine | 医学 | 中医、西医、营养学 |
| physics | 物理 | 量子力学、相对论、热力学 |
| math | 数学 | 线性代数、概率统计、微积分 |
| psychology | 心理学 | 认知心理学、社会心理学 |
| philosophy | 哲学 | 认识论、伦理学、美学 |
| history | 历史 | 中国史、世界史、科技史 |
| engineering | 工程 | 机械、电子、土木 |
| design | 设计 | UI/UX、平面设计、建筑设计 |
| business | 商业 | 管理、营销、战略 |
| personal-management | 个人管理 | GTD、时间管理、习惯 |
| personal-insight | 个人洞见 | 反思、决策记录 |

---

## 🔄 工作流

```
收集内容 → 各分类目录（视频笔记/阅读笔记/灵感素材/...）
                ↓
    每日汇聚（collect_to_inbox 技能，凌晨 2:30 自动执行）
                ↓
    00_inbox/（收件箱，标准化 MD）
                ↓
    每日提纯（inbox_refine 技能，凌晨 3:00 自动执行）
                ↓
    分类 → 按nature+domain写入对应目录
                ↓
    更新本首页统计 + CHANGELOG.md
```

### 提纯规则
1. **分类目录 → 收件箱**：collect_to_inbox 每日 2:30 扫描各分类目录，提取主要内容转入 00_inbox/
2. **inbox → 分类**：inbox_refine 每日 3:00 读取 00_inbox/ 所有 .md，按 nature + domain 分类到目标目录
2. **去重**：与已有知识对比，重复内容合并/更新
3. **模板化**：应用对应知识卡片模板（99_system/templates/）
4. **ID 生成**：格式 `KB-YYYYMMDD-NNN`
5. **首页更新**：刷新统计数字和最近更新时间

---

## 📌 快速链接

- [[CHANGELOG]] — 知识库变更日志
- [[99_system/templates/|卡片模板]] — 4种知识卡片模板
- [[99_system/taxonomies/domains|领域分类表]] — 16个一级领域
- [[99_system/taxonomies/nature-types|属性分类表]] — 9种nature类型 + 决策树

---

## 🤖 本地 LLM

> oMLX v0.3.6 已部署（基于 Apple MLX 框架），API 端口 `localhost:8000`，API Key: `omlx`

| 模型 | 类型 | 量化 | 大小 | 用途 |
|------|------|------|------|------|
| Qwen3-8B-MLX-4bit | LLM | Q4_K_M | 4.26 GB | 中文理解/生成，知识提纯 |
| Qwen2.5-VL-3B-Instruct-8bit | VLM | 8bit | 3.9 GB | 多模态理解（图文） |
| Qwen3-Embedding-0.6B | Embedding | bf16 | 1.19 GB | 向量嵌入（1024维），语义检索 |

> ⚠️ Ollama 已停用，本地推理统一走 oMLX。模型目录：`~/.omlx/models/`

---

*最后更新：2026-04-25 by Claw（oMLX 迁移 + Embedding/VLM 模型下载）*

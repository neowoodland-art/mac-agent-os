---
id: KB-HOME
title: "AgentOS 知识库"
type: homepage
date_created: 2026-04-25
date_modified: 2026-05-03
description: "AgentOS 智能体操作系统知识库首页——中文映射 + 目录导览 + 工具链总览"
---

# 📚 AgentOS 知识库

> 本知识库采用**英文目录 + 中文映射**体系，按知识属性分层存储。
> Vault 路径：`~/workbuddy-agent-os/agent-sync/03_knowledge/` | Obsidian 已绑定此目录

---

## 🗂 目录结构

| 英文目录 | 中文名称 | 文件数 | 最后更新 |
|----------|----------|--------|----------|
| [[00_inbox]] | 📥 收件箱（待提纯） | 3 | 2026-05-03 |
| [[01_submissions]] | 📤 提交箱（待归集） | 3 | 2026-05-03 |
| [[10_concepts]] | 💡 概念层 | 4 | 2026-05-03 |
| [[20_methods]] | 🔧 方法层 | 3 | 2026-05-01 |
| [[30_facts]] | 📋 事实层 | 0 | — |
| [[40_references]] | 📎 参考层 | 0 | — |
| [[50_resources]] | 🛠 资源层 | 0 | — |
| [[60_opinions]] | 💭 观点层 | 0 | — |
| [[90_archive]] | 🗄 归档层 | 1 | 2026-05-03 |
| **总计** | | **14** | **2026-05-03** |

---

## 📖 知识导览

### 💡 概念层（10_concepts/）

| # | 知识条目 | 来源 | 日期 |
|---|---------|------|------|
| 1 | [[10_concepts/social-wisdom-10-rules\|十条社会处世智慧]] | 抖音@袁本初有干货 | 2026-05-03 |
| 2 | [[10_concepts/power-of-naming-reality\|命名现实的力量——情绪叙事与精神图腾]] | ghai 个人洞察 | 2026-05-03 |
| 3 | [[10_concepts/global-accounting-strategic-loss\|全局算账——主动亏损与战略放弃]] | ghai 个人洞察 | 2026-05-03 |

### 🔧 方法层（20_methods/）

| # | 知识条目 | 说明 |
|---|---------|------|
| 1 | [[20_methods/Redmi-12C_20260501_agentos_upgrade\|agentos 升级流程]] | 统一模块升级标准流程 |
| 2 | [[20_methods/Redmi-12C_20260501_auth_manager\|auth_manager 认证模块]] | 多账号登录管理 |
| 3 | [[20_methods/Redmi-12C_20260501_camoufox_fix\|Camoufox 反检测修复]] | 浏览器指纹伪装修复记录 |

### 📥 待处理箱

| 箱 | 数量 | 查看 |
|----|------|------|
| 收件箱（00_inbox/） | 3 条待提纯 | [[00_inbox/]] |
| 提交箱（01_submissions/） | 3 条待归集 | [[01_submissions/]] |

### 🗄 归档（90_archive/）

| # | 条目 | 说明 |
|---|------|------|
| 1 | [[90_archive/deprecated/2026-04-28_测试_LLM_分类器\|测试LLM分类器]] | 测试文件已归档 |

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

## 🔄 工作流（v2.0）

```
"收集这个..." → 知识类 → 01_submissions/（提交箱）
"收集素材..." → 素材类 → agent-local/materials/
                      ↓
          每日 02:00 归集（collect_to_inbox）
          01_submissions/ → 00_inbox/
                      ↓
          每日 02:30 提纯（inbox_refine）
          00_inbox/ → AI 分类 → 按 nature 写入对应目录
                      ↓
          更新首页统计 + CHANGELOG.md
```

### 完整规范
详见：[[99_system/pipelines/content-collection-pipeline|内容收集全链路规范 v2.0]]

---

## 📌 快速链接

- [[CHANGELOG]] — 知识库变更日志
- [[99_system/templates/|卡片模板]] — 4种知识卡片模板
- [[99_system/taxonomies/domains|领域分类表]] — 16个一级领域
- [[99_system/taxonomies/nature-types|属性分类表]] — 9种nature类型 + 决策树
- [[99_system/pipelines/content-collection-pipeline|内容收集全链路规范]] — 完整采集→入库流程定义
- [[99_system/architecture/loading-architecture|加载与检索架构]] — 四管道加载体系
- [[99_system/architecture/trigger-matching-analysis|触发词匹配方案分析]] — 关键词vs语义对比
- [[99_system/protocols/meta-thinking|高阶思维协议]] — 升维思考/本质追问
- [[99_system/protocols/cross-domain|跨域联想协议]] — 跨界类比/新视角
- [[99_system/protocols/stuck-intervention|卡壳干预协议]] — 遇卡壳暂停给选项
- [[99_system/protocols/knowledge-review|知识审查协议]] — 知识入库审查流程

---

## 🤖 本地 LLM

> oMLX v0.3.6 已部署（基于 Apple MLX 框架），API 端口 `localhost:8000`，API Key: `omlx`

| 模型 | 类型 | 量化 | 大小 | 用途 |
|------|------|------|------|------|
| Qwen3-8B-MLX-4bit | LLM | Q4_K_M | 4.26 GB | 中文理解/生成，知识提纯 ⚠️ Chat API 已知 500 错误（需先调模型再回复） |
| Qwen2.5-VL-3B-Instruct-8bit | VLM | 8bit | 3.9 GB | 多模态理解（图文）✅ 正常 |
| Qwen3-Embedding-0.6B | Embedding | bf16 | 1.19 GB | 向量嵌入（1024维），语义检索 ✅ 正常 |

> ⚠️ Ollama 已停用，本地推理统一走 oMLX。模型目录：`~/.omlx/models/`
>
> ⚠️ 本机 oMLX + Qwen3-8B 的 Chat API 有多步兼容问题（tool call 结果回传时 500 错误），如需稳定多步推理建议使用 TRAE SOLO CN 桌面版。

---

## 🛠 工具链总览（2026-05-03）

| 工具 | 路径 / 位置 | 状态 | 说明 |
|------|-------------|------|------|
| **TRAE SOLO CN 桌面版** | `/Applications/TRAE SOLO CN.app` | ✅ 主力 | AI IDE，内置 integrated_browser（21个工具） |
| **trae_controller 技能** | `~/.workbuddy/skills/trae_controller/` | ✅ 已就绪 | 触发词：trae执行/调用trae/让trae做 |
| **agentos CLI** | `05_tools/00_setup/agentos/` | ✅ v2.3.0 | 系统管理：init/sync/skill/tool/check/backup/register |
| **trae-agent CLI** | `05_tools/08_trae_agent/` | ⚠️ 搁置 | 因 oMLX 多步兼容性问题不可用 |
| **Colima / Docker** | `~/.local/bin/` | ⚠️ 半就绪 | 二进制就绪，网络好时 `colima start` |
| **Git 双远程** | Gitee + GitHub | ✅ 已配置 | 主电脑双推，其他单推 Gitee |

---

*最后更新：2026-05-03 by Claw（知识库全面清理 + v2.0 流程 + 工具链更新）*

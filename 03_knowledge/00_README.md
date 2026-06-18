# AgentOS 知识库结构

> 最后更新: 2026-06-17
> 目标: 所有系统相关文档统一在 `99_system/` 下，非系统内容按原分类不变

---

## 顶层分类

| 目录 | 用途 | 包含内容 |
|:-----|:-----|:---------|
| `00_inbox` | 待处理收件箱 | 未分类的碎片内容 |
| `00_stream/` | 信息流原始采集 | feed/clipping/media 等原始素材 |
| `01_daily/` | 日常日志 | 每日工作记录 |
| `01_submissions/` | 外部投稿/采集 | 按来源分目录（创作者名/设备名） |
| `10_concepts/` | 概念知识 | 设计理念、个人管理方法论 |
| `20_methods/` | 方法技能 | AI视频系统、拍摄技巧、工具教程 |
| `30_facts/` | 事实数据 | 结构化事实（当前空） |
| `40_references/` | 参考资料 | 文档、论文 |
| `50_resources/` | 资源索引 | 工具链接、书单（当前空） |
| `60_opinions/` | 个人观点 | 思考笔记（当前空） |
| `90_archive/` | 归档 | 已失效或替换的旧文档 |
| `99_system/` | **系统架构知识** | AgentOS 联邦系统全部架构/设计/协议文档 |

---

## 🔴 99_system/ — 系统架构知识

所有与 AgentOS 联邦系统、Dashboard、矩阵养号、采集、自动化相关的文档都集中在这里。

### 子目录结构

```
99_system/
├── README.md                   ← 本目录索引
│
├── architecture/               ← 架构设计文档
│   ├── federated-multi-machine-architecture.md
│   ├── federation-operations-architecture.md
│   ├── login-system-tech-map.md
│   ├── trigger-matching-analysis.md
│   ├── loading-architecture.md
│   └── IMPLEMENTATION-PLAN-v1.md
│
├── matrix/                     ← 矩阵养号系统（从 04_ops/matrix 移入）
│   ├── matrix-nurture-system-architecture.md
│   ├── matrix-known-pitfalls.md
│   ├── matrix-v6-product-plan.md
│   ├── douyin-comment-automation.md
│   ├── xhs-browse-interaction-techniques.md
│   └── 指纹分辨率触发XHS_AI布局版本.md
│
├── dashboard/                  ← Dashboard 看板设计
│   ├── dashboard-v4-design.md
│   └── (待迁移: PLANS/BUSINESS_ARCHITECTURE_v4.md)
│
├── agent-os-memory-knowledge-architecture.md
├── memory-index.md
│
├── pipelines/                  ← 自动化流程
│   └── content-collection-pipeline.md
│
├── prompts/                    ← 智能体提示词
│   └── classify-knowledge.md
│
├── protocols/                  ← 协议/规范
│   ├── cross-domain.md
│   ├── knowledge-review.md
│   ├── meta-thinking.md
│   └── stuck-intervention.md
│
├── taxonomies/                 ← 分类法
│   ├── domains.md
│   └── nature-types.md
│
├── templates/                  ← 知识卡片模板
│   ├── concept-card.md
│   ├── fact-card.md
│   ├── method-card.md
│   └── personal-insight-card.md
│
├── archive/                    ← 已归档的旧系统文档
│   ├── CORE-ARCHITECTURE.md
│   ├── QUICKSTART.md
│   └── SKILLS-CATALOG.md
│
└── timelines/                  ← 时间线
```

---

## 📋 非系统内容分类指南

| 分类 | 适合放什么 | 例子 |
|:-----|:----------|:-----|
| `10_concepts/` | 通用概念、理念 | 设计思维、个人管理方法论 |
| `20_methods/` | 操作方法、技能 | AI视频教程、拍摄技巧、工具用法 |
| `30_facts/` | 结构化数据 | 参数对照表、配置参考 |
| `40_references/` | 外部资料 | 论文、官方文档、书籍摘录 |
| `50_resources/` | 资源索引 | 工具清单、书单、网站收藏 |
| `60_opinions/` | 个人思考 | 复盘、观点、感悟 |

---

## ⚠️ 注意事项

1. **系统文档必须放 `99_system/`**，不要放 `04_ops/` 或其他地方
2. `04_ops/` 目录将重定向到 `99_system/matrix/`
3. 日常使用中，新的系统架构决策直接写入 `99_system/architecture/`
4. `01_daily/` 只放每日日志，不放架构文档

# 🧠 AgentOS AI 阅读指南

> 每次启动任务时，先读此文件了解知识库结构。

## 知识库结构

```
03_knowledge/
├── 00_inbox/          ← 待提纯收件箱（每日采集暂存）
├── 01_submissions/    ← 待归集提交箱（按来源分目录，23个文件）
├── 10_concepts/       ← 概念知识（19个）
├── 20_methods/        ← 方法技能（140个，含AI视频系统19章）
├── 30_facts/          ← 事实数据
├── 40_references/     ← 参考资料（9个）
├── 50_resources/      ← 资源索引
├── 60_opinions/       ← 个人观点
├── 90_archive/        ← 归档
└── 99_system/         ← 🆕 系统文档集中存放
    ├── architecture/  ← 联邦架构、登录系统、触发分析
    ├── matrix/        ← 矩阵养号系统文档
    ├── references/    ← 系统引用（CloakBrowser, Peekaboo等）
    ├── dashboard/     ← Dashboard 设计文档
    ├── protocols/     ← 协议规范（cross-domain, knowledge-review等）
    ├── pipelines/     ← 自动化管线
    ├── prompts/       ← 智能体提示词
    ├── taxonomies/    ← 分类法
    ├── templates/     ← 知识卡片模板
    └── archive/       ← 归档旧文档
```

## 任务类型 → 查阅目录

| 任务类型 | 查阅目录 | 说明 |
|:---------|:---------|:-----|
| 矩阵养号 | `99_system/matrix/` | 养号架构、蓝图、原子操作、登录体系 |
| 知识入库 | `99_system/protocols/` (knowledge-review) | 入库审查流程 |
| 跨域联想 | `99_system/protocols/` (cross-domain) | 跨域联想协议 |
| 元思考 | `99_system/protocols/` (meta-thinking) | 元认知框架 |
| 卡住干预 | `99_system/protocols/` (stuck-intervention) | 卡住恢复策略 |
| AI视频 | `20_methods/` (ai-video-system/) | 19章完整体系 |
| 系统架构 | `99_system/architecture/` | 联邦架构设计 |
| 知识卡片 | `99_system/templates/` | 卡片模板 |

## 使用规范

1. **不要重复创建**：查知识库前先搜索已有内容
2. **记忆体 vs 知识**：日期前缀文件是 `memory_triage` 输出的记忆体，不是知识。知识是无日期的概念/方法/事实
3. **系统文档**：所有系统架构/设计/协议文档都在 `99_system/` 下
4. **先读指南**：每次启动先读此文件

## 变更日志

| 日期 | 变更 |
|:----|:-----|
| 2026-06-18 | 创建 AI_READING_GUIDE.md |
| 2026-06-18 | 04_ops/ → 99_system/matrix/ |
| 2026-06-18 | 去重删除 ~130 个重复文件 |

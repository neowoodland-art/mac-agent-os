# CORE-ARCHITECTURE.md —— AgentOS v2.0 基准定义

最后更新：2026-04-28

本文档是 AgentOS v2.0 的正式基准。后续若其他大体量说明与本文冲突，以本文为准。

## 1. v2.0 的定位

AgentOS v2.0 是一套运行在 WorkBuddy 上的本地优先个人智能体外骨骼系统。

它不是最早的单机原形复刻，也不是未来多机协同终态，而是当前仓库中已经落地并可恢复的一版稳定基准。

v2.0 只做三件事：

- 冻结当前可运行结构
- 明确同步与本地边界
- 统一文档口径，避免把未来升级方案混入当前实现

## 2. 根目录模型

### 2.1 `~/workbuddy-agent-os/agent-sync/`

作用：同步与版本化的主仓库。

应放入：

- 核心配置
- 技能层
- 知识库
- 共享记忆元数据
- 工具脚本
- 迁移脚本
- 说明文档

### 2.2 `~/workbuddy-agent-os/agent-sync/agent-local/`

作用：本机私有数据区，不进入主仓库，不作为 v2.0 的主文档对象，但作为正式运行边界的一部分存在。

应放入：

- L3 原文
- 向量库
- 临时缓存
- 原始素材
- 已提炼待投递素材

## 3. 目录职责

| 目录 | v2.0 职责 | 是否共享 |
|------|-----------|----------|
| `00_bootstrap/` | 初始化、部署、导入导出 | 是 |
| `01_core/` | SOUL、IDENTITY、USER、MCP 配置 | 是 |
| `02_skills/` | WorkBuddy 技能层 | 是 |
| `03_knowledge/` | Obsidian 知识库 | 是 |
| `04_memory/` | 事实库、摘要、日志与本地挂载点 | 部分共享 |
| `05_tools/` | 公共工具层 | 是 |
| `06_runtime/` | 任务记录与缓存挂载点 | 部分共享 |
| `07_migration/` | 打包、解包、备份 | 是 |

## 4. 本地挂载与共享边界

### 4.1 正式共享内容

以下内容属于 v2.0 的共享资产：

- `01_core/`
- `02_skills/`
- `03_knowledge/`
- `04_memory/long_term/facts.db`
- `04_memory/daily_summaries/`
- `04_memory/logs/`
- `05_tools/`
- `06_runtime/tasks/`
- `07_migration/`

### 4.2 正式本机私有内容

以下内容属于 v2.0 的本机私有资产：

- `04_memory/long_term/raw/`
- `04_memory/vector_db/`
- `06_runtime/cache/`
- `~/workbuddy-agent-os/agent-sync/agent-local/materials/`

### 4.3 软链接映射

当前正式映射如下：

```text
~/workbuddy-agent-os/agent-sync/04_memory/long_term/raw  -> ~/workbuddy-agent-os/agent-sync/agent-local/memory/raw
~/workbuddy-agent-os/agent-sync/04_memory/vector_db      -> ~/workbuddy-agent-os/agent-sync/agent-local/memory/vector_db
~/workbuddy-agent-os/agent-sync/06_runtime/cache         -> ~/workbuddy-agent-os/agent-sync/agent-local/runtime/cache
```

`init.sh` 负责重建这些映射。

## 5. v2.0 的正式数据流

### 5.1 知识流

v2.0 明确定义为“双入口汇聚到 Inbox”。

入口 A：直接入 Inbox

- 已经标准化的内容可以直接写入 `03_knowledge/00_inbox/`

入口 B：分类目录汇聚

- 内容先写入 `50_resources/`、`01_daily/`、`20_methods/`、`40_references/` 等目录
- 再由 `collect_to_inbox` 汇聚进 `00_inbox/`

统一出口：

- `inbox_refine` 将 `00_inbox/` 内容提纯归档到知识库目标目录

因此，v2.0 不再把这两种入口视为冲突，而是视为同一流水线的两种合法前置路径。

### 5.2 记忆流

当前记忆流为：

```text
WorkBuddy 工作日志 / 系统画像 / 上轮摘要
        -> daily_digest.py
        -> facts.db
        -> keyword_index.json / ChromaDB
        -> 原文写入本机私有 raw/
```

### 5.3 工具流

`05_tools/` 是工具层，不等于技能层。

v2.0 允许在工具层中存在：

- 系统检查脚本
- 抓取工具
- 媒体处理脚本
- 独立小项目

但这些工具默认不自动视为对话技能。

## 6. 技能分类

### 6.1 system 技能

system 技能是架构层约定，表示后台自动运行或以系统流程为主：

- `memory_manager`
- `collect_to_inbox`
- `inbox_refine`
- `auto_collector`
- `kb_manager`
- `sync_manager`

### 6.2 user 技能

user 技能是对话直接触发的入口层：

- `content_processor`
- `web_crawler`

### 6.3 约束说明

v2.0 仅把 system / user 作为文档级约定。

以下能力不在 v2.0 强制落地：

- `category` 元数据全量补齐
- `SKILL_CARD.yaml`
- `skill_scanner.py`

这些属于后续版本。

## 7. 初始化与恢复基准

v2.0 的正式恢复步骤如下：

```bash
cd ~/workbuddy-agent-os/agent-sync/00_bootstrap
bash init.sh
bash apply-config.sh
bash import_skills.sh

~/.workbuddy/binaries/python/envs/agent-os/bin/python3 \
    ~/workbuddy-agent-os/agent-sync/02_skills/memory_manager/bootstrap_from_memory.py \
    --root ~/workbuddy-agent-os/agent-sync
```

手动部分：

- 安装 WorkBuddy
- 安装坚果云
- 按需安装 Obsidian
- 安装 oMLX 与模型

## 8. v2.0 延后项

以下内容明确不属于 v2.0：

- 本地素材统一投递脚本 `collect_from_local.py`
- 技能身份证与统一扫描器
- 工具 manifest 与自动化安装体系
- 更细粒度的多机记忆隔离策略
- 基于 `agent-os-local/materials/` 的全新单入口采集体系

这些内容如果要做，必须以 v2.1 或更高版本单独立项。

## 9. 验收标准

满足以下条件，即视为 v2.0 收口完成：

1. 核心文档不再互相冲突
2. 目录边界和软链接边界明确
3. 恢复步骤可以从文档直接执行
4. 知识流与记忆流可以一句话解释清楚
5. 延后项不再混入当前基准描述

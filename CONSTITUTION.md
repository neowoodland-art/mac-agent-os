# AgentOS 架构宪法

> 版本: 1.0 | 最后更新: 2026-06-21
> 本文件是 AgentOS 联邦智能体操作系统的**架构总纲**。
> **同时部署到: `~/.workbuddy/CONSTITUTION.md`** — WorkBuddy AI 按需加载。
>
> 任何代码开发、文档修改、架构决策之前，先读此文件确定归属层面。
>
> **读完此文件后，你应该能回答：**
> - 这段代码属于哪个层？哪个维度？哪个目录？
> - 开发时应遵守什么硬规则？
> - 版本怎么升？文档怎么维护？
> - 架构变更时还需要更新什么？

---

## 第一章：系统定位

### 1.1 一句话定义

AgentOS 是一个**运行在多台 Mac 上的 AI 智能体联邦操作系统**，给 WorkBuddy AI 装上外骨骼——技能、工具、联邦、看板、自动化、记忆、知识、协议。

### 1.2 核心理念

| 理念 | 含义 |
|:-----|:------|
| **代码走同步，数据留本机** | 脚本在 Git（agent-sync/），数据在本地（agent-local/） |
| **唯一权威源** | 每个信息维度只有一个权威源（01_core/VERSION / ORACLE.yaml / SKILL_CARD.yaml） |
| **三层分离** | TRUTH（人工维护）≠ DERIVED（自动生成）≠ VERIFIED（自动对账） |
| **执行通道五层** | 看板→分发→工具→CLI→执行器，层层分明 |
| **不做空壳** | 有文档无代码的技能/工具→归档，不留在活跃目录 |

---

## 第二章：十二维功能全景

系统由 **3 大子系统 × 12 个功能维度** 构成：

### 子系统 A：智能体增强层（给 WorkBuddy 装外骨骼）

| # | 维度 | 位置 | 加载方式 | 说明 |
|:-:|:-----|:-----|:---------|:-----|
| ① | **身份规则** | `01_core/` → `~/.workbuddy/` | 每次对话常驻 ~750 tokens | SOUL.md（规则+触发词）+ IDENTITY.md + USER.md |
| ② | **行为协议** | `03_knowledge/99_system/protocols/` | 触发词激活 ~200 tokens/个 | meta-thinking / cross-domain / stuck-intervention / knowledge-review |
| ③ | **分层记忆** | `04_memory/` | L1→L2→L3 分层截断 | 关键词索引 + ChromaDB 向量 + facts.db + 原文 |
| ④ | **知识库** | `03_knowledge/`（排除 99_system/） | 按需 BM25+向量检索 | 10_concepts/ 20_methods/ 等自然知识 |

### 子系统 B：执行操作系统（自动化干活）

| # | 维度 | 位置 | 说明 |
|:-:|:-----|:-----|:------|
| ⑤ | **技能** | `02_skills/` | WorkBuddy 可调用的能力。当前 7 活跃 + 4 已归档 |
| ⑥ | **工具** | `05_tools/` | 底层执行脚本。当前 8 活跃 + 4 已清空 |
| ⑦ | **看板** | `05_tools/10_dashboard/` | Web 监控界面（FastAPI 1521 行 + 15 插件） |
| ⑧ | **命令分发** | `services/command_bus.py` | 看板→CommandBus→ORACLE 对账→SSH/本地 |
| ⑨ | **CLI 执行** | `05_tools/00_setup/agentos/` + `07_matrix/mc` | 统一命令行入口 + mc 快捷别名 |
| ⑩ | **蓝图系统** | `05_tools/07_matrix/blueprints/` | 12 个 JSON 操作模板 |

### 子系统 C：联邦治理（多机协同 + 安全 + 进化）

| # | 维度 | 位置 | 说明 |
|:-:|:-----|:-----|:------|
| ⑪ | **多机联邦** | `ORACLE.yaml` + guardd + cross_machine | 3 台 Mac、Git 双远程、WPRA 写分区读聚合 |
| ⑫ | **安全治理** | `01_core/SOUL.md` L0 约束 + RSA-4096 + 私钥隔离 | L0 硬约束禁止操作/必须确认/必须操作 |

---

## 第三章：目录结构与职责

```
agent-sync/
│
├── CONSTITUTION.md              ← [本文件] 架构宪法
│
├── 01_core/                     ← 身份规则层（L0，部署到 ~/.workbuddy/）
│   ├── SOUL.md                   AI 行为规则 + 触发词检测
│   ├── IDENTITY.tpl.md           身份模板（init.sh 填充）
│   ├── USER.md                   用户画像
│   ├── VERSION                   版本唯一来源
│   ├── MAINTENANCE_GUIDE.md      运维手册
│   ├── UPDATE_SYSTEM.md          更新体系
│   ├── NIGHTLY_AUTOMATION.md     夜间自动化
│   ├── mcp.json                  MCP 服务配置
│   ├── CONFIG_MANIFEST.yaml      配置清单
│   ├── automation/               自动化配置入仓
│   └── CHANGELOG.md              core 变更日志
│
├── 02_skills/                   ← 能力层（L2）
│   ├── memory_manager/            记忆管理（核心）
│   ├── inbox_refine/              收件箱提纯
│   ├── collect_to_inbox/          内容归集 [legacy]
│   ├── kb_manager/                知识库管理
│   ├── matrix/                    矩阵养号（实现在 05_tools/）
│   ├── sync_manager/              同步备份
│   ├── peekaboo_controller/       GUI 自动化（MCP）
│   └── _archived/                 已归档技能（4 个）
│
├── 03_knowledge/                ← 知识层（L1+L4）
│   └── 99_system/                系统知识（WorkBuddy AI 按需消费）
│       ├── AI_READING_GUIDE.md     AI 入口
│       ├── protocols/              4 个行为协议
│       ├── architecture/           架构文档
│       ├── matrix/                 矩阵系统文档
│       ├── dashboard/              Dashboard 设计
│       ├── pipelines/              流水线规范
│       ├── prompts/                提示词
│       └── archive/                已归档系统文档
│
├── 04_memory/                   ← 记忆层（L5）
│   ├── long_term/facts.db         L2 事实库
│   ├── cross_machine/             跨机数据
│   └── daily_summaries/           每日摘要
│
├── 05_tools/                    ← 工具层（L3）
│   ├── 00_setup/agentos/          统一 CLI 入口（19 子命令）
│   ├── 00_setup/guardd/           联邦守护进程（9 模块）
│   ├── 01_system/                 系统诊断（12 脚本）
│   ├── 05_crawl/                  内容采集
│   ├── 07_matrix/                 矩阵养号系统
│   ├── 08_trae_agent/             Trae AI 编程助手
│   ├── 09_ave/                    视频工厂
│   └── 10_dashboard/              监控面板
│
├── 99_system/                   ← 项目文档层（维护者视角）
│   ├── INDEX.md                   项目文档索引
│   ├── AGENTOS-PANORAMA.md        系统全景
│   └── upgrade_notes/             升级笔记
│
├── ORACLE.yaml                  ← 联邦宪法
├── FEDERATION_GUIDE.md          ← 联邦实操指南
├── AGENTS.md                    ← AI 项目指令
├── README.md                    ← 人类入口
└── requirements.txt             ← Python 依赖
```

---

## 第四章：硬规则（不可绕过）

### 规则 1：版本唯一来源

```
唯一文件：01_core/VERSION

所有文档和代码中的版本号从此文件读取，不允许硬编码。
guardd.py 在启动时动态读取此文件。

版本规则：
  X.0.0 — 核心框架或联邦架构升级（同时必须更新本 CONSTITUTION.md）
  0.X.0 — 工具级增加或重大升级
  0.0.X — 配置小项目升级、bugfix

Skills 版本：独立 semver，写在 SKILL_CARD.yaml 中
```

### 规则 2：SKILL_CARD.yaml 是技能权威元数据

```
原来：SKILL.md 写描述 + version.json 写版本 → 两处不同步
现在：SKILL_CARD.yaml 为权威，包含 version/scripts/changelog/dependencies
      version.json 保留供 export_skills.sh 读取，但版本以 SKILL_CARD 为准
      SKILL.md 只写人类可读的说明

格式规范参见 02_skills/_template/SKILL_CARD.yaml
```

### 规则 3：ORACLE.yaml 是账号分配唯一源

```
废除 accounts_registry.yaml。
所有账号→机器的分配统一写在 ORACLE.yaml 的 accounts: 节下。
guardd _sync_account_override() 从 ORACLE.yaml 读取。
```

### 规则 4：guardd 心跳只写本地

```
心跳数据仅写入：
  - agent-local/runtime/guardd/events/
  - cross_machine/status/{hostname}/heartbeat.json
  - cross_machine/status/live/{uid}.json

❌ 不再写入 cross_machine/machines/{UID}/heartbeat.json（曾导致 Git 污染）
Dashboard 通过 guardd 的反向连接推送获取心跳。
```

### 规则 5：统一 CLI 入口

```
唯一入口：05_tools/00_setup/agentos/ （python3 -m agentos）

19 个子命令：
  系统管理（14）：init / sync / skill / tool / config / check / backup /
                 upgrade / restore / rebuild-vector / localize / register /
                 cluster-status / cluster-cleanup
  联邦管理（5）：matrix / ave / crawl / fleet / serve

mc 是 matrix 的快捷别名，指向统一 CLI。
07_matrix/scripts/agentos/ 保留作为插件库，不再作为独立入口。
```

### 规则 6：空技能/空工具不留在活跃目录

```
- 4 个空技能已归档到 02_skills/_archived/
- 4 个空工具目录已添加 README 说明清空原因
- 新建技能/工具时：先有实现代码，再写 SKILL.md/SKILL_CARD.yaml
```

### 规则 7：协议文件路径

```
行为协议文件位于：03_knowledge/99_system/protocols/
SOUL.md 中引用的 99_system/protocols/ 是相对于知识库根（03_knowledge/）的路径。

根目录 99_system/ 是项目文档（维护者视角），不含协议文件。
```

### 规则 8：文档三分法

```
TRUTH（人工维护，唯一权威）：
  01_core/（SOUL/USER/MAINTENANCE_GUIDE/mcp.json/VERSION）
  02_skills/*/SKILL_CARD.yaml
  ORACLE.yaml
  CONSTITUTION.md（本文件）

DERIVED（从 TRUTH 自动生成）：
  IDENTITY.md（从模板 + init.sh 生成）
  README.md（精简为入口）

VERIFIED（代码 vs 文档自动对账）：
  agentos check 步骤（模块数/命令数/文件存在性）
```

### 规则 9：文件权限

| 目录 | 权限 | 说明 |
|:-----|:------|:------|
| `01_core/` | 只读 | 通过 `apply-config.sh` 部署 |
| `02_skills/` | 可读写 | 改前确认 |
| `03_knowledge/` | 只读 | 改前确认 |
| `04_memory/` | 只读 | 改前确认 |
| `05_tools/` | 可读写 | 工具脚本 |
| `00_bootstrap/` | 可读写 | 改前确认 |
| `99_system/` | 可读写 | 项目文档 |
| `agent-local/` | 只读 | 本机数据，不同步 |

### 规则 10：禁止操作

```
- 禁止直接修改 01_core/ 下的文件（通过 apply-config.sh 部署）
- 禁止修改 agent-local/ 下的任何文件
- 禁止修改 04_memory/long_term/facts.db
- 禁止删除任何文件（只能归档到 90_archive/）
- 禁止修改 01_core/SOUL.md 中的 L0 硬约束规则本身
- 禁止将 L3 层原文暴露给外部 API 或第三方服务
```

### 规则 11：架构变更必须更新宪法

```
涉及以下任何一项变更时，必须同步更新 CONSTITUTION.md：

1. 新增/删除/合并目录层级
2. 新增/删除功能维度（12 维之外）
3. 修改版本规则
4. 修改文件权限规则
5. 新增/删除硬规则
6. 修改开发决策流程

更新后：
  - 递增 CONSTITUTION.md 版本号（1.0 → 1.1 → ...）
  - 更新 ~/.workbuddy/CONSTITUTION.md（重新部署 apply-config.sh）
  - 更新 99_system/INDEX.md 引用
  - 记录到 CHANGELOG.md
```

---

## 第五章：版本对应关系速查

| 组件 | 版本 | 位置 | 版本显式来源 |
|:-----|:-----|:-----|:------------|
| AgentOS 框架 | 4.2.0 | 整个系统 | `01_core/VERSION` AGENTOS_VERSION |
| guardd | 2.3.0 | `05_tools/00_setup/guardd/` | `01_core/VERSION` GUARDD_VERSION |
| ORACLE schema | 1.0 | `ORACLE.yaml` | `01_core/VERSION` ORACLE_SCHEMA |
| **架构宪法** | **1.0** | **CONSTITUTION.md** | **本文件版本声明** |
| memory_manager | 1.2.0 | `02_skills/memory_manager/` | SKILL_CARD.yaml |
| inbox_refine | 1.1.0 | `02_skills/inbox_refine/` | SKILL_CARD.yaml |
| kb_manager | 1.1.0 | `02_skills/kb_manager/` | SKILL_CARD.yaml |
| collect_to_inbox | 1.0.0 | `02_skills/collect_to_inbox/` | SKILL_CARD.yaml |
| matrix | 1.0.0 | `02_skills/matrix/` + `05_tools/07_matrix/` | SKILL_CARD.yaml |
| sync_manager | 1.1.0 | `02_skills/sync_manager/` | SKILL_CARD.yaml |
| peekaboo_controller | 1.0.0 | `02_skills/peekaboo_controller/` | SKILL.md |

---

## 第六章：开发决策流程

决定「新功能/新代码应该放哪」的流程：

```
1. 确定功能属于哪个子系统：
   ├─ 给 AI 用的？→ 子系统 A（智能体增强）
   ├─ 自动化执行？→ 子系统 B（执行操作）
   └─ 多机协同/安全/进化？→ 子系统 C（联邦治理）

2. 确定具体维度（1-12）：
   从第二章的 12 维全景中找到最匹配的维度

3. 确定目录：
   从第三章的目录结构与职责中找到对应目录

4. 检查硬规则：
   第四章的 10 条规则 + 规则 11（架构变更更新宪法），一条不落

5. 确定版本号：
   - 核心框架/联邦架构变更 → 升大版本 + 更新本宪法
   - 工具级别增加或升级 → 升中版本
   - 配置/bug修复 → 升小版本
   修改 01_core/VERSION 后，更新 CHANGELOG.md

6. 创建文档：
   - 新增技能：必须有 SKILL_CARD.yaml + 实现代码
   - 新增工具：必须有 MODULE.md 或 README.md + 实现代码
   - 架构变更：在 99_system/ 或 03_knowledge/99_system/ 添加
```

---

## 附录 A：术语对照

| 术语 | 含义 |
|:-----|:------|
| AgentOS | 本系统代号 Claw |
| WorkBuddy | AI 宿主平台 |
| SOUL.md | AI 行为规则 + 触发词的最高优先级配置 |
| ORACLE.yaml | 联邦宪法，机器定义+账号分配+任务计划 |
| guardd | 守护进程，每 300 秒执行 9 模块循环 |
| WPRA | Write Partitioned Read Aggregated，写分区读聚合 |
| SKILL_CARD.yaml | 技能权威元数据（版本/依赖/脚本/变更日志） |
| 01_core/VERSION | 版本唯一来源 |
| CONSTITUTION.md | 本文件，架构总纲 |
| cross_machine | 04_memory/cross_machine/ 跨机数据交换目录 |

## 附录 B：快速定位表

| 你想做什么 | 去哪个目录 | 看什么文件 |
|:----------|:-----------|:----------|
| 改 AI 行为规则 | `01_core/` | SOUL.md |
| 改用户画像 | `01_core/` | USER.md |
| 加一个新技能 | `02_skills/` | 参考 _template/ |
| 改技能代码 | `02_skills/<技能名>/` | *.py |
| 改知识库 | `03_knowledge/` | 对应分类目录 |
| 改记忆系统 | `04_memory/` | long_term/ |
| 加一个工具 | `05_tools/<编号>_<名称>/` | 参考同类工具 |
| 改矩阵养号 | `05_tools/07_matrix/` | scripts/ |
| 改看板 | `05_tools/10_dashboard/` | app.py / plugins/ / frontend/ |
| 改守护进程 | `05_tools/00_setup/guardd/` | guardd.py |
| 改 CLI | `05_tools/00_setup/agentos/` | main.py |
| 改联邦宪法 | 根目录 | ORACLE.yaml |
| 改文档索引 | `99_system/` | INDEX.md |
| 增版本号 | `01_core/` | VERSION |
| **查架构总纲** | **根目录** | **CONSTITUTION.md** |

# AgentOS 完整说明文档

> **版本**：v2.1.0 | **最后更新**：2026-04-28 | **作者**：ghai
> **系统环境**：macOS 26.4 / Apple M1 / 16GB RAM / 245GB SSD
> **运行时平台**：WorkBuddy 桌面客户端 + 坚果云 + Obsidian

> 说明：本文件保留为扩展历史说明与细节备忘，不再作为 AgentOS v2.0 的唯一基准。
> 当前正式口径请优先查看 `README.md`、`CORE-ARCHITECTURE.md`、`REVIEW-V2.0.md`。

---

## 目录

1. [系统概述](#一系统概述)
2. [整体架构与目录结构](#二整体架构与目录结构)
3. [核心配置文件详解](#三核心配置文件详解)
4. [初始化与部署](#四初始化与部署)
5. [技能体系详解](#五技能体系详解)
6. [知识库结构详解](#六知识库结构详解)
7. [记忆体系统详解](#七记忆体系统详解)
8. [工具脚本目录](#八工具脚本目录)
9. [运行时与缓存](#九运行时与缓存)
10. [迁移与备份](#十迁移与备份)
11. [自动化任务配置](#十一自动化任务配置)
12. [同步策略详解](#十二同步策略详解)
13. [本地/远程使用方式](#十三本地远程使用方式)
14. [数据流全景](#十四数据流全景)
15. [环境依赖清单](#十五环境依赖清单)
16. [当前运行状态](#十六当前运行状态)
17. [已知问题与待解决项](#十七已知问题与待解决项)
18. [附录：根目录文档索引](#十八附录根目录文档索引)

---

## 一、系统概述

### 1.1 是什么

AgentOS 是一套运行在个人 Mac 上的**智能体外骨骼系统**（AI Agent Operating System），为 AI Agent（Claw 🦀）提供四大基础能力：

| 能力 | 说明 |
|------|------|
| **记忆管理** | L0-L3 五级分层记忆，含关键词索引、向量检索、结构化事实库、原始对话存档 |
| **知识管理** | 基于 Obsidian 的本地知识库，9 种属性分类 × 16 个领域，自动提纯归档 |
| **内容采集** | 多平台自动监控采集（RSS/小红书/抖音/B站/网页），AI 提炼后入库 |
| **多设备协作** | 坚果云实时同步 + Git 版本控制，双轨保障数据安全 |

### 1.2 核心设计理念

- **本地优先**：所有数据存储在本地，坚果云只做同步通道
- **四级记忆截断**：L0→L1→L2→L3，每层不无限 fallback，避免 token 浪费
- **技能驱动**：所有能力封装为技能（Skill），按触发词路由，即插即用
- **结构化输出**：去文学化，先结论后步骤
- **软链接隔离**：本机大文件（向量库/素材/缓存）通过软链接指向独立目录，不进同步

### 1.3 技术栈

| 层级 | 技术选型 |
|------|----------|
| AI 运行时 | WorkBuddy 桌面客户端（CodeBuddy） |
| 本地 LLM | oMLX v0.3.6（Apple MLX 框架） |
| 主力模型 | Qwen3-8B-MLX-4bit（4.26GB，Q4_K_M 量化） |
| 多模态 | Qwen2.5-VL-3B-Instruct-8bit（3.9GB，图文理解） |
| 向量模型 | Qwen3-Embedding-0.6B（1.19GB，1024维） |
| 向量数据库 | ChromaDB 1.5.8 |
| 知识库 | Obsidian（Markdown + Frontmatter） |
| 同步 | 坚果云（实时文件同步） + Gitee（Git 版本控制） |
| Python | 3.13.12（WorkBuddy managed + agent-os venv） |
| Node.js | 22.12.0（WorkBuddy managed） |

---

## 二、整体架构与目录结构

### 2.1 双目录架构

AgentOS 采用**同步目录 + 本机目录**的双轨架构：

```
~/                          用户主目录
├── agent-os/               ← 坚果云同步 + Git 版本控制（核心仓库）
│   ├── 00_bootstrap/           初始化与部署脚本
│   ├── 01_core/                核心配置（部署到 ~/.workbuddy/）
│   ├── 02_skills/              技能包（9个自定义技能 + 1个模板）
│   ├── 03_knowledge/           Obsidian 知识库
│   ├── 04_memory/              四级记忆体
│   ├── 05_tools/               工具脚本
│   ├── 06_runtime/             运行时（缓存通过软链接指向本地）
│   ├── 07_migration/           迁移打包/还原脚本
│   ├── .gitignore
│   ├── README.md / CHANGELOG.md / CORE-ARCHITECTURE.md ...
│   └── requirements.txt
│
├── agent-os-local/         ← 本机专属，不同步，不进 Git
│   ├── memory/                 记忆体数据
│   │   ├── raw/                    L3 对话原文（隐私数据）
│   │   └── vector_db/              ChromaDB + 关键词索引
│   ├── runtime/                运行时数据
│   │   └── cache/                  临时缓存
│   └── materials/              采集的原始素材
│       ├── web/                    网页保存
│       ├── video/                  视频下载
│       ├── audio/                  录音文件
│       ├── screenshots/            截图
│       └── refined_for_inbox/      已提炼待投递的 MD
│
└── .workbuddy/              ← WorkBuddy 运行时配置
    ├── SOUL.md                  L0 最高约束（从 01_core/ 部署）
    ├── IDENTITY.md              身份档案
    ├── USER.md                  用户画像
    ├── mcp.json                 MCP 服务器配置
    ├── skills/                  技能目录（从 02_skills/ 导入）
    ├── binaries/                Python/Node 运行时
    │   ├── python/
    │   │   ├── versions/3.13.12/       Python 二进制
    │   │   └── envs/agent-os/          agent-os 虚拟环境
    │   └── node/
    │       ├── versions/22.12.0/       Node 二进制
    │       └── workspace/node_modules/  全局 npm 包
    ├── automations/             定时自动化任务
    └── memory/                  WorkBuddy 工作记忆
```

### 2.2 软链接映射

`agent-os/` 内通过软链接指向 `agent-os-local/` 中的实际目录，脚本无需改路径：

```
~/workbuddy-agent-os/agent-sync/04_memory/long_term/raw     → ~/workbuddy-agent-os/agent-sync/agent-local/memory/raw
~/workbuddy-agent-os/agent-sync/04_memory/vector_db         → ~/workbuddy-agent-os/agent-sync/agent-local/memory/vector_db
~/workbuddy-agent-os/agent-sync/06_runtime/cache            → ~/workbuddy-agent-os/agent-sync/agent-local/runtime/cache
```

> **为什么用软链接**：大文件（向量库 ~1MB+、L3 原文、视频素材）不应进入坚果云同步和 Git 仓库，通过软链接在逻辑上保持路径一致，物理上存储在本机目录。

### 2.3 完整目录树（agent-os/ 内部）

```
~/workbuddy-agent-os/agent-sync/
├── .gitignore                          (846 B)  Git 忽略规则
├── README.md                           (7.71 KB) 项目主文档
├── CHANGELOG.md                        (3.75 KB) 变更日志
├── CORE-ARCHITECTURE.md                (6.14 KB) 系统架构"宪法"
├── QUICKSTART.md                       (2.87 KB) 5分钟快速上手
├── REQUIREMENTS.md                     (4.85 KB) 环境要求说明
├── SKILLS-CATALOG.md                   (11.38 KB) 技能清单与部署手册
├── requirements.txt                    (2.01 KB) Python 依赖清单
│
├── 00_bootstrap/                       初始化与部署
│   ├── init.sh                         (12.45 KB) 一键初始化脚本
│   ├── apply-config.sh                 (3.31 KB) 核心配置部署
│   ├── export_skills.sh                (1.74 KB) 技能导出为压缩包
│   └── import_skills.sh                (2.60 KB) 技能导入到 WorkBuddy
│
├── 01_core/                            核心配置（部署目标：~/.workbuddy/）
│   ├── CHANGELOG.md                    (331 B) 配置变更日志
│   ├── SOUL.md                         (7.74 KB) L0 最高约束
│   ├── IDENTITY.md                     (1.70 KB) AI 身份档案
│   ├── USER.md                         (1.11 KB) 用户画像
│   └── mcp.json                        (261 B) MCP 服务器配置
│
├── 02_skills/                          技能包（9个技能 + 1个模板）
│   ├── _template/                          技能开发模板
│   │   ├── SKILL.md                        (438 B)
│   │   ├── skill.py                        (518 B) 模板脚本
│   │   └── version.json                    (136 B)
│   ├── memory_manager/                     记忆管理（v1.2.0）
│   │   ├── SKILL.md                        (5.07 KB)
│   │   ├── daily_digest.py                 (20.30 KB) 每日对话提炼
│   │   ├── semantic_search.py              (23.75 KB) BM25+向量混合检索
│   │   ├── bootstrap_from_memory.py        (14.49 KB) 冷启动全量导入
│   │   ├── memory_cleanup.py               (3.91 KB) 冲突消解
│   │   ├── agent_memory_init.py            (3.30 KB) 首次初始化
│   │   ├── export_memories.py              (3.64 KB) 记忆导出
│   │   ├── import_memories.py              (7.33 KB) 记忆导入
│   │   └── version.json                    (214 B)
│   ├── inbox_refine/                       收件箱提纯归档（v1.0.0）
│   │   ├── SKILL.md                        (3.89 KB)
│   │   ├── inbox_refine.py                 (14.70 KB) 主脚本
│   │   ├── llm_classifier.py               (15.19 KB) LLM 分类器
│   │   ├── llm_classifier_broken.py        (15.02 KB) 旧版备份
│   │   └── version.json                    (694 B)
│   ├── collect_to_inbox/                   分类目录汇聚收件箱（v1.0.0）
│   │   ├── SKILL.md                        (4.12 KB)
│   │   ├── collect_to_inbox.py             (10.24 KB) 主脚本
│   │   └── version.json                    (98 B)
│   ├── kb_manager/                         知识库管理（v1.1.0）
│   │   ├── SKILL.md                        (3.25 KB)
│   │   ├── kb_ingest.py                    (9.15 KB) 知识入库
│   │   └── version.json                    (192 B)
│   ├── auto_collector/                     24h自动监控收集（v1.0.0）
│   │   ├── SKILL.md                        (3.61 KB)
│   │   └── version.json                    (116 B)
│   ├── content_processor/                  统一内容处理路由（v1.0.0）
│   │   ├── SKILL.md                        (4.26 KB)
│   │   └── version.json                    (119 B)
│   ├── web_crawler/                        网页抓取+反爬（v1.1.0）
│   │   ├── SKILL.md                        (1.76 KB)
│   │   └── version.json                    (151 B)
│   └── sync_manager/                       同步管理（v1.1.0）
│       ├── SKILL.md                        (1.09 KB)
│       └── version.json                    (172 B)
│
├── 03_knowledge/                       Obsidian 知识库
│   ├── .obsidian/                        Obsidian 配置
│   ├── README.md                         (4.19 KB) 知识库首页
│   ├── CHANGELOG.md                      (499 B) 知识库变更日志
│   ├── 00_inbox/                         📥 收件箱（待提纯内容）
│   ├── 01_daily/                         📅 日记
│   ├── 10_concepts/                      💡 概念层（16个子领域目录）
│   │   ├── cs/ ai/ finance/ law/ ...
│   │   └── 2026-04-28_测试_LLM_分类器.md
│   ├── 20_methods/                       🔧 方法层
│   ├── 30_facts/                         📋 事实层
│   ├── 40_references/                    📎 参考层（papers/ + docs/）
│   ├── 50_resources/                     🛠 资源层
│   ├── 60_opinions/                      💭 观点层
│   ├── 90_archive/deprecated/            🗄 归档层
│   └── 99_system/                        ⚙️ 系统层
│       ├── templates/                        4种知识卡片模板
│       ├── taxonomies/                       分类体系
│       ├── prompts/                           分类 Prompt
│       └── timelines/                         版本时间线
│
├── 04_memory/                          四级记忆体
│   ├── .obsidian/                        Obsidian 配置（可视化浏览）
│   ├── .workbuddy/memory/                WorkBuddy 运行记忆
│   ├── CHANGELOG.md                      (313 B) 记忆体变更日志
│   ├── daily_summaries/                  每日对话摘要
│   │   ├── 2026-04-25.md                 (33.58 KB)
│   │   ├── 2026-04-26.md                 (411.56 KB)
│   │   ├── 2026-04-27.md                 (4.12 KB)
│   │   └── 2026-04-28.md                 (1.94 KB)
│   ├── long_term/                        L2 结构化事实 + L3 原文
│   │   ├── facts.db                      (40 KB) SQLite 事实库（52条）
│   │   └── raw/ → ~/workbuddy-agent-os/agent-sync/agent-local/memory/raw/  [软链接]
│   │       ├── 2026-04-25.md ~ 2026-04-28.md
│   │       └── bootstrap_*.md
│   ├── vector_db/ → ~/workbuddy-agent-os/agent-sync/agent-local/memory/vector_db/  [软链接]
│   │   ├── keyword_index.json            (24.78 KB) BM25 关键词索引
│   │   └── chroma/                       ChromaDB 向量库
│   │       └── chroma.sqlite3            (536 KB)
│   ├── logs/                             操作日志
│   └── memory_backup/                    记忆备份
│
├── 05_tools/                           工具脚本（底层公共工具）
│   ├── README.md                         (1.11 KB)
│   ├── 00_setup/                         环境安装工具
│   ├── 01_system/                        系统诊断脚本
│   │   ├── check_automation_env.py       (4.38 KB) 自动化环境检查
│   │   ├── check_facts.py                (1.45 KB) facts.db 查询
│   │   ├── test_omlx_embedding.py        (5.32 KB) oMLX Embedding 测试
│   │   └── reports/                      系统检查报告存档
│   │       └── system-check-report-20260427.md
│   ├── 02_browser/                       浏览器工具
│   ├── 03_ocr/                           OCR 工具
│   ├── 04_media/                         媒体处理工具
│   ├── 05_crawl/                         爬虫工具
│   │   └── content-inspiration/          🎬 口播素材系统 v1.0
│   │       ├── SKILL.md                  (4.82 KB)
│   │       ├── README.md                 (13.49 KB)
│   │       ├── config.yaml               (1.64 KB)
│   │       ├── schema.sql                (3.54 KB)
│   │       ├── collect.py                (9.76 KB) 多平台采集
│   │       ├── analyze.py                (8.25 KB) AI 分析
│   │       ├── downloader.py             (5.93 KB) yt-dlp 下载
│   │       ├── app.py                    (10.45 KB) Gradio Web 界面
│   │       ├── utils.py                  (4.86 KB) 工具函数
│   │       ├── requirements.txt          (255 B)
│   │       ├── data/raw/                 原始采集数据
│   │       └── logs/                     运行日志
│   └── 06_mobile/                        移动端工具
│
├── 06_runtime/                         运行时
│   ├── tasks/                            任务执行记录
│   └── cache/ → ~/workbuddy-agent-os/agent-sync/agent-local/runtime/cache/  [软链接]
│
└── 07_migration/                       迁移与打包
    ├── backup.sh                         (1.43 KB) 手动备份
    ├── pack.sh                           (1.17 KB) 全量打包
    └── unpack.sh                         (1.11 KB) 解包还原
```

---

## 三、核心配置文件详解

### 3.1 SOUL.md — L0 最高约束

**路径**：`~/workbuddy-agent-os/agent-sync/01_core/SOUL.md` → 部署到 `~/.workbuddy/SOUL.md`
**大小**：7.74 KB | **优先级**：最高（不可被任何技能或用户指令绕过）

这是 AgentOS 的"宪法"文件，定义了 AI Agent 的硬约束和软约束：

| 层级 | 内容 | 说明 |
|------|------|------|
| **L0 硬约束** | 禁止操作列表 | 删除安全备份、关闭约束本身、暴露 L3 原文等 |
| **L0 硬约束** | 需确认操作 | 修改知识文件、执行系统命令、修改配置、发起网络请求 |
| **L0 硬约束** | 必须操作 | 每次对话读取身份文件、L0 安全检查、MCP 协议接入 |
| **L1 行为准则** | 编码原则 | 思考优先、简单优先、精准修改、目标驱动 |
| **L1 行为准则** | 职责边界 | 职权检查、明确拒绝 |
| **L1 行为准则** | 规则检查 | 冲突检查、规则优先 |
| **L1 行为准则** | 复用优先 | 技能复用三步走、方案复用 |
| **L1 行为准则** | 输出要求 | 去文学化、可执行性、自行检查、精简提问 |
| **L2 学习规则** | 知识审查 | 入库必审、冲突处理、过期清理（技术 180 天） |
| **L2 学习规则** | 自学习 | 错误日志、知识修补、进化阈值（3 次触发改进） |
| **L2 学习规则** | 性能优化 | 按需加载、记忆截断、回复控制 |

**记忆读取策略**（核心流程）：
```
用户提问 → L0 安全过滤 → L1 关键词索引匹配
  ├─ 无匹配 → 直接回答（不翻记忆）
  └─ 有匹配 → L2 置信度检查
       ├─ ≥ 0.7 → 返回摘要作为上下文
       └─ < 0.7 → 终止，直接回答（不 fallback 到 L3）
L3 仅在用户明确要求"调出原文"时按行号加载
```

### 3.2 IDENTITY.md — AI 身份档案

**路径**：`~/workbuddy-agent-os/agent-sync/01_core/IDENTITY.md` → 部署到 `~/.workbuddy/IDENTITY.md`
**大小**：1.70 KB

```yaml
Name: Claw
Creature: AI 外骨骼（智能体操作系统内核）
Vibe: 精准、高效、无废话、有主见
Emoji: 🦀
```

包含：
- 角色定位（个人智能体外骨骼，非聊天机器人）
- 能力边界（擅长/不擅长/绝对不做）
- 交互风格（先结论后步骤，能验证不问）
- 当前设备信息（由 `init.sh` 自动填充：主机名、系统、Python 路径、Node 路径、oMLX 模型列表、初始化时间）

### 3.3 USER.md — 用户画像

**路径**：`~/workbuddy-agent-os/agent-sync/01_core/USER.md` → 部署到 `~/.workbuddy/USER.md`
**大小**：1.11 KB

```yaml
Name: ghai
City: 苏州
Language: 中文（默认），英文（技术术语保留）
```

记录用户的工作背景、个人偏好（结构化输出、决策果断、注重 token 效率）、当前关注领域和近期动态。此文件随使用持续更新。

### 3.4 mcp.json — MCP 服务器配置

**路径**：`~/workbuddy-agent-os/agent-sync/01_core/mcp.json` → 部署到 `~/.workbuddy/mcp.json`
**大小**：261 B

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "~/workbuddy-agent-os/agent-sync"]
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  }
}
```

两个 MCP 服务器：
- **filesystem**：让 AI Agent 通过标准协议读写 `~/workbuddy-agent-os/agent-sync/` 目录下的文件
- **memory**：提供持久化记忆存储能力

> **注意**：`apply-config.sh` 部署 mcp.json 时，如果目标已存在 mcp.json，会提示手动合并而非覆盖，避免破坏用户已有配置。

---

## 四、初始化与部署

### 4.1 一键初始化（init.sh）

**路径**：`~/workbuddy-agent-os/agent-sync/00_bootstrap/init.sh`（12.45 KB，366 行）

**使用方式**：
```bash
cd ~/workbuddy-agent-os/agent-sync/00_bootstrap && bash init.sh
```

**自动完成的操作**（按顺序）：

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | 检测操作系统 | macOS/Linux，提取版本信息和主机名 |
| 2 | 检测 Python | 优先使用 agent-os venv → managed Python → 系统 python3 |
| 3 | 检测 Node.js | WorkBuddy managed Node 22.12.0 |
| 4 | 创建本机专属目录 | `~/workbuddy-agent-os/agent-sync/agent-local/` 下的 8 个子目录 |
| 5 | 重建软链接 | raw → agent-os-local/memory/raw 等 3 个链接 |
| 6 | 创建 agent-os 内部目录 | 42 个目录（含知识库 16 个领域子目录） |
| 7 | 添加 .gitkeep | 空目录添加占位文件（确保坚果云能同步空目录） |
| 8 | 安装 Python 依赖 | 自动创建 venv 并 `pip install -r requirements.txt` |
| 9 | 填充设备信息 | sed 替换 IDENTITY.md 中的占位符 |
| 10 | 初始化记忆体 | 创建 L1 keyword_index.json 和 L2 facts.db |
| 11 | 检测坚果云 | 自动搜索常见坚果云路径 |
| 12 | 检测 oMLX | curl 检查 localhost:8000 是否响应 |

**输出**：换机还原检查清单（5 项）和目录边界说明。

### 4.2 配置部署（apply-config.sh）

**路径**：`~/workbuddy-agent-os/agent-sync/00_bootstrap/apply-config.sh`（3.31 KB，112 行）

**使用方式**：
```bash
cd ~/workbuddy-agent-os/agent-sync/00_bootstrap && bash apply-config.sh
```

**操作**：
1. **备份旧配置**：将 `~/.workbuddy/` 下已有的 SOUL.md、IDENTITY.md、USER.md 备份到带时间戳的目录
2. **部署配置**：复制 `01_core/` 下的 4 个文件到 `~/.workbuddy/`
3. **mcp.json 特殊处理**：已存在时提示手动合并，不覆盖
4. **BOOTSTRAP.md 清理**：检测到 BOOTSTRAP.md 时提示删除（需 `AUTO_DELETE_BOOTSTRAP=yes` 环境变量确认）

### 4.3 技能导入导出

#### import_skills.sh — 技能导入

**路径**：`~/workbuddy-agent-os/agent-sync/00_bootstrap/import_skills.sh`（2.60 KB）

```bash
# 导入全部技能
bash import_skills.sh

# 导入指定技能
bash import_skills.sh memory_manager
```

**操作**：
- 扫描 `02_skills/` 下所有子目录
- 跳过 `_template/` 和缺少 `SKILL.md` 的目录
- 复制到 `~/.workbuddy/skills/`（用户级技能目录）
- 已存在的技能会先删除再覆盖

#### export_skills.sh — 技能导出

**路径**：`~/workbuddy-agent-os/agent-sync/00_bootstrap/export_skills.sh`（1.74 KB）

```bash
bash export_skills.sh memory_manager
# 输出：07_migration/exports/memory_manager_v1.2.0.zip
```

### 4.4 冷启动记忆体

```bash
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 \
  ~/workbuddy-agent-os/agent-sync/02_skills/memory_manager/bootstrap_from_memory.py \
  --root ~/workbuddy-agent-os/agent-sync
```

将已有工作记忆（MEMORY.md + 工作日志 + 系统画像）全量导入 L1/L2/L3 记忆体。仅在首次运行，之后每日自动提炼。

---

## 五、技能体系详解

### 5.1 技能分类

AgentOS 将技能分为两类：

**system 技能**（后台自动运行，也可手动触发）：

| 技能 | 版本 | 用途 | 自动化时间 |
|------|------|------|-----------|
| memory_manager | v1.2.0 | 记忆提炼/去重/语义检索 | 每日 2:00 |
| collect_to_inbox | v1.0.0 | 知识库目录扫描→收件箱 | 每日 2:30 |
| inbox_refine | v1.0.0 | 收件箱提纯→知识库归档 | 每日 3:00 |
| auto_collector | v1.0.0 | 24h 多平台自动信息收集 | 持续运行 |
| kb_manager | v1.1.0 | 知识入库/分类/检索 | 按需 |
| sync_manager | v1.1.0 | 备份/导出/同步状态 | 按需 |

**user 技能**（对话触发）：

| 技能 | 版本 | 用途 | 触发词示例 |
|------|------|------|-----------|
| content_processor | v1.0.0 | 统一内容处理路由 | 转笔记/剪藏/语音摘要/采集 |
| web_crawler | v1.1.0 | 网页抓取+反爬 | 抓取/crawl/fetch |

### 5.2 快速指令对照表

| 指令 | 路由 | 动作 |
|------|------|------|
| `转笔记` | content_processor → bilinote | 视频→结构化笔记 |
| `摘字幕` | content_processor → bilinote | 仅语音转文字 |
| `视频摘要` | content_processor → bilinote | 提炼核心观点 |
| `剪藏` | content_processor → web-clipper | 网页→Markdown |
| `摘抄` | content_processor → web-clipper | 保存全文 |
| `文章摘要` | content_processor → web-clipper | 3句话概括 |
| `提炼` | content_processor → web-clipper | 方法论/步骤/结论 |
| `翻译` | content_processor → web-clipper | 翻译成中文 |
| `语音摘要` | content_processor → voice-summary | 语音→核心要点 |
| `转文字` | content_processor → voice-summary | 逐字稿 |
| `采集` | content_processor → social-collector | 小红书/抖音→笔记 |
| `开始收集` | auto_collector | 启动 24h 监控 |
| `停止收集` | auto_collector | 暂停监控 |
| `收集报告` | auto_collector | 今日采集摘要 |
| `记忆更新` | memory_manager | 手动触发记忆提炼 |
| `查记忆` | memory_manager | 语义检索记忆 |
| `入库` | kb_manager | 知识入库（→ 00_inbox/） |
| `归集` | collect_to_inbox | 分类目录→收件箱 |
| `提纯` | inbox_refine | 收件箱提纯归档 |
| `抓取` | web_crawler | 网页抓取+反爬 |
| `备份知识库` | sync_manager | 全量备份 |

### 5.3 memory_manager（记忆管理）详解

**版本**：v1.2.0 | **脚本数**：7 个 Python 脚本

#### 核心脚本说明

| 脚本 | 大小 | 用途 | 使用方式 |
|------|------|------|----------|
| `daily_digest.py` | 20.30 KB | 每日对话提炼主脚本 | `--root ~/workbuddy-agent-os/agent-sync --date YYYY-MM-DD` |
| `semantic_search.py` | 23.75 KB | BM25 + 向量语义混合检索 | `search --query "内容" --top-k 5` |
| `bootstrap_from_memory.py` | 14.49 KB | 冷启动全量导入历史记忆 | `--root ~/workbuddy-agent-os/agent-sync` |
| `memory_cleanup.py` | 3.91 KB | 冲突消解与过期记忆清理 | `--root ~/workbuddy-agent-os/agent-sync` |
| `agent_memory_init.py` | 3.30 KB | 首次初始化记忆体 | `--root ~/workbuddy-agent-os/agent-sync` |
| `export_memories.py` | 3.64 KB | 记忆导出为 JSON+MD 压缩包 | `--output ~/backup/` |
| `import_memories.py` | 7.33 KB | 从压缩包恢复记忆（智能去重） | `--input ~/backup/memories.zip` |

#### 每日对话提炼流程

```
1. 读取 Claw 工作日志（~/WorkBuddy/Claw/.workbuddy/memory/YYYY-MM-DD.md）
2. 提取关键事实（who/what/when/where/decision）
3. 去重：对比 L2 已有事实，相似度 > 0.9 则跳过
4. 冲突检测：新事实与旧事实矛盾？→ 标记 OVERRIDE 或提示用户确认
5. 生成摘要（100-200 字/条）
6. 更新 L1 关键词索引（keyword_index.json）
7. 更新 L1_vec 向量索引（ChromaDB + oMLX embedding）
8. 关键对话原文 → 压缩后写入 L3（long_term/raw/）
```

#### 语义检索能力

- **BM25 关键词检索** + **ChromaDB 向量检索** + **RRF（Reciprocal Rank Fusion）加权融合**
- 向量权重 0.6 / BM25 权重 0.4
- 向量引擎：ChromaDB 持久化 + oMLX Qwen3-Embedding-0.6B（1024 维）
- CLI：
  ```bash
  # 检索
  python3 semantic_search.py search --root ~/workbuddy-agent-os/agent-sync --query "查询内容" --top-k 5
  # 回填（向量化所有 L2 事实）
  python3 semantic_search.py backfill --root ~/workbuddy-agent-os/agent-sync
  # 重建索引
  python3 semantic_search.py rebuild --root ~/workbuddy-agent-os/agent-sync
  # 测试 embedding
  python3 semantic_search.py embed --root ~/workbuddy-agent-os/agent-sync --text "测试"
  ```

### 5.4 inbox_refine（收件箱提纯）详解

**版本**：v1.0.0 | **脚本数**：3 个（含 LLM 分类器）

#### 分类决策逻辑

| 内容特征 | nature | 目标目录 |
|----------|--------|----------|
| 已验证的客观事实 | fact | 30_facts/ |
| 可操作的步骤/教程 | method | 20_methods/ |
| 原子概念/基础原理 | concept | 10_concepts/ |
| 公认基础原理 | axiom | 10_concepts/ |
| 法律法规/制度 | regulation | 30_facts/ |
| 论文/文档/外部资料 | reference | 40_references/ |
| 测试数据/基准结果 | data | 30_facts/ |
| 主观看法/推测 | opinion | 60_opinions/ |
| 他人原话/语录 | quote | 60_opinions/ |

#### 置信度评分

| source_type | confidence |
|-------------|-----------|
| official_doc | 0.9 |
| literature | 0.8 |
| experiment | 0.7 |
| personal_exp | 0.5 |
| social_media | 0.3 |
| unknown | 0.4 |

#### LLM 分类器

`llm_classifier.py`（15.19 KB）使用 oMLX + Qwen2.5-VL-3B-Instruct-8bit 进行 AI 辅助分类（因 Qwen3-8B Chat API 存在 500 错误，降级使用 VLM 模型），包含降级机制：LLM 失败时自动回退到启发式规则，分类信心度阈值降至 0.4。

### 5.5 collect_to_inbox（分类目录汇聚收件箱）详解

**版本**：v1.0.0 | **脚本**：`collect_to_inbox.py`（10.24 KB）

#### 扫描目录配置

| 源目录 | 来源技能 | 提取策略 |
|--------|----------|----------|
| `50_resources/视频笔记/` | bilinote | 提取核心摘要 + 关键结论 |
| `50_resources/字幕存档/` | bilinote | 提取前 500 字摘要 |
| `50_resources/阅读笔记/` | web-clipper | 提取标题 + 核心观点 |
| `50_resources/全文存档/` | web-clipper | 提取前 500 字摘要 |
| `50_resources/翻译存档/` | web-clipper | 提取标题 + 3 句话概括 |
| `50_resources/灵感素材/` | social-collector | 提取核心内容 + 互动数据 |
| `50_resources/语音转写/` | voice-summary | 提取关键要点 |
| `20_methods/` | web-clipper 提炼 | 提取方法名 + 步骤 |
| `01_daily/闪念笔记/` | voice-summary | 提取要点 + 标签 |
| `40_references/` | content_processor | 提取标题 + 核心观点 |

### 5.6 content_processor（统一内容处理路由）详解

**版本**：v1.0.0

本技能不替代子技能，而是作为**统一调度层**：

```
用户输入（触发词 + URL/文件）
  ↓
content_processor 解析触发词
  ↓ 路由
  ├─ 视频 → 加载 bilinote 技能
  ├─ 文章 → 加载 web-clipper 技能
  ├─ 语音 → 加载 voice-summary 技能
  └─ 社交 → 加载 social-collector 技能
  ↓ 执行
子技能完成处理 → 输出 Markdown 笔记到对应分类目录
```

### 5.7 web_crawler（网页抓取+反爬）详解

**版本**：v1.1.0

三引擎自适应选择：

| 反爬级别 | 引擎 | 说明 |
|----------|------|------|
| 低（静态页面） | Scrapling 静态模式 | 最快，无需浏览器 |
| 中（动态渲染） | Scrapling 动态模式 | Camoufox 隐身浏览器 |
| 高（Cloudflare 等） | Playwright + Stealth | 完整浏览器模拟+反检测 |

失败自动重试最多 3 次，引擎自动降级。

---

## 六、知识库结构详解

### 6.1 目录结构与命名规则

知识库路径：`~/workbuddy-agent-os/agent-sync/03_knowledge/`，同时作为 Obsidian Vault。

| 编号 | 目录 | 中文名 | 知识属性 | 说明 |
|------|------|--------|----------|------|
| 00 | `00_inbox/` | 📥 收件箱 | — | 待提纯内容暂存 |
| 01 | `01_daily/` | 📅 日记 | — | 每日日记、闪念笔记 |
| 10 | `10_concepts/` | 💡 概念层 | concept/axiom | 16 个子领域目录 |
| 20 | `20_methods/` | 🔧 方法层 | method | 可操作的步骤/教程 |
| 30 | `30_facts/` | 📋 事实层 | fact/regulation/data | 已验证的客观事实 |
| 40 | `40_references/` | 📎 参考层 | reference | 论文/文档/外部资料 |
| 50 | `50_resources/` | 🛠 资源层 | resource | 视频笔记/阅读笔记/灵感素材等 |
| 60 | `60_opinions/` | 💭 观点层 | opinion/quote | 主观看法/他人原话 |
| 90 | `90_archive/` | 🗄 归档层 | — | 已弃用的知识 |
| 99 | `99_system/` | ⚙️ 系统层 | — | 模板/分类/配置 |

### 6.2 领域分类体系

`10_concepts/` 下按 16 个一级领域分子目录：

| 编号 | 英文目录 | 中文 | 典型子领域 |
|------|----------|------|-----------|
| 01 | cs | 计算机科学 | 数据库、前端、后端、运维、安全 |
| 02 | ai | 人工智能 | NLP、CV、强化学习、RAG、Agent |
| 03 | finance | 金融 | 量化交易、价值投资、宏观经济 |
| 04 | law | 法律 | 民法、商法、知识产权 |
| 05 | medicine | 医学 | 中医、西医、营养学 |
| 06 | physics | 物理 | 量子力学、相对论、热力学 |
| 07 | math | 数学 | 线性代数、概率统计、微积分 |
| 08 | psychology | 心理学 | 认知心理学、社会心理学 |
| 09 | philosophy | 哲学 | 认识论、伦理学、美学 |
| 10 | history | 历史 | 中国史、世界史、科技史 |
| 11 | engineering | 工程 | 机械、电子、土木 |
| 12 | design | 设计 | UI/UX、平面设计、建筑设计 |
| 13 | business | 商业 | 创业、管理、营销、战略 |
| 14 | personal-management | 个人管理 | GTD、番茄工作法、精力管理 |
| 15 | personal-insight | 个人洞见 | 决策模型、价值观、反思 |
| 16 | other | 其他 | 待新增领域 |

> 当"其他"类别超过总知识 5% 时，memory_manager 会提示新增领域。

### 6.3 知识卡片模板

`99_system/templates/` 下有 4 种标准化模板：

| 模板文件 | 适用类型 | 核心字段 |
|----------|----------|----------|
| `concept-card.md` | 概念/公理 | 一句话定义、核心原理、与相关概念区别、主流选择 |
| `method-card.md` | 方法/教程 | 适用场景、步骤、注意事项、示例 |
| `fact-card.md` | 事实/数据 | 事实陈述、数据来源、可信度 |
| `personal-insight-card.md` | 个人洞见 | 背景、思考过程、结论、行动项 |

所有知识卡片使用标准 Frontmatter：

```yaml
---
id: KB-YYYYMMDD-NNN
title: "知识标题"
type: concept|method|fact|reference|resource|opinion
status: draft|review|published|archived
nature: fact|opinion|method|regulation|reference|data|quote|axiom
domain: [领域1, 领域2]
tags: [标签列表]
confidence: 0.0-1.0
source: "原始来源 URL"
source_type: official_doc|literature|experiment|personal_exp|social_media|unknown
date_created: YYYY-MM-DD
date_modified: YYYY-MM-DD
version: 1
previous_version: ""
superseded_by: ""
---
```

### 6.4 分类体系配置文件

| 文件 | 路径 | 说明 |
|------|------|------|
| `domains.md` | `99_system/taxonomies/domains.md` | 16 个一级领域定义 |
| `nature-types.md` | `99_system/taxonomies/nature-types.md` | 9 种 nature 类型 + 决策树 |
| `folder-aliases.json` | `99_system/taxonomies/folder-aliases.json` | 英文目录 ↔ 中文映射 |
| `classify-knowledge.md` | `99_system/prompts/classify-knowledge.md` | 知识分类 Prompt |

---

## 七、记忆体系统详解

### 7.1 五级分层架构

```
┌─────────────────────────────────────────────────┐
│ L0: SOUL.md（硬约束）                             │ 不存储，直接注入 prompt
├─────────────────────────────────────────────────┤
│ L1: 关键词索引（keyword_index.json）               │ 52 条条目
│     + 向量索引（ChromaDB + embedding）             │ 52 条向量
├─────────────────────────────────────────────────┤
│ L2: 结构化事实库（facts.db, SQLite）               │ 52 条事实
├─────────────────────────────────────────────────┤
│ L3: 对话原文（long_term/raw/*.md）                 │ 6 个文件
└─────────────────────────────────────────────────┘
```

### 7.2 L2 facts.db 表结构

```sql
CREATE TABLE facts (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,        -- 主语
    predicate TEXT NOT NULL,      -- 谓语
    object TEXT NOT NULL,         -- 宾语
    confidence REAL DEFAULT 0.7,  -- 置信度
    nature TEXT DEFAULT 'fact',   -- 属性
    domain TEXT,                  -- 领域
    source TEXT,                  -- 来源
    date_created TEXT,            -- 创建时间
    date_modified TEXT,           -- 修改时间
    previous_version TEXT,        -- 前一版本
    superseded_by TEXT,           -- 被谁取代
    version INTEGER DEFAULT 1     -- 版本号
);
```

索引：`subject` / `domain` / `confidence`

### 7.3 记忆体文件说明

| 路径 | 类型 | 说明 |
|------|------|------|
| `04_memory/vector_db/keyword_index.json` (24.78 KB) | L1 | BM25 关键词索引 |
| `04_memory/vector_db/chroma/chroma.sqlite3` (536 KB) | L1_vec | ChromaDB 向量索引 |
| `04_memory/long_term/facts.db` (40 KB) | L2 | SQLite 结构化事实 |
| `04_memory/long_term/raw/YYYY-MM-DD.md` | L3 | 当日对话原文 |
| `04_memory/daily_summaries/YYYY-MM-DD.md` | 摘要 | 每日提炼结果 |
| `04_memory/logs/` | 日志 | 错误日志、冲突日志、入库日志 |
| `04_memory/memory_backup/` | 备份 | 记忆备份存档 |

---

## 八、工具脚本目录

### 8.1 05_tools/ 与 02_skills/ 的区别

- **`02_skills/`**：可被 WorkBuddy 对话触发的技能，有 `SKILL.md` 身份证
- **`05_tools/`**：底层公共工具，被技能调用或手动执行，不暴露给对话

### 8.2 系统诊断脚本

| 脚本 | 路径 | 大小 | 用途 |
|------|------|------|------|
| `check_automation_env.py` | `05_tools/01_system/` | 4.38 KB | 检查自动化运行环境配置 |
| `check_facts.py` | `05_tools/01_system/` | 1.45 KB | 查询 facts.db 中的事实 |
| `test_omlx_embedding.py` | `05_tools/01_system/` | 5.32 KB | 测试 oMLX Embedding API 连通性 |

**调用方式**：
```bash
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 ~/workbuddy-agent-os/agent-sync/05_tools/01_system/check_automation_env.py
```

### 8.3 口播素材系统（content-inspiration）

**路径**：`~/workbuddy-agent-os/agent-sync/05_tools/05_crawl/content-inspiration/`
**版本**：v1.0.0 | **独立项目**，包含完整 Web 界面

解决的核心问题：口播创作者的素材灵感管理。

| 组件 | 脚本 | 大小 | 用途 |
|------|------|------|------|
| 采集 | `collect.py` | 9.76 KB | 多平台元数据采集 |
| 分析 | `analyze.py` | 8.25 KB | oMLX + Qwen2.5-VL AI 分析 |
| 下载 | `downloader.py` | 5.93 KB | yt-dlp 视频下载 |
| 界面 | `app.py` | 10.45 KB | Gradio Web 界面 |
| 工具 | `utils.py` | 4.86 KB | 公共工具函数 |
| 配置 | `config.yaml` | 1.64 KB | 运行时配置 |
| 数据 | `schema.sql` | 3.54 KB | SQLite 数据库表结构 |

**数据流**：
```
collect.py → JSONL 存档（data/raw/）
    ↓
analyze.py → oMLX Qwen2.5-VL 分析 → SQLite 索引
    ↓
app.py → Gradio Web 界面统一检索
    ↓
downloader.py → yt-dlp → ~/workbuddy-agent-os/agent-sync/agent-local/materials/video/
```

**启动方式**：
```bash
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 ~/workbuddy-agent-os/agent-sync/05_tools/05_crawl/content-inspiration/app.py
```

---

## 九、运行时与缓存

### 9.1 06_runtime/ 结构

| 目录 | 用途 | 存储位置 |
|------|------|----------|
| `06_runtime/tasks/` | 任务执行记录 | agent-os（同步） |
| `06_runtime/cache/` | 临时缓存 | agent-os-local（本地） |

### 9.2 agent-os-local/ 完整结构

```
~/workbuddy-agent-os/agent-sync/agent-local/
├── memory/
│   ├── raw/                       L3 对话原文（隐私数据）
│   │   ├── 2026-04-25.md          (6.82 KB)
│   │   ├── 2026-04-26.md          (6.29 KB)
│   │   ├── 2026-04-27.md          (4.78 KB)
│   │   ├── 2026-04-28.md          (4.54 KB)
│   │   └── bootstrap_*.md         启动时导入的历史记忆
│   └── vector_db/                 向量数据库（ChromaDB + 关键词索引）
│       ├── keyword_index.json     (24.78 KB)
│       └── chroma/                ChromaDB 持久化数据
├── runtime/
│   └── cache/                     临时缓存
└── materials/                     采集的原始素材
    ├── web/                       网页保存
    ├── video/                     视频下载（yt-dlp 输出）
    ├── audio/                     录音文件
    ├── screenshots/               截图
    └── refined_for_inbox/         已提炼待投递的 MD
```

---

## 十、迁移与备份

### 10.1 备份脚本（backup.sh）

**路径**：`~/workbuddy-agent-os/agent-sync/07_migration/backup.sh`（1.43 KB）

```bash
bash backup.sh [backup_dir]
# 默认备份到 04_memory/memory_backup/
```

**操作**：
- 备份核心配置（01_core/）
- 备份记忆体（long_term/、vector_db/、daily_summaries/）
- 备份技能包（02_skills/）
- 自动清理 30 天以上的旧备份

### 10.2 全量打包（pack.sh）

**路径**：`~/workbuddy-agent-os/agent-sync/07_migration/pack.sh`（1.17 KB）

```bash
bash pack.sh
# 输出：07_migration/exports/agent-os_YYYYMMDD_HHMMSS.tar.gz
```

排除项：缓存、虚拟环境、`__pycache__`、`.DS_Store`、`node_modules`

### 10.3 解包还原（unpack.sh）

**路径**：`~/workbuddy-agent-os/agent-sync/07_migration/unpack.sh`（1.11 KB）

```bash
bash unpack.sh <archive_path> [target_dir]
# 解压后按提示运行 init.sh → apply-config.sh → import_skills.sh
```

### 10.4 换机还原流程（3步）

```bash
# 1. 等坚果云同步完成，agent-os 目录出现在本机
# 2. 一键初始化（自动完成所有配置）
cd ~/workbuddy-agent-os/agent-sync/00_bootstrap && bash init.sh

# 3. 部署核心配置
bash apply-config.sh

# 4. 导入技能
bash import_skills.sh

# 5. 手动安装 oMLX（Apple MLX 框架，硬件依赖）
```

`init.sh` 自动完成：创建本地目录、重建软链接、创建 venv 安装依赖、填充设备信息、检测坚果云和 oMLX。

---

## 十一、自动化任务配置

### 11.1 WorkBuddy 自动化任务

| 任务 | 时间 | 脚本 | 说明 |
|------|------|------|------|
| 每日记忆提炼 | 每日 02:00 | `memory_manager/daily_digest.py` | 对话→L2 事实 |
| 收件箱汇聚 | 每日 02:30 | `collect_to_inbox/collect_to_inbox.py` | 知识库扫描→inbox |
| 收件箱提纯 | 每日 03:00 | `inbox_refine/inbox_refine.py` | inbox→分类归档 |
| RSS 检查 | 每小时 | auto_collector | 检查所有 RSS 源 |
| 社交平台检查 | 每 2 小时 | auto_collector + TikOmni | 小红书/抖音博主 |
| 网页变化检查 | 每小时 | auto_collector + Crawl4AI | 指定网页监控 |
| 采集日报 | 每日 23:00 | auto_collector | 今日采集汇总 |

### 11.2 自动化任务存储

自动化任务配置存储在：
- `~/.workbuddy/automations/<automation-id>/automation.toml` — 运行时配置
- `~/workbuddy-agent-os/agent-sync/.codebuddy/automations/<automation-id>/memory.md` — 执行记录

---

## 十二、同步策略详解

### 12.1 双轨同步

| 轨道 | 工具 | 同步范围 | 优势 |
|------|------|----------|------|
| 实时同步 | 坚果云客户端 | 整个 `~/workbuddy-agent-os/agent-sync/` 目录 | 即时、增量、无感 |
| 版本控制 | Git（Gitee 私有仓库） | 代码/配置/知识文件 | 历史追溯、分支管理、冲突解决 |

### 12.2 不同步的内容

以下内容通过软链接指向 `~/workbuddy-agent-os/agent-sync/agent-local/`，天然不会进入坚果云同步和 Git：

- L3 对话原文（`04_memory/long_term/raw/`）
- ChromaDB 向量库（`04_memory/vector_db/chroma/`）
- 临时缓存（`06_runtime/cache/`）
- 原始素材（`agent-os-local/materials/`）

### 12.3 Git 排除规则（.gitignore）

```gitignore
# 系统文件
.DS_Store / __pycache__ / *.pyc

# 虚拟环境
.venv/ / venv/

# 运行时缓存（已软链接）
06_runtime/cache/

# 大媒体文件
*.mp4 / *.mp3 / *.mov / *.zip / *.tar.gz

# WorkBuddy 运行时
.codebuddy/ / .workbuddy/

# Obsidian 插件（各设备自行安装）
.obsidian/plugins/

# 备份和报告
backup_*/ / system-check-report-*.md
```

### 12.4 Git 远程仓库

- **平台**：Gitee 私有仓库
- **地址**：`git@gitee.com:babycalf/mac-agent-os.git`
- **分支策略**：main 分支，单线开发
- **SSH 密钥**：`~/.ssh/id_ed25519a`（个人公钥）

### 12.5 索引卡片命名规范（多机协作）

多台电脑采集的素材通过**索引卡片**共享，避免大文件同步冲突：

```
{hostname}_{YYYYMMDD}_{slug}.md
示例：Redmi-12C_20260428_douyin-普通人逆袭.md
      MBP-M3_20260428_bilibili-科普冷知识.md
```

卡片模板：
```yaml
---
title: 素材标题
source_url: https://...
local_path: ~/workbuddy-agent-os/agent-sync/agent-local/materials/video/xxx.mp4
type: video|audio|web|image
platform: douyin|xiaohongshu|bilibili|web
collected_by: Redmi-12C    ← 标明采集机器
collected_at: 2026-04-28
tags: [标签1, 标签2]
---
```

---

## 十三、本地/远程使用方式

### 13.1 本地使用（当前配置）

**本机环境**：
- 设备：MacBook Air M1（Redmi-12C） / macOS 26.4
- Python：3.13.12（`~/.workbuddy/binaries/python/envs/agent-os/bin/python3`）
- Node.js：22.12.0（`~/.workbuddy/binaries/node/versions/22.12.0/bin/node`）
- 本地 LLM：oMLX v0.3.6（localhost:8000，API Key: `omlx`）

**使用流程**：
1. 打开 WorkBuddy 桌面客户端
2. 在 Claw 工作区对话，AI 自动加载 SOUL.md/IDENTITY.md/USER.md
3. 使用触发词（转笔记/剪藏/采集/提纯 等）调用技能
4. 自动化任务在后台按时执行

**关键路径速查**：
```
# Python（所有脚本用这个）
~/.workbuddy/binaries/python/envs/agent-os/bin/python3

# Node.js
~/.workbuddy/binaries/node/versions/22.12.0/bin/node

# 知识库（Obsidian Vault）
~/workbuddy-agent-os/agent-sync/03_knowledge/

# 本地 LLM API
http://localhost:8000/v1/chat/completions  (Authorization: Bearer omlx)
http://localhost:8000/v1/embeddings        (Authorization: Bearer omlx)

# 坚果云同步目录
~/Nutstore Files/
```

### 13.2 远程/换机使用

**前提条件**：
1. 新机器已安装 WorkBuddy 桌面客户端
2. 新机器已安装坚果云客户端，且同步完成

**还原步骤**：
```bash
# 1. 确认 agent-os 目录已通过坚果云同步到本机
ls ~/workbuddy-agent-os/agent-sync/README.md

# 2. 一键初始化（自动创建本地目录、重建软链接、安装依赖）
cd ~/workbuddy-agent-os/agent-sync/00_bootstrap && bash init.sh

# 3. 部署核心配置到 WorkBuddy
bash apply-config.sh

# 4. 导入技能
bash import_skills.sh

# 5. 冷启动记忆体（首次）
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 \
  ~/workbuddy-agent-os/agent-sync/02_skills/memory_manager/bootstrap_from_memory.py --root ~/workbuddy-agent-os/agent-sync

# 6. 安装 oMLX（从 https://omlx.ai 下载）

# 7. 配置 Obsidian Vault → ~/workbuddy-agent-os/agent-sync/03_knowledge/

# 8. 重启 WorkBuddy
```

**换机注意事项**：
- `~/workbuddy-agent-os/agent-sync/agent-local/` **不会**通过坚果云同步，每台机器独立
- 向量库和 L3 原文需要在新机器上重新生成（`bootstrap_from_memory.py` 或 `semantic_search.py backfill`）
- 设备信息会由 `init.sh` 自动更新到 IDENTITY.md
- Python/Node 路径可能因 WorkBuddy 版本不同而变化，`init.sh` 会自动检测

### 13.3 跨平台兼容性

| 平台 | 说明 |
|------|------|
| **macOS** | 直接运行，无需额外配置 |
| **Linux** | 直接运行，部分系统命令可能需要 `sudo` |
| **Windows** | 需通过 WSL2 运行，路径使用 `/mnt/c/Users/xxx/` |

所有路径使用 `$HOME` 或相对路径，不硬编码绝对路径，确保跨平台兼容。

---

## 十四、数据流全景

### 14.1 内容采集→知识归档 完整流程

```
用户输入 / 自动监控
  ↓
┌──────────────────────────────────────────┐
│  content_processor（统一路由层）          │
│  ├─ 视频 → bilinote                     │
│  ├─ 文章 → web-clipper                  │
│  ├─ 语音 → voice-summary                │
│  └─ 社交 → social-collector             │
└────────────┬─────────────────────────────┘
             ↓
     各分类目录（视频笔记/阅读笔记/灵感素材/...）
             ↓
     collect_to_inbox（每日 2:30 自动 / 手动"归集"）
             ↓
     00_inbox/（收件箱，标准化 MD）
             ↓
     inbox_refine（每日 3:00 自动 / 手动"提纯"）
             ↓
     分类写入 03_knowledge/ 对应目录 + 更新首页
```

### 14.2 记忆提炼流程

```
每日对话记录（~/WorkBuddy/Claw/.workbuddy/memory/YYYY-MM-DD.md）
  ↓
memory_manager/daily_digest.py（每日 2:00 自动）
  ↓
┌─ 提取关键事实 → 去重 → 冲突检测
├─ 更新 L2 facts.db（SQLite）
├─ 更新 L1 keyword_index.json（BM25）
├─ 更新 L1_vec ChromaDB（向量）
└─ 关键原文 → L3 raw/（压缩存储）
```

### 14.3 语义检索流程

```
用户查询 → memory_manager/semantic_search.py
  ↓
BM25 关键词检索（keyword_index.json）
  + 向量语义检索（ChromaDB + oMLX Embedding）
  ↓
RRF 加权融合（BM25:0.4 + 向量:0.6）
  ↓
返回 Top-K 结果
```

### 14.4 多机协作数据流

```
本机采集 → ~/workbuddy-agent-os/agent-sync/agent-local/materials/（本机专属，不同步）
  ↓ AI 提炼
~/workbuddy-agent-os/agent-sync/03_knowledge/00_inbox/（标准化 MD）
  ↓ 坚果云实时同步
其他电脑收到的 inbox 内容
  ↓
inbox_refine → 归档到知识库 → Git commit → Gitee
```

---

## 十五、环境依赖清单

### 15.1 必需环境

| 软件 | 最低版本 | 安装方式 | 状态 |
|------|----------|----------|------|
| WorkBuddy 桌面客户端 | 最新版 | [codebuddy.cn](https://www.codebuddy.cn) | ✅ |
| Python | 3.10+ | WorkBuddy 自动管理 | ✅ 3.13.12 |
| Node.js | 18+ | WorkBuddy 自动管理 | ✅ 22.12.0 |

> Python 和 Node.js 由 WorkBuddy 自带，**不需要手动安装**。

### 15.2 Python 依赖库

| 包 | 版本要求 | 用途 | 使用者 | 安装状态 |
|---|---------|------|--------|---------|
| trafilatura | ≥2.0.0 | 网页正文提取 | kb_ingest, web-clipper | ✅ |
| sqlite-utils | ≥3.35 | SQLite 增强 | facts.db 操作 | ✅ |
| feedparser | ≥6.0.0 | RSS 解析 | auto_collector | ✅ |
| schedule | ≥1.2.0 | 定时任务 | auto_collector | ✅ |
| chromadb | ≥1.0.0 | 向量数据库 | semantic_search | ✅ 1.5.8 |
| scrapling | ≥0.1.0 | 三引擎反爬 | web_crawler | ✅ |
| crawl4ai | ≥0.1.0 | 智能结构化抓取 | web_crawler | ✅ |
| playwright | ≥1.50.0 | 浏览器自动化 | web_crawler | ✅ |
| playwright-stealth | latest | 反检测 | web_crawler | ✅ |
| openai-whisper | latest | 语音转文字 | voice-summary | ✅ |
| gradio | latest | Web 界面 | content-inspiration | ✅ 6.13 |
| yt-dlp | latest | 视频下载 | content-inspiration | ✅ 2026.3 |

**安装命令**（全部在 agent-os venv 中）：
```bash
~/.workbuddy/binaries/python/envs/agent-os/bin/pip install -r ~/workbuddy-agent-os/agent-sync/requirements.txt
```

### 15.3 Node.js 依赖

| 包 | 用途 | 安装状态 |
|---|---|---------|
| @tikomni/skills | 小红书/抖音数据采集 | ✅ |

**安装命令**：
```bash
cd ~/.workbuddy/binaries/node/workspace && \
  ~/.workbuddy/binaries/node/versions/22.12.0/bin/npm install @tikomni/skills
```

### 15.4 系统软件

| 软件 | 用途 | 安装状态 |
|------|------|---------|
| oMLX v0.3.6 | 本地 LLM 运行 | ✅ 已安装 |
| Obsidian v1.12.7 | 知识库管理 | ✅ 已安装 |
| 坚果云 | 文件同步 | ✅ 已安装 |
| Playwright Chromium | 浏览器引擎 | ✅ headless shell 已安装 |
| Ollama | 本地 LLM（已停用） | ⚠️ 已停用，改用 oMLX |

---

## 十六、当前运行状态

### 16.1 模块状态总览

| 模块 | 状态 | 说明 |
|------|------|------|
| 核心配置（SOUL/IDENTITY/USER） | ✅ | 已部署到 ~/.workbuddy/ |
| Python 环境 | ✅ | venv 3.13.12 + 全部依赖 |
| Node.js 环境 | ✅ | 22.12.0 + TikOmni |
| 记忆系统 | ✅ | L2 有 52 条事实，L1 52 条索引，L1_vec 52 条向量（三方一致） |
| 知识库 | ✅ | 目录就绪 + 首页 + 模板 + 分类体系 |
| 收件箱提纯 | ✅ | inbox_refine 每日 3:00 自动 |
| 收件箱汇聚 | ✅ | collect_to_inbox 每日 2:30 自动 |
| 记忆提炼 | ✅ | daily_digest 每日 2:00 自动 |
| 技能包 | ✅ | 8 个自定义技能 + 多个插件技能 |
| 坚果云同步 | ✅ | 已配置 |
| Git 版本控制 | ✅ | Gitee 私有仓库 |
| oMLX | ✅ | v0.3.6 运行中 |
| Obsidian | ✅ | Vault 已绑定 03_knowledge/ |
| 口播素材系统 | ✅ | v1.0 已部署（Gradio + yt-dlp + AI 分析） |

### 16.2 本地 LLM 状态

| 模型 | 类型 | 大小 | 用途 | Chat API | Embedding API |
|------|------|------|------|----------|---------------|
| Qwen3-8B-MLX-4bit | LLM | 4.26GB | 中文理解/生成 | ❌ 500 错误 | — |
| Qwen2.5-VL-3B-Instruct-8bit | VLM | 3.9GB | 多模态理解 | ✅ 正常 | — |
| Qwen3-Embedding-0.6B | Embedding | 1.19GB | 向量嵌入（1024维） | — | ✅ 正常 |

> **关键发现**（2026-04-27）：Qwen3-8B-MLX-4bit Chat API 返回 500 错误，已将 inbox_refine 降级使用 VLM 模型，添加降级机制。

### 16.3 磁盘空间

总量 228GB，已用 12GB，可用 161GB（截至 2026-04-25）

---

## 十七、已知问题与待解决项

### 17.1 已解决问题

| 问题 | 日期 | 解决方案 |
|------|------|----------|
| Qwen3-8B Chat API 500 错误 | 2026-04-27 | inbox_refine 降级使用 VLM 模型 + 启发式回退 |
| Ollama→oMLX 迁移 | 2026-04-27 | 更新所有 .md/.sh/.py 文件中的引用 |
| 旧路径 /Users/5kecheng/ → /Users/chengzige/ | 2026-04-25 | 全面清理，零残留 |
| 根目录散落脚本 | 2026-04-28 | 移入 05_tools/01_system/ |
| 目录隔离 | 2026-04-28 | 引入 agent-os-local + 软链接机制 |

### 17.2 待解决项

| 项目 | 优先级 | 说明 |
|------|--------|------|
| Homebrew 安装 | 中 | 可选，安装后可装 yt-dlp/ffmpeg/screenpipe |
| BiliNote Docker | 低 | 视频转笔记依赖，需 Docker Desktop |
| Qwen3-8B Chat API 修复 | 中 | oMLX 侧问题，等待更新 |

---

## 十八、附录：根目录文档索引

| 文件 | 大小 | 说明 |
|------|------|------|
| `README.md` | 7.71 KB | 项目主文档（架构、技能、状态） |
| `CORE-ARCHITECTURE.md` | 6.14 KB | 系统架构"宪法"（目录职责、软链接、同步策略） |
| `QUICKSTART.md` | 2.87 KB | 5 分钟快速上手指南 |
| `REQUIREMENTS.md` | 4.85 KB | 环境要求详细说明 |
| `SKILLS-CATALOG.md` | 11.38 KB | 技能清单与部署手册 |
| `CHANGELOG.md` | 3.75 KB | 版本变更日志 |
| `requirements.txt` | 2.01 KB | Python 依赖清单（含安装命令） |
| `.gitignore` | 846 B | Git 忽略规则 |

---

> **文档版本**：v2.1.0 | **生成时间**：2026-04-28 16:18
> **生成者**：Claw 🦀（AgentOS 智能体外骨骼）
> **数据来源**：agent-os 实际文件结构和内容分析

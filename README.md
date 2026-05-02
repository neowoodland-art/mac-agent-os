# AgentOS —— 智能体操作系统

> 版本 2.0.1 | 更新于 2026-04-25 | 设备：MacBook Air M1 8GB

---

## 一、是什么

AgentOS 是一个本地运行的智能体操作系统，为 AI Agent（Claw 🦀）提供记忆、知识、技能、同步四大基础能力。

**核心理念**：
- **四级记忆**：L0 安全约束 → L1 索引 → L2 事实 → L3 原文，截断不 fallback
- **技能驱动**：所有能力封装为技能，按触发词路由
- **本地优先**：数据存储在本地 Obsidian，坚果云同步
- **结构化输出**：去文学化，先结论后步骤

---

## 二、目录结构

```
~/workbuddy-agent-os/agent-sync/
├── 00_bootstrap/           # 初始化脚本
│   ├── init.sh             # 一键初始化
│   └── apply-config.sh     # 配置部署
├── 01_core/                # 核心配置（部署到 ~/.workbuddy/）
│   ├── SOUL.md             # 最高约束（L0 硬约束）
│   ├── IDENTITY.md         # 身份档案
│   └── USER.md             # 用户画像
├── 02_skills/              # 技能包（同步到 ~/.workbuddy/skills/）
│   ├── _template/          # 技能模板
│   ├── memory_manager/     # 记忆管理
│   ├── kb_manager/         # 知识库管理
│   ├── inbox_refine/       # 收件箱提纯
│   ├── collect_to_inbox/   # 分类目录汇聚收件箱 ★ 新增
│   ├── auto_collector/     # 24h 自动收集
│   ├── content_processor/  # 统一内容处理
│   ├── web_crawler/        # 网页抓取+反爬
│   └── sync_manager/       # 同步管理
├── 03_knowledge/           # Obsidian 知识库（含首页 README.md）
│   ├── 00_inbox/           # 📥 收件箱（待提纯）
│   ├── 01_daily/           # 📅 日记
│   ├── 10_concepts/        # 💡 概念层
│   ├── 20_methods/         # 🔧 方法层
│   ├── 30_facts/           # 📋 事实层
│   ├── 40_references/      # 📎 参考层
│   ├── 50_resources/       # 🛠 资源层
│   ├── 60_opinions/        # 💭 观点层
│   ├── 90_archive/         # 🗄 归档层
│   └── 99_system/          # ⚙️ 系统层（模板/分类/配置）
├── 04_memory/              # 四级记忆体
│   ├── vector_db/          # L1 关键词索引
│   │   └── keyword_index.json
│   ├── long_term/          # L2 结构化事实 + L3 原文
│   │   ├── facts.db
│   │   └── raw/
│   ├── daily_summaries/    # 每日摘要
│   ├── logs/               # 运行日志
│   └── memory_backup/      # 备份
├── 05_tools/               # 工具脚本
├── 06_runtime/             # 运行时（任务日志、缓存）
├── 07_migration/           # 迁移打包
├── requirements.txt        # Python 依赖
├── SKILLS-CATALOG.md       # 技能清单与部署手册
├── REQUIREMENTS.md         # 依赖详细说明
├── QUICKSTART.md           # 快速开始
├── CHANGELOG.md            # 变更日志
└── README.md               # 本文件
```

---

## 三、技能体系

### 技能清单（14 个）

| 技能 | 用途 | 触发词 | 状态 |
|------|------|--------|------|
| memory_manager | 记忆提炼/去重/冲突检测 | 记忆更新、整理记忆 | ✅ |
| kb_manager | 知识入库/分类/检索 | 入库、保存知识 | ✅ |
| inbox_refine | 收件箱提纯归档+更新首页 | 提纯、整理收件箱 | ✅ |
| collect_to_inbox | 分类目录汇聚收件箱 | 归集、收集到收件箱 | ✅ |
| auto_collector | 24h 自动监控收集 | 开始收集、收集报告 | ✅ |
| content_processor | 统一内容处理入口 | 转笔记/剪藏/采集 等 | ✅ |
| web_crawler | 网页抓取+反爬 | 抓取、crawl | ✅ |
| sync_manager | 备份/导出/同步状态 | 备份知识库 | ✅ |
| bilinote | 视频→结构化笔记 | 转笔记、摘字幕 | ⚠️ 需 Docker |
| web-clipper | 网页→Markdown | 剪藏、摘抄 | ✅ |
| voice-summary | 语音→核心要点 | 语音摘要 | ✅ |
| social-collector | 小红书/抖音→笔记 | 采集 | ✅ |
| tikomni-data | 跨平台数据引擎 | tikomni | ✅ |
| obsidian | Vault 操作 | - | ✅ |
| Playwright Scraper | 浏览器抓取 | - | ✅ |

### 数据流

```
用户输入
  ↓
Claw 解析意图 → 匹配触发词 → 加载技能
  ↓
┌──────────────────────────────────────────┐
│  content_processor（统一路由层）          │
│  ├─ 视频 → bilinote                     │
│  ├─ 文章 → web-clipper                  │
│  ├─ 语音 → voice-summary                │
│  └─ 社交 → social-collector             │
└────────────────┬─────────────────────────┘
                 ↓
         各分类目录（视频笔记/阅读笔记/灵感素材/...）
                 ↓
         collect_to_inbox 汇聚收件箱（每日 2:30 自动 / 手动"归集"）
                 ↓
         00_inbox/（收件箱，标准化 MD）
                 ↓
         inbox_refine 提纯归档（每日 3:00 自动 / 手动"提纯"）
                 ↓
         分类写入 03_knowledge/ 对应目录 + 更新首页
                 ↓
         memory_manager 提炼 → 04_memory/ (L1/L2/L3)
```

---

## 四、固定路径速查

```
# Python（所有脚本用这个）
AGENTOS_PYTHON=~/.workbuddy/binaries/python/envs/agent-os/bin/python3

# Node.js
MANAGED_NODE=~/.workbuddy/binaries/node/versions/22.12.0/bin/node

# 坚果云同步
NUTSTORE=~/NutstoreCloudBridge/

# 知识库
KNOWLEDGE_BASE=~/workbuddy-agent-os/agent-sync/03_knowledge/
```

---

## 五、快速开始

```bash
# 1. 初始化
cd ~/workbuddy-agent-os/agent-sync && bash 00_bootstrap/init.sh

# 2. 安装 Python 依赖
~/.workbuddy/binaries/python/envs/agent-os/bin/pip install -r requirements.txt

# 3. 冷启动记忆体
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 \
  02_skills/memory_manager/bootstrap_from_memory.py --root ~/workbuddy-agent-os/agent-sync

# 4. 验证
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 -c \
  "import sqlite3; c=sqlite3.connect('04_memory/long_term/facts.db'); print(f'L2 事实数: {c.execute(\"SELECT COUNT(*) FROM facts\").fetchone()[0]}')"
```

详细步骤见 [QUICKSTART.md](QUICKSTART.md)，依赖说明见 [REQUIREMENTS.md](REQUIREMENT.md)，技能清单见 [SKILLS-CATALOG.md](SKILLS-CATALOG.md)。

---

## 六、当前状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 核心配置 | ✅ | SOUL/IDENTITY/USER 已部署 |
| Python 环境 | ✅ | venv + 全部依赖已安装 |
| Node.js 环境 | ✅ | TikOmni 已安装 |
| 记忆系统 | ✅ | L2 有 36 条事实，每日 2:00 自动提炼 |
| 知识库 | ✅ | 目录就绪 + 首页 + 模板 + 分类体系 |
| 收件箱提纯 | ✅ | inbox_refine 每日 3:00 自动执行 |
| 收件箱汇聚 | ✅ | collect_to_inbox 每日 2:30 自动执行 |
| 技能包 | ✅ | 15 个技能已创建 |
| 坚果云同步 | ✅ | 路径 ~/NutstoreCloudBridge/ |
| oMLX | ✅ | v0.3.6 已安装，模型：Qwen3-8B-MLX-4bit（4.1GB，Q4_K_M） |
| Obsidian | ✅ | 已安装，Vault 绑定 03_knowledge/ |
| Playwright Chromium | ⚠️ | 浏览器下载失败（网络问题） |
| BiliNote Docker | ⚠️ | 待部署 |
| Homebrew | ❌ | 未安装（可选） |

---

## 七、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 2.1.0 | 2026-04-25 | 新增 inbox_refine 技能 + 知识库首页 + 收件箱提纯自动化 + oMLX/Obsidian 安装 |
| 2.0.1 | 2026-04-25 | 依赖统一+文档修正+新增 auto_collector/content_processor |
| 2.0.0 | 2026-04-25 | AgentOS 初始化框架落地 |

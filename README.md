# AgentOS —— 多智能体协同操作系统

> 版本 3.0.0 | 更新于 2026-05-02

---

## 一、是什么

AgentOS 是一个本机运行的**多智能体协同系统**。它可以让多台电脑通过 Git 组成一个 **智能体联邦**：一台作为主节点(master)负责知识提纯和核心维护，其他机器作为工作节点(maintainer)和采集节点(node)负责内容采集和本地运营。

**核心理念**：
- **角色驱动**：master / maintainer / node 三级角色，脚本自动检查身份决定行为
- **全量Git跟踪**：agent-sync/ 目录全量进 Git，不搞选择性部分同步
- **本地自主**：向量数据库、本机记忆、原始素材存储在 agent-local/，不同步
- **提交流道**：各节点通过 submissions/ 提交内容，master 统一提纯发布

---

## 二、目录结构

```
~/workbuddy-agent-os/
├── agent-sync/                  # Git 全量跟踪（协同目录）
│   ├── 00_bootstrap/            # 初始化脚本
│   │   ├── init.sh              # 一键初始化（创建目录/软链接/身份/依赖）
│   │   └── apply-config.sh      # 配置部署
│   ├── 01_core/                 # 核心配置模板（本地化到 agent-local/identity/）
│   │   ├── SOUL.md              # 最高约束（L0 硬约束，共享）
│   │   ├── IDENTITY.tpl.md      # 身份模板（init.sh 生成本机版）
│   │   ├── USER.tpl.md          # 用户模板
│   │   └── HOST_ID.tpl.md       # 主机标识+角色模板
│   ├── 02_skills/               # 技能包（全量同步）
│   │   ├── memory_manager/      # 记忆管理
│   │   ├── kb_manager/          # 知识库管理
│   │   ├── inbox_refine/        # 收件箱提纯（仅 master 执行）
│   │   ├── collect_to_inbox/    # 分类目录汇聚收件箱
│   │   ├── auto_collector/      # 24h 自动收集
│   │   ├── content_processor/   # 统一内容处理
│   │   ├── web_crawler/         # 网页抓取+反爬
│   │   ├── git_sync_manager/    # Git 多机同步管理器
│   │   └── matrix/              # 多平台养号
│   ├── 03_knowledge/            # Obsidian 知识库（master 管理）
│   │   ├── 00_inbox/            # 收件箱（master 提纯用）
│   │   ├── 01_submissions/      # 各节点提交箱（maintainer/node 写入）
│   │   ├── 10_concepts/         # 概念层
│   │   ├── 20_methods/          # 方法层
│   │   ├── 30_facts/            # 事实层
│   │   ├── 40_references/       # 参考层
│   │   ├── 50_resources/        # 资源层
│   │   ├── 60_opinions/         # 观点层
│   │   ├── 90_archive/          # 归档层
│   │   └── 99_system/           # 系统层
│   ├── 04_memory/
│   │   ├── cross_machine/       # 跨机有价值记忆（master 汇总）
│   │   ├── daily_summaries/     # 共享摘要
│   │   ├── long_term/raw/       # → agent-local/memory/raw（软链接）
│   │   └── CHANGELOG.md
│   ├── 05_tools/                # 工具脚本
│   │   ├── 00_setup/agentos/    # agentos CLI
│   │   └── 01_system/           # 系统工具（role_check.py 等）
│   ├── 06_runtime/cache/        # → agent-local/runtime/cache（软链接）
│   ├── 07_migration/            # 迁移打包
│   ├── requirements.txt
│   ├── CORE-ARCHITECTURE.md     # 核心架构文档 v3.0
│   ├── SKILLS-CATALOG.md        # 技能清单
│   ├── QUICKSTART.md            # 快速开始
│   ├── CHANGELOG.md
│   └── README.md                # 本文件
│
└── agent-local/                 # 本机专属（不同步）
    ├── identity/                # 从模板生成的身份文件
    │   ├── IDENTITY.md          # 本机版（含本机设备信息）
    │   ├── USER.md
    │   └── HOST_ID.md           # 本机标识 + 角色 + 能力开关
    ├── memory/
    │   ├── raw/                 # L3 对话原文
    │   ├── vector_db/           # 向量数据库（升级后本地重建）
    │   └── daily/               # 本机每日记忆摘要
    ├── materials/               # 原始素材
    ├── submissions/             # 待提交内容
    │   ├── inbox/               # 知识提交到 master
    │   └── memory_export/       # 有价值记忆提交
    └── runtime/
        └── cache/
```

---

## 三、多智能体协同架构

### 角色体系

| 角色 | 权限 | 负责任务 | 自动化 |
|------|------|---------|--------|
| **master** | 读写全部协同目录 | 知识提纯、记忆汇总、核心维护 | 全部启用 |
| **maintainer** | 写入 submissions/ | 内容采集、本地记忆、提交价值内容 | 采集/记忆启用 |
| **node** | 只提交不写入 | 信息采集、素材上传 | 仅采集启用 |

所有自动化脚本启动时自动调用 `role_check.py` 检查角色，不匹配则跳过。

### 数据流管道

```
# 采集 → 提交 → 提纯 → 发布
[节点] web_crawler/content_processor
    → agent-local/materials/
    → agent-local/submissions/inbox/     ← 人工或自动筛选有价值内容
    → git push                           ← 提交到协同目录
    → [master] git pull
    → inbox_refine 审核提纯（仅 master 执行）
    → 03_knowledge/                      ← 发布到知识库
    → git push                           ← 所有节点获取

# 记忆流
[所有机器] daily_digest 本机提炼
    → agent-local/memory/daily/          ← 本地存储
    → agent-local/submissions/memory_export/  ← 有价值记忆提交
    → [master] 定期汇总
    → 04_memory/cross_machine/           ← 跨机记忆库

# 升级流
git pull
    → agentos upgrade
    → agentos rebuild-vector             ← 本地重建向量库
    → agentos localize                    ← 生成本机身份
```

---

## 四、技能体系

### 核心技能（16 个）

| 技能 | 用途 | 触发词 | 角色约束 |
|------|------|--------|---------|
| memory_manager | 记忆提炼/去重/检索 | 记忆更新、整理记忆 | 全部 |
| kb_manager | 知识入库/分类/检索 | 入库、保存知识 | master |
| inbox_refine | 收件箱提纯归档 | 提纯、整理收件箱 | **仅 master** |
| collect_to_inbox | 分类目录汇聚收件箱 | 归集、收集到收件箱 | 全部 |
| auto_collector | 24h 自动监控收集 | 开始收集、收集报告 | 全部 |
| content_processor | 统一内容处理入口 | 转笔记/剪藏/采集 | 全部 |
| web_crawler | 网页抓取+反爬 | 抓取、crawl | 全部 |
| git_sync_manager | Git 多机同步配置 | git同步、SSH配置 | 全部 |
| matrix | 多平台养号 | 养号、切换账号 | 全部 |
| sync_manager | 备份/导出 | 备份知识库 | master |
| bilinote | 视频→笔记 | 转笔记、摘字幕 | 全部 |
| web-clipper | 网页→Markdown | 剪藏、摘抄 | 全部 |
| voice-summary | 语音→要点 | 语音摘要 | 全部 |
| social-collector | 小红书/抖音→笔记 | 采集 | 全部 |
| tikomni-data | 跨平台数据引擎 | tikomni | 全部 |
| obsidian | Vault 操作 | - | 全部 |

---

## 五、agentos CLI 命令

| 命令 | 功能 | 使用场景 |
|------|------|---------|
| `agentos init` | 换机一键初始化 | 新机器首次部署 |
| `agentos sync` | 双机技能/MCP同步 | 新机器/升级后 |
| `agentos skill` | 技能管理 | 技能操作 |
| `agentos tool` | 工具管理 | 工具操作 |
| `agentos check` | 全系统健康检查 | 验证系统 |
| `agentos upgrade` | 统一模块升级 | 拉取+安装+检查 |
| `agentos rebuild-vector` | **本地重建向量库** | 升级后执行 |
| **`agentos localize`** | **从模板生成本机身份** | 新机器配置 |
| `agentos backup` | 备份 agent-local/ | 定期备份 |
| `agentos restore` | 还原备份 | 数据恢复 |
| `agentos config` | 配置管理 | 配置 diff/apply |

---

## 六、快速开始

### 新机器部署（从零开始）

```bash
# 1. 克隆仓库
git clone git@gitee.com:babycalf/mac-agent-os.git ~/workbuddy-agent-os/agent-sync

# 2. 一键初始化（目录/软链接/依赖）
cd ~/workbuddy-agent-os/agent-sync && bash 00_bootstrap/init.sh

# 3. 生成本机身份（设置角色）
agentos localize
# → 编辑 agent-local/identity/HOST_ID.md 设置 role: master/maintainer/node

# 4. 同步技能到 WorkBuddy
agentos sync

# 5. 升级依赖
agentos upgrade

# 6. 重建向量数据库
agentos rebuild-vector

# ✅ 完成！系统根据角色自动运行对应任务
```

### 日常使用

```bash
# 拉取最新代码
cd ~/workbuddy-agent-os/agent-sync && git pull

# 检查系统状态
agentos check

# 重建向量库（升级后执行）
agentos rebuild-vector

# 提交有价值内容到 master
# → 手动放置内容到 agent-local/submissions/inbox/
# → master 运行 inbox_refine 时自动处理
```

---

## 七、当前状态

| 模块 | 状态 | 版本 |
|------|------|------|
| 多智能体协同架构 | ✅ v3.0 | 2026-05-02 |
| 角色体系 | ✅ master/maintainer/node | 2026-05-02 |
| 身份模板 | ✅ IDENTITY/USER/HOST_ID 模板化 | 2026-05-02 |
| 角色校验 | ✅ role_check.py | 2026-05-02 |
| 提交流道 | ✅ submissions/ 管道 | 2026-05-02 |
| 向量数据库 | ✅ agentos rebuild-vector 本地重建 | 2026-05-02 |
| Git双远程 | ✅ Gitee + GitHub | 2026-05-02 |
| 技能包 | ✅ 16 个技能（含 git_sync_manager） | 2026-05-02 |
| core 配置 | ✅ 全量 Git 跟踪 | 2026-05-02 |

---

## 八、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 3.0.0 | 2026-05-02 | 多智能体协同架构：角色体系、模板身份、角色校验、提交管道、向量本地重建、全量 Git 跟踪 |
| 2.1.0 | 2026-04-25 | 新增 inbox_refine 技能 + 收件箱自动化 |
| 2.0.0 | 2026-04-25 | AgentOS 初始化框架落地 |

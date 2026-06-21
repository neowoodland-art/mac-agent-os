# AgentOS 项目变更日志

## [4.2.0] - 2026-06-21

### 文档体系重构
- **新建 `01_core/VERSION`** — 版本唯一来源，终结版本打架
- **新建 `99_system/INDEX.md`** — 项目文档总索引，一处维护全部引用
- **精简 AGENTS.md** — 从 180 行→56 行，去掉过时硬编码数字
- **精简 README.md** — 从 246 行→26 行，改为入口性质

### 技能归档
- **归档 4 个空技能**：content_processor、web_crawler、auto_collector、cloakbrowser_controller（移至 `02_skills/_archived/`）
- **collect_to_inbox 降级**：SKILL.md 从 v2.0 降为 v1.0，标记 `status: legacy`，文档与实际代码一致

### 版本收敛
- **guardd.py 版本从 VERSION 读取**：不再硬编码 `version = "2.3.0"`
- **所有 version.json 对齐到 SKILL_CARD.yaml**：memory_manager 1.2.0, inbox_refine 1.1.0, kb_manager 1.1.0, sync_manager 1.1.0
- **collect_to_inbox SKILL_CARD 降级**：1.1.0→1.0.0 `status: legacy`

### 架构宪法发布
- **新建 `CONSTITUTION.md`**（根目录）— 架构总纲，包含 12 维全景、10 条硬规则、版本规则、开发决策流程
- **部署到 `~/.workbuddy/CONSTITUTION.md`** — WorkBuddy AI 按需加载，开发工具硬性读取
- **规则 11：架构变更必须更新宪法** — 目录层级/功能维度/版本规则/文件权限等变更时同步更新
- **`99_system/ARCHITECTURE_CONSTITUTION.md`** 标记为已迁移（指向根目录版本）
- **所有入口已更新**：AGENTS.md / 99_system/INDEX.md / apply-config.sh
- **inbox_refine SKILL.md 对齐**：1.0.0→1.1.0
- **03_knowledge/versions.json 更新**：4.1.0→4.2.0

### 代码层清理
- **统一 CLI 入口**：`00_setup/agentos` 成为统一入口，同时加载 `07_matrix/scripts/agentos/plugins/` 的联邦命令
- **`mc` 脚本指向统一 CLI**：优先使用 00_setup/agentos 包路径
- **废止 accounts_registry.yaml**：所有账号分配统一在 ORACLE.yaml 中管理
  - `guardd _sync_account_override()` 改为读取 ORACLE.yaml
  - 支持 ORACLE 多平台格式（一个 identity 绑定 douyin + xiaohongshu）
- **删除 guardd cross_machine 心跳写入**：不再写入 `cross_machine/machines/{UID}/heartbeat.json`，避免 Git 污染
- **自动化配置入仓**：新建 `01_core/automation/`
  - `workflows.yaml` — WorkBuddy 4 个自动化任务定义
  - `launchd/com.agentos.guardd.plist.template` — guardd plist 模板

### 文档修复
- **FEDERATION_GUIDE.md 数字更新**：蓝图 14→12，guardd 检查项更新为 9 模块
- **federated-multi-machine-architecture.md guardd 模块更新**：7→9，补齐 dashboard_sync 和 sync_checker
- **SOUL.md.v2-backup 归档标记**
- **03_knowledge/99_system/ 冗余文件归档**：ARCHITECTURE_AUDIT.md 等 6 个文件标记为已归档

## [4.1.0] - 2026-05-15

### 联邦式多机协同架构（V2.1）
- **新增 `docs/DASHBOARD_DATA_LAYER_V2.md`** — 联邦式数据架构完整设计文档
- **新增 7 大协同子系统**：
  1. 状态机（heartbeat.json, 5-10min 周期, 15min 离线判定）
  2. 事件总线（events/ 跨机事件日志, 10 种事件类型）
  3. 任务协作（tasks/ 异步文件机制, pending→in_progress→completed）
  4. 加密通讯（RSA-4096 密钥对, 公钥注册/私钥本地, encrypted/ 加密消息）
  5. 知识双向同步（拉取总知识库更新 + 推送本地知识到 submissions/）
  6. 自动升级（versions.json 版本清单, breaking 自动/手动双模式）
  7. 文件直传（SSH rsync 全自动 + AirDrop 半自动备选）
- **新增 `guardd` 守护进程**：9 模块主循环（最初文档记录为 7 模块，实际代码实现 9 模块，v4.2.0 已修正）, launchd 安装, 5 分钟周期, 全规则引擎 0 token 消耗
- **新增 `cross_machine/` 子目录**：events/ status/ tasks/ encrypted/ knowledge/
- **README.md 升级 v4.1.0**：新增"多机联邦协作"章节 + 第四层导航
- **新增安全边界**：私钥/API Key 固定在 agent-local/identity/secrets/, 永不进入 agent-sync/

### 文档更新
- 新增 03_knowledge/99_system/ 知识卡片：联邦式多机协同架构
- 新增 01_core/MAINTENANCE_GUIDE.md guardd 运维章节

## [4.0.0] - 2026-05-03

### 系统文档体系重构
- 根目录精简：从 12 个文件减至 4 个（README + CHANGELOG + requirements + .gitignore）
- 删除废弃文件：01_submissions.md(空)、agent-os.code-workspace、REQUIREMENTS.md(与requirements.txt重复)、VERSION(不再维护)
- 归档过时文档：CORE-ARCHITECTURE.md / SKILLS-CATALOG.md / QUICKSTART.md → 99_system/archive/
- README.md 重写为三层导航体系（入口→系统文档→技能/知识库）
- 新增 01_core/UPDATE_SYSTEM.md 更新体系规范
- 新增 99_system/architecture/loading-architecture.md 四管道加载架构
- 新增 99_system/architecture/trigger-matching-analysis.md 触发词方案分析

### 协议体系重构
- SOUL.md v4.0 精简版：5671B（减重 40%），仅含行为规则+模式切换+安全边界
- 协议文件从 20_methods/agent-protocols/ → 99_system/protocols/
- 4 个协议全部重写对齐新规范（高阶思维/跨域联想/卡壳干预/知识审查）
- 新增 trigger_matcher.py 语义匹配脚本（关键词+Embedding混合模式）

### 配置维护
- apply-config.sh v2.0：增加版本追踪 + 多机角色预设 + 自动注册
- .config-version.json 自动生成部署记录
- .obsidian/ 解除 Git 追踪（各机器独立配置不冲突）
- 知识库清理：归档测试文件 + 删除 14 个空占位目录 + README 更新
- **`agentos config`** — 配置管理子命令（status/diff/apply/rollback）
- `01_core/CONFIG_MANIFEST.yaml` — 配置清单（9文件，A/B/C三类管理）
- `agentos/config_mgr.py` — 配置管理引擎
- `agentos init` 新增 PATH 自动检测配置
- `VERSION` 文件（版本号唯一来源）

### 修复
- 路径清理：删除 `~/workbuddy-agent-os/agent-sync/` 和 `~/workbuddy-agent-os/agent-local/` 残留目录
- 5 个脚本的 help 文本从"agent-os-local 根目录"修正为完整路径

### 变更
- Git 双远程仓库：Gitee + GitHub 同步推送
- 停用坚果云，完全切换到 Git 版本管理

## [2.2.0] — 2026-05-01

### 新增
- **`agentos upgrade`** — 统一模块升级引擎
- MODULE.md 标准化规范（首个: Matrix 模块）
- `auth_manager.py` 原子化登录模块
- SOUL.md v3.3 逐级加载重构（精简 72%）
- 4 个 G2 协议文件（meta-thinking/cross-domain/stuck/knowledge-review）
- Matrix 养号系统全链路稳定（3账号12/12步全部通过）

## [2.0.1] - 2026-04-25

### 修复

- **依赖管理统一**：删除旧的 `04_memory/vector_db/.venv`，统一使用 managed Python 专用 venv
  - 旧路径：`~/workbuddy-agent-os/agent-sync/04_memory/vector_db/.venv`（分散，与脚本运行环境不一致）
  - 新路径：`~/.workbuddy/binaries/python/envs/agent-os/`（统一，脚本和自动化共用）
- **init.sh 修复**：指向新 venv，用 `requirements.txt` 安装依赖
- **daily_digest.py 重写**：接入三个真实数据源（Claw 工作日志、WorkBuddy 系统画像、上轮摘要）
- **自动化任务修复**：Python 路径更新为新 venv

### 新增

- **bootstrap_from_memory.py**：冷启动脚本，首次运行时将已有 MEMORY.md 灌入 L1/L2
- **requirements.txt**：集中声明 Python 依赖（trafilatura + sqlite-utils）
- **WorkBuddy 自动化**：每日凌晨 2:00 自动执行 `daily_digest.py`（ID: `agentos`）
- **冷启动执行**：L2 写入 36 条初始事实，L1 索引同步建立

### 文档更新

- **REQUIREMENTS.md**：修正 venv 路径、更新实际设备状态、写清固定安装命令、新增自动化配置说明
- **QUICKSTART.md**：新增步骤 4（冷启动记忆体）、修正坚果云路径为 `~/NutstoreCloudBridge/`
- **README.md**：新增记忆数据流说明、固定路径速查表、补全目录说明

## [2.0.0] - 2026-04-25

### 新增

#### 核心框架
- L0→L1→L2→L3 四级记忆模型
- SOUL.md v2.0：完整的三层规则体系（硬约束/软约束/学习规则）
- IDENTITY.md v2.0：Claw 身份档案，含设备信息自动填充
- USER.md v2.0：ghai 用户档案
- mcp.json：MCP 协议基础配置模板

#### 初始化脚本
- init.sh：自动创建目录、安装依赖、填充设备信息
- apply-config.sh：核心配置部署到 ~/.workbuddy/
- import_skills.sh：技能导入
- export_skills.sh：技能打包导出

#### 技能包
- memory_manager：每日对话提炼、去重、冲突检测、版本管理
  - daily_digest.py：每日提炼脚本（凌晨 2:00 自动运行）
  - bootstrap_from_memory.py：冷启动（首次导入已有记忆）
  - memory_cleanup.py：冲突消解与过期清理
  - agent_memory_init.py：记忆体初始化
- kb_manager：知识库入库、分类、检索、备份
  - kb_ingest.py：知识入库脚本（支持 URL/文件/文本）
- _template：技能模板（SKILL.md + version.json + skill.py）
- web_crawler：网页抓取（占位）
- sync_manager：同步管理（占位，由坚果云替代）

#### 知识库
- 按属性分层目录结构（概念/方法/事实/参考/资源/观点）
- 16 个一级领域子目录
- 知识卡片模板（概念卡/事实卡/方法卡/个人洞见卡）
- 领域分类表（domains.md）
- 知识属性分类表（nature-types.md + 分类决策树）
- 中文映射配置（folder-aliases.json）
- 知识分类提示词模板

#### 迁移脚本
- pack.sh：全量打包
- unpack.sh：解包还原
- backup.sh：手动备份

#### 说明文件
- README.md：项目概览
- QUICKSTART.md：5 分钟快速上手
- REQUIREMENTS.md：环境依赖清单
- CHANGELOG.md：本文件

### 设计决策

| 决策 | 选择 | 原因 |
|---|---|---|
| 知识库物理目录分层 | 按属性（概念/方法/事实/...）为第一层 | 人找知识先想"类型"再想"领域"，机器检索空间更小 |
| 记忆读取策略 | L2 置信度不足直接截断，不 fallback 到 L3 | 节省 token，避免无关信息干扰 |
| 跨机同步 | 坚果云，不用 Git | 国内访问 Git 不稳定 |
| 存储策略 | 单条存储线 + 平台自适应 | 避免数据分裂，init.sh 自动检测系统 |
| 目录命名 | 英文文件夹名 + 中文映射 | 机器兼容性 + 人类可读性 |
| Python 环境 | managed Python + 专用 venv | 不污染系统环境，版本可控 |

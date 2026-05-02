# AgentOS 项目变更日志

## [2.3.0] - 2026-05-02

### 新增
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

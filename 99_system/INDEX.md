# AgentOS 项目文档索引

> 最后更新: 2026-06-21 | 版本: 4.2.0

## 系统身份与规则（01_core/ → ~/.workbuddy/）

| 文件 | 说明 | 加载方式 |
|:-----|:------|:---------|
| **CONSTITUTION.md** | **架构宪法（先读此文件）** | **部署到 ~/.workbuddy/ 按需加载** |
| SOUL.md | AI 行为规则、模式切换、安全边界 | 常驻 ~750 tokens/次 |
| IDENTITY.md | 系统身份、设备信息（从模板生成） | 常驻 |
| USER.md | 用户画像与偏好 | 常驻 |
| MAINTENANCE_GUIDE.md | 运维操作手册 | 按需查阅 |
| mcp.json | MCP 服务配置（filesystem/memory/peekaboo） | WorkBuddy 启动时加载 |
| VERSION | 版本唯一来源 | 所有文档以此为准 |

## 行为协议（03_knowledge/99_system/protocols/）

| 协议 | 触发场景 | 加载时机 |
|:-----|:---------|:---------|
| meta-thinking | 升维思考、本质追问 | 触发词激活 ~200 tokens |
| cross-domain | 跨界类比、新视角 | 触发词激活 |
| stuck-intervention | 卡壳暂停给选项 | 条件触发 |
| knowledge-review | 知识入库审查 | 触发词激活 |

## 技能（02_skills/）

当前活跃 7 个技能（4 个已归档，见 `02_skills/_archived/README.md`）：

| 技能 | 版本 | 说明 | 状态 |
|:-----|:-----|:------|:-----|
| memory_manager | 1.2.0 | 五级记忆体 + 语义检索 | ✅ |
| inbox_refine | 1.0.0 | 收件箱 AI 分类归档 | ✅ |
| collect_to_inbox | 2.0.0 | 提交箱→收件箱归集 | ⚠️ 文档降级（代码未同步） |
| kb_manager | 1.1.0 | 知识库管理 | ✅ |
| matrix | 1.0.0 | 矩阵养号（实现在 05_tools/07_matrix/） | ✅ |
| sync_manager | 1.1.0 | 同步备份 | ✅ |
| peekaboo_controller | 1.0.0 | macOS GUI 自动化（MCP） | ✅ |

## Dashboard 看板

| 文档 | 路径 | 说明 |
|:-----|:------|:------|
| Dashboard README | `05_tools/10_dashboard/README.md` | **看板架构、API、CMD_REGISTRY、前端调用规范（必读）** |
| 五层架构审计 | `PLANS/AUDIT_5LAYER_REPORT.md` | 所有视图的合规状态 |
| 命令传导统一治理 | `PLANS/COMMAND_UNIFICATION_PLAN.md` | 2026-06-25 治理方案 |

## 工具（05_tools/）

| 工具 | 说明 | 调用方式 |
|:-----|:------|:---------|
| 00_setup/agentos/ | 系统管理 CLI（init/check/backup/upgrade/…14 命令） | 命令行 |
| 00_setup/guardd/ | 联邦守护进程（9 模块，300 秒周期） | launchd 自动 |
| 01_system/ | 系统诊断脚本（12 个 .py） | agentos check / 手动 |
| 05_crawl/ | 内容采集（longcat + content-inspiration） | 手动 / API |
| 07_matrix/ | 矩阵养号（Camoufox 浏览器 + 12 个蓝图） | mc CLI / Dashboard |
| 08_trae_agent/ | Trae AI 编程助手 | CLI |
| 09_ave/ | 视频工厂 | CLI / API（8001 端口） |
| 10_dashboard/ | 监控面板（FastAPI 1521 行 + 15 插件） | 浏览器 :9988 |

## 联邦系统

| 文档 | 路径 |
|:-----|:------|
| 联邦宪法 | ORACLE.yaml |
| 联邦使用指南 | FEDERATION_GUIDE.md |
| 联邦架构 | 03_knowledge/99_system/architecture/federated-multi-machine-architecture.md |
| 加载与检索架构 | 03_knowledge/99_system/architecture/loading-architecture.md |
| cross_machine 结构 | 04_memory/cross_machine/ |
| 守护进程源码 | 05_tools/00_setup/guardd/guardd.py（1166 行） |

## 架构全景

| 文档 | 路径 | 说明 |
|:-----|:------|:------|
| **架构宪法**（先读此文件） | **CONSTITUTION.md**（根目录，同时部署到 ~/.workbuddy/） | **总纲：硬规则 + 十二维全景 + 版本规则 + 开发决策流程** |
| 系统全景 | 99_system/AGENTOS-PANORAMA.md | 完整系统概述 |
| 联邦多机架构 | 03_knowledge/99_system/architecture/ | 技术架构设计 |
| 内容收集全链路 | 03_knowledge/99_system/pipelines/ | 采集→归档规范 |
| 记忆与知识体系 | 03_knowledge/99_system/architecture/ | 分层记忆设计 |

## 版本体系

版本唯一源：`01_core/VERSION`

| 组件 | 版本 |
|:-----|:-----|
| AgentOS 框架 | 4.2.0 |
| guardd 守护进程 | 2.3.0 |
| ORACLE schema | 1.0 |

版本规则：
- **大版本（X.0.0）** — 核心框架或联邦架构升级
- **中版本（0.X.0）** — 工具级增加或重大升级
- **小版本（0.0.X）** — 配置小项目升级、bugfix

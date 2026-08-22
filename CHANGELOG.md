# AgentOS 项目变更日志

## [4.5.0] - 2026-08-16

### 新增：评论互动全量模型（v2 重构，替换 4.4.0 分组模型）

#### 核心变化：账号分组 → 账号全量 × 视频按比例 × 动作组合
- **账号全量执行** — 每个账号对"命中的视频"执行该视频的动作组合（点赞/收藏/评论连做），不再分组分工（删除点赞组/收藏组/评论组概念）
- **视频比例控制** — 点赞 90% / 收藏 30% / 评论 60%（可调 0-100），每个视频独立随机决定动作组合，未命中任何动作的视频直接跳过
- **评论两道闸门（防封号）** — 每视频评论上限（默认 5，随机挑账号评）+ 每账号日评论上限（默认 20，到限自动降级为只赞藏）
- **评论内容可控** — 评论互动内置「⚙️ 评论内容设置」折叠面板（13 角色数字输入 → 按视频生成评论池 → 可编辑/删除/重新生成），执行时按序领取设定内容（`comment_map`），未设定退回随机语料
- **蓝图组合机制** — 引擎支持 `+` 分隔组合蓝图名（如 `interact_like+interact_collect+interact_comment`），`merge_blueprints()` 合并 steps（goto_url 去重 + 连续 wait 合并），无需新蓝图即可同视频多动作连做
- **删除误导项** — 删除百分比滑块（strategy 模式下实际不生效）、浏览作者其他作品（默认不执行）、关注动作、账号分组参数

#### 新增：评论工作台疑问类角色（一问一答）
- **🙋 提问（questioner）** + **💬 回答（answerer）** 两个独立角色，新增「疑问类（一问一答）」分组（提问默认 17% > 回答 12%）
- 语料库新增「解答」分类（14 条评论 + 5 模板，通用化无行业限制，混用"隔空回应式"/"独立解答式"）
- 后端 `role_counts` 精确计数模式（`generate` 接口 + `batch_get_comments_by_roles` 支持，每个角色精确取 N 条，不受比例取整误差影响）

#### 修复：抖音页面改版兼容（8 月中 data-e2e 属性变更）
- **前置条件软条件机制** — `Condition.soft` 标志：like/collect/follow 的按钮 selector 条件失败时不再跳过（skipped），放行底层兜底（键盘 Z / JS 文字查找 / 坐标）；其他操作硬条件行为完全不变（保护旧蓝图）
- **评论内容生效** — `_resolve_args` 的 `@corpus` 占位符优先使用 `--comment-text`（计划/面板设定的内容），未指定才从语料库随机取
- **账号中心远程昵称取不到** — `account_service.py get_all_accounts()` 远程账号 profile 合并被 if/else 逻辑错误挡住（远程账号 tags 为空永远进不了 `_get_profile_for_account` 分支），改为无条件合并远程 profile（guardd `/accounts/profiles`），本机与远程对等
- **账号标签保存不上** — 远程账号打标签 PATCH 返回 400（本机 MatrixManager 无此账号）；改为远程账号 tags 写入集中标签文件（`agent-local/data/account_tags_cache.json`，读取侧 `_load_tags_cache` 已读此文件）；前端 `_saveTags` 增加响应检查（失败不再静默）
- **评论互动 MD 表格导入** — 导入区新增「📋 MD表格」入口：粘贴 Markdown 表格（`| 标题 | 链接 | 评论数 |`）自动正则提取「标题+链接」对并解析（纯前端正则，0 AI 调用）
- **评论互动引导内容** — 评论内容设置面板新增「🎯 引导内容」输入框 + 「引导引用比例」（默认 80%）：引导类（guide_*）+ 回答型（answerer）角色按比例在 AI 生成时结合引导内容（如"引导关注公众号约号"），其他角色正常；不输入引导内容则行为不变
- **AI 优化与消耗监控** — AIGenerator 关闭思考模式（`thinking: disabled`，评论生成无需推理，reasoning_tokens 归零，成本直降）；AI 调用记录 token 用量到 `agent-local/runtime/ai_usage.jsonl`；新增 `/api/ops/ai/usage` 聚合接口；看板「统计概览」首页新增「🤖 今日 AI 消耗」卡片（token/费用/次数/缓存命中率，按 flash 官方空闲价估算）

#### 技术说明
- 计划生成器 `_build_interact_plan` v2 位于 `command_bus.py`，strategy 参数改为 `like_ratio / collect_ratio / comment_ratio / comment_per_video / comment_daily_limit / pace`
- 组合蓝图实现在 `engine.py` 的 `merge_blueprints()`
- 前端数字输入全部带范围保护（比例 0-100、评论上限 0-20、日限 1-100、角色条数 0-20）
- 改动文件：`command_bus.py` / `matrix-interact.js` / `comment-workbench.js` / `comment_workbench.py` / `mc/corpus.py` / `corpus/douyin.yaml` / `engine.py` / `douyin_ops.py` / `ops/_base.py`
- ⚠️ `01_core/VERSION` 未修改（版本由 ghai 决定），正式发布时同步

## [4.4.0] - 2026-08-09

### 新增：互动计划生成器（批量互动防封号核心）

#### 核心能力
- **账号分组（30赞/5评/5藏）** — 40 账号按数量随机分组，不同动作混合执行，模拟真人分散行为
- **每视频评论配额** — 每条视频最多 N 条评论（默认 5，可调 3/10），不再全量账号评论
- **每账号评论日上限** — 默认 12 条/天，达上限自动踢出轮动池（点赞/关注不限流）
- **账号轮动** — 评论账号随机轮动分配，避免同一账号连续刷
- **评论内容随机** — 从语料库随机取（dict 解析兼容），避免重复文案
- **执行节奏两档** — 🐢宽松（慢安全）/ ⚡紧凑（快风险高），间隔按动作区分

#### 配套
- 新增 `interact_collect.json` 蓝图（收藏操作，之前是占位符）
- 批量互动页新增「📊 互动策略」参数区（评论上限/评论日上限/分组数/节奏）

#### 修复
- `--comment_text` → `--comment-text`（参数名连字符，argparse 不再报错）
- 语料库 dict 解析（`{"text":...}` 取 text 字段）
- 前端接受 `accepted` 状态（提交成功不再误报"未知错误"）

#### 技术说明
- 计划生成器在 `command_bus.py` 的 `_build_interact_plan()`，strategy 模式走独立路径，不动 mc 引擎/guardd
- 账号数 < 分组需求时，账号优先填评论组（收藏/点赞组可能为空）

## [4.3.0] - 2026-08-05

### 新增：抖音博主监控系统（抖追踪重大升级）

#### 博主跟踪闭环
- **视频行「👤 跟踪」按钮** — 在抖追踪「跟踪中」列表，一键把视频作者加入博主监控
- **博主监控 Tab** — 博主列表（粉丝/涨粉/作品数/今日采集状态）+ 手动刷新单个/全部
- **每日快照** — 记录粉丝数/获赞数/作品数/新视频，按天存 `douyin_authors.json`
- **新视频发现** — 刷新博主时自动发现新视频并加入视频跟踪
- **趋势查看** — 博主历史快照展开（每日粉丝/作品/新视频）
- **前3条视频展示** — 博主行直接显示最新3条视频（标题+点赞/评论/收藏）

#### 抖追踪列表增强
- **标题/作者关键字动态筛选** — 输入即过滤（不重建 DOM，五笔输入不失焦）
- **每页条数 100/200/300 可选** + 上一页/下一页/跳页
- **跟踪中搜索/全选/删除选中** — 批量清理无效跟踪
- **已跟踪状态持久化** — 用博主 uid 精确匹配，刷新后不再重复跟踪

#### 修复
- 账号选择器筛选改为**包含逻辑（AND）** + 保留选中状态（原为排除逻辑，只能选一个条件）
- track-video 重复跟踪不再覆盖 `prev_stats`（保留对比链）
- 去掉指挥台历史失败累计告警（只增不减无告警意义）
- 抖追踪全部更新 F5 后恢复进度提示（sessionStorage）

#### 技术说明
- 博主数据接口用「数字 uid」（`profile/other`、`aweme/post`），不能用 sec_user_id（会报 UserId不合法）
- 新增 8 个博主监控 API 端点 + `get_author_profile`/`get_author_videos` 采集函数

## [4.2.2] - 2026-07-26/27

### 运维改进 + 账号中心增强

#### 修复：clear-all 清不完远程机器队列
- **`_guardd_api()` 加 timeout 参数** — 默认 5s，clear-all 用 10s
- **clear-all 返回逐台结果** — 全部成功返回 `ok`，有失败返回 `partial`
- 解决了远程机器偶尔连通性差导致队列清不干净的问题

#### 新增：账号中心批量删除标签
- 选中多个账号后底部弹出「🏷️ 删除标签」按钮
- 弹窗列出选中账号的所有标签，点击即删除
- 逐账号 PATCH 更新，界面自动更新

#### 修复：5kecheng guardd POST 挂死
- guardd 运行 28 天后 `do_POST` handler 卡死（`rfile.read` 阻塞）
- 重启后恢复，guardd 版本号更新至 v2.3.1

#### 修复：mediacrawler_adapter CDP 采集优化
- 去掉 Playwright 降级方案（headless 模式有封号风险）
- CDP 断连时全量重建 Playwright 实例，不重用旧 state
- 新增 Chrome 状态检测 + 一键重启 API
- 新增登录状态检测 + 打开登录页功能
- 复用已有 Chrome 页面执行 fetch，不创建新标签页（零闪烁）

## [4.3.0] - 2026-07-15/16

### 抖追踪系统 + CDP 采集引擎

#### 新增：抖追踪全链路
- **🎵 抖追踪 Tab** — 从 tyhtak API 导入视频列表 → CDP 采集 → 跟踪 → 历史
- **📡 跟踪中 Tab** — 独立跟踪专项页，显示 👍/💬/⭐ 数据 + 评论区
- **全选/勾选机制** — 列表全选勾选框 + 单条勾选 + 采集选中/跟踪选中
- **一键复制** — 单条复制、复制已选、复制全部（标题+链接）
- **刷新全部 / 更新选中** — 逐个刷新（3 秒间隔）+ 进度显示，支持选择性刷新
- **评论展开** — 默认 5 条，点「展开全部」看 20 条

#### 新增：MediaCrawler 风格 CDP 采集引擎
- **`mediacrawler_adapter.py`** — Chrome CDP 模式，复用 Chrome 登录态调抖音官方 API
- 全局单例 Session，不复用已关闭 tab，避免重复开浏览器
- CDP 不可用时自动降级 Playwright 标准模式
- 获取准确数据：点赞/评论/收藏/分享/20条热评

#### 新增：Chrome 远程调试开机自启
- **`com.agentos.chrome-debug.plist`** — launchd 管理，KeepAlive 崩溃后自动重启
- **`chrome_debug.sh`** — 检测 9222 端口，不在线自动启动 Chrome

#### 修复：评论工作台
- 粘贴解析支持「标题+链接」配对格式（检测 douyin.com 链接模式）
- 视频列表显示双行排版：标题 + 网址（小字灰色）

#### 修复：前端导航/路由
- 浏览器标题跟随路由页面切换（`AgentOS - 矩阵总览` 等）
- 删除 `_tryMigratedView` 双路由系统
- 修复 `#view-dynamic` display 问题
- 删除废弃视图文件：matrix-record/backup/export/run/settings
- 构建产物加入 `.gitignore`（`static/assets/`）

## [4.2.2] - 2026-06-26

### 定向评论B模式修复 — 输入方式+登录检测

#### `<douyin_ops.py>` post_comment
- **修复** B模式 (`/video/` 独立页面) 评论输入不生效问题
- 输入方式改为 **pbcopy + Meta+V 粘贴**（复制 reply_comment 方案）
- 原因：Draft.js + Camoufox(Firefox) 下 `press_sequentially` 分发的键盘事件不被正确拦截
- 粘贴是浏览器原生操作，Draft.js 可靠处理 `insertFromPaste` 事件
- 输入后验证：`_verify_comment_posted()` 检查评论区前5条是否含刚发文字
- 选择器顺序恢复为 `[contenteditable="true"]` 优先

#### `<login_state_machine.py>` DouyinDetector & DouyinLoginRecovery
- **修复** 登录检测误触广告问题（"登录后领取奖励"广告被当成未登录信号）
- **LOGGED_IN_ANCHORS** 增强：+3 个顶栏头像选择器（`[class*="DyHeader"] [class*="avatar"]` 等）
- **NOT_LOGGED_ANCHORS** 移除 `'div:has-text("登录后")'` — 太宽泛会匹配广告
- **页面文本检测** 去掉 `"登录后"` 关键词（同样匹配广告）
- **`_trigger_login` JS 兜底** 改为只查 `button, a` + `offsetHeight > 10` 过滤，防止点到广告元素

### 验证
- [ ] 定向评论手动测试中

## [4.2.1] - 2026-06-25

### 命令传导统一治理
- **新建 `PLANS/COMMAND_UNIFICATION_PLAN.md`** — 命令传导统一治理方案 v1.0
- **CommandBus 新增 CMD_REGISTRY 注册表** — 统一 cmd_type → 命令模板映射，collect 自动按账号平台选择采集蓝图
- **前端统一调用路径** — matrix-collect.js 改走 POST /api/ops/run，参数格式统一为 {type, accounts, params}
- **删除废弃路由** — routes/matrix.py 中 /collect-homepage、/collect-homepage/phone、/collect-homepage/cancel、/collect-homepage/status 已删除
- **platforms/ 标记 deprecated** — collect() 方法中的存档脚本引用已替换，添加废弃标记
- **CLI mc collect --all 修复** — 支持 --all 参数采集所有账号
- **AUDIT_5LAYER_REPORT.md 更新** — 信息采集路径审计状态更新

### 验证
- [x] Phase 1: CommandBus CMD_REGISTRY 注册表已添加，collect 默认带 --blueprints
- [x] Phase 2: matrix-collect.js 已改走 /api/ops/run，/collect-homepage 路由已删除
- [x] Phase 3: CLI mc collect --all/--phone/--account/--status 全部修复
- [x] Phase 4: platforms/*/plugin.py collect() 已改走 CommandBus，标记 deprecated
- [x] Phase 5: AUDIT_5LAYER_REPORT.md 信息采集审计已更新

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

# AgentOS 项目变更日志

## [4.6.5] - 2026-09-20

### 修复：worker 机器误跑 Dashboard 导致「数据视图分裂」（标签改了看不到）

**根因**：三台机器都装了 Dashboard 并 launchd 自启（5kecheng 从 8/21 起持续运行）。
Dashboard 是联邦统一控制平面（只有 master 应运行），worker 各自跑导致账号标签/备注等
本机数据在不同看板显示不同值 → 用户在本机改标签、去那台机器看却没变。

- **停用 worker Dashboard**：5kechengdeAir 已停用（launchctl bootout + plist 改名 .disabled，保留 guardd）；
  7kecheng 机器离线，待上线后执行脚本
- **新增一键脚本** `00_bootstrap/disable_worker_dashboard.sh`：
  - 多来源身份识别（hostname / ComputerName / LocalHostName / HOST_ID.md）→ master 上执行会**自动中止**（需 --force 才继续）
  - 停用后验证 Dashboard 进程=0 / guardd 进程>0 / 9988 端口释放
- **文档**：FEDERATION_GUIDE §3.1 增加「部署原则：只有 master 运行 Dashboard」+ 正确访问方式（统一访问 http://100.111.43.6:9988）
- 验证：5kecheng 停用后中心看板仍正常聚合三台账号（21+20+15=56）；guardd 心跳正常


## [4.6.4] - 2026-09-20

### 重构：侧边栏菜单单点化（消除三份硬编码菜单的技术债）

- **新增** `frontend/src/nav-menu.js`：全项目菜单的**唯一**定义处（5 分组 30 项）
- **三处统一引用**：`inline.js` / `navigation.js` / `modules/matrix_views.js` 均改为 `import { NAV_GROUPS }` + `const groups = NAV_GROUPS`（其他代码零改动）
- **零行为变化**：以重构前**实际生效**的菜单（matrix_views.js 的启用项）为基准；旧菜单里未上线的项（matrix-corpus / matrix-commands 等）以注释形式保留在 nav-menu.js，需要时取消注释即可
- 验证：构建产物「API 配置」出现次数 **3 → 1**（确认单点）；三处无残留旧菜单定义；菜单规模 5 组 30 项
- 收益：**以后新增/删除菜单只改 nav-menu.js 一处**，不会再出现改了菜单看不到（4.6.2 踩过的坑）


## [4.6.3] - 2026-09-20

### 新增：API Key 版本管理（替换 / 回滚 / 删除 —— 支持轮换已泄露的 key）

- **保存即归档**：填入新 key 保存时，旧值**自动存入历史**（标记「被替换」），不会丢失
- **🔄 一键回滚**：历史面板列出该字段的所有版本（脱敏 + 备注 + 时间 + 🟢使用中），点「🔄 启用」即可切回旧版本；切换前的当前值也会自动归档，可来回切
- **🗑 删除版本**：确认无用的旧版本（如已泄露的 key）一键删除；**使用中的版本禁止删除**（提示先切换）
- 存储：`agent-local/tools/ave/config/key_history.yaml`（600 权限，不进 git）；接口只回传索引 + 脱敏值，**不下发完整 key**
- 后端：`POST /config/api-keys/activate`（切换生效）/ `POST /config/api-keys/delete`（删除版本）；GET 增加 `history` 字段
- 实测全流程：保存 A → 保存 B（A 自动归档）→ 切换回 A（B 归档，A 变使用中）→ 删除 B → 删除使用中版本被拒（400）✓

## [4.6.2] - 2026-09-19

### 修复：🔑 API 配置菜单项看不到（菜单存在**三处**硬编码，实际生效的那处未改）

- **根因**：侧边栏菜单有三处硬编码定义，`main.js` 的 import 顺序决定谁生效：
  ```
  12: import './inline.js'                → 菜单 A（最先，被覆盖）
  18: import './navigation.js'            → 菜单 B（被覆盖）
  24: import './modules/matrix_views.js'  → 菜单 C ← 最后加载，实际生效
  ```
  新加的 api-config 只加在 A/B 两处，**生效的 C 没加** → 用户看不到
- **修复**：三处菜单的「服务」分组全部补上 `api-config`；构建产物验证「API 配置」出现 3 次 ✓
- **顺带健壮性**：`inline.js` 的 `_renderNav()` 优先委托 `window.renderNav()`；`navigation.js` 自动渲染加 `DOMContentLoaded` 保护
- **技术债记录**：三处菜单硬编码重复（`inline.js` / `navigation.js` / `modules/matrix_views.js`），建议后续抽为统一 `nav-menu.js` 单点定义，避免同类问题再发

## [4.6.1] - 2026-09-19

### 优化：AI 配置单点化（key 全项目只在配置中心一处）

- **`AIGenerator._load_config()` 三级优先级**：
  1. 环境变量 `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL`（最高，容器/CI 友好）
  2. **配置中心** `agent-local/tools/ave/config/local.yaml → llm.*`（推荐，全项目唯一配置点）
  3. 兼容旧配置 `05_tools/07_matrix/config/ai.yaml → ai.*`（兜底）
- **`ai.yaml` 的 key 清空**（本机文件）：改 key 只需在 Dashboard → 🔑 API 配置 一处操作，彻底避免两处不一致
- **配置页新增 2 项**：`模型名`（如 deepseek-v4-flash）/ `API 地址`，与密钥区分处理
  - 接口新增 `secret` 标记：密钥类脱敏显示（前 5 + 后 4）+ 输入框 password；普通配置（模型名/地址）明文显示 + 输入框 text
- ⚠️ **修正一处副作用**：`local.yaml → llm.model` 原为 `deepseek-chat`，会覆盖 ai.yaml 的 `deepseek-v4-flash`（导致改用计费更高的模型）→ 已修正为 `deepseek-v4-flash`，并写入 ai_usage 日志验证
- 实测：环境变量覆盖 ✅ / 配置中心覆盖 ai.yaml ✅（临时目录精确验证）/ 缺配置中心时回退 ✅ / 端到端生成 ✅（日志记录 model=deepseek-v4-flash）

## [4.6.0] - 2026-09-19

### 新增：🔑 API 配置页面 + pre-commit 防泄露钩子（公开仓库密钥安全方案）

背景：仓库保持 public，但历史曾误提交密钥（百炼 / DeepSeek）。本版提供「各使用者自行配置密钥」的完整机制。

- **🔑 API 配置页面**（Dashboard → 服务 → 🔑 API 配置）
  - 按用途分组展示 10 项配置：AI 文本（DeepSeek）/ 视觉分析+人物置换（百炼）/ 图像生成（可灵）/ 素材（Pexels）/ 视频生成（火山方舟·即梦）/ 语音合成（火山）
  - 每项显示**脱敏状态**（前 5 + 后 4 位）+ ✅已配置/⚠️未配置徽章 + 「🧪 测试」就地验证连通性
  - 输入框填入新 key → 保存（留空保存 = 清除）；页面明示「只存本机、不进 git」
  - 后端 `routes/api_config.py`：GET 状态 / POST 保存 / POST 测试；写入 `agent-local/.../local.yaml`（自动 chmod 600）
  - **安全设计**：接口一律脱敏不回显完整 key；仅允许写入白名单字段（防越权）；日志只记后 4 位
- **pre-commit 防泄露钩子**（`00_bootstrap/hooks/pre-commit`，deploy.sh 自动安装）
  - 提交前扫描暂存内容，命中 key 模式（`sk-`/`api-key-kling-`/`AKLT`/`LTAI`/`ark-`）即**阻止提交**并提示
  - 实测：假 key 提交被正确拦截 ✓
- **deploy.sh 引导**：部署完成后提示「打开 Dashboard → 🔑 API 配置填自己的 key」+ 环境变量用法
- 实测：状态查询 9/10 项正确脱敏；保存 → 600 权限 → 清除 全链路通过；越权路径被拒（400）；测试接口正确识别（可灵✅ / 百炼账号欠费⚠️ / DeepSeek 旧 key 401❌）

## [4.5.9] - 2026-09-19

### 新增：初次抓取筛选增强（点赞/评论区间 + 发布时间）

- **👍 点赞区间**：原「点赞≥」单值 → 改为 `下限~上限` 区间（留空=不限）
- **💬 评论区间**（新增）：`下限~上限`，可按互动热度筛（如只要 100~1000 评论的）
- **📅 发布时间区间**（新增）：日期选择器 `从~到`，按视频发布时间筛选
  - 兼容两种日期格式：API 的 `2026-08-24 21:15:29` 与页面兜底的 `20260814`（统一归一化为 `YYYY-MM-DD`）
- 行数据新增 `data-comments` / `data-pub` 属性；两处筛选逻辑（初次抓取 + 导入路径）同步更新
- 实测：区间边界逻辑验证通过（赞 10~100 时 150 赞被正确过滤、无数据行在区间/日期筛选下被排除、空筛选全显示）

## [4.5.8] - 2026-09-18

### 新增：引导条数可控 + 引导要求强化

- **🎯 引导条数**输入框：指定带引导要素的评论条数（留空=自动 30%；填大些可多生成再挑选；0=不带引导）
- **引导要求提到最高优先级**（prompt 首位）：明确「必须恰好 N 条带出，一条都不能少」，并给出多角度示例（有人问怎么找 / 有人分享经历 / 有人说预约方式 / 有人夸技术）
- **自然过渡引导**：若引导要素与讨论主题差异大，要求用自然联想过渡（吃辣油腻 → 肠胃遭不住 → 找医生 → 怎么挂号），杜绝生硬插入
- 容量保护：引导条数不超过「总数 − 路人条数」，避免与路人配比冲突
- 实测（10 条 + 引导 6 条 + 引导路径）：明确引导 4 条 + 痛点铺垫 3 条，植入自然（"我爸那次拖着不去，后来朋友介绍了个肛肠科主任…关键要提前约"）
- 用法建议：引导条数填大（如 8）+ 倍数 1.5x → 生成更多含引导的评论，从中挑选终稿

## [4.5.7] - 2026-09-18

### 新增：讨论角色配比 + 长评论 + 生成倍数（+ 修复 max_tokens 截断）

- **👥 角色配置**（折叠区）：8 角色（过来人/追问者/赞同者/纠结者/质疑者/分享者/路人/好奇者）可填条数配比 → AI 严格按配比生成；留空 = AI 自由发挥（prompt 要求角色多样、不机械轮换）
- **📖 长评论条数**：控制 60~150 字「娓娓道来讲经历」型评论数量（默认 2，0~3）—— 由过来人讲亲身经历，有前因后果有细节
- **⚡ 生成倍数** 1x/1.5x/2x（默认 1.5x）：多生成便于人工挑选删除（配比模式放大配比、自由模式放大总数）
- **铺垫克制硬约束**：开场闲聊 + 转折过渡合计 ≤ 总数 25%，尽快进入实质讨论
- **🔧 修复 AI 输出被截断**（根因）：`_call_api` 的 `max_tokens` 原硬编码 300，加长评论后 token 需求暴增（10 条含 2 长评论需 ~1000 token）→ 只输出 4 条；改为**动态计算**（`total×60 + 长评论×250 + 300`，上限 4000），timeout 30s→60s
- **warning 提示**：AI 输出条数不足期望时前端明确提示（"AI 少输出 N 条，可重新生成或手动补"），期望值按配比总和计算
- 实测：配比 10 条 → 精确输出 10 条（过来人3/追问者2/路人2/赞同者2/纠结者1），长评论 3 条质量达标

## [4.5.6] - 2026-09-18

### 新增：讨论主题自动提取 + 引导路径（起点→要素→收尾）

- **🎯 主题自动提取**：解析视频后自动从标题提炼讨论主题（如标题含"肥肠面" → 主题"肥肠面"）；主题框旁加「🔄 提取」按钮可重提；不覆盖用户已填
- **🧭 引导路径**（新增字段，与讨论走向并存）：
  - 起点 = 讨论主题（自动来）+ 终点 = 引导要素（用户填）
  - 「🤖 AI 生成路径」按钮：按「开场 → 转折 → 逐个要素 → 收尾行动」推演
  - **步数自适应**：max(3, 2 + 要素数)，封顶 6 步（1 要素→3 步 / 2 要素→4 步 / 3 要素→5 步）
  - 约束：引导要素一个都不能漏，每个至少 1 步承载；最后一步负责行动收尾
- 生成讨论时把「主题 + 引导要素 + 引导路径 + 讨论走向」一起喂给 AI，保证讨论**按路径推进并落到引导目标**
- 实测（肥肠面例子）：主题提炼"肥肠面"✓；2 要素→路径 4 步✓；生成 10 条讨论严格按路径推进（聊肥肠面 → 肠胃遭不住 → 推荐主任 → 预约挂号），要素全覆盖
- 后端：`POST /comment-workbench/extract-topic`、`POST /comment-workbench/generate-path`（+ corpus.py extract_topic / generate_guide_path）

## [4.5.5] - 2026-09-17

### 优化：讨论走向改为三步显式流程（写想法 → AI 生成 → 采用）

- **① 写想法**：自然语言随便写（可跳跃、口语）
- **② AI 生成讨论方向**：AI 理解后输出 3~6 阶段结构化方向，显示在独立框，**可手动修改**
- **③ ✅ 采用此方向**：点采用后写入「最终走向」（生成讨论时使用），流程有明确确认步骤
- 切换预设走向时自动隐藏 AI 方向区，保持流程清晰
- 实测：三步流程（生成→修改→采用→写入最终走向）验证通过

## [4.5.4] - 2026-09-17

### 新增：讨论走向「预设模板 + AI 拆解」

- **6 个预设走向**（下拉选择，不用自己想）：疑问解答型 / 亲历分享型 / 质疑争论型 / 对比选择型 / 场景切入型 / 感叹种草型
- **自定义自然语言 → AI 拆解**：写一段话（可跳跃、口语化），点「🤖 AI 拆解走向」→ AI 输出 3~6 阶段的清晰走向 → 可在结果框手动修改后再生成
- 解决「用户写的走向 AI 读不懂」问题：先拆解成结构化走向，再作为生成 prompt 输入
- 实测（用户原始想法：「讨论肥肠引到肛肠医院，对面开肥肠店，医生下来吃…宋佳…孙刘星」）：
  → AI 拆解出 6 阶段（肥肠店位置 → 发现就在医院对面 → 调侃医生下楼吃 → 聊医院名气 → 具体医生 → 收尾调侃），关键信息零遗漏
- 后端：`POST /api/comment-workbench/parse-outline` + AIGenerator.parse_discussion_outline

## [4.5.3] - 2026-09-17

### 新增：评论工作台「多人讨论」模式（AI 一次生成讨论剧本 → 拆条分发）

- **生成机制**：AI **一次调用**生成完整讨论剧本（多人接力对话，每行带角色标签），系统按行拆成独立评论
  - 实测：12 条一次生成，角色标签齐全、接力感强、3 个引导对象自然分散植入、路人打酱油 2 条
- **多引导对象**：引导要素支持多行（多个推荐对象），AI 分给不同发言者自然带出（"你推你的我推我的"）
- **弱指向表达**：prompt 要求避免「楼上/上面说的」等强顺序词（适配多机并行发布）
- **条数随机分配**：下限保底 + 均匀随机加成（非刻意均摊，自然出现 1/2/3 条混合）
- **账号不足校验**：总条数 × 每账号上限 → 计算最少发言账号数，不足时明确提示补选或减条
- **围观账号**：多余账号自动不参与（不发言）；路人氛围由 AI 写进剧本
- 前端：评论工作台加模式切换（🎯定向评论 / 💬多人讨论）+ 讨论设置面板 + 对话流预览（可编辑/删除）
- 后端：`POST /api/comment-workbench/generate-discussion`（生成剧本）+ command_bus `discussion` 分发分支
- 实测：dry_run 端到端链路（5 条讨论 → 5 个任务，无错误）


## [4.5.2] - 2026-08-24

### 新增：抓取源批量跟踪视频博主

- **抓取源 Tab 新增「📌 批量跟踪视频博主」折叠面板** — 粘贴视频链接（每行一个，支持「标题: xxx + 链接」格式），一键解析 + 批量跟踪博主
- **🔍 解析链接** — 正则提取全部 URL 并去重，显示数量
- **📌 批量跟踪** — 逐个调用 track-author 解析博主加入「博主监控」，实时日志显示 新增/已存在/失败 + 失败明细，重复博主自动跳过
- **后端 `_extract_aweme_id` 支持抖音精选页链接** — `jingxuan?modal_id=xxx` / `discover?modal_id=xxx` 格式（modal_id 即视频 aweme_id），此前只支持 `/video/数字` 和短链
- 实测：jingxuan 链接正确解析 aweme_id（7673872336403957937 等），批量跟踪需抖音登录态

## [4.5.1] - 2026-08-23

### 新增：评论互动「存为默认」设置持久化

- **💾 存为默认** — 执行区新增按钮，把当前所有互动/评论设置存入浏览器 localStorage：互动动作比例（点赞/收藏/评论）、执行间隔、评论闸门（每视频上限/每账号日限/节奏）、评论内容设置（13 角色条数）、引导内容 + 引导引用比例、AI 改写开关
- **自动填充** — 下次打开评论互动页面自动应用已保存默认值（角色输入框在展开评论内容设置时按默认值初始化）
- **↩️ 恢复默认** — 清除已保存默认，恢复系统默认值（引导类各 1 条、其余 0）
- 实测：保存→读取→角色初始值→清除 全链路验证通过

### 修复：评论互动多视频生成只有 1 个视频评论（URL query 被截断）

- 根因：`_ia_parse` 的 URL 提取 `line.split(/[?\s]/)` 把 `?` 后的 query string 截掉，抖音 jingxuan 链接的 `modal_id` 在 `?` 后 → 40 个视频 url 全变成同一个 `https://www.douyin.com/jingxuan` → 评论池 `comment_map` 只剩 1 个 key
- 修复：改为 `line.trim().split(/\s+/)` 只按空白切分，保留完整 URL（含 modal_id）
- 实测：3 个视频解析出 3 个唯一 url，commentMap 3 个 key

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

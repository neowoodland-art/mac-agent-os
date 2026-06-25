# 评论互动系统 — 详细规划

> 版本: v1.0-draft | 日期: 2026-06-25
> 范围: 定向评论 + 收藏点赞 → 合并为"评论互动"全功能
> 基于: AgentOS 联邦多机协同 + CommandBus 分发 + 现有蓝图引擎

---

## 一、功能全景

### 1.1 核心能力

| 能力 | 说明 |
|:-----|:------|
| **定向评论** | 给指定视频/博主评论，多个账号参与 |
| **三级接力评论** | A评→B回复A→C回复B，形成互动链 |
| **点赞互动** | 点赞视频/评论/关注评论者 |
| **定时错开** | 跨小时/跨天的评论时间编排 |
| **跨机协同** | 三台机器之间任务分配与排队 |
| **语料集成** | 现有语料库(L1-L4)复用 + 上下文感知 |
| **评论载体** | 文字 + emoji + 图片（预留） |

### 1.2 用户场景

```
用户输入:
  博主/视频链接: https://www.douyin.com/video/xxx
  或博主主页:    https://www.douyin.com/user/xxx
  互动策略:     热评互动 / 三级接力 / 点赞关注
  时间窗口:     2小时 / 跨天
  参与账号:     douyin_136, xhs_7 (自动分配给7kecheng)
                douyin_01, xhs_01 (自动分配给5kechengdeAir)

系统输出:
  自动编排 → 按机器+时间分配任务
  → 机器1 13:00 douyin_136 发评论A
  → 机器2 13:05 douyin_01 回复A
  → 机器1 13:10 xhs_7 回复B
  → 全部完成后汇总报告
```

---

## 二、架构设计

### 2.1 系统分层

```
L5 看板层 ── 评论互动视图 (matrix-interact.js)
  │  POST /api/ops/run {type:'interact', accounts, params:{...}} 
L4 路由层 ── routes/ops.py (已存在，复用)
  │  → CommandBus.dispatch('interact', ...)
L3 分发层 ── CommandBus + CMD_REGISTRY (已存在，扩展)
  │  → 按机器分组 → 每机一条 interact 命令
  │  → 高级编排: InteractOrchestrator
L2 编排层 ── InteractOrchestrator (新增)
  │  ├── 解析互动策略
  │  ├── 生成时间线 (谁在什么时间做什么)
  │  ├── 拆解为原子任务 (每个账号每个时间点一条)
  │  └── 写入跨机任务队列
L1 执行层 ── 现有 mc run + 蓝图引擎 (复用)
  │  新增互动蓝图: interact_chain, interact_like, interact_comment
  │  复用现有: douyin_ops.py, xhs_ops.py (post_comment, like, follow)
L0 浏览器层 ── Camoufox (已有，不变)
```

### 2.2 新增模块

```
05_tools/07_matrix/
├── scripts/
│   ├── mc/
│   │   ├── cli.py           ← 新增: interact 子命令
│   │   ├── interact.py      ← [新增] 互动引擎 (InteractOrchestrator)
│   │   │   ├── InteractOrchestrator    — 主编排器
│   │   │   ├── InteractionPlan         — 互动计划
│   │   │   ├── TimeLine                — 时间线
│   │   │   └── ChainStrategy           — 接力策略
│   │   └── engine.py        ← 扩展: 支持互动蓝图的 resolve_args
│   ├── matrix_modules/
│   │   └── interact/        ← [新增] 互动模块
│   │       ├── __init__.py
│   │       ├── chain.py     — 三级接力逻辑
│   │       ├── timeline.py  — 时间线生成
│   │       └── strategy.py  — 互动策略选择
├── blueprints/
│   ├── interact_chain.json      ← [新增] 三级接力蓝图
│   ├── interact_comment.json    ← [新增] 定向评论蓝图
│   ├── interact_like.json       ← [新增] 点赞互动蓝图
│   └── interact_hot.json        ← [新增] 热评互动蓝图
```

---

## 三、蓝图设计

### 3.1 定向评论蓝图 (interact_comment)

```json
{
  "id": "interact_comment",
  "name": "互动-定向评论",
  "description": "给指定视频发评论（含语料库+表情）",
  "version": "1.0",
  "platform": "douyin",
  "steps": [
    {"step_id": 1, "op": "goto_url", "args": {"url": "@url"}},
    {"step_id": 2, "op": "wait_watch", "args": {"seconds": null}},
    {"step_id": 3, "op": "open_comments", "args": {}},
    {"step_id": 4, "op": "post_comment", "args": {"text": "@comment_text"}},
    {"step_id": 5, "op": "close_comments", "args": {}}
  ],
  "args_schema": {
    "url": {"type": "string", "required": true, "desc": "视频链接"},
    "comment_text": {"type": "string", "required": true, "desc": "评论内容，支持@corpus从语料库取"}
  }
}
```

### 3.2 三级接力蓝图 (interact_chain)

```json
{
  "id": "interact_chain",
  "name": "互动-三级接力",
  "description": "A评→B回复A→C回复B，形成互动链",
  "version": "1.0",
  "platform": "douyin",
  "steps": [
    {"step_id": 1, "op": "goto_url", "args": {"url": "@url"}},
    {"step_id": 2, "op": "wait_watch", "args": {"seconds": null}},
    {"step_id": 3, "op": "open_comments", "args": {}},
    {"step_id": 4, "op": "post_comment", "args": {"text": "@comment_text"}},
    {"step_id": 5, "op": "close_comments", "args": {}},
    {"step_id": 6, "op": "reply_to_comment", "args": {"target": "@reply_to", "text": "@reply_text"}}
  ],
  "args_schema": {
    "url": {"required": true},
    "comment_text": {"desc": "一级评论内容"},
    "reply_to": {"desc": "回复目标的评论ID或用户名"},
    "reply_text": {"desc": "回复内容"},
    "chain_position": {"enum": ["first", "reply", "second_reply"]}
  }
}
```

蓝图不分三级为三个独立的蓝图。**用同一个蓝图 + 不同参数**，InteractOrchestrator 根据 `chain_position` 决定每个账号执行哪一步。

### 3.3 点赞互动蓝图 (interact_like)

```json
{
  "id": "interact_like",
  "name": "互动-点赞互动",
  "description": "点赞视频+点赞评论+关注评论者",
  "version": "1.0",
  "platform": "douyin",
  "steps": [
    {"step_id": 1, "op": "goto_url", "args": {"url": "@url"}},
    {"step_id": 2, "op": "wait_watch", "args": {"seconds": null}},
    {"step_id": 3, "op": "like", "args": {}},
    {"step_id": 4, "op": "open_comments", "args": {}},
    {"step_id": 5, "op": "like_comment", "args": {"target": "@target_comment"}},
    {"step_id": 6, "op": "follow_user", "args": {"target": "@target_user"}},
    {"step_id": 7, "op": "close_comments", "args": {}}
  ]
}
```

### 3.4 热评互动蓝图 (interact_hot)

组合评论 + 点赞 + 回复热评：

```json
{
  "id": "interact_hot",
  "name": "互动-热评互动",
  "description": "在热门评论下回复，提升曝光",
  "version": "1.0",
  "platform": "douyin",
  "steps": [
    {"step_id": 1, "op": "goto_url", "args": {"url": "@url"}},
    {"step_id": 2, "op": "open_comments", "args": {}},
    {"step_id": 3, "op": "scroll_to_hot_comment", "args": {}},
    {"step_id": 4, "op": "like_comment", "args": {"target": "first_hot"}},
    {"step_id": 5, "op": "reply_to_comment", "args": {"text": "@reply_text"}},
    {"step_id": 6, "op": "close_comments", "args": {}}
  ]
}
```

---

## 四、任务编排引擎 (InteractOrchestrator)

### 4.1 核心流程

```
用户输入:
  {url, strategy, accounts, time_window}

InteractOrchestrator.plan()
  │
  ├── 1. 解析互动策略
  │     strategy="chain"   → 生成三级接力计划
  │     strategy="comment" → 生成批量评论计划  
  │     strategy="like"    → 生成点赞互动计划
  │     strategy="hot"     → 生成热评互动计划
  │
  ├── 2. 生成时间线
  │     根据 time_window + interval 计算每个账号的执行时间
  │     例: 3账号 × 三级接力
  │       账号A 13:00 发评论 → 间隔5分钟
  │       账号B 13:05 回复A  → 间隔5分钟
  │       账号C 13:10 回复B  → 完成
  │
  ├── 3. 拆解为原子任务
  │     每个 (账号, 时间, 蓝图, 参数) = 一条原子任务
  │     每台机器独占一条（机器级别串行，账号级别串行）
  │
  ├── 4. 写入任务队列
  │     通过 CommandBus 分发到各台机器
  │     → 不立即执行，先写入任务数据库（带时间戳）
  │     → guardd 或守护线程按时触发
  │
  └── 5. 返回计划
      {plan: [...], status: "scheduled"}
```

### 4.2 时间线生成算法

```
输入: accounts=[A, B, C], strategy="chain", window={start: "13:00", end: "15:00"}

chain 策略:
  A 在 13:00 → 发评论 (first)
  B 在 13:00 + offset1 → 回复A (reply, reply_to=A)
  C 在 13:00 + offset1 + offset2 → 回复B (second_reply, reply_to=B)

  其中 offset = random(300, 600) 秒 (5-10分钟)
  支持跨小时: offset 累加可以到 next hour

batch 策略:
  A 在 13:00 → 评论 (内容1)
  B 在 13:00 + random(300,900) → 评论 (内容2)
  C 在 13:00 + random(600,1800) → 评论 (内容3)

like 策略:
  A 在 13:00 → 点赞视频+关注博主
  B 在 13:00 + random(120,600) → 点赞视频+点赞热评
```

### 4.3 跨机任务排队

```
CommandBus.dispatch("interact", all_accounts, params)
  → 按 machine 分组
  → 每台机器构建一条 InteractOrchestrator 任务
  
每台机器上:
  MachineSession 串行队列
  
  [interact_任务A] → 执行A → 完成后
  [等待中到13:05] → 定时器触发
  [interact_任务B] → 执行B → 完成后
  ...
```

**关键**：定时触发不是由 CommandBus 的 poll 守卫做，而是由 **InteractOrchestrator 在机器本地启动一个延迟协程**。

执行流程：
```python
class InteractOrchestrator:
    async def execute_plan(self, plan: InteractionPlan):
        """按时间线顺序执行所有子任务"""
        for step in plan.timeline:
            # 等待到指定时间
            wait_seconds = (step.scheduled_at - datetime.now()).total_seconds()
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            # 执行当前步骤
            result = await self._execute_step(step)
            step.result = result
```

---

## 五、看板集成 (Dashboard)

### 5.1 新视图: 评论互动 (matrix-interact.js)

参照现在 `matrix-collect.js` 和 `matrix-nurture.js` 的模式：

```javascript
// 使用已有 account-selector 组件
// ① 选择账号
// ② 输入互动参数（URL/博主/策略/时间）
// ③ 提交 → POST /api/ops/run {type:'interact', accounts, params}
```

**交互流程**：

```
┌─────────────────────────────────────────────┐
│  💬 评论互动                                  │
│                                              │
│  账号选择器 (复用 createAccountSelector)      │
│  ┌─────────────────────────────────────────┐ │
│  │ ☑ douyin_136  🎵 7kecheng             │ │
│  │ ☑ xhs_7       📕 7kecheng             │ │
│  │ ☑ douyin_01   🎵 5kechengdeAir        │ │
│  │ ...                                    │ │
│  └─────────────────────────────────────────┘ │
│                                              │
│  互动参数:                                    │
│  视频链接  [________________________] 📋      │
│  互动策略  [热评互动 ▼] [三级接力] [点赞]     │
│  时间窗口  [13:00] ~ [15:00]                 │
│  延迟间隔  [5-10] 分钟 / 步                  │
│  语料分类  [美食 ▼] [旅行] [通用]            │
│                                              │
│  [🔍 预检]  [🚀 提交互动]                    │
│                                              │
│  执行计划预览:                                │
│  ┌─────────────────────────────────────────┐ │
│  │ 13:00 douyin_136 → 发评论 "看着就很有.." │ │
│  │ 13:05 xhs_7       → 回复 ↑ "同意！.."   │ │
│  │ 13:12 douyin_01   → 回复 xhs_7 "... "   │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### 5.2 API 路由

复用现有 `POST /api/ops/run`，新增 type `interact`：

```json
POST /api/ops/run
{
  "type": "interact",
  "accounts": ["douyin_136", "xhs_7", "douyin_01"],
  "params": {
    "strategy": "chain",
    "url": "https://www.douyin.com/video/xxx",
    "time_window": {"start": "13:00", "end": "15:00"},
    "interval": {"min": 300, "max": 600},
    "corpus_category": "food",
    "chain_position": {
      "douyin_136": "first",
      "xhs_7": "reply",
      "douyin_01": "second_reply"
    },
    "dry_run": true  // 预检模式：只返回计划不执行
  }
}
```

### 5.3 CMD_REGISTRY 扩展

```python
CMD_REGISTRY = {
    ...,
    "interact": {
        "runner": None,  # 不走 nurture_runner.sh，直接调 InteractOrchestrator
        "defaults": {"rounds": 1},
        "single_account": False,
    },
}
```

---

## 六、现有代码复用清单

### 6.1 可直接复用的

| 组件 | 用途 |
|:-----|:------|
| `account-selector.js` | 账号选择器（不改） |
| `routes/ops.py` | API 路由（扩展 type=interact） |
| `CommandBus` | 按机器分发、排队（复用） |
| `MachineSession` | 串行队列（复用） |
| `douyin_ops.post_comment(text)` | 评论发送（复用） |
| `douyin_ops.like()` | 点赞（复用） |
| `douyin_ops.follow()` | 关注（复用） |
| `xhs_ops.xhs_comment(text)` | 小红书评论（复用） |
| `corpus.py` | 语料库（复用） |
| `ai_generator.py` | AI 评论生成（复用） |
| `nurture_runner.sh` | 执行包装器（可选复用，interact 可能直接走 mc run） |

### 6.2 需要新增/扩展的

| 组件 | 说明 |
|:-----|:------|
| `mc/interact.py` | InteractOrchestrator 编排引擎 |
| `mc/cli.py` | 新增 `mc interact` 子命令 |
| `blueprints/interact_*.json` | 互动蓝图 |
| `matrix_modules/interact/` | 互动模块（chain、timeline、strategy）|
| `douyin_ops.reply_to_comment()` | 回复评论原子操作 **（新增）** |
| `douyin_ops.like_comment()` | 点赞评论原子操作 **（新增）** |
| `douyin_ops.scroll_to_hot_comment()` | 滚动到热评（新增） |
| `frontend/src/views/matrix-interact.js` | 看板视图 |

### 6.3 新增原子操作

```python
# douyin_ops.py

async def reply_to_comment(self, page, target: str, text: str) -> bool:
    """回复指定评论。target 可以是评论序号或评论者用户名"""
    # 1. 找到目标评论的回复按钮
    # 2. 点击"回复"
    # 3. 输入框聚焦
    # 4. 填入回复内容
    # 5. 发送
    pass

async def like_comment(self, page, target: str = "first_hot") -> bool:
    """点赞评论。target=first_hot / 指定序号"""
    # 1. 找到目标评论
    # 2. 找到点赞按钮（大拇指/心形）
    # 3. 点击
    pass

async def follow_user(self, page, target: str) -> bool:
    """关注指定用户（从评论区）"""
    pass
```

---

## 七、语料库增强（三级互动语料）

现有语料库是单条评论。三级互动需要**配对语料**：

```python
# 新增: interact_corpus.py 或扩展 corpus.py

# 三级互动语料对
CHAIN_CORPUS = {
    "food": {
        "first": "看着就很有食欲，周末去试试",
        "reply": "同意！上次吃过一次确实不错",
        "second_reply": "我也去过！他家那个招牌菜绝了"
    },
    "tech": {
        "first": "这个技术分析很透彻，学到了",
        "reply": "对，特别是第三点我之前完全没想到",
        "second_reply": "是的，按照这个方法试了效果很好"
    },
    "travel": {
        "first": "这个地方太美了，已加入旅行清单",
        "reply": "去年去过，风景确实很好，值得二刷",
        "second_reply": "求攻略！准备下个月去"
    },
    ...
}
```

每套三级语料包含三个层次的评论，形成一个自然的对话流。

---

## 八、实施路线图

### Phase 1（基础能力）— 2天

| 任务 | 产出 |
|:-----|:------|
| 新增 `douyin_ops.reply_to_comment()` | 原子操作 |
| 新增 `douyin_ops.like_comment()` | 原子操作 |
| 编写 3 个互动蓝图 JSON | blueprints |
| 扩展 `corpus.py` 增加三级接力语料 | 语料库 |
| 构建 `matrix-interact.js` 基础视图 | 看板 |
| 扩展 CMD_REGISTRY 增加 interact 类型 | 后端 |

### Phase 2（编排引擎）— 2天

| 任务 | 产出 |
|:-----|:------|
| 实现 `InteractOrchestrator` 核心 | mc/interact.py |
| 时间线生成算法 | timeline.py |
| 跨机任务队列 | interact 走 CommandBus |
| 预检功能 (dry_run) | 返回计划预览 |

### Phase 3（高级功能）— 2天

| 任务 | 产出 |
|:-----|:------|
| 三级接力全流程联调 | chain 端到端 |
| 跨小时定时触发 | asyncio sleep / guardd定时 |
| 看板计划预览 | 前端展示时间线 |
| 执行进度跟踪 | status API |

### Phase 4（增强）— 持续

| 任务 | 产出 |
|:-----|:------|
| 图片/表情包评论 | 蓝图扩展 |
| AI 生成评论（oMLX） | 对接现有 ai_generator |
| 互动效果分析 | 看板统计 |
| 自动策略推荐 | 基于账号健康度 |

---

## 九、关键设计决策

| 决策 | 选择 | 理由 |
|:-----|:------|:------|
| 蓝图复用 vs 新建 | 新建互动蓝图系列 | 避免污染现有养号蓝图 |
| 定时触发方式 | InteractOrchestrator 内部 sleep | 简单可靠，不依赖外部调度 |
| 三级接力实现 | 同一个蓝图+chain_position 参数 | 减少蓝图数量，参数化驱动 |
| 跨机协同 | 复用 CommandBus 队列 | 已有成熟的分发/排队机制 |
| 看板视图 | 新建 matrix-interact.js | 功能独立，不与现有视图耦合 |
| CMD_REGISTRY 扩展 | 新增 type=interact | 统一入口，不走硬编码分支 |

---

## 十、与现有系统的关系

```
现有系统              新增系统
────────              ────────
养号 (nurture)        评论互动 (interact)
├── 日常浏览           ├── 定向评论
├── 随机点赞/评论      ├── 三级接力
├── asyncio.gather     ├── 时间线编排
└── 蓝图 douyin_daily  └── 互动蓝图系列

采集 (collect)         点赞 (like) → 并入 interact
├── 读主页信息         
└── 写 profiles.json  
                          
登录 (login)           评论 (comment) → 并入 interact
├── smart-login        
└── 状态检测           
```

**合并策略**：`like` 和 `comment` 类型的 `CMD_REGISTRY` 保留向后兼容，但前端视图统一到 `matrix-interact.js`，不再使用独立的 `matrix-comment.js` 和 `matrix-like.js`。

---

## 十一、风险与对策

| 风险 | 概率 | 影响 | 对策 |
|:-----|:----:|:----:|:------|
| 回复评论 DOM 结构变化 | 高 | 中 | CSS 选择器 + JS 多兜底 |
| 跨小时 sleep 被中断 | 中 | 高 | 使用 guardd 持久化定时器 |
| 同一时间多账号冲突 | 中 | 中 | MachineSession 队列保证单线程 |
| 抖音限流/封号 | 低 | 高 | 不超过每天10条/账号 |
| 三级接力找不到目标评论 | 中 | 中 | fallback 到独立评论 |

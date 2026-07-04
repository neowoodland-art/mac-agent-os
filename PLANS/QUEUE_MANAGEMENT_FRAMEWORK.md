# AgentOS 队列管理与程序职责框架

> 版本: 1.0 | 日期: 2026-07-04
> 目标: 说清楚"什么程序管什么"、"任务怎么流转"、"三台机器各自干什么"

---

## 一、程序总图：三台机器各自运行什么

```
                    ┌──────────────────────────────────────────┐
                    │  Master（chengzigedeAir）                  │
                    │                                            │
                    │  ┌─ Dashboard ───────────────────────────────────────┐ │
                    │  │  FastAPI :9988                                    │ │
                    │  │  职责: 接收用户请求、展示状态、调度分发            │ │
                    │  │  包含: routes/*.py (API层)                       │ │
                    │  │       services/command_bus.py (调度层)            │ │
                    │  │       services/video_analyzer.py (视频分析) 🆕    │ │
                    │  │       frontend/ (前端页面 47个视图)               │ │
                    │  └────────────────────────────────────────────────────┘ │
                    │                                            │
                    │  ┌─ guardd :9090 ──────────────────────────────────────┐ │
                    │  │  16个模块 + 15秒调度循环                           │ │
                    │  │  职责: 本地任务排队→执行、心跳上报                 │ │
                    │  └────────────────────────────────────────────────────┘ │
                    │                                            │
                    │  └── 也负责自己的3台账号的养号/评论/采集 ──┘          │
                    └──────────────────────┬───────────────────────────────┘
                                           │ Tailscale
                    ┌──────────────────────────────────────────┐
                    │  Worker（5kechengdeAir / 7kecheng）        │
                    │                                            │
                    │  ┌─ guardd :9090 ─────────────────────────┐ │
                    │  │  只跑 guardd（无 Dashboard）             │ │
                    │  │  职责: 收大包→拆小包→三队列→3 slot执行 │ │
                    │  └────────────────────────────────────────┘ │
                    │                                            │
                    │  账号: 5kecheng=12个, 7kecheng=大量的      │ │
                    └──────────────────────────────────────────────┘
```

**结论**: Dashboard 只在 Master 跑，Worker 只跑 guardd。

---

## 二、每个程序的具体职责

### 2.1 Dashboard（Master 专用）

| 模块 | 文件 | 职责 |
|:-----|:------|:------|
| **路由层** | `routes/ops.py` | 接收用户提交 → 调 CommandBus |
| **命令分发** | `services/command_bus.py` | 拆解任务→按机器打包→调 guardd API |
| **视频分析** | `services/video_analyzer.py` 🆕 | 浏览器提取标题→分类→选评论 |
| **前端** | `frontend/src/views/*` | 47 个视图，用户操作入口 |

### 2.2 guardd 守护进程（每台机器都有）

| 模块 | 文件位置 | 职责 |
|:-----|:---------|:------|
| **HTTP 服务器** | `guardd.py` line 227-380 | 端口 9090，接收/响应所有 API 请求 |
| **调度引擎** | `modules/scheduler.py` | **三队列管理 + 3 slot 流水线 + 账号互斥** |
| **任务存储** | `modules/task_store.py` | 任务数据持久化（SQLite + 内存双写） |
| **优先级队列** | `modules/priority_queue.py` | heapq 实现，支持按时间调度和取消 |
| **槽位管理器** | `modules/slot_manager.py` | 3 slot 分配/释放，浏览器进程监控 |
| **执行器** | `modules/executor.py` | 子进程执行 `mc run`，解析输出，超时控制 |
| **心跳上报** | `modules/heartbeat.py` | 每15秒收集本地状态→推送给 Dashboard |
| **计划同步** | `modules/schedule_bridge.py` | 每60秒检查 ORACLE 定时任务并提交 |
| **账号监控** | `modules/account_monitor.py` | 实时检查 cookies.sqlite 登录态 |
| **清理维护** | `guardd.py` line 1420-1450 | 9 模块循环每 300 秒执行 |

---

## 三、任务流转全路径：从用户提交到账号执行

### 3.1 场景：用户提交 20 个账号评论 1 个视频

```
你 (Dashboard 浏览器)
  │ POST /api/ops/run {type:"smart_comment", accounts:[...20个], params:{urls:["https://..."]}}
  ▼
┌─ routes/ops.py line 36 ─────────────────────────────────────────────┐
│ api_ops_run()                                                        │
│  数据校验 → CommandBus.dispatch("smart_comment", accounts, params)   │
└───────────────────────────┬──────────────────────────────────────────┘
                            ▼
┌─ services/command_bus.py line 908 ──────────────────────────────────┐
│ CommandBus.dispatch()                                                │
│                                                                      │
│  STEP 1: 加载 ORACLE.yaml → 按机器分组                              │
│    7kecheng → [12个账号]                                             │
│    5kechengdeAir → [8个账号]                                        │
│                                                                      │
│  STEP 2: smart_comment 分支 (line 1007)                             │
│    ├─ 新建 VideoAnalyzer → asyncio.run(analyze_batch(urls))          │
│    │   └─ 无头浏览器打开视频 → 提取标题/描述                        │
│    │   └─ 关键词匹配 → 行业分类 (health/general)                    │
│    │   └─ 从行业池或万能池选评论                                     │
│    │   └─ 返回 {url: {title, industry, comment}}                     │
│    │                                                                  │
│    └─ 拆解: 每个账号×每个URL = 最小单元                              │
│       ├─ {douyin_133, comment, "医生讲得很清楚", P0, 7kecheng}       │
│       ├─ {douyin_134, comment, "医生讲得很清楚", P0, 7kecheng}       │
│       └─ ... × 20                                                    │
│                                                                      │
│  STEP 3: 按机器打包 → MachineSession.send()                          │
│    ├─ POST http://100.65.35.28:9090/scheduler/submit (12个P0任务)    │
│    └─ POST http://100.72.182.121:9090/scheduler/submit (8个P0任务)    │
└───────────────────────────┬──────────────────────────────────────────┘
                            ▼
┌─ guardd HTTP :9090 (Worker机器) ──────────────────────────────────┐
│ do_POST /scheduler/submit                                           │
│  → api_scheduler_submit() → _init_scheduler() → scheduler.submit() │
│                                                                      │
│  submit_task():                                                      │
│  ├─ 账号互斥检查（第1层）→ 同一账号不可同时入队                     │
│  ├─ 根据 priority 入对应队列:                                        │
│  │   P0=0 → queue_priority (优先队列)                                 │
│  │   P1=1 → queue_normal (日常队列)                                   │
│  │   P2=2 → queue_filler (劣后队列)                                   │
│  └─ 有空闲 slot → 立即分配                                           │
└───────────────────────────┬──────────────────────────────────────────┘
                            ▼
┌─ scheduler.run_cycle() 每15秒 ─────────────────────────────────────┐
│                                                                      │
│  ① _check_all_active_tasks():                                       │
│    ├─ slot0: [P1养号 douyin_133] → 还在跑？→ 检查超时              │
│    ├─ slot1: [P1养号 douyin_134] → 已完成！→ _release_slot()        │
│    │   └─ 释放 account_slots["douyin_134"]                          │
│    │   └─ 检查 paused_tasks: 有P0等这个slot? → 推入 queue_priority  │
│    └─ slot2: [P2采集 douyin_135] → 还在跑                           │
│                                                                      │
│  ② _schedule_all_slots():                                           │
│    ├─ slot0: 忙 → 跳过                                               │
│    ├─ slot1: 空闲 → _pop_by_priority()                              │
│    │   ├─ queue_priority pop → 取出 {douyin_134, comment} ← P0      │
│    │   └─ _assign_task() + account_slots["douyin_134"] = slot1      │
│    └─ slot2: 忙 → 跳过                                               │
│                                                                      │
│  ③ slot_manager.check_health(): 监控浏览器进程                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 关键：每台机器的 guardd 独立管理自己的队列

```
7kecheng 的 guardd:
  queue_priority: [P0评论×4, P0评论×3]  ← 智能评论待执行
  queue_normal:   [P1养号×22]           ← 日常养号排队
  queue_filler:   [P2采集×8]            ← 采集任务有空才做
  ---------------
  slot0: → [P1养号 douyin_133 → P0评论 douyin_183 → 恢复P1 douyin_143]
  slot1: → [P1养号 douyin_134 → P0评论 douyin_184 → 恢复P1 douyin_144]
  slot2: → [P2采集 douyin_135 → ...]
  ---------------
  account_slots: {"douyin_133":0, "douyin_134":1, "douyin_135":2}

5kechengdeAir 的 guardd:
  queue_priority: [P0评论×2]
  queue_normal:   [P1养号×15]
  queue_filler:   []
  ---------------
  slot0: → [P1养号 douyin_01 → P0评论 douyin_02 → 恢复P1 douyin_03]
  slot1: → [空闲]
  slot2: → [空闲]
  ---------------
  account_slots: {"douyin_01":0}
```

**两台机器互不干扰** — 各自管各自的队列和 slot。

---

## 四、谁管队列

### 4.1 一句话回答

| 程序 | 管什么 |
|:-----|:--------|
| **CommandBus**（Master） | 把大任务拆成最小单元 → 按机器打包 → 分发到各机 guardd |
| **guardd scheduler**（每台机器） | 收到包后 → 自己管理三队列 → 分配 3 slot 执行 → 账号互斥 |
| **guardd heartbeat**（每台机器） | 只管 **上报状态** 给 Dashboard — **不参与队列管理** |

### 4.2 详细

```
大任务（20个账号评论1个视频）
    │
    ▼ CommandBus（Dashboard 进程）
    拆成 20 个小单元
    按机器分成 2 个包: 7kecheng=12个, 5kecheng=8个
    │
    ├──→ 7kecheng guardd:
    │       收到12个P0任务 → 入 queue_priority
    │       scheduler: 从queue取 → 分到3个slot → 执行
    │
    └──→ 5kechengdeAir guardd:
            收到8个P0任务 → 入 queue_priority
            scheduler: 从queue取 → 分到3个slot → 执行
```

**heartbeat 只做状态上报，不干涉队列。**

---

## 五、三队列详细逻辑

### 5.1 队列类型

| 队列 | 变量名 | 优先级 | 谁来入队 | 何时执行 | 可被抢占 |
|:-----|:--------|:-------|:---------|:---------|:---------|
| P0 优先 | `queue_priority` | 最高 | smart_comment / 定向操作 | 有空闲 slot 立即执行 | ❌（它抢别人） |
| P1 日常 | `queue_normal` | 中 | 养号定时任务 / 日常操作 | P0 都执行完才取 | ✅ 被 P0 打断 |
| P2 劣后 | `queue_filler` | 低 | 批量采集 / 后台同步 | 只有 P0/P1 都空时才做 | ✅ 被 P0/P1 抢占 |

### 5.2 分配算法（`_pop_by_priority`）

```
每次 slot 空闲:
  ① 先看 queue_priority → 有 P0 → 取出来执行
  ② queue_priority 空 → 看 queue_normal → 有 P1 → 取出来执行
  ③ queue_normal 也空 → 看 queue_filler → 有 P2 → 取出来执行

每一步都跳过 busy 账号:
  如果任务的账号在 account_slots 表中 → 跳过不取
```

### 5.3 P0 抢占（`insert_priority`）

```
收到 P0 任务 → 检查账号:
  ├─ 账号空闲 → 直接入 queue_priority
  └─ 账号忙碌 → 挂到该 slot 的 paused_slots 列表
       slot0: [▶️P1养号 douyin_133] → paused_slots[0] = [P0评论]
       ↓ 养号完成
       _release_slot(0) → 检测到 paused_slots[0] 有 P0
       → P0 入 queue_priority → slot0 立即分配
       ↓ P0 执行完
       → 恢复被中断的 P1 队列
```

### 5.4 账号互斥表（`account_slots`）

```
account_slots = {
    "douyin_133": 0,   # douyin_133 在 slot0 运行
    "douyin_134": 1,   # douyin_134 在 slot1 运行
}

三层防护:
  第1层: submit_task() 入队时 → 检查 account_slots
  第2层: _pop_by_priority() 分配时 → 跳过 busy 账号
  第3层: slot_manager 执行前 → 浏览器级别拦截
```

---

## 六、与旧的 9 模块心跳循环的关系

### 6.1 各自独立运行

```
guardd 进程:
  ┌─ 主线程: HTTP 服务器 :9090
  ├─ 调度线程: scheduler.run_cycle() 每15秒
  └─ 原文线程: _run_heartbeat_cycle() 每300秒
               包含 9 个模块:
               1. module_heartbeat_collect
               2. module_account_cleanup
               3. module_login_check
               4. module_results_cleanup
               5. module_browser_cleanup
               6. module_knowledge_sync      ← 知识库同步
               7. module_cleanup_ops         ← 命令清理
               8. module_dashboard_sync      ← 看板同步
               9. module_sync_checker        ← 同步检查
```

**心跳只做辅助工作，不参与调度。** 调度由 `scheduler.run_cycle()` 独立完成。

---

## 七、现有技能体系与本次改造的关系

### 7.1 已归档技能（设计文档，无代码）

| 技能 | 内容 | 与本次改造的关系 |
|:-----|:------|:----------------|
| `web_crawler` | Scrapling + Crawl4AI 爬虫设计 | 实际代码未实现，但 Scrapling 已安装 ✅，可用来增强视频信息提取 |
| `content_processor` | 视频/文章/音频采集设计 | 设计框架可参考，无代码 |
| `auto_collector` | 24小时自动监控设计 | 设计框架可参考，无代码 |

### 7.2 可利用的已安装包

| 包名 | 已安装 | 可用来做什么 |
|:-----|:-------|:------------|
| **scrapling** 0.2.99 | ✅ | HTTP 静态页面抓取（比启动浏览器快） |
| **crawl4ai** | ✅ | LLM 友好的页面内容提取 |
| **cloakbrowser** | ✅ | 高反爬场景（https://www.douyin.com 动态内容） |
| **playwright** | ✅ | 浏览器自动化（当前 VideoAnalyzer 使用） |

### 7.3 可做的增强（不阻塞）

| 增强点 | 当前做法 | 可优化为 | 优先级 |
|:-------|:---------|:---------|:------|
| 视频标题提取 | 启动无头 Playwright | 先用 Scrapling HTTP 请求 meta tag，失败再降级浏览器 | 可优化 |
| 热门评论分析 | 未实现 | 爬虫获取视频页面的 top 评论，分析情感和话题 | 后续 |
| AI 生成评论 | 模板关键词匹配 | 上下文传到本地 oMLX 模型生成个性化评论 | 后续 |

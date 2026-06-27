# AgentOS 任务编排与调度系统 — 全面规划 v3.0

> 日期: 2026-06-27 | 版本: 4.3.0 规划
> 前置文档: PLANS/INTERACT_SYSTEM_PLAN.md, PLANS/COMMAND_UNIFICATION_PLAN.md, PLANS/OPTIMIZATION_PLAN_v2.md
> 当前状态: Phase 1 已落地（命令传导统一），Phase 2 启动（心跳+任务编排）

---

## 一、核心概念与场景分析

### 1.1 三台机器的角色

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  chengzigedeAir     │     │  5kechengdeAir      │     │  7kecheng           │
│  100.111.43.6       │     │  100.72.182.121      │     │  100.65.35.28       │
│  ──────────────     │     │  ──────────────      │     │  ──────────────      │
│  角色: master       │     │  角色: worker        │     │  角色: worker        │
│  Dashboard: ✅      │     │  Dashboard: ❌       │     │  Dashboard: ❌       │
│  养号: 少量账号    │     │  养号: 中等账号      │     │  养号: 大量账号      │
│  guardd: ✅         │     │  guardd: ✅          │     │  guardd: ✅          │
│  心跳: 主动推送    │     │  心跳: 通过master    │     │  心跳: 通过master    │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

### 1.2 场景拆解

**场景A — 日常养号（定时任务）**
```
每天 08:00 ~ 23:00
每台机器各自串行执行账号集合:
  账号集1（douyin账号5个）→ 约3小时
     ↓ 串行
  账号集2（xhs账号3个）  → 约2小时
     ↓ 串行
  账号集3（douyin账号4个）→ 约3小时
```
→ 每台机器的 MachineSession 串行队列，自动衔接

**场景B — 定向评论（高优插入）**
```
在养号队列运行时，突发插入:
  1. 用户提交: 视频URL + 20个账号 + 间隔40分钟
  2. 评估: 当前养号任务进度
  3. 决策: 高优先级 → 暂停养号 → 插入评论任务 → 恢复养号
```
→ 需要 **优先级队列** 和 **任务抢占/暂停/恢复** 机制

**场景C — 三级接力评论（依赖链）**
```
账号A 评论 (step1)
   ↓ 依赖: step1 成功
账号B 回复 A (step2)  
   ↓ 依赖: step2 成功
账号C 回复 B (step3)
```
→ 需要 **任务依赖图** 和 **状态回传**

**场景D — 跨机协同（三台机器协作一个任务）**
```
任务: 对同一个视频进行 20 个账号的定向评论
账号A-D 在 chengzigedeAir → 时间: 13:00-13:40
账号E-J 在 5kechengdeAir  → 时间: 13:10-14:30
账号K-T 在 7kecheng       → 时间: 13:20-16:00
```
→ 需要 **跨机时间线同步** 和 **全局任务视图**

---

## 二、当前架构的问题

### 2.1 MachineSession 队列太简单

当前: 一个机器只有一个 current_cmd + 一个 queued_cmds 列表
- ❌ 没有按优先级排队
- ❌ 没有时间调度
- ❌ 没有暂停/恢复
- ❌ 没有任务依赖

### 2.2 没有心跳同步任务状态

当前 guardd 心跳只包含 hostname/status/running_tasks/browsers_open
- ❌ 没有每个任务的详细状态
- ❌ 没有队列视图
- ❌ 没有跨机任务同步

### 2.3 没有优先级概念

当前所有任务同等优先级
- ❌ 定向评论应该比日常养号优先级高
- ❌ 没有抢占机制

### 2.4 没有任务依赖跟踪

nurture_runner.sh → mc run → 跑完就结束
- ❌ 不知道每个账号的执行结果
- ❌ step2 无法等待 step1 完成后获取其评论ID

---

## 三、新架构设计

### 3.1 总体架构

```
┌──────────────────────────────────────────────────────────────┐
│ L6 看板层 (Dashboard)                                        │
│  ├─ 操作视图 (matrix-*.js) — 提交任务                        │
│  ├─ 计划视图 (matrix-schedule.js) — 查看/管理全局时间线      │
│  └─ 任务监控视图 — 查看各机实时队列                          │
├──────────────────────────────────────────────────────────────┤
│ L5 调度层 (Scheduler) — 【新增】                              │
│  ├─ TaskScheduler         — 全局任务调度器（运行在master）    │
│  ├─ 优先级队列            — P0/P1/P2 多级队列                │
│  ├─ 时间线生成器          — 根据策略生成执行时间线            │
│  └─ 依赖管理器            — 任务依赖图解析                    │
├──────────────────────────────────────────────────────────────┤
│ L4 API 路由 (routes/ops.py) — 统一执行入口                    │
│  ├─ POST /api/ops/run     — 提交任务（已有，扩展）           │
│  ├─ POST /api/ops/schedule— 编排计划任务（新增）              │
│  ├─ GET  /api/ops/queue   — 查看队列（新增）                  │
│  └─ POST /api/ops/cancel  — 取消/暂停/恢复（新增）            │
├──────────────────────────────────────────────────────────────┤
│ L3 命令分发 (CommandBus) — 扩展                               │
│  ├─ CMD_REGISTRY          — 注册表（已有）                    │
│  ├─ MachineSession v2     — 升级为优先级+时间调度队列         │
│  ├─ CrossMachineSync      — 跨机任务状态同步（通过心跳）      │
│  └─ TaskTracker           — 任务执行追踪                      │
├──────────────────────────────────────────────────────────────┤
│ L2 执行引擎 (mc)                                             │
│  ├─ engine.py + BatchEngine — 批量执行（已有）                │
│  ├─ InteractOrchestrator   — 互动编排引擎（Phase 2 新增）     │
│  ├─ nurture_runner.sh      — 养号包装器（已有）               │
│  └─ plan_executor.py       — 计划执行器（新增）               │
├──────────────────────────────────────────────────────────────┤
│ L1 原子操作 (douyin_ops, xhs_ops) — 已有                     │
├──────────────────────────────────────────────────────────────┤
│ L0 浏览器层 (Camoufox) — 已有                                 │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 任务数据结构

```python
@dataclass
class Task:
    """统一任务描述 —— 所有操作最终落为 Task"""
    task_id: str                            # 全局唯一 task_id
    cmd_type: str                           # nurture / interact / collect / login
    accounts: list[str]                     # 涉及的账号列表
    machine: str                            # 分配给哪台机器
    priority: int                           # 0=最高(P0), 1=中(P1), 2=低(P2)
    
    # 执行计划
    schedule_type: str                      # "now" / "delay" / "cron" / "dependency"
    scheduled_at: Optional[datetime]        # 计划执行时间
    cron_expr: Optional[str]                # cron 表达式 (schedule_type="cron")
    
    # 依赖关系
    depends_on: list[str]                   # 依赖的 task_id 列表
    depends_status: list[str]               # 依赖要求的状态 ["completed"]
    interval_after_dep: int = 0             # 依赖完成后等待秒数
    
    # 执行参数
    params: dict                            # 传给执行器的参数
    blueprint: str                          # 蓝图名称
    rounds: int = 1
    
    # 运行时状态
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[dict] = None           # 执行结果
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 上下文传递（三级接力用）
    context: dict = field(default_factory=dict)
    # 例如: {"comment_id": "xxx", "comment_text": "..."}


class TaskStatus(str, Enum):
    PENDING     = "pending"      # 已创建，等待调度
    SCHEDULED   = "scheduled"    # 已安排执行时间
    QUEUED      = "queued"       # 在机器队列中等待
    PREFLIGHT   = "preflight"    # 前置检查中
    RUNNING     = "running"      # 执行中
    PAUSED      = "paused"       # 被高优任务暂停
    WAITING_DEP = "waiting_dep"  # 等待依赖完成
    COMPLETED   = "completed"    # 成功完成
    FAILED      = "failed"       # 执行失败
    CANCELLED   = "cancelled"    # 被取消
    SKIPPED     = "skipped"      # 跳过（依赖失败导致）
```

### 3.3 优先级队列设计

```python
PRIORITY_MAP = {
    "interact_chain":  0,   # 三级接力 — 最高优先级
    "interact":        0,   # 定向评论
    "comment":         0,   # 单条评论
    "login":           1,   # 登录
    "nurture":         1,   # 日常养号
    "collect":         2,   # 信息采集 — 最低优先级
    "like":            2,   # 点赞
}
```

**P0 任务（交互类）**：
- 可抢占当前运行的 P1/P2 任务
- 被抢占的任务标记为 PAUSED
- P0 执行完后自动恢复

**P1 任务（日常养号/登录）**：
- 不可抢占 P0
- 被 P0 抢占后自动暂停，P0 完成后恢复

**P2 任务（采集/点赞）**：
- 闲时执行，任何高优任务都可抢占

### 3.4 任务执行生命周期

```
PENDING → [依赖检查] → WAITING_DEP → [依赖满足]
→ SCHEDULED → [时间到] → QUEUED → [轮到]
→ RUNNING → [高优抢占?] → PAUSED → [恢复] → RUNNING
→ COMPLETED / FAILED / CANCELLED / SKIPPED
```

---

## 四、核心模块设计

### 4.1 TaskScheduler（全局调度器）

位置: 05_tools/07_matrix/scripts/matrix_modules/scheduler/

```
scheduler/
├── __init__.py
├── task.py            — Task 数据模型
├── task_store.py      — 任务持久化存储 (SQLite)
├── priority_queue.py  — 优先级队列
├── dependency.py      — 依赖图解析器
├── timeline.py        — 时间线生成器
├── cross_machine.py   — 跨机任务同步
├── scheduler.py       — 主编排器
└── executor.py        — 任务执行器
```

**核心流程**:

```
TaskScheduler.submit(task)
  ├── 1. 执行依赖分析 → 构建 DAG
  ├── 2. 按机器分组 → 分配到各机
  ├── 3. 生成执行时间线
  ├── 4. 写入 task_store (SQLite)
  ├── 5. 通知对应机器的 guardd
  └── 6. 返回 plan_id


TaskScheduler.poll()  (每 15 秒由 guardd 调用)
  ├── 1. 扫描所有 PENDING/SCHEDULED 任务
  ├── 2. 检查依赖是否满足
  ├── 3. 检查时间是否到达
  ├── 4. 检查机器是否空闲
  ├── 5. 按优先级投递到 MachineSession
  └── 6. 更新任务状态
```

### 4.2 MachineSession v2（升级队列）

```python
class MachineSession:
    """单台机器的命令执行会话 (v2.0)"""
    
    def __init__(self, machine: str):
        self.machine = machine
        self.is_local = (machine == HOSTNAME)
        self.active_task: Optional[Task] = None       # 当前执行
        self.paused_task: Optional[Task] = None        # 被抢占暂停的任务
        self.priority_queue = PriorityQueue()          # 优先级队列
        self.completed_tasks: list[Task] = []          # 已完成
        self.task_store = TaskStore()                  # SQLite 持久化
        
    def submit(self, task: Task):
        """提交任务到队列"""
        if task.priority == 0 and self.active_task and self.active_task.priority > 0:
            self._preempt(task)
            return
        self.priority_queue.push(task)
        task.status = TaskStatus.QUEUED
        self.task_store.save(task)
    
    def _preempt(self, high_task: Task):
        """高优抢占当前任务"""
        self.active_task.status = TaskStatus.PAUSED
        self.paused_task = self.active_task
        self.task_store.save(self.active_task)
        self._signal_stop(self.active_task)
        high_task.status = TaskStatus.RUNNING
        self.active_task = high_task
        self._execute(high_task)
    
    def poll(self):
        """轮询：检查当前任务状态 + 启动下一个"""
        now = time.time()
        if self.active_task and self.active_task.status.is_terminal:
            self.task_store.save(self.active_task)
            self.completed_tasks.append(self.active_task)
            if self.paused_task:
                self.paused_task.status = TaskStatus.RUNNING
                self.active_task = self.paused_task
                self.paused_task = None
                self._execute(self.active_task)
                return
            self.active_task = None
        
        if not self.active_task:
            next_task = self.priority_queue.pop_ready(now)
            if next_task:
                next_task.status = TaskStatus.RUNNING
                self.active_task = next_task
                self._execute(next_task)
```

### 4.3 心跳集成（guardd 增强）

**当前心跳**（每300秒）：
```json
{"hostname": "chengzigedeAir", "status": "online", "running_tasks": 2, "browsers_open": 3}
```

**升级后心跳**（每30~60秒，携带详细任务状态）：
```json
{
    "hostname": "chengzigedeAir",
    "status": "online",
    "machine_uid": "4cf443bc",
    "last_seen": "2026-06-27T10:00:00Z",
    "tasks": {
        "active": {"task_id": "interact_001", "cmd_type": "interact", "account": "douyin_136", "status": "running", "progress": {"step": 3, "total": 5}},
        "paused": null,
        "queued": [{"task_id": "nurture_003", "priority": 1, "estimated_at": "2026-06-27T10:20:00Z"}],
        "completed_today": 3,
        "failed_today": 0
    },
    "system": {"cpu_percent": 23.5, "memory_percent": 62.1, "browsers_open": 1}
}
```

---

## 五、三级接力评论的编排实现

### 5.1 任务链示例

用户提交: 对视频V做三级接力，账号A→B→C

TaskScheduler 生成 3 个 Task:

- Task-A: task_id="chain_V_001", accounts=["douyin_A"], machine="chengzigedeAir", priority=0, chain_position="first", schedule_type="now"
- Task-B: task_id="chain_V_002", accounts=["douyin_B"], machine="5kechengdeAir", priority=0, chain_position="reply", schedule_type="dependency", depends_on=["chain_V_001"], interval_after_dep=300
- Task-C: task_id="chain_V_003", accounts=["douyin_C"], machine="7kecheng", priority=0, chain_position="second_reply", schedule_type="dependency", depends_on=["chain_V_002"], interval_after_dep=300

### 5.2 依赖状态回传

Task-A 执行完 post_comment 后，把评论ID传回 Task-B：

```python
task.result = {
    "comment_id": "74001234567890",
    "comment_text": "一级评论内容",
    "account_id": "douyin_A",
    "status": "completed"
}

dep_result = task_store.get("chain_V_001").result
reply_to_comment_id = dep_result["comment_id"]
```

---

## 六、定时任务编排

### 6.1 从 ORACLE.yaml 到调度器

当前 ORACLE.yaml 已定义定时任务（schedules: 节），将其自动导入 TaskScheduler：

```python
schedules = oracle.get("schedules", [])
for s in schedules:
    task = Task(
        task_id=f"{s['name']}_{date}",
        cmd_type="nurture",
        accounts=s.get("accounts", "all"),
        machine=s.get("on_machines", "*"),
        priority=1,
        schedule_type="cron",
        cron_expr=s["schedule"],
        params=s.get("params", {}),
    )
    task_store.save(task)
```

### 6.2 每日时间线示例

```
08:00  每台机器开始养号
11:00  养号完成
    [空闲时段]  ← 可插入交互任务
13:00  用户提交定向评论 → P0 插入
13:05  各机分别执行评论任务
14:00  继续养号/等待
17:00  晚上养号
20:00  全部完成
```

---

## 七、与现有代码的关系

### 7.1 不需要改的

| 模块 | 原因 |
|:-----|:------|
| douyin_ops.py | 原子操作层不变 |
| xhs_ops.py | 同上 |
| engine.py | 单次批量执行引擎不变 |
| nurture_runner.sh | 养号包装器不变 |
| corpus.py | 语料库不变 |

### 7.2 需要扩展的

| 模块 | 改动 |
|:-----|:------|
| command_bus.py:MachineSession | 升级为优先级队列 |
| guardd.py:heartbeat | 增加详细任务状态 |
| routes/ops.py | 新增 schedule/queue/cancel 路由 |

### 7.3 需要新增的

| 模块 | 说明 |
|:-----|:------|
| scheduler/task.py | Task 数据模型 |
| scheduler/task_store.py | SQLite 持久化 |
| scheduler/priority_queue.py | 优先级队列 |
| scheduler/dependency.py | 依赖图 |
| scheduler/timeline.py | 时间线 |
| scheduler/scheduler.py | 主编排器 |

---

## 八、关键设计决策

### 决策1: 中心化调度

master 上的 TaskScheduler 做全局决策，worker 上的 guardd 只负责接收/执行/上报。简单可控，单点决策避免冲突。

### 决策2: 本地 SQLite 持久化

每台机器本地 SQLite (agent-local/runtime/scheduler/tasks.db)，通过心跳上报给 master。比跨网络数据库可靠。

### 决策3: 非抢占式 + 队列优先级

P0 不强制打断 P1 的当前执行轮次，而是在 P1 的下一轮前插入。Camoufox 浏览器不能随意中断。

### 决策4: 评论成功判定

post_comment 返回 'ok' AND _verify_comment_posted 找到文字 AND 拿到 comment_id。失败则重试1-2次 → 标记 FAILED → 后续依赖标记 SKIPPED。

---

## 九、实施路线图

### Phase 1（本周）— 基础架构

| 任务 | 工作量 |
|:-----|:-------|
| Task 数据模型 + TaskStore (SQLite) | 中 |
| 优先级队列 | 小 |
| MachineSession v2 升级 | 中 |
| guardd 心跳增强 | 中 |
| Dashboard 任务监控视图 | 大 |

### Phase 2（下周）— 编排引擎

| 任务 | 工作量 |
|:-----|:-------|
| TaskScheduler 核心 | 大 |
| 依赖图解析器 | 中 |
| 时间线生成器 | 中 |
| 跨机任务同步 | 中 |
| InteractOrchestrator 对接 | 中 |

### Phase 3（下月）— 高级功能

| 任务 | 工作量 |
|:-----|:-------|
| 抢占/暂停/恢复 | 中 |
| 三级接力全流程联调 | 大 |
| 定时任务 cron 支持 | 中 |
| Dashboard 计划预览 | 大 |
| 自动恢复失败任务 | 中 |

# AgentOS 任务编排与调度系统 — 全面规划 v3.0

> 日期: 2026-06-27 | 版本: 4.3.0 规划 | 第2版重写
> 基于: 用户需求深度讨论 + 现有架构审计
> 核心原则: 不新增臃肿层级，能合并的合并到现有组件

---

## 一、需求全景图

### 1.1 任务的两类本质

经过讨论，所有操作不按"动作类型"分类，而按**意图**分类：

| 维度 | 日常养号（scheduled） | 特殊交互（priority） |
|:-----|:---------------------|:--------------------|
| **触发方式** | 定时/循环自动触发 | 用户主动提交 |
| **操作内容** | 蓝图中编排的随机动作 | 指定具体目标（URL/直播间） |
| **是否指定链接** | ❌ 不指定，随机推荐流 | ✅ 指定具体视频/博主/直播间 |
| **执行时间** | 按日程表串行执行 | 随时插入，可设置间隔 |
| **优先级** | 低（可被抢占） | 高（抢占低优任务） |

**关键结论**：同一个"点赞"动作，既可以是养号里的随机点赞（走蓝图），也可以是特殊交互里的指定点赞（走定向任务）。**按意图分类而非按动作分类**。

### 1.2 任务的粒度拆解

```
用户提交: "20个账号评论这个视频"
  ↓
调度层拆解为 20 个独立子任务:
  ├─ 账号A 在 13:00 评论
  ├─ 账号B 在 13:05 评论  (间隔5分钟)
  ├─ 账号C 在 13:12 评论  (随机间隔7分钟)
  ├─ 账号D 在 13:15 评论  (随机间隔3分钟)
  └─ ...
  ↓
每个子任务 = 一条独立 Task，有自己的状态追踪
```

间隔参数：用户可设置 `{min: 5, max: 15}` 分钟，调度器在每个子任务执行完毕后随机等待。

### 1.3 任务依赖链

```
三级接力评论:
  账号A 评论           → 完成后产出 comment_id
     ↓ 依赖 A 成功
  账号B 回复 A         → 需要 A 的 comment_id
     ↓ 依赖 B 成功
  账号C 回复 B         → 需要 B 的 comment_id

直播间关注:
  所有账号先进直播间     → 等待全部进入
     ↓ 全部就绪
  同时发起关注           → 关注主播
     ↓ 关注完成
  等待10分钟            → 观看时长
     ↓ 时间到
  退出直播间
```

### 1.4 已有功能不需要改的

| 现有模块 | 原因 |
|:---------|:------|
| `douyin_ops.py` 原子操作 | 底层能力不变，只管"怎么点"不管"什么时候点" |
| `engine.py` 批量执行 | 单次批量的执行引擎逻辑不变 |
| `nurture_runner.sh` | 养号包装器不变，调度层直接调它 |
| `blueprints/*.json` | 蓝图文件不变，调度层读取蓝图参数 |
| `corpus.py` 语料库 | 评论内容生成逻辑不变 |

---

## 二、调度层放在哪？— 方案对比

### 方案A：完全新增 scheduler/ 模块（v3.0初版方案）

```
scheduler/  ← 全新模块
  ├── task.py
  ├── task_store.py
  ├── scheduler.py
  └── ...
```
- ❌ 新增一层，系统更臃肿
- ❌ 需要额外进程/线程
- ❌ 和 guardd 职责重叠

### 方案B：合并到 guardd（推荐方案）

```
guardd  ← 现有守护进程，扩展
  ├── HTTP Server (已有)        ← 扩展任务管理API
  ├── 300s周期循环 (已有)        ← 缩短到15-30s
  ├── 心跳上报 (已有)            ← 增加详细任务状态
  ├── 任务调度引擎 [新增]        ← 优先级队列+时间线
  └── 浏览器槽位管理 [新增]      ← 接管mc的浏览器限制
```

**原因**：
- guardd 已经在每台机器上运行
- guardd 已经有 HTTP API（/task 接受任务）
- guardd 已经有周期性循环（用于心跳）
- guardd 已经有跨机通信（心跳上报到 Dashboard）
- **不需要额外进程**，全部在 guardd 内部完成

### 方案C：合并到 CommandBus

```
CommandBus  ← 扩展为带调度功能
```
- ❌ CommandBus 运行在 Dashboard 进程内，Dashboard 挂了调度就停了
- ❌ CommandBus 主要职责是分发，不是调度
- ❌ 不适合做本机队列管理

### 结论：采用方案B，调度功能合并到 guardd

---

## 三、新架构（轻量级）

### 3.1 系统分层

```
┌─────────────────────────────────────────────────────┐
│ L5 看板（Dashboard）                                  │
│  ├─ 联邦指挥台 (matrix-command.js) ← 重建为任务管理  │
│  │   显示: 每台机器的实时队列 + 时间线 + 执行状态     │
│  │   操作: 提交任务 / 拖拽排序 / 暂停/恢复/取消      │
│  │   告警: 封号/登录失败/任务失败 → 高亮提示         │
│  └─ 操作视图 (matrix-interact.js) ← 提交交互任务     │
│      POST /api/ops/run {type, accounts, params}      │
├─────────────────────────────────────────────────────┤
│ L4 API 路由 (routes/ops.py)                          │
│  统一入口: POST /api/ops/run                         │
│  新增:     Task 管理路由（查看列表/取消/重排）       │
├─────────────────────────────────────────────────────┤
│ L3 命令分发 (CommandBus)                              │
│  职责缩小: 仅做按机器分组 + 模板渲染 + 投递到 guardd │
│  不再管理队列 — 队列管理下沉到各机 guardd            │
│  不再管理轮询 — 轮询下沉到各机 guardd                │
├─────────────────────────────────────────────────────┤
│ L2 本机调度 (guardd) ← 核心增强                       │
│  ├─ HTTP Server: /task (接收任务)                    │
│  │               /tasks (查询队列)                    │
│  │               /task/{id}/cancel (取消)             │
│  │               /task/{id}/pause (暂停)              │
│  │               /task/{id}/resume (恢复)             │
│  ├─ TaskScheduler: 优先级队列 + 浏览器槽位管理        │
│  ├─ Heartbeat: 每15秒上报详细状态到 Dashboard         │
│  └─ Executor: 调 mc run / mc interact / 等            │
├─────────────────────────────────────────────────────┤
│ L1 mc 引擎                                            │
│  engine.py → 单次执行，被 guardd 调用                 │
│  浏览器数量控制 → 上移至 guardd 的槽位管理            │
├─────────────────────────────────────────────────────┤
│ L0 浏览器层 (Camoufox)                                │
└─────────────────────────────────────────────────────┘
```

### 3.2 新架构的轻量说明

| 组件 | 变化 | 原因 |
|:-----|:-----|:------|
| **guardd** | 增强，非新增 | 合并调度器 + 心跳增强 + 槽位管理 |
| **CommandBus** | 瘦身 | 去掉 poll/queue 逻辑，只做分发+模板渲染 |
| **Dashboard** | 重建联邦指挥台 | 可视化任务管理（不是新增组件） |
| **scheduler/** | 不新增目录 | 代码放在 guardd 模块内 |

---

## 四、任务模型

### 4.1 任务分类（按意图）

```json
{
  "task_type": "scheduled",
  // 或 "priority"

  "task_id": "nurture_douyin_daily_20260627",
  "accounts": ["douyin_01", "douyin_02"],
  "machine": "chengzigedeAir",
  
  // 调度参数
  "schedule": {
    "type": "cron",          // cron / interval / dependency / now
    "cron": "0 8 * * *",     // 每天8点
    "interval_sec": null,     // 间隔秒数（优先级任务用）
    "interval_random": null,  // {min: 300, max: 900} 随机间隔
  },

  // 依赖（三级接力用）
  "depends_on": [],
  "interval_after_dep": 0,

  // 执行参数
  "blueprint": "douyin_daily",
  "rounds": 3,
  "params": {},               // 特殊链接等

  // 状态
  "status": "pending",
  "progress": {"current": 0, "total": 3},
  "result": null,
  "error": null
}
```

### 4.2 任务状态流转

```
PENDING ──→ QUEUED ──→ RUNNING ──→ COMPLETED
  │           │           │
  │           │      [高优抢占]
  │           │           │
  │           │      ┌────▼────┐
  │           │      │ PAUSED  │──→ [恢复] → RUNNING
  │           │      └─────────┘
  │           │
  │      [用户取消] → CANCELLED
  │
  [依赖未满足] → WAITING_DEP → [满足] → QUEUED
  
  RUNNING → FAILED → [重试] → QUEUED
                    → [重试耗尽] → FAILED
                                  → [依赖任务] → SKIPPED
```

### 4.3 账号状态跟踪

每个账号在执行过程中会维护状态，任务完成后回写：

```json
{
  "account_id": "douyin_136",
  "machine": "7kecheng",
  "status": "active",          // active / login_expired / banned / sms_verify
  "last_task": "interact_001",
  "last_error": null,
  "browser_slot": 2,            // 占用的浏览器槽位
  "tasks_today": 5,
  "failed_today": 0
}
```

当 guardd 检测到账号状态变化（登录过期/封号）→ Dashboard 收到心跳告警 → 联邦指挥台高亮显示。

---

## 五、任务拆解与插入逻辑

### 5.1 优先级任务的拆解

```
用户提交: "20个账号评论视频V，间隔5-15分钟"
  ↓
CommandBus 收到请求:
  ├─ 1. 查 ORACLE.yaml 把20个账号按机器分组
  │     机器A: 5个账号
  │     机器B: 8个账号
  │     机器C: 7个账号
  ├─ 2. 对每台机器生成一条"编排任务"
  └─ 3. 发送给各机 guardd
      ↓
各机 guardd 收到编排任务:
  ├─ TaskScheduler.decompose()
  │   ├─ 拆成5条独立子任务（每个账号一条）
  │   ├─ 计算时间线（每条间隔随机5-15分钟）
  │   └─ 写入本机 task_store
  └─ 返回编排计划给 Dashboard
```

### 5.2 优先级插入 vs 日常养号

```
当前机器队列:
  [scheduled] 养号 douyin_01-05 (P1) → 正在执行
  
插入 priority 任务:
  ├─ 方式A: 等待当前这一轮执行完 → 插入 P0
  │   养号 douyin_01-05 第3轮结束
  │   → [priority] 账号A 评论视频V (P0)
  │   → 间隔8分钟
  │   → [priority] 账号B 评论视频V (P0)
  │   → 间隔5分钟
  │   → ...全部 P0 子任务完成
  │   → [scheduled] 恢复养号 douyin_01-05 第4轮
  
  ├─ 方式B: 强行暂停当前养号
  │   养号进程收到 SIGSTOP 或 guardd stop API
  │   → 插入 P0
  │   → P0 完成
  │   → 恢复养号进程
  │   (注: 需要浏览器进程支持暂停，技术复杂)
  
  推荐用方式A: 等当前这一轮完再接 P0
  (Camoufox 浏览器不能随意中断)
```

### 5.3 浏览器槽位管理

当前：`mc/engine.py` 用 `--max-browsers=3` 控制并发浏览器数。

升级后：由 **guardd** 统一管理本机浏览器槽位：

```python
class BrowserSlotManager:
    """浏览器槽位管理器 — 在 guardd 内部
    槽位 = Camoufox 浏览器实例，identity_dir 是唯一ID
    槽位编号不重要（用户可能拖拽窗口），核心是 browser_id

    关键规则:
      1. 一个账号同一时间只能在一个浏览器上运行
      2. 槽位只是计数器，实际以 browser_id 为准
      3. 释放槽位 = 关闭浏览器进程，不是简单标记空闲
    """
    def __init__(self, max_slots=3):
        self.max_slots = max_slots
        self.slots = [None] * max_slots

    def acquire(self, account_id, identity_dir):
        for s in self.slots:
            if s and s["account_id"] == account_id:
                raise Exception(f"账号 {account_id} 已在运行")
        for i in range(self.max_slots):
            if self.slots[i] is None:
                info = {"slot_id": i, "account_id": account_id, "browser_id": identity_dir, "pid": None}
                self.slots[i] = info
                return info
        return None

    def release(self, browser_id):
        for i in range(self.max_slots):
            if self.slots[i] and self.slots[i]["browser_id"] == browser_id:
                self.slots[i] = None
                return True
        return False

    def get_usage(self):
        slots_info = []
        for i, s in enumerate(self.slots):
            if s: slots_info.append({"slot_id": i, "account_id": s["account_id"], "browser_id": s["browser_id"]})
        return {"max": self.max_slots, "used": sum(1 for s in self.slots if s), "slots": slots_info}

    def find_account(self, account_id):
        for s in self.slots:
            if s and s["account_id"] == account_id:
                return s
        return None

### 6.1 当前问题

| 问题 | 表现 |
|:-----|:------|
| 信息不全 | 只显示"运行中"，不知道每台机器的具体任务 |
| 交互不准 | 状态刷新滞后，看不到队列里有什么 |
| 无手动干预 | 不能暂停/取消/重排任务 |
| 无告警 | 封号/登录失败没有醒目提示 |

### 6.2 新指挥台设计

```
┌─────────────────────────────────────────────────────────────┐
│  🚀 联邦指挥台                                              │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  📡 三机状态总览                                         │ │
│  │   🟢 chengzigedeAir  (3/3槽位) 运行中: 养号  | 队列: 2  │ │
│  │   🟡 5kechengdeAir   (2/3槽位) 运行中: 评论  | 队列: 3  │ │
│  │   🔴 7kecheng        (0/3槽位) offline        | 心跳:-- │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  📋 chengzigedeAir 任务时间线  [今天 08:00 ~ 23:00]    │ │
│  │                                                         │ │
│  │  08:00 ── [🔄] 养号 douyin_01-05  ─── 第3轮 [▓▓▓▓░░]  │ │
│  │  11:00 ── [⏸] 养号 xhs_01-03      ─── 等待中          │ │
│  │  13:00 ── [🔴] 定向评论 视频V      ─── 子任务1/5       │ │
│  │  13:08 ── [⏳] 定向评论 视频V      ─── 子任务2/5       │ │
│  │  13:15 ── [⏳] 定向评论 视频V      ─── 子任务3/5       │ │
│  │  ...                                                     │ │
│  │  [拖拽调整顺序] [暂停] [取消] [插入新任务]              │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  ⚠️ 告警中心                                             │ │
│  │  ⚠️ douyin_136 @ 7kecheng — 登录过期 (10分钟前)        │ │
│  │  ❌ xhs_07 @ 5kechengdeAir — 封号 (2小时前)            │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 联邦指挥台能力清单

| 能力 | 说明 |
|:-----|:------|
| **状态总览** | 三台机器在线/离线、槽位使用率、当前任务、队列长度 |
| **时间线视图** | 每台机器今天已执行和待执行的任务时间线 |
| **进度条** | 当前运行的每个任务完成百分比 |
| **手动调度** | 拖拽调整待执行任务顺序 |
| **暂停/恢复/取消** | 对正在执行或排队中的任务操作 |
| **插入新任务** | 直接在当前队列中插入 priority 任务 |
| **告警中心** | 封号、登录失败、任务失败的高亮提示 |
| **历史追踪** | 已完成任务的执行结果（成功/失败/耗时）|

### 6.4 任务卡片的优先级标识

每个任务在时间线上显示时，带优先级标签：

```
[P0🔴 优先] 定向评论 视频V          13:00  账号: douyin_136 | 子任务 2/5
[P1🟢 日常] 养号 douyin_01-05     08:00  蓝图: douyin_daily | 第3/10轮
[P2⚪ 闲时] 采集个人信息           03:00  蓝图: douyin_read_profile | 全部账号
```

在指挥台上方提供筛选开关: [☑ 优先任务] [☑ 日常任务] [☐ 闲时任务]，默认显示 P0+P1。

### 6.5 账号冲突检测机制

当 guardd 收到新任务时:

```
接收 priority 任务: 账号A 评论视频V
  ├─ BrowserSlotManager.find_account("账号A")
  │   ├─ 返回 None → 空闲 → 正常分配槽位
  │   └─ 返回 slot_info → 账号A正在运行 → 等待完成
  ├─ 检查账号状态: active→执行 / banned→告警跳过 / login_expired→插入登录恢复
  └─ 检查浏览器进程: pid存活→复用 / 不存在→启动新浏览器
```

冲突检测确保: 同账号不分配到两个浏览器实例 → 避免指纹冲突和封号风险


---

## 七、恢复 guardd 的增强方案

### 7.1 guardd 新增能力

```python
# guardd.py 原有 + 新增模块

class GuarddServer:
    """guardd 主进程 — 每个机器一个实例"""
    
    def __init__(self):
        # 原有
        self.http_server = HTTPServer(('0.0.0.0', 9090), GuarddHTTPHandler)
        self.hostname = resolve_hostname()
        
        # 新增
        self.task_store = TaskStore()              # SQLite 持久化
        self.slot_manager = BrowserSlotManager(max_slots=3)
        self.priority_queue = PriorityQueue()
        self.active_task: Optional[Task] = None
        self.heartbeat_interval = 15               # 15秒心跳
        
    def run_cycle(self):
        """主循环 — 每 15 秒执行一次"""
        while True:
            # 1. 检查当前任务状态
            self._check_active_task()
            
            # 2. 队列调度：从队列取出下一个可执行任务
            self._schedule_next()
            
            # 3. 上报心跳到 Dashboard
            self._send_heartbeat()
            
            # 4. 清理过期数据
            self._cleanup()
            
            time.sleep(self.heartbeat_interval)
```

### 7.2 与 Dashboard 的通信

```
guardd → Dashboard (POST /api/push/heartbeat):
  每15秒上报一次:
  {
    "hostname": "chengzigedeAir",
    "status": "online",
    "slots": {"max": 3, "used": 2, "list": ["douyin_01", "douyin_02"]},
    "active_task": {"id": "nurture_001", "type": "scheduled", "blueprint": "douyin_daily", 
                    "progress": "60%", "elapsed_sec": 7200},
    "queued": [{"id": "nurture_002", "type": "scheduled", "estimated_start": "11:00"},
               {"id": "interact_001", "type": "priority", "estimated_start": "13:00"}],
    "alerts": [{"account": "douyin_136", "type": "login_expired", "time": "09:30"}],
    "system": {"cpu": 23, "mem": 62}
  }


Dashboard → guardd (POST /task):
  下发新任务:
  {
    "task_id": "interact_20260627_001",
    "type": "priority",
    "accounts": ["douyin_136"],
    "params": {"url": "https://www.douyin.com/video/xxx", "text": "@corpus"},
    "blueprint": "interact_comment",
    "schedule": {"type": "interval", "interval_sec": 600, "interval_random": {"min": 300, "max": 900}}
  }
```

### 7.3 CommandBus 瘦身后的职责

```python
# 瘦身后的 CommandBus — 只做三件事:
class CommandBus:
    def dispatch(self, cmd_type, accounts, params):
        """1. 按机器分组 + 模板渲染 + 投递"""
        machine_groups = self._group_by_machine(accounts)
        for machine, accts in machine_groups:
            task = self._render_task(cmd_type, accts, params)
            self._send_to_guardd(machine, task)
    
    def _send_to_guardd(self, machine, task):
        """2. 投递到目标机器的 guardd"""
        if machine == HOSTNAME:
            # 本机：直接调 guardd 内部 API
            local_guardd.submit_task(task)
        else:
            # 远程：HTTP 调 guardd
            guardd_api(f"http://{ip}:9090/task", "POST", task)
    
    def get_global_queue(self):
        """3. 聚合各机队列信息（通过心跳/API）"""
        for machine in ALL_MACHINES:
            status = self._query_guardd(machine)
            # 聚合为全局视图
```

---

## 八、执行流程完整示例

### 8.1 日常养号的一天

```
08:00  ── guardd 读取 ORACLE.yaml 的 schedules 节
     │   发现 08:00 douyin_daily → 生成 Task
     │   TaskScheduler 检查槽位: 3个空 → 开始执行
     │   在 3 个浏览器上同时跑 3 个账号的养号
     │   每跑完一个账号 → 释放槽位 → 启动下一个账号
     ├── 第1轮 douyin_01,02,03 并行
     ├── 第2轮 douyin_04,05,06 并行
     └── ...
11:00  ── 所有 douyin 账号跑完 → 释放槽位 → 等待下个定时任务
     │   心跳上报: 队列为空, 3个槽位空闲
     │   
13:00  ── 用户在 Dashboard 提交定向评论
     │   20个账号, 间隔5-15分钟, 视频V
     │   CommandBus 按机器分组后投递给各机 guardd
     │   guardd 拆解为子任务, 排入优先级队列
     ├── chengzigedeAir: 5个子任务, P0 插入队列头
     ├── 5kechengdeAir:  8个子任务, P0 插入队列头
     └── 7kecheng:       7个子任务, P0 插入队列头
     │   
13:05  ── chengzigedeAir: 当前养号第3轮结束
     │   检测到 P0 任务 → 暂停后续养号 → 开始执行评论
     │   账号A → 浏览器槽位1 → post_comment → 完成
     │   等待8分钟 → 账号B → 浏览器槽位1 → post_comment → 完成
     │   ...全部5个完成 → 恢复养号队列
```

### 8.2 三级接力的编排

```
用户提交: 三级接力, 账号A→B→C, 视频V

CommandBus.dispatch("interact", [A,B,C], {url:V, strategy:"chain"})
  │
  ├─ 按机器分组: A在机器1, B在机器2, C在机器3
  ├─ 生成3条 Task:
  │   Task-A: machine=1, chain_position="first",  schedule_type="now"
  │   Task-B: machine=2, chain_position="reply",   depends_on=["Task-A"]
  │   Task-C: machine=3, chain_position="second",  depends_on=["Task-B"]
  └─ 发送到各机 guardd
      │
      ├─ 机器1 guardd: Task-A → 立即执行 → post_comment → 完成
      │   → 把 result.comment_id 写入 task_store
      │   → Dashboard 心跳收到: Task-A COMPLETED
      │
      ├─ 机器2 guardd: Task-B 状态 WAITING_DEP
      │   → 每15秒检查 Task-A 状态
      │   → 发现 Task-A completed → 等待300秒 → 执行
      │   → 读取 Task-A.result.comment_id
      │   → reply_to_comment(comment_id) → 完成
      │   → Task-B COMPLETED
      │
      └─ 机器3 guardd: Task-C 状态 WAITING_DEP
          → 每15秒检查 Task-B 状态
          → 发现 Task-B completed → 等待300秒 → 执行
          → 读取 Task-B.result.comment_id
          → reply_to_comment(comment_id) → 完成
          → Task-C COMPLETED

Dashboard 实时显示三级进度:
  [✅] 13:00 账号A 评论成功
  [⏳] 13:05 账号B 回复A...
  [📅] 13:10 账号C 回复B (等待中)
```

---

## 九、与现有代码的合并策略

### 9.1 代码放在哪里

```
05_tools/00_setup/guardd/
├── guardd.py                  ← 主文件，约1400行 → 预计增加到2000行
├── modules/
│   ├── __init__.py
│   ├── heartbeat.py           ← [new] 心跳上报逻辑(从主文件抽出)
│   ├── task_store.py          ← [new] SQLite任务持久化
│   ├── priority_queue.py      ← [new] 优先级队列
│   ├── slot_manager.py        ← [new] 浏览器槽位管理
│   ├── scheduler.py           ← [new] 调度引擎
│   └── executor.py            ← [new] 任务执行器(调mc)
├── launch.sh
├── install_guardd.sh
└── com.agentos.guardd.plist
```

`guardd.py` 主文件保持不变，新增功能以模块方式导入。

### 9.2 不需要动的文件

| 文件 | 原因 |
|:-----|:------|
| `douyin_ops.py` | 原子操作层，只管"怎么点" |
| `xhs_ops.py` | 同上 |
| `engine.py` | 单次执行引擎，被 guardd Executor 调用 |
| `nurture_runner.sh` | 包装器，被 guardd Executor 调用 |
| `blueprints/*.json` | 蓝图定义不变 |
| `corpus.py` | 语料库不变 |
| `login_state_machine.py` | 登录检测逻辑不变 |
| `command_bus.py` | 瘦身（去掉poll/queue），保留模板渲染+分发 |

### 9.3 需要改的文件

| 文件 | 改动 |
|:-----|:------|
| `guardd.py` | + 5个模块导入，+ 调度循环，+ 槽位管理 |
| `command_bus.py` | 去掉 poll 守卫线程、CMD_POLL_STRATEGY，dispatch 改为投递到 guardd |
| `routes/ops.py` | + 任务管理路由 |
| `frontend/src/views/matrix-command.js` | 重建为联邦指挥台 |
| `frontend/src/views/matrix-interact.js` | 提交交互任务（已有框架需完善）|

---

## 十、实施路线图

### Phase 1 — guardd 调度引擎（本周）

| # | 任务 | 工作量 |
|:-:|:-----|:-------|
| 1.1 | TaskStore (SQLite) 持久化 | 小 |
| 1.2 | 优先级队列 | 小 |
| 1.3 | 浏览器槽位管理 | 小 |
| 1.4 | 调度主循环集成到 guardd | 中 |
| 1.5 | guardd HTTP API 扩展 (/tasks, /task/cancel) | 中 |
| 1.6 | 心跳增强（携带详细任务状态） | 中 |

### Phase 2 — 联邦指挥台（下周）

| # | 任务 | 工作量 |
|:-:|:-----|:-------|
| 2.1 | Dashboard 任务状态聚合（从各机心跳读取） | 中 |
| 2.2 | 联邦指挥台前端骨架（三机总览+时间线） | 大 |
| 2.3 | 任务手动调度（暂停/恢复/取消/重排） | 中 |
| 2.4 | 告警中心（封号/登录失败高亮） | 中 |
| 2.5 | CommandBus 瘦身（去掉poll/queue逻辑） | 小 |

### Phase 3 — 高级编排（下月）

| # | 任务 | 工作量 |
|:-:|:-----|:-------|
| 3.1 | 任务拆解（一台机器收到群组任务后拆成子任务） | 中 |
| 3.2 | 依赖链支持（waitting_dep 状态+跨机查询） | 中 |
| 3.3 | 三级接力全流程 | 大 |
| 3.4 | 任务失败自动重试+链式跳过 | 中 |
| 3.5 | ORACLE.yaml 定时任务自动导入 | 小 |

---



---

## 十二、架构审计与改进建议（2026-06-27 评审结果）


### 12.1 需要你决策的议题

#### 决策A：任务拆解位置

**问题**: 用户提交"20个账号评论视频V"，拆成20条子任务的工作放在哪层？

| 方案 | 拆解位置 | 优点 | 缺点 |
|:-----|:---------|:-----|:------|
| **A（推荐）** | CommandBus | master有全局子任务视图，指挥台可直接展示各机完整时间线 | CommandBus 从薄变厚 |
| B | guardd | guardd 逻辑内聚，CommandBus 保持薄 | master看不到子任务粒度 |

**我的建议**：选 **方案A**。原因是指挥台必须看到每条子任务的进度，不可能让20个账号的评论显示为"1条任务 20/20进度"。让 CommandBus 负责"模板渲染+按机器分组+拆解"三位一体。

#### 决策B：Dashboard 读路径是否直连 guardd

**问题**: 指挥台查询各机队列状态，走 CommandBus 还是直连各机 guardd？

| 方案 | 读路径 | 写路径 | 优点 |
|:-----|:-------|:-------|:-----|
| **C（推荐）** | Dashboard→guardd(直连HTTP) | Dashboard→CommandBus→guardd | 读不依赖CommandBus，CommandBus宕机不影响查看 |
| D | 全走 CommandBus | 全走 CommandBus | 统一入口，但CommandBus变成瓶颈 |

**我的建议**：选 **方案C（读写分离）**。理由:
- 读操作是查询类（GET /tasks, GET /heartbeat），直接调各机 guardd 简单高效
- 写操作是命令类（POST /task, POST /cancel），需要 CommandBus 做机器分组和模板渲染
- CommandBus 可以独立重启，不影响 Dashboard 查看队列


### 12.2 我直接确认的决策

以下是我的判断，不需要你决策：

| 决策 | 结论 | 理由 |
|:-----|:------|:------|
| guardd 拆分方式 | 拆成 modules/ 多文件 | 主文件1400行已到极限，新增调度逻辑后预计超2500行，必须拆分 |
| 跨机依赖通信 | 事件推送而非轮询 | O(n²) 轮询在>10个任务时代价不可接受 |
| guardd 单点故障 | 三层防护: launchd+恢复+超时兜底 | guardd 崩溃不丢失任务，1秒内重生 |
| 任务存储 | 内存 dict + SQLite 双写 | 内存保性能，SQLite 保持久化 |
| 浏览器孤儿清理 | guardd 启动时全量扫描 | 实现简单，成本低 |
| ORACLE 同步 | guardd 启动+每6小时 | 不是实时系统，6小时间隔足够 |
| 心跳间隔 | 15秒 | 与调度轮询周期一致，不要额外线程 |


### 12.3 guardd 拆分方案（详细讨论）

#### 当前问题

`guardd.py` 目前 1386 行，HTTP 处理器、9个模块循环、心跳上报、文件同步全部在一个文件里。加上调度引擎后预计突破 2500 行，必须拆分。

#### 拆分方案

```
05_tools/00_setup/guardd/
├── guardd.py                     ← 主入口(~200行)，只做:
│                                     1. import 所有模块
│                                     2. 启动 HTTP Server
│                                     3. 启动主循环 run_cycle()
│
├── modules/
│   ├── __init__.py
│   ├── http_handler.py           ← [抽出] HTTP请求处理(约300行)
│   │   ├── GuarddHTTPHandler
│   │   ├── GET /health, /tasks, /task/{id}
│   │   └── POST /task, /task/{id}/cancel
│   │
│   ├── heartbeat.py              ← [抽出] 心跳上报(约200行)
│   │   ├── collect_system_stats()
│   │   ├── collect_task_stats()
│   │   └── send_heartbeat()
│   │
│   ├── task_store.py             ← [新增] 任务持久化(约200行)
│   │   ├── SQLite 存储
│   │   ├── 内存缓存(dict) + 定时写回
│   │   └── 启动时恢复未完成任务
│   │
│   ├── priority_queue.py         ← [新增] 优先级队列(约150行)
│   │   ├── heapq 实现
│   │   ├── push / pop_ready / peek
│   │   └── cancel / reorder
│   │
│   ├── slot_manager.py           ← [新增] 浏览器槽位(约150行)
│   │   ├── acquire / release / find_account
│   │   ├── 启动时扫描孤儿浏览器
│   │   └── 槽位状态上报
│   │
│   ├── scheduler.py              ← [新增] 调度引擎(约300行)
│   │   ├── run_cycle() 主循环
│   │   ├── _check_active_task()
│   │   ├── _schedule_next()
│   │   ├── _decompose_task()
│   │   └── _notify_dependents()
│   │
│   ├── executor.py               ← [新增] 任务执行器(约200行)
│   │   ├── 调 mc run / mc interact
│   │   ├── 捕获输出 + 解析结果
│   │   └── 超时控制
│   │
│   └── oracle_sync.py            ← [新增] ORACLE同步(约100行)
│       ├── 启动时导入 schedules
│       └── 每6小时增量同步
│
├── launch.sh                     ← 不变
├── install_guardd.sh              ← 不变
└── com.agentos.guardd.plist       ← 不变
```

#### 拆分后主文件 (guardd.py)

```python
#!/usr/bin/env python3
from modules.http_handler import GuarddHTTPHandler, start_http_server
from modules.heartbeat import HeartbeatReporter
from modules.task_store import TaskStore
from modules.priority_queue import PriorityQueue
from modules.slot_manager import BrowserSlotManager
from modules.scheduler import Scheduler
from modules.executor import Executor
from modules.oracle_sync import OracleSync

class GuarddServer:
    def __init__(self):
        self.task_store = TaskStore()
        self.slot_manager = BrowserSlotManager(max_slots=3)
        self.priority_queue = PriorityQueue()
        self.executor = Executor(self.task_store, self.slot_manager)
        self.oracle_sync = OracleSync(self.task_store)
        self.scheduler = Scheduler(
            self.task_store, self.priority_queue,
            self.slot_manager, self.executor
        )
        self.heartbeat = HeartbeatReporter(self.task_store, self.slot_manager, self.scheduler)

    def run(self):
        start_http_server(self)
        self.oracle_sync.sync()
        self.slot_manager.cleanup_orphans()
        self.scheduler.run_cycle()
```

主文件 ~150 行，只做组装。每个模块职责单一。


### 12.4 CommandBus 读写分离方案（详细讨论）

#### 当前问题

CommandBus 目前既负责写（分发任务）也负责读（poll 状态、聚合队列）。导致:
- 页面刷新要等 CommandBus 响应
- CommandBus 挂了 Dashboard 什么都看不到
- 代码耦合

#### 读写分离方案

```
写路径（提交任务）:
  前端 → POST /api/ops/run → CommandBus.dispatch()
    ├─ 按机器分组 + 模板渲染 + 任务拆解
    └─ 投递到各机 guardd

读路径（查看状态）:
  前端 → GET /api/ops/queue?machine=all
    └→ 直接调各机 guardd HTTP API:
        ├─ chengzigedeAir:  GET http://127.0.0.1:9090/tasks
        ├─ 5kechengdeAir:   GET http://100.72.182.121:9090/tasks
        └─ 7kecheng:        GET http://100.65.35.28:9090/tasks
        └→ 聚合为全局视图

取消/暂停:
  前端 → POST /api/ops/cancel
    └→ 直接调对应机器 guardd: POST guardd_ip:9090/task/{id}/cancel
```

#### 方案优势

| 对比项 | 现在（全走CommandBus） | 读写分离后 |
|:-------|:----------------------|:-----------|
| CommandBus 宕机影响 | 提交任务❌ + 看队列❌ | 只能提交任务❌，看队列✅ |
| 前端刷新速度 | 要等 CommandBus 聚合 | 直接查各机 guardd，快 |
| 代码复杂度 | dispatch + poll + queue 混在一起 | dispatch 只写，UI 只读 |

#### 任务拆解在 CommandBus 中的实现

```python
class CommandBus:
    def dispatch(self, cmd_type, accounts, params):
        machine_groups = self._group_by_machine(accounts)
        tasks = []
        for machine, accts in machine_groups.items():
            if cmd_type == "interact" and len(accts) > 1:
                # 交互任务：每个账号拆一条独立 Task
                for acct in accts:
                    task = self._render_single_task(cmd_type, [acct], params, machine)
                    task.decomposed_from = f"group_{int(time.time())}"
                    tasks.append(task)
            else:
                # 普通任务：合并成一条 Task
                task = self._render_task(cmd_type, accts, params, machine)
                tasks.append(task)
        for task in tasks:
            self._send_to_guardd(task.machine, task)
        return {"plan_id": "xxx", "count": len(tasks)}
```


### 12.5 其他重要审计建议

#### 1. guardd HTTP 安全 — ✅ 已决策

HTTPServer 绑定到 127.0.0.1:9090，加简单 API token 认证。
各机 guardd 之间通信时携带 token，Dashboard 查询各机时也携带 token。
token 存放在各机 agent-local/identity/secrets/guardd_token，安装时自动生成。

#### 2. 跨机依赖事件推送 — ✅ 已决策

不用轮询。每台机器的 guardd 维护一个"我依赖谁"的反向索引。
Task-A 完成后，机器1 guardd 查索引发现机器2的 Task-B 依赖它，直接 HTTP POST 通知机器2。
机器2 guardd 收到通知后将 Task-B 从 WAITING_DEP 移入 QUEUED。
超时兜底：通知丢失时，15分钟没收到则主动查一次上游。

```python
def _notify_dependents(self, completed_task):
    for dep_task_id in self.task_store.find_dependents(completed_task.task_id):
        dep = self.task_store.get(dep_task_id)
        if dep and dep.machine != self.hostname:
            guardd_api(f"http://{dep.machine_ip}:9090/task/{dep_task_id}/dep_ready", "POST")
```

#### 3. 任务超时熔断

每个 Task 增加 max_execution_sec 硬限制，超时自动标记 FAILED：

```python
def _check_active_task(self):
    if self.active_task and self.active_task.status == "running":
        elapsed = time.time() - self.active_task.started_at
        max_time = self.active_task.params.get("max_execution_sec", 3600)
        if elapsed > max_time:
            self.active_task.status = "failed"
            self.active_task.error = f"超时 ({elapsed:.0f}s)"
```

#### 4. 安全：防止重复提交

同一 task_id 重复提交时，guardd 应返回"已存在"而非重新执行。

#### 5. guardd 单点故障防护 — ✅ 已决策

guardd 崩溃不会丢失任务，通过三层防护：

**第一层：launchd 自动重启（已有）**
`com.agentos.guardd.plist` 已配置 KeepAlive=true + RunAtLoad=true。
guardd 进程崩溃后 launchd 在 1 秒内自动拉起新进程。

**第二层：启动时恢复未完成任务（新增）**
guardd 启动时执行以下恢复流程：

```
guardd.startup_recovery()
  ├─ 1. 扫描孤儿浏览器进程
  │     ps aux | grep camoufox → 遍历 browser_pids/ 目录
  │     有进程但无对应槽位记录 → 标记为孤儿
  │     有关联槽位但进程不存在 → 清理槽位记录
  │
  ├─ 2. 从 task_store 加载未完成任务
  │     SELECT * FROM tasks WHERE status IN ('running', 'queued', 'waiting_dep')
  │     加载到内存队列，重置状态为 queued（重启后需要重新检查前置条件）
  │
  ├─ 3. 恢复依赖索引
  │     重建 WAITING_DEP 任务的依赖图
  │     检查依赖项是否已完成 → 已完成则入 queued 队列
  │     未完成则保留 WAITING_DEP 状态
  │
  └─ 4. 上报恢复结果到 Dashboard
      通过心跳上报恢复的任务数量
```

**第三层：超时兜底（新增）**
如果在心跳周期内（15秒）没有收到某台机器的心跳，Dashboard 标记该机器为 offline。
之前下发给该机器的任务状态变为 unknown，等机器恢复后重新同步。


### 12.6 调整后的实施路线图

| Phase | 任务 | 工作量 |
|:------|:-----|:-------|
| **1a** | guardd modules/ 目录拆分 | 小 |
| **1b** | TaskStore 内存+SQLite + PriorityQueue | 中 |
| **1c** | 启动时孤儿浏览器清理 | 小 |
| **1d** | BrowserSlotManager + 心跳增强 | 中 |
| **1e** | 调度主循环 + Executor | 中 |
| **2a** | CommandBus 读写分离 + 任务拆解 | 中 |
| **2b** | 指挥台前端（读视图）| 大 |
| **2c** | 跨机依赖事件推送 | 中 |
| **3a** | 指挥台操作功能（取消/暂停/重排）| 大 |
| **3b** | ORACLE 定时任务同步 | 小 |
| **3c** | 三级接力全流程 | 大 |
| **3d** | 告警中心 | 中 |
| **3e** | 任务超时熔断 + 自动恢复 | 中 |


### 决策1: 调度放 guardd，不新增层级
- guardd 已经是每台机器上的常驻进程
- 合并比新建更轻量，减少进程数

### 决策2: 按意图分类，不按动作分类
- `scheduled` = 定时养号（蓝图驱动，随机动作）
- `priority` = 特殊交互（用户指定目标，可设置间隔）
- 同一个原子操作可以在两类任务中出现

### 决策3: 浏览器槽位上移
- 从 `mc/engine.py` 移到 `guardd/slot_manager.py`
- 让调度层能感知和控制浏览器资源

### 决策4: 非抢占式插入
- 等待当前养号轮次完成后再插入 P0 任务
- 不强制中断 Camoufox 浏览器

### 决策5: CommandBus 瘦身
- 去掉 poll 守卫线程
- 去掉 CMD_POLL_STRATEGY
- 只保留：按机器分组 + 模板渲染 + 投递到 guardd

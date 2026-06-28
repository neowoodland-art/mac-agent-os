# AgentOS 命令传导架构

> 版本: 1.0 | 最后更新: 2026-06-28
> 本文档描述从 L5 前端到 L0 浏览器的命令传导全链路设计与实际实现

---

## 一、五层传导架构

```
L5: 前端视图 (views/*.js)
  │ POST /api/ops/run {type, accounts, params}
  │
L4: API 路由层 (routes/ops.py)
  │ → api_ops_run() → CommandBus.dispatch()
  │
L3: 命令分发层 (CommandBus)
  │ dispatch():
  │   1. ORACLE 合规检查 (account→machine映射)
  │   2. CMD_REGISTRY 查模板 / 硬编码
  │   3. 按机器分组 + 模板渲染
  │   4. ThreadPoolExecutor 并行分发
  │
  ├──→ ▸ 新路径(优先): /scheduler/submit
  │     发送 {command_line, cmd_type, accounts, priority, interval, params}
  │        → guardd Scheduler → PriorityQueue → SlotManager
  │        → Executor._build_cmd() 仅加执行环境前缀
  │
  ├──→ ▸ 旧路径(降级): /task (v7)
  │     发送 {cmd: "cd scripts && python -m ..."}
  │        → guardd _start_task() → subprocess.Popen
  │
  └──→ ▸ 兜底路径: subprocess(本地) / SSH nohup(远程)
           nurture: nurture_runner.sh / 其他: 直接 Python

L2: 调度执行器 (Scheduler + Executor)
  │ Scheduler.run_cycle() 每15秒:
  │   → _check_all_active_tasks()   检查3个 slot
  │   → _schedule_all_slots()       分配新任务
  │   → Executor.execute(task)
  │     → _build_cmd(task):
  │         ▸ 优先用 command_line (L3已渲染好) → 仅加 cd+python 前缀
  │         ▸ 兜底: 自行硬编码构建 (向后兼容)
  │     → 子进程执行 → 日志解析 → 进度更新

L1: 平台原子操作 (douyin_ops.py / xhs_ops.py)
  │ → Camoufox 浏览器执行

L0: Camoufox 0.4.11 + Playwright 1.58.0
```

---

## 二、核心设计原则

### 2.1 三层降级设计

不是两条平行的命令生成路径，而是**三层降级保护**：

| 层级 | 路径 | 命令由谁构建 | 执行管理 | 可用条件 |
|:-----|:-----|:------------|:---------|:---------|
| **新路径** ⭐ | `/scheduler/submit` | L3渲染cmd_line, L2只加前缀 | guardd调度器(15s+3slot) | guardd v2.3.0+ |
| **旧路径** | `/task` | L3渲染完整shell命令 | guardd直接subprocess | guardd可用 |
| **兜底** | subprocess/SSH | L3渲染+执行环境 | 直接执行 | 任何时候 |

**正常流中只有单一路径**（新路径），每次降级都是因为上层不可用。

### 2.2 命令生成责任分离

| 层 | 职责 | 产出 |
|:---|:-----|:-----|
| **L3 CommandBus** | 操作意图→CLI命令字符串 | `mc run --accounts=A --blueprints=B --rounds=3` |
| **L2 Executor** | 加执行环境前缀 | `cd scripts && PYTHONPATH=... python3 -m mc run ...` |
| **L2 Executor.兜底** | command_line为空时重新构建 | 同上格式的完整命令 |

### 2.3 任务拆解

interact 类型的多账号任务在 L3 被拆解为 per-account 子任务（command_bus.py:1062-1087行），直接投递到 guardd `/scheduler/submit`。每条子任务有独立 task_id 和状态追踪。

---

## 三、CMD_REGISTRY 注册表

### 3.1 注册表结构

```python
CMD_REGISTRY = {
    "nurture": {
        # 无 template — dispatch() 硬编码（因--mix,--interval特殊参数）
        "defaults": {"blueprint": "douyin_daily", "rounds": 10},
        "auto_blueprint": False,
    },
    "collect": {
        "template": "mc run --accounts={ids} --blueprints={blueprint} --rounds={rounds}",
        "defaults": {"rounds": 1},
        "auto_blueprint": True,
        "blueprint_map": {"douyin": "douyin_read_profile", "xiaohongshu": "xiaohongshu_read_profile"},
    },
    "login": {
        "template": "mc smart-login {ids}",
        "single_account": True,
    },
    "logout": {
        "template": "mc run --accounts={ids} --blueprints=douyin_daily --rounds=1",
    },
    "comment": {
        "template": "mc task comment --account={ids} --url={url} --direction={direction}",
        "required_params": ["url"],
    },
    "like": {
        "template": "mc run --accounts={ids} --blueprints=douyin_daily --rounds=1",
    },
    "interact": {
        "template": "mc run --accounts={ids} --blueprints={blueprint} --rounds=1 "
                    "--url={url} --direction={direction} --corpus={corpus}",
        "defaults": {"blueprint": "interact_comment", "direction": "", "corpus": ""},
        "required_params": ["url"],
    },
}
```

### 3.2 nurture 的特殊处理

nurture 类型**不经过 CMD_REGISTRY 模板渲染**，dispatch() 对其做硬编码（command_bus.py:965-978行），原因是：
1. 需要按平台分组（douyin/xiaohongshu 走不同的默认蓝图）
2. 有固定参数 `--mix --interval=45-90`
3. 支持通过 params 传递自定义 `interval`、`stagger` 等参数

---

## 四、任务生命周期

```
pending → scheduled → queued → preflight → running → completed
                                            ↓          → failed
                                            ↓          → cancelled
                                            ↓          → skipped
                                            → paused (可恢复)
                                            → waiting_dep (依赖等待)
```

**终端状态**: completed / failed / cancelled / skipped
**活跃状态**: running / queued / preflight / paused / waiting_dep

---

## 五、调度引擎架构 (guardd)

### 5.1 组件关系

```
HTTP Server (:9090)
  ├── POST /scheduler/submit → api_scheduler_submit()
  ├── GET  /scheduler/tasks  → api_scheduler_status()
  ├── POST /task/{id}/stop   → _stop_task()
  ├── POST /task/pause       → scheduler.pause_task()
  ├── POST /task/resume      → scheduler.resume_task()
  ├── POST /queue/reorder    → scheduler.reorder_queue()
  ├── GET  /accounts/status  → AccountMonitor
  └── GET  /accounts/profiles → profiles.json

Scheduler (15秒循环)
  ├── PriorityQueue (heapq, P0/P1/P2)
  ├── BrowserSlotManager (3 slot)
  ├── Executor (子进程+日志解析)
  └── TaskStore (内存+SQLite双写)

HeartbeatReporter (每轮上报)
  ├── slot使用率
  ├── 账号登录状态
  ├── 任务统计
  └── 浏览器健康

ScheduleBridge (60秒检查)
  └── schedule.yaml → guardd scheduler
```

### 5.2 优先级策略

| 任务类型 | 优先级 | 说明 |
|:---------|:-------|:------|
| interact, comment | P0 | 用户主动交互，最高优先 |
| nurture, collect | P1 | 日常养号/采集 |
| scheduled tasks | P1 | 定时任务 |
| logout, login | P2 | 低优先 |

---

## 六、已知维护注意事项

### 6.1 executor._build_cmd() 兜底代码

executor.py:148-189行的 `_build_cmd()` 有独立于 CMD_REGISTRY 的命令构建逻辑。此代码**正常流不会触发**（因 `command_line` 始终存在），仅作为向后兼容的安全网保留。修改 dispatch() 中的命令格式时，应同步检查此处的兜底是否一致。

### 6.2 comment 的潜在不一致

| 来源 | comment 命令格式 |
|:-----|:----------------|
| CMD_REGISTRY template | `mc task comment --account=... --url=...` |
| executor._build_cmd() 兜底 | `mc run --accounts=... --blueprints=... --rounds=1 --url=...` |

正常流走 CMD_REGISTRY，但如果兜底被触发（`command_line` 为空），会导致执行完全不同的命令。

### 6.3 routes/matrix.py 旧路由状态

| 路由 | 状态 | 说明 |
|:-----|:------|:------|
| `/nurture/start` | 已废弃·走CommandBus | 保留兼容，内部调 CommandBus |
| `/nurture/preview` | 只读·保留 | 排期预览，无执行操作 |
| `/task/run` | 已废弃·走CommandBus | 保留兼容，内部调 CommandBus |
| `/batch-run` | 已改造·走CommandBus | 2026-06-28 改造完成 |
| `/blueprints/{name}/execute` | 保留 | 蓝图单步执行 |
| `/accounts/{id}/login` | 保留 | 小红书走SMS/抖音走CommandBus |

### 6.4 命令轮询的迁移

旧版 CommandBus 有 `_start_poll_guard()` 轮询线程（每15秒检查各机状态）。v4.3.0 后此逻辑已迁移到 guardd 的 `Scheduler.run_cycle()`（15秒循环），CommandBus 中的 `_start_poll_guard()` 已空桩（command_bus.py:1264-1266行）。

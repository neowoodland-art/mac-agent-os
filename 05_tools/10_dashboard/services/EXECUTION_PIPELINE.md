# 统一执行管道 v5 — 设计文档

> 目标：所有操作（nurture/collect/login/logout/comment/like）共享同一个执行管道，
> 从预检 → 确认 → 发送 → 启动验证 → 轮询 → 完成，每步都有状态反馈。

---

## 一、问题现状

之前每次都在各个视图里独立写 fetch → 显示结果，没有统一的执行体验：

| 视图 | 预检 | 确认 | 发送 | 启动验证 | 轮询 | 完成 |
|:-----|:----:|:----:|:----:|:--------:|:----:|:----:|
| 养号执行 | ❌ | ✅(confirm) | ❌旧端点 | ❌ | ❌旧API | ❌ |
| 信息采集 | ❌ | ❌ | ❌旧端点 | ❌ | ❌ | ❌ |
| 定向评论 | ❌ | ❌ | ❌旧端点 | ❌ | ❌ | ❌ |
| 收藏点赞 | ❌ | ❌ | ❌旧端点 | ❌ | ❌ | ❌ |
| 联邦指挥台 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

每个视图都自己写了一套 fetch → log 的逻辑，代码重复，体验不一致。

---

## 二、统一执行管道设计

### 2.1 前端组件

```javascript
// 所有执行按钮统一使用这个组件
const pipeline = createExecutionPipeline(containerElement, {
  // ── 必需 ──
  type: 'nurture',           // 操作类型
  getAccounts: () => [...],  // 获取选中账号的回调
  
  // ── 可选 ──
  title: '养号执行',         // 对话框标题
  onPlan: (plan) => {},      // 确认前的计划预览（可自定义）
  commandTemplate: (accounts, params) => {...}, // 自定义命令
  
  // ── 回调 ──
  onStatusChange: (phase, data) => {}, // 阶段变化回调
});
```

### 2.2 执行管道阶段

```
阶段名         前端显示                                  后端动作
────────────────────────────────────────────────────────────────────
IDLE           就绪                                      —
PREFLIGHT      🔍 预检机器状态...                        调用 /api/ops/machines
PLAN           📋 显示执行计划 + 机器状态                 调用 /api/ops/run (dry_run)
CONFIRM        🖥️ 弹出确认对话框                         用户确认/取消
DISPATCHING    📡 正在发送命令到 XX 机器...               调用 /api/ops/run
DISPATCHED     ✅ 命令已发送 (PID:12345)                 记录PID
LAUNCH_WAIT    ⏳ 等待进程启动...                         等待2秒
LAUNCH_CHECK   🔍 检查进程是否启动...                     查进程表/SSH pgrep
RUNNING        🟢 进程运行中 (5/10轮)                    轮询 /api/ops/status
BROWSER_CHECK  🌐 浏览器已启动 (3进程)                   查浏览器进程
COMPLETED      ✅ 执行完成: 8成功/2失败/120s              读取最终结果
FAILED         ❌ 执行失败: 错误信息
```

### 2.3 后端 API

```
POST /api/ops/run
  → Phase 1-2: dispatch
  → Phase 3-5: 通过 /api/ops/status 和 /api/ops/machines 轮询

GET /api/ops/status?account=xxx
  → 返回命令的完整状态 + 阶段

GET /api/ops/machines
  → 返回所有机器的浏览器/命令/槽位状态
```

### 2.4 前端执行流程代码

```javascript
export async function executeCommand(options) {
  const { type, accounts, params, logEl, statusEl } = options;
  
  // Phase 0: Preflight
  setPhase('preflight', '🔍 预检机器状态...');
  const machines = await api('/api/ops/machines');
  
  // Phase 1: Plan + Confirm
  setPhase('plan', '📋 生成执行计划...');
  const plan = await api('/api/ops/run', {type, accounts, params: {...params, dry_run: true}});
  const confirmed = await showConfirmDialog(plan, machines);
  if (!confirmed) { setPhase('cancelled', '⏸ 已取消'); return; }
  
  // Phase 2: Dispatch
  setPhase('dispatching', '📡 发送命令...');
  const result = await api('/api/ops/run', {type, accounts, params});
  showDispatchResult(result);
  
  // Phase 3-5: Monitor
  await monitorExecution(result, (phase, msg) => {
    setPhase(phase, msg);
  });
}
```

---

## 三、确认对话框标准

所有执行操作共享同一个确认对话框格式：

```
┌─────────────────────────────────────┐
│ 📋 养号执行确认                       │
│                                      │
│ 🟢 chengzigedeAir (本机)             │
│   槽位: 2/3 可用                     │
│   浏览器: 1 个运行中                  │
│   ┌──────────────────────────────┐   │
│   │ 🖥️ douyin_test → 10轮        │   │
│   │   蓝图: douyin_daily          │   │
│   │   窗口: 槽位2 (100,0)         │   │
│   └──────────────────────────────┘   │
│                                      │
│ 🔴 5kechengdeAir (远程)              │
│   不可达（SSH 超时）                  │
│   ┌──────────────────────────────┐   │
│   │ ❌ xhs_01 → 无法执行          │   │
│   └──────────────────────────────┘   │
│                                      │
│              [取消]  [确认执行]        │
└─────────────────────────────────────┘
```

---

## 四、执行状态反馈标准

每台机器独立显示状态条：

```
📡 养号执行状态
────────────────────────────────────────────────
🖥️ chengzigedeAir     🟢 运行中 (5/10轮, 3成功/2失败)
☁️ 5kechengdeAir      🔴 SSH 不可达 (已跳过)
☁️ 7kecheng           ⏳ 浏览器启动中... (8s)
────────────────────────────────────────────────
```

---

## 五、集成到所有视图

| 视图 | 按钮 | 替换为统一管道 |
|:-----|:-----|:--------------|
| 养号执行 | 执行选中 / 全部启用 | executeCommand('nurture', ...) |
| 信息采集 | 采集选中 / 全部 | executeCommand('collect', ...) |
| 信息采集 | 登录选中 | executeCommand('login', ...) |
| 定向评论 | 执行评论 | executeCommand('comment', ...) |
| 收藏点赞 | 执行点赞 | executeCommand('like', ...) |
| 联邦指挥台 | 批量执行 | executeCommand(selectedType, ...) |

---

## 六、v6 队列与强制停止（2026-06-25 新增）

### 6.1 每台机器一个队列

```
CommandBus 收到新命令
  ↓
MachineSession.is_busy?
  ├── 否 → 立即执行（send_local / send_remote）
  └── 是 → status=queued，加入 queued_cmds 排队
              ↓
        当前命令完成 → poll() 检测到 terminal
              ↓
        _start_next() → 出队 → send() → 执行
```

### 6.2 强制停止

```
用户点击"停止"
  ↓
POST /api/ops/cancel/{run_id}
  ↓
session.cancel(cmd)
  ├── kill(cmd.pid)                    ← 杀 mc run 进程
  ├── pkill -f {account_id}            ← 清 Camoufox 浏览器
  └── _start_next()                    ← 启动队列下一条
```

### 6.3 已实现状态

| 组件 | 状态 |
|:-----|:----:|
| MachineSession.queue | ✅ v6 已实现 |
| cancel() 杀进程+清浏览器 | ✅ v6 已实现 |
| poll() 完成自动调度下一条 | ✅ v6 已实现 |
| get_queue_info() API | ✅ v6 已实现 |
| 前端显示队列/停止按钮 | ⬜ 待实现 |

## 七、实施步骤

| 步骤 | 内容 | 文件 |
|:-----|:-----|:------|
| 1 | 创建 `services/execution_pipeline.py` — 后端管道引擎 | 后端 |
| 2 | 创建 `frontend/src/components/execution-pipeline.js` — 前端管道组件 | 前端 |
| 3 | 更新 `routes/ops.py` — 对接管道引擎的 phased status | 后端 |
| 4 | 更新 inline `index.html` — 所有执行按钮用统一管道 | 前端 |
| 5 | 更新 migrated views — 所有执行按钮用统一管道 | 前端 |
| 6 | 集成测试 — 所有操作类型通过管道验证 | 测试 |

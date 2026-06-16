---
type: concept
domain: system
nature: plan
tags: [agentos, v3.0, implementation, plan, tasks]
status: active
created: 2026-06-16
updated: 2026-06-16
version: 1.0.0
supersedes: []
---

# AgentOS 联邦指挥台 — 实施计划 v1.0

> 基于 `federation-operations-architecture.md` 设计文档
> 参考: `federated-multi-machine-architecture.md` / `dashboard-v4-design.md` / `CORE-ARCHITECTURE.md`
> 总体估计: ≈ 20 小时

---

## 一、优先级总览

```
P0 ─── 感知层: 让指挥台"看到"所有机器状态
  ├─ 机器状态条(在线/离线/忙碌)
  ├─ 账号级忙碌状态
  └─ 操作前的资源检查

P1 ─── 路由层: 让指挥台"指挥"远程机器
  ├─ owner_machine 操作路由
  ├─ 远程执行通道完善
  └─ 按钮状态智能化(灰掉/提示/远程执行)

P2 ─── 引擎层: 操作生命周期管理
  ├─ 统一操作队列(状态机)
  ├─ 资源锁系统
  ├─ 状态归零(pre-flight reset)
  └─ 日志聚合

P3 ─── 生态层: 高级功能和系统完备
  ├─ 文件级 WPRA 写入规范
  ├─ guardd 模块补全
  ├─ 9 插件体系完善
  └─ 键盘锁定/离线队列/DAG
```

---

## 二、依赖关系拓扑

```
P0-1 机器状态条
  └── 依赖: guardd 心跳已实现 ✅
  └── 阻塞: P1-1 (操作路由需要知道机器是否在线)

P0-2 账号忙碌状态
  └── 依赖: 本地资源锁文件
  └── 阻塞: P2-2 (资源锁系统)

P1-1 操作路由 (owner_machine 判断)
  └── 依赖: P0-1 (机器在线状态)
  └── 阻塞: P1-2 (远程执行通道)

P1-2 远程执行通道
  └── 依赖: federation API 已部分实现 ✅
  └── 前置: 完善 /api/federation/exec 支持所有操作类型

P2-1 状态机队列
  └── 依赖: P1-1, P1-2
  └── 前置: cross_machine/tasks/ 目录

P2-2 资源锁系统
  └── 依赖: 本地文件锁 + guardd 锁管理
  └── 前置: guardd 锁模块

P3-1 WPRA 写入规范
  └── 依赖: cross_machine/data/ 目录结构已存在 ✅
  └── 前置: 插件改写为文件级写入
```

---

## 三、Phase 0: 立即修复 (之前审计发现的问题)

| # | 任务 | 文件 | 估计 | 优先级 |
|:-:|:-----|:-----|:----:|:------:|
| 0.1 | 账号管理跨机显示(已做) | index.html | ✅ 已完成 | P0 |
| 0.2 | 修复 matrix-mgmt 路由 | app.py | ✅ 已完成 | P0 |
| 0.3 | 修复 cross-machines API | app.py | ✅ 已完成 | P0 |
| 0.4 | 修复 loadSmsAccounts 数据格式 | index.html | ✅ 已完成 | P0 |
| 0.5 | SMS API 加 owner_machine | sms_proxy_api.py | ✅ 已完成 | P0 |
| 0.6 | 前端代理/调度/任务路径错配 | index.html | ≈ 20min | P0 |
| 0.7 | 语料库缺失API补充 | routes/matrix.py | ≈ 30min | P0 |

---

## 四、Phase 1: 感知层 — 让指挥台"看见" (≈ 3h)

### 1.1 机器状态条 (≈ 1h)

在每个视图顶部增加机器状态条:

```
┌─────────────────────────────────────────────────────┐
│  🟢 chengzigedeAir  🟢 5kechengdeAir  ⚪ 7kecheng  │
│  账号: 5在线/5总      账号: 0在线/5总    离线30分钟   │
└─────────────────────────────────────────────────────┘
```

**文件**: `index.html` + `core.js` (添加全局状态条组件)
**实现**:
- 每 30s 轮询 `/api/federation/health` 获取三台机器在线状态
- 状态条渲染为全局组件,所有视图共用
- 绿/黄/灰三色: 在线 / 忙碌(有任务运行) / 离线(>5min无心跳)

### 1.2 账号级忙碌状态 (≈ 1h)

```
douyin_01  🟢 在线 ✅ 可操作
douyin_02  🔴 忙碌 ⏳ 正在养号中 (剩余23分钟)
douyin_03  ⚪ 离线 ❌ 机器5kecheng当前离线
```

**文件**: `sms_proxy_api.py` (加忙碌字段) + `index.html` (展示)
**实现**:
- guardd 维护一个 `locks.json`,记录当前哪个账号正在被操作
- SMS API 响应中加 `busy: true/false`, `busy_since: timestamp`
- 忙碌的账号按钮灰掉,显示"正在操作中"

### 1.3 前端路径错配修复 (≈ 20min)

| 前端调用 | 改为 | 文件 |
|:---------|:-----|:-----|
| `/api/matrix/proxy/list` | `/api/matrix/proxies` | index.html |
| `/api/matrix/schedule/list` | `/api/matrix/schedules` | index.html |
| `/api/matrix/task/comment` | `/api/matrix/task/run` (POST+type=comment) | index.html |

---

## 五、Phase 2: 路由层 — 让指挥台"指挥" (≈ 5h)

### 2.1 操作路由 — 本地 vs 远程 (≈ 2h)

**核心逻辑** (所有操作按钮的通用函数):

```javascript
async function executeOperation(accountId, operationType, params) {
  // 1. 查账号所属机器
  const account = findAccount(accountId);
  const targetMachine = account.owner_machine;
  
  // 2. 查机器是否在线
  const machineStatus = await getMachineStatus(targetMachine);
  if (machineStatus === 'offline') {
    showError(`${targetMachine} 当前离线，无法操作`);
    return;
  }
  
  // 3. 如果是本机 → 本地API
  if (targetMachine === currentMachine) {
    return localExecute(operationType, params);
  }
  
  // 4. 如果是远程机器 → 联邦 exec
  return remoteExecute(targetMachine, operationType, params);
}
```

**文件**: 新建 `static/modules/operation-router.js`
**改动**:
- `accountLogin()` → 通过路由执行
- `clearCookies()` → 通过路由执行
- `deleteAccount()` → 通过路由执行
- `batchExecute()` → 支持跨机批量

### 2.2 远程执行通道完善 (≈ 2h)

**文件**: `services/remote_exec.py`
**新增能力**:
- 支持登录命令: `ssh {machine} "cd agent-sync && agentos matrix login {account}"`
- 支持养号命令: `ssh {machine} "cd agent-sync && agentos matrix run --blueprint {bp} --rounds {n}"`
- 支持采集命令: `ssh {machine} "cd agent-sync && agentos matrix collect {phone}"`
- 统一返回格式: `{status, output, error, duration_sec}`

### 2.3 新建前端模块目录 (≈ 30min)

```bash
static/modules/
├── core.js              # 框架核心 ✅ 现有
├── operation-router.js  # 操作路由 (新建)
├── machine-bar.js       # 机器状态条 (新建)
├── operation-queue.js   # 操作队列 (Phase 3)
├── resource-lock.js     # 资源锁 (Phase 3)
└── ...                  # 现有其他模块
```

**文件**: `index.html` — 加入新的 script 加载顺序

### 2.4 按钮状态智能化 (≈ 30min)

| 账号状态 | 登录按钮 | 养号按钮 | 采集按钮 |
|:---------|:--------|:---------|:---------|
| 本机·在线·空闲 | 🟢 可用 | 🟢 可用 | 🟢 可用 |
| 本机·在线·忙碌 | 🔴 灰掉"正在养号中" | 🔴 灰掉 | 🟢 可用 |
| 远程·在线·空闲 | 🟢 "远程执行" | 🟢 "远程执行" | 🟢 "远程执行" |
| 远程·离线 | ⚪ 灰掉"XX机离线" | ⚪ 灰掉 | ⚪ 灰掉 |

---

## 六、Phase 3: 引擎层 — 操作生命周期管理 (≈ 7h)

### 3.1 统一操作队列 + 状态机 (≈ 3h)

**文件**: 
- `guardd/modules/operation_queue.py` (新建)
- `static/modules/operation-queue.js` (新建)

**后端**:
```python
# guardd/modules/operation_queue.py
class OperationQueue:
    """操作队列 — 管理本机所有操作的生命周期"""
    
    def submit(self, op_type, params) -> str:
        """提交操作,返回 operation_id"""
        # 写 cross_machine/tasks/pending/{op_id}.json
        
    def check(self, op_id) -> dict:
        """查询操作状态"""
        
    def cancel(self, op_id) -> bool:
        """取消正在运行的操作"""
        
    def cleanup(self, op_id):
        """操作完成后清理"""
```

**前端**: 操作日志面板,按机器/时间/类型过滤

### 3.2 资源锁系统 (≈ 2h)

**文件**: 
- `guardd/modules/resource_lock.py` (新建)
- `static/modules/resource-lock.js` (新建)

**锁表**:
```python
locks = {
    "browser": {"held_by": "op_001", "acquired_at": "...", "ttl": 3600},
    "account:douyin_01": {"held_by": "op_001", ...},
    "identity:douyin_01_camo": {"held_by": "op_001", ...},
}
```

**规则**:
- 锁自动过期 (TTL)
- 锁可被强制释放 (管理员)
- 锁冲突时: 拒绝新操作,提示"资源被 XX 操作占用"

### 3.3 状态归零 Pre-flight Reset (≈ 1h)

**文件**: `guardd/modules/preflight.py` (新建)

每次操作前自动执行:

```bash
1. pkill -f camoufox          # 杀残留浏览器
2. pkill -f playwright        # 杀残留驱动
3. rm -rf /tmp/camoufox_*     # 清临时文件
4. check_locks()              # 检查并释放过期锁
5. check_disk_space()         # 检查磁盘空间
6. return "ready"             # 返回就绪状态
```

### 3.4 日志聚合 (≈ 1h)

**文件**: 
- `app.py` 新增 `/api/logs/push` 端点
- `guardd/modules/log_aggregator.py` (新建)

**日志格式**:
```json
{
  "op_id": "op_20260616_001",
  "machine": "5kechengdeAir",
  "type": "nurture_run",
  "status": "completed",
  "states": [...],
  "output": "...",
  "duration_sec": 360,
  "triggered_by": "dashboard"
}
```

---

## 七、Phase 4: 生态层 — 系统完备 (≈ 5h)

### 4.1 WPRA 写入规范落地 (≈ 2h)

参考 `dashboard-v4-design.md` 中的 cross_machine 数据规范:

```python
# 每个插件写数据时遵循
CROSS_MACHINE / "data" / {plugin} / {uid}.json
# 内容包含
{"plugin": "...", "version": "...", "machine_uid": "...", 
 "hostname": "...", "timestamp": "...", "data": {...}}
```

**文件**: 
- `plugins/base.py` — 更新 `write_shared_data()`
- `plugins/matrix.py` — 改写为文件级写入
- `plugins/guardd.py` — 改写为文件级写入

### 4.2 guardd 模块补全 (≈ 2h)

参考 `federated-multi-machine-architecture.md`:

| 模块 | 状态 | 任务 |
|:-----|:----:|:-----|
| `heartbeat` | ✅ 已实现 | — |
| `task_worker` | ⏳ 部分 | 扫描 cross_machine/tasks/ 执行 |
| `upgrade_checker` | ❌ 缺失 | 版本比对+自动拉取 |
| `memory_triage` | ❌ 缺失 | 记忆过滤→提交箱 |
| `knowledge_sync` | ❌ 缺失 | 知识库变更通知 |
| `encrypted_channel` | ❌ 缺失 | RSA 加密通信 |
| `cleanup` | ❌ 缺失 | 清理30天以上旧数据 |
| `operation_queue` | ❌ 缺失 | Phase 3 新建 |
| `resource_lock` | ❌ 缺失 | Phase 3 新建 |
| `preflight` | ❌ 缺失 | Phase 3 新建 |

### 4.3 9 插件体系完善 (≈ 1h)

检查现有插件 vs 设计:

| 插件 | dashboard-v4 设计 | 现状 |
|:-----|:-----------------|:-----|
| guardd | 🖥 联邦机器 | ✅ 已实现 |
| matrix | 📱 矩阵养号 | ✅ 已实现 |
| ave | 🎬 视频工厂 | ✅ 已实现 |
| collector | 📡 内容采集 | ⏳ crawl.py 新建 |
| skills | 🧩 技能树 | ❌ 缺失 |
| knowledge | 📚 知识库 | ✅ kb_api.py |
| automation | ⏰ 自动任务 | ⏳ scheduler.py 新建 |
| tools | 🔧 工具集 | ❌ 缺失 |
| system | ⚙️ 系统核心 | ⏳ system_plugins.py |

---

## 八、实施顺序总结

```
Week 1 (3天)    Phase 1: 感知层
                ├── 1.1 机器状态条     ≈ 1h
                ├── 1.2 账号忙碌状态   ≈ 1h  
                └── 1.3 前端路径修复   ≈ 20min

Week 2 (3天)    Phase 2: 路由层
                ├── 2.1 操作路由       ≈ 2h
                ├── 2.2 远程执行通道   ≈ 2h
                ├── 2.3 前端模块化     ≈ 30min
                └── 2.4 按钮状态智能化 ≈ 30min

Week 3 (3天)    Phase 3: 引擎层
                ├── 3.1 操作队列       ≈ 3h
                ├── 3.2 资源锁         ≈ 2h
                ├── 3.3 状态归零       ≈ 1h
                └── 3.4 日志聚合       ≈ 1h

Week 4 (2天)    Phase 4: 生态层
                ├── 4.1 WPRA 写入规范  ≈ 2h
                ├── 4.2 guardd 模块    ≈ 2h
                └── 4.3 9插件体系      ≈ 1h

Phase 0 (已做)  ✅ 6项审计修复完成
Phase 0 (待做)  ❌ 0.6 前端路径错配 ≈ 20min
                ❌ 0.7 语料库API    ≈ 30min
```

---

## 九、风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|:-----|:----:|:----:|:-----|
| SSH 远程执行权限不足 | 中 | 高 | 先实现本地操作,远程执行作为可选升级 |
| 资源锁导致操作阻塞 | 低 | 中 | 锁设 TTL,管理员可强制释放 |
| guardd 模块太多难维护 | 中 | 中 | 模块化设计,每个模块独立文件,可单独启用/禁用 |
| 前端模块化导致加载顺序问题 | 低 | 高 | 使用串行加载器,明确依赖顺序 |
| 文件级 WPRA 写入增加 Git 冲突 | 低 | 中 | 按 machine_uid 隔离文件,不会冲突 |

---

## 十、验收标准

### Phase 1 完成标志
- [ ] 每个视图顶部显示三台机器状态条
- [ ] 账号卡片显示忙碌状态
- [ ] 前端所有 fetch 路径正确,无 404

### Phase 2 完成标志
- [ ] 远程账号按钮自动路由到对应机器
- [ ] 离线机器操作按钮灰掉并提示
- [ ] 可通过 Dashboard 远程登录/养号/采集

### Phase 3 完成标志
- [ ] 每个操作有完整生命周期追踪
- [ ] 资源冲突时正确拒绝或排队
- [ ] 操作前自动清理残留进程
- [ ] 操作日志可查看、可过滤

### Phase 4 完成标志
- [ ] 所有插件按 WPRA 规范写入
- [ ] guardd 10 模块正常运行
- [ ] 9 插件体系完整

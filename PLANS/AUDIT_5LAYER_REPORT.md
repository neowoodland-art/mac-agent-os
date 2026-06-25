# Dashboard 五层架构合规审计报告 v1.0

> 日期: 2026-06-19
> 审计范围: 所有 33 个前端视图 + 4 个内联模块

---

## 一、五层架构标准

```
Layer 5: 前端视图 (Vite views/*.js)         → 调 API
Layer 4: API 路由 (routes/*.py)              → 调 CommandBus
Layer 3: 命令总线 (CommandBus)                → 调 MachineSession
Layer 2: 执行引擎 (mc run / mc task)         → 调 原子操作
Layer 1: 浏览器 (Camoufox)                   → 执行操作
```

**通过标准**: 前端 API 调用 → 后端路由 → CommandBus.dispatch() → 子进程执行

---

## 二、账户操作视图 (必须走 CommandBus)

### ✅ 已合规 (7个)

| 视图 | 操作 | API 调用 | 后端路径 | 
|:-----|:------|:---------|:---------|
| **养号执行** | 启动养号 | `POST /api/ops/run` | → CommandBus → `mc run` |
| **联邦指挥台** | 执行操作 | `POST /api/ops/run` | → CommandBus → `mc run` |
| **信息采集** | 批量采集 | `POST /api/ops/run {type:'collect'}` | → CommandBus `CMD_REGISTRY` → `mc run --blueprints=auto` |
| **信息采集** | 单账号采集 | `POST /api/ops/run {type:'collect'}` | → CommandBus `CMD_REGISTRY` → `mc run --blueprints=auto` |
| **定向评论** | 执行评论 | `POST /api/ops/run {type:'comment'}` | → CommandBus `CMD_REGISTRY` → `mc task comment` |
| **收藏点赞** | 执行点赞 | `POST /api/ops/run {type:'like'}` | → CommandBus `CMD_REGISTRY` → `mc run --blueprints=douyin_daily` |
| **登录** (账号管理/各视图🔑) | 打开浏览器 | `POST /api/ops/run {type:'login'}` | → CommandBus `CMD_REGISTRY` → `mc smart-login` |
| **CMD_REGISTRY 注册表** | 统一 cmd_type → 命令模板 | 在 command_bus.py 定义 | 新增操作只需加一行，不需改 dispatch |

### ℹ️ 系统运维操作 (不走 CommandBus 是合理的)

| 视图 | 操作 | API | 原因 |
|:-----|:------|:----|:------|
| **远程Shell** | 在远端执行命令 | `POST /api/federation/exec` | 系统管理工具, 非账号操作 |
| **对账检查** | ORACLE 宪法对账 | `POST /api/fleet/reconcile` | 系统健康检查 |
| **一键同步** | Git 同步所有机器 | `POST /api/fleet/sync` | 系统运维 |

### 📊 只读数据视图 (无操作, 无需 CommandBus)

| 视图 | API | 说明 |
|:-----|:----|:------|
| machines | `/api/machines` | 机器状态, 只读 |
| matrix-accounts | `/api/matrix/accounts` | 账号列表, 只读 |
| matrix-blueprints | `/api/matrix/blueprints`, `/api/matrix/atom-ops` | 蓝图列表+原子操作, 只读 |
| matrix-atom-ops | `/api/matrix/atom-ops` | 原子操作列表, 只读 |
| matrix-corpus | `/api/matrix/corpus` | 语料库, 只读 |
| matrix-summary | `/api/matrix/cross-machines`, `/api/matrix/system-info` | 多机总览, 只读 |
| matrix-sms-proxy | `/api/matrix/sms/*` | SMS 代理配置, 只读 |
| matrix-schedule | `/api/matrix/schedules` | 定时任务, 只读 |
| capabilities | `/api/capabilities` | 能力目录, 只读 |
| costs | `/api/summary`, `/api/costs/breakdown` | 费用统计, 只读 |
| productions | `/api/matrix/sms/accounts` | 生产列表, 只读 |
| assets | `/api/assets` | 资产库, 只读 |

### ❌ 14行占位符 (无功能)

| 视图 | 状态 |
|:-----|:------|
| ave-render, ave-script, ave-materials, ave-templates | 占位符 |
| crawl-history, crawl-sources | 占位符 |
| serve-dashboard, serve-mcp, serve-schedule | 占位符 |
| matrix-login | 跳转到采集 |
| matrix-publish | "开发中..." |
| workflow | 占位符 |

---

## 三、远程执行路径 (federation API)

`recording.js` 中 `_routeOperation()` 对远程机器分发走 federation API:

| 操作 | Federation 端点 | 现状 |
|:-----|:----------------|:------|
| login(远程) | `POST /api/federation/login` | ⚠️ 直接 SSH 执行 |
| logout(远程) | `POST /api/federation/logout` | ⚠️ 直接 SSH 执行 |
| comment(远程) | `POST /api/federation/comment` | ⚠️ 直接 SSH 执行 |
| nurture(远程) | `POST /api/federation/nurture` | ⚠️ 直接 SSH 执行 |
| collect(远程) | `POST /api/federation/collect` | ⚠️ 直接 SSH 执行 |

**这些 federation 端点应该也改为走 CommandBus**, 否则远程操作不经过命令总线的 preflight/冷却/并发控制。

---

## 四、ORACLE 合规检查规则

### 4.1 账号→机器映射表

`ORACLE.yaml` 是账号→机器的**宪法级**映射表。CommandBus 执行前自动校验：

```
请求: account=douyin_test, machine=5kechengdeAir
  → ORACLE 查 douyin_test → 应属于 chengzigedeAir
  → 发出警告: "douyin_test 按 ORACLE 应在 chengzigedeAir，实际发往 5kechengdeAir"
  → 仍然允许执行（可能是临时调配）
```

### 4.2 三种结果

| 检查结果 | 行为 | 前端显示 |
|:---------|:-----|:---------|
| 匹配 | 正常执行 | ✅ 绿色 |
| 不匹配 | 执行 + 警告 | ⚠️ 橙色警告 |
| 未登记 | 执行 + 警告 | ⚠️ 建议 git pull 后 fleet_reconcile |

### 4.3 规则存证

- `ORACLE.yaml` — 宪法文件，账号机器映射的 source of truth
- `command_bus.py` — 运行时校验，每次 dispatch 自动检查
- `fleet_reconcile` — 对账工具，检查实际状态是否符合 ORACLE

---

## 五、总结

| 类别 | 数量 | 状态 |
|:-----|:-----|:------|
| 账户操作视图 | **7** | ✅ **全部已合规**(走 CommandBus) |
| 系统运维视图 | **3** | ℹ️ 合理不走 CommandBus |
| 只读数据视图 | **12** | ℹ️ 无操作 |
| 占位符视图 | **11** | ❌ 无功能 |
| 远程分发端点 | **5** | ⚠️ 待改造 |

**当前优先级**: 远程端点(federation)改造 → 占位符填充 → 旧模块清理

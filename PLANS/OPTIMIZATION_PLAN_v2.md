# AgentOS 命令传导与采集系统——全面优化规划 v2.0

> 日期: 2026-06-25 | 版本: 4.2.1
> 基于: CONSTITUTION.md、FEDERATION_GUIDE.md、AUDIT_5LAYER_REPORT.md、COMMAND_UNIFICATION_PLAN.md
> 覆盖: 命令传导全链路 + 信息采集全链路 + 远程执行 + 数据持久化 + 封号检测

---

## 一、当前架构全景

```
L5 前端视图 (12个操作视图)
  │ 统一格式: {type, accounts, params}
  │ 统一入口: POST /api/ops/run
  ▼
L4 API 路由
  ├── routes/ops.py      ← ✅ 统一执行入口（已治理）
  └── routes/matrix.py   ← ✅ 只保留 GET 读操作（已治理）
  ▼
L3 CommandBus
  ├── CMD_REGISTRY        ← ✅ 注册表（已治理）
  ├── dispatch()           ← ✅ 注册表驱动（已治理）
  ├── MachineSession       ← ✅ 每机队列（已治理）
  ├── CMD_POLL_STRATEGY    ← ✅ 按类型策略（已治理）
  └── poll守卫线程         ← ✅ 15s自动检测（已治理）
  ▼
L2 mc 引擎
  ├── nurture_runner.sh    ← ⚠️ 远程参数默认值已修
  ├── BatchEngine          ← ✅ 支持封号标记
  └── LoginStateMachine    ← ✅ 支持banned状态
  ▼
L1 平台原子操作
  ├── douyin_ops.py        ← ✅ 封号检测+同步写homepage_info
  └── ops/xhs_ops.py       ← ✅ 封号检测+同步写homepage_info
  ▼
L0 Camoufox 浏览器
```

---

## 二、剩余问题清单（按优先级）

### P0 —— 必须修（功能阻断）

| # | 问题 | 发现时间 | 涉及文件 |
|:-:|:-----|:---------|:---------|
| ① | **远程 nurture 空值参数导致参数错位** | 2026-06-25 | `command_bus.py:_send_remote` ✅ **已修复** |
| ② | **前端批量账号逐个发送**（matrix-nurture） | 2026-06-25 | `matrix-nurture.js` ✅ **已修复** |
| — | 以上两个问题已修复并推送 | — | — |

### P1 —— 应修（影响体验/一致性和正确性）

| # | 问题 | 涉及文件 | 说明 |
|:-:|:-----|:---------|:------|
| ③ | **`routes/matrix.py` 中 `/nurture/start` 和 `/nurture/preview` 绕过 CommandBus** | `routes/matrix.py:333-443` | 约100行 POST 代码直接调引擎，不走 CommandBus |
| ④ | **`routes/matrix.py` 中 `/task/run` 路由绕过 CommandBus** | `routes/matrix.py:757-790` | 任务执行直接 subprocess |
| ⑤ | **`matrix-accounts.js` 单账号采集(`_actCol`)+登录(`_actLogin`)逐个发送** | `matrix-accounts.js:121-145` | 和修复前的 `_nurtureExec` 一样的问题 |
| ⑥ | **`matrix-comment.js` 评论执行逐个发送** | `matrix-comment.js` | 需要审计 |
| ⑦ | **`matrix-like.js` 收藏点赞逐个发送** | `matrix-like.js` | 需要审计 |
| ⑧ | **CMD_REGISTRY 中 comment 的模板含 `{direction}`，可能缺失** | `command_bus.py:631` | 前端可能不传 direction |
| ⑨ | **nurture 在 CMD_REGISTRY 中定义了 `runner` 字段但 dispatch 未使用** | `command_bus.py:640` | 注册表与实际逻辑不一致 |

### P2 —— 可修（清理/优化/后续）

| # | 问题 | 涉及文件 | 说明 |
|:-:|:-----|:---------|:------|
| ⑩ | **`platforms/` 目录已标记 deprecated 但代码还存在** | `platforms/` | 等待最终清理 |
| ⑪ | **`agentos/plugins/matrix.py` 引用存档脚本** | `agentos/plugins/matrix.py:189-192` | 依然引用 `collect_batch_runner.py` |
| ⑫ | **`scripts/archive/` 中的旧脚本可移出** | `scripts/archive/` | 确认无引用后移除 |
| ⑬ | **`routes/matrix.py` 中 `/nurture/preview`(GET读操作)可保留但需要文档说明** | `routes/matrix.py:333` | 仅预览功能 |
| ⑭ | **联邦机器 `fleet_collector` 缓存过期后 Dashboard 读到旧数据** | `services/fleet_collector.py` | 需要自动刷新机制 |
| ⑮ | **Dashboard 信息采集页展示多渠道数据聚合时的去重** | `routes/matrix.py` | 多台机器有同一个账号时重复显示 |
| ⑯ | **`crawl-tasks.js`、`crawl-sources.js` 等占位符视图无功能** | `views/crawl-*.js` | 11个占位符 |

### P3 —— 远期（架构优化）

| # | 问题 | 说明 |
|:-:|:-----|:------|
| ⑰ | **nurture_runner.sh 和 _send_remote 参数传递方式不同** | 本地传数组、远程传 shell 字符串，应统一 |
| ⑱ | **远程结果回传路径不一致** | nurture 结果在 `/tmp/`，collect 结果在 `runtime/results/` |
| ⑲ | **CMD_REGISTRY 从 dict 改为 dataclass** | 类型安全+IDE 补全 |
| ⑳ | **`routes/ops.py` 改为 class-based router** | 更好的可维护性 |

---

## 三、信息采集专项优化

### 3.1 当前链路（治理后）

```
前端 matrix-collect.js → POST /api/ops/run {type:'collect', accounts, params}
  → CommandBus CMD_REGISTRY["collect"]
    → auto_blueprint: 按账号平台自动选 douyin_read_profile / xiaohongshu_read_profile
    → 按机器分组 → MachineSession 队列 → _send_local / _send_remote
  → 远程执行 mc run --blueprints=xxx --rounds=1
  → BatchEngine → LoginStateMachine → 原子操作 → 数据提取
  → _save_profiles_json() → 写 profiles.json + homepage_info.json ✅
```

### 3.2 已修复的问题

| 问题 | 修复 |
|:-----|:------|
| profiles.json 和 homepage_info.json 不同步 | ✅ `_save_profiles_json()` 同步写两个文件 |
| 封号检测在采集流程内 | ✅ 登录层也检测封号，直接标记 banned |
| 正则取数字为'?' | ✅ 小红书 e2e 兜底已加 |
| 数据写入了但 Dashboard 不显示 | ✅ fleet_collector 缓存清除已做 |

### 3.3 信息采集的剩余优化

| 优化项 | 说明 | 优先级 |
|:-------|:-----|:-------|
| 采集进度实时反馈到 Dashboard | 目前是"提交后等完成"，没有进度条 | P2 |
| 多机采集结果去重 | 同一个 identity_dir 在多台机器都有数据时重复显示 | P2 |
| 采集历史对比（上次 vs 本次） | 方便查看粉丝增长 | P3 |
| homepage_info.json 数据与 ORACLE 账号映射对账 | 自动发现"有账号但未采集" | P2 |

---

## 四、统一命令模板注册表（CMD_REGISTRY）最终设计

```python
CMD_REGISTRY = {
    "nurture": {
        "template": "mc run --accounts={ids} --blueprints={blueprint} --rounds={rounds}",
        "defaults": {"blueprint": "douyin_daily", "rounds": 10},
        "runner": "nurture_runner.sh",       # shell 包装器（本地用）
        "auto_blueprint": False,
    },
    "collect": {
        "template": "mc run --accounts={ids} --blueprints={blueprint} --rounds={rounds}",
        "defaults": {"rounds": 1},
        "auto_blueprint": True,
        "blueprint_map": {
            "douyin": "douyin_read_profile",
            "xiaohongshu": "xiaohongshu_read_profile",
        },
    },
    "login": {
        "template": "mc smart-login {ids}",
        "single_account": True,
    },
    "logout": {
        "template": "mc run --accounts={ids} --blueprints=douyin_daily --rounds=1",
    },
    "comment": {
        "template": "mc task comment --account={ids} --url={url}",
        "required_params": ["url"],
    },
    "like": {
        "template": "mc run --accounts={ids} --blueprints=douyin_daily --rounds=1",
    },
}
```

**核心原则**：
- ✅ 所有操作共用同一套模板渲染引擎
- ✅ 新增操作只需在注册表加一行
- ✅ `auto_blueprint` 让前端不用知道具体蓝图名
- ✅ `required_params` 在 dispatch 时自动校验

---

## 五、实施路线图

### Phase 6: 统一后端执行路由（P1）

| # | 任务 | 文件 | 工作量 |
|:-:|:-----|:-----|:-------|
| 6.1 | 删除 `routes/matrix.py` 中 `/nurture/start` 绕过 CommandBus 的代码 | `routes/matrix.py` | 小 |
| 6.2 | 删除 `/task/run` 绕过 CommandBus 的代码 | `routes/matrix.py` | 小 |
| 6.3 | 确认所有前端视图已改用 `/api/ops/run` | 逐个审计 views/ | 中 |
| 6.4 | 修复 accounts.js 单账号采集逐个发送 | `matrix-accounts.js` | 小 |

### Phase 7: 前端统一调用格式审计（P1）

| # | 任务 | 说明 |
|:-:|:-----|:------|
| 7.1 | 审计所有 views/ 中的 POST 调用，确认格式统一 | 逐个检查 |
| 7.2 | 修复不合规的调用 | 同上 |
| 7.3 | 增加 ESLint 规则或文档约束 | 后续 |

### Phase 8: 远程执行结果回传统一（P2）

| # | 任务 | 说明 |
|:-:|:-----|:------|
| 8.1 | 统一远程命令的结果文件路径 | 目前 `/tmp/` 和 `runtime/results/` 混用 |
| 8.2 | 统一 poll 策略对远程命令的检查方式 | 目前本地和远程各一套逻辑 |

### Phase 9: 清理遗留代码（P2）

| # | 任务 | 文件 |
|:-:|:-----|:------|
| 9.1 | 移除 `platforms/` 目录（或移到 archive） | `platforms/` |
| 9.2 | 修复 `agentos/plugins/matrix.py` 存档引用 | `agentos/plugins/matrix.py` |
| 9.3 | 确认 `scripts/archive/` 无外部引用后移出 | `scripts/archive/` |
| 9.4 | 删除 `routes/matrix.py` 中已废弃的 GET/POST 路由（需逐个确认） | `routes/matrix.py` |

---

## 六、治理后最终状态

```
L5 前端 ── 统一 POST /api/ops/run {type, accounts, params}
L4 路由 ── ops.py 唯一执行入口 | matrix.py 只读查询
L3 总线 ── CMD_REGISTRY 注册表 | 统一模板渲染 | 自动按机器分组
L2 引擎 ── BatchRunner | LoginStateMachine | 封号检测
L1 操作 ── douyin_ops + xhs_ops | 三段式原子操作
L0 浏览器 ── Camoufox | 登录态管理
数据层 ── profiles.json + homepage_info.json 同步写入
封号层 ── 登录检测 + 采集检测 双层判断
```

---

## 七、验证清单

- [ ] Phase 6: 无 POST 路由绕过 CommandBus
- [ ] Phase 7: 所有前端 views POST 调用格式统一
- [ ] Phase 8: 远程结果回传一致，Dashboard 能看到远程执行结果
- [ ] Phase 9: 无 archive 脚本的外部引用

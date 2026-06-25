# AgentOS 命令传导统一治理方案 v1.0

> 日期: 2026-06-25
> 版本: 4.2.1 规划
> 状态: 规划中 → 逐步落地中
> 主线: 消除调用链路打架，CommandBus 成为唯一执行入口

---

## 一、背景与问题

### 1.1 当前问题清单

看板经过多次改造迁移，积累了大量不一致的调用路径。扫描发现：

| # | 问题 | 涉及文件 | 严重程度 |
|:-:|:-----|:---------|:---------|
| ① | 采集有 **6 条入口路径**，5 条有问题 | `routes/matrix.py`、`services/command_bus.py`、`platforms/`、`mc/cli.py` | P0 |
| ② | CommandBus 的 cmd_type 映射散落在 dispatch() 中，不一致 | `services/command_bus.py:698-719` | P0 |
| ③ | `platforms/` 插件层引用已归档脚本 | `platforms/douyin/plugin.py`、`platforms/xiaohongshu/plugin.py` | P1 |
| ④ | 前端视图参数格式不统一（account_ids vs accounts） | `matrix-collect.js`、`matrix-accounts.js` | P1 |
| ⑤ | `routes/matrix.py` 中有路由绕过 CommandBus | `/collect-homepage/phone`、`/nurture/start` | P1 |
| ⑥ | `mc collect --all` 无参数时提示退出不执行 | `mc/cli.py:641-652` | P2 |
| ⑦ | `agents/plugins/matrix.py` 引用存档脚本 | `agentos/plugins/matrix.py:191` | P2 |

### 1.2 根因

```
看板改造迁移过程中：
  旧路径（routes/matrix.py + 直接subprocess）← 未删除
  新路径（routes/ops.py + CommandBus）      ← 新增
  platforms/ 插件层（引用存档脚本）          ← 未同步更新
  前端视图（分两批迁移，参数格式未统一）    ← 未统一
```

---

## 二、治理目标

### 2.1 核心原则

```
┌──────────────────────────────────────────────┐
│     L5 前端视图（薄层）                        │
│     统一发 {type, accounts, params}           │
│     统一走 POST /api/ops/run                  │
├──────────────────────────────────────────────┤
│     L4 API 路由（薄层转发）                    │
│     routes/ops.py 是唯一的执行入口             │
│     routes/matrix.py 中的执行类路由全部删除     │
├──────────────────────────────────────────────┤
│     L3 CommandBus（注册表驱动）               │
│     CMD_REGISTRY 统一映射 cmd_type → 命令     │
│     新增操作只需加一行注册表                   │
├──────────────────────────────────────────────┤
│     L2-L0 mc 引擎 + 原子操作（唯一执行层）     │
│     所有命令最终走到同一套引擎                 │
└──────────────────────────────────────────────┘
```

### 2.2 治理后

| 维度 | 治理前 | 治理后 |
|:-----|:-------|:-------|
| 采集入口 | 6 个（5 个坏） | 2 个（前端 `/api/ops/run` + CLI `mc collect`）|
| 命令映射 | 散落在 dispatch() 中硬编码 | 注册表 `CMD_REGISTRY` |
| 前端调用格式 | `account_ids` / `accounts` 混用 | 统一 `{type, accounts, params}` |
| 新增操作类型 | 改 CommandBus 代码 | 加一行注册表 |
| 平台层 | 两层（PlatformOps + Platform） | 一层（mc 引擎 + 原子操作）|
| archive 引用 | 多处 | 零 |

---

## 三、实施步骤

### Phase 0: 方案文档（当前）

- [x] 创建 `PLANS/COMMAND_UNIFICATION_PLAN.md`（本文档）
- [x] 更新 `01_core/VERSION` → 4.2.1
- [x] 更新 `CHANGELOG.md`

### Phase 1: CommandBus 加操作注册表（P0） ✅

- [x] 在 `services/command_bus.py` 新建 `CMD_REGISTRY` 注册表
- [x] 注册表包含：nurture / collect / login / logout / comment / like
- [x] collect 默认 `--blueprints` 根据账号平台自动选择
- [ ] 验证：所有入口命令格式一致（等启动 Dashboard 后验证）

**修改文件**：`services/command_bus.py` ✅

### Phase 2: 前端统一调用路径（P1） ✅

- [x] `matrix-collect.js` 改走 `POST /api/ops/run {type:'collect', accounts, params}`
- [x] 删除 `routes/matrix.py` 中：
  - `/collect-homepage`
  - `/collect-homepage/phone`
  - `/collect-homepage/cancel`
  - `/collect-homepage/status`
- [ ] 验证：信息采集页批量采集功能正常（等启动 Dashboard 后验证）

**修改文件**：`frontend/src/views/matrix-collect.js` ✅、`routes/matrix.py` ✅

### Phase 3: CLI mc collect 修复（P2） ✅

- [x] `mc/cli.py:cmd_collect()` 支持 `--all` 参数
- [x] 按手机号采集改为先查账号ID再执行（修复直接传phone的bug）
- [x] 新增 `--status` 显示采集状态
- [x] 删除废弃提示
- [ ] 验证：CLI `mc collect --all` 正常（等实际执行时验证）

**修改文件**：`mc/cli.py` ✅

### Phase 4: 标记 platforms/ 为 deprecated（P1） ✅

- [x] `platforms/douyin/plugin.py` 的 `collect()` 方法不再引用 archive 脚本
- [x] `platforms/xiaohongshu/plugin.py` 同上
- [x] 添加 deprecated 注释说明替代方案
- [ ] 注册到 99_system/INDEX.md（待定，取决于 platforms/ 是否记录在 INDEX）

**修改文件**：`platforms/*/plugin.py` ✅

### Phase 5: 更新 AUDIT_5LAYER_REPORT.md（P2） ✅

- [x] 更新信息采集的审计状态（从 `/matrix/collect-homepage` 改为 `/api/ops/run`）
- [x] 添加 CommandBus 注册表审计项

**修改文件**：`PLANS/AUDIT_5LAYER_REPORT.md` ✅

---

## 四、关键设计决策

### 4.1 CMD_REGISTRY 注册表设计

```python
CMD_REGISTRY = {
    "nurture": {
        "runner": "nurture_runner.sh",            # shell 包装器
        "defaults": {"blueprint": "douyin_daily", "rounds": 10},
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

### 4.2 前端统一调用格式

```javascript
// ✅ 所有操作统一格式
await apiRequest('/api/ops/run', {
    method: 'POST',
    body: JSON.stringify({
        type: 'collect',        // nurture / collect / login / logout / comment / like
        accounts: ['douyin_01'], // 账号ID列表
        params: {               // 操作参数（可选，不传则用注册表默认值）
            rounds: 1,
            // blueprint 由服务端根据账号平台自动推断
        },
    }),
});
```

### 4.3 与现有架构的关系

```
现有架构:
  routes/matrix.py → 多个执行入口（需要干掉）
  routes/ops.py    → 统一执行入口（需要保留并做强）
  CommandBus       → 转发层（加注册表）
  mc CLI           → 直接调执行引擎

治理后:
  所有执行操作 → routes/ops.py → CommandBus(注册表) → mc 引擎
  routes/matrix.py 只保留读操作（GET）
  CLI 直接调 mc 引擎（与 CommandBus 共享执行层）
```

---

## 五、版本更新

| 组件 | 当前版本 | 目标版本 | 变更 |
|:-----|:---------|:---------|:-----|
| AgentOS 框架 | 4.2.0 | **4.2.1** | 命令传导统一治理 |
| guardd | 2.3.0 | 2.3.0 | 无变更 |
| ORACLE schema | 1.0 | 1.0 | 无变更 |

---

## 六、验证清单

每阶段完成后验证：

- [ ] Phase 1: CommandBus 注册表生效，collect 命令带 `--blueprints`
- [ ] Phase 2: 信息采集页批量采集功能正常，`/api/matrix/collect-homepage` 路由已删除
- [ ] Phase 3: CLI `mc collect --all` 执行所有账号采集
- [ ] Phase 4: platforms/plugin 不再引用 archive 脚本
- [ ] Phase 5: 审计报告已更新

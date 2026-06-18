# AgentOS 联邦系统 — 全面架构审计报告

> 审计日期: 2026-06-18
> 审计范围: agent-sync/05_tools/07_matrix/scripts + 10_dashboard + 00_bootstrap
> 文件总量: 130 个 Python 文件, 7 个 Shell, 36 个目录

---

## 一、系统全景图

```
┌─────────────────────────────────────────────────────────────────┐
│                     Dashboard (uvicorn :9988)                    │
│  app.py · routes/matrix.py · routes/ops.py · 7 个 services/    │
│  static/index.html (7700行内联JS) · frontend/ (Vite 33视图)      │
├──────────────────────┬──────────────────┬──────────────────────┤
│    mc CLI (入口)      │  matrix.py (旧入口)│   agentos (新入口)    │
│  mc/cli.py (15命令)   │  统一脚本入口     │  cli.py + plugins/   │
├──────────────────────┴──────────────────┴──────────────────────┤
│                        scripts/ (核心)                          │
│  matrix_mgmt.py · collect_*.py · nurture_*.py                  │
│  cdp_connector.py · auth_manager.py · anti_detection.py        │
│  atom_ops.py · orchestrator.py · task_engine.py                │
├──────────────────────┬──────────────────┬──────────────────────┤
│    matrix_modules/    │    mc/ 包        │    archive/          │
│  account/ (登录)      │  cli.py          │  41个旧脚本(已归档)  │
│  nurture/ (养号)      │  run.py/engine   │                      │
│  ops/xhs/ (小红书原子) │  task.py/schedule│                      │
│  comment/             │  proxy/recorder  │                      │
├──────────────────────┴──────────────────┴──────────────────────┤
│                        数据层                                    │
│  agent-local/tools/matrix/                                     │
│  config/accounts.yaml · data/homepage_info.json · identities/  │
│  14个JSON蓝图 · profiles/*.json · anchor_db.sqlite             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、模块级审计

### 2.1 入口层

| 入口 | 文件 | 作用 | 状态 |
|:-----|:-----|:-----|:-----|
| `mc` CLI | `mc/cli.py` | **当前主入口**，15 个子命令: run/collect/account/blueprint/login/smart-login/task/schedule/corpus/proxy/sms/status/record/op/remote | ✅ 正常 |
| `matrix.py` | `matrix.py` | 旧版统一入口（`matrix_utils`），仍被 mc CLI 部分引用 | ⏳ 兼容层 |
| `agentos` | `agentos/cli.py` | 新版智能体 CLI，挂载 plugins/ave/crawl/fleet/matrix/serve | 🔄 开发中 |
| Dashboard | `app.py` | Web 管理台，~50 个 API 端点，33 个视图 | ✅ 正常 |
| `matrix_mgmt.py` | 账号/蓝图/备份管理 | 核心数据管理，被所有组件引用 | ✅ 正常 |

### 2.2 矩阵养号层

| 模块 | 文件 | 功能 | 复用情况 | 状态 |
|:-----|:-----|:------|:--------|:------|
| 账号管理 | `matrix_mgmt.py` | CRUD+多机聚合+蓝图+备份 | 所有组件引用 | ✅ 正常 |
| 账号登录 | `matrix_modules/account/xhs_login.py` | 小红书 SMS 登录原子操作 | 被 xiaohongshu_login.py 调用 | ✅ 正常 |
| 账号登录 | `matrix_modules/account/sms_login.py` | 抖音 SMS 登录原子操作 | 被 douyin_login.py 调用 | ✅ 正常 |
| 账号登录 | `matrix_modules/account/douyin_login.py` | 抖音登录CLI | CLI模式 | ✅ 正常 |
| 账号登录 | `matrix_modules/account/xiaohongshu_login.py` | 小红书登录CLI | CLI模式 | ✅ 正常 |
| 养号引擎 | `matrix_modules/nurture/runner.py` | **75408b** 超大文件，含 38 个函数 | mc run 的核心 | ⚠️ 过大需拆分 |
| 养号引擎 | `orchestrator.py` | 养号调度器(AtomOps+Blueprint) | 替代 runner 的新版 | 🔄 开发中 |
| 日常养号 | `nurture_daily.py` | 旧版日常调度器（286行） | 可能被 runner 替代 | ⏳ 过渡状态 |
| 蓝图 | `nurture_blueprint.py` | 蓝图执行 | 被 atom_ops 调用 | ✅ 正常 |
| 批量采集 | `collect_batch_runner.py` | 分批并行采集 | **当前使用版本** | ✅ 正常 |
| 单身份采集 | `collect_homepage_info.py` | 单身份采集 | 被 batch_runner import | ✅ 正常 |

### 2.3 浏览器/反检测层

| 模块 | 文件 | 大小 | 复用情况 | 状态 |
|:-----|:-----|:----|:--------|:------|
| CDP连接器 | `cdp_connector.py` | 最大(>300行) | **所有浏览器操作的基础** | ✅ 正常 |
| Camoufox管理器 | `camoufox_manager.py` | ~200行 | 部分使用 | ⏳ 与cdp_connector重复 |
| 浏览器管理器 | `browser_manager.py` | ~200行 | 实验性 | ❌ 被cdp_connector替代 |
| 优雅退出 | `browser_utils.py` | `GracefulBrowser`类 | 被 login 模块使用 | ✅ 正常 |
| 反检测 | `anti_detection.py` | BehaviorProfile类 | 部分引用 | ✅ 正常 |
| 账号切换 | `switch_account.py` | Chrome Profile切换 | 基本废弃 | 🗑️ 应归档 |

### 2.4 登录状态管理

| 模块 | 文件 | 功能 | 复用 | 状态 |
|:-----|:-----|:------|:-----|:------|
| 认证管理器 | `auth_manager.py` | Cookie/DOM 多维登录检测 | **核心工具** | ✅ 正常 |
| 页面状态 | `page_state.py` | 页面模式检测(grid/player/search) | 部分使用 | ⏳ 可增强 |
| 原子操作 | `atom_ops.py` | AtomOps类(通用操作) | orchestrator核心 | ✅ 正常 |
| 抖音操作 | `douyin_ops.py` | DouyinOps类(300+行) | 养号引擎核心 | ✅ 正常 |

### 2.5 小红书原子操作

| 模块 | 文件 | 功能 | 状态 |
|:-----|:-----|:------|:------|
| selectors | `matrix_modules/ops/xhs/selectors.py` | DOM选择器常量 | ✅ 正常 |
| browse | `matrix_modules/ops/xhs/browse.py` | 浏览操作 | ✅ 正常 |
| interact | `matrix_modules/ops/xhs/interact.py` | 互动操作 | ✅ 正常 |
| ATOMIC_OPS.md | `matrix_modules/ops/xhs/ATOMIC_OPS.md` | 操作文档 | ✅ 正常 |

### 2.6 任务调度

| 模块 | 文件 | 功能 | 状态 |
|:-----|:-----|:------|:------|
| 任务引擎 | `task_engine.py` | 蓝图执行引擎 | ⏳ 与 runner 功能重叠 |
| 任务调度 | `task_scheduler.py` | 定时任务 | ✅ 正常 |
| C2命令总线 | `c2/command_bus.py` | 跨机命令(HTTP/Git降级) | ✅ 正常 |
| C2采集器 | `c2/profile_scraper.py` | 跨机数据聚合 | ⏳ 旧版功能 |

### 2.7 Dashboard 后端服务

| 服务 | 大小 | 功能 | 状态 |
|:-----|:----|:------|:------|
| `command_bus.py` | 27KB, **4类28函数** | **统一命令总线(v5)** | ✅ **核心** |
| `browser_orchestrator.py` | 9.5KB | 浏览器编排(并发控制) | ✅ 正常 |
| `remote_exec.py` | 6KB | 远程SSH执行 | ⏳ 部分被command_bus替代 |
| `operation_queue.py` | 5.6KB | 操作队列 | ⏳ 与command_bus重叠 |
| `preflight.py` | 3.8KB | 预检(磁盘/浏览器/进程) | ✅ 正常 |
| `resource_lock.py` | 4.4KB | 资源锁定 | ⏳ 与browser_orch重叠 |
| `data_aggregator.py` | 6.7KB | 数据聚合 | ✅ 正常 |
| `log_aggregator.py` | 3.5KB | 日志聚合 | ✅ 正常 |

### 2.8 Dashboard 路由

| 路由文件 | 端点 | 功能 | 状态 |
|:---------|:------|:------|:------|
| `routes/matrix.py` | ~15个 | 养号/采集/蓝图/喂饭 | ✅ 正常 |
| `routes/ops.py` | 4个 | 统一命令总线API | ✅ **核心** |

### 2.9 引导/部署层

| 脚本 | 功能 | 状态 |
|:-----|:------|:------|
| `deploy.sh` | 一键部署(3机) | ✅ 正常 |
| `fleet_sync.sh` | 多机同步 | ✅ 正常 |
| `fleet_reconcile.sh` | 多机对账 | ✅ 正常 |
| `init.sh` | 环境初始化 | ✅ 正常 |
| `setup_env.sh` | 环境配置 | ✅ 正常 |

### 2.10 知识库/规划文档

| 文档 | 内容 | 状态 |
|:-----|:------|:------|
| `ARCHITECTURE_v3.md` | Dashboard架构蓝图(10+) | ✅ 正常 |
| `ARCHITECTURE.md` | 旧版架构 | ⏳ 过时 |
| `DEPLOYMENT.md` | 部署文档 | ⏳ 需更新 |
| `EXECUTION_PIPELINE.md` | 统一执行管道设计 | ✅ 最新 |
| `VITE_MIGRATION_PLAN.md` | 前端重构计划 | ✅ 最新 |

---

## 三、核心问题清单

### P0 — 必须修复

| # | 问题 | 涉及文件 | 影响 |
|:-:|:-----|:---------|:-----|
| 1 | `matrix_modules/nurture/runner.py` 75408b/38函数 — 过于庞大 | 全部养号操作 | 难以维护和调试 |
| 2 | `cdp_connector.py` 和 `camoufox_manager.py` / `browser_manager.py` 功能**严重重叠** | 3个文件管理浏览器 | 调用混乱 |
| 3 | `services/operation_queue.py` 与 `command_bus.py` 功能重叠 | 队列管理重复 | 两种排队逻辑并存 |

### P1 — 需重构

| # | 问题 | 涉及 | 影响 |
|:-:|:-----|:------|:------|
| 4 | 采集流程登录检测**刚修复**(xhs)，抖音登录**尚未集成** | collect_*.py | 抖音未登录时不会自动登录 |
| 5 | `remote_exec.py` 被 `command_bus.py` **部分替代**但未被移除 | 远程执行 | 两份远程执行代码 |
| 6 | `resource_lock.py` 与 `browser_orchestrator.py` 资源管理重叠 | 资源管理 | 两种锁机制 |
| 7 | `switch_account.py` 基本**废弃**但未被归档 | 账号切换 | 死代码 |
| 8 | `browser_manager.py` 实验性代码未被正式使用 | 浏览器管理 | 死代码 |

### P2 — 需优化

| # | 问题 | 涉及 | 影响 |
|:-:|:-----|:------|:------|
| 9 | 41个已归档脚本在 `archive/` — 部分可能含可复用逻辑 | archive/ | 需要清理或复用 |
| 10 | `nurture_daily.py` 被 `collect_batch_runner.py` 部分替代但未删除 | 养号调度 | 两份调度逻辑 |
| 11 | `orchestrator.py` 和 `nurture_daily.py` 功能定位不清 | 调度器 | 新旧交替 |
| 12 | `static/index.html` 7700行 — 内联JS过于庞大 | 前端 | 维护困难 |
| 13 | 未统一使用 `local_paths.py` — 文件散落硬编码路径 | 多处 | 可维护性差 |

---

## 四、模块关系图

```
                          用户/开发
                             │
                ┌────────────┼────────────┐
                │            │            │
           mc CLI          Dashboard   agentos CLI
         (mc/cli.py)     (app.py:9988)  (agentos/cli.py)
                │            │            │
                └─────┬──────┴─────┬──────┘
                      │            │
              command_bus.py  c2/command_bus.py
              (统一命令总线v5)   (HTTP/Git降级)
                      │
         ┌────────────┼──────────────────┐
         │            │                  │
      本地执行      远程SSH         队列调度
         │            │                  │
    ┌────┴────┐  remote_exec.py   operation_queue.py
    │         │
  角色模块  引擎模块
    │         │
  account/  nurture/runner.py
  xhs_login  douyin_ops.py
  sms_login  atom_ops.py
  auth_mgr   blueprint
    │
  cdp_connector.py (浏览器基础)
```

---

## 五、操作类型映射

| 操作 | mc CLI │ 命令总线 │ 前端 | 后端执行 | 状态 |
|:-----|:-------|:---------|:-----|:---------|:-----|
| 养号执行 | `mc run` | `POST /api/ops/run {type:nurture}` | 养号视图 | `mc run --accounts=...` | ✅ |
| 信息采集 | `mc collect` | `POST /api/ops/run {type:collect}` | 采集视图 | `collect_batch_runner.py` | ✅ |
| 登录 | `mc smart-login` | `POST /api/ops/run {type:login}` | 登录视图 | `douyin_login/xhs_login` | ✅ |
| 退出 | `mc account logout` | `POST /api/ops/run {type:logout}` | 登录视图 | `mc account logout ...` | ✅ |
| 评论 | `mc task comment` | `POST /api/ops/run {type:comment}` | 评论视图 | `mc task comment ...` | ✅ |
| 点赞 | `mc task like` | `POST /api/ops/run {type:like}` | 点赞视图 | `mc task like ...` | ✅ |
| 蓝图 | `mc blueprint` | — | 蓝图视图 | matrix_mgmt | ✅ |
| 账号 | `mc account` | — | 账号视图 | matrix_mgmt | ✅ |
| 代理 | `mc proxy` | — | SMS代理 | proxy管理 | ✅ |
| 短信 | `mc sms` | — | SMS代理 | ApiSMSHandler | ✅ |

---

## 六、建议行动顺序

### Phase A: 清理重复（~2小时）

```
1. browser_manager.py → 归档到 archive/
2. switch_account.py → 归档到 archive/  
3. remote_exec.py → 如果完全被 command_bus 替代则归档
4. resource_lock.py → 合并到 browser_orchestrator.py
5. operation_queue.py → 集成到 command_bus.py
```

### Phase B: 整合核心（~3小时）

```
1. 统一浏览器管理 (cdp_connector.py → 唯一入口)
   - camoufox_manager.py 的功能合并到 cdp_connector
   
2. 统一养号引擎
   - nurture_daily.py 的功能合并到 collect_batch_runner.py
   - orchestrator.py 作为新版 adoption
   
3. 统一采集登录
   - 在 extract_douyin() 中也加入登录检测(已为xhs修复)
   - 创建通用 login_if_needed(page, platform, phone) 函数
```

### Phase C: 标准化路径（~1小时）

```
1. 所有文件改用 local_paths.py 获取路径
2. 消除硬编码的 `~/workbuddy-agent-os/agent-local/...`
```

### Phase D: 文档化（~30分钟）

```
1. 更新 ARCHITECTURE_v3.md 反映当前真实架构
2. 在 99_system/ 更新 README.md
```

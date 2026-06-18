# ⚖️ AgentOS 联邦系统 — 架构宪法 v1.0

> 本文件是 AgentOS 联邦系统的**最高架构规范**，定义所有模块的职责边界、调用规则、生命周期。
>
> **本文件描述的是目标架构（最终状态）**。当前实际系统处于过渡阶段，部分组件仍是旧版。
> 所有新代码都按此规范编写，旧代码逐步替换，不倒退。
>
> 生效日期: 2026-06-18
> 版本: 1.0
> 维护者: chengzigedeAir (主控机)
> 适用范围: 所有联邦机器 (chengzigedeAir / 5kechengdeAir / 7kecheng)

---

## 目录

- [第一章 总纲](#第一章-总纲)
- [第二章 架构分层](#第二章-架构分层)
- [第三章 组件状态与生命周期](#第三章-组件状态与生命周期)
- [第四章 调用规范](#第四章-调用规范)
- [第五章 数据流规范](#第五章-数据流规范)
- [第六章 迁移路线图](#第六章-迁移路线图)
- [第七章 例外处理](#第七章-例外处理)
- [附录A 组件状态一览表](#附录a-组件状态一览表)
- [附录B 旧系统索引](#附录b-旧系统索引)

---

## 第一章 总纲

### 1.1 设计原则

| # | 原则 | 说明 |
|:-:|:-----|:------|
| 1 | **目标架构驱动** | 本宪法描述的是最终目标架构。当前系统处于过渡期，存在「桥接」组件（如 `mc` CLI），它们会随着迁移推进逐步退役 |
| 2 | **统一入口** | 所有操作通过 `POST /api/ops/run`（后端）或 `agentos <command>`（CLI）执行。`mc` 是过渡期桥接入口，逐步被 `agentos` 取代 |
| 3 | **单点职责** | 每个模块只做一件事，禁止功能重叠（参见第三章组件状态） |
| 4 | **联邦透明** | 调用方无需关心操作在哪台机器执行，command_bus 自动路由 |
| 5 | **状态可观测** | 每个操作都有完整的生命周期（queued→preflighting→dispatching→running→completed/failed） |
| 6 | **前向兼容** | 旧模块持续可用直到新模块完全验证通过，但标记为"废弃"后不再修复 |
| 7 | **路径统一** | 所有文件路径通过 `local_paths.py` 获取，禁止硬编码 |

### 1.2 系统总架构

```
                    ┌──────────────────────────────────────┐
                    │        agentos CLI (最终目标)          │
                    │   agentos <domain> <command>          │
                    │                                      │
                    │   ┌─────────┐   ┌───────────┐        │
                    │   │ matrix  │   │   ave     │        │  ← 插件自动发现
                    │   │ 社交矩阵 │   │  视频工厂  │        │
                    │   ├─────────┤   ├───────────┤        │
                    │   │ fleet   │   │  crawl    │        │
                    │   │ 联邦管理 │   │  内容采集  │        │
                    │   ├─────────┤   └───────────┘        │
                    │   │ serve   │                         │
                    │   │ 服务管理 │                         │
                    │   └─────────┘                         │
                    └──────────────────┬───────────────────┘
                                       │
                    ┌──────────────────┴───────────────────┐
                    │      mc CLI (过渡桥接)                 │
                    │  15 个命令 → 分散到 agentos 各插件     │
                    └──────────────────┬───────────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                │              Dashboard                       │
                │    (app.py:9988) Web 界面，封装所有领域      │
                └──────────────────────┬──────────────────────┘
                                       │
                              ┌────────┴────────┐
                              │  command_bus.py  │    ← 传输层（唯一通道，不变）
                              └────────┬────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         │                             │                             │
    ┌────┴────┐                  ┌────┴────┐                  ┌─────┴─────┐
    │ 本地执行 │                  │ SSH远程 │                  │  队列     │
    └────┬────┘                  └────┬────┘                  └─────┬─────┘
         │                             │                             │
    ┌────┴─────────────────────────────┴─────────────────────────────┴────┐
    │                        执行体                                       │
    │  nurture / collect / login / comment / like / logout               │
    └──────────────────────────────┬──────────────────────────────────────┘
                                   │
                          ┌────────┴────────┐
                          │  cdp_connector   │        ← 浏览器层（唯一入口）
                          │  + auth_manager  │
                          └────────┬─────────┘
                                   │
                          ┌────────┴────────┐
                          │ Camoufox Browser│        ← 指纹浏览器
                          └─────────────────┘
```

---

## 第二章 架构分层

### 2.1 入口层

#### agentos CLI — 插件式框架（最终目标）

`agentos` CLI 是一个**插件式框架**，核心机制是 `agentos/base.py` 中定义的 `AgentOSPlugin` 基类 + 自动发现机制：

```
agentos <domain> <command> [options]
         ↑ 插件领域   ↑ 该领域下的子命令
```

现有 5 个领域插件，每个对应 Dashboard 的一个大类：

| 领域 | 插件文件 | 对应 Dashboard 视图群 | 来源 |
|:-----|:---------|:---------------------|:------|
| **matrix** | `plugins/matrix.py` | 矩阵养号系列 (11个视图) | 来自 mc CLI 的账号/养号/采集/评论/点赞/发布等 |
| **ave** | `plugins/ave.py` | 视频工厂系列 (4个视图) | **独立领域，非 mc 来源** |
| **crawl** | `plugins/crawl.py` | 内容采集系列 (3个视图) | **独立领域，非 mc 来源** |
| **fleet** | `plugins/fleet.py` | 联邦管理系列 (3个视图) | 来自 mc CLI 的远程/同步/对账 |
| **serve** | `plugins/serve.py` | 服务管理系列 (3个视图) | 来自 mc CLI 的 MCP/Dashboard/调度 |

`agentos` 采用**插件自动发现**机制：`discover_plugins()` 扫描 `plugins/` 目录，自动加载继承 `AgentOSPlugin` 的类。这意味着：
- **新增领域 = 在 plugins/ 加一个 .py 文件**，无需修改框架代码
- **已有字段通过 `nav` 属性（JSON 格式）与 Dashboard 导航联动**
- **所有插件共享 `--json`（JSON 输出）和 `--verbose` 通用参数**

#### mc CLI — 过渡期桥接入口

`mc` CLI 是 `agentos` 开发完成前的过渡入口。mc 的 15 个命令**分散对应**到多个 agentos 领域：

| mc 命令 | → agentos 领域 |
|:--------|:---------------|
| `mc run` / `mc account` / `mc collect` / `mc smart-login` / `mc task` / `mc blueprint` / `mc corpus` / `mc record` / `mc op` | → **`agentos matrix`** |
| `mc status` / `mc remote` | → **`agentos fleet`** |
| `mc proxy` / `mc sms` | → **`agentos serve`** (或 matrix) |
| `mc schedule` | → **`agentos serve`** |

#### 入口层汇总

| 入口 | 文件 | 当前状态 | 目标状态 | 职责 |
|:-----|:-----|:---------|:---------|:------|
| `agentos` CLI | `agentos/cli.py` | 🔄 **开发中** | ✅ **最终目标** | 插件式框架，统一所有领域入口 |
| `mc` CLI | `mc/cli.py` | ✅ **当前主力** 但标记为过渡 | 🗑️ **退役** → agentos | 命令行操作，逐个迁移到 agentos 各插件 |
| Dashboard | `app.py:9988` | ✅ **活跃** | ✅ **一直保留** | Web 管理界面，封装所有领域 |
| `matrix.py` | `matrix.py` | ⏳ **过渡** | 🗑️ 退役 | 旧CLI入口，被 mc/agentos 替代 |

**迁移原则**:
1. `mc` 的命令**不是全部进 `agentos matrix`**，而是按领域分到对应的 agentos 插件
2. 每迁移一个命令，`mc` 对应子命令标记为 `@deprecated` 并指向正确的 `agentos <domain>` 用法
3. `agentos serve` 和 `agentos fleet` 可以独立于 `agentos matrix` 先行完成（因为它们依赖少）
4. 新增领域插件无需修改框架——加文件即可

#### Dashboard 与 agentos 的对应关系

Dashboard 的 33 个视图按领域分组，与 agentos 插件一一对应：

| Dashboard 导航分组 | 包含视图 | → agentos 插件 |
|:------------------|:---------|:--------------|
| 📱 矩阵 | 11 个视图（账号/养号/采集/发布/评论/点赞/蓝图/定时/语料/登录/指挥台） | **matrix** |
| 🎬 视频工厂 | 4 个视图（渲染/脚本/素材/模板） | **ave** |
| 📡 内容采集 | 3 个视图（任务/源/历史） | **crawl** |
| 🖥️ 联邦 + 机器状态 | 4 个视图（状态/同步/对账/远程） | **fleet** |
| ⚙️ 服务 | 3 个视图（MCP/Dashboard/调度） | **serve** |

### 2.2 传输层

传输层是**整个联邦系统的唯一命令通道**。所有操作（本机和远程）都通过 `command_bus.py` 分发。

| 组件 | 文件 | 状态 | 职责 |
|:-----|:-----|:-----|:------|
| **CommandBus** | `services/command_bus.py` | ✅ **核心** | 命令生命周期管理、机器路由、状态轮询 |
| MachineSession | 同上 | ✅ **核心** | 单机会话、预检、发送、轮询、取消 |
| Command | 同上 | ✅ **核心** | 命令模型（含生命周期状态机） |
| `c2/command_bus.py` | 旧版C2 | 🗑️ **废弃** | 被新版 command_bus 替代 |

**API 合约**:
```
POST /api/ops/run  {type, accounts, params}
  → {status, commands: [{run_id, machine, status, pid, message}]}

GET  /api/ops/status [?machine=xxx]
  → {commands: [{run_id, type, accounts, status, elapsed_sec, message}]}

GET  /api/ops/machines
  → {machines: {machine_name: {reachable, browsers_running, active_commands}}}

POST /api/ops/cancel/{run_id}
  → {ok: true}
```

**规则**: 
- 所有执行操作（nurture/collect/login/logout/comment/like）必须走 CommandBus
- 禁止绕过 CommandBus 直接调用 `subprocess.Popen`、`SSH`、`mc run` 等
- 前端统一使用 `ExecutionPipeline.run()` （参见 `static/index.html`）

### 2.3 执行体层 (Executors)

执行体是被 CommandBus 调用的具体操作实现。

| 操作 | 命令模板 | 后端执行文件 | 状态 |
|:-----|:---------|:-------------|:-----|
| **nurture** | `mc run --accounts=X --blueprints=Y --rounds=N` | `nurture_runner.sh` → `nurture/runner.py` | ✅ |
| **collect** | `mc collect --phone=X` | `collect_batch_runner.py` | ✅ |
| **login** | `mc smart-login X` | `sms_login.py` / `xhs_login.py` | ✅ |
| **logout** | `mc account logout X` | via matrix_mgmt | ✅ |
| **comment** | `mc task comment --account=X --url=Y` | via mc/task.py | ✅ |
| **like** | `mc task like --account=X --url=Y` | via mc/task.py | ✅ |

**规则**:
- 每个执行体必须支持 `--phone` 或 `--account` 单身份模式（由 command_bus 按机器分组后调用）
- 执行体只做一件事，不负责机器路由、预检、结果回传
- 结果以 JSON 文件写入 `$AGENT_LOCAL/runtime/{op_type}/results/{run_id}.json`

### 2.4 浏览器层

浏览器层是**所有浏览器操作的唯一接口**。三个模块对应不同阶段，但**现阶段只用 cdp_connector.py**。

| 组件 | 文件 | 状态 | 职责 |
|:-----|:-----|:------|:------|
| **CDPConnector** | `cdp_connector.py` | ✅ **活跃 - 主接口** | 浏览器启动/连接/导航/关闭 |
| **auth_manager** | `auth_manager.py` | ✅ **活跃** | 登录状态检测（Cookie / DOM 双维度） |
| **anti_detection** | `anti_detection.py` | ✅ **活跃** | 行为指纹、人体延迟模拟 |
| **page_state** | `page_state.py` | ✅ **活跃** | 页面模式检测（grid/player/search） |
| **GracefulBrowser** | `browser_utils.py` | ✅ **活跃** | 浏览器优雅退出 + 超时自动关闭 |
| camoufox_manager | `camoufox_manager.py` | 🗑️ **废弃** | 被 CDPConnector 替代 |
| browser_manager | `browser_manager.py` | 🗑️ **废弃** | 实验性模块，从未正式使用 |

**规则**:
- 所有浏览器操作必须通过 `CDPConnector` 创建/管理
- 登录状态检测必须通过 `auth_manager.get_login_status()`（Cookie + DOM 双重验证）
- 行为模拟必须通过 `anti_detection.BehaviorProfile`
- 禁止直接写 `camoufox` 或 `playwright` 原生调用

### 2.5 数据层

| 组件 | 位置 | 访问方式 | 状态 |
|:-----|:-----|:---------|:------|
| **matrix_mgmt** | `matrix_mgmt.py` | `MatrixManager()` 实例 | ✅ **核心** |
| **accounts.yaml** | `agent-local/tools/matrix/config/` | 通过 matrix_mgmt | ✅ |
| **identities/** | `agent-local/tools/matrix/identities/` | 通过 matrix_mgmt | ✅ |
| **anchor_db** | `matrix_modules/nurture/anchor_db.py` | 养号行为锚点 | ✅ |
| **local_paths** | `local_paths.py` | **路径获取的唯一入口** | ✅ **核心** |

**规则**:
- 账号 CRUD **必须**通过 `matrix_mgmt.MatrixManager`
- 所有路径 **必须**通过 `local_paths.py`，禁止 `Path.home() / "workbuddy-agent-os" / ...`
- 跨机账号数据通过 `matrix_mgmt._read_all_machines_accounts()` 聚合

---

## 第三章 组件状态与生命周期

每个组件有以下状态之一：

| 状态 | 标识 | 含义 | 处理方式 |
|:-----|:-----|:------|:---------|
| ✅ **活跃** | 绿色 | 当前标准组件，所有新代码必须使用 | 持续维护 |
| ⏳ **过渡** | 黄色 | 正在被取代，但仍被引用 | 尽快迁移 |
| 🔄 **开发中** | 蓝色 | 新开发尚未完成 | 完成后切换 |
| 🗑️ **废弃** | 红色 | 不再维护，将归档 | 迁移到 archive/ |
| 归档 | — | 已从主代码库移除，只保留参考 | 在 archive/ 中只读 |

### 完整状态表

详见 [附录A](#附录a-组件状态一览表)

---

## 第四章 调用规范

### 4.1 前端 → 后端 调用规则

```
前端点击按钮
  → collectExec() / doNurtureExec() / runComment() / ...  
      → ExecutionPipeline.run({type, accounts, params, logId, statusId})
          → fetch /api/ops/machines              (预检)
          → fetch POST /api/ops/run {dry_run}    (计划)
          → confirm()                             (确认)
          → fetch POST /api/ops/run               (执行)
          → setInterval fetch /api/ops/status     (轮询)
          → 完成后停止轮询
```

**规则**：
- 所有执行按钮**必须**使用 `ExecutionPipeline.run()`，禁止手动写 fetch 逻辑
- `ExecutionPipeline` 是前端唯一的执行入口
- 新视图必须通过 `router.js` 注册为 migrated view

### 4.2 后端 → 执行体 调用规则

```
command_bus.dispatch(type, accounts, params)
  → 按 machine 分组
    → 每组一条命令（含多个账号）
      → preflight()       检查机器+槽位
      → graceful_exit()   清理同机残留
      → send()            发送到本机/远程
        → nurture_runner.sh / mc collect / mc smart-login ...
```

**规则**：
- 参数传递用 `accounts=["a","b","c"]` 批量形式（按机器分组后）
- 结果回传用 JSON 文件 → command_bus.poll() 读取

### 4.3 路径获取规则

```python
# ✅ 正确: 使用 local_paths
from local_paths import config_path, data_path, profiles_path
accounts = config_path("accounts.yaml")    # → correct path
db       = data_path("matrix.db")          # → correct path

# ❌ 错误: 硬编码
Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / ...
```

---

## 第五章 数据流规范

### 5.1 命令生命周期状态机

```
                      ┌────────────┐
                      │   queued   │
                      └─────┬──────┘
                            │
                      ┌─────┴──────┐
                      │ preflighting│
                      └─────┬──────┘
                     ┌──────┴───────┐
                     │              │
              ┌──────┴─────┐  ┌────┴──────┐
              │ preflight_ │  │dispatching│
              │  failed    │  └────┬──────┘
              └────────────┘       │
                            ┌──────┴──────┐
                            │   running   │
                            └──────┬──────┘
                     ┌──────────────┼────────────────┐
                     │              │                │
              ┌──────┴─────┐ ┌──────┴──────┐  ┌──────┴──────┐
              │ completed  │ │   failed    │  │ timed_out   │
              └────────────┘ └─────────────┘  └─────────────┘
```

### 5.2 数据流向

```
用户操作 → ExecutionPipeline → fetch /api/ops/run
  → command_bus.dispatch()
    → MachineSession.send()
      → (本机) subprocess.Popen / (远程) SSH
        → executor script
          → 写入 $AGENT_LOCAL/runtime/{type}/results/{run_id}.json
  ← {run_id, status, pid}
  ← command_bus.poll() 读取结果文件
  ← ExecutionPipeline 轮询 /api/ops/status
  ← 前端显示
```

---

## 第六章 迁移路线图

### Phase 0: agentos 能力建设（最高优先级）

`agentos` CLI 是**插件式框架**，现有 5 个领域插件。优先把核心操作迁移到正确的插件：

#### agentos matrix（核心 — P0）

| mc 命令 | agentos 对应 | 状态 |
|:--------|:------------|:------|
| `mc account` → | `agentos matrix account` | 🔄 待迁移 |
| `mc run` → | `agentos matrix run` | 🔄 待迁移 |
| `mc collect` → | `agentos matrix collect` | 🔄 待迁移 |
| `mc smart-login` → | `agentos matrix login` | 🔄 待迁移 |
| `mc account logout` → | `agentos matrix logout` | 🔄 待迁移 |
| `mc task comment/like` → | `agentos matrix comment / like` | 🔄 待迁移 |
| `mc blueprint` → | `agentos matrix blueprint` | 🔄 待迁移 |
| `mc corpus` → | `agentos matrix corpus` | 🔄 待迁移 |

#### agentos fleet（P1 — 独立可先行）

| mc 命令 | agentos 对应 | 状态 |
|:--------|:------------|:------|
| `mc status` → | `agentos fleet status` | 🔄 待迁移 |
| `mc remote exec` → | `agentos fleet exec` | 🔄 待迁移 |
| — | `agentos fleet sync` | ✅ 已有 |

#### agentos serve（P1 — 独立可先行）

| mc 命令 | agentos 对应 | 状态 |
|:--------|:------------|:------|
| `mc schedule` → | `agentos serve schedule` | 🔄 待迁移 |
| `mc proxy` → | `agentos serve proxy` | 🔄 待迁移 |
| `mc sms` → | `agentos serve sms` | 🔄 待迁移 |

#### agentos ave（独立领域，不来自 mc）

| 功能 | agentos 对应 | 状态 |
|:-----|:------------|:------|
| 渲染任务 | `agentos ave render` | ✅ 已有 |
| 脚本生成 | `agentos ave script` | ✅ 已有 |
| 素材库 | `agentos ave materials` | ✅ 已有 |
| 模板管理 | `agentos ave templates` | ✅ 已有 |

#### agentos crawl（独立领域，不来自 mc）

| 功能 | agentos 对应 | 状态 |
|:-----|:------------|:------|
| 采集任务 | `agentos crawl tasks` | ✅ 已有 |
| 源管理 | `agentos crawl sources` | ✅ 已有 |
| 采集历史 | `agentos crawl history` | ✅ 已有 |

每迁移一个命令，`mc` 对应子命令标记为 `@deprecated` 并指向 `agentos`。
当 `mc` 所有命令都迁移完成后，`mc` 本身退役。

### Phase 1: 清理废弃代码（与 Phase 0 并行）

| 待归档文件 | 目标位置 | 替代方案 |
|:-----------|:---------|:---------|
| `camoufox_manager.py` | `archive/camoufox_manager.py` | `cdp_connector.py` |
| `browser_manager.py` | `archive/browser_manager.py` | `cdp_connector.py` |
| `switch_account.py` | `archive/switch_account.py` | —（已废弃功能） |
| `c2/command_bus.py` | `archive/c2_command_bus.py` | `services/command_bus.py` |
| `c2/profile_scraper.py` | `archive/c2_profile_scraper.py` | Dashboard 采集API |

### Phase 2: 功能整合（Phase 0 中并行）

| 待整合 | 目标 | 说明 |
|:-------|:------|:------|
| `nurture_daily.py` → `orchestrator.py` | 统一养号引擎 | 新版orchestrator完成adoption |
| `remote_exec.py` → `command_bus.py` | 统一远程执行 | command_bus._send_remote 已实现 |
| `operation_queue.py` → `command_bus.py` | 统一队列 | command_bus 内置队列 |
| `resource_lock.py` → `browser_orchestrator.py` | 统一资源锁 | browser_orch 做并发控制 |
| `matrix.py` → `mc/cli.py` | 统一入口 | mc 已有完整命令集 |

### Phase 3: 标准化（贯穿始终）

| 待标准化 | 说明 |
|:---------|:------|
| 所有文件改用 `local_paths.py` | 消除硬编码路径 |
| `extract_douyin()` 加入登录检测 | 对标 `extract_xiaohongshu()` |
| 统一日志格式（JSON Lines） | 便于聚合分析 |

### 迁移原则

1. **先存档，不删除** — 旧代码移到 `archive/`，不删 git 历史
2. **新系统允许有问题** — 发现问题就修问题，不退回旧系统
3. **冻结旧系统** — 废弃模块不再提交修复PR
4. **文档先行** — 每次迁移前更新宪法附录

---

## 第七章 例外处理

### 7.1 允许绕过的情形

在以下情形可以临时绕过规范，但必须**事后补充 Issue/MR**：

1. **紧急修复线上问题** — 但修复后24小时内必须补全规范
2. **一次性迁移/归档脚本** — 迁移完成后删除
3. **实验性新功能** — 标记为 `@experimental`，独立目录开发

### 7.2 违规处理

对违反本宪法的代码合并/部署：
- 代码审查不通过
- Dashboard 部署自动回滚
- 运行期拦截告警（guardd 检测到不一致时报警）

---

## 附录A: 组件状态一览表

### 入口层

| 组件 | 当前状态 | 目标状态 | 说明 |
|:-----|:---------|:---------|:------|
| `agentos` CLI (框架) | 🔄 **开发中** | ✅ **最终目标** | 插件式框架，`agentos <domain> <command>` |
| `agentos/plugins/matrix.py` | 🔄 **开发中** | ✅ **最终目标** | 社交矩阵插件 |
| `agentos/plugins/ave.py` | ✅ **已有** | ✅ **保留** | 视频工厂插件（独立领域） |
| `agentos/plugins/crawl.py` | ✅ **已有** | ✅ **保留** | 内容采集插件（独立领域） |
| `agentos/plugins/fleet.py` | ✅ **已有** | ✅ **保留** | 联邦管理插件 |
| `agentos/plugins/serve.py` | ✅ **已有** | ✅ **保留** | 服务管理插件 |
| `mc/cli.py` | ✅ **活跃(桥接)** | 🗑️ **退役** | 当前主力，逐个迁移到 agentos 各插件 |
| `app.py` (Dashboard) | ✅ **活跃** | ✅ **保留** | Web 界面，长期存在 |
| `matrix.py` | ⏳ **过渡** | 🗑️ **退役** | 旧入口，被 mc/agentos 替代 |

### 传输层

| 组件 | 状态 | 迁移目标 | 备注 |
|:-----|:-----|:---------|:-----|
| `services/command_bus.py` | ✅ **活跃 (标准)** | — | **所有操作必走这里** |
| `routes/ops.py` | ✅ **活跃** | — | command_bus 的 API 暴露 |
| `c2/command_bus.py` | 🗑️ **废弃** | → `services/command_bus.py` | Phase1 归档 |
| `c2/profile_scraper.py` | 🗑️ **废弃** | → Dashboard 采集 | Phase1 归档 |
| `services/operation_queue.py` | 🗑️ **废弃** | → `command_bus.py` | Phase2 整合 |
| `services/remote_exec.py` | 🗑️ **废弃** | → `command_bus.py` | Phase2 整合 |
| `services/resource_lock.py` | 🗑️ **废弃** | → `browser_orchestrator.py` | Phase2 整合 |

### 执行体层

| 组件 | 状态 | 迁移目标 | 备注 |
|:-----|:-----|:---------|:-----|
| `nurture_runner.sh` | ✅ **活跃** | — | 养育执行包装器 |
| `collect_batch_runner.py` | ✅ **活跃** | — | 批量采集引擎 |
| `collect_homepage_info.py` | ✅ **活跃** | — | 单身份采集逻辑 |
| `sms_login.py` / `xhs_login.py` / `douyin_login.py` | ✅ **活跃** | — | 登录执行体 |
| `nurture_daily.py` | ⏳ **过渡** | → `orchestrator.py` | Phase2 迁移 |
| `nurture/runner.py` | ⏳ **过渡** | 拆分为子模块 | 75KB过大需拆分 |
| `orchestrator.py` | 🔄 **开发中** | — | 新版养号引擎 |

### 浏览器层

| 组件 | 状态 | 迁移目标 | 备注 |
|:-----|:-----|:---------|:-----|
| `cdp_connector.py` | ✅ **活跃 (标准)** | — | **所有浏览器操作的唯一入口** |
| `auth_manager.py` | ✅ **活跃** | — | 登录状态检测唯一入口 |
| `anti_detection.py` | ✅ **活跃** | — | 行为指纹 |
| `browser_utils.py` | ✅ **活跃** | — | 优雅退出 |
| `page_state.py` | ✅ **活跃** | — | 页面模式检测 |
| `camoufox_manager.py` | 🗑️ **废弃** | → `cdp_connector.py` | Phase1 归档 |
| `browser_manager.py` | 🗑️ **废弃** | 直接归档 | Phase1 归档 |
| `switch_account.py` | 🗑️ **废弃** | 直接归档 | Phase1 归档 |

### 数据层

| 组件 | 状态 | 备注 |
|:-----|:------|:------|
| `matrix_mgmt.py` | ✅ **活跃 (标准)** | 账号管理唯一入口 |
| `local_paths.py` | ✅ **活跃 (标准)** | 路径获取唯一入口 |
| `anchor_db.py` | ✅ **活跃** | 养号行为数据库 |
| `auth_manager.py` | ✅ **活跃** | Cookie/DOM 登录检测 |

### Dashboard 服务层

| 组件 | 状态 | 备注 |
|:-----|:------|:------|
| `command_bus.py` | ✅ **核心** | 命令传输 |
| `browser_orchestrator.py` | ✅ **活跃** | 并发控制+错峰 |
| `preflight.py` | ✅ **活跃** | 执行前预检 |
| `data_aggregator.py` | ✅ **活跃** | 数据聚合 |
| `log_aggregator.py` | ✅ **活跃** | 日志聚合 |
| `remote_exec.py` | 🗑️ **废弃** | 被 command_bus 替代 |
| `operation_queue.py` | 🗑️ **废弃** | 被 command_bus 替代 |
| `resource_lock.py` | 🗑️ **废弃** | 被 browser_orch 替代 |

---

## 附录B: 旧系统索引

### 已归档文件 (archive/)

位于 `05_tools/07_matrix/scripts/archive/`，共 41 个文件，全部为 Phase A/B 测试脚本。
**参考价值**：这些文件不再被任何活跃代码引用，但包含部分可复用的 DOM 操作 selector/pattern。

### 废弃但未归档文件 (需 Phase1 处理)

| 文件 | 位置 | 最后改动 | 归档目标 |
|:-----|:------|:---------|:---------|
| camoufox_manager.py | scripts/ | — | archive/ |
| browser_manager.py | scripts/ | — | archive/ |
| switch_account.py | scripts/ | — | archive/ |
| c2/command_bus.py | scripts/c2/ | — | archive/ |
| c2/profile_scraper.py | scripts/c2/ | — | archive/ |

---

> **本宪法每季度审查一次，根据系统实际演进情况更新版本号。**
> 
> 下一版预期: v1.1（Phase 1 清理完成后）

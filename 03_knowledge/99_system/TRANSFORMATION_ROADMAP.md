# AgentOS 联邦系统 — 全量改造路线图

> **依据**: `ARCHITECTURE_CONSTITUTION.md` (架构宪法 v1.0)  
> **集成**: `ARCHITECTURE_v3.md` + `VITE_MIGRATION_PLAN.md` + `EXECUTION_PIPELINE.md` + 审计报告  
> **目标**: 一套标准、一个框架、三机统一、联邦自治  
> **创建**: 2026-06-18 | **状态**: ✅ 已定义，待执行

---

## 一、最终目标状态

当所有阶段完成时，系统呈现以下面貌：

```
用户操作方式（三选一）:
  agentos matrix run --accounts douyin_01 --blueprints douyin_daily    ← CLI
  agentos fleet sync                                                    ← CLI
  agentos ave render ...                                                ← CLI
  Dashboard (localhost:9988)                                            ← Web
  智能体 (AI 自动调度)                                                   ← AI

后端架构:
  agentos/plugins/matrix.py   →  command_bus.py  →  执行体
  agentos/plugins/ave.py      →  (直接调用)       →  视频处理
  agentos/plugins/crawl.py    →  (直接调用)       →  抓取引擎
  agentos/plugins/fleet.py    →  SSH/HTTP        →  远程机器
  agentos/plugins/serve.py    →  本地服务         →  MCP/调度

数据层:
  matrix_mgmt.py (账号唯一入口)
  local_paths.py (路径唯一入口)
  auth_manager.py (登录检测唯一入口)
  cdp_connector.py (浏览器唯一入口)

已退役:
  mc CLI                          → 全部能力迁移到 agentos
  matrix.py                       → 入口退役
  camoufox_manager.py             → 归档
  browser_manager.py              → 归档
  switch_account.py               → 归档
  c2/command_bus.py               → 归档
  c2/profile_scraper.py           → 归档
  remote_exec.py                  → 被 command_bus 替代
  operation_queue.py              → 被 command_bus 替代
  resource_lock.py                → 被 browser_orchestrator 替代
  nurture_daily.py                → 被 orchestrator 替代
  static/index.html (7700行)      → 被 Vite 构建产物替代
```

---

## 二、阶段总览

```
Phase 0: agentos 框架补全         ← 短期（本周）
  ├── Step 0.1: agentos matrix 插件补齐
  ├── Step 0.2: agentos fleet/serve 插件补齐
  └── Step 0.3: agentos 作为 mc 的壳（调用转发）

Phase 1: 清理 + 标准化              ← 短期（并行）
  ├── Step 1.1: 废弃文件归档（5个文件）
  ├── Step 1.2: service 层合并（remote_exec/operation_queue/resource_lock）
  ├── Step 1.3: local_paths.py 路径统一
  └── Step 1.4: 抖音采集加入登录检测

Phase 2: Dashboard 前端重构         ← 中期（2-3天）
  ├── Step 2.1: Vite HMR 开发模式稳定
  ├── Step 2.2: 迁移视图对接新 API
  ├── Step 2.3: 构建产物部署
  └── Step 2.4: 旧 index.html 退役

Phase 3: agentos → 全线贯通         ← 中期
  ├── Step 3.1: mc 全部命令迁移到 agentos
  ├── Step 3.2: mc CLI 退役
  └── Step 3.3: 三机统一部署验证

Phase 4: 联邦自治                   ← 长期
  ├── Step 4.1: 智能体自动调度
  ├── Step 4.2: 故障自愈
  └── Step 4.3: 全链路监控
```

---

## 三、详细执行计划

---

### Phase 0: agentos 框架补全（最高优先级）

#### Step 0.1: agentos matrix 插件补齐

**现状**: `agentos/plugins/matrix.py` 只有 77 行，只有基本框架，没实现具体命令。

**目标**: `agentos matrix run|collect|login|logout|comment|like|blueprint|corpus` 能正常调用底层。

| 子任务 | 文件 | 预计 | 前置 |
|:-------|:-----|:----|:------|
| 0.1a 实现 `agentos matrix run` → 调用 `mc run` | `plugins/matrix.py` + `cli.py` | 1h | — |
| 0.1b 实现 `agentos matrix collect` → 调用 `collect_batch_runner.py` | 同上 | 1h | — |
| 0.1c 实现 `agentos matrix login/logout` → 调用 login 模块 | 同上 | 1h | — |
| 0.1d 实现 `agentos matrix comment/like` → 调用 mc task | 同上 | 1h | — |
| 0.1e 实现 `agentos matrix blueprint/corpus` → 调用 matrix_mgmt | 同上 | 0.5h | — |

**验收**: `agentos matrix run --accounts douyin_test --blueprints douyin_daily --rounds 1` 成功执行

#### Step 0.2: agentos fleet/serve 插件补齐

| 子任务 | 文件 | 预计 |
|:-------|:-----|:-----|
| 0.2a `agentos fleet sync/reconcile/exec` → 调用 fleet_sync.sh/fleet_reconcile.sh | `plugins/fleet.py` | 0.5h |
| 0.2b `agentos serve mcp/dashboard/schedule` → 调用对应服务 | `plugins/serve.py` | 0.5h |
| 0.2c `agentos serve proxy/sms` → 接入代理/短信管理 | `plugins/serve.py` | 1h |

#### Step 0.3: agentos 作为 mc 的壳

**策略**: 在 mc CLI 执行时，**优先检查 agentos 是否有对应实现**。如果有，直接转发到 agentos。

```
mc run --accounts=X --blueprints=Y
  → 检查 agentos 是否可用
    → 是: subprocess.run(["agentos", "matrix", "run", ...])
    → 否: 走旧逻辑（向后兼容）
```

这样做的意义：
- 用户无感知迁移（mc 命令照常敲，背后用的是 agentos）
- 一旦 agentos 稳定了，mc 只需改一个转发开关
- 不用一次性重写所有 mc 命令

| 子任务 | 预计 |
|:-------|:-----|
| 0.3a mc/cli.py 入口加 agentos 转发检测 | 1h |
| 0.3b 逐个命令切换转发（从最简单开始：status/blueprint/corpus） | 2h |

---

### Phase 1: 清理 + 标准化（与 Phase 0 并行）

#### Step 1.1: 废弃文件归档

| 文件 | 移到 | 替代方案 | 预计 |
|:-----|:-----|:---------|:-----|
| `camoufox_manager.py` | `archive/camoufox_manager.py` | `cdp_connector.py` | 5min |
| `browser_manager.py` | `archive/browser_manager.py` | `cdp_connector.py` | 5min |
| `switch_account.py` | `archive/switch_account.py` | 无（已废弃） | 5min |
| `c2/command_bus.py` | `archive/c2_command_bus.py` | `services/command_bus.py` | 5min |
| `c2/profile_scraper.py` | `archive/c2_profile_scraper.py` | Dashboard API | 5min |
| 检查所有 import 引用 → 更新或移除 | — | — | 30min |

⚠️ **必须先检查引用关系再移**，防止 import 断裂。

#### Step 1.2: service 层合并

| 待合并 | 合并到 | 说明 | 预计 |
|:-------|:-------|:-----|:------|
| `remote_exec.py` | `command_bus.py._send_remote()` | command_bus 已实现远程发送 | 1h |
| `operation_queue.py` | `command_bus.py` (内置队列) | command_bus.MachineSession 已有队列 | 1h |
| `resource_lock.py` | `browser_orchestrator.py` | 并发限制由 browser_orch 做 | 1h |

**步骤**:
1. 检查每个函数的调用方（用 grep 找 import/reference）
2. 把调用方改成新路径
3. 旧文件标记 deprecated 头注释
4. 确认无引用后归档

#### Step 1.3: local_paths.py 路径统一

**审计所有硬编码路径**（已知有 ~10 处）：

| 文件 | 硬编码路径 | 改为 |
|:-----|:----------|:-----|
| `collect_homepage_info.py:23-27` | `Path.home() / "workbuddy-agent-os"` | `local_paths.data_path()` |
| `collect_batch_runner.py:27-32` | 同上 | 同上 |
| `xiaohongshu_login.py:34-35` | 同上 | 同上 |
| `camoufox_manager.py` | 同上 | 同上（若归档则跳过） |
| 其他... | 扫描所有 .py 文件 | 逐个修改 |

#### Step 1.4: 抖音采集加入登录检测

对标刚修复的小红书方案：

```python
# extract_douyin() 中，在导航到首页/个人页后
if not logged_in:
    from sms_login import sms_login  # 抖音 SMS 登录
    login_ok = await sms_login(page, phone=phone, ...)
    if login_ok: reload + retry
```

| 子任务 | 预计 |
|:-------|:-----|
| 1.4a 检查 `sms_login.py` 是否有独立的 login 函数（类似 xhs_login） | 15min |
| 1.4b 在 `extract_douyin()` 中加入登录检测 → 自动登录 | 1h |
| 1.4c 端到端测试 | 30min |

---

### Phase 2: Dashboard 前端重构

#### Step 2.1: Vite HMR 开发模式稳定

**现状**: frontend/ 已有 Vite 项目，33 个视图已迁移为 ES Module。但 Dashboard 直接服务 `static/index.html`（内联代码），Vite 前端尚未接入。

**需要解决的问题**:
| 问题 | 当前状态 | 修复方案 |
|:-----|:---------|:---------|
| Dashboard 使用 `static/index.html`（内联 7700 行） | 正常运行但无法 HMR | 保持现状，Vite 构建产物覆盖 static/ |
| Vite 前端 (`frontend/`) 的视图是迁移版但功能可能不全 | 33 个 .js 文件 | 逐个验证功能 |
| ExecutionPipeline 在 Vite 版中需要从 ES Module 加载 | 已内联到 index.html | 迁移到 `components/execution-pipeline.js` |

**正确的接入方式**:
1. 开发时: `cd frontend && npm run dev` → `localhost:5173/static/` → 有 HMR
2. 部署时: `cd frontend && npm run build` → 输出到 `../static/` → Dashboard 直接服务

#### Step 2.2: 迁移视图对接新 API

确保所有视图的按钮使用 `ExecutionPipeline.run()` + `POST /api/ops/run`：

| 视图 | 当前 API | 目标 API | 预计 |
|:-----|:---------|:---------|:-----|
| 养号执行 | `/api/ops/run` | ✅ 已对接 | — |
| 信息采集 | `/api/ops/run` | ✅ 已对接 | — |
| 登录管理 | `/api/ops/run` | ✅ 已对接 | — |
| 定向评论 | `/api/ops/run` | ✅ 已对接 | — |
| 收藏点赞 | `/api/ops/run` | ✅ 已对接 | — |
| 联邦指挥台 | `/api/ops/run` | ✅ 已对接 | — |

#### Step 2.3: 构建产物部署

```bash
cd frontend
npm run build    # → 输出到 ../static/
# 验证 Dashboard localhost:9988 正常服务
# 三机同步: fleet_sync.sh
```

#### Step 2.4: 旧 index.html 退役

当 Vite 构建产物稳定后：
1. 重命名 `static/index.html` → `static/index_legacy.html`（备份）
2. Vite 构建的 `static/index.html` 成为主文件
3. 保留回滚能力（`index_legacy.html` 可恢复）

---

### Phase 3: agentos → 全线贯通

#### Step 3.1: mc 全部命令迁移到 agentos

| mc 命令 | → agentos | 迁移状态 |
|:--------|:----------|:---------|
| `mc run` | `agentos matrix run` | ⬜ 待迁移 |
| `mc collect` | `agentos matrix collect` | ⬜ 待迁移 |
| `mc account` | `agentos matrix account` | ⬜ 待迁移 |
| `mc smart-login` | `agentos matrix login` | ⬜ 待迁移 |
| `mc account logout` | `agentos matrix logout` | ⬜ 待迁移 |
| `mc task comment` | `agentos matrix comment` | ⬜ 待迁移 |
| `mc task like` | `agentos matrix like` | ⬜ 待迁移 |
| `mc blueprint` | `agentos matrix blueprint` | ⬜ 待迁移 |
| `mc corpus` | `agentos matrix corpus` | ⬜ 待迁移 |
| `mc status` | `agentos fleet status` | ⬜ 待迁移 |
| `mc remote` | `agentos fleet exec` | ⬜ 待迁移 |
| `mc schedule` | `agentos serve schedule` | ⬜ 待迁移 |
| `mc proxy` | `agentos serve proxy` | ⬜ 待迁移 |
| `mc sms` | `agentos serve sms` | ⬜ 待迁移 |
| `mc record` | `agentos matrix record` | ⬜ 待迁移 |

#### Step 3.2: mc CLI 退役

- mc 入口输出: `⚠️ mc 已退役，请使用: agentos <domain> <command>`
- 保留 mc 脚本指向 agentos 的软链接（可选）

#### Step 3.3: 三机统一部署验证

| 检查项 | 验证方式 |
|:-------|:---------|
| 三机 agentos 版本一致 | `fleet_sync.sh` 同步后检查 |
| 三机 Python 环境一致 | `fleet_reconcile.sh` |
| 三机 Dashboard 正常启动 | 访问各机 :9988 |
| 远程执行链路正常 | 从本机发起到 5kecheng/7kecheng 的 collect 和 nurture |

---

### Phase 4: 联邦自治（长远目标）

| 步骤 | 说明 | 预计 |
|:-----|:------|:------|
| 4.1 智能体自动调度 | agentos 接收 AI 指令自动执行 | 未来 |
| 4.2 故障自愈 | guardd 检测到进程异常自动重启 | 未来 |
| 4.3 全链路监控 | 所有操作的状态/耗时/成功率可视化 | 未来 |

---

## 四、各阶段工作量预估

| Phase | 步骤数 | 预计工时 | 说明 |
|:------|:------|:---------|:------|
| **Phase 0** agentos 补全 | ~8 步 | **~8h** | 最高优先级，先做 |
| **Phase 1** 清理标准化 | ~6 步 | **~4h** | 与 Phase 0 并行 |
| **Phase 2** 前端重构 | ~4 步 | **~4h** | 可以后做，现有内联版能用 |
| **Phase 3** agentos 贯通 | ~3 步 | **~6h** | 依赖 Phase 0 完成 |
| **Phase 4** 联邦自治 | ~3 步 | 远期 | 前期不做 |
| | **总计** | **~22h** | |

---

## 五、风险和注意事项

| 风险 | 概率 | 影响 | 缓解措施 |
|:-----|:----|:------|:---------|
| agentos 开发中导致 mc 不稳定 | 低 | 高 | Step 0.3 的转发机制可降级回 mc |
| 归档文件被其他模块 import | 中 | 中 | 归档前 grep 全库检查引用 |
| Vite 构建产物破坏 Dashboard | 低 | 高 | 保留 index_legacy.html 回滚 |
| 远程机器同步延迟 | 中 | 低 | fleet_sync.sh 可手动触发 |

---

## 六、验收标准（全部完成时）

- [ ] `agentos matrix run|collect|login|logout|comment|like|blueprint|corpus` 全部可用
- [ ] `agentos fleet sync|reconcile|exec` 全部可用
- [ ] `agentos serve mcp|dashboard|schedule|proxy|sms` 全部可用
- [ ] `mc <any>` 全部指向 `agentos`（或直接提示退役）
- [ ] 废弃的 6 个文件全部归档，无引用断裂
- [ ] service 层无重复功能（remote_exec/operation_queue/resource_lock 归档）
- [ ] 所有硬编码路径改为 `local_paths.py`
- [ ] 抖音采集也有登录检测（对标小红书）
- [ ] Dashboard 通过 Vite 构建产物正常服务
- [ ] 三台机器都升级到同一版本，互操作正常

---

> **本路线图按 Phase 顺序执行。每完成一个 Step 打勾标记。**
> 
> 当前进度: ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ (0/15)

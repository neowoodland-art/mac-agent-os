# AgentOS 联邦架构 v3.0 — 完整蓝图

> **版本**: 3.0.0 | **更新**: 2026-06-17  
> **目标**: 统一三机联邦，每机智能体可独立运作，Dashboard 可统一指挥

---

## 一、系统架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                    用户入口层                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Web看板   │  │ 智能体   │  │ CLI终端   │  │ 定时任务     │ │
│  │ (SPA)    │  │ (AI)    │  │ (SSH)   │  │ (cron/task) │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘ │
└───────┼──────────────┼──────────────┼───────────────┼─────────┘
        │              │              │               │
┌───────▼──────────────▼──────────────▼───────────────▼─────────┐
│                    API 网关层 (FastAPI :9988)                   │
│                                                                │
│  /api/plugins/*    — 插件元信息                                 │
│  /api/identity     — 本机身份                                   │
│  /api/machines     — 联邦机器状态                               │
│  /api/health       — 健康检查                                   │
│  /api/matrix/*     — 矩阵养号全套 (accounts/nurture/blueprint)   │
│  /api/federation/* — 联邦远程操作 (nurture/exec/collect/login)  │
│  /api/machine/*    — 远程命令执行                                │
│  /api/push/*       — 心跳推送                                    │
└───────┬──────────────────────┬──────────────────┬──────────────┘
        │                      │                  │
┌───────▼────────┐   ┌─────────▼────────┐   ┌────▼──────────┐
│  本机执行       │   │  远程 SSH 执行    │   │  跨机数据聚合   │
│  subprocess    │   │  remote_exec.py  │   │  data_aggregtor│
│  mc run / mc ✅│   │  SSH → 远程 mc   │   │  HTTP拉取      │
└────────────────┘   └──────────────────┘   └───────────────┘
```

---

## 二、API 分层

### 2.1 插件层 (plugins/)

| 插件 | 职责 | API |
|:-----|:-----|:----|
| `guardd` | 联邦心跳/机器状态 | `/api/machines`, `/api/push/*` |
| `matrix` | 矩阵养号 | `/api/plugins/matrix/*` |
| `federation` | 联邦操作 | `/api/federation/*` |
| `scheduler` | 定时调度 | `/api/plugins/scheduler/*` |
| `sms_proxy_api` | 短信服务 | `/api/sms/*` |

### 2.2 路由层 (routes/)

| 路由 | 职责 | 端点 |
|:-----|:-----|:-----|
| `routes/matrix.py` | 账号管理+养号+蓝图+原子操作 | `/api/matrix/*` |

### 2.3 服务层 (services/)

| 服务 | 职责 |
|:-----|:-----|
| `remote_exec.py` | SSH远程执行引擎 |
| `data_aggregator.py` | 联邦数据聚合 |
| `operation_queue.py` | 操作队列 |
| `resource_lock.py` | 资源锁 |
| `preflight.py` | 前置检查 |
| `log_aggregator.py` | 日志聚合 |

---

## 三、视图完整清单 (25个)

| 导航组 | 视图 | 实现状态 | API 依赖 |
|:-------|:-----|:---------|:---------|
| **矩阵** | 账号管理 (`matrix-sms-proxy`) | ✅ 功能完整 | `/api/matrix/accounts` |
| | 养号执行 (`matrix-nurture`) | 🔧 近期修复 | `/api/matrix/nurture/start` |
| | 信息采集 (`matrix-collect`) | 🟡 待验证 | `/api/matrix/collect/*` |
| | 内容发布 (`matrix-publish`) | 🟡 待验证 | `/api/matrix/publish/*` |
| | 蓝图管理 (`matrix-blueprints`) | ✅ 功能完整 | `/api/matrix/blueprints` |
| | 定向评论 (`matrix-comment`) | 🟡 待验证 | `/api/matrix/comment/*` |
| | 定时任务 (`matrix-schedule`) | 🟡 待验证 | `/api/matrix/schedule/*` |
| | 语料库 (`matrix-corpus`) | 🟡 待验证 | `/api/matrix/corpus/*` |
| **视频工厂** | 渲染任务 (`ave-render`) | 🟡 待验证 | `/api/productions` |
| | 脚本生成 (`ave-script`) | 🟡 待验证 | `/api/characters` |
| | 素材库 (`ave-materials`) | 🟡 待验证 | `/api/assets/*` |
| | 模板 (`ave-templates`) | 🟡 待验证 | `/api/capabilities` |
| **内容采集** | 采集任务 (`crawl-tasks`) | 🟡 待验证 | `/api/crawl/*` |
| | 源管理 (`crawl-sources`) | 🟡 待验证 | `/api/crawl/*` |
| | 采集历史 (`crawl-history`) | 🟡 待验证 | `/api/crawl/*` |
| **联邦** | 机器状态 (`machines`) | ✅ 功能完整 | `/api/machines` |
| | 一键同步 (`fleet-sync`) | ✅ 功能完整 | `/api/git-sync` |
| | 对账检查 (`fleet-reconcile`) | 🟡 待验证 | `/api/fleet/reconcile` |
| | 远程Shell (`fleet-exec`) | 🟡 待验证 | `/api/machine/exec` |
| **服务** | MCP状态 (`serve-mcp`) | 🔴 未实现 | N/A |
| | Dashboard日志 (`serve-dashboard`) | 🟡 待验证 | N/A |
| | 全局定时任务 (`serve-schedule`) | 🔴 未实现 | N/A |

---

## 四、执行链路 (关键路径)

### 4.1 养号执行链路（已修复 ✅）

```
用户点击「执行选中」
  → nurtureExecSelected()              ← index.html JS
    → POST /api/matrix/nurture/start    ← routes/matrix.py
      → 自动选蓝图 + 路由到机器
        → 本机: subprocess mc run       ← local path
        → 远程: remote_exec exec_nurture ← SSH path
          → SSH → mc run                ← remote path
            → mc/engine.py              ← 身份分组+浏览器
              → cdp_connector.py        ← Camoufox
```

### 4.2 智能登录链路（待验证 ⚠️）

```
用户点击「登录」
  → POST /api/federation/login
    → remote_exec exec_login
      → SSH → mc smart-login {account_id}
        → douyin_login.py / xiaohongshu_login.py
```

### 4.3 信息采集链路（待验证 ⚠️）

```
用户点击「采集」
  → POST /api/federation/collect
    → remote_exec exec_collect
      → SSH → mc collect
```

---

## 五、三机统一环境

| 项目 | chengzigedeAir | 5kechengdeAir | 7kecheng |
|:-----|:--------------|:-------------|:---------|
| Python venv | agent-os ✅ | agent-os ✅ | agent-os ✅ |
| camoufox | 0.4.11 ✅ | 0.4.11 ✅ | 0.4.11 ✅ |
| playwright | 1.58.0 ✅ | 1.58.0 ✅ | 1.58.0 ✅ |
| Git版本 | cc04e9d93a | cc04e9d93a | cc04e9d93a |
| Dashboard | launchd ✅ | launchd ✅ | launchd ✅ |
| 身份目录 | phone_*命名 ✅ | phone_*命名 ✅ | phone_*命名 ✅ |
| 账号总数 | 30 (联邦聚合) | 30 (联邦聚合) | 30 (联邦聚合) |

---

## 六、任务优先级 (Phase 3 执行计划)

### P0 — 核心功能修复（本机优先）

| # | 任务 | 视图 | 预估 |
|:-:|:-----|:-----|:----|
| 1 | 养号执行端到端验证：API→mc run→浏览器→执行 | matrix-nurture | ✅ DONE |
| 2 | 账号管理视图修复：编辑/删除/状态显示 | matrix-sms-proxy | 1h |
| 3 | 蓝图管理视图修复：增删改+编排 | matrix-blueprints | 1h |
| 4 | 信息采集端到端：触发→执行→结果回显 | matrix-collect | 2h |
| 5 | 智能登录端到端：从看板触发远程登录 | federation | 2h |

### P1 — 联邦功能

| # | 任务 | 视图 | 预估 |
|:-:|:-----|:-----|:----|
| 6 | 远程执行路由：本机/远程账号智能分发 | 全部矩阵视图 | 2h |
| 7 | 执行结果回显：进度条+日志流 | matrix-nurture | 2h |
| 8 | 联邦定时任务：跨机定时执行 | serve-schedule | 3h |

### P2 — 完善

| # | 任务 | 视图 | 预估 |
|:-:|:-----|:-----|:----|
| 9 | 语料库管理 | matrix-corpus | 2h |
| 10 | 定向评论 | matrix-comment | 2h |
| 11 | 远程Shell | fleet-exec | 1h |
| 12 | 对账检查可视化 | fleet-reconcile | 1h |

# Dashboard 数据层 · 多智能体协同设计

> 版本: v1.0 | 2026-05-15
> 定位: AgentOS 多智能体系统 · 共享观测层

---

## 一、定位：不是 AVE 的面板，是 AgentOS 的观测层

Dashboard 不是 AVE 的附属工具。它应该是一套**跨智能体的共享数据服务**，任何 Agent（Claw、AVE、Matrix、Trae 等）都可以通过统一接口写入和查询。

### 现存 Agent 一览

| Agent | 目录 | 适合 Dashboard 跟踪什么 |
|:------|:-----|:------------------------|
| **09_ave** | `05_tools/09_ave/` | 视频生产任务、素材生成、API 调用 |
| **07_matrix** | `05_tools/07_matrix/` | 抖音养号任务、蓝�运行、账号切换 |
| **claw assistant** | `~/.workbuddy/` | 各种自动化任务、CLI 执行的历史 |
| **02_browser / 05_crawl** | `05_tools/` | 爬虫任务、页面采集记录 |

---

## 二、存储位置

根据 AgentOS 的目录结构约定：

| 类别 | 路径 | 说明 |
|:----|:-----|:------|
| **代码（可同步）** | `~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard/` | 多机共享，坚果云同步 |
| **数据（本地）** | `~/workbuddy-agent-os/agent-local/runtime/dashboard/` | 本地 SQLite + 缓存，不同步 |
| **客户端库** | `~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard/client.py` | Agent 导入用，写数据入口 |
| **后端服务** | `~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard/server.py` | FastAPI 应用 |
| **前端页面** | `~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard/templates/` | HTML 单页应用 |

**为什么数据放 `agent-local` 而不是 `agent-sync`？**
- SQLite 不适合坚果云同步（并发写会导致 DB 损坏）
- 每台机器的生产数据天然不同，不应该同步
- `agent-local/runtime/` 已经是 AgentOS 为"运行时数据"预设的位置

---

## 三、多智能体数据模型

### 3.1 agents — 智能体注册表

```sql
CREATE TABLE agents (
    id TEXT PRIMARY KEY,        -- 'ave', 'matrix', 'claw', 'trae'
    name TEXT NOT NULL,         -- 'audio score video engine'
    type TEXT DEFAULT 'tool',   -- 'tool' | 'skill' | 'pipeline' | 'assistant'
    version TEXT,               -- 当前版本号
    status TEXT DEFAULT 'active',
    last_seen_at TEXT,           -- 最后心跳时间
    meta_json TEXT               -- 扩展元数据
);
```

预注册的 Agent：

| id | name | type |
|:---|:-----|:-----|
| `ave` | AudioScore Video Engine | tool |
| `matrix` | Matrix Account Manager | tool |
| `claw` | Claw AI Assistant | assistant |
| `memory` | Memory Manager | skill |

### 3.2 productions — 生产任务（跨 agent 通用）

这是核心表。**不限于视频生产**——任何 agent 的"一次任务执行"都是一条 production。

```sql
CREATE TABLE productions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL REFERENCES agents(id),
    pipeline TEXT NOT NULL,            -- 'ave:oral' | 'ave:beat-sync' | 'matrix:browse' | 'claw:research'
    status TEXT DEFAULT 'running',     -- 'running' | 'completed' | 'failed' | 'cancelled'
    title TEXT,                        -- 人类可读名称
    input_summary TEXT,                -- JSON: 输入概览
    output_summary TEXT,               -- JSON: 输出概览
    config_json TEXT,                  -- JSON: 完整参数快照
    duration_sec REAL,
    total_cost REAL DEFAULT 0.0,
    currency TEXT DEFAULT 'CNY',
    error_message TEXT,
    tags TEXT,                         -- 逗号分隔，跨 agent 搜索用
    created_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE INDEX idx_productions_agent ON productions(agent_id);
CREATE INDEX idx_productions_status ON productions(status);
CREATE INDEX idx_productions_created ON productions(created_at);
```

### 3.3 production_steps — 步骤级跟踪

```sql
CREATE TABLE production_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_id INTEGER REFERENCES productions(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    step_name TEXT NOT NULL,           -- 'parse_script' | 'tts' | 'kling_generate' | ...
    step_type TEXT DEFAULT 'process',  -- 'process' | 'api_call' | 'human_review' | 'decision' | 'wait'
    status TEXT DEFAULT 'pending',
    input_ref TEXT,                    -- 输入引用（文件路径 / URL）
    output_ref TEXT,                   -- 输出引用
    started_at TEXT,
    ended_at TEXT,
    duration_sec REAL,
    cost REAL DEFAULT 0.0,
    detail TEXT,                       -- 步骤详情 JSON
    error_message TEXT,
    metadata_json TEXT                 -- 扩展字段
);

CREATE INDEX idx_steps_production ON production_steps(production_id);
```

### 3.4 assets — 跨 agent 共享资产

所有 agent 生成的、可复用的数字资产统一注册在这里。**关键设计**：资产一旦注册，就属于全局资产池，任何 agent 都可以引用。

```sql
CREATE TABLE assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_type TEXT NOT NULL,          -- 'character_sheet' | 'bgm' | 'generated_clip' | 'script' | 'lora' | 'screenshot' | 'dataset'
    name TEXT,
    description TEXT,
    file_path TEXT,                    -- 本地绝对路径
    file_size INTEGER,
    file_hash TEXT,                    -- SHA256，用于去重
    source_agent TEXT REFERENCES agents(id),
    source TEXT,                       -- 'generated' | 'imported' | 'downloaded' | 'user_provided' | 'pexels'
    license TEXT,                      -- 版权信息
    meta_json TEXT,                    -- JSON: 资产元数据
    tags TEXT,                         -- 逗号分隔
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(file_hash)
);

CREATE INDEX idx_assets_type ON assets(asset_type);
CREATE INDEX idx_assets_source ON assets(source_agent);
```

### 3.5 production_assets — 资产使用记录

```sql
CREATE TABLE production_assets (
    production_id INTEGER REFERENCES productions(id) ON DELETE CASCADE,
    asset_id INTEGER REFERENCES assets(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'input',         -- 'input' | 'output' | 'intermediate' | 'reference'
    PRIMARY KEY (production_id, asset_id)
);
```

### 3.6 agent_events — 智能体间事件总线

这是**跨智能体通信**的关键设计。一个 agent 完成某项任务后，可以通过事件通知其他 agent。

```sql
CREATE TABLE agent_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_agent TEXT REFERENCES agents(id),
    target_agent TEXT,                 -- null = broadcast 给所有 agent
    event_type TEXT NOT NULL,          -- 'production.completed' | 'asset.created' | 'pipeline.ready' | 'error.occurred'
    severity TEXT DEFAULT 'info',      -- 'info' | 'warning' | 'error' | 'critical'
    title TEXT,
    payload_json TEXT,                 -- 事件负载 JSON
    status TEXT DEFAULT 'pending',     -- 'pending' | 'read' | 'acknowledged'
    created_at TEXT DEFAULT (datetime('now')),
    read_at TEXT
);

CREATE INDEX idx_events_target ON agent_events(target_agent);
CREATE INDEX idx_events_status ON agent_events(status);
CREATE INDEX idx_events_created ON agent_events(created_at);
```

### 3.7 ER 关系

```
agents ──1:N── productions ──1:N── production_steps
  │                 │
  │                 └── M:N ── assets (via production_assets)
  │
  └──1:N── agent_events (source)
       └──?:1── agent_events (target)
```

---

## 四、客户端库设计

每个 Agent 通过 `client.py` 写入，不需要直接操作 SQLite。这是**唯一**的写入口。

```python
# ~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard/client.py

"""
Dashboard Client — 供所有 Agent 调用

用法:
    from dashboard_client import DashboardClient
    db = DashboardClient()  # 自动连接 agent-local/runtime/dashboard/ave.db

    # 注册自己
    db.register_agent("ave", "AudioScore Video Engine", "tool")

    # 开始一个 production
    prod_id = db.start_production(
        agent_id="ave",
        pipeline="ave:oral",
        title="知识讲座视频 #047",
        config={"script": "lecture.yaml", "style": "knowledge_lecture"}
    )

    # 记录步骤
    db.log_step(prod_id, "tts", "completed", cost=0.30, detail={"chars": 85})
    db.log_step(prod_id, "render", "completed", cost=0.0)

    # 注册资产
    asset_id = db.register_asset(
        asset_type="generated_clip",
        name="clip_hermit_01.mp4",
        file_path="/tmp/kling_hermit.mp4",
        source_agent="ave",
        tags=["kling", "hermit", "cinematic"]
    )

    # 关联资产到 production
    db.link_asset(prod_id, asset_id, role="output")

    # 完成 production
    db.complete_production(prod_id, status="completed", total_cost=1.20)

    # 发送事件通知
    db.send_event("ave", "claw", "production.completed",
                  title="视频 #047 生成完成", payload={"prod_id": prod_id})
```

### 核心 API

| 方法 | 功能 | 被调用频率 |
|:-----|:-----|:----------|
| `register_agent(id, name, type)` | 注册/更新 agent | 安装时一次 |
| `start_production(...)` | 开始任务 | 每次 CLI 执行 |
| `log_step(...)` | 记录步骤 | 每个步骤 |
| `update_step(...)` | 更新步骤状态 | 异步步骤 |
| `complete_production(...)` | 完成任务 | 每次完成/失败 |
| `register_asset(...)` | 注册资产 | 每个新文件 |
| `link_asset(prod, asset, role)` | 关联资产 | 每次资产使用 |
| `send_event(source, target, type, ...)` | 发送事件 | 按需 |

---

## 五、后端 API 设计

FastAPI 服务，运行在 `http://localhost:9132`。

### 核心端点

```
GET  /api/status                    # 服务健康检查
GET  /api/summary                   # 总览指标（总数、本月、总成本、资产数）

GET  /api/productions               # 生产列表（支持 filter: ?agent=&status=&pipeline=&tags=）
GET  /api/productions/{id}          # 生产详情 + 步骤列表
GET  /api/productions/{id}/assets   # 生产关联的资产

GET  /api/assets                    # 资产列表（支持 filter: ?type=&agent=&tags=&q=）
GET  /api/assets/{id}               # 资产详情 + 使用记录
GET  /api/assets/{id}/productions   # 该资产被哪些 production 用过

GET  /api/agents                    # agent 列表
GET  /api/agents/{id}/productions   # 某个 agent 的所有 production

GET  /api/events                     # 事件列表
GET  /api/events?target={agent_id}  # 发给某个 agent 的事件

GET  /api/costs                     # 费用汇总（按 agent/策略/时间分组）
```

### 查询示例

```
# 查看 AVE 最近失败的 production
GET /api/productions?agent=ave&status=failed

# 搜索资产
GET /api/assets?q=定妆照&type=character_sheet

# 查看 matrix 本周的全部任务
GET /api/productions?agent=matrix&from=2026-05-08&to=2026-05-15
```

---

## 六、集成方式

### 6.1 AVE 集成（Sprint 1 要做）

在 `main.py` 的每个关键节点加 ~50 行调用。改动量极小：

```python
# 在 video_factory.py 的入口
from dashboard_client import DashboardClient
db = DashboardClient()

# run_oral() 开始
prod_id = db.start_production("ave", "ave:oral", title, config=args)

# TTS 步骤完成
db.log_step(prod_id, "tts", "completed", cost=0.30)

# 素材搜索完成
db.log_step(prod_id, "search_material", "completed", detail={"count": 6})

# 合成完成
db.complete_production(prod_id, status="completed", total_cost=tracker.total)
```

### 6.2 Matrix 集成（Sprint 3 可选）

```python
# 在 task_engine.py 的入口
prod_id = db.start_production("matrix", "matrix:browse", "抖音浏览 #102")
db.log_step(prod_id, "switch_account", "completed")
db.log_step(prod_id, "open_douyin", "completed")
db.log_step(prod_id, "browse_videos", "completed", detail={"count": 15})
db.complete_production(prod_id, status="completed")
```

### 6.3 Claw Assistant 集成（Sprint 3 可选）

通过 WorkBuddy 的 CLI 埋点，每次执行自动化任务自动记录。

---

## 七、数据生命周期

| 阶段 | 操作 | 位置 |
|:-----|:-----|:------|
| **创建** | `client.py` 写入 | `agent-local/runtime/dashboard/ave.db` |
| **读取** | HTTP API → 前端 Dashboard | FastAPI + HTML |
| **备份** | 随 agent-local 整体备份策略 | 暂不单独处理 |
| **清理** | >90 天的 production 自动归档 (可配置) | 归档到 `agent-local/runtime/dashboard/archive/` |
| **跨机迁移** | 不同步。每台机器独立数据 | `agent-local` 不同步的设计 |

---

## 八、文件结构

```
agent-sync/05_tools/10_dashboard/
├── __init__.py
├── client.py              # Agent 客户端库（唯一写入口）
├── models.py              # SQLAlchemy ORM 或 raw SQL schema
├── server.py              # FastAPI 应用
├── templates/
│   ├── index.html         # 总览页
│   ├── productions.html   # 生产列表
│   ├── detail.html        # 生产详情
│   └── assets.html        # 资产浏览器
├── static/
│   └── app.js             # 前端交互逻辑
└── README.md              # 使用说明

agent-local/runtime/dashboard/
├── ave.db                 # SQLite 主数据库
├── cache/                 # 文件缓存
└── archive/               # 历史归档
```

---

## 九、为什么这样设计

### 9.1 为什么用 SQLite 而不是其他 DB？

| 数据库 | 适用性 | |
|:-------|:-------|:-|
| SQLite | ✅ 单机多进程读、零运维、AgentOS 已有使用 | **选这个** |
| PostgreSQL | ❌ 太重，单机不需要 |
| JSON 文件 | ❌ 不支持并发写、不支持查询 |
| LevelDB/RocksDB | ❌ 没 SQL 查询，不支持关联 |

### 9.2 为什么用 HTTP API 而不是直接写 SQLite？

| 方式 | 问题 |
|:-----|:-----|
| 直接写 SQLite | 每个 agent 都要 import sqlite3 + 写 SQL，产生代码耦合 |
| 通过 API | agent 只需 import client.py + 调方法，后端封装所有 DB 逻辑 |

### 9.3 为什么 events 表放在这里而不是单独的消息队列？

轻量。当前多智能体在同一台机器上，SQLite 轮询足够。如果以后需要跨机器，可以从 events 表迁移到真正的消息队列（如 Redis pub/sub）。

---

## 十、开发量估算

| 模块 | 估计 | 说明 |
|:-----|:----:|:------|
| `models.py` (schema) | 0.2h | SQL 建表语句 |
| `client.py` (核心 6 个方法) | 1h | ~150 行 Python |
| `server.py` (API 端点) | 1h | ~200 行 FastAPI |
| AVE 埋点接入 | 0.5h | main.py + video_factory.py 加 ~50 行 |
| **合计** | **~2.7h** | 一个下午可完成 |

# AVE Dashboard — 生产监控面板方案设计

> 版本: v1.0-draft | 2026-05-15
> 状态: 概念设计

---

## 一、需求还原

你的诉求：

> "在一个页面里，能全方位看到生产线的进度和进展，追溯历史、查询资产（BGM、素材、定妆照、生成片段等），看到一条视频产线的全流程回溯，能复用、能修正、能定位问题，还能跟踪成本和付费历史。"

**一句话**：一个 AVE 的"生产管理后台"，把 CLI 的黑盒操作变成可视化的透明产线。

---

## 二、价值评估

### 2.1 解决了什么核心问题

| 问题 | 现状 | Dashboard 解决 |
|:----|:----|:--------------|
| **产线不可视** | CLI 跑完才知道结果 | 实时看进度、每步状态 |
| **无法追溯** | 不知道哪次用了哪个 BGM/素材 | 每条 production 关联所有输入输出 |
| **无法复用** | 想重跑类似配置要手动记参数 | 一键 re-run / clone |
| **费用失控** | 跑完才知道花了多少钱 | 实时累计 + 单步成本分解 |
| **故障定位慢** | 出错了要翻终端日志 | 红点 + 错误详情 + 重试按钮 |
| **素材管理散** | 文件散落在 cache、output、tmp 里 | 统一索引 + 标签 + 搜索 |

### 2.2 投入产出分析

| 维度 | 评估 |
|:----|:-----|
| **工程量** | 中等（~1.5天：0.5天数据层 + 0.5天后端 + 0.5天前端） |
| **长期收益** | 极高——每次生产都自动记录，解决了"不可追溯、不可复用"的根本问题 |
| **风险** | 低——数据层是增量添加，不影响现有 CLI 运行 |
| **是否阻塞 P0** | 否——可以和 P0 平行开发 |

**结论：应该做，但不是立即做。建议在 P0/P1 核心功能完成后，作为 P2 的基石模块启动。**

---

## 三、架构设计

### 3.1 整体架构

```
现有AVE CLI                              新 Dashboard
──────────                               ──────────
main.py                                  ave_dashboard/
  ├── video-factory                         ├── app.py (FastAPI 后端)
  ├── beat-sync                             ├── templates/
  ├── digital-human                         │   └── dashboard.html (前端页面)
  └── ...                                   └── static/
       │                                        └── app.js
       │ 自动写DB
       ▼
  ┌─────────────────────────┐
  │  SQLite: data/ave.db   │ ◄──── FastAPI 读取 + API
  └─────────────────────────┘
```

### 3.2 数据模型（SQLite）

```sql
-- 生产记录（每次运行一条）
CREATE TABLE productions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy        TEXT NOT NULL,       -- 'oral' | 'beat-sync' | 'digital-human' | 'story'
    status          TEXT DEFAULT 'running', -- 'running' | 'completed' | 'failed'
    script_path     TEXT,
    script_name     TEXT,
    output_path     TEXT,
    duration_sec    REAL,
    total_cost      REAL DEFAULT 0.0,
    config_json     TEXT,                -- 完整的 CLI 参数 JSON
    error_message   TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    completed_at    TEXT
);

-- 生产步骤（每个 production 的每一步）
CREATE TABLE production_steps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    production_id   INTEGER REFERENCES productions(id),
    step_name       TEXT NOT NULL,       -- 'parse_script' | 'tts' | 'search_material' | ...
    status          TEXT DEFAULT 'pending', -- 'pending' | 'running' | 'completed' | 'failed'
    started_at      TEXT,
    ended_at        TEXT,
    duration_sec    REAL,
    cost            REAL DEFAULT 0.0,
    detail          TEXT,                -- 步骤详情（如素材数、字数等）
    error_message   TEXT
);

-- 资产注册表（所有可复用的数字资产）
CREATE TABLE assets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_type      TEXT NOT NULL,       -- 'character_sheet' | 'bgm' | 'generated_clip' | 'script' | 'lora' | 'pexels_cache'
    name            TEXT,
    file_path       TEXT,
    file_size       INTEGER,
    hash            TEXT,                -- 文件哈希，用于去重
    source          TEXT,                -- 'pexels' | 'kling' | 'user_upload' | 'generated'
    meta_json       TEXT,                -- 元数据（BPM, mood, segment_count 等）
    production_id   INTEGER,             -- 从哪次 production 产生的
    created_at      TEXT DEFAULT (datetime('now'))
);

-- 资产标签
CREATE TABLE asset_tags (
    asset_id    INTEGER REFERENCES assets(id),
    tag         TEXT NOT NULL,
    PRIMARY KEY (asset_id, tag)
);

-- 资产-生产关联（一个 production 用了哪些资产）
CREATE TABLE production_assets (
    production_id   INTEGER REFERENCES productions(id),
    asset_id        INTEGER REFERENCES assets(id),
    role            TEXT,                -- 'input' | 'output' | 'intermediate'
    PRIMARY KEY (production_id, asset_id)
);
```

### 3.3 集成方式（对现有 CLI 的改动）

**改动极小**——只需要在 `main.py` 和 `video_factory.py` 的每个关键节点加一行：

```python
from lib.dashboard import log_production, log_step, log_asset

# 在 production 开始时
prod_id = log_production(strategy="口播", config=args)

# 在每步结束时
log_step(prod_id, step_name="tts", status="completed", cost=0.30, detail="85 字符")

# 在生成资产时
log_asset(prod_id, type="generated_clip", path="/tmp/clip.mp4", tags=["hermit", "kling"])
```

现有代码量 3000+ 行，新增约 **50 行埋点** 即可。不需要改现有逻辑。

### 3.4 Dashboard 功能清单

| 板块 | 功能 |
|:----|:-----|
| **总览卡片** | 总产量、本月产量、累计费用、资产总数 |
| **生产列表** | 按时间倒叙、按策略/状态筛选、搜索 |
| **生产详情** | 每步状态+耗时+费用、输入输出资产列表、输出视频预览 |
| **资产浏览器** | 按类型/标签筛选、搜索、预览、查看被哪些 production 使用 |
| **重复利用** | re-run（同配置）、clone as new（修改配置再跑） |
| **费用分析** | 按策略/按时间/按单步的费用分解图 |
| **失败追踪** | 失败 production 列表、错误详情、重试按钮 |

---

## 四、与现有规划的关系

### 4.1 优先级定位

```
P0 (Sprint 1) ─── 定妆照 + Kling LipSync + Schema 扩展
  │
P1 (Sprint 2) ─── 变速卡点 + 节拍升级
  │
P2 (Sprint 3) ─── 角色叙事 + LatentSync + 资产管理
  │                    ↑
  └── Dashboard ───────┘ ← 建议和 Sprint 3 一起做
```

**理由**：
- P0 和 P1 是核心功能增强，应该优先
- Dashboard 的**数据层**可以和 P0 并行搭（半天）
- Dashboard 的**前端**等到 Sprint 3 再做，那时资产管理和角色叙事也需要界面，一次性写完整

### 4.2 依赖关系

| 依赖 | 说明 | 是否阻塞 |
|:----|:-----|:--------:|
| P0 完成 | Dashboard 不依赖任何 P0 功能 | ❌ 不阻塞 |
| 资产索引 | Dashboard 的资产浏览器依赖 asset_manager 模块 | ⚠️ 建议 asset_manager 先搭 |
| CLI 埋点 | 需要在 main.py 加 ~50 行 log 调用 | ✅ 半天可完成 |

### 4.3 分步交付

| 阶段 | 内容 | 交付物 | 时间 |
|:----|:-----|:------|:----:|
| **Phase 1** (和P0平行) | DB schema + 埋点 + 后端 API | `data/ave.db`, `lib/dashboard.py`, `app.py` | 0.5天 |
| **Phase 2** (P2开始时) | 前端页面 V1: 生产列表+详情+费用 | `dashboard.html` | 0.5天 |
| **Phase 3** (资产管理器完成) | 资产浏览器 + 搜索 + 复用 | 前端更新 | 0.5天 |

---

## 五、我自问自答的几个问题

### 这会不会变成一个沉重的 Web 项目？

**不会。** 设计原则是"轻量 + 可摘除"：
- 后端用 FastAPI（Python 自带，AVE 不需要新依赖）
- 前端用单 HTML 页面（Vue.js CDN 或原生 JS，不构建）
- 数据用 SQLite（零运维）
- 所有新增代码放在 `scripts/lib/dashboard.py` 一个文件
- 如果以后不需要，删掉这个文件 + 前端目录即可

### CLI 用户会不会受影响？

**不会。** Dashboard 是增量添加。所有埋点都是 `try/except` 包起来的——如果 DB 写失败，CLI 继续运行，不报错。

### 值不值得在开发核心功能之前做？

**不值得先做。** 但值得在核心功能开发的同时**搭好数据层**。数据层（DB schema + 埋点）只需要半天，埋完后 CLI 自动积累数据。前端可以在任何时候再写——数据已经在那里了。

---

## 六、建议方案

> **做。但分步做。**

| 时机 | 做什么 | 原因 |
|:----|:------|:-----|
| **现在** (和定妆照+P0平行) | 搭 DB schema + CLI 埋点 | 半天工作量, 数据开始积累 |
| **P1 完成后** (也就是1-2天内) | 写后端 API + 前端 V1 | 那时已经有几十条 production 数据了, 面板直接有内容 |
| **资产管理器完成后** | 前端 V2 加上资产浏览器 | 资产管理器的索引+Dashboard 的展示天然互补 |

**要不要**这个功能？——**要**。

**什么时候做？**——建议从明天开始搭数据层（0.5天），前端等有数据了再写。这样既不影响 P0/P1 的开发节奏，又能在 1-2 天内看到 Dashboard 的效果。

如果确认要做，我可以：
1. 先创 SQLite schema 文件
2. 在 `main.py` 和 `video_factory.py` 加埋点
3. 搭好 FastAPI 后端骨架

等你决定 P0 从哪步开始后，Dashboard 数据层可以同步启动。

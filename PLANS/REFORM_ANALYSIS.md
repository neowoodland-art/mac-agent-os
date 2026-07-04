# 改造分析报告：现状 vs 目标架构

> 日期: 2026-07-04 | 基于 `PLANS/TASK_ORCHESTRATION_ARCHITECTURE.md`
> 审计范围: 全部 7 个模块，逐项检查

---

## 一、改造项总览

| # | 模块 | 改造类型 | 优先级 |
|:-:|:-----|:---------|:-------|
| 1 | `scheduler.py` | 🔧 **重写** — 现有逻辑不满足需求 | P0 |
| 2 | `priority_queue.py` | ✅ **不动** — 现有类直接可用 | - |
| 3 | `command_bus.py` | 🆕 **新增** smart_comment 类型 | P1 |
| 4 | `video_analyzer.py` | 🆕 **新建** — 不存在 | P1 |
| 5 | `corpus.py` | 🔧 **改造** — 加行业过滤 + 万能兜底 | P1 |
| 6 | `douyin.yaml` | 🔧 **重构** — 语料分层 | P1 |
| 7 | `profiles.json` | 🔧 **补字段** — 加 industry | P2 |
| 8 | `ops-command.js` | 🆕 **加功能** — 三队列显示 | P3 |

---

## 二、逐项分析

---

### 改造项 1：`scheduler.py` — 🔧 重写

**当前代码**（`guardd/modules/scheduler.py:33-362`）：

当前是单队列模式：
```python
class Scheduler:
    def __init__(self):
        self.queue = PriorityQueue()        # ← 一个队列装所有优先级
        self.active_tasks: dict[int, dict]  # {slot_id: task}
        self.paused_tasks: dict[int, dict]
```

| 功能点 | 现状 | 目标 | 问题 |
|:-------|:-----|:-----|:-----|
| 队列数量 | **1 个** 混装所有优先级 | **3 个** 独立队列(P0/P1/P2) | ❌ P0不能插队，P2不能填空 |
| `_pop_next_task()` | 遍历所有任务，按`(priority, scheduled_at)`排序后取第一个 | 先看P0→再看P1→再看P2，且跳过 busy 账号 | ❌ 无法实现优先级隔离 |
| 账号互斥 | slot_manager.find_account() 在分配时检查 | 三层检查：入队时+分配时+执行前 | ❌ 入队层不检查，可能重复入队 |
| 账号状态表 | 无 | `account_slots: dict[str, int]` | ❌ 没有快速查询账号状态的能力 |
| P0 抢占 | 无 | 当前任务结束后插队 | ❌ 完全未实现 |
| P2 劣后 | 无 | 只在空闲时执行，可被抢占 | ❌ 完全未实现 |
| 暂停任务暂存 | `paused_tasks` 存在但不被 active 使用 | P0插入时暂停P1，完成后恢复 | ❌ 逻辑不完整 |

**改造原因**：当前逻辑是**功能错误的**。三个优先级的任务混在一个队列里，虽然排序时按 priority 字段，但 `_pop_next_task` 取完第一个任务后就 break 了，不会继续往后看。当高优任务 due 时间还没到时（`scheduled_at > now`），堆顶返回 None，整个调度循环就停了。这导致 P0 任务无法真正插队。

**改动量**：~200行，重写 `Scheduler` 类。

---

### 改造项 2：`priority_queue.py` — ✅ 不动

**当前代码**（`guardd/modules/priority_queue.py:1-79`）：

```python
class PriorityQueue:
    """基于 heapq 实现，支持优先级排序 + 时间调度 + 取消/重排"""
```

当前实现完全满足需求。三队列只需创建三个独立实例：
```python
self.queue_priority = PriorityQueue()  # P0
self.queue_normal   = PriorityQueue()  # P1
self.queue_filler   = PriorityQueue()  # P2
```

无需修改此类。

---

### 改造项 3：`command_bus.py` — 🆕 新增 smart_comment

**当前代码**（`services/command_bus.py:807-842`）：

```python
CMD_REGISTRY = {
    "nurture": {...},
    "collect": {...},
    "login": {...},
    "logout": {...},
    "comment": {...},
    "like": {...},
    "interact": {...},
    "record": {...},
}
```

| 功能点 | 现状 | 目标 | 问题 |
|:-------|:-----|:-----|:-----|
| 评论类型 | `comment` / `interact` — 直接传 `mc task comment` | + `smart_comment` — 先分析视频再评论 | ❌ 缺少视频分析环节 |
| 分发逻辑 | 按机器分组后直接发到 guardd | 先调 VideoAnalyzer 分析所有URL，再分组分发 | ❌ 无分析环节 |

**改造原因**：**新功能需求**。现有 comment/interact 可以保留不变，新增 smart_comment 走新的视频分析流程。

**改动量**：~20行，加一条注册表 + dispatch 分支。

---

### 改造项 4：`video_analyzer.py` — 🆕 新建

**当前**：文件不存在。

**需要新建**一个完整的视频分析模块，包含：
- 浏览器打开 URL 提取标题/描述
- 关键词匹配行业分类
- 根据账号 industry 选评论

**改造原因**：**完全是新增功能**，原来是直接传评论或者随机取语料，现在需要先分析视频内容再做匹配。

**改动量**：~150行新文件。

---

### 改造项 5：`corpus.py` — 🔧 改造

**当前代码**（`scripts/mc/corpus.py:51-57`）：

```python
KEYWORD_CATEGORY_MAP = [
    (["科技", "数码", "手机"], ["称赞", "提问"]),
    (["美食", "做饭", "菜"], ["称赞", "共鸣"]),
    (["旅游", "风景", "旅行"], ["称赞", "提问"]),
    (["情感", "生活", "感悟"], ["共鸣", "安慰"]),
    (["知识", "科普", "教育"], ["提问", "补充"]),
]
```

| 功能点 | 现状 | 目标 | 问题 |
|:-------|:-----|:-----|:-----|
| 关键词覆盖 | **5组**（科技/美食/旅游/情感/知识） | **9+组**（加上医疗/财经/育儿/汽车等） | ❌ 无医疗关键词，健康类视频无法匹配 |
| 行业过滤 | 无 | 根据账号 industry 过滤语料 | ❌ 医疗账号可能发科技评论 |
| 万能兜底 | `_get_random_comment()` 全域随机 | 从万能池（称赞/提问/共鸣）取 | ❌ 没有万能池概念 |
| 分类→方向映射 | `DIRECTION_TO_CATEGORY` 5个 | 同步扩展 | ❌ 需要对齐 |

**改造原因**：**现有功能不完整**。关键词覆盖太窄，缺少行业过滤机制和万能兜底逻辑。

**改动量**：~50行，改 `KEYWORD_CATEGORY_MAP` + `get_comment_for_video()`。

---

### 改造项 6：`douyin.yaml` — 🔧 重构

**当前结构**（`corpus/douyin.yaml:239行`）：

```
categories:
  赞美:    (30条，通用)
  共鸣:    (15条，通用)
  提问:    (15条，通用)
  感慨:    (15条，通用)
  客观:    (10条，通用)
  补充:    (5条，通用)
```

| 功能点 | 现状 | 目标 | 问题 |
|:-------|:-----|:-----|:-----|
| 语料分层 | **平铺**，都在同一层 | **两层**：万能池 + 行业池 | ❌ 无法区分行业 |
| accessible 字段 | 无 | `accessible: "*"` 或 `accessible: ["health"]` | ❌ 无法限制账号使用 |
| match_tags 字段 | 无 | 每个行业池带关键词标签 | ❌ 无法自动匹配视频 |

**改造原因**：**结构设计不满足新需求**。需要按行业分层，加 accessible 和 match_tags 字段。

**改动量**：YAML 结构调整，将现有评论分类到"万能称赞""万能提问""万能共鸣"下，新增"大健康称赞"等行业池。

---

### 改造项 7：`profiles.json` — 🔧 补字段

**当前**（`profiles.json:344行`）：

```json
{
  "douyin_133": {"nickname":"苏州胃肠体检敏敏", ...},
  "douyin_test": {"nickname":"小美养生茶", ...},
}
```

没有一个账号有 `industry` 字段。

**改造原因**：**缺少关键数据**。没有 industry 字段，VideoAnalyzer 无法判断账号该用哪个语料池。

**改动量**：每个账号加一行 `"industry": "health"` 或 `"industry": "general"`，手动配置。

---

### 改造项 8：`ops-command.js` — 🆕 加功能

**当前代码**：

前端已有 P0/P1/P2 的 HTML 筛选 checkbox（第41-43行），但后台 scheduler 返回的队列数据中优先级是混在一起的，前端无法真正按优先级分类展示。

**改造原因**：**新功能需求**。后台改为三队列后，前端需要分开显示三个队列的长度+内容。

**改动量**：~80行，加三个队列的独立展示区域。

---

## 三、改造原因分类

| 类别 | 数量 | 项 |
|:-----|:-----|:----|
| ❌ **功能错误**（现有逻辑有问题） | 1 | scheduler.py — 单队列导致P0/P2无法正常工作 |
| ⚠️ **功能不完整**（有但不够） | 2 | corpus.py 关键词覆盖窄、douyin.yaml 无行业过滤 |
| 🆕 **新功能需求**（完全新增） | 4 | video_analyzer.py、command_bus smart_comment、profiles.json industry、ops-command三队列 |
| ✅ **无需修改** | 1 | priority_queue.py |

---

## 四、按 Phase 的改造详细清单

### Phase 1：队列改造（P0）

| 文件 | 当前行数 | 改动 | 原因 |
|:-----|:---------|:------|:------|
| `guardd/modules/scheduler.py` | 362行 | 重写：单队列→三队列 + 账号互斥表 + P0抢插 + P2填空 | ❌ 功能错误，当前单队列无法实现优先级隔离 |

### Phase 2：语料重组（P1）

| 文件 | 当前行数 | 改动 | 原因 |
|:-----|:---------|:------|:------|
| `corpus/douyin.yaml` | 239行 | 重构为万能池+行业池 | 🆕 新需求，需要按行业分层 |
| `scripts/mc/corpus.py` | 701行 | 扩展关键词 + 加行业过滤 + 万能兜底 | ⚠️ 关键词覆盖窄，缺少过滤 |
| `profiles.json` | 344行 | 各账号加 industry 字段 | 🆕 新需求，需要标记账号行业 |

### Phase 3：视频分析（P1）

| 文件 | 当前行数 | 改动 | 原因 |
|:-----|:---------|:------|:------|
| **新建** `services/video_analyzer.py` | 0 → ~150行 | 视频URL分析+分类+选评论 | 🆕 完全新增 |
| `services/command_bus.py` | 1289行 | CMD_REGISTRY 加 smart_comment | 🆕 新需求 |

### Phase 4：指挥台展示（P2）

| 文件 | 当前行数 | 改动 | 原因 |
|:-----|:---------|:------|:------|
| `frontend/views/ops-command.js` | 413行 | 三队列独立展示 | 🆕 新需求 |

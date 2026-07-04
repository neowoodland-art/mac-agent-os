# AgentOS 任务编排与调度架构 v1.0

> 版本: 1.0 | 日期: 2026-07-04 | 基于全部现有代码审计 + 需求讨论
> 前置阅读: `PLANS/SCHEDULER_ARCHITECTURE_v3.md`（调度引擎原始设计）
> 本文件替代: 旧版调度设计中的 Phase 2/3 部分，整合为新架构

---

## 一、设计目标

| 目标 | 说明 |
|:-----|:------|
| **评论与视频内容关联** | 评论不再随机，根据视频标题/标签匹配行业语料 |
| **账号行业隔离** | 大健康账号发健康评论，通用账号发通用评论，互不串 |
| **三优先级调度** | P0优先/P1日常/P2劣后，插队不中断浏览器 |
| **账号互斥** | 同一账号不能同时出现在两个浏览器 |
| **中央分析+远程执行** | Master统一做视频分析/分类/选评论，Worker只执行 |

---

## 二、最小任务单元

### 2.1 定义

```
最小任务单元 = {account_id, operation_type, params, machine, priority}
```

一个任务单元 = 一个账号 × 一次浏览器操作的组合，不可再拆。

### 2.2 任务类型

| operation_type | 说明 | 默认优先级 | 来源 |
|:---------------|:-----|:-----------|:-----|
| `smart_comment` | 智能评论（带视频分析+行业匹配） | P0 | Dashboard 提交 |
| `comment` | 定向评论（已有模式） | P0 | Dashboard / CLI |
| `nurture` | 日常养号 | P1 | 定时任务 / 手动 |
| `collect` | 信息采集 | P2 | 手动 / 定时 |
| `like` | 点赞互动 | P1 | 蓝图 |
| `login` | 登录（特殊，不走调度器） | - | 单独处理 |

### 2.3 任务状态

```
PENDING → QUEUED → RUNNING → COMPLETED
                     ↓           ↓
                  FAILED      CANCELLED
```

---

## 三、三层编排体系

### 3.1 系统分层

```
用户提交（Dashboard / API）
    │
    ▼
┌── L3: Master 中央编排 ──────────────────────────────┐
│  (chengzigedeAir)                                     │
│                                                        │
│  ① 接收任务（url列表 + 账号列表 + 操作类型）         │
│                                                        │
│  ② 视频分析（本机浏览器提取信息）                     │
│     ├─ 标题 / 描述 / 标签                             │
│     ├─ 关键词匹配 → 分类（医疗健康 / 通用）           │
│     └─ 从对应语料池选评论                             │
│                                                        │
│  ③ 拆解为最小单元                                     │
│     {douyin_133, comment, url, "医生讲得很清楚"}      │
│                                                        │
│  ④ 按机器打包                                         │
│     7kecheng → [5个单元]                              │
│     5kechengdeAir → [3个单元]                         │
│                                                        │
│  ⑤ POST /scheduler/submit → 各机 guardd              │
└────────────────────────────┬──────────────────────────┘
                             │ Tailscale
                             ▼
┌── L2: 各机 guardd 调度器 ──────────────────────────┐
│  (7kecheng / 5kechengdeAir)                          │
│                                                        │
│  收到大包 → 展开为独立任务                             │
│                                                        │
│  三队列管理:                                           │
│    P0 优先: 智能评论、定向操作（当前任务结束后插队）  │
│    P1 日常: 养号、点赞（FIFO 正常排队）               │
│    P2 劣后: 采集、同步（slot 空闲才执行）              │
│                                                        │
│  账号互斥守卫                                          │
│                                                        │
│  3 Slot 流水线                                         │
│    slot0: [P1→P1→P1]                                  │
│    slot1: [P1→P0→P1]  ← P0插队                        │
│    slot2: [P2→空闲→P2]  ← P2填空                      │
└──────────────────────────────────────────────────────┘
```

### 3.2 各程序职责

| 节点 | 程序 | 职责 |
|:-----|:------|:------|
| **Master** | CommandBus | 接收请求→拆解→按机器分组→分发 |
| **Master** | VideoAnalyzer 🆕 | 视频URL分析、行业分类、选评论 |
| **Master** | Dashboard API | 前端界面、健康监控 |
| **Worker** | guardd HTTP Server | 接收任务、返回状态 |
| **Worker** | Scheduler 🆕改 | 三队列管理、3 slot流水线、P0抢插、账号互斥 |
| **Worker** | Executor | 子进程执行（mc run / mc task comment） |
| **Worker** | SlotManager | 浏览器槽位管理、进程监控 |
| **Worker** | HeartbeatReporter | 每15秒上报slot/队列/账号状态到Dashboard |

---

## 四、三队列调度算法

### 4.1 队列结构

```python
class Scheduler:
    # 三个独立优先队列
    queue_priority = PriorityQueue()  # P0: 智能评论/定向操作
    queue_normal   = PriorityQueue()  # P1: 养号/点赞/日常
    queue_filler   = PriorityQueue()  # P2: 采集/同步/劣后

    # 3 条流水线
    active_tasks: dict[int, dict]     # {slot_id: task}
    
    # 账号互斥表
    account_slots: dict[str, int]     # {account_id: slot_id}
    
    # 被 P0 打断的 P1 任务暂存
    paused_tasks: dict[int, dict]     # {slot_id: task}
```

### 4.2 调度循环（每15秒）

```
run_cycle():
  step 1: 检查所有 slot
          任务完成 → 释放 slot + 从 account_slots 中移除账号
  
  step 2: 检查暂停队列
          有被 P0 打断的 P1 任务 → 放回日常队列恢复
  
  step 3: 分配空闲 slot
          for slot_id in [0, 1, 2]:
              if slot 正在运行: continue
              
              # 取当前活跃账号列表
              busy = set(account_slots.values())
              
              # 按优先级取任务（避开 busy 账号）
              task = pop_available(P0优先, P1日常, P2劣后)
              
              if task:
                  account_slots[task.account] = slot_id
                  start_execution(slot_id, task)
```

### 4.3 P0 抢占逻辑

```
收到 P0 任务 → 检查目标账号:
  ├─ 空闲 → 直接分配给空闲 slot
  └─ 忙碌 → 等到当前任务结束后插入:
       slot0: [P1养号_01, ▶️P0评论, P1养号_02, P1养号_03]
                           ↑ P1完成后立即执行P0
                           P0完成后恢复P1队列
 
 不中断正在执行的浏览器（不强行 kill 进程）
```

### 4.4 P2 劣后逻辑

```
P2 只在 slot 空闲且 P0/P1 都为空时才执行
P2 可被任何 P0/P1 抢占:
  slot2: [▶️P2采集] → 收到P1养号 → P2回队列 → [▶️P1养号] → P1完成 → [▶️P2采集]
```

---

## 五、账号互斥守卫（三层检查）

### 5.1 检查层级

| 层级 | 位置 | 检查内容 | 阻止时机 |
|:-----|:------|:---------|:---------|
| 第1层 | `submit_task()` | 该账号在 task_store 中是否有 running/queued 状态 | 入队时拒绝 |
| 第2层 | `_schedule_all_slots()` | 该账号在 `account_slots` 表中是否存在 | 分配时跳过 |
| 第3层 | `slot_manager.find_account()` | 该账号是否已打开浏览器 | 执行前拦截 |

### 5.2 账号状态表

```python
account_slots = {
    "douyin_133": 0,   # slot 0 正在运行
    "douyin_134": 1,   # slot 1 正在运行
    # "douyin_135"  → 不在表中 = 空闲
}
```

任务完成自动移除，异常崩溃时 scheduler 清理。

---

## 六、视频分析引擎（VideoAnalyzer）

### 6.1 模块说明

```
新建文件: agent-sync/05_tools/10_dashboard/services/video_analyzer.py
运行位置: 仅 Master（本机），Worker 不需要
使用技术: Camoufox 浏览器（已有）+ 关键词匹配（已有）
```

### 6.2 核心逻辑

```python
class VideoAnalyzer:
    """视频分析器：提取信息 → 行业分类 → 选评论"""
    
    # 行业关键词映射
    INDUSTRY_TAGS = {
        "medical": ["医生","医院","药","健康","养生","中医","体检",
                    "症状","治疗","康复","营养","饮食","锻炼","专家"],
        "finance": ["股票","基金","理财","投资","经济","A股","财经"],
        "tech":    ["手机","数码","电脑","科技","AI","人工智能","评测"],
        "food":    ["美食","做饭","菜谱","餐厅","好吃","探店"],
    }
    
    async def analyze(self, url: str) -> VideoContext:
        """分析单个视频URL
        1. Camoufox 浏览器打开 URL
        2. 提取: 标题(document.title) / meta描述 / 标签
        3. 读取评论区热门评论（可选）
        4. 返回 VideoContext
        """
    
    def classify(self, context: VideoContext) -> str:
        """分类行业"""
        for ind, tags in INDUSTRY_TAGS.items():
            if any(tag in context.title for tag in tags):
                return ind
        return "general"  # 兜底
    
    def pick_comment(self, industry: str, account_industry: str, direction: str) -> str:
        """选评论
        账号行业匹配视频行业 → 行业语料
        不匹配 → 万能语料
        """
```

### 6.3 与现有能力的关系

| 现有能力 | 是否使用 | 说明 |
|:---------|:---------|:------|
| **Camoufox + Playwright** | ✅ 直接使用 | 已有，打开视频页取信息 |
| **douyin_ops.goto_url()** | ✅ 直接使用 | 已有，导航到指定URL |
| **CorpusManager** | ✅ 改造使用 | 加行业过滤 + 万能池 |
| **Scrapling / Crawl4AI** | ❌ 不使用 | 抓不了抖音动态内容 |
| **ChromaDB (agent-local/vector_db/)** | ⚠️ 可选 | Phase 2 加向量分类时可复用 |

---

## 七、语料库结构

### 7.1 两层语料池

```yaml
# corpus/douyin.yaml
categories:
  # ── 万能池（所有账号可用，不匹配行业时兜底）──
  万能称赞:
    accessible: "*"
    comments:
    - 博主说得很对
    - 讲得不错，学到了
    - 分析得很到位
  万能提问:
    accessible: "*"
    comments:
    - 请问这个怎么学？
    - 大概需要多长时间？
  万能共鸣:
    accessible: "*"
    comments:
    - 太真实了
    - 说出了我的心声

  # ── 行业池（仅对应行业账号可用）──
  大健康称赞:
    accessible: ["health"]
    match_tags: ["医生","医院","药","健康","养生","中医","体检","症状"]
    comments:
    - 医生讲得很清楚，通俗易懂
    - 这个方子很实用，收藏了
    - 讲得很专业，学到了
  大健康提问:
    accessible: ["health"]
    comments:
    - 这个症状一般怎么处理？
    - 平时饮食有什么需要注意的？
```

### 7.2 账号行业标记

```json
// profiles.json
{
  "douyin_133":  {"nickname":"苏州胃肠体检敏敏", "industry":"health"},
  "douyin_test": {"nickname":"小美养生茶",      "industry":"health"},
  "douyin_134":  {"nickname":"在苏州呀",        "industry":"general"},
  "xhs_01":      {"nickname":"...",             "industry":"general"}
}
```

两种行业：`health`（大健康）、`general`（通用）。现阶段统一。

---

## 八、完整数据流示例

### 场景：提交 20 个账号评论 1 个视频

```
Step 1: Master 收到请求
  POST /api/ops/run {type:"smart_comment", urls:["https://..."], accounts:[...]}
    ↓

Step 2: VideoAnalyzer 分析视频
  本机 Camoufox 打开视频URL
  → 标题: "胃镜检查到底疼不疼？医生告诉你真相"
  → 关键词匹配: "医生"、"胃" → industry: medical
  → 选评论: "医生讲得很清楚，通俗易懂"
    ↓

Step 3: 拆解最小单元
  20个账号 × 1个视频 = 20个任务单元
  每个单元 = {account_id, comment:"医生讲得很清楚", url, priority:P0}
    ↓

Step 4: 按机器打包
  查 ORACLE 账号→机器分配表:
    7kecheng → 12个账号 → 12个单元
    5kechengdeAir → 8个账号 → 8个单元
    ↓

Step 5: 分发到各机 guardd
  POST http://100.65.35.28:9090/scheduler/submit (12个P0任务)
  POST http://100.72.182.121:9090/scheduler/submit (8个P0任务)
    ↓

Step 6: 各机 scheduler 处理
  7kecheng:
    slot0: [P1养号, P1养号, P1养号]  (正在执行)
    slot1: [P1养号, P1养号, P1养号]
    slot2: [P2采集, P2采集]
    
    插入 P0 评论包:
    slot0: [P1养号, ▶️P0评论×4, 恢复P1养号]
    slot1: [P1养号, ▶️P0评论×4, 恢复P1养号]
    slot2: [▶️P0评论×4, P2采集, P2采集]
    ↓

Step 7: 各账号打开视频 → 贴预选评论 → 验证
  (Worker 只做这一步，不做任何分析)
```

---

## 九、要改的文件清单

### Phase 1：队列改造（核心）

| 文件 | 改动 | 工作量 |
|:-----|:------|:-------|
| `guardd/modules/scheduler.py` | 三队列分立 + P0抢插 + P2填空 + 账号互斥表 | 大(~200行) |
| `guardd/modules/priority_queue.py` | 现有类不需要大改，加`pop_if()`方法 | 小(~20行) |

### Phase 2：语料重组

| 文件 | 改动 | 工作量 |
|:-----|:------|:-------|
| `corpus/douyin.yaml` | 万能池 + 行业池 分层结构 | 中(重组) |
| `scripts/mc/corpus.py` | `get_comment_for_video()` 加行业过滤 + 万能兜底 | 中(~50行) |
| `profiles.json` | 各账号加 `industry` 字段 | 手动 |

### Phase 3：视频分析 + 智能评论

| 文件 | 改动 | 工作量 |
|:-----|:------|:-------|
| **新建** `services/video_analyzer.py` | 视频分析+行业分类+选评论 | 中(~150行) |
| `services/command_bus.py` | CMD_REGISTRY 加 `smart_comment` 类型 | 小(~20行) |
| `routes/ops.py` | 加智能评论端点 | 小(~10行) |

### Phase 4：指挥台展示（可选）

| 文件 | 改动 | 工作量 |
|:-----|:------|:-------|
| `frontend/views/ops-command.js` | 显示三队列 + P0/P1/P2 过滤 | 中(~80行) |

---

## 十、回退方案

| 标签 | commit | 说明 |
|:-----|:--------|:------|
| `pre-task-architecture` | `7d2b5b14d` | **改架构前的完整备份** |
| `stable-ba34e3d56` | `ba34e3d56` | 再往前的稳定版 |
| `pre-fix-backup` | 略 | 更早备份 |

```bash
# 回退命令
git checkout pre-task-architecture
git push origin --force HEAD:main
```

---

## 十一、暂不处理

| 事项 | 原因 |
|:-----|:------|
| 三级接力评论 | 需求暂缓 |
| 向量模型分类 (ChromaDB) | Phase 2 可选，关键词匹配先行 |
| 视频内容深度分析（字幕/画面） | 复杂度高，当前只分析标题+描述 |
| AI 生成评论（大模型） | 需配置 API key，后续可加 |
| 评论风格跟随热门评论 ("跟风") | 后续可加 |

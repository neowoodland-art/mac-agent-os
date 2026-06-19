# AgentOS 联邦系统 — 状态机架构方案 v3.0

> 目标：让账号在指定动作中随意切换，不受意外打扰，遇到问题自动回到正轨
> 基于现有 `CommandBus` / `ORACLE.yaml` / `guardd` 框架，不重复造轮子

---

## 一、现有系统总览（读代码后的正确理解）

### 1.1 三台机器的真实角色

```
┌─ Dashboard Web 服务 ────────────────────┐
│  chengzigedeAir (master) :9988           │  ← 唯一运行 Dashboard 的机器
│  5kechengdeAir (worker)  ❌ 不跑 Web     │
│  7kecheng (worker)       ❌ 不跑 Web     │
└─────────────────────────────────────────┘

用户在任意电脑打开 http://100.111.43.6:9988 即可操作 Dashboard。
不是"三台都打开本地看板"。
```

**各机器的身份归属**（来自 ORACLE.yaml）：

| 机器 | 身份 | 所属平台账号 |
|:-----|:------|:-----------|
| chengzigedeAir | phone_15370103682 | douyin_test + xhs_01 |
| | douyin_133 / douyin_133_2 / douyin_134 | 各一个抖音 |
| 5kechengdeAir | douyin_01_camo | douyin_01 + xhs_01 |
| | douyin_02_camo | douyin_02 + xhs_02 |
| | douyin_camo01 | douyin_camo01 + xhs_03 |
| 7kecheng | 13个身份 | 各一个抖音 + 小红书 |

### 1.2 现有五层架构（不是新设计，是读出已有的）

```
Layer 5: Dashboard UI (静态前端 SPA)
  → 本地访问 localhost:9988 或远程访问 100.111.43.6:9988

Layer 4: FastAPI 后端路由
  → app.py (plugins/ 插件管理, 数据聚合)
  → routes/ops.py (POST /api/ops/run — 统一执行入口)
  → routes/... (各功能路由)

Layer 3: 命令分发总线 — CommandBus
  → services/command_bus.py
    → CommandBus.dispatch(type, accounts, params)
    → 按 machine 分组 → MachineSession
    → 本机: subprocess.Popen (mc run / mc collect / ...)
    → 远程: SSH → remote_exec → 结果回传

Layer 2: 执行引擎 — mc CLI + 养号脚本
  → mc run → nurture_loop() → run_one_round()
  → 养号: nurture_blueprint.py (Python step list)
  → 登录: sms_login.py / xhs_login.py / douyin_login.py
  → 状态检测: _execute_op() + read_state() + BehaviorConfig

Layer 1: 浏览器管理层 — Camoufox
  → CDPConnector → Camoufox (Firefox)
  → 身份目录: agent-local/tools/matrix/identities/{name}/
  → guardd 守护: 每60s检测孤儿浏览器/磁盘/超时
```

### 1.3 命令分发全过程

```
你在 Dashboard 选账号 → 选蓝图 → 填参数 → 点执行
    ↓
POST /api/ops/run  {
  "type": "nurture",
  "accounts": ["douyin_01"],
  "params": {"blueprint": "douyin_daily", "rounds": 3}
}
    ↓
CommandBus.dispatch()
  → 从 ORACLE.yaml 查到 douyin_01 属于机器 A
  → 获取/创建 MachineSession(A)
  → preflight(): SSH可达? 活跃命令<3?
  → 本机: Popen("mc run --accounts=douyin_01 --blueprint=douyin_daily --rounds=3")
  → 远程: SSH("mc run ... > /tmp/ops_xxx.log &")
    ↓
GET /api/ops/status  ← 轮询状态
  → 本地: 读 runtime/nurture/results/{run_id}.json
  → 远程: SSH cat 远程的结果文件
    ↓
执行结果写文件 → Dashboard 显示
```

**这就是现有的框架。我 v1/v2 里写的"新五层模型"是重复造轮子，已废弃。**

---

## 二、我用状态机要加的东西（不做新框架，只加新模块）

### 2.1 加什么

| 模块 | 位置 | 说明 | 依赖现有代码 |
|:-----|:------|:-----|:-----------|
| `login_state_machine.py` | `matrix_modules/account/` | 登录检测 + Cookie恢复 + SMS重登 | 复用 `xhs_login.py` `sms_login.py` `douyin_login.py` |
| `blueprint_engine.py` | `matrix_modules/` | 蓝图执行引擎（注入状态检查钩子） | 复用 `nurture_blueprint.py` `runner.py` 的 step 格式 |
| `cooldown_manager.py` | `matrix_modules/nurture/` | 操作冷却管理 | 对接现有 `BehaviorConfig` |
| `vision_bridge.py` | ✅ 已存在 | oMLX 视觉分析 | 独立模块 |

### 2.2 不加什么

| ❌ 不加 | 原因 |
|:---------|:------|
| 新的命令分发 | `CommandBus` + `MachineSession` 已经完整 |
| 新的路由 API | `ops.py` 的 `POST /api/ops/run` 已定义格式 |
| 新的 ORACLE | ORACLE.yaml 已经是宪法 |
| 新的身份管理 | 身份目录 + 账号分配已经在 ORACLE 中 |
| 新的看板 | Dashboard 已有完整前后端 |

### 2.3 状态机怎么嵌入现有流程

```
现有流程:
POST /api/ops/run → CommandBus → subprocess(Popen mc run) → 写结果文件
                                                             
我要加的 (在 mc run 内部加钩子):
mc run → 登录状态机(加在开头) → 蓝图执行 → 每步后检查验证弹窗 → 冷却管理
                                  ↑ 复用现有 nurture_blueprint.py
```

核心改动点：**在 `nurture_blueprint.py` / `runner.py` 的执行循环里插入三个钩子**：

```python
# 现有代码 (runner.py nurture_loop)
for round in range(rounds):
    for step in blueprint_steps:
        result = await step.fn(page)   # ← 现有代码

# 改为:
for round in range(rounds):
    # 钩子1: 每轮开始前检测登录（新增）
    await login_state_machine.ensure_login(page, account)
    
    for step in blueprint_steps:
        # 钩子2: 执行每步后检查验证（新增）
        result = await step.fn(page)     # ← 现有代码
        if result == 'VERIFY':
            await verification_handler.handle(page)
            continue
        
        # 钩子3: 冷却等待（新增）
        await cooldown_manager.wait(step.op)
```

**不改现有代码结构，只插入三个钩子。**

---

## 三、蓝图：保持现有 JSON 格式 + 参数模板

### 3.1 当前 JSON 格式（保留不动）

```json
{
  "id": "douyin_comment",
  "steps": [
    {"step_id": 1, "op": "goto_url", "args": {"url": "@url"}},
    {"step_id": 2, "op": "wait_watch", "args": {}},
    {"step_id": 3, "op": "open_comments", "args": {}},
    {"step_id": 4, "op": "post_comment", "args": {"text": "@comment_text"}},
    {"step_id": 5, "op": "close_comments", "args": {}}
  ]
}
```

**`@url` `@corpus` `@keyword` 这种参数模板系统很好**，保留并在 Dashboard 执行时替换。

### 3.2 怎么区分评论的两种模式

抖音评论有**两种入口**（当前代码已有这两种操作）：

| op | 场景 | 当前实现位置 |
|:---|:------|:-----------|
| `post_comment` | 在视频评论区直接发评论 | `nurture_blueprint.py:op_comment()` |
| `reply_comment` | 回复某条已有评论 | `runner.py:reply_comment` (蓝图 `douyin_reply` 中用) |

蓝图选哪个 op 取决于你下发的参数。评论时如果给了 `reply_to` 就用 `reply_comment`，否则用 `post_comment`。

### 3.3 语料库 + 多账号跟踪评论

语料库存放：
```
05_tools/07_matrix/corpus/
├── corpus_praise.json    → ["好作品!", "太棒了!", ...]
├── corpus_question.json  → ["请问怎么做的?", ...]
└── corpus_thread.json    → [
    {"step1": "第一句: 好作品!", "step2": "第二句回复: 同意!", "step3": "第三句: 关注了"}
  ]
```

**跟踪评论（A→B→C）通过蓝图序列实现**：

```python
# 在 sequence_runner.py 中:
SEQUENCE = [
    {"blueprint": "comment", "account": "xhs_01", "params": {"url": "@input_url", "text": "@corpus_thread[0]"}},
    {"blueprint": "reply_comment", "account": "douyin_test", "params": {"target_text": "@corpus_thread[0]", "reply": "@corpus_thread[1]"}},
    {"blueprint": "reply_comment", "account": "douyin_133", "params": {"target_text": "@corpus_thread[1]", "reply": "@corpus_thread[2]"}},
]
```

每条语料的 step1/step2/step3 会被自动取用。这个不走新框架，直接走现有的 CommandBus 顺序下发。

---

## 四、登录状态机（唯一真正要写的新模块）

### 4.1 接口

```python
class LoginStateMachine:
    async def ensure_login(self, page, account_id: str, platform: str) -> bool:
        """确保登录，返回 True=已登录"""
        
    async def _detect(self, page, platform: str) -> str:
        """检测状态: 'logged_in' / 'not_logged' / 'unknown'"""
        # DOM 检测: xhs → .user-avatar  douyin → [data-e2e=user-avatar]
        
    async def _recover_cookie(self, page) -> bool:
        """刷新页面让 cookie 生效"""
        
    async def _recover_sms(self, page, phone: str) -> bool:
        """SMS 验证码登录"""
        # 复用 sms_login.py 的原子操作
```

### 4.2 用法

```python
# 在 runner.py nurture_loop 开头加:
async def nurture_loop(...):
    lsm = LoginStateMachine()
    ok = await lsm.ensure_login(page, identity_name, platform)
    if not ok:
        return {"status": "failed", "error": "login_failed"}
    # ... 继续现有逻辑
```

---

## 五、执行计划（只做增量，不重构）

| 任务 | 文件 | 工作量 | 前置依赖 |
|:-----|:------|:------|:--------|
| 写 LoginStateMachine | `matrix_modules/account/login_state_machine.py` | 半天 | 无（复用现有原子操作） |
| 加登录钩子到 nurture_loop | 改 `runner.py` + `nurture_blueprint.py` | 1小时 | LoginStateMachine |
| 加验证处理钩子到 op 执行后 | 改 `runner.py` | 1小时 | 无（复现现有 _handle_verify） |
| 加冷却管理 | `matrix_modules/nurture/cooldown_manager.py` | 1小时 | 无 |
| 语料库目录 + 蓝图参数扩展 | `corpus/*.json` + 改 blueprint JSON | 半天 | 无 |
| Dashboard 参数表单对接 | `static/index.html` (Vite 迁移后) | 跟 Vite 一起 | Vite 迁移完成 |

---

## 六、误区总结（防止再跑偏）

| 我原来写错的 | 实际上 | 参考文件 |
|:------------|:-------|:--------|
| "五层新架构" | 已有 `CommandBus` + `MachineSession` + `ORACLE.yaml` | `services/command_bus.py` |
| "Dashboard三台都跑" | 只有 chengzigedeAir:9988 | `DEPLOYMENT.md` |
| "蓝图是新概念" | 已有 14 个 JSON + 参数模板 `@url` `@corpus` | `blueprints/*.json` |
| "新框架要造" | 只在现有代码插三个钩子 | `runner.py` `nurture_blueprint.py` |
| "命令格式要定" | 已有 `POST /api/ops/run` 格式已定 | `routes/ops.py` `BUSINESS_ARCHITECTURE_v4.md` |

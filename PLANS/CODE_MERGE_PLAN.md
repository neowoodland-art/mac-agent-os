# AgentOS 联邦系统 — 代码合并与清理方案 v1.0

> 目标：消除重复/歧义/新旧版本并存问题，留下一套统一清晰的代码

---

## 一、CLI 合并：`mc` + `matrix` → `mc` 统一

### 1.1 现状

| 功能 | `mc` (当前主入口) | `matrix` (旧入口) |
|:-----|:-----------------|:-----------------|
| 账号列表 | ✅ `mc account list` | ✅ `matrix account list`（读不同yaml） |
| 账号状态 | ✅ `mc account status` | ✅ `matrix account status`（不同判断方式） |
| 账号登录 | ✅ `mc account login` | ✅ `matrix account login`（代码相同） |
| **账号创建** | ❌ **没有** | ✅ `matrix account create` → `create_identity.py` |
| 账号导出 | ✅ `mc account export` | ❌ |
| 账号导入 | ✅ `mc account import` | ❌ |
| 蓝图列表 | ✅ `mc blueprint list` | ✅ `matrix config blueprint list` |
| **养号执行** | ✅ `mc run` (**BatchEngine**) | ✅ `matrix nurture run` (**nurture_multi**) |
| 定时任务 | ✅ `mc task` | ❌ |
| 语料库 | ✅ `mc corpus` | ❌ |
| 代理 | ✅ `mc proxy` (预留) | ❌ |
| SMS | ✅ `mc sms` (预留) | ❌ |
| 全局状态 | ✅ `mc status` | ✅ `matrix status` |
| **config展示** | ❌ | ✅ `matrix config show` |

### 1.2 关键问题

**问题1：`matrix account create` 是 mc 没有的**
`mc` 缺少创建身份功能。需要把 `create_identity.py` 的调用移植过来。

**问题2：`mc account list` 和 `matrix account list` 读不同的 yaml**
- `mc account list` → 读 `config/accounts.yaml`（mc配置）
- `matrix account list` → 也读 `config/accounts.yaml`（其实是同一个文件）
- 这里其实不冲突，只是 `matrix` 把所有 enabled 账号都列出来

**问题3：养号执行有两套路径**
- `mc run` → `BatchEngine` → CDPConnector → DouyinOps/XhsOps → JSON 蓝图
- `matrix nurture run` → `nurture_multi` / `nurture_xhs_loop` → `runner.py` → `nurture_blueprint.py` (Python步列表)

这两套是**完全不同的执行逻辑**！`mc run` 走 JSON 蓝图，`matrix nurture` 走 Python 步列表。

### 1.3 合并方案

**目标：只保留 `mc`，`matrix.py` 移入 `archive/`。**

| 要加的功能 | 加到 `mc` 哪里 | 代码来源 |
|:----------|:-------------|:---------|
| `mc account create <name>` | `mc/cli.py:cmd_account` → 新增 action="create" | 从 `matrix.py:cmd_account_create` 搬 |
| `mc config show` | `mc/cli.py` → 新增子命令 | 从 `matrix.py:cmd_config_show` 搬 |

**养号执行路径统一**：
- **保留 `mc run`**（走 BatchEngine + JSON 蓝图）
- **删除 `matrix nurture run`**
- `runner.py` 中的 `nurture_multi` / `nurture_xhs_loop` 保留备查，但不再通过 CLI 直接调用

---

## 二、Ops 合并：抖音 → 统一 DouyinOps

### 2.1 现状：抖音有三套操作代码

| 实现 | 文件 | 形式 | 状态 |
|:-----|:------|:------|:------|
| **A: DouyinOps 完整类** | `douyin_ops.py` (210行) | 完整类，20个操作 | ✅ **当前使用** (engine.py 调这个) |
| **B: ops/douyin/ 拆分布** | `ops/douyin/browse.py` + `interact.py` (70行) | 独立函数，5个操作 | ❌ 轻量版、不完整、未使用 |
| **C: runner.py 内联执行** | `runner.py:_execute_op()` | 内联函数，10个操作 | ❌ 旧养号路径在用 |

**ops/douyin/browse.py + interact.py = 冗余代码**。只有 5 个操作（goto_home, goto_video, scroll_feed, like, collect, comment, next_video），而且和 DouyinOps 功能完全重叠。

### 2.2 小红书情况

| 实现 | 文件 | 状态 |
|:-----|:------|:------|
| **XhsOps** | `ops/xhs_ops.py` | ✅ 当前使用 (engine.py 调这个) |
| **runner.py 内联** | `runner.py` 中 `nurture_xhs_loop` | ❌ 旧养号路径在用 |

小红书只有一套 XhsOps，没有冗余问题。

### 2.3 Ops 合并方案

| 操作 | 当前方案 |
|:-----|:---------|
| `douyin_ops.py` DouyinOps | ✅ **保留为主入口** |
| `ops/douyin/browse.py` | **归档**到 `archive/` |
| `ops/douyin/interact.py` | **归档**到 `archive/` |
| `ops/douyin/` 目录 | **删除**（已被 DouyinOps 完整覆盖） |
| `runner.py` 中的 `_execute_op()` | 保持不动（旧养号路径还在用，等迁移完再删） |

---

## 三、工具 vs 蓝图：厘清职责

### 3.1 当前散落的独立工具

| 文件 | 功能 | 应该归类 |
|:-----|:------|:---------|
| `collect_homepage_info.py` | 采集用户主页信息（昵称/粉丝/关注） | **走蓝图** (现有 `douyin_read_profile` + `xiaohongshu_read_profile`) |
| `collect_batch_runner.py` | 批量采集多个账号 | **走蓝图** + `mc run` 批量执行 |
| `publish_video.py` | 视频发布（Camoufox浏览器上传，可选调外部sau CLI） | **Camoufox模式→走蓝图**（加4个发布操作到Ops）；sau模式保持独立工具 |
| `login_identity.py` | 身份登录 | **走 mc account login** |
| `create_identity.py` | 创建新身份 | **走 mc account create** |
| `guardd.py` | 系统守护进程 | **不是蓝图**，保持独立 |

### 3.2 蓝图 vs 工具的定义

| | 蓝图 (Blueprint) | 工具 (Tool) |
|:--|:----------------|:------------|
| **做什么** | 操作账号（登录/点赞/评论/采集/发布） | 维护系统（创建身份/管理代理/启动daemon） |
| **执行方式** | 被 `mc run` 调用，走浏览器 + 原子操作 | 直接 CLI 调用，不涉及浏览器 |
| **定义位置** | `blueprints/*.json` | `scripts/*.py` 或 `mc/*.py` |
| **例子** | `douyin_daily`, `douyin_comment`, `xhs_daily` | `create_identity.py`, `guardd.py`, `cdp_connector.py` |

**结论**：`collect_homepage_info.py` 的功能应该通过 `mc run --blueprint=douyin_read_profile` 来实现。它有独立的 `douyin_read_profile` 蓝图（9步）和 `xiaohongshu_read_profile` 蓝图（8步），只是原来没有通过 `mc run` 统一入口调用。应该改成：

```bash
# 原来: python collect_homepage_info.py --single phone_xxx
# 改为: mc run --accounts=douyin_test --blueprints=douyin_read_profile --rounds=1
```

---

## 四、完整合并行动清单

### Phase 1: CLI 合并（30分钟）

| # | 任务 | 改动文件 | 说明 |
|:-:|:-----|:---------|:------|
| 1 | `mc account create` | `mc/cli.py` | 新增 action="create", 调 create_identity.py |
| 2 | `mc config show` | `mc/cli.py` | 新增子命令，搬 matrix.py 的 cmd_config_show |
| 3 | `matrix.py` 移入 archive | 删除原文件 | 标记废弃 |

### Phase 2: Ops 清理（15分钟）

| # | 任务 | 说明 |
|:-:|:-----|:------|
| 1 | `ops/douyin/` 目录归档 | browse.py + interact.py 功能完全被 douyin_ops.py 覆盖 |
| 2 | 确认 engine.py 只引用 douyin_ops.py | 当前已经是这样，不改 |

### Phase 3: 工具→蓝图迁移（辅助标注）

| # | 任务 | 说明 | 操作 |
|:-:|:-----|:------|:-----|
| 1 | `collect_homepage_info.py` 迁移 | 提取函数(extract_douyin/extract_xiaohongshu)被collect_batch_runner复用 | 保留不动，新增 blueprints 内数据输出能力后自然废弃 |
| 2 | `collect_batch_runner.py` 迁移 | 有独特的分批管理/输出格式逻辑，暂不能直接取代 | 保留，待BlueprintEngine支持结构化输出后再迁移 |
| 3 | **LoginStateMachine** | ✅ 这才是真正要写的核心模块 | 立即开始写 |

> **实际优先级调整**：工具→蓝图迁移是清理任务，可延后。
> 当下最有价值的是写 `login_state_machine.py`，嵌入到现有的 BatchEngine 执行流中。

### Phase 4: 废弃代码归档

| 文件 | 处理 |
|:-----|:------|
| `matrix.py` (整个) | → `archive/` |
| `ops/douyin/browse.py` | → `archive/` |
| `ops/douyin/interact.py` | → `archive/` |
| `atom_ops.py` | → `archive/` |
| `yanghao_runner.py` | → `archive/` |
| `orchestrator.py` | → `archive/` |
| `step_by_step_v2.py` | → `archive/` |
| `step_by_step_v3.py` | → `archive/` |
| `xhs_session_test.py` | 删除（测试文件） |
| `watch_session.py` | 删除（测试文件） |

---

## 五、合并后架构

```
mc CLI (统一入口)
├── mc account list|create|login|status|export|import
├── mc run --accounts --blueprints --rounds     ← 唯一执行入口
├── mc blueprint list|show
├── mc task comment
├── mc corpus list|add|select
├── mc proxy list|test|set
├── mc sms config|test
├── mc status all|accounts|browsers
└── mc config show                              ← 新增

执行路径 (唯一):
mc run → BatchEngine → CDPConnector → Camoufox → DouyinOps / XhsOps → JSON蓝图步

独立工具 (不通过蓝图, 直接CLI调用):
cdp_connector.py    浏览器连接管理
create_identity.py  创建身份
guardd.py           系统守护进程
vision_bridge.py    oMLX视觉分析
```

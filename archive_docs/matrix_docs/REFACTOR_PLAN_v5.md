# Matrix 重构方案 v5 — 执行可靠性 + 智能体可调用

> 版本: v5.0 | 日期: 2026-06-09 | 状态: 方案阶段
> 基于: 全项目代码审查 + AgentOS 联邦架构理解

---

## 一、目标

让 Matrix 养号系统达到三个标准：

1. **执行可靠性** — 每个操作有前后验证，结果可追踪，不误报成功
2. **智能体可稳定调用** — 统一的 CLI + 清晰的文档，智能体不需要读源码就能用
3. **自动化任务** — 通过 guardd 或 cron 定时执行，不依赖人工盯日志

---

## 二、当前问题根因

```
核心矛盾：engine.py 的 run_single() (773行) 是一艘"独木舟"——
自己解析蓝图、自己连浏览器、自己写 page.evaluate 执行操作、自己汇总报告。
它绕过了系统里已有的 DouyinOps (563行) 和 AtomOps (517行)，
把调度层和操作层糊在一起，导致：

  → 操作执行后无验证 (like 按钮真的变色了吗?)
  → 小红书操作零抽象 (10个 xhs_* 全是内联 evaluate)
  → 新增平台/操作需要修改 engine.py 本身
  → 测试一个操作 = 启动整个引擎
```

---

## 三、目标架构

```
mc (唯一 CLI 入口)
  │
  ├─ mc run → mc/engine.py (纯调度层, ~200行)
  │   │
  │   ├─ 解析参数 (accounts, blueprints, rounds)
  │   ├─ 并行调度 (asyncio.gather, 每账号一个持久浏览器)
  │   ├─ 蓝图选择 (_pick_blueprint)
  │   └─ 报告汇总 (BatchReport)
  │       │
  │       └──→ platform_ops/ (平台操作层, 每平台一个类)
  │            ├── DouyinOps   — 已有 (douyin_ops.py)
  │            ├── XhsOps      — 新建 (从 engine.py 提取)
  │            ├── ProfileReader — 新建 (dy_read_* 系列)
  │            └── AtomOps     — 已有, 集成 pre_check/post_check
  │
  ├─ mc account → matrix_mgmt.py (账号管理)
  ├─ mc blueprint → matrix_mgmt.py (蓝图管理)
  ├─ mc corpus → mc/corpus.py (语料库)
  └─ mc status → mc/status.py (状态查询)
```

---

## 四、执行链路重构

### 现状 (engine.py run_single)

```python
if op == "goto_home":     ... conn.page.goto("https://www.douyin.com/") ...
elif op == "like":        ... conn.page.evaluate("querySelector...click()") ...
elif op == "xhs_like":    ... conn.page.evaluate("querySelector...click()") ...  # 又写一遍
elif op == "post_comment": ... pbcopy + evaluate + keyboard.press ...
# 28 个 elif...
```

### 目标 (调度器调用平台Ops)

```python
async def run_single(self, account_id, blueprint_name, round_idx, conn=None):
    ops = PlatformOps.for_account(account_id, conn.page)
    
    for step in blueprint.steps:
        result = await ops.execute(
            op=step.op,
            args=step.args,
            validate=True              # ← 新增：执行后验证
        )
        report.add_step(result)
```

### 平台Ops 接口

```python
class PlatformOps(ABC):
    """平台操作基类 — 智能体通过 mc 调用，不直接操作此类"""
    
    async def execute(self, op: str, args: dict, validate: bool = True) -> OpResult:
        """执行一个操作，可选验证"""
        
    def supported_ops(self) -> list[str]:
        """返回支持的操作列表"""
```

每个平台类（DouyinOps, XhsOps）实现此接口。对于已验证的操作（like, collect, comment等），内部委托给 AtomOps 以复用 pre_check/post_check。

---

## 五、操作验证机制

复用 `atom_ops.py` 中已有的 `_execute()` 模式：

```
操作执行流程 (每个步骤):
  1. pre_check() — 确认页面状态允许此操作
     ├─ like: 在视频播放器页？ → check "video_player" 锚点
     ├─ comment: 评论区已打开？ → check "comment_input" 锚点
     └─ goto_home: 总是允许
     
  2. execute() — 执行操作
     
  3. post_check() — 确认操作生效
     ├─ like: 按钮 class 变化？
     ├─ collect: 按钮状态切换？
     └─ goto_home: 页面加载完成？
     
  4. 失败重试 (默认1次)
  
  5. 返回结构化 OpResult { success, op, detail, elapsed, retries }
```

### 验证结果的存储

操作结果不在 print log 中散落，而是写入结构化记录：

```python
# engine.py 回调 → 写 RunLog
class RunLog:
    account_id: str
    blueprint: str
    round: int
    steps: list[OpResult]
    started_at: datetime
    ended_at: datetime
    summary: {"success": 8, "failed": 2, "skipped": 1}
```

存储位置：`agent-local/tools/matrix/logs/run_{date}_{account}.jsonl`

---

## 六、新增文件清单

| 文件 | 来源 | 说明 |
|------|------|------|
| `scripts/ops/xhs_ops.py` | **新建** | 小红书操作（从 engine.py 提取 10 个 xhs_* 操作） |
| `scripts/ops/profile_reader.py` | **新建** | 主页信息采集（dy_read_* / xhs_read_* 系列） |
| `scripts/ops/_base.py` | **新建** | PlatformOps 基类 + OpResult 定义 |
| `scripts/mc/runlog.py` | **新建** | 结构化运行日志 |
| `scripts/mc/nurture_daily.py` | **新建** | Python版每日养号编排（替代 nurture_daily.sh 对 mc 的命令行调用） |

## 七、修改文件清单

| 文件 | 变更 |
|------|------|
| `scripts/mc/engine.py` | 从 773行 缩至 ~250行，去除全部内联 page.evaluate，改为调用 PlatformOps |
| `scripts/mc/cli.py` | 补全子命令（account create, status accounts），支持 `--validate` flag |
| `scripts/mc/run.py` | 简化，委托 engine.BatchEngine |
| `scripts/douyin_ops.py` | 实现 PlatformOps 接口，集成 AtomOps 验证 |
| `mc` (shell wrapper) | Python路径改为 `which python3`，去掉硬编码 |
| `scripts/nurture_daily.sh` | 改为调用 `mc run` 命令 |
| `SKILL.md` | 更新命令示例，文档状态 |
| `TOOL.md` | 版本号统一，架构图更新 |

## 八、文件废弃/归档

| 文件 | 处理 |
|------|------|
| `scripts/matrix.py` | 保留但加废弃说明，所有调用改用 mc |
| `scripts/nurture_master.sh` | 废弃，功能由 nurture_daily.sh 覆盖 |
| 25+ 调试/测试脚本 | 移入 `scripts/_archive/` |
| `scripts/yanghao_runner.py` | 交互模式合并到 `mc account login` |
| `scripts/task_engine.py` | 蓝图执行功能合并到 mc/engine.py |
| `scripts/matrix_modules/nurture/runner.py` | 废弃（1946行，功能被新engine覆盖） |
| `scripts/camoufox_manager.py` / `camoufox_server.py` | 移入 `_archive/` |
| `scripts/browser_manager.py` / `browser_keepalive.py` | 保留 mc/browser.py，删除重复 |

## 九、硬编码修复

| 位置 | 当前 | 修复 |
|------|------|------|
| `mc` shell wrapper | `/Users/5kecheng/.workbuddy/...` | `which python3` 或 `$AGENTOS_PYTHON` |
| `matrix_mgmt.py` L32 | `/Users/chengzige/.workbuddy/...` | `Path.home() / ".workbuddy"` |
| `nurture_master.sh` | 硬编码 Python 路径 | 改用 mc 命令 |
| `ARCHITECTURE.md` L190 | 窗口位置硬编码 | 从 accounts.yaml 读 |

## 十、实施顺序

```
Phase 0 (本文档)                    [完成] 方案设计
Phase 1: 操作层提取                  [下一步]
  1. 创建 ops/_base.py (OpResult + PlatformOps 基类)
  2. 创建 ops/xhs_ops.py (从 engine.py 提取)
  3. 创建 ops/profile_reader.py (从 engine.py 提取)
  4. douyin_ops.py 实现 PlatformOps 接口

Phase 2: 引擎重构
  1. engine.py 从 773行 缩至 ~250行
  2. run_single() 改为调用 PlatformOps.execute()
  3. 集成 runlog.py 结构化日志
  4. 验证：用现有账号跑一次养号，确认结果一致

Phase 3: CLI 统一
  1. mc 补全缺失子命令 (account create, status)
  2. mc shell wrapper 修复硬编码路径
  3. 编写 mc 命令参考手册

Phase 4: 脚本清理
  1. 25+ 脚本移入 _archive/
  2. 废弃文件移除
  3. .gitignore 更新

Phase 5: 文档
  1. SKILL.md / TOOL.md / MODULE.md 更新
  2. 所有版本号统一为 v5.0
```

---

## 十一、不破坏的约束

- `agent-local/` 不动（本机数据，不同步）
- `cross_machine/data/matrix/` 不动（联邦状态通道）
- `blueprints/` 不动（共享蓝图，格式不变）
- `accounts_registry.yaml` 不动
- `install.sh` 不动（新机部署依赖它）
- `accounts.yaml` 格式不动
- **所有 shell 脚本的调用接口保持兼容**（nurture_daily.sh 仍然可用）

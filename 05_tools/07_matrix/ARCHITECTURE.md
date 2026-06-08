# Douyin 全模拟运营系统架构 v1.0

> 最后更新: 2026-05-15
> 基于 AgentOS 多机协同体系

---

## 设计原则

1. **代码走同步，数据留本机** — 脚本在 agent-sync (Gitee)，工作区在 agent-local (不参与同步)
2. **四层隔离** — 管理层/流水线层/操作层/数据层，每层独立演进
3. **每账号独立工作区** — 身份、素材、文案、发布记录各自独立
4. **原子操作可组合** — 所有操作遵循 `前置锚点 → 执行 → 后置锚点` 模式
5. **与现有养号系统共存** — 新架构不破坏 `matrix.py` / `nurture_blueprint.py`

---

## 目录结构

```
~/workbuddy-agent-os/
├── agent-sync/                              ← Gitee 同步（代码/技能）
│   └── 05_tools/
│       └── 07_matrix/
│           ├── ARCHITECTURE.md              ← 本文档
│           ├── scripts/
│           │   ├── matrix.py                ← 统一 CLI
│           │   ├── atom_ops.py              ← 原子操作库
│           │   ├── nurture_blueprint.py     ← 养号蓝图
│           │   ├── douyin_ops.py            ← 抖音专用操作
│           │   ├── matrix_modules/          ← 子模块
│           │   ├── pipelines/               ← [新] 流水线脚本
│           │   │   ├── __init__.py
│           │   │   ├── content_publish.py   ← 内容发布流水线（待建）
│           │   │   ├── ecom_pipeline.py     ← 电商流水线（待建）
│           │   │   └── live_pipeline.py     ← 直播流水线（待建）
│           │   └── ops/                     ← 平台操作
│           └── blueprints/
│
├── agent-local/                             ← 本机数据（不参与同步）
│   └── tools/
│       └── matrix/
│           ├── config/
│           │   └── accounts.yaml            ← 账号注册信息
│           ├── identities/                  ← 浏览器指纹+登录态
│           │   ├── douyin_01_camo/
│           │   ├── douyin_02_camo/
│           │   └── douyin_camo01/
│           └── accounts/                    ← [新] 每账号工作区
│               ├── douyin_01/
│               │   ├── content/             ← 视频素材
│               │   │   ├── raw/             ← 原始素材
│               │   │   ├── edited/          ← 剪辑成品
│               │   │   └── thumbnails/      ← 封面图
│               │   ├── scripts/             ← 脚本文案
│               │   │   ├── drafts/          ← 草稿
│               │   │   └── posted/          ← 已发布
│               │   ├── publish/             ← 发布记录
│               │   │   ├── queue/           ← 待发布队列
│               │   │   └── published/       ← 已发布记录
│               │   └── backup/
│               │       └── cookies/         ← 登录态备份
│               ├── douyin_02/               ← 同上
│               └── douyin_camo01/           ← 同上
```

---

## 四层架构

### Layer 1: 数据层（本机，不同步）

每个账号独立文件夹，包含四类数据：

| 子目录 | 用途 | 数据来源 |
|:-------|:-----|:---------|
| `content/` | 视频素材（raw/edited/thumbnails） | 外部导入 / 剪辑 |
| `scripts/` | 脚本文案（drafts/posted） | AI 生成 / 手动编写 |
| `publish/` | 发布队列 + 历史记录 | 系统自动写入 |
| `backup/` | 登录态备份 | 系统自动备份 |

### Layer 2: 操作层（代码，Gitee 同步）

原子操作（`atom_ops.py` 和 `douyin_ops.py`）：

| 操作 | 状态 | 说明 |
|:-----|:----:|:-----|
| browse | ✅ | 浏览视频流 |
| like / collect | ✅ | 点赞/收藏 |
| comment path a | ✅ | 弹窗覆盖层评论（KeyX+Enter） |
| comment path b | ✅ | 全屏视频页评论（scroll+click+Enter） |
| search | ✅ | 搜索并打开 |
| follow | ✅ | 关注 |
| **publish_video** | ⏳ 待建 | 上传视频+文案+封面 |
| **live_sim** | ⏳ 待建 | 直播推流模拟 |
| **product_select** | ⏳ 待建 | 选品/带货 |
| **dm_send** | ⏳ 待建 | 私信 |

### Layer 3: 流水线层（代码，Gitee 同步）

| 流水线 | 状态 | 操作链 |
|:-------|:----:|:-------|
| 养号流水线 (nurture) | ✅ | browse → interact → comment → loop |
| 内容发布流水线 | ⏳ 待建 | 读取队列 → 登录 → 上传 → 发布 → 记录 |
| 电商流水线 | ⏳ 待建 | 选品 → 添加到橱窗 → 推广 |
| 直播流水线 | ⏳ 待建 | OBS推流 → 直播间互动 → 带货 |

### Layer 4: 管理层（规划中）

- 内容排期日历
- 多账号任务调度
- 发布成功率 KPI

---

## 两条评论路径对比

| 维度 | Path A: 弹窗覆盖层 | Path B: 全屏视频页 |
|:-----|:------------------|:------------------|
| 入口 | 精选页→点卡片→弹窗播放器 | 直接打开 `/video/xxx` URL |
| 评论区状态 | 隐藏 (hasCL=false) → KeyX 打开 | 页面上方直接可见 |
| 激活方式 | 坐标 (479,687) 双击 | scrollIntoView + click 输入容器 |
| 输入方式 | pbcopy + Meta+V (共享) | pbcopy + Meta+V (共享) |
| 发送方式 | Enter | Enter |
| 适用场景 | 养号流程中的日常操作 | 收到指定链接后自动评论 |

Route 规则：
```
if URL 包含 /video/ → Path B
else → 检查 hasCL
  if hasCL=true → 直接聚焦
  if hasCL=false → KeyX 打开 → Path A
```

---

## 并行执行架构（v4.3 新增）

`mc run` 使用 `mc/engine.py` 的 `BatchEngine` 执行批量任务。v4.3 改为并行模式：

### 设计要点

1. **单账号全轮复用浏览器** — 每个账号创建一个 Camoufox 连接，跑完全部轮次再关闭
2. **多账号 `asyncio.gather`** — 所有账号的 `_run_account_all_rounds()` 同时启动
3. **浏览器启停优化** — N 个账号 × R 轮 → 启停 N 次（而非 N×R 次）

### 新旧对比

```
旧版 (v1.1):
  轮1: A→B→C (串行) → 间隔 → 轮2: A→B→C → 间隔 → 轮3: A→B→C
  # 每步开闭一次浏览器，后一个等前一个完成
  # 3账号×3轮 ≈ 500-900s/批次

新版 (v1.2):
  A的全部3轮 ──┐
  B的全部3轮 ──┼── asyncio.gather ── 同时完成
  C的全部3轮 ──┘
  # 每账号一个持久浏览器，互不等待
  # 3账号×3轮 ≈ 150-350s/批次（约节省 60%）
```

### 代码入口

| 方法 | 职责 |
|:-----|:-----|
| `BatchEngine.run()` | prepare 所有账号 → gather 子任务 → 汇总 |
| `_run_account_all_rounds()` | 每账号：resolve → cookie 检查 → 启动浏览器 → 循环轮次 → 关闭 |
| `run_single(conn=...)` | 单轮单账号：导航到首页 → 执行蓝图步骤 → 返回报告 |
| `_pick_blueprint(round_idx)` | 混合随机/顺序选择本轮蓝图 |

### 共享连接模式

`run_single()` 新增 `conn` 参数：
- `conn=None` → 自行创建并关闭浏览器（独立使用场景）
- `conn=CDPConnector` → 复用已有连接（`_run_account_all_rounds` 内部调用）

### 注意事项

- 并行启动多个 Camoufox 实例时，不要同时调用 `connect()` 中的 `pkill -f camoufox`
  （目前 connect() 中始终执行，但因同步调用在 async 之前完成，3 个并行的 connect() 的
   pkill 都在任何 Camoufox 启动前执行完毕，因此不会跨进程误杀）
- `BrowserManager.prepare()` 在 `run()` 中统一调用，不在子任务中重复执行


2026-05-15 修改：窗口位置固定从 `accounts.yaml` 读取，不再保存回写。
Camoufox 启动偏移会导致保存的坐标偏离预期（如 0→652, 400→2169）。

| 账号 | 固定位置 |
|:-----|:--------:|
| douyin_01 | (0, 0) |
| douyin_02 | (400, 0) |
| douyin_camo01 | (750, 0) |

---

## 评论故障修复记录（2026-05-15）

### 问题
养号流程中评论发送失败，日志显示 `页面出现评论: ❌`

### 根因
1. **输入方式错误**: `keyboard.type()` 被 Draft.js 忽略，execCommand fallback 不触发 React 状态
2. **发送键错误**: Alt+Enter 不再被新版抖音支持

### 修复
| 文件 | 行 | 改前 | 改后 |
|:-----|:---|:-----|:-----|
| `runner.py` | Step 2 输入 | keyboard.type → execCommand | **pbcopy + Meta+V** |
| `runner.py` | Step 3 发送 | Ctrl+Enter → Alt+Enter | **Enter** |
| `runner.py` | 坐标保存 | 每次结束回写 accounts.yaml | **删除，固定读配置** |
| `nurture_blueprint.py` | op_comment 发送 | Alt+Enter (osascript) | **keyboard.press Enter** |

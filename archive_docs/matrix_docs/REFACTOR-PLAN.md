# Matrix 养号系统 — 重构设计方案 v2.2

> 最后更新：2026-05-01
> 版本：2.2.0 (草案)

> 本文件为设计方案，待确认后再实施。

## 一、当前问题诊断

| # | 问题 | 根因 | 影响 |
|---|------|------|------|
| 1 | 退出时 Chrome 崩溃/恢复弹窗 | `os.kill(pid, 9)` 强行杀进程，未走正常关闭 | 下次启动弹恢复确认框 |
| 2 | 点赞/收藏永远失败 | 操作前未验证当前页面状态，直接在首页点按钮 | 操作无效果 |
| 3 | "11/11 完成"但什么都没做 | 没有操作后的锚点验证，异常也被吞了 | 误报成功 |
| 4 | 不知道当前在什么页面 | 没有页面状态跟踪器 | 操作错位 |
| 5 | 登录验证不可靠 | 只查了一个 `data-e2e` 选择器，页面不同状态结果不同 | 误判未登录 |
| 6 | 脚本散乱不可组合 | 每个测试脚本都重复写类似逻辑 | 维护成本高 |

## 二、架构设计

### 2.1 三层架构

```
┌─────────────────────────────┐
│    WorkBuddy 技能层          │  ← 对话触发
│  (SKILL.md + 养号指令)       │
├─────────────────────────────┤
│    orchestrator 调度层       │  ← 智能选账号/蓝图/状态机
│  (yanghao_orchestrator.py)  │
├─────────────────────────────┤
│    原子操作层 (21个原子操作)   │  ← 可组合、可验证
│  (AtomOps + 校验器)          │
├─────────────────────────────┤
│    CDP连接器 + 浏览器管理     │  ← 优雅启停
│  (cdp_connector + browser)  │
└─────────────────────────────┘
```

### 2.2 原子操作定义 (每个操作带前置校验 + 后置锚点)

```
每个原子操作 = (名称, 执行函数, 前置校验, 后置锚点, 超时, 重试次数)

例子:
  "like" =
    pre_check:  当前在视频播放器页, 点赞按钮存在
    execute:    点击 [data-e2e="video-player-digg"]
    post_check: 点赞数+1 或 按钮状态变化
    timeout:    10s
    retry:      2次
```

### 2.3 页面状态机

```
[首页 grid] ──点击视频──→ [视频播放器]
    ↑                       │
    │                       ↓
    │                   [下滑/下一条]
    │                       │
    │                       ↓
    │                   [新视频播放器]
    │                       │
    └─────── 返回首页 ──────┘

页面锚点:
  grid 模式:  有 [data-e2e="alink-item"]，无 video-player-digg
  播放器模式: 有 [data-e2e="video-player-digg"]
  搜索页:     有 [data-e2e="searchbar-input"]
  登录态:     有 sessionid cookie + 特定 DOM 元素
```

### 2.4 浏览器优雅管理

```python
# 不要 kill -9，用正常关闭
browser_manager = BrowserManager()
await browser_manager.launch(account='douyin_01')  # 启动
await browser_manager.close()                       # 正常关闭，不走 kill
await browser_manager.graceful_shutdown()           # 先 SIGTERM，等待，再 SIGKILL
```

### 2.5 蓝图新格式 (带验证锚点)

```json
{
  "id": "douyin_browse_v2",
  "version": "3.0.0",
  "steps": [
    {
      "step_id": 1,
      "op": "goto_and_verify",
      "args": {"url": "https://www.douyin.com/"},
      "verify": {"mode": "page", "anchor": "alink-item"},
      "on_fail": "retry(2)"
    },
    {
      "step_id": 2,
      "op": "open_video",
      "args": {},
      "verify": {"mode": "element", "selector": "[data-e2e='video-player-digg']"},
      "on_fail": "try_search"
    },
    {
      "step_id": 3,
      "op": "wait_watch",
      "args": {"seconds": 8},
      "verify": {"mode": "state", "field": "video_playing", "expect": true},
      "on_fail": "skip"
    },
    {
      "step_id": 4,
      "op": "like",
      "args": {},
      "verify": {"mode": "change", "selector": "[data-e2e='video-player-digg']", "attr": "class"},
      "on_fail": "log_warn"
    }
  ]
}
```

### 2.6 调度器设计

```python
class YanghaoOrchestrator:
    """养号调度器"""
    
    async def run(self, account_id, blueprint_id):
        """执行一次养号"""
        # 1. 校验账号配置
        # 2. 校验蓝图
        # 3. 启动浏览器 (优雅)
        # 4. 登录校验
        # 5. 逐步骤执行 (带验证锚点)
        # 6. 生成报告
        # 7. 关闭浏览器 (优雅)
    
    async def verify_login(self):
        """多维度验证登录态"""
        # cookie: sessionid 存在
        # DOM: user-avatar 或 user-detail 可见
        # 请求: 能获取推荐内容
```

### 2.7 接入 WorkBuddy 技能

在 `matrix/SKILL.md` 中新增触发词：

```yaml
triggers:
  - 养号
  - 运行养号
  - 南方小马铃薯
  - 次元时空的桃子
  - 橙子哥
```

WorkBuddy 通过 Skill 工具加载后，**由我在对话中根据你的指令自动编排执行**，而不是写死脚本。

### 2.8 接入 agentos CLI

```bash
agentos yanghao                             # 交互选账号+蓝图
agentos yanghao --account douyin_01         # 指定账号
agentos yanghao --account douyin_01 --blueprint douyin_browse_v2  # 全指定
agentos yanghao --list                      # 列出账号和蓝图
agentos yanghao --status                    # 查看当前运行状态
```

### 2.9 跨机恢复

```
agent-sync/02_skills/matrix/  →  包含所有脚本和蓝图
agent-local/tools/matrix/     →  账号登录态、Cookies、Profiles

换机流程:
  agentos init                    → 安装技能+目录
  agentos restore backup.tar.gz   → 还原登录态
  agentos yanghao --status        → 验证可用
```

## 三、实施计划（建议）

1. **阶段1**: 设计并实现 `AtomOps` 原子操作层（含前置校验+后置锚点）
2. **阶段2**: 实现 `BrowserManager` 优雅启停
3. **阶段3**: 实现 `PageState` 页面状态机
4. **阶段4**: 重写蓝图格式（v3.0.0），加入验证锚点
5. **阶段5**: 实现 `YanghaoOrchestrator` 调度器
6. **阶段6**: 接入 agentos CLI 和 WorkBuddy 技能
7. **阶段7**: 全面测试三账号 + 跨机恢复

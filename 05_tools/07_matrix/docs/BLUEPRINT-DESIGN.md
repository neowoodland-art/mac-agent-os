# Blueprint 蓝图设计规范 v1.0.0

> 最后更新：2026-05-01
> 设计目标：可组合、可验证、可追踪的脚本化操作流

## 一、设计原则

每个蓝图由若干 **原子操作步骤** 组成，每个步骤必须记录：

```
前置条件 (pre-condition)  →  执行操作  →  后置条件 (post-condition)
     ↑                          ↓
     状态验证锚点           状态验证锚点
```

## 二、步骤格式

```json
{
  "step_id": 1,
  "op": "goto_home",
  "args": {},
  
  "pre": {
    "page_mode": ["unknown", "grid", "player", "search"],
    "login_required": false,
    "check": []
  },
  
  "post": {
    "page_mode": "grid",
    "anchors": ["alink-item"],
    "video_found": false,
    "description": "到达首页卡片列表"
  },
  
  "verify": {"mode": "anchor", "anchor": "grid_page", "timeout": 15},
  "on_fail": "retry(2)"
}
```

## 三、预定义页面模式

| 模式 | 锚点元素 | 描述 |
|------|---------|------|
| `unknown` | 无 | 未知/空白页 |
| `grid` | `[data-e2e="alink-item"]` | 首页卡片列表 |
| `player` | `[data-e2e="video-player-digg"]` | 视频播放器（带点赞/收藏按钮） |
| `search` | `[data-e2e="searchbar-input"]` | 搜索页 |
| `login_popup` | `[class*="login"]` 覆盖层 | 登录弹窗 |

## 四、预定义的原子操作

| 操作 | 前置条件 | 后置条件 | 说明 |
|------|---------|---------|------|
| `goto_home` | 任意 | `grid` | 导航到首页，激活手机模式 |
| `search(keyword)` | `grid` | `search` | 输入关键词搜索 |
| `open_video` | `grid` / `search` | `player` | 打开第一个找到的视频 |
| `like` | `player` | `player`(已赞) | 点赞当前视频 |
| `collect` | `player` | `player`(已收藏) | 收藏当前视频 |
| `next_video` | `player` | `player`(新视频) | 切换下一条（手机模式：全局流） |
| `comment(text)` | `player` + 登录 | `player`(已评论) | 输入评论并发送 |
| `go_back` | `player` | `grid` / `search` | 返回上一页 |
| `wait_watch(seconds)` | `player` | `player` | 观看一段时间 |
| `scroll_feed` | `grid` | `grid` | 首页滚动 |

## 五、完整流程示例：douyin_nurture_v1

```
start: unknown
  │
  ├── goto_home          (pre:unknown  → post:grid)
  │     └── 激活手机模式：设UA→导航→刷新→等渲染
  │
  ├── search(关键词)     (pre:grid     → post:search)
  │
  ├── open_video         (pre:search   → post:player)
  │
  ├── like               (pre:player   → post:player)
  ├── wait_watch(8s)     (pre:player   → post:player)
  │
  ├── next_video         (pre:player   → post:player)   ← 手机模式全局流
  │
  ├── like               (pre:player   → post:player)
  ├── collect            (pre:player   → post:player)
  │
  ├── go_back            (pre:player   → post:search)
  │
  └── open_video         (pre:search   → post:player)
       ├── like
       ├── collect
       └── next_video
```

## 六、状态持久化

每次养号运行后，生成 `.state.json` 记录：

```json
{
  "run_id": "20260501_093000",
  "account": "douyin_01",
  "blueprint": "douyin_nurture_v1",
  "steps": [
    {"step": 1, "op": "goto_home", "pre": "unknown", "post": "grid", "success": true}
  ],
  "login_method": "profile",
  "device_mode": "mobile_tablet",
  "duration_sec": 76
}
```

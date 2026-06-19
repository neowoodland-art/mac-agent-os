# Matrix 养号系统 — 全面架构文档 v2.2

> **最后更新**：2026-05-10  
> **作者**：Claw  
> **核心原则**：原子操作 × 状态机 × 唯一特征码 × 蓝图链

---

## 0. 总架构哲学

每个操作都是一条因果链：
```
[唯一前置状态] → [原子操作] → [唯一后置状态]
         ↑                          ↓
   上一个操作的后置           下一个操作的前置
```

**关键规则**：
1. 每个状态必须有**唯一的特征码组合**（URL + DOM锚点 + video数量 + 其他）
2. 每个操作执行前**必须先验证前置状态**
3. 每个操作执行后**必须验证后置状态**
4. 验证失败 → 不执行操作，先恢复到一个已知状态
5. 所有状态可查询、可追踪、可恢复

---

## 1. 完整状态机

### 1.1 状态定义与特征码

| 状态ID | 特征码 | 描述 |
|--------|--------|------|
| `INIT` | 浏览器刚启动，无页面 | 初始态 |
| `LOGIN` | URL=`douyin.com` + sessionid Cookie 存在 + `[data-e2e="user-avatar"]` 可见 | 已登录首页 |
| `HOME_GRID` | URL=`douyin.com/jingxuan` + `[data-e2e="alink-item"]` >= 3 + video=1（背景） | 精选页卡片列表 |
| `HOME_RECOMMEND` | URL=`douyin.com/?recommend=1` + `[data-e2e="alink-item"]` >= 3 | 推荐页卡片列表 |
| `VIDEO_PLAYER` | URL 含 `/video/` 或 `modal_id` + video>=2 + `[data-e2e="video-player-digg"]` 存在 | 视频播放页 |
| `COMMENT_PANEL` | `VIDEO_PLAYER` + `[data-e2e="comment-list"]` 可见 + `.public-DraftEditor-content` 存在 | 评论区已打开 |
| `INPUT_FOCUSED` | `COMMENT_PANEL` + `document.activeElement` 是 `.public-DraftEditor-content` + 光标闪烁 | 输入框已聚焦 |
| `TEXT_ENTERED` | `INPUT_FOCUSED` + `.public-DraftEditor-content` 的 `textContent.length > 0` | 文字已输入 |
| `COMMENT_SENT` | 评论已发送 + `[data-e2e="comment-list"]` 内含刚发的文本 | 评论已发送 |
| `SEARCH` | URL 含 `/search/` + `[data-e2e="searchbar-input"]` | 搜索结果页 |
| `VERIFY_CODE` | `.second-verify-panel` 或 `input[placeholder*="验证码"]` 可见 | 验证码弹窗 |
| `UNKNOWN` | 无法匹配任何已知特征码 | 未知状态 |

### 1.2 状态迁移图

```
INIT → LOGIN → HOME_GRID → VIDEO_PLAYER → COMMENT_PANEL → INPUT_FOCUSED → TEXT_ENTERED → COMMENT_SENT
       ↓            ↓              ↓              ↓               ↓               ↓
     HOME_GRID   SEARCH     ←回首页→        VERIFY_CODE    ←聚焦失败→      发送失败→
       ↓                                                                       ↑
    VIDEO_PLAYER ←—— 点卡片/导航视频URL ————————————————————————————————————————
```

### 1.3 状态检测函数

核心检测函数 `detect_state(page)` 返回当前状态ID：

```python
async def detect_state(page) -> str:
    """返回当前状态ID（唯一可识别）"""
    # 检测优先级：从最具体到最通用
    # 1. 验证码弹窗
    if has_verify_popup: return "VERIFY_CODE"
    # 2. 评论发送成功
    if has_comment_list_with_text: return "COMMENT_SENT"
    # 3. 文字已输入
    if editor_has_text: return "TEXT_ENTERED"
    # 4. 输入框聚焦
    if editor_is_focused: return "INPUT_FOCUSED"
    # 5. 评论区打开
    if comment_panel_visible: return "COMMENT_PANEL"
    # 6. 视频播放
    if video_player_active: return "VIDEO_PLAYER"
    # 7. 搜索结果
    if search_page: return "SEARCH"
    # 8. 首页/推荐
    if home_page: return "HOME_GRID" / "HOME_RECOMMEND"
    # 9. 已登录
    if logged_in: return "LOGIN"
    return "UNKNOWN"
```

---

## 2. 原子操作完整清单

每个原子操作 = (名称, 前置状态, 操作, 后置状态, 超时, 重试策略)

### 2.1 登录段

| 原子操作 | 前置 | 操作 | 后置 | 特征码变化 |
|---------|------|------|------|-----------|
| `navigate_login` | `INIT` | goto douyin.com → 等待页面加载 | `LOGIN` | URL→douyin + sessionid存在 |

### 2.2 首页段

| 原子操作 | 前置 | 操作 | 后置 | 特征码变化 |
|---------|------|------|------|-----------|
| `goto_home` | `LOGIN`/任意 | 导航到 douyin.com/?recommend=1 | `HOME_GRID` | URL→jingxuan + alink-item≥3 |
| `click_video_card` | `HOME_GRID` | 双击 `.discover-video-card-item` 或 `[data-e2e="alink-item"]` | `VIDEO_PLAYER` | video≥2 + `/video/` 或 player UI |
| `search_keyword` | `HOME_GRID` | 输入关键词+Enter | `SEARCH` | URL→/search/ |
| `click_search_result` | `SEARCH` | 点击第一个结果卡片 | `VIDEO_PLAYER` | video≥2 |
| `scroll_feed` | `HOME_GRID` | 鼠标滚轮/键盘下滑 | `HOME_GRID` | URL不变，卡片刷新 |

### 2.3 视频播放段

| 原子操作 | 前置 | 操作 | 后置 | 特征码变化 |
|---------|------|------|------|-----------|
| `wait_watch` | `VIDEO_PLAYER` | 等待N秒 | `VIDEO_PLAYER` | video 内容变化(可选) |
| `like_video` | `VIDEO_PLAYER` | 按Z/点digg按钮 | `VIDEO_PLAYER` | digg_state→digged |
| `collect_video` | `VIDEO_PLAYER` | 点收藏按钮 | `VIDEO_PLAYER` | 收藏状态变化 |
| `follow_author` | `VIDEO_PLAYER` | 按G/点关注 | `VIDEO_PLAYER` | 关注按钮变化 |
| `next_video` | `VIDEO_PLAYER` | 键盘ArrowDown / 滚轮 | `VIDEO_PLAYER` | video.src变化 |
| `open_comments` | `VIDEO_PLAYER` | 按X / 点评论图标 | `COMMENT_PANEL` | comment-list可见 + .public-DraftEditor-content存在 |

### 2.4 评论段

| 原子操作 | 前置 | 操作 | 后置 | 特征码变化 |
|---------|------|------|------|-----------|
| `focus_editor` | `COMMENT_PANEL` | Playwright locator双击 `.public-DraftEditor-content` | `INPUT_FOCUSED` | activeElement=编辑器 |
| `type_comment` | `INPUT_FOCUSED` | `page.keyboard.type()` 逐字输入 | `TEXT_ENTERED` | editor textContent>0 |
| `send_comment` | `TEXT_ENTERED` | 点击发送按钮 / Ctrl+Enter / Alt+Enter | `COMMENT_SENT` / `VERIFY_CODE` | comment-list含文本 |
| `close_comments` | `COMMENT_PANEL` | 按X / Escape | `VIDEO_PLAYER` | comment-list消失 |

### 2.5 恢复段

| 原子操作 | 前置 | 操作 | 后置 | 特征码变化 |
|---------|------|------|------|-----------|
| `recover_home` | 任意 | 导航到 douyin.com → 等待卡片加载 | `HOME_GRID` | URL+卡片 |
| `recover_video` | `HOME_GRID`/任意 | 点卡片进入视频 | `VIDEO_PLAYER` | video≥2 |
| `recover_comments` | `VIDEO_PLAYER` | 开评论（键盘+DOM双策略） | `COMMENT_PANEL` | comment-list可见 |

---

## 3. 完整蓝图链：评论流程

```
┌─────────────────────────────────────────────────────────┐
│                  蓝图：douyin_comment_send               │
├─────────────────────────────────────────────────────────┤
│ Step 1: goto_home                                      │
│   pre:  INIT or any       post: HOME_GRID              │
│   anchor: URL=jingxuan + alink-item≥3                  │
│   fail: 重试3次，截图                                     │
├─────────────────────────────────────────────────────────┤
│ Step 2: click_video_card                               │
│   pre:  HOME_GRID          post: VIDEO_PLAYER          │
│   anchor: video≥2 + player UI                          │
│   操作: 双击 .discover-video-card-item 或 alink-item     │
│   fail: goto_home → 重试                                  │
├─────────────────────────────────────────────────────────┤
│ Step 3: open_comments                                  │
│   pre:  VIDEO_PLAYER      post: COMMENT_PANEL          │
│   anchor: comment-list可见 + Draft-editor存在             │
│   操作: 键盘X / DOM点评论图标 / 键盘x                      │
│   fail: 恢复VIDEO_PLAYER → 重试                           │
├─────────────────────────────────────────────────────────┤
│ Step 4: focus_editor                                   │
│   pre:  COMMENT_PANEL     post: INPUT_FOCUSED          │
│   anchor: activeElement = .public-DraftEditor-content   │
│   操作: Playwright locator 双击编辑器                      │
│   兜底: DOM focus + click / 坐标(479,687)双击             │
│   fail: 恢复COMMENT_PANEL → 重试                          │
├─────────────────────────────────────────────────────────┤
│ Step 5: type_comment                                   │
│   pre:  INPUT_FOCUSED     post: TEXT_ENTERED           │
│   anchor: editor.textContent.length > 0                │
│   操作: page.keyboard.type(text, delay=40)              │
│   兜底: execCommand('insertText')逐字符注入               │
│   等待: 1.5s 让 React 处理（发送按钮出现）                  │
├─────────────────────────────────────────────────────────┤
│ Step 6: send_comment                                   │
│   pre:  TEXT_ENTERED      post: COMMENT_SENT           │
│   anchor: comment-list含刚发的文本                        │
│   操作: 找发送按钮点击 / Ctrl+Enter / Alt+Enter           │
│   兜底: 3次尝试找按钮 → 键盘兜底                            │
│   验证: 检查 [data-e2e="comment-list"] 内文本             │
│   fail: 检测 VERIFY_CODE                                 │
├─────────────────────────────────────────────────────────┤
│ Step 7: goto_home (下一轮)                              │
│   pre:  COMMENT_SENT      post: HOME_GRID              │
│   操作: 导航到 douyin.com                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 4. 数据表结构

### `atomic_ops` — 原子操作注册表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| op_name | TEXT UNIQUE | 操作名 |
| description | TEXT | 描述 |
| action_type | TEXT | click/nav/key/eval/wait |
| target | TEXT | 操作目标(选择器/键名/URL) |
| pre_state | TEXT | 前置状态ID |
| post_state | TEXT | 后置状态ID |
| timeout | INTEGER | 超时秒数 |
| retry | INTEGER | 重试次数 |
| verify_rule | TEXT | 后置验证规则(JSON) |
| created_at | DATETIME | |

### `anchor_rules` — 状态特征码规则

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| state_name | TEXT | 状态ID |
| field | TEXT | 检测字段(url/videoCount/selector等) |
| operator | TEXT | eq/neq/gt/gte/lt/lte/includes |
| value | TEXT | 期望值 |
| logic_group | INTEGER | 同一组AND，不同组OR |
| active | BOOLEAN | |
| created_at | DATETIME | |

### `state_transitions` — 合法状态迁移

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| from_state | TEXT | 起始状态 |
| to_state | TEXT | 目标状态 |
| via_op | TEXT | 通过哪个操作 |
| weight | INTEGER | 权重(优先级) |

### `action_logs` — 操作执行日志

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| execution_id | TEXT | 执行批次 |
| identity | TEXT | 账号ID |
| op_name | TEXT | 操作名 |
| pre_state | TEXT | 执行前状态 |
| post_state | TEXT | 执行后状态 |
| success | BOOLEAN | |
| duration_ms | INTEGER | |
| error | TEXT | |
| created_at | DATETIME | |

### `blueprints` — 蓝图定义

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | 蓝图ID |
| name | TEXT | 名称 |
| version | TEXT | 版本 |
| steps | JSON | 步骤序列 |
| created_at | DATETIME | |

---

## 5. 关键选择器清单

### 5.1 页面检测

| 检测项 | 选择器/代码 | 说明 |
|--------|-------------|------|
| 视频播放页 | `document.querySelectorAll('video').length >= 2` + `[data-e2e="video-player-digg"]` | video≥2 + player按钮 |
| 评论区打开 | `[data-e2e="comment-list"]` + `.public-DraftEditor-content` | 列表+编辑器都存在 |
| 输入框聚焦 | `document.activeElement === document.querySelector('.public-DraftEditor-content')` | activeElement是编辑器 |
| 输入框有内容 | `.public-DraftEditor-content.textContent.length > 0` | 编辑器内有文字 |
| 验证码弹窗 | `.second-verify-panel` / `input[placeholder*="验证码"]` | |
| 首页卡片 | `[data-e2e="alink-item"]` / `.discover-video-card-item` | |

### 5.2 操作目标

| 操作 | 方式 | 目标 |
|------|------|------|
| 进入视频 | Playwright locator双击 | `.discover-video-card-item` 或 `[data-e2e="alink-item"]` |
| 打开评论 | 键盘x / DOM 点 | `[data-e2e="video-comment-count"]` 或 `[data-e2e="feed-comment-icon"]` |
| 聚焦编辑器 | Playwright locator双击 | `.public-DraftEditor-content` |
| 输入文字 | `page.keyboard.type(text)` | 已聚焦的activeElement |
| 发送 | DOM找按钮点击 | 按钮含"发送"/上箭头 / Ctrl+Enter / Alt+Enter |

---

## 6. 已校准配置

| 参数 | 窗口 | 值 | 校准日期 |
|------|------|-----|---------|
| 输入框中心X | 702×783 | 479 | 2026-05-10 (实测算) |
| 输入框中心Y | 702×783 | 687 | 2026-05-10 (实测算) |
| 离右边缘 | 702 | 223px | 2026-05-10 |
| 离底边缘 | 783 | 96px | 2026-05-10 |
| 编辑器选择器 | - | `.public-DraftEditor-content` | 2026-05-10 |

---

## 7. 已知问题与修复记录

| 问题 | 状态 | 根因 | 修复 |
|------|------|------|------|
| `a[href*="/video/"]` 不存在 | ✅ 已修 | 抖音用JS点击事件，不用a标签 | 改用 `[data-e2e="alink-item"]` |
| `_detect_page_state` 太严格 | ✅ 已修 | 要求video≥2+playerUI才判player | 简化：有video就算player |
| `KeyX` 不生效 | ✅ 已修 | 没先点视频区域获取焦点 | 加 `_ensure_video_focused()` 再按x |
| 焦点检测在两快键之间 | ✅ 已修 | `page.evaluate` 干扰焦点 | 删除中间的detect调用 |
| 评论验证假阳性 | ✅ 已修 | `body.innerText.includes` 命中input内容 | 改查 `[data-e2e="comment-list"]` |
| execCommand不触发React | ⚠️ 待测 | Draft.js拦截DOM修改 | 改用 `page.keyboard.type()` |
| Camoufox profile lock | ⚠️ 待修 | 强杀不释放 .parentlock | 每次启动前检测+清理 |

---

## 8. 后续开发规范

1. **任何修改前先确认状态** — 读当前状态ID，只执行当前状态允许的操作
2. **一次只改一个原子操作** — 不改整条链，改完就测
3. **改完更新文档** — 状态机、蓝图、选择器、配置同步更新
4. **所有坐标必须从配置读** — 不硬编码，`ui_layout.py` 统一管理
5. **验证防假阳性** — 检查特定元素，不用 `body.innerText.includes()`
6. **双击之间不插操作** — 不调用 `page.evaluate` 或其他可能干扰焦点的操作

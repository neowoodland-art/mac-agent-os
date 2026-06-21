# AgentOS 原子操作架构审计与重构方案

## 一、旧代码设计原则（提炼自旧版 runner.py / interact.py）

### 1.1 每步操作 = 状态机三要素

```
[前置状态检测] → [操作执行] → [后置状态验证]
         ↓             ↓              ↓
   当前在哪个页面？  执行操作   操作是否真的生效了？
```

**旧代码实现**（`_ensure_player_state`、`CommentStateMachine`）：
```python
# 前置检测
state = await _detect_page_state(page)
# 只有确认在播放页才执行操作
if state not in ("player", "search_player"):
    recovered = await _ensure_player_state(...)
# 执行
await page.keyboard.press("KeyZ")
# 后置验证
assert await _check_anchor(page, 'video_page')
```

### 1.2 锚点系统（`_check_anchor`）

| 锚点 | 检测方式 | 作用 |
|:-----|:---------|:-----|
| `video_page` | `video` 元素 > 0 | 确认在视频播放页 |
| `home_page` | `.discover-video-card-item` > 0 | 确认在首页feed |
| `video_playing` | `!video.paused && readyState > 0` | 确认视频在播放 |
| `has_videos` | `a[href*="/video/"]` > 0 | 页面有视频链接 |

### 1.3 评论区状态机（`CommentStateMachine`）

```
closed → panel_open → input_focused → text_entered → sent
                ↓           ↓               ↓
          键盘x打开     检测activeElement  检测textContent
          验证has_panel  验证isEditable    验证has_text
```

**核心：每一步都调用 `detect()` 验证状态是否真的变化了。**

### 1.4 行为链（`CHAINS`）

旧代码用**行为链**而非固定步骤模板：
```python
CHAINS = [
    [('open_comment', 'KeyX'),
     ('type_comment', 'input'),   # 调用 _send_comment 状态机
     ('wait_10s', 'wait'),
     ('scroll_comment', 'scroll')],
]
```

每个链中的操作都是**键盘快捷键优先**（KeyZ/KeyX/KeyG），DOM 兜底。

---

## 二、当前新代码的问题审计

| 问题 | 表现 | 根因 |
|:-----|:-----|:------|
| **无前置状态检测** | open_video 在首页找不到卡片→硬等30s→失败 | 不先检测页面状态就直接找元素 |
| **无后置验证** | post_comment 返回"sent"但评论没发出去 | 不检查评论区是否出现了刚发的文字 |
| **无锚点系统** | 所有操作都用 CSS 类名硬匹配（CSS modules 不可靠） | 没有用 video/card 等特征判断 |
| **状态机缺失** | 点赞/收藏/评论等操作的执行结果和页面实际脱节 | 没有 `detect()` 验证状态变化 |
| **DOM 优先于键盘** | 所有操作先找 DOM 元素，找不到才 fallback | 旧代码用键盘快捷键为主，更可靠 |
| **无回退策略** | 一个方法失败就放弃或硬等30s | 旧代码有3层回退（键盘→DOM→坐标） |

---

## 三、重构方案

### 3.1 新原子操作模板

```python
async def atomic_like(page) -> OpResult:
    """点赞操作（前后状态检测模板）"""
    # 1. 前置状态检测
    state = await detect_page_state(page)
    if state not in ('player', 'search_player'):
        return OpResult('like', False, f'不在播放页(state={state})')
    
    # 2. 操作执行（键盘优先）
    await page.keyboard.press('z')
    await asyncio.sleep(1)
    
    # 3. 后置验证（检测按钮状态变化）
    ok = await verify_like(page)  # 检测 data-e2e-state 或 toast
    if ok:
        return OpResult('like', True, '👍')
    
    # 4. 回退：DOM 点击
    btn = page.locator('[data-e2e="video-player-digg"]')
    if await btn.count() > 0:
        await btn.click()
        await asyncio.sleep(1)
        ok = await verify_like(page)
    
    return OpResult('like', ok, '👍' if ok else '-')
```

### 3.2 统一状态检测函数

```python
async def detect_page_state(page) -> str:
    """检测当前页面状态"""
    url = page.url
    video_count = await page.evaluate("document.querySelectorAll('video').length")
    cards = await page.evaluate(
        "document.querySelectorAll('.discover-video-card-item, [data-e2e=\"alink-item\"]').length"
    )
    
    if video_count > 0 and '/video/' in url:
        return 'player_full'        # B模式：独立播放页
    if video_count > 0 and 'modal_id' in url:
        return 'player_modal'       # A模式：弹窗播放
    if video_count > 0:
        return 'player_unknown'     # 有视频，模式待定
    if '/search/' in url:
        return 'search'
    if '/user/' in url:
        return 'profile'
    if cards > 0:
        return 'grid'               # 首页feed
    return 'unknown'
```

### 3.3 每个操作绑定状态依赖

| 操作 | 前置状态要求 | 后置验证方式 |
|:-----|:------------|:-------------|
| `goto_home` | (任意) | state → 'grid' |
| `open_video` | 'grid' | state → 'player_*' |
| `like` | 'player_*' | 按钮state变化或toast出现 |
| `collect` | 'player_*' | 按钮state变化或toast出现 |
| `follow` | 'player_*' | 按钮文字从"关注"变"已关注" |
| `open_comments` | 'player_*' | state → 'comment_panel_open' |
| `post_comment` | 'comment_panel_open' | comment_list中出现刚发的文字 |
| `close_comments` | 'comment_panel_open' | state回到'player_*' |
| `next_video` | 'player_*' | modal_id或video内容变化 |
| `search` | (任意) | state → 'search' |
| `go_back` | (任意) | URL或state变化 |

---

## 四、实施计划

### Phase 1：基础设施（1-2小时）
1. 实现 `detect_page_state()` — 统一状态检测
2. 实现 `verify_*()` 系列 — 每个操作的后置验证函数
3. 实现 `ensure_page_state(target)` — 如果不在目标状态则导航过去

### Phase 2：重写原子操作（2-3小时）
4. 按模板重写 `douyin_ops.py` 中所有操作
5. 按模板重写 `ops/xhs_ops.py` 中所有操作
6. 移除所有无验证的假成功返回

### Phase 3：测试验证（1-2小时）
7. 逐步测试每个操作（用户交互模式）
8. 修复各平台的特定选择器/DOM差异

---

以上是完整的审计和方案。你要我按这个方向执行吗？

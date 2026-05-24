# XHS 小红书原子操作手册

> 版本: v2 | 更新: 2026-05-24 | 基于 Playwright + Camoufox 实测验证

---

## 一、基础定位规则

### 1.1 笔记卡片定位

| 元素 | 选择器 | 说明 |
|------|--------|------|
| 卡片容器 | `section.note-item` | 取 bounding rect 用此元素 |
| 卡片链接 | `section.note-item a` | 取 href 用此元素（⚠️ bounding rect = 0） |
| 卡片标题 | `.title, [class*=title]` | 嵌套在 section 内的标题 |

**关键坑**：`section.note-item a` 的 `getBoundingClientRect()` 返回 `(0,0,0,0)`。必须先取父级 `section.note-item` 的 rect，再从中取 `a` 标签提取 `href`。

### 1.2 笔记详情定位

| 元素 | 选择器 | 说明 |
|------|--------|------|
| 详情遮罩 | `.note-detail-mask` | SPA 详情页容器（fixed，全屏覆盖） |
| 底部互动栏 | `.interactions` | 点赞/收藏/评论按钮的容器 |
| 点赞按钮 | `span.like-wrapper` | ✅ 实测可用，x > 视口 30% |
| 收藏按钮 | `span.collect-wrapper` | ✅ 实测可用，x > 视口 30% |
| 评论入口 | `.comment-btn` 等 | 底部栏评论按钮 |

**关键规则**：页面中有大量 `like-wrapper`（评论区每条回复都有）。**区分底部栏 vs 评论区按钮的特征**：底部栏按钮的 `x` > 视口宽度 × 30%（约 210px 以上），评论区按钮在左侧（x ≈ 60~100px）。

---

## 二、锚点检测系统

### 2.1 `is_note_detail_mode()` — 笔记详情 vs 图片查看器

**三要素综合判断**：
1. **has_mask** — 存在 `.note-detail-mask` 元素
2. **has_interact_bar** — 底部互动栏按钮可见（like-wrapper 的 x > viewW×0.3）
3. **has_note_url** — URL 匹配 `/explore/{20位以上十六进制ID}`

```
is_detail = has_mask && has_interact_bar && has_note_url
```

**四种状态**：
| 状态 | 判断 | 说明 |
|------|------|------|
| 笔记详情模式 | mask + 互动栏 + URL | ✅ 可以执行互动 |
| 疑似图片查看器 | 有 mask 但无互动栏 | ❌ 需退出或重新导航 |
| 不在详情页 | 无 mask | ❌ 回到首页 |
| 未知状态 | 其他 | ❌ 截图+兜底 |

### 2.2 其他锚点

| 锚点类型 | 检测方式 |
|----------|----------|
| 首页已加载 | `section.note-item` 存在 |
| 笔记详情锚点 | `.note-detail-mask` 存在 |
| 评论区打开 | `.comment-section` 存在 |
| 搜索页 | `.search-result` 存在 |
| 页面加载完成 | `#app` 存在 |

---

## 三、原子操作（按流程顺序）

### 3.1 导航 `goto_home()`

```
前置状态: 浏览器刚启动（about:blank）
操作:      page.goto("https://www.xiaohongshu.com/explore")
后置状态: URL = /explore, 页面渲染完成
锚点:     #app 存在
超时:     20s → 30s fallback
```

### 3.2 关闭登录弹窗 `dismiss_login_modal()`

```
前置状态: 页面已加载，可能出现登录弹窗
操作:     JS: display:none 所有 modal/dialog/mask/position:fixed+zIndex>100
后置状态: 弹窗不可见
锚点:     无（可选）
```

### 3.3 获取卡片列表 `get_note_cards()`

```
前置状态: 首页已加载
操作:     JS: querySelectorAll('section.note-item') 取 index/href/rect
后置状态: 返回 List[dict]（不为空）
返回:     [{index, href, title, rect:{x,y,w,h}}]
⚠️ 注意:  过滤 rect.w < 10 的无效卡片
```

### 3.4 点击卡片进入详情 `click_note_card()`

```
前置状态: 首页已加载，有卡片数据
操作:
  1. 获取 section.note-item 的 bounding rect
  2. scrollIntoView({block: 'center'})
  3. 重新获取 rect（滚动后坐标变化）
  4. page.mouse.move(cx, cy, steps=5~12)     ← Playwright 原生鼠标
  5. 单次 page.mouse.click(cx, cy)           ← ⚡ 非双击！
  6. 等待 3~5s（SPA 过渡）
  7. 锚点: is_note_detail_mode()
     - ✅ → 返回 URL
     - ❌ → fallback page.goto(href)
后置状态: 笔记详情页
锚点:     is_note_detail_mode() = true
⚠️ 注意:
  - 用 section.note-item 取 rect（不是 a 标签）
  - 单次单击（双击触发图片查看器）
  - 随机选卡片（非总点第一张）
```

### 3.5 分析互动按钮 `analyze_interact_page()`

```
前置状态: 笔记详情页（is_note_detail_mode = true）
操作:     JS: 取 like-wrapper / collect-wrapper 位置和可见性
返回:     { like: {x,y,w,h,visible,isActive,cls,text},
              collect: {x,y,w,h,visible,isActive,cls,text} }
⚠️ 注意:  用 x > viewW*0.3 过滤出底部栏按钮
```

### 3.6 L 形鼠标移动 `mouse_move_l_shape()`

```
前置状态: 任何（鼠标在当前位置）
操作:     三段式 page.mouse.move():
  L1: (cx, cy) → (cx, safeY=100)     — 垂直上移到安全区
  L2: (cx, safeY) → (targetX, safeY) — 水平移动到目标上方
  L3: (targetX, safeY) → (targetX, targetY) — 垂直下移到目标
  每段 steps=3~4，总 steps≈8~12
后置状态: 鼠标在目标坐标
⚠️ 注意:
  - 安全区 Y=100 在输入框上方
  - 避免直线移动穿过评论区输入框
```

### 3.7 点赞 `like()`

```
前置状态: 笔记详情页，底部栏可见
操作:
  1. get_bottom_bar_buttons_js() → 取 like 按钮位置
  2. 如果 isActive → 跳过（已点赞）
  3. 如果不可见 → scrollIntoView({block:'center'})
  4. mouse_move_l_shape(like.x, like.y)
  5. page.mouse.click(like.x, like.y)
  6. 等待 1.5~2.5s
  7. 验证: isActive 变化 → ✅
  8. 失败则重试一次
后置状态: 已点赞（class 含 like-active）
锚点:     like-wrapper.isActive = true
⚠️ 注意:
  - 使用 page.mouse.click（非 element.click / JS dispatchEvent）
  - 必须先 scrollIntoView 确保按钮在视口内
```

### 3.8 收藏 `collect()`

```
前置状态: 笔记详情页，底部栏可见
操作:
  1. get_bottom_bar_buttons_js() → 取 collect 按钮位置
  2. 如果 isActive → 跳过（已收藏）
  3. 如果不可见 → scrollIntoView({block:'center'})
  4. mouse_move_l_shape(collect.x, collect.y)
  5. page.mouse.click(collect.x, collect.y)
  6. 等待 1.5~2.5s
  7. 验证: isActive 变化 或 计数增加 → ✅
  8. 失败则重试一次
后置状态: 已收藏（class 含 active）
锚点:     collect-wrapper.isActive = true 或 text 计数 +1
⚠️ 注意: 和点赞流程一致，共用 L 形路径
```

### 3.9 拟人滚动 `scroll_feed_human()`

```
前置状态: 首页/发现页
操作:
  循环 N 次（默认 2~3 屏）:
    page.mouse.wheel(0, dist=200~500)    ← 鼠标滚轮
    随机停顿 1~3s（40% 概率）
后置状态: 瀑布流已滚动
⚠️ 注意:
  - 用 page.mouse.wheel（非 JS 滚动）
  - 间隔随机抖动（非固定间隔）
  - 不采用双重滚动（mouse.wheel + JS scrollBy）
```

### 3.10 浏览笔记详情 `browse_note_detail()`

```
前置状态: 笔记详情页
操作:
  - 视频笔记: 等待 video 播放，随机观看时长
  - 图文笔记: 分段 scrollBy(50~150px)，每段停顿 1~2.5s
后置状态: 笔记内容已浏览
返回:     实际浏览秒数
```

### 3.11 返回首页 `go_back_to_home()`

```
前置状态: 笔记详情页
操作:
  方式1: page.go_back()
  方式2: page.goto(/explore)
后置状态: URL = /explore
锚点:     section.note-item 存在
```

---

## 四、评论状态机

### 4.1 状态定义

```
closed → panel_open → input_focused → text_entered → sent → verified
```

### 4.2 各步骤

| 步骤 | 方法 | 操作 | 锚点 |
|------|------|------|------|
| 打开评论区 | `open_panel()` | 点击 comment-entry 或滚动到评论区 | `.comment-section` 存在 |
| 聚焦输入框 | `focus_input()` | click 输入框 或 JS focus() | state = input_focused |
| 输入文本 | `enter_text()` | pbcopy + Meta+V（系统级） | 输入框包含输入文本 |
| 发送 | `send()` | Enter 或点击发送按钮 | 输入框清空 |
| 验证 | `verify()` | 检查评论区是否出现评论 | 输入框清空 或 评论可见 |

### 4.3 关键规则

- **输入方式**：pbcopy（剪贴板）→ `Meta+V`（系统级粘贴），和抖音一致
- ⚠️ XHS 输入框可能是 `contenteditable div` 或 `input`，pbcopy + Meta+V 对两种都有效
- **发送方式**：优先点击发送按钮，兜底 Enter 键
- **验证**：发送后检查输入框清空（比检查评论列表更可靠）

---

## 五、交互引擎选择

| 操作类型 | 推荐方式 | 说明 |
|----------|----------|------|
| 点击卡片 | `page.mouse.click()` | 单次单击 ✅ 实测最佳 |
| 点赞/收藏 | `page.mouse.click()` | 单次单击 ✅ 实测最佳 |
| 搜索框输入 | `search_input.fill()` | 常规文本输入无防检测 |
| 评论输入 | `pbcopy + Meta+V` | contenteditable div 专用 |
| 键盘事件 | `page.keyboard.press()` | Enter / Meta+V / Escape |
| 滚动 | `page.mouse.wheel()` | 拟人操作，优于 JS 滚动 |

**为什么不用 element.click() / JS dispatchEvent：**
- XHS SPA 可能屏蔽 JS 事件
- element.click() 不产生真实的 mousedown/mouseup/mousemove 事件序列
- page.mouse API 产生完整的事件序列，和真人操作一致

---

## 六、已知坑 & 解决方案

| 问题 | 现象 | 解决方案 |
|------|------|----------|
| a 标签 zero-rect | card.querySelector('a').getBoundingClientRect() = (0,0,0,0) | 用父级 section.note-item 取 rect |
| 双击触发图片查看器 | 第 2 次 click 打开全屏图片 | 单次单击 |
| like-wrapper 过多 | 页面中有大量 like-wrapper（评论区每条回复都有） | 用 x > viewW×0.3 过滤 |
| 鼠标路径穿过输入框 | 直线移动会经过评论区输入框 | L 形路径 |
| SPA 过渡延迟 | click 后页面需要时间加载 | 等待 3~5s |
| 图片查看器状态 | 没有互动栏、URL 可能不变 | is_note_detail_mode() 三要素判断 |

---

## 七、目录结构

```
ops/xhs/
├── __init__.py         — 模块导出
├── ATOMIC_OPS.md       — 本文档
├── selectors.py        — DOM 选择器 + JS 辅助函数
├── browse.py           — 浏览类操作
└── interact.py         — 交互类操作（点赞/收藏/关注/评论）
```

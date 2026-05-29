---
title: 小红书养号页面交互技术
tags: [xhs, browse, interaction, qr-wall, refresh, black-screen, ai-layout]
created: 2026-05-29
updated: 2026-05-29
nature: method
---

## 核心选择器

### 首页/瀑布流
- 瀑布流容器：`#app .layout.limit`
- 笔记卡片：`section.note-item`（DOM 分析确认）
- 卡片封面链接：`a.cover.mask.ld`
- 卡片图片：`a.cover.mask.ld img`

### 笔记详情页
- 详情容器：`.note-detail, [class*=note-detail], .note-page`
- 标题：`.title, h1, [class*=note-title]`
- 内容：`.content, [class*=content], .desc`

### 弹窗/遮罩
- 登录弹窗：`[class*=login], [class*=modal], [role=dialog], .reds-alert`
- 通用遮罩：`[class*=mask], [class*=overlay], [class*=modal]`

### 锚点验证
| 锚点类型 | 选择器 |
|----------|--------|
| 首页 | `section.note-item` |
| 笔记详情 | `.note-detail, [class*=note-detail], .title, h1` |
| 视频页 | `video` |
| 评论打开 | `.comment-section, [class*=comment-section]` |
| 搜索页 | `.search-result, [class*=search-result]` |

## JS 智能查找函数

### find_refresh_button_js()

三策略查找瀑布流页面右下角 FAB 刷新按钮：

1. **选择器匹配**：`button[class*="refresh"]`、`[class*="fab"]`、`[class*="floating"]` 等
2. **SVG 扫描**：查找包含旋转箭头路径的 SVG 元素（刷新图标 = arc + rotate 特征）
3. **fixed 定位过滤**：右下角区域（x > viewport 60%, y > viewport 60%）的可点击元素

返回 `{found, x, y, w, h, text, method}`

### find_qr_wall_back_button_js()

检测 QR 检测墙并定位返回首页按钮：

1. **QR 墙关键词检测**：body 文本包含"扫码"/"二维码"/"非常用登录"/"验证"等
2. **返回按钮匹配**：优先级排序 — "返回首页"(10) > "返回"(20) > "首页"(30) > "确定/我知道了"(50)
3. **候选过滤**：宽度/高度 > 5px（排除不可见元素），文本长度 < 15 字符

返回 `{found, x, y, w, h, text, priority}`

### dismiss_login_modal_js()

隐藏登录弹窗和固定定位遮罩层。设置 `display:none` 而非移除 DOM。

### get_note_cards_js()

获取瀑布流所有笔记卡片的 index、href、title、rect 信息。

## 鼠标模拟技术

### L 型鼠标路径（_l_shaped_click）

模拟真人鼠标移动轨迹：

```
起点(随机偏移) → 水平移动(5-10步) → 垂直移动(3-8步) → 微抖动(±2px) → 点击
```

- 每步延迟 10-30ms（随机），总耗时 100-400ms
- 起点偏移范围：x ±150px, y -100~+50px
- 限制在视口内（防止鼠标移出窗口）
- 微抖动模拟手指不稳

### 双击策略（聚焦→执行）

macOS 窗口激活限制下，点击需要先聚焦再执行：
1. 第一次点击 → 聚焦窗口（可能不触发元素事件）
2. 第二次点击 → 实际执行操作

## 常见问题与恢复策略

### 黑屏恢复

**现象**：瀑布流页面变黑，卡片不可见
**根因**：SPA 状态异常，非窗口移出屏幕
**恢复链**：

```
1. scroll_feed 回到顶部 → 检测卡片
2. click_bottom_nav_tab("发现") → 刷新页面状态
3. goto_home() → 直接导航兜底
```

### QR 检测墙恢复

**现象**：中央弹出大弹窗，提示"扫码"/"非常用登录"
**根因**：XHS 非常用登录检测触发，非登录状态失效
**恢复链**：

```
1. click_qr_wall_back_button() → 点弹窗上的"返回首页"按钮
2. click_bottom_nav_tab("发现") → 底部导航恢复
3. go_back_to_home() → 直接导航兜底
```

**重要区别**：QR 墙 ≠ 未登录。QR 墙是频控触发，多刷会恢复。未登录二维码弹窗是另一种情况。

### 首页锚点验证失败

```
1. click_refresh_button() → 点右下角物理刷新按钮（优先，模拟真人）
2. page.reload() → API 刷新（fallback）
3. init_anti_detection() → 重新初始化反检测
```

### AI-layout 兼容（A/B 测试）

**触发条件**：指纹分辨率 + DPR（低分屏 1920x1080 DPR=1.0 易触发）
**差异**：无顶部搜索栏、无 header-container、首卡 y 偏移 272px vs 144px
**兼容措施**：
- `search()`：标准输入框 → ALT 输入框 → URL fallback（三重降级）
- `click_search_result()`：标准选择器 → 通用 href 匹配
- 启动时自动检测布局版本（standard/ai-layout/unknown）

**指纹建议**：screen ≥ 1920x1080, DPR ≥ 1.25

## 登录检测规则

1. **顺序**：页面级登录检测 → dismiss_login_modal（先检测再关闭，否则误判）
2. **等待**：首页加载后等 5 秒（给弹窗渲染时间）
3. **关键词**："登录之后更精彩" / "扫码登录" / "手机号登录" / "请登录" / "立即登录"
4. **尺寸区分**：`getBoundingClientRect(width>200, height>100)` 区分导航栏 vs 模态弹窗

## 操作前状态检查清单

进入每轮养号前：
1. 首页锚点验证（`section.note-item` 存在）
2. 登录弹窗关闭
3. 反检测初始化
4. Cookie/Session 检查（非必需，未登录也可浏览）

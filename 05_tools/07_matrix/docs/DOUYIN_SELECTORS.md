# 抖音 Web 端选择器手册

> 扫描时间：2026-04-27 | 浏览器窗口：702×681 | CDP 端口：9222
> 连接方式：Patchright `connect_over_cdp` | 代理需绕过：`no_proxy=localhost,127.0.0.1`

---

## 键盘快捷键

| 键 | 功能 | 备注 |
|----|------|------|
| **Z** | 点赞 | 需英文输入法 |
| **X** | 打开/关闭评论 | |
| **F** | 关注作者 / 进直播间 | |
| **B** | 弹幕开关 | |
| **空格** | 播放/暂停 | |
| **↑** | 上一个视频 | |
| **↓** | 下一个视频 | |
| **Enter** | 搜索确认 / 评论发送 | |

---

## 全局元素

| 元素 | 选择器 | 备注 |
|------|--------|------|
| 搜索框 | `[data-e2e="searchbar-input"]` | type=input |
| 搜索按钮 | `[data-e2e="searchbar-button"]` | |
| 右上角头像 | `[data-e2e="live-avatar"]` | hover 弹出菜单 |
| 左侧导航 | `[data-e2e="douyin-navigation"]` | |

### 左侧导航栏

| 项目 | 大致位置(y) |
|------|-----------|
| 精选 | 64 |
| 推荐 | 124 |
| 搜索 | 184 |
| 关注 | 244 |
| 朋友 | 304 |
| 我的 | 364 |
| 直播 | 441 |
| 放映厅 | 501 |
| 短剧 | 561 |

---

## 视频播放页（推荐/关注）

### 互动按钮

| 操作 | 键盘 | 选择器 | 状态判断 |
|------|------|--------|---------|
| 点赞 | **Z** | `[data-e2e="video-player-digg"]` | `data-e2e-state`: `video-player-no-digged`(未赞) / `video-player-digged`(已赞) |
| 评论（打开） | **X** | `[data-e2e="feed-comment-icon"]` | |
| 收藏 | - | `[data-e2e="video-player-collect"]` | |
| 分享 | - | `[data-e2e="video-player-share"]` | |
| 关注/进直播 | **F** | `[data-e2e="feed-follow-icon"]` | |
| 更多 | - | `[data-e2e="video-play-more"]` | |

### 翻页

| 操作 | 键盘 | 选择器 |
|------|------|--------|
| 上翻视频 | **↑** | `[data-e2e="video-switch-prev-arrow"]` |
| 下翻视频 | **↓** | `[data-e2e="video-switch-next-arrow"]` |

### 播放控制

| 操作 | 键盘 | 备注 |
|------|------|------|
| 播放/暂停 | **空格** | |
| 弹幕开关 | **B** | |

---

## 评论区

> 按 X 或点击评论图标后，右侧弹出评论面板，视频从 570px 缩窄到 234px

| 元素 | 选择器 | 备注 |
|------|--------|------|
| 评论列表 | `[data-e2e="comment-list"]` | |
| 评论输入框 | `.public-DraftEditor-content` | Draft.js 富文本编辑器，contentEditable |
| 输入容器(聚焦态) | `.comment-input-container-focus` | 激活后添加此 class |
| 发送按钮 | `.commentInput-right-ct .WFB7wUOX` | 向上箭头图标 |
| 表情按钮 | `.commentInput-right-ct .BVMl8WNl` 第2个 | |
| 图片上传 | `.commentInput-right-ct .BVMl8WNl` 第1个 | |
| @提及 | `.commentInput-right-ct .BVMl8WNl` 第3个 | |
| 评论更多 | `[data-e2e="video-comment-more"]` | |
| 弹幕输入框 | `input[placeholder="发一条弹幕吧"]` | 非评论框，注意区分 |

### 评论操作流程

```
1. 按 X 打开评论面板
2. 点击 .public-DraftEditor-content 激活输入
3. 输入文字（type_into Draft.js 编辑器）
4. Enter 发送 / 点击发送按钮
5. 可能触发验证码弹窗
```

---

## 搜索结果页

**URL 格式**：`https://www.douyin.com/root/search/{关键词}?type=general`

### Tab 分类栏

| Tab | 选择器 | 备注 |
|-----|--------|------|
| 综合（激活） | `.NiqGqBbw` | 不同 class 表示激活态 |
| 视频/用户/直播 | `.t3OsOj2N` | |

### 子分类筛选

| 选择器 | 示例 |
|--------|------|
| `.neT9xRMd.vZeqhI2r` | 直播间、胃肠镜、中医院… |
| 激活态额外 class | `.Bp4xnVjA` |

### 显示模式

| 模式 | 选择器 |
|------|--------|
| 多列 | `.cSG1ckL8` |
| 单列 | `.cSG1ckL8.ltQEgur_` |

### 结果卡片

| 元素 | 选择器 | 备注 |
|------|--------|------|
| 卡片容器 | `.search-result-card` | 整卡可点击(cursor:pointer)，无 `<a>` 标签 |
| 视频封面 | `.videoImage` | 219×292 |
| 标题 | `.wSEoiOKC` | |
| 作者 | `.YebDknhI` | @username |
| 点赞数 | `.LUd60iMQ` | |
| 布局 | 3列网格 | x=31, x=276, x=521 |

### 点击第 N 个搜索结果

```python
cards = page.query_selector_all('.search-result-card')
cards[0].click()  # 第1个
```

---

## 关注页

**URL**：`https://www.douyin.com/follow`

### 左侧关注列表

| 元素 | 选择器 | 备注 |
|------|--------|------|
| 列表头 | `.mZ1rdREf` | "列表综合排序" |
| 我的关注 | `.IMOte1q1.mZ1rdREf` | "我的关注(N)" |
| 关注用户项 | `.ILK2RAD5` | 点击切换到该用户视频 |

### 右侧视频流

与推荐页结构相同，互动按钮选择器通用。

---

## 个人主页

**URL**：`https://www.douyin.com/user/self?showTab=post`

### 用户信息

| 元素 | data-e2e |
|------|----------|
| 用户详情 | `user-detail` |
| 用户信息 | `user-info` |
| 关注数 | `user-info-follow` |
| 粉丝数 | `user-info-fans` |
| 获赞数 | `user-info-like` |

### Tab 栏

| Tab | 位置(y) |
|-----|---------|
| 作品 | 221 |
| 推荐 | 221 |
| 喜欢 | 221 |
| 收藏 | 221 |
| 观看历史 | 221 |
| 稍后再看 | 221 |
| 我的预约 | 221 |
| AI 笔记 | 221 |

### 作品列表

| 元素 | data-e2e |
|------|----------|
| 作品列表 | `user-post-list` |
| 滚动列表 | `scroll-list` |

---

## 头像悬停菜单

**触发**：hover `[data-e2e="live-avatar"]`

**面板**：`.userMenuPanelShadowAnimation`（x≈360, 宽328）

| 菜单项 | 选择器 | 链接 |
|--------|--------|------|
| 用户名 | `.uz1VJwFY.e6huIECy` | → 个人主页 |
| 我的喜欢 | `.uz1VJwFY.espXX7re` 第1个 | → 喜欢 |
| 我的收藏 | `.uz1VJwFY.espXX7re` 第2个 | → 收藏 |
| 观看历史 | `.uz1VJwFY.espXX7re` 第3个 | → 历史 |
| 稍后再看 | `.uz1VJwFY.espXX7re` 第4个 | → 稍后再看 |
| 我的作品 | `.uz1VJwFY.espXX7re` 第5个 | → 作品 |
| 我的订单 | `.uz1VJwFY.VSHeqy7Q` | 无链接 |

---

## 验证码弹窗

> 评论后可能触发短信验证码

| 元素 | 选择器 | 备注 |
|------|--------|------|
| 遮罩 | `.second-verify-mask` | 全屏遮罩 |
| 面板 | `.second-verify-panel` | |
| 标题 | `.uc-ui-verify-new_header-title` | "接收短信验证码" |
| 关闭 | `.uc-ui-verify-new_header-close` | |
| 提示 | `.uc-ui-verify_sms-verify_content_desc` | 手机号脱敏 |
| 输入框 | `.uc-ui-verify_sms-verify_input` | |
| 获取验证码 | 面板内按钮 | |
| 验证按钮 | `.uc-ui-verify_sms-verify_button.primary` | 非 disabled 时可点 |
| 取消按钮 | `.uc-ui-verify_sms-verify_button.second` | |

---

## 技术备忘

### CDP 连接

```python
import os
os.environ['no_proxy'] = 'localhost,127.0.0.1'
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'

from patchright.async_api import async_playwright
async with async_playwright() as p:
    browser = await p.chromium.connect_over_cdp('http://localhost:9222')
    context = browser.contexts[0]
    page = context.pages[0]
```

### Draft.js 输入

评论框是 Draft.js 富文本编辑器，不能用普通 `fill()`，需用 `type_into()` 或 `press_sequentially()`：

```python
editor = page.locator('.public-DraftEditor-content')
await editor.click()
await editor.press_sequentially('评论内容')
```

### 起始页固定

每次操作从固定 URL 开始：`https://www.douyin.com/?recommend=1`

### SVG className

SVG 元素的 `className` 是 `SVGAnimatedString` 对象，非字符串。JS 中需用 `el.className.baseVal`。

### 点赞状态判断

```python
digg = page.locator('[data-e2e="video-player-digg"]')
state = await digg.get_attribute('data-e2e-state')
# "video-player-no-digged" = 未点赞
# "video-player-digged" = 已点赞
```

### 搜索卡片无 `<a>` 标签

搜索结果卡片通过 JS 事件跳转，需用 `card.click()` 而非导航链接。

# Matrix 养号系统 — 全量状态机目录 v2.3

> **方法**：逐状态交互采集特征码，先列框架，你导航到我采集。
> **目标**：每个状态有唯一特征码，不重复，不遗漏。

---

## 0. 环境变量（每次操作前必检）

| 环境因子 | 影响 | 检测方式 |
|---------|------|---------|
| 窗口宽度 | 布局、坐标 | `window.innerWidth` |
| 窗口高度 | 布局、坐标 | `window.innerHeight` |
| 窗口位置(left, top) | 鼠标事件路由 | `window.screenX/Y` |
| 窗口是否激活 | 键盘/鼠标事件是否可达 | AppleScript / `document.hasFocus()` |
| 登录态 | 是否可交互 | sessionid cookie + DOM头像 |
| 当前URL | 页面判定基础 | `location.href` |
| 页面title | 辅助判定 | `document.title` |

---

## 1. 状态大类（第一级分类）

我按"一眼就能看出来"的原则分大类。你看有没有漏的：

| 大类ID | 名称 | 特征（一瞥即可识别） |
|--------|------|-------------------|
| `BROWSER` | 浏览器层 | 浏览器启动/关闭/崩溃 |
| `LOGIN` | 登录相关 | 登录框/扫码/验证码 |
| `HOME` | 首页 | 精选/推荐/关注/朋友 |
| `SEARCH` | 搜索 | 搜索结果列表/搜索播放 |
| `PLAYER` | 视频播放 | 全屏/覆盖播放/横竖屏 |
| `COMMENT` | 评论 | 评论面板/输入框/发送 |
| `PROFILE` | 个人主页 | 自己/他人/作品/喜欢 |
| `LIVE` | 直播 | 直播间 |
| `COMPOSE` | 创作 | 发布/上传 |
| `VERIFY` | 验证 | 短信验证码/滑块 |
| `ERROR` | 异常 | 404/崩溃/网络断开 |

---

## 2. 逐大类的子状态（第二级）

### 2.1 `BROWSER` — 浏览器层

| 状态码 | 名称 | 特征码 |
|--------|------|--------|
| `B_INIT` | 浏览器刚启动 | 无页面，`about:blank` |
| `B_READY` | 浏览器就绪 | 抖音页面已加载 |
| `B_CRASH` | 浏览器崩溃 | 页面无法响应 |
| `B_LOCKED` | profile 锁冲突 | `.parentlock` 残留 |

### 2.2 `LOGIN` — 登录

| 状态码 | 名称 | 特征码 |
|--------|------|--------|
| `L_LOGGED_IN` | 已登录 | sessionid cookie + avatar icon |
| `L_LOGGED_OUT` | 未登录 | 无sessionid、右上角显示"登录"按钮 |
| `L_SCAN` | 扫码登录 | 二维码弹窗 |
| `L_PHONE` | 手机号登录 | 输入手机号页面 |
| `L_PASSWORD` | 密码登录 | 用户名密码输入框 |
| `L_VERIFY_SMS` | 短信验证 | `.second-verify-panel` |

### 2.3 `HOME` — 首页

| 状态码 | 名称 | 特征码 |
|--------|------|--------|
| `H_JINGXUAN` | 精选页 | URL=`/jingxuan` + `.discover-tab-container` + `[data-e2e="alink-item"]` ≥ 3 |
| `H_RECOMMEND` | 推荐页 | URL=`/ ?recommend=1` + 单列feed + `[data-e2e="alink-item"]` |
| `H_FOLLOW` | 关注页 | URL=`/follow` + 左侧关注列表 |
| `H_FRIEND` | 朋友页 | URL=`/friend` |
| `H_SEARCH_INPUT` | 搜索框激活 | URL=cheng + `[data-e2e="searchbar-input"]` 聚焦 |

### 2.4 `SEARCH` — 搜索

| 状态码 | 名称 | 特征码 |
|--------|------|--------|
| `S_LIST` | 搜索结果列表 | URL=`/search/` + 多列卡片 `.search-result-card` |
| `S_PLAYER` | 搜索播放页 | URL=`/search/` + video≥2 + player UI |
| `S_FILTER` | 搜索筛选激活 | `.Bp4xnVjA`（子分类激活态） |

### 2.5 `PLAYER` — 视频播放

这是最复杂的大类，需要细拆。

| 状态码 | 名称 | 特征码 |
|--------|------|--------|
| `P_FULL` | 全屏播放 | video≥2 + URL含`/video/` 或 `modal_id` + `[data-e2e="video-player-digg"]` |
| `P_OVERLAY` | 覆盖播放 | video=1 + `[data-e2e="video-player-digg"]` + `[class*="overlay"]` |
| `P_MUTED` | 静音 | video.muted=true |
| `P_PAUSED` | 暂停 | video.paused=true |
| `P_LOOP` | 连播 | 连播按钮激活 |
| `P_CLEAR` | 清屏模式 | 按J后的纯净模式 |
| `P_HOME` | 作者主页 | URL=`/user/` + 从播放页跳转 |
| `P_COLLECTION` | 合集 | 合集播放模式 |
| `P_HASHTAG` | 话题页 | 话题标签页 |

### 2.6 `COMMENT` — 评论

| 状态码 | 名称 | 特征码 |
|--------|------|--------|
| `C_CLOSED` | 评论关闭 | 无 comment-list + 无 editor |
| `C_PANEL` | 评论面板打开 | `[data-e2e="comment-list"]` 可见 + `.public-DraftEditor-content` 存在 |
| `C_INPUT_FOCUSED` | 输入框聚焦 | `C_PANEL` + activeElement=editor + 光标闪烁 |
| `C_TEXT_ENTERED` | 文字已输入 | `C_INPUT_FOCUSED` + editor.textContent>0 + 发送按钮可见 |
| `C_SENT` | 已发送 | comment-list 含刚发文本 |
| `C_VERIFY` | 验证码触发 | `.second-verify-panel` |
| `C_LIST_SCROLL` | 正在滚动评论列表 | 评论列表滚动条位置变化 |

### 2.7 `PROFILE` — 个人主页

| 状态码 | 名称 | 特征码 |
|--------|------|--------|
| `P_SELF` | 我的主页 | URL=`/user/self` + `[data-e2e="user-detail"]` |
| `P_OTHER` | 他人主页 | URL=`/user/` + `[data-e2e="user-detail"]` |
| `P_POSTS` | 作品Tab | 作品Tab激活 |
| `P_LIKES` | 喜欢Tab | 喜欢Tab激活 |
| `P_COLLECTS` | 收藏Tab | 收藏Tab激活 |
| `P_HISTORY` | 历史Tab | 历史Tab激活 |

### 2.8 其他

| 状态码 | 名称 | 特征码 |
|--------|------|--------|
| `V_SMS` | 短信验证码 | `.second-verify-panel` + `input[placeholder*="验证码"]` |
| `V_SLIDE` | 滑块验证 | 滑块组件可见 |
| `E_404` | 404 | 页面含404 |
| `E_TIMEOUT` | 超时 | 页面加载超时 |
| `E_BLOCKED` | 被拦截 | 反爬页面/访问限制 |

---

## 3. 下一阶段：交互采集特征码

框架搭完了，你看 2.1~2.8 还有没有漏的大类或子状态？

确认框架没问题后，我们一个一个状态来采集：你导航到那个状态，我读特征码，你确认对不对。先从最简单的 `H_JINGXUAN`（精选页）开始？

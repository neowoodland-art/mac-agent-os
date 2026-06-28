---
title: 抖音登录流程 — 全链路知识与踩坑记录
tags: [douyin, login, sms, verification, iframe, selector, timing]
created: 2026-06-28
updated: 2026-06-28
nature: reference
---

# 抖音登录流程 — 全链路知识与踩坑记录

> 本文包含 2026-06-28 大规模调试中积累的所有登录经验。
> 适用于 `douyin_ops.py` 的 `_ensure_logged_in()` 和 `sms_login()` 方法。

---

## 一、登录状态检测

### 1.1 判断已登录的方法（按可靠性排序）

| 方法 | 选择器 | 可靠性 | 说明 |
|:-----|:--------|:-------|:------|
| `data-e2e` 用户信息区 | `[data-e2e="user-info"]` | ⭐⭐⭐ 最高 | 抖音官方 e2e 标记，有就必已登录 |
| 头像元素 | `[class*="avatar"]` 或 `[data-e2e*="avatar"]` | ⭐⭐ 中 | 部分页面没有这个选择器 |
| 登录按钮不可见 | `button:has-text("登录")` 不可见 | ⭐ 低 | 仅作兜底，不精确 |

### 1.2 判断未登录的方法

- 右上角可见的**「登录」按钮**
- 选择器：`button:has-text("登录"), span:has-text("登录"), div:has-text("登录")`
- 注意：首页推荐流中这个按钮始终存在，要用 `is_visible()` 确认

### 1.3 关键注意事项

- **首次打开抖音首页加载慢**，至少要等 **6 秒**才能做登录检测（我们试过 2s→3s→5s→6s，6s 最稳定）
- 登录弹窗可能在上次会话的 cookie 有效时不弹出，直接显示已登录状态
- 登录成功后**必须重新导航到 `/user/self`**，因为弹窗处理改变了页面 URL

---

## 二、登录弹窗检测

### 2.1 弹窗位置：iframe

抖音的登录弹窗（passport 护照页）是在 **iframe** 中加载的，iframe URL 模式：
- `passport.douyin.com`
- `sso.douyin.com`
- 域名含 `login`

### 2.2 弹窗选择器

| 用途 | 选择器 | 说明 |
|:-----|:--------|:------|
| 弹窗容器 | `.second-verify-panel, .uc-ui-verify_sms-verify` | 覆盖新旧两版 class |
| 二维码区域 | `div[class*=qrcode], img[class*=qrcode], canvas[class*=qrcode]` | 用于二维码检测 |

### 2.3 ⚠️ iframe 查找顺序（重要！）

**必须先查 iframe，再查主页面！**

```
❌ 错误做法（我们踩过的坑）：
   1. 主页面查 verify_panel → 匹配到遮罩层（`.second-verify-panel`）
   2. login_frame = page（主页面）
   3. 在主页面搜手机输入框 → 找不到 ❌（因为输入框在 iframe 内）

✅ 正确做法（修复后）：
   1. 遍历所有 iframe，找 passport/login 域的 verify_panel
   2. 找到 → login_frame = iframe
   3. 在 iframe 内搜手机输入框 → 能找到 ✅
   4. iframe 没找到 → fallback 到主页面
```

### 2.4 弹窗类型判断

弹窗可能有三种状态：

```
弹窗出现
  ├─ 一键登录 → 有 "一键登录" 按钮，无手机号输入框
  ├─ 验证码登录 → 有手机号输入框 + 获取验证码按钮
  └─ 二维码登录 → 有二维码图片/画布，需切 tab
```

#### 一键登录特征
- 选择器：`button:has-text("一键登录"), span:has-text("一键登录")`
- 点击后等 5 秒
- 可能直接登录成功，也可能跳到验证码页（继续走 sms）

#### 验证码登录特征
- 手机号输入框：`input[placeholder*="手机"]`（匹配 `placeholder="请输入手机号"`）
- 验证码输入框：`input[placeholder*="验证码"]`（匹配 `placeholder="请输入验证码"`）
- 获取验证码按钮：`button:has-text("获取验证码")`

#### 二维码登录特征
- 检测：`div[class*=qrcode], img[class*=qrcode], canvas[class*=qrcode]`
- 处理：找到「验证码登录」tab 并点击切换

---

## 三、SMS 验证码流程

### 3.1 完整流程

```
1. 导航到登录页（如果不在）
2. 查找 passport iframe（最多 5 次尝试，每次间隔 2 秒）
3. 等 3 秒渲染
4. 检测二维码 → 切「验证码登录」tab
5. 找手机号输入框 → 填入手机号（3 次重试，每次间隔 1 秒）
6. 点击「获取验证码」
7. 轮询 SMS API 获取验证码（最多 6 次，共 60 秒超时）
8. 填入验证码
9. 点击「登录」
10. 判断是否登录成功
```

### 3.2 手机号输入框查找（带重试）

```python
phone_sel = "input[placeholder*='手机'], input[type='tel'], input[name='mobile'], input[id*='phone'], input[id*='mobile']"
for retry in range(3):
    for sel in [phone_sel, "input:first-of-type"]:
        inp = await login_frame.query_selector(sel)
        if inp and await inp.is_visible():
            # 填入手机号
            break
    if phone_filled:
        break
    await asyncio.sleep(1)
```

**注意**：`input:first-of-type` 会匹配到首页搜索框，所以优先用 `placeholder` 选择器。

### 3.3 验证码输入框查找

```python
code_sel = "input[placeholder*='验证码'], input[maxlength='6'], input[maxlength='4'], input[autocomplete='one-time-code']"
```

### 3.4 登录成功判断

| 判断方法 | 说明 |
|:---------|:------|
| URL 变化 | `"passport" in current_url` → 仍在登录页 / `not` → 登录成功 |
| 右上角头像 | `[data-e2e="user-info"]` 存在且可见 → 登录成功（**兜底方案**）|

**两者都用！** 如果 URL 变了但右上角还没渲染出头像，等 3 秒再查一次。

---

## 四、时序控制（重要）

### 4.1 各步骤等待时间

| 步骤 | 等待时间 | 原因 |
|:-----|:---------|:------|
| 首次打开后检测 | **6 秒** | 抖音首页加载慢，特别是第一打开，推荐流+弹窗需要完整渲染 |
| 切换 tab 后 | **3 秒** | tab 切换动画 + 新内容渲染 |
| 填手机号后 | **1 秒** | 防抖 + 输入框状态同步 |
| 点击获取验证码后 | **2 秒** | 等待 SMS 发送 |
| 填入验证码后 | **1 秒** | 防抖 |
| 点击登录后 | **3-5 秒** | 等待页面跳转 |
| 登录成功后重导航 | **3 秒** | 等待 `/user/self` 渲染 |

### 4.2 超时控制

- SMS 验证码轮询：最长 **60 秒**（6 次 × 10 秒）
- 单次 iframe 查找：最长 **10 秒**（5 次 × 2 秒）
- 页面 goto 超时：**20 秒**

---

## 五、选择器备忘（抖音 Web 版）

### 5.1 官方 `data-e2e` 选择器

这些是抖音官方的自动化测试标记，最稳定：

| 用途 | 选择器 |
|:-----|:--------|
| 用户信息区（已登录标志） | `[data-e2e="user-info"]` |
| 用户头像 | `[data-e2e="user-avatar"]`（不一定存在） |
| 搜索输入框 | `[data-e2e="searchbar-input"]` |
| 点赞按钮 | `[data-e2e="video-player-digg"]` |
| 收藏按钮 | `[data-e2e="video-player-collect"]` |
| 分享按钮 | `[data-e2e="video-player-share"]` |
| 评论列表 | `[data-e2e="comment-list"]` |
| 评论点赞 | `[data-e2e="comment-digg"]` |
| 粉丝数 | `[data-e2e="user-info-fans"]`（值可能混合中文） |
| 关注数 | `[data-e2e="user-info-follow"]` |
| 获赞数 | `[data-e2e="user-info-like"]` |

### 5.2 登录弹窗选择器（不定期变化）

这些 class 名由抖音前端动态生成，**每次发布可能变化**：

| 用途 | 6月28日已确认的 class |
|:-----|:----------------------|
| 手机号输入框 | `yKcGN1NT X5L8kib_` |
| 验证码输入框 | `tnpNAdqe _Yqor1vk` |
| 获取验证码按钮 | `gKXDWaPG KX2Mhb6E` |
| 验证码 tab | `zad3EGHJ` |

**因此，不要依赖 class 名，用 placeholder/text 代替。**

### 5.3 推荐做法：文本/属性匹配

```python
# ✅ 稳定
input[placeholder*="手机"]     # 匹配 "请输入手机号"
input[placeholder*="验证码"]    # 匹配 "请输入验证码"
button:has-text("获取验证码")   # 匹配按钮文字
div:has-text("验证码登录")      # 匹配 tab 文字

# ❌ 不稳定（class 会变）
.tnpNAdqe                      # 下个版本可能就改了
.yKcGN1NT                      # 同上
```

---

## 六、已踩过的坑（必读）

### 坑 1：logger 未定义导致 executor 闪退

**现象**：任务提交后状态一直 "running"，实际已挂，slots 空但 active_tasks 有残留。

**根因**：`executor.py` 中使用了 `logger.info()` 但 `logger = logging.getLogger("guardd.executor")` 未定义，NameError 抛出，executor 闪退但任务状态来不及更新。

**修复**：添加 `logger = logging.getLogger("guardd.executor")`。

### 坑 2：主页面遮罩层匹配导致 iframe 检测失败

**现象**：弹窗出现了但手机号输入框找不到。

**根因**：`verify_panel` 选择器 `.second-verify-panel` 在主页面遮罩层上匹配成功，`login_frame` 设为主页面（不是 iframe），在主页面搜手机输入框当然搜不到。

**修复**：先查 iframe，再查主页面。

### 坑 3：登录后页面 URL 变化导致采集到首页数据

**现象**：采集任务显示完成，但 profiles.json 中昵称/粉丝数据为空或为首页标题。

**根因**：登录弹窗处理后，页面 URL 从 `/user/self` 变成了首页或其他地址，但 `goto_profile()` 继续刮取当前页面内容（首页推荐流），拿不到用户数据。

**修复**：登录成功后重新 `goto("/user/self")`。

### 坑 4：2 秒等待不够

**现象**：浏览器打开后鼠标立即动了，此时页面还没渲染完，弹窗还没出现。

**根因**：抖音首页首次加载~4-5 秒，2 秒时 `_has_avatar()` 判断为未登录（因为没渲染完），然后触发弹窗检测也找不到弹窗，最后点了"登录"按钮导致页面刷新。

**修复**：初始等待时间从 2 秒改为 6 秒。

### 坑 5：`_build_cmd` 按字段拼装导致 command_line 出错

**现象**：采集任务一直失败，executor 日志显示 `--blueprints=` 为空。

**根因**：`executor._build_cmd()` 从 `task.get("blueprint")` 读蓝图名，但 CommandBus 传的 `blueprint` 字段是空字符串（没传对），拼出了 `mc run --blueprints= --rounds=1`。

**修复**：优先使用 `task.command_line`（CommandBus 已渲染好的完整命令），`_build_cmd` 按字段拼装仅作 fallback。

### 坑 6：5kecheng 双 guardd 进程

**现象**：远程机器任务不执行，所有请求都返回空。

**根因**：SSH 部署时 `pkill -9 -f guardd` + `nohup python3 guardd.py` 启动了一个新实例，而 launchd 也管理了一个旧实例。两个 guardd 争抢端口 9090，其中一个没有 HTTP 服务。

**修复**：统一用 launchd 管理，不用 nohup。

### 坑 7：登录后 URL 不变（前端 overlay 形式）

**现象**：登录成功了但 `sms_login` 返回 False。

**根因**：有的登录弹窗是前端 overlay（不在 passport 域名下），URL 不变化。`sms_login` 只检查 URL，误判为失败。

**修复**：加 `_has_avatar()` 兜底判断。

### 坑 8：profiles.json 同步走本地文件违反联邦对等

**现象**：7kecheng 采集了数据，但 Dashboard 看不到。

**根因**：`AccountService._get_profile_for_account()` 直接读本机 `profiles.json`，不走 guardd API。

**修复**：改为统一通过 guardd HTTP API (`/accounts/profiles`) 读取，本机远程无差别。

---

## 七、录制文件分析指南

录制的 JSON 文件位于 `agent-local/tools/matrix/recordings/`。

### 7.1 关键字段含义

| 字段 | 含义 |
|:-----|:------|
| `t` | 事件类型（click/hover/key/scroll） |
| `tag` | HTML 标签 |
| `text` | 元素文本内容 |
| `cls` | 元素的 CSS class（关键！） |
| `placeholder` | input 元素的占位符 |
| `type` | input 类型 |
| `e2e` | data-e2e 属性值 |
| `vis` | 元素是否可见 |
| `before_state.selectors` | 录制前页面状态快照 |
| `before_state.text_snippet` | 页面文本片段 |

### 7.2 如何从录制中提取特征码

```bash
# 找手机号输入框
grep -B5 -A3 "请输入手机号" recording_xxx.json

# 找验证码输入框
grep -B5 -A3 "请输入验证码" recording_xxx.json

# 找登录按钮
grep -B5 -A3 "获取验证码" recording_xxx.json

# 查看页面文本快照（了解页面状态）
grep "text_snippet" recording_xxx.json | head -1 | python3 -c "import json,sys;print(json.load(sys.stdin)['text_snippet'][:500])"
```

---

## 八、蓝图登录检测覆盖范围

当前 `_ensure_logged_in()` 被以下操作调用：

| 蓝图操作 | 在流程中调用位置 |
|:---------|:----------------|
| `goto_home` | `execute_op()` 中 goto 首页后 |
| `dy_goto_profile` | `execute_op()` 中 goto 个人主页后 |
| `goto_profile` | 独立方法中被调用 |
| `_ensure_logged_in` 自身 | 无弹窗时递归调用 |

### 设计原则

所有涉及浏览器导航的操作（`goto_home`、`goto_url`、`goto_profile`）**都应该**调用 `_ensure_logged_in()`。目前 `goto_url` 还没有加，待补。

---

## 九、相关文件索引

| 文件 | 内容 |
|:-----|:------|
| `douyin_ops.py` | 抖音原子操作 + `_ensure_logged_in` + `sms_login` |
| `matrix_modules/account/sms_login.py` | SMS 登录模块 |
| `matrix_modules/account/douyin_login.py` | 抖音登录模块 |
| `matrix_modules/account/login_state_machine.py` | 登录状态机 |
| `03_knowledge/99_system/matrix/matrix-known-pitfalls.md` | 已知坑（浏览器/系统） |
| `03_knowledge/99_system/matrix/matrix-sms-verification.md` | SMS 验证码自动接收配置 |

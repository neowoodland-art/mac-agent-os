# 评论发送 — 原子操作详细规格书 v1.0

> 版本：1.0 | 最后更新：2026-05-10
> 状态：已通过全自动测试验证
> 适用窗口：702×783 | 窗口位置：(652, 0)

---

## 0. 前置条件（所有操作前必检）

| 检查项 | 方式 | 失败处理 |
|--------|------|---------|
| Camoufox 进程不冲突 | `pkill -f camoufox` + 删 `.parentlock` | 重试 |
| 窗口在最前端 | AppleScript `set frontmost` | 重试3次 |
| 窗口大小正确 | `window.innerWidth===702 && window.innerHeight===783` | 调整后再继续 |
| 页面已完全加载 | `document.readyState === 'complete'` | 等待3秒重试 |

---

## 1. 原子操作：enter_video（精选页 → 视频播放页）

### 前置状态：H_JINGXUAN
```
特征码:
  - URL: douyin.com/jingxuan
  - cards: document.querySelectorAll('.discover-video-card-item').length >= 3
  - vc: document.querySelectorAll('video').length === 1
```

### 操作步骤
```
1. _activate_window()           # 窗口置前
2. card = locator('.discover-video-card-item').first
3. card.click(force=True)       # 第1次点卡片 → 触发预览播放
4. sleep(1.5)                   # 等预览播放出现
5. vid = locator('video').first
6. vid.click()                  # 第2次点 video → 进入弹窗播放器
7. sleep(1)
8. vid.click()                  # 第3次点 video → 确保播放
9. sleep(4)                     # 等播放器完全加载
```

### 后置状态：P_FULL
```
特征码:
  - vc: >= 2 (弹窗播放器有多个 video)
  - URL: douyin.com/jingxuan?modal_id=xxx (弹窗模式)
  - 或 URL: douyin.com/video/xxx (全屏模式)
```

### 失败恢复
```
重试3次 → 每次回到 H_JINGXUAN (goto douyin.com) → 滚动画廊选不同卡片
3次全失败 → 截图 + 报告
```

---

## 2. 原子操作：open_comments（视频播放页 → 评论区打开）

### 前置状态：P_FULL
```
特征码: vc>=2 + (URL含/video/或modal_id)
```

### 操作步骤
```
1. 前置锚点检测: [data-e2e="comment-list"] 是否存在？
   → 已存在：跳过（评论区已开）
   → 不存在：继续

2. _activate_window()
3. vid = locator('video').first
4. box = vid.bounding_box()
5. mouse.click(box.center)     # 点视频中心获得焦点
6. sleep(0.5)
7. keyboard.press('x')          # x 键开评论
8. sleep(2)
9. 验证: [data-e2e="comment-list"] 是否存在
10. 如果不存在 → DOM 点评论图标兜底
```

### 后置状态：C_PANEL
```
特征码:
  - [data-e2e="comment-list"] 可见
  - 输入框尚未加载（懒加载）
```

---

## 2b. 原子操作：close_comments（评论区 → 关闭）

### 前置状态：C_PANEL
```
特征码: [data-e2e="comment-list"] 可见
```

### 操作步骤
```
1. keyboard.press('Escape')  或  keyboard.press('x')
2. sleep(1)
3. 验证: [data-e2e="comment-list"] 不可见
```

### 后置状态：P_FULL

---

## 3. 原子操作：focus_editor（评论区 → 输入框聚焦）

### 前置状态：C_PANEL
```
特征码: [data-e2e="comment-list"] 可见
```

### 操作步骤（核心——模拟真人鼠标轨迹）
```
1. _activate_window()
2. 目标坐标: (479, 687) — 窗口 702×783

3. 鼠标轨迹模拟（8步缓慢移动，总耗时约1.3s）:
   for step in 0..7:
       px = 10 + (479-10) * (step+1) / 8
       py = 10 + (687-10) * (step+1) / 8
       mouse.move(px, py)
       sleep(0.1)

4. sleep(0.5)                   # 停顿让 hover 触发

5. mouse.click(479, 687)        # 第1次单击 → 加载编辑器 + 获得焦点
6. sleep(1)                     # 等待编辑器渲染

7. 验证: activeElement 是否是 .public-DraftEditor-content
8. 如果没激活 → mouse.click(479, 687) 第2次 → sleep(1) → 再验证

9. 仍未激活 → 多点尝试:
   [(350,747), (300,747), (400,747), (250,747)]
   每个位置: mouse.move → sleep(0.3) → click → sleep(0.5) → click → sleep(0.5) → 验证
```

### 后置状态：INPUT_FOCUSED
```
特征码:
  - document.activeElement === .public-DraftEditor-content
  - activeElement.isContentEditable === true
  - 编辑器存在（懒加载完成）
```

### 关键参数
```
编辑器选择器: .public-DraftEditor-content
元素类名: notranslate public-DraftEditor-content
角色: combobox
内容可编辑: true
```

---

## 4. 原子操作：type_comment（输入框 → 文字输入）

### 前置状态：INPUT_FOCUSED
```
特征码: activeElement 是 Draft.js 编辑器
```

### 操作步骤
```
1. osascript -e 'set the clipboard to "评论内容"'   # 设置剪贴板
2. sleep(0.3)
3. keyboard.press('Meta+v')                          # Playwright Cmd+V 粘贴
4. sleep(2)                                          # 等待 Draft.js 处理
5. 验证: .public-DraftEditor-content.textContent.length > 0
```

### 后置状态：TEXT_ENTERED
```
特征码:
  - .public-DraftEditor-content.textContent.trim().length > 0
  - 内容为刚输入的文本
```

### 注意
```
不能使用:
  - keyboard.type() → Draft.js 不处理 CDP 键盘事件
  - execCommand('insertText') → Draft.js 覆盖 DOM 更改
  - pyautogui.write() → 中文 IME 问题

只能用: 剪贴板粘贴（系统级复制 + 浏览器内 Cmd+V）
```

---

## 5. 原子操作：send_comment（文字已输入 → 发送）

### 前置状态：TEXT_ENTERED
```
特征码: editor 有内容
```

### 操作步骤
```
方案A（优先）: 找发送按钮
  1. 查询 button 含 text"发送"/class含"send"/"submit"/"arrow"
  2. 找到后 click
  3. 验证

方案B: Alt+Enter（系统级）
  1. osascript key code 36 using option down
  2. sleep(3)
  3. 验证验证码弹窗

方案C: Ctrl+Enter（兜底）
  1. keyboard.press('Control+Enter')
  2. sleep(1)
  3. keyboard.press('Alt+Enter')
  4. 验证
```

### 后置状态：COMMENT_SENT 或 VERIFY_CODE
```
COMMENT_SENT:
  - [data-e2e="comment-list"] 含刚发的文本内容
  
VERIFY_CODE:
  - input[placeholder*="验证码"] 可见
  - 或 .second-verify-panel 可见
```

---

## 6. 异常处理：验证码弹窗

### 触发条件
```
send_comment 后检测到:
  - input[placeholder*="验证码"]
  - .second-verify-panel
```

### 自动处理
```
1. ApiSMSHandler 启动轮询（每3秒）
   - API: wx.tyhtak.com/api/biz/msg/messages
   - api_key: gtmsg2026
   - phone: 15370103682
2. 提取最新短信中的验证码（4-6位数字）
3. 回填到 input[placeholder*="验证码"]
4. 点击确认按钮
5. 超时120秒 → 手动输入兜底
```

---

## 7. 完整蓝图链（执行顺序）

```
┌─────────────────────────────────────────────────────┐
│              蓝图：douyin_comment_send               │
├─────────────────────────────────────────────────────┤
│ ① launch_browser     → 状态: H_JINGXUAN            │
│ ② enter_video        → 状态: P_FULL                │
│ ③ open_comments      → 状态: C_PANEL               │
│ ④ focus_editor       → 状态: INPUT_FOCUSED          │
│ ⑤ type_comment       → 状态: TEXT_ENTERED           │
│ ⑥ send_comment       → 状态: COMMENT_SENT           │
│ ⑦ 如果是 VERIFY_CODE → 自动获取+回填验证码           │
│ ⑧ goto_home          → 回到 H_JINGXUAN（下一轮）    │
└─────────────────────────────────────────────────────┘
```

---

## 8. 调试信息记录格式

每个原子操作执行时必须记录：
```
[步骤名] 前置状态: X → 执行中 → 后置状态: Y | 耗时: Ns | 结果: OK/FAIL
```

失败时额外记录：
```
当前URL: xxx
当前vc: N
activeElement: tag/class
错误信息: xxx
```
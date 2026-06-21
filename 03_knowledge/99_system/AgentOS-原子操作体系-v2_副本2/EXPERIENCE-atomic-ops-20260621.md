# 原子操作体系开发经验文档 v1.0

> 创建时间: 2026-06-21 10:05
> 时间跨度: 2026-06-20 09:00 ~ 2026-06-21 10:00
> 涉及平台: 抖音(douyin)、小红书(xiaohongshu)
> 文档性质: 经验沉淀 + 框架设计 + 代码对照

---

## 第一章：时间线回顾

### 2026-06-20（Day 1）

| 时间 | 事件 | 关键结论 |
|:-----|:-----|:---------|
| 09:00-12:00 | 登录状态机重构 + Vite前端修复 | 三组件架构(PlatformDetector/RecoveryChain/LoginManager)定型 |
| 14:00-16:20 | 抖音登录 3 种场景调试 | 全通。关键修复: 检测器误判(移除data-e2e anchor)、短信验证码取旧码、登录按钮是"确认登录"不是"登录" |
| 16:30-18:10 | 小红书登录修复 | 全通。关键修复: SmsRecovery调xhs_login、XhsDetector cookie误判、is_logged_in()太松、步骤顺序错误(同意并登录在点登录后)、div.foot-btn选择器、oauth-tip切换 |
| 18:10-20:40 | 养号蓝图v2.0 + 抖音日常45步测试 | 45步39成功。关键修复: open_video双击+验证+焦点、like从DOM改为键盘z、open_video加回首页兜底 |
| 20:40-23:10 | 抖音录制2轮 + 小红书原子操作测试 | 小红书post_comment首次成功(JS找输入框方案)。关键修复: xhs_ops补wait_watch/go_back、冷却前缀匹配 |

### 2026-06-21（Day 2）

| 时间 | 事件 | 关键结论 |
|:-----|:-----|:---------|
| 08:00-09:00 | 双平台修复 | follow键盘f→g、post_comment加send按钮查找+验证、open_video多选择器+状态检测 |
| 09:00-09:27 | 架构反思 | ghai指出新代码全不能用——缺乏前置状态检测和后置验证。Claw从头学习旧代码_retry_enter_video、_check_anchor、CommentStateMachine |
| 09:27-09:34 | 方案重构 | 提出三层状态模型(L1页面/L2区域/L3元素)、增强录制、单步调试、看板流程图 |
| 09:34-09:42 | PageInspector实现 | 创建page_inspector.py，L1/L2/L3三层检测 |
| 09:42-09:46 | 增强录制讨论 | ghai提出: 只按一次·标记状态变化，系统自动推断操作。Claw优化: 系统根据状态差自动识别操作类型 |
| 09:46-09:54 | ghai录制18步 | 首次用新思路录制。发现新问题: 收藏键是C不是无键、弹幕B键、分享V键 |
| 09:54-10:05 | 视觉状态层讨论 | ghai发现: 按钮变色(灰→红→黄)是重要的状态变化，当前录制没有捕获。提出L4视觉状态层 |

---

## 第二章：核心概念与设计原则

### 2.1 原子操作的本质

一个原子操作 = **四个要素**:
```
[前置状态] → [操作执行] → [后置状态] → [验证结果]
```

- **前置状态**必须包含: 页面类型(L1)、鼠标区域(L2)、元素详情(L3)、视觉状态(L4)
- **操作执行**是一个确定的动作: 点击某个元素、按某个键盘键
- **后置状态**与前置状态有明确差异(URL变化、DOM变化、视觉变化)
- **验证结果**是真实可观测的，不是代码返回的布尔值

### 2.2 错误模式总结

以下所有错误都有一个共同根因: **没有做状态检测**

| 错误表现 | 具体操作 | 原因 |
|:---------|:---------|:-----|
| open_video 在首页找不到卡片 | 直接找.discover-video-card-item | 不先检测是否在播放页 |
| like 返回"成功"但页面没反应 | 键盘z在feed流中无效 | 不检测是否在视频详情页 |
| collect 全部失败0.0s | 用[data-e2e]选择器找按钮 | 不检测按钮的视觉/属性状态 |
| post_comment 返回sent但评论没发 | pbcopy+Meta+V+Enter | 不验证comment-list是否出现文字 |
| follow 无反应 | KEYS['follow']='f' | 没有用录制数据验证(实际是g键) |

### 2.3 各种选择器优劣

| 方式 | 可靠性 | 适用场景 |
|:-----|:------|:---------|
| 键盘快捷键(z/c/g/x) | ⭐⭐⭐⭐⭐ | 抖音所有互动操作 |
| data-e2e 锚点 | ⭐⭐⭐ | 旧版抖音 (可能被新版移除) |
| CSS类名 | ⭐⭐ | 不稳定(CSS modules会加hash) |
| 坐标(录制位置) | ⭐⭐⭐⭐ | 固定布局中稳定 |
| 文字匹配 | ⭐⭐⭐ | 关注/发送等有固定文字 |
| 视觉状态(颜色) | ⭐⭐⭐⭐ | 🆕 L4层,按钮状态判断 |

### 2.4 抖音网页版快捷键完整表

```
互动类:
  Z   赞/取消赞
  C   收藏/取消收藏
  G   关注/取消关注
  F   进入作者主页
  X   打开/关闭评论
  V   复制分享口令
  P   推荐给朋友
  R   不感兴趣

播放类:
  B   开始/关闭弹幕
  J   清屏
  K   自动连播
  Y   网页内全屏
  H   全屏
  L   稍后再看
  Space 暂停/播放
  ↑↓  上下翻页
  ←→  快进快退(长按2倍速)
  Shift+/Shift-  音量调大/调小
```

---

## 第三章：统一状态模型(引擎层核心)

### 3.1 四层状态检测

```
L1: 页面类型
  ├── 判断依据: URL pattern + DOM特征(video数量、card数量、搜索栏、导航栏)
  ├── 抖音类型: grid(首页)、player_modal(弹窗)、player_full(独立页)、search(搜索)、profile(主页)
  └── 小红书类型: grid(explore)、note_detail(笔记详情)、search(搜索结果)、profile(主页)

L2: 鼠标区域
  ├── 判断依据: 鼠标坐标 / 窗口尺寸 → 百分比区域
  ├── 区域类型: video_area(中央上)、bottom_bar(底部按钮)、comment_area(评论区)、feed_area(内容区)、nav_area(左侧导航)、sidebar(右侧推荐)
  └── 用途: 确定操作上下文(在按钮区点击=互动操作,在feed区点击=选择内容)

L3: 元素详情
  ├── 检测: 鼠标正指向的元素(elementFromPoint) + 周围200px内的所有可交互元素
  ├── 属性: tag、class、text、位置、尺寸、visibility
  └── 用途: 确定具体操作目标(这个SPAN是like-lottie点赞按钮)

L4: 视觉状态 🆕
  ├── 检测: computedStyle(color/fill/stroke)、data-state/aria-pressed属性、textContent变化
  ├── 典型变化:
  │   ├── 点赞: 灰色(#999) → 红色(#ff2d55), data-e2e-state从空变digged
  │   ├── 收藏: 灰色 → 黄色, 文字从"收藏"变"已收藏"
  │   ├── 关注: 文字从"关注"变"已关注", 按钮颜色变红
  │   └── 弹幕: aria-pressed属性变化
  └── 用途: 验证操作是否真正生效(不是代码返回的假成功)
```

### 3.2 状态转换规则

```
抖音:
  grid ──(双击卡片)──> player_modal
  grid ──(搜索)──────> search
  grid ──(点头像)────> profile
  player_* ──(z键)───> player_*(点赞已变)
  player_* ──(c键)───> player_*(收藏已变)
  player_* ──(g键)───> player_*(关注已变)
  player_* ──(go_back)──> grid
  search ──(点结果)──> player_*
  search ──(go_back)──> grid
  profile ──(go_back)──> grid

小红书:
  grid ──(点笔记)──> note_detail
  note_detail ──(点❤️)──> note_detail(已赞)
  note_detail ──(点⭐)──> note_detail(已收藏)
  note_detail ──(go_back)──> grid
  grid ──(搜索)──> search
  search ──(点结果)──> note_detail
```

---

## 第四章：录制系统设计

### 4.1 录制原理

```
用户操作流程:
  1. 按 ·  → 系统捕获状态快照(所有四层数据)
  2. 做操作 → 用户自由操作(点击/键盘/停留/滚动)
  3. 按 ·  → 系统捕获状态快照 + 自动对比差异
  ...重复...
  4. 按 Esc → 结束录制

系统自动推断:
  - 对比相邻两个状态的差异
  - URL变化 → 可能进入新页面
  - video数量变化 → 进入/离开播放页
  - 按钮颜色变化 → 点赞/收藏/关注操作
  - 评论输入框出现/消失 → 打开/关闭评论
```

### 4.2 录制数据格式

```json
{
  "step": 2,
  "label": "open_video",           // 人工标注或系统自动建议
  "before": {
    "url": "...jingxuan",          // L1
    "page_type": "grid",           // L1
    "video_count": 0,              // L1
    "card_count": 20,              // L1
    "mouse_x": 262, "mouse_y": 209, // L2
    "mouse_region": "video_area",  // L2
    "element_at_point": {          // L3
      "tag": "VIDEO", "class": "", ...
    },
    "visual_states": {             // L4
      "like_active": false,        // 赞为空
      "collect_active": false      // 收为空
    }
  },
  "action": {
    "type": "click",
    "x": 262, "y": 209,
    "target": "VIDEO",
    "click_count": 2               // 双击
  },
  "after": {
    "url": "...modal_id=xxx",
    "page_type": "player_modal",
    "video_count": 1,
    "diff": "从首页进入播放页"
  }
}
```

### 4.3 标注系统（人工+自动）

录制后进入标注界面：
- 自动建议: 系统根据状态diff推断操作名称(URL变化→open_video, 按钮变色→like)
- 人工修正: 你可以修改名称、补充备注
- 合并步骤: 连续2-N步可以合并为1个复合原子操作(如: x+打字+发送 = post_comment)

---

## 第五章：当前代码状态

### 5.1 已修复的问题

| 文件 | 问题 | 修复 |
|:-----|:-----|:-----|
| douyin_ops.py | KEYS['follow']='f' → 应该是'g' | ✅ 已修复 |
| douyin_ops.py | collect没有键盘fallback | ⚠️ 加了C键但未测试 |
| douyin_ops.py | open_video选择器单一 | ✅ 加了多选择器+状态检测 |
| douyin_ops.py | post_comment无验证逻辑 | ✅ 加了send按钮搜索+comment-list文本验证 |
| xhs_ops.py | go_back未定义 | ✅ 已添加 |
| xhs_ops.py | wait_watch未定义 | ✅ 已添加 |
| xhs_ops.py | post_comment完全失败 | ✅ JS找输入框方案成功 |
| mc/engine.py | 冷却前缀不匹配(xhs_like不匹配like) | ✅ 已去前缀 |

### 5.2 仍需修复的问题

| 文件 | 问题 | 优先级 |
|:-----|:-----|:------|
| douyin_ops.py | collect 用 C 键（不是DOM选择器） | P0 |
| douyin_ops.py | 所有操作加 L4 视觉验证 | P0 |
| douyin_ops.py | 新增 danmaku(B键), share(V键) | P1 |
| xhs_ops.py | xhs_click_note go_back后feed未刷新 | P1 |
| xhs_ops.py | 小红书没有C/G快捷键，需要DOM点 | P1 |

### 5.3 关键文件清单

| 文件 | 作用 | 状态 |
|:-----|:-----|:----:|
| `scripts/ARCHITECTURE_AUDIT.md` | 新旧代码对比审计 | ✅ 完成 |
| `scripts/page_inspector.py` | 四层状态检测器(新) | ✅ 已创建 |
| `scripts/douyin_ops.py` | 抖音原子操作 | ⚠️ 部分修复 |
| `scripts/ops/xhs_ops.py` | 小红书原子操作 | ⚠️ 部分修复 |
| `scripts/mc/engine.py` | 执行引擎 | ✅ 冷却修复 |
| `scripts/mc/recorder.py` | 录制工具 | 🔵 待增强(L4+自动推断) |
| `blueprints/dy_step_test.json` | 抖音11步测试蓝图 | ✅ |
| `blueprints/xhs_test_all.json` | 小红书17步测试蓝图 | ✅ |
| `blueprints/dy_test_all.json` | 抖音16步全原子测试蓝图 | ✅ |
| `scripts/matrix_modules/nurture/runner.py` | 旧版稳定代码(参考用) | ✅ |

---

## 第六章：开发方法论

### 6.1 禁止事项

1. **不要修改旧代码** — 旧代码是宝贵的参考,即使不完美也证明了可行路径
2. **不要用CSS类名作为主要选择器** — CSS modules会使类名不可靠
3. **不要假设操作成功了** — 必须用L4视觉状态验证
4. **不要把抖音的操作方法套用给小红书** — 两个平台的DOM结构完全不同
5. **不要在没有录制数据支持的情况下添加新操作** — 优先让ghai录一次,从数据出发

### 6.2 高效开发流程

```
1. ghai录制真实操作(5-10分钟)
2. Claw分析录制数据,提取状态diff(2分钟)
3. 一起标注原子操作名称(2分钟)
4. Claw生成代码模板(1分钟)
5. ghai审核确认(1分钟)
6. 单步测试(3秒/步)
7. 全流程验证(1分钟)

总计: ~15分钟完成一个完整原子操作
```

反面对比:
```
旧流程: Claw手写代码 → 猜测选择器 → 跑全蓝图 → 等14分钟 → 失败 → 再猜 → ...
完全不可行
```

### 6.3 测试原则

1. **从首页开始**: goto_home是最基础的原子操作,先确认
2. **逐条路径测试**: 不要混在一起测
3. **三秒原则**: 单步测试结果3秒内必须看到,不等完整蓝图
4. **绿了就固化**: 一个操作测试通过立即标记绿色,不回头动

---

## 第七章：附录 - 按键映射

### 抖音 Keys 正确值

```python
KEYS = {
    "like":       "z",     # ✅ 正确
    "collect":    "c",     # ❌ 之前代码里没有定义
    "comment":    "x",     # ✅ 正确
    "follow":     "g",     # ✅ 修复后正确 (之前错为f)
    "danmaku":    "b",     # 🆕 新增
    "share":      "v",     # 🆕 新增(复制分享口令)
    "clear_screen": "j",   # 🆕 新增
    "prev":       "ArrowUp",
    "next":       "ArrowDown",
    "enter":      "Enter",
}
```

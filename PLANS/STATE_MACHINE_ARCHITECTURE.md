# AgentOS 联邦系统 — 状态机架构方案 v1.0

> 目标：让账号在指定动作中随意切换，不受意外打扰，遇到问题自动回到正轨

---

## 一、总体架构（四层模型）

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Layer 4: 联邦指挥台 (Dashboard UI)                │
│              命令下发 / 状态监控 / 日志查看 / 人工介入入口             │
├─────────────────────────────────────────────────────────────────────┤
│                    Layer 3: 蓝图编排层 (Blueprint Scheduler)          │
│        按蓝图执行步骤链：步骤A → 检查A ✅ → 步骤B → 检查B ✅ → ...   │
│        遇到意外 → 降级/重试/截图/上报                                │
├─────────────────────────────────────────────────────────────────────┤
│                    Layer 2: 原子操作层 (Atomic Operations)            │
│        每个操作自带"正常/被验证"两种状态                             │
│        登录状态机 / 操作状态机 / 异常处理子模块                      │
├─────────────────────────────────────────────────────────────────────┤
│                    Layer 1: 浏览器管理层 (Browser Runtime)            │
│        Camoufox 反检测引擎 / 身份隔离 / 窗口资源池 / 机器调度        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、Layer 1: 浏览器管理层

### 2.1 核心原则

| 规则 | 说明 |
|:-----|:------|
| 统一引擎 | 三台机器全部使用 **Camoufox**（Firefox 内核 + 反检测指纹） |
| 身份隔离 | 每个账号（xhs_01 / douyin_test）有独立的 user_data 目录 → Cookie/Storage 全部隔离 |
| 窗口规范 | 每个浏览器窗口 702×783，按坐标平铺防止重叠和封号 |
| 资源限制 | 本机 16GB 内存，**最多同时开 4 个 browser 窗口**（每个约 1.5GB） |
| 节点机限制 | 5kechengdeAir / 7kecheng 各 2-3 个同时运行 |

### 2.2 窗口坐标图谱

```
屏幕虚拟坐标（模拟三屏协调）
┌──────────────────────────────────────────────────────────┐
│  [0,0]        [702,0]       [1404,0]     [2106,0]       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ xhs_01   │ │ douyin   │ │ xhs_02   │ │ douyin   │   │
│  │          │ │ _test    │ │ (预留)    │ │ _133     │   │
│  │ 702×783  │ │ 702×783  │ │ 702×783  │ │ 702×783  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│                                                          │
│  [0,783]       [702,783]      [1404,783]   [2106,783]    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 备用     │ │ 备用     │ │ 备用     │ │ 备用     │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└──────────────────────────────────────────────────────────┘
```

**本机实际可用（16GB）**：主窗口 4 个（x轴平铺），其余可选

### 2.3 同身份跨平台切换

同一个身份是否可以"先登录抖音、切到小红书、再切回来"？

**答案：不建议。** 原因：
1. Camoufox 的 user_data 绑定一个 browser profile → 切换平台需要关掉现有的再开另一个
2. 更好的做法：**一个平台一个身份目录**，各自独立运行
3. 但如果想省资源：可以用同一个 profile 先后打开不同平台 → 先关一个窗口再开另一个

**推荐方案**：

| 场景 | 方案 |
|:-----|:------|
| 日常养号（同时操作多账号） | 每个账号开独立窗口，同时运行 |
| 单账号多平台（抖音+小红书同一人） | 开两个窗口，两套身份 |
| 节点机做日活 | 每台固定 2-3 个窗口，跑同一蓝图 |

### 2.4 机器分工

| 机器 | 角色 | 身份配额 | 同时窗口 | 视觉模型 |
|:-----|:------|:---------|:---------|:---------|
| chengzigedeAir | **主控开发机** | 4 个 | 2-4 个 | ✅ oMLX + Qwen-VL |
| 5kechengdeAir | 养号节点 | 2-3 个 | 2 个 | ❌ |
| 7kecheng | 养号节点 | 2-3 个 | 2 个 | ❌ |

---

## 三、Layer 2: 原子操作层 — 状态机核心

### 3.1 登录状态机（最重要）

这是整个体系的**核心保险**——每个操作之前必须确认登录状态。

```
                          ┌──────────────┐
         start ──────────→│  UNKNOWN     │
                          └──────┬───────┘
                                 │ 检测登录状态
                                 ▼
                    ┌─────────────────────────┐
                    │    DETECT_LOGIN_STATE    │
                    │  · DOM特征检测           │
                    │  · Cookie有效性检测       │
                    │  · 视觉检检测（备用）     │
                    └────────────┬────────────┘
                                 │
                ┌────────────────┼────────────────┐
                ▼                ▼                ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │  LOGGED_IN   │ │ NOT_LOGGED   │ │   UNKNOWN    │
        │  (已登录)     │ │ (未登录)     │ │ (无法判断)   │
        └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
               │                │                │
               ▼                ▼                ▼
         [进入操作流程]   [进入登录恢复流程]  [截图+视觉分析]
                                   │                  │
                                   ▼                  ▼
                        ┌──────────────────┐  ┌──────────────┐
                        │ LOGIN_RECOVERY   │  │ 人工判断后   │
                        │ Chain:           │  │ 进入登录恢复 │
                        │ 1. Cookie 恢复    │  └──────────────┘
                        │ 2. SMS 验证码登录 │
                        │ 3. 截图+上报      │
                        └──────────────────┘
```

#### 3.1.1 状态检测（DETECT_LOGIN_STATE）

每个平台的判断特征：

| 平台 | ✅ 已登录特征 | ❌ 未登录特征 |
|:-----|:-------------|:-------------|
| **小红书** | 头像元素 `.user-avatar` / 红点计数 `.reds-count` / 用户昵称 | 手机号输入框 / 登录弹窗 / "登录/注册"按钮 |
| **抖音** | 头像 `[data-e2e=user-avatar]` / 用户信息 `.user-info-avatar` | 登录按钮 / 扫码登录框 |

**检测策略**：
```
1. `page.evaluate()` DOM 查询（首选，快）
2. 如果 DOM 查询 ambiguous → `vision_bridge` 截图分析（保底）
3. 连续 3 次 detecting 结果一致 → 固化结论
```

#### 3.1.2 登录恢复流程（LOGIN_RECOVERY）

```
LOGIN_RECOVERY
│
├── Step 1: Cookie 恢复
│   重新加载页面 → 再检测 → 如果已登录 → ✅ 回到 LOGGED_IN
│
├── Step 2: SMS 验证码登录
│   (仅在 Step 1 失败后执行)
│   ① 检测登录弹窗 → 无弹窗则触发
│   ② 填手机号（从 identity config 读取）
│   ③ 点"继续" / "获取验证码"
│   ④ 调用 SMS API 等待验证码
│   ⑤ 填 6 位验证码
│   ⑥ 点"同意并登录"
│   ⑦ 检测登录状态 → ✅ → 回到 LOGGED_IN
│
├── Step 3: 截图上报（2次失败后）
│   ① screen shot 保存
│   ② vision_bridge 分析异常
│   ③ 日志记录到 report
│   ④ 通知用户：return NEEDS_MANUAL
│
└── Step 4: 手动介入
    用户登录完成后 → 标记状态 → 继续执行
```

#### 3.1.3 状态代码

```python
@dataclass
class LoginState:
    status: Literal["UNKNOWN", "LOGGED_IN", "NOT_LOGGED", "NEEDS_MANUAL"]
    platform: str          # "xhs" / "douyin"
    account: str           # "xhs_01"
    method: str            # "dom" / "visual" / "cookie"
    screenshot: str | None # 异常时的截图路径
    confidence: float      # 0.0 ~ 1.0
```

#### 3.1.4 登录状态管理接口

```python
class LoginStateMachine:
    """登录状态机 — 每个账号实例化一个"""

    async def ensure_login(self, page, account_id: str, platform: str) -> LoginState:
        """核心入口：保证账号是登录状态，如果否，尝试恢复"""

    async def _detect_state(self, page, platform: str) -> LoginState:
        """检测当前状态（DOM + Cookie + 视觉）"""

    async def _recover_cookie(self, page) -> bool:
        """刷新页面：让已有cookie生效"""

    async def _recover_sms(self, page, phone: str, account_name: str) -> bool:
        """SMS验证码登录流程"""

    async def _report_unknown(self, page) -> LoginState:
        """截图 + 视觉分析 + 上报"""
```

---

### 3.2 操作状态机

每一个原子操作（浏览、点赞、评论、收藏等）都有**两种子状态**：

```
                  ┌──────────────┐
                  │  OPERATION   │
                  │  START       │
                  └──────┬───────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  PRE_OP_CHECK        │
              │  · 登录状态确认       │
              │  · 操作间隔检测       │
              │  · 风控冷却检测       │
              └──────────┬───────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
     ┌────────────────┐   ┌────────────────┐
     │  NORMAL_EXEC   │   │ BLOCKED_BY     │
     │  · 执行操作     │   │ VERIFICATION   │
     │  · 3-8秒随机等待 │   │ (被验证弹窗拦截)│
     └───────┬────────┘   └───────┬────────┘
             │                    │
             ▼                    ▼
     ┌────────────────┐   ┌────────────────┐
     │  POST_OP_CHECK  │   │ HANDLE_VERIFY  │
     │  · 执行成功?     │   │ · 检测弹窗类型  │
     │  · 触发了验证?   │   │ · SMS重登      │
     └───────┬────────┘   │ · 截图分析     │
             │            └───────┬────────┘
             │                    │
             │   ┌────────────────┘
             ▼   ▼
     ┌────────────────┐
     │  OP_COMPLETE    │
     │  · 记录操作日志  │
     │  · 更新冷却时间  │
     └────────────────┘
```

#### 3.2.1 验证弹窗处理（HANDLE_VERIFY）

```
检测到操作被验证弹窗拦截
│
├── 截图 + vision_bridge 快速识别弹窗类型
│   ├── "安全验证" / "重新登录" → 进入 SMS 重登
│   ├── "滑块验证" → 上报用户手动处理
│   └── "未知弹窗" → 截图 + 上报
│
├── 特征锚点检测
│   ├── 检测到 `.r-captcha-modal` → 滑块验证（用户处理）
│   ├── 检测到 `input[placeholder*="验证码"]` → SMS 流程
│   └── 检测到登录弹窗 → SMS 登录恢复
│
└── 3次尝试均失败 → 截图 + 上报 NEEDS_MANUAL
```

#### 3.2.2 操作冷却管理

```python
class CooldownManager:
    """操作间隔管理 — 防止风控"""

    MIN_INTERVAL = 3       # 最小操作间隔（秒）
    MAX_INTERVAL = 8       # 最大操作间隔（秒）
    COMMENT_COOLDOWN = 60  # 评论后冷却 60 秒
    ACTION_COUNTER_RESET = 1800  # 30分钟后重置操作计数

    # 每个操作类型的推荐间隔
    COOLDOWNS = {
        "like":        (3, 8),
        "collect":     (5, 12),
        "comment":     (30, 60),
        "follow":      (60, 120),
        "scroll":      (2, 5),
        "click_note":  (3, 8),
    }
```

---

## 四、Layer 3: 蓝图编排层

### 4.1 蓝图格式扩展

**现有格式**：
```json
{
  "step_id": 1,
  "op": "goto_home",
  "args": {}
}
```

**扩展后格式（加入状态检查）**：
```json
{
  "step_id": 1,
  "op": "goto_home",
  "args": {},
  "state_check": {
    "require_login": true,         // 执行前确认登录
    "verify_after": true,          // 执行后检查是否触发验证
    "expected": "home_page",       // 预期的页面状态特征
    "fallback_op": "sms_relogin",  // 触发验证后的降级操作
    "max_retries": 2,              // 最大重试次数
    "retry_delay": 5               // 重试间隔（秒）
  }
}
```

### 4.2 蓝图执行引擎

```python
class BlueprintEngine:
    """蓝图的执行引擎"""

    async def execute(self, blueprint: dict, account_id: str):
        """执行整个蓝图"""
        for step in blueprint["steps"]:
            login_ok = await self.login_machine.ensure_login(page, account_id)
            if login_ok.status != "LOGGED_IN":
                return self._halt_and_report(login_ok)

            result = await self._execute_step(step)
            if result.triggered_verification:
                result = await self._handle_verification(result)
                if not result.success:
                    return self._halt_and_report(result)

            await self.cooldown.wait(step.op)

    async def _execute_step(self, step: dict) -> StepResult:
        """执行单个步骤"""
        op_func = self.registry.get(step["op"])
        if not op_func:
            return StepResult(success=False, error=f"Unknown op: {step['op']}")
        try:
            await op_func(self.page, **step.get("args", {}))
            return StepResult(success=True)
        except VerificationError:
            return StepResult(success=True, triggered_verification=True)
```

---

## 五、异常处理体系

### 5.1 异常分级

| 等级 | 名称 | 处理方式 | 举例 |
|:-----|:-----|:---------|:-----|
| P0 | 致命 | 停止执行，上报用户 | 浏览器崩溃、账号被封 |
| P1 | 可恢复 | 自动重试 3 次 → 降级 | 网络超时、验证弹窗 |
| P2 | 可忽略 | 跳过当前步骤继续 | 单个笔记加载失败 |
| P3 | 监控 | 记录日志不处理 | 页面微小的布局变化 |

### 5.2 特征锚点体系

**核心思路**：每个"状态"都有一个或多个**特征锚点**（DOM/Cookie/URL），通过这些锚点来判断当前处于什么状态。

```
当前状态 = 锚点匹配结果
    ↓
检测到特征A + 特征B = 已登录
检测到特征C + 特征D = 被验证弹窗拦截
检测到特征E + 特征F = 需要 SMS 登录
```

#### 小红书特征锚点

| 状态 | 锚点 DOM | 锚点 URL 特征 |
|:-----|:---------|:--------------|
| 已登录 | `.user-avatar` / `.reds-count` | `explore` / `feed` |
| 登录弹窗 | `input[placeholder*="手机"]` / `.login-container` | - |
| 验证码输入 | `input[placeholder*="验证码"]` | - |
| 滑块验证 | `.r-captcha-modal` / `#fe-captcha-container` | - |
| 操作限制 | "操作太频繁" / 弹窗含"验证" | - |

#### 抖音特征锚点

| 状态 | 锚点 DOM | 锚点 URL 特征 |
|:-----|:---------|:--------------|
| 已登录 | `[data-e2e=user-avatar]` | `/` / `feed` |
| 登录弹窗 | 包含"登录"的按钮出现 | - |
| 验证码 | `input` + 文案"验证码" | - |

### 5.3 视觉分析降级

当 DOM 锚点判断失败（页面改版、弹窗未知），触发视觉分析：

```
DOM判断ambiguous → 截图 → vision_bridge 分析
    ↓
返回结构化描述：
{
  "has_login": true/false,
  "visible_dialogs": ["登录弹窗", "滑块验证"],
  "key_text": ["手机号", "验证码", "同意并登录"],
  "buttons": [{"text": "登录", "position": (x,y)}],
  "input_fields": [{"type": "phone", "position": (x,y)}]
}
    ↓
状态机根据视觉输出判断当前状态
    ↓
操作建议返回给执行引擎
```

---

## 六、完整执行链路举例

### 案例：小红书 `xhs_daily` 养号

```
① 选账号 xhs_01
   ↓
② 浏览器管理层：开 Camoufox 窗口 702×783 @(0,0)
   ↓
③ 登录状态机：
   → DETECT_LOGIN_STATE
   → LOGGED_IN ✅（3 秒检测到头像 DOM）
   ↓
④ 蓝图开始执行：
   Step 1: xhs_goto_home → 导航到首页
     → LOGIN_CHECK ✅ → POST_CHECK: 正常
     → COOLDOWN: 3s
   Step 2: xhs_scroll_feed → 滑动瀑布流
     → LOGIN_CHECK ✅ → POST_CHECK: 正常
     → COOLDOWN: 5s
   Step 3: xhs_click_note → 点开一篇笔记
     → LOGIN_CHECK ✅ → POST_CHECK: 正常
     → COOLDOWN: 8s
   Step 4: wait_watch → 浏览10秒
     → OK
     ↓
   Step 5: xhs_like → 点赞
     → LOGIN_CHECK ✅
     → 执行点赞
     → POST_CHECK: ❌ 触发验证弹窗！
       → HANDLE_VERIFY: 检测到登录弹窗
       → SMS 重登流程
       → LOGGED_IN ✅ 恢复
       → 跳过当前 Step，进入下一轮冷却
     → COOLDOWN: 8s
   Step 6: xhs_collect → 收藏
     → LOGIN_CHECK ✅ → 继续...
   ...
   Step 17: 完成本轮
   ↓
⑤ 关闭浏览器 / 保持打开（看配置）
```

---

## 七、三台机器的差异化配置

```yaml
# 每台机器 ~/.workbuddy/agentos.yaml
machines:
  chengzigedeAir:
    role: master
    max_browsers: 4
    vision_model: true
    accounts: [xhs_01, douyin_test, douyin_133, douyin_134]

  5kechengdeAir:
    role: worker
    max_browsers: 2
    vision_model: false
    accounts: [douyin_135, douyin_136]

  7kecheng:
    role: worker
    max_browsers: 2
    vision_model: false
    accounts: [douyin_137, xhs_02]
```

---

## 八、实施路线图

### Phase A: 登录状态机核心（1-2天）
| 优先级 | 任务 | 产出 |
|:-------|:-----|:------|
| P0 | `LoginStateMachine` 类（检测 + 恢复） | login_state_machine.py |
| P0 | 小红书/Douyin 登录锚点表 | 整理到 selectors.py |
| P1 | 登录恢复之 SMS 重登 + "同意并登录" | 复用 sms_login.py |
| P1 | 截图 + 视觉分析降级 | vision_bridge 对接 |

### Phase B: 操作状态机 + 蓝图引擎（2-3天）
| 优先级 | 任务 | 产出 |
|:-------|:-----|:------|
| P0 | 蓝图执行引擎（含状态检查） | blueprint_engine.py |
| P0 | 操作冷却管理 | cooldown_manager.py |
| P1 | 验证弹窗自动检测 + 处理 | handle_verify.py |
| P1 | 操作日志记录 | operation_log.py |

### Phase C: 异常处理 + 管理界面（3-4天）
| 优先级 | 任务 | 产出 |
|:-------|:-----|:------|
| P1 | 异常分级 + 自动重试 | exception_handler.py |
| P2 | 操作失败截图自动库 | error_screenshot_manager.py |
| P2 | Dashboard 执行历史视图 | 对接现有 ops 路由 |

### Phase D: 多机协调 + 联邦视图（4-5天）
| 优先级 | 任务 | 产出 |
|:-------|:-----|:------|
| P2 | 三台机器状态同步 | fleet_sync 增强 |
| P2 | Dashboard 显示所有机器执行状态 | 联邦视图完善 |
| P3 | 主控机下发蓝图到节点机 | c2 命令扩展 |

---

## 九、关键文件清单

| 文件 | 说明 | 状态 |
|:-----|:------|:------|
| `login_state_machine.py` | 登录状态机核心 | ❌ 待新建 |
| `blueprint_engine.py` | 蓝图执行引擎（含状态检查） | ❌ 待新建 |
| `cooldown_manager.py` | 操作冷却管理 | ❌ 待新建 |
| `handle_verify.py` | 验证弹窗检测 + 处理 | ❌ 待新建 |
| `vision_bridge.py` | oMLX 视觉分析桥接 | ✅ 已存在 |
| `cdp_connector.py` | 浏览器启动管理 | ✅ 已存在 |
| `browser_utils.py` | GracefulBrowser 浏览器生命周期 | ✅ 已存在 |
| `sms_login.py` | SMS 验证码登录 | ✅ 已存在 |
| `xhs_login.py` | 小红书原子操作 | ✅ 已存在 |

---

## 十、常见执行流程图

```
开浏览器 → 加载账号 → 检测登录 → 已登录 ✅ → 执行操作
                                      │
                                      ▼ 未登录
                               Cookie 恢复 → 检测 → 已登录
                                      │
                                      ▼ 仍失败
                               SMS 登录 → 检测 → 已登录
                                      │
                                      ▼ 3次失败
                               截图上报 → 手动介入
```

```
执行操作中 → POST_CHECK
    │
    ├── 正常完成 → 冷却等待 → 下一步
    │
    └── 触发验证弹窗
        │
        ├── 检测到"验证码输入" → SMS 重登 → 恢复
        │
        ├── 检测到"滑块验证" → 截图 → 上报用户
        │
        ├── 检测到"操作频繁" → 延长冷却 → 恢复
        │
        └── 未知弹窗 → 截图 → vision_bridge 分析 → 处理
```

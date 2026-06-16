---
type: concept
domain: system
nature: architecture
tags: [agentos, v3.0, matrix, login, auth, sms]
status: draft
created: 2026-06-16
updated: 2026-06-16
version: 1.0.0
---

# AgentOS 联邦登录系统 — 技术图谱 v1.0

> 目标: 全自动跨平台登录，智能匹配登录方式，零人工介入

---

## 一、现有代码结构总览

```
scripts/
├── login_identity.py              # 手动登录（旧，等待用户按Enter）
├── auth_manager.py                # 登录态检测原子模块 ✅
├── cdp_connector.py               # 浏览器连接器（Camoufox持久化/CDP）✅
│
├── matrix_modules/account/
│   ├── douyin_login.py            # 抖音自动登录（含SMS）✅ 核心
│   ├── xiaohongshu_login.py       # 小红书自动登录 ❌ 缺失
│   ├── sms_login.py               # SMS验证码原子操作 ✅ 核心
│   └── sms/
│       ├── __init__.py            # 统一导出
│       ├── base.py                # SMSHandler 抽象基类
│       └── api.py                 # ApiSMSHandler API轮询 ✅ 核心
│
├── dashboard/plugins/
│   └── sms_proxy_api.py           # Dashboard登录API（调的是旧脚本）⚠️
│
└── archive/
    ├── scan_login.py              # 扫码登录（归档）📦
    └── test_sms_login.py          # 短信登录测试（归档）📦
```

## 二、平台登录流程对比

### 2.1 抖音登录（已有 douyin_login.py）

```
前置检测:
  1. 读取 accounts.yaml → 手机号
  2. 创建/确认身份目录
  3. 启动 Camoufox 持久化浏览器

执行流程:
  1. 导航 https://www.douyin.com/
  2. 等待6秒 → 检测登录面板 #login-panel-new
  3. 如果已经登录（检测 data-e2e=user-avatar）→ 跳过
  4. 没检测到面板 → 等待15秒让用户手动点"登录"
  5. 检测到面板 → 调用 sms_login 流程

SMS登录子流程 (sms_login.py):
  Step 1: 点"一键登录"按钮
  Step 2: 等待验证码输入框出现
  Step 3: ApiSMSHandler 轮询获取验证码（最多3次，超时重发）
  Step 4: 填入验证码（JS设置value+dispatchEvent）
  Step 5: 点确认（DOM点击 → 系统级鼠标兜底）
  Step 6: 验证登录态（面板消失+有头像）

后置处理:
  - 写操作日志 login_log.jsonl
  - 采集用户资料 ProfileScraper
  - 浏览器保持打开
```

### 2.2 小红书登录（缺失）

```
当前状态:
  - 无独立入口脚本
  - sms_login.py 的原子操作可复用（点击按钮/填验证码/点确认）
  - 登录面板检测、一键登录、URL导航需要适配

差异点:
  - 登录URL不同: https://www.xiaohongshu.com/explore
  - 登录面板CSS选择器不同
  - "一键登录"按钮文本可能不同
  - 登录态Cookie名不同: a1 / web_session
```

### 2.3 扫码登录（归档）

```
archive/scan_login.py 已实现:
  - 生成二维码
  - 检测扫码结果
  - 确认登录

适用场景: 桌面端抖音扫码登录
```

## 三、登录态检测体系

### 3.1 四维状态检测（当前 sms_proxy_api.py）

| 维度 | 检测方式 | 判断依据 |
|:-----|:---------|:---------|
| has_identity | 文件夹存在性 | `identities/{name}/user_data/` 是否存在 |
| has_cookie | Firefox cookies.sqlite | `SELECT count(*) FROM moz_cookies WHERE name LIKE '%session%'` |
| has_profile | 文件存在性 | `user_data/profiles.yaml` 是否存在 |
| has_registry | 注册表存在性 | 账号是否在 accounts.yaml 注册 |

### 3.2 Cookie 级检测（auth_manager.py）

| 平台 | 关键Cookie | 检测方式 |
|:-----|:-----------|:---------|
| 抖音 | `sessionid`, `sid_guard` | Cookie名匹配 |
| 小红书 | `a1`, `web_session` | Cookie名匹配 |

### 3.3 DOM 级检测（auth_manager.py）

| 平台 | 选择器 | 说明 |
|:-----|:-------|:-----|
| 抖音 | `[data-e2e='user-avatar']` | 主指示器 |
| 抖音 | `[data-e2e='user-detail']` | 备用 |
| 小红书 | `.user-avatar` | 头像元素 |
| 小红书 | `.reds-count` | 计数元素 |

### 3.4 综合检测逻辑 (get_login_status)

```
Cookie 检测ok 且 DOM 检测ok → method='both'
Cookie 检测ok               → method='cookie'
DOM 检测ok                  → method='dom'
兜底: Cookie数量 > 30       → 判定已登录
```

## 四、需要补充的环节

### P0: Dashboard 调正确脚本
```
当前:  /api/matrix/accounts/{id}/login → login_identity.py（手动）
预期:  根据 platform 自动路由:
         douyin     → douyin_login.py（全自动）
         xiaohongshu → xiaohongshu_login.py（待创建）
```

### P0: 小红书入口脚本 (xiaohongshu_login.py)
```
复用 douyin_login.py 框架 + sms_login.py，仅修改:
  - 平台URL → xiaohongshu.com/explore
  - 登录面板选择器 → 小红书专用
  - 一键登录按钮文本 → 适配小红书
  - Cookie规则 → auth_manager 已有
```

### P1: 智能匹配引擎
```
根据账号信息自动选择登录方式:
  1. 已登录 → 跳过（检测 has_cookie + 验证过期）
  2. 有身份无Cookie → 按平台执行自动登录
  3. 首次登录 → 创建身份 → 自动登录
  4. 短信登录 → 自动触发短信 → 轮询获取 → 自动填入
  5. 扫码兜底 → 检测平台是否支持扫码
```

### P1: 过期session检测
```
方法: 在登录页检测"已登录"状态后，导航到个人中心
      检查是否可加载用户信息（不发敏感请求）
      如果跳转到登录页 → session过期
```

### P2: 跨机路由
```
远程机器登录:
  Dashboard → fire-and-forget 发送命令
  远程机器 → 执行 douyin_login.py
  完成后 → 更新本地 has_cookie 状态
```

## 五、当前系统完整调用链

```
Dashboard 🔑 点击
  ↓
POST /api/matrix/accounts/{id}/login
  ↓
sms_proxy_api.py: api_account_login()
  ↓
subprocess.Popen([agent-os python, -m, mc, account, login, {id}])
  ↓  (当前链路)
mc/cli.py: cmd_login()
  ↓
subprocess.Popen([sys.executable, login_identity.py, {id}, --platform {p}])
  ↓
login_identity.py → 开Camoufox → 等Enter → 检测Cookie → 退出
  ⚠️ 需要人按Enter，不是全自动

  ↓  (目标链路)
mc/cli.py: 新增路由 → 检测platform
  ↓  douyin
douyin_login.py → 开Camoufox → 自动点一键登录 → 自动收短信 → 自动填 → 自动确认 → 自动验证
  ↓  xiaohongshu (待创建)
xiaohongshu_login.py → 同上逻辑
```

## 六、设计原则（不改原有代码，只加新功能）

1. **原有脚本不动** — `login_identity.py` 保留，通过新入口分流
2. **新增平台脚本** — 按 `douyin_login.py` 模板创建 `xiaohongshu_login.py`
3. **智能分流** — `mc account login` 检测 platform 自动路由
4. **逐步替换** — 新流程跑通后再切换 Dashboard 默认调用
5. **兜底机制** — 自动流程失败后提示用户手动操作

---

*版本: 1.0.0-draft | 2026-06-16*

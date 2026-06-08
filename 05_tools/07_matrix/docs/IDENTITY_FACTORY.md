# 🦀 身份工厂：反检测 + 持久化标准化方案

> 基于 Camoufox 的「反检测伪装」+「持久化上下文」构建的多账号身份管理系统
> 版本: v1.0 | 日期: 2026-05-03

---

## 一、核心认知纠偏

### 1.1 反检测 ≠ 反持久化

| 概念 | 定义 | 关系 |
|---|---|---|
| **反检测 (Anti-Detection)** | 让网站无法识别你是自动化工具/不同身份 | Camoufox 的**设计目标** |
| **反持久化 (Anti-Persistence)** | 每次关闭后清空所有状态 | Camoufox 的**默认行为**（不是设计目标） |
| **持久化 (Persistence)** | 保存并复用登录态、浏览数据 | Camoufox **完全支持**，只是需要正确配置 |

**关键结论**：Camoufox 的默认行为（临时 profile + 随机指纹）是为了开发测试方便，**不代表它不支持持久化**。其 Playwright API 天然支持 `launch_persistent_context` + `user_data_dir`。

### 1.2 Camoufox 的真正优势

| 维度 | Chrome Profiles | Camoufox 持久化 |
|---|---|---|
| 指纹隔离 | ❌ 同一台机器的真实指纹 | ✅ 每身份独立伪造指纹 |
| 反检测深度 | ❌ JS 层修补（易被检测） | ✅ C++ 源码级修改（底层注入噪声） |
| 内核优势 | ❌ Chrome 被重点监控 | ✅ Firefox 冷门，避开重点关照 |
| Cloudflare 通过率 | ~50% | **88.58%**（2026 评测） |
| 身份隔离 | ❌ 数据隔离 ≠ 身份隔离 | ✅ 真正的"不同人用不同电脑" |
| 持久化能力 | ✅ user-data-dir 原生支持 | ✅ persistent_context + user_data_dir |

### 1.3 当前代码的三个致命缺陷

#### 缺陷一：没有使用持久化上下文

**位置**：`cdp_connector.py:69-104` — `_launch_camoufox()`

```python
cf = AsyncCamoufox(**kwargs)
self._camoufox_browser = await cf.start()
```

`start()` → `AsyncNewBrowser(..., persistent_context=False)` → `playwright.firefox.launch()`（临时 profile）

**影响**：每次启动生成 `/tmp/playwright_xxx/` 临时目录，所有登录态丢失。

#### 缺陷二：没有固化指纹

**位置**：`cdp_connector.py:73-85`

```python
kwargs = {
    'os': 'windows',      # 只约束了范围（Windows 池）
    'humanize': 1.5,
    # ← 没有 fingerprint 参数
}
```

**链路**：`launch_options()` → `if fingerprint is None` → `generate_fingerprint(random)` → 每次指纹不同

**影响**：抖音服务端检测到「同一 session_id 对应不同设备指纹」→ 强制短信验证。

#### 缺陷三：Cookie 注入是错误做法

**位置**：`yanghao_runner.py:149-164`

```python
cookie_file = ... / f"{acct_id}_cookies.json"
cookies = json.loads(cookie_file.read_text())
# 注入 Cookie
for c in cookies:
    await conn.context.add_cookies([{...}])
```

**问题**：抖音风控的校验逻辑是「session_id + 设备指纹」双重校验。Cookie 注入只传了 session_id，但当前设备的随机指纹与当初登录时的指纹不匹配 → 风控拦截 → 强制短信验证。

---

## 二、正确架构：身份工厂（Identity Factory）

### 2.1 核心理念

把「反检测伪装」和「持久化登录」变成标准化工程组件：

```
┌──────────────────────────────────────────────────────────┐
│                    身份工厂 (Identity Factory)             │
├───────────────┬────────────────┬─────────────────────────┤
│  create_identity  │  login_identity   │     run_task            │
│  (BrowserForge    │  (手动登录一次     │     (以登录态自动执行)    │
│   生成固化指纹)   │    state 保存)    │                         │
├───────────────┴────────────────┴─────────────────────────┤
│                    identities/                            │
│   ├── douyin_01/        ← 第一个身份                      │
│   │   ├── config.yaml   ← 固化指纹 + 代理配置             │
│   │   └── user_data/    ← Firefox 持久化 Profile          │
│   ├── douyin_02/        ← 第二个身份                      │
│   │   ├── config.yaml                                    │
│   │   └── user_data/                                     │
│   └── ...                                                │
└──────────────────────────────────────────────────────────┘
```

### 2.2 核心规则：一手机号 = 一身份

**同手机号的抖音和小红书账号必须共用同一个 identity_dir。**

这是经过实践验证的结论：

| ❌ 错误做法 | ✅ 正确做法 |
|:-----------|:-----------|
| douyin_01 → `identities/douyin_01_camo` | douyin_01 → `identities/douyin_01_camo` |
| xhs_01 → `identities/xhs_01`（新建身份） | xhs_01 → `identities/douyin_01_camo`（**复用**） |
| 结果：两个浏览器指纹，两个登录态 | 结果：一个浏览器指纹，一份登录态，抖音和小红书 cookie 共存 |

**为什么必须相同？**
- 一个手机号绑定一个实际的"人"，反检测的本质是让平台认为你是"同一个人在不同网站活动"
- 抖音和小红书分别存储 session cookie，互不冲突
- 只需用 `CookieGuard` 保护对方平台的 cookie（删除时别误删）

**代码中如何配置（accounts.override.yaml）**：
```yaml
- id: douyin_04
  phone: '18550099083'
  enabled: true
- id: xhs_04
  phone: '18550099083'   # 同手机号
  enabled: true
```

`MatrixManager` 的 `list_accounts()` 方法会自动为同手机号的 xhs 账号分配与 douyin 相同的 identity_dir。

**验证方法**：
```bash
cd scripts && python -c "
from mc.engine import resolve_account
a = resolve_account('xhs_04')
print(a.get('identity_hint'))  # 输出: douyin_04（与 douyin_04 相同）
"
```

### 2.2 目录结构

```
agent-local/tools/matrix/
├── identities/                  # 所有身份集中存放
│   ├── douyin_01/               # 抖音主号
│   │   ├── config.yaml          # 指纹 + 代理配置（可版本控制）
│   │   └── user_data/           # 持久化 Profile（不提交 Git）
│   ├── douyin_02/               # 抖音副号
│   │   ├── config.yaml
│   │   └── user_data/
│   └── douyin_camo01/           # 第三个号（Chrome 或 Camoufox）
│       ├── config.yaml
│       └── user_data/
├── scripts/                     # 已有脚本，需改造
│   ├── cdp_connector.py         # → 新增: launch_camoufox_persistent()
│   ├── yanghao_runner.py        # → 新增: --identity 模式
│   ├── camoufox_manager.py      # → 改造: 支持 persistent_context
│   └── ... (新建)
│   ├── create_identity.py       # 生成新身份（指纹固化）
│   ├── login_identity.py        # 首次手动登录
│   └── run_task.py              # 以已登录身份执行任务
└── config/
    └── accounts.yaml            # → 重构: 指向 identities/ 目录
```

### 2.3 配置文件格式 `config.yaml`

```yaml
# identities/douyin_01/config.yaml
identity:
  name: "douyin_01"
  platform: "douyin"
  proxy: null                    # 可选：固定代理
  notes: "抖音主号"

# 由 BrowserForge 生成并固化的指纹
fingerprint:
  navigator:
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0"
    platform: "Win32"
    hardwareConcurrency: 8
    deviceMemory: 8
    language: "zh-CN"
  screen:
    width: 1920
    height: 1080
    availWidth: 1920
    availHeight: 1040
    colorDepth: 24
  webgl:
    vendor: "Google Inc. (Intel)"
    renderer: "ANGLE (Intel, Intel(R) UHD Graphics (0x00009BC4) Direct3D11 vs_5_0 ps_5_0)"
  # ... 完整指纹由 BrowserForge 生成
```

### 2.4 关键 API：持久化上下文

```
AsyncCamoufox(persistent_context=True, user_data_dir=path, fingerprint=fixed_fp)
    ↓
AsyncNewBrowser(..., persistent_context=True)
    ↓
playwright.firefox.launch_persistent_context(user_data_dir=path, ...)
    ✅ 所有状态保存到 path 下
    ✅ 下次启动直接复用
```

对应 Chrome 的方案：

```
Google Chrome --user-data-dir=path --remote-debugging-port=port
    ↓
CDP connect
    ✅ 所有状态保存在 path 下
    ✅ 浏览器不退出，状态持久
```

**两者本质相同**，差异在于：
- Chrome：浏览器进程常驻 + CDP 连接
- Camoufox：`launch_persistent_context` 管理生命周期

---

## 三、标准化流程

### 3.1 创建身份 → `create_identity`

```
BrowserForge.generate()
    ↓
生成完整设备指纹（固定）
    ↓
写入 identities/{name}/config.yaml
    ↓
✅ 身份创建完成
```

### 3.2 首次登录 → `login_identity`

```
启动 Camoufox(headless=False, persistent_context=True, user_data_dir=path, fingerprint=fixed)
    ↓
打开目标网站（抖音首页）
    ↓
弹窗等待 → 用户手动登录
    ↓
用户按 Enter 确认
    ↓
所有登录态保存到 user_data/
    ↓
✅ 身份激活完成
```

**这是唯一一次手动操作**。之后所有任务复用这个 state。

### 3.3 日常任务 → `run_task`

```
启动 Camoufox(headless=True, persistent_context=True, user_data_dir=path, fingerprint=fixed)
    ↓
直接以已登录状态访问抖音
    ↓
执行蓝图操作（浏览/点赞/收藏等）
    ↓
保持浏览器不退出，继续下一轮
    ↓
✅ 循环执行
```

### 3.4 多账号并行

```
for identity in [douyin_01, douyin_02, douyin_camo01]:
    创建身份目录
    首次登录（手动）
    
# 日常运行
asyncio.gather(
    run_loop("douyin_01"),
    run_loop("douyin_02"),
    run_loop("douyin_camo01"),
)
```

---

## 四、与现有代码的关系

### 4.1 保留的部分

| 文件 | 用途 | 保留 |
|---|---|---|
| `blueprints/` | 蓝图定义 | ✅ 不变 |
| `douyin_ops.py` | 原子操作 | ✅ 不变 |
| `atom_ops.py` | 原子操作 | ✅ 不变 |
| `auth_manager.py` | 登录状态检测 | ✅ 改进 |
| `task_engine.py` | 蓝图执行引擎 | ✅ 改进加载方式 |
| `anti_detection.py` | 反检测 | ✅ 改进 |
| `accounts.yaml` | 账号配置 | 🛠 重构格式 |

### 4.2 需要改造的文件

| 文件 | 改造内容 | 优先级 |
|---|---|---|
| `cdp_connector.py` | 新增 `_launch_camoufox_persistent()`，支持 `persistent_context` + `user_data_dir` + 固化指纹 | **P0** |
| `yanghao_runner.py` | 新增 `--identity` 模式，通过身份目录启动 | **P0** |
| `camoufox_manager.py` | 改造 `--launch` 使用持久化上下文 | **P1** |
| `accounts.yaml` | 新增 `identity_dir` 字段指向 identities/ | P1 |
| `config_template/` | 更新模板 | P2 |

### 4.3 新增文件

| 文件 | 功能 | 优先级 |
|---|---|---|
| `scripts/create_identity.py` | 用 BrowserForge 生成指纹并创建身份目录 | **P0** |
| `scripts/login_identity.py` | 标准化首次登录流程 | **P0** |
| `scripts/run_task.py` | 以已登录身份执行自动化任务 | P1 |
| `docs/IDENTITY_FACTORY.md` | 本文档 | ✅ 已完成 |

---

## 五、关键注意事项

### 5.1 user_data 不可共享
- 每个身份独立的 `user_data/` 目录
- 禁止混用，否则身份关联
- 禁止提交到 Git（包含登录态）

### 5.2 指纹固化后不可变
- 一旦身份创建完成，`config.yaml` 中的指纹不可修改
- 修改指纹 = 换了一台电脑 → 掉登录
- 如果需要新指纹 → 创建新身份，重新登录

### 5.3 代理一致性
- 一个身份最好绑定固定代理
- 代理变更会触发 IP 地理位置突变 → 风控
- 在 `config.yaml` 的 `identity.proxy` 中指定

### 5.4 浏览器常驻模式
- 登录后浏览器不退出（当前循环模式正确）
- `persistent_context` 确保状态即时刷新
- 避免频繁启停（减少指纹比对次数）

### 5.5 检测结论

根据 [2026 反检测浏览器评测](https://www.browserling.com/blog/2026-antidetect-browsers-review)，Camoufox 在以下维度表现：

| 指标 | Camoufox | Chrome stealth | Chrome 原生 |
|---|---|---|---|
| Cloudflare 通过率 | **88.58%** | 11.21% (patchright) | ~50% |
| Canvas 指纹伪装 | ✅ C++ 级 | ⚠️ JS 级 | ❌ |
| WebGL 伪装 | ✅ | ⚠️ | ❌ |
| 字体伪装 | ✅ | ⚠️ | ❌ |
| 多身份隔离 | ✅ 身份级 | ⚠️ Profile 级 | Profile 级 |

Camoufox + 持久化上下文 + BrowserForge 固化指纹 + 固定代理 = 当前最优方案。

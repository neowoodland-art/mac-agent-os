# TOOL.md — 矩阵养号系统 Matrix

> **工具版本**: v4.1  
> **接入日期**: 2026-04-29  
> **维护者**: ghai  
> **路径方案**: local.yaml + local_paths.py（无软链接，多机安全）  
> **更新日期**: 2026-05-03  
> **平台支持**: 抖音 ✅ | 小红书 🔄 | 知乎 🔄 | 快手 📋

---

## 一句话说明

通过 Chrome CDP 和 Camoufox（Firefox 内核）程序化控制浏览器，自动完成多平台社交账号的日常养号任务（浏览、点赞、评论、收藏等），模拟真实用户行为。

---

## 架构概览（v4.1）

```
matrix.py ← 统一 CLI 入口（account/nurture/config/status 四域）
    │
    ├── account/           ← 账号管理域
    │   ├── create_identity.py  ← 身份工厂（BrowserForge 固化指纹）
    │   ├── login_identity.py   ← 首次登录（持久化保存登录态）
    │   ├── sms/               ← 短信验证码接口（预留）
    │   └── captcha/           ← 图形验证码接口（预留）
    │
    ├── nurture/           ← 养号执行域
    │   ├── runner.py          ← 常驻循环引擎（Chrome CDP + Camoufox 双引擎）
    │   └── behavior.py        ← 行为模拟参数化（13项可配置）
    │
    ├── engine/            ← 浏览器引擎层
    │   └── cdp_connector.py   ← Chrome CDP / Camoufox 持久化连接
    │
    ├── ops/               ← 操作层（多平台）
    │   └── douyin/
    │       ├── browse.py      ← 浏览类操作
    │       └── interact.py    ← 交互类操作
    │
    └── config/            ← 配置管理
        └── accounts.yaml      ← 账号配置（含 identity_dir）
```
└── screenshots/                  # 截图快照

⭐ 路径解析方式 (v4.0):
  local_paths.py → 读取 local.yaml → 获取 data_root
  → config_path("x")     → data_root/config/x
  → data_path("x")       → data_root/data/x
  → logs_path("x")       → data_root/logs/x
  → profiles_path("x")   → data_root/profiles/x
  → screenshots_path("x")→ data_root/screenshots/x
  → code_dir()           → 05_tools/07_matrix/（代码目录）
```

---

## 快速使用

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix

# 启动抖音账号（Chrome CDP）
python scripts/switch_account.py --method profile --target douyin_01 --port 9222

# 执行日常浏览蓝图
python scripts/task_engine.py --blueprint douyin_browse_v2 --account douyin_01

# 定时调度
python scripts/task_scheduler.py

# 查看账号状态
python scripts/switch_account.py --status
```

---

## 环境依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 使用 agent-os venv |
| Google Chrome | 最新版 | CDP 直连 |
| Camoufox | 最新版 | Firefox 内核，反检测 |
| playwright | ≥1.40 | 浏览器自动化 |

完整依赖见 `requirements.txt`，安装：
```bash
pip install -r ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/requirements.txt
```

---

## 新机恢复

```bash
# 一键恢复（建立本地目录骨架 + 生成 local.yaml + 安装依赖）
bash ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/install.sh

# 然后将账号配置复制/重新填写
cp ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/config_template/accounts.yaml \
   ~/workbuddy-agent-os/agent-local/tools/matrix/config/accounts.yaml
# 编辑 accounts.yaml 填入本机账号信息
```

---

## 统一 CLI 使用（v4.1 推荐）

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts

# 账号管理
python matrix.py account list                        # 列出所有账号
python matrix.py account create <name>               # 创建新身份
python matrix.py account login <name>                # 首次登录
python matrix.py account status [name]               # 查看状态

# 养号执行
python matrix.py nurture run -a <name> -r 10         # 单账号循环
python matrix.py nurture run -a a -a b -r 10         # 多账号并发
python matrix.py nurture run -a <name> -r 10 --daemon # 保持连接不退出

# 配置管理
python matrix.py config show                          # 查看配置
python matrix.py config blueprint list                # 查看蓝图

# 状态监控
python matrix.py status all                          # 全局状态
python matrix.py status browsers                     # 浏览器状态
```

---

## 核心机制

### 双引擎架构

| 引擎 | 适用账号 | 连接方式 | 窗口控制 | 视口控制 |
|------|----------|----------|----------|----------|
| Chrome CDP | douyin_01/02 | CDP WebSocket | --window-size 参数 | Emulation.setDeviceMetricsOverride |
| Camoufox 持久化 | douyin_camo01 | launch_persistent_context | window.open(features) | 启动前 config 注入 DOM 属性 |

### Camoufox 窗口/视口控制方案（v4.1 修复）

**问题**：Playwright 的 Firefox `launch_persistent_context` 模式完全接管了窗口管理和视口设置，
`--width/--height` 参数、`window.resizeTo`、`page.set_viewport_size` 均无效。

**解决方案（双层控制）**：

1. **物理窗口尺寸** — 启动后用 `window.open(url, name, 'width=702,height=783')` 创建新窗口。
   Firefox 的 `window.open` 特性参数字段是原生支持的，Playwright 无法覆盖。

2. **页面视口/屏幕尺寸** — 通过 Camoufox 的 `config` 参数在启动前注入 DOM 属性覆盖：
   ```python
   config={
       "window.innerWidth": 702,
       "window.innerHeight": 783,
       "window.outerWidth": 702,
       "window.outerHeight": 783,
       "screen.width": 702,
       "screen.height": 783,
       "screen.availWidth": 702,
       "screen.availHeight": 783,
   }
   ```
   Camoufox 的扩展会在每个页面加载前读取 config 并覆盖 DOM 属性，
   效果等同 Playwright 的 `set_viewport_size` 但不受其限制。

3. **窗口尺寸配置** — 写入 `identities/{name}/config.yaml`：
   ```yaml
   window: [702, 783]
   ```

### 行为模拟参数化

行为参数可在 `identities/{name}/config.yaml` 中覆盖默认值：

```yaml
behavior:
  base_delay: 1.5              # 操作间基础间隔(秒)
  delay_variance: 0.8          # 随机波动范围
  attention:
    distraction_chance: 0.05   # "分心"概率
    watch_duration: [4, 12]    # 观看视频时长(秒)
  round_break:
    min_break: 5               # 轮间最短休息(秒)
    max_break: 20              # 轮间最长休息(秒)
```

---

## 接口预留

| 模块 | 状态 | 说明 |
|------|------|------|
| `account/sms/base.py` | 抽象基类 | 短信验证码处理（默认手动输入） |
| `account/captcha/base.py` | 抽象基类 | 图形验证码处理（默认手动处理） |
| `ops/xiaohongshu/` | 目录预留 | 小红书操作集 |
| `ops/kuaishou/` | 目录预留 | 快手操作集 |
| `ops/bilibili/` | 目录预留 | B站操作集 |

---

## 环境依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 使用 agent-os venv |
| Google Chrome | 最新版 | CDP 直连 |
| Camoufox | ≥0.4.11 | Firefox 内核，反检测 |
| playwright | ≥1.40 | 浏览器自动化 |
| browserforge | 最新 | BrowserForge 指纹生成 |
| camoufox | ≥0.4 | Firefox 反检测浏览器 |

完整依赖见 `requirements.txt`，安装：
```bash
pip install -r ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/requirements.txt
```

## 多机同步说明 (v4.0)

本工具不再使用软链接，改为 `local.yaml` + `local_paths.py` 方案：

- `local.yaml` — 记录本机数据目录路径，每台机器独立生成
- `local.yaml` 不参与坚果云同步（请加入排除列表）
- 所有 Python 脚本通过 `scripts/local_paths.py` 读取路径
- 任何脚本启动时若 `local.yaml` 不存在，会报错并提示运行 `install.sh`

`local.yaml` 格式（自动生成，无需手动编辑）：
```yaml
matrix:
  local_data_root: /Users/xxx/workbuddy-agent-os/agent-local/tools/matrix
```

---

## 当前开发状态

| 阶段 | 内容 | 状态 |
|------|------|------|
| A | Chrome CDP + 抖音原子操作（18个）+ 蓝图引擎 | ✅ 已完成 |
| B | Camoufox 集成 + 多浏览器内核 | 🔄 进行中 |
| C | 鼠标轨迹仿真 + 语料库完善 | 📋 规划中 |
| D | 小红书/知乎完整支持 | 📋 规划中 |

---

## 注意事项

- `local.yaml` 每台机器独立配置，**不纳入坚果云同步**（加入排除列表）
- `profiles/` 目录含 Chrome 用户数据（~100MB），存于 `agent-local/` 本地
- `config/accounts.yaml` 含账号标识信息，存于 `agent-local/` 本地
- 换机后 profiles 需重新登录各平台账号
- Camoufox 需单独安装（见 docs/CAMOUFOX_LOGIN_MANAGEMENT.md）
- 多机同步只需每台机器运行一次 `install.sh`
- 避免使用软链接指向 agent-local，统一通过 `local_paths.py` 管理路径

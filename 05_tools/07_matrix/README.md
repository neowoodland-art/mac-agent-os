# Matrix 矩阵养号系统

> **版本**: v4.2 | **环境**: macOS (Apple Silicon) | **引擎**: Camoufox (Firefox 内核) + Chrome CDP
> **平台**: 抖音 ✅ | 小红书 ✅ | 知乎 🔄
> **最后更新**: 2026-05-30

---

## 一句话

Matrix 是一套[四层架构](./ARCHITECTURE.md)的社交账号养号自动化系统。通过程序化控制浏览器（Camoufox/Chrome CDP），自动完成日常养号任务（浏览、点赞、评论、搜索），模拟真实用户行为。

代码在 `agent-sync`（Gitee 同步），数据在 `agent-local`（本机，不同步）。

---

## 快速上手

```bash
# 1. 新机部署（见 docs/SETUP_ON_NEW_MACHINE.md）
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix
bash install.sh

# 2. 检查账号状态
cd scripts && python matrix.py status accounts

# 3. 运行养号主控（抖音→小红书 全流程）
bash ../nurture_master.sh

# 4. 或只跑某平台单账号
python matrix.py nurture run -a douyin_01 -r 10
python matrix.py nurture run -a xhs_02 -r 10
```

---

## 目录结构

```
~/workbuddy-agent-os/
├── agent-sync/05_tools/07_matrix/       ← Gitee 同步（代码）
│   ├── README.md                         ← 本文档
│   ├── ARCHITECTURE.md                   ← 四层架构说明
│   ├── TOOL.md                           ← 技术细节（双引擎、反检测）
│   ├── install.sh                        ← 新机一键部署
│   ├── config_template/accounts.yaml     ← 账号配置模板
│   ├── scripts/
│   │   ├── matrix.py                     ← 统一 CLI 入口（推荐）
│   │   ├── nurture_master.sh             ← 养号主控脚本（全流程）
│   │   ├── atom_ops.py                   ← 原子操作库
│   │   ├── douyin_ops.py                 ← 抖音操作集
│   │   ├── matrix_modules/               ← 子模块
│   │   │   └── utils/cookie_manager.py   ← Cookie 安全模块
│   │   └── ops/                          ← 平台操作（按平台拆分）
│   ├── blueprints/                       ← 任务蓝图
│   └── docs/                             ← 文档目录（25+文件）
│
└── agent-local/tools/matrix/            ← 本机数据（不参与同步）
    ├── config/accounts.yaml              ← 本机账号配置
    ├── identities/{name}/                ← 每账号浏览器指纹+登录态
    ├── accounts/{name}/                  ← 每账号素材/文案/发布记录
    └── backups/cookies/                  ← Cookie 自动备份
```

---

## 核心概念

### 统一 CLI：`matrix.py`

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts

# ── 账号管理 ──
python matrix.py account list               # 列出所有账号
python matrix.py account status [name]      # 登录状态
python matrix.py account login <name>       # 首次手动登录

# ── 养号执行 ──
python matrix.py nurture run -a <name> -r 10            # 单账号 10 轮
python matrix.py nurture run -a a -a b -r 10            # 多账号并发
python matrix.py nurture run -a <name> -r 10 --daemon   # daemon 保持
python matrix.py nurture run -a <name> -r 10 --no-daemon # 完成后关闭浏览器
python matrix.py config blueprint list       # 查看可用蓝图

# ── 状态监控 ──
python matrix.py status all                 # 全局状态
python matrix.py status browsers            # 浏览器运行状态
```

### 养号主控脚本：`nurture_master.sh`

全自动两阶段执行，适合定时任务：

```
Phase 0: Cookie 全量备份 → 存储到 backups/cookies/
Phase 1: 抖音 ×3 并行养号（--no-daemon）
Phase 2: 休息 30s
Phase 3: 小红书 ×3 并行养号
```

```bash
# 手动启动
bash /path/to/nurture_master.sh
```

日志位于 `/tmp/nurture_master/{douyin|xhs}_phase.log`，各账号日志在 `/tmp/matrix_nurture_{account}.log`。

### 账号配置

每账号信息在 `agent-local/tools/matrix/config/accounts.yaml` 中注册：

```yaml
accounts:
- id: douyin_01          # 账号名（CLI 参数用这个）
  platform: douyin       # 平台
  phone: '185xxxx8610'   # 手机号
  identity_dir: identities/douyin_01_camo  # 浏览器身份目录
  window: [702, 783]     # 窗口尺寸
  window_position: [0, 0] # 屏幕位置（多账号防重叠）
```

> ⚠️ **XHS 复用身份**：小红书账号与抖音账号共享 identity_dir（同浏览器指纹）。
> 例：`xhs_01` → `douyin_01_camo`。切换时要**保护对方 Cookie**——`cookie_manager.py` 自动处理。

---

## 评论自动化

### 双路径

| 路径 | 场景 | 触发 | 发送 | 验证 |
|------|------|------|------|------|
| **Path A**: 弹窗覆盖层 | 养号流程 | KeyX 打开评论面板 | Enter | 页面评论确认 |
| **Path B**: 全屏视频页 | 指定链接 | scrollIntoView + click | Enter | 页面评论确认 |

**输入一律使用**：`pbcopy` + `Meta+V`（Draft.js 编辑器唯一可靠方式）

```python
# 流程（状态机）
closed → panel_open (打开评论区)
       → input_focused (聚焦输入框: 坐标双击 / DOM / Playwright locator)
       → text_entered (pbcopy + Meta+V)
       → sent (Enter → 页面确认)
```

详细规格见 [docs/COMMENT_FLOW_SPEC.md](./docs/COMMENT_FLOW_SPEC.md)。

---

## Cookie 安全保护

**问题**：XHS 和抖音共享 identity_dir，清 XHS cookie 可能误删抖音 session。

**方案**：`CookieGuard(identity_name)` 提供三层保护：

```python
from matrix_modules.utils.cookie_manager import CookieGuard, backup_all_identities

# 全量备份（nurture_master.sh 自动执行）
backup_all_identities(platform='master', label='pre_start')

# 指定身份备份
guard = CookieGuard("douyin_01_camo")
guard.backup(platform="douyin")          # 备份抖音 cookie
guard.protect("douyin")                   # 保护抖音 session
guard.restore(platform="douyin")          # 恢复抖音 cookie
```

备份位置：`agent-local/tools/matrix/backups/cookies/`

---

## 双引擎架构

| 引擎 | 适用 | 反检测能力 | 窗口控制 |
|------|------|-----------|---------|
| **Camoufox** (推荐) | 所有账号 | Firefox 内核 + 指纹固化 | persist_context + window.open |
| **Chrome CDP** (旧) | 部分老账号 | UA + viewport + touchEmulation | --window-size 参数 |

Camoufox 使用 `config` 参数在启动前注入 DOM 属性：

```python
config={
    "window.innerWidth": 702, "window.innerHeight": 783,
    "screen.width": 702, "screen.height": 783,
}
```

详细技术说明见 [TOOL.md](./TOOL.md)。

---

## 平台支持

### 抖音 ✅
- 浏览视频流 + 滑视频（8~20s 随机间隔）
- 点赞/收藏/关注
- 评论（Path A）
- 搜索发现
- 三账号并行（Camoufox）

### 小红书 ✅
- 瀑布流浏览 + 点击笔记卡片
- 点赞 + 收藏
- 评论（已知问题：聚焦失败）
- 搜索
- QR 码拦截墙自动重试（三轮回退）
- AI-layout 布局自动检测（standard / ai-layout / unknown）

---

## 已知问题 & 应对

| 问题 | 触发条件 | 影响 | 应对 |
|------|---------|------|------|
| `.parentlock` 残留 | 养号异常退出 | Camoufox 启动失败 | `find ... -name ".parentlock" -delete` |
| XHS Page.reload 挂起 | 偶发 | 协程永久阻塞 | kill 重跑 |
| XHS QR 码墙 | 账号被标记 | 无法点击笔记 | 3 轮回退重试自动恢复 |
| 评论聚焦失败 | 坐标偏移/DOM变化 | 跳过评论 | 不影响浏览养号 |
| XHS 评论聚焦失败 | 所有方式 | 跳过评论 | 已知未修复问题 |
| Chrome 148 更新 | 浏览器升级 | set_viewport_size 失效 | 改用 set_viewport_size（新方案） |

---

## 日志与监控

| 日志 | 位置 | 内容 |
|------|------|------|
| 主控脚本 | `/tmp/nurture_master/` | 抖音/小红书阶段输出 |
| 各账号详细 | `/tmp/matrix_nurture_{account}.log` | 每轮详情、评论记录 |
| 运行时截图 | `agent-local/.../screenshots/` | 调试用截图 |
| 执行记录 | `agent-local/.../data/matrix.db` | SQLite 结构化记录 |

---

## 新机部署

详细步骤见 [docs/SETUP_ON_NEW_MACHINE.md](./docs/SETUP_ON_NEW_MACHINE.md)。

极简版：

```bash
# 1. 同步代码
cd ~/workbuddy-agent-os
git clone git@gitee.com:babycalf/mac-agent-os.git agent-sync

# 2. 部署
bash agent-sync/05_tools/07_matrix/install.sh

# 3. 配置账号
cp agent-sync/.../config_template/accounts.yaml \
   agent-local/tools/matrix/config/accounts.yaml
# 编辑 accounts.yaml，填入本机手机号、身份目录

# 4. 安装 Camoufox（仅首次）
pip install camoufox && python -m camoufox fetch

# 5. 首次登录各平台（需手动扫码/短信）
python matrix.py account login douyin_01
```

---

## 相关文档

| 文档 | 用途 |
|------|------|
| [SETUP_ON_NEW_MACHINE.md](./docs/SETUP_ON_NEW_MACHINE.md) | ⭐ 新机部署完整指南 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 四层架构、设计原则 |
| [TOOL.md](./TOOL.md) | 技术细节、双引擎、反检测、行为参数 |
| [ARCHITECTURE_FULL.md](./docs/ARCHITECTURE_FULL.md) | 完整架构文档 |
| [COMMENT_FLOW_SPEC.md](./docs/COMMENT_FLOW_SPEC.md) | 评论状态机规格 |
| [CAMOUFOX_LOGIN_MANAGEMENT.md](./docs/CAMOUFOX_LOGIN_MANAGEMENT.md) | Camoufox 登录管理 |

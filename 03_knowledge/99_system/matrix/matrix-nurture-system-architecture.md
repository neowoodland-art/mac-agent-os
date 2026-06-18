---

title: Matrix 养号系统架构与运维指南
tags: [matrix, nurture, architecture, operations, douyin, xhs]
created: 2026-05-29
updated: 2026-05-29
nature: method
collected: true
collected_date: 2026-06-09
---

## 系统概览

Matrix 养号系统是一套多平台浏览器自动化框架，支持抖音（Douyin）和小红书（XHS）的账号养号、浏览互动、评论等操作。

## 架构

```
统一入口 matrix.py (CLI)
├── 双引擎连接 cdp_connector.py
│   ├── Chrome CDP (UA + viewport + touchEmulation 三合一)
│   └── Camoufox 持久化 (config 注入, 反检测)
├── 养号控制 runner.py (nurture_loop / nurture_xhs_loop)
├── 操作层 ops/
│   ├── douyin/ (browse.py, interact.py)
│   └── xhs/ (browse.py, interact.py, selectors.py)
├── 行为模拟 nurture/behavior.py (13 项可配置参数)
├── 身份管理 identities/{name}/
│   ├── config.yaml (窗口位置、代理等)
│   ├── fingerprint.pkl (浏览器指纹)
│   └── user_data/ (浏览器 profile 数据)
└── 主控脚本 nurture_master.sh (Phase 1 抖音 → Phase 2 小红书)
```

## 核心概念

### 双引擎模式

| 引擎 | 适用场景 | 特点 |
|------|----------|------|
| Chrome CDP | 需要高性能/稳定连接 | UA+viewport+touchEmulation 三合一注入 |
| Camoufox | 需要强反检测 | 持久化 profile, config 注入, 指纹隔离 |

### 统一 CLI

```bash
matrix {account|nurture|config|status} {action} {params}
```

### 账号共享身份

XHS 和抖音可共享同一 identity_dir（如 `douyin_01_camo` 同时用于 `xhs_01`），实现指纹统一。但需注意 **profile 互斥**：同一时刻只能有一个浏览器实例使用同一 profile。

## 养号流程

### 抖音养号轮次

```
首页 → 点击推荐卡片 → 看视频(随机时长) → 点赞/收藏(5中1) → 搜索框搜索 → 返回首页 → 循环
```

### 小红书养号轮次

```
首页(瀑布流)
→ Step 0: click_refresh_button()         ← 必执行，预防黑屏/卡死
→ Step 1: scroll_feed_human(1-3屏)        ← 拟人化滚动
→ Step 2: click_note_card(max_retries=3)  ← 含误触作者→新标签页检测+重试
→ Step 3: browse_note_detail(4-12s)       ← 图文/视频自适应
→ Step 4: random_interact()               ← 点赞/收藏/关注随机触发
→ Step 5: comment(每3轮1次)               ← pbcopy+Meta+V+Enter
→ Step 6: QR墙检测 + 返回首页              ← click_qr_wall_back_button优先
→ Step 7: 搜索发现(每2轮1次) → 返回后刷新  ← 搜索返回后加click_refresh_button
→ 循环
```

所有 `page.evaluate()` 调用均有 `asyncio.wait_for` 超时保护（8-10s），防止卡死。

## 后台运行

```bash
nohup matrix nurture run --account <name> --rounds 10 > /tmp/nurture_<acct>.log 2>&1 &
```

- 独立日志：`/tmp/nurture_<acct>.log`
- 全局日志：`/tmp/nurture.log`
- **Python stdout 缓冲问题**：后台进程日志可能延迟写入，需检查账号级日志

## 浏览器生命周期管理

### daemon 模式（重要）

- `--daemon`：养号结束后浏览器保持运行（便于调试）
- `--no-daemon`：养号结束后正常关闭浏览器释放资源
- **跨 Phase 场景**：Phase 1 抖音结束必须用 `--no-daemon` 关闭浏览器，否则 Phase 2 小红书复用同 profile 会 TargetClosedError
- `argparse.BooleanOptionalAction` 实现 `--daemon` / `--no-daemon` 双向开关

### Profile 冲突排查

**现象**：`TargetClosedError` 或页面无法操作
**根因**：两个浏览器实例争用同一 profile 目录（`.parentlock` 锁文件）
**解决**：确保前一个实例完全关闭（`conn.close()`），必要时清理 `.parentlock`

### conn.close() 实现

调用 `_camoufox_browser.close()` + `_playwright.stop()`，完整释放所有资源。

## Cookie 管理（CookieGuard）

- **模块**：`utils/cookie_manager.py` 中的 `CookieGuard(identity_name)`
- **规则**：共享 identity_dir 不能用裸 `sqlite3 DELETE`，必须用 `delete_platform_cookies_safe()` 自动备份对方平台 cookie
- **备份位置**：`backups/cookies/{identity_dir_name}/`
- **自动集成**：runner.py + matrix.py + nurture_master.sh

## 行为模拟参数（behavior.py）

13 项可配置参数控制养号行为的人性化程度：
- 点击延迟、滑动速度、浏览时长、互动概率、轮间休息等

## 账号管理

- **identities 目录**：每个身份独立文件夹（config.yaml + fingerprint.pkl + user_data/）
- **accounts.yaml**：集中管理所有账号配置（窗口位置、identity_dir 映射等）
- **窗口位置**：从 accounts.yaml 读取，运行结束不回写
- **identity_dir**：必须从 accounts.yaml 读取，不能仅用 identity_name 构造路径

## known-pitfalls

### Camoufox
- 启动失败 → 清理 `.user_data` 锁文件（`.parentlock`）
- 指纹分辨率影响 XHS 布局版本（见 AI-layout 兼容知识卡）

### Chrome
- Chrome 148+ → `Emulation.setDeviceMetricsOverride` 失效，改用 `set_viewport_size`
- macOS 窗口激活需用 AppleScript（系统限制）

### macOS 26.4
- 系统升级后 .so 文件因 Team ID 不匹配无法加载 → ad-hoc 重新签名
- 脚本：`codesign --force --sign - <file>`

### Python 后台进程
- stdout 默认缓冲导致日志延迟/丢失 → 检查账号级日志文件
- `PYTHONUNBUFFERED=1` 可强制无缓冲

## 全模拟运营架构

```
Layer 4: 管理层     排期/调度/KPI（规划中）
Layer 3: 流水线层   内容/电商/直播流水线
Layer 2: 操作层     原子操作（发布/评论/互动）
Layer 1: 数据层     每账号工作区（素材/脚本/发布记录/cookie备份）
```

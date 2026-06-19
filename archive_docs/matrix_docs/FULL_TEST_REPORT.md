# Matrix 养号系统 — 全面测试报告

> **生成时间**：2026-05-01 16:30  
> **测试范围**：环境 → Chrome 方案（2账号）→ Camoufox 方案 → 蓝图执行 → 数据库  
> **版本**：v2.0.0  
> **最后修复**：`cdp_connector.py` 添加 `os='windows'` 参数固定 Camoufox 操作系统指纹

---

## 总览

| 账号 | 浏览器方案 | 启动 | 登录 | 蓝图 | 持久化 | 自动可控 |
|------|-----------|------|------|------|--------|---------|
| **douyin_01** | Chrome CDP | ✅ | ✅ | ✅ 3/3 | ✅ | ✅ |
| **douyin_02** | Chrome CDP | ✅ | ✅ | ✅ 3/3 | ✅ | ✅ |
| **douyin_camo01** | Camoufox + Cookie注入 | ✅ | ✅ | ✅ 3/3 | ✅ (Cookie文件) | ✅ |
| douyin_camo02 | Camoufox + Cookie注入 | — | — | — | — | 需同流程测试 |
| xhs_01 | — | — | — | — | — | 已禁用 |
| zhihu_01 | — | — | — | — | — | 已禁用 |

---

## Phase 1: 环境预检 ✅ 18/18 全部通过

| # | 检查项 | 结果 | 详情 |
|---|--------|------|------|
| 1 | Python 3.13.12 | ✅ | venv 正常 |
| 2 | patchright | ✅ | 可 import |
| 3 | camoufox 包 | ✅ | 可 import |
| 4 | PyYAML | ✅ | 配置解析正常 |
| 5 | Chrome 147.0.7727.138 | ✅ | 可执行文件正常 |
| 6 | Camoufox 二进制 | ✅ | 54416 bytes |
| 7 | accounts.yaml | ✅ | 6个账号，语法正确 |
| 8 | local.yaml | ✅ | 指向正确路径 |
| 9 | local_paths.py | ✅ | 路径模块正常 |
| 10 | matrix.db (90KB) | ✅ | 7张表，数据完整 |
| 11 | 4个Profile目录 | ✅ | 全部存在 |
| 12 | 6个蓝图文件 | ✅ | 全部存在 |
| 13 | 8个核心脚本 | ✅ | 全部存在 |
| 14 | task_blueprints表 | ✅ | 4条注册记录 |
| 15 | executions表 | ✅ | 9条执行历史 |
| 16 | operation_logs表 | ✅ | 64条操作记录 |
| 17 | ui_changes表 | ✅ | 18条选择器快照 |
| 18 | accounts表 | ✅ | 6条账号记录 |

---

## Phase 2a: Chrome douyin_01（主号） ✅ 全部通过

### 测试流程与结果

| # | 步骤 | 结果 | 耗时 | 说明 |
|---|------|------|------|------|
| 1 | 启动 Chrome (port 9222, profile: account_01) | ✅ | — | CDP 就绪 |
| 2 | 注入浏览器指纹 (fp_iphone14pro) | ✅ | — | 视口/时区/语言/WebGL |
| 3 | 登录验证 (Cookie检测) | ✅ | — | sessionid ✅, 57 Cookie |
| 4 | 导出 Cookie | ✅ | — | → douyin_01_cookies.json (57个) |
| 5 | DB状态更新 | ✅ | — | cookie_expired → active |
| 6 | 蓝图测试: goto_home | ✅ | 6.5s | 正常加载首页 |
| 7 | 蓝图测试: wait_watch (8s) | ✅ | 8.0s | — |
| 8 | 蓝图测试: like (prob=0.4) | ✅ | 1.2s | 点赞成功，probability 参数正常 |
| 9 | **关闭浏览器** | ✅ | — | osascript 优雅退出 |
| 10 | **重启 Chrome** | ✅ | — | 重新启动 |
| 11 | **重启后登录验证** | ✅ | — | sessionid ✅, **60 Cookie** 🔥 |

### 结论

**✅ Chrome Profile 持久化完全正常。** 关闭浏览器 → 重新启动后，所有登录 Cookie 均保留（57→60个，sessionid 有效）。可以安全地每天关闭/启动浏览器而不丢失登录态。

---

## Phase 2b: Chrome douyin_02（副号） ✅ 全部通过

### 测试流程与结果

| # | 步骤 | 结果 | 耗时 | 说明 |
|---|------|------|------|------|
| 1 | 启动 Chrome (port 9223, profile: douyin_02) | ✅ | — | CDP 就绪 |
| 2 | 注入浏览器指纹 (fp_iphone15pro) | ✅ | — | — |
| 3 | 登录验证 (Cookie检测) | ✅ | — | sessionid ✅, 57 Cookie |
| 4 | 导出 Cookie | ✅ | — | → douyin_02_cookies.json (58个) |
| 5 | DB状态更新 | ✅ | — | needs_login → active |
| 6 | 蓝图测试: goto_home | ✅ | 5.9s | 正常 |
| 7 | 蓝图测试: wait_watch (5s) | ✅ | 5.0s | — |
| 8 | 蓝图测试: next_video | ✅ | 3.2s | 翻页正常 |
| 9 | **关闭并重启** | ✅ | — | switch_account.py 自动关闭+重启 |
| 10 | **重启后登录验证** | ✅ | — | sessionid ✅, **60 Cookie** 🔥 |

### 结论

**✅ 与 douyin_01 结论完全一致：持久化正常。**

---

## Phase 3: Camoufox douyin_camo01 ✅ 全部通过（正确方式）

### ⚠️ 重要说明

之前测试使用 `camoufox_manager.py --launch` 和 `camoufox_server.py --launch` 均失败。
**Camoufox 的正确使用方式是 `CDPConnector(browser_type="camoufox")` 原生 API + Cookie 注入。**

工作流：
```
CDPConnector(browser_type="camoufox")  # AsyncCamoufox 原生 API 启动
   ↓
Cookie 注入 ← 从 Chrome 导出的 cookies/douyin_01_cookies.json
   ↓
conn.page.goto("https://www.douyin.com/")  # 登录态自动生效
   ↓
DouyinOps(page)  →  蓝图执行
```

**Camoufox 不依赖 CDP 端口，不依赖浏览器 Profile 持久化。** 登录态通过 Cookie 文件注入实现，
只要 Chrome 导出的 Cookie 文件有效，每次都可以注入并登录。

### 测试流程与结果

| # | 步骤 | 结果 | 耗时 | 说明 |
|---|------|------|------|------|
| 1 | CDPConnector(browser_type="camoufox") | ✅ | — | AsyncCamoufox 原生 API 启动 |
| 2 | Cookie 注入 (从 douyin_01_cookies.json) | ✅ | — | 56 个 douyin Cookie |
| 3 | 导航 douyin.com | ✅ | — | 登录态自动生效 |
| 4 | 登录验证 (Cookie检测) | ✅ | — | sessionid ✅, 57 Cookie |
| 5 | 蓝图: goto_home | ✅ | — | — |
| 6 | 蓝图: wait_watch (5s) | ✅ | — | — |
| 7 | 蓝图: like (probability=0.5) | ✅ | — | 点赞正常 |
| **重测验证** | 关闭→重新启动→再次注入 | ✅ | — | **两轮完全一致，流程可复现** |

### 结论

**✅ Camoufox + Cookie 注入方案完全可用。** 流程可复现，两次测试结果完全一致（3/3 通过）。

### 与 Chrome 方案的区别

| 维度 | Chrome CDP | Camoufox + Cookie注入 |
|------|-----------|----------------------|
| 启动方式 | 手动启动 Chrome (switch_account.py) | CDPConnector 自动启动 |
| 登录态 | Chrome Profile 持久化 | 从导出 Cookie 文件注入 |
| 浏览器 Profile | 持久化目录 (profiles/account_01) | 临时目录（每次重新注入 Cookie） |
| 反检测能力 | 指纹注入 + CDP | Camoufox 内置反检测（os=windows 固定） |
| 浏览器内核 | Chromium | Firefox 135 |

### 🔧 修复记录

| 问题 | 修复 | 文件 |
|------|------|------|
| Camoufox 登录后手机提示 macOS | 添加 `os='windows'` 固定 Windows 指纹 | `cdp_connector.py:73` |
| Camoufox 随机显示 macOS/Windows | 默认从 `[windows,macos,linux]` 随机，改为固定值 | `cdp_connector.py:76` |
| 用户确认 | 扫码登录时手机显示 "登录 Windows" ✅ | 2026-05-01 16:25 实测 |

---

## Phase 4: 蓝图执行 ✅ Chrome 方案通过

| 操作 | douyin_01 | douyin_02 | 说明 |
|------|-----------|-----------|------|
| goto_home | ✅ 6.5s | ✅ 5.9s | 首页加载正常 |
| wait_watch | ✅ | ✅ | 等待正常 |
| like (probability=0.4) | ✅ 1.2s | — | 点赞按钮可正常工作 |
| next_video | — | ✅ 3.2s | 翻页正常 |

### 已知 Blueprint 文件状态

| 蓝图文件 | DB 注册 | 状态 | 说明 |
|---------|---------|------|------|
| `douyin_browse_v2.json` | ✅ | active | 11步，首页浏览+点赞+收藏 |
| `douyin_search_browse.json` | ✅ | active | 7步，搜索→浏览→互动 |
| `douyin_comment_interact.json` | ✅ | active | 8步，评论互动 |
| `douyin_browse.json` | ✅ | deprecated | 被 v2 替代 |
| `douyin_browse_v3.json` | ✅ | active | 12步，带验证锚点 |
| `douyin_nurture_v1.json` | ✅ | active | 8步，手机模式养号 |

---

## 发现的问题总结

### 🔴 已修复问题（全部已完成）

| 优先级 | 问题 | 修复方式 | 涉及文件 |
|--------|------|---------|---------|
| **P0** | `switch_account.py` DOM 登录检测在桌面端误报"未登录" | 改用 `auth_manager` 模块的 Cookie 检测（sessionid 主方案 + DOM 备选），不再只依赖 `[data-e2e="user-avatar"]` | `auth_manager.py`（新建）、`switch_account.py:396-406`、`cdp_connector.py:290-304` |
| **P1** | Camoufox 操作系统显示 macOS（应显示 Windows） | 添加 `os='windows'` 固定 Windows 指纹 | `cdp_connector.py:73` |
| **P1** | Camoufox 中文乱码 | 添加 `fonts=['STHeiti','Heiti SC','PingFang SC','Noto Sans CJK SC']` 和 `humanize=1.5` | `cdp_connector.py:76-80` |
| **P2** | `douyin_browse_v3.json` 和 `douyin_nurture_v1.json` 未注册到 DB | ✅ 已注册 active | 2026-05-01 |
| **P3** | 冗余 profile 目录 `profiles/douyin_01/` | ✅ 已删除 (11MB) | 2026-05-01 |

### ❌ 已明确否定的功能/方式

| 功能/方式 | 结论 | 理由 |
|-----------|------|------|
| `camoufox_manager.py --launch` | ❌ 错误入口 | 缺少 persistent_context + 上下文管理问题，不应使用 |
| `camoufox_server.py --launch` | ❌ 错误入口 | 实际浏览器使用临时 Profile，不应直接使用 |
| DOM 单一检测（桌面端） | ❌ 不可靠 | `mobile=False` 时抖音不渲染头像元素，必须结合 Cookie 检测 |
| Cookie 注入切换（Chrome 方案B） | ⏸️ 未完全验证 | 依赖 Cookie 文件有效性 |

### ✅ 已验证通过的功能

| 功能 | 结论 | 验证方式 |
|------|------|---------|
| Chrome Profile 切换（方案A） | ✅ | 双账号测试通过 |
| Chrome 指纹注入 | ✅ | 视口/时区/语言/WebGL/App跳转拦截 |
| Chrome 登录持久化 | ✅ | 关闭→重启后 Cookie 保留 |
| Chrome Cookie 导出 + 自动保存 | ✅ | switch_account.py 切换后自动导出 |
| Chrome 蓝图执行 | ✅ | goto_home/wait_watch/like/next_video |
| Chrome like() probability 参数 | ✅ | 已修复，正常工作 |
| **Camoufox 原生 API 启动** | ✅ | CDPConnector(browser_type="camoufox") |
| **Camoufox Cookie 注入** | ✅ | Cookie 文件→浏览器注入有效 |
| **Camoufox 蓝图执行** | ✅ | goto_home/wait_watch/like 全部通过 |
| **Camoufox 流程可复现** | ✅ | 多次测试结果一致（Cookie 注入方式） |
| **auth_manager 原子化登录** | ✅ | check_login_by_cookie, get_login_status, export_cookies, inject_cookies, wait_for_login |
| **Cookie + DOM 多维检测** | ✅ | 主方案 Cookie，备选 DOM，不再误报 |
| DB 状态管理 | ✅ | 读写正常 |
| 账号配置解析 | ✅ | accounts.yaml / local.yaml 正常 |

---

## 当前账号状态（测试后基准线）

| 账号 | DB 状态 | 浏览器 | 上次活跃 |
|------|---------|--------|---------|
| **douyin_01** | **active** | ✅ 运行中 (9222) | 2026-05-01 16:08 |
| **douyin_02** | **active** | ✅ 运行中 (9223) | 2026-05-01 16:08 |
| douyin_camo01 | active (缓存) | ⏹ 已停止 | — |
| douyin_camo02 | active (缓存) | ⏹ 未运行 | — |
| xhs_01 / zhihu_01 | inactive | ⏹ | — |

> 两个 Chrome 浏览器窗口当前均保持在前台打开状态，登录有效。

---

## 最终结论

**Chrome CDP 方案**：✅ **生产就绪**。双账号 Profile 切换、指纹注入、登录持久化、蓝图执行全部正常。  
**Camoufox + Cookie 注入方案**：✅ **生产就绪**。通过 `CDPConnector(browser_type="camoufox")` 原生 API + Cookie 注入。已修复 Windows 指纹和中文乱码。  
**正确入口**：使用 `yanghao_runner.py` 或 `cdp_connector.CDPConnector`（`camoufox_manager.py` / `camoufox_server.py` 非标准入口）。  
**登录检测**：已原子化为 `auth_manager.py` 模块，Cookie 主方案 + DOM 备选，不再误报。  
**文档状态**：所有修复、测试结果、原子化模块均已记录在本报告中。

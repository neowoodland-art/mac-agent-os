# Matrix 养号系统 — 系统架构设计

> **版本**：v2.1.0  
> **最后更新**：2026-05-01  
> **设计原则**：原子化可复用 → 固化不反复 → 全链路串接

---

## 1. 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    用户触发（对话/定时）                      │
└─────────────────┬───────────────────────────┬───────────────┘
                  │                           │
          ┌───────▼───────┐         ┌─────────▼────────┐
          │  yanghao_runner.py  │     │ task_scheduler.py │
          │  （手动/交互入口）   │     │  （定时任务入口）   │
          └───────┬───────┘         └─────────┬────────┘
                  │                           │
                  └──────────┬────────────────┘
                             │
                    ┌────────▼────────┐
                    │  CDPConnector   │
                    │  (浏览器连接层)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
      ┌───────▼──────┐ ┌────▼────┐ ┌───────▼──────┐
      │ Chrome CDP    │ │Camoufox │ │ auth_manager │
      │ (端口 9222+)  │ │原生 API  │ │ (登录管理)    │
      └───────┬──────┘ └────┬────┘ └───────┬──────┘
              │              │              │
              └──────┬───────┘              │
                     │                      │
              ┌──────▼──────┐     ┌─────────▼────────┐
              │  DouyinOps  │     │  Cookie 文件     │
              │ (原子操作库) │     │ (持久化存储)      │
              └──────┬──────┘     └─────────────────┘
                     │
              ┌──────▼──────┐
              │  蓝图引擎    │
              │ task_engine  │
              └─────────────┘
```

---

## 2. 原子化模块清单

| 模块 | 文件 | 职责 | 依赖 |
|------|------|------|------|
| **auth_manager** | `scripts/auth_manager.py` | 登录检测、Cookie 导出/注入、等待登录 | 无（纯函数 + Playwright API） |
| **cdp_connector** | `scripts/cdp_connector.py` | 浏览器连接（Chrome CDP / Camoufox 原生） | auth_manager（登录检测） |
| **douyin_ops** | `scripts/douyin_ops.py` | 抖音原子操作（18个：like/collect/comment/scroll等） | Playwright Page |
| **local_paths** | `scripts/local_paths.py` | 统一路径管理 | 无 |
| **page_state** | `scripts/page_state.py` | 页面模式检测、状态建议 | Playwright Page |
| **task_engine** | `scripts/task_engine.py` | 蓝图加载与逐步执行 | douyin_ops |
| **yanghao_runner** | `scripts/yanghao_runner.py` | 完整养号流程入口（交互/参数双模式） | cdp_connector + douyin_ops |
| **switch_account** | `scripts/switch_account.py` | 账号切换、状态查看 | auth_manager |
| **full_test** | `scripts/full_test.py` | 全面测试 + 报告生成 | task_engine + auth_manager |

---

## 3. 登录管理（auth_manager 原子操作）

### 3.1 检测流程

```
get_login_status(context, page)
    │
    ├── Cookie 检测（主方案）
    │    ├── 遍历所有 Cookie
    │    ├── 检查 sessionid / sid_guard 是否存在
    │    └── 返回 cookie_ok + cookie_count + session_id
    │
    └── DOM 检测（备选，仅移动端视口有效）
         ├── 检查 [data-e2e='user-avatar']
         ├── 检查 [data-e2e='user-detail']
         └── 返回 dom_ok
    
    └── 综合判断
         ├── cookie_ok + dom_ok → logged_in=True, method="both"
         ├── cookie_ok only     → logged_in=True, method="cookie"
         ├── dom_ok only        → logged_in=True, method="dom"
         └── 均无               → logged_in=False
```

### 3.2 可用 API

| 函数 | 用途 | 返回 |
|------|------|------|
| `check_login_by_cookie(context)` | Cookie 检测 | bool |
| `check_login_by_dom(page, platform)` | DOM 检测 | bool |
| `get_login_status(context, page)` | 多维综合检测 | dict |
| `export_cookies(context, path)` | 导出 Cookie | int(数量) |
| `inject_cookies(context, path)` | 注入 Cookie | int(数量) |
| `wait_for_login(context, page)` | 等待手动登录 | dict |
| `get_session_id(cookies)` | 提取 sessionid | str/None |

### 3.3 持久化策略

```
Chrome 方案：Profile 目录持久化（浏览器关闭重启后 Cookie 自动保留）
    ↓
首次切换/登录后 → auth_manager.export_cookies() → data/cookies/{id}_cookies.json
    ↓
Camoufox 启动时 → auth_manager.inject_cookies() → 从 Cookie 文件恢复登录
```

---

## 4. 浏览器方案对比

| 维度 | Chrome CDP | Camoufox (Firefox) |
|------|-----------|-------------------|
| 启动入口 | `switch_account.py --method profile` | `CDPConnector(browser_type="camoufox")` |
| 登录方式 | Chrome Profile 持久化（自动） | Cookie 注入（从文件） |
| 登录检测 | auth_manager Cookie 检测 | auth_manager Cookie 检测 |
| 操作系统指纹 | 实际 macOS（CDP 覆盖 UA） | 固定 Windows（`os='windows'`） |
| 中文字体 | 系统自带 | 需指定 fonts 参数 |
| 反检测 | CDP 指纹注入 + JS 注入 | Camoufox 内置 + humanize |
| 适用场景 | 主力养号（doyin_01/02） | 辅助养号（douyin_camo01/02） |

---

## 5. 蓝图执行链路

```
yanghao_runner.py / task_engine.py
    │
    ├── 1. CDPConnector.connect()        → 启动/连接浏览器
    ├── 2. conn.init_anti_detection()    → 指纹注入
    ├── 3. auth_manager.get_login_status() → 验证登录
    ├── 4. 加载 blueprint JSON            → 读取步骤
    ├── 5. DouyinOps(page)               → 绑定操作对象
    ├── 6. 逐步骤执行:
    │       ├── goto_home()
    │       ├── wait_watch(seconds)
    │       ├── like(probability)
    │       ├── collect(probability)
    │       ├── next_video()
    │       ├── search(keyword)
    │       ├── post_comment(text)
    │       └── ...
    └── 7. 记录执行结果 → matrix.db
```

---

## 6. 已知问题跟踪

| ID | 状态 | 问题 | 涉及文件 | 修复日期 |
|----|------|------|---------|---------|
| P0 | ✅ 已修复 | DOM 登录检测桌面端误报 | auth_manager.py + switch_account.py | 2026-05-01 |
| P1 | ✅ 已修复 | Camoufox 显示 macOS | cdp_connector.py | 2026-05-01 |
| P1 | ✅ 已修复 | Camoufox 中文乱码 | cdp_connector.py | 2026-05-01 |
| P2 | ✅ 已修复 | douyin_browse_v3/nurture_v1 未注册 DB | DB task_blueprints | 2026-05-01 |
| P3 | ✅ 已修复 | 冗余 profiles/douyin_01 目录（11MB） | 文件系统 | 2026-05-01 |

---

## 7. 快速操作指南

```bash
TOOL=~/workbuddy-agent-os/agent-sync/05_tools/07_matrix

# 查看账号状态
python $TOOL/scripts/switch_account.py --status
python $TOOL/scripts/auth_manager.py 9222    # 独立登录检测

# 启动 Chrome + 切换账号 + 自动导出 Cookie
python $TOOL/scripts/switch_account.py --method profile --target douyin_01 --port 9222

# 启动 Camoufox + Cookie 注入 + 执行蓝图（正确方式）
python $TOOL/scripts/yanghao_runner.py --account douyin_camo01 --blueprint douyin_browse_v2 --browser camoufox

# 完整测试
python $TOOL/scripts/full_test.py --account-only douyin_01
```

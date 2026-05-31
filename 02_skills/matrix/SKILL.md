---
name: matrix
version: 1.0.0
description: 多平台社交账号矩阵养号——蓝图调度、账号切换、任务状态查询、蓝图管理
triggers:
  - 矩阵
  - 养号
  - 抖音养号
  - 执行蓝图
  - 切换账号
  - 账号状态
  - matrix
  - 查看蓝图
  - 添加蓝图
  - 任务调度
---

# Matrix 矩阵养号技能

## 概述

通过 Chrome CDP 和 Camoufox（Firefox 内核）控制浏览器，自动执行多平台社交账号日常养号任务。  
支持抖音（已完成）、小红书/知乎（框架就绪，待登录账号）。

**工具位置**: `~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/`  
**本地数据**: `~/workbuddy-agent-os/agent-local/tools/matrix/`

---

## 触发词与对应动作

| 触发词 | 动作 |
|--------|------|
| `账号状态` / `查看账号` | 列出所有账号及登录状态 |
| `执行蓝图 <蓝图名> <账号>` | 执行指定蓝图 |
| `查看蓝图` | 列出所有可用蓝图及说明 |
| `切换账号 <账号ID>` | 切换 Chrome Profile 到指定账号 |
| `启动调度` | 启动定时任务调度器 |
| `任务状态` | 查看最近任务执行记录 |
| `matrix 安装` | 在新机运行 install.sh |

---

## 核心能力

### 1. 账号管理
- 多账号隔离（每个账号独立 Chrome Profile）
- 账号状态查询（登录态检查，Cookie 主方案 + DOM 备选）
- 登录检测原子化模块：`auth_manager.py`
  - `check_login_by_cookie()` — Cookie 检测（主方案，不依赖 UI）
  - `check_login_by_dom()` — DOM 检测（备选，需移动端视口）
  - `get_login_status()` — 多维综合检测
  - `export_cookies()` / `inject_cookies()` — Cookie 导出/注入
  - `wait_for_login()` — 等待用户手动登录（轮询）
- 双方案切换：Profile 切换（稳定）/ Cookie 注入（实验性）
- **`switch_account.py` 切换后自动导出 Cookie 到 `data/cookies/{id}_cookies.json`**

### 2. 蓝图执行

| 蓝图 | 说明 | 步骤数 | 状态 |
|------|------|--------|------|
| `douyin_browse_v2` | 推荐页浏览 + 随机点赞/收藏 | 11步 | ✅ 活跃 |
| `douyin_search_browse` | 搜索关键词 → 浏览结果 → 点赞 | 7步 | ✅ 活跃 |
| `douyin_comment_interact` | 浏览推荐 → 打开评论区 → 发评论 | 8步 | ✅ 活跃 |

### 3. 原子操作库（抖音，18个）
`goto_home` / `wait_watch` / `like` / `collect` / `follow` / `comment` /  
`search` / `open_comments` / `close_comments` / `scroll_feed` 等

### 4. 定时调度
通过 `task_scheduler.py` 设定各账号的执行频率，后台持续运行。

---

## 常用命令

```bash
TOOL=~/workbuddy-agent-os/agent-sync/05_tools/07_matrix

# 查看所有账号
python $TOOL/scripts/switch_account.py --list

# 查看当前活跃账号（含 Cookie 检测）
python $TOOL/scripts/switch_account.py --status

# 切换到指定账号（Profile 方式）+ 自动导出 Cookie
python $TOOL/scripts/switch_account.py --method profile --target douyin_01 --port 9222

# 独立登录检测（auth_manager 原子化模块）
python $TOOL/scripts/auth_manager.py 9222        # 检测端口 9222 的登录状态
python $TOOL/scripts/auth_manager.py 9223        # 检测端口 9223

# 启动 Camoufox + Cookie 注入（正确方式）
python $TOOL/scripts/yanghao_runner.py --account douyin_camo01 --blueprint douyin_browse_v2 --browser camoufox

# 执行蓝图
python $TOOL/scripts/task_engine.py --blueprint douyin_browse_v2 --account douyin_01

# 后台定时调度
python $TOOL/scripts/task_scheduler.py

# 手动启动 Chrome
bash $TOOL/scripts/launch_chrome.sh douyin_01 9222
```

---

## 执行流程

```
用户触发（对话 or 定时）
    ↓
task_scheduler.py（定时调度）
    ↓
switch_account.py（切换 Chrome Profile / Cookie 注入）
    ↓
task_engine.py（加载蓝图 JSON → 逐步执行）
    ↓
douyin_ops.py（原子操作：点赞/评论/浏览...）
    ↓
cdp_connector.py / camoufox_manager.py（浏览器 CDP 控制）
    ↓
写入 data/matrix.db（任务记录）+ logs/（执行日志）
```

---

## 账号配置文件

位置：`~/workbuddy-agent-os/agent-local/tools/matrix/config/accounts.yaml`

```yaml
accounts:
  - id: douyin_01
    platform: douyin
    browser: chrome
    profile_dir: douyin_01   # 对应 profiles/ 下的目录名
    status: active
```

---

## 蓝图文件格式（供新增参考）

位置：`~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/blueprints/`

```json
{
  "name": "蓝图唯一ID",
  "description": "蓝图说明",
  "platform": "douyin",
  "steps": [
    {"step": 1, "op": "goto_home", "args": {}},
    {"step": 2, "op": "wait_watch", "args": {"seconds": 8}},
    {"step": 3, "op": "like", "args": {"probability": 0.3}}
  ]
}
```

---

## 标准化文档

| 文档 | 用途 |
|------|------|
| `docs/SYSTEM_ARCHITECTURE.md` | **系统架构设计** — 模块关系、链路、原子操作清单（必读） |
| `docs/ACCOUNT_LOGIN_SOP.md` | **账号登录 SOP** — 标准化操作流程 |
| `docs/FULL_TEST_REPORT.md` | **全面测试报告** — ✅/❌ 全部标注，含时间戳 |

**所有操作请先查阅架构文档和 SOP，按标准步骤执行，不得临时改代码。**

---

## 开发状态

| 阶段 | 内容 | 状态 |
|------|------|------|
| A | Chrome CDP + 抖音原子操作（18个）+ 蓝图引擎 + 定时调度 | ✅ 已完成 |
| B | Camoufox（Firefox内核）集成 + 多浏览器内核 | ✅ 已完成（2026-04-30） |
| C | 鼠标轨迹仿真 + 语料库完善 + Canvas/AudioContext 指纹噪声 | 📋 规划中 |
| D | 小红书/知乎完整支持 + 多平台联动 | 📋 规划中 |

### 阶段B完成说明
- Camoufox 通过 `camoufox.async_api.AsyncCamoufox` 原生 API 启动（`CDPConnector(browser_type="camoufox")`）
- **重要**：Camoufox 不依赖 CDP 端口，通过 **Cookie 注入** 从 Chrome 导出的 Cookie 文件登录
- 标准入口：`yanghao_runner.py --account douyin_camo01 --blueprint douyin_browse_v2 --browser camoufox`
- **不要使用** `camoufox_manager.py --launch` 或 `camoufox_server.py --launch`（非标准入口）
- 登录态验证通过 Cookie 检测（sessionid），无需 DOM 头像元素
- Chrome 方案 + Camoufox 方案均已通过全量测试验证 ✅

---

## 多机同步

详见 `docs/SYNC_GUIDE.md` — 包含:

- 同步架构说明（什么是同步的 / 什么是每机独立的）
- 主电脑修改→提交→推送的标准流程
- 新机拉取→部署→登录的标准流程
- 本地依赖安装清单（Python 包 / Playwright / Camoufox）
- 版本对照表 + 快速检查清单

### 快速新机恢复

```bash
# 1. 拉取最新代码
cd ~/workbuddy-agent-os/agent-sync && git pull origin main

# 2. 一键安装（建立目录 + 依赖 + 配置）
bash ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/install.sh

# 3. 填写本机账号配置
vim ~/workbuddy-agent-os/agent-local/tools/matrix/config/accounts.yaml

# 4. 各账号重新扫码登录
python scripts/switch_account.py --method profile --target douyin_01 --port 9222
```

---

## 注意事项

- `profiles/` 含 Chrome 登录数据（~100MB），**换机后需重新登录**各平台
- `config/accounts.yaml` 含账号信息，**不随 agent-os 同步**，存于 agent-os-local
- Camoufox 阶段B尚未稳定，生产环境使用 Chrome CDP（阶段A）
- 反检测措施：指纹注入 + 随机延迟 + 蓝图随机化，勿过度调低延迟

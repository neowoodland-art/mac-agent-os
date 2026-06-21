# AgentOS 联邦系统 — 三台机器统一环境

## 机器对照表

| ORACLE 名 | Tailscale 名 | IP | SSH 用户 | Home 目录 |
|:----------|:-------------|:---|:---------|:----------|
| chengzigedeAir | macbook-air | 100.111.43.6 | chengzige | /Users/chengzige |
| 5kechengdeAir | 5macbook-air | 100.72.182.121 | 5kecheng | /Users/5kecheng |
| 7kecheng | 7macbook-air | 100.65.35.28 | 7kecheng | /Users/7kecheng |

## 统一后的 Python 环境

| 项目 | 三台机器一致 ✅ |
|:-----|:---------------|
| 养号用 venv | agent-os (旧名 matrix 已废弃) ✅ |
| Python 版本 | 3.13.12 ✅ |
| Python 签名 | adhoc（无 Team ID）✅ |
| orjson | 3.11.9 ✅ |
| camoufox | 0.4.11 ✅ |
| playwright | 1.58.0 ✅ |
| Git 版本 | 一致 ✅ |
| 蓝图文件 | 14 个（已同步）✅ |

## PYTHON 路径规范（重要）
所有涉及 PYTHON 路径的地方**必须使用 agent-os venv**，禁用了 matrix venv：
- `$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3`
- 旧路径 `envs/matrix/` 已全部替换
- 远程执行用 `$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3`
- remote_exec.py 使用 `$MC_PYTHON` 动态发现变量

## 登录系统关键发现
- 小红书登录弹窗: 无cookie自动弹出, DOM类名 `.login-container` / `.reds-modal-open`
- 手机号输入框: `input[placeholder="输入手机号"]`
- "继续"按钮: 手机号输入框右侧, 文字"继续", 无勾选协议
- 填手机号必须用 Playwright `page.fill()` 或 `page.type()` (+键盘事件), 不能用 JS set value (React不识别)
- 填完后按 Tab 键触发失焦, "继续"按钮才可点击
- 短信验证码: 通过 ApiSMSHandler 轮询 wx.tyhtak.com API
- 抖音登录已有完整 douyin_login.py (含sms_login原子操作)

## 小红书登录方案演进

### v1/v2 (已淘汰) — 鼠标点击协议复选框 ❌
- 找包含"同意"的最小高度可见元素 → `mouse.click(left - 20px, center_y)`
- 问题: 小红书复选框是自定义元素（非原生 `<input type="checkbox">`），left-20px 定位极不可靠
- 多次验证失败，元素位置随弹窗布局变化

### v3 (当前方案, 待验证) — 点"同意并登录"按钮 ✅
- 新发现: 点击「直接登录」按钮会弹出浮窗，浮窗上有「同意并登录」按钮
- 点击「同意并登录」= 协议勾选 + 登录意图一次性完成
- **不再需要**定位复选框或 left-20px hack
- 2026-06-16 晚发现该方案，尚未做 DOM 扫描验证

### 原子操作文件
- `matrix_modules/account/xhs_login.py` — 小红书原子操作（仿 sms_login.py 模式）
  - 状态检测: `has_login_panel()`, `has_sms_inputs()`, `is_logged_in()`
  - 操作函数: `fill_phone()`, `click_continue()`, `click_agree_and_login()`, `fill_6_digit_code()`, `click_largest_login_btn()`
  - 主流程: `xhs_login(page, phone, account_name, log_func, use_v3)`
- `matrix_modules/account/xiaohongshu_login.py` — 顶层入口（调用 xhs_login 原子操作）

## 路径变量
- AGENT_SYNC=$HOME/workbuddy-agent-os/agent-sync
- AGENT_LOCAL=$HOME/workbuddy-agent-os/agent-local

## 远程管理
本机 (chengzigedeAir) 可通过 SSH 控制所有机器:
```bash
ssh 5kecheng@100.72.182.121 "命令"
ssh 7kecheng@100.65.35.28 "命令"
# 或通过 mc CLI
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts
python3 -m mc remote exec 5kechengdeAir "命令" --via ssh
```

## 版本锁定
依赖版本已锁定在 `agent-sync/requirements.txt`
新机器部署后执行: `pip install -r requirements.txt`

## 代码签名修复
新机器必须执行: `codesign -f -s - $HOME/.workbuddy/binaries/python/versions/3.13.12/bin/python3`
deploy.sh 已自动检测此步骤。

## 部署文档
- `DEPLOY-GUIDE.md` v2.0: 完整部署指南
- `deploy.sh`: 一键部署脚本
- `fleet_sync.sh`: 多机同步
- `fleet_reconcile.sh`: 对账引擎

## 架构关键概念（已修正 v2）
- **身份模型**: 一个手机号=一个身份目录。这个身份下可以存多个平台账号(xhs+douyin), 跨平台只需改 URL, 不用重开浏览器
- **窗口排布**: 本机最多3个浏览器同时运行, 每个窗口 X坐标+150 重叠排布(cdp_connector window_position参数)
- **蓝图定义**: 蓝图是你和我交互的"命名模板+参数", 不是内部执行步骤链。如 daily(时长), comment(url+text)
- **原子操作**: 最小执行单元, 自带状态检测。执行中触发验证弹窗 → 自动组合其他原子操作(如SMS登录)恢复
- **状态机核心**: 每次操作前必检登录态 → 执行 → 后检查是否触发验证 → 验证则自动恢复 → 冷却 → 下一步

## Vite 前端重构 (已完成)
- `static/index.html` 7700行 → Vite + Vanilla JS 模块化架构 ✅
- 已迁移到按视图拆分文件，Vite HMR 热更新 ✅

## 五层执行架构 (L1-L5) — 2026-06-20
所有 Dashboard 操作的执行链路：
```
L5 Dashboard UI → L4 API路由 → L3 CommandBus → L2 mc引擎 → L1 浏览器
```

### 各层核心文件
| 层 | 位置 |
|:---|:-----|
| L5 | `frontend/src/views/matrix-*.js` |
| L4 | `routes/ops.py`, `routes/matrix.py` |
| L3 | `services/command_bus.py` |
| L2 | `scripts/mc/engine.py`, `scripts/mc/run.py` |
| L1 | `scripts/douyin_ops.py`, `scripts/xhs_ops.py` |

### 登录检测 (2026-06-20 重构 v2.0)
- **架构**: PlatformDetector(策略模式) + RecoveryChain(可配置) + LoginStateMachine(编排器)
- **检测**: DouyinDetector 四重检测 — DOM锚点 → 页面文本("未登录"/"粉丝+关注") → 标题 → Cookie(仅日志)
- **恢复链**: DouyinLoginRecovery(抖音专用) → CookieRecovery → SmsRecovery(小红书) → VisualRecovery
- **三种场景全通过**: 已登录 ✅ / 短期过期(一键+SMS) ✅ / 全新登录(手机+SMS) ✅
- **关键**: 登录按钮文字在短期过期时为"确认登录"，全新登录时为"登录"
- **参考**: `FEDERATION_GUIDE.md` 4.4 节 + 第十一章完整文档

## 原子操作体系 v2（2026-06-21 建立）

### 核心文档
| 文档 | 路径 | 内容 |
|:-----|:-----|:-----|
| 经验文档 | `.workbuddy/memory/EXPERIENCE-atomic-ops-20260621.md` | 完整时间线、设计原则、选择器优劣、快捷键表、代码状态 |
| 项目规划 | `.workbuddy/memory/PLAN-atomic-ops-v2.md` | 三层架构设计、增强录制、单步调试、看板集成 |
| 架构审计 | `.workbuddy/memory/ARCHITECTURE_AUDIT.md` | 新旧代码对比、根本问题分析、重构方案 |

### 关键技术突破
1. **状态检测模型**: L1页面类型 + L2鼠标区域 + L3元素详情 + L4视觉状态
2. **键盘快捷键优先**: Z赞/C收藏/G关注/X评论/B弹幕/V分享 — DOM只是兜底
3. **录制增强**: 只按一次·标记状态diff, 系统自动推断操作类型
4. **单步调试**: 3秒出结果, 不等完整蓝图

### 各平台操作清单
| 抖音 | 方法 | 小红书 | 方法 |
|:-----|:-----|:------|:-----|
| like | 键盘Z | xhs_like | DOM点击SPAN.like-lottie |
| collect | 键盘C | xhs_collect | DOM点击SVG(like右边70px) |
| follow | 键盘G | xhs_follow | DOM点击SPAN.reds-button |
| open_comments | 键盘X | xhs_comment | 需打开评论区(不能用X) |
| post_comment | X→点输入框→打字→点发送 | xhs_post_comment | JS找输入框+按钮 |
| close_comments | 键盘X | — | go_back() |
| next_video | 键盘↓ | xhs_scroll_feed | 键盘↓ |
| open_video | 双击卡片(键盘→DOM→坐标三层兜底) | xhs_click_note | 点笔记封面 |

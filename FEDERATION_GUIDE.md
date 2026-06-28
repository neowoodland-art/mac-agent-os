# AgentOS 联邦系统使用指南

> 版本 4.2.0 | 2026-06-21
> 本文档让三台机器都能理解整个联邦系统：架构、工具、操作流程、故障处理

---

## 一、三台机器概况

| 主机名 | Tailscale IP | SSH 用户 | Home | 角色 |
|:-------|:-------------|:---------|:-----|:-----|
| **chengzigedeAir** (macbook-air) | 100.111.43.6 | chengzige | /Users/chengzige | master |
| **5kechengdeAir** (5macbook-air) | 100.72.182.121 | 5kecheng | /Users/5kecheng | worker |
| **7kecheng** (7macbook-air) | 100.65.35.28 | 7kecheng | /Users/7kecheng | worker |

**共同点**（三台一致）：
- Python 3.13.12 agent-os venv
- Playwright 1.58.0 + Camoufox 0.4.11
- Git 双端同步（Gitee + GitHub）
- 12 个蓝图 JSON 文件（另有测试蓝图）
- 联邦目录结构

**本机独有**（agent-local/ 不同步）：
- 身份密钥、API Key
- 本地记忆、素材
- 运行时日志

---

## 二、目录结构

### 共享仓库: `~/workbuddy-agent-os/agent-sync/`

```
agent-sync/
├── 00_bootstrap/        ← 初始化脚本（init.sh + apply-config.sh）
├── 01_core/             ← 核心配置 + 系统操作手册
├── 02_skills/           ← WorkBuddy 技能
├── 03_knowledge/        ← Obsidian 知识库
│   ├── 00_inbox/        → 待提纯收件箱
│   ├── 01_submissions/  → 多机提交箱
│   └── ...
├── 04_memory/           ← 跨机记忆/心跳/事件
├── 05_tools/            ← 所有工具脚本
│   ├── 00_setup/        → 系统安装/guardd
│   ├── 01_system/       → 系统工具
│   ├── 05_crawl/        → 采集工具(LongCat)
│   ├── 07_matrix/       → 矩阵养号核心
│   │   └── scripts/     → Python CLI + mc CLI
│   ├── 09_ave/          → 视频工厂
│   └── 10_dashboard/    → 系统监控面板
├── README.md            ← 系统入口
├── FEDERATION_GUIDE.md  ← 本文件
├── DEPLOY-GUIDE.md      ← 部署指南
└── requirements.txt     ← Python 依赖
```

### 本机独有: `~/workbuddy-agent-os/agent-local/`

```
agent-local/
├── identity/secrets/    ← 私钥、API Key
├── materials/           ← 素材（大文件）
├── memory/              ← 本机记忆
├── runtime/             ← 运行时日志
│   ├── dashboard.log/.err   ← Dashboard 日志
│   ├── guardd/              ← guardd 日志
│   └── socks5_*.log         ← 代理日志
```

---

## 三、核心系统

### 3.1 Dashboard — 系统监控面板

**URL**: `http://localhost:9988/`

**启动方式**（launchd 管理，开机自启）：
```bash
# 查看状态
launchctl list com.agentos.dashboard

# 手动重启
launchctl unload ~/Library/LaunchAgents/com.agentos.dashboard.plist
launchctl load ~/Library/LaunchAgents/com.agentos.dashboard.plist

# 看日志
tail -f ~/workbuddy-agent-os/agent-local/runtime/dashboard.log
```

**功能模块**（侧边栏 5 组 25+ 视图）：

| 组 | 子视图 | 说明 |
|:---|:-------|:-----|
| 矩阵 📱 | 账号管理、养号执行、信息采集、内容发布、定向评论、收藏点赞、蓝图管理、登录管理、定时任务、语料库、联邦指挥台 | 多平台账号矩阵 |
| 视频工厂 🎬 | 渲染任务、脚本生成、素材库、模板 | AVE 视频制作 |
| 内容采集 📡 | 采集任务、源管理、采集历史 | 网页采集 |
| 联邦 🖥️ | 机器状态、一键同步、对账检查、远程Shell | 跨机管理 |
| 服务 ⚙️ | MCP状态、Dashboard日志、全局定时任务 | 系统监控 |

**开发模式**（修改前端代码后热更新）：
```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard/frontend
npx vite build              # 构建生产版本
launchctl reload ...        # 重启 Dashboard
```

**后端**：FastAPI (Python)，端口 9988，app.py 注册所有 API 路由。

### 3.2.5 CommandBus → guardd 任务管理体系 (v7)

**架构演进**：v6 之前用 SSH/subprocess 直接执行；v7 改为 Dashboard 调 guardd HTTP API，guardd 作为节点代理管理任务生命周期。

**组件关系**：

```
Dashboard (控制平面)              guardd (每台机器的节点代理)
┌─────────────────────┐          ┌──────────────────────────┐
│ 看板UI              │  HTTP    │ HTTP Server :9090         │
│ 任务编排(CMD模板)    │◄────────►│ 任务管理器(进程追踪)      │
│ 跨机状态聚合         │          │ 心跳上报(每300s)          │
│ POST /api/ops/run   │          │ 模块化健康检查(9模块)     │
└─────────────────────┘          └──────────────────────────┘
```

**位置**：
- 控制面：`05_tools/10_dashboard/services/command_bus.py`
- 节点代理：`05_tools/00_setup/guardd/guardd.py`

**职责**：
- CommandBus：接收看板命令 → ORACLE 对账 → 按机器分组 → 渲染CMD模板 → HTTP发给目标机器guardd
- guardd：接收HTTP任务 → 创建子进程 → 追踪PID → 日志采集 → 状态上报 → 支持停止/清理

**任务生命周期状态**：
```
queued → running → completed / failed / cancelled / crashed
```

**guardd HTTP API**（端口 9090）：
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/task` | 接收并执行任务（body: cmd, run_id, machine） |
| GET | `/tasks` | 返回所有任务状态列表 |
| POST | `/task/{id}/stop` | 停止指定任务（SIGTERM → SIGKILL） |
| GET | `/health` | 健康检查（心跳数据 + 任务统计） |

**停止机制**：Dashboard → `POST /api/ops/stop/{run_id}` → 查找任务所在机器 → HTTP调guardd `/task/{id}/stop` → guardd kill 子进程 → 标记为 CANCELLED

**与 v6 的区别**：
- 不再 subprocess 直接执行，改为 HTTP 调 guardd
- 远程机器不再走 SSH，走 HTTP (Tailscale IP + 9090)
- guardd 从定时任务(300s) 改为持久守护进程(KeepAlive=true)
- 任务PID持久追踪，支持真正的进程级停止

### 3.2 guardd — 节点代理守护进程 (v7)

**作用**：持久运行的节点代理，提供 HTTP 任务管理 API + 定时健康检查(300s)。

**v7 架构变更**：从 launchd 定时任务(StartInterval=300) 改为持久守护进程(KeepAlive=true)：
- HTTP Server (端口 9090) — 接收 Dashboard 下发的任务
- 任务管理器 — 创建子进程、追踪 PID、支持停止/清理
- 心跳循环 — 每 300 秒执行 9 模块健康检查（原有逻辑不变）

**三台机器都已通过 launchd 安装**，开机自启，`launch.sh` 包装器自动适配本机路径。

```bash
# 查看状态
launchctl list com.agentos.guardd

# 查看任务状态
curl -s http://localhost:9090/tasks | python3 -m json.tool

# 查看健康检查结果
cat ~/workbuddy-agent-os/agent-local/runtime/guardd/last_run.json

# 查看日志
tail -20 ~/workbuddy-agent-os/agent-local/runtime/guardd/guardd.log

# 手动重载（改配置后）
launchctl unload ~/Library/LaunchAgents/com.agentos.guardd.plist
launchctl load ~/Library/LaunchAgents/com.agentos.guardd.plist
```

**检查项**（9 模块，每 300 秒一轮）：心跳上报 → Dashboard 数据同步 → 任务执行 → 升级检查 → 记忆整理 → 知识同步 → 加密通道 → Git 同步拉取 → 过期数据清理。

### 3.3 Socks5 代理转发

**作用**：将本机 10800 端口的 socks5 请求转发到远程。

```bash
launchctl list com.agentos.socks5-forwarder
```

---

## 四、命令行工具

### 4.1 `mc` CLI — 矩阵管理系统

**路径**：`~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts/`

```bash
# 激活环境后
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts
python3 -m mc --help

# 核心子命令
python3 -m mc run --accounts=A --blueprints=B --rounds=N   # ✅ 批量执行
python3 -m mc account list|create|login|status              # ✅ 账号管理
python3 -m mc task comment --url=...                        # ✅ 定向评论
python3 -m mc corpus list|add                               # ✅ 语料库
python3 -m mc config show                                   # ✅ 系统配置
python3 -m mc status all                                    # ✅ 全局状态
python3 -m mc publish --platform=douyin ...                 # ✅ 视频发布
python3 -m mc remote exec <host> <cmd>                      # ✅ 远程执行
python3 -m mc blueprint list|show                           # ✅ 蓝图管理
```

### 4.2 `agentos` CLI — 系统管理

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts
python3 -m agentos --help

# 常用子命令
python3 -m agentos serve     # 启动服务（dashboard, guardd 等）
python3 -m agentos register  # 注册到联邦
python3 -m agentos check     # 系统健康检查
```

### 4.3 `matrix_mgmt.py` — 账号管理

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts
python3 matrix_mgmt.py --help

# 常用操作
python3 matrix_mgmt.py accounts list           # 列出账号
python3 matrix_mgmt.py accounts sync           # 同步账号
python3 matrix_mgmt.py backup                  # 备份

### 4.4 登录状态机（2026-06-20 重构 v2.0）

**代码位置**: `scripts/matrix_modules/account/login_state_machine.py`

**架构**：三组件模式

```
LoginStateMachine (编排器)
  ├─ PlatformDetector (策略模式, 按平台可插拔)
  │   ├─ DouyinDetector  — 文本检测 + DOM锚点 + Cookie辅助
  │   └─ XhsDetector     — DOM锚点 + Cookie辅助
  └─ RecoveryChain (可配置恢复链)
      ├─ DouyinLoginRecovery — 抖音专用：点击登录 → 一键登录或填手机
      │   → SMS验证码 → 确认登录  ← 2026-06-20 完成
      ├─ CookieRecovery     — 导航到 user/self
      ├─ SmsRecovery        — 小红书 SMS 备用
      └─ VisualRecovery     — 截图上报
```

**三种登录场景全部通过验证**（2026-06-20）：

| 场景 | 触发条件 | 流程 | 状态 |
|:-----|:---------|:-----|:----:|
| **已登录** | Session cookie 有效 | detect → `logged_in` → 直接执行蓝图 | ✅ |
| **短期过期** | Session cookie 存在但服务端标记过期 | detect → `not_logged` → 点登录 → 点一键登录 → SMS码 → **确认登录** → 蓝图 | ✅ |
| **全新登录** | 无 cookie | detect → `not_logged` → 点登录 → 自动填手机 → 获取验证码 → **登录** → 蓝图 | ✅ |

**关键发现**：
- 登录按钮文字在不同场景不同：全新登录是「登录」，短期过期是「**确认登录**」
- 抖音 UI 使用自定义组件，`<input>` 的 placeholder 无法通过通用 CSS 选择器匹配
- 使用 JS `page.evaluate()` 遍历所有元素 + 文本匹配作为兜底
- 点击被浮层拦截时，JS `el.click()` 绕过 Playwright 的可见性检查

**2026-06-20 重构要点**：
1. `DouyinDetector.detect()` 四重检测：DOM锚点 → 页面文本 → 标题 → Cookie（仅日志）
2. 修复 `[data-e2e="user-avatar"]` 误匹配视频创作者头像的问题
3. `RecoveryChain` 每一步有独立 timeout，超时自动跳过
4. SMS 验证码轮询用 `_fetch_messages()` 直接调用，只接受 `id > min_id` 的新消息
  1. 抖音 `logged_in` 锚点从 2 个 -> 9 个（增加 `img[alt*="头像"]`、`a[href*="/user/self"]` 等）
  2. 新增 Cookie 兜底检测：DOM 检测失败后，检查 `page.context.cookies()` 中是否存在 `sessionid/token`，有则返回 `"logged_in"`
  3. `_recover_cookie()` 改为直接导航到 `https://www.douyin.com/user/self`，强制触发登录态渲染
- 验证：`douyin_test`（3个 session cookie）从之前的 `"未登录(status=unknown) 跳过本轮"` 变为能正常进入蓝图执行流程

### 4.5 多机账号管理

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts
python3 matrix_mgmt.py --help

# 常用操作
python3 matrix_mgmt.py accounts list           # 列出账号（所有机器声明+读聚合去重）
python3 matrix_mgmt.py accounts sync           # 多机同步
python3 matrix_mgmt.py backup                  # 备份
python3 matrix_mgmt.py restore                 # 恢复
```

---

## 五、联邦协作机制

### 5.1 Git 同步（主通道）

所有共享数据通过 Git 双端同步（Gitee + GitHub）。

```bash
# 每日工作流
cd ~/workbuddy-agent-os/agent-sync
git pull                    # 开始前拉取最新
# ... 工作 ...
git add -A && git commit -m "描述"
git push                    # 完成后推送
```

**冲突处理**：
```bash
# 如果 git pull 冲突
git stash                   # 暂存本地修改
git pull                    # 拉取最新
git stash pop               # 恢复本地修改
# 手动解决冲突 → git add → git commit
```

### 5.2 一键同步（Dashboard 内）

Dashboard → 联邦 → 一键同步：通过 SSH 在 3 台机器间执行 git pull/push 同步。

### 5.3 对账检查

Dashboard → 联邦 → 对账检查：检查本机是否符合 ORACLE.yaml 宪法定义（蓝图、账号数、环境一致性）。

### 5.4 联邦对等原则（强制约束）

**核心思想：所有联邦机器完全对等，本机不特殊。**

```
Dashboard
    ↓ HTTP POST /api/ops/run {type, accounts, params}
    └─── CommandBus.dispatch()
            ├─── 本机 → HTTP localhost:9090/...   ← guardd HTTP API
            └─── 远程 → HTTP tailscale_ip:9090/... ← 同样的 guardd HTTP API
```

**硬约束：**

1. **不允许本机短路优化** — Dashboard 对本机的操作必须走与远程完全相同的代码路径。禁止
   - 绕过 guardd 直接读本地 filesystem
   - 直接用 subprocess 调 mc CLI 代替 guardd API
   - 直接从本地 override.yaml 读账号状态而不查 guardd `/accounts/status`

2. **本机测试通 = 远程可用** — 一段代码在本机（chengzigedeAir）通过 guardd HTTP API 测试通过后，
   在远程机器（5kechengdeAir、7kecheng）上直接可运行，不需要改任何代码。

3. **唯一例外是地址解析** — 本机用 `localhost:9090`，远程用 `tailscale_ip:9090`，
   这个区别是必要的，也是唯一的区别。这个解析统一由 `command_bus._guardd_api()` 处理，
   业务代码不需要感知。

4. **数据同步不走直连** — 远程机器的数据（账号状态、任务状态）通过 guardd HTTP API 获取，
   不通过 SSH 直连文件、不通过 fleet_collector 拉取文件副本。所有跨机数据交互都经过 guardd。

**设计检查清单（代码审查时使用）：**

```
□ Dashboard 对本机的操作是否走了 guardd HTTP API？
□ 是否有绕过 guardd 直接本地操作的代码路径？
□ 远程机器能否直接运行这段代码（地址解析除外）？
□ 数据获取是否统一通过 guardd API 而不是文件直读？
```

---

## 六、矩阵养号系统

### 6.1 蓝图（Blueprint）

蓝图是定义好"做什么"的 JSON 文件，位于 `05_tools/07_matrix/blueprints/`：

| 蓝图 | 说明 | 步数 | 状态 |
|:-----|:------|:----:|:----:|
| `douyin_read_profile.json` | 抖音读主页（昵称/粉丝/获赞等） | 9 | ✅ 验证通过 |
| `douyin_daily.json` | 日常养号（浏览/点赞/收藏/评论随机） | 23 | 🔵 待测试 |
| `douyin_active_v1.json` | 高活跃养号（多浏览+多搜索+评论） | 27 | 🔵 待测试 |
| `douyin_comment.json` | 定向评论（给链接→看视频→评论） | 5 | 🔵 待测试 |
| `douyin_search.json` | 搜索浏览（关键词→搜索→互动） | 14 | 🔵 待测试 |
| `douyin_collect.json` | 搜索博主→采集主页 | 5 | 🔵 待测试 |
| `douyin_search_browse.json` | 搜索+点赞+返回 | 7 | 🔵 待测试 |
| `douyin_reply.json` | 回复评论 | 5 | 🔵 待测试 |
| `douyin_comment_test.json` | 评论测试 | 5 | 🔵 待测试 |
| `dy_test_all.json` | 抖音全量功能测试 | — | 🔵 测试用 |
| `xhs_daily.json` | 小红书日常养号 | 17 | 🔵 待测试 |
| `xhs_active_v1.json` | 小红书高活跃养号 | 26 | 🔵 待测试 |
| `xiaohongshu_read_profile.json` | 小红书读主页 | 8 | 🔵 待测试 |
| `xhs_test_all.json` | 小红书全量功能测试 | — | 🔵 测试用 |

### 6.2 养号执行流程

1. **挑选账号**：在 Dashboard "账号管理" 中勾选账号
2. **选择蓝图**：在 Dashboard "养号执行" 中选蓝图
3. **执行**：点击执行，系统按蓝图步骤自动操作
4. **查看结果**：Dashboard → 联邦 → 远程Shell 查看执行日志

### 6.3 三台机器的账号分工

每台机器声明自己管理的账号（声明文件在 `profiles/{account_id}.json`）：
- **chengzigedeAir**: douyin_test, xhs_01 等
- **5kechengdeAir**: 各声明文件
- **7kecheng**: 各声明文件

规则：**各管各的账号**，读聚合时去重不覆盖。

---

## 七、配置文件

### 7.1 Python 环境

```bash
# 统一使用 agent-os venv
$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3

# 远程执行脚本用
$MC_PYTHON=$(echo $HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3)

# 安装依赖
pip install -r ~/workbuddy-agent-os/agent-sync/requirements.txt
```

### 7.2 Launchd 服务

三台机器共用 plist 模板（`05_tools/00_setup/guardd/com.agentos.guardd.plist`），
通过 `launch.sh` 包装器自动适配本机 `$HOME` 路径。

| 服务 | Plist | 作用 |
|:-----|:------|:-----|
| dashboard | `com.agentos.dashboard` | 监控面板（9988端口） |
| guardd | `com.agentos.guardd` | 系统守护（300秒周期） |
| socks5-forwarder | `com.agentos.socks5-forwarder` | SOCKS5代理转发（10800端口） |

### 7.3 代理配置

```yaml
# config/sms.yaml 中
proxy: 127.0.0.1:10800    # 本地 socks5 代理
```

---

## 八、常见问题

### 8.1 Dashboard 视图一直"加载中"

**原因**：Rollup tree-shake 删除了 inline loader 函数（2026-06-18 修复过）。

**解决**：
1. 检查 Vite 构建：`cd frontend && npx vite build`
2. 检查 bundle 大小：正常的 bundle 约 255kB（太小说明函数被 tree-shake 了）
3. 重启 Dashboard：`launchctl unload/load com.agentos.dashboard`

### 8.2 开机弹出 Python 错误窗

**原因**：guardd launchd plist 路径不对（2026-06-19 修复为 launch.sh 包装器）。

**解决**：确保已部署最新 plist：
```bash
sed "s|__HOME__|$HOME|g" \
  05_tools/00_setup/guardd/com.agentos.guardd.plist \
  > ~/Library/LaunchAgents/com.agentos.guardd.plist
launchctl unload ~/Library/LaunchAgents/com.agentos.guardd.plist
launchctl load ~/Library/LaunchAgents/com.agentos.guardd.plist
```

### 8.3 Dashboard 端口被占用

```bash
lsof -i :9988            # 查看谁占用了端口
kill -9 <PID>            # 杀掉旧进程
launchctl reload ...     # 重启
```

### 8.4 Git push 失败

```bash
# 检查远程仓库
git remote -v

# 检查是否有未推送的提交
git status

# 如果 Gitee/GitHub 其中一个失败
git push gitee main      # 单独推 Gitee
git push github main     # 单独推 GitHub
```

### 8.5 "执行历史"一直加载

**原因**：`loadExecutionHistory()` 函数在 inline.js 中未被 Vite 打包（2026-06-19 已修复）。

**解决**：检查是否有最新的 Dashboard bundle（255kB 左右），重启即可。

### 8.6 Python 代码签名问题

```bash
# 新机器部署后必须执行
codesign -f -s - $HOME/.workbuddy/binaries/python/versions/3.13.12/bin/python3
# deploy.sh 中已自动检测此步骤
```

---

## 九、每日工作流

### 主控机器（chengzigedeAir）

```bash
# 1. 拉取最新代码
cd ~/workbuddy-agent-os/agent-sync && git pull

# 2. 检查 Dashboard 是否运行
curl -s http://localhost:9988/api/health

# 3. 查看所有机器状态
# → 打开浏览器 http://localhost:9988 → 联邦 → 机器状态

# 4. 对账检查
# → 联邦 → 对账检查 → 执行对账

# 5. 工作完成后推送
git add -A && git commit -m "描述当天工作"
git push
```

### 工作节点（5kechengdeAir / 7kecheng）

```bash
# 1. 拉取最新代码
cd ~/workbuddy-agent-os/agent-sync && git pull

# 2. 检查 guardd 状态
launchctl list com.agentos.guardd
tail -3 ~/workbuddy-agent-os/agent-local/runtime/guardd/last_run.json

# 3. 本地工作
# ...

# 4. 推送
git add -A && git commit -m "描述"
git push
```

### 所有机器通用

```bash
# 每天第一次使用前
git pull

# 遇到问题时
cat ~/workbuddy-agent-os/agent-local/runtime/guardd/guardd.log | tail -20
curl -s http://localhost:9988/api/health
```

---

## 十一、五层执行架构 (L1–L5)

所有 Dashboard 操作（养号、采集、登录、评论）都经过这五层：

```
L5 ─── Dashboard UI ───────── frontend/src/views/*.js
  │     用户点击按钮 → API 调用
  ▼
L4 ─── API 路由 ───────────── routes/matrix.py, routes/ops.py
  │     POST /api/ops/run → 调 CommandBus
  ▼
L3 ─── CommandBus ─────────── services/command_bus.py
  │     ORACLE.yaml 合规检查 → account→machine 映射
  │     预检（SSH可达、进程数）→ 分组 → mc/SSH
  ▼
L2 ─── mc 引擎 ────────────── scripts/mc/engine.py
  │     BatchEngine → 身份分组 → 启动浏览器
  │     蓝图解析 → 执行步骤 → 钩子检测
  ▼
L1 ─── Camoufox 浏览器 ────── scripts/douyin_ops.py / xhs_ops.py
       真实浏览器操作 → 点赞/评论/采集/登录
```

### 各层职责

| 层 | 位置 | 核心文件 | 职责 |
|:---|:-----|:---------|:-----|
| **L5** | Dashboard 前端 | `frontend/src/views/matrix-*.js` | 按钮交互、确认弹窗、状态轮询、结果展示 |
| **L4** | FastAPI 路由 | `routes/ops.py` `routes/matrix.py` | 参数校验 → 调用 CommandBus → 返回结果 |
| **L3** | CommandBus | `services/command_bus.py` | ORACLE合规、按机器分组、预检、SSH/本机分发、状态轮询 |
| **L2** | mc引擎 | `scripts/mc/engine.py` `scripts/mc/run.py` | 身份分组→浏览器→蓝图步骤执行→钩子检查 |
| **L1** | 平台Ops | `scripts/douyin_ops.py` `scripts/xhs_ops.py` | 页面操作原子（goto/like/comment/read_profile等） |

### 命令的生命周期

用户点击「养号执行」→ 命令经过的完整路径：

```
L5: 用户选账号→选蓝图→点执行
    → 前端 /api/ops/run POST {type:"nurture", accounts:[...], params:{blueprint:"douyin_daily"}}
L4: POST /api/ops/run → CommandBus.dispatch("nurture", accounts, params)
L3: CommandBus.dispatch():
    1. ORACLE.yaml 检查 account→machine 映射
    2. 按机器分组（同机账号合并为一条命令）
    3. 预检：SSH 可达性、活跃进程数
    4. 构造命令行: mc run --accounts=... --blueprints=... --rounds=N
    5. _send_local: subprocess.Popen(mc run ...) → 返回 PID
    6. Command.status = DISPATCHING → RUNNING → COMPLETED/FAILED
L2: BatchEngine.run():
    1. 身份分组：同 identity_dir 的账号共用浏览器
    2. 启动 Camoufox 浏览器
    3. LoginStateMachine.ensure_login() 钩子
    4. 遍历蓝图步骤 → ops.execute(op, args)
    5. 每步后 check_verify_dialog() 钩子 + 冷却
    6. 返回 BatchReport
L1: DouyinOps/XhsOps:
    → goto_home / like / comment / dy_read_nickname / ...
```

### 登录检测流程（L1 关键钩子）

```
ensure_login(account, platform)
  ├─ _detect(page)
  │   ├─ DOM锚点检查（平台特定选择器）
  │   ├─ 页面标题检测（抖音："xxx的抖音"=已登录）
  │   └─ Cookie兜底检测（sessionid/token 是否存在）
  ├─ _recover_cookie(page)
  │   └─ 导航到 user/self → 强制触发登录态
  └─ _recover_sms(page, account)
      └─ sms_login() → 填手机→等验证码→点同意
```

### 常见断点排查

| 现象 | 可能断点 | 排查方法 |
|:-----|:---------|:---------|
| 点击按钮没反应 | L5 事件绑定→L4 API | 检查前端控制台、API 返回 |
| API 返回 500 | L4 路由→L3 CommandBus | 看 dashboard.log |
| 命令"已分发"但状态不变 | L3 poll()→L2 进程 | `ps aux \| grep mc run`、看 runtime/commands/run_id.log |
| 命令"已完成"但没数据 | L2→L1 引擎 | 看命令日志中 `ensure_login` 是否通过 |
| 账号被跳过（skipped） | L1 ensure_login 失败 | 检查 session cookie 是否有效 |
| 执行卡住不动 | L1 SMS 验证弹窗 | 手动输入验证码或等超时 |

| 要找什么 | 路径 |
|:---------|:-----|
| 系统入口 | `~/workbuddy-agent-os/agent-sync/README.md` |
| 联邦指南（本文） | `~/workbuddy-agent-os/agent-sync/FEDERATION_GUIDE.md` |
| 部署指南 | `~/workbuddy-agent-os/agent-sync/DEPLOY-GUIDE.md` |
| Dashboard 源码 | `~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard/` |
| Dashboard 前端 | `~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard/frontend/` |
| 矩阵脚本 | `~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts/` |
| 蓝图 | `~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/blueprints/` |
| guardd 源码 | `~/workbuddy-agent-os/agent-sync/05_tools/00_setup/guardd/` |
| guardd 日志 | `~/workbuddy-agent-os/agent-local/runtime/guardd/` |
| Dashboard 日志 | `~/workbuddy-agent-os/agent-local/runtime/dashboard.log` |
| Python venv | `$HOME/.workbuddy/binaries/python/envs/agent-os/` |
| Launchd plists | `~/Library/LaunchAgents/com.agentos.*.plist` |

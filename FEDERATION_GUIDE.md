# AgentOS 联邦系统使用指南

> 版本 4.2.0 | 2026-06-19
> 本文档让三台机器都能理解整个联邦系统：架构、工具、操作流程、故障处理

---

## 一、三台机器概况

| 主机名 | Tailscale IP | SSH 用户 | Home | 角色 |
|:-------|:-------------|:---------|:-----|:-----|
| **chengzigedeAir** (macbook-air) | 100.111.43.6 | chengzige | /Users/chengzige | 主控 + Dashboard |
| **5kechengdeAir** (5macbook-air) | 100.72.182.121 | 5kecheng | /Users/5kecheng | 工作节点 |
| **7kecheng** (7macbook-air) | 100.65.35.28 | 7kecheng | /Users/7kecheng | 工作节点 |

**共同点**（三台一致）：
- Python 3.13.12 agent-os venv
- Playwright 1.58.0 + Camoufox 0.4.11
- Git 双端同步（Gitee + GitHub）
- 14 个蓝图文件
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

### 3.2 guardd — 系统守护进程

**作用**：每 300 秒执行一轮健康检查 + 自动恢复。

**三台机器都已通过 launchd 安装**，开机自启，`launch.sh` 包装器自动适配本机路径。

```bash
# 查看状态
launchctl list com.agentos.guardd

# 查看最近一次运行结果
cat ~/workbuddy-agent-os/agent-local/runtime/guardd/last_run.json

# 查看日志
tail -20 ~/workbuddy-agent-os/agent-local/runtime/guardd/guardd.log

# 手动重载（改配置后）
launchctl unload ~/Library/LaunchAgents/com.agentos.guardd.plist
launchctl load ~/Library/LaunchAgents/com.agentos.guardd.plist
```

**检查项**：心跳上报、Dashboard 存活、磁盘空间、孤儿进程、知识同步、Git 同步。

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

# 子命令
python3 -m mc run           # 运行任务（按蓝图）
python3 -m mc browser       # 浏览器管理
python3 -m mc proxy         # 代理管理
python3 -m mc scheduler     # 任务调度
python3 -m mc runlog        # 运行日志
python3 -m mc recorder      # 录制操作
python3 -m mc corpus        # 语料库管理
python3 -m mc exporter      # 导出
python3 -m mc task          # 任务管理
python3 -m mc analyzer      # 分析器
python3 -m mc engine        # 引擎管理
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
python3 matrix_mgmt.py restore                 # 恢复
```

### 4.4 `guardd.py` — 守护进程（手动运行）

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/00_setup/guardd
python3 guardd.py                              # 前台运行（调试用）
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

---

## 六、矩阵养号系统

### 6.1 蓝图（Blueprint）

蓝图是定义好"做什么"的 JSON 文件，位于 `05_tools/07_matrix/blueprints/`：

| 蓝图 | 说明 |
|:-----|:------|
| `douyin_daily.json` | 抖音日常养号 |
| `xhs_daily.json` | 小红书日常养号 |
| `douyin_comment.json` | 抖音定向评论 |
| `douyin_search.json` | 抖音搜索 |
| `douyin_collect.json` | 抖音信息采集 |
| `xiaohongshu_read_profile.json` | 小红书读主页 |
| `douyin_read_profile.json` | 抖音读主页 |

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

## 十、关键路径速查

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

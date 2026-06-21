# AgentOS 系统操作速查手册

> 版本：v1.1 | 最后更新：2026-05-15
> 用途：换机安装 / 日常同步 / 升级技能 / 角色切换——所有系统级操作一览
> 仓库策略：主电脑双仓库（Gitee + GitHub），其他电脑仅 Gitee

---

## 一、操作总表

| 场景 | 命令 | 频率 | 耗时 |
|------|------|------|------|
| **首次装新机** | `agentos init` | 每台机器仅一次 | 3-5分钟 |
| **日常同步** | `git pull` + 增量部署 | 每次工作前/后 | 1分钟 |
| **部署身份文件** | `bash apply-config.sh` | 01_core/ 有改动时 | 10秒 |
| **同步技能** | `agentos skill install` | 02_skills/ 有改动时 | 10秒 |
| **升级 agentos CLI** | `agentos upgrade` | CLI 本身有版本更新时 | 1分钟 |
| **切换机器角色** | `HOST_ROLE=xxx bash apply-config.sh` | 需要改变角色时 | 10秒 |
| **重建向量索引** | `agentos rebuild-vector` | 知识库大批量更新后 | 3分钟 |
| **健康检查** | `agentos check` | 出问题时 | 30秒 |

---

## 二、换机初始化（仅一次）

**场景**：买到新电脑 / 重装系统后，从头搭建 AgentOS。

```bash
# 1. 安装 WorkBuddy（从官网下载）

# 2. 克隆仓库
cd ~/workbuddy-agent-os
git clone git@gitee.com:babycalf/mac-agent-os.git agent-sync

# 3. 运行一键初始化
cd agent-sync
agentos init

# 4. 部署身份文件
bash 00_bootstrap/apply-config.sh
```

**`agentos init` 自动完成**：
- 创建 agent-sync/ + agent-local/ 目录
- 安装 Python/Node 依赖
- 注册所有技能到 WorkBuddy
- 配置 MCP 服务器
- 创建自动化定时任务

---

## 三、日常同步（每天做）

**场景**：本机和另一台机器互相同步最新代码。

### 3.1 流程

```bash
# 第1步：拉取远程最新代码（所有机器都先做这步）
cd ~/workbuddy-agent-os/agent-sync
git pull

# 第2步：部署身份文件（如果 01_core/ 有更新）
bash 00_bootstrap/apply-config.sh

# 第3步：同步技能（如果 02_skills/ 有更新）
agentos skill install

# 第4步：推送本地更新（如果本机有改动）
git add .
git commit -m "更新说明"
git push
```

### 3.2 ⚠️ 推送规则（重要）

**禁止使用 `git push --force`**。强制推送会导致其他机器的提交记录丢失。

你的 commit 被拒绝时，说明远程比你新（别人先推了），你应该：

```bash
# 正确做法
git add .
git commit -m "更新说明"
git pull      # 先拉取别人更新（自动合并）
git push      # 再推自己的

# 错误做法（会导致其他人的代码丢失）
git push --force   # ❌ 禁止！会覆盖远程历史
```

如果确实需要强制推送（如修复敏感信息），使用更安全的版本：

```bash
# 安全的强制推送：只在你基于最新远程代码时才允许
git push --force-with-lease
# 比 --force 安全：如果你本地不是基于最新远程，会拒绝
```

### 3.3 多机协作防冲突机制

| 机制 | 说明 | 配置方式 |
|------|------|---------|
| **Git 规范** | 先 pull 再 push，不用 --force | 团队约定 |
| **pre-push 钩子** | 执行 `git push --force` 时自动拒绝 | 运行 `apply-config.sh` 自动安装 |
| **--force-with-lease** | 安全强制推送，检查本地是否基于最新远程 | 替代 --force |
| **GitHub 分支保护** | 公开仓库免费，可禁止 force push | GitHub → Settings → Branches |

> pre-push 钩子已集成到 `apply-config.sh`，每次部署配置时会自动安装到 `.git/hooks/pre-push`。
> 钩子脚本在 `00_bootstrap/hooks/pre-push`，所有机器 git pull 后自动同步。

**推荐**：在 Gitee 仓库设置中开启 main 分支保护（设置 → 分支保护 → 不允许强制推送），这样即使有人用了 `--force` 也会被拒绝。

### 3.2 gitignore 规则（避免机器专属文件冲突）

`.gitignore` 已配置以下排除规则，各机器专属文件不会进入仓库：

| 排除项 | 原因 | 说明 |
|--------|------|------|
| `.obsidian/` | 窗口布局/插件配置各机器不同 | workspace.json 记录打开的文件和窗口位置 |
| `01_core/IDENTITY.md` | 从模板生成，填充本机设备信息 | 模板为 IDENTITY.tpl.md，各机器运行 init 生成 |
| `01_core/HOST_ID.md` | 角色/主机名各机器不同 | 每台机器独立设置 |
| `01_core/USER.md` | 用户偏好各机器可能不同 | 同上 |
| `01_core/mcp.json` | MCP 服务路径各机器不同 | 模板为 mcp.tpl.json |
| `04_memory/long_term/facts.db` | 本地记忆库，各机器独立 | 不同步 |
| `04_memory/logs/*.log` | 日志文件，各机器独立 | — |
| `04_memory/vector_db` | 向量库，可重建 | — |
| `agent-local/` | 整机专属数据目录 | 软链到本机私有位置 |

**如有新文件需要排除**，编辑 `.gitignore` 后运行：
```bash
git rm --cached <文件路径>    # 解除 Git 追踪（不删本地文件）
```

### 3.2 同步协作图

```
本机（A）         远程仓库         另一台（B）
  │                  │                │
  ├─ git push ──────→│←── git pull ──┤
  │                  │                │
  │←── git pull ────│── git push ──→│
  │                  │                │
```

> 每次工作前 → `git pull`（拉取别人更新）
> 每次工作后 → `git push`（推送自己更新）

---

## 四、升级技能（02_skills/ 变更时）

**场景**：某台机器新增/修改了技能文件（content_processor/collect_to_inbox 等）。

### 操作步骤

```bash
# 1. 拉取更新
git pull

# 2. 查看技能变更了哪些
git diff --name-status HEAD~1 02_skills/

# 3. 安装/更新所有技能到 WorkBuddy
agentos skill install

# 4. 验证技能已注册
agentos skill list
```

> 注意：`agentos skill install` 会扫描 `02_skills/` 下的所有 SKILL.md，注册到 WorkBuddy。新增技能会自动注册，修改技能会自动更新。

---

## 五、升级核心配置（01_core/ 变更时）

**场景**：SOUL.md/IDENTITY.md/USER.md 有更新。

### 操作步骤

```bash
# 1. 拉取更新
git pull

# 2. 查看身份文件变更了什么
git diff HEAD~1 -- 01_core/SOUL.md 01_core/IDENTITY.md 01_core/USER.md

# 3. 部署到 .workbuddy/（使新配置生效）
bash 00_bootstrap/apply-config.sh

# 4. 重启 WorkBuddy（使新 SOUL.md 被加载）
# 在 WorkBuddy 中重启即可

# 5. 验证部署版本
cat ~/.workbuddy/.config-version.json
```

### 版本追踪

每次执行 `apply-config.sh` 会自动生成版本记录：

```json
{
  "deployed_at": "20260503_120117",   // 部署时间
  "host_role": "unified",              // 当前机器角色
  "files": {                           // 各文件MD5
    "SOUL.md": "27f08daf...",
    "IDENTITY.md": "ca0478d9...",
    "USER.md": "086bb449..."
  }
}
```

---

## 六、切换机器角色

**场景**：某台机器角色变更（统一版→仅采集内容→媒体处理机）。

### 预设角色

| 角色 | 适用场景 | SOUL.md 版本 |
|------|----------|-------------|
| `unified` | 所有机器统一配置（默认） | 完整版 |
| `main-node` | 主力工作机 | 完整版 |
| `submit-node` | 仅采集内容 | 精简版（仅收集规则） |
| `media-node` | 视频/音频处理 | 中量版（采集+素材） |

### 操作步骤

```bash
# 设定角色并部署
HOST_ROLE=submit-node bash 00_bootstrap/apply-config.sh

# 查看当前角色
cat ~/.workbuddy/.config-version.json | grep host_role
```

> 当前阶段使用 `unified`（统一版本），后续可按需分配不同角色。

---

## 七、升级 agentos CLI（05_tools/00_setup/ 变更时）

**场景**：agentos 主程序有版本更新。

```bash
# 查看当前版本
agentos --version

# 升级
agentos upgrade

# 验证新版本
agentos --version
```

---

## 八、guardd 守护进程运维

guardd 是 AgentOS 联邦多机协同守护进程，每 300 秒执行一轮 9 模块循环（心跳/dashboard同步/任务/版本/记忆/知识/加密/git同步/清理）。

### 安装

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/00_setup/guardd
bash scripts/install.sh
```

安装后 guardd 会通过 launchd 自动管理，重启后也会自动运行。

### 手动控制

```bash
# 查看守护进程状态
launchctl print gui/$(id -u)/com.agentos.guardd

# 立即执行一次（不等待周期）
launchctl kickstart -k gui/$(id -u)/com.agentos.guardd

# 手动测试执行（调试用）
python3 ~/workbuddy-agent-os/agent-sync/05_tools/00_setup/guardd/guardd.py

# 暂停守护进程（不卸载）
launchctl bootout gui/$(id -u)/com.agentos.guardd

# 恢复守护进程
launchctl bootstrap gui/$(id -u)/com.agentos.guardd

# 彻底卸载
launchctl bootout gui/$(id -u)/com.agentos.guardd || true
rm -f ~/Library/LaunchAgents/com.agentos.guardd.plist
```

### 查看运行状态

```bash
# 最近一次执行结果
cat ~/workbuddy-agent-os/agent-local/runtime/guardd/last_run.json

# 完整日志
cat ~/workbuddy-agent-os/agent-local/runtime/guardd/guardd.log

# 错误日志
cat ~/workbuddy-agent-os/agent-local/runtime/guardd/errors.log
```

### 9 模块说明

| 模块 | 职责 | 输出 |
|------|------|------|
| heartbeat | 采集 CPU/内存/磁盘 → 写入心跳 | `cross_machine/status/{host}/heartbeat.json` |
| task_worker | 扫描并执行分配至本机的跨机任务 | `cross_machine/tasks/completed/` |
| upgrade_checker | 版本清单比对，发现更新后发事件 | `cross_machine/events/` + 本地 version 记录 |
| memory_triage | 过滤本地记忆，推送通用内容到提交箱 | `agent-local/submissions/memory_triage/` |
| knowledge_sync | 检测知识库变更 + 推送本地提交 | 事件日志 + `03_knowledge/01_submissions/` |
| encrypted_channel | 解密 RSA-4096 加密消息（需 cryptography） | `agent-local/identity/secrets/received/` |
| cleanup | 清理超过 30 天的旧事件和已完成任务 | 删除过期文件 |

### 依赖说明

- **基本运行**：Python 标准库（无额外依赖）
- **加密消息**：需安装 `cryptography` 库（`pip install cryptography`）
- **日志自动轮转**：launchd 管理的 stdout/stderr 日志不会自动截断，建议定期检查 `agent-local/runtime/guardd/` 目录大小

---

## 九、不用做的事

| 操作 | 什么时候需要 | 备注 |
|------|-------------|------|
| `agentos init` | ❌ 仅换机时一次 | 日常不要重复执行 |
| 重建向量库 | ❌ 知识库内容无变化时 | 只在大批量入库后做 |
| 手动修改 `.workbuddy/` | ❌ 应通过 `apply-config.sh` 部署 | 直接改会被下次部署覆盖 |
| 重启机器 | ❌ WorkBuddy 重启即可 | 不需要重启操作系统 |

---

## 十、快速查询：我怎么知道该做什么？

| 场景 | 你的问题 | 答案 |
|------|---------|------|
| 新机 | "刚买电脑，怎么装环境？" | 走 **二、换机初始化** |
| 日常 | "另一台机器有更新，我要拉吗？" | 走 **三、日常同步** |
| 技能 | "我更新了一个技能文件" | 走 **四、升级技能** |
| 核心 | "改了 SOUL.md，另一台怎么生效？" | 走 **五、升级核心配置** |
| 角色 | "这台机器以后只做采集" | 走 **六、切换机器角色** |
| CLI | "agentos 有新版了" | 走 **七、升级 agentos CLI** |
| 集群 | "怎样查看各机器是否在线？" | 走 **八、guardd**，查看 `cross_machine/status/{host}/heartbeat.json` |
| 集群 | "怎么给另一台机器发加密消息？" | 走 **八、guardd**，参考 encrypted_channel 模块 |

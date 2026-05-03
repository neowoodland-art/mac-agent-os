# AgentOS 系统操作速查手册

> 版本：v1.0 | 最后更新：2026-05-03
> 用途：换机安装 / 日常同步 / 升级技能 / 角色切换——所有系统级操作一览

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

## 八、不用做的事

| 操作 | 什么时候需要 | 备注 |
|------|-------------|------|
| `agentos init` | ❌ 仅换机时一次 | 日常不要重复执行 |
| 重建向量库 | ❌ 知识库内容无变化时 | 只在大批量入库后做 |
| 手动修改 `.workbuddy/` | ❌ 应通过 `apply-config.sh` 部署 | 直接改会被下次部署覆盖 |
| 重启机器 | ❌ WorkBuddy 重启即可 | 不需要重启操作系统 |

---

## 九、快速查询：我怎么知道该做什么？

| 场景 | 你的问题 | 答案 |
|------|---------|------|
| 新机 | "刚买电脑，怎么装环境？" | 走 **二、换机初始化** |
| 日常 | "另一台机器有更新，我要拉吗？" | 走 **三、日常同步** |
| 技能 | "我更新了一个技能文件" | 走 **四、升级技能** |
| 核心 | "改了 SOUL.md，另一台怎么生效？" | 走 **五、升级核心配置** |
| 角色 | "这台机器以后只做采集" | 走 **六、切换机器角色** |
| CLI | "agentos 有新版了" | 走 **七、升级 agentos CLI** |

# AgentOS 环境要求

## 当前设备实际状态

| 软件 | 状态 | 版本 | 备注 |
|---|---|---|---|
| WorkBuddy | ✅ 已安装 | — | 桌面客户端，核心运行环境 |
| Python (managed) | ✅ 已安装 | 3.13.12 | `~/.workbuddy/binaries/python/versions/3.13.12/bin/python3` |
| Python venv (agent-os) | ✅ 已安装 | 3.13.12 | `~/.workbuddy/binaries/python/envs/agent-os/bin/python3` |
| Node.js (managed) | ✅ 已安装 | 22.12.0 | `~/.workbuddy/binaries/node/versions/22.12.0/bin/node` |
| 坚果云 | ✅ 已安装 | — | 同步目录：`~/NutstoreCloudBridge/` |
| Obsidian | ❌ 未安装 | — | 需手动安装 |

## 必需基础环境

| 软件 | 最低版本 | 用途 | 安装方式 |
|---|---|---|---|
| **WorkBuddy 桌面客户端** | 最新版 | AI 运行时、技能执行、自动化调度 | [codebuddy.cn](https://www.codebuddy.cn) 下载 |
| **Python** | 3.10+ | 技能脚本、记忆管理、数据清洗 | WorkBuddy 自动管理，无需手动安装 |
| **Node.js** | 18+ | WorkBuddy 运行时 | WorkBuddy 自动管理，无需手动安装 |

> ⚠️ **不需要手动安装 Python 和 Node.js**——WorkBuddy 自带 managed 版本，路径固定。
> 如果 WorkBuddy 未安装，需先从 [codebuddy.cn](https://www.codebuddy.cn) 下载。

## Python 依赖库

### 安装方法（固定命令）

```bash
# 1. 创建虚拟环境（仅需一次）
~/.workbuddy/binaries/python/versions/3.13.12/bin/python3 \
  -m venv ~/.workbuddy/binaries/python/envs/agent-os

# 2. 安装依赖
~/.workbuddy/binaries/python/envs/agent-os/bin/pip install \
  -r ~/workbuddy-agent-os/agent-sync/requirements.txt

# 3. 验证
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 \
  -c "import trafilatura, sqlite_utils; print('依赖OK')"
```

### 依赖清单

| 库 | 版本 | 用途 | 使用者 |
|---|---|---|---|
| trafilatura | ≥2.0.0 | 网页正文提取 | kb_ingest.py |
| sqlite-utils | ≥3.35 | SQLite 增强操作 | facts.db 便捷操作 |

> 依赖安装在 `~/.workbuddy/binaries/python/envs/agent-os/` 虚拟环境中，不污染系统环境。
> 所有 agent-os 脚本统一使用此 venv 的 Python 执行。

### 可选依赖（暂不安装）

| 库 | 版本 | 用途 | 何时安装 |
|---|---|---|---|
| chromadb | ≥1.0.0 | 向量数据库，L1 语义检索升级 | 当关键词索引不够用时 |

## 可选工具

| 软件 | 用途 | 安装方式 | 是否必须 |
|---|---|---|---|
| **Obsidian** | 浏览和编辑知识库 | [obsidian.md](https://obsidian.md) 下载 | 推荐但非必须 |
| **坚果云客户端** | 跨机同步 agent-os 目录 | [jianguoyun.com](https://www.jianguoyun.com) 下载 | 跨机同步时需要 |

### 坚果云同步配置

当前坚果云同步路径：`~/NutstoreCloudBridge/`

配置方式（二选一）：
1. **方式 A（推荐）**：将 `~/workbuddy-agent-os/agent-sync/` 移动到坚果云同步目录
   ```bash
   mv ~/workbuddy-agent-os/agent-sync ~/NutstoreCloudBridge/agent-os
   ```
2. **方式 B**：在坚果云客户端中添加 `~/workbuddy-agent-os/agent-sync/` 为自定义同步文件夹

> ⚠️ 移动后需更新 WorkBuddy 自动化中的路径和工作区配置。

### Obsidian 推荐插件

| 插件 | 用途 | 是否必须 |
|---|---|---|
| Dataview | 知识查询和时间线视图 | 推荐 |
| Templater | 使用知识卡片模板 | 推荐 |
| Timeline | 时间线可视化 | 可选 |

## WorkBuddy 自动化配置

AgentOS 依赖一个 WorkBuddy 自动化任务，每日凌晨 2:00 自动执行记忆提炼：

| 配置项 | 值 |
|---|---|
| 自动化 ID | `agentos` |
| 名称 | AgentOS 每日记忆提炼 |
| 调度 | 每日凌晨 2:00 |
| Python 路径 | `~/.workbuddy/binaries/python/envs/agent-os/bin/python3` |
| 脚本路径 | `~/workbuddy-agent-os/agent-sync/02_skills/memory_manager/daily_digest.py` |

> 此自动化在首次运行 `init.sh` 后由 WorkBuddy 内部创建，无需手动配置。

## 跨平台说明

AgentOS 使用相对路径和 `$HOME` 变量，兼容 macOS / Linux / Windows (WSL2)。

| 平台 | 说明 |
|---|---|
| **macOS** | 直接运行，无需额外配置 |
| **Linux** | 直接运行，部分系统命令可能需要 `sudo` |
| **Windows** | 需通过 WSL2 运行，路径使用 `/mnt/c/Users/xxx/` |

> ⚠️ managed Python 和 venv 路径在不同设备上可能不同，换机后需重新运行 `init.sh`。

## 安装验证

```bash
# 检查 WorkBuddy managed Python
~/.workbuddy/binaries/python/versions/3.13.12/bin/python3 --version
# 应输出: Python 3.13.12

# 检查 agent-os venv
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 --version
# 应输出: Python 3.13.12

# 检查 venv 依赖
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 \
  -c "import trafilatura, sqlite_utils; print('依赖OK')"

# 检查 WorkBuddy managed Node.js
~/.workbuddy/binaries/node/versions/22.12.0/bin/node --version
# 应输出: v22.12.0

# 检查坚果云
ls ~/NutstoreCloudBridge/ && echo "坚果云已安装"
```

全部就绪后，执行初始化：

```bash
cd ~/workbuddy-agent-os/agent-sync/00_bootstrap && bash init.sh
```

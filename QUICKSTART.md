# AgentOS 快速上手

> 版本 3.0 | 多智能体协同模式

## 前置条件

- ✅ **WorkBuddy 桌面客户端**（[codebuddy.cn](https://www.codebuddy.cn) 下载）— 必需
- ✅ **Git**（macOS 自带）— 代码同步必需
- ✅ **Gitee 或 GitHub 账号** — 用于多机协同
- ⬜ **Obsidian**（[obsidian.md](https://obsidian.md) 下载）— 推荐，浏览知识库

> Python 和 Node.js 由 WorkBuddy 自动管理，**不需要手动安装**。

---

## 新机器部署流程

### 1. 克隆仓库

```bash
git clone git@gitee.com:babycalf/mac-agent-os.git ~/workbuddy-agent-os/agent-sync
cd ~/workbuddy-agent-os/agent-sync
```

> 如果 SSH 未配置，用 `git_sync_manager` 技能引导配置。

### 2. 一键初始化

```bash
bash 00_bootstrap/init.sh
```

脚本自动完成：
- 创建 `agent-local/` 目录结构（identity/memory/materials/submissions...）
- 重建 3 条软链接（raw/vector_db/cache）
- 安装 Python 依赖
- 检测设备和系统信息
- 创建 L1 关键词索引

### 3. 生成本机身份

```bash
agentos localize
```

执行后：
- `agent-local/identity/IDENTITY.md` — 本机身份（含主机名、路径等）
- `agent-local/identity/USER.md` — 用户信息
- `agent-local/identity/HOST_ID.md` — **本机角色 + 能力开关**

**关键步骤**：编辑 `HOST_ID.md` 设置角色：

```yaml
# 选择一种角色：
# master     → 知识提纯/记忆汇总/核心维护（推荐主电脑）
# maintainer → 内容采集/本地记忆/提交价值内容（推荐工作机）
# node       → 信息采集/素材上传（推荐轻量设备）
角色: master
```

> 角色决定自动化任务：master 自动执行 inbox_refine，其他角色跳过。

### 4. 同步技能到 WorkBuddy

```bash
agentos sync
```

将 `02_skills/` 下的技能注册到 WorkBuddy，同时部署 MCP 配置。

### 5. 升级依赖

```bash
agentos upgrade
```

拉取最新代码 + 安装依赖 + 环境检查。

### 6. 重建向量数据库

```bash
agentos rebuild-vector
```

在本地重建语义检索索引（升级后必须执行）。

### 7. 验证系统状态

```bash
agentos check
```

---

## 日常使用流程

### 拉取最新代码

```bash
cd ~/workbuddy-agent-os/agent-sync && git pull
```

### 主节点（master）操作

```bash
# 查看待提纯内容
ls 03_knowledge/01_submissions/

# 手动触发收件箱提纯
agentos skill run inbox_refine

# 查看各节点提交
find 03_knowledge/01_submissions/ -name "*.md"

# 提交变更到协同仓库
git add -A
git commit -m "知识库更新摘要"
git push
```

### 工作/采集节点操作

```bash
# 提交知识内容
cp 提炼后的笔记.md ~/workbuddy-agent-os/agent-local/submissions/inbox/
# 然后 git commit + git pull request 或手动同步

# 本机记忆提炼（自动运行）
# 结果保存在 agent-local/memory/daily/
```

### 升级流程

```bash
git pull
agentos upgrade
agentos rebuild-vector
```

---

## 角色行为速查

| 场景 | master | maintainer | node |
|------|--------|------------|------|
| 本地记忆提炼 | ✅ 自动 | ✅ 自动 | ✅ 自动 |
| 内容采集 | ✅ 自动 | ✅ 自动 | ✅ 自动 |
| 知识库提纯 | ✅ 自动 | ⛔ 跳过 | ⛔ 跳过 |
| Git 推送 | ✅ 自动 | ❌ 手动 | ❌ 手动 |
| 提交有价值内容 | — | ✅ 通过 submissions | ✅ 通过 submissions |
| 向量库重建 | ✅ 升级后执行 | ✅ 升级后执行 | ✅ 升级后执行 |

---

## 验证

```bash
# 1. 检查角色
cat ~/workbuddy-agent-os/agent-local/identity/HOST_ID.md

# 2. 检查角色检查工具
python3 ~/workbuddy-agent-os/agent-sync/05_tools/01_system/role_check.py

# 3. 检查向量库状态
agentos rebuild-vector --dry-run

# 4. 检查 Git 状态
cd ~/workbuddy-agent-os/agent-sync && git status
```

---

## 多机首次协同设置

```bash
# 机器A（master）：
git clone ... && bash init.sh && agentos localize
# 编辑 HOST_ID.md → role: master
agentos sync && agentos upgrade && agentos rebuild-vector

# 机器B（maintainer）：
git clone ... && bash init.sh && agentos localize
# 编辑 HOST_ID.md → role: maintainer
agentos sync && agentos upgrade && agentos rebuild-vector

# 机器B 采集后提交：
cp 内容 ~/agent-local/submissions/inbox/
cd ~/agent-sync && git add -A && git commit -m "提交内容" && git push

# 机器A 提纯发布：
cd ~/agent-sync && git pull
# → inbox_refine 自动检测 submissions/ 中的新内容
# → 审核后发布到知识库 → git push

# 机器B 获取最新知识库：
cd ~/agent-sync && git pull
```

---

🎉 **完成！** 你的多智能体联邦已就绪。各节点按角色自动运行对应任务。

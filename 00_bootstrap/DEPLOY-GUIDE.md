# AgentOS 新机器部署指南

> 版本: v1.0 | 最后更新: 2026-06-15
> 本文件供其他机器的 AI 智能体读取后自动执行部署操作。

---

## 一、前置条件

在开始部署前，请确认：

1. ✅ 本机已安装 **WorkBuddy**（从官网下载）
2. ✅ 已拥有 Gitee 仓库的 SSH 访问权限
3. ✅ macOS 版本 ≥ 14.0（推荐 macOS 25+）

---

## 二、部署步骤（AI 请按顺序执行）

### 步骤 1：克隆仓库

```bash
cd ~
git clone git@gitee.com:babycalf/mac-agent-os.git workbuddy-agent-os/agent-sync
cd workbuddy-agent-os/agent-sync
```

### 步骤 2：一键部署

```bash
bash 00_bootstrap/deploy.sh
```

此脚本会自动完成：
- 设置 `$AGENT_SYNC` / `$AGENT_LOCAL` 环境变量并写入 `.zshrc`
- 创建 `agent-local/` 目录结构
- 创建 `agent-local/config.yaml` 本机配置
- 检查 Python 和依赖

### 步骤 3：使环境变量生效

```bash
source ~/.zshrc
```

### 步骤 4：验证安装

```bash
# 验证路径
echo "AGENT_SYNC=$AGENT_SYNC"
echo "AGENT_LOCAL=$AGENT_LOCAL"

# 验证 Python
$AGENT_SYNC/00_bootstrap/init.sh
```

---

## 三、Tailscale 远程连接配置（需手动，每台机器执行一次）

Tailscale 用于多机器之间的安全通信，让 `mc remote exec` 可以跨局域网执行命令。

### 3.1 安装 Tailscale

```bash
# 方式一：官网下载安装
open https://tailscale.com/download

# 方式二：Homebrew 安装（如已安装 Homebrew）
brew install --cask tailscale
```

### 3.2 启动并登录

安装完成后：
1. 打开 Tailscale 应用（或在终端执行 `open -a Tailscale`）
2. 点击 **登录**（Sign in）
3. 使用 Google / Apple / GitHub 账号登录（任意一个，所有机器用同一账号）
4. 登录成功后，终端执行 `tailscale status` 验证

### 3.3 验证连接

在所有机器都安装并登录 Tailscale 后：

```bash
# 查看所有已连接的机器
tailscale status

# 应该看到类似输出：
# 100.x.x.x    chengzigedeAir    chengzigedeAir   -
# 100.x.x.x    5kechengdeAir     5kechengdeAir   -
# 100.x.x.x    7kecheng          7kecheng        -
```

### 3.4 （可选）配置 SSH 通过 Tailscale

每台机器执行一次：

```bash
sudo systemsetup -setremotelogin on
```

然后任意机器可以用 Tailscale IP SSH 连接：

```bash
ssh chengzige@100.x.x.x
```

---

## 四、验证完整部署

### 4.1 验证路径系统

```bash
# 应该看到非空输出
ls $AGENT_SYNC/ORACLE.yaml
ls $AGENT_LOCAL/config.yaml
```

### 4.2 验证跨机通信

```bash
# 查看所有机器在线状态
tailscale status

# 测试 mc remote
cd $AGENT_SYNC/05_tools/07_matrix/scripts
python3 -m mc remote list
```

### 4.3 验证养号系统

```bash
cd $AGENT_SYNC/05_tools/07_matrix/scripts
python3 -m mc status all
```

---

## 五、日常同步

### 5.1 每日同步（自动）

guardd 守护进程每 15 分钟自动执行 `git pull` 同步最新配置。

### 5.2 手动同步

```bash
cd $AGENT_SYNC && git pull
```

### 5.3 本机有改动时（改配置后）

```bash
cd $AGENT_SYNC && git add . && git commit -m "改动说明" && git push
```

---

## 六、常见问题

### Q: `deploy.sh` 找不到 Python 怎么办？
A: 先安装 WorkBuddy，它会自动安装 Python 3.13。安装后重试。

### Q: `tailscale status` 看不到其他机器？
A: 确保所有机器都已登录同一个 Tailscale 账号，且都处于在线状态。

### Q: 如何确认部署成功？
A: 运行 `echo $AGENT_SYNC` 应有输出，`ls $AGENT_SYNC/ORACLE.yaml` 文件应存在。

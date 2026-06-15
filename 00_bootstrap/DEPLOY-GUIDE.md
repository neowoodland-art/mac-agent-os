# AgentOS 新机器部署指南

> 版本: v2.0 | 最后更新: 2026-06-15
> 本文件供 AI 智能体读取后自动执行部署。

---

## 架构说明

### 与旧版部署的关系

| 旧版 (v1.0) | 新版 (v2.0) | 关系 |
|:------------|:------------|:------|
| `init.sh` | 保留，增加代码签名检测 | 扩展 |
| `deploy.sh` | 保留，增加步骤 | 扩展 |
| `setup_env.sh` | 保留 | 不变 |
| — | `requirements.txt` | **新增**：版本锁定 |
| — | Python 重签步骤 | **新增**：解决代码签名问题 |

**旧版部署方案仍然可用**，v2.0 是在其基础上增加了 2 个新步骤：
1. 检测 WorkBuddy 管理的 Python 是否有代码签名问题 → 自动修复
2. 从 `requirements.txt` 安装锁定版本的核心依赖

### 联邦系统 CLI

底层 CLI 是 `mc`（`05_tools/07_matrix/mc`），它统一管理养号、采集、远程执行等功能。未来 AgentOS 系统级的 CLI 可以在此基础上扩展，但目前 `mc` 已经覆盖了所有核心操作。

---

## 一、前置条件

1. ✅ 本机已安装 **WorkBuddy**（从官网下载）
2. ✅ 已拥有 Gitee 仓库的 SSH 访问权限
3. ✅ macOS 版本 ≥ 14.0
4. ✅ **Tailscale** 已安装并登录（跨局域网通信用）
5. ✅ **远程登录**已开启：系统设置 → 通用 → 共享 → 远程登录

---

## 二、部署步骤（AI 请按顺序执行）

### 步骤 1：克隆仓库

```bash
cd ~
git clone git@gitee.com:babycalf/mac-agent-os.git workbuddy-agent-os/agent-sync
```

### 步骤 2：运行部署脚本

```bash
cd ~/workbuddy-agent-os/agent-sync
bash 00_bootstrap/deploy.sh
```

`deploy.sh` 会自动：
- 设置环境变量 `AGENT_SYNC` / `AGENT_LOCAL` 并写入 `.zshrc`
- 创建 `agent-local/` 目录结构
- 创建 `agent-local/config.yaml` 默认配置
- 检测 Tailscale 状态

### 步骤 3：修复 Python 代码签名（新增）

WorkBuddy 管理的 Python 二进制被腾讯签名，带有 Team ID，导致 orjson 等 `.so` 文件无法加载。需要移除签名：

```bash
PYTHON_BIN="$HOME/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
codesign -f -s - "$PYTHON_BIN"
```

验证修复：
```bash
"$PYTHON_BIN" -c "import orjson; print(orjson.__version__)"
```

预期输出：`3.11.9`

### 步骤 4：安装核心依赖（新增）

```bash
cd ~/workbuddy-agent-os/agent-sync
pip install -r requirements.txt
```

### 步骤 5：验证环境

```bash
bash 00_bootstrap/fleet_reconcile.sh
```

所有检查项应为绿色 ✅。如果红色 ❌，请根据提示修复。

### 步骤 6：启动 Dashboard

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard
nohup python3 run.py 9988 > /dev/null 2>&1 &
```

---

## 三、新机器加入联邦集群

上述步骤完成后，通知主控机器（chengzigedeAir）的管理员，将新机器信息加入 `ORACLE.yaml`：

```yaml
machines:
  新机器名:
    hostname: 新机器名
    tailscale_host: 新机器tailscale名
    tailscale_ip: 100.x.x.x
    ssh_user: 用户名
    uid_prefix: 新机器的 uid 前8位
    role: worker
    os: macOS arm64
```

然后在本机执行同步：
```bash
bash 00_bootstrap/fleet_sync.sh
```

---

## 四、已知问题与处理

### 1. 登录进程卡死

`mc account login` 命令在 Cookie 过期或需要扫码时，会打开浏览器等待用户操作，不会自动超时退出。如果调度器连续 spawn 多个登录命令且无人操作，会积累大量僵尸进程。

**预防**: 启动养号前先验证账号登录状态：
```bash
python3 -m mc status all | grep -i "login"
```

**处理**: 如果已累积僵尸进程，手动 kill：
```bash
pkill -f "mc account login"
```

### 2. Python 代码签名问题复发

如果 WorkBuddy 升级后重新安装了 Python，代码签名可能会恢复。重新执行步骤 3 即可。

### 3. 包版本不一致

三台机器从 `requirements.txt` 安装即可对齐：
```bash
pip install -r requirements.txt --force-reinstall
```

---

## 五、完整部署流程（速查）

```bash
# 新机器部署（6步，约10分钟）
git clone git@gitee.com:babycalf/mac-agent-os.git ~/workbuddy-agent-os/agent-sync
cd ~/workbuddy-agent-os/agent-sync
bash 00_bootstrap/deploy.sh
source ~/.zshrc
codesign -f -s - $HOME/.workbuddy/binaries/python/versions/3.13.12/bin/python3
pip install -r requirements.txt
bash 00_bootstrap/fleet_reconcile.sh
```

---

## 六、联邦常用操作

```bash
# 一键同步所有机器
bash 00_bootstrap/fleet_sync.sh

# 单机对账检查
bash 00_bootstrap/fleet_reconcile.sh

# 远程执行命令
python3 -m mc remote exec 机器名 "命令" --via ssh

# 查看所有机器状态
python3 -m mc remote status
```

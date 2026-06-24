# guardd v2.3.0 — 联邦守护进程 (WPRA v2.0)

> **架构**: WPRA v2.0 — 每台机器只写自己的命名空间，永不冲突
> **版本**: 2.3.0 | **更新**: 2026-05-31
> 适用: 所有 AgentOS 联邦机器

---

## 架构变化 (v2.3.0 关键升级)

v2.3.0 从 `git add -A` 切换到 **WPRA (Write Partitioned, Read Aggregated)** 模型：

| 旧架构 (≤2.2.x) | 新架构 (≥2.3.0) |
|:-----------------|:-----------------|
| `git add -A` 全量提交 → 冲突 | `git add <本机文件>` → 精确提交 |
| 全员写 `_registry.json` → 覆盖冲突 | guardd 不写聚合文件，只写自己的命名空间 |
| 单文件 `accounts_registry.yaml` | 每台机器 `machines/{uid}/accounts.yaml` |
| 心跳写到 `status/live/` | 同时写到 `machines/{uid}/heartbeat.json` |

**每台机器只操作自己的命名空间：**
```
machines/{MACHINE_UID}/
├── MACHINE.yaml               ← 身份声明（首次写入，终身只读）
├── heartbeat.json              ← 心跳（含 file_version + updated_at）
└── events/{date}.jsonl         ← 事件日志（append-only）
```

**不再由 guardd 写入的文件**（已移交给 Dashboard 单实例管理）：
- `status/live/_registry.json` — 安全删除，无冲突风险

---

## 前置条件

- 本机能访问 Gitee (git@gitee.com:babycalf/mac-agent-os.git)
- 已配置 SSH 密钥 (有推送权限)
- Python 3 可用

---

## 安装步骤

### 1. 克隆/拉取仓库

```bash
# 首次 (如果还没有仓库)
git clone git@gitee.com:babycalf/mac-agent-os.git ~/workbuddy-agent-os/agent-sync

# 已有仓库
cd ~/workbuddy-agent-os/agent-sync && git pull
```

### 2. 创建本地目录

```bash
mkdir -p ~/workbuddy-agent-os/agent-local/identity
mkdir -p ~/workbuddy-agent-os/agent-local/runtime/guardd
```

### 3. 首次运行测试

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/00_setup/guardd
python3 guardd.py --once
```

如果输出 `心跳已上报` 表示成功。此时:
- 本机 UID 已生成 → `agent-local/identity/machine_uid`
- 本机 hostname 已缓存 → `agent-local/identity/cached_hostname`
- 心跳已写入 (旧) → `cross_machine/status/live/{UID}.json`
- 心跳已写入 (新) → `cross_machine/machines/{UID}/heartbeat.json` ✅ WPRA v2.0
- 身份声明已创建 → `cross_machine/machines/{UID}/MACHINE.yaml`
- 数据已推送到 Git (精确 add，非 `-A`)

### 4. 验证 Dashboard

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard
python3 run.py 9988
```

浏览器打开 `http://本机IP:9988` → 看到所有机器状态

### 5. 配置自动启动 (macOS launchd)

创建 plist 文件:

```bash
cat > ~/Library/LaunchAgents/com.agentos.guardd.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentos.guardd</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/$(whoami)/workbuddy-agent-os/agent-sync/05_tools/00_setup/guardd/guardd.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/$(whoami)/workbuddy-agent-os/agent-sync</string>
    <key>RunAtLoad</key>
    <true/>
    <key>StartInterval</key>
    <integer>300</integer>
    <key>StandardOutPath</key>
    <string>/Users/$(whoami)/workbuddy-agent-os/agent-local/runtime/guardd/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/$(whoami)/workbuddy-agent-os/agent-local/runtime/guardd/stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

# 加载启动
launchctl load ~/Library/LaunchAgents/com.agentos.guardd.plist
```

### 6. 配置 Dashboard 自动启动

```bash
cat > ~/Library/LaunchAgents/com.agentos.dashboard.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentos.dashboard</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/$(whoami)/workbuddy-agent-os/agent-sync/05_tools/10_dashboard/run.py</string>
        <string>9988</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/$(whoami)/workbuddy-agent-os/agent-sync/05_tools/10_dashboard</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/$(whoami)/workbuddy-agent-os/agent-local/runtime/guardd/dashboard_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/$(whoami)/workbuddy-agent-os/agent-local/runtime/guardd/dashboard_stderr.log</string>
</dict>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.agentos.dashboard.plist
```

---

## 版本管理

**版本文件**: `cross_machine/guardd-required-version.txt`

guardd 每次启动时会检查版本号。如果当前版本低于要求版本:
1. 自动执行 `git pull` 拉取最新代码
2. 提示重启

**如果版本不匹配, 手动更新**:
```bash
cd ~/workbuddy-agent-os/agent-sync && git pull
# 然后重启 guardd
launchctl unload ~/Library/LaunchAgents/com.agentos.guardd.plist
launchctl load ~/Library/LaunchAgents/com.agentos.guardd.plist
```

---

## 常见问题

| 问题 | 解决方法 |
|------|---------|
| Git push 权限不足 | 检查 SSH key 是否添加到 Gitee |
| 启动报错 | 检查 stdout.log/stderr.log |
| Dashboard 看不到其他机器 | 点击左侧 **[🔄 同步]** 执行 git pull |
| 磁盘占用 | `agent-local/runtime/guardd/` 下的日志会自动轮转 |

# guardd v2.0.0 — 联邦守护进程部署指南

> 适用: Redmi-12C / 5kecheng / 7kechengdeAir / 任何新加入的机器
> 所有机器使用同一版本, 数据通过 Git 同步, 无需机器间直连

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
- 心跳已写入 → `cross_machine/status/live/{UID}.json`
- 数据已推送到 Git

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

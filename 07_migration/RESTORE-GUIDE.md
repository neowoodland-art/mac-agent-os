# AgentOS 换机还原操作手册

适用版本：AgentOS v2.1.0，agentos CLI v1.0.0

---

## 前置条件（新机上准备好）

- [ ] macOS（或其他系统，安装对应工具）
- [ ] 坚果云客户端已安装，已登录同一账号
- [ ] Python 3.9+ 已安装（macOS 自带）
- [ ] WorkBuddy 已安装
- [ ] oMLX 已安装（如需要本地 LLM）

---

## 方式一：坚果云同步（推荐）

### 1. 配置坚果云同步

```
打开坚果云客户端
  → 确保 ~/workbuddy-agent-os/agent-sync/ 在同步范围内
  → 等待同步完成（首次可能需要几分钟）
```

验证同步完成：
```bash
ls ~/workbuddy-agent-os/agent-sync/02_skills/
# 应该能看到 memory_manager、inbox_refine 等目录

cd ~/workbuddy-agent-os/agent-sync/05_tools/agentos/
sudo chmod +x install.sh
install.sh
export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc
source ~/.zshrc
agentos --version
agentos --help
```


### 2. 运行一键初始化

```bash
# agentos CLI 已包含在 agent-sync 里，直接用 Python 执行：
PY=~/.workbuddy/binaries/python/envs/agent-os/bin/python3

# 如果没有 WorkBuddy 管理的 Python，用系统 Python：
if [ ! -f "$PY" ]; then PY=python3; fi

cd ~/workbuddy-agent-os/agent-sync/05_tools/00_setup
$PY -c "
import sys
sys.path.insert(0, '.')
from agentos.main import main
sys.argv = ['agentos', 'init']
main()
"
```

### 3. 安装 agentos CLI 到 PATH

```bash
bash ~/workbuddy-agent-os/agent-sync/05_tools/00_setup/agentos/install.sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 4. 如果有旧机备份，还原本地数据

```bash
# 从旧机拷贝的备份文件
agentos restore /path/to/backup/agentos_local_*.tar.gz
```

### 5. 重启 WorkBuddy

关闭并重新打开 WorkBuddy，检查：
- 模型列表中出现 DeepSeek-V4-Pro
- MCP 服务器状态正常
- 技能列表中包含所有 AgentOS 技能

### 6. 验证

```bash
agentos check
```

---

## 方式二：手动拷贝（U盘/tar包）

### 1. 旧机上备份

```bash
# 备份全部（推荐）
cd ~ && tar -czf workbuddy-agent-os-backup.tar.gz workbuddy-agent-os/

# 或只备份 agent-local（agent-sync 通过坚果云同步）
agentos backup --output /path/to/export
```

### 2. 拷贝到新机

```
将 workbuddy-agent-os-backup.tar.gz 拷贝到新机 ~/ 目录
```

### 3. 解压

```bash
cd ~
tar -xzf workbuddy-agent-os-backup.tar.gz
```

### 4. 运行初始化（同上方式一第2步开始）

---

## 常用问题

### Q: 初始化报 "Python not found"
```bash
# macOS 自带 python3
which python3
# 如果没有，安装：brew install python@3.13
```

### Q: 初始化报 "requirements.txt not found"
坚果云同步未完成，等待同步后再执行。

### Q: 自动化任务不生效
```bash
# 启动自动化任务
agentos skill install
agentos sync
# 重启 WorkBuddy
```

### Q: MCP 服务器报错
```bash
# 检查并重新部署 MCP 配置
agentos sync
```

---

## 换机后首次使用清单

```
[ ] agentos check 全部通过
[ ] WorkBuddy 能识别所有技能（对话中说"技能列表"）
[ ] 自动化任务显示 ACTIVE 状态
[ ] oMLX 正常运行（如需要）
[ ] Obsidian 以 agent-sync/03_knowledge/ 为 Vault
```

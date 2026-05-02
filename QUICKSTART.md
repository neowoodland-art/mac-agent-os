# AgentOS 5 分钟快速上手

## 前置条件

确保已安装：
- ✅ **WorkBuddy 桌面客户端**（[codebuddy.cn](https://www.codebuddy.cn) 下载）— 必需
- ✅ **坚果云客户端**（[jianguoyun.com](https://www.jianguoyun.com) 下载）— 跨机同步需要
- ⬜ **Obsidian**（[obsidian.md](https://obsidian.md) 下载）— 推荐，浏览知识库用

> Python 和 Node.js 由 WorkBuddy 自动管理，**不需要手动安装**。

> 详细依赖列表见 [REQUIREMENTS.md](./REQUIREMENTS.md)

## 步骤 1：初始化

```bash
cd ~/workbuddy-agent-os/agent-sync/00_bootstrap
bash init.sh
```

脚本会自动：
- 创建所有目录结构
- 安装 Python 依赖（到 `~/.workbuddy/binaries/python/envs/agent-os/`）
- 检测操作系统并填充设备信息
- 初始化记忆体文件（L1 索引 + L2 facts.db）

## 步骤 2：部署核心配置

```bash
bash apply-config.sh
```

将 `01_core/` 下的 SOUL.md、IDENTITY.md、USER.md 部署到 `~/.workbuddy/`。

## 步骤 3：导入技能

```bash
bash import_skills.sh
```

将 `02_skills/` 下的自定义技能注册到 WorkBuddy。

## 步骤 4：冷启动记忆体

```bash
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 \
  ~/workbuddy-agent-os/agent-sync/02_skills/memory_manager/bootstrap_from_memory.py \
  --root ~/workbuddy-agent-os/agent-sync
```

将已有的工作记忆（MEMORY.md + 工作日志 + 系统画像）导入 L1/L2 记忆体。

> 此步骤仅需首次运行，之后每日凌晨自动提炼。

## 步骤 5：配置坚果云同步

当前坚果云同步路径：`~/NutstoreCloudBridge/`

**方式 A（推荐）**：移动到坚果云同步目录
```bash
mv ~/workbuddy-agent-os/agent-sync ~/NutstoreCloudBridge/agent-os
```

**方式 B**：在坚果云客户端中添加 `~/workbuddy-agent-os/agent-sync/` 为自定义同步文件夹

> ⚠️ 移动后需更新 WorkBuddy 自动化中的路径。

## 步骤 6：打开 Obsidian 知识库（可选）

1. 下载安装 [Obsidian](https://obsidian.md)
2. 启动后选择"打开文件夹"
3. 选择 `~/workbuddy-agent-os/agent-sync/03_knowledge/`
4. 建议安装 Dataview 插件（用于时间线视图）

## 步骤 7：重启 WorkBuddy

重启 WorkBuddy 客户端，新配置生效。

## 验证

在 WorkBuddy 中开启新对话，检查：
- AI 是否读取了 SOUL.md 中的约束
- AI 是否知道知识库和记忆体的路径
- AI 是否遵循了"去文学化"的输出要求

验证记忆系统：
```bash
# 查看 L2 事实库
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 -c "
import sqlite3
conn = sqlite3.connect('$HOME/agent-os/04_memory/long_term/facts.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM facts')
print(f'L2 事实数: {c.fetchone()[0]}')
conn.close()
"

# 查看 L1 索引
cat ~/workbuddy-agent-os/agent-sync/04_memory/vector_db/keyword_index.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'L1 索引条目: {len(data[\"entries\"])}')
"
```

---

🎉 **完成！** 你的 AgentOS 已就绪。每日凌晨 2:00 将自动提炼前一天的工作记忆。

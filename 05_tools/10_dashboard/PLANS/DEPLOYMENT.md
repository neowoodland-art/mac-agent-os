# 多机部署与同步更新指南

> 版本: 1.1.0 | 最后更新: 2026-05-16
> 适用: AgentOS 联邦架构下所有主机

---

## 更新流程概览

```
本机 (Redmi-12C)                其他主机 (Mac mini / …)
┌──────────────────┐           ┌──────────────────┐
│ git add + commit  │           │                    │
│ git push          │──Gitee──▶│ git pull           │
│ (本机已就绪)       │           │ 停止旧服务          │
│                   │           │ 启动新服务          │
└──────────────────┘           │ (完成更新)          │
                                └──────────────────┘
```

---

## 一、本机提交（已完成）

变更清单：

| 文件 | 类型 | 说明 |
|:----|:----:|:-----|
| `05_tools/09_ave/scripts/main.py` | 修改 | dashboard 命令重定向到 `10_dashboard/` |
| `05_tools/09_ave/scripts/lib/dashboard.py` | 修改 | Python 3.9 兼容修复 (`from __future__ import annotations`) |
| `05_tools/09_ave/scripts/dashboard/app.py` | 删除 | 迁出到 `10_dashboard/` |
| `05_tools/09_ave/scripts/dashboard/static/index.html` | 删除 | 迁出到 `10_dashboard/` |
| `05_tools/10_dashboard/` | 新增 | 系统级监控面板（完整模块） |
| `03_knowledge/versions.json` | 新增 | guardd 版本跟踪清单 |
| `10_dashboard/app.py` | 修改 | v1.1.0 新增 `/api/machines` 联邦机器状态接口 |
| `10_dashboard/static/index.html` | 修改 | 新增「机器状态」面板（含在线/离线/磁盘/CPU） |
| `requirements.txt` | 修改 | 新增 fastapi / uvicorn 依赖 |
| `05_tools/09_ave/scripts/composer/hybrid.py` | 新增 | Sprint 2 口播+卡点融合 |
| `05_tools/09_ave/scripts/composer/speed_ramp.py` | 新增 | Sprint 2 变速卡点引擎 |
| `05_tools/09_ave/scripts/asset_manager/` | 新增 | 素材资产管理 |
| `05_tools/09_ave/scripts/story_director/` | 新增 | 故事导演模块 |

---

## 二、其他主机同步步骤

在 **每台** 需要更新的主机上按顺序执行：

### 步骤 1：同步代码

```bash
cd ~/workbuddy-agent-os/agent-sync
git pull
```

预期结果：
- `05_tools/10_dashboard/` 目录出现（含 app.py / run.py / plugins/ 等）
- `05_tools/09_ave/scripts/dashboard/` 目录消失（已被删除）
- `05_tools/09_ave/scripts/main.py` 更新（dashboard 命令）
- `05_tools/09_ave/scripts/lib/dashboard.py` 更新（Python 3.9 修复）
- `03_knowledge/versions.json` 出现（版本跟踪）
- `05_tools/10_dashboard/static/index.html` 新增「机器状态」导航项
- `requirements.txt` 新增 fastapi / uvicorn（需重新安装依赖）

### 步骤 2：检查旧 Dashboard 进程（如已启动过）

```bash
ps aux | grep uvicorn | grep -v grep
```

如果有输出，说明旧 Dashboard 仍在运行，需要停止并重启。

### 步骤 3：停止旧服务

```bash
# 找到旧进程 PID（第二列数字）
ps aux | grep uvicorn | grep -v grep | awk '{print $2}' | xargs kill
```

> ⚠️ 旧 Dashboard 的路径 `09_ave/scripts/dashboard/` 已被删除，
> 如果不停止，进程会报 FileNotFoundError。

### 步骤 4：启动新 Dashboard（使用 managed Python 3.13）

```bash
# 推荐使用 managed Python venv（避免 Python 3.9 兼容问题）
~/.workbuddy/binaries/python/envs/agent-os/bin/python \
  ~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard/run.py
```

或者简写为：

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard
~/.workbuddy/binaries/python/envs/agent-os/bin/python run.py
```

验证启动：

```bash
curl http://localhost:9988/api/health
# 预期: {"status":"ok","version":"1.0.0","plugins":{"ave":"available"}}

curl http://localhost:9988/api/machines
# 预期: {"machhes":[ ... ],"total":N} 显示联邦内所有主机状态
```

### 步骤 5：验证 guardd 正常运行（无需重启）

```bash
cat ~/workbuddy-agent-os/agent-local/runtime/guardd/last_run.json
# 确认所有 7 模块状态为 "ok"
```

guardd 本身未变化，无需重启。它会自动发现 `versions.json`，检测到 version 变更后写入事件。

---

## 三、启动方式参考（Dashboard）

新 Dashboard 支持三种启动方式：

```bash
# 方式 1: 通过 AVE 入口（推荐，自动处理路径）
cd ~/workbuddy-agent-os/agent-sync/05_tools/09_ave/scripts
~/.workbuddy/binaries/python/envs/agent-os/bin/python main.py dashboard

# 方式 2: 独立启动
cd ~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard
~/.workbuddy/binaries/python/envs/agent-os/bin/python run.py

# 方式 3: uvicorn 开发模式
cd ~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard
~/.workbuddy/binaries/python/envs/agent-os/bin/uvicorn app:app --reload --port 9988
```

> ⚠️ **注意 Python 版本**：系统默认 `python3` 为 3.9.6，不支持 `X | Y` 类型注解语法。
> **必须**使用 managed Python 3.13.12 venv 路径，否则会报 TypeError。

---

## 四、故障排查

| 症状 | 原因 | 解决 |
|:----|:----|:-----|
| `TypeError: unsupported operand type(s) for |` | 使用系统 Python 3.9 运行 | 改用 `~/.workbuddy/binaries/python/envs/agent-os/bin/python` |
| `ModuleNotFoundError: No module named 'app'` | uvicorn 找不到 `10_dashboard/app.py` | 确保 CWD 在 `10_dashboard/` 目录下 |
| `curl: (7) Connection refused` | Dashboard 未启动 | 先执行启动命令 |
| `FileNotFoundError: dashboard/app.py` | 旧进程仍在运行 | kill 旧 uvicorn 进程 |
| guardd 未检测到版本更新 | `versions.json` 不存在或格式错误 | 检查 `03_knowledge/versions.json` 是否存在且 JSON 有效 |

---

## 五、后续模块接入

当前仪表盘仅含 AVE 插件。后续模块（Matrix / guardd）接入方法：

```python
# 1. 创建 10_dashboard/plugins/matrix.py
# 2. 实现 DashboardPlugin 基类
# 3. 在 app.py 的 _register_plugins() 中添加一行
```

详见 `10_dashboard/PLANS/ARCHITECTURE.md`。

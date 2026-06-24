# guardd — AgentOS 守护进程

## 职责

guardd 是每台机器上运行的**后台守护进程**，负责周期性的系统维护和状态上报。不做命令分发，不做养号执行——那些是 `mc run` 的事。

## 工作方式

由 `launchd`（macOS 的服务管理器）管理，开机自动启动，崩溃自动重启。

```
launchd (PID 1)
  └── guardd.py (Python 进程)
        ├── 每 300 秒（5分钟）运行一次完整周期
        └── 每次运行按顺序执行：
              1. module_heartbeat() — 状态心跳
              2. module_identity() — 身份同步
              3. module_collector() — 信息采集
```

## 3 个核心模块

### 1. `module_heartbeat()` — 状态心跳

**做什么**：向主控机报告本机在线状态

**写入文件**：
```
cross_machine/status/live/{machine_uid}.json
  ├── uid / hostname / ip
  ├── last_seen  (时间戳)
  └── version, mac 等元数据
```

**频率**：每 300 秒（5 分钟）

**作用**：Dashboard 的机器状态栏通过此文件判断各机器是否在线。

### 2. `module_identity()` — 身份同步

**做什么**：确保本机的身份声明与主控机对齐

**写入文件**：
```
cross_machine/machines/{machine_uid}/accounts.yaml
  └── 本机管理的所有账号声明
```

**频率**：每 300 秒

**作用**：让主控机知道"这台机器管理哪些账号"。

### 3. `module_collector()` — 信息采集

**做什么**：对本机的每个已登录账号执行主页信息读取

**调用的命令**：
```bash
mc run --accounts={id} --blueprints={douyin_read_profile|xiaohongshu_read_profile} --rounds=1
```

**写入文件**：
```
agent-local/tools/matrix/data/homepage_info.json
  └── 每个账号的主页信息（昵称/粉丝/关注数等）
```

**写完后**：自动调一次 `git add + commit + push`，把采集数据同步到 Git 仓库

**频率**：每 300 秒（但仅在检测到有新登录状态时执行）

## 日志

```
agent-local/runtime/guardd/guardd.log    — 主日志（10MB 轮转，保留 3 份）
agent-local/runtime/guardd/stdout.log    — 标准输出 (launchd 重定向)
agent-local/runtime/guardd/stderr.log    — 错误输出 (launchd 重定向)
```

日志轮转使用 `RotatingFileHandler`，单文件 10MB，保留 3 个备份。

## 安装与状态管理

```bash
# 安装/更新 plist
cd 05_tools/00_setup/guardd && bash install_guardd.sh

# 查看运行状态
launchctl print gui/$(id -u)/com.agentos.guardd | grep state

# 查看日志
tail -f ~/workbuddy-agent-os/agent-local/runtime/guardd/guardd.log

# 手动运行一次完整的 guardd 周期（测试用）
cd 05_tools/00_setup/guardd
../../10_dashboard/venv/bin/python3 guardd.py --once

# 停止（不让 launchd 重启）
launchctl bootout gui/$(id -u)/com.agentos.guardd
```

## 身份解析

guardd 使用三级降级解析机器注册名：

1. `cached_hostname` 文件 — 写入固定注册名，防 IP 漂移
2. IP 映射表 — LAN IP → 注册名（硬编码）
3. Registry 查询 — 通过 machine_uid 匹配
4. `os.uname().nodename` — 最终兜底

## 依赖

- Python 3.10+
- `requests`（仅在 heartbeat 上报到主控机 API 时需要）
- 项目 `agent-sync` 目录（`git pull` 使用）

## 与 Dashboard 的关系

```
Dashboard (uvicorn)
  └── 通过 API 查询 guardd 的状态文件
  └── 通过 SSH 读取其他机器的采集数据

guardd (launchd)
  └── 每 300 秒写入状态/身份/采集数据到文件系统
  └── 不直接与 Dashboard 通信
```

两者**不直接通信**，通过文件系统交换数据。guardd 负责写，Dashboard 负责读。即使 Dashboard 不运行，guardd 仍正常工作。

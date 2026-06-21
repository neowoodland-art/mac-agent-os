---
type: concept
domain: system
nature: architecture
tags: [agentos, v2.1, federated, multi-machine, architecture, guardd]
status: active
created: 2026-05-15
updated: 2026-05-15
version: 1.0.0
---

# 联邦式多机协同架构（V2.1）

> AgentOS 支持多台 Mac 组成**智能体联邦**，通过三层架构实现数据隔离 + 轻量协同。

## 架构总览

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  machine a   │     │  machine b   │     │  machine c   │
│  (redmi-12c) │     │ (mac-mini)   │     │ (macbook air)│
│              │     │              │     │              │
│  agent-local │     │  agent-local │     │  agent-local │
│  (私钥/记忆/  │     │  (私钥/记忆/  │     │  (私钥/记忆/  │
│   重资产)     │     │   重资产)     │     │   重资产)     │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └──────────┬─────────┴─────────┬──────────┘
                  │    agent-sync/    │
                  │  (NutSync 同步)   │
                  └──────────────────┘
                   events/  status/  tasks/
                   encrypted/  knowledge/
                  ┌──────────────────┐
                  │  直传层 (SSH/AirDrop) │
                  └──────────────────┘
```

## 三层数据架构

| 层 | 路径 | 内容 | 同步方式 |
|----|------|------|---------|
| **agent-local/** | 本机专属 | 私钥 · API Key · 素材库 · 本地记忆 · 提交箱 · 守护进程日志 | ❌ 永不共享 |
| **agent-sync/** | 共享目录 | 配置 · 知识库 · 技能 · 记忆摘要 · 工具脚本 | NutSync 双向同步 |
| **直传层** | 点对点 | 大文件传输（视频/素材等） | SSH rsync / AirDrop |

## 七大协同子系统

| # | 子系统 | 说明 | 关键文件 | 状态 |
|---|--------|------|---------|------|
| ① | **状态机** | 每台 5-10 分钟上报心跳，15 分钟无心跳判离线 | `cross_machine/status/{host}/heartbeat.json` | ✅ 已实现 |
| ② | **事件总线** | 跨机事件日志（任务完成/错误/更新等 10 种类型） | `cross_machine/events/{date}/*.json` | ✅ 已实现 |
| ③ | **任务协作** | 跨机任务请求/响应（异步文件机制） | `cross_machine/tasks/` | ✅ 已实现 |
| ④ | **加密通讯** | RSA-4096 密钥对，公钥注册/私钥本地 | `cross_machine/encrypted/` | ✅ 已实现 |
| ⑤ | **知识同步** | 双向：拉取知识库 + 推送本地新知识到收件匣 | `03_knowledge/01_submissions/` | ✅ 已实现 |
| ⑥ | **自动升级** | 版本清单驱动，非破坏性更新自动执行 | `cross_machine/knowledge/versions.json` | ✅ 已实现 |
| ⑦ | **文件直传** | 同局域网 SSH rsync / AirDrop 直传大文件 | `guardd/modules/transfer.py` | ✅ 已实现 |

## 安全边界

| 内容 | 存储位置 | 安全性 |
|------|---------|--------|
| 公钥 | `cross_machine/registry/*_pub.pem` | ✅ 公开安全 |
| 加密消息 | `cross_machine/encrypted/` | ✅ 无私钥不可读 |
| 私钥/API Key | `agent-local/identity/secrets/` | ✅ 永不共享 |
| 记忆数据 | `agent-local/memory/` | ✅ 每机独立 |
| 重资产 | `agent-local/tools/*/` | ✅ 不跨机同步 |

## 守护进程 guardd

每台机器运行 `guardd` 守护进程，负责 7 个子系统的自动化执行。

- **安装**: launchd 管理，300 秒周期
- **引擎**: 纯规则引擎，0 token 消耗
- **路径**: `05_tools/00_setup/guardd/guardd.py`
- **日志**: `agent-local/runtime/guardd/`

### guardd 9 模块

| 模块 | 职责 |
|------|------|
| `heartbeat` | 状态上报（CPU/内存/任务）写入 heartbeat.json + 推送 Dashboard |
| `dashboard_sync` | 将本机 Dashboard 插件数据写入跨机共享目录 |
| `task_worker` | 扫描本机任务并执行 |
| `upgrade_checker` | 版本清单比对，自动/手动升级 |
| `memory_triage` | 过滤本地记忆，推送通用内容到提交箱 |
| `knowledge_sync` | 检测知识库变更 + 推送本地提交箱到远程 |
| `encrypted_channel` | 解密加密消息到本地 |
| `sync_checker` | 自动 git pull 拉取远程变更 |
| `cleanup` | 清理 30 天以上的旧事件和已完成任务 |

## 相关文件

- `docs/DASHBOARD_DATA_LAYER_V2.md` — 联邦式数据架构完整设计
- `01_core/MAINTENANCE_GUIDE.md` — guardd 运维操作手册
- `README.md` — 系统入口（多机联邦章节）
- `CHANGELOG.md` — V2.1 变更记录

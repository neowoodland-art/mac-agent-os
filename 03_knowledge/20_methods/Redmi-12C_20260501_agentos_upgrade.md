---
id: method-20260501-upgrade-engine
title: 统一升级引擎 agentos upgrade
type: method
tags: [系统管理, CLI, 升级, 模块管理]
collected_by: Redmi-12C
created: 2026-05-01
confidence: 0.85
nature: fact

collected: true
collected_date: 2026-05-03---

# agentos upgrade — 统一升级引擎

## 概述
扫描 agent-sync/ 下所有模块，对每个模块执行标准化 4 步升级。替代散落的 install.sh、pip install、git pull 等手动操作。

## 命令
```bash
agentos upgrade                 # 全量升级所有模块
agentos upgrade --module matrix  # 只升级 Matrix（模糊匹配）
agentos upgrade --module 07_matrix  # 只升级 Matrix 工具
agentos upgrade --dry-run       # 预览模式
```

## 执行流程
1. `git pull origin main` — 拉取最新代码
2. 扫描 18 个模块（8 个 skill + 8 个 tool + 2 个其他）
3. 按模块层级执行不同操作
4. 自动注册技能到 WorkBuddy
5. 输出升级报告

## 三层模块管理

| 层级 | 说明 | 模块数 | upgrade 行为 |
|------|------|--------|------------|
| L1 纯代码层 | 无本地依赖，纯脚本 | 17 个 | git pull + 代码同步 |
| L2 本地数据层 | 需本地目录 + 依赖 + 配置 | 1 个（matrix） | install.sh → pip → check |
| L3 系统配置层 | 需选择性更新的配置 | — | 规划中（upgrade --config） |

## Python 环境统一
所有 pip install 操作统一使用 `get_python()` 获取 managed Python 路径：
1. `AGENTOS_PYTHON` 环境变量
2. `~/.workbuddy/binaries/python/envs/agent-os/bin/python3`
3. `~/.workbuddy/binaries/python/versions/3.13.12/bin/python3`
4. `python3`（系统 fallback）

确保多机环境一致。

## 位置
`05_tools/00_setup/agentos/upgrade.py`

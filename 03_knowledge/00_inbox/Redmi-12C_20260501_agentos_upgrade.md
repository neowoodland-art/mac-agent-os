---
title: "统一升级引擎 agentos upgrade"
source_dir: 03_knowledge/20_methods
source_file: Redmi-12C_20260501_agentos_upgrade.md
date: 2026-05-03
collected_date: 2026-05-03
tags: [系统管理, CLI, 升级, 模块管理]
nature: method
domain: general
status: inbox
---

# 统一升级引擎 agentos upgrade

> 来源：03_knowledge/20_methods

# agentos upgrade — 统一升级引擎
## 概述
## 命令
## 执行流程
1. `git pull origin main` — 拉取最新代码
2. 扫描 18 个模块（8 个 skill + 8 个 tool + 2 个其他）
3. 按模块层级执行不同操作
4. 自动注册技能到 WorkBuddy
5. 输出升级报告
## 三层模块管理
## Python 环境统一
1. `AGENTOS_PYTHON` 环境变量
2. `~/.workbuddy/binaries/python/envs/agent-os/bin/python3`
3. `~/.workbuddy/binaries/python/versions/3.13.12/bin/python3`
4. `python3`（系统 fallback）
## 位置

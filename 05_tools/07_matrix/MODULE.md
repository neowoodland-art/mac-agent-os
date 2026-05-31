---
name: matrix
version: "2.1.0"
type: tool
description: 多平台社交账号矩阵养号工具
author: agent-os
last_updated: 2026-05-01
---

# Matrix 养号工具模块

## 模块信息

| 字段 | 值 |
|------|-----|
| 名称 | matrix |
| 版本 | 2.1.0 |
| 类型 | tool |
| 路径 | `05_tools/07_matrix/` |
| 本地数据 | `agent-local/tools/matrix/` |
| 依赖 | patchright, camoufox, PyYAML |

## 模块结构

```
05_tools/07_matrix/          ← 同步目录（Git + 坚果云）
├── MODULE.md                 ← 本文件（模块描述）
├── install.sh                ← 新机部署脚本
├── requirements.txt          ← Python 依赖
├── local.yaml.template       ← 本地配置模板
├── config_template/          ← 账号配置模板
├── scripts/                  ← 核心代码
├── blueprints/               ← 蓝图文件
└── docs/                     ← 标准化文档

agent-local/tools/matrix/    ← 本地数据（每机独立，不同步）
├── config/accounts.yaml      ← 本机账号配置
├── data/cookies/             ← 登录 Cookie
├── data/matrix.db            ← 执行记录
├── profiles/                 ← Chrome Profile（需重新登录）
├── logs/                     ← 运行日志
└── screenshots/             ← 截图
```

## 部署方式

```bash
# 本模块的部署由 agentos upgrade 统一管理
# 如单独执行:
bash install.sh                           # 建目录 + 装依赖 + 生成 local.yaml
pip install -r requirements.txt            # 安装 Python 包
python -m patchright install chromium      # 安装 Playwright Chromium
pip install camoufox && python -m camoufox fetch  # 安装 Camoufox
```

## 升级历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 2.1.0 | 2026-05-01 | 原子化登录模块 auth_manager.py + 稳定性修复 |
| 2.0.0 | 2026-04-30 | Camoufox 集成 + 蓝图引擎升级 |
| 1.0.0 | 2026-04-27 | 初始版本 |

---
name: sync_manager
version: 1.1.0
description: 同步管理技能——知识库备份、导出、迁移（同步由坚果云处理）
triggers:
  - 备份知识库
  - 导出知识库
  - 同步状态
  - backup kb
  - 备份
  - 知识库备份
---

# Sync Manager Skill（同步管理）

## 概述

管理 Obsidian 知识库的备份、导出和迁移。同步功能由坚果云处理，本技能不涉及。

## 核心能力

### 1. 备份知识库
- 将 `03_knowledge/` 全量打包到 `04_memory/memory_backup/`
- 命名：`kb_backup_YYYY-MM-DD_HHmm.tar.gz`

### 2. 导出知识库
- 生成可分发的知识库压缩包
- 可选：只导出特定领域/标签

### 3. 同步状态
- 检查坚果云同步路径 `~/NutstoreCloudBridge/` 的状态
- 报告最近同步时间和文件差异

## 坚果云同步

- 同步路径：`~/NutstoreCloudBridge/`
- 同步方式：坚果云客户端自动同步，非 Git
- 本技能不管理云端同步过程

## 依赖

| 依赖 | 说明 | 状态 |
|---|---|---|
| 坚果云客户端 | 知识库同步 | ✅ 已安装 |
| tar/gzip | 备份打包 | ✅ 系统自带 |

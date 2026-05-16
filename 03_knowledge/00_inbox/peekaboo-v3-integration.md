---
title: "Peekaboo v3 桌面 GUI 自动化"
source_dir: 03_knowledge/40_references
source_file: peekaboo-v3-integration.md
date: 2026-05-16
collected_date: 2026-05-16
tags: [peekaboo, 截图, 桌面自动化, OCR, MCP]
nature: reference
domain: 效率
status: inbox
---

# Peekaboo v3 桌面 GUI 自动化

> 来源：03_knowledge/40_references

# Peekaboo v3 桌面 GUI 自动化

## 基本信息

- 版本: v3.1.2
- 安装: `npm install -g @steipete/peekaboo`
- MCP: `npx -y @steipete/peekaboo mcp --json --log-level error`
- 权限: 屏幕录制 + 辅助功能（macOS）

## 核心能力

- 截图：窗口截图、区域截图、全屏截图
- 操作：点击、输入、拖拽、滚动、快捷键
- 识别：应用列表、窗口列表、UI 控件树

## 使用策略

| 规则 | 值 | 说明 |
|------|----|------|
| 截图冷却 | 5s | 两次截图最小间隔 |
| 单会话上限 | 20次 | 一次对话最大截图数 |
| 缓存 | 30s | 同一应用复用缓存 |
| 优先级 | DOM→API→文本→截图 | 截图是最后手段 |

## 系统集成

- MCP 配置: `01_core/mcp.json`
- 技能: `02_skills/peekaboo_controller/SKILL.md`
- 策略

...（内容已截断，完整内容见源文件）

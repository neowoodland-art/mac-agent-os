---
name: peekaboo_controller
version: 1.0.0
description: Peekaboo v3 GUI 自动化——屏幕视觉识别+鼠标键盘操作
triggers:
  - 截图
  - 屏幕
  - 点击
  - 桌面操作
  - 视觉识别
  - OCR
  - peekaboo
  - 自动化点击
---

# Peekaboo Controller Skill

macOS 桌面 GUI 自动化。像素级视觉识别操控屏幕，不依赖 DOM/系统 API。

## 安装

```bash
npm install -g @steipete/peekaboo       # npm（推荐）
# 验证权限
peekaboo permissions status
```

## MCP 配置

已在 `01_core/mcp.json` 注册。

## 常用命令

```bash
peekaboo image                    # 截图
peekaboo list apps                # 列出应用
peekaboo click "按钮"             # 视觉点击
peekaboo type "文字"              # 输入
peekaboo "打开抖音并搜索毛选"      # 自然语言
```

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
# 验证权限（必须 Granted）
peekaboo permissions status
```

## MCP 配置（已注册 01_core/mcp.json）

```json
"peekaboo": {
  "command": "npx",
  "args": ["-y", "@steipete/peekaboo", "mcp"]
}
```

## 常用命令

```bash
peekaboo image                    # 截图（最前窗口）
peekaboo list apps                # 列出应用
peekaboo click "按钮文字"          # 视觉点击
peekaboo type "输入文字"           # 输入
peekaboo scroll                   # 滚动
peekaboo "自然语言指令"            # 综合调度
```

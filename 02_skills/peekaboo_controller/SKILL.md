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

## MCP 配置（token 优化版）

已在 `01_core/mcp.json` 注册，带 token 节省参数：
```json
"peekaboo": {
  "command": "npx",
  "args": ["-y", "@steipete/peekaboo", "mcp", "--json", "--log-level", "error"]
}
```

- `--json`：输出机器可读 JSON，比默认文本小 60-80%
- `--log-level error`：只输出错误，不输出 info/warning 日志

## 常用命令

```bash
peekaboo image                    # 截图（自动保存）
peekaboo list apps --json         # JSON 格式输出（节省 token）
peekaboo click "按钮"             # 视觉点击
peekaboo type "文字"              # 输入
```

## Token 节省技巧

- 命令后加 `--json`：输出量减少 60-80%
- 截图时指定区域：`peekaboo image --area`，避免全屏大图
- 不需要时关闭 MCP：`peekaboo daemon stop`

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
- 截图时指定区域或窗口，避免全屏大图
- 不需要时关闭 MCP：`peekaboo daemon stop`

## 使用策略（防滥用）

内置 `policy.py` 策略层，自动控制截图频率和用量：

| 规则 | 值 | 说明 |
|------|----|------|
| 截图冷却 | 5 秒 | 两次截图之间至少间隔 5 秒 |
| 单会话上限 | 20 次 | 一次对话最多截 20 张 |
| 缓存有效期 | 30 秒 | 同一应用 30 秒内复用缓存 |
| 优先级顺序 | DOM → API → 文本 → **截图最后** | 截图是最后手段 |

```python
# 使用策略层（推荐）
from policy import screenshot, reset, status

path = screenshot("抖音")          # 带冷却/上限检查
path = screenshot("抖音", force=True)  # 跳过检查（手动确认时用）
reset()                              # 新对话前重置
print(status())                      # 查看用量
```

> **原则**：能用 DOM 不用截图，能用 API 不用浏览器。
> Peekaboo 是做**兜底**的，不是主路径。

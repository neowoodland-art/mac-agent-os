# 05_tools —— 工具脚本目录

存放跨技能使用的公共工具脚本，不作为独立技能，而是给技能和运维使用的底层工具。

## 目录结构

| 目录 | 用途 |
|:-----|:------|
| `00_setup/` | agentos CLI（14 子命令）+ guardd 守护进程（9 模块）+ 多机同步脚本 |
| `01_system/` | 环境检查、诊断、系统健康脚本（12 个） |
| `02_browser/` | [已清空] 浏览器工具已迁移至 07_matrix/ |
| `03_ocr/` | [已清空] OCR 由 Peekaboo MCP 提供 |
| `04_media/` | [已清空] 媒体处理由 FFmpeg + AVE 提供 |
| `05_crawl/` | 爬虫工具（longcat 长期爬虫 + content-inspiration 口播素材采集） |
| `06_mobile/` | [已清空] |
| `07_matrix/` | 矩阵养号系统（mc CLI + Camoufox + 12 个蓝图） |
| `08_trae_agent/` | Trae AI 编程助手集成 |
| `09_ave/` | AVE 视频工厂（文案→合成→渲染全链路） |
| `10_dashboard/` | 系统监控面板（FastAPI + 15 插件 + 前端） |

## 与 02_skills 的区别

- **`02_skills/`**：可被 WorkBuddy 对话触发的技能，有 `SKILL.md` 身份证
- **`05_tools/`**：底层公共工具，被技能调用或手动执行，不暴露给对话

## 调用方式

所有脚本使用 agent-os venv 的 Python 执行：
```bash
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 ~/workbuddy-agent-os/agent-sync/05_tools/01_system/check_automation_env.py
```

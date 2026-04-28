# 05_tools —— 工具脚本目录

存放跨技能使用的公共工具脚本，不作为独立技能，而是给技能和运维使用的底层工具。

## 目录结构

| 目录 | 用途 | 脚本 |
|------|------|------|
| `00_setup/` | 首次安装工具（ffmpeg 静态二进制等） | — |
| `01_system/` | 环境检查、诊断、系统健康脚本 | `check_automation_env.py` `check_facts.py` `test_omlx_embedding.py` |
| `01_system/reports/` | 系统检查报告存档 | — |
| `02_browser/` | Playwright 相关工具 | — |
| `03_ocr/` | OCR 工具 | — |
| `04_media/` | 媒体处理（yt-dlp、ffmpeg 等） | — |
| `05_crawl/` | 爬虫工具（MediaCrawler 等） | — |
| `06_mobile/` | 移动端工具 | — |

## 与 02_skills 的区别

- **`02_skills/`**：可被 WorkBuddy 对话触发的技能，有 `SKILL.md` 身份证
- **`05_tools/`**：底层公共工具，被技能调用或手动执行，不暴露给对话

## 调用方式

所有脚本使用 agent-os venv 的 Python 执行：
```bash
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 ~/agent-os/05_tools/01_system/check_automation_env.py
```

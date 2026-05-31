# 2026-05-14 系统升级：Peekaboo v3 + CloakBrowser 集成

## 升级内容

本机（chengzige）已完成以下升级：

### 1. Peekaboo v3 — 桌面 GUI 自动化

**用途**：屏幕视觉识别 + 鼠标键盘操作（OCR、截图、桌面应用操作）

**安装（每台机器独立执行）**：
```bash
npm install -g @steipete/peekaboo
peekaboo permissions status   # 确认权限已开启
```

**MCP 配置已同步**：`01_core/mcp.json` → `apply-config.sh` 自动部署到本机

**技能文件**：`02_skills/peekaboo_controller/SKILL.md`

### 2. CloakBrowser — 源码级反爬浏览器

**用途**：替换 Playwright/agent-browser，30/30反爬检测通过

**安装（每台机器独立执行）**：
```bash
pip install cloakbrowser
# 首次运行自动下载 ~200MB Chromium 二进制
```

**技能文件**：`02_skills/cloakbrowser_controller/SKILL.md`

### 3. web_crawler 引擎升级

**变更**：高反爬引擎从 Playwright + Stealth 替换为 CloakBrowser

## 本机操作清单

```bash
# 本机（chengzige）已完成：
npm install -g @steipete/peekaboo              ✅
pip install cloakbrowser                        ✅
git commit/push 02_skills/ + 01_core/mcp.json   ✅
```

## 其他机器操作清单

```bash
# 5kecheng / 7kecheng 执行：

# 0. 同步代码
cd ~/workbuddy-agent-os/agent-sync
git pull
bash 00_bootstrap/apply-config.sh   # 部署新 MCP 配置

# 1. 安装 Peekaboo（仅 macOS）
npm install -g @steipete/peekaboo
peekaboo permissions status   # 去系统设置开权限

# 2. 安装 CloakBrowser
pip install cloakbrowser

# 3. 验证
python3 -c "import cloakbrowser; print('CloakBrowser OK')"
peekaboo --version
```

## 不涉及的模块

- **Matrix 养号（Camoufox）**— 不动，已深度适配
- **OpenCLI** — 不变
- **Scrapling/Crawl4AI** — 不变
- **httpx** — 不变

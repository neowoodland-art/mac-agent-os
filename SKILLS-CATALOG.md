# AgentOS 技能清单与部署手册 v2.0

> 最后更新：2026-04-25 | 设备：MacBook Air M1 8GB | 系统：macOS 26.4

---

## 一、快速指令对照表

| 指令 | 技能 | 动作 |
|------|------|------|
| `转笔记` | content_processor → bilinote | 视频→结构化笔记 |
| `摘字幕` | content_processor → bilinote | 仅语音转文字 |
| `视频摘要` | content_processor → bilinote | 提炼核心观点 |
| `视频大纲` | content_processor → bilinote | 层级内容大纲 |
| `剪藏` | content_processor → web-clipper | 网页→Markdown |
| `摘抄` | content_processor → web-clipper | 保存全文 |
| `文章摘要` | content_processor → web-clipper | 3 句话概括 |
| `提炼` | content_processor → web-clipper | 方法论/步骤/结论 |
| `翻译` | content_processor → web-clipper | 翻译成中文 |
| `语音摘要` | content_processor → voice-summary | 语音→核心要点 |
| `转文字` | content_processor → voice-summary | 逐字稿 |
| `采集` | content_processor → social-collector | 小红书/抖音→笔记 |
| `采集摘要` | content_processor → social-collector | 采集+AI总结 |
| `开始收集` | auto_collector | 启动 24h 监控 |
| `停止收集` | auto_collector | 暂停监控 |
| `收集报告` | auto_collector | 今日采集摘要 |
| `记忆更新` | memory_manager | 手动触发记忆提炼 |
| `入库` | kb_manager | 知识入库（→ 00_inbox/） |
| `归集` | collect_to_inbox | 分类目录→收件箱 |
| `收集到收件箱` | collect_to_inbox | 手动触发汇聚 |
| `提纯` | inbox_refine | 收件箱提纯归档 |
| `整理收件箱` | inbox_refine | 手动触发提纯 |
| `抓取` | web_crawler | 网页抓取+反爬 |
| `备份知识库` | sync_manager | 全量备份 |

---

## 二、技能详览

### 1. memory_manager（记忆管理）

| 属性 | 值 |
|------|-----|
| 版本 | 1.1.0 |
| 位置 | `~/agent-os/02_skills/memory_manager/` + `~/.workbuddy/skills/memory_manager/` |
| 触发词 | 记忆更新、每日提炼、整理记忆、记忆检查、查记忆 |
| 核心脚本 | `daily_digest.py`、`bootstrap_from_memory.py`、`memory_cleanup.py`、`agent_memory_init.py` |
| 依赖 | sqlite-utils ✅、sqlite3(标准库) ✅ |

### 2. kb_manager（知识库管理）

| 属性 | 值 |
|------|-----|
| 版本 | 1.1.0 |
| 位置 | `~/agent-os/02_skills/kb_manager/` + `~/.workbuddy/skills/kb_manager/` |
| 触发词 | 入库、保存知识、知识分类、查知识库、ingest、kb |
| 核心脚本 | `kb_ingest.py` |
| 入库目标 | `03_knowledge/00_inbox/`（收件箱，待提纯） |
| 依赖 | trafilatura ✅、chromadb ✅、sqlite-utils ✅ |

### 3. inbox_refine（收件箱提纯）

| 属性 | 值 |
|------|-----|
| 版本 | 1.0.0 |
| 位置 | `~/agent-os/02_skills/inbox_refine/` + `~/.workbuddy/skills/inbox_refine/` |
| 触发词 | 提纯、整理收件箱、归档inbox、inbox refine |
| 核心脚本 | `inbox_refine.py` |
| 自动化 | 每日凌晨 3:00（WorkBuddy automation `agentos-2`） |
| 前置步骤 | collect_to_inbox（每日 2:30 先汇聚到收件箱） |
| 流程 | 00_inbox/ → 分类 → 应用模板 → 写入目标目录 → 更新首页 → 更新 CHANGELOG |
| 依赖 | python3 ✅、file_read/write ✅、oMLX+Qwen3-8B-MLX-4bit ✅（可选） |

### 4. collect_to_inbox（分类目录汇聚收件箱）★ 新增

| 属性 | 值 |
|------|-----|
| 版本 | 1.0.0 |
| 位置 | `~/agent-os/02_skills/collect_to_inbox/` + `~/.workbuddy/skills/collect_to_inbox/` |
| 触发词 | 归集、收集到收件箱、汇聚收件箱、collect inbox |
| 核心脚本 | `collect_to_inbox.py` |
| 自动化 | 每日凌晨 2:30（WorkBuddy automation `agentos-3`） |
| 扫描目录 | 50_resources/视频笔记、50_resources/字幕存档、50_resources/阅读笔记、50_resources/全文存档、50_resources/翻译存档、50_resources/灵感素材、50_resources/语音转写、20_methods/、01_daily/闪念笔记、40_references/ |
| 流程 | 扫描各分类目录 → 提取主要内容 → 生成标准化 MD → 写入 00_inbox/ → 标记原文件已收集 |
| 依赖 | python3 ✅ |

### 5. auto_collector（24h 自动收集）

| 属性 | 值 |
|------|-----|
| 版本 | 1.0.0 |
| 位置 | `~/agent-os/02_skills/auto_collector/` + `~/.workbuddy/skills/auto_collector/` |
| 触发词 | 开始收集、停止收集、收集状态、收集报告、监控 |
| 监控源 | RSS/B站/小红书/抖音/网页 |
| 依赖 | feedparser ✅、schedule ✅、@tikomni/skills ✅、crawl4ai ✅ |
| 待部署 | BiliNote Docker（视频监控） |

### 6. content_processor（统一内容处理）

| 属性 | 值 |
|------|-----|
| 版本 | 1.0.0 |
| 位置 | `~/agent-os/02_skills/content_processor/` + `~/.workbuddy/skills/content_processor/` |
| 触发词 | 转笔记/剪藏/语音摘要/采集/摘抄/提炼/翻译 等 |
| 路由 | → bilinote / web-clipper / voice-summary / social-collector |
| 依赖 | trafilatura ✅、whisper ✅、@tikomni/skills ✅、crawl4ai ✅ |

### 7. web_crawler（网页抓取+反爬）

| 属性 | 值 |
|------|-----|
| 版本 | 1.1.0 |
| 位置 | `~/agent-os/02_skills/web_crawler/` + `~/.workbuddy/skills/web_crawler/` |
| 触发词 | 抓取、爬取、crawl、fetch |
| 引擎 | Scrapling(三模式) + Crawl4AI + Playwright+Stealth |
| 依赖 | scrapling ✅、crawl4ai ✅、playwright ✅、playwright-stealth ✅ |
| 待解决 | Playwright Chromium 浏览器下载（网络问题） |

### 8. sync_manager（同步管理）

| 属性 | 值 |
|------|-----|
| 版本 | 1.1.0 |
| 位置 | `~/agent-os/02_skills/sync_manager/` + `~/.workbuddy/skills/sync_manager/` |
| 触发词 | 备份知识库、导出知识库、同步状态 |
| 同步方式 | 坚果云（`~/NutstoreCloudBridge/`） |
| 依赖 | 坚果云 ✅、tar/gzip(系统自带) ✅ |

### 7. bilinote（视频→结构化笔记）

| 属性 | 值 |
|------|-----|
| 位置 | `~/.workbuddy/skills/bilinote/` |
| 触发词 | 转笔记、摘字幕、视频摘要、视频大纲 |
| 依赖 | BiliNote Docker ⚠️ 待部署 |

### 8. web-clipper（网页→Markdown）

| 属性 | 值 |
|------|-----|
| 位置 | `~/.workbuddy/skills/web-clipper/` |
| 触发词 | 剪藏、摘抄、文章摘要、提炼、翻译 |
| 依赖 | trafilatura ✅ |
| 状态 | ✅ 可用 |

### 9. voice-summary（语音→核心要点）

| 属性 | 值 |
|------|-----|
| 位置 | `~/.workbuddy/skills/voice-summary/` |
| 触发词 | 语音摘要、转文字、闪念笔记 |
| 依赖 | openai-whisper ✅ |
| 状态 | ✅ 文字可用 |

### 10. social-collector（小红书/抖音→笔记）

| 属性 | 值 |
|------|-----|
| 位置 | `~/.workbuddy/skills/social-collector/` |
| 触发词 | 采集、采集摘要 |
| 依赖 | @tikomni/skills ✅ |
| 状态 | ✅ 可用 |

### 11. tikomni-data（跨平台数据引擎）

| 属性 | 值 |
|------|-----|
| 位置 | `~/.workbuddy/skills/tikomni-data/` |
| 触发词 | tikomni、提取数据 |
| 依赖 | @tikomni/skills ✅ |
| 状态 | ✅ 可用 |

### 12. obsidian（Obsidian Vault 操作）

| 属性 | 值 |
|------|-----|
| 位置 | `~/.workbuddy/skills/obsidian/` |
| 状态 | ✅ 可用 |

### 13. Playwright Scraper（浏览器抓取）

| 属性 | 值 |
|------|-----|
| 位置 | `~/.workbuddy/skills/Playwright Scraper/` |
| 状态 | ✅ 可用 |

---

## 三、完整依赖清单

### Python 依赖（agent-os venv）

| 包 | 版本 | 用途 | 安装状态 |
|---|---|---|---|
| trafilatura | 2.0.0 | 网页内容提取 | ✅ |
| sqlite-utils | 3.39 | SQLite 增强 | ✅ |
| feedparser | latest | RSS 解析 | ✅ |
| schedule | latest | 定时任务 | ✅ |
| chromadb | latest | 向量数据库 | ✅ |
| scrapling | latest | 三引擎反爬抓取 | ✅ |
| crawl4ai | latest | LLM 友好结构化抓取 | ✅ |
| playwright | 1.58.0 | 浏览器自动化 | ✅ |
| playwright-stealth | latest | 反检测 | ✅ |
| openai-whisper | latest | 语音转文字 | ✅ |
| stagehand | latest | 复杂页面交互 | ✅ |

**安装命令**：
```bash
# 所有 pip 包一条命令安装
/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/pip install \
  trafilatura sqlite-utils feedparser schedule chromadb \
  scrapling 'crawl4ai[all]' playwright playwright-stealth \
  openai-whisper stagehand
```

### Node.js 依赖

| 包 | 用途 | 安装状态 |
|---|---|---|
| @tikomni/skills | 小红书/抖音数据采集 | ✅ |

**安装命令**：
```bash
cd /Users/chengzige/.workbuddy/binaries/node/workspace && \
NODE_PATH=/Users/chengzige/.workbuddy/binaries/node/versions/22.12.0/bin/node \
/Users/chengzige/.workbuddy/binaries/node/versions/22.12.0/bin/npm install @tikomni/skills
```

### 系统/外部依赖

| 软件 | 安装方式 | 用途 | 状态 |
|---|---|---|---|
| oMLX | 官网下载 / App Store | 本地 LLM 运行（MLX 框架） | ✅ 已安装 v0.3.6 |
| Obsidian | 官网下载 | 知识库管理 | ✅ 已安装 |
| Playwright Chromium | `playwright install chromium` | 浏览器引擎 | ⚠️ 待下载 |
| BiliNote Docker | Docker 部署 | 视频转笔记 | ⚠️ 待部署 |
| yt-dlp | `brew install yt-dlp` | 视频下载 | ⚠️ 需 brew |
| ffmpeg | `brew install ffmpeg` | 音视频转换 | ⚠️ 需 brew |
| ScreenPipe | `brew install screenpipe` | 屏幕录制 OCR | ⚠️ 需 brew |
| Homebrew | 官网安装脚本 | 包管理器 | ❌ 未安装 |
| jq | 系统自带 | JSON 处理 | ✅ |

---

## 四、环境配置

### 固定路径

```
# Python
MANAGED_PYTHON=/Users/chengzige/.workbuddy/binaries/python/versions/3.13.12/bin/python3
AGENTOS_PYTHON=/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3
AGENTOS_VENV=/Users/chengzige/.workbuddy/binaries/python/envs/agent-os

# Node.js
MANAGED_NODE=/Users/chengzige/.workbuddy/binaries/node/versions/22.12.0/bin/node
NODE_WORKSPACE=/Users/chengzige/.workbuddy/binaries/node/workspace

# agent-os
AGENTOS_ROOT=~/agent-os

# 知识库
KNOWLEDGE_BASE=~/agent-os/03_knowledge/

# 坚果云
NUTSTORE=~/NutstoreCloudBridge/
```

### 迁移到新机器时

1. 安装 WorkBuddy（自动提供 managed Python/Node）
2. 创建 agent-os venv：
   ```bash
   $MANAGED_PYTHON -m venv $AGENTOS_VENV
   $AGENTOS_VENV/bin/pip install -r ~/agent-os/requirements.txt
   ```
3. 安装 Node 依赖：
   ```bash
   cd $NODE_WORKSPACE && npm install @tikomni/skills
   ```
4. 安装 Homebrew → `brew install yt-dlp ffmpeg screenpipe`
5. 安装 Obsidian
6. 部署 BiliNote Docker
7. 运行 `playwright install chromium`
8. 运行冷启动：`$AGENTOS_PYTHON ~/agent-os/02_skills/memory_manager/bootstrap_from_memory.py --root ~/agent-os`

---

## 五、自动化任务

| 任务 | 频率 | 命令 |
|------|------|------|
| 每日记忆提炼 | 每日 2:00 | `$AGENTOS_PYTHON ~/agent-os/02_skills/memory_manager/daily_digest.py --root ~/agent-os` |
| 分类目录汇聚收件箱 | 每日 2:30 | `$AGENTOS_PYTHON ~/agent-os/02_skills/collect_to_inbox/collect_to_inbox.py --root ~/agent-os` |
| 知识库收件箱提纯 | 每日 3:00 | `$AGENTOS_PYTHON ~/agent-os/02_skills/inbox_refine/inbox_refine.py --root ~/agent-os` |
| RSS 检查 | 每小时 | auto_collector |
| 社交平台检查 | 每 2 小时 | auto_collector + TikOmni |
| 网页变化检查 | 每小时 | auto_collector + Crawl4AI |
| 采集日报 | 每日 23:00 | auto_collector 汇总 |

---

## 六、待解决项

| 项目 | 优先级 | 说明 |
|------|--------|------|
| Playwright Chromium | 中 | 网络问题导致下载失败，需换网络重试 |
| Homebrew | 中 | 可选，安装后可装 yt-dlp/ffmpeg/screenpipe |
| BiliNote Docker | 低 | 视频转笔记核心依赖，需 Docker Desktop |

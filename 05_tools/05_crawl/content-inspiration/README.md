# 🎬 口播素材智能采集与分析系统

> 完全本地运行的口播灵感工坊——采集、AI 分析、智能下载、统一检索，隐私安全零成本。

**版本**：v1.0.0  
**适用环境**：Mac M1 / 16GB RAM / macOS  
**作者**：ghai  
**日期**：2026-04-28

---

## 一、这是什么？

一个个人口播创作者的**素材灵感管理系统**。解决的核心问题：

| 痛点 | 解决方案 |
|------|----------|
| 素材散布在抖音/小红书/B站 | 一键采集元数据到本地 SQLite |
| 收藏夹大量 404 | AI 判断价值 → 自动下载到本地 |
| 看标题判断不了口播价值 | 本地 LLM 自动提取金句/情绪/结构 |
| 不想上云、不想付费 | 全部跑在本机，零网络依赖（采集除外） |

**一句话**：搜得到、看得懂、存得住、找得快。

---

## 二、系统架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  collect.py │────→│  analyze.py  │────→│   app.py    │
│  多平台采集   │     │  AI 分析      │     │  Web 界面    │
└──────┬──────┘     └──────┬───────┘     └──────┬──────┘
       │                   │                    │
       ▼                   ▼                    ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  JSONL 存档   │   │  oMLX 本地LLM │   │  SQLite 索引  │
│  data/raw/   │   │  Qwen2.5-VL  │   │  data/db     │
└──────────────┘   └──────────────┘   └──────┬───────┘
                                           │
                                    ┌──────▼───────┐
                                    │downloader.py │
                                    │  yt-dlp 下载  │
                                    └──────┬───────┘
                                           │
                                           ▼
                               ~/agent-os-local/materials/
```

### 技术选型

| 组件 | 选型 | 为什么 |
|------|------|--------|
| 采集引擎 | MediaCrawler (Playwright) | 主流平台支持最全 |
| AI 大脑 | oMLX + Qwen2.5-VL-3B-8bit | 本地免费，3B 模型足够 JSON 输出 |
| 结构化存储 | SQLite (WAL 模式) | 零配置，16GB 无压力 |
| 媒体下载 | yt-dlp | 支持平台最多 |
| Web 界面 | Gradio | Python 原生，开发最快 |
| 配置管理 | YAML | 人类可读，注释友好 |

---

## 三、快速开始

### 3.1 环境准备

```bash
# 确认 Python 环境
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 --version
# 应输出: Python 3.13.12

# 确认 oMLX 运行中
curl -s http://localhost:8000/v1/models -H "Authorization: Bearer omlx" | python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data']]"
# 应输出: Qwen2.5-VL-3B-Instruct-8bit
```

### 3.2 安装依赖

```bash
~/.workbuddy/binaries/python/envs/agent-os/bin/pip install gradio yt-dlp
```

### 3.3 初始化数据库

```bash
cd ~/agent-os/05_tools/05_crawl/content-inspiration
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 collect.py --init-db
# 输出: [OK] 数据库初始化完成
```

### 3.4 开始使用

```bash
# 1. 采集素材（需要先配置 MediaCrawler Cookie）
python collect.py -p xiaohongshu -k "普通人逆袭"

# 2. AI 分析（需要 oMLX 运行中）
python analyze.py

# 3. 启动 Web 界面
python app.py
# 打开 http://127.0.0.1:7860

# 4. 下载视频（在 Web 界面标记后）
python downloader.py
```

---

## 四、项目结构

```
content-inspiration/
├── SKILL.md              # 技能身份证（system/user 能力说明）
├── README.md             # 本文件（完整项目说明）
├── config.yaml           # 所有配置（平台/模型/存储/下载/Web）
├── schema.sql            # 数据库表结构（3 张表）
├── requirements.txt      # Python 依赖清单
│
├── collect.py            # 采集脚本（MediaCrawler 封装）
├── analyze.py            # AI 分析脚本（oMLX 调用 + JSON 解析）
├── downloader.py         # 下载脚本（yt-dlp 封装）
├── app.py                # Web 界面（Gradio）
├── utils.py              # 通用工具（配置/数据库/日志/JSONL）
│
├── data/
│   ├── raw/              # JSONL 原始采集存档
│   │   └── 2026-04-28_xiaohongshu_普通人逆袭.jsonl
│   └── database.db       # SQLite 素材库
│
└── logs/                 # 运行日志（按日期分割）
    ├── collect_20260428.log
    └── analyze_20260428.log
```

### 与 AgentOS 的关系

```
~/agent-os/                          ← 坚果云同步 + Git
└── 05_tools/05_crawl/
    └── content-inspiration/         ← 本项目
        ├── 代码 + 配置 + 数据库      （同步）
        └── data/raw/*.jsonl         （同步）

~/agent-os-local/                    ← 本机专属，不同步
└── materials/
    ├── video/                       ← 下载的视频
    └── audio/                       ← 下载的音频
```

- 项目代码和数据库跟随 agent-os 同步
- 下载的视频/音频在本机专属目录，不占用同步空间
- AI 分析结果可通过 AgentOS 的 inbox_refine 归档到知识库

---

## 五、配置说明（config.yaml）

```yaml
# 平台和关键词
platforms:
  - xiaohongshu          # 目前最成熟
  - douyin               # 需要 Cookie
  - bilibili             # 支持

keywords:
  - "普通人逆袭"
  - "情感故事"
  - "科普冷知识"

max_count: 20            # 每关键词每次采集上限

# 本地 LLM（oMLX，非 Ollama）
llm:
  model: "Qwen2.5-VL-3B-Instruct-8bit"
  base_url: "http://localhost:8000/v1"   # oMLX 端口
  api_key: "omlx"                        # oMLX 固定 key
  timeout: 120                            # 每条分析超时
  temperature: 0.3                        # 低温度保证稳定

# 存储路径
storage:
  raw_dir: "data/raw"
  db_path: "data/database.db"
  media_dir: "~/agent-os-local/materials/video"
  audio_dir: "~/agent-os-local/materials/audio"

# Web 界面
web:
  host: "127.0.0.1"
  port: 7860
  title: "口播灵感工坊"

# 下载配置
download:
  rate_limit: "1M"        # 速率限制，防 IP 封禁
  retries: 3              # 重试次数
```

---

## 六、脚本详细说明

### collect.py — 采集脚本

**功能**：从主流平台采集内容元数据（标题、描述、封面、互动数据等），不下载视频本体。

```bash
# 初始化数据库
python collect.py --init-db

# 指定平台和关键词采集
python collect.py -p xiaohongshu -k "科普冷知识"

# 指定数量
python collect.py -p xiaohongshu -k "情感故事" -n 10

# 按 config.yaml 批量采集（遍历所有平台×关键词）
python collect.py
```

**输出**：
- `data/raw/YYYY-MM-DD_平台_关键词.jsonl` — 原始数据存档
- `data/database.db` — 写入 materials 表（自动去重）

**前置条件**：MediaCrawler 已安装并配置好 Cookie。

### analyze.py — AI 分析脚本

**功能**：对未分析的素材调用本地 oMLX（Qwen2.5-VL-3B），提取口播可用信息。

```bash
# 分析所有未分析的素材
python analyze.py

# 只分析前 10 条（测试用）
python analyze.py -n 10

# 只看有多少待分析（不执行）
python analyze.py --dry-run

# 重试之前失败的记录
python analyze.py --retry-failed
```

**输出**：写入 analysis 表，字段包括：
- `tags` — AI 标签（科普、情感、冷知识…）
- `golden_quote` — 可直接引用的金句
- `core_idea` — 核心立意
- `structure` — 口播脚本结构
- `emotion` — 整体情绪
- `worth_downloading` — 是否推荐下载

**注意**：串行执行（每次只处理一条），16GB Mac 不会 OOM。每条间隔 1 秒。

### downloader.py — 下载脚本

**功能**：下载标记为 pending 的素材视频到本地。

```bash
# 下载所有标记为待下载的
python downloader.py

# 下载所有 AI 推荐的
python downloader.py --all

# 限制数量
python downloader.py -n 5

# 手动指定 URL
python downloader.py -u "https://v.douyin.com/xxx"
```

**输出**：文件保存到 `~/agent-os-local/materials/video/`，文件名格式：
```
xiaohongshu_作者名_标题前20字_日期.mp4
```

### app.py — Web 界面

**功能**：本地浏览器访问的素材管理界面。

```bash
python app.py
# 打开 http://127.0.0.1:7860
```

**功能清单**：
- 🔍 关键词搜索（标题/描述/标签/金句）
- 📋 平台/情绪/下载状态筛选
- 📊 实时统计（总数/已分析/已下载/AI推荐）
- 📖 素材详情（AI 分析完整结果）
- 📥 一键标记下载
- 📝 金句可直接复制

### utils.py — 工具函数

| 函数 | 用途 |
|------|------|
| `load_config()` | 加载 config.yaml |
| `get_db()` / `init_db()` | 数据库连接/初始化 |
| `setup_logger()` | 日志配置 |
| `parse_jsonl()` / `save_jsonl()` | JSONL 读写 |
| `check_omlx()` | 检测 oMLX 可用性 |
| `truncate_text()` | 文件名安全截断 |

---

## 七、数据库设计

### materials 表（素材元数据）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| platform | TEXT | 平台（xiaohongshu/douyin/bilibili） |
| original_id | TEXT | 平台内唯一 ID |
| url | TEXT | 原始链接 |
| title | TEXT | 标题 |
| description | TEXT | 描述/正文 |
| author | TEXT | 作者 |
| cover_url | TEXT | 封面图 |
| music_name | TEXT | BGM |
| like_count | INTEGER | 点赞数 |
| analyzed | INTEGER | 0未分析/1已分析/2失败 |
| download_status | TEXT | none/pending/downloading/done/failed |
| local_files | TEXT | JSON（本地文件路径） |
| raw_json | TEXT | 完整原始数据备份 |

### analysis 表（AI 分析结果）

| 字段 | 类型 | 说明 |
|------|------|------|
| material_id | INTEGER | 关联素材 |
| tags | TEXT | AI 标签（逗号分隔） |
| golden_quote | TEXT | 金句 |
| core_idea | TEXT | 核心立意 |
| structure | TEXT | 脚本结构 |
| emotion | TEXT | 情绪 |
| worth_downloading | TEXT | yes/no/maybe |
| download_reason | TEXT | 下载理由 |
| raw_model_output | TEXT | 模型原始输出（调试） |

### collect_batches 表（采集批次记录）

记录每次采集的平台、关键词、数量、状态，方便回溯。

---

## 八、知识库索引卡片

采集并分析后的素材，可以在知识库中生成索引卡片（存入 `03_knowledge/50_resources/`）：

**文件名格式**：`{hostname}_{YYYYMMDD}_{slug}.md`  
**示例**：`Redmi-12C_20260428_xiaohongshu-普通人逆袭.md`

```markdown
---
title: 普通人逆袭合集
source_url: https://www.xiaohongshu.com/explore/xxx
local_path: ~/agent-os-local/materials/video/xiaohongshu_作者_标题.mp4
type: video
platform: xiaohongshu
collected_by: Redmi-12C
collected_at: 2026-04-28
tags: [口播素材, 励志, 逆袭]
---
一句话说明：适合逆袭主题口播开头，情绪张力强。
```

`collected_by` 字段防止多机同步时文件名冲突。

---

## 九、MediaCrawler 配置（前置条件）

### 安装

```bash
cd ~/agent-os/05_tools/05_crawl
git clone https://github.com/NanmiCoder/MediaCrawler.git
cd MediaCrawler
~/.workbuddy/binaries/python/envs/agent-os/bin/pip install -r requirements.txt
```

### 配置 Cookie

各平台需要在首次使用前扫码登录获取 Cookie：

1. `cd ~/agent-os/05_tools/05_crawl/MediaCrawler`
2. `python main.py --platform xhs --lt qrcode`
3. 扫描终端显示的二维码
4. Cookie 自动保存，后续无需重复登录

### 配置本项目

安装完成后，更新 `config.yaml`：
```yaml
crawler:
  project_path: "~/agent-os/05_tools/05_crawl/MediaCrawler"
```

---

## 十、性能与资源管理（16GB Mac）

| 场景 | 内存占用 | 建议 |
|------|----------|------|
| 采集（Playwright） | ~500MB | 关闭其他浏览器 |
| AI 分析（Qwen2.5-VL-3B） | ~2GB | 关闭其他大型应用，串行执行 |
| Web 界面（Gradio） | ~300MB | 轻量，无压力 |
| 下载（yt-dlp） | ~100MB | 速率限制 1MB/s |

**关键原则**：分析期间不同时运行其他 AI 任务，每次只处理一条记录。

---

## 十一、常见问题

**Q: oMLX 返回 500 错误？**  
A: Qwen3-8B-MLX-4bit 有已知问题。本系统使用 Qwen2.5-VL-3B-Instruct-8bit，不受影响。

**Q: 采集没有数据？**  
A: 检查 MediaCrawler Cookie 是否过期，重新扫码登录。

**Q: AI 分析结果不准确？**  
A: 3B 模型有限，可通过调整 `temperature`（降低=更稳定）或更换更强模型改善。

**Q: 视频下载失败？**  
A: 抖音/小红书链接有时效性，采集后尽快下载。也可尝试 `--retry-failed`。

**Q: 如何接入 AgentOS 自动化？**  
A: 可在 WorkBuddy 中创建定时自动化，例如每天凌晨执行 `python analyze.py`。

---

## 十二、合规提醒

- ⚠️ 仅供**个人学习研究**，禁止大规模抓取或商业化
- 下载的视频仅供**分析借鉴**，口播内容须二次原创
- 所有数据**本地存储**，注意定期备份

---

## 十三、未来扩展

- [ ] 定时自动采集 + 热点推送
- [ ] 向量语义搜索（接入 ChromaDB + Qwen3-Embedding）
- [ ] 提示词模板可视化编辑
- [ ] 素材标签归一化
- [ ] 简易剪辑时间线

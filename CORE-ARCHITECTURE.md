# CORE-ARCHITECTURE.md —— AgentOS 核心架构说明

> 本文档是 AgentOS 的"宪法"，定义了目录职责、数据边界、换机流程。
> 最后更新：2026-05-02

---

## 一、系统定位

AgentOS 是一套运行在个人 Mac 上的**智能体外骨骼系统**，核心能力：
- 记忆管理（L0-L3 五级分层）
- 知识库管理（Obsidian Vault）
- 内容采集与自动化（定时采集、提炼、归档）
- 多平台协作（通过坚果云同步 + Git 版本控制）

---

## 二、目录职责

### `~/workbuddy-agent-os/agent-sync/`（坚果云同步 + Git 版本控制）

| 目录 | 职责 | 同步 | Git |
|------|------|------|-----|
| `00_bootstrap/` | 初始化脚本（init.sh、apply-config.sh） | ✅ | ✅ |
| `01_core/` | 核心配置（SOUL.md、IDENTITY.md、USER.md、mcp.json） | ✅ | ✅ |
| `02_skills/` | 所有技能（每个技能一个文件夹，含 SKILL.md） | ✅ | ✅ |
| `03_knowledge/` | Obsidian 知识库（只放提炼后的 .md 文件） | ✅ | ✅ |
| `04_memory/` | 记忆体（L2 facts.db + L1 索引 + 日志） | ✅ | ✅ |
| `05_tools/` | 公共工具脚本（环境检查、爬虫、媒体处理） | ✅ | ✅ |
| `06_runtime/tasks/` | 任务执行记录 | ✅ | ✅ |
| `07_migration/` | 打包/还原脚本 | ✅ | ✅ |
| `CHANGELOG.md` | 变更日志 | ✅ | ✅ |
| `README.md` | 项目说明 | ✅ | ✅ |
| `REQUIREMENTS.md` | 环境要求 | ✅ | ✅ |
| `SKILLS-CATALOG.md` | 技能目录 | ✅ | ✅ |
| `CORE-ARCHITECTURE.md` | 本文档 | ✅ | ✅ |

### `~/workbuddy-agent-os/agent-local/`（本机专属，不同步，不进 Git）

```
agent-os-local/
├── memory/                    # 记忆体相关（软链接目标）
│   ├── raw/                   # L3 对话原文（隐私）
│   └── vector_db/             # ChromaDB + 关键词索引
├── runtime/                   # 运行时临时数据
│   └── cache/                 # 临时缓存
└── materials/                 # 采集的原始素材
    ├── web/                   # 网页保存
    ├── video/                 # 视频下载（yt-dlp 输出）
    ├── audio/                 # 录音文件
    ├── screenshots/           # 截图
    └── refined_for_inbox/     # 已提炼待投递的 .md
```

> `agent-os/` 内通过**软链接**指向 `agent-os-local/` 中的实际目录，脚本无需改路径。

---

## 三、软链接映射

```
~/workbuddy-agent-os/agent-sync/04_memory/long_term/raw     → ~/workbuddy-agent-os/agent-local/memory/raw
~/workbuddy-agent-os/agent-sync/04_memory/vector_db         → ~/workbuddy-agent-os/agent-local/memory/vector_db
~/workbuddy-agent-os/agent-sync/06_runtime/cache            → ~/workbuddy-agent-os/agent-local/runtime/cache
```

换机时 `init.sh` 会自动检测并重建这些软链接。

---

## 四、技能分类规则

### system 技能（后台自动运行，不直接对话触发）

| 技能 | 说明 |
|------|------|
| `memory_manager` | 记忆提炼、去重、语义检索 |
| `inbox_refine` | 收件箱提纯→知识库归档 |
| `collect_to_inbox` | 知识库目录扫描→收件箱 |
| `auto_collector` | 24h 自动信息收集 |
| `sync_manager` | 备份与同步管理 |
| `kb_manager` | 知识库入库与管理 |

### user 技能（对话触发）

| 技能 | 说明 |
|------|------|
| `content_processor` | 统一内容处理（视频/文章/语音/社交） |
| `web_crawler` | 网页抓取 + 反爬 |
| `git_sync_manager` | Git多机同步管理器（替代坚果云依赖） |

---

## 五、知识库索引卡片规范

多台电脑采集的素材通过**索引卡片**共享，避免大文件同步冲突。

### 文件命名

```
{hostname}_{YYYYMMDD}_{slug}.md
示例：Redmi-12C_20260428_douyin-普通人逆袭.md
      MBP-M3_20260428_bilibili-科普冷知识.md
```

### 卡片模板

```markdown
---
title: 素材标题
source_url: https://...
local_path: ~/workbuddy-agent-os/agent-local/materials/video/xxx.mp4
type: video|audio|web|image
platform: douyin|xiaohongshu|bilibili|web
collected_by: Redmi-12C
collected_at: 2026-04-28
tags: [标签1, 标签2]
---
一句话说明这个资源的口播改编价值。
```

> `collected_by` 字段标明采集机器，防止多机同步时同名冲突。

---

## 六、同步策略

### 坚果云
- 同步整个 `~/workbuddy-agent-os/agent-sync/` 目录
- `~/workbuddy-agent-os/agent-local/` 不加入同步（通过软链接隔离，天然安全）
- 无需配置选择性排除

### Git
- 远程仓库：`https://gitee.com/babycalf/mac-agent-os.git`
- 分支策略：main 分支，单线开发
- 排除：大媒体文件、运行时缓存、打包产物（见 `.gitignore`）

### Git同步技能（替代坚果云）
使用 `git_sync_manager` 技能可完全替代坚果云依赖：
1. **首次配置**：技能引导完成SSH密钥生成、Gitee公钥添加、仓库配置
2. **日常同步**：一键执行 `git pull` / `git push` 操作
3. **多机管理**：每台电脑使用独立SSH密钥，安全隔离
4. **自动化**：可配置定时任务或通过 `agentos sync` 命令触发

### 数据流

```
本机采集 → ~/workbuddy-agent-os/agent-local/materials/ → AI提炼 → ~/workbuddy-agent-os/agent-sync/03_knowledge/00_inbox/
                                                        ↓ 坚果云同步
                                                        ↓
其他电脑 → inbox_refine → 归档到知识库 → Git commit → Gitee
```

---

## 七、换机还原流程（3步）

```bash
# 1. 等坚果云同步完成，agent-os 目录出现在本机
# 2. 安装基础环境
cd ~/workbuddy-agent-os/agent-sync/00_bootstrap && bash init.sh

# 3. 手动安装 oMLX（Apple MLX 框架，硬件依赖）
```

`init.sh` 会自动完成：
- 创建 `~/workbuddy-agent-os/agent-local/` 各子目录
- 重建 3 个软链接（raw、vector_db、cache）
- 创建 Python venv 并安装依赖
- 填充本机设备信息到 IDENTITY.md
- 部署核心配置（SOUL.md、USER.md）到 WorkBuddy
- 检测并提示需要手动安装的组件

---

## 八、定时任务

| 任务 | 时间 | 脚本 | 说明 |
|------|------|------|------|
| 每日记忆提炼 | 02:00 | `memory_manager/daily_digest.py` | 对话→L2 事实 |
| 收件箱汇聚 | 02:30 | `collect_to_inbox/collect_to_inbox.py` | 知识库扫描→inbox |
| 收件箱提纯 | 03:00 | `inbox_refine/inbox_refine.py` | inbox→分类归档 |

---

## 九、运行时外挂（不属于仓库）

以下组件由系统管理，不进 Git，换机时需手动安装：

| 组件 | 路径 | 说明 |
|------|------|------|
| oMLX | `/Applications/oMLX.app` | 本地 LLM 引擎 |
| WorkBuddy Python | `~/.workbuddy/binaries/python/` | WorkBuddy 管理的运行时 |
| WorkBuddy Node | `~/.workbuddy/binaries/node/` | WorkBuddy 管理的运行时 |
| Playwright 浏览器 | `~/Library/Caches/ms-playwright/` | `playwright install chromium` 重装 |
| 坚果云客户端 | `/Applications/Nutstore.app` | 系统应用 |

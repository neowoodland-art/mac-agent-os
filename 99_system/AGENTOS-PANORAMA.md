# AgentOS 联邦智能体系统全景文档

> 版本：v1.0 | 最后更新：2026-06-15
> 目的：完整记录系统"是什么"，为后续架构优化提供结构化参考
> 本文件不讨论"怎么做"，只记录"现在是什么"和"经历过什么"

---

## 第一部分：系统身份

### 1.1 一句话定义

一个**运行在多台 Mac 上的 AI 智能体联邦操作系统**，各机器通过 Git 共享代码和配置，各自执行养号/采集/知识管理等任务，通过 Dashboard 统一监控。

### 1.2 核心设计理念

- **代码走同步，数据留本机** — 脚本在 Git，数据在本地
- **四层隔离** — 管理层/流水线层/操作层/数据层各自独立
- **每账号独立工作区** — 身份/素材/文案/发布记录各自独立
- **原子操作可组合** — 所有操作遵循"前置锚点→执行→后置锚点"
- **WPRA 写分区·读聚合** — 各写各的文件，最后统一读取（v2.0 架构）

### 1.3 用户画像（ghai）

- 多台 Mac 电脑使用者（最少 3 台）
- 从事 AI 短视频/矩阵内容运营
- 需要多账号、多平台（抖音/小红书）自动化管理
- 有知识库和记忆管理需求
- 同时也在探索 AI 视频生成（Seedance/即梦/豆包）

---

## 第二部分：硬件基础设施

### 2.1 机器清单

| 机器 | UID | 硬件 | 操作系统 | 角色 | 位置 |
|:-----|:----|:-----|:---------|:-----|:-----|
| chengzigedeAir | 4cf443bc... | MacBook Air M1, 16GB | macOS 26.4 arm64 | **本机** | 本地 |
| 5kechengdeAir | f13b03d1... | Mac (未知配置) | macOS 25.4 arm64 | 远程机器 | Gitee 同步 |
| 7kecheng | d19759cf... | Mac (未知配置) | macOS arm64 | 远程机器 | Gitee 同步 |

### 2.2 机器连接方式

- **Git 仓库**：Gitee（主）+ GitHub（备），双远程推送
- **SSH**：配置了到 Gitee/GitHub 的 SSH 密钥（id_ed25519a）
- **Tailscale**：5kechengdeAir 上已安装，本机尚未安装
- **远程执行**：`mc remote exec` 已实现 SSH/HTTP 两种方式
- **局域网**：各机器在 192.168.31.x 网段内互通

---

## 第三部分：软件与依赖

### 3.1 运行时环境

| 组件 | 版本 | 路径 | 说明 |
|:-----|:-----|:-----|:------|
| Python (managed) | 3.13.12 | `~/.workbuddy/binaries/python/versions/3.13.12/` | WorkBuddy 管理 |
| Python (system) | 3.9.6 | `/usr/bin/python3` | macOS 自带 |
| Python (venv) | 3.13.12 | `~/.workbuddy/binaries/python/envs/agent-os/` | 主运行环境 |
| Node.js | 22.12.0 | `~/.workbuddy/binaries/node/versions/22.12.0/` | WorkBuddy 管理 |
| Camoufox | (pip) | venv 内安装 | Firefox 内核浏览器，用于养号 |
| oMLX | v0.3.6 | /Applications/oMLX.app | 本地 LLM 推理引擎 |
| Ollama | v0.21.2 | /Applications/Ollama.app | 已停用 |
| Orjson | 3.11.9 | venv site-packages | 曾因 macOS 签名问题导致浏览器启动失败 |

### 3.2 本地 LLM 模型

| 模型 | 用途 | 状态 |
|:-----|:------|:------|
| Qwen3-8B-MLX-4bit | 主力推理 | ❌ Chat API 500 错误 |
| Qwen2.5-VL-3B-Instruct-8bit | 多模态理解 | ✅ 正常 |
| Qwen3-Embedding-0.6B | 向量嵌入（1024维） | ✅ 正常 |

### 3.3 已知环境问题

1. **orjson macOS 代码签名**：Python 3.13 的 .so 文件被 Tencent 签名，与本地编译的 orjson 冲突 → 需 `codesign --remove-signature` 后重新签署
2. **Python 版本割裂**：系统 3.9 vs 管理 3.13，不同版本行为差异
3. **Camoufox 启动**：依赖 orjson 和特定系统库，部分机器启动失败
4. **Git 仓库膨胀**：含浏览器缓存和二进制文件，接近 1GB

---

## 第四部分：系统组件全览

### 4.1 顶层目录

```
workbuddy-agent-os/
├── agent-sync/         594MB  ← Git 仓库（代码 + 配置 + 一些数据）
│   ├── 00_bootstrap/         启动脚本、init.sh、apply-config.sh
│   ├── 01_core/              核心配置：SOUL.md, IDENTITY.md, USER.md
│   ├── 02_skills/            自定义技能：memory_manager, matrix, kb_manager 等
│   ├── 03_knowledge/         知识库（按分类：01_daily~50_resources）
│   ├── 04_memory/            跨机协同（WPRA）、记忆文件
│   ├── 05_tools/             全部工具：
│   │   ├── 00_setup/         agentos CLI, guardd 守护进程
│   │   ├── 01_system/        系统级脚本（路径修复、检测等）
│   │   ├── 02_browser/       浏览器自动化
│   │   ├── 03_ocr/           OCR 识别
│   │   ├── 04_media/         媒体处理
│   │   ├── 05_crawl/         爬虫（longcat, content-inspiration）
│   │   ├── 06_mobile/        移动端
│   │   ├── 07_matrix/        矩阵养号系统（核心）
│   │   ├── 08_trae_agent/    TRAE 控制
│   │   ├── 09_ave/           视频工厂
│   │   └── 10_dashboard/     Dashboard 看板（FastAPI + 前端）
│   ├── 90_archive/           归档文档
│   └── 99_system/            系统文档、架构、协议
│
└── agent-local/              本机数据（不同步）
    ├── identity/             机器身份、machine_uid
    ├── memory/               记忆文件（L1/L2/L3、向量库）
    ├── tools/                工具运行时数据
    │   └── matrix/           matrix 系统数据
    │       ├── config/       accounts.yaml 账号配置
    │       ├── identities/   浏览器身份（Cookie + 指纹）
    │       └── data/         运行时数据、profiles.json
    ├── vector_db/            向量库（ChromaDB + 关键词索引）
    └── runtime/              运行时缓存
```

### 4.2 工具详解

#### 05_tools/07_matrix — 矩阵养号系统（核心）
| 子模块 | 说明 | 状态 |
|:-------|:------|:------|
| `mc` CLI | 统一命令行入口 | ✅ 活跃 |
| `scripts/mc/run.py` | 批量执行引擎（BatchEngine） | ✅ 活跃 |
| `scripts/mc/engine.py` | Camoufox 浏览器操作引擎 | ✅ 活跃 |
| `scripts/mc/cli.py` | CLI 命令调度（10+ 子命令） | ✅ 活跃 |
| `scripts/mc/analyzer.py` | 录制分析器 | ✅ 新增 |
| `scripts/mc/exporter.py` | 蓝图导出器 | ✅ 新增 |
| `scripts/mc/recorder.py` | 操作录制器 | ✅ 新增 |
| `blueprints/` | 14 个蓝图（抖音 9 + 小红书 4 + 录制 1） | ✅ |
| `scripts/nurture_daily.py` | 日常养号调度器 v1.0 | ✅ |
| `scripts/collect_batch_runner.py` | 批量主页信息采集 | ✅ |
| `scripts/collect_homepage_info.py` | 主页信息采集 | ✅ |
| `scripts/cdp_connector.py` | Chrome CDP 连接（含反检测） | ✅ |
| `scripts/anti_detection.py` | 反检测模块 | ✅ |
| Dashboard 集成 | 看板中的矩阵管理（7 个子页面） | ✅ |

#### 05_tools/10_dashboard — Dashboard 看板
| 模块 | 说明 |
|:-----|:------|
| `app.py` | FastAPI 主应用（3000+ 行，含所有 API） |
| `static/index.html` | 单页前端（4000+ 行，含所有前端逻辑） |
| `plugins/base.py` | 插件基类（AGENT_SYNC/AGENT_LOCAL 路径常量） |
| `plugins/matrix.py` | 矩阵插件（账号管理、蓝图、原子操作） |
| `plugins/kb_api.py` | 知识库 API |
| `plugins/sms_proxy_api.py` | 短信/代理管理 |
| `plugins/system_plugins.py` | 系统插件 |
| `plugins/_registry.py` | 注册表管理 |

#### 05_tools/00_setup — 系统基础设施
| 模块 | 说明 |
|:-----|:------|
| `agentos/main.py` | `agentos` CLI（init/check/upgrade/rebuild-vector） |
| `guardd/guardd.py` | 守护进程（心跳 + 自动化 + 数据管理）目前有 7 个模块 |
| `sync_machine.sh` | 机器同步脚本 |

#### 05_tools/05_crawl — 采集系统
| 模块 | 说明 |
|:-----|:------|
| `longcat/` | 长期爬虫（含浏览器 Profile ~400MB） |
| `content-inspiration/` | 内容灵感采集（豆包浏览器驱动） |

#### 05_tools/09_ave — 视频工厂
| 模块 | 说明 |
|:-----|:------|
| `scripts/service_layer/app.py` | 服务层 API |
| `scripts/main.py` | 主程序 |

### 4.3 技能系统（02_skills/）

| 技能 | 用途 | 状态 |
|:-----|:------|:------|
| memory_manager | 记忆提炼、冲突消解、语义检索 | ✅ |
| kb_manager | 知识库管理（新增/清洗/搜索/备份） | ✅ |
| inbox_refine | 收件箱提纯分类归档 | ✅ |
| collect_to_inbox | 内容归集到收件箱 | ✅ |
| auto_collector | 24小时自动信息收集 | ✅ |
| content_processor | 统一内容处理入口 | ✅ |
| sync_manager | 同步管理（备份/导出/迁移） | ✅ |
| matrix | 矩阵养号技能 | ✅ |
| web_crawler | 网页抓取（Scrapling/Crawl4AI） | ✅ |

---

## 第五部分：所有工作流程

### 5.1 养号流程

```
┌─ 定时触发 ─────────────────────────────────────┐
│                                                 │
│  mc run --accounts A,B,C --blueprints X --rounds N   │
│    ↓                                                │
│  BatchEngine                                       │
│    ├─ 账号A: 启动 Camoufox → 执行蓝图循环 → 关闭    │
│    ├─ 账号B: 启动 Camoufox → 执行蓝图循环 → 关闭    │
│    └─ 账号C: 启动 Camoufox → 执行蓝图循环 → 关闭    │
│    ↓                                                │
│  报告输出                                           │
│                                                     │
│  蓝图内步骤: goto_home → browse → like →            │
│             comment → next_video → 循环              │
└─────────────────────────────────────────────────────┘
```

执行方式：
- **Dashboard 命令与任务 → 全部养号**：选身份/时间/并发 → 一键启动
- **Dashboard 命令与任务 → 批量执行**：选账号/蓝图 → 一键执行
- **CLI 直接执行**：`mc run --accounts ...`
- **定时自动化**：nurture_daily.py 调度器

### 5.2 采集流程

```
主页信息采集（collect_batch_runner.py）：
  启动 → 读取 accounts.yaml → 分批并行
    ├─ 账号A (打开浏览器 → 导航到主页 → 读取信息 → 写入 profiles.json)
    ├─ 账号B (同上)
    └─ 账号C (同上)
  → 更新 collect_progress.json
  → 完成后通知 Dashboard
```

### 5.3 知识库流程

```
采集 → 01_submissions/ → (02:30 归集) → 00_inbox/
  → (03:00 提纯) → AI 分类 → 归档到 10_concepts/20_methods/ 等
  → 更新 README 统计
  → 更新 CHANGELOG
  → (03:30 向量重建) → ChromaDB 向量化 → 可语义检索
```

### 5.4 记忆管理流程

```
每日 02:00:
  提取昨日对话 → 关键事实 (who/what/when/where/decision)
  → 去重 (L2 相似度 > 0.9 跳过)
  → 冲突检测 (Override 或提示用户)
  → 更新 L1 关键词索引
  → 更新 L1_vec 向量索引 (ChromaDB + oMLX Embedding)
  → 原文压缩写入 L3
```

### 5.5 guardd 守护进程（7 模块）

| 模块 | 功能 | 周期 |
|:-----|:------|:------|
| module_heartbeat | 心跳上报 | 每轮 |
| module_automation | 定时任务检查 | 每轮 |
| module_event_log | 事件日志 | 触发时 |
| module_knowledge_sync | 知识同步 | 每轮 |
| module_system_info | 系统信息收集 | 每轮 |
| module_git_sync | Git 同步 | 每轮 |
| module_cross_machine | 跨机数据管理 | 每轮 |

---

## 第六部分：通信与同步机制

### 6.1 数据流向

```
你 (ghai)
  ├─ 操作 Dashboard (http://localhost:9988)
  │    └─ Dashboard 调用各 API → 操作本地文件/启动进程
  │
  ├─ git push → Gitee/GitHub → 其他机器 git pull
  │    ├─ 代码同步 (agent-sync/)
  │    ├─ 运行时数据同步 (04_memory/cross_machine/)
  │    │    ├─ machines/{uid}/accounts.yaml  ← 各写各的
  │    │    ├─ machines/{uid}/heartbeat.json  ← 各写各的
  │    │    ├─ events/{date}.jsonl            ← 各写各的
  │    │    └─ data/{uid}.json                ← 各写各的
  │    └─ 知识库同步 (03_knowledge/)
  │
  └─ SSH 远程连接
       └─ mc remote exec <host> <command>
            └─ SSH 到目标机器执行命令
```

### 6.2 WPRA 写分区·读聚合（当前架构, v2.0）

**写分区**：每台机器只写 `machines/{自己的UID}/` 下的文件
**读聚合**：Dashboard 读取时遍历所有机器的目录，聚合为完整视图

**已知问题**：
1. `_registry.json` 曾是多机器写冲突的根源（已修复为单实例写）
2. `git add -A` 会把所有机器的文件 staging，导致冲突
3. `accounts_registry.yaml` 单文件跨机器导致冲突（已迁移到 WPRA）
4. 架构文档说各写各的，但 guardd 的某些模块还在写全局文件

---

## 第七部分：自动化任务

### 7.1 WorkBuddy 内置自动化

| 任务 | 时间 | 状态 | 说明 |
|:-----|:------|:------|:------|
| AgentOS 每日记忆提炼 | 02:00 | ⏸ PAUSED | 提取对话→L2事实+L1索引 |
| 向量库与索引定时更新 | 02:30 | 🟢 ACTIVE | 知识库→关键词+ChromaDB |
| AgentOS 收件箱提纯 | 03:00 | ⏸ PAUSED | 收件箱→分类归档 |

### 7.2 未自动化的流程

| 流程 | 当前状态 | 问题 |
|:-----|:---------|:------|
| Git push 到远程 | 手动执行 | 夜间自动化完成后不会自动推送 |
| 工作日志生成 | 未实现 | 夜间任务完成后无汇总报告 |
| 向量重建 | 单独自动化已创建 | 但记忆提炼的向量更新已暂停 |
| 账号状态检查 | 手动 | 没有定时检查所有账号登录状态 |
| 远程机器同步 | 手动 | 需要手动 SSH 到各机器执行 git pull |

---

## 第八部分：历史问题与事故记录

### 8.1 路径问题（反复发生，4 次以上）

| 时间 | 问题 | 影响范围 |
|:-----|:------|:---------|
| 04-25 | `/Users/5kecheng/` → `/Users/chengzige/` 路径替换 | 6 个文件 |
| 04-29 | P0: 自动化 `--root` 路径失效 | 4 个自动化任务全部失效 |
| 04-29 | 旧路径 `~/agent-os` 残留 | 61 个文件 235 处引用 |
| 06-15 | Dashboard 中 12 处 `Path.home()` 硬编码 | 跨机兼容性 |

### 8.2 Git 冲突（反复发生）

| 类型 | 根因 | 频率 |
|:-----|:------|:------|
| `_registry.json` 冲突 | 多机器同时写同一个文件 | 每次同步 |
| `accounts.yaml` 冲突 | WPRA 迁移后仍有遗留 | 频繁 |
| `accounts_registry.yaml` 冲突 | 旧架构遗留文件 | 已删除 |
| 运行时数据冲突 | `git add -A` 包含所有机器数据 | 频繁 |

### 8.3 环境与依赖问题

| 问题 | 根因 | 状态 |
|:-----|:------|:------|
| orjson 代码签名 | macOS 安全策略，二进制 .so 签名不匹配 | 已修复 |
| lxml 版本冲突 | scrapling vs crawl4ai 版本要求不一致 | 已修复 |
| Qwen3-8B Chat API 500 | 模型兼容性问题 | 未修复（用 VLM 替代） |
| Camoufox 浏览器启动失败 | 依赖缺失/环境不一致 | 偶发 |

### 8.4 设计上的反复

| 事项 | 初始方案 | 当前方案 | 改了几次 |
|:-----|:---------|:---------|:---------|
| 账号注册表 | 单文件 accounts_registry.yaml | WPRA machines/{uid}/accounts.yaml | 3 次 |
| 路径结构 | `~/agent-os/`, `~/agent-os-local/` | `~/workbuddy-agent-os/agent-sync/`, `~/workbuddy-agent-os/agent-local/` | 2 次 |
| 自动同步 | 坚果云 | Git 双远程 | 2 次 |
| 本地 LLM | Ollama | oMLX | 1 次 |
| 浏览器引擎 | Chrome CDP | Camoufox (Firefox) | 1 次 |
| 架构文档 | 单机 (2.2.0) | 联邦多机 (4.0.0) | 多次重构 |

---

## 第九部分：待办与未完成事项

### 9.1 明确的待办

1. **发布功能**：`social-auto-upload` 已克隆但未整合
2. **Tailscale 安装**：本机未安装，远程执行依赖 SSH（局域网内可用）
3. **`update_vector_db.py`**：已创建但未提交到仓库
4. **夜间自动化 Git push**：记忆提炼+向量更新完成后自动推送
5. **7kecheng 角色定义**：这台机器当前账号不明，角色未定义

### 9.2 未完全解决的问题

1. **Dashboard 单页过大**：`index.html` 4000+ 行，难维护
2. **app.py 过大**：3000+ 行，包含所有 API
3. **无统一错误处理**：错误散落在各个模块
4. **无统一日志系统**：不同模块日志格式不同
5. **新机部署步骤多**：虽然 init.sh 存在，但环境依赖复杂
6. **跨机调试困难**：不知道另一台机器当前状态

### 9.3 未来想做的

根据系统文档和对话记录推测：

1. **内容发布流水线**（publishing pipeline）— 自动发布到抖音/小红书
2. **电商流水线**（ecom pipeline）— 选品/带货
3. **直播流水线**（live pipeline）— OBS 推流/互动
4. **Trae 智能体集成** — 用 TRAE 写代码
5. **远程命令控制** — 通过 Tailscale/SSH 向其他机器发送任务
6. **内容灵感采集** — 豆包热榜/即梦灵感 → 自动生成视频

---

## 第十部分：总结——系统当前的核心矛盾

### 10.1 结构性问题

```
┌─────────────────────────────────────────────────────┐
│  1. Git 仓库 ≈ 1GB（含浏览器缓存 + 二进制 .so 文件） │
│      → push 超时、冲突不断、新机器克隆慢               │
├─────────────────────────────────────────────────────┤
│  2. 环境依赖不一致（Python 3.9 vs 3.13, orjson 签名） │
│      → 同一代码在不同机器上行为不同                      │
├─────────────────────────────────────────────────────┤
│  3. 配置散落（部分在 agent-sync, 部分在 agent-local）  │
│      → 改配置不知道会影响什么、影响哪台机器               │
├─────────────────────────────────────────────────────┤
│  4. 无统一调度（自动化/手工/远程执行三套机制）            │
│      → 哪个任务在哪个机器上跑、什么时候跑，靠人记         │
├─────────────────────────────────────────────────────┤
│  5. 每台机器没有"全局视角"（各看各的 heartbeat）         │
│      → 机器A不知道机器B现在在干什么                      │
└─────────────────────────────────────────────────────┘
```

### 10.2 根本原因

**不是技术问题，是分层问题。** 代码（code）、配置（config）、运行时数据（data）三层混在一起，没有明确的边界和职责划分。每台机器的独有信息（环境差异、本地配置）和共有信息（任务规则、账号分配）也没有分开管理。

---
*本文档是 AgentOS 系统的"现在是什么"的快照，不包含任何改造方案。方案讨论请基于本文档进行。*

# AgentOS vNext 重构规划与工作计划

> 版本：2026-04-29（第一稿，待审核）  
> 状态：**【待审核】** — 请确认目录结构与工作计划后再进入实施阶段

---

## 一、工作核心要点（实施前必读）

### 程序功能定位

| 模块 | 功能 | 说明 |
|------|------|------|
| `memory_manager` | 记忆提炼与固化 | 从对话日志/WorkBuddy记忆中提炼关键事实，生成L1/L2/L3分层记忆，并检测固化条件推送inbox/memory |
| `kb_manager` | 知识入库 | 接受inbox各分区内容，分类、填写frontmatter、写入知识库对应目录 |
| `inbox_refine` | 收件箱精炼 | 扫描inbox各分区，调用LLM分类，自动归档到知识库 |
| `collect_to_inbox` | 内容采集推送 | 扫描本地素材/记忆，精炼后推送到协同inbox对应分区 |
| `auto_collector` | 自动化采集 | 定时抓取外部信息（网页/RSS/社交媒体等），推送inbox/knowledge |
| `sync_manager` | 同步管理 | 管理agent-os多机git同步，冲突检测与解决 |
| `skill_scanner` | 技能状态扫描 | 扫描所有SKILL_CARD.yaml，报告哪些技能就绪/缺依赖 |
| `vector_db` | 双轨向量库 | local向量库（私有内容）+ global向量库（协同知识），检索时合并 |

### 核心数据流

```
本机采集（raw素材）
    ↓ collect_to_inbox / 用户手动提炼
agent-os-local/materials/refined_for_inbox/
    ↓ 用户确认/AI判断固化条件
agent-sync/03_knowledge/00_stream/inbox/
    ├── knowledge/   ← 外部知识采集
    ├── memory/      ← 记忆固化内容
    ├── tools/       ← 工具提交
    ├── personal/    ← 个人笔记
    └── media/       ← 轻量媒体
    ↓ inbox_refine / kb_manager（AI自动分类）
agent-sync/03_knowledge/[10~60_xxx]/
    ↓ 每台机器自动重建
agent-os-local/vector_db/global/   ← 协同知识向量化
agent-os-local/vector_db/local/    ← 私有内容向量化
    ↓ 检索时合并（先local后global）
用户查询响应
```

### 实施三原则

1. **不破坏现有功能** — 重命名/移动目录前做好兼容或路径别名处理
2. **协同目录轻量化** — 大文件/向量库/本机专属内容绝不进入agent-os/
3. **渐进实施** — 先目录结构，再配置文件，最后代码完善

---

## 二、新目录结构（【待审核】）

### 2.1 agent-os/ 变更说明

```
agent-os/
├── 00_bootstrap/                  # 【保留】初始化脚本
│   ├── init.sh                    # 主安装入口（后续增加HOST_ID读取逻辑）
│   ├── apply-config.sh
│   ├── export_skills.sh
│   └── import_skills.sh
│
├── 01_core/                       # 【扩展】核心配置
│   ├── IDENTITY.md                # 系统身份
│   ├── SOUL.md                    # 智能体灵魂设定
│   ├── USER.md                    # 用户画像
│   ├── mcp.json                   # MCP配置
│   ├── CHANGELOG.md
│   └── HOST_ID.md                 # 【新增★】本机标识与角色
│                                  #  格式：my-macbook_macOS14.4_16GB_master
│
├── 02_skills/                     # 【扩展】技能库
│   ├── _template/                 # 技能模板（含SKILL_CARD.yaml模板）
│   ├── memory_manager/            # 【扩展】记忆管理
│   │   ├── SKILL.md
│   │   ├── SKILL_CARD.yaml        # 【新增★】技能身份证
│   │   ├── daily_digest.py        # 每日提炼
│   │   ├── memory_extractor.py    # 【新增★】记忆固化提取（推送inbox）
│   │   ├── bootstrap_from_memory.py
│   │   ├── agent_memory_init.py
│   │   ├── export_memories.py
│   │   ├── import_memories.py
│   │   ├── memory_cleanup.py
│   │   ├── semantic_search.py
│   │   └── version.json
│   ├── kb_manager/                # 【扩展】知识库管理
│   │   ├── SKILL.md
│   │   ├── SKILL_CARD.yaml        # 【新增★】技能身份证
│   │   ├── kb_ingest.py           # 知识入库（更新inbox路径适配）
│   │   ├── kb_search.py           # 【新增★】知识检索（双轨向量）
│   │   └── version.json
│   ├── inbox_refine/              # 【扩展】收件箱精炼
│   │   ├── SKILL.md
│   │   ├── SKILL_CARD.yaml        # 【新增★】技能身份证
│   │   ├── inbox_refine.py        # 精炼主程序（更新多分区支持）
│   │   ├── llm_classifier.py
│   │   └── version.json
│   ├── collect_to_inbox/          # 【扩展】采集推送
│   │   ├── SKILL.md
│   │   ├── SKILL_CARD.yaml        # 【新增★】技能身份证
│   │   ├── collect_to_inbox.py    # 采集推送（更新本地素材路径）
│   │   └── version.json
│   ├── auto_collector/            # 【扩展】自动采集
│   │   ├── SKILL.md
│   │   ├── SKILL_CARD.yaml        # 【新增★】技能身份证
│   │   └── version.json
│   ├── sync_manager/              # 【扩展】同步管理
│   │   ├── SKILL.md
│   │   ├── SKILL_CARD.yaml        # 【新增★】技能身份证
│   │   └── version.json
│   ├── web_crawler/               # 【保留】网页爬取
│   │   └── SKILL.md
│   └── content_processor/        # 【保留】内容处理
│       └── SKILL.md
│
├── 03_knowledge/                  # 【重构】知识库
│   ├── 00_stream/                 # 【新增★】数据流入区（替代原00_inbox）
│   │   └── inbox/                 # 协同收件箱（唯一进入通道）
│   │       ├── knowledge/         # 外部知识（采集提炼后的MD知识卡）
│   │       ├── memory/            # 记忆固化（本机重要记忆提炼后推入）
│   │       ├── tools/             # 工具提交（TOOL_CARD.yaml+入口脚本）
│   │       ├── personal/          # 个人内容（笔记/会议记录/随手记）
│   │       └── media/             # 轻量媒体（<1MB关键附图）
│   ├── 01_daily/                  # 【保留】每日记录
│   ├── 10_concepts/               # 【保留】概念（含各领域子目录）
│   ├── 20_methods/                # 【保留】方法
│   ├── 30_facts/                  # 【保留】事实/数据
│   ├── 40_references/             # 【保留】参考资料
│   ├── 50_resources/              # 【保留】资源
│   ├── 60_opinions/               # 【保留】观点
│   ├── 90_archive/                # 【保留】归档
│   └── 99_system/                 # 【保留】系统文档
│
├── 04_memory/                     # 【精简】记忆系统（仅保留协同部分）
│   ├── daily_summaries/           # 【保留】每日摘要（可多机共享）
│   ├── long_term/                 # 【保留】长期记忆（经固化的全局记忆）
│   ├── logs/                      # 【保留】运行日志
│   └── memory_backup/             # 【保留】记忆备份
│   # ⚠️【审核点】vector_db 从此处移除，仅在本机local目录维护
│
├── 05_tools/                      # 【扩展】工具层
│   ├── 00_setup/                  # 【保留】环境安装
│   ├── 01_system/                 # 【扩展】系统工具
│   │   └── skill_scanner.py       # 【新增★】技能状态扫描器
│   ├── 02_browser/
│   ├── 03_ocr/
│   ├── 04_media/
│   ├── 05_crawl/
│   └── 06_mobile/
│
├── 06_runtime/                    # 【保留】运行时
│   └── tasks/
│
├── 07_migration/                  # 【保留】迁移工具
│   ├── backup.sh
│   ├── pack.sh
│   └── unpack.sh
│
└── 90_archive/                    # 【保留】全局归档
```

### 2.2 agent-os-local/ 变更说明

```
agent-os-local/
├── materials/                     # 【保留+扩展】本机原始素材
│   ├── audio/                     # 音频
│   ├── video/                     # 视频
│   ├── screenshots/               # 截图
│   ├── web/                       # 网页存档
│   └── refined_for_inbox/         # 【保留】精炼待提交内容（暂存区）
│
├── memory/                        # 【扩展】本机记忆
│   ├── raw/                       # 【保留】原始记忆日志（每日.md）
│   └── long_term/                 # 【新增★】本机长期记忆（固化前暂存）
│
├── knowledge/                     # 【新增★】本机私有知识库（绝不同步）
│   ├── projects/                  # 项目过程记录
│   └── personal/                  # 个人私密笔记
│
├── vector_db/                     # 【重构★】双轨向量库（绝不同步）
│   ├── local/                     # 本机私有内容向量化
│   │   └── chroma/
│   └── global/                    # 协同知识库向量化（从agent-os重建）
│       ├── keyword_index.json
│       └── chroma/
│
├── runtime/                       # 【保留】运行时缓存
│   └── cache/
│
└── machine_info.json              # 【新增★】本机环境描述
                                   #  含：主机名、OS、内存、角色、依赖清单
```

---

## 三、关键审核点（请逐一确认）

| # | 审核项 | 建议方案 | 需用户决策 |
|---|--------|----------|------------|
| ① | `03_knowledge/00_inbox/` → `03_knowledge/00_stream/inbox/` | 用新路径，旧路径做兼容软链接 | 是否保留旧00_inbox或完全迁移？ |
| ② | `04_memory/vector_db` 移除出协同目录 | 迁移到 `agent-os-local/vector_db/global/` | 确认向量库不参与多机同步 |
| ③ | `agent-os-local/knowledge/` 新增 | 存放本机私有知识和项目过程 | 确认路径合适 |
| ④ | `machine_info.json` 格式 | 见下方模板，自动生成+手动补充 | 确认字段范围 |
| ⑤ | SKILL_CARD.yaml 是否所有技能都要加 | 只给自研技能（5个核心）加 | 确认 |

---

## 四、实施任务清单（第二步工作计划）

### Phase 1：目录结构落地（即可执行）
- [x] 创建规划文档（本文件）
- [ ] 创建 `agent-sync/03_knowledge/00_stream/inbox/{knowledge,memory,tools,personal,media}/`
- [ ] 创建 `agent-os-local/knowledge/{projects,personal}/`
- [ ] 创建 `agent-os-local/memory/long_term/`
- [ ] 创建 `agent-os-local/vector_db/{local,global}/chroma/`
- [ ] 创建 `agent-os/01_core/HOST_ID.md`
- [ ] 创建 `agent-os/05_tools/01_system/skill_scanner.py`（如不存在）

### Phase 2：配置文件（目录确认后）
- [ ] 为5个核心技能创建 `SKILL_CARD.yaml`
- [ ] 创建 `agent-os-local/machine_info.json`
- [ ] 创建 `_template/SKILL_CARD.yaml` 模板

### Phase 3：核心代码完善（最终实施）
- [ ] **memory_extractor.py** — 记忆固化提取，检测固化条件，推送inbox/memory/
- [ ] **kb_ingest.py 更新** — 适配新inbox多分区路径
- [ ] **inbox_refine.py 更新** — 支持5分区不同处理逻辑
- [ ] **collect_to_inbox.py 更新** — 扫描agent-os-local/materials/refined_for_inbox/
- [ ] **kb_search.py 新增** — 双轨向量库检索，先local后global合并结果
- [ ] **vector_db_rebuild.py 新增** — 重建向量库（local/global两套）

---

## 五、machine_info.json 模板

```json
{
  "machine": {
    "id": "my-macbook_macOS14.4_16GB_master",
    "display_name": "My MacBook Air M1",
    "role": "master",
    "os": "macOS",
    "os_version": "14.4",
    "memory_gb": 16,
    "cpu": "Apple M1",
    "hostname": "my-macbook.local"
  },
  "environment": {
    "python_path": "~/.workbuddy/binaries/python/envs/agent-os/bin/python3",
    "agent_os_path": "~/workbuddy-agent-os/agent-sync",
    "agent_os_local_path": "~/workbuddy-agent-os/agent-local",
    "shell": "zsh"
  },
  "software": {
    "git_version": "",
    "obsidian": true,
    "workbuddy": true
  },
  "network": {
    "vpn_available": false,
    "notes": ""
  },
  "special_config": {},
  "last_updated": "2026-04-29",
  "auto_update": false
}
```

---

## 六、SKILL_CARD.yaml 标准模板

```yaml
# SKILL_CARD.yaml —— 技能身份证（标准模板）
skill:
  name: "技能名称"
  id: "skill_id"
  version: "1.0.0"
  category: "core-system"  # core-system / user-custom / external
  status: "active"          # active / inactive / experimental
  created: "2026-04-29"
  updated: "2026-04-29"

description:
  short: "一句话描述"
  use_cases: []
  tags: []

ownership:
  master_editor: "my-macbook_macOS14.4_16GB_master"
  readonly_on_other_devices: true

environment:
  os: "macos"
  python_path: "~/.workbuddy/binaries/python/envs/agent-os/bin/python3"
  pip_dependencies: []

setup:
  install_script: ""
  post_check: ""

usage:
  entry_point: "main.py"
  scheduled: ""
  manual_trigger: ""
```

---

> **【审核状态】** 请确认以上目录结构和计划后，回复"确认开始实施"或提出修改意见。  
> 确认后将进入第二步：实际创建目录、生成配置文件、完善核心代码。

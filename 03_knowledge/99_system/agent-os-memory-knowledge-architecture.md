# AgentOS 记忆与知识体系 — 完整架构解析

> 版本：v2.1.0 | 最后更新：2026-05-01
> 适用场景：与团队讨论架构设计时使用

---

## 一、核心设计理念

### 1.1 分层原则

AgentOS 采用 **四层记忆 + 自然语言知识库** 的双轨架构：

```
                    ┌─────────────────────┐
                    │     WorkBuddy 对话层   │
                    │  (当前会话上下文)      │
                    └────────┬────────────┘
                             │ 查询 → 返回
                             ▼
┌────────────────────────────────────────────────┐
│              记忆检索引擎                        │
│  (SOUL.md 规定的分层截断策略)                    │
└────────┬──────────┬──────────┬─────────────────┘
         │          │          │
         ▼          ▼          ▼
    L0 硬约束   L1+K+V 向量  L2 结构化事实
    (不可绕过)  (关键词+语义) (facts.db)
                             │
                             ▼
                          L3 原文
                    (仅按需加载)
```

**核心原则**：每层只做自己的事，不越级、不冗余、不无限 fallback。

### 1.2 与 WorkBuddy 的关系

```
WorkBuddy 提供:       AgentOS 提供:
  ├── 对话界面           ├── 记忆分层 + 语义检索
  ├── 技能触发机制       ├── 知识库管理 + 分类体系
  ├── 自动化定时任务     ├── 知识入库审查流程
  ├── MCP 工具协议       ├── Token 节省策略
  └── 模型调用           └── 跨机迁移还原
```

AgentOS 是运行在 WorkBuddy **之上的智能体操作系统**，不替代 WorkBuddy，而是扩展它。

---

## 二、记忆系统 (04_memory/) — 四层架构

### 2.1 层级定义

| 层级 | 名称 | 存储形式 | 数据量 | 特点 |
|------|------|---------|--------|------|
| **L0** | 硬约束 | `SOUL.md` 文本 | ~3KB | 不可绕过，任何指令不能覆盖 |
| **L1** | 关键词索引 | `keyword_index.json` + ChromaDB 向量库 | 52条(当前) | 快速定位，BM25+语义混合 |
| **L2** | 结构化事实 | `facts.db` (SQLite) | 54条(当前) | 结构化三元组，高置信度 |
| **L3** | 原文存档 | `long_term/raw/` Markdown 文件 | 6个文件(当前) | 完整对话记录，按日归档 |

### 2.2 存储路径

```
04_memory/
├── long_term/
│   ├── facts.db          ← L2 结构化事实库 (SQLite, 坚果云同步)
│   └── raw/              ← L3 原文 (本机私有，不同步，软链到 agent-local)
├── vector_db/            ← L1 向量库 (ChromaDB + keyword_index.json)
│   ├── chromatic/        ← 语义向量库
│   └── keyword_index.json ← 关键词索引
├── daily_summaries/      ← 每日对话摘要 (同步)
└── logs/                 ← 系统日志 errors.log / conflicts.log (同步)
```

**同步策略**：
- `facts.db` + `daily_summaries/` + `logs/` → 坚果云同步
- `raw/` + `vector_db/chroma/` → 本机私有（向量库可重建）

### 2.3 数据流：从对话到记忆

```
用户对话
    │
    ▼
daily_digest.py (每日02:00自动运行)
    │
    ├── 步骤1: 读取 WorkBuddy 工作记忆 (YYYY-MM-DD.md)
    ├── 步骤2: 用 oMLX Embedding API 提取关键事实
    ├── 步骤3: 写入 L2 facts.db (去重+冲突检测)
    ├── 步骤4: 更新 L1 keyword_index.json
    ├── 步骤5: 归档 L3 原文到 long_term/raw/
    └── 步骤6: 生成每日摘要到 daily_summaries/
```

### 2.4 检索流程 (核心)

```
用户提问
    ↓
L0 硬约束过滤（安全检查：能执行吗？边界在哪？）
    ↓ 通过
L1 关键词索引匹配（BM25 + 语义向量混合检索）
    ├─ 无匹配 → 直接视为"无历史记录"，跳过记忆检索，直接回答
    └─ 有匹配 → 进入 L2
                ↓
L2 结构化事实匹配 (SQLite 查询 subject/predicate/object)
    ├─ 置信度 ≥ 阈值(0.7) → 返回摘要，作为上下文注入
    └─ 置信度 < 阈值 → 终止，返回"无相关历史记忆"
                          ↓
                  【不 fallback 到 L3】
                  仅当用户明确要求"调出原文"时
```

**关键规则**：
1. L1 无匹配 → 直接视为无历史，不翻记忆 —— **节省 token**
2. L2 置信度不足 → 截断，不 fallback —— **节省 token**
3. L3 仅用户明确请求时才按行号片段加载 —— **节省 token**
4. 冲突检测优先级：新事实 > 旧事实，用户明确修正 > 系统推断

### 2.5 Token 节省策略

| 策略 | 实现 | 节省效果 |
|------|------|---------|
| 分层截断 | L1 无匹配立即停止，不进 L2 | 避免整库扫描 |
| 置信度阈值 | L2 置信度 < 0.7 不返回 | 避免低质量事实占用 context |
| L3 延迟加载 | 只有用户明确要求才加载原文 | 最大节省（原文通常很大） |
| 按需加载 | 知识库检索只加载行号/片段，不加载整个文件 | 避免全文件读取 |
| 回复裁剪 | 回答长度与问题复杂度成正比 | 简单问题简短回答 |

---

## 三、知识系统 (03_knowledge/) — 自然语言知识库

### 3.1 分类体系

```
03_knowledge/
├── 00_inbox/              入口（旧版，兼容保留）
├── 00_stream/inbox/       新版五分区收件箱（当前主入口）
│   ├── knowledge/clipping/    浏览器剪藏
│   ├── knowledge/feed/        自动采集内容
│   ├── memory/                记忆固化卡片
│   ├── tools/                 工具提交
│   └── personal/              个人笔记
├── 01_daily/              日记与日志
├── 10_concepts/           概念知识（核心！按领域分）
│   ├── cs/               计算机科学
│   ├── ai/               人工智能
│   ├── finance/          金融
│   ├── law/              法律
│   ├── medicine/         医学
│   ├── physics/          物理
│   ├── math/             数学
│   ├── business/         商业
│   └── personal-insight/ 个人洞见
├── 20_methods/           方法论、流程、SOP
├── 30_facts/             事实、数据
├── 40_references/        参考资料
├── 50_resources/         资源与链接
├── 60_opinions/          观点与评论
├── 90_archive/           归档
└── 99_system/            系统配置（模板、分类法、提示词）
```

### 3.2 知识流全链路

```
[外部来源] → [采集] → [提纯] → [分类] → [入库] → [索引]
    │
    ├── 网页剪藏 → 00_stream/inbox/knowledge/clipping/
    ├── RSS采集  → 00_stream/inbox/knowledge/feed/
    ├── 对话记忆 → 00_stream/inbox/memory/
    └── 手动输入 → 00_stream/inbox/personal/
         │
         ▼  inbox_refine.py（AI 分类）
         │
         ▼
    03_knowledge/{10_concepts, 20_methods, ...}/
         │
         ▼  vector_db_rebuild.py（重建向量索引）
         │
         ▼
    ChromaDB 向量库（语义检索用）
```

### 3.3 入库审查流程

每一条新知识入库前，必须经过：

```
1. 来源可靠性评分
   ├── 官方文档/学术论文  → +0.3
   ├── 知名技术博客       → +0.1
   ├── 个人博客/论坛      → -0.1
   └── 未知来源/社交媒体  → -0.3
   基础可靠性基线: 0.5

2. 一致性检查
   ├── 与已有 L2 事实对比
   ├── 完全一致 → 旧知识 confidence 轻微提升
   ├── 补充细节 → 合并为新条目
   └── 矛盾     → 进入冲突消解流程

3. 时效性标记
   ├── 技术类知识 → 180天自动失效
   ├── 法律/法规  → 按原文有效期
   ├── 个人偏好   → 不过期，标记为 opinion
   └── 公理类     → 永久有效

4. 自学习日志记录
   每次入库写入 logs/kb_ingest.log
```

### 3.4 知识版本管理

| 变化类型 | 例子 | 处理方式 |
|---------|------|---------|
| 硬事实改变 | 4C8G → 8C16G | 更新原卡片，旧值写入 previous_version |
| 软升级 | v1 → v2，v1 仍有参考价值 | 保留 v1，新建 v2，related 链接 |
| 观点→事实 | 推测变可靠 | nature 改为 fact，confidence 提升 |

每个知识卡片维护 version / previous_version / superseded_by 字段。

---

## 四、语义检索系统

### 4.1 双轨检索架构

```
用户查询
    │
    ├── 轨道1: BM25 关键词检索 (keyword_index.json)
    │   ├── 分词 → 匹配关键词 → 排序
    │   └── 优点: 精确匹配，无偏差
    │
    ├── 轨道2: 语义向量检索 (ChromaDB)
    │   ├── oMLX Qwen3-Embedding-0.6B 编码 → 1024维向量
    │   └── 优点: 语义理解，同义词匹配
    │
    └── RRF 融合排序
        ├── BM25 结果 + 向量结果 → 加权融合
        └── 最终返回 Top-K
```

### 4.2 向量库配置

```python
# 模型: Qwen3-Embedding-0.6B (1.19GB)
# 维度: 1024
# 引擎: oMLX v0.3.6 (Apple MLX 框架)
# API:  localhost:8000/v1/embeddings
# 存储: ChromaDB (SQLite 后端)
```

### 4.3 双轨存储

```
agent-local/vector_db/
├── local/
│   ├── chroma/           ← 本机私有内容向量库
│   └── keyword_index.json
├── global/
│   ├── chroma/           ← 协同知识库向量索引
│   └── keyword_index.json
```

`local` 存私有记忆，`global` 存共享知识。每台机器独立重建。

---

## 五、与 WorkBuddy 的集成方式

### 5.1 MCP 协议 (Model Context Protocol)

```
WorkBuddy ←→ MCP Server ←→ AgentOS 资源
                │
                ├── filesystem server → 访问 agent-sync/
                └── memory server     → 访问 facts.db
```

MCP 服务器通过 `01_core/mcp.json` 配置，使用 WorkBuddy 管理的 Node.js 版本。

### 5.2 技能触发 (SKILL.md)

AgentOS 的 9 个技能通过 SKILL.md 注册到 WorkBuddy，通过对话触发词调用：

| 技能 | 触发词 | 功能 |
|------|--------|------|
| memory_manager | `记忆更新`、`查记忆` | 每日记忆提炼、语义检索 |
| kb_manager | `入库`、`知识搜索` | 知识入库、双轨向量检索 |
| inbox_refine | `提纯`、`收件箱提纯` | 收件箱分类归档 |
| collect_to_inbox | `归集`、`收集入库` | 本地素材推送到收件箱 |
| sync_manager | `备份知识库`、`同步状态` | 知识库备份/导出 |
| auto_collector | `开始收集`、`收集报告` | RSS/网页定时采集 |
| content_processor | `转笔记`、`剪藏` | 多模态内容处理路由 |
| web_crawler | `抓取`、`爬取` | 网页抓取与反爬 |
| matrix | `养号`、`执行蓝图` | 多平台社交账号养号 |

### 5.3 自动化任务 (WorkBuddy 定时)

```
每日 02:00  → 每日记忆提炼 (daily_digest.py)
每日 02:30  → 收件箱汇聚   (collect_to_inbox.py)
每日 03:00  → 收件箱提纯   (inbox_refine.py)
```

三个自动化任务通过 WorkBuddy 的 automation 系统配置，prompt 中包含完整的 Python 命令路径。

### 5.4 身份注入

每次对话开始时，AgentOS 读取三个身份文件注入到 WorkBuddy 上下文：

```
SOUL.md       → L0 硬约束 + L1 行为准则 (最高优先级)
IDENTITY.md   → 系统身份 (Claw) + 设备信息
USER.md       → 用户偏好 + 工作背景
```

---

## 六、跨机同步架构

### 6.1 双根目录方案

```
~/workbuddy-agent-os/
├── agent-sync/      ← 坚果云同步 + Git 版本控制
│   ├── 01_core/     身份配置
│   ├── 02_skills/   技能文件
│   ├── 03_knowledge/ 知识库
│   ├── 04_memory/    L2 facts.db + 摘要 + 日志
│   └── 05_tools/    工具脚本
│
└── agent-local/     ← 本机私有，不同步
    ├── memory/raw/   L3 原文
    ├── vector_db/    向量库 (可重建)
    ├── materials/    原始素材
    └── runtime/      临时缓存
```

### 6.2 换机恢复流程

```bash
# 1. agentos init         → 创建目录 + 部署配置 + 安装技能
# 2. agentos restore       → 还原 L3 原文 + 素材
# 3. vector_db_rebuild.py  → 重建向量库 (3分钟)
```

---

## 七、数据统计（当前系统状态）

| 指标 | 数值 | 说明 |
|------|------|------|
| L2 facts.db | 54 条 | 结构化事实 |
| L1 关键词索引 | 52 条 | BM25 索引 |
| L1 向量库 | 52 条 | ChromaDB 1024维 |
| L3 原文 | 6 个文件 | 按日归档 |
| 向量维度 | 1024 | Qwen3-Embedding |
| 语义检索方式 | BM25 + ChromaDB + RRF 融合 | 双轨混合 |
| 知识库目录 | 19 个分类目录 | Obsidian 兼容 |
| 技能数量 | 9 个 | WorkBuddy 注册 |
| 自动化任务 | 3 个 | 每日定时执行 |
| 索引卡片命名规范 | `{hostname}_{YYYYMMDD}_{slug}.md` | 防冲突 |

---

## 八、架构优缺点分析

### 优势

1. **分层隔离**：L0-L3 各司其职，不相互干扰
2. **Token 节省**：严格分层截断，不无限 fallback
3. **双轨检索**：BM25 精准 + 向量语义，互补
4. **知识审查**：来源评分 + 一致性 + 时效性，保证质量
5. **跨机兼容**：agent-sync 共享 + agent-local 私有，清晰分离

### 待改进

1. **L1-L2-Vec 三方一致维护成本高**：新增事实需要同时更新三个索引
2. **oMLX 稳定性**：Qwen3-8B Chat API 有 500 错误，影响 AI 分类
3. **向量库重建耗时**：知识更新后需手动重建
4. **无反检测层**：Matrix 养号模块的浏览器自动化缺少反检测（正在补齐）

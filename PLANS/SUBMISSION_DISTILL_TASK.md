# Task: submission_distill 内容蒸馏任务 🧪
> **用途**: 将 `01_submissions/` 中积压的原始采集内容自动蒸馏为结构化报告
> **建议添加至**: `ORACLE.yaml → tasks:`
> **基于数据**: 2026-05-18 至 06-08 共 70 篇袁本初文章（238KB）

---

## 一、任务定义（YAML 片段）

```yaml
- name: submission_distill
  description: "蒸馏 01_submissions 原始文章为分类摘要+元数据报告"
  schedule: 0 5 * * 1
  # ^ 每周一早5点（赶在 inbox_refine 4点+vector_rebuild 3:30 之前）
  on_machines:
  - chengzigedeAir
  action: distill
  params:
    source_dir: "01_submissions"
    output_dir: "03_knowledge/00_stream"
    batch_size: 10
    max_age_days: 14
    # 摘要模式: llm — 用 AI 写自然语言摘要
    #          extract — 仅提取关键词和元数据（快速版）
    mode: llm
```

也可拆为两个子任务，一个做关键词提取，一个做 AI 摘要：

```yaml
- name: submission_metadata
  description: "提取 submissions 元数据和关键词索引（快速，每天跑）"
  schedule: 0 5 * * *
  on_machines:
  - chengzigedeAir
  action: distill
  params:
    mode: extract
    source_dir: "01_submissions"
    output_dir: "04_memory/long_term"

- name: submission_abstract
  description: "提交物 AI 摘要生成（耗时长，每周跑）"
  schedule: 0 5 * * 1
  on_machines:
  - chengzigedeAir
  action: distill
  params:
    mode: llm
    source_dir: "01_submissions"
    output_dir: "03_knowledge/00_stream"
    batch_size: 10
```

---

## 二、运行时数据流

```
01_submissions/*.md
  │
  ├── step 1: extract_metadata (每天)
  │   ├── 解析文件名 → {date, author, category, seq}
  │   ├── 解析 front matter → {yaml fields}
  │   ├── 提取标签 → keywords[]
  │   ├── 计算字数、行数
  │   └── 更新 keyword_index.json
  │
  ├── step 2: group_by_category (每周)
  │   ├── 按分类聚类
  │   ├── 按日期排序
  │   └── 计算跨分类交叉引用
  │
  ├── step 3: generate_summary (每周)
  │   ├── 每个分类读最新一篇代表性文章
  │   ├── LLM 生成 200-300 字摘要
  │   ├── 提炼核心概念
  │   └── 输出到 03_knowledge/00_stream/
  │
  └── step 4: aggregate (每周)
      ├── 生成跨分类主题网络
      ├── 更新统计表
      └── 生成 JSON 摘要输出
```

---

## 三、首次执行时的预期输出

| 输出文件 | 内容 |
|:---------|:-----|
| `03_knowledge/00_stream/YYYY-MM_submissions_distillation.md` | 全量蒸馏报告（分类摘要+元数据+主题网络） |
| `04_memory/long_term/keyword_index_YYYYMMDD.json` | 更新后的关键词索引 |
| 同时更新 | `02_skills/kb_manager/` 中的分类知识条目 |

### 首次处理（基于当前 70 篇）统计预期

| 分类 | 篇数 | 预计摘要长度 | 代表标签 |
|:-----|:----:|:-----------:|:---------|
| 社会观察 | 22 | ~2,000字 | 底层逻辑、阶层流动、AI、就业、教育内卷 |
| 政治分析 | 18 | ~1,800字 | 地缘政治、中美关系、大国博弈、社会治理 |
| 经济分析 | 14 | ~1,600字 | 财务自由、资产配置、被动收入、投资 |
| 哲学思考 | 10 | ~1,400字 | 认知升维、思维方式、方法论、阶层跃迁 |
| 历史解读 | 6 | ~1,200字 | 历史周期律、文明升维、制度分析 |

### 跨分类主题网络

```
认知升维 ──→ 社会观察（阶层流动）
   │
   ├──→ 经济分析（财务自由系统）
   │
   ├──→ 政治分析（大国博弈底层逻辑）
   │
   └──→ 历史解读（文明升维）
```

---

## 四、与现有 ORACLE 任务的依赖关系

| 现有任务 | 时间 | 与 distill 的关系 |
|:---------|:----:|:-----------------|
| `collect_profiles` | 03:00 每天 | ✅ 前置——先采集后蒸馏 |
| `vector_rebuild` | 03:30 每天 | ⚠️ 错峰——distill 改 05:00 |
| `knowledge_inbox_refine` | 04:00 每天 | ⚠️ 错峰——distill 改 05:00 |
| `git_sync` | 每15分钟 | ✅ 独立，不冲突 |

---

## 五、关键技术决策

### 为什么每天 extract 但每周 generate？

- **extract**（元数据提取）：纯文本处理，每篇 < 0.1秒，70篇 < 10秒，可以每天跑
- **generate**（AI摘要）：每批10篇需要 LLM 调用，10-30秒/批，7批 ~2分钟，每周一次就够了

### batch_size=10 的考量

- 10篇恰好是平均一天的产量
- 一批的 token 量约 35KB * 10 = 350KB，在 LLM 上下文窗口内
- 分批处理可以防止单批次超时

### mode=llm vs mode=extract 的区别

- `extract`：纯文本的 shell 脚本就能完成（提取元数据、关键词、字数）
- `llm`：需要 LLM 调用（写摘要、提炼概念、跨分类分析）

---

## 六、实现建议

distill action 的实现可以放在 `05_tools/07_matrix/scripts/` 下：

```bash
# scripts/distill.sh — 内容蒸馏脚本
# 用法: bash distill.sh <mode> <source_dir> <output_dir> [batch_size]

mode=${1:-extract}
source_dir=${2:-01_submissions}
output_dir=${3:-03_knowledge/00_stream}
batch_size=${4:-10}

case "$mode" in
  extract)
    # 遍历所有 .md，提取 front matter + 文件名元数据
    # 输出 keyword_index.json
    ;;
  llm)
    # 按分类聚类 → 每类取最新篇 → LLM 摘要 → 写报告
    ;;
esac
```

或者封装成 `mc distill` CLI 子命令，统一走 CommandBus。

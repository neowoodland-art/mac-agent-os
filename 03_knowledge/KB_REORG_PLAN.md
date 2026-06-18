# 知识库全面整理执行计划

> 创建: 2026-06-17 23:25 | 状态: ⏳ 待确认
> 目标: 364个文件 → 约100个唯一内容文件，全部正确归类

---

## 一、原始设计（来自 README.md + CORE-ARCHITECTURE.md）

原始知识库设计为：
- `00_inbox/` — 待提纯收件箱
- `01_submissions/` — 待归集提交箱（按来源分目录）
- `10_concepts/` — 概念知识
- `20_methods/` — 方法技能
- `30_facts/` — 事实数据
- `40_references/` — 参考资料（含系统工具引用）
- `50_resources/` — 资源索引
- `60_opinions/` — 个人观点
- `90_archive/` — 归档
- **没有 `99_system/` 和 `04_ops/`** — 这两个目录是后来新增的

`04_ops/` 不在原始设计中，是后来加的 → 移空后可删除。

---

## 二、审计发现

### 问题1: 日期前缀副本（~220个冗余文件）

`20_methods/` 下有大量同一内容的日期版本：
```
2026-05-16_xxx.md              ← 原始版本
2026-05-17_2026-05-16_xxx.md   ← 第一次复制（内容可能微调）
2026-06-01_2026-05-17_...xxx.md ← 第二次复制
2026-06-02_...xxx.md            ← 第三次复制
...
```

**结论**：文件名越短=越早的版本，文件名越长=被AI采集系统多次重新采集。内容可能相同或略有差异。**保留内容最完整的版本**（通常是最新日期最长的），其余删除，不存档。

### 问题2: 系统文档散落在 3 个目录

| 当前路径 | 应移至 | 原因 |
|:---------|:-------|:-----|
| `04_ops/matrix/` (6个) | `99_system/matrix/` | 全部是矩阵系统架构文档 |
| `20_methods/Camoufox_集成修复记录.md` (+5个副本) | `99_system/matrix/` | 系统集成记录 |
| `20_methods/原子化登录管理模块_auth_manager.md` (+5个副本) | `99_system/matrix/` | 登录系统模块 |
| `20_methods/统一升级引擎_agentos_upgrade.md` (+5个副本) | `99_system/` | 升级引擎 |
| `20_methods/cross-domain.md` 等4协议(+各5副本) | `99_system/protocols/` | 协议，但已存在更完整版本 |
| `40_references/matrix-sms-verification.md` (+7个副本) | `99_system/matrix/` | 系统引用文档 |
| `40_references/cloakbrowser-integration.md` (+7个副本) | `99_system/references/` | 系统引用文档 |
| `40_references/peekaboo-v3-integration.md` (+7个副本) | `99_system/references/` | 系统引用文档 |

### 问题3: 协议文档版本对比

| 协议 | 99_system版本 | 20_methods副本版本 | 结论 |
|:-----|:-------------|:-------------------|:-----|
| cross-domain.md | 2001 bytes | 1248 bytes | **99_system更完整，保留** |
| knowledge-review.md | (待查) | (待查) | 保留99_system |
| meta-thinking.md | (待查) | (待查) | 保留99_system |
| stuck-intervention.md | (待查) | (待查) | 保留99_system |

**这些协议文档有没有用？** 有——`cross-domain.md` 是跨域联想协议，`knowledge-review.md` 是知识入库审查流程。这些是智能体思考框架的一部分。建议保留在 `99_system/protocols/`。

---

## 三、执行步骤

### Step 1: 扩展 99_system/ 结构

```bash
mkdir -p 99_system/matrix
mkdir -p 99_system/references
```

### Step 2: 移动系统文档

从 `04_ops/matrix/` → `99_system/matrix/`:
```bash
mv 04_ops/matrix/*.md 99_system/matrix/
```

从 `20_methods/` 去重后移入 `99_system/`:
- 以 `_集成修复记录.md` 结尾的 → `99_system/matrix/`
- 以 `auth_manager.md` 结尾的 → `99_system/matrix/`
- 以 `agentos_upgrade.md` 结尾的 → `99_system/`
- 协议类（cross-domain, knowledge-review 等）→ 删除（已有更新版本在 `99_system/protocols/`）

从 `40_references/` 移入 `99_system/`:
- `matrix-sms-verification.md` 类 → `99_system/matrix/`
- `cloakbrowser`, `peekaboo` → `99_system/references/`

### Step 3: 删除日期前缀副本

规则：同一内容只保留**文件名最长的那个版本**（最新日期），其余删除。
涉及约 200 个文件，主要在 `20_methods/` 和 `40_references/`。

### Step 4: 删除废弃目录

```bash
rmdir 04_ops/  # 移空后删除
```

### Step 5: 更新 README

更新 `03_knowledge/README.md` 的文件计数和索引。

### Step 6: 写系统指令文件

在 `99_system/` 下建 `AI_READING_GUIDE.md`，告诉智能体：
- 每次启动先读 `99_system/AI_READING_GUIDE.md`
- 按任务类型查阅对应目录
- 知识库使用规范

---

## 四、预览：清理后的结构

```
03_knowledge/
├── 00_README.md              ← 顶层索引（已建）
├── 00_inbox/                 ← 不变
├── 01_submissions/           ← 不变（23个采集文件）
├── 10_concepts/              ← 不变（19个概念文件）
├── 20_methods/               ← 只保留纯方法论（约30个文件）
│   └── ai-video-system/      ← 完整保留（19章）
├── 30_facts/                 ← 不变
├── 40_references/            ← 只保留非系统引用
├── 50_resources/             ← 不变
├── 60_opinions/              ← 不变
├── 90_archive/               ← 不变
├── CHANGELOG.md              ← 不变
└── 99_system/                ← 扩展
    ├── AI_READING_GUIDE.md   ← 🆕 系统指令
    ├── README.md             ← 已建
    ├── architecture/         ← 6个文件
    ├── matrix/               ← ← 6+3个文件（从04_ops + 20_methods + 40_references 移入）
    ├── references/           ← ← 2个文件（从40_references 移入）
    ├── dashboard/            ← 设计文档
    ├── agentos-upgrade.md    ← ← 升级引擎（从20_methods移入）
    ├── pipelines/            ← 1个文件
    ├── prompts/              ← 1个文件
    ├── protocols/            ← 4个文件
    ├── taxonomies/           ← 2个文件
    ├── templates/            ← 4个文件
    └── archive/              ← 3个文件
```

---

## 五、确认事项

1. **日期副本去重原则**：保留最长文件名（最新日期），其余直接删除，不归档。✅ 你已确认
2. **`04_ops/` 移空后删除**：原设计没有这个目录 ✅ 你已确认
3. **协议文档**：`99_system/protocols/` 版本更完整，`20_methods/` 的副本删除
4. **`40_references/` 移走系统引用后**：只剩空目录，保留（原设计有此目录）

确认后我执行，预计半小时完成。

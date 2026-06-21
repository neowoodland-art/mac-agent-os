---
name: inbox_refine
version: 1.1.0
description: 知识库收件箱提纯——每日将 00_inbox/ 内容分类归档到知识库，更新首页统计和变更日志
triggers:
  - 提纯
  - 收件箱提纯
  - 归档inbox
  - inbox refine
  - 整理收件箱
  - 归档知识
  - 提纯收件箱
---

# Inbox Refine 技能

## 概述

将 `00_inbox/` 中的原始内容按知识属性分类，应用模板后归档到对应目录，并更新知识库首页和变更日志。

## 触发条件

- 每日凌晨 3:00 自动执行（WorkBuddy 自动化）
- 手动说"提纯"、"整理收件箱"、"inbox refine"

## 工作流

```
1. 扫描 00_inbox/ 所有 .md 文件
2. 逐个读取 → 分析内容
3. 确定分类：
   - nature：fact/method/concept/reference/data/opinion/quote/axiom/regulation
   - domain：从 99_system/taxonomies/domains.md 选择 1-3 个
   - confidence：根据 source_type 评分
4. 应用对应模板（99_system/templates/）
5. 生成 ID：KB-YYYYMMDD-NNN
6. 写入目标目录
7. 删除 00_inbox/ 原文件
8. 更新 README.md 统计
9. 更新 CHANGELOG.md
```

## 分类决策逻辑

### nature 判定
| 内容特征 | nature | 目标目录 |
|----------|--------|----------|
| 已验证的客观事实 | fact | 30_facts/ |
| 可操作的步骤/教程 | method | 20_methods/ |
| 原子概念/基础原理 | concept | 10_concepts/ |
| 公认基础原理 | axiom | 10_concepts/ |
| 法律法规/制度 | regulation | 30_facts/ |
| 论文/文档/外部资料 | reference | 40_references/ |
| 测试数据/基准结果 | data | 30_facts/ |
| 主观看法/推测 | opinion | 60_opinions/ |
| 他人原话/语录 | quote | 60_opinions/ |

### confidence 评分
| source_type | confidence |
|-------------|-----------|
| official_doc | 0.9 |
| literature | 0.8 |
| experiment | 0.7 |
| personal_exp | 0.5 |
| social_media | 0.3 |
| unknown | 0.4 |

## 去重规则

1. 读取目标目录已有文件，提取 title 和 tags
2. 标题相似度 > 0.8 → 合并（补充细节，不新建）
3. 内容完全一致 → 跳过，记录日志
4. 同一事实新旧矛盾 → 新事实覆盖，旧值写入 previous_version

## Frontmatter 模板

```yaml
---
id: KB-YYYYMMDD-NNN
title: "__标题__"
type: __concept/fact/method/opinion/reference__
status: published
nature: __fact/method/concept/...__
domain: [__领域1__, __领域2__]
subdomain: []
tags: [__标签1__, __标签2__]
confidence: 0.8
source: "__来源URL或出处__"
source_type: __official_doc/literature/personal_exp/...__
date_created: YYYY-MM-DD
date_modified: YYYY-MM-DD
version: 1
previous_version: ""
superseded_by: ""
---
```

## 更新首页统计

读取 `03_knowledge/README.md`，替换 `## 📊 知识统计` 下的表格：
- 扫描各目录下 .md 文件数量
- 找出每个目录最近修改的文件日期
- 更新总计行

## 更新变更日志

在 `03_knowledge/CHANGELOG.md` 顶部追加：
```markdown
## YYYY-MM-DD

### 归档
- [nature] title → 目标目录 (KB-YYYYMMDD-NNN)
- ...
```

## 依赖

| 包/工具 | 用途 | 安装状态 |
|---------|------|----------|
| file_read/file_write | 读写文件 | ✅ 内置 |
| python3 | 脚本执行 | ✅ managed |
| oMLX + Qwen3-8B-MLX-4bit | 本地 LLM 辅助分类（可选） | ✅ 已安装 |

## 路径约定

| 项目 | 路径 |
|------|------|
| 收件箱 | `~/workbuddy-agent-os/agent-sync/03_knowledge/00_inbox/` |
| 知识库根 | `~/workbuddy-agent-os/agent-sync/03_knowledge/` |
| 首页 | `~/workbuddy-agent-os/agent-sync/03_knowledge/README.md` |
| 变更日志 | `~/workbuddy-agent-os/agent-sync/03_knowledge/CHANGELOG.md` |
| 模板 | `~/workbuddy-agent-os/agent-sync/03_knowledge/99_system/templates/` |
| 分类表 | `~/workbuddy-agent-os/agent-sync/03_knowledge/99_system/taxonomies/` |
| 中文映射 | `~/workbuddy-agent-os/agent-sync/03_knowledge/99_system/taxonomies/folder-aliases.json` |

## 错误处理

- 无法分类的内容 → 保留在 00_inbox/，添加标签 `#待分类`，记录日志
- 模板应用失败 → 使用最小 Frontmatter（id/title/nature/date_created）
- 首页更新失败 → 只记录日志，不阻断归档流程

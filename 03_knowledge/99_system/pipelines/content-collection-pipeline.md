---
id: KB-20260503-002
title: "内容收集全链路规范 v2.0"
type: method
status: active
nature: method
domain: personal-management
subdomain: [知识管理, 自动化]
tags: [pipeline, 收集, 收件箱, 提纯, 多机同步, 规范]
confidence: 1.0
source: "AgentOS 系统设计"
source_type: system
date_created: 2026-05-03
date_modified: 2026-05-03
version: 2
aliases: [收集链路规范 v2]
keywords: [收集, 收件箱, 提纯, 提交, 知识入库, 素材, 采集路由]
summary: "统一的内容收集全链路规范——所有机器统一流程，按收集子类型路由，区分知识类与素材类，支持即时与批量双模式"
related: ["KB-20260503-001"]
previous_version: "KB-20260503-002 (v1)"
superseded_by: ""
---

# 内容收集全链路规范 v2.0

> 最后更新：2026-05-03
> 所有机器统一流程，不区分主从。收集内容统一进提交箱，按类型路由处理。

---

## 一、核心设计原则

```
1. 所有机器统一流程 → 角色切换不影响
2. 收集内容先进提交箱 → 再决定即时还是批量
3. 收集子类型决定提取方式 → 不是所有收集都是为了知识
4. 知识类 vs 素材类分流 → 素材不进提纯流水线
5. 即时处理 = 提交箱→收件箱→提纯→返回结果
6. 批量处理 = 提交箱→(定时)→收件箱→提纯→入库
```

---

## 二、目录体系

| 目录 | 角色 | 谁使用 |
|------|------|--------|
| `01_submissions/` | **收集提交箱**（所有机器收集的内容统一放这里） | 所有机器 |
| `00_inbox/` | **待提纯收件箱**（等待 AI 分类入库） | 提纯时使用 |
| `10_concepts/` ~ `60_opinions/` | **知识归档** | 提纯后写入 |
| `agent-local/materials/` | **素材仓库**（背景音乐/截图/原图/视频片段，不提纯） | 直接存储 |

### submissions 结构

```
01_submissions/
├── 20260503_social-wisdom_video.md      ← 机器A 收集的抖音视频
├── 20260503_article_xxx.md               ← 机器B 收集的文章
└── 20260503_bg-music_yyy.md              ← 收集的背景音乐（素材类）
```

> 不分子目录，所有机器平等。文件名 `{YYYYMMDD}_{slug}_{source_type}.md`

---

## 三、两个入口：知识 vs 素材

整个系统只有 **两个入口命令**，用户通过关键词区分意图：

```
"收集这个..." → 知识类采集 → 走完整 pipeline（提交箱→提纯→入库）
"收集素材..." → 素材类分析 → 直存 materials/（不经过提纯流水线）
```

### 入口对比

| 你说 | 含义 | purpose | 去向 | 后续 |
|------|------|---------|------|------|
| `收集这个视频` | 知识收集 | knowledge | → 01_submissions/ | 等待提纯入库 |
| `收集素材` | 素材分析 | material | → materials/ | 不经过提纯 |
| `收集素材，视频结构` | 素材+分析维度 | material | → materials/ + AI分析结果 | 不经过提纯 |

### 素材子类型（分析维度）

"收集素材"后面可以跟分析维度，决定 AI 怎么分析这个视频/内容：

| 你说 | collect_subtype | AI 分析内容 | 输出 |
|------|----------------|-------------|------|
| `收集素材` | default | 仅保存原始内容 | 文件 + 基础信息 |
| `收集素材，视频结构` | video-structure | 分析起承转合、节奏分段、内容框架 | analysis 报告 |
| `收集素材，拍摄脚本` | shooting-script | 提取/重建拍摄脚本、分镜描述 | script 文件 |
| `收集素材，镜头运镜` | camera-movement | 分析镜头类型（推拉摇移跟）、构图方式 | analysis 报告 |
| `收集素材，前三秒钩子` | opening-hook | 分析开头 3 秒的吸引点、悬念设置 | analysis 报告 |
| `收集素材，悬疑点` | suspense-points | 提取内容的悬疑设计、反转点、冲突点 | analysis 报告 |
| `收集素材，文案结构` | copy-structure | 分析文案的黄金圈、痛点-方案-结果等框架 | analysis 报告 |

### 完整采集路由表（v2.0 合并版）

| 入口关键词 | 内容类型 | 子类型 | 用途 | 输出 |
|-----------|----------|--------|------|------|
| `收集这个` | douyin-video | default | 知识 | → 01_submissions/ |
| `收集这个` | douyin-video | subtitle | 知识 | → 01_submissions/ |
| `收集这个` | webpage | default | 知识 | → 01_submissions/ |
| `收集这个` | webpage | fulltext | 知识 | → 01_submissions/ |
| `收集这个` | audio | transcription | 知识 | → 01_submissions/ |
| `收集这个` | audio | summary | 知识 | → 01_submissions/ |
| `收集素材` | douyin-video | default（保存） | 素材 | → materials/videos/ |
| `收集素材` | douyin-video | video-structure | 素材 | → materials/ + analysis |
| `收集素材` | douyin-video | shooting-script | 素材 | → materials/ + script |
| `收集素材` | douyin-video | camera-movement | 素材 | → materials/ + analysis |
| `收集素材` | douyin-video | opening-hook | 素材 | → materials/ + analysis |
| `收集素材` | douyin-video | suspense-points | 素材 | → materials/ + analysis |
| `收集素材` | douyin-video | copy-structure | 素材 | → materials/ + analysis |
| `收集素材` | audio | raw | 素材 | → materials/audios/ |
| `收集素材` | image | default | 素材 | → materials/images/ |
| wechat-article | **默认** | 提取标题+正文 | 知识 | → 01_submissions/ |
| audio | `转文字` | 语音转文字（whisper） | 知识 | → 01_submissions/ |
| audio | `汇总` | 提取内容摘要 | 知识 | → 01_submissions/ |
| audio | `原文件` | 仅保存音频文件 | 素材 | → materials/ |
| image | **默认** | 保存原图 + OCR 文字（如有） | 素材 | → materials/ |
| text/note | **默认** | 保存原文 | 知识 | → 01_submissions/ |

### 3.4 用户指令与路由映射

| 你说 | 路由结果 |
|------|----------|
| `收集这个视频` | 自动识别来源 → 默认提取（标题+描述+标签）→ 知识类 |
| `收集这个视频的字幕` | douyin-video + 字幕 → 知识类 |
| `收集这个视频的背景音乐` | douyin-video + 背景音乐 → 素材类 |
| `收集这个视频的音频` | douyin-video + 音频下载 → 素材类 |
| `收集这个视频的截图` | douyin-video + 截图 → 素材类 |
| `总结这个视频` | douyin-video + AI 总结 → 知识类 |
| `收集这个链接` | 自动识别 → 默认提取 → 知识类 |
| `收集这篇文章` | webpage + 默认 → 知识类 |
| `收集这个音频` | audio + 默认（转文字）→ 知识类 |
| `收集这个音频的背景音` | audio + 原文件 → 素材类 |
| `收集这张图片` | image + 默认 → 素材类 |
| `提取这首歌` | audio + 原文件 → 素材类 |

### 3.5 收集输出格式

**知识类** 输出到 `01_submissions/`：

```markdown
---
title: "原标题"
collect_type: "douyin-video"
collect_subtype: "default"  # default / subtitle / audio / screenshot / summary
purpose: "knowledge"         # knowledge / material
source_url: "原始链接"
source_author: "作者名"
source_date: "发布日期"
collected_by: "机器名"
collected_date: "2026-05-03"
status: submitted
tags: [标签1, 标签2]
---

## 原文信息

{提取的主要内容}

## 原始链接

{source_url}
```

**素材类** 输出到 `agent-local/materials/`：

```markdown
---
title: "素材名称"
collect_type: "douyin-video"
collect_subtype: "bgm"
purpose: "material"
source_url: "来源链接"
collected_date: "2026-05-03"
---
素材文件：{文件路径}
用途说明：{背景音乐/截图/原图等}
```

---

## 四、处理模式：即时 vs 批量

| 模式 | 触发方式 | 流程 |
|------|----------|------|
| **即时** | `提纯这个` | COLLECT → 01_submissions → 00_inbox → REFINE → 返回结果 |
| **批量** | 定时（每日 02:00） | COLLECT → 01_submissions →（等待）→ STAGE → REFINE → STORE → INDEX |

### 4.1 即时模式

```
你："收集这个视频，提纯它"
  ↓
① COLLECT → 提取内容 → 写入 01_submissions/
  ↓
② 即时转入 00_inbox/
  ↓
③ REFINE → AI 分类 → 写入对应目录
  ↓
④ 返回：内容和分类结果给你
```

### 4.2 批量模式

```
你："收集这个视频"
  ↓
① COLLECT → 提取内容 → 写入 01_submissions/（等待）
  ↓
  （凌晨 02:00 定时任务）
  ↓
② STAGE → 01_submissions/ → 00_inbox/
  ↓
③ REFINE → AI 分类 → 写入对应目录 + 更新索引
```

### 4.3 触发词速查

| 你说 | 模式 | 说明 |
|------|------|------|
| `收集这个...` | 批量 | 进提交箱，等定时处理 |
| `收集这个...并提纯` | 即时 | 进提交箱 → 立即提纯 → 返回结果 |
| `提纯这个` | 即时 | 对刚收集的内容立即提纯 |
| `归集` | 批量触发 | 手动触发批量归集流程 |
| `提纯所有` | 批量触发 | 手动触发批量提纯 |

---

## 五、完整流程示例

### 场景：即时收集抖音视频并提纯

```
你："收集这个视频并提纯"
  ↓
我识别: 抖音视频 → 默认提取（标题+描述+标签）
  ↓                           ← 如果链接是纯音频则走 audio 路由
判断: 知识类
  ↓
写入 01_submissions/20260503_social-wisdom_douyin-video.md
  ↓
标记为即时 → 立即转入 00_inbox/
  ↓
运行 REFINE:
  ├── AI 判定 nature:concept / domain:personal-management
  ├── 套用 concept-card 模板
  └── 写入 10_concepts/social-wisdom-10-rules.md
  ↓
返回结果:
  "已收集并提纯完成。内容已存入 10_concepts/ 目录。
   共 9 条社会智慧，分类为 概念/个人管理。"
```

### 场景：收集背景音乐（素材类）

```
你："收集这个视频的背景音乐"
  ↓
我识别: 抖音视频 → 音频提取
  ↓
判断: 素材类（不是知识）
  ↓
下载音频文件 → 保存到 agent-local/materials/audios/
  ↓
创建素材记录 → agent-local/materials/audios/20260503_bgm_xxx.md
  ↓
返回结果:
  "背景音乐已保存到 materials/audios/ 目录。
   文件名：20260503_bgm_xxx.mp3"
```

### 场景：批量收集一篇知乎文章

```
你："收集这篇文章"
  ↓
我识别: 网页文章 → 默认提取
  ↓
判断: 知识类
  ↓
写入 01_submissions/20260503_zhihu-article_webpage.md
  ↓
返回结果:
  "已收集。文章将在下次定时提纯时处理（每日 02:00）。
   如需立即处理，请说：提纯这个"
```

---

## 六、系统状态速查

| 你说 | 返回 |
|------|------|
| `收集状态` | 提交箱 N 条待处理 / 收件箱 N 条待提纯 / 上次提纯时间 |
| `待处理` | 列出提交箱中所有待归集的内容 |
| `待提纯` | 列出收件箱中所有待提纯的内容 |

---

## 七、本规范与现有技能的关系

| 技能 | 角色 | 说明 |
|------|------|------|
| `content_processor` | 采集入口 | 实现 COLLECT 节点的路由逻辑（视频/音频/文章/图片分发） |
| `collect_to_inbox` | 归集 | 实现 STAGE 节点（01_submissions/ → 00_inbox/） |
| `inbox_refine` | 提纯 | 实现 REFINE 节点（AI 分类 + 模板 + 入库 + 索引） |

> 当前 `content_processor` 技能已存在，但路由表尚未按本规范更新。
> `collect_to_inbox` 和 `inbox_refine` 技能已按此流程工作。

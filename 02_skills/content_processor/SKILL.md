---
name: content_processor
version: 1.0.0
description: 统一内容处理入口——视频/文章/语音/社交多种处理模式路由，整合 bilinote/web-clipper/voice-summary/social-collector
triggers:
  - 转笔记
  - 摘字幕
  - 视频摘要
  - 视频大纲
  - 剪藏
  - 摘抄
  - 文章摘要
  - 提炼
  - 翻译
  - 转文字
  - 语音摘要
  - 采集
  - 采集摘要
  - 处理内容
---

# Content Processor Skill（统一内容处理入口）

## 概述

统一的内容处理入口技能，根据触发词路由到具体的子技能（bilinote/web-clipper/voice-summary/social-collector）执行。
本技能不替代子技能，而是作为**统一调度层**，简化用户操作。

## 触发词路由表

### 视频处理 → 路由到 `bilinote`

| 触发词 | 执行动作 |
|--------|----------|
| 转笔记, 视频笔记, vnote | 完整字幕转写 + AI 大纲 + 关键帧 + 时间戳 |
| 摘字幕, 字幕 | 仅语音转文字，不做 AI 提炼 |
| 视频摘要, 摘要 | 提炼 3 点核心观点 |
| 视频大纲, 大纲 | 按层级整理内容大纲 |

### 文章/图文处理 → 路由到 `web-clipper`

| 触发词 | 执行动作 |
|--------|----------|
| 剪藏, clip | 网页正文提取，去广告评论区，存 Markdown |
| 摘抄, 全文保存, 存全文 | 保留原文全部文字 |
| 文章摘要, 概括 | 3 句话概括核心内容 |
| 提炼, extract | 提取所有方法论/步骤/结论，编号整理 |
| 翻译 | 翻译成中文（或指定语言） |

### 语音处理 → 路由到 `voice-summary`

| 触发词 | 执行动作 |
|--------|----------|
| 转文字, 语音转字 | Whisper 逐字稿（带时间戳） |
| 语音摘要, 录音摘要, vsummary | 去口头禅，提炼核心观点 |

### 跨平台采集 → 路由到 `social-collector`

| 触发词 | 执行动作 |
|--------|----------|
| 采集, collect, 保存帖子 | TikOmni 获取结构化数据 → 标准模板存笔记 |
| 采集+摘要 | 采集后额外 AI 总结 |

## 执行流程

```
用户输入（触发词 + URL/文件）
  ↓
content_processor 解析触发词
  ↓ 路由
  ├─ 视频 → 加载 bilinote 技能
  ├─ 文章 → 加载 web-clipper 技能
  ├─ 语音 → 加载 voice-summary 技能
  └─ 社交 → 加载 social-collector 技能
  ↓ 执行
子技能完成处理
  ↓ 输出
  ├─ Markdown 笔记 → 03_knowledge/各分类目录/
  ├─ 摘要 → 对话直接返回
  └─ 结构化数据 → JSON 文件
```

## 子技能依赖

| 子技能 | 安装位置 | 说明 |
|--------|----------|------|
| bilinote | `~/.workbuddy/skills/bilinote/` | 视频→结构化笔记，需 BiliNote Docker |
| web-clipper | `~/.workbuddy/skills/web-clipper/` | 网页→Markdown，✅ 可用 |
| voice-summary | `~/.workbuddy/skills/voice-summary/` | 语音→核心要点，✅ 文字可用 |
| social-collector | `~/.workbuddy/skills/social-collector/` | 小红书/抖音→笔记，✅ 可用 |

## 保存路径规则

> 各内容类型保存到对应分类目录。由 `collect_to_inbox` 技能每日凌晨 2:30 提取主要内容转入收件箱，再由 `inbox_refine` 技能每日凌晨 3:00 提纯归档。

| 内容类型 | 保存路径 | 命名规则 |
|----------|----------|----------|
| 视频笔记 | `03_knowledge/00_inbox/` | `YYYY-MM-DD_标题.md` |
| 网页剪藏 | `03_knowledge/40_references/` | `YYYY-MM-DD_标题.md` |
| 语音摘要 | `03_knowledge/01_daily/` | `语音备忘录_YYYY-MM-DD_HHmm.md` |
| 社交帖子 | `03_knowledge/00_inbox/` | `YYYY-MM-DD_{平台}_{标题前20字}.md` |

## 与子技能的关系

**本技能不替代子技能**。设计原则：
1. 子技能可以独立调用（直接说"剪藏"就触发 web-clipper）
2. content_processor 提供统一的触发词入口和路由逻辑
3. 子技能的 SKILL.md 保持独立完整，可单独维护

## 依赖

| 包 | 用途 | 安装状态 |
|---|---|---|
| trafilatura | 网页内容提取 | ✅ 已安装 |
| openai-whisper | 语音转文字 | ✅ 已安装（需模型下载） |
| @tikomni/skills | 社交平台采集 | ✅ 已安装 |
| crawl4ai | 智能网页抓取 | ✅ 已安装 |

## 注意事项

- "转笔记"需要 BiliNote Docker 先启动
- Whisper 首次使用会自动下载模型（base ~150MB）
- 视频处理优先用 BiliNote API，不可用时 fallback 到 yt-dlp + Whisper

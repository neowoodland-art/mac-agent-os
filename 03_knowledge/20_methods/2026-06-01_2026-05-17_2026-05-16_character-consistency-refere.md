---

id: KB-20260601-010
title: ""
type: method
status: published
nature: method
domain: [general]
subdomain: []
tags: ["待补充"]
confidence: 0.5
source: ""
source_type: unknown
date_created: 2026-06-01
date_modified: 2026-06-01
version: 1
previous_version: ""
superseded_by: ""
summary: ""
collected: true
collected_date: 2026-06-02
---

# 2026-05-17_2026-05-16_character-consistency-reference-sheet

> 来源：03_knowledge/20_methods

# 2026-05-16_character-consistency-reference-sheet
# character-consistency-reference-sheet
# 角色一致性定妆照方案（参考图/多视角 Character Sheet/九宫格）
---
## 一、核心原则
### 从"Lights, Camera, Consistency"论文中提取的核心结论
- **I2I 种子帧是角色一致性的架构支点**（ablation 证明：没有 I2I 种子帧，一致性评分从 7.99 暴跌至 0.55）
- Asset-First（先出角色定妆照，再出场景）—— 把身份与上下文解耦
- Temporal Bridge：上一场景的最后一帧作为下一场景第一帧的视觉条件
- CLIPSeg+DINO 用于评估角色一致性的客观指标
---
## 二、主流定妆照方案
### 方案 A：单参考图锚定（Kling 官方推荐）
**适用场景**：角色不复杂、场景变化不大的快速生产
- 用 **同一张参考图** 锚定每一次生成
- 每张图必须清晰展示角色的 **面部、发型、服装**
- 参考图要求：**中性光照 + 干净背景**，让模型聚焦主体

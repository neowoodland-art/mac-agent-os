---
title: "ch13-tool-workflow"
source_dir: 03_knowledge/20_methods
source_file: ch13-tool-workflow.md
date: 2026-05-16
collected_date: 2026-05-16
tags: 
nature: method
domain: general
status: inbox
---

# ch13-tool-workflow

> 来源：03_knowledge/20_methods

# Ch13: 工具实操与工作流搭建
---
## 一、四大核心工具详解
### Runway Gen-3 Alpha
**定位**：电影级画质、精细控制，专业制作首选
**操作流程**：
1. 准备高质量静态图（建议1080p以上，最好4K）
2. 上传图片至平台（支持JPG/PNG）
3. 编写提示词描述期望的动态效果
4. 调整 Camera Motion 参数和 Motion Bucket
5. 生成预览（耗时2-5分钟）
**提示词结构**：
**参数**：
- Motion Bucket：0-10（控制运动强度）
- Camera Motion：Dolly In/Out、Tracking Shot、Orbit、Bird's Eye
- 时长上限：16秒
- 分辨率：最高4K
---
### Kling 可灵
**定位**：中文理解最佳、性价比高
**操作流程**：
1. 准备1080p以上静态图
2. 上传图片（支持JPG/PNG）
3. 用自然语言描述动态效果
4. 选择运动模式
5. 生成预览（耗时1-3分钟）
**提示词**：直接用中文写，自然语言描述
**参数**：通过界面选择运动强度，时长上限10秒（可扩展）

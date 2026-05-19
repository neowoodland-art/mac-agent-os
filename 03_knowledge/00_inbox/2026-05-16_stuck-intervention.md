---
title: "2026-05-16_stuck-intervention"
source_dir: 03_knowledge/20_methods
source_file: 2026-05-16_stuck-intervention.md
date: 2026-05-17
collected_date: 2026-05-17
tags: ["待补充"]
nature: method
domain: general
status: inbox
---

# 2026-05-16_stuck-intervention

> 来源：03_knowledge/20_methods

# stuck-intervention
# 卡壳干预模板
---
## 执行步骤
1. 立即停止当前尝试，不自行继续
2. 写入 04_memory/logs/errors.log（格式: timestamp | context | error_type | attempted_solutions）
3. 按以下模板组织输出
---
## 输出模板
**已尝试方案**:
- 方案A: [简述] → 失败原因: [简述]
- 方案B: [简述] → 失败原因: [简述]
**候选方案**:
- **A)** [方案简述] — 预估耗时: [X分钟] — 风险: [简述]
- **B)** [方案简述] — 预估耗时: [X分钟] — 风险: [简述]
**建议**: [倾向 A/B，简述理由]
**等待你的决定** → 收到后按选定方案继续执行。
---
## 退出

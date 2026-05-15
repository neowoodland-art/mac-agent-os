# 知识库变更日志

## 2026-05-15

### 新增
- [method] 邵氏电影美学AI提示词技巧——依士曼胶片+高调硬光+影棚置景 → 20_methods/ (KB-20260515-002) ← 抖音@黄一鸣AI 单视频提取
- [method] AI提示词驱动文生视频——李导（Agent版）10条视频知识提取 → 20_methods/ (KB-20260515-001) ← 抖音@李导（Agent版）前10条视频批量提取
- [method] 可灵AI提示词完全知识手册——文生视频/图生视频提示词工程 → 20_methods/kling/ (KB-20260515-003) ← 抖音16条可灵AI教程视频提取 · 105条知识条目
- [system] AI视频提示词系统创作教科书知识体系 → 00_ai_video_system/ (KB-20260515-SYS) ← 19章框架+结果推导方法论+采集队列

## 2026-05-14

### 新增
- [tool] Peekaboo v3 桌面 GUI 自动化——屏幕视觉识别+鼠标键盘操作 → 02_skills/peekaboo_controller/ (KB-20260514-001)
- [tool] CloakBrowser 源码级反爬浏览器——30/30反爬检测通过 → 02_skills/cloakbrowser_controller/ (KB-20260514-002)
- [system] Peekaboo 使用策略层：截图冷却5s/上限20次/缓存30s → 02_skills/peekaboo_controller/policy.py
- [method] AI提示词驱动文生视频——AICG造梦局10条视频知识提取 → 20_methods/ (KB-20260514-KB)
- [system] 升级文档：Peekaboo + CloakBrowser 集成说明 → 99_system/upgrade_notes/

### 变更
- web_crawler 引擎升级 v1.2.0：Playwright + Stealth → CloakBrowser（高反爬引擎）
- MCP 配置新增 Peekaboo 服务（带 --json --log-level error token优化）
- 本机安装验证：Peekaboo v3.1.2 + CloakBrowser v0.3.28

### 保留不动
- Matrix 养号（Camoufox）— 已深度适配，不更换内核
- OpenCLI — 不变
- Scrapling/Crawl4AI — 不变
- httpx — 不变

## 2026-05-13

### 新增
- [system] Matrix 养号系统 SMS 验证码自动接收 → 40_references/ (KB-20260510-001)

## 2026-05-06

### 新增
- [concept] 毛选十条经典思维 → 10_concepts/ (KB-20260506-002) ← 从抖音图文提取的版本
- [concept] 搞钱的底层逻辑——价值创造与有效努力 → 10_concepts/ (KB-20260506-001)

## 2026-05-03

### 新增
- [concept] 命名现实的力量——情绪叙事与精神图腾 → 10_concepts/ (KB-20260503-003)
- [concept] 全局算账——主动亏损、战略放弃与主次思维 → 10_concepts/ (KB-20260503-004)
- [system] 内容收集全链路规范 v2.0 → 99_system/pipelines/
- [submission] 10条社会智慧（默认提取）→ 01_submissions/
- [submission] 10条社会智慧（字幕）→ 01_submissions/
- [submission] 10条社会智慧（AI总结）→ 01_submissions/

### 归档
- [test] 测试LLM分类器 → 90_archive/deprecated/

### 变更
- 知识库首页 README.md 全面更新（统计/流程/工具链）
- 维护手册重写为系统操作速查手册（MAINTENANCE_GUIDE.md）
- 清理 10_concepts/ 下 14 个空占位子目录
- 统一收集链路：01_submissions/ → 00_inbox/ → refine → store

## 2026-04-28

### 归档
- [concept] 测试 LLM 分类器 → 10_concepts/ (KB-20260428-001)

## 2026-04-25

### 新增
- 知识库目录结构（按属性分层：概念/方法/事实/参考/资源/观点）
- 知识卡片模板（概念卡、事实卡、方法卡、个人洞见卡）
- 领域分类表（16 个一级领域）
- 知识属性分类表（9 种 nature 类型 + 分类决策树）
- 中文映射配置（folder-aliases.json）
- 知识分类提示词模板

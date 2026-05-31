---
name: content_inspiration
version: 1.0.0
description: 口播素材智能采集与分析系统——多平台采集、AI提炼、智能下载、统一检索
category: user
triggers:
  - 口播素材
  - 素材采集
  - 灵感采集
  - 采集素材
  - 口播灵感
  - 素材工坊
  - content inspiration
  - 启动工坊
  - 分析素材
  - 下载素材
---

# Content Inspiration —— 口播素材智能采集与分析系统

## 概述

完全运行在本机 Mac 的口播素材管理系统，实现"采集→AI分析→智能下载→检索查阅"的完整闭环。不依赖任何云端服务，隐私安全。

## 系统能力

### System 能力（后台自动运行，脚本式任务）

| 能力 | 脚本 | 说明 |
|------|------|------|
| 数据库管理 | `schema.sql` | SQLite WAL 模式，3 张表（materials/analysis/collect_batches） |
| 配置驱动 | `config.yaml` | 所有参数集中管理，模型/平台/存储/下载均可配置 |
| 数据库初始化 | `utils.py: init_db()` | 自动建表、开启 WAL、外键约束 |
| JSONL 存档 | `utils.py: save_jsonl()` | 原始采集数据可追溯回溯 |
| oMLX 健康检查 | `utils.py: check_omlx()` | 自动检测本地 LLM 可用性 |
| 日志系统 | `utils.py: setup_logger()` | 按日期分割，同时输出文件和控制台 |
| 去重机制 | `collect.py: save_to_db()` | 基于 platform+original_id 唯一索引 |

### User 能力（用户直接触发/操作）

| 能力 | 脚本 | 用法 | 说明 |
|------|------|------|------|
| 按需采集 | `collect.py` | `python collect.py -p xiaohongshu -k "科普冷知识"` | 从指定平台采集素材元数据 |
| 全量采集 | `collect.py` | `python collect.py` | 按 config.yaml 配置批量采集 |
| AI 分析 | `analyze.py` | `python analyze.py` | 对所有未分析素材调用本地 LLM |
| 限量分析 | `analyze.py` | `python analyze.py -n 10` | 只分析前 10 条（测试用） |
| 重试失败 | `analyze.py` | `python analyze.py --retry-failed` | 重试之前分析失败的记录 |
| 下载视频 | `downloader.py` | `python downloader.py` | 下载所有标记为 pending 的素材 |
| 下载推荐 | `downloader.py` | `python downloader.py --all` | 下载所有 AI 推荐的素材 |
| 手动下载 | `downloader.py` | `python downloader.py -u "URL"` | 指定 URL 直接下载 |
| Web 界面 | `app.py` | `python app.py` | 启动 Gradio 搜索/浏览界面 |
| 初始化数据库 | `collect.py` | `python collect.py --init-db` | 仅创建数据库表结构 |

## 数据流程

```
用户配置关键词
     ↓
collect.py → MediaCrawler → JSONL 存档 + SQLite 入库
     ↓
analyze.py → oMLX(Qwen2.5-VL-3B) → AI 标签/金句/情绪/推荐
     ↓
app.py (Web界面) → 浏览/搜索/标记下载
     ↓
downloader.py → yt-dlp → ~/workbuddy-agent-os/agent-local/materials/video/
     ↓
知识库索引卡片 → 03_knowledge/50_resources/
```

## 依赖关系

### 必需

| 依赖 | 版本 | 用途 | 安装状态 |
|------|------|------|----------|
| Python | 3.10+ | 运行环境 | ✅ 3.13.12 |
| oMLX | v0.3.6 | 本地 LLM 推理 | ✅ 运行中 |
| Qwen2.5-VL-3B | 8bit | 多模态内容理解 | ✅ 已加载 |
| httpx | ≥0.24 | HTTP 客户端（调 oMLX） | ✅ 已安装 |
| PyYAML | ≥6.0 | 配置文件解析 | ✅ 已安装 |
| Pillow | ≥9.0 | 图片处理 | ✅ 已安装 |

### 待安装

| 依赖 | 版本 | 用途 | 安装命令 |
|------|------|------|----------|
| gradio | ≥4.0 | Web 界面 | `pip install gradio` |
| yt-dlp | ≥2024.0 | 视频下载 | `pip install yt-dlp` |

### 可选

| 依赖 | 用途 | 说明 |
|------|------|------|
| MediaCrawler | 多平台采集 | 需单独 clone 并配置 Cookie |
| ffmpeg | 音频提取 | yt-dlp 的音频模式需要 |

## 存储路径

| 类型 | 路径 | 说明 |
|------|------|------|
| 项目代码 | `~/workbuddy-agent-os/agent-sync/05_tools/05_crawl/content-inspiration/` | 坚果云同步 + Git |
| 原始 JSONL | `data/raw/` | 跟随项目目录 |
| SQLite 数据库 | `data/database.db` | 跟随项目目录 |
| 下载的视频 | `~/workbuddy-agent-os/agent-local/materials/video/` | 本机专属，不同步 |
| 下载的音频 | `~/workbuddy-agent-os/agent-local/materials/audio/` | 本机专属，不同步 |
| 运行日志 | `logs/` | 跟随项目目录 |

## 限制与注意事项

1. **MediaCrawler Cookie**：首次使用需在各平台手动扫码登录，获取 Cookie 后填入 MediaCrawler 配置
2. **链接时效性**：抖音/小红书链接有时效性，采集后 24 小时内下载成功率最高
3. **内存管理**：AI 分析串行执行（每次只处理一条），避免 16GB Mac OOM
4. **模型精度**：3B 小模型可能有标签不准确的情况，建议人工校验
5. **合规提醒**：仅供个人学习研究，禁止商业化或大规模抓取

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2026-04-28 | 初始版本，核心闭环（采集→分析→下载→查阅） |

# AVE 项目落地任务清单 · 跟踪看板

> 版本: v3.0-tracker | 最后更新: 2026-05-15
> 状态: ⬜ 待办 · 🔄 进行中 · ✅ 已完成 · 🚧 阻塞

---

## 使用方式

```diff
+ 每完成一项，把 ⬜ 改成 ✅
+ 每开始一项，把 ⬜ 改成 🔄
+ 遇到阻塞，把 ⬜ 改成 🚧 并在备注写原因
```

---

## Sprint 0 — 已完成的基建（不需要再做）

| # | 任务 | 状态 | 产出 |
|:-:|:----|:----:|:-----|
| 0.1 | Kling API 图生视频集成 | ✅ | `material_producer/kling/kling.py` |
| 0.2 | TTS (CosyVoice + 字级时间戳) | ✅ | `voice_synthesizer/aliyun.py` |
| 0.3 | Pexels 素材搜索 | ✅ | `material_producer/pexels/search.py` |
| 0.4 | BGM 混音 + 避让 | ✅ | `composer/ffmpeg.py` |
| 0.5 | ASS 字级字幕生成 | ✅ | `composer/ffmpeg.py` |
| 0.6 | 长视频自动分段 + concat | ✅ | `composer/ffmpeg.py` |
| 0.7 | 剧本解析 (LLM/模板) | ✅ | `director_parser/parser.py` |
| 0.8 | 口播策略 (video-factory) | ✅ | `video_factory.py` |
| 0.9 | 数字人策略 (Wan2.2 + DreamActor) | ✅ | `material_producer/wan2_2/` |
| 0.10 | 节拍检测 + xfade 卡点 | ✅ | `composer/beat_sync.py` |
| 0.11 | 成本跟踪器 | ✅ | `lib/cost_tracker.py` |
| 0.12 | 全域调研（角色一致性 + LipSync + 外部项目） | ✅ | 入库知识库 + `PLANS/AVE_V3_ARCHITECTURE.md` |
| 0.13 | AVE v3 全链路架构规划 | ✅ | `PLANS/AVE_V3_ARCHITECTURE.md` |
| 0.14 | Dashboard 生产监控面板方案设计 | ✅ | `PLANS/DASHBOARD_DESIGN.md` |

---

## Sprint 1 — P0 (核心增强，~1天)

### 1.1 角色一致性：定妆照 Grid Method

| # | 子任务 | 状态 | 产出文件 |
|:-:|:-------|:----:|:---------|
| 1.1.1 | 编写 Grid Method Prompt 模板（2x3多视角 + 多表情） | ✅ | `prompts/character_sheet_prompts.md` |
| 1.1.2 | 创建 `scripts/character_sheet.py`（定妆照自动生成模块） | ✅ | `scripts/character_sheet.py` |
| 1.1.3 | CLI 子命令 `python main.py character-sheet --desc "..." --output sheet.png` | ✅ | `main.py` 扩展 |
| 1.1.4 | YAML Schema 扩展：剧本增加 `character_ref` 字段 | ✅ | `director_parser/schemas.py` |
| 1.1.5 | 角色描述块锁定：全片自动注入固定角色描述 | ✅ | `composer/character_locker.py` |

**依赖**: 无（独立模块）
**验收标准**: 跑一个命令输出 2x3 网格定妆照 + 一个剧本能用 `character_ref` 引用角色

---

### 1.2 唇形同步：Kling LipSync 集成

| # | 子任务 | 状态 | 产出文件 |
|:-:|:-------|:----:|:---------|
| 1.2.1 | 创建 `scripts/composer/lipsync.py`（Kling LipSync API 封装） | ✅ | `scripts/composer/lipsync.py` |
| 1.2.2 | CLI 子命令 `python main.py lipsync --video clip.mp4 --audio voice.wav` | ✅ | `main.py` 扩展 |
| 1.2.3 | 口播策略后处理钩子：合成后自动跑 LipSync | ✅ | `video_factory.py` 扩展 |
| 1.2.4 | 成本跟踪对接 | ✅ | `lib/cost_tracker.py` 扩展 |

**依赖**: 需要 fal.ai API Key（$0.014/5s）
**验收标准**: 跑一个口播 production，输出视频带口型匹配

---

### 1.3 Dashboard 数据层（和 1.1/1.2 平行）

| # | 子任务 | 状态 | 产出文件 |
|:-:|:-------|:----:|:---------|
| 1.3.1 | SQLite schema 定义（6 表） | ✅ | `data/ave.db` (自动创建) |
| 1.3.2 | 创建 `scripts/lib/dashboard.py`（埋点封装） | ✅ | `scripts/lib/dashboard.py` |
| 1.3.3 | main.py 埋点：每次 production 自动写 DB（~50行） | ✅ | `main.py` + `video_factory.py` 扩展 |
| 1.3.4 | cost_tracker 埋点：自动记录费用 | ✅ | `lib/cost_tracker.py` 扩展 |
| 1.3.5 | FastAPI 后端骨架 + DB 读取 API | ✅ | `scripts/dashboard/app.py` |

**依赖**: 无（纯增量，和 P0 功能平行）
**验收标准**: 跑一条 production 后，SQLite 里有对应的 production + steps + cost 记录

---

## Sprint 2 — P1 (体验增强，~1天)

### 2.1 变速卡点引擎

| # | 子任务 | 状态 | 产出文件 |
|:-:|:-------|:----:|:---------|
| 2.1.1 | 创建 `scripts/composer/speed_ramp.py`（setpts + atempo 滤波器链） | ⬜ | `scripts/composer/speed_ramp.py` |
| 2.1.2 | 支持缓变速度曲线（0.7→1.0→1.3） | ⬜ | `speed_ramp.py` |
| 2.1.3 | CLI 子命令 `python main.py speed-ramp --input clip.mp4 --curve 0.5,1.0,1.5` | ⬜ | `main.py` 扩展 |
| 2.1.4 | 卡点策略集成：高能段落自动变速 | ⬜ | `video_factory.py` 扩展 |

**依赖**: 无
**验收标准**: 输入一段视频 + 速度曲线，输出变速后的视频（音频同步）

---

### 2.2 节拍检测升级（BeatSync-Engine 架构）

| # | 子任务 | 状态 | 产出文件 |
|:-:|:-------|:----:|:---------|
| 2.2.1 | 能量曲线 + 频谱特征提取（RMS/Flux/Kick/Snare） | ⬜ | `composer/beat_sync.py` 增强 |
| 2.2.2 | 歌曲结构检测（Intro→Verse→Chorus→Bridge→Outro） | ⬜ | `composer/beat_sync.py` 增强 |
| 2.2.3 | 能量波切密度（高能→密集切，低能→长保持） | ⬜ | `composer/beat_sync.py` 增强 |
| 2.2.4 | Frame-locked 时间线（消除 xfade 漂移） | ⬜ | `composer/beat_sync.py` 增强 |

**依赖**: 无
**验收标准**: 对比升级前后的节拍匹配精确度

---

### 2.3 口播+卡点融合管线

| # | 子任务 | 状态 | 产出文件 |
|:-:|:-------|:----:|:---------|
| 2.3.1 | 创建 `scripts/composer/hybrid.py`（口播场景间插入变速卡点过渡） | ⬜ | `scripts/composer/hybrid.py` |
| 2.3.2 | 过渡段自动匹配 BGM 节拍 | ⬜ | `hybrid.py` |
| 2.3.3 | CLI 子命令 / video-factory 扩展 | ⬜ | `main.py` 扩展 |

**依赖**: 2.1.1 + 2.2.1
**验收标准**: 一个口播视频在高潮段落自动插入变速卡点过渡

---

## Sprint 3 — P2 (系统完善，~2天)

### 3.1 角色叙事策略

| # | 子任务 | 状态 | 产出文件 |
|:-:|:-------|:----:|:---------|
| 3.1.1 | 场景分解模块（剧本→N个场景 + 每场景Prompt） | ⬜ | `scripts/story_director/scene_planner.py` |
| 3.1.2 | Temporal Bridge（上场景末帧→下场景首帧条件） | ⬜ | `scripts/story_director/temporal_bridge.py` |
| 3.1.3 | 批量 Kling 生成（固定 seed + 角色描述块） | ⬜ | `scripts/story_director/batch_generator.py` |
| 3.1.4 | story 策略 CLI + video-factory 入口 | ⬜ | `main.py` + `video_factory.py` 扩展 |
| 3.1.5 | HoloCine 全局一致性策略参考实现 | ⬜ | `story_director/` |

**依赖**: 1.1.1, 1.1.2, 1.1.3
**验收标准**: 输入一个多场景剧本 + 定妆照，输出一个带角色一致性的多场景视频

---

### 3.2 本地 Lip-Sync（LatentSync v1.5）

| # | 子任务 | 状态 | 产出文件 |
|:-:|:-------|:----:|:---------|
| 3.2.1 | 本地部署 LatentSync（Docker 或 venv） | ⬜ | `scripts/latentsync/` |
| 3.2.2 | AVE 集成接口（与 lipsync.py 统一接口） | ⬜ | `composer/lipsync.py` 扩展 |
| 3.2.3 | 自动切换：API 不可用时降级到本地 | ⬜ | `composer/lipsync.py` 扩展 |

**依赖**: 无，但需要 8GB VRAM
**验收标准**: 在本地 GPU 上跑通 LipSync

---

### 3.3 素材资产管理器

| # | 子任务 | 状态 | 产出文件 |
|:-:|:-------|:----:|:---------|
| 3.3.1 | 创建 `scripts/asset_manager/index.py`（素材索引） | ⬜ | `scripts/asset_manager/index.py` |
| 3.3.2 | 缓存管理（Pexels/Kling 生成片段自动入索引） | ⬜ | `scripts/asset_manager/cache.py` |
| 3.3.3 | 标签系统 + 搜索 | ⬜ | `scripts/asset_manager/tags.py` |

**依赖**: 1.3.2（Dashboard 数据层）
**验收标准**: 搜索关键词能找到对应的历史素材

---

### 3.4 Dashboard 前端页面

| # | 子任务 | 状态 | 产出文件 |
|:-:|:-------|:----:|:---------|
| 3.4.1 | 生产列表页（筛/搜/排序） | ⬜ | `dashboard/templates/index.html` |
| 3.4.2 | 生产详情页（每步状态 + 资产 + 费用 + re-run） | ⬜ | `dashboard/templates/detail.html` |
| 3.4.3 | 资产浏览器（类型/标签筛选 + 搜索 + 使用记录） | ⬜ | `dashboard/templates/assets.html` |
| 3.4.4 | 费用分析（按策略/时间/单步） | ⬜ | `dashboard/templates/costs.html` |

**依赖**: 1.3.5（后端 API）+ 3.3（资产索引）
**验收标准**: 打开浏览器能看到所有 production 和数据

---

## Sprint 4 — P3 (可选增强)

| # | 任务 | 状态 | 备注 |
|:-:|:----|:----:|:-----|
| 4.1 | LoRA 训练管线（CharForge / IC-LoRA） | ⬜ | 极高一致性需求时启用 |
| 4.2 | Wan2.2-S2V-14B 本地部署 | ⬜ | 需要 24-40GB VRAM，消费级显卡暂不支持 |
| 4.3 | ComfyUI 工作流导出支持 | ⬜ | 从 AVE 导出到 ComfyUI 编辑 |
| 4.4 | 即梦 VIP 自动化接入（Peekaboo） | ⬜ | 复用 Matrix 养号框架 |
| 4.5 | 多音色 TTS 库管理 | ⬜ | 管理多个 CosyVoice 音色 + 配音切换 |

---

## 快速参考：分策略状态总览

| 策略 | 当前状态 | Sprint 1 后 | Sprint 2 后 | Sprint 3 后 |
|:----|:--------:|:----------:|:----------:|:----------:|
| **口播** | ✅ 可用 | ✅ + 定妆照 + LipSync | ✅ + 变速过渡 | ✅ + 资产索引 + Dashboard |
| **卡点** | ✅🔧 可用但粗糙 | ✅🔧 | ✅ 节拍升级 + 变速 | ✅ |
| **数字人** | ✅ 可用 | ✅ + LipSync 增强 | ✅ | ✅ |
| **角色叙事** | ❌ 不存在 | ❌ | ❌ | ✅ 初版可用 |
| **Dashboard** | ❌ 不存在 | 🔄 数据层在积累 | 🔄 数据在积累 | ✅ 前端可用 |

---

## 进度标记说明

```diff
+ ✅ 已完成 — 无需再关注
+ 🔄 进行中 — 正在开发
+ ⬜ 待办 — 计划内但未开始
+ 🚧 阻塞 — 等待前置条件
```

> 建议把这个文件放在 AVE 项目根目录，每次完成一项就更新状态。
> 或者你告诉我完成了哪项，我来帮你更新。

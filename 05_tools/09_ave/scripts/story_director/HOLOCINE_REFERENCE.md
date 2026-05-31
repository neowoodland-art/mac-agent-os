# HoloCine 全局一致性策略参考

> 版本: 1.0 | 更新: 2026-05-18
> 来源: CVPR 2026 Highlight — "HoloCine: Consistent Character Generation for Long-Form Video"

---

## 核心设计模式

HoloCine 提出了 4 层一致性框架，本模块 (AVE story_director) 实现了其中部分模式。

### 1. Character Reference Sheet（定妆照）✅ 已实现

**HoloCine 做法**: 多视角多表情的参考网格图 → CLIP embedding 特征锚点

**AVE 实现**: `character_sheet.py` — 2x3 Grid Method 定妆照生成

- 2x3 网格: 正面/侧面/3/4 + 中性/微笑/愤怒
- 描述块锁定 (`character_locker.py`): 全片自动注入固定角色描述
- 角色库 (`CHARACTER_DB`): JSON 持久化，支持多角色存储

### 2. 固定 Seed 时间线（Partial Seed Anchoring）✅ 已实现

**HoloCine 做法**: 每个场景用不同但固定的 seed → 跨场景确保同一角色特征一致

**AVE 实现**: `batch_generator.py` — seed = base_seed + scene_id

- 每场景固定 seed，同一角色在不同场景的视觉一致性提升
- 支持 Kling 文生视频（百炼 & 官方 API）
- seed 缓存机制: 相同 seed + 相同 prompt 命中缓存

### 3. 场景分解 + 视角规划（Scene Decomposition）✅ 已实现

**HoloCine 做法**: 剧本 → N 个场景，每场景指定镜头运动/光线/角色位置

**AVE 实现**: `scene_planner.py` — 基于规则分解

- 按 BGM section 自动分组
- 从文本/搜索词推断环境、动作、光线
- 自动分配镜头运动

### 4. Temporal Bridge（时间桥接）✅ 已实现

**HoloCine 做法**: 上场景末帧 → 下场景首帧的一致性约束

**AVE 实现**: `temporal_bridge.py` — 场景间过渡分析

- 5 种桥接类型: continuous / environment / mood / switch / chapter
- 对比环境、角色、光线、镜头变化
- 生成 FFmpeg xfade 参数
- 自动选择过渡类型

### 5. LoRA 微调（Identity-Specific Fine-tuning）⬜ 未实现

**HoloCine 做法**: 用参考网格图训练 LoRA → 推理时加载

**AVE 规划**: Sprint 4.1 (CharForge / IC-LoRA)

- 场景: 极高一致性需求时启用
- 预期收益: 角色特征锚定精度从 ~70% 提升至 ~95%
- 工具链: Kling LoRA / IC-LoRA / ComfyUI

### 6. 运动连续性约束（Motion Continuity）⬜ 部分实现

**HoloCine 做法**: 场景 A 末帧的姿态特征 → 场景 B 首帧的姿态初始化

**AVE 现状**: temporal_bridge 仅生成文字描述，未做姿态特征传递

- 当前: "The character walks through a door..." 文字指引
- 目标: 用 DensePose / OpenPose 提取末帧姿态 → 注入首帧

### 7. 全局光照一致性（Global Illumination Consistency）⬜ 未实现

**HoloCine 做法**: 提取首场景的色调映射 → 约束后续场景色温

**AVE 现状**: 基于文本情绪的粗略光线推断

---

## 参考论文

| 论文 | 会议/期刊 | 核心贡献 | AVE 关联 |
|:-----|:---------|:---------|:---------|
| HoloCine | CVPR 2026 Highlight | 长视频角色一致性 4 层框架 | story_director 核心架构参考 |
| Lights, Camera, Consistency | arXiv 2512.16954 | 跨场景光照/角色/背景一致性 | temporal_bridge 扩展方向 |
| Character-consistent Video Generation | — | 定妆照 + LoRA 方案 | character_sheet.py 参考 |
| VideoPoet | Google | 长视频时序建模 | 远期参考 |

## 参考项目

| 项目 | 链接 | 相关模块 |
|:-----|:-----|:---------|
| BeatSync-Engine | GitHub | 6-stage beat-sync → beat_sync.py |
| ComfyUI-vidflows | GitHub | multi-shot narrative → story_director |

## 未来集成方向

```
角色一致性成熟度矩阵:

当前状态        │ Sprint 3 目标    │ Sprint 4 (远期)
───────────────┼─────────────────┼──────────────────
定妆照 ✅       │ 多视点参考图 ✅   │ LoRA 微调 ⬜
固定 seed ✅    │ seed 缓存 ✅     │ seed 级联 ⬜
场景分解 ⬜      │ 规则分解 ✅      │ LLM 语义分解 ⬜
文字桥接 ⬜      │ 桥接类型 ✅      │ 姿态特征传递 ⬜
光线推断 ⬜      │ 文本光线推断 ✅   │ 色调映射提取 ⬜
```

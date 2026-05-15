# AVE v3 全链路架构规划书

> 版本: v3.0-draft | 最后更新: 2026-05-15
> 基于全域调研（Kling API / HoloCine / BeatSync-Engine / LatentSync / Lights-Camera-Consistency）

---

## 一、现状总览

### 1.1 已实现能力 ✅

| 模块 | 功能 | 依赖 |
|:----|:----|:----:|
| **口播策略** | 文案→TTS→素材搜索→混音→字幕→合成 | CosyVoice + Pexels + FFmpeg |
| **卡点策略** | BGM→librosa节拍检测→素材→拍点切换→xfade | librosa + FFmpeg |
| **数字人策略** | 图片+音频→Wan2.2 OmniHuman 对口型/M1动作模仿 | 火山引擎 DreamActor |
| **Kling API 视频生成** | 文生视频/图生视频 (kling-v3) | 百炼 DashScope / Kling JWT |
| **剧本解析** | 文案→LLM分镜→YAML脚本 | LLM (模板/在线) |
| **锚点切换** | 静音检测驱动画面切换 | librosa |
| **BGM 避让** | 说话时压低BGM / 间隙恢复 | 字级时间戳驱动 |
| **字幕生成** | ASS字幕 (字级精确时间戳) | CosyVoice 时间戳 |
| **长视频分段** | >180s 自动分段 + concat | FFmpeg |

### 1.2 待增强能力 🔧

| 模块 | 现状 | 目标 |
|:----|:----|:-----|
| **变速卡点** | 仅固定速度 xfade 切换 | setpts + atempo 动态速度曲线 |
| **Kling LipSync** | 无集成 | 对接 fal.ai Kling LipSync API |
| **角色一致性** | 仅手动 prompt 工程 | 定妆照→参考图→批量生成的自动化管线 |
| **节拍检测** | 单层 beat_track | BeatSync-Engine 6阶段架构 (能量/结构/剪切策略) |
| **素材复用** | 无缓存系统 | 索引+缓存+标签体系 |

### 1.3 调研中能力 🔍

| 模块 | 来源 | 预计投入 |
|:----|:----|:--------:|
| **角色叙事策略** | HoloCine + Lights-Camera-Consistency | 2-3天 |
| **本地 Lip-Sync** | LatentSync v1.5 (字节跳动) | 0.5天部署 |
| **多场景批量生成** | Kling Image O1 多图融合 | 0.5天 |
| **数字资产索引** | 本地素材库 + 生成历史 | 1天 |

---

## 二、四策略管线详解

### 策略 A：口播（主路径，已成熟）

```
输入: 文案(.txt/.yaml)
流程:
  文案 → [剧本解析] → YAML分镜脚本
  → [TTS: CosyVoice] → 带字级时间戳的人声 WAV
  → [素材搜索: Pexels] → 每段 2 个视频素材
  → [混音] → 人声 + BGM (可选避让)
  → [字幕: ASS] → 字级精确时间戳
  → [合成: FFmpeg] → 1080×1920 竖版视频
输出: final.mp4
```

**可直接执行的命令**: `python main.py video-factory --strategy 口播 --script script.yaml`

**增强方向**:
- 🔧 Kling LipSync 后处理: 合成后加一步 LipSync 让口型匹配
- 🧠 Kling AI 素材替代 Pexels: 图生视频生成更精准的场景素材

---

### 策略 B：卡点（已实现，需增强）

```
输入: BGM + 素材 (提供/Pexels搜索)
流程:
  BGM → [节拍检测: librosa beat_track] → BPM + 拍点列表
  → [分组: N拍/组] → 每组时长 = N × (60/BPM)
  → [素材分配] → 循环取素材, 精确裁剪到组时长
  → [拼接: xfade] → 过渡拼接 (≤8组)
输出: beat_sync.mp4
```

**可直接执行的命令**: `python main.py video-factory --strategy 卡点 --bgm bgm.wav --search 风景`

**待增强**:
| 功能 | 来源 | 实现方式 |
|:----|:----|:--------|
| **变速卡点 (speed ramp)** | FFmpeg setpts | `setpts=(1/v)*PTS` + `atempo=v` 滤波器链 |
| **能量波切密度** | BeatSync-Engine | 高能段落更密集剪切, 低能段落保持 |
| **歌曲结构检测** | BeatSync-Engine | Intro→Verse→Chorus→Bridge→Outro 分区 |
| **视觉智能选素材** | BeatSync-Engine Qwen3-VL | 动作/美感/质量评分, 语义标签匹配 |

---

### 策略 C：数字人（已实现，分模式）

```
输入: 角色头像 + 文案/参考视频
流程 (对口型):
  头像 + 文案 → [TTS: CosyVoice] → 音频
  → [Wan2.2 OmniHuman] → 带口型的数字人视频
输出: /tmp/ave_digital_human.mp4

流程 (动作模仿):
  头像 + 参考视频 → [火山引擎 DreamActor M1] → 动作模仿视频
```

**可直接执行的命令**: `python main.py video-factory --strategy 数字人 --image photo.jpg --text "文案"`

**增强方向**:
- 🔧 Kling LipSync: 将 OmniHuman 换成 Kling LipSync (成本可控, 质量更高)
- 🔧 LatentSync v1.5 本地部署: 零成本, 中文优化
- 🧠 Wan2.2-S2V-14B: 远期替换, 音频→视频一步到位

---

### 策略 D：角色叙事（新策略，调研中）

```
输入: 定妆照 + 剧本(.yaml) → 多场景故事
流程:
  [定妆照生成] → 角色 sheet / 参考图
  → [场景分解] → 剧本 → N个场景 + 每个场景的 Prompt
  → [批量生成] → Kling 图生视频 (每场景固定seed + 角色描述块)
  → [Temporal Bridge] → 上场景末帧 → 下场景首帧条件
  → [卡点合成] → BGM + 节拍 + 变速过渡
  → [LipSync] → 语音驱动口型
输出: story_final.mp4
```

**这个策略目前不存在**，需要从零构建。它吸收外部项目的核心思路：

| 来源 | 吸收点 | 实现方式 |
|:----|:-------|:--------|
| **HoloCine** (CVPR 2026) | 全局场景一致性, 稀疏注意力 | 用 Kling 的固定seed + 参考图模拟 |
| **Lights-Camera-Consistency** | Asset-First, Temporal Bridge, JSON蓝图 | 设计 AVE 剧本 YAML 扩展格式 |
| **Kling 3.0 参考图** | 单参考图锚定全片 | 定妆照→参考图→每场景生成 |
| **Grid Method** | 2x3 多视角 Character Sheet | 先生成定妆照网格, 再逐一入场景 |

---

## 三、数字资产管理体系

### 3.1 资产分类

| 资产类型 | 来源 | 存储位置 | 复用方式 |
|:---------|:----|:---------|:--------|
| **角色定妆照** | AI生成/用户提供 | `assets/characters/` | Kling 参考图 / IP-Adapter |
| **角色 LoRA** | CharForge 训练 | `assets/lora/` | ComfyUI / SD 生态 |
| **生成视频片段** | Kling API | `cache/generations/` | 剪辑拼接 / 素材库 |
| **Pexels 素材** | 网络搜索 | `cache/pexels/` | 各策略通用 |
| **BGM 文件** | Pixabay/生成 | `assets/bgm/` | 卡点 / 口播策略 |
| **剧本 YAML** | 用户编写/LLM生成 | `scripts/` | 版本管理 / 批量生产 |
| **历史输出** | 各策略成品 | `output/` | 回放 / 二次剪辑 |
| **LipSync 缓存** | LatentSync | `cache/lipsync/` | 重复使用 |

### 3.2 资产流转图（跨策略复用）

```
定妆照    ────→ 口播 (片头数字人)
  │
  ├──────→ 数字人 (恒等保持)
  │
  └──────→ 角色叙事 (场景批量生成)
              │
              ├──────→ 卡点 (混剪素材)
              │
              └──────→ 口播 (最终合成)

生成片段  ───→ 口播 (Pexels 素材替代)
  │
  ├──────→ 卡点 (素材复用)
  │
  └──────→ 素材缓存 → 下一次复用

BGM      ─────→ 口播 / 卡点 / 角色叙事 (通用)
```

### 3.3 资产索引建议

当前没有素材索引系统。建议新增 `scripts/asset_manager/` 模块：

```python
# asset_manager/index.py — 素材索引
class AssetIndex:
    def index_pexels_cache(self, cache_dir): ...
    def index_generations(self, gen_dir): ...
    def search(self, tags: list[str], type: str): ...
    def get_character_ref(self, char_id: str): ...
    def get_lipsync_cache(self, audio_hash: str): ...
```

---

## 四、外部项目集成点矩阵

| 外部项目 | 类型 | 集成方式 | 优先级 | 投入 |
|:---------|:----|:---------|:-----:|:----:|
| **BeatSync-Engine** | 开源 | 6阶段架构 → 升级 AVE beat_sync.py | P1 | 0.5天 |
| **Kling LipSync (fal.ai)** | API | `scripts/composer/lipsync.py` 新增 | **P0** | 0.5天 |
| **LatentSync v1.5** | 开源 | `scripts/latentsync/` 本地推理 | P2 | 0.5天 |
| **HoloCine** | 论文 | 角色叙事策略的核心理论框架 | P2 | 2天 |
| **Lights-Camera-Consistency** | 论文 | JSON蓝图+Temporal Bridge 设计模式 | P2 | 1天 |
| **CharForge / IC-LoRA** | 开源 | LoRA 训练管线 | P3 | 1天 |
| **Grid Method (Midjourney社区)** | 方法论 | 定妆照生成 prompt 模板 | P0 | 0.2天 |
| **Wan2.2-S2V-14B** | 开源 | 远期替换数字人引擎 | P3 | 待定 |
| **MoneyPrinterTurbo** | 开源 | 参考其全自动化架构设计 | P3 | 0.3天 |
| **ComfyUI-vidflows** | 开源 | ComfyUI 内的多镜头叙事参考 | P3 | 0.3天 |

---

## 五、开发路线图（按优先级）

### Sprint 1 (P0, ~1天)

| 序号 | 任务 | 产出文件 | 来源 |
|:---:|:----|:---------|:-----|
| 1 | **定妆照生成** — 2x3 Grid Method Prompt 模板 + 自动化脚本 | `scripts/character_sheet.py` | Grid Method |
| 2 | **Kling LipSync 集成** — 新增 lipsync.py 模块 + CLI 子命令 | `scripts/composer/lipsync.py` | fal.ai |
| 3 | **角色描述块锁定** — Scene YAML 扩展 `character_ref` 字段 | `scripts/director_parser/schemas.py` | Lights-Camera |

### Sprint 2 (P1, ~1天)

| 序号 | 任务 | 产出文件 | 来源 |
|:---:|:----|:---------|:-----|
| 4 | **变速卡点引擎** — setpts + atempo 动态速度曲线 | `scripts/composer/speed_ramp.py` | BeatSync-Engine |
| 5 | **节拍检测升级** — 能量曲线+歌曲结构+剪切策略 (6阶段) | 改写 `scripts/composer/beat_sync.py` | BeatSync-Engine |
| 6 | **卡点+口播融合管线** — 口播场景中插入变速卡点过渡 | `scripts/composer/hybrid.py` | 新设计 |

### Sprint 3 (P2, ~2天)

| 序号 | 任务 | 产出文件 | 来源 |
|:---:|:----|:---------|:-----|
| 7 | **角色叙事策略** — 定妆照→场景批量生成→Temporal Bridge | `scripts/story_director/` | HoloCine + LCC |
| 8 | **本地 LatentSync 部署** — Docker / venv 部署 + AVE 集成 | `scripts/latentsync/` | 字节跳动 |
| 9 | **素材资产管理器** — 索引 + 缓存 + 标签 + 搜索 | `scripts/asset_manager/` | 新设计 |

### Sprint 4 (P3, 可选)

| 序号 | 任务 | 来源 |
|:---:|:----|:-----|
| 10 | LoRA 训练管线 (CharForge) | CharForge |
| 11 | Wan2.2-S2V-14B 本地部署 | Wan-AI |
| 12 | ComfyUI 工作流导出支持 | ComfyUI-vidflows |

---

## 六、关键决策记录

### 6.1 Kling LipSync vs. 本地 LatentSync

| 维度 | Kling LipSync (fal.ai) | LatentSync v1.5 (本地) |
|:----|:---------------------:|:---------------------:|
| 成本 | $0.014/5s (¥0.10/镜头) | 免费 |
| 质量 | ⭐⭐⭐⭐ 商业级 | ⭐⭐⭐⭐⭐ 中文优化 |
| 部署 | 零部署 (API调用) | 需 8GB VRAM + Docker |
| 延迟 | ~12分钟/次 | ~数秒~数十秒 |
| 适合 | **短期快速集成** | 中期大批量场景 |

**结论**：先上 Kling LipSync（P0，半天完成集成），LatentSync 作为 P2 储备。

### 6.2 角色叙事 vs. 增强现有策略

**不新建策略**，而是在现有策略上叠加 3 个增强层：
1. **定妆照层** — 所有策略共享（P0）
2. **角色锁定层** — 场景 YAML 加 character_ref 字段（P0）
3. **LipSync 层** — 合成后后处理（P0）

角色叙事策略本质上是"口播 + 定妆照 + 批量场景 + 卡点的融合产物"，不是独立的全新管线。

### 6.3 素材策略：Pexels vs. Kling AI vs. 即梦VIP

| 策略 | 成本 | 质量匹配度 | 可用性 |
|:----|:----:|:---------:|:------:|
| **Pexels** (当前) | 免费 (需API Key) | ⭐⭐ (通用素材, 不精确) | ✅ 稳定 |
| **Kling AI 图生视频** | ¥1/5s | ⭐⭐⭐⭐ (精准匹配) | ✅ AVE已集成 |
| **即梦VIP (网页版)** | ¥0.22-0.37/段 | ⭐⭐⭐⭐⭐ | 🚧 需Peekaboo |
| **即梦API** | ¥1-3/段 | ⭐⭐⭐⭐⭐ | 🚧 高级会员 |

**结论**：维持 Pexels 为默认素材源（免费），Kling AI 素材为按需增强（高精度场景），即梦为长期优化方向。

---

## 七、自纠偏：架构辩论

### 辩论 1：要不要做统一的"剧本→多场景→角色叙事"管线？

**正方**：这是用户需要的最终形态——输入一个故事，输出一个完整的角色化视频
**反方**：这会是一个很重的投入（2-3天），且依赖多个未成熟的外部模型
**裁决**：先不做统一管线。改为在现有 3 个策略上加"角色一致性增强层"和"LipSync 层"，角色叙事是"口播+定妆照+卡点"的组合产物。等 P0/P1 完成后，自然就知道统一的管线应该长什么样。

### 辩论 2：Kling LipSync API 还是本地模型？

**正方**：API 零部署、零维护、商业级质量、价格合理
**反方**：12分钟推理时间太长、依赖服务商、文本模式仅120字
**裁决**：API 先上（P0），本地模型作为中期增强（P2）。API 的 12 分钟可以通过并行提交缓冲。

### 辩论 3：变速卡点值不值得单独做一个模块？

**正方**：这是用户明确提到的核心需求，也是和竞品差异化的关键
**反方**：FFmpeg setpts/atempo 实现简单，不需要单独模块
**裁决**：值。但不是单独做"speed_ramp.py"，而是把变速作为 beat_sync 管线的一个可选滤波器链。BeatSync-Engine 的能量波切密度策略才是真正的核心创新——变速只是具体实现手段。

---

## 八、项目文件结构建议

```
scripts/
├── main.py                           # CLI 入口
├── video_factory.py                  # 工厂路由 (已有, 扩展)
├── character_sheet.py                # 🆕 定妆照生成 (Grid Method)
├── asset_manager/                    # 🆕 资产管理
│   ├── index.py                      #    素材索引
│   ├── cache.py                      #    缓存管理
│   └── tags.py                       #    标签系统
├── composer/
│   ├── beat_sync.py                  # 🔧 节拍检测升级 (6阶段)
│   ├── speed_ramp.py                 # 🆕 变速滤波器链
│   ├── lipsync.py                    # 🆕 Kling LipSync 集成
│   ├── ffmpeg.py                     # (已有)
│   └── hybrid.py                     # 🆕 口播+卡点融合
├── story_director/                   # 🆕 角色叙事 (P2)
│   ├── scene_planner.py              #    场景分解
│   ├── temporal_bridge.py            #    Temporal Bridge
│   └── batch_generator.py            #    批量 Kling 生成
├── director_parser/
│   ├── parser.py                     # 🔧 扩展 character_ref
│   └── schemas.py                    # 🔧 YAML schema 扩展
├── material_producer/
│   ├── kling/kling.py                # 🔧 增加 seed 参数
│   └── pexels/search.py              # (已有)
├── voice_synthesizer/                # (已有)
└── lib/
    └── config.py                     # (已有)
```

---

## 九、下一步行动

**立即做 (P0)**:
1. 定妆照 Grid Method Prompt 模板
2. Kling LipSync 集成 (lipsync.py + CLI)
3. YAML Schema 扩展 (character_ref 字段)

**明天做 (P1)**:
4. 变速卡点引擎
5. 节拍检测升级

**本周做 (P2)**:
6. 角色叙事管线初版
7. 素材资产管理器

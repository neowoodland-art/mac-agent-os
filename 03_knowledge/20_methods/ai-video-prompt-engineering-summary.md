---
id: KB-20260515-001
title: "AI视频素材生成——提示词工程与分镜脚本方法汇总"
type: method
status: active
nature: reference
domain: ai
subdomain: [AI视频生成, 提示词工程, 分镜脚本, AVE集成]
tags: [AI视频, prompt工程, 分镜, 风格统一, 角色一致性]
source: "知识库同步 + 全网调研"
date_created: 2026-05-15
date_modified: 2026-05-15
version: 1

collected: true
collected_date: 2026-05-16---

# AI视频素材生成——提示词工程与分镜脚本方法汇总

> 目标：为 AVE 视频工厂设计一套"文案→分镜→AI素材生成"的标准方法

---

## 一、核心流程：文案 → 分镜 → 素材

```
文案脚本
    ↓ [DeepSeek/LLM + 分镜模板]
结构化分镜脚本 (镜号/画面描述/旁白/类型/景别)
    ↓ [统一风格关键词 + 图生视频 / 文生视频]
AI 素材片段 (每段5-10s)
    ↓ [Ken Burns + 字幕 + BGM]
final.mp4
```

---

## 二、分镜脚本提示词模板

### 2.1 文案→分镜生成模板

```
角色设定:
  你是一个专业的视频分镜师。

任务:
  根据以下文案，生成一个详细的分镜脚本。
  要求包括:
  1. 镜号 (Shot Number)
  2. 画面描述 (Visual Description) — 详细描述画面内容
  3. 旁白文案 (Narration)
  4. 建议的画面类型 (Type of Visual): 实景 / 动画 / 图示
  5. 建议的镜头景别 (Shot Scale): 全景 / 中景 / 特写

文案:
{这里放文案内容}
```

### 2.2 分镜提示词结构（五要素）

每条分镜的 AI 生成提示词应包含这五个维度：

| 要素 | 说明 | 示例 |
|:-----|:-----|:------|
| **① 风格** | 整体视觉风格 | 极简扁平化3D / 水墨国风 / 超写实电影感 |
| **② 主体** | 画面主角及其动作 | 一个身穿蓝衬衫的男性，困惑挠头 |
| **③ 环境** | 背景和场景元素 | 被彩色图标和文件包围，浅蓝背景 |
| **④ 镜头运动** | 运镜方式 | 镜头缓慢俯视拉远 / 稳定跟拍 |
| **⑤ 光线质感** | 光照和材质 | 柔和的均匀环境光，细微投影 |

### 2.3 完整提示词组装示例

```python
prompt = f"{style}，{subject}，{environment}，{camera_motion}，{lighting}"
#  → "水墨国风，一位老者在山水间打太极，云雾缭绕的山峰背景，镜头缓慢推进，柔和自然光"
```

---

## 三、风格统一方法

### 3.1 三原则

1. **定义核心风格锚点**: 整期视频定义一个核心风格词（如 "超写实电影感" / "水墨国风"）
2. **所有分镜共用风格词**: 每条 prompt 开头/结尾强制加入统一风格描述
3. **固定主体一致性**: 保持主角穿着、相貌、画风不变

### 3.2 角色一致性技巧

- 图生视频: 首帧用同一张角色图作为参考
- 描述中固定特征: "鹅蛋脸柳叶眉，长发披肩，白色连衣裙"
- Kling/即梦都支持参考图模式

---

## 四、高级技巧（来自知识库）

### 4.1 动作拆解法
复杂表情/动作拆解为子动作序列:
```
❌ "害羞地笑" 
✅ "嘴唇闭合→唇缝紧贴→嘴角微微上扬→肩膀微耸→下巴内收→眼神先向下看再猛抬"
```

### 4.2 情绪控制
- 标点符号: 省略号... 波浪号~ 破折号—— 控制语气节奏
- 发声描述: "轻声说"、"低沉地"、"激动地"
- 节奏描述: "语速渐快"、"停顿片刻"

### 4.3 空间锚定
通过空间参照物增强画面张力:
- 前景/中景/背景分层
- 参照物比例（蚂蚁视角/巨人视角）
- 远近虚实对比

### 4.4 反向提示词
写"不要什么"有时比"要什么"更有效:
```
negative_prompt: 畸形、面瘫、扭曲、比例失调
```

---

## 五、AVE 集成方案

### 5.1 当前状态

AVE 的 `main.py generate` 流程目前:
- 依赖 YAML 脚本的 `material.search` 字段 → Pexels 搜索关键词
- 素材来源单一，质量不可控

### 5.2 改进方案

在 YAML 脚本中增加 `prompt` 字段，支持 AI 生成:

```yaml
segments:
- id: 1
  text: "上善若水，水善利万物而不争。——《道德经》"
  duration_sec: 10
  material:
    provider: kling          # 或 pexels / bailian
    style: "水墨国风"
    subject: "流水穿石，水滴石穿"
    environment: "云雾缭绕的山涧，青苔覆盖的岩石"
    camera: "镜头缓慢推进，俯拍"
    lighting: "柔和的散射光，晨雾氛围"
```

这样 AVE 就能自动组装完整 prompt 调用 Kling/百炼 API。

### 5.3 优先级

| 阶段 | 内容 | 预计工作量 |
|:-----|:-----|:----------|
| P0 | YAML 增加 prompt 字段支持 | 2h |
| P1 | 分镜模板集成到 director_parser | 3h |
| P2 | 风格统一 + 角色一致性控制 | 4h |
| P3 | 自动从文案生成完整分镜脚本 | 1d |

---

## 六、参考来源

| 来源 | 类型 | 价值点 |
|:-----|:-----|:-------|
| 知识库 ai-prompt-video-knowledge.md | 10条视频提取 | Seedance2.0技巧、动作拆解法 |
| 知识库 ai-prompt-creator-2.md | 博主干货 | 反向提示词、空间锚定 |
| 腾讯云 AI视频全攻略 | 技术文章 | 分镜模板、五要素结构 |

---

## 附：2026 AI视频提示词工程完全手册

> 采集来源: freeaitool.com / 阿里云万相官方文档 / zeeklog.com

### 一、六要素串联公式（通用）

```
提示词 = [主体] + [动作/运动] + [环境/场景] + [镜头语言] + [光影色调] + [风格画质]
```

**模板示例（英文优先）**：
```
A 30-year-old man in a dark suit, standing on a rooftop at midnight,
rain falling around him. He slowly turns his head toward the camera.
Medium shot, slow push-in, shallow depth of field.
Cold blue moonlight, warm orange neon signs reflecting on wet surfaces,
high contrast, cinematic color grading, 4K, anamorphic lens flares, 2.39:1.
```

### 二、镜头语言速查

| 英文关键词 | 中文 | 效果 |
|-----------|------|------|
| close-up | 特写 | 强调面部表情或细节 |
| medium shot | 中景 | 人物半身, 最常用 |
| wide shot | 广角/全景 | 展示环境 |
| bird's eye view | 鸟瞰 | 正上方俯视 |
| low angle | 低角度 | 仰拍, 压迫感/英雄感 |
| dolly zoom | 推拉变焦 | 背景压缩, 惊悚效果 |
| tracking shot | 跟拍 | 镜头跟随主体 |
| slow push-in | 缓慢推进 | 紧张感/专注感 |
| dolly in/out | 推/拉 | 靠近或远离主体 |
| pan | 摇摄 | 镜头水平转动 |

### 三、动态控制词库

| 类型 | 英文词 | 效果 |
|------|--------|------|
| 平移 | walking, running, flying | 主体移动 |
| 缓慢 | slowly drifting, gently swaying | 轻柔氛围 |
| 快速 | sprinting, rushing, zooming | 速度感 |
| 旋转 | spinning, rotating, orbiting | 环绕镜头 |
| 变形 | morphing, dissolving, transforming | 创意转场 |

### 四、光影关键词

| 关键词 | 效果 |
|--------|------|
| golden hour | 黄金时刻(日落暖光) |
| blue hour | 蓝色时刻(黄昏蓝调) |
| dramatic lighting | 戏剧性光影 |
| soft diffused light | 柔和漫射光 |
| neon glow | 霓虹辉光 |
| backlit / silhouette | 逆光/剪影 |
| high key / low key | 高调/低调 |
| volumetric lighting | 体积光 |
| rim light | 轮廓光 |

### 五、阿里云万相专用公式

**基础公式**（文生视频）：
```
主体 + 场景 + 运动 + 美学控制 + 风格化
```

**图生视频公式**：
```
运动 + 运镜
```
（主体和风格已由图固定, 只需描述怎么动）

**声音公式**（wan2.7+）：
```
主体 + 场景 + 运动 + 人声(内容+情绪+语调) + 音效(材质+行为) + BGM(风格)
```

**多镜头公式**（wan2.6+）：
```
第1个镜头[0-3秒]: xxx
第2个镜头[3-6秒]: xxx
第3个镜头[6-10秒]: xxx
```

### 六、负面提示词模板

```
deformed, blurry, extra limbs, text, watermark, cartoon,
low resolution, unnatural movement, flickering, bad hands,
missing fingers, bad face, bad proportions
```

### 七、避坑指南

| 常见错误 | 后果 | 修正 |
|---------|------|------|
| 只写主体不写运动 | 画面静止 | 明确运动方向和速度 |
| 运动描述矛盾 | 画面撕裂 | 避免矛盾描述 |
| 忽略镜头语言 | 画面平淡 | 至少加一个镜头术语 |
| 提示词过长(>150词) | 模型丢失重点 | 控制在50-150词 |
| 中文提示词 | 理解偏差 | 尽量使用英文 |
| 一次出片不好放弃 | 效果不佳 | 迭代: 写→生成→调整→再写 |

### 八、进阶工作流

1. **从短到长迭代**：先写核心要素，逐步添加环境/镜头/光影
2. **参考图高于文字**：I2V时一张好图+简短运动描述远超纯文字
3. **分镜控制节奏**：10秒以上用时间轴分段描述
4. **运动幅度不宜过大**：新手先从单一方向微动开始

### 九、图生图/图生视频专用（Stable Diffusion + AnimateDiff）

**基础图生成参数**：

| 参数 | 推荐值 |
|------|--------|
| 采样器 | DPM++ 2M Karras |
| 步数 | 30 |
| CFG Scale | 7 |
| 分辨率 | 512x768 (竖屏) |
| 权重语法 | (keyword:1.2) 强化特定元素 |

**AnimateDiff 运动参数**：

| 参数 | 效果 | 推荐范围 |
|------|------|---------|
| Translation X | 水平移动 | -2 ~ 2 |
| Translation Y | 垂直移动 | -2 ~ 2 (上移常用0.5) |
| Rotation | 画面旋转 | -0.5 ~ 0.5 |
| Scale | 镜头推拉 | 0.98 ~ 1.02 |

**新手黄金法则**：运动幅度不宜过大，人物易变形，从单一微动开始。

**ControlNet 解决闪烁**：启用Tile模型 + tile_resample预处理器，显著提升帧间连续性。

### 十、模型选型建议

| 模型 | 最佳用途 |
|------|---------|
| majicMIX realistic | 写实人像 |
| ChilloutMix | 写实人像(亚洲脸优) |
| Anything V5 | 二次元动漫 |
| Realistic Vision | 风景/建筑 |
| DreamShaper | 通用高质量 |
| Counterfeit | 二次元(偏插画) |

**通用正向提示词模板**：
```
(masterpiece, best quality:1.2), 1girl, solo, detailed face,
highly detailed skin, soft lighting, depth of field, natural look
```

**通用负向提示词**：
```
nsfw, bad hands, bad fingers, missing fingers, extra fingers,
bad face, bad eyes, bad proportions, ugly, duplicate, morbid,
deformed, blurry, low quality, worst quality, signature, watermark
```
| PromptMart.cn | 提示词库 | 50000+ 提示词模板参考 |
| video-to-prompt.com | 在线工具 | 视频→提示词逆向工程 |

# AVE v2.0 落地实施计划

> AudioScore Video Engine — 智能体可调用的自动化视频编排引擎
>
> **版本**: v1.0 (规划)
> **创建**: 2026-05-04
> **负责人**: ghai / Claw
> **状态**: 📋 规划阶段

---

## 一、项目概览

### 1.1 这是什么

AVE v2.0 是一个以**双轨音频锚点**为时间轴，通过**导演脚本**精确控制视听元素的自动化视频编排引擎。它接收结构化YAML指令，输出最终视频文件。

### 1.2 核心能力

| 能力 | 说明 | 技术方案 |
|------|------|---------|
| 情绪化人声合成 | 一个音色演绎多种情绪 | 豆包语音 2.0 (火山引擎) |
| 背景音乐生成 | 氛围化配乐，风格可控 | ACE-Step 1.5 / MusicGen (云GPU) |
| 数字人出镜 | 静态图→口播视频 | Wan2.2-S2V (通义万相 API) |
| 素材搜索 | 根据语义搜索视频素材 | Pexels API (免费) |
| 导演脚本 | 文案→结构化YAML→视频 | 本地大模型解析 |
| 渲染合成 | 多轨合成最终视频 | Remotion + FFmpeg |

### 1.3 系统架构图

```
                用户文案
                   │
              [01_director_parser]
             大模型解析 → director_script.yaml
                   │
     ┌─────────────┼─────────────┐
     │             │             │
     ▼             ▼             ▼
[02_voice]    [03_bgm]     [05_material]
豆包语音2.0   ACE-Step     Pexels + Wan2.2
     │             │             │
     └─────────────┼─────────────┘
                   │
              [04_anchor_extractor]
              双轨锚点对齐
                   │
              [06_composer]
            Remotion + FFmpeg
                   │
              final.mp4
```

---

## 二、目录结构与文件清单

### 2.1 工具模块路径

参照 `05_tools/` 现有模块的 `TOOL.md + scripts/` 结构：

```
~/workbuddy-agent-os/agent-sync/
├── 05_tools/
│   └── 09_ave/                          ← 工具模块根目录
│       ├── TOOL.md                      ← 工具说明文档 (必须)
│       ├── install.sh                   ← 一键安装脚本 (可选)
│       ├── requirements.txt.pip         ← Python 依赖
│       ├── config.yaml                  ← API 密钥/默认参数配置模板
│       │
│       ├── scripts/                     ← 核心脚本目录
│       │   ├── __init__.py
│       │   ├── main.py                  ← 统一 CLI 入口
│       │   │
│       │   ├── 01_director_parser/
│       │   │   ├── __init__.py
│       │   │   ├── parser.py            ← 文案 → director_script.yaml
│       │   │   └── schemas.py           ← YAML 结构校验
│       │   │
│       │   ├── 02_voice_synthesizer/
│       │   │   ├── __init__.py
│       │   │   ├── volcano.py           ← 豆包语音 2.0 适配器
│       │   │   └── aliyun.py            ← CosyVoice 备用适配器
│       │   │
│       │   ├── 03_bgm_generator/
│       │   │   ├── __init__.py
│       │   │   ├── ace_step.py          ← ACE-Step 1.5 适配器
│       │   │   └── suno.py              ← Suno API 备用适配器
│       │   │
│       │   ├── 04_anchor_extractor/
│       │   │   ├── __init__.py
│       │   │   └── extractor.py         ← librosa 锚点提取
│       │   │
│       │   ├── 05_material_producer/
│       │   │   ├── __init__.py
│       │   │   ├── pexels.py            ← Pexels 搜索
│       │   │   ├── wan2_2.py            ← Wan2.2-S2V 适配器
│       │   │   └── fallback.py          ← 本地素材回落
│       │   │
│       │   ├── 06_composer/
│       │   │   ├── __init__.py
│       │   │   ├── remotion.py          ← Remotion 项目生成
│       │   │   └── ffmpeg.py            ← FFmpeg 后处理
│       │   │
│       │   ├── 07_service_layer/
│       │   │   ├── __init__.py
│       │   │   ├── api.py               ← FastAPI 服务
│       │   │   └── skill_bridge.py      ← WorkBuddy 技能对接
│       │   │
│       │   └── lib/                     ← 通用工具库
│       │       ├── __init__.py
│       │       ├── config.py            ← 配置加载
│       │       ├── cache.py             ← 素材/结果缓存
│       │       └── logger.py            ← 日志
│       │
│       └── assets/                      ← 模板/参考资源
│           ├── director_template.yaml   ← 导演脚本模板
│           └── demo_scripts/            ← 测试脚本集
│
├── 02_skills/
│   └── ave/                             ← WorkBuddy 技能
│       ├── SKILL.md                     ← 技能定义
│       └── reference/                   ← 技能参考文档
│           └── director_schemas.md
│
└── agent-local/
    └── tools/
        └── ave/                         ← 本机数据（不同步）
            ├── config/
            │   └── local.yaml           ← 本地 API 密钥等敏感配置
            ├── cache/
            │   ├── materials/           ← 素材缓存
            │   └── outputs/             ← 渲染缓存
            └── templates/
                └── remotion/            ← Remotion 项目模板
```

### 2.2 核心文件清单

| 编号 | 文件 | 功能 | 优先级 |
|------|------|------|--------|
| P0 | `09_ave/TOOL.md` | 工具说明文档 | ⭐ 必须 |
| P0 | `09_ave/scripts/main.py` | CLI 入口 | ⭐ 必须 |
| P0 | `09_ave/scripts/01_director_parser/parser.py` | 文案解析 | ⭐ 必须 |
| P0 | `09_ave/scripts/02_voice_synthesizer/volcano.py` | 豆包语音 | ⭐ 必须 |
| P0 | `09_ave/scripts/05_material_producer/pexels.py` | 素材搜索 | ⭐ 必须 |
| P0 | `09_ave/scripts/06_composer/ffmpeg.py` | 合成 | ⭐ 必须 |
| P1 | `09_ave/scripts/03_bgm_generator/ace_step.py` | 背景音乐 | 建议 |
| P1 | `09_ave/scripts/04_anchor_extractor/extractor.py` | 锚点提取 | 建议 |
| P2 | `09_ave/scripts/05_material_producer/wan2_2.py` | 数字人 | 可选 |
| P2 | `09_ave/scripts/07_service_layer/api.py` | FastAPI 服务 | 可选 |
| P2 | `02_skills/ave/SKILL.md` | WorkBuddy 技能 | 可选 |

---

## 三、实施阶段（分4阶段推进）

### 阶段 1：基础设施（1天）

**目标**：目录结构搭建 + API 注册 + 配置就绪

```
任务清单:
☐ 创建 09_ave/ 完整目录结构
☐ 创建 agent-local/tools/ave/config/ 目录
☐ 注册火山引擎豆包语音 2.0 → 获取 API Key + App ID + Access Token
☐ 注册阿里云百炼 → 获取 API Key
☐ 注册 Pexels → 获取 API Key
☐ 编写 config.yaml 模板
☐ 编写 local.yaml（本地敏感配置）
☐ 编写 install.sh 安装脚本
☐ 编写 TOOL.md 工具说明
☐ 提交到 Git: git add, commit, push
```

**产出**：
- 可 `git clone` 后在目标机器 `bash install.sh` 一键就绪
- agentos upgrade 能识别并检查 09_ave 模块

### 阶段 2：核心链路 MVP（2-3天）

**目标**：跑通 文案→人声→素材→合成 的可用闭环

**任务清单**：

**02_voice_synthesizer (半天)**
```
☐ 实现 volcano.py 基础 TTS 调用
☐ 测试: python main.py voice --text "测试" --output test.wav
☐ 上传音色样本 → 获取 speaker_id
☐ 实现情感指令参数: emotion, speed, pitch
☐ 实现 CosyVoice 备用适配器
```

**05_material_producer (半天)**
```
☐ 实现 pexels.py 搜索+下载
☐ 实现回退策略: search → fallback cache
☐ 测试: python main.py material --search "sunset beach"
```

**01_director_parser (半天)**
```
☐ 实现 schemas.py YAML 结构校验 (Pydantic)
☐ 实现 parser.py 文案 → YAML
☐ 编写 director_template.yaml
☐ 测试: python main.py parse --script demo.txt
```

**06_composer (半天)**
```
☐ 实现 ffmpeg.py 音视频合成
☐ 实现字幕叠加 (ass/srt 字幕)
☐ 测试: python main.py compose --voice voice.wav --material clips/
```

**MVP 集成测试**
```
☐ 用一个小笑话脚本跑通完整链路
☐ 产出第一个 final.mp4（纯人声+素材画面）
```

### 阶段 3：品质提升（1-2天）

**目标**：加入背景音乐 + 锚点对齐 → 多轨精准编排

**任务清单**：

**03_bgm_generator**
```
☐ 调研 ACE-Step 1.5 部署方案 (云端 GPU)
☐ 或实现 Suno API 备用适配器
☐ 实现 ace_step.py → bgm.wav
```

**04_anchor_extractor**
```
☐ 实现 extractor.py (librosa 节奏检测)
☐ 实现人声字级锚点: word_timestamps → anchors.json
☐ 实现 BGM 段落锚点: section_boundaries
```

**01_director_parser 升级**
```
☐ 支持完整的导演脚本模板 (bgm_section, camera, avatar 等字段)
```

**06_composer 升级**
```
☐ 双轨混音: voice.wav + bgm.wav → mixed_audio.wav
☐ 基于锚点对齐画面切换
☐ 支持分段渲染 (3分钟以上视频)
```

### 阶段 4：数字人 + 技能封装（1天）

**目标**：数字人出镜 + 作为 WorkBuddy 技能可调用

**任务清单**：

**05_material_producer 升级**
```
☐ 实现 wan2_2.py (通义万相 S2V)
☐ 实现 detect 图片合规检查
☐ 实现异步任务轮询
☐ 回落策略: detect失败 → 重试 → 跳过数字人
```

**07_service_layer**
```
☐ FastAPI 服务: POST /ave/generate
☐ 任务队列 + 进度轮询
☐ 错误处理与重试逻辑
```

**02_skills/ave/SKILL.md**
```
☐ 技能触发词: 视频、剪辑、生成视频
☐ 输入: 文案文本 + 风格标签
☐ 流程: 调用大模型 → 生成 YAML → 调用 AVE API
☐ 输出: 返回 final.mp4 本地路径
```

---

## 四、API 注册清单与成本

### 4.1 必须注册的服务

| 服务 | 用途 | 注册步骤 | 预计耗时 |
|------|------|---------|---------|
| **火山引擎** | 豆包语音 2.0 | 注册→实名→ARK模型服务→创建API Key | 30min |
| **阿里云百炼** | Wan2.2-S2V + CosyVoice | 注册→实名→开通服务→创建API Key | 20min |
| **Pexels** | 素材搜索 | 注册→API Dashboard→创建Application | 10min |

### 4.2 各服务凭证清单

```
agent-local/tools/ave/config/local.yaml：

# 火山引擎 (豆包语音 2.0)
volcano:
  api_key: "sk-xxx"          # ARK → API Key 管理
  app_id: "xxx"              # 语音控制台 → App ID
  access_token: "xxx"        # 语音控制台 → Access Token
  speaker_id: "xxx"          # 声音复刻 → 训练后获取
  tts_model: "volcano_tts_2.0"

# 阿里云百炼
aliyun:
  api_key: "sk-xxx"          # 百炼 → API Key
  wan_model: "wan2.2-s2v"
  cosyvoice_model: "cosyvoice-v3.5-plus"

# Pexels
pexels:
  api_key: "xxx"             # Pexels API Dashboard
  rate_limit: 200             # 请求/小时
```

### 4.3 月费预估 (日更一条3分钟视频)

| 模块 | 方案 | 月费 | 备注 |
|------|------|------|------|
| 人声合成 | 豆包语音 2.0 年付 | ~22元 | 首3月免费 |
| 数字人 | HeyGen Creator | ~211元 | 或用 Wan2.2 API 按量计费 |
| 背景音乐 | ACE-Step 云端GPU | ~2元 | 或 Suno API ~15-30元 |
| 素材搜索 | Pexels | 0元 | 免费 |
| 大模型调用 | DeepSeek / 通义千问 | ~1-10元 | 文案解析 |
| **合计** | | **~25-250元/月** | 取决于数字人方案 |

---

## 五、本地硬件需求

| 环节 | 部署位置 | 需求 | Mac 16G 可行性 |
|------|---------|------|---------------|
| 文案解析 | 云端 API | 无 | ✅ 直接调 |
| 人声合成 | 云端 API | 无 | ✅ 直接调 |
| 背景音乐 | 云端 GPU | 6GB+ 显存 | ❌ 需云 GPU |
| 数字人 | 云端 API | 无 | ✅ 直接调 |
| 素材搜索 | 云端 API | 无 | ✅ 直接调 |
| 锚点提取 | 本地 | CPU, librosa | ✅ |
| Remotion | 本地 | 16GB RAM | ✅ 3-5min 以内 |
| FFmpeg | 本地 | 无特殊要求 | ✅ 已装 |

> **结论**：Mac 16GB 内存足够处理 3 分钟内视频的本地环节。
> 仅背景音乐生成（ACE-Step）和 Remotion 渲染长视频需要云端或分段。

---

## 六、可能遇到的问题与应对

### 6.1 API 层问题

| 问题 | 概率 | 影响 | 应对方案 |
|------|------|------|---------|
| 豆包语音 API 认证失败 | 中 | 人声不可用 | 实现 CosyVoice 备选；local.yaml 三重凭证逐一校验 |
| Wan2.2-S2V 图片检测不通过 | 中 | 数字人无法生成 | 回落：跳过数字人片段，仅用素材画面+字幕 |
| Pexels 搜索无结果 | 高 | 素材缺失 | 3层回落：search → AI生成 → fallback_mood_videos |
| Pexels 速率限制 | 低 | 搜索被限 | 本地缓存层，已搜过的关键词不重复请求 |
| ACE-Step API 响应慢 | 中 | BGM 生成延迟 | 异步队列，不影响主流程；或改用 Suno API |

### 6.2 本地渲染问题

| 问题 | 概率 | 影响 | 应对方案 |
|------|------|------|---------|
| Remotion 内存不足 | 中 | 长视频渲染失败 | 分段渲染（3分钟/段）→ FFmpeg concat |
| FFmpeg 编码参数不合适 | 低 | 视频过大/质量差 | 预设多组编码参数，按场景切换 |
| 中间文件撑满磁盘 | 中 | 渲染中断 | 自动清理策略：渲染成功后删除 wav/clips |
| 中文字幕编码乱码 | 低 | 字幕显示异常 | 强制 UTF-8 + ASS 格式（非 SRT） |

### 6.3 编排逻辑问题

| 问题 | 概率 | 影响 | 应对方案 |
|------|------|------|---------|
| 语音与画面不同步 | 中 | 观感差 | 锚点容差机制：画面切换 ±0.2s |
| BGM 段落与文案不匹配 | 中 | 情绪割裂 | 导演脚本中明确 bgm_section 映射 |
| 多个素材时长与口播不匹配 | 高 | 画面空白/超长 | 自动拼接/裁剪素材到精确时长 |
| 大模型解析 YAML 格式错误 | 中 | 链路中断 | schemas.py 严格校验 + 自动修复 |

---

## 七、落地检查清单

### 7.1 基础设施

```
☐ 09_ave/ 目录创建完成
☐ TOOL.md 编写完成
☐ install.sh 编写完成
☐ agent-local/tools/ave/config/local.yaml 配置完成
☐ agentos upgrade 能识别 09_ave 模块
☐ git commit + push 到远程
```

### 7.2 MVP 链路

```
☐ 豆包语音 2.0 TTS 调用成功 → test.wav
☐ Pexels 搜索+下载成功 → material.mp4
☐ 文案→导演脚本 YAML 解析成功
☐ FFmpeg 音视频合成成功 → final.mp4
☐ 小笑话脚本跑通全链路
```

### 7.3 品质提升

```
☐ 背景音乐生成 (ACE-Step/Suno) → bgm.wav
☐ 双轨混音: voice + bgm
☐ 锚点提取 + 画面同步切换
☐ 分段渲染 + concat (长视频)
```

### 7.4 技能封装

```
☐ Wan2.2-S2V 数字人接入
☐ FastAPI 服务运行
☐ 02_skills/ave/SKILL.md 编写
☐ agentos sync 注册技能
☐ 技能调用测试: "帮我把这段文案做成视频"
```

---

## 八、技能定义草案

### 8.1 技能触发

**技能名**：`ave_video_director`

**触发词**：
- 视频、剪辑、生成视频、做视频
- 把这段话做成视频、AI 视频、自动剪辑
- director script、导演脚本

### 8.2 技能流程

```
用户输入文案
    ↓
01_director_parser: 大模型解析文案 → director_script.yaml
    ↓
02_voice_synthesizer: 逐段合成情绪化人声 → voice_segments/
    ↓
03_bgm_generator: 生成背景音乐 → bgm.wav (可选)
    ↓
04_anchor_extractor: 双轨锚点提取 → anchors.json
    ↓
05_material_producer: 并行搜索素材 → material_clips/
                      + Wan2.2-S2V → avatar_clips/ (可选)
    ↓
06_composer: 编排渲染 + 编码 → final.mp4
    ↓
返回 final.mp4 路径给用户
```

### 8.3 用户输入示例

```bash
# 最简调用
python main.py generate --script "今天我们来聊聊..."

# 指定风格
python main.py generate --script demo.txt --style bedtime_story

# 高级：直接传导演脚本
python main.py compose --director-script script.yaml
```

---

## 九、首次启动步骤

```bash
# 1. 进入项目
cd ~/workbuddy-agent-os/agent-sync

# 2. 创建目录结构
mkdir -p 05_tools/09_ave/{scripts/{01_director_parser,02_voice_synthesizer,03_bgm_generator,04_anchor_extractor,05_material_producer/{pexels,wan2_2,fallback},06_composer,07_service_layer,lib},assets/demo_scripts}
mkdir -p agent-local/tools/ave/{config,cache/{materials,outputs},templates/remotion}

# 3. 配置 API 密钥 (参考 4.2 节)
# 编辑 agent-local/tools/ave/config/local.yaml

# 4. 安装 Python 依赖
pip install -r 05_tools/09_ave/requirements.txt.pip

# 5. 测试人声合成
python 05_tools/09_ave/scripts/main.py voice --text "你好，这是测试" --output test.wav

# 6. 跑通 MVP 闭环 (文案→人声→素材→合成)
python 05_tools/09_ave/scripts/main.py generate --script assets/demo_scripts/test_story.txt

# 7. 注册技能到 WorkBuddy
agentos sync

# 8. 提交到 Git
git add -A && git commit -m "feat: AVE v2.0 工具模块初始化" && git push
```

---

## 十、文件生成顺序（按依赖关系）

```
第1批 (并行，无依赖):
  ├── TOOL.md
  ├── config.yaml
  ├── requirements.txt.pip
  ├── lib/config.py
  ├── lib/cache.py
  └── lib/logger.py

第2批 (无内部依赖):
  ├── 02_voice_synthesizer/volcano.py
  ├── 05_material_producer/pexels.py
  └── 06_composer/ffmpeg.py

第3批 (依赖第2批):
  ├── 01_director_parser/parser.py
  ├── 01_director_parser/schemas.py
  ├── 02_voice_synthesizer/aliyun.py
  └── 05_material_producer/fallback.py

第4批 (依赖第2+3批):
  ├── 03_bgm_generator/ace_step.py
  ├── 03_bgm_generator/suno.py
  ├── 04_anchor_extractor/extractor.py
  └── 06_composer/remotion.py

第5批 (依赖前面全部):
  ├── main.py (CLI 入口)
  ├── 05_material_producer/wan2_2.py
  ├── 07_service_layer/api.py
  └── 07_service_layer/skill_bridge.py

第6批 (最后):
  ├── 02_skills/ave/SKILL.md
  ├── install.sh
  └── assets/director_template.yaml
```

---

**文档版本**: v1.0
**最后更新**: 2026-05-04
**下一步**: 开始阶段1 → 目录创建 + API 注册

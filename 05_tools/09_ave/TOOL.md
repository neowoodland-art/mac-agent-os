# TOOL.md — AVE v3.0 (AudioScore Video Engine)

> **工具版本**: v3.0
> **接入日期**: 2026-05-04
> **最后更新**: 2026-05-09
> **维护者**: ghai
> **路径方案**: local.yaml + local_paths.py（无软链接，多机安全）
> **Python**: ~/.workbuddy/binaries/python/versions/3.13.12/
> **FFmpeg**: /opt/homebrew/bin/ffmpeg (v7.1.1)

---

## 一句话说明

通过**导演脚本**（YAML）驱动，自动完成文案→人声合成→素材搜索→背景音乐→渲染合成的全流程视频编排引擎。BGM 采用三阶路由：真实音乐库 → AI 生成 (mlx-audiocraft) → FFmpeg 和弦垫音。

---

## 依赖的 API 服务

| 服务 | 用途 | 费用 | 配置位置 |
|------|------|------|---------|
| 阿里云百炼 (CosyVoice) | 人声合成 | 按量付费 | agent-local/tools/ave/config/local.yaml |
| Pexels | 素材搜索 (视频) | 免费 (200次/小时) | 同上 |
| HuggingFace / hf-mirror | AI 模型下载 | 免费 | 环境变量 HF_ENDPOINT |

---

## 快速开始

```bash
cd 05_tools/09_ave/scripts/

# 人声合成
python main.py voice --text "测试文字" --output test.wav

# 素材搜索 (中文自动翻译英文)
python main.py material --search "日出云海" --count 3

# 背景音乐 (三阶路由自动选择)
python main.py bgm --mood calm --duration 60     # Tier 3: 和弦垫音

# AI BGM (需 pip install mlx-audiocraft, 首次下载模型)
HF_ENDPOINT=https://hf-mirror.com python main.py bgm --mood funny --duration 60 --use-mlx

# 全链路生成
python main.py generate --script director_script.yaml --output final.mp4 --clips-per-segment 2

# 全链路生成 + BGM
python main.py generate --script director_script.yaml --output final.mp4 --clips-per-segment 2 --bgm /path/to/bgm.wav

# 全链路生成 + BGM 避让 (说话音低→间隙恢复)
python main.py generate --script director_script.yaml --output final.mp4 --clips-per-segment 2 --bgm /path/to/bgm.wav --duck

# 全链路生成 + 锚点画面切换
python main.py generate --script director_script.yaml --output final.mp4 --clips-per-segment 2 --anchor-transitions

# 全链路生成 + BGM避让 + 锚点切换
python main.py generate --script director_script.yaml --output final.mp4 --clips-per-segment 2 --bgm /path/to/bgm.wav --duck --anchor-transitions

# 字幕 (默认开启, 基于 CosyVoice 字级时间戳精准对齐)
python main.py generate --script director_script.yaml --no-subtitles  # 关闭字幕

# 数字人片尾
python main.py digital-human --image avatar.jpg --text "关注我，一起聆听世界，我们下期再见"

# 情绪参数测试
python main.py emotion-test --text "测试文本"
```

---

## 架构

```
YAML 导演脚本 ──→ main.py generate
                      │
         ┌────────────┼──────────────┐
         ▼            ▼              ▼
   voice_synthesizer  │     material_producer
   CosyVoice TTS      │     Pexels 搜索+缓存
         │            │              │
         └────────────┼──────────────┘
                      ▼
            bgm_generator (三阶路由)
         ┌───────┬───────┬──────────┐
         ▼       ▼       ▼          ▼
      bgm_lib  mlx-     chord_pad  composer/
      (未启用) audiocra ft (备用)   ffmpeg.py
               ft (主)              │
                                    ▼
                              final.mp4
```

## BGM 三阶路由 (v3.0)

| mood | prompt | BPM |

```
请求 BGM (mood, duration)
    │
    ├─→ Tier 1: 音乐库 (有文件?) ─→ 载入 + 循环截取
    │
    ├─→ Tier 2: mlx-audiocraft (--use-mlx) ─→ AI 生成 + 循环
    │
    └─→ Tier 3: chord_pad (默认) ─→ FFmpeg 和弦氛围音
```

### Tier 2: mlx-audiocraft

- 模型: `facebook/musicgen-small` (300M 参数)
- 安装: `pip install mlx-audiocraft`
- 首次: 下载 ~300MB 模型权重 (需 huggingface 或 hf-mirror.com)
- 速度: M1 上 10s 音乐 ~46s 生成
- Prompt 控制风格/乐器/BPM/节奏
- 国内用户需设置 `HF_ENDPOINT=https://hf-mirror.com`
- 代码中已自动检测并设置镜像

### Tier 3: chord_pad (离线保障)

- 文件: `scripts/bgm_generator/chord_pad.py`
- 原理: FFmpeg aevalsrc 生成多层 detuned 正弦波和弦
- 效果: 低通滤波 + 混响，产生温暖垫音
- 10种情绪预设: calm/soothing/happy/excited/sad/mystery/angry/professional/normal/funny/inspiring
- 速度: 即时生成

### 情绪→Prompt 映射

| mood | prompt | BPM |
|------|--------|:---:|
| calm | soft ambient piano, gentle pad, nature sounds, no percussion, no vocals | 60 |
| soothing | warm ambient drone, slow strings, peaceful atmosphere, no vocals | 50 |
| happy | bright ukulele, cheerful melody, acoustic guitar, no vocals | 90 |
| excited | upbeat electronic, driving beat, synth pads, no vocals | 120 |
| sad | melancholic piano, slow strings, emotional, no vocals | 55 |
| mystery | dark ambient, deep synth pad, suspenseful, no vocals | 60 |
| angry | intense orchestral, heavy drums, dramatic, no vocals | 110 |
| professional | corporate soft jazz, clean piano, polished, no vocals | 75 |
| funny | playful xylophone, quirky light music, cartoon style, no vocals | 100 |
| inspiring | uplifting cinematic, building strings, triumphant, no vocals | 85 |
| normal | soft background music, gentle, ambient, no vocals | 70 |

---

## 文件清单

```
05_tools/09_ave/
├── TOOL.md                    ← 本文件
├── director_script.yaml       ← 演示脚本 (会打太极的猫)
├── requirements.txt.pip       ← Python 依赖
├── scripts/
│   ├── main.py                ← CLI 入口 (v1.1)
│   ├── anchor_extractor/      ← librosa 音频锚点
│   ├── bgm_generator/         ← BGM 三阶路由
│   │   ├── suno.py            ← Tier 1-2-3 路由 + mlx-audiocraft
│   │   ├── chord_pad.py       ← Tier 3 FFmpeg 和弦垫音
│   │   └── bgm_download.py    ← BGM 库管理 (搁置)
│   ├── composer/
│   │   └── ffmpeg.py          ← FFmpeg 合成/混音/字幕 (v1.1)
│   ├── director_parser/       ← 文案→YAML (oMLX + 降级)
│   ├── lib/                   ← 通用库 (config/logger)
│   ├── material_producer/
│   │   └── pexels/
│   │       └── search.py      ← Pexels 搜索 (v1.1, 中文翻译)
│   ├── service_layer/         ← API 服务层
│   └── voice_synthesizer/
│       ├── aliyun.py          ← CosyVoice TTS
│       └── volcano.py         ← 豆包语音 TTS (备用)
├── PLANS/                     ← 规划文档
├── assets/                    ← 资源
└── install.sh                 ← 安装
```

---

## 已知问题 & 修复记录

### 已修复
| 问题 | 修复 | 版本 |
|------|------|:----:|
| 视频时长 > 音频时长 (135s vs 53s) | composer/ffmpeg.py `compose_video`: 无条件加 `-shortest` | v1.1 |
| BGM 纯正弦波像杂音 | BGM v2: 和弦进行+低通+混响 | v2.0 |
| BGM 音量过低 (0.06) | suno.py: 移除生成时 volume 衰减; main.py: `bgm_volume=0.35` | v3.0 |
| Python UnboundLocalError | 移除函数内 `import os` / `from lib.config import load_config` | v1.1 |
| FFmpeg amix 语法错误 | 输入标签 `[0:a][1:a]` 直接拼接不用逗号 | v2.0 |
| 手动下载 BGM 效率低 | 改为 mlx-audiocraft AI 生成 (Tier 2 主方案) | v3.0 |
| **字幕不精确 (脚本时长 vs 实际人声)** | **aliyun.py `synthesize_with_timestamps()`: CosyVoice 字级时间戳对齐** | **v2.3** |
| **Callback 数据未收集** | **加 `wait_done()` 等待异步回调完成** | **v2.3** |
| **BGM 像杂音** | **V2 和弦垫音 (低通+混响) + mlx-audiocraft AI BGM** | v3.0 |

### 保留特性
- `--subtitles` 标志 (默认开启): 基于 CosyVoice 字级时间戳自动计算每段精确起止时间
- 时间戳回退: 字数不匹配时自动回落比例估算
- 字幕样式: 字号 = height × 4.4% (竖屏1080p→84px), 位置 = 底部上方20%, 描边3px
- `--duck` BGM 避让: 基于字级时间戳, 说话时 BGM=0.15, 间隙时 BGM=0.50, 300ms 过渡
- `--anchor-transitions` 锚点画面切换: librosa 检测静音段, 在切换点切换素材
- `--beat-sync` (v3.0): BGM 节拍检测 → 拍点切换素材 → xfade 过渡
- 费用追踪: `lib/cost_tracker.py` 每次 API 调用自动记录费用

## 文件中转仓库

即梦/火山引擎 API 需要图片/视频/音频的公网 HTTP URL。

```
仓库: git@gitee.com:babycalf/ghvideo.git
直链: https://gitee.com/babycalf/ghvideo/raw/master/{filename}
用途: 存储 API 调用所需的临时媒体文件
本地: agent-local/tools/ave/ghvideo/
上传: python lib/ghvideo_upload.py 文件1 文件2
```

## 策略体系 (v3.0)

视频工厂按 4 种策略组织, 生产时选择策略 + 提供内容即可:

```
请求: {策略, 内容素材}
    │
    ├─→ 口播策略 ✅ (当前)
    │   文案 → TTS → Pexels素材 → BGM避让 → 锚点切换 → 精确字幕 → 数字人片头片尾
    │   适用: 知识分享、励志金句、故事讲述
    │
    ├─→ 卡点策略 🔧 (待开发)
    │   BGM → 节拍检测 → 素材/图片 → 拍点切换 → xfade过渡 → 文字叠加
    │   适用: 卡点视频、节奏混剪
    │
    ├─→ 数字人策略 🔧 (待开发)
    │   DreamActor M1: 照片 + 参考视频 → 动作模仿视频
    │   OmniHuman: 头像 + 音频 → 对口型数字人
    │   适用: 数字人出镜、动作模仿
    │
    └─→ 模板策略 🔍 (调研中)
        pyJianYingDraft/CapCutAPI → 程序化生成剪映草稿 → 渲染导出
        适用: 批量生产、模板复用
```

### 各策略依赖

| 策略 | 核心依赖 | API | 状态 |
|:-----|:---------|:----|:----:|
| 口播 | CosyVoice + Pexels + mlx-audiocraft | 阿里云 + Pexels | ✅ 可用 |
| 卡点 | librosa + FFmpeg xfade | 无 | ✅ P1 完成 |
| 数字人 | OmniHuman / DreamActor M1 | 火山引擎 | ✅ OmniHuman + DreamActor 均已可用 |
| 模板 | pyJianYingDraft / CapCutAPI | 无(本地剪映) | 🔍 调研中 |

### 实施优先级

| 阶段 | 内容 | 状态 |
|:----|:-----|:----:|
| P1 | beat-sync 卡点模式 | ✅ 完成 |
| P2 | DreamActor M1 动作模仿接入 | ✅ 完成 |
| P3 | 视频工厂 CLI (策略路由) | ✅ 完成 |
| P4 | 剪映模板集成 | 🔍 调研中 |

### 待优化
- 生成速度: mlx-audiocraft 在 M1 上 10s 需 ~46s (~4.7x)
- 视频分段渲染: 3分钟以上自动分段 (composer 已有代码，未充分测试)
- 字幕叠加: ASS 字幕 (composer 已有代码，generate 未启用)
- 锚点提取: librosa 模块 (目前未集成到全链路)

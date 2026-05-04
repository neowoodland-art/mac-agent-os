# TOOL.md — AVE v2.0 (AudioScore Video Engine)

> **工具版本**: v1.0
> **接入日期**: 2026-05-04
> **维护者**: ghai
> **路径方案**: local.yaml + local_paths.py（无软链接，多机安全）
> **更新日期**: 2026-05-04

---

## 一句话说明

通过**导演脚本**（YAML）驱动，自动完成文案→人声合成→素材搜索→背景音乐→渲染合成的全流程视频编排。可作为 WorkBuddy 技能被调用。

---

## 依赖的 API 服务

| 服务 | 用途 | 费用 | 配置位置 |
|------|------|------|---------|
| 火山引擎豆包语音 2.0 | 情绪化人声合成 | ~22元/月 | agent-local/tools/ave/config/local.yaml |
| 阿里云百炼 (CosyVoice) | 人声备选 | 按量 | 同上 |
| 阿里云百炼 (Wan2.2-S2V) | 数字人 | 按量 | 同上 |
| Pexels | 素材搜索 | 免费 | 同上 |

---

## 快速开始

```bash
# 首次部署
bash 05_tools/09_ave/install.sh

# 人声合成测试
python 05_tools/09_ave/scripts/main.py voice --text "测试文字" --output test.wav

# 素材搜索测试
python 05_tools/09_ave/scripts/main.py material --search "sunset beach"

# 完整链路
python 05_tools/09_ave/scripts/main.py generate --script demo.txt
```

---

## 架构

```
文案 ─→ 01_director_parser ─→ director_script.yaml
                                  │
         ┌────────────────────────┼────────────────────┐
         ▼                        ▼                    ▼
   02_voice_synthesizer      03_bgm_generator     05_material_producer
   豆包语音 2.0 / CosyVoice  ACE-Step / Suno      Pexels / Wan2.2
         │                        │                    │
         └────────────────────────┼────────────────────┘
                                  ▼
                            04_anchor_extractor
                            06_composer (Remotion + FFmpeg)
                                  ▼
                             final.mp4
```

---

## 文件清单

```
05_tools/09_ave/
├── TOOL.md                    ← 本文件
├── install.sh                 ← 一键安装
├── config.yaml                ← 配置模板
├── requirements.txt.pip       ← Python 依赖
├── scripts/
│   ├── main.py                ← CLI 入口
│   ├── 01_director_parser/    ← 文案解析
│   ├── 02_voice_synthesizer/  ← 人声合成
│   ├── 03_bgm_generator/      ← 背景音乐
│   ├── 04_anchor_extractor/   ← 锚点提取
│   ├── 05_material_producer/  ← 素材生产
│   ├── 06_composer/           ← 渲染合成
│   ├── 07_service_layer/      ← API 服务
│   └── lib/                   ← 通用库
agent-local/tools/ave/
├── config/local.yaml          ← 本地密钥
└── cache/                     ← 缓存
```

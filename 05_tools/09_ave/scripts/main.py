#!/usr/bin/env python3
"""
AVE v2.0 — AudioScore Video Engine CLI

版本: v1.1 | 更新: 2026-05-06

用法:
  python main.py voice --text "你好" --output test.wav
  python main.py material --search "sunset beach"
  python main.py parse --script demo.txt
  python main.py compose --voice voice.wav --clips clip1.mp4 clip2.mp4
  python main.py generate --script demo.txt
  python main.py emotion-test --text "你好世界"
"""
import argparse
import os
import sys

# 确保能找到 scripts 下的模块
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from lib.config import get_api_config, load_config
from lib.logger import get_logger

logger = get_logger("cli")


def main():
    parser = argparse.ArgumentParser(description="AVE v2.0 — 自动化视频编排引擎")
    sub = parser.add_subparsers(dest="command", required=True)

    # ── voice ──
    p_voice = sub.add_parser("voice", help="人声合成")
    p_voice.add_argument("--text", required=True, help="合成文本")
    p_voice.add_argument("--output", default="output.wav", help="输出路径")
    p_voice.add_argument("--provider", default="aliyun", choices=["aliyun", "volcano"], help="TTS 服务商")
    p_voice.add_argument("--emotion", default="normal", help="情绪 (normal/happy/sad/angry)")

    # ── material ──
    p_mat = sub.add_parser("material", help="素材搜索")
    p_mat.add_argument("--search", required=True, help="搜索关键词")
    p_mat.add_argument("--count", type=int, default=3, help="数量")
    p_mat.add_argument("--orientation", default="portrait", help="portrait/landscape")

    # ── parse ──
    p_parse = sub.add_parser("parse", help="文案→导演脚本")
    p_parse.add_argument("--script", required=True, help="文案文件路径")
    p_parse.add_argument("--style", default="knowledge_lecture", help="视频风格")
    p_parse.add_argument("--no-llm", action="store_true", help="不使用 LLM，手动模板")

    # ── compose ──
    p_comp = sub.add_parser("compose", help="视频合成")
    p_comp.add_argument("--voice", required=True, help="人声 WAV 路径")
    p_comp.add_argument("--clips", nargs="+", required=True, help="素材视频路径列表")
    p_comp.add_argument("--bgm", default=None, help="BGM 路径 (可选)")
    p_comp.add_argument("--output", default="final.mp4", help="输出路径")
    p_comp.add_argument("--resolution", default="1080x1920", help="分辨率")

    # ── anchors ──
    p_anc = sub.add_parser("anchors", help="锚点提取")
    p_anc.add_argument("--voice", required=True, help="人声 WAV 路径")
    p_anc.add_argument("--bgm", default=None, help="BGM 路径 (可选)")
    p_anc.add_argument("--output", default="anchors.json", help="输出路径")

    # ── generate ──
    p_gen = sub.add_parser("generate", help="全链路生成")
    p_gen.add_argument("--script", required=True, help="文案文件路径")
    p_gen.add_argument("--style", default="knowledge_lecture", help="视频风格")
    p_gen.add_argument("--output", default="final.mp4", help="输出路径")
    p_gen.add_argument("--clips-per-segment", type=int, default=2, help="每段搜索素材数 (默认2)")
    p_gen.add_argument("--bgm", default=None, help="BGM 路径或情感类型 (可选)")
    p_gen.add_argument("--subtitles", action="store_true", default=True, help="叠加字幕 (默认开启)")
    p_gen.add_argument("--anchor-transitions", action="store_true", default=False,
                       help="锚点驱动画面切换 (在静音处自动切素材+淡变)")
    p_gen.add_argument("--duck", action="store_true", default=False,
                       help="BGM 音量避让 (说话压低BGM, 间隙恢复)")

    # ── emotion-test ──
    p_emo = sub.add_parser("emotion-test", help="情绪参数测试")
    p_emo.add_argument("--text", required=True, help="测试文本")
    p_emo.add_argument("--output-dir", default="/tmp/ave_emotion_test", help="输出目录")
    p_emo.add_argument("--emotions", default=None, help="逗号分隔的情绪列表 (默认全部)")

    # ── bgm ──
    p_bgm = sub.add_parser("bgm", help="生成背景音乐")
    p_bgm.add_argument("--mood", default="normal", help="情绪 (calm/soothing/happy/excited/sad/mystery/professional/normal/funny/inspiring)")
    p_bgm.add_argument("--duration", type=float, default=60, help="时长(秒)")
    p_bgm.add_argument("--output", default="/tmp/ave_bgm.wav", help="输出路径")
    p_bgm.add_argument("--pixabay-key", default=None, help="Pixabay API Key (可选)")
    p_bgm.add_argument("--use-mlx", action="store_true", help="尝试 mlx-audiocraft AI 生成 (需安装)")

    # ── digital-human ──
    p_dh = sub.add_parser("digital-human", help="生成数字人视频 (Wan2.2)")
    p_dh.add_argument("--image", required=True, help="头像图片路径")
    p_dh.add_argument("--text", default="关注我，一起聆听世界", help="口播文案")
    p_dh.add_argument("--output", default="/tmp/ave_digital_human.mp4", help="输出路径")
    p_dh.add_argument("--resolution", default="480P", choices=["480P", "720P"], help="分辨率")

    # ── beat-sync ──
    p_bs = sub.add_parser("beat-sync", help="卡点视频 (BGM节拍驱动画面切换)")
    p_bs.add_argument("--bgm", required=True, help="BGM 音频路径")
    p_bs.add_argument("--clips", nargs="*", default=[], help="素材路径列表 (可选)")
    p_bs.add_argument("--search", default="", help="Pexels 搜索关键词 (素材不够时补充)")
    p_bs.add_argument("--output", default="/tmp/ave_beat_sync.mp4", help="输出路径")
    p_bs.add_argument("--group-size", type=int, default=4, help="每组节拍数 (默认4)")
    p_bs.add_argument("--texts", nargs="*", default=[], help="每段叠加的文字 (可选)")
    p_bs.add_argument("--resolution", default="1080x1920", help="分辨率")

    args = parser.parse_args()

    # ─── dispatch ───

    if args.command == "voice":
        cfg = load_config()
        if args.provider == "aliyun":
            from voice_synthesizer.aliyun import synthesize
            ak = cfg.get("aliyun", {}).get("api_key", "")
            vid = cfg.get("aliyun", {}).get("voice_id", "")
            synthesize(args.text, args.output, api_key=ak, voice_id=vid, emotion=args.emotion)
        else:
            from voice_synthesizer.volcano import synthesize
            vcfg = cfg.get("volcano", {})
            synthesize(args.text, args.output,
                       access_token=vcfg.get("access_token", ""),
                       app_id=vcfg.get("app_id", ""),
                       access_key_id=vcfg.get("access_key_id", ""),
                       secret_access_key=vcfg.get("secret_access_key", ""))

    elif args.command == "material":
        cfg = load_config()
        api_key = cfg.get("pexels", {}).get("api_key", "")
        from material_producer.pexels.search import search_videos
        results = search_videos(args.search, args.count, api_key=api_key, orientation=args.orientation)
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['path']} ({r['duration']}s)")

    elif args.command == "parse":
        from director_parser.parser import parse_script
        out = parse_script(args.script, style=args.style, use_llm=not args.no_llm)
        print(f"✅ 导演脚本已生成: {out}")

    elif args.command == "compose":
        from composer.ffmpeg import compose_video, mix_audio, create_subtitles
        # 先混音
        mixed = mix_audio(args.voice, args.bgm) if args.bgm else args.voice
        # 合成视频
        compose_video(args.clips, mixed, args.output, resolution=args.resolution)

    elif args.command == "anchors":
        from anchor_extractor.extractor import extract_anchors
        extract_anchors(args.voice, args.bgm, args.output)

    elif args.command == "emotion-test":
        from voice_synthesizer.aliyun import synthesize
        cfg = load_config()
        ak = cfg.get("aliyun", {}).get("api_key", "")
        vid = cfg.get("aliyun", {}).get("voice_id", "")

        emotions = args.emotions.split(",") if args.emotions else [
            "normal", "happy", "sad", "angry", "soothing", "excited", "mystery", "professional"
        ]

        out_dir = args.output_dir
        os.makedirs(out_dir, exist_ok=True)

        print(f"[AVE] 情绪测试: {args.text!r}")
        print(f"       输出目录: {out_dir}")
        print(f"       情绪列表: {emotions}")
        print()

        results = []
        for emo in emotions:
            out_path = os.path.join(out_dir, f"emotion_{emo}.wav")
            try:
                synthesize(args.text, out_path, api_key=ak, voice_id=vid, emotion=emo, speed=1.0)
                size_kb = os.path.getsize(out_path) // 1024
                print(f"  ✅ {emo:15s} → {out_path} ({size_kb}KB)")
                results.append((emo, out_path, None))
            except Exception as e:
                print(f"  ❌ {emo:15s} → 失败: {e}")
                results.append((emo, None, str(e)))

        print()
        print("=" * 50)
        print("情绪测试结果汇总")
        print("=" * 50)
        for emo, path, err in results:
            status = "✅" if path else "❌"
            print(f"  {status} {emo:15s} {'OK' if path else err}")
        print()
        print(f"提示: 用 ffplay /tmp/ave_emotion_test/emotion_*.wav 试听对比")

    elif args.command == "bgm":
        from bgm_generator.suno import generate_bgm, get_available_moods
        print(f"[AVE] BGM 生成: mood={args.mood}, duration={args.duration}s")
        print(f"       可用情绪: {get_available_moods()}")

        # 从配置读取 Pixabay Key (如果有)
        cfg = load_config()
        pixabay_key = args.pixabay_key or cfg.get("pixabay", {}).get("api_key", "")

        out = generate_bgm(
            mood=args.mood,
            duration=args.duration,
            output=args.output,
            pixabay_key=pixabay_key,
            use_mlx=args.use_mlx,
        )
        size_kb = os.path.getsize(out) // 1024
        print(f"\n✅ BGM 生成: {out} ({size_kb}KB)")
        print(f"   试听: ffplay {out}")

    elif args.command == "digital-human":
        from voice_synthesizer.aliyun import synthesize
        from material_producer.wan2_2.wan2_2 import generate_digital_human

        cfg = load_config()
        ak = cfg.get("aliyun", {}).get("api_key", "")
        vid = cfg.get("aliyun", {}).get("voice_id", "")

        # 合成人声 (≤20s)
        audio_path = "/tmp/ave_dh_voice.wav"
        print(f"[AVE] 数字人生成: {args.text}")
        print("  第1步: 合成人声...")
        synthesize(args.text, audio_path, api_key=ak, voice_id=vid, emotion="normal")

        # 生成数字人
        print("  第2步: 生成数字人 (Wan2.2, ~5-10分钟)...")
        result = generate_digital_human(
            args.image, audio_path, ak,
            output_path=args.output,
            resolution=args.resolution,
            text=args.text,
        )
        import os as _os
        size_mb = _os.path.getsize(result) / 1024 / 1024
        print(f"\n✅ 数字人完成: {result} ({size_mb:.1f}MB)")

    elif args.command == "beat-sync":
        from composer.beat_sync import compose_beat_sync
        from lib.config import load_config

        cfg = load_config()
        pexels_key = cfg.get("pexels", {}).get("api_key", "")

        print(f"[AVE] Beat-Sync 卡点视频")
        print(f"  BGM: {args.bgm}")
        print(f"  素材: {len(args.clips)} 个 + 搜索 '{args.search}'")
        print(f"  节拍分组: {args.group_size}拍/组")
        if args.texts:
            print(f"  文字: {len(args.texts)} 段")

        compose_beat_sync(
            bgm_path=args.bgm,
            output_path=args.output,
            material_clips=args.clips or None,
            group_size=args.group_size,
            resolution=args.resolution,
            texts=args.texts or None,
            pexels_api_key=pexels_key,
            pexels_search=args.search,
        )
        import os as _os
        sz_mb = _os.path.getsize(args.output) / 1024 / 1024
        print(f"\n✅ Beat-Sync 完成: {args.output} ({sz_mb:.0f}MB)")

    elif args.command == "generate":
        cfg = load_config()

        print(f"[AVE] 全链路生成: {args.script}")
        print("  第1步: 读取脚本...")
        import yaml

        # 如果输入是 YAML 直接读，否则用 LLM 解析
        if args.script.endswith((".yaml", ".yml")):
            with open(args.script, encoding="utf-8") as f:
                script_data = yaml.safe_load(f)
            script_path = args.script
            print(f"    已编译 YAML，直接读取")
        else:
            from director_parser.parser import parse_script
            script_path = parse_script(args.script, style=args.style)
            with open(script_path, encoding="utf-8") as f:
                script_data = yaml.safe_load(f)

        segments = script_data.get("segments", [])
        total_duration = sum(s.get("duration_sec", 10) for s in segments)
        print(f"    共 {len(segments)} 段, 预计 {total_duration}s")

        print("  第3步: 合成人声 (带字级时间戳)...")
        from voice_synthesizer.aliyun import synthesize_with_timestamps
        ak = cfg.get("aliyun", {}).get("api_key", "")
        vid = cfg.get("aliyun", {}).get("voice_id", "")
        text_all = "\n".join(s["text"] for s in segments)
        # 用一个全局情绪 (取第一个 segment 的或默认)
        default_emoji = segments[0].get("voice_emotion", "normal") if segments else "normal"
        voice_path, word_ts = synthesize_with_timestamps(
            text_all, "/tmp/ave_voice.wav",
            api_key=ak, voice_id=vid, emotion=default_emoji,
        )
        print(f"    字级时间戳: {len(word_ts)} 个字")

        print("  第4步: 搜索素材 (每段2个)...")
        from material_producer.pexels.search import search_videos
        mat_cfg = cfg.get("pexels", {})
        all_clips = []  # [(path, duration, segment_id), ...]
        for seg in segments:
            seg_id = seg.get("id", "?")
            keyword = seg.get("material", {}).get("search", "")
            if not keyword:
                continue
            clips = search_videos(
                keyword,
                count=args.clips_per_segment,
                api_key=mat_cfg.get("api_key", ""),
                orientation="portrait",
            )
            for c in clips:
                all_clips.append((c["path"], c["duration"], seg_id))
            print(f"    段{seg_id}: {keyword[:30]!r} → {len(clips)} 个素材")

        if not all_clips:
            print("  ⚠️ 无素材，跳过合成")
            return

        clip_paths = [c[0] for c in all_clips]
        print(f"    共 {len(clip_paths)} 个素材片段")

        print("  第5步: 混音 (人声+BGM)...")
        from composer.ffmpeg import mix_audio, duck_bgm
        bgm_path = args.bgm if args.bgm and os.path.exists(args.bgm) else None
        if bgm_path:
            if args.duck:
                print(f"    BGM: {bgm_path} (音量避让: 说话0.15→间隙0.50, {len(word_ts)} 个字)")
                ducked_bgm = duck_bgm(voice_path, bgm_path, "/tmp/ave_ducked_bgm.wav",
                                      word_timestamps=word_ts)
                mixed_audio = mix_audio(voice_path, ducked_bgm, bgm_volume=1.0)
            else:
                print(f"    BGM: {bgm_path} (音量 0.35)")
                mixed_audio = mix_audio(voice_path, bgm_path, bgm_volume=0.35)
        else:
            print("    无 BGM")
            mixed_audio = voice_path

        print("  第6步: 合成视频...")
        from composer.ffmpeg import compose_video, create_subtitles, segment_render, concat_segments, _get_media_duration

        # 字幕: 用字级时间戳计算每段精确起止
        subtitles_path = None
        if args.subtitles and segments and word_ts:
            # 从全部字的时间戳重建全文 (word_ts 每条有 text/begin_time/end_time)
            # 计算每个字的累积字符位置
            char_positions = []
            acc = 0
            for w in word_ts:
                char_positions.append(acc)
                acc += len(w["text"])
            full_text_from_ts = "".join(w["text"] for w in word_ts)

            cursor = 0
            for seg in segments:
                seg_text = seg["text"]
                try:
                    pos = full_text_from_ts.index(seg_text, cursor)
                    char_end = pos + len(seg_text)
                    # 找到 pos ≤ 累积位置 < char_end 的字
                    seg_word_indices = [i for i in range(len(word_ts))
                                        if char_positions[i] >= pos
                                        and char_positions[i] + len(word_ts[i]["text"]) <= char_end]
                    seg_words = [word_ts[i] for i in seg_word_indices] if seg_word_indices else []
                except ValueError:
                    seg_words = []

                if seg_words:
                    seg["start_sec"] = seg_words[0]["begin_time"] / 1000.0
                    seg["end_sec"] = seg_words[-1]["end_time"] / 1000.0
                else:
                    # 回退: 按全长比例估算
                    total_ms = word_ts[-1]["end_time"]
                    seg["start_sec"] = (pos / max(len(full_text_from_ts), 1)) * total_ms / 1000.0
                    seg["end_sec"] = (char_end / max(len(full_text_from_ts), 1)) * total_ms / 1000.0

                cursor = pos + len(seg_text)

            subtitles_path = "/tmp/ave_subtitles.ass"
            create_subtitles(segments, subtitles_path, resolution=(1080, 1920))
            print(f"    字幕 (精确): {subtitles_path} ({len(segments)} 段, {len(word_ts)} 字)")

        # 分段渲染: 3分钟以上自动分段
        audio_duration = _get_media_duration(mixed_audio)
        if audio_duration > 180:
            print(f"    视频较长 ({audio_duration:.0f}s > 180s)，自动分段渲染...")
            import tempfile
            seg_dir = tempfile.mkdtemp(prefix="ave_seg_")
            seg_files = segment_render(
                clip_paths, mixed_audio,
                output_dir=seg_dir,
                subtitles_path=subtitles_path,
            )
            if len(seg_files) > 1:
                concat_segments(seg_files, args.output)
                import shutil
                shutil.rmtree(seg_dir, ignore_errors=True)
                print(f"    分段拼接完成: {args.output}")
            else:
                import shutil
                shutil.move(seg_files[0], args.output)
                shutil.rmtree(seg_dir, ignore_errors=True)
        else:
            # 锚点驱动模式
            if args.anchor_transitions:
                print("    锚点驱动画面切换...")
                from anchor_extractor.extractor import get_silence_periods
                from composer.ffmpeg import compose_with_anchors
                silences = get_silence_periods(mixed_audio, min_silence_sec=0.1)
                print(f"    检测到 {len(silences)} 个静音段 (过渡点)")
                compose_with_anchors(
                    clip_paths, mixed_audio, args.output,
                    silence_periods=silences,
                    total_duration=audio_duration,
                    subtitles_path=subtitles_path,
                )
            else:
                compose_video(clip_paths, mixed_audio, args.output,
                              resolution="1080x1920",
                              subtitles_path=subtitles_path)

        print(f"\n✅ 生成完成: {args.output}")
        clip_total = sum(c[1] for c in all_clips)
        print(f"   素材总时长: {clip_total:.1f}s / 人声: {total_duration}s")


if __name__ == "__main__":
    main()

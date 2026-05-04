#!/usr/bin/env python3
"""
AVE v2.0 — AudioScore Video Engine CLI

用法:
  python main.py voice --text "你好" --output test.wav
  python main.py material --search "sunset beach"
  python main.py generate --script demo.txt
  python main.py compose --director-script script.yaml
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="AVE v2.0 — 自动化视频编排引擎")
    sub = parser.add_subparsers(dest="command", required=True)

    # voice
    p_voice = sub.add_parser("voice", help="人声合成")
    p_voice.add_argument("--text", required=True)
    p_voice.add_argument("--output", default="output.wav")
    p_voice.add_argument("--emotion", default="正常")

    # material
    p_mat = sub.add_parser("material", help="素材搜索")
    p_mat.add_argument("--search", required=True)
    p_mat.add_argument("--count", type=int, default=3)

    # parse
    p_parse = sub.add_parser("parse", help="文案→导演脚本")
    p_parse.add_argument("--script", required=True)

    # compose
    p_comp = sub.add_parser("compose", help="编排合成")
    p_comp.add_argument("--director-script", required=True)

    # generate
    p_gen = sub.add_parser("generate", help="全链路生成")
    p_gen.add_argument("--script", required=True)
    p_gen.add_argument("--style", default="knowledge_lecture")

    args = parser.parse_args()

    if args.command == "voice":
        from scripts.lib.config import get_api_config
        from scripts.voice_synthesizer.volcano import synthesize
        cfg = get_api_config("volcano")
        print(f"[AVE] 人声合成: {args.text[:30]}...")
        synthesize(args.text, args.output, cfg, emotion=args.emotion)

    elif args.command == "material":
        from scripts.lib.config import get_api_config
        from scripts.material_producer.pexels import search_videos
        cfg = get_api_config("pexels")
        print(f"[AVE] 素材搜索: {args.search}")
        urls = search_videos(args.search, args.count, cfg)
        for u in urls:
            print(f"  {u}")

    elif args.command == "parse":
        from scripts.director_parser.parser import parse_script
        print(f"[AVE] 解析文案: {args.script}")
        script = parse_script(args.script)
        print(script)

    elif args.command == "compose":
        from scripts.composer.ffmpeg import compose_video
        print(f"[AVE] 合成视频: {args.director_script}")
        compose_video(args.director_script)

    elif args.command == "generate":
        from scripts.director_parser.parser import parse_script
        from scripts.voice_synthesizer.volcano import synthesize
        from scripts.composer.ffmpeg import compose_video
        print(f"[AVE] 全链路生成: {args.script}")
        print("  此命令需要各模块就绪后才能运行")


if __name__ == "__main__":
    main()

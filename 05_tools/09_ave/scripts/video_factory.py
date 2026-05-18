"""
AVE 视频工厂 — 统一生产入口

按策略路由到不同管线, 提供统一的输入接口和进度报告。

策略:
  口播   文案 → TTS → Pexels素材 → BGM → 字幕 → 数字人片头片尾
  卡点   BGM → 节拍检测 → 素材 → 拍点切换 → xfade
  数字人  照片+音频 → OmniHuman 或 照片+视频 → DreamActor

用法:
  python main.py video-factory --strategy 口播 --script script.yaml
  python main.py video-factory --strategy 卡点 --bgm bgm.wav --search 关键词
  python main.py video-factory --strategy 数字人 --image photo.jpg --text 文案
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import os
import time
from pathlib import Path

from lib.config import load_config
from lib.cost_tracker import get_tracker, print_history
from lib.logger import get_logger

logger = get_logger("factory")


# ── 策略配置 ─────────────────────────────────────────────

STRATEGIES = {
    "口播": {
        "desc": "文案→TTS→素材→BGM→字幕→数字人片头片尾",
        "default_output": "/tmp/ave_oral.mp4",
    },
    "卡点": {
        "desc": "BGM→节拍检测→素材→拍点切换→xfade过渡",
        "default_output": "/tmp/ave_beat.mp4",
    },
    "数字人": {
        "desc": "OmniHuman(对口型) / DreamActor(动作模仿)",
        "default_output": "/tmp/ave_digital_human.mp4",
    },
    "口播+卡点": {
        "desc": "人声锚点+BGM能量变速→帧锁定拼接",
        "default_output": "/tmp/ave_hybrid.mp4",
    },
    "故事": {
        "desc": "剧本→场景分解→Kling批量生成→角色一致性拼接",
        "default_output": "/tmp/ave_story.mp4",
    },
}


def run_oral(script: str, output: str, clips_per_segment: int,
             bgm: str | None, duck: bool, anchor: bool, subtitles: bool,
             mix_engine: str = "ffmpeg") -> str:
    """口播策略: 调用 main.py generate"""
    from main import main as cli_main
    # 直接调用 generate 的逻辑
    cfg = load_config()
    import yaml

    print(f"[视频工厂] 口播策略: {script}")

    # Dashboard 埋点: 创建 production 记录
    try:
        from lib.dashboard import init_db, log_production, log_step, complete_production
        init_db()
        dash_pid = log_production(
            strategy="口播",
            script_path=script,
            script_name=os.path.basename(script) if script else "",
        )
        if dash_pid > 0:
            from lib.cost_tracker import set_current_production_id
            set_current_production_id(dash_pid)
    except Exception:
        dash_pid = -1

    # 1. 读取脚本
    if script.endswith((".yaml", ".yml")):
        with open(script, encoding="utf-8") as f:
            script_data = yaml.safe_load(f)
    else:
        from director_parser.parser import parse_script
        script = parse_script(script)
        with open(script, encoding="utf-8") as f:
            script_data = yaml.safe_load(f)

    segments = script_data.get("segments", [])
    total_duration = sum(s.get("duration_sec", 10) for s in segments)
    print(f"  脚本: {len(segments)} 段, 预计 {total_duration}s")

    # 2. TTS
    print("  [1/6] 合成人声...")
    from voice_synthesizer.aliyun import synthesize_with_timestamps
    ak = cfg.get("aliyun", {}).get("api_key", "")
    vid = cfg.get("aliyun", {}).get("voice_id", "")
    text_all = "\n".join(s["text"] for s in segments)
    voice_path, word_ts = synthesize_with_timestamps(
        text_all, "/tmp/ave_factory_voice.wav",
        api_key=ak, voice_id=vid,
    )
    if dash_pid > 0:
        log_step(dash_pid, "tts", "completed", detail=f"{len(text_all)}字")
    tracker = get_tracker()
    tracker.log("CosyVoice", chars=len(text_all), note=f"口播TTS {len(segments)}段")

    # 3. 素材搜索
    print("  [2/6] 搜索素材...")
    from material_producer.pexels.search import search_videos
    mat_cfg = cfg.get("pexels", {})
    all_clips = []
    for seg in segments:
        keyword = seg.get("material", {}).get("search", "")
        if not keyword:
            continue
        clips = search_videos(keyword, count=clips_per_segment,
                              api_key=mat_cfg.get("api_key", ""), orientation="portrait")
        all_clips.extend((c["path"], c["duration"]) for c in clips)
        tracker.log("Pexels", note=f"搜索: {keyword}")
    clip_paths = [c[0] for c in all_clips]
    print(f"  素材: {len(clip_paths)} 个")
    if dash_pid > 0:
        log_step(dash_pid, "search_material", "completed", detail=f"搜索到 {len(clip_paths)} 个素材")

    # 3.5 自动 BGM 选择 (基于情绪分析)
    if not bgm:
        print("  [▸] 自动选择 BGM (情绪分析)...")
        try:
            from audio_line.layer2_analysis.emotion_analyzer import EmotionAnalyzer
            from music_selector import BGMSelector

            emotions_analyzer = EmotionAnalyzer()
            emotion_result = emotions_analyzer.analyze(voice_path)

            # 情绪 → BGM 风格映射
            EMOTION_STYLE_MAP = {
                "energetic": "燃系",
                "happy": "轻快",
                "calm": "舒缓",
                "sad": "治愈",
                "aggressive": "燃系",
                "neutral": "治愈",
            }
            target_style = EMOTION_STYLE_MAP.get(emotion_result.mood, "治愈")
            print(f"    检测到情绪: {emotion_result.mood} ({emotion_result.description})")
            print(f"    匹配 BGM 风格: {target_style}")

            selector = BGMSelector()
            candidates = selector.get_by_style(target_style) + selector.get_trending(limit=3)
            # 去重
            seen = set()
            unique_candidates = []
            for c in candidates:
                if c["id"] not in seen:
                    seen.add(c["id"])
                    unique_candidates.append(c)

            if unique_candidates:
                chosen = unique_candidates[0]
                bgm_path_auto = chosen.get("file", "")
                if os.path.exists(bgm_path_auto):
                    bgm = bgm_path_auto
                    print(f"    ✅ 自动选中 BGM: {chosen['name']} - {chosen['artist']} ({chosen['style']})")
                else:
                    print(f"    ⚠ BGM 文件不存在，跳过: {chosen['name']} ({bgm_path_auto})")
            else:
                print("    ⚠ 未找到匹配的 BGM")
        except ImportError as e:
            print(f"    ⚠ 情绪分析模块不可用: {e} (跳过自动选BGM)")
        except Exception as e:
            print(f"    ⚠ 自动选 BGM 失败: {e}")

    # 4. BGM + 避让 + 混音
    print("  [3/6] 混音...")
    from composer.ffmpeg import mix_audio, duck_bgm
    final_audio = voice_path
    if bgm and os.path.exists(bgm):
        if duck:
            bgm_path = duck_bgm(voice_path, bgm, "/tmp/ave_factory_ducked.wav",
                                word_timestamps=word_ts)
            bgm_for_mix = bgm_path
            print(f"    BGM避让: ON")
        else:
            bgm_for_mix = bgm
            print(f"    BGM: ON (固定音量)")

        # 混音引擎选择: ffmpeg (默认) | audio_line (MixModule)
        if mix_engine == "audio_line":
            try:
                from audio_line.layer3_creation.module_d_mix import MixModule
                mix_mod = MixModule()
                mix_result = mix_mod.mix(
                    stems={"voice": voice_path, "bgm": bgm_for_mix},
                    output_path="/tmp/ave_factory_master.wav",
                    stem_levels={"voice": 0.0, "bgm": -6.0},
                )
                final_audio = mix_result.master_path
                print(f"    AudioLine 混音: {mix_result.loudness} LUFS, "
                      f"峰值={mix_result.peak_dB} dBFS")
            except Exception as e:
                print(f"    ⚠ AudioLine 混音失败: {e} (回退 ffmpeg)")
                final_audio = mix_audio(voice_path, bgm_for_mix, bgm_volume=1.0)
        else:
            final_audio = mix_audio(voice_path, bgm_for_mix, bgm_volume=1.0)

    # 5. 字幕
    print("  [4/6] 生成字幕...")
    from composer.ffmpeg import create_subtitles
    subtitles_path = None
    if subtitles and segments and word_ts:
        full_text_from_ts = "".join(w["text"] for w in word_ts)
        char_pos = []
        acc = 0
        for w in word_ts:
            char_pos.append(acc)
            acc += len(w["text"])
        cursor = 0
        for seg in segments:
            seg_text = seg["text"]
            try:
                pos = full_text_from_ts.index(seg_text, cursor)
                char_end = pos + len(seg_text)
                seg_words = [word_ts[i] for i in range(len(word_ts))
                             if char_pos[i] >= pos and char_pos[i] + len(word_ts[i]["text"]) <= char_end]
            except ValueError:
                seg_words = []
            if seg_words:
                seg["start_sec"] = seg_words[0]["begin_time"] / 1000.0
                seg["end_sec"] = seg_words[-1]["end_time"] / 1000.0
            cursor = pos + len(seg_text)
        subtitles_path = "/tmp/ave_factory_subtitles.ass"
        create_subtitles(segments, subtitles_path)
        print(f"  字幕: {len(segments)} 段")

    # 6. 合成视频
    print("  [5/6] 合成视频...")
    from composer.ffmpeg import compose_video, _get_media_duration
    from composer.ffmpeg import segment_render, concat_segments

    audio_duration = _get_media_duration(final_audio)
    if audio_duration > 180:
        import tempfile, shutil
        seg_dir = tempfile.mkdtemp(prefix="ave_fac_")
        seg_files = segment_render(clip_paths, final_audio, output_dir=seg_dir,
                                   subtitles_path=subtitles_path)
        if len(seg_files) > 1:
            concat_segments(seg_files, output)
            shutil.rmtree(seg_dir, ignore_errors=True)
        else:
            shutil.move(seg_files[0], output)
            shutil.rmtree(seg_dir, ignore_errors=True)
    else:
        if anchor:
            print("  锚点画面切换...")
            from anchor_extractor.extractor import get_silence_periods
            from composer.ffmpeg import compose_with_anchors
            silences = get_silence_periods(final_audio, min_silence_sec=0.1)
            compose_with_anchors(clip_paths, final_audio, output,
                                 silence_periods=silences,
                                 total_duration=audio_duration,
                                 subtitles_path=subtitles_path)
        else:
            compose_video(clip_paths, final_audio, output,
                          resolution="1080x1920", subtitles_path=subtitles_path)

    if dash_pid > 0:
        log_step(dash_pid, "compose", "completed", cost=0, detail=f"{audio_duration:.0f}s 视频")

    # 7. LipSync 后处理 (如果脚本指定了角色且有定妆照)
    print("  [6/7] 检查 LipSync 后处理...")
    character_refs = script_data.get("meta", {}).get("character_refs", [])
    lipsync_needed = False
    for seg in segments:
        if seg.get("character_ref") and any(
            cr.get("lip_sync") for cr in character_refs if cr.get("name") == seg["character_ref"]
        ):
            lipsync_needed = True
            break
    if lipsync_needed:
        print("    角色 LipSync 已启用, 尝试后处理...")
        try:
            cfg = load_config()
            fal_key = cfg.get("fal", {}).get("api_key", "")
            if fal_key:
                from composer.lipsync import lipsync_audio_to_video
                lipsync_result = lipsync_audio_to_video(
                    video_path=output,
                    audio_path=voice_path,
                    output_path=output.replace(".mp4", "_lipsync.mp4"),
                )
                # 替换原视频
                import shutil
                shutil.move(lipsync_result, output)
                print(f"    ✅ LipSync 完成")
                if dash_pid > 0:
                    log_step(dash_pid, "lipsync", "completed", detail="口型对齐")
            else:
                print("    ⏭️ 未配置 fal.ai API Key, 跳过 LipSync")
        except Exception as e:
            print(f"    ⚠️ LipSync 失败: {e} (不影响主线流程)")

    # 8. 检查数字人片头片尾 (可选)
    print("  [7/7] 检查数字人片头片尾...")
    avatar_cfg = script_data.get("meta", {}).get("avatar", {})
    opening_text = avatar_cfg.get("opening_text", "")
    closing_text = avatar_cfg.get("closing_text", "")
    avatar_image = avatar_cfg.get("image", "")

    if avatar_image and opening_text:
        print("  需要生成片头 + 片尾数字人 (需手动调用 digital-human)")
        print(f"  片头: {opening_text}")
        print(f"  片尾: {closing_text}")

    sz_mb = os.path.getsize(output) / 1024 / 1024
    print(f"\n✅ 口播完成: {output} ({sz_mb:.0f}MB, {audio_duration:.0f}s)")

    # Dashboard: 完成 production
    if dash_pid > 0:
        try:
            complete_production(
                dash_pid, status="completed", output_path=output,
                duration_sec=audio_duration,
                total_cost=get_tracker()._total_cost(),
            )
            from lib.cost_tracker import set_current_production_id
            set_current_production_id(0)
        except Exception:
            pass

    return output


def run_beat(bgm: str, output: str, search: str, group_size: int,
             clips: list[str], texts: list[str],
             target_bpm: float = 0.0) -> str:
    """卡点策略"""
    print(f"[视频工厂] 卡点策略: {bgm}")
    from composer.beat_sync import compose_beat_sync
    cfg = load_config()
    pexels_key = cfg.get("pexels", {}).get("api_key", "")

    result = compose_beat_sync(
        bgm_path=bgm,
        output_path=output,
        material_clips=clips or None,
        group_size=group_size,
        texts=texts or None,
        pexels_api_key=pexels_key,
        pexels_search=search,
        target_bpm=target_bpm,
    )
    return result


def run_digital_human(image: str, text: str, output: str, resolution: str,
                      mode: str, video: str | None,
                      character: str = "") -> str:
    """数字人策略"""
    from voice_synthesizer.aliyun import synthesize
    cfg = load_config()
    ak = cfg.get("aliyun", {}).get("api_key", "")
    vid = cfg.get("aliyun", {}).get("voice_id", "")

    # 角色注册 → 音色选择
    char_voice_style = ""
    if character:
        try:
            from character_registry import CharacterRegistry
            registry = CharacterRegistry()
            try:
                char_obj = registry.get_character(character)
                char_voice_style = char_obj.voice_style
                print(f"  角色 '{character}' 音色: {char_voice_style}")
            except KeyError:
                print(f"  ⚠ 未找到角色 '{character}', 使用默认音色")
        except Exception as e:
            print(f"  ⚠ 角色注册读取失败: {e}")

    print(f"[视频工厂] 数字人策略: mode={mode}")

    # 角色 voice_style → voice_id 映射 (占位, 可根据实际音色库扩展)
    VOICE_STYLE_MAP = {
        "甜美": "wan2.2-s2v",  # 示例映射
        "成熟": "cosyvoice-v3.5-plus",
        "知性": "cosyvoice-v3.5-plus",
        "默认": vid,
    }
    if char_voice_style and char_voice_style in VOICE_STYLE_MAP:
        vid = VOICE_STYLE_MAP[char_voice_style]
        print(f"  → 映射音色: {char_voice_style} → {vid}")

    if mode == "对口型":
        from material_producer.wan2_2.wan2_2 import generate_digital_human
        audio_path = "/tmp/ave_factory_dh_voice.wav"
        print("  [1/2] 合成人声...")
        synthesize(text, audio_path, api_key=ak, voice_id=vid)
        print("  [2/2] 生成数字人 (OmniHuman)...")
        result = generate_digital_human(
            image, audio_path, ak, output_path=output,
            resolution=resolution, text=text,
        )
    elif mode == "动作模仿":
        if not video:
            raise ValueError("动作模仿模式需要 --video 参数")
        # DreamActor M1 调用
        from lib.ghvideo_upload import upload_and_get_url
        import httpx, json, hmac, hashlib, datetime
        from datetime import timezone

        ak_v = cfg.get("volcano", {}).get("access_key_id", ak)
        sk_v = cfg.get("volcano", {}).get("secret_access_key", "")

        host='visual.volcengineapi.com';region='cn-north-1';service='cv'

        def sr(p,b):
            t=datetime.datetime.now(timezone.utc);cd=t.strftime('%Y%m%dT%H%M%SZ');ds=t.strftime('%Y%m%d')
            q='&'.join(f'{k}={p[k]}'for k in sorted(p));ph=hashlib.sha256(b.encode()).hexdigest()
            kd=hmac.new(sk_v.encode(),ds.encode(),hashlib.sha256).digest();kr=hmac.new(kd,region.encode(),hashlib.sha256).digest()
            ks=hmac.new(kr,service.encode(),hashlib.sha256).digest();skey=hmac.new(ks,b'request',hashlib.sha256).digest()
            sig=hmac.new(skey,f'HMAC-SHA256\n{cd}\n{ds}/{region}/{service}/request\n{hashlib.sha256(f"POST\n/\n{q}\ncontent-type:application/json\nhost:{host}\nx-content-sha256:{ph}\nx-date:{cd}\n\ncontent-type;host;x-content-sha256;x-date\n{ph}".encode()).hexdigest()}'.encode(),hashlib.sha256).hexdigest()
            return {'X-Date':cd,'Authorization':f'HMAC-SHA256 Credential={ak_v}/{ds}/{region}/{service}/request, SignedHeaders=content-type;host;x-content-sha256;x-date, Signature={sig}','X-Content-Sha256':ph,'Content-Type':'application/json'}

        # 获取公网URL
        img_url = upload_and_get_url(image) if not image.startswith("http") else image
        vid_url = upload_and_get_url(video) if not video.startswith("http") else video
        print(f"  头像URL: {img_url[:60]}...")
        print(f"  参考视频URL: {vid_url[:60]}...")

        p={'Action':'CVSync2AsyncSubmitTask','Version':'2022-08-31'}
        b=json.dumps({'req_key':'jimeng_dream_actor_m1_gen_video_cv','image_url':img_url,'video_url':vid_url})
        r=httpx.post(f'https://{host}/',params=p,headers=sr(p,b),data=b,timeout=30).json()
        tid=r.get('data',{}).get('task_id','')
        print(f"  任务提交: {tid}")

        for i in range(60):
            time.sleep(10)
            p2={'Action':'CVSync2AsyncGetResult','Version':'2022-08-31'}
            b2=json.dumps({'req_key':'jimeng_dream_actor_m1_gen_video_cv','task_id':tid})
            try:
                r2=httpx.post(f'https://{host}/',params=p2,headers=sr(p2,b2),data=b2,timeout=30).json()
                s=r2.get('data',{}).get('status','?');u=r2.get('data',{}).get('video_url','')
                if u:
                    r3=httpx.get(u,timeout=120)
                    with open(output,'wb') as f:f.write(r3.content)
                    dur=r2.get('usage',{}).get('duration',0)
                    get_tracker().log("DreamActor",duration=dur,resolution=resolution.replace("P","")+"P",note="动作模仿")
                    break
                print(f'    [{i+1}/60] {s}')
                if s in ('FAILED','failed'):
                    print(f'  失败: {json.dumps(r2,ensure_ascii=False)[:300]}')
                    break
            except Exception as e:
                print(f'    [{i+1}/60] {e}')
                time.sleep(5)
    else:
        raise ValueError(f"未知数字人模式: {mode}")

    sz_mb = os.path.getsize(result) / 1024 / 1024
    print(f"\n✅ 数字人完成: {result} ({sz_mb:.1f}MB)")
    return result


def run_hybrid(
    voice: str, bgm: str, output: str,
    search: str = "", group_size: int = 4,
    clips: list[str] | None = None,
    texts: list[str] | None = None,
    enable_speed_ramp: bool = True,
    base_speed: float = 1.0, high_speed: float = 1.5, low_speed: float = 0.7,
    min_silence: float = 0.15,
) -> str:
    """口播+卡点融合策略"""
    from composer.hybrid import compose_hybrid
    cfg = load_config()
    pexels_key = cfg.get("pexels", {}).get("api_key", "")

    print(f"[视频工厂] 口播+卡点策略")
    print(f"  人声: {voice}")
    print(f"  BGM:  {bgm}")
    print(f"  变速: {'关闭' if not enable_speed_ramp else f'{low_speed:.1f}~{high_speed:.1f}x'}")

    # Dashboard 埋点
    try:
        from lib.dashboard import init_db, log_production, log_step, complete_production
        init_db()
        prod_id = log_production("hybrid", f"混合_{Path(voice).stem}")
        log_step(prod_id, "compose", "开始")
    except Exception:
        pass

    result = compose_hybrid(
        voice_path=voice,
        bgm_path=bgm,
        output_path=output,
        material_clips=clips or None,
        texts=texts or None,
        pexels_api_key=pexels_key,
        pexels_search=search,
        enable_speed_ramp=enable_speed_ramp,
        base_speed=base_speed,
        high_speed=high_speed,
        low_speed=low_speed,
        group_size=group_size,
        min_silence_sec=min_silence,
    )

    try:
        complete_production(prod_id)
    except Exception:
        pass

    return result


def run_story(
    script: str,
    output: str,
    character: str = "",
    block: str = "",
    story_model: str = "turbo",
    story_duration: int = 5,
    story_lang: str = "en",
    seed: int = 42,
    dry_run: bool = False,
    force: bool = False,
) -> str:
    """故事策略: 剧本→场景分解→Kling批量生成→拼接"""
    from story_director.scene_planner import plan_scenes, export_scenes
    from story_director.temporal_bridge import enrich_scenes_with_bridges
    from story_director.batch_generator import run_story_pipeline

    cfg = load_config()

    print(f"[视频工厂] 故事策略: {script}")
    print(f"  角色: {character or '(无)'}  Seed: {seed}")

    # Dashboard 埋点
    try:
        from lib.dashboard import init_db, log_production, log_step, complete_production
        init_db()
        prod_id = log_production("故事", os.path.basename(script))
        if prod_id > 0:
            from lib.cost_tracker import set_current_production_id
            set_current_production_id(prod_id)
            log_step(prod_id, "plan_scenes", "开始")
    except Exception:
        prod_id = -1

    # 加载角色描述块
    character_block = block
    if not character_block and character:
        from character_sheet import load_character
        char = load_character(character)
        if char:
            character_block = char.get("description", "")
            print(f"  角色库: '{character}' → {character_block[:40]}...")

    # Step 1: 场景分解
    print("  [1/3] 场景分解...")
    scenes = plan_scenes(
        script_path=script,
        character_name=character or None,
        character_block=character_block,
        lang=story_lang,
    )
    print(f"    → {len(scenes)} 个场景")
    if prod_id > 0:
        log_step(prod_id, "plan_scenes", "completed", detail=f"{len(scenes)} 场景")

    # Step 2: 桥接
    print("  [2/3] 过渡桥接...")
    enriched = enrich_scenes_with_bridges(scenes, character_block=character_block)
    import time
    tmp_scenes_path = f"/tmp/ave_story_scenes_factory_{int(time.time())}.json"
    export_scenes(scenes, tmp_scenes_path, character_block=character_block,
                  lang=story_lang, seed=seed)
    if prod_id > 0:
        log_step(prod_id, "build_bridges", "completed")

    if dry_run:
        print("\n⏸️  Dry-run — 场景分解:")
        for s in enriched:
            bridge = s.get("bridge_to_next", {})
            print(f"  Scene {s['scene_id']}: {s.get('duration_sec', '?')}s "
                  f"char={s.get('character_ref', 'none')} "
                  f"trans={bridge.get('type', '-') if bridge else '-'}")
            print(f"    Prompt: {s.get('prompt', '')[:80]}...")
        return ""

    # Step 3: 批量生成
    print("  [3/3] 批量 Kling 生成...")
    pipeline_result = run_story_pipeline(
        scenes_path=tmp_scenes_path,
        output_dir="",
        model=story_model,
        duration=story_duration,
        force=force,
    )

    # 尝试拼接最终视频
    import subprocess
    concat_script = pipeline_result.get("concat_script", "")
    if concat_script and os.path.exists(concat_script):
        print(f"  [后处理] 执行拼接脚本...")
        try:
            subprocess.run(["bash", concat_script, output], check=True, timeout=600)
        except subprocess.TimeoutExpired:
            print("  ⚠️ 拼接超时")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️ 拼接失败: {e}")

    if prod_id > 0:
        try:
            complete_production(prod_id, output_path=output,
                                total_cost=get_tracker()._total_cost())
            set_current_production_id(0)
        except Exception:
            pass

    # 汇总
    for r in pipeline_result.get("results", []):
        icon = "✅" if r["status"] == "success" else "💾" if r["status"] == "cached" else "❌"
        print(f"  {icon} Scene {r['scene_id']:2d}: {r.get('path', 'N/A')}")

    return output


def show_status():
    """显示工厂状态"""
    print("=" * 40)
    print("🎬 AVE 视频工厂 · 状态")
    print("=" * 40)
    print()
    for name, info in STRATEGIES.items():
        print(f"  {name:5s}: {info['desc']}")
    print()
    tracker = get_tracker()
    tracker.summary()

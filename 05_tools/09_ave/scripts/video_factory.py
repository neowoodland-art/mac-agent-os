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
}


def run_oral(script: str, output: str, clips_per_segment: int,
             bgm: str | None, duck: bool, anchor: bool, subtitles: bool) -> str:
    """口播策略: 调用 main.py generate"""
    from main import main as cli_main
    # 直接调用 generate 的逻辑
    cfg = load_config()
    import yaml

    print(f"[视频工厂] 口播策略: {script}")

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

    # 4. BGM + 避让 + 混音
    print("  [3/6] 混音...")
    from composer.ffmpeg import mix_audio, duck_bgm
    final_audio = voice_path
    if bgm and os.path.exists(bgm):
        if duck:
            bgm_path = duck_bgm(voice_path, bgm, "/tmp/ave_factory_ducked.wav",
                                word_timestamps=word_ts)
            final_audio = mix_audio(voice_path, bgm_path, bgm_volume=1.0)
            print(f"    BGM避让: ON")
        else:
            final_audio = mix_audio(voice_path, bgm, bgm_volume=0.35)
            print(f"    BGM: ON (固定音量)")

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

    # 7. 数字人片头片尾 (可选)
    print("  [6/6] 检查数字人片头片尾...")
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
    return output


def run_beat(bgm: str, output: str, search: str, group_size: int,
             clips: list[str], texts: list[str]) -> str:
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
    )
    return result


def run_digital_human(image: str, text: str, output: str, resolution: str,
                      mode: str, video: str | None) -> str:
    """数字人策略"""
    from voice_synthesizer.aliyun import synthesize
    cfg = load_config()
    ak = cfg.get("aliyun", {}).get("api_key", "")
    vid = cfg.get("aliyun", {}).get("voice_id", "")

    print(f"[视频工厂] 数字人策略: mode={mode}")

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

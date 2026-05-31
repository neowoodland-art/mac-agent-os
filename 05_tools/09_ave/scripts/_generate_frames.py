"""
批量生成 8 张漫剧分镜图 — WorkBuddy 云服务 (混元生图 3.0)
"""
import sys, json, os, subprocess, time

OUT_DIR = "/Users/7kecheng/workbuddy-agent-os/agent-local/tools/ave/cache/generated/PROD-20260517-0003"
os.makedirs(OUT_DIR, exist_ok=True)

CLOUD_SCRIPT = "/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/builtin-skills/buddy-multimodal-generation/scripts/buddy-cloud.py"
PYTHON = "/Users/7kecheng/.workbuddy/binaries/python/envs/agent-os/bin/python"

# 从 visual_prompts JSON 加载
with open("/Users/7kecheng/workbuddy-agent-os/agent-local/tools/ave/cache/PROD-20260517-0003_visual_prompts.json") as f:
    prompts = json.load(f)

# 读取 token
token = open("/dev/tty", "r") if False else ""  # placeholder — will pass via pipe

print(f"将生成 {len(prompts)} 张分镜图")
print()

results = []
for i, vp in enumerate(prompts):
    seg_id = vp["id"]
    scene = vp["scene"]
    prompt = vp["visual_prompt"]

    # 清理 prompt — 去掉架构标记，转为纯文本描述
    clean_prompt = (
        f"日系清新漫画风格。{scene}。"
        f"主角阿远，黑短发戴细框眼镜，"
        f"情绪：{vp['emotion']}。"
        f"镜头：{vp.get('reference_image', '中景')}"
    )
    # 使用更精确的 prompt
    final_prompt = (
        f"日系清新漫画风格，{scene}。"
        f"一个25岁黑短发戴细框金属眼镜的偏瘦男生阿远，"
        f"表情{vp['emotion']}。"
        f"柔和色调，线条干净，温暖治愈氛围。"
    )

    out_path = f"{OUT_DIR}/seg_{seg_id:02d}_{scene}.png"
    print(f"[{i+1}/{len(prompts)}] #{seg_id} {scene} — 生成中...", end=" ", flush=True)

    start = time.time()
    # 使用 --no-poll 先提交，后续再检查状态
    # 先试试直接同步生成
    result = subprocess.run(
        [PYTHON, CLOUD_SCRIPT, "image", final_prompt,
         "--resolution", "1248:832",
         "--revise", "1",
         "--token-stdin"],
        input=token,
        capture_output=True, text=True, timeout=300
    )
    elapsed = time.time() - start

    if result.returncode == 0:
        # 从输出中提取图片 URL
        output = result.stdout.strip()
        print(f"✅ ({elapsed:.0f}s)")
        # 保存输出信息
        results.append({"id": seg_id, "scene": scene, "output": output, "path": out_path})
    else:
        print(f"❌ 失败: {result.stderr.strip()[:100]}")
        results.append({"id": seg_id, "scene": scene, "error": result.stderr.strip()})

print(f"\n完成: {len([r for r in results if 'output' in r])}/{len(prompts)} 张")

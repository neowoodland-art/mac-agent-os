"""
AVE v2.0 脚本工厂 — 从素材生成导演脚本
"""
import os, sys, json, yaml, argparse, datetime, urllib.request, re
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "scripts_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

OMLX_URL = "http://localhost:8000/v1/chat/completions"

def ai(prompt, tokens=2000, temp=0.3):
    body = json.dumps({"model": "Qwen3-8B-MLX-4bit", "messages": [{"role":"user","content":prompt}], "max_tokens":tokens, "temperature":temp}).encode()
    req = urllib.request.Request(OMLX_URL, data=body, headers={"Authorization":"Bearer omlx","Content-Type":"application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=300).read())["choices"][0]["message"]["content"]

def analyze(title, desc):
    r = ai(f"""分析以下内容，输出JSON：
标题：{title}
描述：{desc}
输出：{{"core_topic":"一句话主题","target_audience":"目标人群","hook_type":"钩子类型","key_points":["点1","点2"],"emotional_tone":"情绪基调","suggested_style":"knowledge_lecture/bedtime_story/funny_talk/tech_review"}}""", 800, 0.3)
    m = re.search(r'\{.*\}', r, re.DOTALL)
    return json.loads(m.group()) if m else {"core_topic":title,"key_points":[]}

def segments(analysis, style):
    kp = analysis.get("key_points",[])
    pts = "\n".join([f"- {p}" for p in kp]) if kp else ""
    r = ai(f"""你是一个短视频脚本专家。生成分段口播脚本。

主题：{analysis.get("core_topic","")}
要点：{pts}
风格：{style}

字段：id(数字), text(口播文本), duration_sec(秒), voice_emotion(语气), camera(镜头), bgm_section(intro/main/climax/outro), material.search(英文搜索词), subtitles(true/false)

要求：4-6段，总60-90秒。首段5-8秒钩子，末段总结。

输出JSON数组：
[{{"id":1,"text":"...","duration_sec":8,"voice_emotion":"开场悬念","camera":"slow_zoom_in","bgm_section":"intro","material":{{"search":"..."}},"subtitles":true}}]""", 2000, 0.3)
    m = re.search(r'\[.*?\]', r, re.DOTALL)
    segs = json.loads(m.group()) if m else []
    for i,s in enumerate(segs):
        s["id"]=i+1
        bgm=str(s.get("bgm_section","")).lower()
        for v in ["intro","main","climax","outro"]:
            if v in bgm: s["bgm_section"]=v; break
        else: s["bgm_section"]="main"
    return segs

def run(topic, style=None):
    a = analyze(topic, topic)
    s = style or a.get("suggested_style","knowledge_lecture")
    segs = segments(a, s) or [{"id":1,"text":topic,"duration_sec":30,"voice_emotion":"正常讲述","camera":"medium_shot","bgm_section":"main","material":{"search":topic},"subtitles":True}]
    pid = f"vid_{datetime.date.today().strftime('%Y%m%d')}_{int(datetime.datetime.now().timestamp())%10000:04d}"
    y = {"meta":{"project_id":pid,"style":s,"voice":{"provider":"volcano","voice_id":"my_voice","default_emotion":a.get("emotional_tone","专业沉稳")},"bgm":{"provider":"ace_step","genre":"cinematic","tempo":110,"mood":"inspirational","structure":[{"section":"intro"},{"section":"main"},{"section":"climax"},{"section":"outro"}]},"output":{"resolution":"1080x1920","fps":30},"avatar":{"image_url":"","provider":"wan2.2_s2v","default_position":"bottom_right"},"material":{"fallback":True}},"segments":segs}
    yp = OUTPUT_DIR/f"{pid}.yaml"; mp = OUTPUT_DIR/f"{pid}.md"
    with open(yp,"w",encoding="utf-8") as f: yaml.dump(y,f,allow_unicode=True,default_flow_style=False,sort_keys=False)
    md = f"""# {pid} — {a.get('core_topic','')}

> 由 AVE 脚本工厂自动生成 | {datetime.date.today().isoformat()}

## 来源信息
| 项目 | 内容 |
|------|------|
| 核心主题 | {a.get('core_topic','-')} |
| 目标人群 | {a.get('target_audience','-')} |
| 风格 | {s} | 钩子 | {a.get('hook_type','-')} | 情绪 | {a.get('emotional_tone','-')} |

## 关键要点
{chr(10).join([f'- {p}' for p in a.get('key_points',[])]) if a.get('key_points') else '- （AI分析中）'}

## 生产备注
- **语音**: 火山引擎 **BGM**: Ace Studio **素材**: Pexels搜索+本地兜底 **分辨率**: 1080×1920竖屏
- **注意**: 脚本为AI生成，建议人工审核。配画关键词可能需要手动调整。
"""
    with open(mp,"w",encoding="utf-8") as f: f.write(md)
    print(f"✅ {pid}: {len(segs)}段 | {yp} | {mp}")
    return yp, mp

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--topic", required=True); p.add_argument("--style")
    args=p.parse_args()
    run(args.topic, args.style)

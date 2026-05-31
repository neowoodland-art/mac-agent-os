"""
工作流引擎 — 可视化 DAG 管线定义与执行

节点类型 (15种):
  story_prototype → 剧本原型 (自然语言故事)
  script          → 脚本输入
  script_adaptor  → 剧本改编
  strategy        → 策略选择
  tts             → TTS 合成
  model           → AI 模型
  material        → 素材源
  style           → 风格预设
  bgm             → BGM 选择
  character       → 角色
  audit_gate      → 审计门
  output          → 输出
  storyboard      → 分镜规划
  prompt_gen      → 分镜提示词生成
  subtitle        → 字幕生成
"""

import os, json, time, uuid, threading, logging
from pathlib import Path

logger = logging.getLogger("workflows")

# ── 字符编排路径 ──
_AVE_DIR = Path(__file__).resolve().parent.parent / "09_ave" / "scripts"
_REGISTRY_PATH = _AVE_DIR / "character_registry" / "registry.yaml"

# ═══════════════════════════════════════════
# 15 种节点类型定义
# ═══════════════════════════════════════════

NODE_DEFINITIONS = {
    "story_prototype": {
        "label": "剧本原型",
        "icon": "📝",
        "description": "用自然语言描述故事梗概，作为剧本创作起点",
        "category": "flow",
        "color": "#a855f7",
        "default_config": {"genre": "mystery", "story_text": ""},
        "options_map": {
            "genre": ["mystery", "comedy", "sci_fi", "modern", "ancient", "fantasy"],
        },
    },
    "script": {
        "label": "脚本输入",
        "icon": "📜",
        "description": "编写或选择脚本（支持在线编辑）",
        "category": "input",
        "color": "#6366f1",
        "default_config": {
            "editor_mode": "inline", "content": "", "type": "yaml",
            "parser": "auto", "path": "",
        },
        "options_map": {
            "editor_mode": ["inline", "manual", "upload"],
            "type": ["yaml", "json", "md"],
            "parser": ["auto", "detailed", "simple"],
        },
    },
    "script_adaptor": {
        "label": "剧本改编",
        "icon": "🔄",
        "description": "将自然语言故事自动转换为结构化脚本",
        "category": "core",
        "color": "#22c55e",
        "default_config": {"adapt_style": "detailed_adapt"},
        "options_map": {
            "adapt_style": ["detailed_adapt", "fast_extract", "dialogue_first"],
        },
    },
    "strategy": {
        "label": "策略选择",
        "icon": "🎯",
        "description": "选择生产策略",
        "category": "core",
        "color": "#22c55e",
        "default_config": {"strategy": "auto"},
        "options_map": {
            "strategy": ["auto", "manual", "ai_generated"],
        },
    },
    "tts": {
        "label": "TTS 合成",
        "icon": "🔊",
        "description": "文本转语音（CosyVoice）",
        "category": "audio",
        "color": "#f59e0b",
        "default_config": {
            "voice_id": "cosyvoice-v3.5-plus",
            "speed": 1.0,
            "pitch": 0.0,
        },
        "options_map": {
            "voice_id": ["cosyvoice-v3.5-plus", "cosyvoice-v3.0-plus"],
            "speed": "::number:0.5:2.0:0.1",
            "pitch": "::number:-3.0:3.0:0.5",
        },
    },
    "model": {
        "label": "AI 模型",
        "icon": "🤖",
        "description": "选择 AI 生成模型",
        "category": "generate",
        "color": "#3b82f6",
        "default_config": {
            "provider": "kling", "model": "kling-v3",
            "duration": 5, "seed": 42,
        },
        "options_map": {
            "provider": ["kling", "jimeng", "wan"],
            "model": ["kling-v3", "kling-v1", "wan2.1"],
            "duration": "::number:2:30:1",
            "seed": "::number:0:999999:1",
        },
    },
    "material": {
        "label": "素材源",
        "icon": "🖼️",
        "description": "选择素材来源",
        "category": "material",
        "color": "#ec4899",
        "default_config": {
            "source": "pexels", "search_keyword": "",
            "count": 5, "orientation": "portrait",
        },
        "options_map": {
            "source": ["pexels", "local", "upload"],
            "orientation": ["portrait", "landscape", "square"],
            "count": "::number:1:20:1",
        },
    },
    "style": {
        "label": "风格预设",
        "icon": "🎨",
        "description": "视觉风格预设",
        "category": "visual",
        "color": "#8b5cf6",
        "default_config": {"style": "cinematic", "color_grade": "warm"},
        "options_map": {
            "style": ["cinematic", "hyper_realistic", "artistic", "anime", "vintage"],
            "color_grade": ["warm", "cool", "neutral", "dramatic", "monochrome"],
        },
    },
    "bgm": {
        "label": "BGM 选择",
        "icon": "🎵",
        "description": "背景音乐选择（支持节拍检测与节奏匹配）",
        "category": "audio",
        "color": "#14b8a6",
        "default_config": {
            "mode": "manual", "mood": "upbeat",
            "rhythm": "medium", "bpm": 120,
            "volume": 0.7, "duck_enabled": True,
        },
        "options_map": {
            "mode": ["manual", "auto", "ai_generated"],
            "mood": ["happy", "sad", "epic", "calm", "tense", "upbeat",
                     "romantic", "inspiring", "healing"],
            "rhythm": ["low", "medium", "high"],
            "bpm": "::number:60:180:5",
            "volume": "::number:0.0:1.0:0.05",
        },
    },
    "character": {
        "label": "角色",
        "icon": "👤",
        "description": "角色引用与定妆照（从注册表加载真实数据）",
        "category": "core",
        "color": "#f97316",
        "default_config": {
            "registry_name": "", "outfit_preset": "default",
            "use_reference_images": True, "lip_sync": False,
        },
        "options_map": {
            "outfit_preset": ["default", "running", "gym", "basketball"],
        },
    },
    "audit_gate": {
        "label": "审计门",
        "icon": "🛡️",
        "description": "人工审核确认后继续",
        "category": "flow",
        "color": "#ef4444",
        "default_config": {
            "message": "请确认此步骤结果",
            "auto_approve": False, "timeout_minutes": 60,
        },
        "options_map": {
            "timeout_minutes": "::number:1:480:5",
        },
    },
    "output": {
        "label": "输出",
        "icon": "📦",
        "description": "输出视频配置",
        "category": "output",
        "color": "#64748b",
        "default_config": {
            "format": "mp4", "resolution": "1080x1920",
            "output_path": "", "auto_open": True,
        },
        "options_map": {
            "format": ["mp4", "mov", "gif"],
            "resolution": ["1080x1920", "1920x1080", "720x1280"],
        },
    },
    "storyboard": {
        "label": "分镜规划",
        "icon": "🎬",
        "description": "将脚本分解为场景级分镜（景别/运镜/转场/对白/动作）",
        "category": "process",
        "color": "#a855f7",
        "default_config": {
            "camera_style": "cinematic", "transition": "hard",
            "scene_count": 6, "output_format": "json",
        },
        "options_map": {
            "camera_style": ["cinematic", "dynamic", "static"],
            "transition": ["hard", "fade_in", "fade_out", "dissolve", "slide", "cut"],
            "scene_count": "::number:2:20:1",
            "output_format": ["json", "yaml", "md"],
        },
    },
    "prompt_gen": {
        "label": "分镜提示词",
        "icon": "✨",
        "description": "将分镜+角色转换为每场景的视频生成提示词",
        "category": "core",
        "color": "#8b5cf6",
        "default_config": {
            "prompt_style": "detailed",
            "quality": "standard",
            "add_negative": True,
        },
        "options_map": {
            "prompt_style": ["detailed", "simple", "stepwise"],
            "quality": ["standard", "turbo", "quality"],
        },
    },
    "subtitle": {
        "label": "字幕生成",
        "icon": "💬",
        "description": "从对白文本生成时间轴字幕（SRT/ASS）",
        "category": "output",
        "color": "#06b6d4",
        "default_config": {
            "format": "srt", "position": "bottom",
            "style": "white", "max_length": 18,
        },
        "options_map": {
            "format": ["srt", "ass", "vtt"],
            "position": ["bottom", "top"],
            "style": ["white", "yellow", "cyan"],
            "max_length": "::number:10:40:2",
        },
    },
}


# ═══════════════════════════════════════════
# 6 个工作流模板
# ═══════════════════════════════════════════

WORKFLOW_TEMPLATES = {
    "basic_dub": {
        "name": "基础口播",
        "cost": "¥2-5",
        "description": "标准口播视频：脚本→TTS→素材→BGM→字幕→合成",
        "nodes": [
            {"id": "n1", "type": "script", "label": "脚本", "x": 40, "y": 160,
             "config": {"editor_mode": "inline", "type": "yaml"}},
            {"id": "n2", "type": "tts", "label": "TTS", "x": 300, "y": 160,
             "config": {"voice_id": "cosyvoice-v3.5-plus", "speed": 1.0}},
            {"id": "n3", "type": "material", "label": "素材搜索", "x": 300, "y": 40,
             "config": {"source": "pexels", "count": 5, "orientation": "portrait"}},
            {"id": "n4", "type": "bgm", "label": "BGM", "x": 300, "y": 280,
             "config": {"mode": "manual", "mood": "upbeat", "volume": 0.7, "duck_enabled": True}},
            {"id": "n5", "type": "output", "label": "视频输出", "x": 560, "y": 160,
             "config": {"format": "mp4", "resolution": "1080x1920"}},
        ],
        "edges": [
            {"from": "n1", "to": "n2"},
            {"from": "n1", "to": "n3"},
            {"from": "n1", "to": "n4"},
            {"from": "n2", "to": "n5"},
            {"from": "n3", "to": "n5"},
            {"from": "n4", "to": "n5"},
        ],
    },
    "beat_sync": {
        "name": "卡点视频",
        "cost": "¥1-3",
        "description": "BGM→节拍检测→素材匹配→变速卡点合成",
        "nodes": [
            {"id": "n1", "type": "bgm", "label": "BGM 导入", "x": 40, "y": 160,
             "config": {"mode": "auto", "mood": "upbeat", "volume": 0.8}},
            {"id": "n2", "type": "style", "label": "卡点风格", "x": 300, "y": 160,
             "config": {"style": "cinematic", "color_grade": "dramatic"}},
            {"id": "n3", "type": "audit_gate", "label": "质量审核", "x": 560, "y": 160,
             "config": {"message": "卡点效果是否符合预期？"}},
            {"id": "n4", "type": "output", "label": "视频输出", "x": 800, "y": 160,
             "config": {"format": "mp4", "resolution": "1080x1920"}},
        ],
        "edges": [
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n3"},
            {"from": "n3", "to": "n4"},
        ],
    },
    "character_narrative": {
        "name": "角色叙事",
        "cost": "¥10-25",
        "description": "定妆照→剧本→多场景→Kling批量→角色一致性拼接",
        "nodes": [
            {"id": "n1", "type": "story_prototype", "label": "剧本输入", "x": 40, "y": 260,
             "config": {"genre": "mystery"}},
            {"id": "n2", "type": "script_adaptor", "label": "脚本改编", "x": 260, "y": 260,
             "config": {"adapt_style": "detailed_adapt"}},
            {"id": "n3", "type": "character", "label": "角色引用", "x": 260, "y": 400,
             "config": {"outfit_preset": "default", "use_reference_images": True}},
            {"id": "n4", "type": "strategy", "label": "故事策略", "x": 260, "y": 120,
             "config": {"strategy": "auto"}},
            {"id": "n5", "type": "model", "label": "Kling 生成", "x": 500, "y": 260,
             "config": {"provider": "kling", "model": "kling-v3", "duration": 5, "seed": 42}},
            {"id": "n6", "type": "tts", "label": "旁白 TTS", "x": 500, "y": 100,
             "config": {"voice_id": "cosyvoice-v3.5-plus", "speed": 1.0}},
            {"id": "n7", "type": "audit_gate", "label": "生成审核", "x": 740, "y": 260,
             "config": {"message": "所有场景已生成，确认拼接？"}},
            {"id": "n8", "type": "output", "label": "最终输出", "x": 980, "y": 260,
             "config": {"format": "mp4", "resolution": "1080x1920"}},
        ],
        "edges": [
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n5"},
            {"from": "n3", "to": "n5"},
            {"from": "n4", "to": "n5"},
            {"from": "n5", "to": "n7"},
            {"from": "n2", "to": "n6"},
            {"from": "n6", "to": "n7"},
            {"from": "n7", "to": "n8"},
        ],
    },
    "digital_human": {
        "name": "数字人口播",
        "cost": "¥3-8",
        "description": "角色照片+文案→TTS→数字人→口型同步→输出",
        "nodes": [
            {"id": "n1", "type": "script", "label": "文案输入", "x": 40, "y": 160,
             "config": {"editor_mode": "inline"}},
            {"id": "n2", "type": "tts", "label": "人声合成", "x": 260, "y": 160,
             "config": {"voice_id": "cosyvoice-v3.5-plus"}},
            {"id": "n3", "type": "character", "label": "数字人角色", "x": 260, "y": 40,
             "config": {"lip_sync": True}},
            {"id": "n4", "type": "output", "label": "数字人视频", "x": 520, "y": 160,
             "config": {"format": "mp4", "resolution": "1080x1920"}},
        ],
        "edges": [
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n4"},
            {"from": "n3", "to": "n4"},
        ],
    },
    "hybrid_dub": {
        "name": "口播+卡点混合",
        "cost": "¥4-10",
        "description": "人声锚点+BGM能量变速→帧锁定拼接",
        "nodes": [
            {"id": "n1", "type": "script", "label": "口播脚本", "x": 40, "y": 160,
             "config": {"editor_mode": "inline"}},
            {"id": "n2", "type": "tts", "label": "人声合成", "x": 260, "y": 160,
             "config": {"voice_id": "cosyvoice-v3.5-plus"}},
            {"id": "n3", "type": "style", "label": "混合风格", "x": 260, "y": 40,
             "config": {"style": "cinematic", "color_grade": "dramatic"}},
            {"id": "n4", "type": "output", "label": "混合视频", "x": 520, "y": 160,
             "config": {"format": "mp4", "resolution": "1080x1920"}},
        ],
        "edges": [
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n4"},
            {"from": "n3", "to": "n4"},
        ],
    },
    "short_drama": {
        "name": "短剧创作",
        "cost": "¥15-50",
        "description": "故事原型→改编→脚本→角色→策略→分镜→提示词→视频+配音+配乐+字幕→审核→输出",
        "nodes": [
            {"id": "n1", "type": "story_prototype", "label": "故事输入", "x": 40, "y": 260,
             "config": {"genre": "mystery"}},
            {"id": "n2", "type": "script", "label": "脚本编辑", "x": 220, "y": 260,
             "config": {"editor_mode": "manual", "type": "yaml"}},
            {"id": "n3", "type": "character", "label": "角色设定", "x": 420, "y": 400,
             "config": {"outfit_preset": "default"}},
            {"id": "n4", "type": "strategy", "label": "短剧策略", "x": 420, "y": 260,
             "config": {"strategy": "auto"}},
            {"id": "n5", "type": "storyboard", "label": "分镜规划", "x": 600, "y": 160,
             "config": {"camera_style": "cinematic", "scene_count": 6}},
            {"id": "n6", "type": "prompt_gen", "label": "提示词生成", "x": 780, "y": 60,
             "config": {"prompt_style": "detailed", "quality": "standard", "add_negative": True}},
            {"id": "n7", "type": "model", "label": "场景视频", "x": 960, "y": 60,
             "config": {"provider": "kling", "model": "kling-v3", "duration": 5}},
            {"id": "n8", "type": "tts", "label": "角色配音", "x": 780, "y": 200,
             "config": {"voice_id": "cosyvoice-v3.5-plus"}},
            {"id": "n9", "type": "bgm", "label": "配乐", "x": 780, "y": 340,
             "config": {"mode": "auto", "mood": "upbeat", "duck_enabled": True}},
            {"id": "n10", "type": "subtitle", "label": "字幕", "x": 960, "y": 200,
             "config": {"format": "srt", "position": "bottom", "style": "white"}},
            {"id": "n11", "type": "audit_gate", "label": "成片审核", "x": 1140, "y": 200,
             "config": {"message": "所有短剧场景已完成，确认合成？"}},
            {"id": "n12", "type": "output", "label": "短剧成片", "x": 1320, "y": 200,
             "config": {"format": "mp4", "resolution": "1080x1920"}},
        ],
        "edges": [
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n4"},
            {"from": "n3", "to": "n6"},
            {"from": "n4", "to": "n5"},
            {"from": "n5", "to": "n6"},
            {"from": "n6", "to": "n7"},
            {"from": "n4", "to": "n8"},
            {"from": "n4", "to": "n9"},
            {"from": "n2", "to": "n10"},
            {"from": "n7", "to": "n11"},
            {"from": "n8", "to": "n11"},
            {"from": "n9", "to": "n11"},
            {"from": "n10", "to": "n11"},
            {"from": "n11", "to": "n12"},
        ],
    },
}


# ═══════════════════════════════════════════
# 角色注册表加载
# ═══════════════════════════════════════════

_registry_cache = {"data": None, "mtime": 0}


def load_character_registry():
    """加载角色注册表"""
    if not _REGISTRY_PATH.exists():
        return {"characters": {}, "active_character": ""}
    try:
        import yaml
        mtime = _REGISTRY_PATH.stat().st_mtime
        if _registry_cache["mtime"] >= mtime and _registry_cache["data"] is not None:
            return _registry_cache["data"]
        with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        _registry_cache["data"] = data
        _registry_cache["mtime"] = mtime
        return data
    except Exception as e:
        logger.warning(f"加载角色注册表失败: {e}")
        return {"characters": {}, "active_character": ""}


def get_character_list():
    """获取角色名称列表"""
    data = load_character_registry()
    chars = data.get("characters", {})
    active = data.get("active_character", "")
    return [{"name": name, "active": name == active} for name in chars]


def get_character_data(name: str) -> dict | None:
    """获取单个角色详情"""
    data = load_character_registry()
    return data.get("characters", {}).get(name)


def reload_character_registry():
    """强制重新加载注册表"""
    _registry_cache["mtime"] = 0
    return load_character_registry()


# ═══════════════════════════════════════════
# WorkflowRunner — DAG 执行引擎
# ═══════════════════════════════════════════

class WorkflowRunner:
    """工作流运行器（Kahn 拓扑排序 + 线程执行）"""

    def __init__(self):
        self._runs: dict[str, dict] = {}

    def create_run(self, template_id: str, nodes: list, edges: list) -> str:
        """创建工作流运行"""
        run_id = f"wf_{uuid.uuid4().hex[:12]}"
        self._runs[run_id] = {
            "run_id": run_id,
            "template_id": template_id,
            "nodes": nodes,
            "edges": edges,
            "status": "pending",
            "created": time.time(),
            "node_states": {n["id"]: "pending" for n in nodes},
        }
        return run_id

    def get_run(self, run_id: str) -> dict | None:
        """获取运行状态"""
        return self._runs.get(run_id)

    def start_run(self, run_id: str):
        """异步启动工作流"""
        run = self._runs.get(run_id)
        if not run:
            return
        run["status"] = "running"
        for n in run["nodes"]:
            run["node_states"][n["id"]] = "running"

        def _execute():
            try:
                ordered = self._kahn_sort(run["nodes"], run["edges"])
                for n in ordered:
                    run["node_states"][n["id"]] = "completed"
                run["status"] = "completed"
            except Exception as e:
                run["status"] = "failed"
                logger.error(f"工作流 {run_id} 执行失败: {e}")

        t = threading.Thread(target=_execute, daemon=True)
        t.start()

    @staticmethod
    def _kahn_sort(nodes: list, edges: list) -> list:
        """Kahn 拓扑排序"""
        node_map = {n["id"]: n for n in nodes}
        in_deg = {n["id"]: 0 for n in nodes}
        adj = {n["id"]: [] for n in nodes}
        for e in edges:
            f, t = e["from"], e["to"]
            if f in node_map and t in node_map:
                adj[f].append(t)
                in_deg[t] = in_deg.get(t, 0) + 1
        queue = [nid for nid, d in in_deg.items() if d == 0]
        result = []
        while queue:
            nid = queue.pop(0)
            if nid in node_map:
                result.append(node_map[nid])
            for neigh in adj.get(nid, []):
                in_deg[neigh] -= 1
                if in_deg[neigh] == 0:
                    queue.append(neigh)
        return result


_singleton = None


def get_runner() -> WorkflowRunner:
    """获取 WorkflowRunner 单例"""
    global _singleton
    if _singleton is None:
        _singleton = WorkflowRunner()
    return _singleton


def get_node_categories() -> dict:
    """获取按分类组织的节点列表（前端 SPA 所需格式）"""
    cat_map = [
        ("input", "输入"),
        ("core", "核心处理"),
        ("audio", "音频"),
        ("generate", "生成"),
        ("material", "素材"),
        ("visual", "视觉"),
        ("process", "流程处理"),
        ("flow", "流程控制"),
        ("output", "输出"),
    ]
    _defs = {}
    categories = []
    for cat_key, cat_label in cat_map:
        nodes_in_cat = [
            nid for nid, ndef in NODE_DEFINITIONS.items()
            if ndef.get("category") == cat_key
        ]
        if nodes_in_cat:
            for nid in nodes_in_cat:
                _defs[nid] = NODE_DEFINITIONS[nid]
            categories.append({
                "key": cat_key,
                "label": cat_label,
                "nodes": nodes_in_cat,
            })
    return {
        "categories": categories,
        "_defs": _defs,
        "total": len(NODE_DEFINITIONS),
    }

"""
提示词组装器 V3 (PromptAssembler) — 模块化10层角色描述系统

架构: 10层模块，从粗到细逐层构建角色
  L0 身份层   — 姓名/性别/年龄/种族/世界观
  L1 面部轮廓  — 脸型/头型/下颌线/颧骨
  L2 五官细节  — 眼(形/色/神)/眉/鼻/嘴/耳
  L3 头发层    — 发型/长度/颜色/质地/发际线
  L4 皮肤妆容  — 肤色/肤质/底妆/特殊标记/质感
  L5 体型姿态  — 身高/体型/肩宽/站姿/手部
  L6 服装配饰  — 上装/下装/外套/鞋/配饰
  L7 神态表情  — 微表情/眼神/情绪基调/气质
  L8 光线镜头  — 光型/色温/镜头/景深/氛围
  L9 背景场景  — 环境/背景色/季节/天气

每个层级包含:
  - build_{layer}(data) → 自然语言描述片段
  - vocab_{layer}  → 该层级的完整词汇/选项
  - default_{layer} → 默认值

用法:
  from prompt_assembler_v3 import CharacterPromptSystem, CHAR_LAYERS
  system = CharacterPromptSystem()
  
  # 逐层构建
  system.set_layer("L2_face_eyes", {"shape": "丹凤眼", "color": "深褐", "spirit": "锐利"})
  
  # 生成最终提示词
  prompt = system.build_prompt(variant="front_face")
  
  # 获取当前完整描述
  desc = system.get_layers_descriptions()
  
  # 获取某层的可用选项
  options = system.get_layer_options("L2_face_eyes")
"""

from typing import Optional, Any
import json


# ═══════════════════════════════════════════════════════════
# 第零层: L0 — 核心身份
# ═══════════════════════════════════════════════════════════

L0_IDENTITY = {
    "label": "核心身份",
    "icon": "🆔",
    "order": 0,
    "fields": [
        {"key": "name", "label": "角色名", "type": "text", "placeholder": "如: 阿远"},
        {"key": "gender", "label": "性别", "type": "select", "options": ["男性", "女性"]},
        {"key": "age", "label": "年龄", "type": "select", "options": ["少年(12-18)", "青年(18-30)", "壮年(30-45)", "中年(45-60)", "老年(60+)"]},
        {"key": "ethnicity", "label": "种族/地域", "type": "select", "options": ["中国", "东亚", "东南亚", "南亚", "中东", "欧美", "非洲", "拉美"]},
        {"key": "worldview", "label": "世界观/时代", "type": "select", "options": ["现代", "古风", "科幻", "奇幻", "民国", "未来", "赛博朋克"]},
    ],
    "build": lambda d: f"{d.get('name','')}，一位{d.get('age','青年').split('(')[0]}{d.get('gender','')}，{d.get('ethnicity','')}人，{d.get('worldview','现代')}背景",
}

# ═══════════════════════════════════════════════════════════
# 第一层: L1 — 面部轮廓
# ═══════════════════════════════════════════════════════════

L1_FACE_SHAPE = {
    "label": "面部轮廓",
    "icon": "🗿",
    "order": 1,
    "fields": [
        {"key": "shape", "label": "脸型", "type": "select",
         "options": ["鹅蛋脸", "瓜子脸", "圆脸", "方脸", "国字脸", "长脸", "菱形脸", "心形脸"],
         "description": "国字脸/方脸 → 稳重正气；鹅蛋脸 → 温婉；瓜子脸 → 精致秀气"},
        {"key": "jaw", "label": "下颌线", "type": "select",
         "options": ["柔和模糊", "清晰分明", "棱角突出", "圆润温和"]},
        {"key": "cheekbone", "label": "颧骨", "type": "select",
         "options": ["适中自然", "高突出", "饱满圆润", "低平"]},
        {"key": "forehead", "label": "额头", "type": "select",
         "options": ["饱满宽阔", "适中", "窄小", "高额头"]},
    ],
    "build": lambda d: (
        f"{d.get('shape','')}"
        f"{'，' + d.get('jaw','') if d.get('jaw') else ''}"
        f"{'，' + d.get('cheekbone','') + '颧骨' if d.get('cheekbone') else ''}"
        f"{'，' + d.get('forehead','') + '额头' if d.get('forehead') else ''}"
    ),
}

# ═══════════════════════════════════════════════════════════
# 第二层: L2 — 五官细节
# ═══════════════════════════════════════════════════════════

L2_FACIAL_FEATURES = {
    "label": "五官细节",
    "icon": "👁️",
    "order": 2,
    "sub_layers": {
        "eyes": {
            "label": "眼睛",
            "icon": "👁️",
            "fields": [
                {"key": "shape", "label": "眼型", "type": "select",
                 "options": ["丹凤眼", "杏眼", "桃花眼", "圆眼", "细长眼", "下垂眼", "上挑眼", "单眼皮", "双眼皮", "内双"],
                 "description": "丹凤眼 → 古典东方美；杏眼 → 圆润可爱；桃花眼 → 含情脉脉"},
                {"key": "color", "label": "瞳孔颜色", "type": "select",
                 "options": ["深褐", "浅褐", "黑色", "琥珀色", "灰色", "蓝色", "绿色"]},
                {"key": "size", "label": "大小", "type": "select",
                 "options": ["大而有神", "适中", "细长", "小而有神"]},
                {"key": "spirit", "label": "眼神", "type": "text",
                 "placeholder": "如: 深邃锐利、清澈温柔、沉稳内敛", "multi": True},
                {"key": "detail", "label": "细节补充", "type": "text",
                 "placeholder": "如: 眼尾微垂、卧蚕明显、睫毛浓密"},
            ],
            "build": lambda d: (
                f"{d.get('size','')}{d.get('shape','')}"
                f"{'（' + d.get('color','') + '色瞳孔' + '）' if d.get('color') else ''}"
                f"{'，' + d.get('spirit','') if d.get('spirit') else ''}"
                f"{'，' + d.get('detail','') if d.get('detail') else ''}"
            ),
        },
        "eyebrows": {
            "label": "眉毛",
            "icon": "🧐",
            "fields": [
                {"key": "shape", "label": "眉型", "type": "select",
                 "options": ["剑眉", "柳叶眉", "一字眉", "上挑眉", "弯眉", "粗眉", "细长眉"]},
                {"key": "state", "label": "状态", "type": "select",
                 "options": ["舒展自然", "微微蹙起", "高挑", "平缓"]},
                {"key": "color", "label": "眉色", "type": "select",
                 "options": ["浓黑", "深棕", "浅棕", "自然黑"]},
            ],
            "build": lambda d: (
                f"{d.get('shape','')}"
                f"{'，' + d.get('color','') if d.get('color') else ''}"
                f"{'，' + d.get('state','') if d.get('state') else ''}"
            ),
        },
        "nose": {
            "label": "鼻子",
            "icon": "👃",
            "fields": [
                {"key": "bridge", "label": "鼻梁", "type": "select",
                 "options": ["高挺", "挺直窄小", "中等挺拔", "低平柔和"]},
                {"key": "tip", "label": "鼻头", "type": "select",
                 "options": ["小巧圆润", "圆润饱满", "尖翘", "略宽"]},
                {"key": "wing", "label": "鼻翼", "type": "select",
                 "options": ["适中", "略宽", "窄小"]},
            ],
            "build": lambda d: (
                f"鼻梁{d.get('bridge','')}"
                f"{'，鼻头' + d.get('tip','') if d.get('tip') else ''}"
                f"{'，鼻翼' + d.get('wing','') if d.get('wing') else ''}"
            ),
        },
        "lips": {
            "label": "嘴唇",
            "icon": "👄",
            "fields": [
                {"key": "shape", "label": "唇型", "type": "select",
                 "options": ["薄唇", "厚唇", "M形唇", "饱满", "樱桃小嘴", "微笑唇"]},
                {"key": "color", "label": "唇色", "type": "select",
                 "options": ["自然淡粉", "健康红润", "偏苍白", "暗紫红", "裸色"]},
                {"key": "state", "label": "状态", "type": "select",
                 "options": ["自然闭合", "微张", "紧抿", "嘴角微扬", "含笑意"]},
            ],
            "build": lambda d: (
                f"{d.get('shape','')}"
                f"{'（' + d.get('color','') + '）' if d.get('color') else ''}"
                f"{'，' + d.get('state','') if d.get('state') else ''}"
            ),
        },
    },
    "build": lambda d: "",  # 由子层分别构建
}

# ═══════════════════════════════════════════════════════════
# 第三层: L3 — 头发
# ═══════════════════════════════════════════════════════════

L3_HAIR = {
    "label": "头发",
    "icon": "💇",
    "order": 3,
    "fields": [
        {"key": "style", "label": "发型", "type": "select",
         "options": ["短发", "寸头", "中长发", "长发", "背头", "三七分", "齐刘海", "斜刘海",
                     "大背头", "碎发", "丸子头", "高马尾", "低马尾", "披肩发", "盘发"]},
        {"key": "color", "label": "发色", "type": "select",
         "options": ["黑色", "深棕", "浅棕", "亚麻色", "灰色", "银白", "渐变挑染"]},
        {"key": "texture", "label": "发质", "type": "select",
         "options": ["柔顺直发", "自然微卷", "波浪卷", "小卷", "粗硬", "细软", "蓬松"]},
        {"key": "length", "label": "长度", "type": "select",
         "options": ["板寸(3mm)", "短(3-6cm)", "及耳", "及肩", "及胸", "及腰", "过腰"]},
        {"key": "detail", "label": "细节补充", "type": "text",
         "placeholder": "如: 两侧收短顶部略长、发际线略高"},
    ],
    "build": lambda d: (
        f"{d.get('texture','')}{d.get('style','')}"
        f"{'（' + d.get('color','') + '）' if d.get('color') else ''}"
        f"{'，' + d.get('length','') if d.get('length') else ''}"
        f"{'，' + d.get('detail','') if d.get('detail') else ''}"
    ),
}

# ═══════════════════════════════════════════════════════════
# 第四层: L4 — 皮肤与妆容
# ═══════════════════════════════════════════════════════════

L4_SKIN_MAKEUP = {
    "label": "皮肤与妆容",
    "icon": "✨",
    "order": 4,
    "fields": [
        {"key": "skin_tone", "label": "肤色", "type": "select",
         "options": ["冷白皮", "暖白皮", "自然偏白", "健康小麦", "蜜色", "古铜色", "深色"],
         "description": "冷白→清冷；暖白→温润；小麦→阳光健康"},
        {"key": "skin_texture", "label": "肤质", "type": "select",
         "options": ["细腻光滑", "自然肌理", "毛孔可见", "粗糙", "哑光", "水润光泽"],
         "description": "人像特写建议 '细腻光滑'+'自然肌理' 组合使用"},
        {"key": "complexion", "label": "气色", "type": "select",
         "options": ["红润健康", "略显苍白", "疲惫暗沉", "容光焕发", "自然均匀"]},
        {"key": "makeup_base", "label": "底妆", "type": "select",
         "options": ["素颜", "淡妆", "精致妆容", "烟熏妆", "裸妆", "浓妆"]},
        {"key": "makeup_lip", "label": "唇妆", "type": "select",
         "options": ["自然唇色", "淡裸色", "豆沙色", "正红色", "暗紫色", "水光唇"]},
        {"key": "makeup_eye", "label": "眼妆", "type": "select",
         "options": ["无眼妆", "自然眼线", "淡眼影", "烟熏", "猫眼眼线"]},
        {"key": "blemish", "label": "特殊标记", "type": "text",
         "placeholder": "如: 右眉上细疤、左颊美人痣、法令纹明显、笑纹"},
    ],
    "build": lambda d: (
        f"{d.get('skin_tone','')}"
        f"{'，' + d.get('skin_texture','') if d.get('skin_texture') else ''}"
        f"{'，' + d.get('complexion','') if d.get('complexion') else ''}"
        f"{'，' + d.get('makeup_base','') if d.get('makeup_base') else ''}"
        f"{'（' + d.get('makeup_eye','') + '，' + d.get('makeup_lip','') + '）' if d.get('makeup_eye') or d.get('makeup_lip') else ''}"
        f"{'，' + d.get('blemish','') if d.get('blemish') else ''}"
    ),
}

# ═══════════════════════════════════════════════════════════
# 第五层: L5 — 体型与姿态
# ═══════════════════════════════════════════════════════════

L5_BODY = {
    "label": "体型与姿态",
    "icon": "🏋️",
    "order": 5,
    "fields": [
        {"key": "height", "label": "身高", "type": "select",
         "options": ["矮小(155-165cm)", "中等(165-175cm)", "中高(175-185cm)", "高大(185cm+)"]},
        {"key": "build", "label": "体型", "type": "select",
         "options": ["纤细瘦弱", "偏瘦", "标准匀称", "健壮", "壮硕", "丰满", "魁梧"]},
        {"key": "shoulder", "label": "肩宽", "type": "select",
         "options": ["窄肩", "标准", "宽肩", "厚肩"]},
        {"key": "posture", "label": "气质姿态", "type": "select",
         "options": ["挺拔", "微驼", "自然放松", "端庄", "慵懒", "紧绷"]},
        {"key": "hands", "label": "手部", "type": "text",
         "placeholder": "如: 手指修长、关节分明、指甲修剪整齐"},
    ],
    "build": lambda d: (
        f"身高{d.get('height','中等').split('(')[0]}"
        f"体型{d.get('build','')}"
        f"{'，' + d.get('shoulder','') if d.get('shoulder') else ''}"
        f"{'，姿态' + d.get('posture','') if d.get('posture') else ''}"
        f"{'，' + d.get('hands','') if d.get('hands') else ''}"
    ),
}

# ═══════════════════════════════════════════════════════════
# 第六层: L6 — 服装与配饰
# ═══════════════════════════════════════════════════════════

L6_CLOTHING = {
    "label": "服装与配饰",
    "icon": "👔",
    "order": 6,
    "fields": [
        {"key": "top", "label": "上装", "type": "text",
         "placeholder": "如: 深灰色拉链运动夹克"},
        {"key": "inner", "label": "内搭", "type": "text",
         "placeholder": "如: 白色圆领速干内衬"},
        {"key": "bottom", "label": "下装", "type": "text",
         "placeholder": "如: 深蓝色牛仔裤、黑色运动短裤"},
        {"key": "outerwear", "label": "外套", "type": "text",
         "placeholder": "如: 深藏蓝亚麻外套"},
        {"key": "shoes", "label": "鞋子", "type": "text",
         "placeholder": "如: 白色跑步鞋"},
        {"key": "accessories", "label": "配饰", "type": "text", "multi": True,
         "placeholder": "如: 蓝色无线运动耳机(右耳)、细框金属眼镜、简约电子手表、运动护腕"},
        {"key": "style_tag", "label": "穿搭风格", "type": "select",
         "options": ["运动休闲", "商务正装", "商务休闲", "街头潮流", "日系清新", "简约素雅", "军事工装", "复古"]},
    ],
    "build": lambda d: (
        f"身穿{d.get('top','')}"
        f"{'，内搭' + d.get('inner','') if d.get('inner') else ''}"
        f"{'，下穿' + d.get('bottom','') if d.get('bottom') else ''}"
        f"{'，外披' + d.get('outerwear','') if d.get('outerwear') else ''}"
        f"{'，脚蹬' + d.get('shoes','') if d.get('shoes') else ''}"
        f"{'，佩戴' + d.get('accessories','') if d.get('accessories') else ''}"
        f"{'，' + d.get('style_tag','') + '风格' if d.get('style_tag') else ''}"
    ),
}

# ═══════════════════════════════════════════════════════════
# 第七层: L7 — 神态与表情
# ═══════════════════════════════════════════════════════════

L7_EXPRESSION = {
    "label": "神态与表情",
    "icon": "😊",
    "order": 7,
    "fields": [
        {"key": "base_mood", "label": "情绪基调", "type": "select",
         "options": ["平静从容", "温和友善", "冷峻严肃", "开朗活泼", "忧郁内敛", "自信昂扬", "恬静淡然"]},
        {"key": "expression", "label": "表面表情", "type": "select",
         "options": ["中性无表情", "淡淡微笑", "开怀大笑", "微笑", "皱眉沉思", "瞪大眼惊讶", "绷着脸"]},
        {"key": "eye_spirit", "label": "眼神细节", "type": "text",
         "placeholder": "如: 目光坚定直视前方、眼神游离若有所思、眼中带笑意、目光如炬"},
        {"key": "micro_expr", "label": "微表情", "type": "text", "multi": True,
         "placeholder": "如: 嘴角微微上翘、眉头轻蹙、眼角细纹、鼻翼轻动"},
        {"key": "aura", "label": "气质气场", "type": "text",
         "placeholder": "如: 沉稳内敛不怒自威、亲和温暖如沐春风、疏离清冷生人勿近"},
    ],
    "build": lambda d: (
        f"神色{d.get('base_mood','')}"
        f"{'，表情' + d.get('expression','') if d.get('expression') else ''}"
        f"{'，' + d.get('eye_spirit','') if d.get('eye_spirit') else ''}"
        f"{'，' + d.get('micro_expr','') if d.get('micro_expr') else ''}"
        f"{'，整体气质' + d.get('aura','') if d.get('aura') else ''}"
    ),
}

# ═══════════════════════════════════════════════════════════
# 第八层: L8 — 光线与镜头
# ═══════════════════════════════════════════════════════════

L8_LIGHTING_CAMERA = {
    "label": "光线与镜头",
    "icon": "📸",
    "order": 8,
    "fields": [
        {"key": "light_type", "label": "光型", "type": "select",
         "options": ["柔光箱均匀布光", "美人碟柔光", "伦勃朗光", "分割光", "侧光/塑形光",
                     "逆光/轮廓光", "阴天漫射光", "顶光/戏剧性"],
         "description": "美人碟光 → 人像经典；伦勃朗光 → 立体感；分割光 → 戏剧性"},
        {"key": "color_temp", "label": "色温", "type": "select",
         "options": ["暖色调(金色)", "冷色调(青蓝)", "中性白平衡", "混合色温", "自然日光"]},
        {"key": "lens", "label": "镜头焦距", "type": "select",
         "options": ["广角(24mm)", "标准(50mm)", "中焦(85mm)", "长焦(135mm)", "微距"]},
        {"key": "depth", "label": "景深", "type": "select",
         "options": ["浅景深/背景虚化", "中等景深", "大景深/全清晰"]},
        {"key": "light_detail", "label": "光线细节", "type": "text",
         "placeholder": "如: 光线从右侧45°打来，在左脸形成柔和阴影"},
    ],
    "build": lambda d: (
        f"{d.get('light_type','柔光箱均匀布光')}"
        f"{'，' + d.get('color_temp','') if d.get('color_temp') else ''}"
        f"{'，' + d.get('lens','') + '镜头' if d.get('lens') else ''}"
        f"{'，' + d.get('depth','') if d.get('depth') else ''}"
        f"{'，' + d.get('light_detail','') if d.get('light_detail') else ''}"
    ),
}

# ═══════════════════════════════════════════════════════════
# 第九层: L9 — 背景与场景
# ═══════════════════════════════════════════════════════════

L9_BACKGROUND = {
    "label": "背景与场景",
    "icon": "🌄",
    "order": 9,
    "fields": [
        {"key": "bg_type", "label": "背景类型", "type": "select",
         "options": ["纯色背景", "影棚布景", "自然户外", "城市街景", "室内空间", "特定场景"]},
        {"key": "bg_color", "label": "背景色/氛围", "type": "select",
         "options": ["纯白/干净", "纯灰/专业", "纯黑/神秘", "暖色/温馨", "冷色/冷静", "渐变色"]},
        {"key": "environment", "label": "具体环境", "type": "text",
         "placeholder": "如: 清晨城市街道、江南古巷青砖墙、健身房器械区"},
        {"key": "season", "label": "季节/天气", "type": "select",
         "options": ["晴天", "阴天", "雨后", "雪天", "黄昏", "深夜", "清晨", "午后"]},
    ],
    "build": lambda d: (
        f"{d.get('environment','')}"
        f"{'，' + d.get('bg_color','') if d.get('bg_color') else ''}"
        f"{'，' + d.get('season','') if d.get('season') else ''}"
    ),
}

# ═══════════════════════════════════════════════════════════
# 层级注册表
# ═══════════════════════════════════════════════════════════

CHAR_LAYERS = {
    "L0_identity": L0_IDENTITY,
    "L1_face_shape": L1_FACE_SHAPE,
    "L2_facial_features": L2_FACIAL_FEATURES,
    "L3_hair": L3_HAIR,
    "L4_skin_makeup": L4_SKIN_MAKEUP,
    "L5_body": L5_BODY,
    "L6_clothing": L6_CLOTHING,
    "L7_expression": L7_EXPRESSION,
    "L8_lighting_camera": L8_LIGHTING_CAMERA,
    "L9_background": L9_BACKGROUND,
}

# 各子层（L2的各部位）
SUB_LAYERS = {
    "L2_face_eyes": L2_FACIAL_FEATURES["sub_layers"]["eyes"],
    "L2_face_eyebrows": L2_FACIAL_FEATURES["sub_layers"]["eyebrows"],
    "L2_face_nose": L2_FACIAL_FEATURES["sub_layers"]["nose"],
    "L2_face_lips": L2_FACIAL_FEATURES["sub_layers"]["lips"],
}

# 所有可配置项合并
ALL_LAYERS = {**CHAR_LAYERS, **SUB_LAYERS}


# ═══════════════════════════════════════════════════════════
# 变体提示词模板
# ═══════════════════════════════════════════════════════════

# ── 正面面部特写（定妆照基准） ──
FRONT_FACE_TEMPLATE_ZH = (
    "{L0}。{L1}。{eyes}。{eyebrows}。{nose}。{lips}。{L3}。{L4}。{L5}。{L6}。{L7}。{L8}。{L9}。"
    "专业人像摄影，正面面向相机，中性自然表情。"
    "商业摄影品质，8k分辨率，写实风格，高细节。比例9:16"
)

FRONT_FACE_TEMPLATE_EN = (
    "{L0}. {L1}. {eyes}. {eyebrows}. {nose}. {lips}. {L3}. {L4}. {L5}. {L6}. {L7}. {L8}. {L9}. "
    "Professional portrait photography, front-facing camera, neutral expression. "
    "Commercial photography quality, 8k resolution, photorealistic style, high detail. --ar 9:16"
)

# ── 全身照 ──
FULL_BODY_TEMPLATE_ZH = (
    "{L0}。{L1}。{eyes}。{L3}。{L4}。{L5}。{L6}。{L7}。"
    "全身站立摄影照片，白色背景，影室均匀布光。"
    "商业时尚摄影风格，写实全身入镜。比例9:16"
)

# ── 网格定妆照 ──
GRID_STANDARD_ZH = (
    "一张专业的角色定妆参考表，展示{L0}。{L1}。{eyes}。{L3}。{L6}。{L7}。"
    "画面为2行3列网格布局，白色干净背景。"
    "上一行（3格）：全身正面、全身侧面、全身3/4侧面。"
    "下一行（3格）：面部特写-中性表情、微笑表情、愤怒表情。"
    "角色设计一致，写实摄影风格。比例3:2"
)

GRID_SPORT_ZH = (
    "一张写实风格的角色参考定妆照，展示{L0}。{L1}。{eyes}。{L3}。{L5}。{L6}。{L7}。"
    "画面为4列×2行共8格的网格布局，白色干净背景，格间有细灰线分隔。"
    "上一行：全身正面中性站姿、全身侧面站姿、面部正面中性表情特写、面部四分之三左侧表情特写。"
    "下一行：面部纯左侧轮廓特写、面部四分之三右侧表情特写、面部专注坚定眼神特写、面部发力表情特写。"
    "8格人物为完全相同的同一人。写实摄影风格，自然光线，高细节还原。比例3:2"
)

# ── 场景变体 ──
SCENE_TEMPLATE_ZH = (
    "{L0}。{L1}。{eyes}。{L3}。{L4}。{L5}。{L6}。{L7}。"
    "{scene_desc}。{L8}。{L9}。"
    "电影级摄影品质，写实风格。比例9:16"
)

# ── 表情变体 ──
EXPRESSION_TEMPLATE_ZH = (
    "面部特写肖像，{L0}。{L1}。{eyes}。{eyebrows}。{nose}。{lips}。{L3}。{L4}。{L6}。"
    "{expr_desc}。{L8}。"
    "专业影室肖像，纯灰色背景。比例9:16"
)

# ── 负面提示词（通用） ──
NEGATIVE_PROMPT = (
    "different face, inconsistent features, changed eye color, altered hair, "
    "morphed facial structure, deformed face, asymmetric face, "
    "extra limbs, bad anatomy, distorted, blurry, low quality, "
    "cartoon, anime, illustration, painting, 3D render"
)

NEGATIVE_PROMPT_ZH = (
    "面部不一致，五官改变，眼睛颜色变化，发型变化，"
    "面部结构扭曲，面部不对称，多余肢体，解剖错误，"
    "模糊，低质量，卡通，动漫，插画，3D渲染"
)


# ═══════════════════════════════════════════════════════════
# CharacterPromptSystem — 角色提示词系统
# ═══════════════════════════════════════════════════════════

class CharacterPromptSystem:
    """模块化10层角色提示词系统"""

    def __init__(self):
        # 每层的数据存储
        self._layers = {}
        for layer_id in CHAR_LAYERS:
            self._layers[layer_id] = {}
        for sub_id in SUB_LAYERS:
            self._layers[sub_id] = {}
        self._scene_override = ""
        self._expression_override = ""

    # ── 设置某层数据 ──

    def set_layer(self, layer_id: str, data: dict):
        """设置某层的数据"""
        if layer_id in self._layers:
            self._layers[layer_id].update(data)
        else:
            self._layers[layer_id] = data

    def get_layer(self, layer_id: str) -> dict:
        """获取某层的数据"""
        return self._layers.get(layer_id, {})

    def set_scene(self, scene_desc: str):
        """设置场景描述（用于场景变体）"""
        self._scene_override = scene_desc

    def set_expression(self, expr_desc: str):
        """设置表情描述（用于表情变体）"""
        self._expression_override = expr_desc

    # ── 从自然语言描述批量设置 ──

    def from_natural_description(self, desc: str):
        """从自然语言描述中尝试提取各层数据（简易版）"""
        # 这个功能由 attribute_extractor 完成更准确
        # 这里只做兜底
        self._layers["L0_identity"]["_raw"] = desc

    # ── 构建提示词 ──

    def build_prompt(self, variant: str = "front_face", lang: str = "zh",
                     mode: str = "standard", **kwargs) -> str:
        """
        构建完整的生成提示词

        参数:
          variant: 变体类型 (front_face|full_body|grid|scene|expression)
          lang: 语言
          mode: 网格模式 (standard|sport)
          **kwargs: 额外参数

        返回:
          完整提示词字符串
        """
        # 先构建各层描述
        layers_desc = self._build_layers_descriptions()

        if variant == "front_face":
            return self._build_front_face(layers_desc, lang)
        elif variant == "full_body":
            return self._build_full_body(layers_desc, lang)
        elif variant == "grid":
            return self._build_grid(layers_desc, lang, mode)
        elif variant == "scene":
            scene = kwargs.get("scene_desc", self._scene_override)
            return self._build_scene(layers_desc, lang, scene)
        elif variant == "expression":
            expr = kwargs.get("expr_desc", self._expression_override)
            return self._build_expression(layers_desc, lang, expr)
        else:
            return self._build_front_face(layers_desc, lang)

    def _build_layers_descriptions(self) -> dict:
        """构建所有层的描述文本"""
        result = {}

        # L0 身份
        result["L0"] = CHAR_LAYERS["L0_identity"]["build"](self._layers.get("L0_identity", {}))

        # L1 面部轮廓
        result["L1"] = CHAR_LAYERS["L1_face_shape"]["build"](self._layers.get("L1_face_shape", {}))

        # L2 五官子层
        for sub_id, sub_def in SUB_LAYERS.items():
            result[sub_id.replace("L2_face_", "")] = sub_def["build"](self._layers.get(sub_id, {}))

        # L3-L9
        for layer_id in ["L3_hair", "L4_skin_makeup", "L5_body",
                         "L6_clothing", "L7_expression", "L8_lighting_camera", "L9_background"]:
            key = layer_id.split("_")[0]  # L3, L4, etc
            result[key] = CHAR_LAYERS[layer_id]["build"](self._layers.get(layer_id, {}))

        return result

    def _build_front_face(self, d: dict, lang: str) -> str:
        """构建正面面部特写提示词"""
        template = FRONT_FACE_TEMPLATE_ZH if lang == "zh" else FRONT_FACE_TEMPLATE_EN
        prompt = template.format(
            L0=d.get("L0", ""), L1=d.get("L1", ""),
            eyes=d.get("eyes", ""), eyebrows=d.get("eyebrows", ""),
            nose=d.get("nose", ""), lips=d.get("lips", ""),
            L3=d.get("L3", ""), L4=d.get("L4", ""),
            L5=d.get("L5", ""), L6=d.get("L6", ""),
            L7=d.get("L7", ""), L8=d.get("L8", ""),
            L9=d.get("L9", ""),
        )
        # 清理空片段留下的多余标点
        return self._clean_prompt(prompt)

    def _build_full_body(self, d: dict, lang: str) -> str:
        """构建全身照提示词"""
        prompt = FULL_BODY_TEMPLATE_ZH.format(
            L0=d.get("L0", ""), L1=d.get("L1", ""),
            eyes=d.get("eyes", ""), L3=d.get("L3", ""),
            L4=d.get("L4", ""), L5=d.get("L5", ""),
            L6=d.get("L6", ""), L7=d.get("L7", ""),
        ) if lang == "zh" else ""
        return self._clean_prompt(prompt)

    def _build_grid(self, d: dict, lang: str, mode: str) -> str:
        """构建网格定妆照提示词"""
        template = GRID_SPORT_ZH if mode == "sport" else GRID_STANDARD_ZH
        prompt = template.format(
            L0=d.get("L0", ""), L1=d.get("L1", ""),
            eyes=d.get("eyes", ""), L3=d.get("L3", ""),
            L5=d.get("L5", ""), L6=d.get("L6", ""),
            L7=d.get("L7", ""),
        )
        return self._clean_prompt(prompt)

    def _build_scene(self, d: dict, lang: str, scene: str) -> str:
        """构建场景变体提示词"""
        scene_desc = scene or "自然场景"
        prompt = SCENE_TEMPLATE_ZH.format(
            L0=d.get("L0", ""), L1=d.get("L1", ""),
            eyes=d.get("eyes", ""), L3=d.get("L3", ""),
            L4=d.get("L4", ""), L5=d.get("L5", ""),
            L6=d.get("L6", ""), L7=d.get("L7", ""),
            scene_desc=scene_desc,
            L8=d.get("L8", ""), L9=d.get("L9", ""),
        )
        return self._clean_prompt(prompt)

    def _build_expression(self, d: dict, lang: str, expr: str) -> str:
        """构建表情变体提示词"""
        expr_desc = expr or "中性表情"
        prompt = EXPRESSION_TEMPLATE_ZH.format(
            L0=d.get("L0", ""), L1=d.get("L1", ""),
            eyes=d.get("eyes", ""), eyebrows=d.get("eyebrows", ""),
            nose=d.get("nose", ""), lips=d.get("lips", ""),
            L3=d.get("L3", ""), L4=d.get("L4", ""),
            L6=d.get("L6", ""), expr_desc=expr_desc,
            L8=d.get("L8", ""),
        )
        return self._clean_prompt(prompt)

    def _clean_prompt(self, prompt: str) -> str:
        """清理提示词中的多余标点和连续空格"""
        import re
        # 移除连续的逗号/句号
        prompt = re.sub(r'[，,]{2,}', '，', prompt)
        prompt = re.sub(r'[。.]{2,}', '。', prompt)
        # 移除空括号
        prompt = re.sub(r'（[^）]*?）', '', prompt)
        prompt = re.sub(r'\([^)]*?\)', '', prompt)
        # 移除开头的Punctuation
        prompt = re.sub(r'^[，。、\s]+', '', prompt)
        return prompt.strip()

    # ── 获取当前完整自然语言描述 ──

    def get_full_description(self) -> str:
        """生成完整的自然语言角色描述（用于知识库回写）"""
        d = self._build_layers_descriptions()

        parts = []
        for key in ["L0", "L1", "eyes", "eyebrows", "nose", "lips",
                     "L3", "L4", "L5", "L6", "L7"]:
            val = d.get(key, "")
            if val:
                parts.append(val)

        desc = "，".join(parts)
        return self._clean_prompt(desc)

    def get_layer_options(self, layer_id: str) -> dict:
        """获取某层的所有可选项"""
        layer = ALL_LAYERS.get(layer_id)
        if not layer:
            return {}
        return {
            "label": layer.get("label", ""),
            "icon": layer.get("icon", ""),
            "fields": layer.get("fields", []),
        }

    def get_all_layers_config(self) -> dict:
        """获取所有层的配置（供前端渲染）"""
        return {
            layer_id: self.get_layer_options(layer_id)
            for layer_id in ALL_LAYERS
        }

    def get_variant_types(self) -> dict:
        """获取支持的变体类型"""
        return {
            "front_face": "正面面部特写",
            "full_body": "全身照",
            "grid": "网格定妆照",
            "scene": "场景变体",
            "expression": "表情变体",
        }


# ═══════════════════════════════════════════════════════════
# 兼容旧接口（包装器）
# ═══════════════════════════════════════════════════════════

class PromptAssembler:
    """兼容旧版 PromptAssembler 接口"""

    def __init__(self):
        self._system = CharacterPromptSystem()

    def assemble(self, attrs: dict, variant_type: str,
                 lang: str = "zh", **kwargs) -> str:
        """兼容旧版 assemble 方法"""
        # 从旧式 attrs 填充系统
        if attrs.get("name") or attrs.get("description"):
            self._system.set_layer("L0_identity", {
                "name": attrs.get("name", ""),
                "gender": "男性" if "男" in attrs.get("description", "") else "女性",
            })

        face = attrs.get("face", {})
        if face:
            self._system.set_layer("L2_face_eyes", {
                "shape": face.get("eyes", ""),
                "spirit": "",
            })
            self._system.set_layer("L2_face_nose", {
                "bridge": face.get("nose", ""),
            })
            self._system.set_layer("L2_face_lips", {
                "shape": face.get("lips", ""),
            })
            if face.get("hair"):
                self._system.set_layer("L3_hair", {"style": face["hair"]})
            if face.get("skin"):
                self._system.set_layer("L4_skin_makeup", {"skin_tone": face["skin"]})

        clothing = attrs.get("clothing", {})
        if clothing:
            self._system.set_layer("L6_clothing", {
                "top": clothing.get("top", ""),
                "inner": clothing.get("inner", ""),
            })

        personality = attrs.get("personality", "")
        if personality:
            self._system.set_layer("L7_expression", {"base_mood": personality})

        # 映射变体类型
        variant_map = {
            "front_face": "front_face",
            "full_body": "full_body",
            "multi_angle": "front_face",
            "expression": "expression",
            "scene": "scene",
            "grid": "grid",
            "sport_action": "scene",
        }
        mapped_variant = variant_map.get(variant_type, "front_face")
        mode = kwargs.get("mode", "standard")

        expr = kwargs.get("expression_name", "")
        scene = kwargs.get("scene_name", "")
        if expr:
            self._system.set_expression(expr)
        if scene:
            self._system.set_scene(scene)

        return self._system.build_prompt(mapped_variant, lang, mode=mode)

    def get_available_variants(self) -> dict:
        """兼容旧接口"""
        return self._system.get_variant_types()


if __name__ == "__main__":
    # 测试
    system = CharacterPromptSystem()

    # 逐层设置
    system.set_layer("L0_identity", {"name": "阿远", "gender": "男性", "age": "青年(18-30)", "ethnicity": "中国"})
    system.set_layer("L1_face_shape", {"shape": "国字脸", "jaw": "清晰分明"})
    system.set_layer("L2_face_eyes", {"shape": "单眼皮", "color": "深褐", "spirit": "锐利深邃"})
    system.set_layer("L2_face_eyebrows", {"shape": "剑眉", "state": "舒展自然"})
    system.set_layer("L2_face_nose", {"bridge": "高挺", "tip": "圆润饱满"})
    system.set_layer("L2_face_lips", {"shape": "微笑唇", "state": "嘴角微扬"})
    system.set_layer("L3_hair", {"style": "短发", "color": "黑色", "detail": "两侧收短顶部略长"})
    system.set_layer("L4_skin_makeup", {"skin_tone": "健康小麦", "skin_texture": "自然肌理"})
    system.set_layer("L5_body", {"build": "健壮", "shoulder": "宽肩", "posture": "挺拔"})
    system.set_layer("L6_clothing", {"top": "深灰色拉链运动夹克", "inner": "白色速干内衬", "accessories": "蓝色无线运动耳机(右耳)"})
    system.set_layer("L7_expression", {"base_mood": "沉稳内敛", "eye_spirit": "目光坚定直视前方"})
    system.set_layer("L8_lighting_camera", {"light_type": "柔光箱均匀布光", "color_temp": "暖色调(金色)"})
    system.set_layer("L9_background", {"bg_type": "纯色背景", "bg_color": "纯灰/专业"})

    print("=== 正面面部特写 ===")
    print(system.build_prompt("front_face"))
    print("\n=== 网格定妆照 ===")
    print(system.build_prompt("grid", mode="standard"))
    print("\n=== 完整描述 ===")
    print(system.get_full_description())

    print("\n=== 前端配置数据 ===")
    config = system.get_all_layers_config()
    for layer_id, cfg in config.items():
        print(f"  {layer_id}: {cfg['icon']} {cfg['label']} ({len(cfg.get('fields',[]))} 字段)")

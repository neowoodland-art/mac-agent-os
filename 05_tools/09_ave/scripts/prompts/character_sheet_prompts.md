# Grid Method 定妆照 Prompt 模板
>
> 版本: 2.0 | 最后更新: 2026-05-18
> 用于 Kling 文生图 / Kling I2I 生成定妆照参考图库

---

## 一、标准 2x3 网格 Prompt（日常/漫剧风格）

### 英文模板（Kling / Midjourney 通用）

```
A professional character design sheet for [角色描述].
Layout is a 2x3 grid on a clean white background.
Top row (3 panels): full body front view, full body side profile view, full body 3/4 turn view.
Bottom row (3 panels): close-up of face - neutral expression, smiling expression, angry expression.
Consistent character design, flat shading, concept art style. --ar 3:2
```

### 中文模板（即梦 / 通义万相）

```
一张专业的角色设计表，展示[角色描述]。
画面为2行3列的网格布局，白色干净背景。
上一行（3格）：全身正面、全身侧面、全身3/4侧面。
下一行（3格）：面部特写-中性表情、微笑表情、愤怒表情。
角色设计一致，扁平着色，概念艺术风格。比例3:2
```

---

## 二、体育专用 3x3 网格 Prompt（写实摄影风格）

> 版本: 2026-05-18 | mode="sport" | 对应 character_sheet.py --mode sport

### 2.1 英文模板（T2I 纯文字生成）

```
A photorealistic character reference sheet for [角色描述].
Layout is a 3x3 grid on a clean white background, each panel separated by thin gray lines.
Row 1 (body views): full body front view standing neutral, full body side profile, full body 3/4 turn.
Row 2 (face close-ups): face neutral calm expression, face with determined focused look, face with intense exertion expression.
Row 3 (sport poses): dynamic running pose mid-stride, explosive jumping action, low defensive or power stance.
Photorealistic, sports photography style, same person in all 9 panels with identical face/hair/physique/clothes,
natural lighting, high detail. --ar 3:2
```

### 2.2 中文模板（T2I 纯文字生成）

```
一张写实风格的角色参考定妆照，展示[角色描述]。
画面为3行3列共9格的网格布局，白色干净背景，格间有细灰线分隔。
第一行（体型展示）：全身正面中性站姿、全身侧面站姿、全身3/4斜面站姿。
第二行（面部特写）：面部中性平静表情、面部专注坚定眼神、面部运动发力表情。
第三行（运动姿态）：跑步动态冲刺姿态、跳跃爆发力姿态、低重心防守蓄力姿态。
真实摄影写实风格，9格人物为完全相同的同一人，面部五官、发型、服装、体型高度一致，
自然光线，高细节还原，非插画非动漫。比例3:2
```

### 2.3 英文模板（I2I 参考照模式）

> 有真实参考照时用这个，人脸一致性：75-85% → 85-92%
> 对应 character_sheet.py --mode sport --ref reference.jpg

```
Based on the reference photo, create a photorealistic 3x3 character reference sheet.
The character is [角色描述].
Layout is a 3x3 grid on a clean white background, each panel separated by thin gray lines.
Row 1: full body front view, full body side view, full body 3/4 view - same outfit as reference.
Row 2: face portrait neutral, face portrait focused, face portrait intense effort.
Row 3: running action pose, jumping/explosive action pose, defensive/power stance pose.
MUST maintain exact same face, hairstyle, body shape as the reference photo person.
Photorealistic sports photography, natural lighting, high detail. --ar 3:2
```

---

## 三、角色描述块模板

角色描述块是跨场景一致性锚点，**全片所有 Prompt 必须复制同一段**：

```
[角色名], [性别], [年龄], [体型], [发型发色],
[面部特征], [肤色], [服装风格], [标志性配饰].
```

### 示例 A：日常商务

```
一位28岁的中国男性，身高178cm，标准体型，
黑色短发三七分，单眼皮，小麦色皮肤，
穿着深蓝色商务休闲西装外套配白色衬衫，
戴着一副细框金属眼镜。
```

### 示例 B：体育运动（基于真实参考照 — ghai）

```
一位中国男性，约42岁，体型健壮肩宽，
黑色短发利落，国字脸单眼皮，神态沉稳内敛，
肤色健康自然，
身穿深灰色运动夹克配白色速干内衬，
右耳戴着蓝色无线运动耳机。
```

---

## 四、Prompt 组装规则

每个视频场景的 Prompt = **角色描述块（不变）** + **场景描述块（每场景改）** + **镜头指令块（每场景改）**

```
[角色描述块: 完全复制上面的模板]
[场景描述块: 例如 "在清晨的城市公路上迎着阳光跑步"]
[镜头指令块: 例如 "中景侧面跟拍，低角度，运动模糊背景，暖色自然光"]
```

---

## 五、体育场景 Prompt 示例（ghai 角色）

### 男性角色（沉稳健壮型）

| 场景 | 场景描述块 | 镜头指令块 |
|:----|:---------|:---------|
| 晨跑 | 在清晨的城市街道上跑步，身体前倾摆臂有力，深灰夹克微微飘动，白色内衬渗出汗迹 | 中景侧面跟拍，动态模糊背景，清晨冷蓝色调 |
| 户外健身 | 在户外健身区做引体向上，双手握杠悬空，背部肌肉线条清晰可见，蓝色耳机点缀 | 低角度仰拍，强调力量感，逆光剪影边缘 |
| 街头篮球 | 在街头篮球场急停跳投，腾空后仰，单手出球，衣服因动作飘起 | 广角低角度，动态凝固抓拍，午后强烈阳光从侧面穿来 |
| 力量训练 | 在健身房杠铃架前深蹲，腿部发力蹬地，核心紧绷，表情专注 | 侧面中景，健身房冷白光，背景器械虚化 |

### 女性角色（活力运动型，供对照）

| 场景 | 场景描述块 | 镜头指令块 |
|:----|:---------|:---------|
| 户外跑步 | 在滨海步道上跑步，高马尾飞扬，朝阳侧光打在脸上形成温暖光晕 | 中景跟拍，暖色自然光，海天背景虚化 |
| 跳绳训练 | 在运动场跳绳，脚尖踮起，绳子高速旋转形成光影弧线 | 慢动作抓拍感，正面中景，背景轻微虚化 |

### 裔年轻（2026-05-29 自动注册）

角色描述块（跨场景一致性锚点，全片复制同一段）:
```
中景镜头，一位气质干净清澈的亚裔年轻男性，长相温润正派，五官端正立体，眼神真诚温暖带笑。身着燕麦色羊绒衫外搭深藏蓝亚麻外套，直身微侧，姿态挺拔舒展。背景是雨后湿润的江南古巷，斑驳青砖墙，脚下石板路反着水光。他一手拎着一袋用褐色纸袋包着、微微冒着热气的桂花糕，低头看向纸袋，嘴角带着温柔的笑意。 高清细节，暖色调，湿漉漉的地面映照天色，整体呈现胶片般柔和细腻的质感
```

结构化属性:
- 面部: {"shape": "", "eyes": "", "nose": "", "lips": "嘴角", "hair": "", "skin": "", "facial_hair": "", "glasses": "", "distinctive": ""}
- 体型: {"build": "", "height": "", "posture": "挺拔", "age_group": ""}
- 服装: {"top": "身着燕麦色羊绒衫（袖口微微挽起）外搭深藏蓝亚麻外套", "inner": "背景是雨后湿润的江南古巷", "bottom": "", "shoes": "", "style": ""}
- 配件: 
- 性格: 气质干净清澈的亚裔年轻男性


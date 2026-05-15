# Grid Method 定妆照 Prompt 模板
>
> 版本: 1.0 | 最后更新: 2026-05-15
> 用于 Kling 文生图 / Midjourney 生成 2x3 多视角角色定妆照

---

## 标准 2x3 网格 Prompt

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

## 角色描述块模板

角色描述块是跨场景一致性锚点，**全片所有 Prompt 必须复制同一段**：

```
[角色名], [性别], [年龄], [体型], [发型发色], 
[面部特征], [肤色], [服装风格], [标志性配饰].
```

### 示例

```
一位28岁的中国男性，身高178cm，标准体型，
黑色短发三七分，单眼皮，小麦色皮肤，
穿着深蓝色商务休闲西装外套配白色衬衫，
戴着一副细框金属眼镜。
```

---

## Prompt 组装规则

每个视频场景的 Prompt = **角色描述块（不变）** + **场景描述块（每场景改）** + **镜头指令块（每场景改）**

```
[角色描述块: 完全复制上面的模板]
[场景描述块: 例如 "站在现代简约风格的办公室里, 阳光透过落地窗洒进来"]
[镜头指令块: 例如 "中景, 镜头从正面缓缓推近, 浅景深, 温暖的自然光线"]
```

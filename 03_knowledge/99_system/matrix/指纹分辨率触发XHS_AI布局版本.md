---

title: 指纹分辨率触发小红书 AI-layout 版本
tags: [xhs, fingerprint, ai-layout, resolution]
created: 2026-05-27
collected: true
collected_date: 2026-06-09
---

## 现象

xhs_03（douyin_camo01）的首页布局和其他两个账号不同：
- 没有顶部搜索栏（`input.search-input` 不存在）
- 没有顶部 `header-container` 
- 首卡 y 偏移从 144px → 272px
- 主容器 class 是 `ai-layout-active`
- 但 `section.note-item` 选择器兼容，卡片正常

## 根因分析

通过修改指纹确认：**屏幕分辨率 + devicePixelRatio 触发了 XHS 的 A/B 测试版本分配。**

### 三账号指纹对比

| 特征 | xhs_01 | xhs_02 | xhs_03（改前） | xhs_03（改后） |
|------|--------|--------|----------------|----------------|
| Screen | 2752x1152 | 2176x1224 | **1920x1080** | 2752x1152 |
| DPR | 1.25 | 1.76 | **1.0** | 1.25 |
| 字体数 | 20 | 20 | **16** | 20（未改） |
| 布局 | standard | standard | **ai-layout** | **standard** ✅ |

### 验证方法

1. 读取 xhs_03 的 `fingerprint.pkl` → `screen.width=1920, screen.height=1080, devicePixelRatio=1.0`
2. 修改为 xhs_01 的规格（2752x1152, DPR=1.25）
3. 清除 XHS cookies + localStorage（清楚 A/B 分配缓存）
4. 重新加载 → **布局变为标准版**（搜索框出现、top bar 恢复、首卡 y=144）

## 结论

**XHS 会基于指纹的 screen 分辨率 + DPR 分配不同的 UI 版本。**
- 低分屏（1920x1080, DPR=1.0）→ `ai-layout-active`（无搜索栏、无顶栏）
- 高分屏（2752x1152, DPR=1.25+）→ 标准版

## 新建账号的指纹建议

为避免触发 AI layout 导致代码兼容问题：

```
fingerprint screen: 推荐 ≥ 1920x1080, DPR ≥ 1.25
具体建议值:
  screen.width: 1920 或更高（如 2752）
  screen.height: 1080 或更高
  devicePixelRatio: 1.25 ~ 2.0
  availWidth: 匹配 screen.width
  availHeight: screen.height - 48
```

## 代码兼容（已做）

即使遇到 AI layout，代码也做了兼容处理：
- `browse.py search()`: 三重降级（标准 → ALT → URL fallback）
- `browse.py click_search_result()`: 标准选择器 → href 通用匹配
- `runner.py`: 启动时自动检测布局版本（standard/ai-layout）

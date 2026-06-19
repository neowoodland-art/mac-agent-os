# Matrix 系统全面升级规划框架 v6.0

> 日期: 2026-06-14 | 状态: 规划阶段
> 本文件定义全部需求，拆解为可执行的任务清单

---

## 一、身份与账号 → 主页信息增强

### 现状
profiles.json 已采集 `fans`、`posts`、`following`、`likes` 字段，但前端卡片未展示。

### 改动
在身份与账号页面的平台行中增加：
```
🎵 抖音  ✅ ✅ ✅  2次  小美养生茶  📊1.1k粉 📹11作  🔑 🚫 🗑
```

在 `api_sms_accounts` 返回数据中透传 `fans`、`posts`、`following`、`likes` 字段。

---

## 二、命令与任务 → 信息采集模块重构

### 当前问题
- 页面太简单，只有一个下拉+两个按钮
- 只能按账号选，不能按身份/身份的平台选

### 目标结构

```
┌─ 👤 信息采集 ──────────────────────────────────┐
│                                                   │
│ 选择范围： [按身份 ▾] [按平台 ▾] [按账号 ▾]       │
│                                                   │
│ ┌─ 可选列表（按选择范围动态展示）───────────────┐  │
│ │ ☑ 📱 15370103682                             │  │
│ │   ├ ☑ 🎵 抖音 (小美养生茶)                   │  │
│ │   └ ☐ 📕 小红书 (xhs_01)                     │  │
│ │ ☐ 📱 13382504284                             │  │
│ │   └ ☐ 🎵 抖音 (douyin_133)                   │  │
│ └──────────────────────────────────────────────┘  │
│                                                   │
│ [👤 执行选中]  [📋 全部采集]                      │
│                                                   │
│ 采集日志：                                        │
│ ✅ douyin_test 采集完成 → 小美养生茶(1.1k粉)      │
│ ⏳ xhs_01 采集中...                               │
└───────────────────────────────────────────────────┘
```

### 采集范围切换逻辑
- **按身份**：显示手机号列表，勾选后该身份下所有平台都采集
- **按平台**：显示抖音/小红书列表，勾选后所有该平台的账号都采集
- **按账号**：显示所有账号列表（当前方式）

---

## 三、定时任务 → 完整可执行系统

### 当前状态
`mc/scheduler.py` 已实现：
- YAML 配置读取
- cron 表达式支持（`time: "09:00"` 格式）
- 自动执行 mc run 命令
- 日志记录

**缺少的**：
- Dashboard 创建/编辑/启停管理
- 历史执行记录
- 执行结果回传（成功/失败）
- 跨机器独立运行
- 命令行 mc schedule 完整子命令

### 目标架构

```
┌─ 定时任务系统 ───────────────────────────────────┐
│                                                    │
│ 配置层：config/schedule.yaml                        │
│   schedules:                                       │
│     douyin_daily:                                  │
│       enabled: true                                │
│       account: douyin_test                         │
│       blueprint: douyin_daily                      │
│       rounds: 3                                    │
│       time: "09:00"                                │
│       days: "1,2,3,4,5,6,7"  # 每周运行日          │
│                                                    │
│ 调度层：mc/scheduler.py                            │
│   - 30秒轮询检查                                   │
│   - 到达时间→执行 mc run                           │
│   - 记录结果到 logs/schedule_{date}.jsonl          │
│                                                    │
│ 管理层：Dashboard                                  │
│   - 任务列表（显示/编辑/删除/启停）                 │
│   - 历史记录（最近20次执行结果）                    │
│   - 手动触发执行                                   │
│                                                    │
│ CLI层：mc schedule                                  │
│   mc schedule list                                 │
│   mc schedule add --id xxx ...                     │
│   mc schedule remove --id xxx                      │
│   mc schedule start/stop                           │
│   mc schedule history --id xxx                     │
└────────────────────────────────────────────────────┘
```

### 执行结果记录格式
```jsonl
{"id":"douyin_daily","time":"09:00","date":"2026-06-14","status":"success","success":12,"failed":1,"duration":180}
{"id":"douyin_daily","time":"09:00","date":"2026-06-15","status":"failed","error":"Cookie expired","duration":5}
```

### 跨机器执行
- 每台机器独立运行 scheduler.py
- 从本地 accounts.yaml 读取账号
- 使用本地 profiles.json
- 结果写入本地 logs/

---

## 四、语料库 → 全面升级 + 移到命令与任务

### 当前结构（v1.x）
```yaml
categories:
  赞美:
    comments: ["讲得太好了"]
    templates: ["{keyword}很好"]
```

### 目标结构（v2.0）
```yaml
version: "2.0"

# 三维语料模型：身份 × 场景 × 内容
personas:
  health_lover:
    name: "养生爱好者"
    tags: ["养生", "健康"]

scenes:
  first_comment:
    label: "首次评论"
    rules: ["与视频内容相关"]
  follow_up:
    label: "跟帖回复"
    rounds: 2

content:
  health_lover.first_comment:
    - "这个养生方法很实用"
  health_lover.follow_up.round_1:
    - "确实如此，{keyword}我也是这么认为的"

# AI 生成配置
ai:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.8
  prompt_template: |
    你是一个{persona}，请对视频"{title}"发表{direction}评论。
    要求：{rules}

# 故事线/对话脚本
storylines:
  douyin_hot_topic:
    name: "抖音热门话题讨论"
    script:
      - scene: intro
        text: "最近{keyword}这个事我也关注了"
      - scene: develop
        text: "其实这个事情要从几个方面看..."
      - scene: reply_expected
        text: "你觉得呢？"
```

### Dashboard 语料库管理
```
命令与任务 → 语料库 TAB
├─ TAB: 按身份     — 选择身份→查看/编辑评论模板
├─ TAB: 按场景     — 首次评论/跟帖回复/作者回复
├─ TAB: 按故事线   — 创建/编辑对话脚本
├─ TAB: AI 生成    — 配置 API Key/模型/提示词模板
└─ TAB: 统计       — 语料总量/各分类数量/使用频率
```

---

## 五、批量执行 → 自动刷新 + 参数完整性

### 当前状态
- 账号列表：每次 `loadMatrixRun` 调用时从 API 获取 ✅ 自动更新
- 蓝图列表：同上 ✅ 自动更新
- 执行参数：轮数/轮间隔/账号间延迟/混合随机/语料分类/代理策略

### 需要确认的
| 参数 | 状态 |
|------|------|
| --accounts | ✅ 自动从 API 获取 |
| --blueprints | ✅ 自动从 API 获取 |
| --rounds | ✅ 有 |
| --interval | ✅ 有 |
| --stagger | ✅ 有（新增） |
| --mix | ✅ 有 |
| --corpus | ✅ 有（但需确认是否生效） |
| --proxy | ✅ 有 |
| --keep | ❌ 预览和执行都缺少 |

### 修复
- `--keep` 参数在 `batchPreview` 和 `batchExecute` 中补全

---

## 六、实施路线

| 阶段 | 内容 | 优先级 | 工作量 |
|------|------|--------|--------|
| P1 | 身份与账号增加粉丝/视频数展示 | 高 | 0.5天 |
| P2 | 信息采集模块重构（三维选择） | 高 | 1天 |
| P3 | 定时任务完善（历史+结果+管理） | 高 | 2天 |
| P4 | 语料库 v2 + Dashboard 管理 | 中 | 3天 |
| P5 | 批量执行参数补全 + 自动刷新 | 中 | 0.5天 |
| P6 | 同步文档 + 其他机器部署 | 高 | 1天 |

---

## 七、风险与依赖

| 风险 | 影响 | 缓解 |
|------|------|------|
| scheduler.py 当前只解析 time，不支持 cron 全语法 | 定时灵活性 | 先保持 time 格式兼容，后续扩展 |
| profiles.json 中粉丝/视频数据可能为空（未采集） | 展示不全 | 为空时显示"-"，提示用户采集 |
| 语料库 v2 格式与 v1 不兼容 | 旧语料不可用 | 代码兼容两种格式 |

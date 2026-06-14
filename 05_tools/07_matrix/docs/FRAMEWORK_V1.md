# MC 系统框架设计方案 v1.0

> 最后更新: 2026-06-14
> 设计目标: 三层分离 + 平台插件化 + 联邦多机协同 + 录制回放全链路 + 原子操作蓝图系统

---

## 一、核心设计原则

1. **CLI 优先** — 所有实操通过 `mc` 命令行执行, 稳定、可脚本化、可审计
2. **三层分离** — CLI 做执行 / AI 做分析决策 / Dashboard 做展示, 各司其职
3. **平台即插件** — 新增一个平台 = 新建一个目录, 标准接口自动发现
4. **不重复造轮子** — 发布/搜索/评论等通用能力集成开源项目
5. **联邦多机** — 每台机器独立运行, 通过 SSH/HTTP 远程调用, Gitee 同步状态
6. **录制回放即技能** — 原子操作录制是核心差异化能力, 录制包 = 可分享的技能

---

## 二、整体架构

```
┌──────────────────────────────────────────────────────────────┐
│  第1层: CLI 命令行 (最稳定层, 所有实操的唯⼀入口)               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  mc [platform] [action] --account <name> [options]      ││
│  │  mc [通用] [action] [options]                           ││
│  │  mc remote <machine> <command>   ← 远程执行              ││
│  │  mc record [start|stop|list|replay] ← 录制回放           ││
│  └──────────────────────────────────────────────────────────┘│
├──────────────────────────────────────────────────────────────┤
│  第2层: MCP Server + AI 智能体 (分析决策, 不直接碰浏览器)       │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  每个平台插件自动生成 MCP 工具                        ││
│  │  AI 智能体 → 调 MCP → 调 CLI → 读结果 → 出报告           ││
│  └──────────────────────────────────────────────────────────┘│
├──────────────────────────────────────────────────────────────┤
│  第3层: Dashboard 看板 (只展示 + 一键触发, 不执行复杂逻辑)     │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  读 JSON 展示 / 点按钮调 CLI / 看历史趋势图表              ││
│  │  多机聚合: 一台 Dashboard 展示所有机器状态                 ││
│  └──────────────────────────────────────────────────────────┘│
├──────────────────────────────────────────────────────────────┤
│  底座: 联邦多机同步                                           │
│  ┌──────────────┬──────────────┬───────────────────────────┐ │
│  │ Gitee 代码    │ SSH 远程执   │ guardd 心跳 + cross_     │ │
│  │ 同步(已有)    │ 行(新增)     │ machine 数据(已有)         │ │
│  └──────────────┴──────────────┴───────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 三、CLI 命令树 (完整版)

### 3.1 平台插件命令

```
mc douyin|xiaohongshu|bilibili|kuaishou|weibo|wechat [action]
  login                      --account <name>      登录
  logout                     --account <name>      登出
  status                     --account <name>      状态检查
  collect                    --account <name>      采集主页信息
  publish                    --account <name>      发布视频/图文
                             --file <path>
                             --title <text>
                             --desc <text>
  nurture                    --account <name>      养号
                             --blueprint <name>
  interact                   --account <name>      互动
                             --action like|comment|follow
                             --target <url/id>
  search                     --keyword <text>      搜索
                             --limit <n>
  live                       --room-id <id>        直播相关
  record                   录制原子操作(平台专属)
    start                   开始录制
    stop                    停止录制
    list                    列出录制包
    replay  <name>          回放录制包
```

### 3.2 通用管理命令

```
mc account
  list                      [--json]              列出所有账号
  create                    --phone <num>          创建新身份
                            --platform dy|xhs
  delete                    --account <id>         删除账号
  status                    [--json]              所有账号状态

mc sms
  check                     --phone <num>         查短信
  wait                      --phone <num>         等待新短信

mc config
  show                      [--json]              查看配置
  set                       <key> <value>         设置配置

mc record                  原子操作录制(跨平台通用)
  list                                            列出所有录制包
  export                    <name> --output <p>   导出录制包
  import                    <file>                导入录制包
  analyze                   <name>                分析录制内容

mc remote                  远程多机执行
  exec                      <machine> <cmd>       在远程机器执行命令
  status                    [--json]              所有机器状态
  sync                                             触发全机同步

mc agent
  "分析采集结果"                                  调 LLM 分析
  "检查账号健康度"
  "生成日报"
```

### 3.3 输出规范

所有命令支持 `--json` 参数, 输出标准 JSON 供 Dashboard 和 AI Agent 消费:

```bash
mc status --all --json
# → {"machines": {...}, "accounts": [...], "collected_at": "..."}

mc douyin collect --account my_name --json
# → {"status": "ok", "nickname": "...", "fans": 1303, ...}
```

---

## 四、平台插件标准

### 4.1 目录结构

```
platforms/
├── __init__.py                  # 插件发现: 自动扫描所有子目录
├── base.py                      # BasePlatform 基类
│
├── douyin/
│   ├── __init__.py              # 注册: name='douyin', actions=[...]
│   ├── cli.py                   # mc douyin [action] 的命令实现
│   ├── collector.py             # 主页信息采集 (已有collect_batch_runner)
│   ├── publisher.py             # 发布 (集成social-auto-upload)
│   ├── interactor.py            # 互动 (点赞/评论/关注)
│   ├── recorder.py              # 录制原子操作 (平台专属)
│   ├── SKILL.md                 # AI Agent 调用说明
│   └── requirements.txt         # 本平台额外依赖
│
├── xiaohongshu/                  # 同上
│
├── bilibili/                    # 发布复用 social-auto-upload
│
├── kuaishou/                    # (TODO)
│
└── wechat/                      # (TODO)
```

### 4.2 插件基类接口

```python
class BasePlatform:
    name: str                          # 平台名: 'douyin'
    display_name: str                  # '抖音'
    actions: list[str]                 # 支持的动作列表
    
    def login(account_name, headless=False) -> bool
    def logout(account_name) -> bool
    def status(account_name) -> dict
    def collect(account_name) -> dict   # 主页信息 → 写 homepage_info.json
    def publish(account_name, file, title, desc) -> bool
    def nurture(account_name, blueprint) -> bool
    def interact(account_name, action, target) -> bool
    def search(keyword, limit) -> list
```

### 4.3 新增平台流程

```bash
# 1. 创建插件目录
mkdir platforms/kuaishou/

# 2. 实现 base.py 中的接口
#    - 最简单的: 只实现 status(), 其他返回 "暂不支持"
#    - 完整版: 逐步实现 login/collect/publish ...

# 3. 注册插件
#    platforms/kuaishou/__init__.py:
#      register_platform(KuaishouPlatform())

# 4. 完成。mc 自动发现:
#    mc kuaishou status --account my_account
```

---

## 五、录制回放系统 (核心差异化能力)

### 5.1 定位

录制回放是 MC 系统区别于纯开源方案的核心能力。通过录制鼠标/键盘操作, 将人的操作经验转化为可复用的"技能包", 在同平台的不同账号间共享。

### 5.2 架构

```
录制阶段:
  人操作浏览器 → mc record start → 记录鼠标/键盘事件 → mc record stop
  → 保存为 platforms/douyin/recordings/login.skill (JSON)

回放阶段:
  mc douyin record replay login.skill --account my_name
  → 按时间轴回放鼠标/键盘事件 → 完成登录

分享阶段:
  mc record export login.skill → 得到 .skill 文件
  → 提交到 Gitee → 其他机器 mc record import → 直接可用
```

### 5.3 与三层架构的融合

- **CLI 层**: `mc record list|start|stop|replay|export|import`
- **平台插件**: 每个平台可以有专属的录制包 (抖音的登录流程 vs 小红书的登录流程不同)
- **跨平台**: 通用的录制包 (如"通用浏览") 放在 `recordings/` 根目录
- **Dashboard**: 录制管理界面保留, 但改为调 CLI 执行

### 5.4 录制包格式规范 (JSON)

```json
{
  "name": "douyin_login_20260614",
  "platform": "douyin",
  "created_at": "2026-06-14T22:00:00",
  "steps": [
    {"time": 0, "action": "navigate", "url": "https://www.douyin.com/"},
    {"time": 3000, "action": "click", "selector": ".login-btn", "x": 350, "y": 680},
    {"time": 5000, "action": "wait", "duration": 30000},
    {"time": 35000, "action": "check_login", "expected": true}
  ]
}
```

---

## 六、原子操作 + 蓝图系统

### 6.1 三层模型

```
录制 (record)
  ↓ 捕捉用户在浏览器上的操作
原子操作 (atom) = {前置状态锚点, 操作步骤, 后置状态验证}
  ↓ 组合串联成工作流
蓝图 (blueprint) = 有向无环图 (DAG) 的原子序列
  ↓ 打包发布为 CLI 命令
CLI 命令 = mc [platform] [blueprint_name] --account <name>
```

### 6.2 原子操作的数据结构

每个原子操作是一个自包含的"操作单元":

```json
{
  "name": "douyin_like_video",
  "category": "interact",
  "platform": "douyin",
  "version": 1,
  "description": "点赞当前播放的视频",
  "before": {
    "url_pattern": "https://www.douyin.com/**",
    "dom_anchor": ".video-player",
    "logged_in": true
  },
  "steps": [
    {"type": "wait", "target": ".like-btn", "timeout": 5000},
    {"type": "click", "target": ".like-btn", "xpath": "//div[contains(@class, 'like')]"},
    {"type": "verify", "check": ".like-btn.active"}
  ],
  "after": {
    "dom_check": ".like-btn.active"
  }
}
```

### 6.3 蓝图的 DAG 结构

蓝图 = 多个原子操作按顺序或条件连接成有向无环图:

```
          ┌─────────┐
          │ 登录检测  │
          └────┬────┘
               │ 未登录
          ┌────▼────┐
          │ 扫码登录  │
          └────┬────┘
               │ 已登录
          ┌────▼────┐
          │ 打开首页  │
          └────┬────┘
          ┌────▼────┐
          │ 浏览推荐  │  ← 循环 5 次
          └────┬────┘
          ┌────▼────┐
          │ 随机点赞  │  ← 30% 概率
          └────┬────┘
          ┌────▼────┐
          │ 等待 8秒  │
          └────┬────┘
          ┌────▼────┐
          │ 滚动加载  │
          └─────────┘
```

蓝图 JSON:

```json
{
  "name": "douyin_daily_browse",
  "platform": "douyin",
  "description": "日常浏览推荐页, 随机点赞",
  "version": 2,
  "nodes": [
    {"id": "check_login", "atom": "check_login", "position": {"x": 100, "y": 0}},
    {"id": "goto_home", "atom": "goto_home", "position": {"x": 100, "y": 80}},
    {"id": "browse", "atom": "wait_watch", "position": {"x": 100, "y": 160}},
    {"id": "like", "atom": "like", "position": {"x": 100, "y": 240}, "probability": 0.3},
    {"id": "scroll", "atom": "scroll_feed", "position": {"x": 100, "y": 320}}
  ],
  "edges": [
    {"from": "check_login", "to": "goto_home"},
    {"from": "goto_home", "to": "browse"},
    {"from": "browse", "to": "like"},
    {"from": "like", "to": "scroll"}
  ]
}
```

### 6.4 与 Dashboard 可视化编辑器的关系

Dashboard 的 **矩阵管理页 (matrix_mgmt.html) 已有 SVG DAG 节点编辑器**。

蓝图编排流程:

```
打开 Dashboard → 矩阵管理 → 蓝图编排 tab
  │
  ├─ 左侧节点面板: 列出所有可用原子操作 (按平台/分类)
  │   登录类 | 浏览类 | 互动类 | 工具类
  │
  ├─ 中间画布: 拖拽原子到画布, 连线编排
  │   支持: 顺序 / 条件分支 / 循环 / 概率
  │
  └─ 右侧属性面板: 配置选中节点的参数
      等待时间 | 点击概率 | 目标选择器
      

编辑完成后:
  → 保存为 blueprint.json → 存入 blueprints/ 目录
  → CLI 直接调用: mc douyin nurture --blueprint douyin_daily --account my_name
  → 或用录制功能生成新原子: mc record start → 操作 → mc record stop → 自动生成原子
```

### 6.5 录制 → 原子 → 蓝图 → CLI 全链路

```
步骤1: 录制
  mc record start                           ← 打开浏览器, 开始录制
  → 人在浏览器上操作 (点赞/评论/浏览...)
  mc record stop                            ← 停止录制
  → 生成 raw_recording.json (时间轴事件序列)

步骤2: 提炼原子
  mc record refine raw_recording.json       ← AI 辅助提炼
  → 生成 atom.json (结构化原子操作, 含前后状态)

步骤3: 组合蓝图
  Dashboard DAG 编辑器                       ← 拖拽编排
  或 CLI: mc blueprint compose --atoms a1,a2,a3
  → 生成 blueprint.json

步骤4: 打包发布
  mc blueprint publish douyin_daily_v3      ← 注入 blueprints/
  → 自动生成 CLI 入口
  mc douyin nurture --blueprint douyin_daily_v3 --account my_name
```

### 6.6 适配界面版本更新

当平台改版 (DOM 结构变化), 旧原子可能失效。方案:

1. **录制新操作**: `mc record start` → 在新版界面上操作 → `mc record stop`
2. **对比旧原子**: `mc record diff old_atom.json new_recording.json`
3. **自动修补**: AI 分析差异, 更新选择器/css/xpath
4. **版本管理**: 原子带 `version` 字段, 旧版蓝图可指定使用旧版原子

---

## 七、联邦多机协同方案

### 6.1 现状评估

| 能力 | 当前状态 | 评价 |
|------|:-------:|:----:|
| 代码同步 | Gitee push/pull | ✅ 够用 |
| 数据同步 | cross_machine 目录 | ✅ 够用 |
| 心跳检测 | guardd (300s 周期) | ⚠️ 基本够用, 但不够实时 |
| 远程执行 | ❌ 无 | 需开发 |
| 中央调度 | ❌ 无 | 按需 |

### 6.2 远程执行方案

最简单的方案: **SSH 包装 + 各机器 HTTP API**

```bash
# 方案A: SSH 远程执行 (简单可靠)
mc remote exec chengzigedeAir "mc douyin collect --account my_name"
# → ssh chengzigedeAir "cd ~/agent-os/... && python mc collect ..."

# 方案B: HTTP API 远程执行 (无需 SSH 配置)
mc remote exec chengzigedeAir "mc douyin collect"
# → curl http://chengzigedeAir:9988/api/cli/run
#   (每台机器 Dashboard 新增 /api/cli/run 端点)

# 方案C: 集群广播
mc remote exec --all "mc collect --all"
# → 同时在所有机器上执行采集
```

推荐方案: **B + A 双通道**。默认走 HTTP API (配置了 SSH 的机器可选 SSH)。

### 6.3 机器注册与管理

每台机器在首次部署时, 在 cross_machine/machines/ 下注册:

```yaml
# cross_machine/machines/7kecheng.yaml
hostname: 7kecheng
ip: 192.168.31.96
port: 9988
ssh_user: 7kecheng
capabilities: [douyin, xiaohongshu]   # 这台机器能操作哪些平台
local_accounts: 11                     # 本机账号数
```

### 6.4 guardd 替换方案: 从 Gitee 迁移到 Tailscale

#### 当前 guardd 的问题

guardd 每 300s 往 Gitee 仓库的 `04_memory/cross_machine/` 写心跳文件:

```
问题1: 每次 git status 都有 10 个文件被修改, 分不清是心跳还是真改动
问题2: 多机同时写 Gitee 导致 push/pull 冲突
问题3: 心跳延迟 (Gitee push 不是实时的)
问题4: 仓库里混入大量无意义的自动生成文件
```

**核心矛盾: Git 是版本管理工具, 不是实时状态同步工具。把心跳数据放 Gitee 是架构错误。**

#### 替换方案: 本地状态 + Tailscale 即时查询

```
┌────────────────────────────────────────────────────────┐
│ 部署前: guardd → Gitee (10个json频繁更新, 冲突不断)    │
│                                                       │
│ 部署后: 各机本地存状态 + 需查询时走 Tailscale HTTP API  │
│                                                       │
│ Gitee 仓库只保留:                                     │
│   代码 + 配置 + cross_machine/machines/ (机器注册,     │
│   几乎不变)                                            │
│                                                       │
│ 各机本地保留:                                          │
│   agent-local/tools/matrix/data/status.json           │
│   (心跳数据, 不参与 Gitee 同步)                        │
│                                                       │
│ 实时查询:                                              │
│   mc remote status → 通过 Tailscale 查各机 API         │
│   实时返回, 无冲突, 无延迟                              │
└────────────────────────────────────────────────────────┘
```

#### 具体实施

```
步骤1: guardd 停止写 Gitee 的 cross_machine/data/
       → 改为写本机 agent-local/tools/matrix/data/guardd_status.json
       → 文件格式不变, 只是换了个目录

步骤2: guardd 不再提交 git
       → 从 guardd.py 中去掉 git add/commit/push 步骤
       → cross_machine/data/*.json 文件不再被更新

步骤3: Gitee 仓库清理
       → 把 04_memory/cross_machine/data/ 加入 .gitignore
       → 一次性提交删除历史心跳文件
       → 以后 git status 不再被心跳文件污染

步骤4: 即时状态替代
       → 每台机器 Dashboard 提供 /api/machine/status 端点
       → mc remote status 通过 Tailscale 查各机
       → 实时, 无冲突, 零延迟
```

#### 对比

| 维度 | guardd (当前) | guardd (改造后) | mc remote |
|------|:------------:|:---------------:|:---------:|
| 存储位置 | Gitee 仓库 | 本机 local 目录 | 内存 + API |
| 更新频率 | 300s | 300s 或更长 | 即时查询 |
| Git 冲突 | ⚠️ 频繁 | ✅ 完全没有 | ✅ 不涉及 Git |
| 实时性 | ❌ 有延迟 | ❌ 有延迟 | ✅ 实时 |
| 历史记录 | ✅ 有 | ✅ 仍保留 | ❌ 无 (可加日志) |

**结论: guardd 保留, 但停止写 Gitee。改为写本机 + `mc remote` 做即时查询。** (2026-06-14 已实施)

### 6.5 `mc remote` 命令（已实现）

```bash
mc remote list                 # 列出已注册机器（来源: 本机machines.json + cross_machine/machines/）
mc remote ping [host]          # 连通性测试 (调用 /api/health)
mc remote status [host]        # 获取所有/指定机器完整状态 (调用 /api/machine/status)
mc remote exec <host> <cmd>    # 在远程机器执行 mc 命令 (调用 /api/machine/exec)
```

**通信方式 (--via):**
- `auto` (默认): 先试 HTTP API (Tailscale IP:9988), 失败自动回退 SSH
- `http`: 强制走 HTTP API (Dashboard 端点)
- `ssh`: 强制走 SSH 通道

**Dashboard 新增端点 (均已在 app.py 实现):**
```python
GET  /api/machine/status    # 本机完整状态 (系统/矩阵/采集/磁盘/guardd)
POST /api/machine/exec      # 远程执行 mc 命令 (白名单安全限制)
```

**Tailscale 安装 (可选, 但强烈推荐):**
```bash
brew install tailscale          # 每台机器都安装
tailscale up                    # 登录同一账号, 获得 100.x.x.x IP
# 之后 mc remote 通过该加密 IP 通信, 跨网络、跨子网、端到端加密
```

---

## 七、与开源项目的集成边界

| 功能 | 策略 | 具体方案 |
|------|:----:|----------|
| **抖音采集主页** | 🏗️ 自研 | 已有的 collect_batch_runner, 优势是联邦多机+批量错峰 |
| **小红书采集主页** | 🏗️ 自研 | Camoufox 方式, 修"我"按钮断点 |
| **录制回放** | 🏗️ 自研 | ⭐ 核心差异化能力, 开源项目没有 |
| **抖音发布视频** | 📦 集成 | social-auto-upload 的 douyin_uploader |
| **小红书发布笔记** | 📦 集成 | social-auto-upload 的 xiaohongshu_uploader |
| **B站发布** | 📦 集成 | social-auto-upload 的 bilibili uploader (本身用的 biliup) |
| **小红书搜索/评论** | 📦 集成 | xiaohongshu-mcp (12.4k stars) |
| **抖音搜索/下载** | 📦 参考 | 参考 dy-cli 的设计, 自己实现 |
| **抖音互动** | 🏗️ 自研 | 已有原子操作库, 集成到插件 |
| **反检测** | 📦 融合 | 引入 dy-cli 的高斯抖动 + 指数退避 |
| **联邦多机** | 🏗️ 自研 | ⭐ 核心差异化能力, 开源项目没有 |
| **多账号矩阵管理** | 🏗️ 自研 | ⭐ 核心差异化能力, 开源项目没有 |

---

## 八、四阶段落地路线

### 第一阶段: 命令行统一 (1-2天)
**目标: 所有操作能通过 mc 完成, 底层不改。**

- [ ] 清理 60+ 遗留脚本 → 归档到 `scripts/archive/`
- [ ] 规范 `mc collect` 命令 (已有, 需包装)
- [ ] 规范 `mc login` / `mc status` / `mc sms`
- [ ] 所有命令支持 `--json` 输出
- [ ] `mc status --all --json`

### 第二阶段: 平台插件化 (3-5天)
**目标: 插件架子搭好, 扩展零成本。**

- [ ] 建 `platforms/` 目录 + `BasePlatform` 基类
- [ ] 抖音插件: 拆入现有采集/养号逻辑
- [ ] 小红书插件: 同上
- [ ] mc 自动发现 `platforms/` 下的插件
- [ ] 录制系统整合: `mc record` 通用 + 平台专属

### 第三阶段: 接入开源生态 (1周)
**目标: 白嫖开源项目的能力。**

- [ ] `mc douyin publish` → 调 social-auto-upload
- [ ] `mc xhs publish` → 调 social-auto-upload
- [ ] `mc xhs search` → 调 xiaohongshu-mcp
- [ ] `mc bilibili publish` → 调 biliup
- [ ] 反检测: 引入高斯抖动 + 指数退避

### 第四阶段: 联邦多机 + 持续扩展
**目标: 万物皆可接, 多机协作。**

- [ ] `mc remote exec` 远程执行
- [ ] `mc remote status` 多机状态
- [ ] Dashboard 合并 + 多机聚合展示
- [ ] 采集历史版本化
- [ ] 新增平台: 快手 / 微博 / 视频号 / 微信群 / 直播
- [ ] MCP Server: 每个插件自动生成 MCP 工具

---

## 九、决策记录

| 决策 | 选项 | 选择 | 原因 |
|------|------|:----:|------|
| 浏览器窗口 | 显示/隐藏 | **显示** | 防封号+能看到进度+需要模拟鼠标 |
| 首发发布平台 | 抖音/小红书 | **抖音** | 用户量大 |
| Dashboard | 合并/保留 | **合并** | 减少混乱 |
| 遗留脚本 | 删除/归档 | **归档** | 万一需要还能找回 |
| 采集历史 | 快照/新覆盖 | **快照** | 看得出变化趋势 |
| 改造范围 | 先本机/全改 | **先本机** | 跑通再同步 |

---

## 十、风险管理

| 风险 | 概率 | 影响 | 应对 |
|:----|:----:|:----:|------|
| 开源项目停更 | 中 | 发布功能断 | 插件架构可换底层 |
| 平台反爬升级 | 高 | 采集/发布失效 | 反检测独立层, 单独升级 |
| 多机 SSH 配置复杂 | 低 | 远程执行用不了 | HTTP API 兜底, 不强制 SSH |
| 录制回放兼容性 | 中 | 跨版本录制包失效 | 录制包带版本号, 向前兼容 |
| Dashboard 合并工作量 | 中 | 阶段投入多 | 最后阶段再做, 先用两个 |

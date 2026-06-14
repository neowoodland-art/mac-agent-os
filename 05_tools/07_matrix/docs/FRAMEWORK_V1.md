# MC 系统框架设计方案 v1.0

> 最后更新: 2026-06-14
> 设计目标: 三层分离 + 平台插件化 + 联邦多机协同 + 录制回放全链路

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

## 六、联邦多机协同方案

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

### 6.4 guardd 改进建议

当前的 guardd 每 300s 写一次心跳, 问题:
- 间隔太长, 机器挂了一台不知道
- 心跳文件在 Gitee 上, 有 push 延迟

**改进方案**: 
- 保持 guardd 现有机制 (不要动, 够用)
- 增加 **"即时状态"通道**: `mc remote status` 时直接 HTTP 请求各机器, 不依赖 Gitee
- heartbeat 缩短到 60s (可选)

### 6.5 多机任务分配

```
场景: 在 chengzigedeAir 上执行抖音养号
→ mc remote exec chengzigedeAir "mc douyin nurture --account my_name --blueprint daily"

场景: 所有机器同时采集
→ mc remote exec --all "mc collect --all"

场景: 查所有机器状态
→ mc remote status --json
  {
    "7kecheng": {"online": true, "accounts": 11, "last_seen": "30s ago"},
    "chengzigedeAir": {"online": true, "accounts": 5, "last_seen": "2min ago"}
  }
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

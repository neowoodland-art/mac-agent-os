# AgentOS 联邦智能体协作指挥台 — 总体规划 v0.3

> 版本: v0.3（草案） | 最后更新: 2026-06-15
> 状态: 架构方向已确认，待细化各层

---

## 一、系统架构：命名空间分层

### 顶层入口

```
agentos                    ← 联邦智能体顶层命令
├── matrix                社交矩阵（抖音/小红书运营）
├── ave                   视频工厂（视频制作与编辑）
├── crawl                 内容采集（互联网内容抓取）
├── fleet                 联邦管理（多机协同）
└── serve                 服务管理（MCP/Dashboard/调度）
```

### 每一层的内部结构

```
agentos matrix                    社交矩阵
├── run                           执行养号/互动
├── account                       账号管理
├── collect                       主页信息采集
├── publish                       内容发布（短视频/图文）
├── blueprint                     蓝图管理
├── task                          定向任务
│   ├── comment                   定向评论
│   ├── search                    搜索任务
│   └── reply                     回复管理
├── schedule                      矩阵定时任务
├── corpus                        语料库
├── sms                           短信验证码
└── proxy                         代理管理


agentos ave                       视频工厂
├── render                        视频渲染/生成
├── script                        脚本/文案生成
├── material                      素材管理
│   ├── list                      素材列表
│   ├── add                       添加素材
│   └── search                    素材搜索
├── template                      模板管理
└── export                        导出/发布


agentos crawl                     内容采集
├── web                           网页内容抓取
├── video                         视频下载
├── extract                       信息提取（正文/标题/标签）
├── schedule                      采集定时任务
└── source                        采集源管理


agentos fleet                     联邦管理
├── sync                          一键同步所有机器
├── reconcile                     对账检查
├── exec                          远程执行命令
├── status                        集群状态
└── logs                          日志聚合


agentos serve                     服务管理
├── mcp                           启动 MCP Server（AI 调用入口）
├── dashboard                     启动/停止看板
└── schedule                      全局定时调度器
```

---

## 二、与现有系统的对应关系

| 新结构 | 现有位置 | 迁移方式 |
|:-------|:---------|:---------|
| `agentos matrix` | `mc` 全部命令 | **改名为 `agentos`，`mc` 保留为 alias** |
| `agentos matrix run` | `mc run` | 不变，直接继承 |
| `agentos matrix collect` | `mc collect` | 不变 |
| `agentos matrix account` | `mc account` | 不变 |
| `agentos matrix publish` | `publish_video.py` | 封装为子命令 |
| `agentos ave` | `09_ave/` (96个脚本) | 封装 CLI |
| `agentos crawl` | `05_crawl/` (29个脚本) | 封装 CLI |
| `agentos fleet` | `fleet_sync.sh` + `fleet_reconcile.sh` | 封装 CLI |
| `agentos serve mcp` | 新建 | 新增 |
| `agentos serve dashboard` | `run.py 9988` | 封装 CLI |

---

## 三、Dashboard 看板的映射

看板的导航结构直接映射到 `agentos` 的命名空间：

```
┌─── AgentOS 联邦指挥台 ──────────────────────────┐
│                                                    │
│  [矩阵]  [视频工厂]  [内容采集]  [联邦]  [服务]     │
│                                                    │
│  ┌─ 矩阵 ───────────────────────────────────────┐  │
│  │  账号管理 │ 养号执行 │ 信息采集 │ 内容发布    │  │
│  │  蓝图管理 │ 定向评论 │ 定时任务 │ 语料库      │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  ┌─ 视频工厂 ────────────────────────────────────┐  │
│  │  渲染任务 │ 脚本生成 │ 素材库 │ 模板          │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  ┌─ 内容采集 ────────────────────────────────────┐  │
│  │  采集任务 │ 源管理 │ 采集历史                  │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  ┌─ 联邦 ────────────────────────────────────────┐  │
│  │  机器状态 │ 一键同步 │ 对账检查 │ 远程Shell   │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  ┌─ 服务 ────────────────────────────────────────┐  │
│  │  MCP 状态 │ Dashboard日志 │ 全局定时任务      │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

---

## 四、MCP 暴露策略

按分层暴露，每个领域提供一组 MCP 工具：

```
agentos-mcp（总入口，自动发现所有子模块）
│
├── matrix/*             社交矩阵工具
│   ├── run_nurture      执行养号
│   ├── collect_info     采集主页
│   ├── publish_video    发布视频
│   ├── task_comment     定向评论
│   └── account_status   账号状态
│
├── ave/*                视频工厂工具 
│   ├── render_video     渲染视频
│   └── generate_script  生成脚本
│
├── crawl/*              内容采集工具
│   ├── fetch_web        抓取网页
│   └── download_video   下载视频
│
└── fleet/*              联邦管理工具
    ├── exec_remote      远程执行
    ├── sync_all         同步
    └── cluster_status   集群状态
```

---

## 五、Dashboard 插件映射

现有的插件系统保持不变，新增插件对应新命名空间：

| 插件 | 对应命名空间 | 状态 |
|:-----|:------------|:------|
| `plugins/matrix.py` | `agentos matrix` | ✅ 已有，需改造 |
| `plugins/kb_api.py` | 属于 `serve` | ✅ 已有 |
| `plugins/ave.py` | `agentos ave` | ✅ 已有 |
| `plugins/guardd.py` | `agentos fleet` | ✅ 已有 |
| `plugins/federation.py` | `agentos fleet` | 🔴 新增 |
| `plugins/scheduler.py` | `agentos serve schedule` | 🔴 新增 |
| `plugins/crawl.py` | `agentos crawl` | 🔴 新增 |

---

## 六、当前 Dashboard 在此架构中的位置

**Dashboard 不是"一个模块"，而是"所有模块的统一操作界面"。**

```
agentos serve dashboard ← 启动看板
                           ↓
                    Dashboard Web
                    ├── 矩阵标签页    → 调用 agentos matrix *
                    ├── 视频工厂标签页 → 调用 agentos ave *
                    ├── 内容采集标签页 → 调用 agentos crawl *
                    ├── 联邦标签页    → 调用 agentos fleet *
                    └── 服务标签页    → 调用 agentos serve *
```

每个标签页的**操作按钮**调用对应的 `agentos` 命令。
每个标签页的**数据展示**来自各机器的 API 聚合。

---

## 七、待讨论问题（下一轮）

架构方向定了之后，需要细化的点：

### 7.1 迁移策略

当前 `mc` 已经有很多脚本、蓝图、配置引用它。迁移方案：
- **A) 一步到位**：把所有 `mc` 引用改为 `agentos`，`mc` 作为 alias 保留
- **B) 渐进迁移**：先加 `agentos` 入口，`mc` 继续可用，逐步过渡

### 7.2 命名空间的 CLI 实现方式

- **A) 单 CLI 多级子命令**：一个 `agentos` 二进制，通过子命令分发（当前 `mc` 的做法）
- **B) 多 CLI 独立安装**：`agentos-matrix`、`agentos-ave` 各自独立

### 7.3 各领域的开发优先级

当前资源有限，先做哪个领域？

| 领域 | 现有成熟度 | 建议优先级 |
|:-----|:----------|:-----------|
| matrix（社交矩阵） | 最成熟，91个脚本 | **Phase 1** |
| fleet（联邦管理） | 基础已通 | **Phase 2** |
| ave（视频工厂） | 96个脚本但未 CLI 化 | **Phase 3** |
| crawl（内容采集） | 29个脚本 | **Phase 4** |
| serve（服务管理） | 新建 | 穿插进行 |

---

你觉得这个结构清晰了吗？如果没问题，下一轮我们就定：
1. 迁移策略（一步到位 vs 渐进）
2. CLI 实现方式（单CLI vs 多CLI）
3. 开发优先级

# Matrix 矩阵养号系统

> **版本**: v5.2 | **环境**: macOS (Apple Silicon) | **引擎**: Camoufox (Firefox 内核)
> **平台**: 抖音 ✅ | 小红书 ✅ | 知乎 🔄
> **最后更新**: 2026-06-13

---

## 一句话

Matrix 是一套社交账号养号自动化系统。通过 Camoufox 控制浏览器，自动完成日常养号任务（浏览、点赞、评论、搜索），模拟真实用户行为。

代码在 `agent-sync`（Gitee + GitHub 双同步），数据在 `agent-local`（本机，不同步）。

---

## 快速上手

```bash
# 1. 进入目录
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix

# 2. 查看所有命令
./mc --help

# 3. 日常养号（抖音）
./mc run --accounts douyin_test --blueprints douyin_daily --rounds 3

# 4. 日常养号（小红书）
./mc run --accounts xhs_01 --blueprints xhs_daily --rounds 2

# 5. 定向评论（给链接+方向）
./mc task comment --url https://v.douyin.com/xxx --direction 称赞

# 6. 搜索浏览
./mc task search --keyword 美食探店 --rounds 5

# 7. 启动 Dashboard
open http://localhost:9988
```

---

## Dashboard 导航

| 菜单 | 功能 |
|------|------|
| **首页** | 运营数据看板（本机账号/已登录/已采集/联邦账号） |
| **身份与账号** | 短信接收、注册新账号、账号卡片（四维状态+人设）、删除/登录/采集 |
| **命令与任务** | TAB1: 批量执行 / TAB2: 定向评论 / TAB3: 定时任务 |
| **账号总览** | 多机摘要 + 全账号表格 |
| **蓝图编排** | 管理所有蓝图 |
| **原子操作** | 原子操作库 |
| **录制管理** | 录制/分析/导出操作 |
| **⚙️ 矩阵设置** | TAB1: 导入导出 / TAB2: 备份恢复 / TAB3: 语料库 |

启动 Dashboard：
```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard
nohup ~/.workbuddy/binaries/python/envs/agent-os/bin/uvicorn app:app --host 0.0.0.0 --port 9988 &
```

---

## 核心功能

### 日常养号

5 个核心蓝图：

| 蓝图 | 用途 | 执行 |
|------|------|------|
| `douyin_daily` | 抖音日常养号（浏览+点赞+收藏+评论） | `mc run --accounts A --blueprints douyin_daily --rounds 3` |
| `xhs_daily` | 小红书日常养号 | `mc run --accounts A --blueprints xhs_daily --rounds 3` |
| `douyin_comment` | 定向评论（打开链接→评论） | `mc task comment --url URL --direction 称赞` |
| `douyin_search` | 搜索浏览（搜关键词→随机看视频） | `mc task search --keyword K --rounds 5` |
| `douyin_collect` | 信息采集（搜博主→采主页信息） | `mc task collect --keyword 博主名` |
| `douyin_reply` | 作者回复（看评论→回复） | `mc task reply --account douyin_test` |

### 智能任务（mc task）

```bash
# 定向评论（自动识别平台、选账号、生成评论）
mc task comment --url https://v.douyin.com/xxx --direction 称赞

# 搜索浏览
mc task search --keyword 美食探店 --rounds 5

# 信息采集
mc task collect --keyword 张三说科技

# 作者回复
mc task reply --account douyin_test

# 参数说明
mc task --list
```

### 账号管理

每个账号四维状态一目了然：
```
🎵 小美养生茶                       douyin_test
📱 15370103682
✅ 身份   ✅ 登录   ✅ 昵称   ✅ 同步
🎯 美食·养生·旅行 | 💬 称赞/提问      ← 人设
[🔑 登录]  [👤 采集]  [🗑 删除]
```

- **状态**：身份 ✅/❌ | 登录 ✅/❌ | 昵称 ✅/❌ | 同步 ✅/❌
- **操作**：🔑登录（打开浏览器扫码） | 👤采集（获取昵称/粉丝数） | 🗑删除

### 注册新账号

```bash
# 方式一：Dashboard 身份与账号 → 注册新账号
# 方式二：CLI
mc account register --platform douyin --phone 138xxxx --name 备注名
```

- 同手机号注册第二个平台时，自动复用同一份浏览器指纹
- 自动创建身份目录 → 打开浏览器 → 扫码登录

### 定时任务

```bash
# 添加定时任务
mc schedule add --id morning --account douyin_test --blueprint douyin_daily --time 09:00 --rounds 3

# 列出定时任务
mc schedule list

# 启动调度器（保持终端运行）
mc schedule start
```

### 账号人设

每个账号可配置人设，养号时自动按人设选语料方向和搜索关键词：

```json
{
  "nickname": "小美养生茶",
  "persona": {
    "interests": ["美食", "养生", "旅行"],
    "comment_style": ["称赞", "提问"],
    "search_keywords": ["美食探店", "养生茶", "周末去哪"]
  }
}
```

配置位置：`agent-local/tools/matrix/data/profiles.json`

---

## 新机部署

```bash
# 1. 拉取代码
cd ~
git clone git@github.com:neowoodland-art/mac-agent-os.git workbuddy-agent-os/agent-sync
cd workbuddy-agent-os/agent-sync

# 2. 运行初始化
bash 00_bootstrap/init.sh

# 3. 安装 Matrix 依赖
cd 05_tools/07_matrix
bash install.sh

# 4. 同步本机账号
# 从 accounts_registry.yaml 自动同步 assigned_machine 为本机的账号

# 5. 启动 Dashboard
cd ~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard
nohup ~/.workbuddy/binaries/python/envs/agent-os/bin/uvicorn app:app --host 0.0.0.0 --port 9988 &

# 6. 第一次使用需扫码登录
./mc account login douyin_test
```

---

## CLI 命令参考

| 命令 | 用途 |
|------|------|
| `mc run --accounts A,B --blueprints X,Y --rounds N` | 批量执行养号任务 |
| `mc task comment --url U --direction D` | 智能定向评论 |
| `mc task search --keyword K` | 搜索浏览 |
| `mc task collect --keyword K` | 信息采集 |
| `mc task reply --account A` | 作者回复 |
| `mc account list` | 列出所有账号 |
| `mc account login <name>` | 扫码登录 |
| `mc schedule list` | 列出定时任务 |
| `mc schedule add --id X --account Y --blueprint Z --time HH:MM` | 添加定时任务 |
| `mc schedule start` | 启动定时调度器 |
| `mc record start --account A` | 录制原子操作 |
| `mc record list/analyze/export` | 录制管理 |
| `mc corpus list` | 查看语料库 |

---

## 数据存储

```
~/workbuddy-agent-os/
├── agent-sync/05_tools/07_matrix/    ← 代码（Git 同步）
│   ├── blueprints/                    ← 任务蓝图（JSON）
│   ├── scripts/mc/                    ← 核心引擎
│   ├── corpus/                        ← 评论语料库
│   └── config/                        ← 配置（定时任务、AI 等）
│
└── agent-local/tools/matrix/         ← 数据（本机，不同步）
    ├── config/accounts.yaml           ← 本机账号配置
    ├── identities/                    ← 浏览器身份目录
    │   ├── douyin_test/               ← 账号A（含 cookies、指纹）
    │   └── phone_138xxxx/             ← 同手机号共享身份（新注册）
    ├── data/profiles.json             ← 昵称/人设数据
    ├── recordings/                    ← 录制包
    └── logs/                          ← 运行日志
```

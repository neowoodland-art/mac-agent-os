# 矩阵养号系统 Matrix — 完整项目说明

> **项目版本**: v3.0（2026-04-28）
> **负责人**: ghai
> **最后更新**: 2026-04-28

---

## 一、项目概述

### 1.1 什么是矩阵养号系统

矩阵养号系统是一个**自动化社交账号运营工具**，通过程序化控制浏览器完成抖音、小红书、知乎等平台的日常养号任务。目标是让多个账号模拟真实用户行为，提升账号权重和活跃度。

### 1.2 核心价值

| 价值点 | 说明 |
|--------|------|
| **自动化** | 告别手动操作，自动执行浏览、点赞、评论、收藏等任务 |
| **多账号** | 支持同时管理多个账号，每个账号独立隔离 |
| **反检测** | 内置多种反检测措施，降低被平台识别为机器人的风险 |
| **可扩展** | 支持多平台、蓝图化任务、灵活配置 |
| **可迁移** | 完整的环境配置和迁移方案 |

### 1.3 支持平台

| 平台 | 状态 | 核心功能 |
|------|------|---------|
| 抖音 | ✅ 已实现 | 推荐浏览、搜索、点赞、收藏、评论、关注 |
| 小红书 | 🔄 框架完成 | 需登录账号 |
| 知乎 | 🔄 框架完成 | 需登录账号 |
| 快手 | 📋 规划中 | 待开发 |

---

## 二、宏伟蓝图与目标

### 2.1 最终愿景

> **打造一个全平台、智能化、可持续的社交账号矩阵运营系统**

### 2.2 发展阶段规划

```
阶段A ✅ 已完成（2026-04-27）
├── Chrome CDP 直连
├── 抖音原子操作库 V2（18个操作）
├── 蓝图执行引擎
├── 定时调度器
├── 账号切换器（双方案）
├── 指纹注入
└── 双账号并行

阶段B 🔄 进行中
├── Camoufox（Firefox内核）集成 ← 当前卡点
├── 多浏览器内核支持
├── 提升反检测能力
└── 第二个账号登录

阶段C 📋 规划中
├── 鼠标轨迹仿真
├── 语料库完善
├── Canvas/AudioContext 指纹噪声
└── 静态住宅IP接入

阶段D 📋 规划中
├── 小红书完整支持
├── 知乎完整支持
├── 多平台联动
└── 智能行为决策
```

### 2.3 里程碑目标

| 阶段 | 目标账号数 | 反检测等级 | 自动化程度 |
|------|-----------|-----------|-----------|
| A | 1-2个 | ⭐⭐ | 半自动（需手动登录） |
| B | 2-4个 | ⭐⭐⭐ | 半自动（Camoufox） |
| C | 4-8个 | ⭐⭐⭐⭐ | 全自动 |
| D | 10+个 | ⭐⭐⭐⭐⭐ | 全自动+智能决策 |

---

## 三、项目架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户指令 / 定时触发                        │
└─────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                      蓝图引擎 (task_engine.py)                    │
│                      定时调度 (task_scheduler.py)                   │
└─────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                     原子操作库 (douyin_ops.py)                     │
│                     18个最小操作单元，含前置检查+执行+后置验证          │
└─────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                     账号切换器 (switch_account.py)                  │
│              方案A: Chrome Profile切换  方案B: Cookie注入            │
└─────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────┐
│  ┌──────────────────┐         ┌──────────────────┐              │
│  │   Chrome CDP      │         │   Camoufox       │              │
│  │   端口 9222/9223  │         │   端口 9301/9302 │              │
│  │   ✅ 已完成       │         │   🔄 进行中      │              │
│  └──────────────────┘         └──────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                     抖音网页 / 小红书 / 知乎                         │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| 原子操作库 | `scripts/douyin_ops.py` | 封装18个浏览器操作 |
| CDP连接器 | `scripts/cdp_connector.py` | 管理Chrome CDP连接 |
| 账号切换器 | `scripts/switch_account.py` | 多账号Profile切换 |
| Camoufox管理 | `scripts/camoufox_manager.py` | Firefox内核管理 |
| 蓝图引擎 | `scripts/task_engine.py` | 读取执行JSON蓝图 |
| 定时调度 | `scripts/task_scheduler.py` | Cron定时任务 |
| 数据库 | `data/matrix.db` | 账号、蓝图、日志存储 |

### 3.3 数据流

```
蓝图JSON → 引擎解析 → 操作序列 → CDP执行 → 页面响应 → 日志记录
              ↓
         频率控制（防封）
              ↓
         错误恢复（自动重试）
              ↓
         结果统计（数据库）
```

---

## 四、环境依赖

### 4.1 系统要求

| 项目 | 要求 | 当前环境 |
|------|------|---------|
| 操作系统 | macOS (Apple Silicon) | ✅ macOS |
| Python | 3.13+ | ✅ 3.13.12 |
| Chrome | 最新版 | ✅ 已安装 |
| 磁盘空间 | 10GB+ | ✅ 充足 |

### 4.2 Python环境

```bash
# 使用的Python路径
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3
```

**必须安装的包**:
```bash
pip install patchright camoufox pyyaml aiosqlite
```

### 4.3 浏览器

| 浏览器 | 用途 | 状态 | 端口 |
|--------|------|------|------|
| Chrome | 主要浏览器 | ✅ 已配置 | 9222/9223 |
| Camoufox | Firefox内核（反检测更强） | 🔄 配置中 | 9301/9302 |

### 4.4 目录结构

```
~/matrix/
├── docs/                           # 项目文档
│   ├── PROJECT_OVERVIEW.md         # 本文件（项目总览）
│   ├── DOUYIN_FULL_PLAN.md         # 抖音完整方案
│   ├── DOUYIN_SELECTORS.md         # 选择器手册
│   ├── PHASE_A_SUMMARY.md          # 阶段A完成总结
│   ├── CAMOUFOX_LOGIN_MANAGEMENT.md # Camoufox集成方案
│   ├── IP_SWITCH_GUIDE.md          # IP切换指南
│   ├── IMPLEMENTATION_GUIDE.md     # 落地手册
│   └── LOCAL_ADAPTATION.md         # 本地适配说明
├── scripts/                        # 核心脚本
│   ├── douyin_ops.py               # 原子操作库（18操作）
│   ├── cdp_connector.py            # CDP连接器
│   ├── switch_account.py           # 账号切换器
│   ├── camoufox_manager.py         # Camoufox管理器
│   ├── task_engine.py              # 蓝图引擎
│   ├── task_scheduler.py           # 定时调度
│   ├── seed_db.py                  # 数据库初始化
│   ├── init_db.py                  # 数据库初始化
│   └── launch_chrome.sh            # Chrome启动脚本
├── blueprints/                     # 任务蓝图
│   ├── douyin_browse_v2.json       # 日常浏览V2（11步）
│   ├── douyin_search_browse.json   # 搜索浏览（7步）
│   ├── douyin_comment_interact.json # 评论互动（8步）
│   └── douyin_browse.json          # 日常浏览V1（已废弃）
├── config/                         # 配置文件
│   └── accounts.yaml               # 账号配置
├── data/                           # 数据存储
│   ├── matrix.db                   # SQLite数据库
│   ├── cookies/                    # Cookie存储
│   └── camoufox_pids/             # Camoufox进程PID
├── profiles/                       # 浏览器Profile
│   ├── account_01/                 # 抖音主号Profile
│   ├── douyin_02/                  # 抖音副号Profile
│   ├── camoufox_01/               # Camoufox账号1
│   └── camoufox_02/               # Camoufox账号2
├── corpus/                         # 语料库
├── logs/                           # 日志
├── screenshots/                    # 截图存档
└── docker/                         # Docker配置（未来）
```

---

## 五、当前状态

### 5.1 已完成功能

#### ✅ 阶段A：Chrome CDP 方案

| 功能 | 状态 | 说明 |
|------|------|------|
| CDP直连Chrome | ✅ 完成 | Patchright connect_over_cdp |
| 原子操作库V2 | ✅ 完成 | 18个操作，含前置检查+后置验证 |
| 蓝图引擎 | ✅ 完成 | JSON蓝图顺序执行 |
| 定时调度 | ✅ 完成 | Cron表达式调度 |
| 账号切换器 | ✅ 完成 | Profile切换+Cookie注入 |
| 指纹注入 | ✅ 完成 | 视口+时区+语言+WebGL |
| 双账号并行 | ✅ 完成 | 端口9222+9223 |

#### 🔄 阶段B：Camoufox 集成（进行中）

| 功能 | 状态 | 说明 |
|------|------|------|
| Camoufox包安装 | ✅ 完成 | v3.0.0 |
| Camoufox浏览器下载 | ✅ 完成 | v135.0.1-beta.24 |
| Profile目录创建 | ✅ 完成 | camoufox_01, camoufox_02 |
| Camoufox启动 | 🔄 卡住 | executable_path配置问题 |
| Camoufox登录 | ⏸ 待开始 | 需启动后才能登录 |
| Camoufox CDP连接 | ⏸ 待开始 | 需登录后验证 |

### 5.2 账号状态

| 账号ID | 平台 | 端口 | 浏览器 | 状态 |
|--------|------|------|--------|------|
| douyin_01 | 抖音 | 9222 | Chrome | ✅ 已登录 |
| douyin_02 | 抖音 | 9223 | Chrome | ⏸ 待登录 |
| xhs_01 | 小红书 | 9224 | Chrome | ⏸ 待注册 |
| zhihu_01 | 知乎 | 9225 | Chrome | ⏸ 待注册 |
| douyin_camo01 | 抖音 | 9301 | Camoufox | 🔄 配置中 |
| douyin_camo02 | 抖音 | 9302 | Camoufox | 🔄 配置中 |

### 5.3 蓝图状态

| 蓝图ID | 名称 | 步骤数 | 状态 | 备注 |
|--------|------|--------|------|------|
| douyin_browse_v2 | 日常浏览V2 | 11步 | ✅ 活跃 | 推荐使用 |
| douyin_search_browse | 搜索浏览 | 7步 | ✅ 活跃 | - |
| douyin_comment_interact | 评论互动 | 8步 | ✅ 活跃 | - |
| douyin_browse | 日常浏览V1 | 8步 | ⛔ 废弃 | 不再使用 |

---

## 六、遇到的问题

### 6.1 Camoufox 启动问题（当前卡点）

**问题描述**：
```
FileNotFoundError: [Errno 2] No such file or directory: 
'/Users/7kecheng/Library/Caches/camoufox/Camoufox.app/Contents/MacOS/properties.json'
```

**原因分析**：
- Camoufox 浏览器缓存文件不完整
- `camoufox_manager.py` 中显式指定的 `executable_path` 导致路径查找错误
- `properties.json` 文件实际位于 `Resources` 目录，而非 `MacOS` 目录

**已尝试的解决**：
1. ✅ 清理缓存 `rm -rf ~/Library/Caches/camoufox`
2. ✅ 重新下载 `camoufox fetch`
3. ✅ 修改脚本移除显式 `executable_path` 路径

**当前状态**：
- 已修改 `camoufox_manager.py` 第148-154行
- 等待下次启动验证

### 6.2 踩坑记录（历史问题，已解决）

| 问题 | 日期 | 原因 | 解决方案 |
|------|------|------|---------|
| `hash()` 跨进程不一致 | 2026-04-27 | Python随机种子 | 改用 `sum(ord(c))` |
| 移动端UA覆盖破坏登录 | 2026-04-27 | Android UA导致Cookie校验失败 | 不覆盖UA |
| 移动端视口破坏登录 | 2026-04-27 | `mobile: True`改变渲染 | `mobile: False` |
| 视口过窄 | 2026-04-27 | 初始参数480px | 实测702x783最佳 |
| Profile目录名错误 | 2026-04-27 | 配置与实际不符 | 修正accounts.yaml |

---

## 七、下一步计划

### 7.1 立即任务（今天）

| 优先级 | 任务 | 状态 | 操作 |
|--------|------|------|------|
| P0 | Camoufox启动验证 | 🔄 进行中 | 移除executable_path后重新启动 |
| P0 | douyin_camo01登录 | ⏸ 等待 | 启动后手动扫码登录 |
| P0 | 导出Cookie | ⏸ 等待 | 登录后导出备份 |

### 7.2 短期任务（本周）

| 优先级 | 任务 | 预计时间 |
|--------|------|---------|
| P0 | Camoufox CDP连接验证 | 1小时 |
| P1 | 鼠标轨迹仿真 | 4小时 |
| P1 | 语料库填充 | 1小时 |
| P2 | douyin_02登录 | 1小时 |

### 7.3 中期任务（本月）

| 优先级 | 任务 | 预计时间 |
|--------|------|---------|
| P1 | 静态住宅IP接入 | 按服务商 |
| P2 | Cookie方案B完善 | 4小时 |
| P3 | 小红书支持 | 1天 |
| P3 | 知乎支持 | 1天 |

### 7.4 长期任务（未来）

| 任务 | 说明 |
|------|------|
| 多平台联动 | 抖音→小红书→知乎互动联动 |
| 智能决策 | AI驱动的行为决策 |
| Docker容器化 | 完全隔离的多容器部署 |

---

## 八、如何执行

### 8.1 快速开始

```bash
# 1. 进入项目目录
cd ~/matrix

# 2. 查看帮助
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 scripts/switch_account.py --help

# 3. 启动Chrome账号（方案A）
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 scripts/switch_account.py --method profile --target douyin_01 --port 9222

# 4. 查看状态
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 scripts/switch_account.py --status
```

### 8.2 执行蓝图

```bash
# 执行日常浏览蓝图
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 scripts/task_engine.py --blueprint douyin_browse_v2 --account douyin_01

# 执行搜索浏览蓝图
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 scripts/task_engine.py --blueprint douyin_search_browse --account douyin_01
```

### 8.3 Camoufox操作（待修复后）

```bash
# 启动Camoufox
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 scripts/camoufox_manager.py --launch douyin_camo01

# 验证登录
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 scripts/camoufox_manager.py --verify douyin_camo01

# 导出Cookie
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 scripts/camoufox_manager.py --export douyin_camo01
```

### 8.4 定时调度

```bash
# 添加每日任务（每天9点执行）
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 scripts/task_scheduler.py --add "douyin_browse_v2" --cron "0 9 * * *"
```

---

## 九、迁移方案

### 9.1 迁移准备清单

迁移前需要准备以下内容：

```
□ 源码目录 ~/matrix/
□ Profile目录 ~/matrix/profiles/
□ Cookie备份 ~/matrix/data/cookies/
□ 配置文件 config/accounts.yaml
□ 浏览器安装（Chrome / Camoufox）
□ Python 3.13+ 环境
□ pip 包（patchright, camoufox, pyyaml）
```

### 9.2 完整迁移步骤

```bash
# 1. 打包源码（排除大文件和缓存）
rsync -av --exclude='profiles/*/Cache' \
      --exclude='logs/*.log' \
      --exclude='.DS_Store' \
      ~/matrix/ /path/to/backup/matrix/

# 2. 打包Profile（选择性迁移登录状态）
rsync -av ~/matrix/profiles/account_01/ /path/to/backup/profiles/account_01/

# 3. 打包Cookie
rsync -av ~/matrix/data/cookies/ /path/to/backup/cookies/

# 4. 在新机器安装依赖
pip install patchright camoufox pyyaml aiosqlite

# 5. 下载Camoufox浏览器
python3 -m camoufox fetch

# 6. 启动Chrome并验证
python3 scripts/switch_account.py --status
```

### 9.3 迁移后检查

```bash
# 检查Python环境
python3 --version  # 应为3.13+

# 检查pip包
pip list | grep -E "patchright|camoufox|pyyaml"

# 检查Chrome
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version

# 检查Camoufox
python3 -m camoufox path

# 初始化数据库
python3 scripts/init_db.py

# 测试CDP连接
python3 scripts/switch_account.py --status
```

### 9.4 注意事项

1. **Profile迁移**：Cookie和登录状态在Profile中，整体迁移最简单
2. **Camoufox**：每个平台需要单独下载浏览器
3. **代理配置**：如果使用代理，迁移后需更新账号配置
4. **端口占用**：确保9222-9322端口未被占用

---

## 十、常见问题

### Q1: Chrome无法启动？

```bash
# 检查Chrome是否安装
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version

# 检查端口是否被占用
lsof -i :9222
```

### Q2: CDP连接失败？

```bash
# 启动Chrome时添加CDP端口
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir=~/matrix/profiles/account_01
```

### Q3: Camoufox下载失败？

```bash
# 设置代理后重试
export https_proxy=http://127.0.0.1:7890
python3 -m camoufox fetch
```

### Q4: 账号被封禁？

- 降低操作频率
- 使用静态住宅IP
- 增加随机延迟
- 模拟真实用户行为

---

## 十一、联系方式

- **项目负责人**: ghai
- **项目目录**: ~/matrix/
- **文档目录**: ~/matrix/docs/

---

## 附录A：关键文件路径速查

| 文件 | 路径 |
|------|------|
| 项目根目录 | ~/matrix/ |
| 账号配置 | ~/matrix/config/accounts.yaml |
| 原子操作库 | ~/matrix/scripts/douyin_ops.py |
| CDP连接器 | ~/matrix/scripts/cdp_connector.py |
| 账号切换器 | ~/matrix/scripts/switch_account.py |
| Camoufox管理 | ~/matrix/scripts/camoufox_manager.py |
| 数据库 | ~/matrix/data/matrix.db |
| Cookie存储 | ~/matrix/data/cookies/ |
| Profile存储 | ~/matrix/profiles/ |

## 附录B：环境变量速查

| 变量 | 值 |
|------|---|
| PYTHON | /Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 |
| CHROME | /Applications/Google Chrome.app/Contents/MacOS/Google Chrome |
| CAMOUFOX_CACHE | ~/Library/Caches/camoufox/ |
| PROJECT_DIR | ~/matrix/ |

---

**文档版本**: v1.0
**创建日期**: 2026-04-28
**更新日期**: 2026-04-28

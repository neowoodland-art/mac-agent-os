# 全自动矩阵养号运维系统 Matrix

> **版本**: v3.0
> **适用平台**: 抖音、小红书、知乎、快手
> **运行环境**: macOS Apple Silicon (M1/M2/M3)
> **最后更新**: 2026-04-28

---

## 🚀 快速开始

```bash
# 进入项目目录
cd ~/matrix

# 启动抖音主号（Chrome）
python scripts/switch_account.py --method profile --target douyin_01 --port 9222

# 执行日常浏览蓝图
python scripts/task_engine.py --blueprint douyin_browse_v2 --account douyin_01

# 查看所有命令
python scripts/switch_account.py --help
```

---

## 📚 文档导航

| 文档 | 说明 | 优先级 |
|------|------|--------|
| **[项目总览](./docs/PROJECT_OVERVIEW.md)** | 完整项目说明、环境依赖、迁移方案 | ⭐必读 |
| **[阶段A总结](./docs/PHASE_A_SUMMARY.md)** | Chrome CDP方案完成情况 | ⭐必读 |
| **[Camoufox集成](./docs/CAMOUFOX_LOGIN_MANAGEMENT.md)** | Firefox内核集成方案 | 🔄进行中 |
| **[抖音完整方案](./docs/DOUYIN_FULL_PLAN.md)** | 架构、蓝图、反检测、IP方案 | 📋参考 |
| **[IP切换指南](./docs/IP_SWITCH_GUIDE.md)** | 代理IP配置方案 | 📋参考 |
| **[选择器手册](./docs/DOUYIN_SELECTORS.md)** | data-e2e选择器对照 | 📋参考 |

---

## 📊 当前状态

### 阶段进度

| 阶段 | 内容 | 状态 |
|------|------|------|
| A | Chrome CDP直连 + 原子操作 + 账号切换 | ✅ 已完成 |
| B | Camoufox集成 + 多浏览器内核 | 🔄 进行中 |
| C | 鼠标轨迹 + 语料库完善 | 📋 规划中 |
| D | 小红书/知乎完整支持 | 📋 规划中 |

### 账号状态

| 账号 | 平台 | 浏览器 | 状态 |
|------|------|--------|------|
| douyin_01 | 抖音 | Chrome | ✅ 已登录 |
| douyin_02 | 抖音 | Chrome | ⏸ 待登录 |
| douyin_camo01 | 抖音 | Camoufox | 🔄 配置中 |
| douyin_camo02 | 抖音 | Camoufox | 🔄 配置中 |
| xhs_01 | 小红书 | Chrome | ⏸ 待注册 |
| zhihu_01 | 知乎 | Chrome | ⏸ 待注册 |

### 蓝图状态

| 蓝图 | 步骤数 | 状态 |
|------|--------|------|
| douyin_browse_v2（日常浏览） | 11步 | ✅ 活跃 |
| douyin_search_browse（搜索浏览） | 7步 | ✅ 活跃 |
| douyin_comment_interact（评论互动） | 8步 | ✅ 活跃 |

---

## 🏗️ 项目架构

```
用户指令/定时触发
       ↓
蓝图引擎 → 原子操作库（18操作）
       ↓
账号切换器（Profile切换 / Cookie注入）
       ↓
┌──────────────┬──────────────┐
│   Chrome     │   Camoufox   │
│   端口9222   │   端口9301   │
└──────────────┴──────────────┘
       ↓
   抖音/小红书/知乎
```

---

## ⚠️ 当前卡点：Camoufox

Camoufox（Firefox内核反检测浏览器）集成遇到以下问题：

1. **问题**：`properties.json` 路径查找错误
2. **已修复**：移除了显式 `executable_path` 配置
3. **待验证**：重新启动验证

**下一步**：
```bash
# 重新启动Camoufox
python scripts/camoufox_manager.py --launch douyin_camo01
```

---

## 📦 迁移打包

如需迁移项目，完整打包以下内容：

```bash
# 打包命令
rsync -av --exclude='profiles/*/Cache' \
      --exclude='logs/*.log' \
      ~/matrix/ /path/to/backup/
```

详见 [PROJECT_OVERVIEW.md - 迁移方案](./docs/PROJECT_OVERVIEW.md#九迁移方案)

---

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.13+ |
| pip | patchright, camoufox, pyyaml |
| Chrome | 最新版 |
| 磁盘 | 10GB+ |

**Python路径**：
```
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3
```

---

## 🔧 关键命令

```bash
# 账号切换
python scripts/switch_account.py --list                    # 列出账号
python scripts/switch_account.py --status                  # 查看状态
python scripts/switch_account.py --method profile --target douyin_01 --port 9222

# 执行蓝图
python scripts/task_engine.py --blueprint douyin_browse_v2 --account douyin_01

# Camoufox
python scripts/camoufox_manager.py --launch douyin_camo01  # 启动
python scripts/camoufox_manager.py --verify douyin_camo01  # 验证登录
python scripts/camoufox_manager.py --export douyin_camo01   # 导出Cookie
```

---

## 📁 目录结构

```
~/matrix/
├── docs/                 # 文档
├── scripts/              # 核心脚本
│   ├── douyin_ops.py    # 原子操作库
│   ├── cdp_connector.py # CDP连接器
│   ├── switch_account.py # 账号切换
│   └── camoufox_manager.py # Camoufox管理
├── blueprints/           # 任务蓝图
├── config/               # 配置
├── data/                 # 数据（数据库+Cookie）
├── profiles/             # 浏览器Profile
├── corpus/               # 语料库
└── logs/                # 日志
```

---

## 📞 联系方式

- **项目负责人**: ghai
- **项目目录**: ~/matrix/
- **核心文档**: ~/matrix/docs/PROJECT_OVERVIEW.md

---

**祝使用愉快！**

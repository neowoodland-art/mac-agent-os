# Matrix 系统文档索引

> 版本: v5.3 | 最后更新: 2026-06-13
> 新机器部署请先看本文档，按序号阅读

---

## 一、新机器部署（必读）

| # | 文档 | 说明 |
|---|------|------|
| 1 | `init_matrix.sh` | **一键部署脚本** — 检测环境→修复→启动 Dashboard |
| 2 | `config_template/accounts.yaml` | 账号配置模板（含身份共享规范） |
| 3 | `config_template/profiles.json` | 人设数据模板 |
| 4 | `config_template/schedule.yaml` | 定时任务配置模板 |
| 5 | `config_template/ai.yaml` | AI 评论生成配置模板 |
| 6 | `start_dashboard.sh` | Dashboard 启停脚本 |
| 7 | `fix_dashboard_launchd.sh` | launchd plist 修复脚本 |

## 二、核心文档

| # | 文档 | 说明 |
|---|------|------|
| 8 | `README.md` | **项目总览** — 功能、命令、架构 |
| 9 | `TOOL.md` | **工具说明** — 版本、前置依赖、文件结构 |
| 10 | `MODULE.md` | **模块架构** — 系统层级、文件依赖 |
| 11 | `docs/MC_COMMAND_REFERENCE.md` | **命令参考手册** — 所有 CLI 命令详解 |
| 12 | `docs/MATRIX_V5_GUIDE.md` | **v5 使用指南** — 完整操作指南 |
| 13 | `docs/CORPUS_V2_PLAN.md` | 语料库架构升级方案 v2.0 |

## 三、配置说明

| # | 文件 | 说明 |
|---|------|------|
| 14 | `accounts_registry.yaml` | 账号注册表（联邦同步用） |
| 15 | `config/accounts.yaml`（agent-local） | 本地账号配置 |
| 16 | `config/sms.yaml` | 短信 API 配置 |
| 17 | `config/ai.yaml` | AI 评论生成配置 |
| 18 | `config/schedule.yaml` | 定时任务配置 |
| 19 | `corpus/douyin.yaml` | 抖音语料库（33条） |
| 20 | `corpus/xiaohongshu.yaml` | 小红书语料库（31条） |

## 四、蓝图清单

| # | 蓝图 | 平台 | 步骤 | 用途 |
|---|------|------|------|------|
| 21 | `douyin_daily` | 🎵 | 23步 | 日常养号（随机浏览+点赞+收藏+评论） |
| 22 | `douyin_active_v1` | 🎵 | 27步 | 高活跃养号 |
| 23 | `douyin_comment` | 🎵 | 5步 | 定向评论（给链接→打开→评论） |
| 24 | `douyin_search` | 🎵 | 14步 | 搜索浏览（搜关键词→随机浏览+互动） |
| 25 | `douyin_collect` | 🎵 | 5步 | 信息采集（搜博主→采集主页信息） |
| 26 | `douyin_reply` | 🎵 | 5步 | 作者回复（打开自己视频→读评论→回复） |
| 27 | `douyin_read_profile` | 🎵 | 9步 | 读取抖音主页信息 |
| 28 | `xhs_daily` | 📕 | 17步 | 小红书日常养号 |
| 29 | `xhs_active_v1` | 📕 | 26步 | 小红书高活跃养号 |
| 30 | `xiaohongshu_read_profile` | 📕 | 8步 | 读取小红书主页信息 |

## 五、原子操作

| # | 操作 | 说明 |
|---|------|------|
| 31 | `goto_home` | 导航到首页 |
| 32 | `wait_watch` | 等待观看（随机5-12秒） |
| 33 | `like` | 点赞 |
| 34 | `collect` | 收藏 |
| 35 | `post_comment` | 发表评论（含@corpus占位符替换） |
| 36 | `open_video` | 打开视频（双击卡片） |
| 37 | `next_video` | 切换到下一个视频 |
| 38 | `search` | 搜索关键词 |
| 39 | `scroll_feed` | 滚动信息流 |
| 40 | `goto_profile` | 进入个人主页（采集全部字段） |
| 41 | `read_my_comments` | 读当前视频评论区 |
| 42 | `reply_comment` | 回复评论 |
| 43 | `set_account_id` | 设置账号上下文（人设/语料匹配用） |

## 六、旧文档（已归档，仅供参考）

```
docs/ARCHITECTURE_FULL.md
docs/BASE_CONVENTIONS.md
docs/REFACTOR-PLAN.md
docs/REPAIR_PLAN.md
docs/SYSTEM_ARCHITECTURE.md
docs/PROJECT_OVERVIEW.md
docs/ANTI-DETECTION-PLAN.md
（以上为 v4.x 旧文档，内容已过时）
```

---

## 新机器部署步骤

```bash
# 1. 拉取代码
cd ~/workbuddy-agent-os/agent-sync
git pull

# 2. 运行初始化脚本（自动检测环境）
bash 05_tools/07_matrix/init_matrix.sh

# 3. 重启 Dashboard
launchctl kickstart -k gui/$(id -u)/com.agentos.dashboard

# 4. 浏览器打开 http://localhost:9988
#    左侧「矩阵系统」→「身份与账号」→ 确认账号列表
```

如果 Dashboard 无法启动，单独修复：
```bash
bash 05_tools/07_matrix/fix_dashboard_launchd.sh
```

## 关键变更说明（v5.0 → v5.3）

- **身份共享**：同手机号共用同一浏览器指纹（identity_dir=phone_手机号）
- **引擎重构**：按身份分组→同浏览器多平台→不同组错峰启动
- **@corpus 恢复**：蓝图中的 @corpus 占位符自动替换为真实评论
- **蓝图平台标记**：所有蓝图名称带平台前缀（抖音-日常养号/小红书-日常养号）
- **清除登录**：每个平台可单独清除登录状态（不影响同身份其他平台）
- **批量执行**：账号不默认勾选、蓝图显示全部带平台标签

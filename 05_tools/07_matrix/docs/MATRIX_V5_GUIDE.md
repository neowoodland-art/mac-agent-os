# Matrix 矩阵养号系统 v5.0 使用文档

> 最后更新: 2026-06-11
> 适用版本: v5.0（PlatformOps 架构）
> 多机同步: Git + 坚果云

---

## 一、总体架构

```
mc（统一 CLI 入口）
  │
  ├─ mc run → mc/engine.py（纯调度层，~300行）
  │   └─ PlatformOps.execute()
  │       ├── DouyinOps（抖音，20+ 操作，platform_ops 接口）
  │       └── XhsOps（小红书，16 操作，ops/xhs_ops.py）
  │
  ├─ mc account → matrix_mgmt.py（账号管理）
  ├─ mc blueprint → matrix_mgmt.py（蓝图管理）
  ├─ mc corpus → mc/corpus.py（语料库）
  └─ mc status → cli.py（状态查询）
```

### 代码 vs 数据

| | 路径 | 共享方式 |
|---|---|---|
| 代码/蓝图 | `agent-sync/05_tools/07_matrix/` | Git 同步 |
| 账号配置 | `agent-local/tools/matrix/config/accounts.yaml` | 本机独立 |
| 浏览器指纹 | `agent-local/tools/matrix/identities/{name}/` | 本机独立 |
| 登录态 | `agent-local/tools/matrix/identities/{name}/user_data/` | 本机独立 |
| 联邦状态 | `cross_machine/data/matrix/{uid}.json` | Git 同步 |

---

## 二、新机部署

```bash
# 1. 拉取代码
cd ~/workbuddy-agent-os/agent-sync
git pull

# 2. 运行安装脚本（建目录 + 装依赖 + 配置）
bash 05_tools/07_matrix/install.sh

# 3. 确认 Python 环境
# mc 会自动检测 Python，或设置环境变量：
export AGENTOS_PYTHON=~/.workbuddy/binaries/python/envs/agent-os/bin/python3

# 4. 检查可用账号
cd 05_tools/07_matrix && ./mc account list
```

---

## 三、账号管理

### 新建账号身份

```bash
# 创建新身份（生成 BrowserForge 指纹）
python scripts/create_identity.py --name douyin_new --platform douyin

# 首次登录（浏览器打开，扫码/短信登录）
./mc account login douyin_new
```

### 同步已有账号（跨机迁移）

```bash
# 旧机器导出
./mc account export    # → 生成压缩包

# 新机器导入
./mc account import <path_to_export.tar.gz>
```

---

## 四、cli 命令参考

### 养号执行

```bash
# 单账号单轮（测试用）
./mc run --accounts douyin_test --blueprints douyin_active_v1 --rounds 1

# 多账号并行
./mc run --accounts douyin_test,douyin_133 --blueprints douyin_active_v1 --rounds 3

# 混合多蓝图（每轮随机选）
./mc run --accounts douyin_test --blueprints douyin_active_v1,douyin_browse_v2 --rounds 3 --mix

# 指定小红书
./mc run --accounts xhs_01 --blueprints xhs_active_v1 --rounds 2

# 完整参数
./mc run --accounts A,B --blueprints X,Y --rounds 3 --mix --interval 45-90 --engine auto
```

### 账号管理

```bash
./mc account list              # 列表（含登录态）
./mc account login <name>      # 首次登录
./mc account status [name]     # 查看状态
./mc account export            # 导出
./mc account import <path>     # 导入
```

### 蓝图管理

```bash
./mc blueprint list            # 列表
./mc blueprint show <name>     # 详情
```

### 状态查询

```bash
./mc status all                # 全局状态
./mc status accounts           # 账号列表
./mc status browsers           # 浏览器进程
```

### 旧版兼容

旧 `matrix.py` 仍可用但标记 deprecated。对照表：

| 旧命令（matrix.py） | 新命令（mc） |
|---|---|
| `python matrix.py account list` | `./mc account list` |
| `python matrix.py account login X` | `./mc account login X` |
| `python matrix.py nurture run -a X -r 10` | `./mc run --accounts X --rounds 10 ...` |
| `python matrix.py status all` | `./mc status all` |
| `python matrix.py config blueprint list` | `./mc blueprint list` |

---

## 五、蓝图说明

### 抖音蓝图

| 蓝图 | 步骤 | 说明 |
|------|------|------|
| `douyin_active_v1` | 27步 | 浏览×6 + 点赞×4 + 评论×2 + 收藏×1 + 搜索×2 |
| `douyin_browse_v2` | 11步 | 轻量浏览+随机点赞 |
| `douyin_nurture_v1` | 8步 | 搜索→浏览→点赞→收藏→切换 |
| `douyin_search_browse` | 7步 | 搜索→浏览→点赞 |
| `douyin_comment_interact` | 8步 | 浏览→打开评论区→发评论 |

### 小红书蓝图

| 蓝图 | 步骤 | 说明 |
|------|------|------|
| `xhs_active_v1` | 26步 | 浏览×5 + 点赞×5 + 搜索×2 + 收藏×2 + 评论×1 + 关注×1 |
| `xiaohongshu_nurture_v2` | 11步 | 浏览→点击→点赞→收藏→搜索→关注 |

### 蓝图格式

```json
{
  "id": "蓝图唯一ID",
  "name": "显示名称",
  "platform": "douyin 或 xiaohongshu",
  "description": "说明",
  "steps": [
    {"step_id": 1, "op": "操作名", "args": {}},
    ...
  ]
}
```

**抖音可用操作**: goto_home, like, collect, follow, open_comments, close_comments, post_comment, next_video, prev_video, search, wait_watch, scroll_feed, open_video, wait, goto_url, go_back

**小红书可用操作**: xhs_goto_home, xhs_browse, xhs_scroll_feed, xhs_click_note, xhs_like, xhs_collect, xhs_comment, xhs_follow, xhs_search, xhs_goto_profile, xhs_read_nickname, xhs_read_user_id, xhs_read_following, xhs_read_fans, xhs_read_likes, xhs_read_bio

---

## 六、自动化任务

### 每日养号

```bash
# 完整执行
bash scripts/nurture_daily.sh

# 仅查看命令（不执行）
bash scripts/nurture_daily.sh --dry

# 仅跑第1组
bash scripts/nurture_daily.sh --group 1
```

### 定时执行（cron）

```cron
# 每天 9:00 和 21:00 执行
0 9,21 * * * cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix && bash scripts/nurture_daily.sh >> /tmp/nurture_daily.log 2>&1
```

### 定时调度器（旧版兼容）

```bash
python scripts/task_scheduler.py
```

---

## 七、多账号并行

`mc run` 原生支持多账号并行。每个账号启动独立 Camoufox 浏览器，窗口自动错位：

| 账号索引 | 窗口位置 | 屏幕区域 |
|----------|---------|---------|
| 0 | (30, 30) | 左上 |
| 1 | (400, 30) | 中上 |
| 2 | (800, 30) | 右上 |
| 3 | (30, 450) | 左下 |
| 4 | (400, 450) | 中下 |
| 5 | (800, 870) | 右下 |

```bash
# 3 个抖音同时跑
./mc run --accounts douyin_test,douyin_133,douyin_133_2 --blueprints douyin_active_v1 --rounds 3
```

---

## 八、跨机器同步流程

```bash
# 主机器修改后
cd ~/workbuddy-agent-os/agent-sync
git add 05_tools/07_matrix/
git commit -m "Matrix v5.0 更新"
git push

# 其他机器
cd ~/workbuddy-agent-os/agent-sync
git pull
bash 05_tools/07_matrix/install.sh   # 如需要重建本地目录
```

**不同步的内容**（各机器独立）：
- `agent-local/tools/matrix/config/accounts.yaml` — 账号配置
- `agent-local/tools/matrix/identities/` — 浏览器指纹 + 登录态
- `agent-local/tools/matrix/logs/` — 运行日志

---

## 九、v5.0 变更说明

### 新增

- `mc` 统一 CLI（替代 `matrix.py`）
- `ops/_base.py` — PlatformOps 基类 + OpResult 结构化结果
- `ops/xhs_ops.py` — 小红书 16 个原子操作
- `mc/runlog.py` — 结构化运行日志（JSONL）
- `mc/engine.py` — 重构引擎（～300行，原 775行）
- `blueprints/douyin_active_v1.json` — 抖音高活跃蓝图
- `blueprints/xhs_active_v1.json` — 小红书高活跃蓝图
- `docs/MC_COMMAND_REFERENCE.md` — 命令参考手册

### 改进

- `douyin_ops.py` 实现 PlatformOps 接口，每个操作返回 OpResult
- `_click_selector` 增加 JS evaluate fallback（穿透 Shadow DOM）
- `goto_home` 增加 commit 模式 + 强制继续（不因 video 未就绪阻塞）
- 进入视频模式：从卡片 `data-aweme-id` 提取视频 ID 直接导航（/video/{id}）
- 视频页双击 video 获取焦点（原代码约定）
- post_comment 用 pbcopy + Meta+V（Draft.js 兼容）
- 所有 `force=True` 跳过 Playwright 可点击性检查
- 硬编码路径修复（Python、用户名）
- `.gitignore` 排除临时蓝图和一次性脚本

### 废弃

- `matrix.py` — 标记 deprecated（用 mc 替代）
- `yanghao_runner.py` — 功能合并到 mc
- `task_engine.py` — 功能合并到 mc/engine.py
- `camoufox_manager.py` / `camoufox_server.py` — 被 cdp_connector.py 取代
- `browser_manager.py` / `browser_keepalive.py` — mc/browser.py 取代
- 25+ 调试脚本 — 移入 `_archive/`

---

## 十、故障排查

### 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 页面加载超时 | Camoufox 下 douyin.com 使用 `commit` 模式 | 自动 fallback，强制继续 |
| like/collect 失败 | Shadow DOM 影响 Playwright locator | 自动 fallback 到 JS evaluate |
| post_comment 失败 | 评论区无标准输入框 DOM | 不依赖选择器，pbcopy + Meta+V 硬发 |
| 多账号窗口重叠 | 未设置 window_position | 自动按索引分配错位 |
| "代理"行消失 | 账号 config.yaml 中 proxy 被注释 | 取消注释恢复代理 |

### 调试命令

```bash
# 查看运行日志
cat /tmp/matrix_step_douyin_test.log

# Peekaboo 截图观察
peekaboo image

# 原子操作诊断
python scripts/diagnose_ops.py
```

### 版本信息

当前所有文档统一版本：v5.0.0。文件清单：

- `MODULE.md` — v5.0.0
- `TOOL.md` — v5.0
- `mc/__main__.py` — v1.0.0（mc CLI 版本）
- `docs/MC_COMMAND_REFERENCE.md` — v5.0
- `blueprints/*.json` — 每个蓝图独立版本
- `install.sh` — v4.0（未变）

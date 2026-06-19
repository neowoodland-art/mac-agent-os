# AgentOS 联邦系统 — 全量审计报告 v1.0

> 审计日期: 2026-06-19 | 基于代码实际读取，无推断无虚构
> 审计范围: `05_tools/07_matrix/` 全部代码 + `05_tools/10_dashboard/` 关键代码 + `ORACLE.yaml`

---

## 一、项目状态总览

### 1.1 三台机器角色（来自 ORACLE.yaml）

| 机器 | IP (Tailscale) | 角色 | Dashboard Web | 职责 |
|:-----|:--------------|:-----|:-------------|:------|
| chengzigedeAir | 100.111.43.6 | **master** | ✅ localhost:9988 | 运行Dashboard + 养号 + 知识库 |
| 5kechengdeAir | 100.72.182.121 | worker | ❌ 不跑 | 养号工人机器 |
| 7kecheng | 100.65.35.28 | worker | ❌ 不跑 | 养号工人机器（大量账号） |

**Dashboard 只能通过 chengzigedeAir:9988 访问。** 用户在任意电脑浏览器打开 `http://100.111.43.6:9988` 即可操作。

### 1.2 本机身份（7个）

| 身份目录 | 所属账号 | 跨平台 |
|:---------|:---------|:-------|
| `phone_15370103682` | douyin_test + xhs_01 | ✅ 同身份跨平台 |
| `douyin_133` | douyin_133 | ❌ 仅抖音 |
| `douyin_133_2` | douyin_133_2 | ❌ 仅抖音 |
| `douyin_134` | douyin_134 | ❌ 仅抖音 |
| `douyin_test` | douyin_test | ❌ 仅抖音 |
| `test_login` | (测试) | ❌ |
| `xhs_01` | xhs_01 | ❌ |

**关键发现**: `phone_15370103682` 是唯一个真正"同身份跨平台"的身份——它的 identity_dir 同时绑定了 douyin_test + xhs_01。其他身份尚未启用跨平台模式。

### 1.3 命令执行链（从 Dashboard 到浏览器）

```
Dashboard → POST /api/ops/run            (routes/ops.py)
  → CommandBus.dispatch()                (services/command_bus.py)
    → MachineSession.send()
      → 本机: _send_local()
        → bash nurture_runner.sh          (services/nurture_runner.sh)
          → python -m mc run              (mc/cli.py → mc/run.py → mc/engine.py)
            → CDPConnector.launch()       (cdp_connector.py → Camoufox)
              → BatchEngine._run_acct_on_conn()
                → DouyinOps / XhsOps     (douyin_ops.py / ops/xhs_ops.py)
                  → step by step from JSON blueprint
      → 远程: _send_remote()
        → SSH command to remote machine
          → remote executes same mc run flow
```

---

## 二、CLI 体系

### 2.1 `mc`（当前主命令）

定义在: `mc/cli.py` | 入口: `python -m mc`

| 子命令 | 功能 | 代码位置 |
|:-------|:-----|:---------|
| `mc run --accounts=A --blueprints=B --rounds=N` | **批量执行引擎** | `mc/run.py` → `mc/engine.py` |
| `mc account list` | 账号列表 | `mc/cli.py:cmd_account()` |
| `mc account login <name>` | 登录 | → `login_identity.py` |
| `mc account status [name]` | 登录状态 | → `matrix_mgmt.py` |
| `mc account export/import` | 导入导出 | → `matrix_mgmt.py` |
| `mc blueprint list/show` | 蓝图管理 | → `matrix_mgmt.py` |
| `mc task comment --url=...` | 定向评论任务 | → `task_engine.py` |
| `mc corpus list/add/select` | 语料库管理 | → `mc/corpus.py` |
| `mc proxy list/test/set` | 代理管理 | 预留 |
| `mc sms config/test` | SMS 配置 | 预留 |
| `mc status all/accounts/browsers` | 全局状态 | `mc/cli.py` |

### 2.2 `matrix`（旧命令，仍可用但非主入口）

定义在: `matrix.py` | 功能类似于 mc，但接口更老

| 子命令 | 说明 |
|:-------|:------|
| `matrix account list` | 列出账号（读 accounts.yaml） |
| `matrix account create` | 创建新身份 |
| `matrix account login` | 首次登录 |
| `matrix nurture run` | 养号（不同于 mc run 的执行路径） |

### 2.3 其他工具

| 文件 | 说明 |
|:-----|:------|
| `guardd.py` | 系统守护进程：每60s检测孤儿浏览器/磁盘/超时/心跳 |
| `orchestrator.py` | 养号编排器（旧版，engine.py 已替代） |
| `yanghao_runner.py` | 养号运行器（旧版启动方式） |
| `task_engine.py` | `mc task` 调度的任务引擎 |
| `task_scheduler.py` | 定时任务调度器 |
| `atom_ops.py` | 旧版原子操作定义（已废弃，ops/ 已替代） |
| `nurture_blueprint.py` | 抖音养号步序列（Python定义，`nurture_loop` 使用） |
| `cdp_connector.py` | 浏览器连接管理器（Camoufox/Chrome） |
| `browser_utils.py` | GracefulBrowser 浏览器生命周期 |
| `browser_manager.py` | 浏览器管理器（旧版） |
| `collect_homepage_info.py` | 主页信息采集 |
| `collect_batch_runner.py` | 批量采集执行器 |
| `publish_video.py` | 视频发布 |
| `login_identity.py` | 身份登录入口 |
| `vision_bridge.py` | oMLX 视觉分析桥接（2026-06-19 新加） |
| `watch_session.py` | 会话监控（2026-06-19 测试用） |
| `auth_manager.py` | 认证管理 |
| `anti_detection.py` | 反检测工具 |
| `page_state.py` | 页面状态读取 |
| `step_by_step_v2.py` | 分步执行v2（旧版） |
| `step_by_step_v3.py` | 分步执行v3（旧版） |

---

## 三、蓝图系统

### 3.1 蓝图文件（14个 JSON）

位于: `05_tools/07_matrix/blueprints/`

| 蓝图 | 平台 | 步骤数 | 说明 |
|:-----|:------|:------|:-----|
| `douyin_daily` | douyin | 23 | 日常养号：浏览/点赞/收藏/评论循环 |
| `douyin_active_v1` | douyin | 27 | 高活跃养号：多浏览+多点赞+搜索+评论 |
| `douyin_comment` | douyin | 5 | 定向评论：goto_url → watch → comment |
| `douyin_comment_test` | douyin | 5 | 定向评论测试（硬编码URL） |
| `douyin_reply` | douyin | 5 | 回复评论：找到我的评论 → 回复 |
| `douyin_search` | douyin | 14 | 搜索+浏览：搜关键词 → 浏览 → 互动 |
| `douyin_search_browse` | douyin | 7 | 搜索浏览(简版) |
| `douyin_collect` | douyin | 5 | 信息采集：搜索 → 打开主页 → 采集 |
| `douyin_read_profile` | douyin | 9 | 读主页：昵称/抖音号/关注/粉丝/获赞 |
| `xhs_daily` | xiaohongshu | 17 | 小红书日常养号 |
| `xhs_active_v1` | xiaohongshu | 26 | 小红书高活跃 |
| `xiaohongshu_read_profile` | xiaohongshu | 8 | 小红书读主页 |
| `export_douyin_01_*` | douyin | 3 | 导出任务（custom ops） |
| `export_xhs_01_*` | xiaohongshu | 4 | 导出任务（custom ops） |

### 3.2 蓝图步骤格式

```json
{"step_id": 1, "op": "goto_url", "args": {"url": "@url"}}
```

**参数模板系统**（运行时替换）：
- `@url` → 从任务参数的 url 字段替换
- `@corpus` → 从语料库取文案
- `@keyword` → 从任务参数的 keyword 字段替换
- `@direction` → 评论方向（正面/提问/共鸣/感慨）
- `@scene` → 场景（first_comment/reply/repeat）
- `@comment_text` → 直接评论文本
- `@reply_text` → 回复文本

### 3.3 蓝图执行方式

**通过 `mc/engine.py` 的 `BatchEngine._run_acct_on_conn()`**：
```
1. 加载 JSON blueprint
2. 按 platform 创建 DouyinOps / XhsOps 实例
3. 导航到平台首页
4. 逐个执行步骤：ops.execute(op, args, step_id)
5. 参数替换由 _resolve_args() 处理
6. 每步间隔 1.5s
```

### 3.4 原生Python蓝图

除了 JSON，还有 `nurture_blueprint.py` 中的 `BLUEPRINT_NURTURE`（Python列表）：
```python
BLUEPRINT_NURTURE = [
    ("进入视频", op_enter_video, {}, 1.0),
    ("观看", op_watch, {}, 1.0),
    ("点赞", op_like, {}, 0.4),    # ← 概率
    ...
]
```
这个由 `nurture_loop()` / `nurture_daily.py` 使用。**注意这个和 JSON 蓝图是两套独立的执行路径。**

---

## 四、原子操作体系

### 4.1 当前实现（ops/ 目录）

```
ops/
├── _base.py          → PlatformOps 基类 + OpResult
├── xhs_ops.py         → XhsOps (16个操作)   ← 小红书
└── douyin/
    ├── __init__.py
    ├── browse.py       → 浏览类操作
    └── interact.py     → 互动类操作

douyin_ops.py            → DouyinOps (20个操作)   ← 抖音（另一套实现）
```

**注意**: 抖音有**两套**操作实现：
1. `douyin_ops.py` → 独立完整类（engine.py 当前使用的）
2. `ops/douyin/` → 拆分版（browse.py + interact.py，可能较新）

### 4.2 DouyinOps 支持的20个操作

| 操作 | 说明 |
|:-----|:------|
| goto_home | 回到首页 |
| goto_url | 跳转到指定URL |
| like | 点赞 |
| collect | 收藏 |
| follow | 关注 |
| open_comments | 打开评论区 |
| close_comments | 关闭评论区 |
| post_comment | 发表评论 |
| next_video | 下一个视频(ArrowDown) |
| prev_video | 上一个视频(ArrowUp) |
| search | 搜索关键词 |
| wait_watch | 等待+观看(随机时长) |
| scroll_feed | 滚动瀑布流 |
| open_video | 点开视频 |
| wait | 等待 |
| go_back | 返回 |
| goto_profile | 去用户主页 |
| read_profile_field | 读主页字段 |
| read_my_comments | 读我的评论 |
| reply_comment | 回复评论 |
| search_browse | 搜索+浏览 |

### 4.3 XhsOps 支持的16个操作

| 操作 | 说明 |
|:-----|:------|
| xhs_goto_home | 回到首页 |
| xhs_browse | 浏览(已在首页则跳过) |
| xhs_scroll_feed | 滚动瀑布流 |
| xhs_click_note | 点击笔记 |
| xhs_like | 点赞 |
| xhs_collect | 收藏 |
| xhs_comment | 评论 |
| xhs_post_comment | 发表评论 |
| xhs_follow | 关注 |
| xhs_search | 搜索 |
| xhs_goto_profile | 去用户主页 |
| xhs_read_nickname | 读昵称 |
| xhs_read_user_id | 读用户ID |
| xhs_read_following | 读关注数 |
| xhs_read_fans | 读粉丝数 |
| xhs_read_likes | 读获赞数 |
| xhs_read_bio | 读个人简介 |

### 4.4 平台操作基类接口

```python
class OpResult:
    op: str        # 操作名
    step_id: int   # 步骤编号
    success: bool
    detail: str    # 简短描述
    elapsed: float # 耗时(秒)
    error: str     # 失败原因

class PlatformOps(ABC):
    async def execute(self, op, args, step_id) -> OpResult  # 统一入口，自动重试
    async def _do_execute(self, op, args, step_id) -> OpResult  # 子类实现
```

---

## 五、命令分发系统

### 5.1 CommandBus (services/command_bus.py)

| 方法 | 功能 |
|:-----|:------|
| `CommandBus.dispatch(type, accounts, params)` | 统一入口，按机器分组 |
| `CommandBus.get_status(machine, account)` | 查询命令状态 |
| `CommandBus.get_all_machines_status()` | 所有机器聚合状态 |
| `CommandBus.cancel(run_id)` | 取消命令 |

**MachineSession** (每机器一个)：

| 方法 | 功能 |
|:-----|:------|
| `send(cmd)` | 本地→`_send_local` / 远程→`_send_remote` |
| `preflight()` | SSH可达? 活跃命令<3? 资源检查 |
| `poll(cmd)` | 轮询结果（本地读文件/远程SSH读取） |
| `cancel(cmd)` | 取消命令（本地pkill/远程SSH pkill） |
| `graceful_exit()` | 优雅退出+清理 |

### 5.2 结果文件格式

```
runtime/nurture/results/{run_id}.json
```

```json
{
  "run_id": "nurture_1234567890_douyin_test",
  "account": "douyin_test",
  "blueprint": "douyin_daily",
  "status": "completed",
  "hostname": "chengzigedeAir",
  "steps": {"total": 23, "success": 21, "failed": 2},
  "duration_secs": 452
}
```

---

## 六、配置文件体系

| 文件 | 用途 | 覆盖范围 |
|:-----|:------|:---------|
| `ORACLE.yaml`（根目录） | 宪法：机器定义/账号分配/任务计划/全局配置 | 三台机器只读 |
| `accounts_registry.yaml`（07_matrix/） | 账号注册表：每个账号的机器归属/平台/窗口位置 | 三台机器同步 |
| `config_template/accounts.yaml` | 账号配置模板 | 按需部署到 config/ |
| `config_template/sms.yaml` | SMS API 配置模板 | 按需部署到 scripts/config/ |
| `config_template/screen_layout.yaml` | UI 布局参数（评论框坐标等） | 按需部署 |
| `config_template/schedule.yaml` | 定时任务模板 | 按需部署 |
| `scripts/config/sms.yaml` | 实际运行的 SMS 配置 | 本机生效 |
| `scripts/config/schedule.yaml` | 实际运行的定时任务 | 本机生效 |
| `scripts/config/comment_corpus.yaml` | 评论语料库 | 本机生效 |

---

## 七、守护进程

| 进程 | 启动方式 | 功能 |
|:-----|:---------|:-----|
| `guardd` | launchd 守护 | 每60s检测：孤儿浏览器/磁盘<5GB/Dashboard存活/命令超时30min/浏览器数>3 |
| `Dashboard` | launchd 守护 (端口9988) | FastAPI Web服务 |
| `socks5-forwarder` | launchd 守护 (端口10800) | SOCKS5 代理转发 |

guardd 检测结果写入 `runtime/guardd/events.log`，心跳推送到 `localhost:9988/api/push/heartbeat`。

---

## 八、语料库体系

| 文件 | 格式 | 用途 |
|:-----|:------|:------|
| `corpus/douyin.yaml` | YAML | 抖音语料（已定义） |
| `corpus/xiaohongshu.yaml` | YAML | 小红书语料（已定义） |
| `scripts/config/comment_corpus.yaml` | YAML | 运行时评论语料库（实际使用） |

`CorpusManager` 类 (`mc/corpus.py`) 提供：
- `get_comment_for_video(title, direction, account_id)` → 根据视频标题和方向选文案
- `get_comment_for_scene(persona, scene, keyword, round_num)` → 按场景选文案

---

## 九、关键依赖版本

| 组件 | 版本 | 路径 |
|:-----|:------|:------|
| Python | 3.13.12 | `~/.workbuddy/binaries/python/envs/agent-os/bin/python3` |
| Camoufox | 0.4.11 | agent-os venv |
| Playwright | 1.58.0 | agent-os venv |
| FastAPI | (在 requirements.txt) | agent-os venv |
| uvicorn | (在 requirements.txt) | agent-os venv |

---

## 十、代码清理建议

以下文件经检查为**废弃/归档状态**，不应再被主动使用：

| 文件 | 被谁取代 | 建议处理 |
|:-----|:---------|:--------|
| `matrix.py` 整体 | `mc/` | 归档到 `archive/` |
| `atom_ops.py` | `ops/_base.py` + `DouyinOps`/`XhsOps` | 归档 |
| `nurture_blueprint.py ` 的 `BLUEPRINT_NURTURE` | `blueprints/*.json` + `engine.py` | 保留（nurture_loop 仍在用） |
| `yanghao_runner.py` | `mc run` 命令 | 归档 |
| `orchestrator.py` | `mc/engine.py` | 归档 |
| `step_by_step_v2.py` / `step_by_step_v3.py` | `engine.py` | 归档 |
| `archive/` 内全部 | (已在 archive) | 保持不动 |
| `browser_manager.py` | `cdp_connector.py` | 保留（CommandBus 可能引用） |
| `xhs_session_test.py` / `watch_session.py` | 测试文件 | 删除或归档 |

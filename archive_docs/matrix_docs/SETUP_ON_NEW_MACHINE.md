# 新机部署完整指南

> **目标**: 在另一台 macOS (Apple Silicon) 机器上完整部署 Matrix 养号系统
> **预估时间**: 30-60 分钟（不含首次登录各平台）
> **适用版本**: v4.2+

---

## 目录

1. [环境准备](#1-环境准备)
2. [同步代码](#2-同步代码)
3. [安装依赖](#3-安装依赖)
4. [配置账号](#4-配置账号)
5. [首次登录](#5-首次登录)
6. [运行养号](#6-运行养号)
7. [日常运维](#7-日常运维)
8. [迁移账号（从旧机）](#8-迁移账号从旧机)
9. [故障排查](#9-故障排查)

---

## 1. 环境准备

| 项目 | 要求 | 检查命令 |
|------|------|---------|
| macOS | Apple Silicon (M1/M2/M3) | `uname -m` → `arm64` |
| Python | 3.10+ | `python3 --version` |
| Git | 已安装 | `git --version` |
| Homebrew | 可选，用于安装工具 | `brew --version` |
| 磁盘空间 | 5GB+ | `df -h ~` |

如果系统中没有 Python 3.10+，先安装：

```bash
# 通过 Homebrew
brew install python@3.13

# 或使用 pyenv
brew install pyenv
pyenv install 3.13.12
```

---

## 2. 同步代码

```bash
# 设定工作目录（建议与主机构一致）
export AGENT_SYNC="$HOME/workbuddy-agent-os/agent-sync"
export AGENT_LOCAL="$HOME/workbuddy-agent-os/agent-local"

# 克隆仓库（请先在本机配置好 Gitee SSH）
git clone git@gitee.com:babycalf/mac-agent-os.git "$AGENT_SYNC"

# 切换到 matrix 目录
cd "$AGENT_SYNC/05_tools/07_matrix"
```

> **网络说明**：仓库托管在 Gitee（国内加速），如主仓库不可达请联系维护者获取同步方式。
> 本系统使用坚果云管理 agent-local 数据（非 Git），详见下文第 8 节。

---

## 3. 安装依赖

### 3.1 一键安装

```bash
cd "$AGENT_SYNC/05_tools/07_matrix"
bash install.sh
```

此脚本会：
- 创建 `agent-local/tools/matrix/` 目录骨架
- 生成 `local.yaml`（本机路径配置文件）
- 安装 Python 依赖 (`pip install -r requirements.txt`)
- 安装 Playwright Chromium
- 检查账号配置

### 3.2 手动安装（如果 install.sh 失败）

```bash
# 建目录
mkdir -p "$AGENT_LOCAL/tools/matrix"/{config,data/cookies,profiles,logs,screenshots}
mkdir -p "$AGENT_LOCAL/tools/matrix/data/camoufox_pids"
mkdir -p "$AGENT_LOCAL/tools/matrix/backups/cookies"
mkdir -p "$AGENT_LOCAL/tools/matrix/accounts"/{douyin_01,douyin_02,douyin_camo01}/{content/{raw,edited,thumbnails},scripts/{drafts,posted},publish/{queue,published},backup/cookies}

# 安装 Python 包
pip install -r "$AGENT_SYNC/05_tools/07_matrix/requirements.txt"

# 安装 Playwright 浏览器
python -m patchright install chromium

# 初始化数据库
cd "$AGENT_SYNC/05_tools/07_matrix/scripts"
python init_db.py

# 生成 local.yaml
cat > "$AGENT_SYNC/05_tools/07_matrix/local.yaml" << EOF
matrix:
  local_data_root: $AGENT_LOCAL/tools/matrix
EOF
```

### 3.3 安装 Camoufox

Camoufox 是养号系统的核心引擎（Firefox 内核反检测浏览器）。

```bash
# 安装 Python 包
pip install camoufox

# 下载 Camoufox 浏览器二进制（约 200MB）
python -m camoufox fetch

# 验证安装
python -c "import camoufox; print(camoufox.__version__)"
```

安装完成后，Camoufox 可执行文件位于：
```
~/Library/Caches/camoufox/Camoufox.app/Contents/MacOS/camoufox
```

### 3.4 依赖清单

| 包 | 版本要求 | 用途 |
|----|---------|------|
| `camoufox` | ≥0.4.11 | Firefox 内核反检测浏览器 |
| `patchright` | ≥1.40 | Playwright 浏览器自动化 |
| `browserforge` | latest | 浏览器指纹生成 |
| `PyYAML` | ≥5.0 | YAML 配置解析 |
| `aiofiles` | latest | 异步文件操作 |
| `Pillow` | latest | 截图处理 |

完整清单见 `requirements.txt`。

---

## 4. 配置账号

### 4.1 复制配置模板

```bash
cp "$AGENT_SYNC/05_tools/07_matrix/config_template/accounts.yaml" \
   "$AGENT_LOCAL/tools/matrix/config/accounts.yaml"
```

### 4.2 编辑账号配置

编辑 `$AGENT_LOCAL/tools/matrix/config/accounts.yaml`，填入本机账号信息：

```yaml
accounts:
  # ── 抖音账号 ──
  - id: douyin_01
    platform: douyin
    phone: "185xxxx8610"          # 改为本机手机号
    identity_dir: identities/douyin_01_camo   # 身份目录名
    window: [702, 783]            # 窗口尺寸
    window_position: [0, 0]       # 屏幕坐标（多账号防重叠）
    enabled: true

  - id: douyin_02
    platform: douyin
    phone: "185xxxx3366"
    identity_dir: identities/douyin_02_camo
    window: [702, 783]
    window_position: [400, 0]     # 紧贴 douyin_01 右侧
    enabled: true

  - id: douyin_camo01
    platform: douyin
    phone: "153xxxx8283"
    identity_dir: identities/douyin_camo01
    window: [702, 783]
    window_position: [750, 0]     # 再往右偏移
    enabled: true

  # ── 小红书账号（共享身份目录）──
  - id: xhs_01
    platform: xiaohongshu
    phone: "185xxxx8610"          # 与 douyin_01 同手机号
    identity_dir: identities/douyin_01_camo  # ← 共享！
    window: [702, 783]
    window_position: [0, 800]     # 抖音下方
    enabled: true

  - id: xhs_02
    platform: xiaohongshu
    phone: "185xxxx3366"
    identity_dir: identities/douyin_02_camo  # ← 共享！
    window: [702, 783]
    window_position: [400, 800]
    enabled: true

  - id: xhs_03
    platform: xiaohongshu
    phone: "153xxxx8283"
    identity_dir: identities/douyin_camo01   # ← 共享！
    window: [702, 783]
    window_position: [750, 800]
    enabled: true
```

**关键规则**：
- `identity_dir` 决定浏览器指纹和登录态目录，同手机号不同平台应共用同一目录
- 共享 identity_dir 时，**Cookie 保护**由 `cookie_manager.py` 自动处理
- `window_position` 控制浏览器启动位置，避免窗口重叠

### 4.3 配置代理（可选）

如需为每个账号配置独立静态代理 IP，在账号配置中添加 `proxy` 字段：

```yaml
  - id: douyin_01
    ...
    proxy: socks5://127.0.0.1:1080   # 可选
```

详细 IP 方案见 [IP_SWITCH_GUIDE.md](./IP_SWITCH_GUIDE.md)。

---

## 5. 首次登录

新机首次需要手动登录各平台账号，建立登录态。

### 5.1 单账号首次登录

```bash
cd "$AGENT_SYNC/05_tools/07_matrix/scripts"
python matrix.py account login douyin_01
```

此命令会：
1. 启动 Camoufox 并加载对应 identity
2. 打开抖音登录页面
3. 等待你手动扫码/短信登录
4. 登录完成后回车确认 **→ session cookie 自动保存**

### 5.2 验证登录状态

```bash
python matrix.py account status douyin_01
# → 应显示 "已登录" 及 cookie session id

python matrix.py account status   # 查看所有账号
```

### 5.3 批量首次登录的小技巧

由于抖音和小红书共享 identity_dir，**先登录抖音，小红书自动复用**：

```
douyin_01 登录完成 → xhs_01 自动可用
douyin_02 登录完成 → xhs_02 自动可用
douyin_camo01 登录完成 → xhs_03 自动可用
```

所以只需要登录 3 次，覆盖 6 个账号。

---

## 6. 运行养号

### 6.1 快速测试

先单账号跑一圈，验证系统是否正常：

```bash
cd "$AGENT_SYNC/05_tools/07_matrix/scripts"

# 抖音单账号 2 轮（约 2-3 分钟）
python matrix.py nurture run -a douyin_01 -r 2
```

观察日志 `/tmp/matrix_nurture_douyin_01.log`，确认：
- Camoufox 浏览器启动成功
- 进入播放页正常
- 能滑视频
- 评论正常

### 6.2 多账号并发

```bash
# 抖音三账号并行 10 轮（约 15-20 分钟）
python matrix.py nurture run \
    -a douyin_01 -a douyin_02 -a douyin_camo01 \
    -r 10 --no-daemon
```

各账号日志 `/tmp/matrix_nurture_{account}.log`，实时查看：

```bash
tail -f /tmp/matrix_nurture_douyin_01.log
```

### 6.3 全自动主控脚本

```bash
# 抖音 → 小红书 完整流程
bash "$AGENT_SYNC/05_tools/07_matrix/scripts/nurture_master.sh"
```

主控脚本执行顺序：
1. Phase 0: 全量 Cookie 备份
2. Phase 1: 抖音 3 账号并行（--no-daemon，完成后关浏览器）
3. 休息 30 秒
4. Phase 2: 小红书 3 账号并行

日志输出：
- 阶段日志：`/tmp/nurture_master/{douyin|xhs}_phase.log`
- 各账号日志：`/tmp/matrix_nurture_{account}.log`

### 6.4 定时任务

使用 cron 或 macOS launchd 设置每日自动运行：

```bash
# crontab 示例（每天 10:00）
0 10 * * * /bin/bash /path/to/nurture_master.sh >> /tmp/nurture_daily.log 2>&1
```

---

## 7. 日常运维

### 7.1 清理残留锁文件

养号异常退出后，Camoufox 可能留下 `.parentlock` 文件，导致下次启动失败：

```bash
# 清理所有 identity 的锁文件
find "$AGENT_LOCAL/tools/matrix/identities" -name ".parentlock" -delete
```

建议在每次运行前执行此命令。

### 7.2 Cookie 备份与恢复

备份位置：`$AGENT_LOCAL/tools/matrix/backups/cookies/`

```bash
# 手动备份所有账号
python -c "
from matrix_modules.utils.cookie_manager import backup_all_identities
backup_all_identities(platform='manual', label='manual_backup')
"
```

### 7.3 查看执行报告

```bash
# 查看各账号最后一轮结果
for acct in douyin_01 douyin_02 douyin_camo01 xhs_01 xhs_02 xhs_03; do
  log="/tmp/matrix_nurture_${acct}.log"
  [ -f "$log" ] && echo "=== $acct ===" && grep "轮数:\|耗时:\|完成" "$log" | tail -2
done
```

### 7.4 更新代码

```bash
cd "$AGENT_SYNC"
git pull origin main
```

如果本地有未提交的修改：

```bash
git stash        # 暂存本地修改
git pull origin main
git stash pop    # 恢复本地修改
```

---

## 8. 迁移账号（从旧机）

如果需要将旧机器的已登录账号迁移到新机，有两种方式：

### 方式 A：全量身份目录迁移（推荐）

将旧机器 `agent-local/tools/matrix/identities/` 下的目录打包：

```bash
# 旧机器上打包
tar czf identities_backup.tar.gz \
  -C ~/workbuddy-agent-os/agent-local/tools/matrix/identities \
  douyin_01_camo douyin_02_camo douyin_camo01

# 通过 U 盘/网络传至新机

# 新机器上解压
tar xzf identities_backup.tar.gz \
  -C ~/workbuddy-agent-os/agent-local/tools/matrix/identities/
```

迁移后**可能需要重新登录**（取决于 Cookie 时效性）。

### 方式 B：坚果云同步

如果旧机和新机都安装了坚果云，可以通过坚果云同步 `agent-local` 目录（注意排除大文件）：

```
坚果云同步路径: ~/NutstoreCloudBridge/matrix-identities/
排除: *.parentlock, *.log
```

---

## 9. 故障排查

### 9.1 Camoufox 启动失败

```
错误: TargetClosedError / EPIPE
```

**原因**：`.parentlock` 残留 或 Playwright driver 崩溃

**解决**：
```bash
# 清理锁文件
find "$AGENT_LOCAL/tools/matrix/identities" -name ".parentlock" -delete

# 清理 Playwright 残留进程
pkill -f "playwright"
pkill -f "camoufox"
```

### 9.2 小红书页面刷挂起

```
日志卡在: "🔄 刷新瀑布流页面..."
```

**原因**：XHS Page.reload 超时后协程未正常退出

**解决**：
```bash
# kill 当前进程
# 清理锁文件后重跑
find ... -name ".parentlock" -delete
python matrix.py nurture run -a xhs_02 -r 10
```

### 9.3 小红书 QR 码拦截墙

```
日志显示: "🚫 QR码拦截墙（回退重试 1/3）"
```

**原因**：账号被平台标记为非常用登录环境

**解决**：系统会自动 3 轮回退重试，多数情况可自行恢复。
如果持续触发，尝试：
1. 手动打开浏览器在该账号下正常浏览几分钟
2. 清除 cookies 后重新登录
3. 检查代理 IP 是否与该账号常用地一致

### 9.4 抖音评论触发短信验证码

```
日志显示: "⏱️ SMS 验证码超时"
```

**原因**：抖音检测到异常评论行为，要求短信验证

**解决**：
- 暂时跳过评论（系统已自动跳过）
- 增加养号间隔（调大 `behavior.base_delay`）
- 换个评论内容

### 9.5 评论聚焦失败

```
日志显示: "⚠️ 所有聚焦方式均失败 (state=panel_open)"
```

**原因**：坐标偏移 / DOM 变化 / Draft.js 版本更新

**解决**：系统已自动跳过评论，不影响浏览养号。可尝试重新校准
（运行 `python calibrate_input.py` 重新采集坐标）。

### 9.6 日志太长，不清除旧记录

养号系统使用追加写日志，多次运行日志会混合。如需清理：

```bash
# 清理所有养号日志
rm -f /tmp/matrix_nurture_*.log
rm -f /tmp/nurture_master/*.log
```

---

## 附录：养号行为参数

行为参数可在 `identities/{name}/config.yaml` 中覆盖默认值：

```yaml
behavior:
  base_delay: 1.5              # 操作间隔(秒)
  delay_variance: 0.8          # 随机波动范围
  attention:
    distraction_chance: 0.05   # "分心"概率
    watch_duration: [4, 12]    # 观看时长(秒)
  round_break:
    min_break: 5               # 轮间最短休息(秒)
    max_break: 20              # 轮间最长休息(秒)
```

---

## 附录：关键文件索引

| 文件 | 说明 |
|------|------|
| `scripts/matrix.py` | 统一 CLI，所有操作的入口 |
| `scripts/nurture_master.sh` | 养号主控脚本 |
| `scripts/matrix_modules/runner.py` | 养号循环引擎 |
| `scripts/matrix_modules/behavior.py` | 行为参数化 |
| `scripts/matrix_modules/utils/cookie_manager.py` | Cookie 安全 |
| `scripts/ops/douyin/browse.py` | 抖音浏览操作 |
| `scripts/ops/douyin/interact.py` | 抖音交互操作 |
| `scripts/douyin_ops.py` | 抖音原子操作（旧方案） |
| `blueprints/douyin_browse_v2.yaml` | 抖音日常浏览蓝图 |
| `local.yaml` | 本机路径配置（每机独立） |

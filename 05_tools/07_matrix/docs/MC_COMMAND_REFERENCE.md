# mc 命令参考手册 — Matrix v5.2

> 统一 CLI 入口，替代旧版 matrix.py。
> 智能体通过 mc 命令调用 Matrix，不需要直接操作 Python 脚本。

---

## 安装

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix
chmod +x mc
# 可选：ln -s $(pwd)/mc /usr/local/bin/mc
```

Python 路径自动检测（AGENTOS_PYTHON > agent-os venv > 系统 python3），换机无需修改。

---

## 命令一览

### 录制系统（v5.1 新增）

```bash
# 开始录制
mc record start --account douyin_test
# → 启动 Camoufox，你在浏览器操作，关键节点按数字键 1-8 标记
#   按 0 结束录制

# 查看录制包
mc record list

# 分析录制包
mc record analyze <录制包路径>

# 导出为蓝图+代码
mc record export <录制包路径>

# 删除录制包
mc record delete <录制包路径>
```

### 定向评论（v5.1 新增）

```bash
# 创建一个仅包含 "打开视频→评论" 的蓝图，然后执行：
mc run --accounts douyin_test --blueprints douyin_comment_test --rounds 1 --keep

# 或手动创建自定义蓝图：
# 1. 在 blueprints/ 下创建 JSON 文件
# 2. 包含 goto_url → wait_watch → open_comments → post_comment
# 3. 用 mc run 执行
```

### 养号执行

```bash
# 批量养号（推荐）
mc run --accounts douyin_01,douyin_02 --blueprints nurture_v1 --rounds 3 --mix --interval 45-90

# 指定语料库
mc run --accounts douyin_01 --blueprints nurture_v1 --rounds 3 --corpus daily_hot

# 查看帮助
mc run --help
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--accounts` | 逗号分隔的账号列表 | 必填 |
| `--blueprints` | 逗号分隔的蓝图列表 | 必填 |
| `--rounds` | 每账号执行轮数 | 10 |
| `--mix` | 混合随机模式（每轮随机选蓝图） | 顺序模式 |
| `--interval` | 轮间间隔(秒)，支持范围 `45-90` | 30-60 |
| `--corpus` | 逗号分隔的语料库分类 | 无 |
| `--daemon` | 后台运行模式 | 否 |
| `--engine` | 引擎（auto/camoufox） | auto |
| `--keep` | 执行完后保留浏览器（需手动关） | 否 |
| `--json` | 输出 JSON 格式结果 | 否 |

### 账号管理

```bash
mc account list              # 列出所有账号及状态
mc account login <name>      # 首次手动登录（打开浏览器等用户操作）
mc account status [name]     # 查看账号登录状态
mc account export            # 导出账号配置
mc account import <path>     # 导入账号配置
```

### 注册新账号（Dashboard 推荐）

在 Dashboard 上完成：
1. 启动 Dashboard → 左侧「矩阵」→「短信与管理」
2. 底部「注册新账号」表单
3. 选平台、填手机号、填备注名 → 点确认
4. 浏览器自动打开 → 扫码登录 → 后续可采集昵称
5. 登录后点「采集昵称」获取昵称/粉丝数

也可以通过 CLI：
```bash
python scripts/matrix.py account create --platform douyin --phone 138xxxx
```

### 短信 API（Dashboard 推荐）

Dashboard 短信页面：
1. 左侧「矩阵」→「短信与管理」
2. 下拉选账号 → 点「查短信」
3. 系统自动解析抖音/小红书验证码

API：
```bash
# 查短信
GET /api/matrix/sms/test/{phone_or_account}

# 查看所有账号手机号
GET /api/matrix/sms/accounts
```

### Dashboard 启动

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard
nohup ~/.workbuddy/binaries/python/envs/agent-os/bin/uvicorn app:app --host 0.0.0.0 --port 9988 &
# 浏览器打开 http://localhost:9988
# 左侧「矩阵」：短信 / 录制 / 账号管理
```

### 新机部署说明

新机部署后同步账号：
```bash
bash ~/workbuddy-agent-os/agent-sync/00_bootstrap/init.sh
# 自动拉取仓库 → 安装依赖 → 同步本机账号
```

`accounts_registry.yaml` 中 `assigned_machine` 标记为当前机器 UID 的账号会自动同步到本机。

### 蓝图管理

```bash
mc blueprint list            # 列出所有蓝图
mc blueprint show <name>     # 查看蓝图详情
```

### 语料库

```bash
mc corpus list               # 查看语料分类
mc corpus add <平台> "语料"   # 添加语料
```

### 状态查询

```bash
mc status all                # 全局状态（浏览器+账号）
mc status accounts           # 账号登录状态
mc status browsers           # 浏览器运行状态
```

### 代理管理

```bash
mc proxy list                # 代理列表
mc proxy test <name>         # 测试代理
```

---

## 自动化任务

### 每日养号（定时执行）

```bash
# 完整执行
bash ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts/nurture_daily.sh

# 仅查看命令（不执行）
bash ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts/nurture_daily.sh --dry

# 仅跑第1组
bash ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts/nurture_daily.sh --group 1
```

日志：`/tmp/nurture_daily_YYYYMMDD.log`

### 结构化日志

每次 mc run 执行后自动写入：

`agent-local/tools/matrix/logs/run_{date}_{account}.jsonl`

查询：
```python
from mc.runlog import get_today_summary
print(get_today_summary())
# → {"date": "20260609", "accounts": {"douyin_01": {"runs": 3, "last_success": 8, ...}}}
```

---

## 与旧版 matrix.py 对照

| 旧命令 | 新命令 |
|--------|--------|
| `python matrix.py account list` | `mc account list` |
| `python matrix.py account login X` | `mc account login X` |
| `python matrix.py nurture run -a X -r 10` | `mc run --accounts X --rounds 10 ...` |
| `python matrix.py status all` | `mc status all` |
| `python matrix.py config blueprint list` | `mc blueprint list` |

---

## 智能体调用约定

智能体通过 WorkBuddy 技能 `matrix` 触发。SKILL.md 定义了触发词和对应的 mc 命令。

当用户说"养号"、"执行蓝图"、"账号状态"时，智能体：
1. 加载 `02_skills/matrix/SKILL.md`
2. 根据触发词匹配对应的 mc 命令
3. 执行命令并汇报结果

**不需要读源码。不需要知道 engine.py 内部细节。**

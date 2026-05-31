# Matrix 养号系统 · 操作手册

> 本手册定义所有任务的标准化创建流程。

---

## 一、文件结构

```
~/matrix/
├── config/
│   ├── accounts.yaml      ← 账号配置（手机/端口/Profile路径）
│   └── tasks.yaml         ← 任务调度配置（蓝图+账号+开关）
├── blueprints/            ← 所有蓝图放这里
│   ├── douyin_browse.json
│   ├── xiaohongshu_like.json
│   └── zhihu_read.json
├── scripts/
│   ├── launch_chrome.sh   ← 启动 Chrome 调试模式
│   ├── cdp_connector.py   ← CDP 连接器（连接 Chrome + 反检测）
│   ├── task_engine.py     ← 蓝图执行引擎
│   ├── task_scheduler.py  ← 定时调度器
│   └── init_db.py         ← 数据库初始化
├── data/
│   └── matrix.db          ← SQLite 数据库
└── profiles/
    └── account_01/        ← 账号 Cookie（自动保存）
        └── Default/       ← Chrome Profile 目录
```

---

## 二、日常操作（每日标准流程）

### 1. 启动 Chrome 调试模式
```bash
bash ~/matrix/scripts/launch_chrome.sh account_01 9222
```

### 2. 手动登录（如需新账号）
在 Chrome 里登录平台 → Cookie 自动保存到 `~/matrix/profiles/<账号>/`

### 3. 执行单个蓝图
```bash
python3 ~/matrix/scripts/task_engine.py <蓝图名> --account <账号ID> --port <端口>

# 示例：执行抖音浏览蓝图
python3 ~/matrix/scripts/task_engine.py douyin_browse --account account_01

# 示例：执行小红书点赞蓝图
python3 ~/matrix/scripts/task_engine.py xiaohongshu_like --account account_01
```

### 4. 预览蓝图（不连接浏览器）
```bash
python3 ~/matrix/scripts/task_engine.py <蓝图名> --dry-run
```

### 5. 定时自动跑
```bash
# 前台运行
python3 ~/matrix/scripts/task_scheduler.py

# 或用 cron/launchd 定时触发
python3 ~/matrix/scripts/task_scheduler.py --once
```

---

## 三、标准化：新增一个完整任务

假设要新增「小红书点赞养号」任务，需要修改/新增以下 3 个文件：

### Step 1 → 新增蓝图文件

**文件**：`~/matrix/blueprints/xiaohongshu_like.json`

```json
{
  "id": "xiaohongshu_like",
  "name": "小红书点赞互动",
  "platform": "xiaohongshu",
  "version": "1.0.0",
  "description": "浏览发现页，随机点赞收藏评论",
  "steps": [
    {
      "op": "goto",
      "args": { "url": "https://www.xiaohongshu.com" },
      "wait_after": 3,
      "retry": 2
    },
    {
      "op": "remove_overlays",
      "args": {},
      "wait_after": 1
    },
    {
      "op": "swipe_up",
      "args": { "distance": 600, "duration_ms": 500 },
      "wait_after": 5,
      "wait_jitter": 1
    },
    {
      "op": "evaluate",
      "args": {
        "script": "() => { const btn = document.querySelector('[class*=like]'); if(btn) btn.click(); }"
      },
      "wait_after": 2
    },
    {
      "op": "swipe_up",
      "args": { "distance": 600, "duration_ms": 450 },
      "wait_after": 10,
      "wait_jitter": 2
    }
  ]
}
```

### Step 2 → 注册到任务配置

**文件**：`~/matrix/config/tasks.yaml`

```yaml
tasks:
  - id: daily_xhs_like
    name: 小红书点赞互动
    blueprint: xiaohongshu_like      # ← 对应 blueprints/*.json 的文件名
    accounts:
      - account_01
    enabled: true                    # true=启用，false=禁用
```

### Step 3 → 如果是新平台，添加账号配置

**文件**：`~/matrix/config/accounts.yaml`

```yaml
accounts:
  - id: account_02
    platform: xiaohongshu
    phone: "13800001111"
    port: 9223                       # 每个账号用不同端口
    profile_dir: profiles/xhs_02
    enabled: true
```

---

## 四、蓝图操作参考

### 支持的操作（op 字段）

| op | 说明 | 关键参数 |
|---|---|---|
| `goto` | 导航到 URL | `url` |
| `wait` | 等待秒数 | `seconds` |
| `swipe_up` | 向上滑动 | `distance`(px), `duration_ms` |
| `swipe_down` | 向下滑动 | `distance`(px), `duration_ms` |
| `touch_tap` | 触摸点击坐标 | `x`, `y` |
| `evaluate` | 执行 JS | `script`（返回 `()=>{...}` 函数） |
| `click` | 点击元素 | `selector` |
| `fill` | 填写输入框 | `selector`, `value` |
| `press` | 按键 | `selector`, `key` |
| `screenshot` | 截图 | `path`（可选） |
| `remove_overlays` | 清理 App 弹窗 | 无参数 |
| `wait_for` | 等待元素出现 | `selector`, `timeout` |

### 步骤级配置

每个步骤可额外设置：

```json
{
  "op": "goto",
  "args": { "url": "https://..." },
  "wait_after": 3,      // 步骤执行后等待 3 秒
  "wait_jitter": 0.5,   // 等待时间随机抖动 ±0.5 秒
  "retry": 2            // 失败重试 2 次
}
```

---

## 五、进阶配置

### 多账号并发

每个账号用独立 Chrome 调试端口，示例：

```bash
# 账号1 → 端口9222
bash ~/matrix/scripts/launch_chrome.sh account_01 9222

# 账号2 → 端口9223
bash ~/matrix/scripts/launch_chrome.sh account_02 9223
```

### 熔断机制（自动）

连续失败 3 次自动暂停 30 分钟，人工介入后自动恢复。

### 数据库执行记录

所有执行自动写入 `~/matrix/data/matrix.db`，可用 sqlite3 查看：

```bash
sqlite3 ~/matrix/data/matrix.db "SELECT * FROM executions ORDER BY created_at DESC LIMIT 10;"
```

---

## 六、故障排查

| 症状 | 原因 | 处理 |
|---|---|---|
| `HTTP Error 502` | urllib 走了代理 | 检查 `cdp_connector.py` 是否用 `ProxyHandler({})` |
| `Emulation.setTouchEmulationOverride` 报错 | Chrome 147 移除了此 API | 升级 cdp_connector.py |
| `webSocketDebuggerUrl` 获取失败 | Chrome 未启动调试模式 | 先运行 `launch_chrome.sh` |
| 步骤执行正常但页面空白 | 窗口尺寸太小 | 修改 `launch_chrome.sh` 的 `--window-size` |
| Cookie 丢失 | Profile 路径不一致 | 确认 `accounts.yaml` 中 `profile_dir` 正确 |

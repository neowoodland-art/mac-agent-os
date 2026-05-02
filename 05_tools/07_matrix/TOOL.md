# TOOL.md — 矩阵养号系统 Matrix

> **工具版本**: v4.0  
> **接入日期**: 2026-04-29  
> **维护者**: ghai  
> **路径方案**: local.yaml + local_paths.py（无软链接，多机安全）  
> **更新日期**: 2026-04-30  
> **平台支持**: 抖音 ✅ | 小红书 🔄 | 知乎 🔄 | 快手 📋

---

## 一句话说明

通过 Chrome CDP 和 Camoufox（Firefox 内核）程序化控制浏览器，自动完成多平台社交账号的日常养号任务（浏览、点赞、评论、收藏等），模拟真实用户行为。

---

## 目录结构

```
05_tools/07_matrix/               ← 代码层（随 agent-os 同步）
├── TOOL.md                       # 本档案
├── install.sh                    # 新机一键恢复（生成 local.yaml）
├── local.yaml                    # ★ 本机路径配置（不同步，install.sh 生成）
├── local.yaml.template           # 路径配置模板
├── requirements.txt              # Python 依赖
├── scripts/                      # 核心 Python 脚本
│   ├── local_paths.py            # ★ 统一路径管理模块（读取 local.yaml）
│   ├── task_engine.py            # 蓝图执行引擎（主入口）
│   ├── switch_account.py         # 账号切换器
│   ├── task_scheduler.py         # 定时调度器
│   ├── douyin_ops.py             # 抖音原子操作库（18个操作）
│   ├── cdp_connector.py          # Chrome CDP 连接器
│   ├── camoufox_manager.py       # Camoufox 浏览器管理
│   ├── camoufox_server.py        # Camoufox Server 启动器
│   ├── gen_report.py             # 测试报告生成
│   └── launch_chrome.sh          # Chrome 启动脚本
├── blueprints/                   # 任务蓝图（JSON 配置）
├── corpus/                       # 评论/互动语料库
├── docs/                         # 详细文档
└── config_template/              # 配置模板（不含敏感信息，供新机参考）
    └── accounts.yaml             # 账号配置模板

workbuddy-agent-os/agent-local/tools/matrix/      ← 数据层（本机专属，不同步）
├── config/accounts.yaml          # 真实账号配置（含 Cookie 路径等）
├── data/matrix.db                # 任务执行记录数据库
├── data/cookies/                 # 账号 Cookie 文件
├── data/camoufox_pids/           # Camoufox 进程 PID
├── profiles/                     # Chrome 用户 Profile（~100MB，不纳入同步）
├── logs/                         # 运行日志
└── screenshots/                  # 截图快照

⭐ 路径解析方式 (v4.0):
  local_paths.py → 读取 local.yaml → 获取 data_root
  → config_path("x")     → data_root/config/x
  → data_path("x")       → data_root/data/x
  → logs_path("x")       → data_root/logs/x
  → profiles_path("x")   → data_root/profiles/x
  → screenshots_path("x")→ data_root/screenshots/x
  → code_dir()           → 05_tools/07_matrix/（代码目录）
```

---

## 快速使用

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix

# 启动抖音账号（Chrome CDP）
python scripts/switch_account.py --method profile --target douyin_01 --port 9222

# 执行日常浏览蓝图
python scripts/task_engine.py --blueprint douyin_browse_v2 --account douyin_01

# 定时调度
python scripts/task_scheduler.py

# 查看账号状态
python scripts/switch_account.py --status
```

---

## 环境依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 使用 agent-os venv |
| Google Chrome | 最新版 | CDP 直连 |
| Camoufox | 最新版 | Firefox 内核，反检测 |
| playwright | ≥1.40 | 浏览器自动化 |

完整依赖见 `requirements.txt`，安装：
```bash
pip install -r ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/requirements.txt
```

---

## 新机恢复

```bash
# 一键恢复（建立本地目录骨架 + 生成 local.yaml + 安装依赖）
bash ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/install.sh

# 然后将账号配置复制/重新填写
cp ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/config_template/accounts.yaml \
   ~/workbuddy-agent-os/agent-local/tools/matrix/config/accounts.yaml
# 编辑 accounts.yaml 填入本机账号信息
```

## 多机同步说明 (v4.0)

本工具不再使用软链接，改为 `local.yaml` + `local_paths.py` 方案：

- `local.yaml` — 记录本机数据目录路径，每台机器独立生成
- `local.yaml` 不参与坚果云同步（请加入排除列表）
- 所有 Python 脚本通过 `scripts/local_paths.py` 读取路径
- 任何脚本启动时若 `local.yaml` 不存在，会报错并提示运行 `install.sh`

`local.yaml` 格式（自动生成，无需手动编辑）：
```yaml
matrix:
  local_data_root: /Users/xxx/workbuddy-agent-os/agent-local/tools/matrix
```

---

## 当前开发状态

| 阶段 | 内容 | 状态 |
|------|------|------|
| A | Chrome CDP + 抖音原子操作（18个）+ 蓝图引擎 | ✅ 已完成 |
| B | Camoufox 集成 + 多浏览器内核 | 🔄 进行中 |
| C | 鼠标轨迹仿真 + 语料库完善 | 📋 规划中 |
| D | 小红书/知乎完整支持 | 📋 规划中 |

---

## 注意事项

- `local.yaml` 每台机器独立配置，**不纳入坚果云同步**（加入排除列表）
- `profiles/` 目录含 Chrome 用户数据（~100MB），存于 `agent-local/` 本地
- `config/accounts.yaml` 含账号标识信息，存于 `agent-local/` 本地
- 换机后 profiles 需重新登录各平台账号
- Camoufox 需单独安装（见 docs/CAMOUFOX_LOGIN_MANAGEMENT.md）
- 多机同步只需每台机器运行一次 `install.sh`
- 避免使用软链接指向 agent-local，统一通过 `local_paths.py` 管理路径

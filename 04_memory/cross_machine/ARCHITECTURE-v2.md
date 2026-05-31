# 联邦多机协同架构 v2.0 —— WPRA 写分区·读聚合

> **版本**: 2.0.0 | **最后更新**: 2026-05-31 | **状态**: 设计文档
> **核心原则**: 各写各的文件，最后统一读取

---

## 目录

- [1. 问题审计](#1-问题审计)
- [2. 核心架构：WPRA 模型](#2-核心架构wpra-模型)
- [3. 机器身份系统](#3-机器身份系统)
- [4. 写分区策略](#4-写分区策略)
- [5. 读聚合策略](#5-读聚合策略)
- [6. 版本与时间戳控制](#6-版本与时间戳控制)
- [7. Git 冲突消除方案](#7-git-冲突消除方案)
- [8. 数据文件规范总表](#8-数据文件规范总表)
- [9. 审计清单](#9-审计清单)
- [10. 全流程实操演练](#10-全流程实操演练)
- [11. 分阶段实施计划](#11-分阶段实施计划)

---

## 1. 问题审计

### 1.1 当前架构的冲突根源

在仔细审计了 guardd.py、app.py、matrix_mgmt.py、plugins/base.py 四个核心文件后，发现以下 **4 个冲突源**：

| # | 文件 | 写入者 | 问题 |
|:-:|:-----|:-------|:-----|
| **C1** | `status/live/_registry.json` | **每台机器的 guardd** (全员写) | 单文件、全员写，每次 git push 必然冲突 |
| **C2** | `data/*/{uid}.json` | **每台机器写自己的** ✅ | 无冲突，但 guardd 在 `_registry.json` 重建时扫描这个目录（多余） |
| **C3** | `accounts_registry.yaml` | **混合**：一次写入 + git 传播，但谁改谁冲突 | 单文件跨越所有机器，改一次冲突一次 |
| **C4** | `git add -A` | **每台机器的 guardd** (全员执行) | 把全目录都 staging 了，包括别的机器写的文件 |

### 1.2 冲突链路

```
机器A guardd 运行
  → module_heartbeat() → 写 status/live/{A_UID}.json ✅ (安全)
  → 还写 _registry.json ← 扫描全 data/ 目录重建 ← 可能包含了机器B刚push的
  → _git_sync() → git add -A → 把机器B的 status/live/{B_UID}.json 也 add 了
  → git commit → git push

机器B guardd 运行
  → git pull → 看到机器A刚push的 _registry.json (可能和B自己的版本不同)
  → 写自己的 status/live/{B_UID}.json
  → 又写 _registry.json (覆盖A刚写的)
  → git add -A → git commit → git push
  → 冲突！因为 _registry.json 被双方先后修改
```

### 1.3 根因

**核心病根只有两个：**

1. **`_registry.json` 不该由 guardd 写**——它是个聚合产物，应该只由 Dashboard 生成
2. **`git add -A` 不能用在联邦系统中**——必须用 `git add <自己写的文件>`
3. **`accounts_registry.yaml` 不该是所有机器共享的单文件**

---

## 2. 核心架构：WPRA 模型

### 2.1 基本原理

```
┌─────────────────────────────────────────────────────┐
│                   WPRA 模型                         │
│                                                     │
│  Write Partitioned     +     Read Aggregated        │
│  (写分区)                    (读聚合)               │
│                                                     │
│  每台机器只写自己的命名空间       读取方遍历所有机器   │
│  从来不碰别人的文件               按时间戳合并        │
│  git commit 只提交自己的修改       呈现统一视图       │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ 机器A    │  │ 机器B    │  │ 机器C    │          │
│  │ 写A/     │  │ 写B/     │  │ 写C/     │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│       │              │              │                │
│       └──────┬───────┴───────┬──────┘                │
│              ▼               ▼                       │
│        ┌──────────────────────────┐                  │
│        │   Git 仓库 (共同载体)     │                  │
│        │   机器A/ 机器B/ 机器C/   │                  │
│        └──────────────────────────┘                  │
│                     │                                │
│                     ▼                                │
│        ┌──────────────────────────┐                  │
│        │  Dashboard (读聚合)      │                  │
│        │  读A/ + 读B/ + 读C/     │                  │
│        │  按updated_at排序合并    │                  │
│        └──────────────────────────┘                  │
└─────────────────────────────────────────────────────┘
```

### 2.2 三定律

1. **写分区定律**：任何机器只能写以自己 `machine_uid` 命名的文件。禁止写其他机器的文件。禁止写匿名文件。
2. **读聚合定律**：任何读取方必须遍历所有机器的文件来做合并。禁止假设"某文件只由一个机器写"。
3. **Git 精确提交定律**：`git add` 必须精确指定本机文件，禁止 `-A` 或 `--all`。

---

## 3. 机器身份系统

### 3.1 身份三层结构

每台机器有**三层身份**，从上到下稳定性递增：

| 层级 | 字段 | 示例 | 稳定性 | 来源 |
|:----:|:-----|:-----|:------:|:-----|
| L0 | **machine_uid** | `4cf443bc-ff14-4ed9-885b-b04c5326304d` | 🔒 永久不变 | UUID v4，第一次启动生成 |
| L1 | **machine_name** | `chengzigedeAir` | ⚡ 变但不失真 | 缓存的 hostname |
| L2 | **display_name** | `Ghai's MacBook Air` | 🔄 用户可改 | 用户设置的别名 |

**L0 是程序主键**——所有文件名以 `{machine_uid}` 命名。

### 3.2 机器身份声明文件

每台机器在首次初始化时，在自己的命名空间根目录写入一个 `MACHINE.yaml`，**终身不改**：

```yaml
# cross_machine/machines/{machine_uid}/MACHINE.yaml
# 机器身份声明 — 创建后只读，永不修改
machine_uid: "4cf443bc-ff14-4ed9-885b-b04c5326304d"
machine_name: "chengzigedeAir"
created_at: "2026-04-25T09:45:16+08:00"
schema_version: "2.0"
role: "workstation"
```

### 3.3 身份文件位置

```
agent-local/identity/
├── machine_uid             ← UUID v4，一行文本
├── cached_hostname         ← 缓存的 hostname
└── machine_name            ← 用户友好名（可选）
```

### 3.4 命名空间目录结构

```
cross_machine/
  machines/
    {machine_uid}/              ← 每台机器一个目录
      MACHINE.yaml              ← 身份声明（创建后只读）
      heartbeat.json            ← 最新心跳
      accounts.yaml             ← 本机管理的账号
      capabilities.yaml         ← 本机能力清单
    {machine_uid}/              ← 另一台机器
      ...
```

---

## 4. 写分区策略

### 4.1 每台机器只写以下文件

```
04_memory/cross_machine/machines/{MACHINE_UID}/
├── heartbeat.json              ← guardd 写（每300s）
├── accounts.yaml               ← matrix_mgmt 写（账号变更时）
├── capabilities.yaml           ← guardd 写（安装/卸载时）
└── events/                     ← guardd 写（事件记录）
    └── 2026-05-31.jsonl        ← append-only 事件日志

04_memory/cross_machine/data/{plugin_name}/
└── {MACHINE_UID}.json          ← Dashboard plugin 写（已经是这个模式 ✅）
```

### 4.2 写的规则

```bash
# ❌ 禁止操作
git add -A                                 # 错误：会 staging 别人文件
git add 04_memory/cross_machine/status/    # 错误：范围太宽
echo '{...}' > cross_machine/machines/{other_uid}/heartbeat.json  # 错误：写别人文件

# ✅ 允许操作
git add 04_memory/cross_machine/machines/{MY_UID}/
git add 04_memory/cross_machine/data/*/{MY_UID}.json
```

### 4.3 文件格式规范

每台机器写的所有数据文件，格式必须统一：

```yaml
# 通用字段（所有数据文件必须包含）
schema_version: "2.0"           # 文件格式版本
file_version: 42                # 本文件修改次数（单调递增）
machine_uid: "...uuid..."       # 谁写的
machine_name: "chengzigedeAir"  # 谁写的（人类可读）
updated_at: "2026-05-31T17:48:28+08:00"  # 最后更新时间
# ... 业务数据 ...
```

---

## 5. 读聚合策略

### 5.1 Dashboard 读聚合流程

```
① git pull (获取所有机器最新数据)
  ↓
② 遍历 cross_machine/machines/*/ (每台机器一个目录)
  ↓
③ 读取每台机器的 heartbeat.json → 构建联邦总览
  ↓
④ 读取每台机器的 accounts.yaml → 构建账号注册表全貌
  ↓
⑤ 读取 data/{plugin}/*.json → 构建插件数据
  ↓
⑥ 按 updated_at 排序 → 去重 → 冲突处理
  ↓
⑦ 呈现统一视图
```

### 5.2 冲突合并规则

| 场景 | 规则 |
|:-----|:-----|
| 同一账号在两台机器上都有定义 | `updated_at` 最新的覆盖旧的（打日志告警） |
| 同一台机器写了多个版本 | 取 `file_version` 最大的 |
| 某台机器 24h 未更新 heartbeat | 标记为 offline |
| 文件 schema_version 不匹配 | 跳过不兼容的文件，打日志告警 |
| 某台机器 `MACHINE.yaml` 不存在 | 标记为未知机器，数据仍读取 |

### 5.3 聚合示例

```python
# 读聚合的伪代码
def aggregate_machine_data():
    machines = {}
    for machine_dir in Path("machines/").iterdir():
        if not machine_dir.is_dir():
            continue
        uid = machine_dir.name
        hb_file = machine_dir / "heartbeat.json"
        if hb_file.exists():
            machines[uid] = read_and_validate(hb_file)
    return machines

def aggregate_accounts():
    all_accounts = []
    for machine_dir in Path("machines/").iterdir():
        acct_file = machine_dir / "accounts.yaml"
        if acct_file.exists():
            accounts = read_and_validate(acct_file)
            for acct in accounts:
                acct["_source_machine"] = machine_dir.name
                all_accounts.append(acct)
    return all_accounts  # 返回时已包含来源机器标记
```

---

## 6. 版本与时间戳控制

### 6.1 三层版本体系

| 层级 | 作用域 | 字段 | 示例 | 说明 |
|:----:|:-------|:-----|:-----|:-----|
| **V0** | 全局架构 | `schema_version` | `"2.0"` | 整个 WPRA 架构版本 |
| **V1** | 每类文件 | `file_schema` | `"heartbeat-v2"` | 某类数据文件的格式版本 |
| **V2** | 每次修改 | `file_version` | `42` | 本文件的修改次数 |
| **V3** | 每次修改 | `updated_at` | `"2026-05-31T17:48:28+08:00"` | 最后更新时间 |

### 6.2 版本不兼容处理

```yaml
# 读聚合时的版本判断逻辑
schema_version: "2.0"   ← 文件格式版本
file_schema: "hb-v2"    ← 心跳格式版本

# 读取方判断：
if file_schema == "hb-v2":
    正常解析
elif file_schema == "hb-v1":
    走旧版解析器 (兼容)
else:
    跳过，打日志告警
```

### 6.3 时间戳在联邦中的用途

| 用途 | 数据源 | 比较方式 |
|:-----|:-------|:---------|
| 判断机器在线 | heartbeat.updated_at | `now - updated_at < 300s` → online |
| 判断数据陈旧 | accounts.updated_at | 按时间取最新 |
| 冲突裁决 | 各机器同类型文件 | `max(file_version)` + `updated_at` |
| 事件排序 | events/*.jsonl | 按 timestamp 排序 |
| 数据过期清理 | 所有文件 | `updated_at < 30天前` → 清理 |

### 6.4 跨机器事件板

```yaml
# events/{machine_uid}/2026-05-31.jsonl
# 格式: 每行一个 JSON 事件，append-only
{"event_id":"evt_001","machine_uid":"4cf443bc...","type":"heartbeat","timestamp":"2026-05-31T17:48:28+08:00","data":{"cpu":0.5}}
{"event_id":"evt_002","machine_uid":"4cf443bc...","type":"nurture_run","timestamp":"2026-05-31T17:50:00+08:00","data":{"account":"douyin_test","result":"success"}}
```

事件日志解决了"谁在什么时候做了什么"的问题——这是机器间协调的事实基础。

---

## 7. Git 冲突消除方案

### 7.1 冲突预防三原则

1. **粒度控制**：每个机器的写操作只影响自己的命名空间
2. **精确 add**：不用 `-A`，改用 `git add <own_namespace>`
3. **拆分单文件**：不存在的共享文件需要聚合，就由 Dashboard 动态生成

### 7.2 guardd 的 git 操作规范

```python
# ❌ 当前问题代码 (guardd.py line 376-393)
def _git_sync():
    subprocess.run(["git", "add", "-A"])    # ← 罪魁祸首
    subprocess.run(["git", "commit", ...])
    subprocess.run(["git", "push", ...])

# ✅ 修复后
def _git_sync(machine_uid, machine_name):
    # 只 add 本机命名空间的文件
    git_add_paths = [
        f"04_memory/cross_machine/machines/{machine_uid}/",
        f"04_memory/cross_machine/data/*/{machine_uid}.json",
        f"04_memory/cross_machine/events/",
    ]
    for path in git_add_paths:
        subprocess.run(["git", "add", path],
                      capture_output=True, timeout=15, cwd=str(repo))
    # 只在本机有变更时才 commit
    r = subprocess.run(["git", "status", "--porcelain",
                        f"04_memory/cross_machine/machines/{machine_uid}/"],
                      capture_output=True, text=True, timeout=10, cwd=str(repo))
    if r.stdout.strip():
        subprocess.run(["git", "commit", "-m", ...], ...)
```

### 7.3 账号注册表重构

**将 `accounts_registry.yaml`（单文件、全员写）重构为：**

```
# ❌ 旧结构：单文件，所有机器共享，谁改谁冲突
agent-sync/05_tools/07_matrix/accounts_registry.yaml

# ✅ 新结构：每台机器声明自己管理的账号
04_memory/cross_machine/machines/{machine_uid}/
  accounts.yaml         ← 本机管理的账号清单
```

**Dashboard 读聚合时遍历所有机器的 accounts.yaml：**

```python
def get_all_accounts():
    """遍历所有机器，聚合账号注册表"""
    all_accounts = []
    machines_dir = CROSS_MACHINE / "machines"
    for machine_dir in machines_dir.iterdir():
        if not machine_dir.is_dir():
            continue
        acct_file = machine_dir / "accounts.yaml"
        if acct_file.exists():
            data = yaml.safe_load(acct_file.read_text())
            for acct in data.get("accounts", []):
                acct["_source_machine_uid"] = machine_dir.name
                acct["_source_machine_name"] = data.get("machine_name", "")
                all_accounts.append(acct)
    return all_accounts
```

### 7.4 `_registry.json` 的消除

**`_registry.json` 是当前问题最大的单文件——它是最频繁写入的聚合文件。**

处理方案：
- **guardd 不再写 `_registry.json`** —— 删除 guardd.py 中 `module_heartbeat()` 里构建 `_registry.json` 的代码（line 331-358）
- **只有 Dashboard 在响应 `/api/push/heartbeat` API 时才更新它**（app.py line 609-611，这个只有一个实例运行，不会有冲突）
- **Dashboard 的 `_registry.json` 只作为运行时缓存，不是数据源**

### 7.5 最终的目录结构和写权限

```
cross_machine/
├── machines/                          ← 核心：每台机器的数据
│   ├── {machine_uid_a}/              ← 只被机器A写入
│   │   ├── MACHINE.yaml              ← 一次写入，终身只读
│   │   ├── heartbeat.json            ← 机器A的 guardd 写
│   │   ├── accounts.yaml             ← 机器A的 matrix_mgmt 写
│   │   ├── capabilities.yaml         ← 机器A的 guardd 写
│   │   └── events/                   ← 机器A的 guardd 写
│   │       └── 2026-05-31.jsonl
│   ├── {machine_uid_b}/              ← 只被机器B写入
│   └── {machine_uid_c}/              ← 只被机器C写入
│
├── data/                              ← 插件数据（已正确 ✅）
│   ├── guardd/{uid}.json              ← 只被 uid 对应机器写
│   ├── matrix/{uid}.json              ← 只被 uid 对应机器写
│   └── ...
│
├── status/
│   └── live/
│       ├── {uid}.json                 ← 只被 uid 对应机器写 ✅
│       └── _registry.json             ← 只被 Dashboard app.py 写
│                                       ← guardd 不碰它
│
├── events/                            ← 全局事件（计划废弃 → 移到 machines/*/events/）
├── tasks/                             ← 任务分发（保持现有）
├── encrypted/                         ← 加密通信（保持现有）
├── knowledge/                         ← 共享知识（保持现有）
└── ARCHITECTURE-v2.md                 ← 本文档
```

---

## 8. 数据文件规范总表

### 8.1 心跳文件 (heartbeat.json)

```yaml
# 路径: machines/{machine_uid}/heartbeat.json
# 写入者: guardd module_heartbeat() 每300s
schema_version: "2.0"
file_schema: "heartbeat-v2"
file_version: 142           # 单调递增
machine_uid: "4cf443bc-ff14-4ed9-885b-b04c5326304d"
machine_name: "chengzigedeAir"
updated_at: "2026-05-31T17:48:28+08:00"

status: "online"
guardd_version: "2.2.0"
cpu_load: 0.42
memory_pct: 45.2
disk_avail_gb: 161.3
uptime_sec: 86400
current_task: null
```

### 8.2 账号注册文件 (accounts.yaml)

```yaml
# 路径: machines/{machine_uid}/accounts.yaml
# 写入者: matrix_mgmt 账号管理操作时
schema_version: "2.0"
file_schema: "accounts-v2"
file_version: 5
machine_uid: "4cf443bc-ff14-4ed9-885b-b04c5326304d"
machine_name: "chengzigedeAir"
updated_at: "2026-05-31T11:09:00+08:00"

accounts:
  - id: douyin_test
    platform: douyin
    phone: 153****8283
    status: logged_in
    enabled: true
```

### 8.3 MACHINE.yaml (身份声明)

```yaml
# 路径: machines/{machine_uid}/MACHINE.yaml
# 写入者: 初始化时一次写入，终身只读
schema_version: "2.0"
file_schema: "machine-identity-v1"
machine_uid: "4cf443bc-ff14-4ed9-885b-b04c5326304d"
machine_name: "chengzigedeAir"
created_at: "2026-04-25T09:45:16+08:00"
role: "workstation"
notes: "Ghai's primary development machine"
```

### 8.4 已废弃/不再使用的文件

| 文件 | 废弃原因 | 替代方案 |
|:-----|:---------|:---------|
| `registry/{hostname}.json` | 旧格式，和 machines/*/ 重复 | `machines/*/MACHINE.yaml` |
| `status/live/_registry.json` (guardd写入部分) | 全员写导致冲突 | 只由 Dashboard app.py 写入 |
| `accounts_registry.yaml` | 单文件全员写 | `machines/*/accounts.yaml` |
| `status/{hostname}/heartbeat.json` | 旧格式，基于 hostname 不安全 | `machines/*/heartbeat.json` |
| `guardd-required-version.txt` | 单文件全员写，读聚合即可 | 废弃，用 version 字段在各文件中 |

---

## 9. 审计清单

### 9.1 设计审计

| 审计项 | 状态 | 说明 |
|:-------|:----:|:-----|
| **每台机器都有唯一不可变身份** | ✅ | `machine_uid` = UUID v4，永久不变 |
| **各写各的文件** | ✅ | 每台机器只操作自己的命名空间 |
| **从来不碰别人的文件** | ✅ | 禁止写入 `machines/{other_uid}/` |
| **git add 精确可控** | ✅ | 不允许 `-A`，只 add 本机文件 |
| **读取方遍历所有机器** | ✅ | Dashboard 遍历 `machines/*/` |
| **版本号控制文件兼容性** | ✅ | `schema_version` + `file_schema` 双保险 |
| **时间戳控制数据新鲜度** | ✅ | `updated_at` + `file_version` |
| **废弃文件的迁移路径** | ✅ | 旧文件保持只读兼容，新系统用新路径 |
| **无全局共享单文件** | ✅ | `_registry.json` 由单实例 Dashboard 写入 |

### 9.2 安全审计

| 审计项 | 状态 | 说明 |
|:-------|:----:|:-----|
| 机器A不能冒用机器B的身份 | ✅ | 私钥在 agent-local，git 无法伪造 |
| 数据不泄露到其他机器 | ✅ | 敏感信息在 agent-local，不进 git |
| 删除操作可追溯 | ✅ | events/ 日志作为审计线索 |

### 9.3 容错审计

| 场景 | 行为 |
|:-----|:-----|
| 机器A断网，机器B正常 | 机器A的 `updated_at` 停留在断网前，Dashboard 标记 offline |
| 机器A的机器_uid 文件丢失 | guardd 生成新 UUID → 成为新机器 → `MACHINE.yaml` 标记旧机退役 |
| 两台机器写了同名的账号 | 时间戳判定：后写的覆盖，标记冲突告警 |
| 某台机器的 `accounts.yaml` 损坏 | 跳过该文件，其他机器的数据不受影响 |
| 机器A搬到了新电脑 | 新 UUID → 新机器身份 → 迁移脚本导入账号数据 |

---

## 10. 全流程实操演练

### 10.1 场景：三台机器协同运转

```
机器: chengzigedeAir (UID: 4cf4...)  →  主力工作站
      5kechengdeAir  (UID: f13b...)  →  养号机
      7kecheng       (UID: d197...)  →  辅助采集机
```

### 10.2 Step-by-step 无冲突运转

```
T+0s: 三台机器同时启动 guardd
  ├─ 机器A → git pull → 写 machines/4cf4.../heartbeat.json
  │          → git add machines/4cf4.../ → git commit → git push
  ├─ 机器B → git pull → 写 machines/f13b.../heartbeat.json
  │          → git add machines/f13b.../ → git commit → git push
  └─ 机器C → git pull → 写 machines/d197.../heartbeat.json
             → git add machines/d197.../ → git commit → git push

  ✅ 结果：三个 push 无冲突，因为各写各的文件，各 add 各的命名空间


T+5min: 机器B完成一轮养号，更新账号状态
  ├─ 机器B → 写 machines/f13b.../accounts.yaml (更新账号状态)
  │          → git add machines/f13b.../accounts.yaml
  │          → git commit → git push ↴
  └─ 机器A → 同时写自己的 heartbeat
             → git add machines/4cf4.../
             → git commit → git push ↴

  ✅ 并行无冲突：B 改 B 的文件，A 改 A 的文件，互不干扰


T+1h: Dashboard 刷新查看所有机器状态
  ├─ git pull (获取所有机器最新数据)
  ├─ 遍历 machines/4cf4.../ + machines/f13b.../ + machines/d197.../
  ├─ 读取各自的 heartbeat.json → 3台机器都在线
  ├─ 读取各自的 accounts.yaml → 聚合得到完整账号表
  └─ 呈现统一视图

  ✅ 读聚合：一次遍历，全貌呈现


T+1天: 机器C下线
  ├─ machines/d197.../heartbeat.json 的 updated_at 不再更新
  └─ Dashboard 检测到 updated_at > 24h → 标记 offline

  ✅ 无额外操作：没有"下线通知"需要写，消失就是下线
```

### 10.3 冲突场景对比

| 场景 | 旧架构 | 新架构 |
|:-----|:-------|:-------|
| 三台机器同时写心跳 | `_registry.json` 三方覆盖 → git冲突 ❌ | 各写各的 `machines/*/heartbeat.json` → 无冲突 ✅ |
| 两台机器同时更新账号 | `accounts_registry.yaml` 被覆盖 | 各写各的 `machines/*/accounts.yaml` → 无冲突 ✅ |
| 一台机器 push 后另一台 push | `git add -A` 包含了对方文件 → 冲突 | `git add` 只加自己文件 → 无冲突 ✅ |
| Dashboard 刷新 | 读 `_registry.json` → 可能读到旧的 | 遍历 `machines/*/` → 总是最新 ✅ |
| 新机器加入 | 手动在 registry/ 加文件 | 写自己的 `machines/{new_uid}/` → 自动被发现 ✅ |

---

## 11. 分阶段实施计划

### Phase 1：修复冲突根源（本次实施）

| # | 任务 | 涉及文件 | 风险 |
|:-:|:-----|:---------|:----:|
| 1.1 | guardd: 删除 `_registry.json` 重建代码 | `guardd.py` line 330-358 | 低 |
| 1.2 | guardd: 删除 `_registry.json` 中扫描 data/ 的逻辑 | `guardd.py` line 340-357 | 低 |
| 1.3 | guardd: 将 `git add -A` 改为精确 add 本机文件 | `guardd.py` line 380 | 中 |
| 1.4 | guardd: 将 status 写入改为 `machines/*/` 新格式 | `guardd.py` module_heartbeat | 低 |
| 1.5 | 创建本机 MACHINE.yaml 身份声明 | guardd 首次运行时 | 低 |
| 1.6 | 废弃旧文件标记（不删，加注释） | 文档 | 低 |

### Phase 2：账号注册表重构（已完成 ✅）

| # | 任务 | 涉及文件 | 状态 |
|:-:|:-----|:---------|:----:|
| 2.1 | matrix_mgmt: 新增 `_write_self_accounts()` | `matrix_mgmt.py` | ✅ |
| 2.2 | matrix_mgmt: 新增 `_read_all_machines_accounts()` | `matrix_mgmt.py` | ✅ |
| 2.3 | list_accounts(): WPRA优先，降级到旧文件 | `matrix_mgmt.py` | ✅ |
| 2.4 | publish_status(): 触发 WPRA 同步写入 | `matrix_mgmt.py` | ✅ |
| 2.5 | create/update/delete: 操作后更新 WPRA | `matrix_mgmt.py` | ✅ |
| 2.6 | 修复硬编码 `/Users/5kecheng/` 路径 | `matrix_mgmt.py` | ✅ |

### Phase 3：Dashboard 读聚合适配（已完成 ✅）

| # | 任务 | 涉及文件 | 状态 |
|:-:|:-----|:---------|:----:|
| 3.1 | Dashboard: _registry.py WPRA 优先读 `machines/*/` | `_registry.py` | ✅ v2.0 |
| 3.2 | Dashboard: guardd 插件 WPRA 心跳路径 | `plugins/guardd.py` | ✅ v3.1 |
| 3.3 | Guardd: 增加 events/ 写入能力 | `guardd.py` | ✅ Phase 1 |

### Phase 4：旧数据清理（已完成 ✅）

| # | 任务 | 涉及文件 | 状态 |
|:-:|:-----|:---------|:----:|
| 4.1 | 确认新系统稳定运行 1 周 | — | ⏳ 等待中 (目标: 2026-06-07) |
| 4.2 | 归档旧 registry 文件 | `registry/*.json` → `registry/_archive/` | ✅ |
| 4.3 | 删除旧 `_registry.json` | `status/live/_registry.json` | ⏳ 等待 4.1 |
| 4.4 | 删除旧 `accounts_registry.yaml` | `07_matrix/accounts_registry.yaml` | ⏳ 已标记废弃，等待 4.1 |
| 4.5 | 归档旧 `status/{hostname}/` 目录 | `status/chengzigedeAir/` 等 → `status/_archive/` | ✅ |

### Phases 5：文档化与标准化

| # | 任务 | 涉及文件 | 风险 |
|:-:|:-----|:---------|:----:|
| 5.1 | 更新 CORE-ARCHITECTURE.md | `03_knowledge/99_system/` | 低 |
| 5.2 | 同步本文档到 Gitee + GitHub | — | 低 |

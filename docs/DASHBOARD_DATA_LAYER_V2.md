# Dashboard 数据层设计 V2.1 —— 联邦式多机协同架构

> 版本 2.1 | 最后更新：2026-05-15
> 本文件定义 AgentOS 多机多 Agent 环境下的完整联邦式数据协同架构

---

## 架构全景（七大子系统）

```
┌─────────────────────────────────────────────────────────────────────┐
│                     machine redmi-12c                                │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     guardd (守护进程, 每5-10分钟循环)         │    │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │    │
│  │  │heartbeat│ │knowledge │ │ upgrade  │ │ memory triage  │  │    │
│  │  │ 状态上报 │ │ 知识同步  │ │ 版本检查  │ │ 记忆提炼上报    │  │    │
│  │  └─────────┘ └──────────┘ └──────────┘ └────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐      │
│  │ tools/ave │ │tools/    │ │ memory/  │ │ identity/secrets/ │     │
│  │ 视频资产   │ │ matrix   │ │ 本地记忆  │ │ 本地密钥 (不共享) │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘      │
└──────────────────────┬──────────────────────────────────────────────┘
                       │ guardd 上报 + 拉取
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    agent-sync/cross_machine/ (坚果云同步)            │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │  registry/   │ │   events/    │ │   status/    │               │
│  │  机器注册     │ │  事件总线     │ │  状态机      │               │
│  │  (+公钥)     │ │  跨机日志     │ │  在线/离线   │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │   tasks/     │ │  encrypted/  │ │ knowledge/   │               │
│  │  跨机任务协作  │ │  加密消息     │ │ 版本清单      │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                     │
│  ▲ 所有放在这里的都是明文安全的（公钥、加密内容、元数据）           │
│  ▲ 敏感信息（私钥、API Key）不在此目录                              │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ 本机     │ │ 其他机器  │ │ 知识库   │
    │Agent     │ │ registry │ │ 03_     │
    │详细数据   │ │ 状态摘要  │ │knowledge │
    └─────────┘ └─────────┘ └─────────┘
          ▲            ▲            ▲
          └────────────┼────────────┘
                       │
          ┌────────────┴────────────┐
          │     Dashboard (只读)     │
          │  每台机器独立运行         │
          └─────────────────────────┘

     ═══════ 补充通道（不经过 agent-sync）═══════
     ┌─────────────────────────────────────────┐
     │   直接传输层 (Direct Transfer Layer)      │
     │                                         │
     │  ┌──────────────┐  ┌──────────────────┐  │
     │  │  AirDrop /   │  │  SSH/rsync       │  │
     │  │  同局域网直传  │  │  大文件直接传输   │  │
     │  └──────────────┘  └──────────────────┘  │
     │                                         │
     │  用途：                                   │
     │  • 大文件素材直接传递 (不走坚果云)          │
     │  • 敏感配置加密传递 (不落盘同步文件夹)      │
     └─────────────────────────────────────────┘
```

---

## 你补充的 7 项需求 → 我的对应设计

### ① 消息/状态机（5-10 分钟心跳）

**需求**：每台电脑需要一个消息/状态机，定时同步本机情况，包括是否在线、正在做什么。

**设计**：

#### 状态机状态流

```
┌─────────────────────────────────────────────────────┐
│               machine state machine                   │
│                                                      │
│  initializing ──► online ──► busy ──► online         │
│       │              │          │                     │
│       │              ▼          │                     │
│       └──────► error ◄──────────┘                     │
│                      │                                │
│                      ▼                                │
│                  offline (超时未上报)                   │
└─────────────────────────────────────────────────────┘
```

#### heartbeat.json（每台机器每 5-10 分钟覆盖写一次）

```json
{
  "hostname": "redmi-12c",
  "system_hostname": "redmi-12c-macbook",
  "state": "online",
  "agents": {
    "ave": { "state": "idle", "last_active": "2026-05-15T14:30:00+08:00" },
    "matrix": { "state": "running", "last_active": "2026-05-15T14:28:00+08:00" },
    "claw": { "state": "waiting", "last_active": "2026-05-15T14:35:00+08:00" }
  },
  "current_task": {
    "agent": "matrix",
    "action": "douyin_browse",
    "started_at": "2026-05-15T14:25:00+08:00"
  },
  "resource": {
    "cpu_pct": 23,
    "mem_pct": 62,
    "disk_free_gb": 180
  },
  "network": {
    "online": true,
    "local_ip": "192.168.31.101",
    "last_sync": "2026-05-15T14:35:01+08:00"
  },
  "version": {
    "agentos": "4.0.0",
    "guardd": "1.0.0"
  },
  "stats_day": {
    "events_emitted": 5,
    "tasks_completed": 2,
    "errors": 0
  },
  "heartbeat_at": "2026-05-15T14:35:02+08:00"
}
```

**存储位置**：`agent-sync/04_memory/cross_machine/status/{hostname}/heartbeat.json`

**判定离线**：其他机器读取时，若 heartbeat_at 超过 15 分钟前，视为 offline。

---

### ② 知识库双向同步

**需求**：各主机发现总知识库或关键内容更新时，可以主动同步推送拉取。

**设计**：

#### 拉（Pull）—— 主知识库更新后传播到各机

```
总知识库更新 (git push / NutSync)
       │
       ▼
agent-sync/03_knowledge/ 变化
       │
       ▼
各机 guardd 检测到本地 03_knowledge/ 有更新
       │
       ▼
执行: cd agent-sync && git pull   (或 NutSync 自动同步)
```

**实际上 NutSync 自动同步了文件级变更，guardd 只需要做两件事**：
1. 检测 03_knowledge/ 的 CHANGELOG.md 或 git 记录是否有新变更
2. 如果有 → 发出 `knowledge_updated` 事件

#### 推（Push）—— 本机新知识提交到收件匣

```
本机产生新知识/素材
       │
       ▼
写入 agent-local/submissions/  (已有流程)
       │  guardd 定期扫描
       ▼
复制/移动到 agent-sync/03_knowledge/01_submissions/{hostname}/
       │  NutSync 自动同步到所有机器
       ▼
主知识机 (chengzige-macmini) 的 inbox_refine 任务
检查 submissions/ → 提纯 → 归档到知识库
```

#### 知识变更通知

```json
// events/2026-05-15/0005_chengzige_knowledge_updated.json
{
  "event_id": "evt_20260515_005",
  "source_host": "chengzige-macmini",
  "source_agent": "knowledge_manager",
  "event_type": "knowledge_updated",
  "timestamp": "2026-05-15T14:30:00+08:00",
  "summary": "知识库新增 3 个文件: AI视频提示词系统 v1.0",
  "details": {
    "new_files": 3,
    "updated_files": 1,
    "topic": "AI视频提示词系统"
  }
}
```

**关键**：知识同步不经特殊通道。NutSync 已经做了文件级同步。guardd 负责：检测变更 → 通知 + 触发本地 pull（如果用的是 git）。已有 `collect_to_inbox` + `inbox_refine` 技能完全可复用。

---

### ③ 自动升级机制

**需求**：关键组件升级后，各级自动升级。

**设计**：

#### 版本清单文件

```
agent-sync/04_memory/cross_machine/knowledge/versions.json
```

```json
{
  "last_updated": "2026-05-15T12:00:00+08:00",
  "components": {
    "agentos_core": {
      "version": "4.1.0",
      "changelog": "修复跨机器事件总线的并发写入冲突",
      "upgrade_script": "00_bootstrap/upgrade_agentos.sh",
      "breaking": false
    },
    "tool_ave": {
      "version": "2.1.0",
      "changelog": "新增 Kling LipSync 集成",
      "upgrade_script": "05_tools/09_ave/scripts/upgrade.sh",
      "breaking": false
    },
    "tool_matrix": {
      "version": "1.3.0",
      "changelog": "新增双号并行支持",
      "upgrade_script": "05_tools/07_matrix/scripts/upgrade.sh",
      "breaking": true
    }
  }
}
```

#### 升级流程

```
主知识机发布新版本 (修改 versions.json)
       │  坚果云同步
       ▼
各机 guardd 检测到 versions.json 变化
       │  对比本机版本
       ▼
有更新？
  ├── No → 跳过
  └── Yes → breaking change?
       ├── Yes → 写入事件: upgrade_pending (需用户确认)
       │          Dashboard 显示"升级待确认"
       │          用户确认后 → 执行升级脚本
       └── No  → 自动执行 upgrade_script
                  写入事件: upgrade_complete
```

#### 升级事件

```json
{
  "event_id": "evt_20260515_006",
  "source_host": "redmi-12c",
  "source_agent": "guardd",
  "event_type": "upgrade_complete",
  "summary": "tool_matrix 从 1.2.0 升级到 1.3.0",
  "details": {
    "component": "tool_matrix",
    "from": "1.2.0",
    "to": "1.3.0",
    "auto": true
  }
}
```

---

### ④ 记忆提炼上报

**需求**：每台机器的本地记忆中，与硬件/本机环境不关联的记忆知识，可以直接提炼上报到主机的收件匣，由主知识管理主机统一归档到总知识库。

**设计**：

#### 筛选规则

```
agent-local/memory/ 中的原始记忆
       │  guardd 的 memory triage 模块处理
       ▼
┌─────────────────────────────────────────────┐
│  三条筛选规则                                │
│                                             │
│  ① 包含本机路径名 / hostname / IP → ❌ 丢弃  │
│  ② 包含本地配置/密钥特征 → ❌ 丢弃            │
│  ③ 通用的方法论 / 概念 / 经验 → ✅ 保留       │
└─────────────────────────────────────────────┘
       │
       ▼
保留的内容 → 格式化提炼 → 写入 submissions/
```

#### 记忆提炼上报格式

```markdown
---
source_host: redmi-12c
source_agent: claw
extracted_at: 2026-05-15T14:30:00+08:00
category: methodology/kling-prompt
confidence: 0.85
original_ref: agent-local/memory/daily/2026-05-14.md
---

# [提炼] Kling 长镜头提示词的关键控制参数

## 内容
在使用 Kling API 生成长镜头时，以下参数组合效果最佳：
- duration: 10 秒（超 10 秒质量下降明显）
- camera_motion: "slow_push" + "orbit" 的组合
- 负面提示词不要超过 3 个，否则画面容易崩

## 原因
此条是从多次生成测试中提炼的经验，不依赖任何本机环境或配置。
```

#### 主机的处理流程

```
各机 submissions/ 中的记忆提炼稿
       │  NutSync 同步
       ▼
主知识机 (chengzige-macmini)
       │  guardd 检测到新提交
       ▼
调用 inbox_refine 技能
       │  去重  →  分类  →  归档
       ▼
写入 03_knowledge/ 相应目录
发出 knowledge_updated 事件
```

---

### ⑤ 加密通讯通道

**需求**：API 密钥/敏感配置不放同步文件夹，避免将来软件发布泄密。通过加密通道传递，需要调用时可拿到。

**设计**：

#### 密钥体系

```
┌───────────────────────────────────────┐
│          每台机器独立密钥对              │
│                                       │
│  公钥 → registry/{hostname}_pub.pem   │  ← agent-sync/ (公开)
│  私钥 → identity/secrets/private.pem  │  ← agent-local/ (绝不共享)
│                                       │
│  对称密钥 (AES-256, 用于加密大文件)     │
│  → identity/secrets/aes.key           │  ← agent-local/
└───────────────────────────────────────┘
```

#### 密钥初始化

```
init.sh 运行时:
  1. 生成 RSA-4096 密钥对
  2. 写入 agent-local/identity/secrets/private.pem
  3. 写入 agent-local/identity/secrets/aes.key (随机 32 字节)
  4. 写入 agent-sync/cross_machine/registry/{hostname}_pub.pem
```

#### 加密消息传递

```
Machine A 需要给 Machine B 传递敏感信息
       │
       ▼
Step 1: 从 registry/ 读取 Machine B 的公钥
       │
Step 2: 用 B 的公钥加密消息 (RSA-OAEP)
       │  (消息内容对第三方不可读)
       ▼
Step 3: 将加密内容写入 agent-sync/cross_machine/encrypted/
        格式: {target_host}_{timestamp}.enc
        (注意：内容已加密，放在 agent-sync 也不会泄密)
       │
Machine B 读取 encrypted/ 中 target_host 为自己的文件
       │
       ▼
Step 4: 用本地私钥解密
        明文写入 agent-local/identity/secrets/received/
```

#### 加密消息文件格式

```json
{
  "encrypted": true,
  "version": 1,
  "source_host": "redmi-12c",
  "target_host": "chengzige-macmini",
  "timestamp": "2026-05-15T14:30:00+08:00",
  "algorithm": "RSA-OAEP",
  "ciphertext_b64": "base64_encoded_encrypted_content...",
  "signature_b64": "base64_encoded_signature..."
}
```

#### 安全边界说明

| 内容 | 存储位置 | 安全性 |
|------|---------|--------|
| 公钥 | agent-sync/registry/ | ✅ 公开安全 |
| 加密消息 | agent-sync/encrypted/ | ✅ 有私钥才能解密 |
| 私钥 | agent-local/identity/secrets/ | ✅ 仅本机可读 |
| API Key 明文 | agent-local/identity/secrets/ | ✅ 不同步 |
| 解密后内容 | agent-local/identity/secrets/received/ | ✅ 不同步 |

**用户放心点**：即使将来 `agent-sync/` 发布成开源项目或示例代码，里面只有公钥和加密内容，没有敏感信息。

---

### ⑥ 隔空投递 / 直接传输

**需求**：苹果电脑之间距离近时，可以直接用 AirDrop 互传大文件/素材，不需要走坚果云。

**设计**：

#### 直接传输架构

```
Machine A (有 45MB 视频)          Machine B (需要这个视频)
       │                                  │
       │  emit event: asset_available     │
       │  (含文件大小 + 路径 + 校验和)      │
       │                                  │
       │  Dashboard 显示: "B 有一个可用素材" │
       │                                  │
       │  ◄── 用户确认传输 ───────────────│
       │                                  │
       ▼                                  ▼
   传输方式决策:
       │
       ├── 同一局域网? ──► SSH rsync / Bonjour 直传
       │                    (scp file user@B:/path/)
       │
       ├── 苹果生态且已配对? ──► AirDrop (osascript)
       │                           (显示分享面板，需用户点确定)
       │
       └── 以上都不行? ──► 走任务协作 (tasks/)
                              B 任务: copy_via_network
```

#### 传输方式对比

| 方式 | 速度 | 自动化程度 | 前提条件 |
|------|------|-----------|---------|
| **SSH rsync** | 千兆局域网 ~100MB/s | 全自动 (需配 SSH Key) | 同子网、SSH 已配置 |
| **AirDrop** | ~20MB/s | 半自动 (需用户点确认) | 同 Apple ID、蓝牙/WiFi |
| **Bonjour + HTTP** | 同局域网 | 全自动 | 目标机运行接收服务 |
| **坚果云同步** | 取决于上行带宽 | 全自动 | 但大文件慢且占流量 |

#### 实现方案（推荐 SSH rsync）

**前提**：每台机器的公钥加入其他机器的 authorized_keys。init.sh 可做一次配置。

```
Machine A 上执行:
  rsync -avP --progress /path/to/video.mp4 \
    user@machine-b.local:/path/to/destination/

成功后 emit event: transfer_complete
```

#### AirDrop 触发 (可用时)

macOS 的 AirDrop 没有完整 CLI，但可以打开 AirDrop 分享面板：

```bash
# 在 Finder 中打开 AirDrop 窗口
open /System/Library/CoreServices/Finder.app

# 或者用 osascript 打开 AirDrop
osascript -e 'tell application "Finder" to open location "x-apple-remotemanagement://..."'
```

**实际推荐**：对于全自动化场景，用 SSH rsync。AirDrop 作为手动备选（用户从 Dashboard 点击"发送到…"时触发 Finder 分享面板）。

---

### ⑦ 守护进程 (guardd)

**需求**：以上所有操作做成具体代码，以守护进程/定时任务持续运行，减少 token 消耗，做到程序化、一直存在。

**设计**：

#### guardd 架构

```
┌─────────────────────────────────────────────────────┐
│                   guardd (守护进程)                   │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │              主循环 (每 300 秒)               │    │
│  │                                             │    │
│  │  ① heartbeat()  → 写 status/{host}/hb.json  │    │
│  │  ② check_tasks() → 读 tasks/ 取自己的任务    │    │
│  │  ③ check_upgrades() → 读 versions.json      │    │
│  │  ④ memory_triage() → 扫描本地记忆提炼提交     │    │
│  │  ⑤ check_knowledge() → 检测知识库变更        │    │
│  │  ⑥ check_encrypted() → 读 encrypted/ 解密   │    │
│  │  ⑦ cleanup() → 清理过期事件/任务文件          │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │          事件监听 (持续运行)                   │    │
│  │  • 监听本地 Agent 的 event 调用              │    │
│  │  • 转发到 events/ 目录                       │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

#### 实现方式

```
agent-sync/05_tools/00_setup/guardd/
├── guardd.py              ← 主守护进程
├── modules/
│   ├── heartbeat.py       ← 状态上报
│   ├── task_worker.py     ← 任务处理
│   ├── upgrade_checker.py ← 版本检查 + 升级执行
│   ├── memory_triage.py   ← 记忆提炼筛选
│   ├── knowledge_sync.py  ← 知识库变更检测
│   ├── encrypted_channel.py ← 加密消息收发
│   └── transfer.py        ← 文件传输 (SSH/AirDrop)
├── scripts/
│   └── install.sh         ← 安装为 launchd/定时任务
└── README.md
```

#### 安装方式

通过 launchd 安装为系统级守护进程，机器启动即运行：

```bash
# install.sh 自动执行:
# 1. 生成 plist 文件
# 2. 加载到 launchctl
# 3. 启动 guardd

# plist 内容示例:
# <key>StartInterval</key>
# <integer>300</integer>   ← 5 分钟一次
```

或者降级方案 —— crontab：

```bash
# crontab -e
*/5 * * * * /path/to/venv/python /path/to/guardd.py
```

#### guardd 日志

```
agent-local/runtime/guardd/
├── guardd.log              ← 运行日志
├── last_run.json           ← 上次运行结果
└── errors.log              ← 仅错误
```

---

## 完整目录结构总览

```
agent-sync/04_memory/cross_machine/
├── registry/                    ← ① 机器注册
│   ├── 7kecheng.json           (已有)
│   ├── chengzige.json          (已有)
│   ├── 7kecheng_pub.pem        ← ⑤ 公钥 (新增)
│   └── chengzige_pub.pem       ← ⑤
│
├── events/                      ← ① 事件总线
│   ├── 2026-05-15/
│   │   ├── 0001_redmi-12c_ave_complete.json
│   │   ├── 0002_5kecheng_matrix_daily.json
│   │   └── 0003_chengzige_knowledge_updated.json
│   └── 2026-05-16/
│
├── status/                      ← ① 状态机
│   ├── redmi-12c/
│   │   └── heartbeat.json      (5-10min 覆盖写)
│   ├── chengzige/
│   │   └── heartbeat.json
│   └── 5kecheng-air/
│       └── heartbeat.json
│
├── tasks/                       ← 跨机任务协作
│   ├── pending/                 ← 待处理
│   ├── in_progress/             ← 处理中
│   └── completed/               ← 已完成
│
├── encrypted/                   ← ⑤ 加密消息 (内容已加密)
│   ├── pending/
│   └── history/
│
└── knowledge/                   ← ②③ 知识同步 & 升级
    └── versions.json            ← ③ 版本清单

agent-local/
├── identity/
│   └── secrets/                 ← ⑤ 密钥 (永不共享)
│       ├── private.pem
│       ├── aes.key
│       └── received/            ← 解密后的消息
│
├── memory/                      ← 本地记忆
│   ├── daily/
│   └── raw/
│
├── submissions/                 ← ②④ 提交箱
│   ├── memory_triage/           ← ④ 记忆提炼上报
│   └── knowledge/               ← ② 新知识提交
│
└── runtime/
    └── guardd/                  ← ⑦ 守护进程日志
        ├── guardd.log
        ├── last_run.json
        └── errors.log
```

---

## 实施路线图

### Phase 0：基础设施 (0.5h)

| 事项 | 产出 |
|------|------|
| 创建 cross_machine/events/ status/ tasks/ encrypted/ knowledge/ 目录 | 目录结构 |
| 编写 `emit_event.py` 工具脚本 | 单文件脚本 |
| 编写 `encrypt_message.py` / `decrypt_message.py` 工具脚本 | 单文件脚本 |
| 初始化各机密钥对 (集成到 init.sh) | 密钥文件 |

### Phase 1：guardd 守护进程 (2h)

| 事项 | 产出 |
|------|------|
| 实现 heartbeat 模块 | heartbeat.py |
| 实现 task_worker 模块 | task_worker.py |
| 实现 emit_event 集成 | 主循环中调用 |
| 实现 memory_triage 模块 | memory_triage.py |
| 编写 install.sh | 安装脚本 |
| 测试 5 分钟循环 | 验证 heartbeat 正常上报 |

### Phase 2：知识协同 (1h)

| 事项 | 产出 |
|------|------|
| 实现 knowledge_sync 模块 | knowledge_sync.py |
| 实现 upgrade_checker 模块 | upgrade_checker.py |
| 创建 versions.json 初始版本 | 版本清单 |
| 编写知识库变更通知逻辑 | 嵌入 guardd 主循环 |

### Phase 3：加密通讯 + 文件传输 (1h)

| 事项 | 产出 |
|------|------|
| 实现 encrypted_channel 模块 | encrypted_channel.py |
| 实现 SSH rsync 传输 | transfer.py |
| 集成 AirDrop 触发器 (osascript) | transfer.py |

### Phase 4：Dashboard UI (2h)

| 事项 | 产出 |
|------|------|
| 本机详细视图 | Dashboard 本机数据展示 |
| 全局联邦视图 | 多机状态、事件、任务展示 |
| 加密消息收发界面 | 加密通讯操作入口 |
| 文件传输界面 | 跨机素材传输操作入口 |

---

## 关键设计决策总结

| 决策点 | 选择 | 原因 |
|--------|------|------|
| 守护进程语言 | Python | 与现有 AgentOS 技术栈一致 |
| 调度方式 | launchd (macOS) | 系统级稳定，机器启动即运行 |
| 状态更新频率 | 5-10 分钟 | 平衡同步负载 vs 信息实时性 |
| 离线判定阈值 | 15 分钟 | 3 个心跳周期 |
| 加密算法 | RSA-4096 + AES-256 | 成熟、Python 原生支持 |
| 大文件传输 | SSH rsync (首选) / AirDrop (备选) | SSH 全自动化，AirDrop 需用户交互 |
| 知识同步 | 复用 NutSync + guardd 检测 | 不重复造轮子 |
| 版本升级 | 自动/手动 双模 | breaking change 需用户确认 |
| 记忆筛选 | 规则引擎 (非 AI) | 避免 token 消耗，程序化执行 |

---

## 补充说明

### 为什么加密消息放在 agent-sync 也没问题

用户担心"将来软件发布忘记清理敏感信息"。设计上：
- agent-sync/ 里的 encrypted/ 目录存储的是**已用收件方公钥加密**的内容
- 没有收件方私钥 → 内容不可读
- 私钥永远在 agent-local/identity/secrets/，不同步
- 即使整个 agent-sync/ 开源，泄露的也只是一堆公钥和加密数据，没有实质风险

### AirDrop vs SSH 的选择逻辑

| 场景 | 推荐方式 |
|------|---------|
| 两台机器在同一局域网且有 SSH Key | SSH rsync (全自动) |
| 临时需要传文件，SSH 未配置 | AirDrop (半自动, 需点确认) |
| 距离近但不在同一局域网 | AirDrop (蓝牙直连) |
| 大文件 (500MB+) | SSH rsync (速度更快) |
| 批量小文件 | SSH rsync |

### Token 消耗说明

guardd 的设计目标就是**程序化、低 token 消耗**：
- 所有决策逻辑用规则引擎（Python if/else），不调用 LLM
- 记忆提炼也用规则筛选（关键词匹配 + 模式识别），不是 AI 总结
- 只在知识库归档环节（inbox_refine）用到 LLM，但那已经是现有流程了
- guardd 运行的 7 个模块全是确定性代码，不消耗任何 API token

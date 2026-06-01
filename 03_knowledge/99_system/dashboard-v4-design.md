---
title: "Dashboard v4.0 — AgentOS 联邦控制中心设计规范"
version: "4.0.0"
last_updated: "2026-05-18"
status: "draft"
author: "Claw (AgentOS)"
supersedes: "Dashboard v3.x"
---

# Dashboard v4.0 — AgentOS 联邦控制中心

## 一、设计哲学

```
不是"一个看板", 而是"联邦控制中心"。
不是"展示数据", 而是"统览+操作"。
不是"单机工具", 而是"跨机协同中枢"。
```

### 核心原则

1. **每台机器一个 Dashboard** → 但看到的数据是一致的（从 cross_machine 读）
2. **每台机器为自己的插件负责** → 本地路径本地配, 共享数据写 cross_machine
3. **插件是"数据线"不是"应用"** → 插件只负责采集+汇总, 不负责业务逻辑
4. **所有模块标注"属于哪台机器"** → 同样养号流程, 各机器状态分开显示
5. **新增模块 = 写一个 plugin.py** → 不需要改 Dashboard 核心代码

---

## 二、数据流架构

```
┌─ Machine A ──────────────────────────────────────┐
│                                                    │
│  模块(本地) → plugin.py 采集                         │
│     ├── 读本地配置 (agent-local/)                   │
│     ├── 执行本地操作                                 │
│     └── 写共享数据 → cross_machine/data/{plugin}/   │
│                                                    │
│  Dashboard(本地) ← 读共享数据                        │
│     ├── cross_machine/data/{plugin}/                │
│     ├── cross_machine/status/live/ (心跳)            │
│     └── cross_machine/registry/ (机器注册信息)       │
│                                                    │
└────────────────────────────────────────────────────┘
                         ▲
                         │ 所有机器读写同一份数据
                         ▼
┌─ Machine B ──────────────────────────────────────┐
│  同上                                              │
│  模块不同 → 写入不同的 cross_machine/data/ 子目录   │
└────────────────────────────────────────────────────┘
```

### 关键结论

| 数据类型 | 存哪里 | 谁写入 | 谁读取 |
|---------|--------|--------|--------|
| **机器心跳** | cross_machine/status/live/{uid}.json | guardd (每台) | Dashboard (所有) |
| **机器注册** | cross_machine/status/live/_registry.json | Dashboard push API | Dashboard (所有) |
| **插件共享数据** | cross_machine/data/{plugin_name}/{uid}.json | 各机器插件 | Dashboard (所有) |
| **本地私有数据** | agent-local/dashboard/{plugin_name}/ | 本地插件 | 本地 Dashboard |
| **跨机任务** | cross_machine/tasks/pending/{id}.json | Dashboard/手动 | guardd (目标机) |
| **事件记录** | cross_machine/events/{date}/{uuid}.json | guardd | Dashboard |

---

## 三、插件规范 v2

### 3.1 目录结构

每个插件是一个独立的 Python 文件，放在 `05_tools/10_dashboard/plugins/` 下：

```
plugins/
├── __init__.py
├── base.py              ← 插件基类 (框架)
├── guardd.py            ← 联邦机器状态 (内置)
├── ave.py               ← AVE 视频工厂 (内置)
├── matrix.py            ← Matrix 账号矩阵 (内置)
├── collector.py         ← 内容采集 (内置)
├── skills.py            ← 技能树 (内置)
├── knowledge.py         ← 知识库 (内置)
├── automation.py        ← 自动化任务 (内置)
├── tools.py             ← 工具集 (内置)
├── system.py            ← 系统核心 (内置)
└── (未来新增模块直接加在这里)
```

### 3.2 插件基类接口

```python
class DashboardPlugin:
    """插件基类 v2.0 — 联邦控制中心规范"""

    # ── 元信息 (必须定义) ───────────────────────────────────
    name: str = ""              # 唯一标识, 如 "matrix"
    label: str = ""             # 中文名, 如 "账号矩阵"
    icon: str = "📱"           # 图标
    version: str = "1.0.0"     # 插件版本
    description: str = ""      # 简要说明
    order: int = 99            # 排序

    # ── 核心方法 ────────────────────────────────────────────

    def summary(self, machines: list[str]) -> dict:
        """
        概览数据 (首页卡片用)
        machines: 当前有哪些机器 (从 _registry.json 读)
        返回结构:
        {
            "总账号": 8,
            "今日发帖": 3,
            "各机器": {
                "chengzigedeAir": {"账号":5, "有效":4},
                "Redmi-12C": {"账号":3, "有效":2}
            }
        }
        """
        raise NotImplementedError

    def detail(self, machine: str = "") -> dict:
        """
        详细面板数据
        machine: 如果为空, 返回所有机器的汇总; 否则返回指定机器
        返回结构: (各插件自定义)
        """
        raise NotImplementedError

    def actions(self) -> list[dict]:
        """
        可执行操作列表
        返回:
        [{"name":"刷新", "method":"POST", "endpoint":"/api/plugins/matrix/refresh"}]
        """
        return []

    def write_shared_data(self, data: dict):
        """将本插件数据写入 cross_machine, 供其他机器读取"""
        uid = _resolve_uid()
        path = CROSS_MACHINE / "data" / self.name / f"{uid}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "plugin": self.name,
            "version": self.version,
            "machine_uid": uid,
            "hostname": HOSTNAME,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }))
```

### 3.3 插件数据写入规范

每个插件写入 `cross_machine/data/` 的数据必须包含以下字段：

```json
{
    "plugin": "matrix",
    "version": "1.0.0",
    "machine_uid": "4cf443bc-ff14-4ed9-885b-b04c5326304d",
    "hostname": "chengzigedeAir",
    "timestamp": "2026-05-18T01:30:00+00:00",
    "data": { /* 插件自定义 */ }
}
```

**关键规则**：
- `machine_uid` 必填 — Dashboard 按此字段去重
- `hostname` 作为显示名 — 但去重按 UID 而非 hostname
- `timestamp` 用于判断数据是否过期（超过 24 小时未更新的标灰）
- `version` 用于版本兼容性判断

---

## 四、路径规则

### 4.1 路径常量

所有插件通过 `base.py` 提供的常量解析路径，禁止硬编码：

```python
# base.py 提供
AGENT_SYNC = Path.home() / "workbuddy-agent-os" / "agent-sync"
AGENT_LOCAL = Path.home() / "workbuddy-agent-os" / "agent-local"
CROSS_MACHINE = AGENT_SYNC / "04_memory" / "cross_machine"
DASHBOARD_LOCAL = AGENT_LOCAL / "runtime" / "dashboard"  # 各机私有
```

### 4.2 路径使用规则

| 场景 | 路径 | 示例 |
|------|------|------|
| 读共享数据 | `CROSS_MACHINE / "data" / {plugin} / {uid}.json` | 所有机器相同 |
| 读本地配置 | `AGENT_LOCAL / "tools" / {module} / "config" / "local.yaml"` | 各机不同 |
| 写共享数据 | `CROSS_MACHINE / "data" / {plugin} / {uid}.json` | 按 UID 区分 |
| 写本地缓存 | `DASHBOARD_LOCAL / "cache" / {plugin} /` | 各机私有 |
| 读任务 | `CROSS_MACHINE / "tasks" / "pending" / {id}.json` | 所有机器可见 |
| 读注册表 | `CROSS_MACHINE / "status" / "live" / "_registry.json"` | 所有机器可见 |

---

## 五、机器感知设计

### 5.1 身份栏

Dashboard 顶部始终显示：

```
📡 chengzigedeAir | UID: 4cf443bc... | 角色: 主工作站 | 仓库: mac-agent-os | v1.1.0
```

- **hostname**: 从 `cached_hostname` 读取, 不会因 IP 变化而变
- **UID**: 从 `agent-local/identity/machine_uid` 读取, 全局唯一
- **角色**: 从 `cross_machine/registry/{name}.json` 读取 role 字段
- **仓库/版本**: 从 Git 读取

### 5.2 插件视图的机器标签

每个插件展示数据时，每条记录标注来源机器：

```
┌─ Matrix 账号矩阵 ──────────────────────────────┐
│                                                  │
│  chengzigedeAir (主工作站)                        │
│  ├─ 抖音号A: ✅ 在线  今日已发 3 篇               │
│  ├─ 抖音号B: ✅ 在线  今日已发 1 篇               │
│  └─ 抖音号C: ❌ 离线  未操作 2天                  │
│                                                  │
│  Redmi-12C (采集节点)                             │
│  ├─ 抖音号X: ✅ 在线  今日已发 5 篇               │
│  └─ 抖音号Y: ✅ 在线  今日已发 2 篇               │
│                                                  │
└──────────────────────────────────────────────────┘
```

### 5.3 自动化任务的机器归属

自动化任务记录格式必须包含：

```json
{
    "id": "sync_Redmi-12C_20260517",
    "name": "袁本初每日采集",
    "source_machine": "chengzigedeAir",     // 谁创建的
    "target_machine": "Redmi-12C",           // 谁执行的
    "source_uid": "4cf443bc-...",
    "target_uid": "a1b2c3d4-...",
    "status": "pending | running | completed | failed",
    "created_at": "...",
    "completed_at": "...",
    "result": ""
}
```

---

## 六、9 个内置插件明细

### P0 核心插件（优先实现）

| # | 插件 | name | 数据源 | 各机器数据 |
|---|------|------|--------|-----------|
| 1 | **🖥 联邦机器** | guardd | cross_machine/status/ + 心跳 | ✅ 每台机器各自心跳 |
| 2 | **🎬 AVE 工厂** | ave | 本地: agent-local/runtime/ave/ + cross_machine/data/ave/ | ✅ 各机独立写入 |

### P0 新增: 矩阵养号

| # | 插件 | name | 数据源 | 各机器数据 |
|---|------|------|--------|-----------|
| 3 | **📱 Matrix 矩阵** | matrix | local.yaml 账号配置 + Blueprint 执行日志 | ✅ 各机的账号不同 |

**数据采集路径**：
```
本地: agent-local/tools/matrix/config/local.yaml    ← 各机自己的矩阵账号
      agent-local/runtime/matrix/                    ← 各机执行日志
共享: cross_machine/data/matrix/{uid}.json           ← 概览汇总
```

**Matrix 插件 summary() 输出示例**：
```json
{
    "总账号": 8,
    "在线": 6,
    "今日发帖": 15,
    "各机器": {
        "chengzigedeAir": {"账号":5,"在线":4,"今日发帖":10},
        "Redmi-12C": {"账号":3,"在线":2,"今日发帖":5}
    }
}
```

### P1 插件

| # | 插件 | name | 数据源 | 各机器数据 |
|---|------|------|--------|-----------|
| 4 | **📡 内容采集** | collector | cross_machine/events/ + 本地 submission | ✅ 各机采集进度 |
| 5 | **🧩 技能树** | skills | ~/.workbuddy/skills/ 目录+技能配置 | ✅ 各机技能列表不同 |
| 6 | **📚 知识库** | knowledge | 03_knowledge/ 文件树 | ❌ 知识库共享(10_concepts等) + 各机提交箱 |
| 7 | **⏰ 自动化任务** | automation | cross_machine/tasks/ + WorkBuddy DB | ✅ 各机任务不同 |
| 8 | **🔧 工具集** | tools | 05_tools/ 目录树 | ✅ 各机工具安装不同 |
| 9 | **⚙️ 系统核心** | system | Git + 系统信息 | ✅ 各机信息不同 |

---

## 七、审计与自检

### 7.1 身份一致性 (当前已知问题 ✅ 已修复)

| 问题 | 状态 | 说明 |
|------|------|------|
| hostname 随 IP 变 | ✅ 已修复 | guardd 缓存 hostname 到 cached_hostname 文件 |
| UID 为主键 | ✅ 已修复 | 所有存储用 UID 而非 hostname |
| 机器去重 | ✅ 已修复 | 从 _registry.json 按 UID 遍历 |

### 7.2 潜在风险与规避

| 风险 | 影响 | 规避方案 |
|------|------|---------|
| **数据格式冲突** | 两台机器同一插件输出不同结构 | version 字段 + summary 输出结构规范化 |
| **数据过期** | 机器宕机后旧数据仍显示 | timestamp + TTL: 24h未更新自动标灰 |
| **权限混乱** | 某机器误写其他机器的数据 | 按 UID 文件名隔离, 不可越界 |
| **插件缺失** | Dashboard 加载失败 | try/except 包裹, 单个插件崩不影响其他 |
| **路径硬编码** | 迁移/换机后路径失效 | 全部通过 base.py 常量, 不出现绝对路径 |
| **目录结构变更** | 新增目录后旧的引用失效 | cross_machine 目录结构存档在 CORE-ARCHITECTURE.md |

### 7.3 无法执行的风险

| 风险 | 原因 | 解决方案 |
|------|------|---------|
| **跨机实时操作** | Dashboard 通过 API 操作其他机的进程 | 降级为 "创建任务 → wait → 轮询结果" |
| **插件自动部署** | 新插件需要手动 scp/rsync | 通过 git push + guardd pull 自动分发 |
| **跨机 SSH 执行** | 无 SSH 互通, 防火墙策略 | 用 cross_machine/tasks/ 文件作为消息队列 |

### 7.4 边缘情况

| 场景 | 行为 |
|------|------|
| 某机器从未推送过数据 | 该机器在 Dashboard 标 "未连接" |
| 某机器推送后宕机 | 数据保留 24h, 超时后标灰 |
| 两台机器 UID 冲突 | 不可能, UUID4 生成, 冲突概率极低 |
| 插件版本升级 | summary() 保证向后兼容, 新增字段可选 |
| 网络分区 | 各机 Dashboard 独立运行, 恢复后自动同步 |

---

## 八、实施计划

### Phase 1: 框架改造 (约1小时)
- [ ] 重写 `base.py` → 插件基类 v2.0
- [ ] 新增 `cross_machine/data/` 目录结构
- [ ] 新增 `DASHBOARD_LOCAL` 本地缓存目录
- [ ] 前端改造: 身份栏 + 侧边栏动态渲染

### Phase 2: 核心插件 (约1.5小时)
- [ ] guardd 插件 → 适配 v2 规范 + 机器标签
- [ ] matrix 插件 → 读取 local.yaml + 写入共享
- [ ] ave 插件 → 适配 v2 规范 + 各机生产统计

### Phase 3: 系统插件 (约1.5小时)
- [ ] skills / knowledge / collector / automation / tools / system
- [ ] 时间线/热力图/告警适配

### Phase 4: 端到端验证 (约0.5小时)
- [ ] 跨机数据一致性测试
- [ ] 新机首次注册全流程
- [ ] 插件报错隔离测试

---

## 九、附录

### 9.1 各机差异点速查

| 维度 | chengzigedeAir (主工作站) | Redmi-12C (采集节点) | 其他机器 |
|------|-------------------------|---------------------|---------|
| 角色 | master | worker | worker |
| AVE工厂 | ✅ 可生产 | ❌ 无 | 按需 |
| Matrix | 5个账号 | 3个账号 | 按需 |
| 采集工具 | 浏览器采集 | 无浏览器 | 按需 |
| Dashboard | ✅ 启动 | ✅ 启动 | ✅ 启动 |

### 9.2 相关文档

- CORE-ARCHITECTURE.md — 系统架构宪法
- content-collection-pipeline.md — 采集链路规范
- SKILLS-CATALOG.md — 技能体系
- guardd 设计文档 — 守护进程

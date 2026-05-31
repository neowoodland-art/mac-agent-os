# AgentOS 系统更新体系规范

> 版本：v1.0 | 最后更新：2026-05-03
> 本文档定义所有类型的更新机制、夜间自动化任务、跟踪页面体系和多机同步流程。

---

## 一、系统有哪几类更新

```
AgentOS 更新体系
    │
    ├── ① 知识库更新  → 知识卡片新增/修改/归档
    ├── ② 系统配置更新 → SOUL.md/IDENTITY/USER 修改
    ├── ③ 技能更新    → SKILL.md 新增/修改
    ├── ④ 工具更新    → 05_tools/ 脚本新增/修改
    └── ⑤ 自动化更新  → 定时任务新增/修改
```

---

## 二、夜间自动化任务（每日定时）

| 时间 | 任务 | 脚本 | 做什么 | 影响 |
|------|------|------|--------|------|
| 02:00 | 每日记忆提炼 | `daily_digest.py` | 从对话中提取关键事实 → L2 facts.db + L1 索引 | 04_memory/ |
| 02:30 | 提交箱归集 | `collect_to_inbox.py` | 01_submissions/ → 00_inbox/ | 03_knowledge/ |
| 03:00 | 收件箱提纯 | `inbox_refine.py` | 00_inbox/ → AI分类 → 归档 → 更新README + CHANGELOG | 03_knowledge/ |

### 当前流程的问题

```
收集内容 → 01_submissions/ → 02:30归集 → 00_inbox/ → 03:00提纯 → 归档
                                                                  ↓
                                                          更新 README 统计
                                                          更新 CHANGELOG
```

**问题1**：READ ME.md 统计依赖于 inbox_refine 脚本，但该脚本可能因 oMLX 稳定性问题失败，导致统计不准。

**问题2**：向量库重建是手动的。知识库内容变化后，向量索引不会自动更新，语义搜索搜不到新内容。

**问题3**：无"变化通知"。每次自动化跑完，你不知道哪些文件变了。

---

## 三、跟踪页面体系

系统需要 **4 个主要页面** 追踪所有变化：

### 页面1：知识库变更日志

**文件**：`03_knowledge/CHANGELOG.md`
**用途**：记录知识库内容变化（新增/修改/归档）
**更新方式**：手动维护 + inbox_refine 自动追加

```markdown
## 2026-05-03

### 新增
- [concept] 命名现实的力量 → 10_concepts/ (KB-20260503-003)
- [system] 内容收集全链路规范 v2.0 → 99_system/pipelines/

### 归档
- [test] 测试LLM分类器 → 90_archive/deprecated/

### 变更
- README.md 统计数字更新
```

### 页面2：README 首页

**文件**：`03_knowledge/README.md`
**用途**：知识库统计 + 导航 + 快速链接
**更新方式**：手工维护

### 页面3：系统操作速查手册

**文件**：`01_core/MAINTENANCE_GUIDE.md`
**用途**：所有系统级操作指南（init/sync/upgrade/角色切换）
**更新方式**：系统配置变化时同步更新

### 页面4：版本追踪文件

**文件**：`.workbuddy/.config-version.json`
**用途**：自动记录身份文件部署版本
**更新方式**：`apply-config.sh` 自动生成

---

## 四、各变更类型的传播链路

### ① 知识库更新

```
手动变更: 02_skills/inbox_refine/SKILL.md → 新增/修改知识卡片
                                                                  ↓
是否需要同步到其他机器? → 否（每台机器知识库独立，Git 同步后直接可见）
                                                                  ↓
是否需要额外操作?       → 其他机器 git pull 即可
                         → 如需向量搜索，重建索引: agentos rebuild-vector
```

### ② 系统配置更新

```
手动变更: 01_core/SOUL.md / IDENTITY.md / USER.md
                                                                  ↓
是否需要同步? → 是（Git 同步文件）
                                                                  ↓
本机生效:    → bash apply-config.sh → 重启 WorkBuddy
其他机器生效: → git pull → bash apply-config.sh → 重启 WorkBuddy
                                                                  ↓
版本追踪:    → .config-version.json 自动记录部署时间 + 文件 hash
```

### ③ 技能更新

```
手动变更: 02_skills/xxx/SKILL.md + 脚本文件
                                                                  ↓
是否需要同步? → 是（Git 同步文件）
                                                                  ↓
本机生效:    → agentos skill install
其他机器生效: → git pull → agentos skill install
```

### ④ 工具更新

```
手动变更: 05_tools/xxx/ 脚本文件
                                                                  ↓
是否需要同步? → 是（Git 同步文件）
                                                                  ↓
生效方式:    → git pull 即可（脚本直接执行，无需注册）
```

### ⑤ 自动化更新

```
手动变更: WorkBuddy 中创建/修改自动化任务
                                                                  ↓
是否需要同步? → 否（自动化配置在本地 workbuddy.db 中）
其他机器:    → 需要在该机器上单独创建同样的自动化
```

---

## 五、多机同步对照表

| 你的操作 | 这个机器执行 | 其他机器执行 |
|---------|------------|------------|
| 新增知识卡片 | `git push` | `git pull`（直接可见） |
| 修改 SOUL.md | `apply-config.sh` + 重启 | `git pull` + `apply-config.sh` + 重启 |
| 修改技能 | `agentos skill install` | `git pull` + `agentos skill install` |
| 新增工具脚本 | `git push` | `git pull`（直接可用） |
| 修改自动化 | 无（本地 workbuddy.db） | 需在该机器单独修改 |
| 新增知识目录 | `git push` | `git pull`（直接可见） |

---

## 六、"每天晚上更新"到底更新什么

**当前夜间 03:00 的自动化（inbox_refine）做完后**：

✅ 00_inbox/ → AI 分类归档
✅ 写入 10_concepts/ 等对应目录
✅ 更新 CHANGELOG.md
✅ 更新 README.md 统计

**未做（待完善）**：

❌ 重建向量索引（需手动 `agentos rebuild-vector`）
❌ 推送变更到远程（需手动 `git push`）

---

## 七、建议新增：一个"变更通知"机制

目前系统没有"我改了什么需要另一台机器知道"的通知。最低成本的方案：

在 `01_core/` 下增加 `PENDING_SYNC.md`：

```markdown
# 待同步通知

## [2026-05-03] 系统配置变更
- SOUL.md → v4.0 精简版，其他机器需跑 apply-config.sh

## [2026-05-03] 技能变更
- content_processor → v2.0，需 agentos skill install
- collect_to_inbox → v2.0，需 agentos skill install
```

**流程**：
```
本机修改 → 更新 PENDING_SYNC.md → git push
其他机器 git pull → 看到 PENDING_SYNC.md → 按指示执行对应操作 → 清空该文件并推送
```

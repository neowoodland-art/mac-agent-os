# AgentOS —— 多智能体协同操作系统

> 版本 4.0.0 | 最后更新：2026-05-03
> 本文件是系统入口，告诉你 AgentOS 是什么、有什么、怎么用。

---

## 一、什么是 AgentOS

AgentOS 是一个**本机运行的多智能体协同系统**。多台电脑通过 Git 组成智能体联邦：
- 每台机器独立运行自己的 Agent（WorkBuddy）
- 通过 Git 共享知识库、技能、配置
- 各自采集 → 统一提交 → 主机器提纯归档

**一句话**：把你所有电脑的 AI 助手变成一个协同系统。

---

## 二、文档导航图

所有文档分三层，告诉你"想看什么，去哪个文件"：

### 第一层：系统入口（根目录）

| 你想看 | 去这里 |
|--------|--------|
| 这是什么、怎么用（本文件） | `README.md` |
| 系统最近改了什么 | `CHANGELOG.md` |
| Python 依赖清单 | `requirements.txt` |

### 第二层：系统文档（01_core/ + 99_system/）

| 你想看 | 去这里 |
|--------|--------|
| AI 的行为规则/模式切换/安全边界 | `01_core/SOUL.md` |
| 系统身份/设备信息 | `01_core/IDENTITY.md` |
| 用户画像/偏好 | `01_core/USER.md` |
| **如何操作**（init/sync/upgrade/角色切换） | `01_core/MAINTENANCE_GUIDE.md` |
| **更新体系**（夜间任务/变更传播/同步） | `01_core/UPDATE_SYSTEM.md` |
| 加载架构（四管道体系） | `99_system/architecture/loading-architecture.md` |
| 触发词方案（关键词→语义匹配） | `99_system/architecture/trigger-matching-analysis.md` |
| 高阶思维协议 | `99_system/protocols/meta-thinking.md` |
| 跨域联想协议 | `99_system/protocols/cross-domain.md` |
| 卡壳干预协议 | `99_system/protocols/stuck-intervention.md` |
| 知识审查协议 | `99_system/protocols/knowledge-review.md` |
| 内容收集全链路规范 | `99_system/pipelines/content-collection-pipeline.md` |

### 第三层：技能 + 知识库

| 你想看 | 去这里 |
|--------|--------|
| 已安装的技能 | 各技能目录下的 `SKILL.md` |
| 知识库首页（含统计+导航） | `03_knowledge/README.md` |
| 知识库变更日志 | `03_knowledge/CHANGELOG.md` |
| 知识卡片模板 | `99_system/templates/` |
| 知识属性分类表 | `99_system/taxonomies/` |

---

## 三、目录结构速览

```
~/workbuddy-agent-os/agent-sync/
├── README.md, CHANGELOG.md, requirements.txt   ← 系统入口
├── 00_bootstrap/     ← 初始化脚本（init.sh + apply-config.sh）
├── 01_core/          ← 核心配置 + 系统操作手册
├── 02_skills/        ← 技能（每个技能一个目录）
├── 03_knowledge/     ← Obsidian 知识库
│   ├── 00_inbox/     ← 待提纯收件箱
│   ├── 01_submissions/ ← 多机提交箱
│   ├── 10_concepts/  ← 概念知识
│   ├── 20_methods/   ← 方法论
│   ├── 90_archive/   ← 归档
│   └── 99_system/    ← 系统文档
├── 04_memory/        ← 记忆系统（L1-L3）
├── 05_tools/         ← 工具脚本（agentos CLI + 系统工具）
├── 06_runtime/       ← 运行时（缓存等）
├── 07_migration/     ← 迁移打包

~/workbuddy-agent-os/agent-local/   ← 本机专属（不同步）
└── materials/         ← 素材库
```

---

## 四、快速开始（新机器）

```bash
# 1. 克隆仓库
git clone git@gitee.com:babycalf/mac-agent-os.git ~/workbuddy-agent-os/agent-sync

# 2. 一键初始化
cd ~/workbuddy-agent-os/agent-sync && bash 00_bootstrap/init.sh

# 3. 部署身份文件
bash 00_bootstrap/apply-config.sh

# 4. 安装技能
agentos skill install

# 5. 验证
agentos check
```

---

## 五、日常操作

| 操作 | 命令 | 频率 |
|------|------|------|
| 拉取更新 | `git pull` | 每次工作前 |
| 部署配置 | `bash apply-config.sh` | 01_core/ 有变动时 |
| 安装技能 | `agentos skill install` | 02_skills/ 有变动时 |
| 推送本机 | `git push` | 每次工作后 |
| 系统检查 | `agentos check` | 出问题时 |
| 注册到集群 | `agentos register` | 新机器（自动执行） |

> 详细操作手册见 `01_core/MAINTENANCE_GUIDE.md`

---

## 六、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 4.0.0 | 2026-05-03 | 系统文档体系重构：精简根目录 + 三层导航 + 四管道架构 + 协议迁移 |
| 3.0.0 | 2026-05-02 | 多智能体协同架构 |
| 2.0.0 | 2026-04-25 | AgentOS 初始化框架落地 |

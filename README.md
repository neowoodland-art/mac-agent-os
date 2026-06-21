# AgentOS —— 多智能体联邦操作系统

> 版本 4.2.0 | 最后更新：2026-06-21
> 给 WorkBuddy AI 装上外骨骼——技能、工具、联邦、看板、自动化。

---

## 快速导航

| 你想做什么 | 去哪里 |
|:---------|:-------|
| 了解系统全貌 | `99_system/INDEX.md` |
| 查看系统全景 | `99_system/AGENTOS-PANORAMA.md` |
| AI 的行为规则 | `01_core/SOUL.md` |
| 系统身份信息 | `01_core/IDENTITY.md`（从模板生成） |
| 用户画像 | `01_core/USER.md` |
| 联邦宪法 | `ORACLE.yaml` |
| 联邦系统实操 | `FEDERATION_GUIDE.md` |
| 运维手册 | `01_core/MAINTENANCE_GUIDE.md` |
| 知识库 AI 入口 | `03_knowledge/99_system/AI_READING_GUIDE.md` |
| 版本唯一来源 | `01_core/VERSION` |

## 新机器初始化

```bash
# 1. 克隆仓库
git clone git@gitee.com:babycalf/mac-agent-os.git ~/workbuddy-agent-os/agent-sync

# 2. 一键初始化
cd ~/workbuddy-agent-os/agent-sync && bash 00_bootstrap/init.sh

# 3. 部署身份文件
bash 00_bootstrap/apply-config.sh
```

## 版本

| 组件 | 版本 |
|:-----|:-----|
| AgentOS 框架 | 4.2.0 |
| guardd 守护进程 | 2.3.0 |

> 版本唯一来源：`01_core/VERSION`
> 变更记录：`CHANGELOG.md`

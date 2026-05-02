# AgentOS 维护机制与文档规范

> 版本：v1.0
> 更新时间：2026-04-29

---

## 一、维护原则

- **分层分责**：核心、技能、工具、知识库、脚本各自独立，互不污染。
- **文档即规范**：所有变更均需在对应文档登记，杜绝口头约定。
- **最小必要原则**：只维护必要的文档，避免冗余和重复。
- **自动化优先**：能自动生成的内容不手动维护。
- **主机唯一主权**：master 机器有最终解释权，其他节点只读或提交。

---

## 二、维护分层与文档映射

| 层级 | 主要内容 | 维护文档 | 变更时机 |
|------|----------|---------|---------|
| **核心层** | 身份、规则、主机ID、MCP配置 | `01_core/IDENTITY.md` `SOUL.md` `USER.md` `HOST_ID.md` `mcp.json` `CHANGELOG.md` | 角色/规则/配置变更时 |
| **技能层** | 技能声明、触发词、命令、changelog | `02_skills/<skill>/SKILL.md` `SKILL_CARD.yaml` `version.json` | 新增/下线/升级技能时 |
| **工具层** | 工具目录、依赖、安装、档案 | `05_tools/<tool>/TOOL.md` `requirements.txt` `install.sh` | 新增/升级工具时 |
| **脚本层** | 具体实现代码 | 代码文件本身 | 代码变更时（文档只需登记新命令/接口） |
| **知识库层** | 知识结构、流转、归档 | `03_knowledge/README.md` `CHANGELOG.md` | 结构/流转规则变更时 |
| **全局索引** | 技能/工具/命令总览 | `SKILLS-CATALOG.md` `05_tools/README.md` | 新增/下线技能/工具时 |

---

## 三、维护流程

### 1. 核心层维护
- 仅 master 机器可编辑
- 变更后必须登记 `01_core/CHANGELOG.md`
- 角色/规则/配置变更需同步 `IDENTITY.md`、`SOUL.md`、`USER.md`、`mcp.json`

### 2. 技能层维护
- 新增/下线技能：登记 `SKILLS-CATALOG.md`，新建/归档 `02_skills/<skill>/`
- 技能升级：`SKILL_CARD.yaml` + `version.json` + `SKILL.md` changelog 必须同步
- 新命令/触发词：补充 `SKILL.md` 命令表

### 3. 工具层维护
- 新增工具：登记 `05_tools/README.md`，新建 `05_tools/<tool>/`
- 依赖变更：同步 `requirements.txt`、`install.sh`、`TOOL.md`
- 目录结构/环境变化：补充 `TOOL.md`

### 4. 脚本层维护
- 只维护代码本身，接口/命令变更需同步技能/工具文档
- 重要脚本建议头部注释用途、调用关系

### 5. 知识库层维护
- 结构/流转规则变更：补充 `03_knowledge/README.md`、`CHANGELOG.md`
- 新增/归档知识分区：及时更新目录说明

### 6. 全局索引维护
- 新增/下线技能/工具：同步 `SKILLS-CATALOG.md`、`05_tools/README.md`
- 指令/命令变更：补充指令对照表

---

## 四、维护建议

- **每次变更先查文档**，有无对应登记项
- **变更后立即登记**，避免遗忘
- **多机协作时，master 机器合并后再同步**
- **归档不用的技能/工具，勿直接删除**
- **定期 review 文档，清理过时内容**

---

## 五、自动化建议

- 能用脚本生成的内容（如 changelog、依赖列表），优先自动化
- 重要变更建议用 git commit message 规范同步
- 复杂流程建议补充流程图（Mermaid 支持）

---

## 六、维护清单（速查）

| 变更内容 | 必须登记文档 |
|----------|-------------|
| 新增/下线技能 | `SKILLS-CATALOG.md`、`02_skills/<skill>/` |
| 技能命令/触发词 | `SKILL.md` |
| 技能升级 | `SKILL_CARD.yaml`、`version.json`、`SKILL.md` |
| 新增/升级工具 | `05_tools/README.md`、`TOOL.md`、`requirements.txt`、`install.sh` |
| 依赖变更 | `requirements.txt`、`SKILL_CARD.yaml` |
| 目录结构/环境变更 | `TOOL.md` |
| 核心规则/身份/配置 | `01_core/` 下所有配置 + `CHANGELOG.md` |
| 知识库结构/流转 | `03_knowledge/README.md`、`CHANGELOG.md` |
| 指令/命令变更 | `SKILLS-CATALOG.md` |

---

> 本文档为 AgentOS 维护机制唯一权威说明，所有维护操作须以此为准。

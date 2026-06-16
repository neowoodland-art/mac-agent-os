# AgentOS 功能差距分析 — 规划 vs 实现

> 版本: v1.0 | 更新: 2026-06-16
> 对照: COMMAND-CENTER-PLAN.md v0.3 / ARCHITECTURE-v2.md / AVE_DASHBOARD_DESIGN.md

---

## 一、矩阵养号

| 导航项 | view | 状态 | 后端 | 说明 |
|:-------|:-----|:----:|:-----|:------|
| **账号管理** | `matrix-sms-proxy` | ✅ 完成 | `routes/matrix.py` | 身份/账号/短信/代理管理，API 完整 |
| **养号执行** | `matrix-nurture` | ✅ 完成 | `routes/matrix.py` | 内联养号面板，调用 `/api/matrix/batch-run` |
| **信息采集** | `matrix-collect` | ⏳ 待集成 | `routes/matrix.py` | **有完整 API** — `/api/matrix/collect-homepage` 等，只需 Dashboard 视图薄封装 |
| **内容发布** | `matrix-publish` | ❌ 无CLI | `publish_video.py` 存在 | `publish_video.py` 在 `07_matrix/scripts/` 目录，需封装为 `agentos matrix publish` CLI + Dashboard API |
| **蓝图管理** | `matrix-blueprints` | ✅ 完成 | `routes/matrix.py` | 13 个蓝图（抖音9+小红书4），编辑器/执行器完整 |
| **定向评论** | `matrix-comment` | ✅ 完成 | `routes/matrix.py` | 内联评论表单，调用 `/api/matrix/task/comment` |
| **定时任务** | `matrix-schedule` | ⏳ 待集成 | `routes/matrix.py` | **有完整 API** — 命令与任务面板已有调度功能，只需独立视图 |
| **语料库** | `matrix-corpus` | ✅ 完成 | `routes/matrix.py` | API 正常 |

### 待集成项（有后端，只需前端封装）

1. **信息采集** — 使用 `/api/matrix/collect-homepage` API 构建独立采集视图
2. **定时任务** — 使用 `/api/matrix/schedule/*` API 构建独立调度视图
3. **内容发布** — 需先封装 `publish_video.py` → `agentos matrix publish` CLI

---

## 二、视频工厂

| 导航项 | view | 状态 | 后端 | 说明 |
|:-------|:-----|:----:|:-----|:------|
| **渲染任务** | `ave-render` | ❌ 无API | 无 | AVE CLI（`09_ave/` 96个脚本）未封装为 `agentos ave` CLI，Dashboard 无从对接 |
| **脚本生成** | `ave-script` | ❌ 无API | 无 | 同上，需先完成 AVE CLI 封装 |
| **素材库** | `ave-materials` | ❌ 无API | 无 | 素材通过 SQLite(`ave.db`) 管理，需封装为 Dashboard API |
| **模板** | `ave-templates` | ❌ 无API | 无 | 模板模块需先封装 AVE CLI |

### 实施建议
- **前置依赖**: 完成 `agentos ave` CLI 封装（render/script/material/template 子命令）
- 然后 Dashboard 创建对应 API 端点，前端展示
- 优先级: 低（AVE 核心功能开发中）

---

## 三、内容采集

| 导航项 | view | 状态 | 后端 | 说明 |
|:-------|:-----|:----:|:-----|:------|
| **采集任务** | `crawl-tasks` | ⏳ 待集成 | `plugin-collector` 有API | **有完整 API** — Dashboard plugin-collector 已实现采集管理功能，只需前端视图对接 |
| **源管理** | `crawl-sources` | ❌ 无CLI | 无 | 采集源管理需要 `agentos crawl source` CLI 完成 |
| **采集历史** | `crawl-history` | ❌ 无API | 无 | 需要新建采集历史的聚合 API |

### 待集成项

1. **采集任务** — plugin-collector 已有采集调度能力，可直接嵌入 Dashboard 视图

---

## 四、联邦管理

| 导航项 | view | 状态 | 后端 | 说明 |
|:-------|:-----|:----:|:-----|:------|
| **机器状态** | `machines` | ✅ 完成 | `plugins/guardd.py` | 联邦心跳 + 机器聚合，数据完整 |
| **一键同步** | `fleet-sync` | ✅ 完成 | `app.py` `/api/fleet/sync` | 调用 `fleet_sync.sh`，Shell 内联 |
| **对账检查** | `fleet-reconcile` | ✅ 完成 | `app.py` `/api/fleet/reconcile` | 调用 `fleet_reconcile.sh`，Shell 内联 |
| **远程Shell** | `fleet-exec` | ✅ 完成 | `services/remote_exec.py` | 调用 `/api/federation/exec`，Shell 内联 |

---

## 五、服务管理

| 导航项 | view | 状态 | 后端 | 说明 |
|:-------|:-----|:----:|:-----|:------|
| **MCP状态** | `serve-mcp` | ❌ 无功能 | 无 | MCP Server 状态监控完全未实现 |
| **Dashboard日志** | `serve-dashboard` | ❌ 无功能 | 无 | Dashboard 运行日志聚合未实现 |
| **全局定时任务** | `serve-schedule` | ❌ 无功能 | 无 | 全局调度器管理未实现 |

### 实施建议
- MCP 状态需要先实现 MCP Server 的健康检测机制
- Dashboard 日志需要 log 聚合方案（如 filebeat 或 journald）
- 调度器需要 `agentos serve schedule` CLI 完成

---

## 六、agentos CLI 插件

| 插件 | 状态 | 子命令 | 说明 |
|:-----|:----:|:-------|:-----|
| `matrix` | ✅ 完成 | run/account/blueprint/sms/proxy etc | 最成熟 |
| `ave` | ⏳ 框架 | render/script/material/template | 子命令框架已创建，功能占位 |
| `crawl` | ⏳ 框架 | web/video/extract/schedule/source | 子命令框架已创建，功能占位 |
| `fleet` | ✅ 完成 | sync/reconcile/exec/status/logs | 基本完成 |
| `serve` | ⏳ 框架 | mcp/dashboard/schedule | 子命令框架已创建，功能占位 |

---

## 七、Dashboard 插件

| 插件 | 状态 | 说明 |
|:-----|:----:|:------|
| `matrix.py` | ✅ 完成 | 账号注册表 + 跨机聚合 |
| `ave.py` | ✅ 完成 | AVE 数据聚合 |
| `guardd.py` | ✅ 完成 | 机器监控 + 联邦心跳 |
| `kb_api.py` | ✅ 完成 | 知识库管理 API |
| `sms_proxy_api.py` | ✅ 完成 | 短信/代理 API |
| `system_plugins.py` | ✅ 完成 | 系统信息 + 自动任务 |
| `federation.py` | 🔴 未创建 | 联邦聚合插件 |
| `scheduler.py` | 🔴 未创建 | 调度器管理插件 |
| `crawl.py` | 🔴 未创建 | 内容采集插件 |

---

## 八、WPRA 架构实施进度

| Phase | 内容 | 进度 |
|:------|:-----|:----:|
| Phase 1 | guardd git 冲突修复、`_registry.json` 删除 | ❌ 未执行 |
| Phase 2 | 账号注册表 WPRA 重构 | ✅ 已完成 |
| Phase 3 | Dashboard 读聚合适配 | ✅ 已完成 |
| Phase 4 | 旧数据清理（等 1 周稳定期） | ⏳ 等待中 |
| Phase 5 | 文档化 + 标准化 | ❌ 未执行 |

---

## 九、优先级建议

```
P0（本周） ─── 矩阵养号核心功能完善
  矩阵信息采集（有API）     ≈ 0.5h
  矩阵定时任务（有API）     ≈ 0.5h
  采集任务视图（有API）     ≈ 0.5h

P1（下周） ─── agentos CLI 封裝 + Dashboard 插件补齐
  agentos ave CLI 封装      ≈ 2h
  agentos crawl CLI 封装    ≈ 1h
  publish_video CLI 封装    ≈ 1h
  federation/scheduler/crawl Dashboard 插件  ≈ 3h

P2（后续） ─── 全新功能
  服务管理（MCP/日志/调度器） ≈ 3h
  视频工厂 Dashboard 视图    ≈ 4h
  WPRA Phase 1 guardd 修复  ≈ 2h
  WPRA Phase 5 文档化       ≈ 1h
```

---

> 文档生成: 2026-06-16 17:46 | 下次更新: 功能变更后同步

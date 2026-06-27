# Dashboard 集成审计报告

> 日期: 2026-06-27 | 基于当前代码状态

## 执行路径总览

```
前端视图 → POST /api/ops/run {type, accounts, params}
  → CommandBus.dispatch()
    → 按机器分组
    → _send_local() / _send_remote()
      → guardd /scheduler/submit (新路径 ✅)
      → guardd /task (旧路径降级)
      → subprocess / SSH (最终降级)
```

## 各视图集成状态

### ✅ 已走新路径（CommandBus → guardd 调度引擎）

| 视图 | 操作类型 | 提交方式 |
|:-----|:---------|:---------|
| `matrix-accounts.js` | collect, login | `fetch('/api/ops/run')` → 新路径 |
| `matrix-collect.js` | collect | `apiRequest('/api/ops/run')` → 新路径 |
| `matrix-nurture.js` | nurture | `apiRequest('/api/ops/run')` → 新路径 |
| `matrix-comment.js` | comment | `apiRequest('/api/ops/run')` → 新路径 |
| `matrix-interact.js` | interact | `apiRequest('/api/ops/run')` → 新路径 |
| `matrix-like.js` | like | `apiRequest('/api/ops/run')` → 新路径 |
| `ops-command.js` | 联邦指挥台 | 读 `/api/ops/queue` + `/api/ops/machines` |

### 🔶 需要注意的点

| 问题 | 说明 |
|:-----|:------|
| **账号管理页采集不显示在指挥台** | 已修复: `_send_local()` 优先走 scheduler，旧路径降级 |
| **指挥台只读不写** | 目前指挥台只能"看"不能"操作"（Phase 3a 实现） |
| **旧 `/task` 路径仍保留** | 作为降级方案，guardd 不可用时自动 fallback |
| **nurture_runner.sh 未集成到调度器** | 养号任务仍走旧 nurture_runner.sh 路径（通过 /task 降级） |

### ⏳ 待实现（Phase 3）

| 功能 | 优先级 |
|:-----|:-------|
| 指挥台操作按钮（取消/暂停/重排） | P0 |
| 告警中心（封号/登录失败高亮） | P1 |
| 三级接力 | P2 |
| 任务超时熔断自动恢复 | P1 |

## 当前数据流

```
用户点击"采集"
  ↓
matrix-accounts.js → POST /api/ops/run
  ↓
CommandBus.dispatch("collect", [account_id], params)
  ↓
_send_local() → guardd /scheduler/submit
  ↓
guardd scheduler → 15s循环 → executor.execute()
  ↓
指挥台每15秒 poll /api/ops/queue → 看到任务
```

## 测试方法

在账号管理页点"采集" → 等15秒 → 刷新指挥台 → 应该能看到任务出现在队列中

# 命令传导治理——改动清单与范围

> 日期: 2026-06-25 | 目标版本: 4.2.1
> 改动后由用户全面审计

---

## 改动范围总览

### 前端视图（4个文件）

| 文件 | 当前问题 | 改为 | 工作量 |
|:-----|:---------|:-----|:-------|
| `views/matrix-like.js` | 用旧路由 `/matrix/task/run` + 双重循环逐个发 | `POST /api/ops/run {type:'like', accounts:全部}` | 中 |
| `views/matrix-sms-proxy.js` | 用已删除的路由 `/matrix/collect-homepage` | `POST /api/ops/run {type:'collect', accounts}` | 小 |
| `views/matrix-accounts.js` | 单账号采集/登录逐个发 | 一次性提交 + 显示结果 | 中 |
| `views/matrix-comment.js` | — | 审计确认是否需要改 | 小 |

### 后端路由（1个文件）

| 路由 | 处理方式 |
|:-----|:---------|
| `routes/matrix.py:/task/run` (POST) | 删除（已改由 `/api/ops/run` 替代） |
| `routes/matrix.py:/nurture/start` (POST) | 删除（已改由 `/api/ops/run` 替代） |
| `routes/matrix.py:/collect-homepage/*` (POST) | ✅ 已删除 |

### 旧模块（modules/ 中的残留引用）

| 模块 | 引用 | 处理 |
|:-----|:------|:------|
| `modules/collect.js:92` | `/api/matrix/task/run` | 改为 `/api/ops/run` |
| `modules/recording.js:137,149` | `/matrix/collect-homepage/phone` + `/status` | 删除或改为新路由 |
| `modules/nurture.js:109,122,153,165` | `/matrix/collect-homepage` + `/status` | 删除或改为新路由 |

### CMD_REGISTRY

| 条目 | 当前 | 改为 |
|:-----|:-----|:-----|
| `nurture.runner` | 定义了但 dispatch 未使用 | dispatch 使用 runner 字段 |
| `comment` 模板 | 含 `{direction}` 可能缺失 | 去掉 direction 或设默认值 |

---

## 实施顺序

```
Step 1: 改 matrix-like.js（旧路由，最高优先级）
Step 2: 改 matrix-sms-proxy.js（旧路由已删除，会404）
Step 3: 改 matrix-accounts.js（逐个发送问题）
Step 4: 改 modules/*.js 旧引用
Step 5: 删除后端旧路由 + 清理 CMD_REGISTRY
Step 6: 构建前端 + 重启 Dashboard
Step 7: git push + 同步远程
Step 8: 提供改动清单供用户审计
```

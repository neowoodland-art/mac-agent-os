# Session handoff — 2026-07-19

## 今日完成

### 账号数据统一（Step 3 视图迁移）
| 视图 | 改动 | 状态 |
|:-----|:------|:------|
| `productions.js` | `/matrix/sms/accounts` → `/v2/accounts` | ✅ |
| `matrix-blueprints.js` | `/matrix/accounts` → `/v2/accounts` | ✅ |
| `matrix-comment.js` | `/matrix/accounts` → `/v2/accounts` | ✅ |
| `matrix-sms-proxy.js` | `/matrix/sms/accounts` → `/v2/accounts` | ✅ |
| `ops-recorder.js` | `/matrix/accounts` → `/v2/accounts` | ✅ |
| `matrix-nurture.js` | `/matrix/accounts` → `/v2/accounts` | ✅ |
| `comment-workbench.js` | `/matrix/accounts` → `/v2/accounts` | ✅ |
| `matrix-like.js` | `/matrix/accounts` → `/v2/accounts` | ✅ |
| `matrix-interact.js` | `/matrix/accounts` → `/v2/accounts` | ✅ |
| `matrix-collect.js` | `/matrix/accounts` → `/v2/accounts` | ✅ |
| `matrix-accounts.js` | `/matrix/accounts` → `/v2/accounts` | ✅ |
| `inline.js` (2处) | `/matrix/accounts` → `/v2/accounts` | ✅ |

### 旧 API 标记 DEPRECATED
- `routes/matrix.py`: `/api/matrix/accounts` 文档+运行时日志标记废弃
- `MANIFEST.yaml`: 添加红线 `🚫 /api/matrix/accounts（读）— 已废弃`

### 状态配置统一
- 新建 `config/status-config.js` (STATUS_CFG + STATUS_ORDER 唯一来源)
- `accounts-center.js`、`account-selector.js` 改为 import

### 账号选择器重构
- 筛选改为排除模式（机器/平台/状态均排除选中的）
- 新增「全选筛选结果」按钮
- 新增「复位选择」按钮
- 搜索框移至第二行

### 养号 pkill 误杀修复
- `nurture_runner.sh`: `pkill -f` 改为 `pgrep`+`ps` 精确匹配
- `command_bus.py`: `graceful_exit()` 先查 guardd 有 active 任务则跳过

### 评论区输入框
- `matrix-comment.js`: `<input>` → `<textarea rows="2">`

## 当前状态
- Dashboard: `localhost:9988` 运行中
- guardd: 三台机器全部运行中，details 正常返回
- 所有账号读取 API 已统一到 `/api/v2/accounts`
- Gitee 已推送，远程机器已同步

## 下次可做的
- `accounts-center.js` 中 POST/DELETE 旧 API（创建/删除/加备注）— 写操作，无 v2 替代

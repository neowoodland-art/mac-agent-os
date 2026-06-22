# Dashboard 修复记录 2026-06-22

## 1. SMS 页面账号下拉为空 + 5秒超时

**症状**: 短信接收页面点击"选择账号"搜索框，下拉列表为空或显示"⏳ 账号列表加载中..."，等5秒后才出现。

**根因**: `modules/corpus.js` 定义了同名的 `loadSmsProxy`、`loadSmsAccounts` 等函数，覆盖了 `inline.js` 的正确版本。

```
import 顺序:
  inline.js  → 定义 loadSmsProxy (正确版: 用 Promise.all + await)
  corpus.js  → 覆盖 window.loadSmsProxy (bug版: 无 await, fire-and-forget)
```

corpus.js 版的 `loadSmsAccounts` 先请求 `/api/federation/accounts`（该端点5秒超时），再 fallback 到本地 `/api/matrix/sms/accounts`。

**修复**: 移出 corpus.js 中 `loadSmsProxy` 函数定义，移除所有覆盖 inline.js 的 SMS 相关 window 赋值（14项）。

**教训**: 同一函数在多文件中定义时，通过 import 顺序决定哪个版本胜出。这种隐式覆盖很容易出 bug。要么只在一个文件中定义，要么在覆盖时显式注释说明。

---

## 2. 机器状态显示离线

**症状**: 顶部状态栏显示"机器数 2 在线 0"；底部机器条显示所有远程机器离线。

**根因**: 
- 顶部状态栏：`loadStats()` 从 AVE 插件读取数据（AVE 只记录了2台机器）
- 底部机器条：`loadMachineBar()` 用 `/api/federation/health`（该端点返回空）

**修复**: 
- 顶部改用 guardd 插件数据（总机器3，在线3）
- 底部改用 `/api/machines` API 的 `status` 字段

**教训**: 多数据源共存时，要明确哪个是权威源。`/api/machines` 是机器状态的权威源。

---

## 3. 账号归属错误

**症状**: `xhs_01` 被 chengzigedeAir 认领（OARCLE 规定属于 5kechengdeAir），6个账号归属错误。

**根因**: WPRA 去重后未用 ORACLE.yaml 覆盖 `owner_machine`。

**修复**: 在 `list_accounts()` 去重后，用 ORACLE.yaml 的 `accounts:` 节覆盖 `assigned_machine`/`owner_machine`。

**教训**: ORACLE.yaml 是账号归属的宪法，所有数据聚合后必须以 ORACLE 为准。

---

## 4. 账号 is_local 与 ORACLE 冲突

**症状**: `xhs_01` 的 `is_local=True` 但 `owner_machine=5kechengdeAir`，导致前端排序把远程账号误判为本机。

**根因**: `is_local()` 函数第1162行 `if acct["id"] in override_map: return True`——只要本地有身份目录就直接判为本机，跳过了第1166行的 `_all_assignments` 兜底检查。但 ORACLE 已经把这个账号分配给了 5kechengdeAir。

**修复**: 在 override_map 匹配后加一道 ORACLE 检查：如果 `assigned_machine`（已被 ORACLE 覆盖）不是本机，返回 False。

**教训**: 数据源覆盖顺序：identity目录 < WPRA < ORACLE.yaml。下层数据不能推翻上层的决策。

---

## 5. corpus.js 中 _renderAccountSelector 覆盖 inline.js

**症状**: 账号选择器在部分页面表现不一致。

**根因**: `_loadAccounts` 和 `_renderAccountSelector` 在 inline.js 和 corpus.js 中各有定义。corpus.js 后导入，覆盖了 inline.js 的版本。

**修复**: 在 inline.js 末尾添加别名重定向：
```javascript
_loadAccounts = window._loadAccounts;
_renderAccountSelector = window._renderAccountSelector;
```

并移除 inline.js 中9处被覆盖的 window 赋值。

**教训**: 模块化拆分时，被拆出的函数必须从原始文件中移除，否则会出现两份定义。

---

## 6. 账号选择器参数不一致

**症状**: 不同页面的账号选择器高度、搜索框显示、默认全选状态不一致。

**根因**: 5处 `_renderAccountSelector` 调用使用了不同的参数：
- `height: '300px'` vs `'350px'` vs `'280px'`
- `checkAll: false` vs 默认 true
- `hideFilter: true` vs 默认 false

**修复**: 全部统一为 `{_data: data, height: '350px'}`。

**教训**: 共享组件必须统一参数。所有调用方应使用相同的配置。

---

## 7. 蓝图管理 [object Object] 显示

**症状**: 蓝图管理页面显示 `1. [object Object] · 2. [object Object] · ... 80. [object Object]`

**根因**: 这是一个**连环 bug**，涉及三层问题：

### 第1层：迁移视图拦截（最外层）
`views/matrix-blueprints.js`（70行只读版）在 `_tryMigratedView` 白名单中，switchView 加载了这个简化版视图后直接 return，registration.js 的完整编辑器（含步骤编排、原子操作卡片、保存/验证）从未被执行。

```javascript
// matrix_views.js 第149行
if (_tryMigratedView(view)) return;  // ← 白名单拦截，直接返回！
// 第162行 — 永远不会执行到
try { if (view === 'matrix-blueprints') window.loadMatrixBlueprints(); } catch(e) {}
```

**修复**: 
1. 从 `_tryMigratedView` 白名单移除 `matrix-blueprints`
2. 从 `view-registry.js` 中注释掉 `matrix-blueprints`

### 第2层：视图本身渲染 bug
`views/matrix-blueprints.js` 中用 `o.name||o` 渲染步骤名。但 API 返回的步骤对象格式为 `{step_id, op, args}`，没有 `name` 字段。`o.name` 为 undefined，`o` 是对象 → `[object Object]`。

**修复**: `o.name||o` → `o.op||o.name||''`

### 第3层：showBpEditor 查找逻辑 bug
即使绕过第1层，registration.js 的 `showBpEditor` 也有 bug：

```javascript
// 注册器版（正确）
const bps = Array.isArray(bd) ? bd : (bd.blueprints || []);
// showBpEditor 版（错误）
const bp = (d.blueprints||[]).find(...)  // d 是数组，d.blueprints 为 undefined
```

API 返回原始数组 `[bp1, bp2, ...]`，不是 `{blueprints: [...]}`。`showBpEditor` 永远找不到蓝图，静默返回。

**修复**: 添加 `Array.isArray(d)` 检测，兼容两种 API 返回格式。

**教训**: 
- 迁移视图会拦截 switchView 的后续逻辑。白名单中的视图名必须确保其功能完整。
- API 返回格式（数组 vs 对象）必须在整个前端保持一致。如果 API 返回数组，所有取数据的代码都要用 `Array.isArray()` 检测。
- 渲染 API 数据时，字段名要与 API 文档对齐（`op` 不是 `name`）。
- [object Object] 100% = 对象被当字符串用。模板字符串中 `${obj}`、字符串拼接 `str + obj`、`obj || fallback` 都可能触发。

---

## 8. Blueprint step 字段 op vs name 不一致

**症状**: `showBpEditor` 和 `stepsPreview` 都用 `s.name` 去查 `_matrixOps`，但 API 返回的字段是 `s.op`。

**根因**: 后端 API 返回的蓝图步骤格式为 `{step_id, op, args}`。前端的原子操作库 `_matrixOps` 索引用的是 `o.name`。所以 `_matrixOps[s.name]` 永远查不到。

**修复**: 
- stepsPreview: `s.name` → `s.op||s.name`
- showBpEditor: `s.name||s` → `s.op||s.name`
- bpRenderSteps: 加 label 兜底，非字符串时重新从 `_matrixOps` 查询

**教训**: API 返回的字段名必须与前端使用的字段名一一对应。如果不对应，必须做映射转换。

---

## 9. 函数冲突：inline.js vs 拆分模块

**总体问题**: 同一函数在多个文件中定义，通过 import 顺序决定哪个版本胜出。这种机制极难排查。

**涉及函数**:
| 函数 | 定义在 | 胜出方 |
|------|--------|--------|
| `_loadAccounts` | inline + corpus | corpus |
| `_renderAccountSelector` | inline + corpus | corpus |
| `loadMatrixNurture` | inline + account_selector | account_selector |
| `loadMatrixCollect` | inline + account_selector | account_selector |
| `loadMatrixComment` | inline + account_selector | account_selector |
| `loadMatrixLike` | inline + account_selector | account_selector |
| `loadOpsCommand` | inline + account_selector | account_selector |
| `loadMatrixCommands` | inline + collect | collect |
| `cmdRunCommentTask` | inline + collect | collect |
| `loadMatrixBlueprints` | inline + registration | registration |
| `showBpEditor` | inline + registration | registration |
| `loadSmsProxy` | inline + corpus | corpus（已修复） |
| `loadSmsAccounts` | inline + corpus | corpus（已修复） |

**修复策略**:
1. 从胜出方中移除被覆盖函数的 window 赋值 → 明确所有权
2. 在 inline.js 末尾添加别名重定向 → 确保内部调用指向最终版本

**教训**: 模块化拆分应该是"**移动代码**"而不是"**复制代码并覆盖**"。拆出一个函数时，必须从原始文件中删除该函数定义。

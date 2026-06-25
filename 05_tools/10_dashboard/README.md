# Dashboard 系统监控面板

> 版本: 2.0.0 | AgentOS 4.2.1
> 最后更新: 2026-06-25
> 端口: 9988

---

## 一、五层执行架构

所有 Dashboard 操作（养号、采集、登录、评论）都经过这五层：

```
L5 ─── Dashboard UI ───────── frontend/src/views/*.js
  │     用户点击按钮 → API 调用
  ▼
L4 ─── API 路由 ───────────── routes/ops.py (统一执行入口)
  │     POST /api/ops/run → 调 CommandBus
  ▼
L3 ─── CommandBus ─────────── services/command_bus.py
  │     CMD_REGISTRY 映射 cmd_type → mc 命令
  │     按机器分组 → 队列 → 预检 → 分发
  ▼
L2 ─── mc 引擎 ────────────── scripts/mc/engine.py
  │     BatchEngine → 身份分组 → 启动浏览器 → 蓝图执行
  ▼
L1 ─── 平台 Ops ───────────── scripts/douyin_ops.py / ops/xhs_ops.py
  │     原子操作（三段式：前置条件→执行→后置验证）
  ▼
L0 ─── Camoufox 浏览器 ────── 真实浏览器操作
```

**核心原则**：
- L3 CommandBus 是通往执行层的**唯一大门**
- 前端/L4/CLI/定时任务 → 全部走 CommandBus
- 不允许绕过 CommandBus 直接 subprocess

---

## 二、目录结构

```
05_tools/10_dashboard/
├── app.py                    ← FastAPI 主入口（插件加载 + 健康检查 + 基础API）
├── run.py                    ← 启动脚本
├── routes/
│   ├── ops.py                ← 统一操作执行入口（POST /api/ops/run）
│   └── matrix.py             ← 矩阵数据查询（账号/蓝图/采集历史等读操作）
├── services/
│   ├── command_bus.py        ← CommandBus（命令总线 + CMD_REGISTRY 注册表）
│   ├── command_chain.py      ← 接力执行链
│   ├── fleet_collector.py    ← 联邦数据聚合
│   ├── remote_exec.py        ← 远程SSH执行
│   ├── preflight.py          ← 执行前预检
│   └── ...
├── plugins/                  ← 插件式数据源（matrix/guardd/ave/crawl等15个）
├── frontend/src/             ← 前端源码（Vite）
│   ├── main.js               ← 入口
│   ├── router.js             ← 路由 + apiRequest 工具函数
│   ├── state.js              ← AppState 全局状态
│   ├── views/                ← 已迁移视图（45+个）
│   │   ├── matrix-collect.js     ← 信息采集视图
│   │   ├── matrix-nurture.js     ← 养号执行视图
│   │   ├── matrix-accounts.js    ← 账号管理视图
│   │   ├── matrix-comment.js     ← 定向评论视图
│   │   ├── matrix-blueprints.js  ← 蓝图编辑器
│   │   └── ...
│   ├── modules/              ← 功能模块（16个）
│   └── components/           ← 共享组件
├── static/                   ← Vite 构建产物（index.html + assets/）
└── PLANS/                    ← 规划文档
```

---

## 三、API 路由说明

### 3.1 操作执行（唯一入口）

**`POST /api/ops/run`** — 所有操作统一入口

请求体格式：
```json
{
  "type": "collect",          // 操作类型（见 CMD_REGISTRY）
  "accounts": ["douyin_01"],  // 账号ID列表
  "params": {                 // 操作参数（可选，不传用注册表默认值）
    "rounds": 1
  }
}
```

支持的 type（定义在 `CMD_REGISTRY`）：

| type | 用途 | 默认 blueprint | 自动推断 |
|:-----|:------|:---------------|:---------|
| `nurture` | 养号执行 | `douyin_daily` | ❌ 不自动 |
| `collect` | 主页信息采集 | 按平台自动选 | ✅ 自动按账号平台选择 |
| `login` | 智能登录 | — | — |
| `logout` | 登出 | `douyin_daily` | ❌ |
| `comment` | 定向评论 | — | — |
| `like` | 点赞 | `douyin_daily` | ❌ |

其他 API：

| 方法 | 路径 | 用途 |
|:-----|:------|:------|
| `GET` | `/api/ops/status` | 查询所有命令状态 |
| `GET` | `/api/ops/history` | 查询命令执行历史 |
| `GET` | `/api/ops/machines` | 所有机器聚合状态 |
| `POST` | `/api/ops/cancel/{run_id}` | 取消指定命令 |
| `POST` | `/api/ops/test-atom` | 单步原子操作测试 |

### 3.2 数据查询（routes/matrix.py）

所有 `/api/matrix/*` 路由**只处理读操作**（GET），不处理写操作（POST）。

| 方法 | 路径 | 用途 |
|:-----|:------|:------|
| `GET` | `/api/matrix/accounts` | 账号列表 |
| `GET` | `/api/matrix/profiles` | 已缓存主页资料 |
| `GET` | `/api/matrix/homepage-info` | 主页信息采集结果（联邦聚合） |
| `GET` | `/api/matrix/blueprints` | 蓝图列表 |
| `GET` | `/api/matrix/atom-ops` | 原子操作列表 |
| `GET` | `/api/matrix/nurture/status` | 养号运行状态 |

**禁止**在 routes/matrix.py 中新增 POST 写操作。
所有写操作必须走 `routes/ops.py` → `CommandBus.dispatch()`。

---

## 四、CommandBus CMD_REGISTRY 注册表

### 4.1 定义位置

`services/command_bus.py:605-640`

```python
CMD_REGISTRY = {
    "nurture": {
        "runner": "nurture_runner.sh",
        "defaults": {"blueprint": "douyin_daily", "rounds": 10},
        "auto_blueprint": False,
    },
    "collect": {
        "template": "mc run --accounts={ids} --blueprints={blueprint} --rounds={rounds}",
        "defaults": {"rounds": 1},
        "auto_blueprint": True,
        "blueprint_map": {
            "douyin": "douyin_read_profile",
            "xiaohongshu": "xiaohongshu_read_profile",
        },
    },
    "login": {
        "template": "mc smart-login {ids}",
        "single_account": True,
    },
    "comment": {
        "template": "mc task comment --account={ids} --url={url} --direction={direction}",
        "required_params": ["url"],
    },
    ...
}
```

### 4.2 字段说明

| 字段 | 含义 | 示例 |
|:-----|:------|:------|
| `template` | 命令模板，用 `{ids}` `{blueprint}` 等变量 | `mc run --accounts={ids} --blueprints={blueprint}` |
| `defaults` | 参数默认值 | `{"rounds": 1}` |
| `auto_blueprint` | 是否根据账号平台自动选择蓝图 | `True` |
| `blueprint_map` | 平台→蓝图映射 | `{"douyin": "douyin_read_profile"}` |
| `runner` | shell 包装器路径（nurture 专用） | `"nurture_runner.sh"` |
| `single_account` | 是否一次只处理一个账号 | `True` |
| `required_params` | 必填参数列表 | `["url"]` |

### 4.3 新增操作类型

新增操作类型只需在 `CMD_REGISTRY` 加一行，不需要改 `dispatch()` 逻辑。

```python
# 例：新增 publish 发布操作
"publish": {
    "template": "mc task publish --account={ids} --file={file}",
    "required_params": ["file"],
}
```

---

## 五、前端调用规范

### 5.1 统一调用格式

所有操作执行类请求必须使用 `apiRequest` 工具函数：

```javascript
import { apiRequest } from '../router.js';

// ✅ 正确：走统一入口
const result = await apiRequest('/ops/run', {
    method: 'POST',
    body: JSON.stringify({
        type: 'collect',           // 操作类型
        accounts: ['douyin_01'],   // 账号ID列表
        params: {
            rounds: 1,             // 操作参数
            // blueprint 由服务端 CMD_REGISTRY 自动推断
        },
    }),
});

// ❌ 错误：不要绕过统一入口
// await apiRequest('/matrix/collect-homepage', ...)  // 已删除
// await apiRequest('/matrix/nurture/start', ...)     // 不走CommandBus
```

### 5.2 参数格式规则

| 字段 | 必须 | 类型 | 说明 |
|:-----|:----|:-----|:------|
| `type` | ✅ | string | `nurture`/`collect`/`login`/`logout`/`comment`/`like` |
| `accounts` | ✅ | [string] | 账号ID数组 |
| `params` | ❌ | object | 可选，不传则用CMD_REGISTRY默认值 |

### 5.3 错误处理

```javascript
try {
    const d = await apiRequest('/ops/run', {
        method: 'POST',
        body: JSON.stringify({ type: 'collect', accounts: ids, params: { rounds: 1 } }),
    });
    // d.status = 'accepted' | 'completed' | 'error'
    // d.errors = [...]  // 校验错误
    // d.warnings = [...] // 警告
} catch (e) {
    // 网络/HTTP错误
}
```

---

## 六、视图清单与说明

### 6.1 矩阵组 📱（20+视图）

| 视图文件 | 功能 | 说明 |
|:---------|:-----|:------|
| `matrix-accounts.js` | 账号管理 | 列表/搜索/筛选/建号/单账号采集🔑 |
| `matrix-nurture.js` | 养号执行 | 全量/按账号执行养号蓝图 |
| `matrix-collect.js` | 信息采集 | 批量采集主页信息，走统一 `/api/ops/run` |
| `matrix-comment.js` | 定向评论 | 给指定视频发评论 |
| `matrix-blueprints.js` | 蓝图编辑器 | 创建/编辑/删除/执行蓝图 |
| `matrix-login.js` | 登录管理 | 查看/管理登录状态 |
| `matrix-run.js` | 原子操作执行 | 单步测试原子操作 |
| `matrix-like.js` | 收藏点赞 | 批量点赞/收藏 |
| `matrix-publish.js` | 内容发布 | 发布视频/图文 |
| `matrix-commands.js` | 执行历史 | 命令执行记录与状态 |
| `matrix-record.js` | 录制工具 | 操作录制/分析/导出 |
| `matrix-export.js` | 数据导出 | 账号/数据导出 |
| `matrix-backup.js` | 备份管理 | 创建/恢复备份 |
| `matrix-corpus.js` | 语料库 | 评论语料管理 |
| `matrix-schedule.js` | 定时任务 | 养号定时调度 |
| `matrix-sms-proxy.js` | 短信与代理 | API配置/测试 |
| `matrix-settings.js` | 系统配置 | 查看/修改配置 |
| `matrix-c2.js` | 联邦指挥台 | 跨机命令执行 |
| `matrix-atom-ops.js` | 原子操作列表 | 查看所有支持的操作 |

### 6.2 视图规范

- ✅ 所有视图已从 inline.js 迁移到 `views/*.js`
- ✅ 已注册到 `view-registry.js`
- ✅ 使用 `router.js` 的 `loadMigratedView()` 动态加载
- ✅ 通过 `apiRequest()` 调用后端 API

---

## 七、版本历史

| 版本 | 日期 | 变更 |
|:-----|:------|:------|
| 2.0.0 | 2026-06-25 | CommandBus CMD_REGISTRY 注册表；统一调用入口到 `/api/ops/run`；废弃 collect-homepage 路由 |
| 1.0.0 | 2026-06-19 | 初始版本，五层架构建立 |

---

## 八、关联文档

| 文档 | 位置 |
|:-----|:------|
| 命令传导统一治理方案 | `PLANS/COMMAND_UNIFICATION_PLAN.md` |
| 五层架构合规审计 | `PLANS/AUDIT_5LAYER_REPORT.md` |
| 联邦系统使用指南 | `FEDERATION_GUIDE.md`（参考 §十一） |
| 架构宪法 | `CONSTITUTION.md` |

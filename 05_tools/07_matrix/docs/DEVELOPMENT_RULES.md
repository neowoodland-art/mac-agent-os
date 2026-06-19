# AgentOS 联邦系统 — 开发规则 v1.0

> 所有新功能/修复必须遵守以下规则，防止代码混乱。

---

## 一、代码分层与职责

| 层 | 文件 | 职责 | 谁写 |
|:---|:-----|:------|:------|
| **蓝图 JSON** | `blueprints/*.json` | **你和我交互的命名模板**，只定义参数，不写逻辑 | AI 写参数定义，你用看板填参数 |
| **原子操作** | `douyin_ops.py` / `ops/xhs_ops.py` / `matrix_modules/account/*.py` | 被 `mc run` 引擎调用的最小操作单元 | AI 写，封装到已有类里 |
| **引擎** | `mc/engine.py` / `mc/task.py` | 执行蓝图 + 状态机钩子(登录检测/验证处理/冷却) | AI |
| **独立工具** | `create_identity.py` / `login_identity.py` / `publish_video.py` | CLI 可直接调的系统维护脚本 | AI |
| **一次脚本** | `/tmp/*.py` | 临时探索/诊断，用完即删 | AI |
| **看板视图** | `frontend/src/views/*.js` | Dashboard 前端视图 | AI |
| **API 路由** | `routes/*.py` | 看板调用的后端接口 | AI |

---

## 二、三原则（必须遵守）

### 原则 1：功能加到已有类里，不建新文件

- 抖音的新操作 → 加 `DouyinOps` 类（`douyin_ops.py`）
- 小红书的新操作 → 加 `XhsOps` 类（`ops/xhs_ops.py`）
- SMS 登录 → 已有 `sms_login.py`，改它
- 登录状态机 → 已有 `login_state_machine.py`

**禁止**：为每个小功能创建独立脚本。除非它是一个**完整的、可独立 CLI 调用的工具**（如 `create_identity.py`）。

### 原则 2：蓝图只定义参数，不写执行逻辑

```json
{
  "id": "douyin_daily",
  "name": "抖音-日常养号",
  "params": { "duration": {"type": "int", "default": 600} },
  "steps": [{"step_id": 1, "op": "goto_home", "args": {}}]
}
```

- 蓝图文件只描述「有什么参数」「分几步」
- 真正的执行逻辑在 `mc/engine.py` + 原子操作里

**禁止**：在蓝图 JSON 里写条件/循环/异常处理。

### 原则 3：`/tmp/*.py` 用完即删

- `/tmp/douyin_login_explore.py` — 用完即删
- `/tmp/test_xxx.py` — 用完即删

**禁止**：把 `/tmp/` 脚本作为正式功能提交到 Git。

---

## 三、新增功能的标准化流程

```
你提需求 → 我评估归属层 → 写入对应文件 → 你测试 → 我修正

例: 抖音SMS登录
你: "douyin_133 登录过期了, 需要SMS重新登录"
我: 归属 → DouyinOps 类
     → douyin_ops.py 加 sms_login() 方法
     → 调已有 sms_login.py 的 SMS 轮询逻辑
     → 蓝图的 needs_login 字段自动触发
     → 不建新文件
```

---

## 四、什么算"独立工具"

只有满足以下**全部**条件的才可以建独立脚本：

1. ✅ 可从 CLI 直接调用（有 `main()` + `argparse`）
2. ✅ 不依赖 `mc run` 引擎
3. ✅ 功能完整闭环（如 `create_identity.py` 创建身份→生成目录→写配置）
4. ❌ 如果只是被引擎或原子操作调用的功能，必须写在对应类里

---

## 五、历史遗留处理

| 文件 | 状态 | 原因 |
|:-----|:------|:------|
| `collect_batch_runner.py` | ✅ 已归档 | 功能已被蓝图 `douyin_read_profile` 替代 |
| `collect_homepage_info.py` | ✅ 已归档 | 同上 |
| `matrix.py` | ✅ 已归档 | 功能被 `mc` CLI 替代 |
| `ops/douyin/` | ✅ 已归档 | 功能被 `douyin_ops.py` 替代 |
| `atom_ops.py` | ✅ 已归档 | 废弃 |
| `yanghao_runner.py` | ✅ 已归档 | 废弃 |
| `step_by_step_v*.py` | ✅ 已归档 | 废弃 |

**新功能必须直接写入活跃文件，不建新独立脚本。**

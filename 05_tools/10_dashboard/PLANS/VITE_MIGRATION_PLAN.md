# Vite + Vanilla JS 前端重构计划

> 创建日期: 2026-06-17 | 执行日期: 2026-06-18
> 状态: ⏳ 计划已定，待执行

---

## 一、为什么要做

### 当前问题
- `static/index.html` 7700 行，一个文件塞了所有视图
- 没有模块化，函数全部全局作用域，名字冲突风险高
- 改一行代码必须重启 Dashboard 才能看到效果（没有热更新）
- 尝试按行号拆分失败：JS 里的 HTML 模板字面量打断函数边界

### 目标
- 每个视图一个文件，50-300 行
- Vite HMR：改代码即时生效，不用重启
- `import/export` 代替全局函数
- 构建产物输出到 `static/`，Dashboard 原样服务

---

## 二、技术栈

| 层 | 选型 | 理由 |
|:---|:-----|:------|
| 构建 | **Vite 6** | 零配置启动、HMR、按需编译 |
| 语言 | **Vanilla JS** (ES Modules) | 不需要 Vue/React，你的是表格+按钮 UI |
| 样式 | **CSS Variables** + 内联样式 | 保持现有设计，不引入 CSS 框架 |
| 后端 | **FastAPI** (不变) | 纯 API 层，不碰后端 |
| 部署 | Vite build → `static/` 目录 | Dashboard 直接服务静态文件 |

**不做 Vue/React 的原因**：
- 你的页面主要是表格、按钮、选择器，没有复杂的双向绑定
- 引入框架 = 额外的学习成本 + 构建配置
- Vanilla JS + 原生 `import/export` 足够

---

## 三、文件结构

```
agent-sync/05_tools/10_dashboard/
├── frontend/                          # 新建：Vite 项目目录
│   ├── index.html                     # 入口 HTML（空壳，只含 <div id="app">）
│   ├── vite.config.js                 # Vite 配置
│   ├── package.json                   # 依赖
│   └── src/
│       ├── main.js                    # 入口：渲染 app.html、初始化路由
│       ├── style.css                  # 全局样式（从旧 index.html 的 <style> 迁移）
│       ├── api.js                     # fetch 封装 + 所有 API 调用
│       ├── router.js                  # switchView + 侧边栏导航逻辑
│       ├── state.js                   # 全局状态（_allAccounts, currentView 等）
│       ├── components/                # 可复用组件
│       │   ├── account-selector.js    # 共享账号选择器（核心组件）
│       │   ├── sidebar.js             # 侧边栏导航
│       │   ├── stats-bar.js           # 顶部状态栏
│       │   ├── result-table.js        # 结果表格（通用）
│       │   └── shell-placeholder.js   # _renderShell 替代
│       └── views/                     # 每个视图一个文件
│           ├── matrix-summary.js
│           ├── matrix-accounts.js     # 账号管理
│           ├── matrix-nurture.js      # 养号执行（含 nurturePreflight 等）
│           ├── matrix-collect.js      # 信息采集（含 collectLogin/collectExec）
│           ├── matrix-comment.js      # 定向评论
│           ├── matrix-like.js         # 收藏点赞
│           ├── matrix-login.js        # 登录管理（跳转）
│           ├── matrix-blueprints.js   # 蓝图管理
│           ├── matrix-atom-ops.js     # 原子操作
│           ├── matrix-schedule.js     # 定时任务
│           ├── matrix-corpus.js       # 语料库
│           ├── matrix-run.js          # 命令与任务
│           ├── ops-command.js         # 联邦指挥台
│           ├── ops-history.js         # 执行历史
│           ├── federation.js          # 联邦相关
│           ├── fleet-sync.js          # 一键同步
│           ├── fleet-exec.js          # 远程 Shell
│           ├── ave-render.js          # 视频工厂
│           └── settings.js            # 设置
├── static/                            # 构建产物输出目录
│   └── (构建后自动生成)
└── PLANS/VITE_MIGRATION_PLAN.md       # 本文件
```

---

## 四、执行步骤（按顺序）

### Phase 1: 搭建 Vite 项目 (预计 30min)

```bash
cd agent-sync/05_tools/10_dashboard
npm create vite@latest frontend -- --template vanilla
cd frontend
npm install
```

然后：
1. 配置 `vite.config.js`：`base: '/static/'`、`build.outDir: '../static'`
2. 复制旧 `index.html` 的 `<style>` 内容到 `src/style.css`
3. 复制旧 `index.html` 的 HTML 骨架到 `src/main.js` 的 innerHTML
4. 验证：`npm run dev` → 能看到页面

### Phase 2: 迁移核心基础设施 (预计 1h)

按依赖顺序迁移：

1. **`src/api.js`** — 封装所有 fetch 调用
   - `api.getAccounts()`, `api.collectHomepage()`, `api.nurtureStart()` 等
   - 每个函数返回 Promise，统一错误处理

2. **`src/router.js`** — 导航路由
   - `switchView(view)` 函数 → `import()` 动态加载视图文件
   - 侧边栏高亮逻辑
   - 子菜单展开/收起

3. **`src/state.js`** — 全局状态
   - `_allAccounts`, `_nurtureAccounts` 等
   - 事件通知机制（账号变更时通知各视图刷新）

4. **`src/components/account-selector.js`** — 核心组件
   - 从旧 JS 的 `_renderAccountSelector()` 迁移
   - 导出为 `class AccountSelector` 或 `function renderAccountSelector()`
   - 支持 `onSelectionChange` 回调

### Phase 3: 逐个迁移视图 (预计 3h)

按优先级从高到低：

1. `matrix-nurture.js` — 养号执行（含预检、执行、轮询）
2. `matrix-collect.js` — 信息采集（含登录+采集）
3. `matrix-comment.js` — 定向评论
4. `matrix-like.js` — 收藏点赞
5. `matrix-blueprints.js` — 蓝图管理
6. `matrix-accounts.js` — 账号管理
7. `ops-command.js` — 联邦指挥台
8. 其余视图

### Phase 4: 联调 + 构建 (预计 30min)

1. `npm run build` → 输出到 `../static/`
2. 重启 Dashboard 验证所有视图
3. 对比旧版，确保功能一致

---

## 五、每个视图的迁移模式

旧版模式：
```javascript
// index.html 中
async function loadMatrixXxx() {
  const el = document.getElementById('view-matrix-xxx');
  el.innerHTML = `<div>...${data}...</div>`;
}
```

新版模式：
```javascript
// views/matrix-xxx.js
import { api } from '../api.js';
import { renderAccountSelector } from '../components/account-selector.js';
import { state } from '../state.js';

export async function loadView(container) {
  const data = await api.getSomeData();
  container.innerHTML = renderTemplate(data);
  // 绑定事件...
}
```

然后 `router.js` 中：
```javascript
case 'matrix-xxx':
  import('./views/matrix-xxx.js').then(m => m.loadView(el));
  break;
```

---

## 六、关键注意事项

### 1. `<script>` 标签的迁移
旧 index.html 的 `<script>` 标签内包含所有 JS。迁移后：
- 旧文件保留为备份（重命名为 `index_legacy.html`）
- 新 Vite 项目从零构建

### 2. CSS 变量的兼容
旧样式使用 CSS 变量（`--bg`, `--text` 等），全部迁移到 `src/style.css`。
Vite 会自动注入到 HTML。

### 3. 模板字面量的迁移
Old: `` `<div>${data}</div>` ``
New: `` `<div>${data}</div>` ``  — 完全一样，只是放到单独的文件中。
Vite 对模板字面量没有特殊处理，它们就是普通 JS。

### 4. 动态 import 路由
`router.js` 使用 `import('./views/xxx.js')` 按需加载视图。
Vite 会自动代码分割，首次只加载当前视图需要的代码。

### 5. 后端兼容
后端不需要任何改动。Vite 构建产物输出到 `static/`，FastAPI 继续服务。
只是 `index.html` 变成 Vite 生成的版本（含构建后的脚本引用）。

### 6. 回滚方案
任何时候出问题：
```bash
cd frontend
git checkout -- index.html  # 恢复旧版
rm -rf frontend              # 删除 Vite 项目
```

---

## 七、验收标准

- [ ] `npm run dev` 能启动并看到完整页面
- [ ] 所有导航视图能正常渲染（22个视图）
- [ ] 养号执行能正常运行（预检→执行→验证）
- [ ] 信息采集能正常运行
- [ ] 共享账号选择器在所有视图正常
- [ ] `npm run build` 后 Dashboard 能正常服务
- [ ] 三台机器同步后都能工作

---

## 八、时间预估

| 阶段 | 时间 | 说明 |
|:-----|:-----|:------|
| Phase 1 搭建 | 30min | Vite 项目初始化 |
| Phase 2 核心 | 1h | api/router/state/组件 |
| Phase 3 视图 (7个主要) | 2h | 养号/采集/评论/点赞/蓝图/账号/指挥台 |
| Phase 3 视图 (其余) | 1h | 联邦/设置/视频工厂等 |
| Phase 4 联调 | 30min | 构建+验证+三机同步 |
| **总计** | **~5h** | |

明天上午开始，预计一天内完成。

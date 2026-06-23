# Dashboard 修复与录制标注工作台 会话记录

日期: 2026-06-22
模型: deepseek-v4-flash

## 会话脉络

### 上午-下午：Dashboard 基础修复
1. **视图迁移审计** — 33个迁移视图核对，发现多个问题
2. **API路径修复** — `sms/presets`→`accounts`, `sms/proxies`→`proxies`
3. **动态import修复** — 字符串拼接→模板字面量，Vite正确生成chunk
4. **机器状态修复** — 信任API status字段，不再被心跳覆盖
5. **账号归属修复** — ORACLE.yaml 覆盖 WPRA 去重结果
6. **is_local冲突修复** — ORACLE覆盖后 xhs_01 误判为本机
7. **机器别名修复** — Redmi-12C 指向 chengzigedeAir

### 下午-晚上：操作流程图 + 工作台（后删除）
1. **ops-flow.js** — SVG状态机流程图（已删除）
2. **ops-workbench.js** — 三栏工作台（已删除）
3. **导航栏新增原子操作分组**（已删除）

### 晚上：录制标注重写 + CommandBus修复
1. **ops-recorder.js 完整重写** — 录制启动/停止/状态 + 三栏分析
2. **CommandBus进程泄露修复** — graceful_exit pkill扩展 + 并发上限
3. **后端新增** — `/api/ops/test-atom` 单步测试端点
4. **导航精简** — 删除无用视图，录制标注并入矩阵分组

## 关键决策
- 用户不需要原子操作/流程图/工作台 → 全部删除
- 只需要录制标注功能，放在矩阵导航下
- 分析 = 前状态(结构化) + 动作(事件) + 后状态(变化)

## 待解决
- `mc task comment` 引擎 spawn 1000+ 进程，日志为空
- 评论功能全链路没跑通（引擎问题，非CommandBus）
- 录制标注页面可能还需要进一步简化

## 关键文件
- `05_tools/10_dashboard/frontend/src/views/ops-recorder.js` — 录制标注
- `05_tools/10_dashboard/services/command_bus.py` — 命令总线
- `05_tools/10_dashboard/routes/ops.py` — 操作执行路由
- `05_tools/10_dashboard/frontend/src/modules/matrix_views.js` — 导航+白名单

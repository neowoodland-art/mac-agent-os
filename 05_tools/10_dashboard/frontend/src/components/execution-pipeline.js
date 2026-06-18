/**
 * execution-pipeline.js — 统一执行管道组件 v5
 *
 * 所有操作（nurture/collect/login/logout/comment/like）共享此管道。
 * 流程: preflight → plan → confirm → dispatch → launch → poll → complete
 *
 * 用法:
 *   import { createExecutionPipeline } from './components/execution-pipeline.js';
 *
 *   const pipeline = createExecutionPipeline({
 *     type: 'nurture',
 *     getAccounts: () => selector.getSelected(),
 *     params: { rounds: 10 },
 *     logEl: document.getElementById('log'),
 *     statusEl: document.getElementById('status'),
 *   });
 *   await pipeline.execute();
 */

const API = '/api';

// 阶段定义
const PHASES = {
  IDLE:         { icon: '⏸️',  label: '就绪' },
  PREFLIGHT:    { icon: '🔍',  label: '预检机器状态' },
  PLAN:         { icon: '📋',  label: '生成执行计划' },
  CONFIRM:      { icon: '🖥️',  label: '等待确认' },
  DISPATCHING:  { icon: '📡',  label: '发送命令' },
  DISPATCHED:   { icon: '✅',  label: '命令已发送' },
  LAUNCH_WAIT:  { icon: '⏳',  label: '等待进程启动' },
  LAUNCH_CHECK: { icon: '🔍',  label: '检查进程启动' },
  RUNNING:      { icon: '🟢',  label: '运行中' },
  BROWSER_CHECK:{ icon: '🌐',  label: '检查浏览器' },
  COMPLETED:    { icon: '✅',  label: '执行完成' },
  FAILED:       { icon: '❌',  label: '执行失败' },
  CANCELLED:    { icon: '⏸️',  label: '已取消' },
};

/**
 * 创建执行管道实例
 * @param {object} opts
 * @param {string} opts.type - 操作类型 (nurture/collect/login/logout/comment/like)
 * @param {function} opts.getAccounts - 获取选中账号列表的函数
 * @param {object} [opts.params] - 操作参数 {rounds, blueprint, url, direction, corpus, ...}
 * @param {HTMLElement} [opts.logEl] - 日志显示容器
 * @param {HTMLElement} [opts.statusEl] - 状态显示容器
 * @param {function} [opts.onPhaseChange] - 阶段变化回调
 * @param {function} [opts.customPlan] - 自定义计划预览（可选）
 * @returns {object} pipeline 实例
 */
export function createExecutionPipeline(opts) {
  const type = opts.type;
  const getAccounts = opts.getAccounts;
  const params = opts.params || {};
  const logEl = opts.logEl;
  const statusEl = opts.statusEl;
  const onPhaseChange = opts.onPhaseChange;
  let cancelled = false;

  /** 当前执行中的命令列表（后端返回） */
  let commands = [];
  let pollTimer = null;

  function setPhase(phaseKey, message) {
    const phase = PHASES[phaseKey] || { icon: '❓', label: message || phaseKey };
    const msg = `${phase.icon} ${message || phase.label}`;
    if (statusEl) statusEl.innerHTML = msg;
    if (logEl) logEl.textContent += (logEl.textContent ? '\n' : '') + msg;
    if (onPhaseChange) onPhaseChange(phaseKey, message);
  }

  function log(msg) {
    if (logEl) logEl.textContent += (logEl.textContent ? '\n' : '') + msg;
  }

  async function api(path, data) {
    const url = `${API}${path}`;
    const options = {
      headers: { 'Content-Type': 'application/json' },
    };
    if (data) {
      options.method = 'POST';
      options.body = JSON.stringify(data);
    }
    const r = await fetch(url, options);
    if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
    return r.json();
  }

  /** 构建确认对话框文本 */
  function buildConfirmText(plan, machineStatus) {
    const cmds = plan.commands || [];
    let text = `📋 ${type}执行确认:\n\n`;

    // 按机器分组
    const byMachine = {};
    cmds.forEach(c => {
      if (!byMachine[c.machine]) byMachine[c.machine] = { accounts: [], info: machineStatus.machines?.[c.machine] || {} };
      byMachine[c.machine].accounts.push(c);
    });

    let hasUnreachable = false;
    Object.entries(byMachine).forEach(([machine, group]) => {
      const ms = group.info;
      const reachable = ms.reachable !== false;
      if (!reachable) hasUnreachable = true;
      const icon = reachable ? '🟢' : '🔴';
      const loc = machine === 'chengzigedeAir' ? ' (本机)' : ' (远程)';
      text += `${icon} ${machine}${loc}\n`;
      if (ms.browsers_running > 0) text += `   浏览器: ${ms.browsers_running} 个运行中\n`;
      if (ms.active_commands > 0) text += `   活跃命令: ${ms.active_commands} 个\n`;
      if (ms.slots_available !== undefined) text += `   槽位: ${ms.slots_available}/${ms.max_concurrent || 3} 可用\n`;
      if (!reachable) text += `   ⚠️ 机器不可达，命令可能无法执行\n`;

      group.accounts.forEach(c => {
        const cmdStr = c.command || '';
        text += `   🖥️ ${c.account}: ${cmdStr.slice(0, 60)}\n`;
      });
      text += '\n';
    });

    if (plan.errors && plan.errors.length) {
      text += '⚠️ 部分账号存在问题:\n';
      plan.errors.forEach(e => { text += `  ❌ ${e.account}: ${e.message}\n`; });
    }
    if (hasUnreachable) text += '\n⚠️ 部分机器不可达，继续执行将跳过这些机器';

    text += '\n确认执行？';
    return text;
  }

  /** 主入口：执行整个管道 */
  async function execute() {
    cancelled = false;

    // 获取选中账号
    const selected = typeof getAccounts === 'function' ? getAccounts() : getAccounts;
    if (!selected || selected.length === 0) {
      setPhase('IDLE', '请先选择要执行的账号');
      return;
    }

    try {
      // ── Phase 0: Preflight ──
      setPhase('PREFLIGHT', '正在检查各机器状态...');
      const machineStatus = await api('/api/ops/machines');

      if (cancelled) return;

      // ── Phase 1: Plan ──
      setPhase('PLAN', '正在生成执行计划...');
      const plan = await api('/api/ops/run', {
        type,
        accounts: selected.map(s => s.id || s),
        params: { ...params, dry_run: true },
      });

      if (cancelled) return;

      // ── Phase 2: Confirm ──
      const confirmText = buildConfirmText(plan, machineStatus);
      if (logEl) logEl.textContent = confirmText;
      if (!confirm(confirmText)) {
        setPhase('CANCELLED', '用户取消');
        return;
      }

      // ── Phase 3: Dispatch ──
      setPhase('DISPATCHING', `正在发送到 ${selected.length} 台机器...`);
      const result = await api('/api/ops/run', {
        type,
        accounts: selected.map(s => s.id || s),
        params,
      });

      commands = result.commands || [];
      if (result.errors && result.errors.length) {
        result.errors.forEach(e => log(`  ❌ ${e.account}: ${e.message}`));
      }

      // 显示调度结果
      let dispatchText = '';
      commands.forEach(cmd => {
        const icon = cmd.status === 'dispatching' ? '📡' : '❌';
        dispatchText += `  ${icon} ${cmd.account} → ${cmd.machine}`;
        if (cmd.pid) dispatchText += ` (PID:${cmd.pid})`;
        dispatchText += '\n';
        if (cmd.log_path) dispatchText += `     📄 ${cmd.log_path}\n`;
      });
      if (dispatchText) log(dispatchText);

      if (cancelled) return;

      // ── Phase 4: Launch Monitor ──
      setPhase('LAUNCH_WAIT', '等待进程启动...');
      await sleep(3000);

      if (cancelled) return;

      // ── Phase 5: Launch Check ──
      setPhase('LAUNCH_CHECK', '检查进程是否已启动...');
      const statusAfter = await api('/api/ops/status');
      const activeCmds = (statusAfter.commands || []).filter(c =>
        commands.some(cmd => cmd.run_id === c.run_id)
      );
      let startedCount = activeCmds.filter(c => c.status === 'running' || c.status === 'dispatching').length;
      if (startedCount > 0) {
        log(`  ✅ ${startedCount}/${commands.length} 个命令已启动`);
      }

      if (cancelled) return;

      // ── Phase 6: Execution Poll (with browser check) ──
      await pollExecution();

    } catch (e) {
      setPhase('FAILED', `异常: ${e.message}`);
    }
  }

  /** 轮询执行状态 */
  async function pollExecution() {
    let pollCount = 0;
    const maxPolls = 60; // 10分钟

    pollTimer = setInterval(async () => {
      if (cancelled || pollCount >= maxPolls) {
        clearInterval(pollTimer);
        return;
      }
      pollCount++;

      try {
        const statusData = await api('/api/ops/status');
        const allCmds = statusData.commands || [];

        // 匹配当前执行的命令
        const ourCmds = allCmds.filter(c =>
          commands.some(cmd => cmd.run_id === c.run_id)
        );

        if (ourCmds.length === 0) return;

        const running = ourCmds.filter(c => c.status === 'running');
        const completed = ourCmds.filter(c => c.status === 'completed');
        const failed = ourCmds.filter(c =>
          ['failed', 'timed_out', 'crashed'].includes(c.status)
        );

        // 浏览器检查（每3次轮询检查一次）
        if (pollCount % 3 === 0) {
          const machinesData = await api('/api/ops/machines');
          const browserInfo = Object.entries(machinesData.machines || {})
            .filter(([_, info]) => info.browsers_running > 0)
            .map(([m, info]) => `${m}: ${info.browsers_running}浏览器`)
            .join(', ');
          if (browserInfo) {
            setPhase('BROWSER_CHECK', `浏览器状态: ${browserInfo}`);
          }
        }

        // 状态报告
        if (running.length > 0) {
          const elapsed = Math.round(running[0].elapsed_sec || 0);
          const msg = running.map(c =>
            `${c.account}: ${c.message || '运行中'} (${elapsed}s)`
          ).join(' | ');
          setPhase('RUNNING', msg);
        }

        // 完成检测
        const done = completed.length + failed.length;
        const total = ourCmds.length;
        if (done === total) {
          clearInterval(pollTimer);
          const successRate = completed.length > 0
            ? `, 成功率 ${Math.round(completed.length / total * 100)}%`
            : '';
          setPhase('COMPLETED', `${completed.length}/${total} 完成${successRate}`);
        }

      } catch (e) {
        // 静默处理轮询错误
      }
    }, 5000);
  }

  /** 取消 */
  function cancel() {
    cancelled = true;
    if (pollTimer) clearInterval(pollTimer);
    setPhase('CANCELLED', '用户取消');
  }

  return { execute, cancel };
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

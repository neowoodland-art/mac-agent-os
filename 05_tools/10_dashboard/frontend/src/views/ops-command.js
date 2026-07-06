/**
 * 联邦指挥台视图 (v5 — 调度器 v4 适配)
 *
 * 基于新调度模型:
 *   - 一条全局队列，P0 隔 P1 交替
 *   - 每台机器 3 slot 从队首取任务
 *   - 事件推送 + 15 秒轮询兜底
 *   - 实时显示三台机器状态
 */
import { apiRequest } from '../router.js';

let _pollTimer = null;
let _lastEvents = [];

export async function loadView(container) {
  container.innerHTML = `
    <div style="padding:16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <div style="font-weight:700;font-size:16px">🚀 联邦指挥台</div>
        <div style="display:flex;gap:8px;align-items:center">
          <span id="cmdLastUpdate" style="font-size:10px;color:var(--text2)"></span>
          <button onclick="window._cmdRefresh()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔄 刷新</button>
          <label style="font-size:10px;color:var(--text2)"><input type="checkbox" id="cmdAutoRefresh" checked onchange="window._cmdToggleAuto()"> 自动(15s)</label>
        </div>
      </div>

      <!-- 告警栏 -->
      <div id="cmdAlerts" style="display:none;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:8px;margin-bottom:8px;font-size:11px">
        <div style="font-weight:600;margin-bottom:4px">⚠️ 告警</div>
        <div id="cmdAlertsList"></div>
      </div>

      <!-- 操作栏 -->
      <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;align-items:center;padding:6px 8px;background:var(--bg2);border-radius:8px;border:1px solid var(--border)">
        <span style="font-size:11px;font-weight:600">🛠️ 管理:</span>
        <select id="cmdResetMachine" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 6px;border-radius:4px;font-size:10px"><option value="">全部机器</option></select>
        <button onclick="window._cmdResetMachine()" style="background:rgba(220,38,38,.1);color:#ef4444;border:1px solid rgba(220,38,38,.3);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔄 初始化机器</button>
        <button onclick="window._cmdResetAll()" style="background:rgba(220,38,38,.1);color:#ef4444;border:1px solid rgba(220,38,38,.3);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:11px">⚠️ 重置全部</button>
        <span id="cmdResetResult" style="font-size:10px;color:var(--text2)"></span>
      </div>

      <!-- 三台机器面板 -->
      <div id="cmdMachinesGrid"></div>

      <!-- 最近事件 -->
      <div id="cmdEventLog" style="margin-top:12px"></div>
    </div>`;

  registerGlobals(container);
  await refreshView(container);
  startAutoRefresh(container);
}

export function unloadView() { stopAutoRefresh(); }

function startAutoRefresh(c) {
  stopAutoRefresh();
  _pollTimer = setInterval(() => {
    if (document.getElementById('cmdAutoRefresh')?.checked) refreshView(c, true);
  }, 15000);
}
function stopAutoRefresh() { if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; } }

function registerGlobals(container) {
  if (window._cmdRegisteredV5) return;
  window._cmdRegisteredV5 = true;

  window._cmdRefresh = () => refreshView(container);
  window._cmdToggleAuto = () => {
    if (document.getElementById('cmdAutoRefresh')?.checked) startAutoRefresh(container);
    else stopAutoRefresh();
  };

  window._cmdResetMachine = async () => {
    const sel = document.getElementById('cmdResetMachine');
    const machine = sel?.value || '';
    if (!machine) { alert('请先选择要初始化的机器'); return; }
    if (!confirm(`确定初始化机器 ${machine}？\n将杀掉所有活跃任务和浏览器进程`)) return;
    const el = document.getElementById('cmdResetResult');
    if (el) el.textContent = '⏳';
    try {
      await apiRequest('/ops/reset', {method:'POST', body:JSON.stringify({machine})});
      if (el) el.textContent = `✅ ${machine} 已初始化`;
      refreshView(container);
    } catch(e) { if (el) el.textContent = '❌ '+e.message; }
  };

  window._cmdResetAll = async () => {
    if (!confirm('⚠️ 重置全部机器？\n将杀掉所有活跃任务和浏览器进程')) return;
    const el = document.getElementById('cmdResetResult');
    if (el) el.textContent = '⏳';
    try {
      const r = await apiRequest('/ops/reset', {method:'POST', body:JSON.stringify({})});
      if (el) el.textContent = `✅ 已重置 ${Object.keys(r.machines||{}).length} 台`;
      refreshView(container);
    } catch(e) { if (el) el.textContent = '❌ '+e.message; }
  };

  window._cmdStop = async (machine, taskId) => {
    if (!confirm(`停止 ${taskId}?`)) return;
    try {
      await apiRequest('/ops/task/cancel', {method:'POST', body:JSON.stringify({task_id:taskId, machine:machine})});
      refreshView(container);
    } catch(e) { alert('❌ '+e.message); }
  };
}

// ── 主渲染 ──
async function refreshView(container, silent = false) {
  const updateEl = document.getElementById('cmdLastUpdate');
  if (updateEl) updateEl.textContent = `🕐 ${new Date().toLocaleTimeString()}`;

  try {
    // 同时拉取调度器队列 + 事件 + 机器状态
    const [queueData, eventsData] = await Promise.all([
      apiRequest('/ops/queue?local_only=false').catch(() => ({machines:{}})),
      apiRequest('/ops/task-events?limit=50').catch(() => ({events:[]})),
    ]);

    _lastEvents = (eventsData.events || []).slice(-30);

    const machines = queueData?.machines || {};
    const machineNames = Object.keys(machines);

    // 更新机器筛选下拉
    for (const selId of ['cmdResetMachine']) {
      const sel = document.getElementById(selId);
      if (sel && sel.options.length <= 1) {
        machineNames.forEach(m => {
          const opt = document.createElement('option');
          opt.value = m; opt.textContent = m;
          sel.appendChild(opt);
        });
      }
    }

    renderAlerts(queueData);
    renderMachines(queueData);
    renderEvents();
  } catch (e) {
    if (!silent) {
      document.getElementById('cmdMachinesGrid').innerHTML =
        `<div style="color:#ef4444;font-size:12px;padding:20px;text-align:center">❌ 加载失败: ${e.message}</div>`;
    }
  }
}

// ── 告警 ──
function renderAlerts(queueData) {
  const el = document.getElementById('cmdAlerts');
  const list = document.getElementById('cmdAlertsList');
  if (!el || !list) return;
  const alerts = [];

  for (const [name, status] of Object.entries(queueData?.machines || {})) {
    if (status?.error) alerts.push({machine:name, level:'error', msg:`🔴 不可达: ${status.error}`});
    const counts = status?.counts || {};
    if (counts?.failed > 0) alerts.push({machine:name, level:'warning', msg:`❌ ${counts.failed} 个任务失败`});
  }

  if (alerts.length) {
    el.style.display = 'block';
    list.innerHTML = alerts.map(a => {
      const bg = a.level === 'error' ? '#fef2f2' : '#fffbeb';
      const border = a.level === 'error' ? '#fecaca' : '#fde68a';
      return `<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 8px;margin-bottom:2px;background:${bg};border:1px solid ${border};border-radius:4px;font-size:10px">
        <span>[${a.machine}] ${a.msg}</span>
        <button onclick="this.parentElement.remove()" style="background:none;border:none;cursor:pointer;font-size:9px;color:var(--text2)">✕</button>
      </div>`;
    }).join('');
  } else {
    el.style.display = 'none';
  }
}

// ── 机器卡片 + Slot + 队列 ──
function renderMachines(queueData) {
  const grid = document.getElementById('cmdMachinesGrid');
  const machines = queueData?.machines || {};

  let html = '';
  for (const [name, status] of Object.entries(machines)) {
    const isOnline = !status?.error;
    const slots = status?.slots || {};
    const slotList = (Array.isArray(slots) ? slots : (slots.slots || slots.list || []));
    const used = slots?.used || 0;
    const max = slots?.max || 3;
    const counts = status?.counts || {};
    const queue = status?.queue || [];
    const queueSizes = status?.queue_sizes || {};

    // 按 P0/P1 分类队列
    const p0queue = queue.filter(q => q.queue === 'P0');
    const p1queue = queue.filter(q => q.queue === 'P1');

    // 机器卡片
    html += `<details open style="margin-bottom:8px;background:var(--bg2);border-radius:10px;border:1px solid var(--border);overflow:hidden">
      <summary style="padding:8px 12px;cursor:pointer;display:flex;align-items:center;gap:8px;background:var(--bg3)">
        <span style="font-size:16px">${isOnline ? '🟢' : '🔴'}</span>
        <span style="font-weight:600;font-size:13px">${name}</span>
        <span style="font-size:10px;color:var(--text2)">${used}/${max} slot · 完成${counts?.completed||0} 失败${counts?.failed||0}</span>
        <span style="margin-left:auto;font-size:10px;color:var(--text2)">
          P0:${queueSizes?.priority||0} P1:${queueSizes?.normal||0} P2:${queueSizes?.filler||0}
        </span>
      </summary>
      <div style="padding:8px 12px">

        <!-- 3 slot 显示 -->
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:8px">`;
    for (let i = 0; i < max; i++) {
      const slot = slotList.find(s => s.slot_id === i) || {};
      const acctId = slot.account_id || '';
      if (!acctId) {
        html += `<div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px dashed var(--border);display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:70px">
          <div style="font-size:18px;opacity:0.2">○</div>
          <div style="font-size:9px;color:var(--text2)">Slot ${i+1} 空闲</div>
        </div>`;
        continue;
      }
      const nick = slot.nickname || slot.account_id || '';
      const platIcon = (slot.platform||'') === 'xiaohongshu' ? '📕' : '🎵';
      const stepIdx = slot.step_index || 0;
      const totalSteps = slot.total_steps || 0;
      const h = slot.health || 'healthy';
      const healthIcon = h === 'healthy' ? '🟢' : h === 'warning' ? '🟡' : '🔴';

      html += `<div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600;font-size:11px">${platIcon} ${slot.account_id||''}</span>
          <span style="font-size:9px;color:var(--text2)">${healthIcon}</span>
        </div>
        <div style="font-size:9px;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${nick}</div>
        ${slot.current_step ? `<div style="font-size:8px;color:var(--text2);margin-top:2px">🔧 ${slot.current_step}</div>` : ''}
        ${slot.elapsed_sec ? `<div style="font-size:8px;color:var(--text2)">⏱ ${_timeStr(slot.elapsed_sec)}</div>` : ''}
        ${totalSteps > 0 ? `
        <div style="margin-top:4px">
          <div style="display:flex;justify-content:space-between;font-size:8px;color:var(--text2)">
            <span>${stepIdx}/${totalSteps}</span>
            <span>${Math.round(stepIdx/(totalSteps||1)*100)}%</span>
          </div>
          <div style="height:3px;background:var(--bg2);border-radius:2px;margin-top:2px">
            <div style="height:100%;width:${Math.min(100,stepIdx/(totalSteps||1)*100)}%;background:#22c55e;border-radius:2px"></div>
          </div>
        </div>` : ''}
      </div>`;
    }
    html += `</div>`;

    // 队列详情
    const allQueue = [...p0queue, ...p1queue];
    if (allQueue.length) {
      html += `<div style="font-size:10px;font-weight:600;margin-bottom:4px;color:var(--text2)">📋 排队队列 (${allQueue.length})</div>
      <div style="font-size:9px">`;
      allQueue.slice(0, 10).forEach(t => {
        const label = t.queue === 'P0' ? '🔴P0' : t.queue === 'P1' ? '🟢P1' : '⚪P2';
        const taskInfo = t.task_id ? t.task_id.split('_').slice(0,3).join('_') : '';
        html += `<div style="display:flex;gap:4px;padding:2px 4px;border-bottom:1px solid var(--border)">
          <span style="min-width:32px">${label}</span>
          <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${taskInfo}</span>
        </div>`;
      });
      if (allQueue.length > 10) html += `<div style="color:var(--text2);padding:2px 4px">...还有 ${allQueue.length-10} 个</div>`;
      html += `</div>`;
    } else {
      html += `<div style="font-size:9px;color:var(--text2);padding:2px 0">📋 队列为空</div>`;
    }

    html += `</div></details>`;
  }

  grid.innerHTML = html || '<div style="font-size:12px;color:var(--text2);padding:20px">暂无机器数据</div>';
}

// ── 最近事件 ──
function renderEvents() {
  const el = document.getElementById('cmdEventLog');
  if (!el || !_lastEvents.length) {
    if (el) el.innerHTML = '';
    return;
  }
  const eventIcons = {started:'▶️', completed:'✅', failed:'❌'};
  el.innerHTML = `
    <details>
      <summary style="cursor:pointer;font-weight:600;font-size:11px;margin-bottom:4px">📡 最近事件 (${_lastEvents.length})</summary>
      <div style="font-size:9px;max-height:150px;overflow-y:auto">
        ${_lastEvents.slice(-15).reverse().map(e => {
          const icon = eventIcons[e.event] || '❓';
          const acct = (e.accounts || []).join(',') || '';
          return `<div style="display:flex;gap:4px;padding:2px 4px;border-bottom:1px solid var(--border)">
            <span>${icon}</span>
            <span style="min-width:70px;color:var(--text2)">${e.machine||''}</span>
            <span style="color:var(--text2)">${e.cmd_type||''}</span>
            <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${acct}</span>
            <span style="color:var(--text2)">${e.time ? e.time.slice(11,19) : ''}</span>
          </div>`;
        }).join('')}
      </div>
    </details>`;
}

function _timeStr(sec) {
  if (!sec || sec <= 0) return '';
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m > 0 ? `${m}m${s}s` : `${s}s`;
}

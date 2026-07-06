/**
 * 联邦指挥台视图 (v5.1 — 调度器 v4 适配)
 *
 * 显示:
 *   每台机器一个可折叠面板
 *   每个 slot: 账号ID | 昵称 | 手机号 | 任务类型 | 进度 | 耗时
 *   排队队列: P0/P1 分类显示
 *   最近事件流
 *   自动刷新不重置折叠状态
 */
import { apiRequest } from '../router.js';

let _pollTimer = null;
let _lastEvents = [];
let _accountCache = [];       // 账号信息缓存（手机号/昵称）
let _machineOpenState = {};   // 折叠状态缓存: {machineName: true/false}

export async function loadView(container) {
  // 预加载账号信息
  try {
    const r = await apiRequest('/v2/accounts');
    _accountCache = r.accounts || [];
  } catch(e) { _accountCache = []; }

  container.innerHTML = `
    <div style="padding:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <div style="font-weight:700;font-size:16px">🚀 联邦指挥台</div>
        <div style="display:flex;gap:8px;align-items:center">
          <span id="cmdLastUpdate" style="font-size:10px;color:var(--text2)"></span>
          <button onclick="window._cmdRefresh()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔄 刷新</button>
          <label style="font-size:10px;color:var(--text2)"><input type="checkbox" id="cmdAutoRefresh" checked onchange="window._cmdToggleAuto()"> 自动(15s)</label>
        </div>
      </div>

      <div id="cmdAlerts" style="display:none;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:8px;margin-bottom:8px;font-size:11px">
        <div style="font-weight:600;margin-bottom:4px">⚠️ 告警</div>
        <div id="cmdAlertsList"></div>
      </div>

      <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;align-items:center;padding:6px 8px;background:var(--bg2);border-radius:8px;border:1px solid var(--border)">
        <span style="font-size:11px;font-weight:600">🛠️ 管理:</span>
        <select id="cmdResetMachine" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 6px;border-radius:4px;font-size:10px"><option value="">全部机器</option></select>
        <button onclick="window._cmdResetMachine()" style="background:rgba(220,38,38,.1);color:#ef4444;border:1px solid rgba(220,38,38,.3);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔄 初始化机器</button>
        <button onclick="window._cmdResetAll()" style="background:rgba(220,38,38,.1);color:#ef4444;border:1px solid rgba(220,38,38,.3);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:11px">⚠️ 重置全部</button>
        <span id="cmdResetResult" style="font-size:10px;color:var(--text2)"></span>
      </div>

      <div id="cmdMachinesGrid"></div>
      <div id="cmdEventLog" style="margin-top:12px"></div>
    </div>`;

  registerGlobals(container);
  await refreshView(container);
  startAutoRefresh(container);
}

export function unloadView() { stopAutoRefresh(); }
function startAutoRefresh(c) { stopAutoRefresh(); _pollTimer = setInterval(() => { if (document.getElementById('cmdAutoRefresh')?.checked) refreshView(c, true); }, 15000); }
function stopAutoRefresh() { if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; } }

function registerGlobals(container) {
  if (window._cmdRegisteredV51) return;
  window._cmdRegisteredV51 = true;
  window._cmdRefresh = () => refreshView(container);
  window._cmdToggleAuto = () => { if (document.getElementById('cmdAutoRefresh')?.checked) startAutoRefresh(container); else stopAutoRefresh(); };
  window._cmdResetMachine = async () => {
    const sel = document.getElementById('cmdResetMachine');
    const machine = sel?.value || '';
    if (!machine) { alert('请先选择机器'); return; }
    if (!confirm(`确定初始化 ${machine}？将杀掉所有活跃任务和浏览器`)) return;
    const el = document.getElementById('cmdResetResult');
    if (el) el.textContent = '⏳';
    try { await apiRequest('/ops/reset', {method:'POST', body:JSON.stringify({machine})}); if (el) el.textContent = `✅ ${machine} 已初始化`; refreshView(container); } catch(e) { if (el) el.textContent = '❌ '+e.message; }
  };
  window._cmdResetAll = async () => {
    if (!confirm('⚠️ 重置全部机器？将杀掉所有任务和浏览器')) return;
    const el = document.getElementById('cmdResetResult');
    if (el) el.textContent = '⏳';
    try { const r = await apiRequest('/ops/reset', {method:'POST', body:JSON.stringify({})}); if (el) el.textContent = `✅ 已重置 ${Object.keys(r.machines||{}).length} 台`; refreshView(container); } catch(e) { if (el) el.textContent = '❌ '+e.message; }
  };
  window._cmdStop = async (machine, taskId) => {
    if (!confirm(`停止 ${taskId}?`)) return;
    try { await apiRequest('/ops/task/cancel', {method:'POST', body:JSON.stringify({task_id:taskId, machine:machine})}); refreshView(container); } catch(e) { alert('❌ '+e.message); }
  };
}

// ── 主刷新 ──
async function refreshView(container, silent = false) {
  const updateEl = document.getElementById('cmdLastUpdate');
  if (updateEl) updateEl.textContent = `🕐 ${new Date().toLocaleTimeString()}`;
  try {
    const [queueData, eventsData] = await Promise.all([
      apiRequest('/ops/queue?local_only=false').catch(() => ({machines:{}})),
      apiRequest('/ops/task-events?limit=50').catch(() => ({events:[]})),
    ]);
    _lastEvents = (eventsData.events || []).slice(-30);

    // 保存当前折叠状态
    document.querySelectorAll('#cmdMachinesGrid details').forEach(el => {
      const summary = el.querySelector('summary');
      if (summary) {
        const text = summary.textContent || '';
        for (const name of Object.keys(queueData?.machines || {})) {
          if (text.includes(name)) {
            _machineOpenState[name] = el.open;
            break;
          }
        }
      }
    });

    const machines = queueData?.machines || {};
    for (const selId of ['cmdResetMachine']) {
      const sel = document.getElementById(selId);
      if (sel && sel.options.length <= 1) {
        Object.keys(machines).forEach(m => { const o = document.createElement('option'); o.value = m; o.textContent = m; sel.appendChild(o); });
      }
    }

    renderAlerts(queueData);
    renderMachines(queueData);
    renderEvents();
  } catch (e) {
    if (!silent) document.getElementById('cmdMachinesGrid').innerHTML = `<div style="color:#ef4444;font-size:12px;padding:20px;text-align:center">❌ ${e.message}</div>`;
  }
}

// ── 告警 ──
function renderAlerts(queueData) {
  const el = document.getElementById('cmdAlerts');
  const list = document.getElementById('cmdAlertsList');
  if (!el || !list) return;
  const alerts = [];
  for (const [name, s] of Object.entries(queueData?.machines || {})) {
    if (s?.error) alerts.push({machine:name, level:'error', msg:`🔴 不可达: ${s.error}`});
    if ((s?.counts?.failed||0) > 0) alerts.push({machine:name, level:'warning', msg:`❌ ${s.counts.failed} 个任务失败`});
  }
  if (alerts.length) {
    el.style.display = 'block';
    list.innerHTML = alerts.map(a => `<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 8px;margin-bottom:2px;background:${a.level==='error'?'#fef2f2':'#fffbeb'};border:1px solid ${a.level==='error'?'#fecaca':'#fde68a'};border-radius:4px;font-size:10px"><span>[${a.machine}] ${a.msg}</span><button onclick="this.parentElement.remove()" style="background:none;border:none;cursor:pointer;font-size:9px;color:var(--text2)">✕</button></div>`).join('');
  } else { el.style.display = 'none'; }
}

// ── 机器 + Slot + 队列 ──
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
    const p0queue = queue.filter(q => q.queue === 'P0');
    const p1queue = queue.filter(q => q.queue === 'P1');
    const p2queue = queue.filter(q => q.queue === 'P2');
    const isOpen = _machineOpenState[name] !== false; // 默认展开

    html += `<details ${isOpen ? 'open' : ''} style="margin-bottom:8px;background:var(--bg2);border-radius:10px;border:1px solid var(--border);overflow:hidden">
      <summary style="padding:8px 12px;cursor:pointer;display:flex;align-items:center;gap:8px;background:var(--bg3)">
        <span style="font-size:16px">${isOnline ? '🟢' : '🔴'}</span>
        <span style="font-weight:600;font-size:13px">${name}</span>
        <span style="font-size:10px;color:var(--text2)">${used}/${max} slot</span>
        <span style="font-size:10px;color:var(--text2)">✅${counts?.completed||0} ❌${counts?.failed||0}</span>
        <span style="margin-left:auto;font-size:10px;color:var(--text2)">P0:${queueSizes?.priority||0} P1:${queueSizes?.normal||0}</span>
      </summary>
      <div style="padding:8px 12px">
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:8px">`;
    for (let i = 0; i < max; i++) {
      const slot = slotList.find(s => s.slot_id === i) || {};
      const acctId = slot.account_id || '';
      if (!acctId) {
        html += `<div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px dashed var(--border);display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:80px">
          <div style="font-size:18px;opacity:0.2">○</div>
          <div style="font-size:10px;color:var(--text2)">Slot ${i+1}</div>
          <div style="font-size:9px;color:var(--text2)">空闲</div>
        </div>`;
        continue;
      }
      const info = _acctInfo(acctId);
      const nickname = slot.nickname || info.nickname || '';
      const phone = info.phone || '';
      const identityDir = slot.browser_id || info.identity_dir || '';
      const platIcon = (slot.platform||info.platform||'') === 'xiaohongshu' ? '📕' : '🎵';
      const stepIdx = slot.step_index || 0;
      const totalSteps = slot.total_steps || 0;
      const health = slot.health || 'healthy';
      const healthIcon = health === 'healthy' ? '🟢' : health === 'warning' ? '🟡' : '🔴';

      // 确定任务类型（从活跃任务 cmd_type 推断，兜底从 blueprint）
      const activeTask = (status.active || status.tasks || []).find(t => t.slot_id === i);
      const cmdType = activeTask?.cmd_type || slot.cmd_type || '';
      const taskType = cmdType.includes('nurture') || cmdType.includes('daily') ? '养号'
        : cmdType.includes('comment') || cmdType.includes('smart_comment') ? '评论'
        : cmdType.includes('collect') || cmdType.includes('read_profile') ? '采集'
        : cmdType.includes('interact') ? '互动'
        : cmdType.includes('login') ? '登录'
        : cmdType.includes('like') ? '点赞'
        : slot.blueprint?.includes('daily') ? '养号'
        : slot.blueprint?.includes('comment') ? '评论'
        : slot.blueprint?.includes('collect') ? '采集'
        : '养号'; // 兜底显示养号（绝大多数任务是养号）

      html += `<div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px">
          <span style="font-weight:600;font-size:11px">${platIcon} ${acctId}</span>
          <span style="font-size:9px">${healthIcon}</span>
        </div>
        ${nickname ? `<div style="font-size:9px;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">👤 ${nickname}</div>` : ''}
        ${phone ? `<div style="font-size:9px;color:var(--text2)">📱 ${phone}</div>` : ''}
        ${identityDir ? `<div style="font-size:8px;color:var(--text2)">🔑 ${identityDir}</div>` : ''}
        <div style="margin-top:3px;font-size:10px;font-weight:500;color:${taskType==='评论'?'#ef4444':taskType==='养号'?'#22c55e':'#8b8fa3'}">${taskType === '评论' ? '🔴' : taskType === '养号' ? '🟢' : '⚪'} ${taskType}</div>
        ${slot.current_step ? `<div style="font-size:8px;color:var(--text2);margin-top:1px">🔧 ${slot.current_step}</div>` : ''}
        ${slot.elapsed_sec ? `<div style="font-size:8px;color:var(--text2)">⏱ ${_timeStr(slot.elapsed_sec)}</div>` : ''}
        ${totalSteps > 0 ? `
        <div style="margin-top:4px">
          <div style="display:flex;justify-content:space-between;font-size:8px;color:var(--text2)"><span>步骤 ${stepIdx}/${totalSteps}</span><span>${Math.round(stepIdx/(totalSteps||1)*100)}%</span></div>
          <div style="height:3px;background:var(--bg2);border-radius:2px;margin-top:2px"><div style="height:100%;width:${Math.min(100,stepIdx/(totalSteps||1)*100)}%;background:#22c55e;border-radius:2px"></div></div>
        </div>` : ''}
      </div>`;
    }
    html += `</div>`;

    // 队列
    const allQ = [...p0queue, ...p1queue, ...p2queue];
    if (allQ.length) {
      html += `<div style="font-size:10px;font-weight:600;margin-bottom:4px">📋 排队 (${allQ.length})`;
      if (p0queue.length) html += ` <span style="color:#ef4444;font-weight:400">🔴P0=${p0queue.length}</span>`;
      if (p1queue.length) html += ` <span style="color:#22c55e;font-weight:400">🟢P1=${p1queue.length}</span>`;
      if (p2queue.length) html += ` <span style="color:var(--text2);font-weight:400">⚪P2=${p2queue.length}</span>`;
      html += `</div><div style="font-size:9px">`;
      allQ.slice(0, 15).forEach(t => {
        const label = t.queue === 'P0' ? '🔴' : t.queue === 'P1' ? '🟢' : '⚪';
        const tid = t.task_id || '';
        // 从 task_id 推断任务类型
        const tt = tid.includes('nurture') ? '养号' : tid.includes('comment') || tid.includes('smart') ? '评论' : tid.includes('collect') ? '采集' : tid.includes('like') ? '点赞' : '';
        // 提取账号名
        const parts = tid.split('_');
        const acct = parts.length > 1 ? parts.slice(-1)[0] : '';
        html += `<div style="display:flex;gap:4px;padding:2px 4px;border-bottom:1px solid var(--border)">
          <span style="min-width:16px">${label}</span>
          <span style="color:var(--text2);min-width:40px">${tt||'?'}</span>
          <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${acct ? acct : tid.slice(0,30)}</span>
        </div>`;
      });
      if (allQ.length > 15) html += `<div style="color:var(--text2);padding:2px 4px;font-size:9px">...还有 ${allQ.length-15} 个</div>`;
      html += `</div>`;
    } else {
      html += `<div style="font-size:9px;color:var(--text2);padding:2px 0">📋 队列为空</div>`;
    }
    html += `</div></details>`;
  }
  grid.innerHTML = html || '<div style="font-size:12px;color:var(--text2);padding:20px">暂无数据</div>';
}

// ── 事件 ──
function renderEvents() {
  const el = document.getElementById('cmdEventLog');
  if (!el || !_lastEvents.length) { if (el) el.innerHTML = ''; return; }
  const icons = {started:'▶️', completed:'✅', failed:'❌'};
  el.innerHTML = `<details>
    <summary style="cursor:pointer;font-weight:600;font-size:11px;margin-bottom:4px">📡 最近事件 (${_lastEvents.length})</summary>
    <div style="font-size:9px;max-height:150px;overflow-y:auto">${_lastEvents.slice(-15).reverse().map(e => {
      const acct = (e.accounts||[]).join(',')||'';
      return `<div style="display:flex;gap:4px;padding:2px 4px;border-bottom:1px solid var(--border)"><span>${icons[e.event]||'❓'}</span><span style="min-width:70px;color:var(--text2)">${e.machine||''}</span><span style="color:var(--text2)">${e.cmd_type||''}</span><span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${acct}</span><span style="color:var(--text2)">${e.time ? e.time.slice(11,19) : ''}</span></div>`;
    }).join('')}</div></details>`;
}

function _acctInfo(accountId) {
  const a = _accountCache.find(x => x.id === accountId) || {};
  const o = _accountCache.find(x => x.phone === accountId) || {};
  return a.id ? a : o;
}
function _timeStr(sec) {
  if (!sec || sec <= 0) return '';
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m > 0 ? `${m}m${s}s` : `${s}s`;
}

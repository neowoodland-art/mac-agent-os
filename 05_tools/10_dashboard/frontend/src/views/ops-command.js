/**
 * 联邦指挥台视图 (v4.3.0 — Phase 2b: 9 轨道 slot 视图)
 *
 * 显示:
 *   3 台机器 × 3 slot = 9 轨道实时状态
 *   每个 slot: 账号ID | 手机号 | 昵称 | 优先级 | 进度 | 健康
 *   任务队列 + P0/P1/P2 优先级过滤
 *   自动刷新 15 秒
 */

import { apiRequest } from '../router.js';

let _pollTimer = null;
let _accountCache = [];

export async function loadView(container) {
  // 预加载账号数据（用于 slot 卡片展示手机号/昵称）
  try {
    const acctRes = await apiRequest('/v2/accounts');
    _accountCache = acctRes.accounts || [];
  } catch(e) {
    _accountCache = [];
  }

  container.innerHTML = `
    <div style="padding:16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <div style="font-weight:700;font-size:16px">🚀 联邦指挥台</div>
        <div style="display:flex;gap:8px;align-items:center">
          <span id="cmdLastUpdate" style="font-size:10px;color:var(--text2)"></span>
          <button onclick="window._cmdRefresh()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔄 刷新</button>
          <label style="font-size:10px;color:var(--text2)">
            <input type="checkbox" id="cmdAutoRefresh" checked onchange="window._cmdToggleAuto()"> 自动(15s)
          </label>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;align-items:center">
        <span style="font-size:11px;color:var(--text2);font-weight:600">筛选:</span>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P0" checked onchange="window._cmdRefresh()"> 🔴 优先</label>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P1" checked onchange="window._cmdRefresh()"> 🟢 日常</label>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P2" onchange="window._cmdRefresh()"> ⚪ 闲时</label>
        <span style="margin-left:12px;font-size:11px;color:var(--text2);font-weight:600">机器:</span>
        <select id="cmdMachineFilter" onchange="window._cmdRefresh()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 6px;border-radius:4px;font-size:10px">
          <option value="all">全部</option>
        </select>
        <span id="cmdQueueCount" style="font-size:10px;color:var(--text2);margin-left:auto"></span>
      </div>

      <!-- 告警中心 -->
      <div id="cmdAlerts" style="display:none;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:8px;margin-bottom:8px;font-size:11px">
        <div style="font-weight:600;margin-bottom:4px">⚠️ 告警</div>
        <div id="cmdAlertsList"></div>
      </div>

      <!-- 9 轨道 slot 视图 -->
      <div id="cmdTrackGrid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px"></div>

      <!-- 各机任务队列详情 -->
      <div id="cmdQueueDetail"></div>
    </div>`;

  // 注册全局函数
  if (!window._cmdRegistered2) {
    window._cmdRegistered2 = true;
    window._cmdRefresh = () => refreshView(container);
    window._cmdStop = async (machine, taskId) => {
      if (!confirm(`停止 ${taskId} ?`)) return;
      try {
        await apiRequest('/ops/task/cancel', {method:'POST', body:JSON.stringify({task_id:taskId, machine:machine})});
        alert('✅ 已停止');
        refreshView(container);
      } catch(e) { alert('❌ '+e.message); }
    };
    window._cmdRemoveQueue = (machine, idx) => alert('移出队列功能开发中');
    window._cmdToggleAuto = () => {
      if (document.getElementById('cmdAutoRefresh')?.checked) startAutoRefresh(container);
      else stopAutoRefresh();
    };
    window._cmdRefresh();
  }

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

function stopAutoRefresh() {
  if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
}

// ── 辅助：从账号缓存中查找手机号/昵称 ──
function _acctInfo(accountId) {
  const a = _accountCache.find(x => x.id === accountId);
  return a || {};
}

function _timeStr(ts) {
  if (!ts || ts <= 0) return '';
  const now = Date.now()/1000;
  if (ts > now) return '刚刚';  // 时间戳还没到（未来）
  const s = Math.floor(now - ts);
  if (s < 5) return '刚刚';
  if (s < 60) return `${s}秒`;
  if (s < 3600) return `${Math.floor(s/60)}分${s%60}秒`;
  return `${Math.floor(s/3600)}时${Math.floor((s%3600)/60)}分`;
}

function _progressPct(idx, total) {
  if (!total || total <= 0) return '';
  return `${Math.round((idx/total)*100)}%`;
}

function _slotStatusColor(slot) {
  if (!slot.account_id) return '#8b8fa3'; // 空闲
  const h = slot.health || 'healthy';
  if (h === 'healthy') return '#22c55e';
  if (h === 'warning') return '#eab308';
  return '#ef4444';
}

function _slotBorder(slot) {
  if (!slot.account_id) return '1px solid var(--border)';
  const h = slot.health || 'healthy';
  if (h === 'healthy') return '1px solid #22c55e';
  if (h === 'warning') return '1px solid #eab308';
  return '1px solid #ef4444';
}

function _slotBg(slot) {
  if (!slot.account_id) return 'var(--bg3)';
  const h = slot.health || 'healthy';
  if (h === 'healthy') return '#22c55e10';
  if (h === 'warning') return '#eab30810';
  return '#ef444410';
}

async function refreshView(container, silent = false) {
  try {
    const [queueData, machineData] = await Promise.all([
      apiRequest('/ops/queue'),
      apiRequest('/ops/machines'),
    ]);

    if (!silent) {
      const el = document.getElementById('cmdLastUpdate');
      if (el) el.textContent = `🕐 ${new Date().toLocaleTimeString()}`;
    }

    renderAlerts(queueData);
    renderTrackGrid(queueData);
    renderQueueDetail(queueData);
  } catch (e) {
    if (!silent) {
      document.getElementById('cmdTrackGrid').innerHTML =
        `<div style="color:#ef4444;font-size:12px;grid-column:1/-1;padding:20px;text-align:center">❌ 加载失败: ${e.message}</div>`;
    }
  }
}

async function renderAlerts(queueData) {
  const el = document.getElementById('cmdAlerts');
  const list = document.getElementById('cmdAlertsList');
  if (!el || !list) return;
  const alerts = [];
  const machines = queueData?.machines || {};

  // 机器级别告警
  for (const [name, status] of Object.entries(machines)) {
    const counts = status?.counts || {};
    if (status?.error) alerts.push({machine:name, level:'error', msg:`🔴 不可达: ${status.error}`});
    if (counts?.failed > 0) alerts.push({machine:name, level:'warning', msg:`❌ ${counts.failed} 个任务失败`});
  }

  // 账号健康告警（从 V2 API 获取）
  try {
    const summary = await apiRequest('/v2/status-summary');
    if (summary.banned > 0) alerts.push({machine:'全域', level:'error', msg:`⛔ ${summary.banned} 个账号已封号`});
    if (summary.cookie_expiring > 0) alerts.push({machine:'全域', level:'warning', msg:`🟡 ${summary.cookie_expiring} 个账号 Cookie 即将过期`});
    if (summary.no_cookie > 0) alerts.push({machine:'全域', level:'info', msg:`🔴 ${summary.no_cookie} 个账号无 Cookie`});
    if (summary.unknown > 0) alerts.push({machine:'全域', level:'info', msg:`⚪ ${summary.unknown} 个账号状态未知`});
  } catch(e) {}

  if (alerts.length > 0) {
    el.style.display = 'block';
    const showP0 = document.querySelector('.cmdFilter[value="P0"]')?.checked ?? true;
    const showP1 = document.querySelector('.cmdFilter[value="P1"]')?.checked ?? true;
    const showP2 = document.querySelector('.cmdFilter[value="P2"]')?.checked ?? false;
    list.innerHTML = alerts.map(a => {
      const bg = a.level === 'error' ? '#fef2f2' : a.level === 'warning' ? '#fffbeb' : '#f8fafc';
      const border = a.level === 'error' ? '#fecaca' : a.level === 'warning' ? '#fde68a' : '#e2e8f0';
      return `<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 8px;margin-bottom:2px;background:${bg};border:1px solid ${border};border-radius:4px;font-size:10px">
        <span>[${a.machine}] ${a.msg}</span>
        <button onclick="this.parentElement.remove()" style="background:none;border:none;cursor:pointer;font-size:9px;color:var(--text2)">✕</button>
      </div>`;
    }).join('');
  } else {
    el.style.display = 'none';
  }
}

function renderTrackGrid(queueData) {
  const grid = document.getElementById('cmdTrackGrid');
  const machineFilter = document.getElementById('cmdMachineFilter');
  const machines = queueData?.machines || {};
  const filterValue = machineFilter?.value || 'all';

  // 更新机器筛选下拉
  machineFilter.innerHTML = '<option value="all">全部</option>';
  let totalUsed = 0, totalMax = 0, totalQueued = 0;

  let html = '';
  for (const [name, status] of Object.entries(machines)) {
    machineFilter.innerHTML += `<option value="${name}">${name}</option>`;
    if (filterValue !== 'all' && name !== filterValue) continue;

    const slots = status?.slots || {};
    const slotList = (Array.isArray(slots) ? slots : (slots.slots || slots.list || []));
    const used = slots?.used || 0;
    const max = slots?.max || 3;
    totalUsed += used; totalMax += max;

    // 机器头部（加底色区分不同机器）
    const isOnline = !status?.error;
    const counts = status?.counts || {};
    html += `<div style="grid-column:1/-1;font-size:11px;font-weight:600;padding:6px 8px;background:var(--bg3);border-radius:6px;margin:4px 0;display:flex;align-items:center;gap:6px">
      <span>${isOnline ? '🟢' : '🔴'} ${name}</span>
      <span style="font-size:10px;color:var(--text2);font-weight:400">${used}/${max} 槽位 · ${counts?.completed||0}完成/${counts?.failed||0}失败</span>
    </div>`;

    // 3 个 slot 卡片
    for (let i = 0; i < max; i++) {
      const slot = slotList.find(s => s.slot_id === i) || {};
      const acctId = slot.account_id || '';
      const info = _acctInfo(acctId);
      const phone = info.phone || acctId ? (slot.phone || '') : '';
      const nick = slot.nickname || info.nickname || acctId;
      const platIcon = (slot.platform || info.platform) === 'xiaohongshu' ? '📕' : '🎵';

      if (!acctId) {
        // 空闲槽位
        html += `<div style="background:var(--bg2);border-radius:8px;padding:8px;border:1px dashed var(--border);display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:80px;gap:4px">
          <div style="font-size:20px;opacity:0.2">○</div>
          <div style="font-size:9px;color:var(--text2)">${name} · Slot ${i+1}</div>
          <div style="font-size:8px;color:var(--text2)">空闲</div>
        </div>`;
        continue;
      }

      const h = slot.health || 'healthy';
      const healthIcon = h === 'healthy' ? '🟢' : h === 'warning' ? '🟡' : '🔴';
      const stepIdx = slot.step_index || 0;
      const totalSteps = slot.total_steps || 0;

      html += `<div style="background:var(--bg2);border-radius:8px;padding:8px;border:1px solid var(--border);position:relative">
        <!-- 运行中状态条 -->
        <div style="height:3px;background:${_slotStatusColor(slot)};border-radius:2px;margin-bottom:6px"></div>
        
        <!-- 账号信息 -->
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div style="font-weight:600;font-size:11px">${platIcon} ${slot.account_id || ''}</div>
          <div style="font-size:9px;color:var(--text2)">${healthIcon}</div>
        </div>
        ${phone ? `<div style="font-size:9px;color:var(--text2);margin-top:2px">📱 ${phone}</div>` : ''}
        <div style="font-size:9px;color:var(--text);margin-top:1px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${nick}</div>
        
        <!-- 任务信息 -->
        ${slot.blueprint ? `<div style="font-size:8px;color:var(--text2);margin-top:4px">📋 ${slot.blueprint}</div>` : ''}
        ${slot.current_step ? `<div style="font-size:8px;color:var(--text2)">🔧 ${slot.current_step}</div>` : ''}
        
        <!-- 进度 -->
        ${totalSteps > 0 ? `
        <div style="margin-top:4px">
          <div style="display:flex;justify-content:space-between;font-size:8px;color:var(--text2)">
            <span>步骤 ${stepIdx}/${totalSteps}</span>
            <span>${_progressPct(stepIdx, totalSteps)}</span>
          </div>
          <div style="height:4px;background:var(--bg3);border-radius:2px;margin-top:2px">
            <div style="height:100%;width:${Math.min(100, (stepIdx/totalSteps)*100)}%;background:#22c55e;border-radius:2px;transition:width 0.5s"></div>
          </div>
        </div>` : ''}
        
        <!-- 耗时 -->
        ${slot.elapsed_sec ? `<div style="font-size:8px;color:var(--text2);margin-top:3px">⏱ ${_timeStr(slot.elapsed_sec)}</div>` : ''}
      </div>`;
    }
  }

  grid.innerHTML = html ||
    '<div style="grid-column:1/-1;text-align:center;padding:20px;color:var(--text2);font-size:12px">无机器数据</div>';

  // 更新队列计数
  const qc = document.getElementById('cmdQueueCount');
  if (qc) {
    let total = 0;
    for (const [name, status] of Object.entries(machines)) {
      total += (status?.queue || []).length;
    }
    qc.textContent = `⏳ ${total} 排队 | ${totalUsed}/${totalMax} 槽位使用中`;
  }
}

function renderQueueDetail(queueData) {
  const detail = document.getElementById('cmdQueueDetail');
  const filterValue = document.getElementById('cmdMachineFilter')?.value || 'all';
  const machines = queueData?.machines || {};

  const showP0 = document.querySelector('.cmdFilter[value="P0"]')?.checked ?? true;
  const showP1 = document.querySelector('.cmdFilter[value="P1"]')?.checked ?? true;
  const showP2 = document.querySelector('.cmdFilter[value="P2"]')?.checked ?? false;

  let html = '';
  for (const [name, status] of Object.entries(machines)) {
    if (filterValue !== 'all' && name !== filterValue) continue;

    const queued = status?.queue || [];
    const counts = status?.counts || {};

    // 按优先级过滤
    const filtered = queued.filter(q => {
      const p = q.priority == null ? 1 : q.priority;
      if (p === 0 && !showP0) return false;
      if (p === 1 && !showP1) return false;
      if (p === 2 && !showP2) return false;
      return true;
    }).sort((a, b) => (a.priority||1) - (b.priority||1));

    if (filtered.length === 0 && filterValue === 'all') continue;

    html += `<div style="background:var(--bg2);border-radius:8px;padding:8px;border:1px solid var(--border);margin-bottom:6px">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <span style="font-weight:600;font-size:11px">${name}</span>
        <span style="font-size:9px;color:var(--text2)">排队: ${filtered.length} | 完成: ${counts.completed||0} | 失败: ${counts.failed||0}</span>
      </div>
      ${filtered.length > 0 ? filtered.slice(0,15).map((q, qi) => {
        const pri = q.priority === 0 ? '🔴' : q.priority === 1 ? '🟢' : '⚪';
        const label = q.priority === 0 ? 'P0' : q.priority === 1 ? 'P1' : 'P2';
        const tid = (q.task_id || '').slice(0, 36);
        const acct = q.accounts ? q.accounts.join(',') : '';
        return `<div style="font-size:9px;padding:2px 4px;background:var(--bg3);border-radius:3px;margin-bottom:2px;display:flex;justify-content:space-between;align-items:center">
          <span>${pri} [${label}] ${tid} ${acct}</span>
          <button onclick="window._cmdRemoveQueue('${name}',${qi})" style="background:none;border:none;cursor:pointer;font-size:9px;color:#ef4444;padding:0 2px" title="移出队列">✕</button>
        </div>`;
      }).join('') : filterValue === 'all' ? '' : '<div style="font-size:9px;color:var(--text2);padding:2px 0">队列为空</div>'}
    </div>`;
  }

  detail.innerHTML = html || '';
}

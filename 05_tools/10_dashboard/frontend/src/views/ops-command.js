/**
 * 联邦指挥台视图 (v4.3.0)
 * 显示三机实时状态 + 任务队列 + 浏览器槽位
 *
 * 修复记录:
 *   2026-06-28: 修复字段路径 status?.tasks?.active → status?.active (后端无 tasks 嵌套层)
 *   2026-06-28: 修复 status?.tasks?.queued → status?.queue (后端字段名为 queue)
 *   2026-06-28: P0/P1/P2 优先级 checkbox 绑定实际过滤逻辑
 */

import { apiRequest } from '../router.js';

let _pollTimer = null;

export async function loadView(container) {
  container.innerHTML = `
    <div style="padding:16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <div style="font-weight:700;font-size:16px">🚀 联邦指挥台</div>
        <div style="display:flex;gap:8px;align-items:center">
          <span id="cmdLastUpdate" style="font-size:10px;color:var(--text2)"></span>
          <button onclick="window._cmdRefresh()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔄 刷新</button>
          <button onclick="window._cmdReset()" style="background:#ef4444;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🗑 重置所有</button>
          <label style="font-size:10px;color:var(--text2)">
            <input type="checkbox" id="cmdAutoRefresh" checked onchange="window._cmdToggleAuto()"> 自动刷新(15s)
          </label>
        </div>
      </div>

      <!-- 账号健康度面板 -->
      <div id="cmdHealthPanel" style="background:var(--bg2);border-radius:8px;padding:8px;border:1px solid var(--border);margin-bottom:8px;display:none">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
          <div style="font-weight:600;font-size:12px">🩺 账号健康度</div>
          <button onclick="document.getElementById('cmdHealthPanel').style.display='none'" style="background:none;border:none;cursor:pointer;font-size:10px;color:var(--text2)">✕</button>
        </div>
        <div id="cmdHealthList" style="font-size:10px;max-height:120px;overflow-y:auto">加载中...</div>
      </div>

      <!-- 三机状态总览 -->
      <div id="cmdMachineOverview" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px">
        <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border);text-align:center">
          <div style="font-size:10px;color:var(--text2)">加载中...</div>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;align-items:center">
        <span style="font-size:11px;color:var(--text2);font-weight:600">筛选:</span>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P0" checked onchange="window._cmdRefresh()"> 🔴 优先任务</label>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P1" checked onchange="window._cmdRefresh()"> 🟢 日常任务</label>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P2" onchange="window._cmdRefresh()"> ⚪ 闲时任务</label>
        <span style="margin-left:12px;font-size:11px;color:var(--text2);font-weight:600">机器:</span>
        <select id="cmdMachineFilter" onchange="window._cmdRefresh()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 6px;border-radius:4px;font-size:10px">
          <option value="all">全部</option>
        </select>
      </div>

      <!-- 告警中心 -->
      <div id="cmdAlerts" style="display:none;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:8px;margin-bottom:8px;font-size:11px">
        <div style="font-weight:600;margin-bottom:4px">⚠️ 告警中心</div>
        <div id="cmdAlertsList"></div>
      </div>

      <!-- 各机详细队列 -->
      <div id="cmdQueueDetail"></div>
    </div>`;

  // 注册全局函数
  if (!window._cmdRegistered) {
    window._cmdRegistered = true;
    window._cmdRefresh = () => refreshView(container);
    window._cmdMoveUp = (machine, idx) => { /* TODO */ };
    window._cmdMoveDown = (machine, idx) => { /* TODO */ };
    window._cmdRemoveQueue = async (machine, idx) => {
      if (!confirm('确定从队列中移除此任务？')) return;
      alert('移出队列功能待实现');
    };
    window._cmdStop = async (machine, taskId) => {
      if (!confirm('确定停止任务 '+taskId+' ？')) return;
      try {
        const r = await apiRequest('/ops/task/cancel', {method:'POST', body:JSON.stringify({task_id:taskId, machine:machine})});
        alert('✅ 已发送停止指令');
        refreshView(container);
      } catch(e) { alert('❌ 停止失败: '+e.message); }
    };
    window._cmdReset = async () => {
      if (!confirm('确定重置所有机器？将清空任务队列、终止运行中的任务。')) return;
      try {
        const r = await apiRequest('/ops/reset', {method:'POST', body:'{}'});
        alert('✅ 已重置: ' + JSON.stringify(r.machines));
        refreshView(container);
      } catch(e) {
        alert('❌ 重置失败: ' + e.message);
      }
    };
    window._cmdToggleAuto = () => {
      if (document.getElementById('cmdAutoRefresh')?.checked) {
        startAutoRefresh(container);
      } else {
        stopAutoRefresh();
      }
    };
  }

  // 首轮加载
  await refreshView(container);
  startAutoRefresh(container);
}

export function unloadView() {
  stopAutoRefresh();
}

function startAutoRefresh(container) {
  stopAutoRefresh();
  _pollTimer = setInterval(() => {
    if (document.getElementById('cmdAutoRefresh')?.checked) {
      refreshView(container, true);
    }
  }, 15000);
}

function stopAutoRefresh() {
  if (_pollTimer) {
    clearInterval(_pollTimer);
    _pollTimer = null;
  }
}

async function refreshView(container, silent = false) {
  try {
    const [queueData, machineData, healthData] = await Promise.all([
      apiRequest('/ops/queue'),
      apiRequest('/ops/machines'),
      apiRequest('/matrix/accounts').catch(() => []),
    ]);
    renderHealth(healthData);

    if (!silent) {
      document.getElementById('cmdLastUpdate').textContent = `最后更新: ${new Date().toLocaleTimeString()}`;
    }

    renderAlerts(queueData);
    renderMachines(queueData, machineData);
    renderQueueDetail(queueData);
  } catch (e) {
    if (!silent) {
      document.getElementById('cmdQueueDetail').innerHTML = `<div style="color:#ef4444;font-size:12px">❌ 加载失败: ${e.message}</div>`;
    }
  }
}

function renderHealth(accounts) {
  const el = document.getElementById('cmdHealthPanel');
  const list = document.getElementById('cmdHealthList');
  if (!el || !list || !Array.isArray(accounts) || accounts.length === 0) return;
  const issues = accounts.filter(a => a.status === 'banned' || a.status === 'login_expired');
  if (issues.length === 0) { el.style.display = 'none'; return; }
  el.style.display = 'block';
  list.innerHTML = issues.map(a => '<div style="padding:2px 0;color:#ef4444">⚠️ ' + (a.platform||'?') + ' ' + (a.id||'?') + ' — ' + (a.status||'unknown') + '</div>').join('');
}

function renderMachines(queueData, machineData) {
  const overview = document.getElementById('cmdMachineOverview');
  const machineFilter = document.getElementById('cmdMachineFilter');
  const machines = queueData?.machines || {};
  const allMachineStatus = machineData?.machines || {};
  
  const currentFilter = machineFilter.value;
  machineFilter.innerHTML = '<option value="all">全部</option>';
  
  let html = '';
  let idx = 0;
  for (const [name, status] of Object.entries(machines)) {
    machineFilter.innerHTML += `<option value="${name}">${name}</option>`;
    
    const slots = status?.slots || {};
    const active = status?.active || null;
    const counts = status?.counts || {};
    const isOnline = !status?.error;
    const usedSlots = slots?.used || 0;
    const maxSlots = slots?.max || 3;
    const statusIcon = isOnline ? (usedSlots > 0 ? '🟢' : '🟢') : '🔴';
    
    html += `
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <div style="font-weight:600;font-size:12px">${statusIcon} ${name}</div>
          <div style="font-size:10px;color:var(--text2)">${usedSlots}/${maxSlots} 槽位</div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(${Math.min(maxSlots,3)},1fr);gap:4px;margin-bottom:4px">
          ${Array.from({length: maxSlots}, (_, i) => {
            const slot = slots?.slots?.find(s => s.slot_id === i);
            const active2 = slot && slot.account_id;
            if (!active2) {
              return `<div style="background:var(--bg3);border-radius:6px;padding:6px;border:1px solid var(--border);text-align:center;font-size:9px;color:var(--text2)">空闲</div>`;
            }
            const platformIcon = slot.platform === 'xiaohongshu' ? '📕' : '🎵';
            const nick = slot.nickname || slot.account_id;
            return `<div style="background:#22c55e20;border-radius:6px;padding:6px;border:1px solid #22c55e">
              <div style="font-size:9px;font-weight:600">${platformIcon} ${nick}</div>
              <div style="font-size:8px;color:var(--text2)">${slot.account_id}</div>
              ${slot.current_step ? `<div style="font-size:8px;color:var(--text2);margin-top:2px">🔧 ${slot.current_step}</div>` : ''}
              ${slot.elapsed_sec ? `<div style="font-size:8px;color:var(--text2)">⏱ ${Math.floor(slot.elapsed_sec/60)}分</div>` : ''}
              ${slot.blueprint ? `<div style="font-size:8px;color:var(--text2)">📋 ${slot.blueprint}</div>` : ''}
            </div>`;
          }).join('')}
        </div>
        ${active ? `
          <div style="font-size:10px;color:var(--text);background:var(--bg3);border-radius:4px;padding:4px 6px;margin-top:4px">
            <div><strong>${active.cmd_type || '?'}</strong> · ${active.account || ''}</div>
            <div style="color:var(--text2)">${active.blueprint || ''} · ${active.progress?.current_step || ''} (${active.progress?.step_index || 0}/${active.progress?.total_steps || '?'})</div>
          </div>
        ` : `
          <div style="font-size:10px;color:var(--text2);margin-top:4px">空闲</div>
        `}
        <div style="font-size:9px;color:var(--text2);margin-top:4px">
          ${counts?.running ? `▶️运行:${counts.running}` : ''}
          ${counts?.queued ? ` ⏳排队:${counts.queued}` : ''}
          ${counts?.completed ? ` ✅完成:${counts.completed}` : ''}
          ${counts?.failed ? ` ❌失败:${counts.failed}` : ''}
        </div>
      </div>`;
    idx++;
  }
  
  overview.innerHTML = html;
  if (currentFilter) machineFilter.value = currentFilter;
}

function renderAlerts(queueData) {
  const el = document.getElementById('cmdAlerts');
  const list = document.getElementById('cmdAlertsList');
  if (!el || !list) return;
  const alerts = [];
  const machines = queueData?.machines || {};
  for (const [name, status] of Object.entries(machines)) {
    const active = status?.active || null;
    const counts = status?.counts || {};
    if (status?.error) alerts.push({machine:name, type:'error', msg:'不可达: '+status.error});
    if (active?.status === 'failed') alerts.push({machine:name, type:'failed', msg:'任务失败: '+active.task_id});
    if (counts?.failed > 0) alerts.push({machine:name, type:'failed_count', msg:counts.failed+' 个任务失败'});
  }
  if (alerts.length > 0) {
    el.style.display = 'block';
    list.innerHTML = alerts.map(a => '<div style="padding:2px 0">⚠️ ['+a.machine+'] '+a.msg+'</div>').join('');
  } else {
    el.style.display = 'none';
  }
}

function renderQueueDetail(queueData) {
  const detail = document.getElementById('cmdQueueDetail');
  const filterValue = document.getElementById('cmdMachineFilter')?.value || 'all';
  const machines = queueData?.machines || {};
  
  // 读取优先级过滤器状态
  const showP0 = document.querySelector('.cmdFilter[value="P0"]')?.checked ?? true;
  const showP1 = document.querySelector('.cmdFilter[value="P1"]')?.checked ?? true;
  const showP2 = document.querySelector('.cmdFilter[value="P2"]')?.checked ?? false;
  
  let html = '';
  for (const [name, status] of Object.entries(machines)) {
    if (filterValue !== 'all' && name !== filterValue) continue;
    
    const active = status?.active || null;
    const queued = status?.queue || [];
    const counts = status?.counts || {};
    const slots = status?.slots?.slots || [];
    
    // 按优先级过滤队列（P0/P1/P2 checkbox）
    const filteredQueued = queued.filter(q => {
      if (q.priority === 0 && !showP0) return false;
      if (q.priority === 1 && !showP1) return false;
      if (q.priority === 2 && !showP2) return false;
      if (q.priority == null && !showP1) return false;
      return true;
    });
    
    html += `
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border);margin-bottom:8px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <div style="font-weight:600;font-size:13px">${name}</div>
          <div style="font-size:10px;color:var(--text2)">队列: ${filteredQueued.length} | 完成: ${counts.completed||0} | 失败: ${counts.failed||0}</div>
        </div>
        
        ${active ? `
          <div style="background:var(--bg3);border-radius:6px;padding:8px;margin-bottom:6px;border-left:3px solid #22c55e">
            <div style="display:flex;justify-content:space-between">
              <div><span style="font-size:10px;background:#ef4444;color:#fff;padding:1px 5px;border-radius:3px;margin-right:4px">P0</span><strong style="font-size:12px">${active.cmd_type || ''}</strong></div>
              <div style="font-size:10px;color:var(--text2)">⏱ ${active.elapsed_sec ? Math.floor(active.elapsed_sec/60)+'分' : '刚刚'}</div>
            </div>
            <div style="font-size:11px;margin-top:4px">账号: ${active.account || ''}</div>
            <div style="font-size:10px;color:var(--text2);margin-top:2px">蓝图: ${active.blueprint || ''}</div>
            <div style="font-size:10px;color:var(--text2);margin-top:2px">当前: ${active.progress?.current_step || ''} (${active.progress?.step_index || 0}/${active.progress?.total_steps || '?'})</div>
            <div style="font-size:10px;color:var(--text2);margin-top:2px">状态: ${active.status || ''}</div>
          </div>
        ` : `
          <div style="background:var(--bg3);border-radius:6px;padding:8px;margin-bottom:6px;color:var(--text2);font-size:11px">当前无活跃任务</div>
        `}
        
        ${slots.length > 0 ? `
          <div style="display:grid;grid-template-columns:repeat(${Math.min(slots.length,3)},1fr);gap:4px;margin-bottom:6px">
            ${slots.map(s => {
              if (!s.account_id) {
                return '<div style=\"background:var(--bg3);border-radius:4px;padding:6px;border:1px solid var(--border);font-size:9px;color:var(--text2)\"><div style=\"font-weight:600\">槽位'+(s.slot_id+1)+'</div><div>空闲</div></div>';
              }
              const pIcon = s.platform === 'xiaohongshu' ? '📕' : '🎵';
              const nick = s.nickname || s.account_id;
              return '<div style=\"background:#22c55e20;border-radius:4px;padding:6px;border:1px solid #22c55e;font-size:9px\">'+
                '<div style=\"font-weight:600\">槽位'+(s.slot_id+1)+'</div>'+
                '<div>'+pIcon+' '+nick+'</div>'+
                '<div style=\"color:var(--text2)\">'+s.account_id+'</div>'+
                (s.current_step ? '<div style=\"color:var(--text2);margin-top:2px\">🔧 '+s.current_step+'</div>' : '')+
                (s.blueprint ? '<div style=\"color:var(--text2)\">📋 '+s.blueprint+'</div>' : '')+
                (s.elapsed_sec ? '<div style=\"color:var(--text2)\">⏱ '+Math.floor(s.elapsed_sec/60)+'分</div>' : '')+
              '</div>';
            }).join('')}
          </div>
        ` : ''}
        
        ${filteredQueued.length > 0 ? `
          <div style="font-size:10px;color:var(--text2);margin-bottom:4px">⏳ 排队中 (${filteredQueued.length}) <span style="font-size:9px;color:var(--text2);margin-left:8px">(拖拽调整顺序功能开发中)</span></div>
          ${filteredQueued.slice(0,10).map((q, qi) => {
            const pri = q.priority === 0 ? '🔴' : q.priority === 1 ? '🟢' : '⚪';
            const label = q.priority === 0 ? 'P0优先' : q.priority === 1 ? 'P1日常' : 'P2闲时';
            return `<div style="font-size:10px;padding:2px 4px;background:var(--bg3);border-radius:3px;margin-bottom:2px;display:flex;justify-content:space-between">
              <span>${pri} [${label}] ${q.task_id?.slice(0,40) || ''}</span>
              <span>
                <button onclick="window._cmdMoveUp('${name}',${qi})" style="background:none;border:none;cursor:pointer;font-size:9px;color:var(--text2)">↑</button>
                <button onclick="window._cmdMoveDown('${name}',${qi})" style="background:none;border:none;cursor:pointer;font-size:9px;color:var(--text2)">↓</button>
                <button onclick="window._cmdRemoveQueue('${name}',${qi})" style="background:none;border:none;cursor:pointer;font-size:9px;color:#ef4444">✕</button>
              </span>
            </div>`;
          }).join('')}
        ` : '<div style="font-size:10px;color:var(--text2)">队列为空</div>'}
      </div>`;
  }
  
  detail.innerHTML = html || '<div style="color:var(--text2);font-size:12px;text-align:center;padding:20px">没有机器数据</div>';
}

/**
 * 联邦指挥台视图 (v4.3.0)
 * 显示三机实时状态 + 任务队列 + 浏览器槽位
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

      <!-- 三机状态总览 -->
      <div id="cmdMachineOverview" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px">
        <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border);text-align:center">
          <div style="font-size:10px;color:var(--text2)">加载中...</div>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;align-items:center">
        <span style="font-size:11px;color:var(--text2);font-weight:600">筛选:</span>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P0" checked> 🔴 优先任务</label>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P1" checked> 🟢 日常任务</label>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P2"> ⚪ 闲时任务</label>
        <span style="margin-left:12px;font-size:11px;color:var(--text2);font-weight:600">机器:</span>
        <select id="cmdMachineFilter" onchange="window._cmdRefresh()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 6px;border-radius:4px;font-size:10px">
          <option value="all">全部</option>
        </select>
      </div>

      <!-- 各机详细队列 -->
      <div id="cmdQueueDetail"></div>
    </div>`;

  // 注册全局函数
  if (!window._cmdRegistered) {
    window._cmdRegistered = true;
    window._cmdRefresh = () => refreshView(container);
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
    // 并行获取所有数据
    const [queueData, machineData] = await Promise.all([
      apiRequest('/ops/queue'),
      apiRequest('/ops/machines'),
    ]);

    if (!silent) {
      document.getElementById('cmdLastUpdate').textContent = `最后更新: ${new Date().toLocaleTimeString()}`;
    }

    renderMachines(queueData, machineData);
    renderQueueDetail(queueData);
  } catch (e) {
    if (!silent) {
      document.getElementById('cmdQueueDetail').innerHTML = `<div style="color:#ef4444;font-size:12px">❌ 加载失败: ${e.message}</div>`;
    }
  }
}

function renderMachines(queueData, machineData) {
  const overview = document.getElementById('cmdMachineOverview');
  const machineFilter = document.getElementById('cmdMachineFilter');
  const machines = queueData?.machines || {};
  const allMachineStatus = machineData?.machines || {};
  
  // 更新机器筛选下拉
  const currentFilter = machineFilter.value;
  machineFilter.innerHTML = '<option value="all">全部</option>';
  
  let html = '';
  let idx = 0;
  for (const [name, status] of Object.entries(machines)) {
    machineFilter.innerHTML += `<option value="${name}">${name}</option>`;
    
    const slots = status?.slots || {};
    const active = status?.tasks?.active || null;
    const counts = status?.tasks?.counts || {};
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
        <div style="display:flex;gap:4px;margin-bottom:4px">
          ${Array.from({length: maxSlots}, (_, i) => {
            const slot = slots?.slots?.find(s => s.slot_id === i);
            const active2 = slot && slot.account_id;
            return `<div style="width:28px;height:28px;border-radius:6px;background:${active2 ? '#22c55e' : 'var(--bg3)'};border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:8px;color:${active2 ? '#000' : 'var(--text2)'}">${active2 ? slot.account_id.slice(-3) : '∅'}</div>`;
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

function renderQueueDetail(queueData) {
  const detail = document.getElementById('cmdQueueDetail');
  const filterValue = document.getElementById('cmdMachineFilter')?.value || 'all';
  const machines = queueData?.machines || {};
  
  let html = '';
  for (const [name, status] of Object.entries(machines)) {
    if (filterValue !== 'all' && name !== filterValue) continue;
    
    const active = status?.tasks?.active || null;
    const queued = status?.tasks?.queued || [];
    const counts = status?.tasks?.counts || {};
    const slots = status?.slots?.slots || [];
    
    html += `
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border);margin-bottom:8px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <div style="font-weight:600;font-size:13px">${name}</div>
          <div style="font-size:10px;color:var(--text2)">队列: ${queued.length} | 完成: ${counts.completed||0} | 失败: ${counts.failed||0}</div>
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
            ${slots.map(s => `
              <div style="background:${s.account_id ? '#22c55e20' : 'var(--bg3)'};border-radius:4px;padding:6px;border:1px solid var(--border);font-size:9px">
                <div style="font-weight:600">槽位${s.slot_id+1}</div>
                <div>${s.account_id || '空闲'}</div>
                ${s.current_step ? `<div style="color:var(--text2)">${s.current_step}</div>` : ''}
                ${s.elapsed_sec ? `<div style="color:var(--text2)">${Math.floor(s.elapsed_sec/60)}分</div>` : ''}
              </div>
            `).join('')}
          </div>
        ` : ''}
        
        ${queued.length > 0 ? `
          <div style="font-size:10px;color:var(--text2);margin-bottom:4px">⏳ 排队中 (${queued.length})</div>
          ${queued.slice(0,10).map(q => {
            const pri = q.priority === 0 ? '🔴' : q.priority === 1 ? '🟢' : '⚪';
            const label = q.priority === 0 ? 'P0优先' : q.priority === 1 ? 'P1日常' : 'P2闲时';
            return `<div style="font-size:10px;padding:2px 4px;background:var(--bg3);border-radius:3px;margin-bottom:2px">${pri} [${label}] ${q.task_id?.slice(0,40) || ''}</div>`;
          }).join('')}
        ` : '<div style="font-size:10px;color:var(--text2)">队列为空</div>'}
      </div>`;
  }
  
  detail.innerHTML = html || '<div style="color:var(--text2);font-size:12px;text-align:center;padding:20px">没有机器数据</div>';
}

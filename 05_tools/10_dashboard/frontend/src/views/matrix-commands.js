/**
 * 命令与任务视图（v2 — 按机器分Tab，含取消/清理/查看日志）
 *
 * 调用规范：
 *   所有操作通过 POST /api/ops/run 统一入口
 *   状态通过 GET /api/ops/status 轮询
 *   取消通过 POST /api/ops/cancel/{run_id}
 *   日志通过 GET /api/ops/log/{run_id}
 *   僵尸清理通过 POST /api/ops/cleanup-stale
 */

import { apiRequest } from '../router.js';

let _pollTimer = null;
const STATUS_ICONS = {
  'completed': '✅', 'failed': '❌', 'crashed': '💥', 'cancelled': '⏸️',
  'timed_out': '⏰', 'running': '🟢', 'dispatching': '📡', 'queued': '⏳',
  'preflighting': '🔍', 'preflight_failed': '🔍❌',
};

export async function loadView(container) {
  const uid = 'cmd_' + Math.random().toString(36).slice(2, 6);
  container.innerHTML = `
    <div style="padding:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <h2 style="font-size:18px;margin:0">🎯 命令与任务</h2>
        <div style="display:flex;gap:6px">
          <span id="statusSummary_${uid}" style="font-size:11px;color:var(--text2);display:flex;align-items:center;gap:6px"></span>
          <button onclick="window._cleanupStale_${uid}()" style="background:rgba(220,38,38,.1);color:var(--red);border:1px solid rgba(220,38,38,.3);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🧹 清理僵尸</button>
          <button onclick="window._refreshCmds_${uid}()" style="background:var(--bg3);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">⟳ 刷新</button>
        </div>
      </div>

      <!-- 机器 Tab -->
      <div id="machineTabs_${uid}" style="display:flex;gap:4px;margin-bottom:8px;flex-wrap:wrap;border-bottom:1px solid var(--border);padding-bottom:6px"></div>

      <!-- 命令列表 -->
      <div id="cmdList_${uid}" style="font-size:11px"></div>
    </div>`;

  await renderAll(uid);
  startPoll(uid);
}

async function renderAll(uid) {
  try {
    const data = await apiRequest('/ops/status');
    const allCmds = data.commands || (Array.isArray(data) ? data : []);

    // 按机器分组
    const byMachine = { '_all': allCmds };
    allCmds.forEach(c => {
      const m = c.machine || 'unknown';
      if (!byMachine[m]) byMachine[m] = [];
      byMachine[m].push(c);
    });

    const machineOrder = ['chengzigedeAir', '5kechengdeAir', '7kecheng', 'unknown'];
    const machines = machineOrder.filter(m => byMachine[m]);

    // 渲染 Tab
    renderTabs(uid, machines, byMachine);

    // 渲染汇总
    renderSummary(uid, allCmds);

    // 默认选中第一个 Tab
    const activeTab = document.querySelector(`[data-cmdtab="_all_${uid}"]`) || document.querySelector(`[data-cmdtab^="_"][data-cmdtab$="_${uid}"]`);
    if (activeTab) activeTab.click();
  } catch (e) {
    document.getElementById(`cmdList_${uid}`).innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}

function renderTabs(uid, machines, byMachine) {
  const tabContainer = document.getElementById(`machineTabs_${uid}`);
  const allCount = byMachine['_all']?.length || 0;
  let html = `<button data-cmdtab="_all_${uid}" onclick="window._switchCmdTab_${uid}('_all')" style="background:var(--primary);color:#fff;border:none;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600">📋 全部 (${allCount})</button>`;

  machines.filter(m => m !== '_all').forEach(m => {
    const cmds = byMachine[m] || [];
    const active = cmds.filter(c => c.status === 'running' || c.status === 'dispatching' || c.status === 'queued').length;
    const icon = m === 'chengzigedeAir' ? '🖥️' : '☁️';
    const badge = active > 0 ? ` <span style="color:var(--green)">●${active}</span>` : '';
    html += `<button data-cmdtab="${m}_${uid}" onclick="window._switchCmdTab_${uid}('${m}')" style="background:var(--bg3);border:1px solid var(--border);padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px">${icon} ${m}${badge}</button>`;
  });
  tabContainer.innerHTML = html;

  // 注册 Tab 切换函数
  window[`_switchCmdTab_${uid}`] = function(machine) {
    // 高亮 Tab
    tabContainer.querySelectorAll('button').forEach(b => {
      if (b.dataset.cmdtab === `${machine}_${uid}` || (machine === '_all' && b.dataset.cmdtab === `_all_${uid}`)) {
        b.style.background = 'var(--primary)';
        b.style.color = '#fff';
        b.style.fontWeight = '600';
      } else {
        b.style.background = 'var(--bg3)';
        b.style.color = 'var(--text)';
        b.style.fontWeight = '400';
      }
    });
    renderCmdList(uid, byMachine[machine] || byMachine['_all'] || []);
  };
}

function renderCmdList(uid, cmds) {
  const listEl = document.getElementById(`cmdList_${uid}`);
  if (!cmds.length) {
    listEl.innerHTML = '<div style="color:var(--text2);padding:12px;font-size:12px">暂无命令记录</div>';
    return;
  }

  let html = `<table style="width:100%;border-collapse:collapse;font-size:10px">
    <tr style="border-bottom:1px solid var(--border);color:var(--text2);font-size:9px">
      <th style="padding:3px 4px;font-weight:400;text-align:left;width:28px">状态</th>
      <th style="padding:3px 4px;font-weight:400;text-align:left;width:40px">类型</th>
      <th style="padding:3px 4px;font-weight:400;text-align:left;width:50px">机器</th>
      <th style="padding:3px 4px;font-weight:400;text-align:left;width:80px">账号</th>
      <th style="padding:3px 4px;font-weight:400;text-align:left">消息</th>
      <th style="padding:3px 4px;font-weight:400;text-align:right;width:40px">耗时</th>
      <th style="padding:3px 4px;font-weight:400;text-align:center;width:110px">操作</th>
    </tr>`;

  cmds.slice(0, 100).forEach(c => {
    const icon = STATUS_ICONS[c.status] || '❓';
    const accts = (c.accounts || [c.account || '']).filter(Boolean).join(',');
    const isActive = c.status === 'running' || c.status === 'dispatching';
    const isQueued = c.status === 'queued';
    const canCancel = isActive || isQueued;
    const bg = isActive ? 'background:rgba(34,197,94,.05)' : isQueued ? 'background:rgba(250,204,21,.05)' : '';

    html += `<tr style="border-bottom:1px solid var(--border);${bg}">
      <td style="padding:3px 4px;font-size:11px" title="${c.status}">${icon}</td>
      <td style="padding:3px 4px">${c.type || c.cmd_type || '?'}</td>
      <td style="padding:3px 4px;font-size:9px;color:var(--text2)">${c.machine || '?'}</td>
      <td style="padding:3px 4px;max-width:80px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${accts}">${accts.slice(0,20)}</td>
      <td style="padding:3px 4px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text2)" title="${c.message || ''}">${c.message || c.status || ''}</td>
      <td style="padding:3px 4px;text-align:right;font-size:9px;color:var(--text2)">${fmtTime(c.elapsed_sec)}</td>
      <td style="padding:3px 4px;text-align:center;white-space:nowrap">
        ${canCancel ? `<button onclick="window._cancelCmd('${c.run_id}')" style="background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.3);padding:1px 6px;border-radius:3px;cursor:pointer;font-size:9px;color:var(--red)">⏹取消</button>` : ''}
        <button onclick="window._viewLog('${c.run_id}')" style="background:var(--bg3);border:1px solid var(--border);padding:1px 6px;border-radius:3px;cursor:pointer;font-size:9px;color:var(--text)">📋日志</button>
      </td>
    </tr>`;
  });
  html += '</table>';
  listEl.innerHTML = html;
}

function renderSummary(uid, cmds) {
  const el = document.getElementById(`statusSummary_${uid}`);
  const running = cmds.filter(c => c.status === 'running' || c.status === 'dispatching').length;
  const queued = cmds.filter(c => c.status === 'queued').length;
  const done = cmds.filter(c => c.status === 'completed').length;
  const failed = cmds.filter(c => ['failed','crashed','timed_out'].includes(c.status)).length;
  let html = '';
  if (running) html += `<span style="color:var(--green)">🟢 ${running}运行</span>`;
  if (queued) html += `<span style="color:#f59e0b">⏳ ${queued}排队</span>`;
  html += `<span style="color:var(--text2)">✅ ${done}完成</span>`;
  if (failed) html += `<span style="color:var(--red)">❌ ${failed}失败</span>`;
  el.innerHTML = html || '<span style="color:var(--text2)">⏸️ 空闲</span>';
}

function fmtTime(sec) {
  if (sec == null || sec === 0) return '-';
  if (sec < 60) return Math.round(sec) + 's';
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return m + 'm' + (s > 0 ? s + 's' : '');
}

function startPoll(uid) {
  if (_pollTimer) clearInterval(_pollTimer);
  _pollTimer = setInterval(() => {
    renderAll(uid).catch(() => {});
  }, 5000);

  // 注册全局 cancel/log 函数
  window._cancelCmd = async function(runId) {
    if (!confirm(`取消命令 ${runId.slice(0,20)}...?`)) return;
    try {
      const r = await apiRequest(`/ops/cancel/${runId}`, { method: 'POST' });
      if (r.ok || r.status === 'ok') {
        renderAll(uid);
      }
    } catch(e) {
      alert('❌ ' + e.message);
    }
  };

  window._viewLog = async function(runId) {
    try {
      const r = await apiRequest(`/ops/log/${runId}`);
      const log = r.log || '（日志为空）';
      const logWin = window.open('', '_blank', 'width=800,height=600');
      logWin.document.write(`<pre style="font-size:11px;padding:12px;background:#1a1a2e;color:#e0e0e0;white-space:pre-wrap;word-break:break-all">${escapeHtml(log)}</pre>`);
      logWin.document.close();
    } catch(e) {
      alert('❌ ' + e.message);
    }
  };

  window[`_cleanupStale_${uid}`] = async function() {
    if (!confirm('清理所有僵尸命令吗？（进程已死但状态为 running 的命令）')) return;
    try {
      const r = await apiRequest('/ops/cleanup-stale', { method: 'POST' });
      alert(`🧹 已清理 ${r.cleaned} 个僵尸命令`);
      renderAll(uid);
    } catch(e) {
      alert('❌ ' + e.message);
    }
  };

  window[`_refreshCmds_${uid}`] = function() {
    renderAll(uid);
  };
}

function escapeHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

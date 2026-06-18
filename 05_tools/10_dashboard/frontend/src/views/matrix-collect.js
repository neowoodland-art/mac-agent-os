/**
 * 信息采集视图（已迁移）
 * 使用共享账号选择器 + 登录/采集一体化
 */

import { apiRequest } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

let _selector = null;

export async function loadView(container) {
  const uid = container.id || 'collect';
  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">📡 登录与信息采集 <span style="font-size:10px;color:var(--text2);font-weight:400">登录+采集一体化</span></div>
        <div id="acctList_${uid}" style="margin-bottom:6px"><div class="loading">⏳ 加载账号列表...</div></div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
          <span id="status_${uid}" style="font-size:10px;color:var(--text2)">⏸️ 空闲</span>
          <button onclick="window._collectLogin()" style="background:#6366f1;color:#fff;border:none;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600">🔑 登录选中</button>
          <button onclick="window._collectExec()" style="background:var(--primary);color:#fff;border:none;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600">📥 采集选中</button>
          <button onclick="window._collectAll()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">📋 采集全部</button>
          <button onclick="window._cancelCollect()" style="background:rgba(220,38,38,.1);color:var(--red);border:1px solid rgba(220,38,38,.3);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">⏹ 停止</button>
          <span id="selCount_${uid}" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>
        <div id="log_${uid}" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:250px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;

  await loadAccounts(uid);
  registerGlobals(uid);

  // 获取采集状态
  try {
    const sr = await apiRequest('/matrix/collect-homepage/status');
    if (sr.running) document.getElementById(`status_${uid}`).innerHTML = '<span style="color:var(--green)">🟢 采集中</span>';
  } catch(e) {}
}

async function loadAccounts(uid) {
  const listEl = document.getElementById(`acctList_${uid}`);
  if (!listEl) return;
  try {
    const [ar, hr] = await Promise.all([
      apiRequest('/matrix/accounts'),
      apiRequest('/matrix/homepage-info').catch(() => ({ results: [] })),
    ]);
    const allAccts = Array.isArray(ar) ? ar.filter(a => a.enabled !== false) : (ar.accounts || []).filter(a => a.enabled !== false);
    const hpIndex = {};
    (hr.results || []).forEach(r => {
      if (r.identity_dir) hpIndex[r.identity_dir] = r;
      if (r.phone) hpIndex[r.phone] = r;
    });

    _selector = createAccountSelector(listEl, {
      accounts: allAccts,
      hpIndex,
      checkAll: false,
      height: '300px',
      showBlueprint: false,
    });
  } catch (e) {
    listEl.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}

function registerGlobals(uid) {
  if (window._collectGlobals) return;
  window._collectGlobals = true;

  window._collectLogin = async function () {
    const selected = _selector?.getSelected() || [];
    if (!selected.length) { alert('请先选择要登录的账号'); return; }
    const logEl = document.getElementById(`log_${uid}`);
    if (logEl) logEl.textContent = '🔑 登录 ' + selected.length + ' 个账号...\n';
    for (const s of selected) {
      try {
        const r = await apiRequest('/ops/run', {
          method: 'POST', body: JSON.stringify({ type: 'login', accounts: [s.id] }),
        });
        if (logEl) logEl.textContent += s.id + ': ' + (r.status || 'OK') + '\n';
      } catch (e) { if (logEl) logEl.textContent += s.id + ': ❌ ' + e.message + '\n'; }
    }
  };

  window._collectExec = async function () {
    const selected = _selector?.getSelected() || [];
    if (!selected.length) { alert('请先选择要采集的账号'); return; }
    const logEl = document.getElementById(`log_${uid}`);
    const statusEl = document.getElementById(`status_${uid}`);
    if (logEl) logEl.textContent = '📥 采集 ' + selected.length + ' 个账号...\n';
    for (const s of selected) {
      try {
        const d = await apiRequest('/matrix/collect-homepage', {
          method: 'POST', body: JSON.stringify({ account_id: s.id }),
        });
        if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">🟢 采集中</span>';
        if (logEl) logEl.textContent += s.id + ': ' + (d.status || 'OK') + ' 机器:' + (d.machine || s.machine) + '\n';
      } catch (e) { if (logEl) logEl.textContent += s.id + ': ❌ ' + e.message + '\n'; }
    }
  };

  window._collectAll = async function () {
    const selected = _selector?.getSelected() || [];
    if (!selected.length) { alert('没有可采集的账号'); return; }
    if (!confirm('采集全部 ' + selected.length + ' 个账号？')) return;
    await window._collectExec();
  };

  window._cancelCollect = async function () {
    const logEl = document.getElementById(`log_${uid}`);
    if (logEl) logEl.textContent += '⏹ 发送停止请求...\n';
    try {
      await apiRequest('/matrix/collect-homepage/cancel', { method: 'POST' });
      if (logEl) logEl.textContent += '✅ 已发送停止命令\n';
    } catch (e) { if (logEl) logEl.textContent += '❌ ' + e.message + '\n'; }
  };
}

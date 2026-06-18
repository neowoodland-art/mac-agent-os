/**
 * 联邦指挥台视图（已迁移）
 * 使用共享账号选择器 + 统一 ops/run API
 */

import { apiRequest } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

let _selector = null;

export async function loadView(container) {
  const uid = container.id || 'ops';
  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border);margin-bottom:8px">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">🖥️ 联邦指挥台 <span style="font-size:10px;color:var(--text2);font-weight:400">选机器 → 选操作 → 选账号 → 批量执行</span></div>
        <div id="acctList_${uid}" style="margin-bottom:6px"><div class="loading">⏳ 加载账号列表...</div></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:11px;color:var(--text2)">操作:
            <select id="opsType_${uid}" onchange="window._opsTypeChange()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
              <option value="nurture">🏃 养号</option>
              <option value="collect">📡 采集</option>
              <option value="login">🔑 登录</option>
              <option value="logout">🔒 登出</option>
            </select>
          </label>
          <label style="font-size:11px;color:var(--text2)" id="roundsLabel_${uid}">轮数:
            <select id="rounds_${uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
              <option value="1">1</option><option value="5">5</option>
              <option value="10" selected>10</option><option value="20">20</option>
            </select>
          </label>
          <button onclick="window._opsExec()" style="background:#22c55e;color:#000;border:none;padding:5px 16px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 批量执行</button>
          <span id="selCount_${uid}" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>
        <div id="log_${uid}" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:300px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;

  // 加载账号
  try {
    const r = await apiRequest('/matrix/accounts');
    const accts = Array.isArray(r) ? r : (r.accounts || []);
    const listEl = document.getElementById(`acctList_${uid}`);
    if (listEl) {
      _selector = createAccountSelector(listEl, {
        accounts: accts,
        checkAll: true,
        height: '300px',
      });
    }
  } catch(e) {
    const listEl = document.getElementById(`acctList_${uid}`);
    if (listEl) listEl.innerHTML = `<div class="error">❌ ${e.message}</div>`;
  }

  registerGlobals(uid);
}

function registerGlobals(uid) {
  if (window._opsGlobals) return;
  window._opsGlobals = true;

  window._opsTypeChange = function () {
    const type = document.getElementById(`opsType_${uid}`)?.value;
    const label = document.getElementById(`roundsLabel_${uid}`);
    if (label) label.style.display = type === 'nurture' ? '' : 'none';
  };

  window._opsExec = async function () {
    const selected = _selector?.getSelected() || [];
    if (!selected.length) { alert('请先选择账号'); return; }
    const type = document.getElementById(`opsType_${uid}`)?.value || 'nurture';
    const rounds = parseInt(document.getElementById(`rounds_${uid}`)?.value || '10');
    const logEl = document.getElementById(`log_${uid}`);
    logEl.textContent = '🚀 提交 ' + type + ' 任务: ' + selected.length + ' 个账号...\n';
    try {
      const params = type === 'nurture' ? { rounds } : {};
      const d = await apiRequest('/ops/run', {
        method: 'POST', body: JSON.stringify({ type, accounts: selected, params }),
      });
      const results = d.results || [];
      logEl.textContent += '📋 结果 (' + results.length + ' 个):\n';
      results.forEach(r => {
        logEl.textContent += `  ${r.status === 'started' || r.status === 'ok' ? '✅' : '❌'} ${r.account_id || r.target}: ${r.status}\n`;
      });
    } catch (e) { logEl.textContent += '❌ ' + e.message + '\n'; }
  };
}

/**
 * 养号执行视图（已迁移）
 * 
 * 使用共享账号选择器 + 统一 ops/run API
 */

import { showLoading, showError, apiRequest } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

let _pollTimer = null;
let _selector = null;

export async function loadView(container) {
  const uid = container.id || 'nurture';
  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">
          🌱 养号执行 <span style="font-size:10px;color:var(--text2);font-weight:400">预检 → 窗口定位 → 执行 → 验证</span>
        </div>

        <div id="acctList_${uid}" style="margin-bottom:6px">
          <div class="loading" style="padding:8px;font-size:12px">⏳ 加载账号列表...</div>
        </div>

        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:11px;color:var(--text2)">轮数:
            <select id="ndRounds_${uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="1">1 测试</option>
              <option value="5">5</option>
              <option value="10" selected>10 默认</option>
              <option value="20">20</option>
              <option value="30">30</option>
            </select>
          </label>
          <label style="font-size:11px;color:var(--text2)">蓝图:
            <select id="ndBlueprint_${uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="">自动匹配</option>
              <option value="douyin_daily">🎵 douyin_daily</option>
              <option value="xhs_daily">📕 xhs_daily</option>
              <option value="douyin_active_v1">🎵 douyin_active_v1</option>
              <option value="xhs_active_v1">📕 xhs_active_v1</option>
            </select>
          </label>
          <button onclick="window._nurturePreflight('${uid}')" 
            style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔍 预检</button>
          <button onclick="window._nurtureExec('${uid}')" 
            style="background:#22c55e;color:#000;border:none;padding:4px 14px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 执行选中</button>
          <button onclick="window._nurtureAll('${uid}')" 
            style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">📋 全部启用</button>
          <span id="selCount_${uid}" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>

        <div id="nurtureStatus_${uid}" style="font-size:11px;color:var(--text2);margin-top:4px"></div>
        <div id="nurturePreflight_${uid}" style="font-size:10px;color:var(--text2);margin-top:2px;font-family:monospace;white-space:pre-wrap"></div>
        <div id="nurtureLog_${uid}" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:300px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;

  // 加载账号并创建共享选择器
  await loadAndSetup(uid);
  registerGlobals(uid);
}

async function loadAndSetup(uid) {
  const listEl = document.getElementById(`acctList_${uid}`);
  if (!listEl) return;

  try {
    const [acctsRes, hpRes] = await Promise.all([
      apiRequest('/matrix/accounts'),
      apiRequest('/matrix/homepage-info').catch(() => ({ results: [], collected_at: '' })),
    ]);

    const allAccts = Array.isArray(acctsRes) ? acctsRes.filter(a => a.enabled !== false) : [];
    const hpIndex = {};
    (hpRes.results || []).forEach(r => {
      if (r.identity_dir) hpIndex[r.identity_dir] = r;
      if (r.phone) hpIndex[r.phone] = r;
    });

    _selector = createAccountSelector(listEl, {
      accounts: allAccts,
      hpIndex,
      checkAll: true,
      height: '350px',
    });
  } catch (e) {
    listEl.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}

// ── 操作函数（挂到 window 供 onclick）──

function registerGlobals(uid) {
  if (window._nurtureGlobals) return;
  window._nurtureGlobals = true;

  window._nurturePreflight = async function () {
    const statusEl = document.getElementById(`nurtureStatus_${uid}`);
    const preflightEl = document.getElementById(`nurturePreflight_${uid}`);
    if (!statusEl) return;
    statusEl.innerHTML = '<span style="color:var(--amber)">🟡 预检中...</span>';
    preflightEl.textContent = '';
    try {
      const d = await apiRequest('/matrix/nurture/status');
      const running = d.running || [];
      const text = running.length
        ? `⚠️ ${running.length} 个任务运行中:\n` + running.map(r => `  ${r.account_id || r.id}: ${r.elapsed_sec || '?'}s`).join('\n')
        : '✅ 预检通过，可以执行';
      preflightEl.textContent = text;
      statusEl.innerHTML = running.length
        ? '<span style="color:var(--green)">🟢 发现运行中任务</span>'
        : '<span style="color:var(--green)">🟢 就绪</span>';
    } catch (e) {
      statusEl.innerHTML = `<span style="color:var(--red)">🔴 预检失败: ${e.message}</span>`;
    }
  };

  window._nurtureExec = async function () {
    const selected = _selector?.getSelected() || [];
    if (!selected.length) { alert('请先选择要执行的账号'); return; }
    const rounds = parseInt(document.getElementById(`ndRounds_${uid}`)?.value || '10');
    const blueprint = document.getElementById(`ndBlueprint_${uid}`)?.value || '';
    const statusEl = document.getElementById(`nurtureStatus_${uid}`);
    const logEl = document.getElementById(`nurtureLog_${uid}`);
    statusEl.innerHTML = '<span style="color:var(--amber)">🟡 提交任务...</span>';
    if (logEl) logEl.textContent = `🚀 提交 ${selected.length} 个账号, ${rounds} 轮...\n`;
    try {
      const d = await apiRequest('/ops/run', {
        method: 'POST',
        body: JSON.stringify({ type: 'nurture', accounts: selected, params: { rounds, blueprint: blueprint || undefined } }),
      });
      const results = d.results || [];
      if (logEl) {
        logEl.textContent = results.map(r =>
          `  ${r.status === 'started' || r.status === 'ok' ? '✅' : '❌'} ${r.account_id || r.target}: ${r.status}`
        ).join('\n');
      }
      statusEl.innerHTML = `<span style="color:var(--green)">🟢 已提交 ${results.filter(r => r.status === 'started' || r.status === 'ok').length} 个</span>`;
      startPolling(uid);
    } catch (e) {
      statusEl.innerHTML = `<span style="color:var(--red)">🔴 提交失败: ${e.message}</span>`;
      if (logEl) logEl.textContent += `❌ ${e.message}\n`;
    }
  };

  window._nurtureAll = async function () {
    _selector?.selectAll(true);
    await window._nurtureExec();
  };
}

function startPolling(uid) {
  stopPolling();
  const logEl = document.getElementById(`nurtureLog_${uid}`);
  const statusEl = document.getElementById(`nurtureStatus_${uid}`);
  _pollTimer = setInterval(async () => {
    try {
      const d = await apiRequest('/matrix/nurture/status');
      const running = d.running || [];
      if (!running.length) {
        statusEl.innerHTML = '<span style="color:var(--green)">🟢 全部完成</span>';
        if (logEl) logEl.textContent += '\n✅ 养号执行全部完成';
        stopPolling();
        return;
      }
      statusEl.innerHTML = `<span style="color:var(--amber)">🟡 ${running.length} 个任务运行中...</span>`;
      if (logEl) logEl.textContent = running.map(r => `  ${r.account_id || r.id}: ${r.status || '运行中'} (${r.elapsed_sec || '?'}s)`).join('\n');
    } catch (e) { /* ignore polling errors */ }
  }, 3000);
}

function stopPolling() {
  if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
}

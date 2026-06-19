/**
 * 收藏点赞视图（已迁移）
 * 使用共享账号选择器
 */

import { apiRequest, confirmExecute } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

let _selector = null;

export async function loadView(container) {
  const uid = container.id || 'like';
  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">❤️ 收藏点赞 <span style="font-size:10px;color:var(--text2);font-weight:400">选择账号 → 填入视频链接 → 执行点赞</span></div>
        <div id="acctList_${uid}" style="margin-bottom:6px"><div class="loading">⏳ 加载账号列表...</div></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
          <textarea id="urls_${uid}" placeholder="视频链接（每行一个，支持多个）" rows="3" style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
          <button onclick="window._runLike()" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:4px;cursor:pointer;font-size:12px;align-self:flex-start">❤️ 执行点赞</button>
        </div>
        <div id="result_${uid}" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;

  try {
    const r = await apiRequest('/matrix/accounts');
    const accts = Array.isArray(r) ? r : (r.accounts || []);
    const listEl = document.getElementById(`acctList_${uid}`);
    if (listEl) {
      _selector = createAccountSelector(listEl, {
        accounts: accts,
        checkAll: false,
        compact: true,
        height: '200px',
        showBlueprint: false,
        showStatus: false,
        showCollectTime: false,
      });
    }
  } catch(e) { /* ignore */ }

  registerGlobals(uid);
}

function registerGlobals(uid) {
  if (window._likeGlobals) return;
  window._likeGlobals = true;

  window._runLike = async function () {
    const selected = _selector?.getSelected() || [];
    const urlsText = document.getElementById(`urls_${uid}`)?.value;
    const el = document.getElementById(`result_${uid}`);
    if (!urlsText || !urlsText.trim()) { el.textContent = '请填写视频链接'; return; }
    const urls = urlsText.split('\n').map(u => u.trim()).filter(u => u);
    if (!selected.length) { el.textContent = '请先选择要执行的账号'; return; }

    // 执行前确认
    const detail = `账号: ${selected.map(s=>s.id).join(', ')}\n视频: ${urls.join('\n')}`;
    const confirmed = await confirmExecute(`即将用 ${selected.length} 个账号点赞 ${urls.length} 个视频`, detail);
    if (!confirmed) { el.textContent = '已取消'; return; }

    el.textContent = '⏳ 使用 ' + selected.length + ' 个账号点赞 ' + urls.length + ' 个视频...\n';
    const results = [];
    for (const url of urls) {
      for (const s of selected) {
        try {
          const d = await apiRequest('/matrix/task/run', {
            method: 'POST', body: JSON.stringify({ type: 'like', url, account: s.id }),
          });
          results.push({ url, account: s.id, status: d.error ? '❌' : '✅', msg: d.error || (d.task_id || 'OK') });
        } catch (e) { results.push({ url, account: s.id, status: '❌', msg: e.message }); }
      }
    }
    const totalOk = results.filter(r => r.status === '✅').length;
    el.textContent = '✅ ' + totalOk + '/' + results.length + ' 完成\n' +
      results.slice(0, 30).map(r => r.status + ' ' + r.account + ' ' + r.url.slice(0, 35) + ' ' + r.msg).join('\n');
  };
}

/**
 * 定向评论视图（已迁移）
 * 使用共享账号选择器
 */

import { apiRequest, confirmExecute } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

let _selector = null;

export async function loadView(container) {
  const uid = container.id || 'comment';
  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">💬 定向评论 <span style="font-size:10px;color:var(--text2);font-weight:400">选择账号 → 填入视频链接 → 方向/语料 → 执行</span></div>
        <div id="acctList_${uid}" style="margin-bottom:6px"><div class="loading">⏳ 加载账号列表...</div></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
          <textarea id="urls_${uid}" placeholder="视频链接（每行一个，支持多个）" rows="3" style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
          <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:140px">
            <select id="dir_${uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
              <option value="">自动选方向</option>
              <option value="称赞">👍 称赞</option><option value="提问">🤔 提问</option>
              <option value="共鸣">💗 共鸣</option><option value="感慨">😌 感慨</option>
              <option value="客观">📊 客观</option>
            </select>
            <select id="corpus_${uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
              <option value="">默认语料</option>
              <option value="通用">📚 通用</option><option value="科技">💻 科技</option>
              <option value="生活">🏠 生活</option><option value="美食">🍔 美食</option>
              <option value="娱乐">🎮 娱乐</option>
            </select>
            <button onclick="window._runComment()" style="background:var(--primary);color:#fff;border:none;padding:5px 12px;border-radius:4px;cursor:pointer;font-size:12px">🚀 执行评论</button>
          </div>
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
        height: '200px',
        showBlueprint: false,
        showCollectTime: false,
      });
    }
  } catch(e) {
    const listEl = document.getElementById(`acctList_${uid}`);
    if (listEl) listEl.innerHTML = `<div class="error">❌ ${e.message}</div>`;
  }

  registerGlobals(uid);
}

function registerGlobals(uid) {
  if (window._commentGlobals) return;
  window._commentGlobals = true;

  window._runComment = async function () {
    const selected = _selector?.getSelected() || [];
    const urlsText = document.getElementById(`urls_${uid}`)?.value;
    const dir = document.getElementById(`dir_${uid}`)?.value;
    const corpus = document.getElementById(`corpus_${uid}`)?.value;
    const el = document.getElementById(`result_${uid}`);

    if (!urlsText || !urlsText.trim()) { el.textContent = '请填写至少一个视频链接'; return; }
    const urls = urlsText.split('\n').map(u => u.trim()).filter(u => u);
    if (!urls.length) { el.textContent = '请填写有效的视频链接'; return; }
    if (!selected.length) { el.textContent = '请先选择要执行的账号'; return; }

    // 执行前确认
    const detail = `账号: ${selected.map(s=>s.id).join(', ')}\n视频: ${urls.join('\n')}\n方向: ${dir || '自动'}\n语料: ${corpus || '默认'}`;
    const confirmed = await confirmExecute(`即将用 ${selected.length} 个账号评论 ${urls.length} 个视频`, detail);
    if (!confirmed) { el.textContent = '已取消'; return; }

    el.textContent = '⏳ 使用 ' + selected.length + ' 个账号评论 ' + urls.length + ' 个视频...\n';
    const results = [];
    for (const url of urls) {
      for (const s of selected) {
        try {
          const d = await apiRequest('/ops/run', {
            method: 'POST',
            body: JSON.stringify({type:'comment', accounts:[account], params:{url, direction}})
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

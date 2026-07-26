/**
 * 💬 私信沟通 — 批量发送私信
 *
 * API: POST /api/ops/run {type:'dm', accounts, params:{targets, message, corpus}}
 */
import { apiRequest } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

let _selector = null;
let _parsedItems = [];

export async function loadView(container) {
  const uid = (container.id || 'dm').replace(/-/g, '_');
  const data = await apiRequest('/v2/accounts');
  const allAccts = Array.isArray(data) ? data : (data.accounts || []);

  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:4px">💬 私信沟通 <span style="font-size:10px;color:var(--text2);font-weight:400">选择账号 → 输入目标用户 → 发送私信</span></div>

        <div id="acctList_${uid}" style="margin-bottom:6px"></div>

        <div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:8px">
          <div style="font-size:11px;color:var(--text2);margin-bottom:4px">🎯 目标用户（每行一个 抖音号/链接）</div>
          <textarea id="dm_input_${uid}" rows="3" style="width:100%;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px;font-family:monospace" placeholder="输入抖音号或主页链接，每行一个"></textarea>
        </div>

        <div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:8px">
          <div style="font-size:11px;color:var(--text2);margin-bottom:4px">💬 私信内容（支持 {nickname} 模板变量）</div>
          <textarea id="dm_message_${uid}" rows="4" style="width:100%;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px;font-family:monospace" placeholder="输入私信内容..."></textarea>
          <div style="font-size:9px;color:var(--text2);margin-top:2px">可选：选择语料库随机抽取内容</div>
          <select id="dm_corpus_${uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px;margin-top:2px">
            <option value="">不使用语料库</option>
          </select>
          <div id="dm_corpus_status_${uid}" style="font-size:9px;color:var(--text2);margin-top:2px"></div>
        </div>

        <div style="display:flex;gap:6px;align-items:center">
          <button id="dm_execBtn_${uid}" style="background:#6366f1;color:#fff;border:none;padding:6px 16px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">📨 发送私信</button>
          <span id="dm_status_${uid}" style="font-size:10px;color:var(--text2)"></span>
        </div>
      </div>
    </div>`;

  _selector = createAccountSelector(`acctList_${uid}`, {
    accounts: allAccts, multiSelect: true,
  });

  // 加载语料库
  try {
    const r = await fetch('/api/corpus/list');
    const d = await r.json();
    const sel = document.getElementById(`dm_corpus_${uid}`);
    (d.corpus || []).forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.name; opt.textContent = c.name;
      sel.appendChild(opt);
    });
  } catch(e) {}

  document.getElementById(`dm_execBtn_${uid}`).addEventListener('click', async () => {
    const accounts = _selector.getSelected();
    if (!accounts.length) { alert('请选择账号'); return; }
    const targets = document.getElementById(`dm_input_${uid}`).value.trim().split('\\n').filter(Boolean);
    if (!targets.length) { alert('请输入目标用户'); return; }
    const message = document.getElementById(`dm_message_${uid}`).value.trim();
    if (!message) { alert('请输入私信内容'); return; }
    const corpus = document.getElementById(`dm_corpus_${uid}`).value;
    const statusEl = document.getElementById(`dm_status_${uid}`);
    statusEl.textContent = '⏳ 提交中...';
    try {
      const r = await apiRequest('/ops/run', {
        method: 'POST',
        body: JSON.stringify({ type: 'dm', accounts: accounts.map(a => a.id), params: { targets, message, corpus } }),
      });
      statusEl.textContent = r.run_id ? '✅ 已提交' : '❌ ' + (r.message || '失败');
    } catch(e) { statusEl.textContent = '❌ ' + e.message; }
  });
}

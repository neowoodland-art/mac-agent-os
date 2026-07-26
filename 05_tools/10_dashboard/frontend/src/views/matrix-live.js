/**
 * 🔴 直播互动 — 直播互动操作
 *
 * API: POST /api/ops/run {type:'live', accounts, params:{targets, actions, corpus}}
 */
import { apiRequest } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

let _selector = null;

export async function loadView(container) {
  const uid = (container.id || 'live').replace(/-/g, '_');
  const data = await apiRequest('/v2/accounts');
  const allAccts = Array.isArray(data) ? data : (data.accounts || []);

  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:4px">🔴 直播互动 <span style="font-size:10px;color:var(--text2);font-weight:400">选择账号 → 输入直播间链接 → 执行互动</span></div>

        <div id="acctList_${uid}" style="margin-bottom:6px"></div>

        <div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:8px">
          <div style="font-size:11px;color:var(--text2);margin-bottom:4px">🎯 直播间链接（每行一个）</div>
          <textarea id="live_input_${uid}" rows="3" style="width:100%;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px;font-family:monospace" placeholder="输入抖音直播间链接，每行一个"></textarea>
        </div>

        <div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:8px">
          <div style="font-size:11px;color:var(--text2);margin-bottom:6px">🎚️ 互动动作</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;font-size:11px">
            <div style="display:flex;align-items:center;gap:4px">
              <span>👍</span><span style="width:50px">点赞</span>
              <input type="range" id="live_rate_like_${uid}" min="0" max="100" value="80" style="flex:1;height:4px"
                oninput="document.getElementById('live_val_like_${uid}').textContent=this.value+'%'">
              <span id="live_val_like_${uid}" style="width:36px;text-align:right;font-size:10px;color:var(--text2)">80%</span>
            </div>
            <div style="display:flex;align-items:center;gap:4px">
              <span>💬</span><span style="width:50px">评论</span>
              <input type="range" id="live_rate_comment_${uid}" min="0" max="100" value="100" style="flex:1;height:4px"
                oninput="document.getElementById('live_val_comment_${uid}').textContent=this.value+'%'">
              <span id="live_val_comment_${uid}" style="width:36px;text-align:right;font-size:10px;color:var(--text2)">100%</span>
            </div>
          </div>
          <div style="font-size:9px;color:var(--text2);margin-top:2px">评论内容来源：</div>
          <select id="live_corpus_${uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px;margin-top:2px">
            <option value="">不使用语料库</option>
          </select>
        </div>

        <div style="display:flex;gap:6px;align-items:center">
          <button id="live_execBtn_${uid}" style="background:#ef4444;color:#fff;border:none;padding:6px 16px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🔴 开始互动</button>
          <span id="live_status_${uid}" style="font-size:10px;color:var(--text2)"></span>
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
    const sel = document.getElementById(`live_corpus_${uid}`);
    (d.corpus || []).forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.name; opt.textContent = c.name;
      sel.appendChild(opt);
    });
  } catch(e) {}

  document.getElementById(`live_execBtn_${uid}`).addEventListener('click', async () => {
    const accounts = _selector.getSelected();
    if (!accounts.length) { alert('请选择账号'); return; }
    const targets = document.getElementById(`live_input_${uid}`).value.trim().split('\\n').filter(Boolean);
    if (!targets.length) { alert('请输入直播间链接'); return; }
    const like_rate = parseInt(document.getElementById(`live_rate_like_${uid}`).value);
    const comment_rate = parseInt(document.getElementById(`live_rate_comment_${uid}`).value);
    const corpus = document.getElementById(`live_corpus_${uid}`).value;
    const statusEl = document.getElementById(`live_status_${uid}`);
    statusEl.textContent = '⏳ 提交中...';
    try {
      const r = await apiRequest('/ops/run', {
        method: 'POST',
        body: JSON.stringify({
          type: 'live',
          accounts: accounts.map(a => a.id),
          params: { targets, actions: { like: like_rate, comment: comment_rate }, corpus },
        }),
      });
      statusEl.textContent = r.run_id ? '✅ 已提交' : '❌ ' + (r.message || '失败');
    } catch(e) { statusEl.textContent = '❌ ' + e.message; }
  });
}

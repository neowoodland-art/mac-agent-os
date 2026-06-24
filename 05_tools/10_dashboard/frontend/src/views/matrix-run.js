export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
  try {
    const [acctR, opsR] = await Promise.all([
      fetch('/api/matrix/accounts').then(r => r.ok ? r.json() : { accounts: [] }).catch(() => ({ accounts: [] })),
      fetch('/api/ops/history').then(r => r.ok ? r.json() : { commands: [] }).catch(() => ({ commands: [] })),
    ]);
    const accounts = Array.isArray(acctR) ? acctR : (acctR.accounts || []);
    const history = opsR.commands || [];
    const accountOpts = accounts.map(a => `<option value="${a.id}">${a.platform==='xiaohongshu'?'📕':'🎵'} ${a.id} (${a.phone||''})</option>`).join('');
    container.innerHTML = `
      <div style="font-size:18px;font-weight:600;margin-bottom:12px">🚀 批量执行</div>
      <div style="display:grid;gap:8px;background:var(--bg2);padding:12px;border-radius:10px;border:1px solid var(--border);margin-bottom:12px">
        <div><label style="font-size:12px;font-weight:600">选择账号</label>
          <div style="display:flex;gap:4px;flex-wrap:wrap;max-height:150px;overflow-y:auto;margin-top:4px">
            ${accounts.map(a => `<label style="font-size:11px;display:inline-flex;align-items:center;gap:4px;padding:2px 6px;background:var(--bg3);border-radius:4px"><input type="checkbox" class="runAcct" value="${a.id}"> ${a.platform==='xiaohongshu'?'📕':'🎵'} ${a.id}</label>`).join('')}
          </div>
        </div>
        <div><label style="font-size:12px;font-weight:600">命令类型 <select id="runType" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:4px;font-size:11px">
          <option value="login">🔑 登录</option><option value="collect">📡 采集</option><option value="nurture">🏃 养号</option><option value="comment">💬 评论</option>
        </select></label></div>
        <div><label style="font-size:12px;font-weight:600">额外参数 <input id="runParams" placeholder='{"blueprint":"douyin_daily","rounds":3}' style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:4px;font-size:11px"></label></div>
        <button id="runBtn" style="background:var(--primary);color:#fff;border:none;padding:8px;border-radius:6px;cursor:pointer;font-size:13px">▶ 执行选中账号</button>
        <div id="runResult" style="font-size:11px"></div>
      </div>
      <div style="font-size:13px;font-weight:600;margin-bottom:8px">📋 最近执行</div>
      <div style="font-size:11px;max-height:300px;overflow-y:auto">
        ${history.length ? history.slice(0,20).map(c => `<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid var(--border);font-size:11px">
          <span>${c.status==='completed'?'✅':c.status==='running'?'🟢':c.status==='failed'?'❌':'⏳'} ${c.type||'?'}</span>
          <span>${(c.accounts||[]).join(',')}</span><span style="color:var(--text2)">${c.message||''}</span>
          <span style="color:var(--text2)">${c.elapsed_sec||0}s</span>
        </div>`).join('') : '<span style="color:var(--text2)">暂无执行记录</span>'}
      </div>`;
    document.getElementById('runBtn').onclick = async () => {
      const selAccts = [...document.querySelectorAll('.runAcct:checked')].map(cb => cb.value);
      if (!selAccts.length) { alert('请选择至少一个账号'); return; }
      const type = document.getElementById('runType').value;
      let params = {};
      try { params = JSON.parse(document.getElementById('runParams').value || '{}'); } catch(e) {}
      document.getElementById('runResult').innerHTML = '⏳ 执行中...';
      try {
        const r = await fetch('/api/ops/run', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({type, accounts: selAccts, params}) });
        const d = await r.json();
        document.getElementById('runResult').innerHTML = `<span style="color:var(--green)">✅ ${d.status||'已发送'} ${d.message||''}</span>`;
      } catch(e) { document.getElementById('runResult').innerHTML = `<span style="color:var(--red)">❌ ${e.message}</span>`; }
    };
  } catch(e) { container.innerHTML = `<div class="error">❌ ${e.message}</div>`; }
}

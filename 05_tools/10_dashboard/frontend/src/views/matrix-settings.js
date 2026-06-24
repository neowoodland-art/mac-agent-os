export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
  try {
    const r = await fetch('/api/matrix/config');
    const cfg = await r.json();
    container.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">⚙️ 矩阵设置</h2>
        <button onclick="location.reload()" style="background:var(--bg3);border:1px solid var(--border);padding:5px 12px;border-radius:5px;cursor:pointer;font-size:12px">🔄 刷新</button>
      </div>
      <div style="background:var(--bg2);border-radius:10px;padding:16px;border:1px solid var(--border);max-width:500px">
        <div style="display:grid;gap:10px;font-size:12px">
          <label>最大并发浏览器数 <input id="s_maxBrowsers" value="${cfg.max_concurrent_browsers||3}" style="width:80px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:4px"></label>
          <label>命令超时(秒) <input id="s_timeout" value="${cfg.command_timeout||600}" style="width:80px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:4px"></label>
          <label>默认轮数 <input id="s_rounds" value="${cfg.default_rounds||10}" style="width:80px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:4px"></label>
          <label>养号间隔(秒) <input id="s_interval" value="${cfg.nurture_interval||'30-60'}" style="width:80px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:4px"></label>
          <button id="saveBtn" style="background:var(--primary);color:#fff;border:none;padding:8px;border-radius:6px;cursor:pointer;font-size:13px">💾 保存配置</button>
          <div id="saveResult" style="font-size:11px"></div>
        </div>
      </div>`;
    document.getElementById('saveBtn').onclick = async () => {
      const data = {
        max_concurrent_browsers: parseInt(document.getElementById('s_maxBrowsers').value) || 3,
        command_timeout: parseInt(document.getElementById('s_timeout').value) || 600,
        default_rounds: parseInt(document.getElementById('s_rounds').value) || 10,
        nurture_interval: document.getElementById('s_interval').value || '30-60',
      };
      try {
        const r = await fetch('/api/matrix/config', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) });
        const d = await r.json();
        document.getElementById('saveResult').innerHTML = d.status==='ok' ? '<span style="color:var(--green)">✅ 已保存</span>' : '<span style="color:var(--red)">❌ '+d.error+'</span>';
      } catch(e) { document.getElementById('saveResult').innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>'; }
    };
  } catch(e) { container.innerHTML = `<div class="error">❌ ${e.message}</div>`; }
}

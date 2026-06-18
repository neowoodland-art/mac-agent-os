/**
 * 一键同步视图（已迁移）
 */
export async function loadView(container) {
  const uid = 'fs_' + Math.random().toString(36).slice(2, 6);
  container.innerHTML = `
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">🔄 一键同步</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">通过 Git 同步三台机器（本机 / 5kecheng / 7kecheng）的最新代码</p>
      <div style="display:flex;gap:8px;margin-bottom:12px">
        <button id="btnSync_${uid}" onclick="window._doFleetSync('${uid}')" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">🔄 执行同步</button>
      </div>
      <div id="log_${uid}" style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:400px;overflow:auto"></div>
    </div>`;

  window._doFleetSync = window._doFleetSync || async function(uid) {
    const logEl = document.getElementById(`log_${uid}`);
    const btn = document.getElementById(`btnSync_${uid}`);
    if (!logEl) return;
    logEl.textContent = '⏳ 执行中...\n';
    btn.disabled = true;
    btn.textContent = '⏳ 同步中...';
    try {
      const r = await fetch('/api/fleet/sync', { method: 'POST' });
      const d = await r.json();
      logEl.textContent = d.output || JSON.stringify(d, null, 2);
    } catch(e) {
      logEl.textContent = '❌ ' + e.message;
    }
    btn.disabled = false;
    btn.textContent = '🔄 执行同步';
  };
}

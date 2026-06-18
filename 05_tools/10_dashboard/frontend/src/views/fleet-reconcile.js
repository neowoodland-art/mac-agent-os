/**
 * 对账检查视图（已迁移）
 */
export async function loadView(container) {
  const uid = 'fr_' + Math.random().toString(36).slice(2, 6);
  container.innerHTML = `
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">🔍 对账检查</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">检查本机是否符合 ORACLE.yaml 宪法定义</p>
      <div style="display:flex;gap:8px;margin-bottom:12px">
        <button id="btnReconcile_${uid}" onclick="window._doFleetReconcile('${uid}')" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">🔍 执行对账</button>
      </div>
      <div id="log_${uid}" style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:400px;overflow:auto"></div>
    </div>`;

  window._doFleetReconcile = window._doFleetReconcile || async function(uid) {
    const logEl = document.getElementById(`log_${uid}`);
    if (!logEl) return;
    logEl.textContent = '⏳ 执行中...\n';
    try {
      const r = await fetch('/api/fleet/reconcile', { method: 'POST' });
      const d = await r.json();
      logEl.textContent = d.output || JSON.stringify(d, null, 2);
    } catch(e) {
      logEl.textContent = '❌ ' + e.message;
    }
  };
}

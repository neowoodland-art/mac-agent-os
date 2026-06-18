/**
 * 定时任务视图（已迁移）
 */
export async function loadView(container) {
  container.innerHTML = '<div id="schedPanel" style="padding:20px"><div class="loading">⏳ 加载定时任务...</div></div>';
  try {
    const ri = await fetch('/api/matrix/schedules');
    const di = await ri.json();
    const tasks = di.tasks || di || [];
    container.innerHTML = `
      <div style="padding:20px">
        <h2 style="font-size:18px;margin-bottom:12px">⏰ 定时任务</h2>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);margin-bottom:12px">
          <div style="font-size:12px;font-weight:600;margin-bottom:6px">📋 任务列表 (${Array.isArray(tasks) ? tasks.length : 0})</div>
          <div style="font-size:12px">${Array.isArray(tasks) && tasks.length ? tasks.map(t =>
            `<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border)">
              <span style="font-size:10px">${t.enabled ? '🟢' : '⚪'}</span>
              <span>${t.account || t.id || '-'}</span>
              <span style="font-size:11px;color:var(--text2)">${t.blueprint || ''}</span>
              <span style="font-size:11px;color:var(--text2)">${t.time || ''}</span>
            </div>`
          ).join('') : '<span style="color:var(--text2)">暂无定时任务</span>'}</div>
        </div>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);margin-bottom:8px">
          <div style="font-size:12px;font-weight:600;margin-bottom:6px">📋 操作</div>
          <button onclick="switchView('matrix-commands')" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">→ 前往命令与任务页</button>
        </div>
      </div>`;
  } catch(e) {
    container.innerHTML = `<div style="padding:20px"><div class="error">❌ ${e.message}</div></div>`;
  }
}

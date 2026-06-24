export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
  try {
    const r = await fetch('/api/matrix/backups/list');
    const d = await r.json();
    const list = d.backups || [];
    container.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">💾 备份恢复</h2>
        <button onclick="location.reload()" style="background:var(--bg3);border:1px solid var(--border);padding:5px 12px;border-radius:5px;cursor:pointer;font-size:12px">🔄 刷新</button>
      </div>
      ${list.length ? `<table style="width:100%;font-size:11px;border-collapse:collapse">
        <tr style="border-bottom:1px solid var(--border);font-size:10px;color:var(--text2)"><th style="padding:4px;text-align:left">ID</th><th style="padding:4px;text-align:left">标签</th><th style="padding:4px;text-align:left">时间</th><th style="padding:4px;text-align:left">大小</th><th style="padding:4px">操作</th></tr>
        ${list.map(b => `<tr style="border-bottom:1px solid var(--border)"><td style="padding:4px">${b.id}</td><td style="padding:4px">${b.label||'-'}</td><td style="padding:4px">${b.created_at||'-'}</td><td style="padding:4px">${b.size||'-'}</td><td style="padding:4px"><button onclick="fetch('/api/matrix/backups/restore/${b.id}',{method:'POST'}).then(()=>location.reload())" style="background:var(--bg3);border:1px solid var(--border);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">恢复</button></td></tr>`).join('')}
      </table>` : '<div style="color:var(--text2);font-size:12px">暂无备份</div>'}
      <div style="margin-top:12px"><button onclick="fetch('/api/matrix/backups/create',{method:'POST'}).then(()=>location.reload())" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">+ 创建备份</button></div>`;
  } catch(e) { container.innerHTML = `<div class="error">❌ ${e.message}</div>`; }
}

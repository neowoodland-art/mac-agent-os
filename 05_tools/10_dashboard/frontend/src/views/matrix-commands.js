export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
  try {
    const r = await fetch('/api/ops/history');
    const d = await r.json();
    const cmds = d.commands || [];
    container.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">🎯 命令与任务</h2>
        <button onclick="location.reload()" style="background:var(--bg3);border:1px solid var(--border);padding:5px 12px;border-radius:5px;cursor:pointer;font-size:12px">🔄 刷新</button>
      </div>
      <div style="font-size:11px;margin-bottom:8px;color:var(--text2)">共 ${cmds.length} 条记录</div>
      <table style="width:100%;font-size:11px;border-collapse:collapse">
        <tr style="border-bottom:1px solid var(--border);color:var(--text2);font-size:10px">
          <th style="padding:4px;text-align:left">状态</th><th style="padding:4px;text-align:left">类型</th><th style="padding:4px;text-align:left">账号</th><th style="padding:4px;text-align:left">机器</th><th style="padding:4px;text-align:left">消息</th><th style="padding:4px;text-align:right">耗时</th><th style="padding:4px;text-align:right">时间</th>
        </tr>
        ${cmds.slice(0,50).map(c => {
          const icon = c.status === 'completed' ? '✅' : c.status === 'running' ? '🟢' : c.status === 'failed' ? '❌' : c.status === 'dispatching' ? '📡' : '⏳';
          return `<tr style="border-bottom:1px solid var(--border)">
            <td style="padding:3px 4px">${icon}</td>
            <td style="padding:3px 4px">${c.type||c.command_type||'?'}</td>
            <td style="padding:3px 4px">${(c.accounts||[c.account||'']).filter(Boolean).join(',')}</td>
            <td style="padding:3px 4px">${c.machine||'?'}</td>
            <td style="padding:3px 4px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${c.message||c.status||''}</td>
            <td style="padding:3px 4px;text-align:right">${c.elapsed_sec ? c.elapsed_sec+'s' : '-'}</td>
            <td style="padding:3px 4px;text-align:right;font-size:10px;color:var(--text2)">${c.created_at ? c.created_at.slice(11,19) : ''}</td>
          </tr>`;
        }).join('')}
      </table>`;
  } catch(e) { container.innerHTML = `<div class="error">❌ ${e.message}</div>`; }
}

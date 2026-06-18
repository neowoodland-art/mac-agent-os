/**
 * 账号管理视图（已迁移）
 */
let _acctsData = [];

export async function loadView(container) {
  container.innerHTML = '<div class="loading">加载中...</div>';
  try {
    // 加载机器信息
    let machinesInfo = '';
    try {
      const mr = await fetch('/api/matrix/cross-machines');
      const md = await mr.json();
      if (md.total_machines) {
        machinesInfo = '<div style="display:flex;gap:12px;margin-bottom:12px;font-size:12px;color:var(--text2);background:var(--bg2);border-radius:var(--radius);padding:8px 12px;border:1px solid var(--border)">' +
          '<span>🖥️ 机器: <strong>' + md.total_machines + '</strong></span>' +
          '<span>👤 账号: <strong>' + md.total_accounts + '</strong></span>' +
          '<span>📡 在线: <strong style="color:var(--green)">' + md.online_machines + '</strong></span>' +
          '</div>';
      }
    } catch(e) { /* ignore */ }

    const r = await fetch('/api/matrix/accounts');
    const d = await r.json();
    _acctsData = Array.isArray(d) ? d : (d.accounts || []);

    if (!_acctsData.length) {
      container.innerHTML = machinesInfo + '<div class="error">暂无账号</div>';
      return;
    }

    container.innerHTML = machinesInfo;
    renderTable(container);
  } catch (e) {
    container.innerHTML = `<span style="color:var(--red)">${e.message}</span>`;
  }
}

function renderTable(container) {
  let html = `
    <div style="background:var(--bg2);border-radius:var(--radius);padding:10px;border:1px solid var(--border);overflow-x:auto;max-height:600px;overflow-y:auto">
    <table style="width:100%;font-size:11px;border-collapse:collapse">
    <thead><tr style="position:sticky;top:0;background:var(--bg2);z-index:1">
      <th onclick="window._acctSort(0)" style="cursor:pointer;padding:6px 4px;border-bottom:2px solid var(--border);white-space:nowrap;text-align:left">ID <span id="as0"></span></th>
      <th onclick="window._acctSort(1)" style="cursor:pointer;padding:6px 4px;border-bottom:2px solid var(--border);white-space:nowrap;text-align:left">机器 <span id="as1"></span></th>
      <th onclick="window._acctSort(2)" style="cursor:pointer;padding:6px 4px;border-bottom:2px solid var(--border);white-space:nowrap;text-align:left">平台 <span id="as2"></span></th>
      <th onclick="window._acctSort(3)" style="cursor:pointer;padding:6px 4px;border-bottom:2px solid var(--border);white-space:nowrap;text-align:left">手机号 <span id="as3"></span></th>
      <th onclick="window._acctSort(4)" style="cursor:pointer;padding:6px 4px;border-bottom:2px solid var(--border);white-space:nowrap;text-align:left">状态 <span id="as4"></span></th>
      <th onclick="window._acctSort(5)" style="cursor:pointer;padding:6px 4px;border-bottom:2px solid var(--border);white-space:nowrap;text-align:left">身份目录 <span id="as5"></span></th>
    </tr></thead>
    <tbody id="acctTbody">`;

  _acctsData.forEach(a => {
    const plat = a.platform === 'douyin' ? '🎵' : a.platform === 'xiaohongshu' ? '📕' : a.platform;
    const status = a._status || '-';
    const statusColor = status === 'logged_in' ? 'var(--green)' : status === 'no_cookie' ? 'var(--red)' : 'var(--text2)';
    html += `<tr>
      <td style="padding:4px;border-bottom:1px solid var(--border);white-space:nowrap"><strong>${a.id}</strong></td>
      <td style="padding:4px;border-bottom:1px solid var(--border);white-space:nowrap">${a.owner_machine || '-'}</td>
      <td style="padding:4px;border-bottom:1px solid var(--border)">${plat}</td>
      <td style="padding:4px;border-bottom:1px solid var(--border)">${a.phone || '-'}</td>
      <td style="padding:4px;border-bottom:1px solid var(--border);color:${statusColor}">${status}</td>
      <td style="padding:4px;border-bottom:1px solid var(--border);font-size:10px;color:var(--text2)">${a.identity_dir || '-'}</td>
    </tr>`;
  });

  html += '</tbody></table></div>';
  html += `<div style="margin-top:6px;font-size:11px;color:var(--text2)">共 ${_acctsData.length} 个账号</div>`;
  container.innerHTML += html;

  // 排序
  let _sortCol = 0, _sortAsc = true;
  window._acctSort = function(col) {
    if (_sortCol === col) _sortAsc = !_sortAsc;
    else { _sortCol = col; _sortAsc = true; }
    document.querySelectorAll('[id^="as"]').forEach(el => el.textContent = '');
    const arrowEl = document.getElementById(`as${col}`);
    if (arrowEl) arrowEl.textContent = _sortAsc ? '▲' : '▼';

    const tbody = document.getElementById('acctTbody');
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const cols = ['td:nth-child(1)', 'td:nth-child(2)', 'td:nth-child(3)', 'td:nth-child(4)', 'td:nth-child(5)', 'td:nth-child(6)'];
    rows.sort((a, b) => {
      const va = (a.querySelector(cols[col]) || {}).textContent || '';
      const vb = (b.querySelector(cols[col]) || {}).textContent || '';
      if (!isNaN(parseFloat(va)) && !isNaN(parseFloat(vb))) return parseFloat(va) - parseFloat(vb);
      return va.localeCompare(vb, 'zh');
    });
    if (!_sortAsc) rows.reverse();
    rows.forEach(r => tbody.appendChild(r));
  };
}

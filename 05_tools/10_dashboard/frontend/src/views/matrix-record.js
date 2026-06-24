/**
 * 录制管理视图 — 录制包列表与统计
 */
export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
  try {
    const [listRes, statsRes] = await Promise.all([
      fetch('/api/matrix/recordings/list'),
      fetch('/api/matrix/recordings/stats'),
    ]);
    const listData = listRes.ok ? await listRes.json() : { recordings: [] };
    const statsData = statsRes.ok ? await statsRes.json() : {};
    const recordings = Array.isArray(listData) ? listData : (listData.recordings || []);
    const stats = statsData.stats || statsData;

    // 格式化时长（秒 → 可读）
    function fmtDuration(sec) {
      if (sec == null) return '-';
      const s = Math.floor(sec);
      const h = Math.floor(s / 3600);
      const m = Math.floor((s % 3600) / 60);
      const ss = s % 60;
      return h > 0 ? `${h}h${m}m` : m > 0 ? `${m}m${ss}s` : `${ss}s`;
    }

    // 格式化时间戳
    function fmtTime(ts) {
      if (!ts) return '-';
      try {
        const d = new Date(ts);
        return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
      } catch { return ts; }
    }

    const totalDuration = stats.total_duration || recordings.reduce((acc, r) => acc + (r.duration || 0), 0);
    const totalCount = recordings.length;

    container.innerHTML = `
      <div style="padding:16px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
          <h2 style="font-size:18px;margin:0">📹 录制管理</h2>
          <span style="font-size:12px;color:var(--text2)">
            <strong>${totalCount}</strong> 条录制 · 总时长 <strong>${fmtDuration(totalDuration)}</strong>
          </span>
        </div>
        <div style="display:flex;gap:6px;margin-bottom:8px;align-items:center">
          <input id="recSearch" placeholder="🔍 搜索账号/任务/备注..." oninput="_filterRec()"
            style="flex:1;padding:4px 8px;font-size:12px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px">
          <span id="recCount" style="font-size:11px;color:var(--text2);white-space:nowrap">共 ${recordings.length} 条</span>
        </div>
        <div id="recTable" style="overflow-x:auto"></div>
      </div>`;

    function buildTable(items) {
      if (!items.length) return '<div style="font-size:12px;color:var(--text2);padding:20px;text-align:center">暂无录制记录</div>';
      let html = '<table style="width:100%;font-size:11px;border-collapse:collapse">';
      html += `<tr style="font-size:9px;color:var(--text2);border-bottom:1px solid var(--border)">
        <th style="padding:4px 6px;font-weight:400;text-align:left">账号</th>
        <th style="padding:4px 6px;font-weight:400;text-align:left">任务</th>
        <th style="padding:4px 6px;font-weight:400;text-align:right">时长</th>
        <th style="padding:4px 6px;font-weight:400;text-align:right">大小</th>
        <th style="padding:4px 6px;font-weight:400;text-align:left">录制时间</th>
        <th style="padding:4px 6px;font-weight:400;text-align:left">状态</th>
        <th style="padding:4px 6px;font-weight:400;text-align:left">备注</th>
      </tr>`;
      items.forEach(r => {
        const statusMap = { completed: '✅ 完成', running: '🔄 录制中', failed: '❌ 失败', pending: '⏳ 等待' };
        const s = statusMap[r.status] || r.status || '-';
        html += `<tr style="border-bottom:1px solid var(--border)" data-filter="${((r.account||'')+(r.task||'')+(r.note||'')).toLowerCase()}">
          <td style="padding:3px 6px"><strong>${r.account || '-'}</strong></td>
          <td style="padding:3px 6px;color:var(--text2)">${r.task || '-'}</td>
          <td style="padding:3px 6px;text-align:right">${fmtDuration(r.duration)}</td>
          <td style="padding:3px 6px;text-align:right;font-size:10px">${r.size ? (r.size / 1024 / 1024).toFixed(1) + 'MB' : '-'}</td>
          <td style="padding:3px 6px;font-size:10px;color:var(--text2)">${fmtTime(r.created_at || r.time)}</td>
          <td style="padding:3px 6px;font-size:10px">${s}</td>
          <td style="padding:3px 6px;font-size:10px;color:var(--text2);max-width:150px;overflow:hidden;text-overflow:ellipsis">${r.note || ''}</td>
        </tr>`;
      });
      html += '</table>';
      return html;
    }

    document.getElementById('recTable').innerHTML = buildTable(recordings);

    window._filterRec = () => {
      const q = (document.getElementById('recSearch')?.value || '').toLowerCase();
      const filtered = q ? recordings.filter(r =>
        ((r.account || '') + (r.task || '') + (r.note || '') + (r.id || '')).toLowerCase().includes(q)
      ) : recordings;
      document.getElementById('recCount').textContent = `共 ${filtered.length}/${recordings.length} 条`;
      document.getElementById('recTable').innerHTML = buildTable(filtered);
    };

    // 统计信息面板
    if (stats.total_recordings !== undefined || stats.by_account) {
      const extraPanel = document.createElement('div');
      extraPanel.style.cssText = 'margin-top:10px;padding:10px;background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);font-size:11px';
      let extraHtml = '<div style="font-weight:600;font-size:12px;margin-bottom:6px">📊 录制统计</div>';
      if (stats.by_account) {
        extraHtml += '<div style="display:flex;flex-wrap:wrap;gap:4px">';
        Object.entries(stats.by_account).forEach(([acct, cnt]) => {
          extraHtml += `<span style="background:var(--bg3);padding:2px 8px;border-radius:4px;border:1px solid var(--border)">${acct}: ${cnt}</span>`;
        });
        extraHtml += '</div>';
      }
      extraPanel.innerHTML = extraHtml;
      document.querySelector('#recTable')?.parentElement?.appendChild(extraPanel);
    }

  } catch (e) {
    container.innerHTML = `<div class="error">❌ ${e.message || e}</div>`;
  }
}

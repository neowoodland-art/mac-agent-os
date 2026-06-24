export async function loadView(container) {
  container.innerHTML = `<div class="view-loading"><div class="spinner"></div><p>加载采集历史...</p></div>`;

  try {
    const res = await fetch('/api/matrix/crawl-history?limit=50');
    if (!res.ok) throw new Error(`获取采集历史失败: ${res.status}`);
    const data = await res.json();
    const records = Array.isArray(data) ? data : (data.records || data.history || data.data || []);

    if (records.length === 0) {
      container.innerHTML = `
        <div class="view-header"><h2>🕸️ 采集历史</h2></div>
        <div class="empty-state">暂无采集记录</div>
        <div class="crawl-toolbar"><button id="crawl-refresh-btn" class="btn btn-secondary">🔄 刷新</button></div>
      `;
      container.querySelector('#crawl-refresh-btn')?.addEventListener('click', () => loadView(container));
      return;
    }

    container.innerHTML = `
      <div class="view-header">
        <h2>🕸️ 采集历史</h2>
        <span class="badge">${records.length} 条</span>
      </div>
      <div class="crawl-toolbar">
        <button id="crawl-refresh-btn" class="btn btn-secondary">🔄 刷新</button>
      </div>
      <div class="crawl-table-wrapper">
        <table class="crawl-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>账号</th>
              <th>平台</th>
              <th>状态</th>
              <th>详情</th>
            </tr>
          </thead>
          <tbody>
            ${records.map((r, idx) => {
              const time = r.time || r.timestamp || r.crawled_at || r.created_at || '';
              const account = r.account || r.username || r.user || r.account_id || '-';
              const platform = r.platform || r.source || r.type || '-';
              const status = (r.status || r.result || r.state || 'unknown').toLowerCase();
              const detail = r.detail || r.message || r.error || r.description || r.url || '';
              const statusLabel = status === 'success' || status === 'completed' ? '成功'
                : status === 'failed' || status === 'error' ? '失败'
                : status === 'running' || status === 'processing' ? '进行中'
                : status;

              return `
                <tr class="crawl-row-${status === 'success' || status === 'completed' ? 'success'
                  : status === 'failed' || status === 'error' ? 'failed'
                  : 'pending'}">
                  <td class="crawl-time">${formatTime(time)}</td>
                  <td class="crawl-account">${account}</td>
                  <td class="crawl-platform">${platform}</td>
                  <td class="crawl-status">
                    <span class="status-tag status-${status === 'success' || status === 'completed' ? 'success'
                      : status === 'failed' || status === 'error' ? 'failed'
                      : 'pending'}">${statusLabel}</span>
                  </td>
                  <td class="crawl-detail">${detail ? detail : '-'}</td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;

    // Wire up refresh
    container.querySelector('#crawl-refresh-btn')?.addEventListener('click', async () => {
      container.innerHTML = `<div class="view-loading"><div class="spinner"></div><p>刷新中...</p></div>`;
      try {
        await loadView(container);
      } catch (err) {
        container.innerHTML = `<div class="view-error"><h3>❌ 刷新失败</h3><p>${err.message}</p></div>`;
      }
    });

  } catch (err) {
    container.innerHTML = `<div class="view-error"><h3>❌ 加载失败</h3><p>${err.message}</p></div>`;
  }
}

function formatTime(ts) {
  if (!ts) return '-';
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    return d.toLocaleString('zh-CN', { hour12: false });
  } catch {
    return ts;
  }
}

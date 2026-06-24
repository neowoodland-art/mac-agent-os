export async function loadView(container) {
  container.innerHTML = `<div class="view-loading"><div class="spinner"></div><p>加载实时时间线...</p></div>`;

  try {
    const res = await fetch('/api/matrix/timeline');
    if (!res.ok) throw new Error(`获取时间线数据失败: ${res.status}`);
    const data = await res.json();
    const points = Array.isArray(data) ? data : (data.timeline || data.points || data.data || []);

    if (points.length === 0) {
      container.innerHTML = `
        <div class="view-header"><h2>📊 实时时间线</h2></div>
        <div class="empty-state">暂无时间线数据</div>
      `;
      return;
    }

    // Extract CPU and disk series
    const series = points.map((p, i) => ({
      label: p.label || p.time || p.timestamp || `T${i + 1}`,
      cpu: parseFloat(p.cpu ?? p.cpu_usage ?? p.cpu_percent ?? 0),
      disk: parseFloat(p.disk ?? p.disk_usage ?? p.disk_percent ?? 0),
      time: p.time || p.timestamp || null
    }));

    const maxCpu = Math.max(...series.map(s => s.cpu), 100);
    const maxDisk = Math.max(...series.map(s => s.disk), 100);
    const maxVal = Math.max(maxCpu, maxDisk, 1);

    container.innerHTML = `
      <div class="view-header">
        <h2>📊 实时时间线</h2>
        <span class="badge">${series.length} 个采样点</span>
      </div>
      <div class="timeline-controls">
        <button id="timeline-refresh-btn" class="btn btn-secondary">🔄 刷新</button>
      </div>

      <div class="timeline-section">
        <h3>💻 CPU 使用率</h3>
        <div class="bar-chart" id="cpu-chart">
          ${series.map(s => `
            <div class="bar-column" title="${s.label}: CPU ${s.cpu.toFixed(1)}%">
              <div class="bar-fill cpu-bar" style="height:${(s.cpu / maxVal) * 100}%"></div>
              <div class="bar-label">${s.label.length > 6 ? s.label.slice(0, 6) + '..' : s.label}</div>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="timeline-section">
        <h3>💾 磁盘使用率</h3>
        <div class="bar-chart" id="disk-chart">
          ${series.map(s => `
            <div class="bar-column" title="${s.label}: 磁盘 ${s.disk.toFixed(1)}%">
              <div class="bar-fill disk-bar" style="height:${(s.disk / maxVal) * 100}%"></div>
              <div class="bar-label">${s.label.length > 6 ? s.label.slice(0, 6) + '..' : s.label}</div>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="timeline-section">
        <h3>📋 详细数据</h3>
        <div class="timeline-table-wrapper">
          <table class="timeline-table">
            <thead>
              <tr>
                <th>时间 / 标签</th>
                <th>CPU (%)</th>
                <th>磁盘 (%)</th>
              </tr>
            </thead>
            <tbody>
              ${series.map(s => `
                <tr>
                  <td>${s.time ? formatTime(s.time) : s.label}</td>
                  <td><span class="value-bar" style="width:${Math.min(s.cpu, 100)}%">${s.cpu.toFixed(1)}</span></td>
                  <td><span class="value-bar disk-bar-inline" style="width:${Math.min(s.disk, 100)}%">${s.disk.toFixed(1)}</span></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    // Wire up refresh
    container.querySelector('#timeline-refresh-btn').addEventListener('click', async () => {
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
  if (!ts) return '';
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    return d.toLocaleString('zh-CN', { hour12: false });
  } catch {
    return ts;
  }
}

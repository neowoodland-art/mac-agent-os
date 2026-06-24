export async function loadView(container) {
  container.innerHTML = `<div class="view-loading"><div class="spinner"></div><p>加载概览...</p></div>`;

  try {
    // Fetch all data sources in parallel
    const [summaryRes, healthRes, machinesRes] = await Promise.all([
      fetch('/api/summary'),
      fetch('/api/federation/health'),
      fetch('/api/machines')
    ]);

    const summary = summaryRes.ok ? await summaryRes.json() : {};
    const health = healthRes.ok ? await healthRes.json() : {};
    const machines = machinesRes.ok ? await machinesRes.json() : [];

    // Normalize data
    const totalAccounts = summary.total_accounts ?? summary.accounts ?? summary.totalAccounts ?? 0;
    const totalBlueprints = summary.total_blueprints ?? summary.blueprints ?? summary.totalBlueprints ?? 0;
    const newMessages = summary.new_messages ?? summary.messages ?? summary.newMessages ?? 0;
    const totalTasks = summary.total_tasks ?? summary.tasks ?? summary.totalTasks ?? 0;

    const machineList = Array.isArray(machines) ? machines
      : (machines.machines || machines.data || machines.nodes || []);

    const healthStatus = (health.status || health.healthy) ?? false;
    const isHealthy = healthStatus === true || healthStatus === 'healthy' || healthStatus === 'ok' || healthStatus === 'online';
    const onlineCount = machineList.filter(m => {
      const s = (m.status || m.state || '').toLowerCase();
      return s === 'online' || s === 'running' || s === 'active' || s === 'healthy' || m.online === true;
    }).length;
    const totalMachines = machineList.length;

    container.innerHTML = `
      <div class="view-header">
        <h2>📊 系统概览</h2>
      </div>

      <!-- Summary Cards -->
      <div class="summary-grid">
        <div class="summary-card">
          <div class="summary-card-icon">🖥️</div>
          <div class="summary-card-value">${totalMachines}</div>
          <div class="summary-card-label">总机器数</div>
          <div class="summary-card-sub">${onlineCount} 在线</div>
        </div>
        <div class="summary-card">
          <div class="summary-card-icon">👤</div>
          <div class="summary-card-value">${totalAccounts}</div>
          <div class="summary-card-label">总账号数</div>
        </div>
        <div class="summary-card">
          <div class="summary-card-icon">📋</div>
          <div class="summary-card-value">${totalBlueprints}</div>
          <div class="summary-card-label">总蓝图数</div>
        </div>
        <div class="summary-card">
          <div class="summary-card-icon">💬</div>
          <div class="summary-card-value">${newMessages}</div>
          <div class="summary-card-label">新消息数</div>
        </div>
        <div class="summary-card">
          <div class="summary-card-icon">📌</div>
          <div class="summary-card-value">${totalTasks}</div>
          <div class="summary-card-label">任务总数</div>
        </div>
        <div class="summary-card health-card">
          <div class="summary-card-icon">${isHealthy ? '✅' : '❌'}</div>
          <div class="summary-card-value">${isHealthy ? '健康' : '异常'}</div>
          <div class="summary-card-label">联邦健康</div>
          <div class="summary-card-sub">${typeof healthStatus === 'string' ? healthStatus : (isHealthy ? 'running' : 'down')}</div>
        </div>
      </div>

      <!-- Machine Status -->
      <div class="view-section">
        <h3>🖥️ 机器在线状态</h3>
        <div class="machine-status-list">
          ${machineList.length === 0
            ? '<div class="empty-state">暂无机器数据</div>'
            : machineList.map(m => {
                const mStatus = (m.status || m.state || 'unknown').toLowerCase();
                const isOnline = mStatus === 'online' || mStatus === 'running' || mStatus === 'active' || mStatus === 'healthy' || m.online === true;
                return `
                  <div class="machine-status-item ${isOnline ? 'online' : 'offline'}">
                    <span class="machine-status-dot ${isOnline ? 'dot-online' : 'dot-offline'}"></span>
                    <span class="machine-name">${m.name || m.hostname || m.id || '未知'}</span>
                    <span class="machine-status-text">${isOnline ? '在线' : '离线'}</span>
                    ${m.ip || m.host ? `<span class="machine-ip">${m.ip || m.host}</span>` : ''}
                  </div>
                `;
              }).join('')
          }
        </div>
      </div>
    `;

  } catch (err) {
    container.innerHTML = `<div class="view-error"><h3>❌ 加载失败</h3><p>${err.message}</p></div>`;
  }
}

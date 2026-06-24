export async function loadView(container) {
  container.innerHTML = `<div class="view-loading"><div class="spinner"></div><p>加载告警中心...</p></div>`;

  try {
    await renderAlerts(container);
  } catch (err) {
    container.innerHTML = `<div class="view-error"><h3>❌ 加载失败</h3><p>${err.message}</p></div>`;
  }
}

async function renderAlerts(container) {
  const res = await fetch('/api/matrix/alerts/list');
  if (!res.ok) throw new Error(`获取告警列表失败: ${res.status}`);
  const alerts = await res.json();
  const list = Array.isArray(alerts) ? alerts : (alerts.alerts || alerts.data || []);

  container.innerHTML = `
    <div class="view-header">
      <h2>🔔 告警中心</h2>
      <span class="badge">${list.length} 条</span>
    </div>
    <div class="alerts-toolbar">
      <button id="alerts-refresh-btn" class="btn btn-secondary">🔄 刷新</button>
    </div>
    <div class="alerts-list">
      ${list.length === 0
        ? '<div class="empty-state">暂无告警 🎉</div>'
        : list.map((alert, idx) => renderAlertItem(alert, idx)).join('')
      }
    </div>
  `;

  // Wire up refresh
  container.querySelector('#alerts-refresh-btn').addEventListener('click', async () => {
    container.innerHTML = `<div class="view-loading"><div class="spinner"></div><p>刷新中...</p></div>`;
    try {
      await renderAlerts(container);
    } catch (err) {
      container.innerHTML = `<div class="view-error"><h3>❌ 刷新失败</h3><p>${err.message}</p></div>`;
    }
  });

  // Wire up dismiss buttons
  container.querySelectorAll('.alert-dismiss-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const alertId = e.target.dataset.alertId;
      if (!alertId) return;
      if (!confirm('确认清除此告警？')) return;

      try {
        const delRes = await fetch(`/api/matrix/alerts/${alertId}`, { method: 'DELETE' });
        if (!delRes.ok) throw new Error(`清除失败: ${delRes.status}`);
        // Remove the item from DOM
        const item = e.target.closest('.alert-item');
        if (item) item.remove();
        // Update badge
        const badge = container.querySelector('.badge');
        const remaining = container.querySelectorAll('.alert-item').length;
        if (badge) badge.textContent = `${remaining} 条`;
        if (remaining === 0) {
          const listEl = container.querySelector('.alerts-list');
          if (listEl) listEl.innerHTML = '<div class="empty-state">暂无告警 🎉</div>';
        }
      } catch (err) {
        alert(`清除告警失败: ${err.message}`);
      }
    });
  });
}

function renderAlertItem(alert, idx) {
  const id = alert.id || alert.alert_id || `alert-${idx}`;
  const severity = (alert.severity || alert.level || 'info').toLowerCase();
  const message = alert.message || alert.msg || alert.title || JSON.stringify(alert);
  const time = alert.time || alert.timestamp || alert.created_at || '';
  const severityLabels = { critical: '严重', error: '错误', warning: '警告', info: '信息' };
  const severityLabel = severityLabels[severity] || severity;
  const severityClass = severity === 'critical' ? 'severity-critical'
    : severity === 'error' ? 'severity-error'
    : severity === 'warning' ? 'severity-warning'
    : 'severity-info';

  return `
    <div class="alert-item ${severityClass}">
      <div class="alert-icon">${severity === 'critical' ? '🔴' : severity === 'error' ? '⛔' : severity === 'warning' ? '⚠️' : 'ℹ️'}</div>
      <div class="alert-body">
        <div class="alert-severity">${severityLabel}</div>
        <div class="alert-message">${message}</div>
        ${time ? `<div class="alert-time">${formatTime(time)}</div>` : ''}
      </div>
      <button class="alert-dismiss-btn btn btn-sm" data-alert-id="${id}">✕</button>
    </div>
  `;
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

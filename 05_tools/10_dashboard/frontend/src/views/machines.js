/**
 * 机器状态视图（已迁移）
 * 替换 index.html 中 inline 的 loadMachines()
 */

import { showLoading, showError, apiRequest } from '../router.js';

export async function loadView(container) {
  showLoading(container, '读取联邦心跳中...');

  try {
    const d = await apiRequest('/machines');
    const machines = d.machines || [];

    // 更新计数
    const countEl = document.getElementById('machineCount');
    if (countEl) countEl.textContent = `共 ${machines.length} 台主机`;

    if (!machines.length) {
      container.innerHTML = '<div class="error" style="padding:40px">无心跳数据</div>';
      return;
    }

    container.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px" id="machineGrid">
        ${machines.map(m => renderMachineCard(m)).join('')}
      </div>
    `;
  } catch (e) {
    showError(container, `加载失败: ${e.message}`);
  }
}

function renderMachineCard(m) {
  // 在线状态 = 信任 API 的 status 字段
  // 心跳时间仅做参考提示，不改变状态判定
  const lastPushSec = m._last_push_sec || 0;
  const isOnline = m.status === 'online';
  const isRecent = m.status === 'recent';
  const dotColor = isOnline ? '#22C55E' : isRecent ? '#F59E0B' : '#EF4444';
  const statusText = isOnline ? '在线' : isRecent ? '近期' : '离线';
  const minAgo = m.minutes_ago || Math.round(lastPushSec / 60) || 0;
  const timeStr = lastPushSec < 60
    ? `${lastPushSec}秒前`
    : minAgo < 60
      ? `${minAgo} 分钟前`
      : `${(minAgo / 60).toFixed(1)} 小时前`;

  const diskUsed = m.disk_used_gb || 0;
  const diskTotal = m.disk_total_gb || 1;
  const diskPct = Math.round((diskUsed / diskTotal) * 100);
  const diskColor = diskPct > 85 ? 'var(--red)' : diskPct > 60 ? 'var(--amber)' : 'var(--green)';
  const diskBar = `
    <div style="height:6px;background:var(--bg3);border-radius:3px;margin:6px 0;overflow:hidden">
      <div style="height:100%;width:${diskPct}%;background:${diskColor};border-radius:3px;transition:width .3s"></div>
    </div>`;

  return `
    <div style="background:var(--bg2);border-radius:var(--radius);padding:20px;border:1px solid ${isOnline ? 'rgba(34,197,94,.2)' : 'var(--border)'}">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
        <div style="display:flex;align-items:center;gap:10px">
          <span style="width:10px;height:10px;border-radius:50%;background:${dotColor};display:inline-block;"></span>
          <div>
            <div style="font-weight:600;font-size:15px">${m.hostname}</div>
            ${m._uid ? `<span style="font-size:10px;color:var(--text2);margin-left:6px">UID: ${m._uid}</span>` : ''}
            <div style="font-size:11px;color:var(--text2)">${m.os || ''}</div>
          </div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px;margin-bottom:12px">
        <div><span style="color:var(--text2)">guardd</span><br>v${m.guardd_version || '-'}</div>
        <div><span style="color:var(--text2)">最后心跳</span><br>${timeStr}</div>
        <div><span style="color:var(--text2)">CPU 负载</span><br>${m.cpu_load || '-'}</div>
        <div><span style="color:var(--text2)">当前任务</span><br>${m.current_task || '无'}</div>
      </div>

      <div style="font-size:12px;color:var(--text2);margin-bottom:2px">磁盘: ${(diskUsed).toFixed(0)}G / ${(diskTotal).toFixed(0)}G</div>
      ${diskBar}
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text2)">
        <span>已用 ${diskPct}%</span>
        <span>剩余 ${(m.disk_avail_gb || 0).toFixed(0)}G</span>
      </div>

      ${m.is_duplicate ? `<div style="margin-top:8px;padding:4px 8px;background:rgba(245,158,11,.1);border-radius:4px;font-size:11px;color:var(--amber)">⚠ hostname 变更: 原名 ${m.duplicate_of || ''}</div>` : ''}
    </div>`;
}

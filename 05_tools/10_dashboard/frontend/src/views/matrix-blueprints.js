/**
 * 蓝图管理视图（已迁移）
 */
export async function loadView(container) {
  container.innerHTML = '<div class="loading">加载中...</div>';
  try {
    const [br, or] = await Promise.all([
      fetch('/api/matrix/blueprints'),
      fetch('/api/matrix/atom-ops'),
    ]);
    const bd = await br.json();
    const od = await or.json();
    const bps = Array.isArray(bd) ? bd : (bd.blueprints || []);
    const allOps = od.ops || [];
    window._matrixOps = {};
    allOps.forEach(o => { window._matrixOps[o.name] = o; });

    const platformLabels = { douyin: '🎵 抖音', xiaohongshu: '📕 小红书' };
    const bpGroups = { douyin: [], xiaohongshu: [] };
    bps.forEach(bp => {
      const p = bp.platform || 'douyin';
      if (bpGroups[p]) bpGroups[p].push(bp);
    });

    let html = '<div style="padding:16px">';

    // 统计行
    html += `<div style="display:flex;gap:10px;margin-bottom:10px;font-size:12px;color:var(--text2)">
      <span>📋 蓝图库: <strong>${bps.length}</strong></span>
      <span>🎵 抖音: <strong>${bpGroups.douyin.length}</strong></span>
      <span>📕 小红书: <strong>${bpGroups.xiaohongshu.length}</strong></span>
    </div>`;

    // 平台分组
    Object.entries(bpGroups).forEach(([platform, blist]) => {
      if (!blist.length) return;
      html += `<div style="background:var(--bg2);border-radius:var(--radius);padding:10px;border:1px solid var(--border);margin-bottom:8px">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">${platformLabels[platform] || platform} (${blist.length})</div>`;

      blist.forEach(bp => {
        const ops = bp.steps || bp.ops || [];
        html += `<div style="background:var(--bg3);border-radius:6px;padding:8px;margin-bottom:4px;border:1px solid var(--border)">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-weight:600;font-size:12px">${bp.name}</span>
            <span style="font-size:10px;color:var(--text2)">${ops.length} 步</span>
          </div>
          <div style="font-size:10px;color:var(--text2);margin-top:2px">${ops.map((o, i) =>
            `${i + 1}. ${o.op || o.name || ''}`).join(' · ')}
          </div>
        </div>`;
      });
      html += '</div>';
    });

    // 原子操作列表
    html += `<div style="background:var(--bg2);border-radius:var(--radius);padding:10px;border:1px solid var(--border)">
      <div style="font-weight:600;font-size:13px;margin-bottom:6px">⚙️ 原子操作 (${allOps.length})</div>`;
    const opGroups = {};
    allOps.forEach(o => {
      const p = o.platform || '通用';
      if (!opGroups[p]) opGroups[p] = [];
      opGroups[p].push(o);
    });
    Object.entries(opGroups).forEach(([p, items]) => {
      html += `<div style="margin-bottom:4px">
        <div style="font-size:11px;font-weight:500;color:var(--text2);margin-bottom:2px">${p}</div>
        <div style="display:flex;flex-wrap:wrap;gap:3px">${items.map(o =>
          `<span style="font-size:10px;background:var(--bg3);padding:2px 6px;border-radius:4px;border:1px solid var(--border)">${o.name}</span>`
        ).join('')}</div>
      </div>`;
    });
    html += '</div></div>';

    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}

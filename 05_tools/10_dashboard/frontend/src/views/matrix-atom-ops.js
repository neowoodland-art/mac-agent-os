/**
 * 原子操作视图（已迁移）
 */
export async function loadView(container) {
  container.innerHTML = '<div class="loading">加载中...</div>';
  try {
    const r = await fetch('/api/matrix/atom-ops');
    const d = await r.json();
    const ops = d.ops || [];

    const groups = {};
    ops.forEach(o => {
      const p = o.platform || '通用';
      if (!groups[p]) groups[p] = [];
      groups[p].push(o);
    });

    const platformLabels = { douyin: '🎵 抖音', xiaohongshu: '📕 小红书', '通用': '⚙️ 通用' };

    let html = `<div style="padding:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <h2 style="font-size:18px;margin:0">⚙️ 原子操作</h2>
        <span style="font-size:12px;color:var(--text2)">共 ${ops.length} 个操作</span>
      </div>`;

    Object.entries(groups).forEach(([p, items]) => {
      const subGroups = {};
      items.forEach(o => {
        const g = o.category || '其他';
        if (!subGroups[g]) subGroups[g] = [];
        subGroups[g].push(o);
      });
      const catLabels = { navigation: '🏠 导航', browse: '📱 浏览', interact: '💡 交互', utility: '⏳ 工具' };

      html += `<div style="margin-bottom:16px">
        <div style="font-size:14px;font-weight:700;margin-bottom:10px;padding:6px 10px;border-radius:6px;background:var(--bg3)">${platformLabels[p] || p} <span style="font-weight:400;font-size:11px;color:var(--text2)">(${items.length})</span></div>`;

      Object.entries(subGroups).forEach(([cat, catItems]) => {
        html += `<div style="margin-bottom:8px">
          <div style="font-size:11px;color:var(--text2);margin-bottom:4px;padding-left:4px">${catLabels[cat] || cat}</div>
          <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:4px">`;
        catItems.forEach(o => {
          html += `<div style="background:var(--bg3);border-radius:6px;padding:6px 8px;border:1px solid var(--border)">
            <div style="font-size:11px;font-weight:500">${o.name}</div>
            <div style="font-size:9px;color:var(--text2);margin-top:1px">${o.description || o.desc || '-'}</div>
          </div>`;
        });
        html += '</div></div>';
      });
      html += '</div>';
    });

    html += '</div>';
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}

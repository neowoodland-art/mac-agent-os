/**
 * 语料库视图（已迁移）
 */
export async function loadView(container) {
  container.innerHTML = '<div class="loading">加载中...</div>';
  try {
    const r = await fetch('/api/matrix/corpus');
    const d = await r.json();
    const cats = d.categories || [];

    // 按平台分组
    const groups = {};
    cats.forEach(c => {
      const p = c.platform === 'xiaohongshu' ? '📕 小红书' : '🎵 抖音';
      if (!groups[p]) groups[p] = [];
      groups[p].push(c);
    });

    let html = `<div style="padding:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <h2 style="font-size:18px;margin:0">📚 语料库</h2>
        <span style="font-size:12px;color:var(--text2)">共 ${cats.length} 个分类 · ${d.total_comments || 0} 条评论</span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px">`;

    Object.entries(groups).forEach(([platform, items]) => {
      html += `<div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:14px;margin-bottom:10px">${platform}</div>
        <table style="width:100%;font-size:11px;border-collapse:collapse">
        <thead><tr><th style="text-align:left;padding:4px;border-bottom:1px solid var(--border)">分类</th><th style="padding:4px;border-bottom:1px solid var(--border)">权重</th><th style="padding:4px;border-bottom:1px solid var(--border)">评论数</th></tr></thead>
        <tbody>${items.map(c => `<tr>
          <td style="padding:4px;border-bottom:1px solid var(--border)">${c.name}</td>
          <td style="padding:4px;border-bottom:1px solid var(--border);text-align:center">${c.weight || '-'}</td>
          <td style="padding:4px;border-bottom:1px solid var(--border);text-align:center">${c.count || c.comment_count || 0}</td>
        </tr>`).join('')}</tbody></table>
      </div>`;
    });

    html += '</div></div>';
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}

/**
 * 成本视图（已迁移）
 */
export async function loadView(container) {
  container.innerHTML = `
    <div style="padding:16px">
      <h2 style="font-size:18px;margin-bottom:12px">💰 费用统计</h2>
      <div id="costSummary"></div>
      <div id="costBreakdown" style="margin-top:12px"></div>
    </div>`;

  try {
    // 总览
    const r = await fetch('/api/summary');
    const d = await r.json();
    const s = d.ave || d;
    document.getElementById('costSummary').innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
        <div style="background:var(--bg2);border-radius:var(--radius);padding:16px;border:1px solid var(--border);text-align:center">
          <div style="font-size:11px;color:var(--text2)">总费用</div>
          <div style="font-size:24px;font-weight:700">¥${(s.total_cost || 0).toFixed(2)}</div>
        </div>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:16px;border:1px solid var(--border);text-align:center">
          <div style="font-size:11px;color:var(--text2)">本月费用</div>
          <div style="font-size:24px;font-weight:700">¥${(s.month_cost || 0).toFixed(2)}</div>
        </div>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:16px;border:1px solid var(--border);text-align:center">
          <div style="font-size:11px;color:var(--text2)">平均费用/生产</div>
          <div style="font-size:24px;font-weight:700">¥${s.total_productions ? (s.total_cost / s.total_productions).toFixed(2) : '0.00'}</div>
        </div>
      </div>`;

    // 按策略统计
    const r2 = await fetch('/api/costs/breakdown');
    const strategies = await r2.json();
    if (!strategies.length) {
      document.getElementById('costBreakdown').innerHTML = '<div class="error" style="padding:40px">暂无费用数据</div>';
      return;
    }
    const maxCost = Math.max(...strategies.map(s => s.total_cost), 1);
    const colors = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#3b82f6'];

    document.getElementById('costBreakdown').innerHTML = `
      <div style="background:var(--bg2);border-radius:var(--radius);padding:16px;border:1px solid var(--border)">
        <div style="font-size:14px;font-weight:600;margin-bottom:12px">按策略统计</div>
        ${strategies.map((s, i) => `
          <div style="margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:2px">
              <span>${s.name || s.strategy}</span>
              <span>¥${(s.total_cost || 0).toFixed(2)} (${s.count || 0} 次)</span>
            </div>
            <div style="height:8px;background:var(--bg3);border-radius:4px;overflow:hidden">
              <div style="height:100%;width:${((s.total_cost || 0) / maxCost * 100).toFixed(1)}%;background:${colors[i % colors.length]};border-radius:4px;transition:width .3s"></div>
            </div>
          </div>
        `).join('')}
      </div>`;
  } catch (e) {
    container.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}

/**
 * 能力目录视图（已迁移）
 */
let _capGroup = 0;
export async function loadView(container) {
  container.innerHTML = `
    <div style="padding:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">⚡ 能力目录</h2>
        <span id="capCount" style="font-size:12px;color:var(--text2)"></span>
      </div>
      <div id="capGroupTabs" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px"></div>
      <div id="capabilityContent"><div class="loading">加载原子能力...</div></div>
    </div>`;

  try {
    const r = await fetch('/api/capabilities');
    const d = await r.json();
    const groups = d.groups || [];
    const matrix = d.matrix || [];

    const countEl = document.getElementById('capCount');
    if (countEl) countEl.textContent = `共 ${d.total_items || 0} 个能力`;

    if (!groups.length) {
      document.getElementById('capabilityContent').innerHTML = '<div class="error" style="padding:40px">暂无能力数据</div>';
      return;
    }

    // 分组标签
    document.getElementById('capGroupTabs').innerHTML = groups.map((g, i) =>
      `<button class="btn ${i === 0 ? 'active' : ''}" onclick="window._switchCapGroup(${i})"
        style="${i === 0 ? 'background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px'
        : 'background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px'}">
        ${g.name} (${g.items.length})
      </button>`
    ).join('');

    _capGroup = 0;
    renderGroup(groups[0], matrix);

    window._switchCapGroup = function(idx) {
      _capGroup = idx;
      // 更新按钮样式
      document.querySelectorAll('#capGroupTabs .btn').forEach((btn, i) => {
        Object.assign(btn.style, i === idx
          ? { background: 'var(--primary)', color: '#fff', border: 'none' }
          : { background: 'var(--bg2)', border: '1px solid var(--border)', color: 'var(--text)' });
      });
      renderGroup(groups[idx], matrix);
    };

  } catch (e) {
    container.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}

function renderGroup(group, matrix) {
  const el = document.getElementById('capabilityContent');
  if (!el) return;
  if (!group || !group.items || !group.items.length) {
    el.innerHTML = '<div class="error" style="padding:40px">暂无数据</div>';
    return;
  }
  el.innerHTML = `
    <div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border);overflow-x:auto">
      <table style="width:100%;font-size:12px;border-collapse:collapse">
        <thead><tr>
          ${Object.keys(group.items[0] || {}).map(h => `<th style="text-align:left;padding:6px 8px;border-bottom:2px solid var(--border);white-space:nowrap">${h}</th>`).join('')}
        </tr></thead>
        <tbody>
          ${group.items.map(item =>
            `<tr>${Object.values(item).map(v =>
              `<td style="padding:4px 8px;border-bottom:1px solid var(--border);font-size:11px">${v || '-'}</td>`
            ).join('')}</tr>`
          ).join('')}
        </tbody>
      </table>
    </div>`;
}

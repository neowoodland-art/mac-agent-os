/**
 * 生产列表视图（已迁移）
 */
export async function loadView(container) {
  container.innerHTML = '<div class="loading">加载中...</div>';
  // 矩阵养号运营数据看板
  try {
    const sr = await fetch('/api/matrix/sms/accounts');
    const sd = await sr.json();
    const accts = (sd.accounts || []).filter(a => a.is_local);
    const online = accts.filter(a => a.has_cookie);
    const profiled = accts.filter(a => a.has_profile);

    let html = `<div style="padding:16px">
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px">
        <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center">
          <div style="font-size:24px;font-weight:700;color:#6366f1">${accts.length}</div>
          <div style="font-size:11px;color:var(--text2)">📱 本机账号</div>
        </div>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center">
          <div style="font-size:24px;font-weight:700;color:var(--green)">${online.length}</div>
          <div style="font-size:11px;color:var(--text2)">🔑 已登录</div>
        </div>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center">
          <div style="font-size:24px;font-weight:700;color:var(--amber)">${profiled.length}</div>
          <div style="font-size:11px;color:var(--text2)">📋 已采集</div>
        </div>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center">
          <div style="font-size:24px;font-weight:700;color:var(--blue)">${online.length - profiled.length}</div>
          <div style="font-size:11px;color:var(--text2)">🔄 待采集</div>
        </div>
      </div>`;

    // 生产列表筛选器
    html += `<div class="filter-bar">
      <select id="filterStrategy_p"><option value="">全部策略</option>
        <option>口播</option><option>卡点</option><option>数字人</option><option>test</option>
      </select>
      <select id="filterStatus_p"><option value="">全部状态</option>
        <option value="completed">已完成</option><option value="failed">失败</option><option value="running">运行中</option>
      </select>
      <input id="searchInput_p" placeholder="搜索脚本名称...">
      <button onclick="window._loadProdList()">查询</button>
      <div id="pagination_p"></div>
    </div>
    <div id="prodList_p" style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);margin-top:8px;min-height:100px">
      <div class="loading">加载生产列表...</div>
    </div>`;

    container.innerHTML = html;

    // 加载生产列表
    window._loadProdList = window._loadProdList || async function() {
      const listEl = document.getElementById('prodList_p');
      if (!listEl) return;
      listEl.innerHTML = '<div class="loading">加载中...</div>';
      try {
        const strategy = document.getElementById('filterStrategy_p')?.value || '';
        const status = document.getElementById('filterStatus_p')?.value || '';
        const search = document.getElementById('searchInput_p')?.value || '';
        const params = new URLSearchParams({ limit: 20 });
        if (strategy) params.set('strategy', strategy);
        if (status) params.set('status', status);
        if (search) params.set('search', search);
        const r = await fetch(`/api/productions?${params}`);
        const d = await r.json();
        const prods = d.productions || d.data || d || [];
        if (!Array.isArray(prods) || !prods.length) {
          listEl.innerHTML = '<div style="padding:40px;color:var(--text2);font-size:12px;text-align:center">暂无生产记录</div>';
          return;
        }
        listEl.innerHTML = prods.map(p =>
          `<div style="padding:8px;border-bottom:1px solid var(--border);font-size:12px;cursor:pointer" onclick="alert(JSON.stringify(${JSON.stringify(p).replace(/"/g, '&quot;')},null,2))">
            <div style="font-weight:500">${p.name || p.script_name || '未知'}</div>
            <div style="font-size:10px;color:var(--text2)">${p.status || '-'} · ${p.strategy || '-'} · ${p.created_at ? new Date(p.created_at).toLocaleString() : ''}</div>
          </div>`
        ).join('');
      } catch (e) {
        listEl.innerHTML = `<div class="error">❌ ${e.message}</div>`;
      }
    };

    window._loadProdList();

  } catch (e) {
    container.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}

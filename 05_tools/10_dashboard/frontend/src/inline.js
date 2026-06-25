// __UNIQUE_TEST_MARKER_987654321__

// ── State ──
const API = '';
let currentView = 'productions';

// ── Sidebar ──
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const btn = document.getElementById('sidebarToggleBtn');
  const isCollapsed = sb.classList.toggle('collapsed');
  btn.textContent = isCollapsed ? '▶' : '◀';
  btn.title = isCollapsed ? '展开侧边栏' : '折叠侧边栏';
}
function toggleGroup(el) {
  const body = el.nextElementSibling;
  if (!body || !body.classList) return;
  // 手风琴: 关闭其他所有分组
  document.querySelectorAll('.nav-group-header').forEach(h => {
    if (h === el) return;
    const b = h.nextElementSibling;
    if (b && b.classList && !b.classList.contains('collapsed')) {
      b.classList.add('collapsed');
      h.dataset.collapsed = 'true';
      const arrow = h.querySelector('span:last-child');
      if (arrow) arrow.textContent = '▶';
    }
  });
  // 切换当前分组
  const isCollapsed = body.classList.toggle('collapsed');
  el.dataset.collapsed = isCollapsed ? 'true' : 'false';
  el.querySelector('span:last-child').textContent = isCollapsed ? '▶' : '▼';
}
function collapseAllGroups() {
  document.querySelectorAll('.nav-group-header').forEach(h => {
    const body = h.nextElementSibling;
    if (body && body.classList && !body.classList.contains('collapsed')) {
      body.classList.add('collapsed');
      h.dataset.collapsed = 'true';
      const arrow = h.querySelector('span:last-child');
      if (arrow) arrow.textContent = '▶';
    }
  });
}
let currentPage = 0;
const PAGE_SIZE = 30;
let searchTimer;

// ── Init ──
loadIdentity();
loadPlugins();
loadStats();
// 自动刷新已由各 migrated view 的 loadView 自行管理

// ── Navigation ──
function switchView(view) {
  // Plugin views → inline rendering
  if (view === 'plugin-matrix') { view = 'matrix-summary'; }
  currentView = view;

  // 所有 nav-item 和 nav-sub 的 active 状态
  document.querySelectorAll('.nav-item, .nav-sub').forEach(e => {
    e.classList.toggle('active', e.dataset.view === view);
  });

  // 视频工厂：点击父级或子项时展开子菜单
  const aveSubViews = ['ave-render', 'ave-script', 'ave-materials', 'ave-templates'];
  const isAve = view === 'plugin-ave' || aveSubViews.includes(view);
  document.querySelectorAll('.nav-sub[data-group="ave"]').forEach(e => {
    e.style.display = isAve ? 'block' : 'none';
  });

  // 矩阵养号：点击父级或子项时展开子菜单
  const matrixSubViews = ['matrix-nurture','matrix-collect','matrix-publish','matrix-blueprints','matrix-interact','matrix-comment','matrix-schedule','matrix-corpus','matrix-sms-proxy','matrix-like','matrix-login','ops-command'];
  const isMatrix = view === 'plugin-matrix' || matrixSubViews.includes(view);
  document.querySelectorAll('.nav-sub[data-group="matrix"]').forEach(e => {
    e.style.display = isMatrix ? 'block' : 'none';
  });

  // 点击「视频工厂」时自动跳转到工作流编辑器
  if (view === 'plugin-ave') {
    document.querySelector('.nav-item[data-view="plugin-ave"]')?.classList.add('active');
    document.querySelector('.nav-sub[data-view="workflow"]')?.classList.add('active');
    switchView('workflow');
    return;
  }

  // 点击「矩阵养号」时自动跳转到多机总览
  if (view === 'plugin-matrix') {
    document.querySelector('.nav-item[data-view="plugin-matrix"]')?.classList.add('active');
    switchView('matrix-summary');
    return;
  }

  // KB tab views → route to kb view with tab switch
  const kbViewToTab = {'kb-knowledge':'kb-knowledge','kb-memory':'kb-memory','kb-system':'kb-system','kb-skills-int':'kb-skills'};
  if (kbViewToTab[view]) {
    const tabName = kbViewToTab[view];
    document.querySelectorAll('.nav-item').forEach(e => {
      e.classList.toggle('active', e.dataset.view === view);
    });
    // Hide ALL other views first
    ['matrix-sms-proxy','matrix-nurture','matrix-collect','matrix-publish','matrix-blueprints','matrix-interact','matrix-comment','matrix-schedule','matrix-corpus',
     'ave-render','ave-script','ave-materials','ave-templates',
     'crawl-tasks','crawl-sources','crawl-history',
     'machines','fleet-sync','fleet-reconcile','fleet-exec',
     'serve-mcp','serve-dashboard','serve-schedule',
     'productions','assets','costs','capabilities','workflow','kb'].forEach(v => {
      document.getElementById('view-' + v)?.classList.add('hidden');
    });
    document.querySelectorAll('[id^="plugin-view-"]').forEach(el => el.classList.add('hidden'));
    // Show KB view
    document.getElementById('view-kb')?.classList.remove('hidden');
    currentView = 'kb';
    const tab = document.querySelector('.kb-tab[data-tab="'+tabName+'"]');
    if (tab) kbSwitchTab(tabName, tab);
    return;
  }

  // 如果点了子项，高亮父级
  if (aveSubViews.includes(view)) {
    document.querySelector('.nav-item[data-view="plugin-ave"]')?.classList.add('active');
  }
  if (matrixSubViews.includes(view)) {
    document.querySelector('.nav-item[data-view="plugin-matrix"]')?.classList.add('active');
  }

  // 视图显隐
  // 视图显隐
  const viewIds = ['matrix-sms-proxy','matrix-nurture','matrix-collect','matrix-publish','matrix-blueprints','matrix-interact','matrix-comment','matrix-schedule','matrix-corpus',
                   'ave-render','ave-script','ave-materials','ave-templates',
                   'crawl-tasks','crawl-sources','crawl-history',
                   'machines','fleet-sync','fleet-reconcile','fleet-exec',
                   'serve-mcp','serve-dashboard','serve-schedule',
                   'productions','assets','costs','capabilities','workflow','kb'];
  viewIds.forEach(v => {
    document.getElementById('view-' + v)?.classList.toggle('hidden', v !== view);
  });

  // 插件视图（动态加载）
  document.querySelectorAll('[id^="plugin-view-"]').forEach(el => el.classList.add('hidden'));
  if (view.startsWith('plugin-') && !matrixSubViews.includes(view) && view !== 'matrix-summary') {
    const pv = document.getElementById('plugin-view-' + view.replace('plugin-',''));
    if (pv) pv.classList.remove('hidden');
  }

  // 所有视图已迁移，由 views/*.js 的 loadView 接管
}

// ── Stats ──
async function loadStats() {
  try {
    const r = await fetch(`${API}/api/summary`);
    const d = await r.json();
    // 从 guardd 插件获取机器数据（AVE 插件数据不全）
    const guarddPlugin = d.plugins && d.plugins.guardd;
    const guarddData = (guarddPlugin && guarddPlugin.data) || {};
    const machines = guarddData['各机器'] || {};
    const onlineCount = guarddData['在线'] || 0;
    const totalMachines = guarddData['总机器'] || Object.keys(machines).length || 0;
    
    document.getElementById('statsBar').innerHTML = `
      <div class="stat-card"><div class="label">机器数</div><div class="value" style="color:var(--green)">${totalMachines}</div><div class="sub">在线 ${onlineCount}</div></div>
      <div class="stat-card"><div class="label">模块</div><div class="value" style="color:var(--blue)">${Object.keys(d.plugins||{}).length}</div><div class="sub">已加载</div></div>
      <div class="stat-card"><div class="label">主机</div><div class="value" style="color:var(--amber)">${d.source_hostname||'-'}</div></div>
      <div class="stat-card"><div class="label">知识库</div><div class="value" style="color:var(--primary)">${d.kb_stats?.total||'?'}</div><div class="sub">篇</div></div>
    `;
  } catch(e) { document.getElementById('statsBar').innerHTML = `<div class="error">❌ 连接失败</div>`; }
}

// ── Productions ──
async function loadProductions(page) {
  if (page !== undefined) currentPage = page;
  const el = document.getElementById('productionList');

  // 矩阵养号运营数据看板（独立容器，不会被覆盖）
  try {
    let statsEl = document.getElementById('matrixDashboardStats');
    if (!statsEl) {
      statsEl = document.createElement('div');
      statsEl.id = 'matrixDashboardStats';
      el.parentNode.insertBefore(statsEl, el);
    }
    const sr = await fetch('/api/matrix/sms/accounts');
    const sd = await sr.json();
    const accts = (sd.accounts || []).filter(a => a.is_local);
    const online = accts.filter(a => a.has_cookie);
    const profiled = accts.filter(a => a.has_profile);
    statsEl.innerHTML = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px">'+
      '<div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center">'+
        '<div style="font-size:24px;font-weight:700;color:#6366f1">'+accts.length+'</div>'+
        '<div style="font-size:11px;color:var(--text2)">📱 本机账号</div></div>'+
      '<div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center">'+
        '<div style="font-size:24px;font-weight:700;color:var(--green)">'+online.length+'</div>'+
        '<div style="font-size:11px;color:var(--text2)">🔑 已登录</div></div>'+
      '<div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center">'+
        '<div style="font-size:24px;font-weight:700;color:var(--amber)">'+profiled.length+'</div>'+
        '<div style="font-size:11px;color:var(--text2)">👤 已采集</div></div>'+
      '<div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center">'+
        '<div style="font-size:24px;font-weight:700;color:var(--text2)">'+sd.accounts.length+'</div>'+
        '<div style="font-size:11px;color:var(--text2)">🌐 联邦账号</div></div>'+
    '</div>';
  } catch(e) { /* ignore */ }
  el.innerHTML = '<div class="loading">加载中...</div>';
  try {
    const strategy = document.getElementById('filterStrategy').value;
    const status = document.getElementById('filterStatus').value;
    const search = document.getElementById('searchInput').value;
    const params = new URLSearchParams({limit: PAGE_SIZE, offset: currentPage * PAGE_SIZE});
    if (strategy) params.set('strategy', strategy);
    if (status) params.set('status', status);
    const r = await fetch(`${API}/api/productions?${params}`);
    const res = await r.json();
    const data = res.data || [];

    if (!data.length) { el.innerHTML = '<div class="error" style="padding:40px">暂无生产记录</div>'; return; }

    const filtered = search ? data.filter(p => (p.script_name||'').includes(search)) : data;
    if (!filtered.length) { el.innerHTML = '<div class="error">未找到匹配记录</div>'; return; }

    el.innerHTML = `<table><thead><tr>
      <th>编号</th><th>策略</th><th>脚本</th><th>状态</th><th>费用</th><th>时长</th><th>时间</th>
    </tr></thead><tbody>${filtered.map(p => `<tr onclick="showDetail(${p.id})">
      <td>#${p.id}</td>
      <td>${p.strategy||'-'}</td>
      <td>${(p.script_name||'').slice(0,30)||'-'}</td>
      <td><span class="badge badge-${(p.status||'unknown').toLowerCase()}">${p.status}</span></td>
      <td>¥${(p.total_cost||0).toFixed(2)}</td>
      <td>${p.duration_sec ? p.duration_sec.toFixed(0) + 's' : '-'}</td>
      <td style="white-space:nowrap">${(p.created_at||'').slice(0,16)}</td>
    </tr>`).join('')}</tbody></table>`;

    // Pagination
    document.getElementById('pagination').innerHTML = currentPage > 0
      ? `<button onclick="loadProductions(${currentPage-1})">← 上一页</button><span style="padding:6px 12px;color:var(--text2)">第 ${currentPage+1} 页</span><button onclick="loadProductions(${currentPage+1})">下一页 →</button>`
      : `<span style="padding:6px 12px;color:var(--text2)">第 1 页</span><button onclick="loadProductions(${currentPage+1})">下一页 →</button>`;
    loadStats();
  } catch(e) { el.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`; }
}

function debounceSearch() { clearTimeout(searchTimer); searchTimer = setTimeout(() => loadProductions(0), 400); }

// ── Detail ──
async function showDetail(id) {
  const el = document.getElementById('detailModal');
  el.classList.remove('hidden');
  el.innerHTML = '<div class="loading" style="padding:60px">加载详情...</div>';
  try {
    const r = await fetch(`${API}/api/productions/${id}`);
    const d = await r.json();
    const p = d.production;
    const steps = d.steps || [];
    const assets = d.assets || [];
    const costs = d.costs || [];

    el.innerHTML = `<div style="position:fixed;inset:0;z-index:100;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;padding:20px" onclick="event.target===this&&closeDetail()">
      <div style="background:var(--bg2);border-radius:12px;max-width:800px;width:100%;max-height:85vh;overflow-y:auto;padding:24px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <div class="detail-header"><h2>#${p.id} ${p.strategy||''}</h2></div>
          <button onclick="closeDetail()" style="background:var(--bg3);border:none;color:var(--text);padding:6px 14px;border-radius:6px;cursor:pointer">✕ 关闭</button>
        </div>
        <div class="detail-meta">
          <span>状态: <span class="badge badge-${(p.status||'').toLowerCase()}">${p.status}</span></span>
          <span>时长: ${p.duration_sec ? p.duration_sec.toFixed(0) + 's' : '-'}</span>
          <span>费用: ¥${(p.total_cost||0).toFixed(2)}</span>
          <span>输出: ${(p.output_path||'-').slice(-30)}</span>
        </div>
        ${p.error_message ? `<div style="margin-top:12px;padding:10px;background:rgba(239,68,68,.1);border-radius:6px;color:var(--red);font-size:13px">${p.error_message}</div>` : ''}

        <div class="section-title">📋 步骤 (${steps.length})</div>
        <div class="step-list">${steps.length ? steps.map(s => `<div class="step-item">
          <div class="dot" style="background:${s.status==='completed'?'var(--green)':s.status==='failed'?'var(--red)':'var(--amber)'}"></div>
          <span class="name">${s.step_name}</span>
          <span class="meta">${s.detail||''}${s.cost ? ' ¥'+s.cost.toFixed(2) : ''}</span>
          ${s.error_message ? `<span style="color:var(--red);font-size:12px">${s.error_message}</span>` : ''}
        </div>`).join('') : '<div style="color:var(--text2);padding:10px">无步骤记录</div>'}</div>

        <div class="section-title">💰 费用明细 (${costs.length})</div>
        ${costs.length ? `<table><thead><tr><th>服务</th><th>时长</th><th>费用</th><th>备注</th></tr></thead><tbody>${costs.map(c => `<tr><td>${c.service||'-'}</td><td>${c.duration_s ? c.duration_s+'s' : c.chars ? c.chars+'字' : '-'}</td><td>¥${(c.cost_yuan||0).toFixed(2)}</td><td>${c.note||''}</td></tr>`).join('')}</tbody></table>`
        : '<div style="color:var(--text2);padding:10px">无费用记录</div>'}

        <div class="section-title">💾 资产 (${assets.length})</div>
        <div class="asset-grid">${assets.length ? assets.map(a => `<div class="asset-card">
          <div class="type">${a.asset_type||'-'}</div>
          <div class="name">${(a.name||a.file_path||'-').slice(0,40)}</div>
          <div class="meta">${a.source||''}${a.file_size ? ' · '+(a.file_size/1024).toFixed(0)+'KB' : ''}</div>
          ${a.tags ? `<div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap">${a.tags.split(',').map(t => `<span style="background:var(--bg3);padding:1px 6px;border-radius:4px;font-size:10px">${t}</span>`).join('')}</div>` : ''}
        </div>`).join('') : '<div style="color:var(--text2);padding:10px">无关联资产</div>'}</div>
      </div>
    </div>`;
  } catch(e) { el.innerHTML = `<div class="error">❌ 加载失败</div>`; }
}
function closeDetail() { document.getElementById('detailModal').classList.add('hidden'); }

// ── Assets ──
async function loadAssets(page) {
  const el = document.getElementById('assetList');
  el.innerHTML = '<div class="loading">加载中...</div>';
  try {
    const type = document.getElementById('assetTypeFilter').value;
    const tag = document.getElementById('assetSearch').value;
    const params = new URLSearchParams({limit: 50});
    if (type) params.set('type', type);
    if (tag) params.set('tag', tag);
    const r = await fetch(`${API}/api/assets?${params}`);
    const data = await r.json();
    if (!data.length) { el.innerHTML = '<div class="error" style="padding:40px">暂无资产</div>'; return; }
    el.innerHTML = `<div class="asset-grid">${data.map(a => `<div class="asset-card" onclick="showDetail(${a.production_id})" style="cursor:pointer">
      <div class="type">${a.asset_type||'-'}</div>
      <div class="name">${(a.name||a.file_path||'-').slice(0,40)}</div>
      <div class="meta">${a.source||''}${a.file_size ? ' · '+(a.file_size/1024).toFixed(0)+'KB' : ''}</div>
      ${a.tags ? `<div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap">${a.tags.split(',').map(t => `<span style="background:var(--bg3);padding:1px 6px;border-radius:4px;font-size:10px">${t}</span>`).join('')}</div>` : ''}
    </div>`).join('')}</div>`;
  } catch(e) { el.innerHTML = `<div class="error">❌ 加载失败</div>`; }
}
function debounceAssetSearch() { clearTimeout(searchTimer); searchTimer = setTimeout(() => loadAssets(), 400); }

// ── Costs ──
async function loadCosts() {
  const el1 = document.getElementById('costSummary');
  const el2 = document.getElementById('costBreakdown');
  try {
    const r = await fetch(`${API}/api/summary`);
    const d = await r.json();
    const s = d.ave || d;
    el1.innerHTML = `<div class="stats" style="grid-template-columns:repeat(3,1fr)">
      <div class="stat-card"><div class="label">总费用</div><div class="value">¥${(s.total_cost||0).toFixed(2)}</div></div>
      <div class="stat-card"><div class="label">本月费用</div><div class="value">¥${(s.month_cost||0).toFixed(2)}</div></div>
      <div class="stat-card"><div class="label">平均费用/生产</div><div class="value">¥${s.total_productions ? (s.total_cost/s.total_productions).toFixed(2) : '0.00'}</div></div>
    </div>`;

    // 按策略统计 (专用API)
    const r2 = await fetch(`${API}/api/costs/breakdown`);
    const strategies = await r2.json();
    const colors = ['#6366f1','#22c55e','#f59e0b','#ef4444','#3b82f6'];

    if (!strategies.length) {
      el2.innerHTML = '<div class="error" style="padding:40px">暂无费用数据</div>';
      return;
    }

    const maxCost = Math.max(...strategies.map(s => s.total_cost), 1);
    el2.innerHTML = `<div class="chart-box">
      <div style="font-size:14px;font-weight:600;margin-bottom:12px">按策略统计</div>
      <div class="cost-bar">${strategies.map((s,i) => `<div style="flex:${(s.total_cost/maxCost*100).toFixed(0)};background:${colors[i%5]};min-width:20px" title="${s.strategy}: ¥${s.total_cost.toFixed(2)}">¥${s.total_cost.toFixed(0)}</div>`).join('')}</div>
      <table><thead><tr><th>策略</th><th>次数</th><th>总时长</th><th>总费用</th><th>平均费用</th></tr></thead><tbody>
        ${strategies.map(s => `<tr><td>${s.strategy}</td><td>${s.count}</td><td>${(s.total_duration||0).toFixed(0)}s</td><td>¥${(s.total_cost||0).toFixed(2)}</td><td>¥${s.avg_cost||'0.00'}</td></tr>`).join('')}
      </tbody></table>
    </div>`;
  } catch(e) { el1.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`; }
}

// ── Machine Status ──
async function loadMachines() {
  const el = document.getElementById('machineGrid');
  const countEl = document.getElementById('machineCount');
  el.innerHTML = '<div class="loading">读取联邦心跳中...</div>';
  try {
    const r = await fetch(`${API}/api/machines`);
    const d = await r.json();
    const machines = d.machines || [];
    countEl.textContent = `共 ${machines.length} 台主机`;

    if (!machines.length) {
      el.innerHTML = '<div class="error" style="padding:40px">无心跳数据</div>';
      return;
    }

    el.innerHTML = machines.map(m => {
      // 安全取值
      const isOnline = m.status === 'online' || m._live === true;
      const isRecent = m.status === 'recent';
      const isLive = m._live === true;
      const dotColor = isLive ? '#1D9E75' : isOnline ? '#22C55E' : isRecent ? '#F59E0B' : '#EF4444';
      const statusText = isLive ? '实时' : isOnline ? '在线' : isRecent ? '近期' : '离线';
      const lastPushSec = m._last_push_sec || 0;
      const minAgo = m.minutes_ago || Math.round(lastPushSec / 60) || 999;
      const timeStr = isLive
        ? `${lastPushSec}秒前`
        : minAgo < 60
          ? `${minAgo} 分钟前`
          : `${(minAgo/60).toFixed(1)} 小时前`;

      // 磁盘条
      const diskUsed = m.disk_used_gb || 0;
      const diskTotal = m.disk_total_gb || 1;
      const diskPct = Math.round((diskUsed / diskTotal) * 100);
      const diskAvail = m.disk_avail_gb || 0;
      const diskColor = diskPct > 85 ? 'var(--red)' : diskPct > 60 ? 'var(--amber)' : 'var(--green)';
      const diskBar = `<div style="height:6px;background:var(--bg3);border-radius:3px;margin:6px 0;overflow:hidden">
        <div style="height:100%;width:${diskPct}%;background:${diskColor};border-radius:3px;transition:width .3s"></div>
      </div>`;

      // 角色标签
      const roleColor = '#378ADD';

      return `<div style="background:var(--bg2);border-radius:var(--radius);padding:20px;border:1px solid ${isOnline ? 'rgba(34,197,94,.2)' : 'var(--border)'}">
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
          <div><span style="color:var(--text2)">guardd</span><br>v${m.guardd_version||'-'}</div>
          <div><span style="color:var(--text2)">最后心跳</span><br>${timeStr}</div>
          <div><span style="color:var(--text2)">CPU 负载</span><br>${m.cpu_load||'-'}</div>
          <div><span style="color:var(--text2)">当前任务</span><br>${m.current_task||'无'}</div>
        </div>

        <div style="font-size:12px;color:var(--text2);margin-bottom:2px">磁盘: ${(m.disk_used_gb||0).toFixed(0)}G / ${(m.disk_total_gb||0).toFixed(0)}G</div>
        ${diskBar}
        <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text2)">
          <span>已用 ${diskPct}%</span>
          <span>剩余 ${(m.disk_avail_gb||0).toFixed(0)}G</span>
        </div>

        ${m.is_duplicate ? `<div style="margin-top:8px;padding:4px 8px;background:rgba(245,158,11,.1);border-radius:4px;font-size:11px;color:var(--amber)">⚠ hostname 变更: 原名 ${m.duplicate_of||''}</div>` : ''}
      </div>`;
    }).join('');
  } catch(e) {
    el.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}

// ── Identity & Plugin Init ──
async function loadIdentity() {
  try {
    const r = await fetch('/api/identity');
    const d = await r.json();
    document.getElementById('identityHostname').innerHTML = `📡 ${d.hostname}`;
    document.getElementById('identityMeta').innerHTML = `UID: ${d.uid} · ${d.role} · ${d.git_repo} @ ${(d.git_version||'').slice(0,7)}`;
  } catch(e) {}
}

async function loadPlugins() {
  try {
    const r = await fetch('/api/plugins');
    const res = await r.json();
    const nav = document.getElementById('navBar');
    const plugins = res.plugins || [];
    // 旧兼容: 忽略不存在的 pluginBadge/pluginCount

    // 构建分组侧边栏 (可折叠) — 按 COMMAND-CENTER-PLAN 排列
    let html = '';
    const S = (label, status) => `<span style="font-size:9px;margin-left:4px;padding:1px 5px;border-radius:3px;background:rgba(217,119,6,.12);color:#d97706;font-weight:500">${status}</span>`;
    const groups = {
      '矩阵': { icon: '📱', items: [
        {view:'matrix-sms-proxy', label:'🪪 账号管理'},
        {view:'matrix-nurture', label:'🏃 养号执行'},
        {view:'matrix-collect', label:'📡 信息采集'},
        {view:'matrix-publish', label:'📤 内容发布'},
        {view:'matrix-interact', label:'💬 评论互动'},
        {view:'matrix-comment', label:'💬 定向评论'},
        {view:'matrix-like', label:'❤️ 收藏点赞'},
        {view:'matrix-blueprints', label:'📋 蓝图管理'},
        {view:'matrix-login', label:'🔑 登录管理'},
        {view:'matrix-schedule', label:'⏱ 定时任务'},
        {view:'matrix-corpus', label:'📚 语料库'},
        {view:'ops-command', label:'🖥️ 联邦指挥台'},
      ]},
      '视频工厂': { icon: '🎬', items: [
        {view:'ave-render', label:'渲染任务'},
        {view:'ave-script', label:'脚本生成'},
        {view:'ave-materials', label:'素材库'},
        {view:'ave-templates', label:'模板'},
      ]},
      '内容采集': { icon: '📡', items: [
        {view:'crawl-tasks', label:'采集任务'},
        {view:'crawl-sources', label:'源管理'},
        {view:'crawl-history', label:'采集历史'},
      ]},
      '联邦': { icon: '🖥️', items: [
        {view:'machines', label:'机器状态'},
        {view:'fleet-sync', label:'一键同步'},
        {view:'fleet-reconcile', label:'对账检查'},
        {view:'fleet-exec', label:'远程Shell'},
        {view:'matrix-commands', label:'🎯 命令与任务'},
      ]},
      '服务': { icon: '⚙️', items: [
        {view:'serve-mcp', label:'MCP状态'},
        {view:'serve-dashboard', label:'Dashboard日志'},
        {view:'serve-schedule', label:'全局定时任务'},
      ]},
    };

    // ── 从 API 加载 agentos 插件注册的导航 ──
    // 已停用：插件导航与硬编码导航重叠（联邦管理/社交矩阵/系统设置），
    // 统一由硬编码导航控制，防止重复项
    async function loadNavFromAPI() {
      // 直接渲染，不使用插件导航
      _renderNav();
    }
    
    function _renderNav() {
      let html = '';
      for (const [gname, g] of Object.entries(groups)) {
        html += `<div class="nav-group-header" onclick="toggleGroup(this)" data-collapsed="true">${g.icon} ${gname} <span style="float:right;font-size:10px;opacity:.5">▶</span></div>`;
        html += `<div class="nav-group-body collapsed">`;
        for (const item of g.items) {
          if (item.sub) {
            html += `<div class="nav-item" data-view="${item.view}" onclick="switchView('${item.view}')">${item.label}</div>`;
            for (const sub of item.sub) {
              html += `<div class="nav-sub" data-group="${item.view.replace('plugin-','')}" data-view="${sub.view}" onclick="switchView('${sub.view}')" style="display:none">${sub.label}</div>`;
            }
          } else {
            html += `<div class="nav-item" data-view="${item.view}" onclick="switchView('${item.view}')">${item.label}</div>`;
          }
        }
        html += '</div>';
      }
      html += '<div class="nav-item" data-view="timeline" onclick="switchView(\'timeline\')" style="display:none">📈 时间线</div>';
      nav.innerHTML = html;
    }
    
    // 先渲染 fallback 导航，再加载 API 覆盖
    _renderNav();
    loadNavFromAPI();
    // 构建完成后恢复当前视图的激活状态
    switchView(currentView);
  } catch(e) {
    // 保底：即使 API 失败也加载生产列表
    loadProductions();
  }
}

// ── Matrix 养号矩阵汇总（inline 视图）──
async function loadMatrixSummary() {
  const el = document.getElementById('matrixSummaryContent');
  const meta = document.getElementById('matrixSummaryMeta');
  el.innerHTML = '<div class="loading">加载矩阵状态...</div>';
  try {
    const r = await fetch('/api/matrix/cross-machines');
    const d = await r.json();
    meta.textContent = `${d.total_machines} 机器 · ${d.total_accounts} 账号`;

    // 获取身份目录统计
    let identityCount = 0;
    try {
      const ir = await fetch('/api/matrix/system-info');
      const id = await ir.json();
      identityCount = id.identity_dirs || 0;
    } catch(e) {}
    meta.textContent += ` · 🪪 ${identityCount} 身份目录`;

    // 检测重复：同一账号出现在不同机器
    const allIds = {};
    const duplicates = [];
    d.machines.forEach(m => {
      (m.accounts||[]).forEach(a => {
        if (allIds[a.id] && allIds[a.id] !== m.hostname) {
          duplicates.push({id: a.id, m1: allIds[a.id], m2: m.hostname});
        }
        allIds[a.id] = m.hostname;
      });
    });

    let html = '';

    // 重复告警
    if (duplicates.length) {
      html += `<div style="padding:12px;background:rgba(239,68,68,.12);border-radius:8px;border:1px solid rgba(239,68,68,.25);margin-bottom:16px">
        <div style="font-weight:600;color:var(--red);margin-bottom:6px">🚨 账号重复分配检测</div>
        ${duplicates.map(dp => `<div style="font-size:13px;margin:2px 0">⚠️ <strong>${dp.id}</strong> 同时分配给 <strong>${dp.m1}</strong> 和 <strong>${dp.m2}</strong></div>`).join('')}
        <div style="font-size:11px;color:var(--text2);margin-top:4px">请编辑 accounts_registry.yaml 修正 assign_machine</div>
      </div>`;
    }

    // 每机器一张卡片
    html += `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:14px">`;
    d.machines.forEach(m => {
      const localTag = m.hostname === d.source_hostname ? '<span style="font-size:10px;color:var(--green);margin-left:6px">(本机)</span>' : '';
      html += `<div style="background:var(--bg2);border-radius:var(--radius);padding:16px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
          <div><span style="font-weight:600;font-size:14px">🖥 ${m.hostname}</span>${localTag}</div>
          <div style="display:flex;gap:6px;font-size:11px">
            <span class="badge badge-blue">共${m.total}</span>
            <span class="badge badge-green">🟢${m.logged_in}</span>
            <span class="badge badge-gray">⏸${m.total-m.logged_in-m.remote}</span>
            ${m.remote ? `<span class="badge badge-amber">📡${m.remote}</span>` : ''}
          </div>
        </div>
        <table style="font-size:12px;margin:0"><thead><tr>
          <th>账号</th><th>平台</th><th>状态</th><th>归属</th>
        </tr></thead><tbody>${(m.accounts||[]).map(a => {
          const s = a.status === 'logged_in' ? '🟢' : a.status === 'disabled' ? '⏸' : a.enabled ? '🔴' : '⏸';
          const isRemote = a.owner_machine && a.owner_machine !== m.hostname && a.status !== 'remote' ? `📡${a.owner_machine}` : a.status === 'remote' ? `📡${a.owner_machine||'?'}` : '✅';
          return `<tr><td><strong>${a.id}</strong></td>
            <td>${a.platform==='douyin'?'🎵':'📕'} ${a.platform}</td>
            <td>${s} ${a.status}</td>
            <td style="font-size:11px;color:var(--text2)">${isRemote}</td></tr>`;
        }).join('')}</tbody></table>
      </div>`;
    });
    html += `</div>`;

    // 蓝图简表
    try {
      const br = await fetch('/api/matrix/blueprints');
      const bd = await br.json();
      const bps = bd.blueprints || [];
      html += `<div style="margin-top:16px;background:var(--bg2);border-radius:var(--radius);padding:16px;border:1px solid var(--border)">
        <div style="font-weight:600;margin-bottom:10px">📋 蓝图 (${bps.length})</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px">${bps.map(b => 
          `<span style="background:var(--bg3);padding:4px 10px;border-radius:4px;font-size:12px">${b.name} <span class="badge badge-blue" style="font-size:9px">${b.step_count}步</span></span>`
        ).join('')}</div>
      </div>`;
    } catch(e) {}

    html += `<div style="margin-top:12px;text-align:right;font-size:11px;color:var(--text2)">
      <a href="/matrix-mgmt" target="_blank" style="color:var(--blue)">📱 打开完整管理页面 →</a>
    </div>`;

    el.innerHTML = html;
  } catch(e) {
    el.innerHTML = `<div class="error">❌ ${e.message}</div>`;
  }
}

// ════════════════════════════════════════════════════════
// Matrix Sub-Views (inline, no new tab)
// ════════════════════════════════════════════════════════

let _accountsData = [];
let _accountsSort = {col:'id', asc:true};

// ════════════════════════════════════════════════════════
// Batch Execution View
// ════════════════════════════════════════════════════════

async function loadMatrixRun() {
  const el = document.getElementById('matrixRunContent');
  const meta = document.getElementById('batchRunMeta');
  if (!el) return;
  el.innerHTML = '<div class="loading">加载中...</div>';

  try {
    // Load accounts + blueprints + corpus in parallel
    const [ar, br, cr] = await Promise.all([
      fetch('/api/matrix/accounts'),
      fetch('/api/matrix/blueprints'),
      fetch('/api/matrix/corpus'),
    ]);
    const ad = await ar.json();
    const bd = await br.json();
    const cd = await cr.json();

    const accounts = (ad.accounts || []).filter(a => a.is_local || a._status === 'logged_in');
    const blueprints = bd.blueprints || [];
    const corpusCats = cd.categories || [];

    meta.textContent = `${accounts.length} 可用账号 · ${blueprints.length} 蓝图`;

    let html = '';

    // ── 账号选择（按平台分组）──
    const douyinAccts = accounts.filter(a => a.platform === 'douyin');
    const xhsAccts = accounts.filter(a => a.platform === 'xiaohongshu');
    const platGroups = [['🎵 抖音', douyinAccts], ['📕 小红书', xhsAccts]].filter(g => g[1].length);

    html += `<div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:14px;margin-bottom:10px">
      <div style="font-weight:600;font-size:13px;margin-bottom:8px">👥 选择账号</div>${
        platGroups.map(([label, list]) =>
          `<div style="font-size:11px;color:var(--text2);margin:4px 0 2px">${label}</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px" class="batchAcctGroup">${
            list.map((a, idx) => {
              const s = a._status === 'logged_in' ? '🟢' : '⏸';
              const phone = String(a.phone || a.phone_mask || '??').slice(0, 11);
              return `<label style="background:var(--bg3);padding:5px 10px;border-radius:5px;border:1px solid var(--border);cursor:pointer;font-size:12px;white-space:nowrap">
                <input type="checkbox" class="batch-acct" value="${a.id}" data-platform="${a.platform}">
                ${s} <strong>${a.id}</strong> <span style="color:var(--text2);font-size:10px">${phone}</span>
              </label>`;
            }).join('')
          }</div>`
        ).join('')
      }</div>`;
    // 旧 forEach 已替换为上方 map 渲染

    // ── 蓝图选择（带平台过滤） ──
    html += `<div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:14px;margin-bottom:10px">
      <div style="font-weight:600;font-size:13px;margin-bottom:8px">📋 选择蓝图 <span style="font-size:11px;color:var(--text2)">（自动根据所选账号过滤平台）</span></div>
      <div style="display:flex;flex-wrap:wrap;gap:6px" id="batchBpList"></div>
      <div style="font-size:11px;color:var(--text2);margin-top:4px" id="bpFilterHint">加载中...</div>
    </div>`;

    // ── 蓝图过滤逻辑（账号选择变化时自动过滤） ──
    window._allBlueprints = blueprints;
    const allBlueprints = blueprints;
    // 蓝图列表渲染（不过滤，显示全部，平台匹配在预览时检查）
    function renderBlueprints() {
      const list = document.getElementById('batchBpList');
      const hint = document.getElementById('bpFilterHint');
      if (!list) return;
      const prevChecked = new Set([...document.querySelectorAll('.batch-bp:checked')].map(e => e.value));
      list.innerHTML = allBlueprints.map(b => {
        const checked = prevChecked.has(b.name) ? 'checked' : '';
        const platTag = b.platform ? (b.platform === 'douyin' ? '🎵' : '📕') : '❓';
        return '<label style="background:var(--bg3);padding:5px 10px;border-radius:5px;border:1px solid var(--border);cursor:pointer;font-size:12px">' +
          '<input type="checkbox" class="batch-bp" value="' + b.name + '" ' + checked + '> ' +
          b.name + ' <span class="badge badge-blue" style="font-size:9px">' + (b.step_count || '?') + '步</span> ' +
          '<span style="font-size:9px;color:var(--text2)">' + platTag + '</span></label>';
      }).join('');
      if (hint) hint.textContent = '✅ 显示全部 ' + allBlueprints.length + ' 个蓝图（平台匹配在执行时自动处理）';
    }

    // ── 参数表单 ──
    html += `<div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:14px;margin-bottom:10px">
      <div style="font-weight:600;font-size:13px;margin-bottom:8px">⚙️ 执行参数</div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px">
        <div><label style="font-size:11px;color:var(--text2)">轮数</label><input id="bpRounds" value="5" type="number" min="1" max="100" style="width:100%"></div>
        <div><label style="font-size:11px;color:var(--text2)">轮间隔(秒)</label><input id="bpInterval" value="30-60" style="width:100%"></div>
        <div><label style="font-size:11px;color:var(--text2)">账号间延迟(秒)</label><input id="bpStagger" value="15-30" style="width:100%"></div>
        <div><label style="font-size:11px;color:var(--text2)">模式</label>
          <div style="display:flex;align-items:center;gap:6px;padding-top:4px">
            <input type="checkbox" id="bpMix" checked> <label for="bpMix" style="font-size:12px">混合随机</label>
          </div>
        </div>
      </div>
      <div style="margin-top:8px">
        <label style="font-size:11px;color:var(--text2)">📚 语料分类</label>
        <div id="corpusPills" style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px">
        <label style="background:var(--bg3);padding:3px 8px;border-radius:4px;border:1px solid var(--border);cursor:pointer;font-size:11px">
          <input type="checkbox" id="bpCorpusRandom" onchange="corpusToggleRandom()"> 🎲 随机
        </label>`;
    corpusCats.forEach(c => {
      if (!c.enabled) return;
      html += `<label style="background:var(--bg3);padding:3px 8px;border-radius:4px;border:1px solid var(--border);cursor:pointer;font-size:11px" class="corpus-cat-label">
        <input type="checkbox" class="batch-corpus" value="${c.name}"> ${c.name}
      </label>`;
    });
    html += `</div></div>
      <div style="margin-top:8px">
        <label style="font-size:11px;color:var(--text2)">🌐 代理策略</label>
        <select id="bpProxy" style="width:150px"><option value="auto">auto</option><option value="none">不使用</option></select>
      </div>
    </div>`;

    // ── 命令预览 + 执行按钮 ──
    html += `<div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:14px;margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <span style="font-weight:600;font-size:13px">💻 命令预览</span>
        <div style="display:flex;gap:6px">
          <button class="btn btn-outline btn-sm" onclick="batchPreview()">🔄 更新预览</button>
          <button class="btn btn-primary btn-sm" onclick="batchExecute()">▶ 执行</button>
        </div>
      </div>
      <pre id="batchCmdPreview" style="background:var(--bg3);padding:10px;border-radius:6px;font-size:12px;font-family:monospace;overflow-x:auto;margin:0">mc run --accounts ...</pre>
    </div>`;

    // ── 执行结果 ──
    html += `<div id="batchOutput" style="display:none;background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:14px">
      <div style="font-weight:600;font-size:13px;margin-bottom:8px">📊 执行输出</div>
      <pre id="batchOutputContent" style="background:var(--bg3);padding:10px;border-radius:6px;font-size:11px;font-family:monospace;max-height:400px;overflow-y:auto;margin:0"></pre>
    </div>`;

    el.innerHTML = html;
    renderBlueprints();
    batchPreview();
  } catch(e) {
    el.innerHTML = `<div class="error">❌ ${e.message}</div>`;
  }
}

// Batch execution helpers
function corpusToggleRandom() {
  const isRandom = document.getElementById('bpCorpusRandom')?.checked;
  document.querySelectorAll('.corpus-cat-label input').forEach(cb => {
    cb.disabled = isRandom;
    cb.closest('label').style.opacity = isRandom ? '0.4' : '1';
  });
  batchPreview();
}

// 保存最后一次预览的选中值，供 batchExecute 使用
var _lastPreview = { accts: [], bps: [], rounds: 5, stagger: '15-30', mix: false, corpus: [], proxy: 'auto' };

function batchPreview() {
  try {
    const accts = [...document.querySelectorAll('.batch-acct:checked')].map(e => e.value);
    const bps = [...document.querySelectorAll('.batch-bp:checked')].map(e => e.value);
    const rounds = document.getElementById('bpRounds')?.value || '5';
    const interval = document.getElementById('bpInterval')?.value || '30-60';
    const stagger = document.getElementById('bpStagger')?.value || '15-30';
    const mix = document.getElementById('bpMix')?.checked;
    const isRandom = document.getElementById('bpCorpusRandom')?.checked;
    const corpus = isRandom ? ['random'] : [...document.querySelectorAll('.batch-corpus:checked')].map(e => e.value);
    const proxy = document.getElementById('bpProxy')?.value || 'auto';

    if (!accts.length) {
      document.getElementById('batchCmdPreview').textContent = '⚠️ 请先选择账号';
      return;
    }
    if (!bps.length) {
      document.getElementById('batchCmdPreview').textContent = '⚠️ 请选择至少一个蓝图';
      return;
    }

    // 平台一致性检查
    let warning = '';
    try {
      const platforms = new Set([...document.querySelectorAll('.batch-acct:checked')].map(e => e.getAttribute('data-platform')));
      const allBps = window._allBlueprints || [];
      if (allBps.length > 0) {
        const bpPlatforms = new Set(
          [...document.querySelectorAll('.batch-bp:checked')]
            .map(e => { try { const b = allBps.find(x => x.name === e.value); return b ? b.platform : '?'; } catch(ex) { return '?'; } })
            .filter(p => p && p !== '?')
        );
        if (bpPlatforms.size === 1 && platforms.has('douyin') && bpPlatforms.has('xiaohongshu')) {
          warning = '\n⚠️ 注意：选择了抖音账号和小红书蓝图，平台不匹配！';
        } else if (bpPlatforms.size === 1 && platforms.has('xiaohongshu') && bpPlatforms.has('douyin')) {
          warning = '\n⚠️ 注意：选择了小红书账号和抖音蓝图，平台不匹配！';
        }
      }
    } catch(ex) { warning = '\n⚠️ 平台检查异常: ' + ex.message; }

    let cmd = `mc run --accounts ${accts.join(',')}`;
    cmd += ` --blueprints ${bps.join(',')}`;
    cmd += ` --rounds ${rounds}`;
    cmd += ` --interval ${interval}`;
    cmd += ` --stagger ${stagger}`;
    if (mix) cmd += ' --mix';
    if (corpus.length) cmd += ` --corpus ${corpus.join(',')}`;
    cmd += ` --proxy ${proxy}`;
    cmd += ` --keep`;

    // 保存到全局，供 batchExecute 使用
    _lastPreview.accts = accts;
    _lastPreview.bps = bps;
    _lastPreview.rounds = rounds;
    _lastPreview.interval = interval;
    _lastPreview.stagger = stagger;
    _lastPreview.mix = mix;
    _lastPreview.corpus = corpus;
    _lastPreview.proxy = proxy;
    document.getElementById('batchCmdPreview').textContent = cmd + warning;
  } catch(e) {
    document.getElementById('batchCmdPreview').textContent = '❌ 预览出错: ' + e.message;
  }
}

async function batchExecute() {
  // 使用 _lastPreview 中保存的值（不重新查询 DOM）
  const accts = _lastPreview.accts;
  const bps = _lastPreview.bps;
  const output = document.getElementById('batchOutput');
  const content = document.getElementById('batchOutputContent');
  if (!output || !content) return;
  if (!accts.length || !bps.length) {
    content.textContent = '❌ 请先在预览中确认账号和蓝图已选择';
    output.style.display = 'block';
    return;
  }

  output.style.display = 'block';
  content.textContent = '⏳ 执行中...\n';
  const rounds = _lastPreview.rounds;
  const interval = _lastPreview.interval;
  const stagger = _lastPreview.stagger;
  const mix = _lastPreview.mix;

  try {
    const r = await fetch('/api/matrix/batch-run', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({accounts: accts, blueprints: bps, rounds, interval, stagger, mix})
    });
    const d = await r.json();
    if (d.status === 'started') {
      content.textContent = `✅ 已启动 (PID: ${d.pid})\n\n命令:\n  ${d.cmd}\n\n查看执行日志:\n  tail -f /tmp/mc_run.log`;
    } else {
      content.textContent = `❌ 启动失败\n${JSON.stringify(d, null, 2)}`;
    }
  } catch(e) {
    content.textContent = `❌ ${e.message}`;
  }
}

// 已合并到下方 loadMatrixAccounts2
async function loadIdentities() {
  const el = document.getElementById('matrixIdentityContent');
  if (!el) return;
  try {
    const r = await fetch('/api/matrix/identities');
    const d = await r.json();
    const identities = d.identities || [];
    if (!identities.length) { el.innerHTML = '<div style="color:var(--text2);font-size:13px;padding:20px;text-align:center">暂无本地身份</div>'; return; }
    el.innerHTML = identities.map(id => {
      const idName = id.identity_dir;
      const phone = id.phone || '未知';
      const cookieStatus = id.has_cookie ? '🍪 已就绪' : '❌ 无Cookie';
      return `<div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border);margin-bottom:10px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <div><span style="font-size:14px">📱</span> <strong style="font-size:14px">${phone}</strong>
            <span style="color:var(--text2);font-size:11px;margin-left:6px">${idName}</span>
            <span style="font-size:11px;margin-left:6px;color:${id.has_cookie?'#22c55e':'#ef4444'}">${cookieStatus}</span>
          </div>
          <button onclick="deleteIdentity('${idName}')" style="background:#ef4444;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🗑 删除身份</button>
        </div>
        <div style="margin-top:6px">
          ${id.accounts.map(a => `<div style="display:flex;align-items:center;gap:6px;padding:4px 6px;background:var(--bg3);border-radius:4px;margin-bottom:3px;font-size:12px">
            <span style="color:${a.status==='logged_in'?'#22c55e':'#8b8fa3'}">${a.status==='logged_in'?'✅':'⏸'}</span>
            <span style="font-weight:600;width:100px">${a.id}</span>
            <span style="color:var(--text2);width:70px;font-size:11px">${a.platform}</span>
            <span style="font-size:11px;color:${a.status==='logged_in'?'#22c55e':'#f59e0b'}">${a.status}</span>
            <span style="flex:1"></span>
            ${id.accounts.length > 1 ? `<button onclick="unbindAccount('${a.id}')" style="background:transparent;color:var(--amber);border:1px solid var(--border);padding:2px 8px;border-radius:3px;cursor:pointer;font-size:10px">解绑</button>` : ''}
          </div>`).join('')}
        </div>
      </div>`;
    }).join('');
  } catch(e) { if (el) el.innerHTML = '<span style="color:var(--red)">'+e.message+'</span>'; }
}

async function loadMatrixAccounts() {
  const el = document.getElementById('matrixAccountsContent');
  if (!el) return;
  el.innerHTML = '<div class="loading">加载中...</div>';
  try {
    let machinesInfo = '';
    try {
      const mr = await fetch('/api/matrix/cross-machines');
      const md = await mr.json();
      if (md.total_machines) {
        machinesInfo = '<div style="display:flex;gap:12px;margin-bottom:12px;font-size:12px;color:var(--text2);background:var(--bg2);border-radius:var(--radius);padding:8px 12px;border:1px solid var(--border)">'+
          '<span>🖥️ 机器: <strong>'+md.total_machines+'</strong></span>'+
          '<span>👤 账号: <strong>'+md.total_accounts+'</strong></span>'+
          '<span>📡 在线: <strong style="color:var(--green)">'+md.online_machines+'</strong></span>'+
        '</div>';
      }
    } catch(e) { /* ignore */ }
    const r = await fetch('/api/matrix/accounts');
    const d = await r.json();
    _accountsData = Array.isArray(d) ? d : (d.accounts || []);
    if (!_accountsData.length) { el.innerHTML = machinesInfo+'<div class="error">暂无账号</div>'; return; }
    el.innerHTML = machinesInfo;
    renderAccountsTable();
  } catch(e) { el.innerHTML = '<span style="color:var(--red)">'+e.message+'</span>'; }
}

function acctSwitchTab(tab, el) {
  document.querySelectorAll('.acct-tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');
  document.getElementById('acct-tab-list').style.display = tab === 'list' ? 'block' : 'none';
  document.getElementById('acct-tab-identity').style.display = tab === 'identity' ? 'block' : 'none';
  if (tab === 'identity') loadIdentities();
}

async function deleteIdentity(identityDir) {
  const accts = document.querySelector('#acct-tab-identity .loading');
  const msg = '⚠️ 确定要删除此身份吗？\\n\\n将删除以下内容:';
  if (!confirm(msg + '\\n- 身份目录: ' + identityDir)) return;
  try {
    const r = await fetch('/api/matrix/identities/' + encodeURIComponent(identityDir), {method:'DELETE'});
    const res = await r.json();
    if (res.status === 'ok') {
      alert('✅ 已删除身份: ' + identityDir + '\\n移除账号: ' + (res.removed_accounts||[]).join(', '));
      loadIdentities();
    } else alert('❌ ' + (res.detail||res.error));
  } catch(e) { alert('❌ '+e.message); }
}

async function unbindAccount(accountId) {
  if (!confirm('⚠️ 解除 ' + accountId + ' 的绑定？\\nCookie 将保留，以后可重新绑定。')) return;
  try {
    const r = await fetch('/api/matrix/accounts/' + encodeURIComponent(accountId) + '/unbind', {method:'POST'});
    const res = await r.json();
    if (res.status === 'ok') {
      alert('✅ ' + accountId + ' 已解绑');
      loadIdentities();
    } else alert('❌ ' + (res.detail||res.error));
  } catch(e) { alert('❌ '+e.message); }
}

function sortAccounts(col) {
  if (_accountsSort.col === col) _accountsSort.asc = !_accountsSort.asc;
  else { _accountsSort.col = col; _accountsSort.asc = true; }
  renderAccountsTable();
}

function renderAccountsTable() {
  const el = document.getElementById('matrixAccountsContent');
  const sorted = [..._accountsData].sort((a, b) => {
    let va = '', vb = '';
    const c = _accountsSort.col;
    if (c === 'id') { va = a.id; vb = b.id; }
    else if (c === 'platform') { va = a.platform||''; vb = b.platform||''; }
    else if (c === 'phone') { va = String(a.phone||a.phone_mask||''); vb = String(b.phone||b.phone_mask||''); }
    else if (c === 'machine') { va = a.is_local ? '本机' : (a.owner_machine||'远程'); vb = b.is_local ? '本机' : (b.owner_machine||'远程'); }
    else if (c === 'status') { va = a._status||''; vb = b._status||''; }
    else if (c === 'display_name') { va = a.display_name||''; vb = b.display_name||''; }
    else if (c === 'identity_dir') { va = a.identity_dir||''; vb = b.identity_dir||''; }
    return _accountsSort.asc ? va.localeCompare(vb) : vb.localeCompare(va);
  });
  const arrow = (col) => _accountsSort.col === col ? (_accountsSort.asc ? ' ▲' : ' ▼') : '';
  const th = (col, label) => `<th style="cursor:pointer;user-select:none" onclick="sortAccounts('${col}')">${label}${arrow(col)}</th>`;

  el.innerHTML = `<table><thead><tr>
    ${th('id','ID')}${th('platform','平台')}${th('phone','手机')}${th('machine','归属机器')}${th('status','状态')}${th('display_name','昵称')}
    ${th('identity_dir','身份目录')}<th>备注</th><th>操作</th>
  </tr></thead><tbody>${sorted.map(a => {
    const s = a._status === 'logged_in' ? '<span class="badge badge-green" style="background:rgba(5,150,105,.1);color:var(--green);padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">✅ 已登录</span>'
      : a._status === 'remote' ? '<span class="badge badge-gray" style="background:rgba(107,114,128,.1);color:var(--text2);padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">📡 远程</span>'
      : a._status === 'disabled' ? '<span class="badge badge-gray" style="background:rgba(107,114,128,.1);color:var(--text2);padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">⏸ 停用</span>'
      : `<span class="badge badge-amber" style="background:rgba(217,119,6,.1);color:var(--amber);padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">⚠️ ${a._status}</span>`;
    const platformIcon = a.platform === 'douyin' ? '🎵' : (a.platform === 'xiaohongshu' ? '📕' : '🌐');
    const machineLabel = a.is_local
      ? '<span style="color:#6366f1;font-size:12px">💻 本机</span>'
      : '<span style="color:var(--text2);font-size:12px">📡 '+(a.owner_machine||'远程')+'</span>';
    return `<tr>
      <td><strong>${a.id}</strong></td>
      <td>${platformIcon} ${a.platform}</td>
      <td style="font-family:monospace;font-size:12px">${String(a.phone||a.phone_mask||'-').slice(0,11)}</td>
      <td>${machineLabel}</td>
      <td>${s}</td>
      <td style="font-size:12px;color:var(--text2);max-width:120px;overflow:hidden;text-overflow:ellipsis">${a.display_name || '-'}</td>
      <td style="font-size:11px;color:var(--text2)">${a.identity_dir ? a.identity_dir.split('/').pop() : '-'}</td>
      <td style="font-size:11px;max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
        <span class="notes-display" data-account="${a.id}">${(a.notes||'-').slice(0,10)}</span>
        <span class="notes-edit" style="display:none">
          <input class="notes-input" data-account="${a.id}" value="${a.notes||''}" style="width:70px;font-size:10px;padding:2px 4px;background:var(--bg2);border:1px solid var(--primary);border-radius:4px;color:var(--text)">
          <span style="cursor:pointer;color:var(--green);font-size:12px" onclick="saveNote('${a.id}')">✓</span>
        </span>
        <span style="cursor:pointer;color:var(--text2);font-size:10px;margin-left:2px" onclick="editNote('${a.id}')">✏️</span>
      </td>
      <td>${a.is_local
        ? `<button class="btn btn-sm" style="background:transparent;color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:6px;cursor:pointer;font-size:11px" onclick="alert('编辑: ${a.id}')">编辑</button>
           <button class="btn btn-sm" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:6px;cursor:pointer;font-size:11px;margin-left:4px" onclick="c2Nurture('${a.id}')">养号</button>`
        : '<span style="font-size:11px;color:var(--text2)">-</span>'}
      </td>
    </tr>`;
  }).join('')}</tbody></table>
  <div style="font-size:11px;color:var(--text2);margin-top:6px">共 ${_accountsData.length} 个账号 · 点击表头排序</div>`;
}

async function loadMatrixBlueprints() {
  const el = document.getElementById('matrixBlueprintsContent');
  el.innerHTML = '<div class="loading">加载中...</div>';
  // 加载蓝图列表 + 原子操作（用于编辑器）
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

    let html = '';

    // ── 可折叠蓝图列表 (默认折叠) ──
    html += `<div style="margin-bottom:10px;background:var(--bg2);border-radius:10px;border:1px solid var(--border);overflow:hidden">`;
    html += `<div onclick="bpToggleList()" style="padding:10px 14px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;user-select:none">
      <span style="font-weight:600;font-size:13px">📋 蓝图库 <span class="badge badge-blue" style="font-size:10px;background:rgba(37,99,235,.1);color:var(--blue);padding:2px 6px;border-radius:6px">${bps.length}</span></span>
      <span id="bp-list-arrow" style="color:var(--text2);font-size:12px">▶ 展开</span>
    </div>`;
    html += `<div id="bp-list-body" style="display:none;padding:0 14px 10px">`;
    if (!bps.length) {
      html += '<div style="padding:6px 0;color:var(--text2);font-size:13px">暂无蓝图</div>';
    } else {
      bps.forEach(b => {
        const stepsPreview = (b.steps||[]).slice(0,3).map(s => window._matrixOps?.[s.op||s.name]?.label||s.op||s.name||'').join(' → ');
        html += `<div style="display:flex;align-items:center;gap:8px;padding:8px 10px;border-bottom:1px solid var(--border);font-size:13px">
          <span style="flex:1"><strong>${b.name}</strong> <span style="color:var(--text2);font-size:11px">${b.step_count}步 · ${b.platform||'douyin'}</span>
            ${stepsPreview ? `<br><span style="color:var(--text2);font-size:11px">${stepsPreview}</span>` : ''}</span>
          <span style="display:flex;gap:4px;flex-shrink:0">
            <button class="btn btn-sm" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:6px;cursor:pointer;font-size:11px" onclick="event.stopPropagation();bpExecute('${b.name}')">▶ 执行</button>
            <button class="btn btn-sm" style="background:transparent;color:var(--text);border:1px solid var(--border);padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px" onclick="event.stopPropagation();showBpEditor('${b.name}')">✏️</button>
            <button class="btn btn-sm" style="background:transparent;color:var(--red);border:1px solid rgba(239,68,68,.3);padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px" onclick="event.stopPropagation();delBp('${b.name}')">🗑</button>
          </span>
        </div>`;
      });
    }
    html += `</div></div>`;

    // ── 编辑器主区域 (全宽) ──
    html += `<div style="background:var(--bg2);border-radius:var(--radius);padding:16px;border:1px solid var(--border)">`;
    html += `
      <div id="bp-editor">
        <div style="display:flex;gap:12px;align-items:end;flex-wrap:wrap;margin-bottom:12px">
          <div style="flex:2;min-width:200px">
            <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:2px">蓝图名称</label>
            <input id="bp-name" placeholder="my_blueprint" style="font-size:14px;font-weight:600">
          </div>
          <div style="flex:1;min-width:120px">
            <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:2px">平台</label>
            <select id="bp-platform" onchange="bpUpdatePlatform()" style="font-size:13px">
              <option value="douyin">🎵 抖音</option>
              <option value="xiaohongshu">📕 小红书</option>
            </select>
          </div>
          <div style="flex:2;min-width:150px">
            <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:2px">说明</label>
            <input id="bp-desc" placeholder="可选说明">
          </div>
          <div style="display:flex;gap:6px;flex-shrink:0">
            <button class="btn btn-primary" onclick="bpSave()" style="padding:7px 18px">💾 保存</button>
            <button class="btn btn-outline" onclick="bpClear()" style="padding:7px 14px">🗑 清空</button>
            <button class="btn btn-outline" onclick="showBpEditor(null)" style="padding:7px 14px">+ 新建</button>
          </div>
        </div>

        <div style="margin:14px 0 8px;display:flex;align-items:center;gap:8px">
          <span style="font-weight:600;font-size:13px;color:var(--text2);white-space:nowrap">⚡ 原子操作</span>
          <div style="display:flex;gap:3px;flex-wrap:wrap" id="bp-op-tabs">
            <span class="badge badge-blue" style="cursor:pointer;padding:3px 8px;font-size:10px" data-ft="all" onclick="bpFilterOps('all')">📋 全部</span>
            <span class="badge badge-gray" style="cursor:pointer;padding:3px 8px;font-size:10px" data-ft="navigation" onclick="bpFilterOps('navigation')">🏠 导航</span>
            <span class="badge badge-gray" style="cursor:pointer;padding:3px 8px;font-size:10px" data-ft="browse" onclick="bpFilterOps('browse')">📱 浏览</span>
            <span class="badge badge-gray" style="cursor:pointer;padding:3px 8px;font-size:10px" data-ft="interact" onclick="bpFilterOps('interact')">💡 交互</span>
            <span class="badge badge-gray" style="cursor:pointer;padding:3px 8px;font-size:10px" data-ft="utility" onclick="bpFilterOps('utility')">⏳ 工具</span>
          </div>
        </div>
        <div id="bp-op-list" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:5px;margin:0 0 16px"></div>

        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-weight:600;font-size:13px;color:var(--text2)">📋 编排步骤</span>
          <span id="bp-step-count" style="font-size:11px;color:var(--text2)">0 步</span>
          <span id="bp-validate" style="font-size:11px"></span>
        </div>
        <div id="bp-steps" style="min-height:80px;border:2px dashed var(--border);border-radius:8px;padding:10px">
          <div style="color:var(--text2);font-size:13px;text-align:center;padding:20px">👆 点击上方原子操作卡片添加到步骤，可无限向下编排</div>
        </div>
      </div>`;
    html += `</div>`;

    el.innerHTML = html;
    // 初始化编辑器状态
    window._bpSteps = [];
    window._editingBp = null;
    window._bpFilter = 'all';
    window._bpListOpen = false;
    bpUpdatePlatform();
  } catch(e) { el.innerHTML = `<div class="error">${e.message}</div>`; }
}

// Blueprint editor helper functions
window.bpToggleList = function() {
  window._bpListOpen = !window._bpListOpen;
  const body = document.getElementById('bp-list-body');
  const arrow = document.getElementById('bp-list-arrow');
  if (body && arrow) {
    body.style.display = window._bpListOpen ? 'block' : 'none';
    arrow.textContent = window._bpListOpen ? '▼ 收起' : '▶ 展开';
  }
};

window.bpAddStep = function(name) {
  const op = window._matrixOps?.[name];
  if (!op) return;
  window._bpSteps = window._bpSteps || [];
  window._bpSteps.push({name, label: op.label||name, requires: op.requires||[], allows: op.allows||[]});
  bpRenderSteps();
};

window.bpRemoveStep = function(idx) {
  window._bpSteps = window._bpSteps || [];
  window._bpSteps.splice(idx, 1);
  bpRenderSteps();
};

function bpRenderSteps() {
  const el = document.getElementById('bp-steps');
  const ve = document.getElementById('bp-validate');
  const sc = document.getElementById('bp-step-count');
  const steps = window._bpSteps || [];
  if (!el) return;
  if (sc) sc.textContent = `${steps.length} 步`;
  if (!steps.length) {
    el.innerHTML = '<div style="color:var(--text2);font-size:13px;text-align:center;padding:20px">👆 点击上方原子操作卡片添加到步骤，可无限向下编排</div>';
    if (ve) ve.innerHTML = '';
    return;
  }
  el.innerHTML = steps.map((s, i) => {
    // 检查与前一步的依赖
    let warn = '';
    if (i > 0) {
      const prev = steps[i-1];
      const prevOp = window._matrixOps?.[prev.name];
      if (prevOp && prevOp.allows && prevOp.allows[0] !== '*' && !prevOp.allows.includes(s.name)) {
        warn = '<span style="color:var(--red);font-size:11px;margin-left:6px">⚠ 与前一步不兼容</span>';
      }
    }
    if (i === 0) {
      const op = window._matrixOps?.[s.name];
      if (op && !op.can_be_first) {
        warn = '<span style="color:var(--red);font-size:11px;margin-left:6px">⚠ 不能作为首步</span>';
      } else if (op && op.can_be_first) {
        warn = '<span style="color:var(--green);font-size:11px;margin-left:6px">✅ 起点</span>';
      }
    }
    // 箭头
    const arrow = i < steps.length - 1
      ? '<div style="padding:2px 0 2px 32px;color:var(--text2);font-size:14px">↓</div>'
      : '';
    // 序号圆
    const numStyle = warn.includes('不兼容') || warn.includes('不能作为首步')
      ? 'background:var(--red);color:#fff'
      : 'background:var(--primary);color:#fff';
    // 兜底：保证 label 是字符串（防止 [object Object]）
    var label = s.label;
    if (typeof label !== 'string') {
      var op2 = window._matrixOps?.[s.name];
      label = op2?.label || s.name || '(未知)';
    }
    return `<div style="padding:2px 0">
      <div style="display:flex;align-items:center;gap:8px;padding:6px 10px;background:var(--bg3);border-radius:6px;border:1px solid var(--border)">
        <span style="width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0;${numStyle}">${i+1}</span>
        <span style="flex:1;font-size:13px"><strong>${label}</strong> ${warn}</span>
        <span style="cursor:pointer;color:var(--red);font-size:16px;opacity:.5" onclick="bpRemoveStep(${i})">✕</span>
      </div>
      ${arrow}
    </div>`;
  }).join('');

  // 验证
  if (ve) {
    fetch('/api/matrix/blueprints/validate', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({steps: steps.map(s => ({name: s.name}))})
    }).then(r=>r.json()).then(res => {
      ve.innerHTML = res.valid
        ? '<span style="color:var(--green);font-size:12px">✅ 编排合法</span>'
        : '<span style="color:var(--red);font-size:12px">❌ '+(res.errors||[]).map(e=>e.msg).join('; ')+'</span>';
    }).catch(() => {});
  }
}

window.bpSave = async function() {
  const name = document.getElementById('bp-name')?.value;
  if (!name) { alert('请输入蓝图名称'); return; }
  const steps = (window._bpSteps||[]).map(s => ({name: s.name, description: (window._matrixOps?.[s.name]?.desc)||''}));
  if (!steps.length) { alert('请添加至少一个步骤'); return; }
  try {
    const r = await fetch('/api/matrix/blueprints', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({name, description: document.getElementById('bp-desc')?.value||'', platform: document.getElementById('bp-platform')?.value||'douyin', steps})
    });
    if (!r.ok) throw new Error((await r.json()).detail);
    bpClear();
    loadMatrixBlueprints();
  } catch(e) { alert('❌ '+e.message); }
};

window.bpClear = function() {
  window._bpSteps = [];
  const ne = document.getElementById('bp-name');
  if (ne) ne.value = '';
  window._editingBp = null;
  bpRenderSteps();
};

// Atomic op filter & render for blueprint editor
window._bpFilter = 'all';

// Platform → available categories mapping
// Platform → available categories mapping (for tab visibility)
const BP_PLATFORM_CATEGORIES = {
  douyin: ['navigation', 'browse', 'interact', 'utility'],
  xiaohongshu: ['navigation', 'browse', 'interact', 'utility'],
};

const BP_CATEGORY_TABS = {
  all: '📋 全部',
  navigation: '🏠 导航',
  browse: '📱 浏览',
  interact: '💡 交互',
  utility: '⏳ 工具',
};

window.bpFilterOps = function(filter) {
  window._bpFilter = filter;
  // Update tab styles
  document.querySelectorAll('#bp-op-tabs span').forEach(t => {
    if (t.style.display === 'none') return;
    t.className = t.dataset.ft === filter ? 'badge badge-blue' : 'badge badge-gray';
    t.style.cssText = 'cursor:pointer;padding:3px 8px;font-size:10px';
  });
  bpRenderOps();
};

function bpGetPlatform() {
  const sel = document.getElementById('bp-platform');
  return sel ? sel.value : 'douyin';
}

function bpUpdatePlatform() {
  // Get allowed categories for this platform
  const platform = bpGetPlatform();
  const cats = BP_PLATFORM_CATEGORIES[platform] || ['navigation', 'browse', 'interact', 'utility'];

  // Update filter tab visibility
  document.querySelectorAll('#bp-op-tabs span').forEach(t => {
    const ft = t.dataset.ft;
    // "all" always visible, others only if in this platform's categories
    const visible = ft === 'all' || cats.includes(ft);
    t.style.display = visible ? 'inline-block' : 'none';
  });

  // If current filter is not available for this platform, reset to 'all'
  if (window._bpFilter !== 'all' && !cats.includes(window._bpFilter)) {
    window._bpFilter = 'all';
  }

  bpRenderOps();

  // Save the platform choice to registry for future (optional)
}

function bpCanFollow(lastStepName, opName) {
  // If no steps yet: only ops that can_be_first or have no requires
  if (!lastStepName) {
    const op = window._matrixOps?.[opName];
    return op ? !!op.can_be_first : true;
  }
  // Check the last step's allows list
  const lastOp = window._matrixOps?.[lastStepName];
  if (!lastOp) return true;
  if (lastOp.allows && lastOp.allows[0] === '*') return true;
  return lastOp.allows ? lastOp.allows.includes(opName) : true;
}

function bpRenderOps() {
  const el = document.getElementById('bp-op-list');
  if (!el) return;

  const allOps = Object.values(window._matrixOps || {});
  const platform = bpGetPlatform();
  const filter = window._bpFilter || 'all';

  const steps = window._bpSteps || [];
  const lastStep = steps.length > 0 ? steps[steps.length - 1] : null;
  const lastName = lastStep ? lastStep.name : null;

  // Filter by: platform field matches OR is "通用"
  const platformOps = allOps.filter(o => {
    const opPlatform = o.platform || '通用';
    return opPlatform === platform || opPlatform === '通用';
  });

  // Then apply category filter
  const filtered = filter === 'all' ? platformOps : platformOps.filter(o => (o.category || '') === filter);

  el.innerHTML = filtered.map(o => {
    const canFollow = bpCanFollow(lastName, o.name);
    let deps = '';
    if (o.requires && o.requires.length && o.requires[0] !== '*') {
      deps = `<span style="font-size:9px;color:var(--blue)">← ${o.requires.join(',')}</span>`;
    } else if (o.can_be_first && !lastName) {
      deps = `<span style="font-size:9px;color:var(--green)">✅ 首步</span>`;
    }
    const opacity = canFollow ? '1' : '.35';
    const cursor = canFollow ? 'pointer' : 'not-allowed';
    const clickHandler = canFollow ? `bpAddStep('${o.name}')` : '';
    const disabledLabel = canFollow ? '' : '<span style="font-size:9px;color:var(--red);margin-left:4px">🚫</span>';
    return `<div class="op-card" style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);cursor:${cursor};opacity:${opacity}" onclick="${clickHandler}">
      <div style="font-size:12px;font-weight:600">${o.label||o.name}${disabledLabel}</div>
      <div style="font-size:10px;color:var(--text2);margin-top:2px">${o.desc||''}</div>
      <div style="margin-top:2px">${deps}</div>
    </div>`;
  }).join('');
  if (!filtered.length) {
    el.innerHTML = '<div style="color:var(--text2);font-size:12px;padding:10px;grid-column:1/-1">当前平台/分类无可用操作</div>';
  }
}

window.showBpEditor = async function(name) {
  if (!name) { bpClear(); return; }
  try {
    const r = await fetch('/api/matrix/blueprints');
    const d = await r.json();
    const bp = Array.isArray(d) ? d.find(b => b.name === name) : (d.blueprints||[]).find(b => b.name === name);
    if (!bp) return;
    window._editingBp = name;
    document.getElementById('bp-name').value = name;
    document.getElementById('bp-desc').value = bp.description||'';
    document.getElementById('bp-platform').value = bp.platform||'douyin';
    window._bpSteps = (bp.steps||[]).map(s => {
      const stepName = s.op || s.name || s;
      const op = window._matrixOps?.[stepName];
      return {name: stepName, label: op?.label||stepName, requires: op?.requires||[], allows: op?.allows||[]};
    });
    bpRenderSteps();
  } catch(e) { alert('❌ '+e.message); }
};

window.delBp = async function(name) {
  if (!confirm(`删除蓝图 ${name}?`)) return;
  try {
    const r = await fetch(`/api/matrix/blueprints/${name}`, {method:'DELETE'});
    if (!r.ok) throw new Error((await r.json()).detail);
    loadMatrixBlueprints();
  } catch(e) { alert('❌ '+e.message); }
};

// Blueprint execute modal
function bpExecute(name) {
  // 存到 DOM 上而不是全局变量（避免 Vite 编译后的变量切分问题）
  const modal = document.getElementById('bpExecModal');
  if (modal) modal.dataset.bpName = name;
  fetch('/api/matrix/accounts').then(r=>r.json()).then(d => {
    const accts = (d.accounts||[]).filter(a => a.is_local && a._status === 'logged_in');
    const modal = document.getElementById('bpExecModal');
    const content = document.getElementById('bpExecContent');
    if (!modal || !content) return;
    content.innerHTML = `
      <div style="margin-bottom:12px"><strong style="font-size:15px">▶ 执行蓝图: ${name}</strong></div>
      <div style="margin-bottom:10px">
        <label style="display:block;font-size:12px;color:var(--text2);margin-bottom:4px">选择身份</label>
        <select id="bpExecIdentity" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:8px 10px;border-radius:6px;font-size:13px">
          ${accts.map(a => `<option value="${a.id}">${a.id} (${a.platform})</option>`).join('')}
          ${accts.length ? '' : '<option value="">暂无已登录账号</option>'}
        </select>
      </div>
      <div style="margin-bottom:10px">
        <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text2);cursor:pointer">
          <input type="checkbox" id="bpExecProxy" checked> 使用代理
        </label>
      </div>
      <div style="display:flex;gap:8px">
        <button onclick="bpDoExec()" style="background:#6366f1;color:#fff;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;font-size:13px">▶ 执行</button>
        <button onclick="closeBpModal()" style="background:transparent;color:var(--text);border:1px solid var(--border);padding:8px 20px;border-radius:6px;cursor:pointer;font-size:13px">取消</button>
      </div>
      <div id="bpExecResult" style="margin-top:10px;font-size:13px"></div>`;
    modal.style.display = 'flex';
  }).catch(e => alert('❌ '+e.message));
}

async function bpDoExec() {
  const sel = document.getElementById('bpExecIdentity');
  const proxy = document.getElementById('bpExecProxy')?.checked;
  const resultEl = document.getElementById('bpExecResult');
  const modal = document.getElementById('bpExecModal');
  const bpName = modal ? (modal.dataset.bpName || '') : '';
  if (!sel || !sel.value) { resultEl.innerHTML = '<span style="color:var(--red)">请选择身份</span>'; return; }
  if (!bpName) { resultEl.innerHTML = '<span style="color:var(--red)">❌ 蓝图名称未设置</span>'; return; }
  resultEl.innerHTML = '<span style="color:var(--text2)">⏳ 执行中...</span>';
  try {
    const r = await fetch('/api/matrix/blueprints/'+encodeURIComponent(bpName)+'/execute', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({account: sel.value, use_proxy: proxy})
    });
    const res = await r.json();
    resultEl.innerHTML = r.ok
      ? '<span style="color:var(--green)">✅ 已启动 · 日志: '+(res.log||'N/A')+'</span>'
      : '<span style="color:var(--red)">❌ '+(res.detail||'执行失败')+'</span>';
  } catch(e) {
    resultEl.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>';
  }
}

function closeBpModal() {
  const modal = document.getElementById('bpExecModal');
  if (modal) modal.style.display = 'none';
}

// ════════════════════════════════════════════════════════
// Registration Form
// ════════════════════════════════════════════════════════
// [旧登记注册函数已移除，注册功能合并到 SMS 页面]

async function loadMatrixAtomOps() {
  const el = document.getElementById('matrixAtomOpsContent');
  el.innerHTML = '<div class="loading">加载中...</div>';
  try {
    const r = await fetch('/api/matrix/atom-ops');
    const d = await r.json();
    const ops = d.ops || [];
    document.getElementById('matrixAtomOpCount').textContent = `共 ${ops.length} 个操作`;
    if (!ops.length) { el.innerHTML = '<div class="error">暂无操作</div>'; return; }
    const groups = {};
    ops.forEach(o => {
      const p = o.platform || '通用';
      if(!groups[p]) groups[p]=[];
      groups[p].push(o);
    });
    const platformLabels = {douyin:'🎵 抖音', xiaohongshu:'📕 小红书', '通用':'⚙️ 通用'};
    el.innerHTML = Object.entries(groups).map(([p, items]) => {
      const subGroups = {};
      items.forEach(o => {
        const g = o.category||'其他';
        if(!subGroups[g]) subGroups[g]=[];
        subGroups[g].push(o);
      });
      const catLabels = {navigation:'🏠 导航', browse:'📱 浏览', interact:'💡 交互', utility:'⏳ 工具'};
      return `<div style="margin-bottom:16px">
        <div style="font-size:14px;font-weight:700;margin-bottom:10px;padding:6px 10px;border-radius:6px;background:var(--bg3)">${platformLabels[p]||p} <span style="font-weight:400;font-size:11px;color:var(--text2)">(${items.length})</span></div>
        ${Object.entries(subGroups).map(([g, sub]) => `
          <div style="font-size:12px;font-weight:600;margin:8px 0 6px;color:var(--text2)">${catLabels[g]||g} (${sub.length})</div>
          <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:6px;margin-bottom:6px">${sub.map(o => {
            let reqHtml = '';
            if (o.requires && o.requires.length && o.requires[0] !== '*') {
              reqHtml = '<span style="display:inline-block;font-size:10px;padding:2px 6px;border-radius:4px;background:rgba(37,99,235,.1);color:var(--blue);margin-top:4px">← 需前序: '+o.requires.slice(0,3).join(',')+(o.requires.length>3?'…':'')+'</span>';
            } else if (o.can_be_first) {
              reqHtml = '<span style="display:inline-block;font-size:10px;padding:2px 6px;border-radius:4px;background:rgba(5,150,105,.1);color:var(--green);margin-top:4px">✅ 可为首步</span>';
            }
            let nextHtml = '';
            if (o.allows && o.allows.length && o.allows[0] !== '*') {
              nextHtml = '<span style="display:inline-block;font-size:10px;padding:2px 6px;border-radius:4px;background:rgba(107,114,128,.1);color:var(--text2);margin-top:2px">→ 后继: '+o.allows.slice(0,4).join(',')+(o.allows.length>4?'…':'')+'</span>';
            }
            const pt = o.platform==='通用'?'⚙️通用':(o.platform==='douyin'?'🎵抖音':'📕小红书');
            return '<div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border)">'
              +'<div style="display:flex;align-items:center;gap:4px;margin-bottom:2px">'
              +'<span style="font-size:9px;font-weight:600;padding:1px 5px;border-radius:3px;background:rgba(99,102,241,.15);color:#818cf8">'+pt+'</span>'
              +'<span style="font-size:12px;font-weight:600">'+(o.label||o.name)+'</span></div>'
              +'<div style="font-size:10px;color:var(--text2);margin-top:1px">'+(o.desc||o.doc||'')+'</div>'
              +'<div style="margin-top:3px;display:flex;flex-wrap:wrap;gap:2px">'+reqHtml+nextHtml+'</div></div>';
          }).join('')}</div>`
        ).join('')}</div>`;
    }).join('');
  } catch(e) { el.innerHTML = `<div class="error">${e.message}</div>`; }
}

async function loadMatrixBackup() {
  const el = document.getElementById('matrixBackupContent');
  el.innerHTML = '<div class="loading">加载中...</div>';
  try {
    const r = await fetch('/api/matrix/backups');
    const d = await r.json();
    const baks = d.backups || [];
    // 按身份分组展示最新
    const groups = {};
    baks.forEach(b => { if(!groups[b.identity]) groups[b.identity]=[]; groups[b.identity].push(b); });
    const html = Object.entries(groups).slice(0,6).map(([ident, items]) => {
      const latest = items[0];
      return `<div style="background:var(--bg3);border-radius:6px;padding:10px;border:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">
        <div><strong style="font-size:13px">${ident}</strong><br><span class="text-xs text-muted">${items.length} 备份 · 最新: ${latest.time_str} (${latest.size_kb}KB)</span></div>
        <div><button class="btn btn-sm btn-outline" onclick="restoreBackup('${ident}','${latest.path}')">恢复</button></div>
      </div>`;
    }).join('') || '<div class="text-muted text-sm">暂无备份</div>';
    el.innerHTML = `<div style="display:grid;gap:8px">${html}</div>
      <div style="margin-top:12px"><div style="display:flex;gap:8px;align-items:center">
        <input id="backupLabelInline" placeholder="备份标签" style="width:200px" value="inline">
        <button class="btn btn-primary btn-sm" onclick="createBackup()">创建备份</button>
      </div></div>
      <div id="backupResultInline" class="mt-4 text-sm"></div>`;
  } catch(e) { el.innerHTML = `<div class="error">${e.message}</div>`; }
}

async function loadMatrixExport() {
  const el = document.getElementById('matrixExportContent');
  el.innerHTML = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
    <div style="background:var(--bg2);border-radius:var(--radius);padding:20px;border:1px solid var(--border)">
      <div style="font-weight:600;margin-bottom:8px">📤 导出账号</div>
      <p class="text-sm text-muted mb-2">导出所有账号配置 + Cookie + 指纹为 ZIP</p>
      <button class="btn btn-primary" onclick="doExport()">导出 ZIP</button>
      <div id="exportResultInline" class="mt-4 text-sm"></div>
    </div>
    <div style="background:var(--bg2);border-radius:var(--radius);padding:20px;border:1px solid var(--border)">
      <div style="font-weight:600;margin-bottom:8px">📥 导入账号</div>
      <p class="text-sm text-muted mb-2">从 ZIP 文件恢复</p>
      <div class="flex" style="align-items:center">
        <input id="importPathInline" placeholder="/tmp/matrix_export.zip" style="flex:1">
        <button class="btn btn-primary" onclick="doImport()">导入</button>
      </div>
      <div id="importResultInline" class="mt-4 text-sm"></div>
    </div>
  </div>`;
}

// Helper functions for inline sub-views
async function createBackup() {
  const label = (document.getElementById('backupLabelHeader')?.value || document.getElementById('backupLabelInline')?.value || 'manual') + '_' + Date.now();
  // Try header result area first, fallback to inline
  let el = document.getElementById('backupResultHeader');
  if (!el) el = document.getElementById('backupResultInline');
  if (el) el.innerHTML = '<span style="color:var(--text2)">⏳ 备份中...</span>';
  try {
    const r = await fetch('/api/matrix/backup', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({label})});
    const res = await r.json();
    if (el) el.innerHTML = `<span style="color:var(--green)">✅ ${res.backup_count||0} 个身份已备份 (${label})</span>`;
    loadMatrixBackup();
  } catch(e) { if (el) el.innerHTML = `<span style="color:var(--red)">${e.message}</span>`; }
}

async function restoreBackup(identity, path) {
  if (!confirm(`从备份恢复 ${identity} 的 Cookie？`)) return;
  try {
    const r = await fetch('/api/matrix/restore', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({identity, path})});
    if (!r.ok) { const e=await r.json(); throw new Error(e.detail); }
    alert('✅ 恢复成功');
  } catch(e) { alert('❌ '+e.message); }
}

async function doExport() {
  const el = document.getElementById('exportResultInline');
  if (el) el.innerHTML = '<div class="loading" style="padding:6px">导出中...</div>';
  try {
    const r = await fetch('/api/matrix/export');
    const res = await r.json();
    if (el) el.innerHTML = `<div style="color:var(--green);font-size:13px">✅ ${res.path} (${res.size_kb}KB)</div>`;
  } catch(e) { if (el) el.innerHTML = `<div class="error">${e.message}</div>`; }
}

async function doImport() {
  const path = document.getElementById('importPathInline')?.value;
  if (!path) { alert('请输入ZIP路径'); return; }
  const el = document.getElementById('importResultInline');
  if (el) el.innerHTML = '<div class="loading" style="padding:6px">导入中...</div>';
  try {
    const r = await fetch('/api/matrix/import', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path})});
    if (!r.ok) { const e=await r.json(); throw new Error(e.detail); }
    const res = await r.json();
    if (el) el.innerHTML = `<div style="color:var(--green);font-size:13px">✅ 配置:${res.accounts_imported} 身份:${res.identities_imported}</div>`;
  } catch(e) { if (el) el.innerHTML = `<div class="error">${e.message}</div>`; }
}

// ═══ 计划对齐：Shell占位函数 + 重定向 ═══

// 通用占位Shell — 创建一个带状态标签的占位页面
function _renderShell(containerId, title, status, note) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const icons = {'无功能':'❌','无API':'🔌','无CLI':'🖥️','待集成':'⏳'};
  const icon = icons[status] || '📋';
  el.innerHTML = `
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:60px 20px;text-align:center">
      <div style="font-size:48px;margin-bottom:16px;opacity:.3">${icon}</div>
      <h2 style="font-size:20px;margin-bottom:8px;color:var(--text)">${title}</h2>
      <div style="display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:6px;background:rgba(217,119,6,.1);color:#d97706;font-size:12px;font-weight:600;margin-bottom:12px">
        🏗️ ${status}
      </div>
      <p style="font-size:13px;color:var(--text2);max-width:400px;line-height:1.6">${note}</p>
    </div>`;
}

// 矩阵系列 — 养号执行（直接内联执行面板）
async function loadMatrixNurture() {
  const el = document.getElementById('view-matrix-nurture');
  el.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">🌱 养号执行 <span style="font-size:10px;color:var(--text2);font-weight:400">预检 → 窗口定位 → 执行 → 验证</span></div>
        <div id="nurtureAcctList" style="margin-bottom:6px">
          <div class="loading" style="padding:8px;font-size:12px">⏳ 加载账号列表...</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:11px;color:var(--text2)">轮数:
            <select id="ndRounds" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="1">1 测试</option><option value="5">5</option>
              <option value="10" selected>10 默认</option>
              <option value="20">20</option><option value="30">30</option>
            </select>
          </label>
           <label style="font-size:11px;color:var(--text2)">蓝图:
             <select id="ndBlueprint" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
               <option value="">自动匹配</option>
             </select>
           </label>
           <script>
             (async function() {
               try {
                 const r = await fetch('/api/matrix/blueprints');
                 const d = await r.json();
                 const bps = d.blueprints || d || [];
                 const sel = document.getElementById('ndBlueprint');
                 if (!sel) return;
                 bps.forEach(bp => {
                   const name = bp.name || bp.file.replace(/\.json$/, '');
                   const file = bp.file.replace(/\.json$/, '');
                   const plat = (bp.platform || '').toLowerCase();
                   const emoji = plat === 'xiaohongshu' ? '📕' : '🎵';
                   const opt = document.createElement('option');
                   opt.value = file;
                   opt.textContent = emoji + ' ' + name;
                   sel.appendChild(opt);
                 });
               } catch(e) { console.warn('蓝图加载失败', e); }
             })();
           </script>
          <button onclick="nurturePreflight()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔍 预检</button>
          <button onclick="nurtureExec()" style="background:#22c55e;color:#000;border:none;padding:4px 14px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 执行选中</button>
          <button onclick="nurtureExecAll()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">📋 全部启用</button>
          <span id="nurtureSelCount" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>
        <div id="nurtureStatus" style="font-size:11px;color:var(--text2);margin-top:4px"></div>
        <div id="nurturePreflightInfo" style="font-size:10px;color:var(--text2);margin-top:2px;font-family:monospace;white-space:pre-wrap"></div>
        <div id="nurtureLog" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:300px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;
  // 用共享选择器加载账号列表
  const data = await _loadAccounts();
  _renderAccountSelector('nurtureAcctList', {_data: data, height: '350px'});
  document.getElementById('nurtureSelCount').textContent = '已选 ' + _getSelectedAccounts().length + ' 个';
}

// 矩阵系列 — 信息采集（按机器分组 + 账号选择）
// 矩阵系列 — 登录与信息采集（合并）
async function loadMatrixCollect() {
  const el = document.getElementById('view-matrix-collect');
  el.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">📡 登录与信息采集 <span style="font-size:10px;color:var(--text2);font-weight:400">登录+采集一体化，选择账号后可仅登录或登录后采集</span></div>
        <div id="collectAccountList" style="margin-bottom:6px">
          <div class="loading" style="padding:8px;font-size:12px">⏳ 加载账号列表...</div>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
          <span id="collectStatus" style="font-size:10px;color:var(--text2)">⏸️ 空闲</span>
          <button onclick="collectLogin()" style="background:#6366f1;color:#fff;border:none;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600">🔑 登录选中</button>
          <button onclick="collectExec()" style="background:var(--primary);color:#fff;border:none;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600">📥 采集选中</button>
          <button onclick="collectAll()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">📋 采集全部</button>
          <button onclick="cancelCollect()" style="background:rgba(220,38,38,.1);color:var(--red);border:1px solid rgba(220,38,38,.3);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">⏹ 停止</button>
          <span id="collectSelCount" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>
        <div id="collectLog" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:250px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;
  const data = await _loadAccounts();
  _renderAccountSelector('collectAccountList', {_data: data, height: '350px'});
  document.getElementById('collectSelCount').textContent = '已选 ' + _getSelectedAccounts().length + ' 个';
  // 加载采集状态
  try {
    const sr = await fetch('/api/matrix/collect-homepage/status');
    const sd = await sr.json();
    if (sd.running) document.getElementById('collectStatus').innerHTML = '<span style="color:var(--green)">🟢 采集中</span>';
  } catch(e) {}
}

// 采集：登录选中账号
window.collectLogin = async function() {
  const selected = _getSelectedAccounts();
  if (!selected.length) { alert('请先选择要登录的账号'); return; }
  const logEl = document.getElementById('collectLog');
  if (logEl) logEl.textContent = '🔑 登录 ' + selected.length + ' 个账号...\n';
  for (const s of selected) {
    try {
      const r = await fetch('/api/ops/run', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'login',accounts:[s.id]})});
      const d = await r.json();
      if (logEl) logEl.textContent += s.id + ': ' + (d.status || 'OK') + '\n';
    } catch(e) { if (logEl) logEl.textContent += s.id + ': ❌ ' + e.message + '\n'; }
  }
};

// 采集：采集选中账号
window.collectExec = async function() {
  const selected = _getSelectedAccounts();
  if (!selected.length) { alert('请先选择要采集的账号'); return; }
  const logEl = document.getElementById('collectLog');
  if (logEl) logEl.textContent = '📥 采集 ' + selected.length + ' 个账号...\n';
  for (const s of selected) {
    try {
      const r = await fetch('/api/matrix/collect-homepage', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({account_id:s.id})});
      const d = await r.json();
      document.getElementById('collectStatus').innerHTML = '<span style="color:var(--green)">🟢 采集中</span>';
      if (logEl) logEl.textContent += s.id + ': ' + (d.status || 'OK') + ' 机器:' + (d.machine||s.machine) + '\n';
    } catch(e) { if (logEl) logEl.textContent += s.id + ': ❌ ' + e.message + '\n'; }
  }
};

// 采集全部
window.collectAll = async function() {
  const selected = _getSelectedAccounts();
  if (!selected.length) { alert('没有可采集的账号'); return; }
  if (!confirm('采集全部 ' + selected.length + ' 个账号？')) return;
  await collectExec();
};

// 采集折叠组
function toggleCollectGroup(id) {
  const el = document.getElementById(id);
  const arrow = document.getElementById(id + '_arrow');
  if (!el) return;
  const hidden = el.style.display === 'none';
  el.style.display = hidden ? '' : 'none';
  if (arrow) arrow.textContent = hidden ? '▼' : '▶';
}

function toggleCollectMachine(master, machine) {
  document.querySelectorAll('.collect-cb[data-machine="' + machine + '"]').forEach(cb => cb.checked = master.checked);
}

// 采集选中账号（批量提交，后端路由到各机器）
async function collectSelected() {
  const cbs = document.querySelectorAll('.collect-cb:checked');
  const ids = Array.from(cbs).map(cb => cb.value);
  const log = document.getElementById('collectLog');
  if (!ids.length) { if (log) log.textContent = '请先选择要采集的账号'; return; }
  if (log) log.textContent = '⏳ 提交 ' + ids.length + ' 个采集任务（自动路由到各机器）...\n';
  try {
    const r = await fetch('/api/matrix/collect-homepage', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({account_ids:ids})});
    const d = await r.json();
    const results = d.results || [];
    if (log) {
      let txt = '📋 采集分发结果:\n';
      results.forEach(r2 => {
        const icon = r2.status === 'started' ? '✅' : r2.status === 'dispatched' ? '📡' : '❌';
        const machine = r2.machine === 'chengzigedeAir' ? '🖥️' : '☁️' + r2.machine;
        txt += '  ' + icon + ' ' + machine + ' ' + (r2.target || '') + ': ' + r2.status;
        if (r2.pid) txt += ' (PID:' + r2.pid + ')';
        txt += '\n';
      });
      log.textContent = txt;
    }
  } catch(e) { if (log) log.textContent += '❌ ' + e.message + '\n'; }
}

// 采集全部
async function collectAll() {
  const cbs = document.querySelectorAll('.collect-cb');
  const ids = Array.from(cbs).map(cb => cb.value);
  if (!ids.length) { 
    const log = document.getElementById('collectLog');
    if (log) log.textContent = '没有可采集的账号';
    return;
  }
  if (!confirm('采集全部 ' + ids.length + ' 个账号（自动路由到各机器）？')) return;
  await collectSelected();
}

// 保留旧函数兼容
window.collectByIdentity = async function(dir) {
  const log = document.getElementById('collectLog');
  if (!log) return;
  log.textContent = '⏳ 开始采集身份: ' + dir + '\n';
  try {
    const r = await fetch('/api/matrix/collect-homepage', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({identity_dir:dir})});
    const d = await r.json();
    log.textContent += JSON.stringify(d, null, 2);
  } catch(e) { log.textContent += '❌ ' + e.message; }
};
window.collectByIdentity = async function(dir) {
  const log = document.getElementById('collectLog');
  if (!log) return;
  log.textContent = '⏳ 开始采集身份: ' + dir + '\n';
  try {
    const r = await fetch('/api/matrix/collect-homepage', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({identity_dir:dir})});
    const d = await r.json();
    log.textContent += JSON.stringify(d, null, 2);
  } catch(e) { log.textContent += '❌ ' + e.message; }
};
window.collectByPhone = async function() {
  const phone = document.getElementById('collectPhoneInput')?.value;
  const log = document.getElementById('collectLog');
  if (!log) return;
  if (!phone) { log.textContent = '请输入手机号'; return; }
  log.textContent = '⏳ 开始采集手机号: ' + phone + '\n';
  try {
    const r = await fetch('/api/matrix/collect-homepage/phone', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone})});
    const d = await r.json();
    log.textContent += JSON.stringify(d, null, 2);
  } catch(e) { log.textContent += '❌ ' + e.message; }
};
window.cancelCollect = async function() {
  const log = document.getElementById('collectLog');
  if (!log) return;
  log.textContent = '⏳ 停止中...\n';
  try {
    const r = await fetch('/api/matrix/collect-homepage/cancel', {method:'POST'});
    const d = await r.json();
    log.textContent += JSON.stringify(d, null, 2);
  } catch(e) { log.textContent += '❌ ' + e.message; }
};
window.loadCollectHistory = async function() {
  const log = document.getElementById('collectLog');
  if (!log) return;
  log.textContent = '⏳ 加载历史...\n';
  try {
    const r = await fetch('/api/matrix/homepage-history');
    const d = await r.json();
    log.textContent += JSON.stringify(d, null, 2);
  } catch(e) { log.textContent += '❌ ' + e.message; }
};

// 矩阵系列 — 内容发布（Shell — 无CLI）
async function loadMatrixPublish() {
  _renderShell('view-matrix-publish', '📤 内容发布', '无CLI',
    '发布模块的 CLI 封装尚未完成。现有的 publish_video.py 在 agent-os/agent-sync/05_tools/07_matrix/scripts/ 目录下。需要 agentos matrix publish CLI 封装。');
}

// 矩阵系列 — 定向评论（共享选择器）
async function loadMatrixComment() {
  const el = document.getElementById('view-matrix-comment');
  el.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">💬 定向评论 <span style="font-size:10px;color:var(--text2);font-weight:400">选择账号 → 填入视频链接 → 方向/语料 → 执行</span></div>
        <div id="commentAccountList" style="margin-bottom:6px">
          <div class="loading" style="padding:8px;font-size:12px">⏳ 加载账号列表...</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
          <textarea id="commentUrls" placeholder="视频链接（每行一个，支持多个）" rows="3" style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
          <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:140px">
            <select id="commentDirection" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
              <option value="">自动选方向</option>
              <option value="称赞">👍 称赞</option>
              <option value="提问">🤔 提问</option>
              <option value="共鸣">💗 共鸣</option>
              <option value="感慨">😌 感慨</option>
              <option value="客观">📊 客观</option>
            </select>
            <select id="commentCorpus" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
              <option value="">默认语料</option>
              <option value="通用">📚 通用</option>
              <option value="科技">💻 科技</option>
              <option value="生活">🏠 生活</option>
              <option value="美食">🍔 美食</option>
              <option value="娱乐">🎮 娱乐</option>
            </select>
            <button onclick="runComment()" style="background:var(--primary);color:#fff;border:none;padding:5px 12px;border-radius:4px;cursor:pointer;font-size:12px">🚀 执行评论</button>
          </div>
        </div>
        <div id="commentResult" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;
  const data = await _loadAccounts();
  _renderAccountSelector('commentAccountList', {_data: data, height: '350px'});
}
window.runComment = async function() {
  const selected = _getSelectedAccounts();
  const urlsText = document.getElementById('commentUrls')?.value;
  const dir = document.getElementById('commentDirection')?.value;
  const corpus = document.getElementById('commentCorpus')?.value;
  const el = document.getElementById('commentResult');
  if (!urlsText || !urlsText.trim()) { el.textContent = '请填写至少一个视频链接'; return; }
  const urls = urlsText.split('\n').map(u => u.trim()).filter(u => u);
  if (!urls.length) { el.textContent = '请填写有效的视频链接'; return; }
  if (!selected.length) { el.textContent = '请先选择要执行的账号'; return; }
  el.textContent = '⏳ 使用 ' + selected.length + ' 个账号评论 ' + urls.length + ' 个视频...\n';
  let results = [];
  for (const url of urls) {
    for (const s of selected) {
      try {
        const r = await fetch('/api/matrix/task/run', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'comment',url,direction:dir||null,account:s.id,corpus:corpus||null})});
        const d = await r.json();
        results.push({url, account:s.id, status: d.error ? '❌' : '✅', msg: d.error || (d.task_id || 'OK')});
      } catch(e) { results.push({url, account:s.id, status: '❌', msg: e.message}); }
    }
  }
  const totalOk = results.filter(r => r.status === '✅').length;
  el.textContent = '✅ ' + totalOk + '/' + results.length + ' 完成\n' +
    results.slice(0,30).map(r => r.status + ' ' + (r.account||'') + ' ' + (r.url||'').slice(0,35) + ' ' + (r.msg||'')).join('\n');
};

// 矩阵系列 — 定时任务（Shell — 待集成）
// 矩阵系列 — 定时任务（有 API → 集成）
async function loadMatrixSchedule() {
  const el = document.getElementById('view-matrix-schedule');
  el.innerHTML = '<div id="schedPanel" style="padding:20px"><div class="loading">⏳ 加载定时任务...</div></div>';
  try {
    const ri = await fetch('/api/matrix/schedules');
    const di = await ri.json();
    const tasks = di.tasks || di || [];
    document.getElementById('schedPanel').innerHTML = `
      <h2 style="font-size:18px;margin-bottom:12px">⏰ 定时任务</h2>
      <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);margin-bottom:12px">
        <div style="font-size:12px;font-weight:600;margin-bottom:6px">📋 任务列表 (${Array.isArray(tasks)?tasks.length:0})</div>
        <div style="font-size:12px">${Array.isArray(tasks) && tasks.length ? tasks.map(t =>
          '<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border)">'+
          '<span style="font-size:10px">'+(t.enabled?'🟢':'⚪')+'</span>'+
          '<span>'+(t.account||t.id||'-')+'</span>'+
          '<span style="font-size:11px;color:var(--text2)">'+(t.blueprint||'')+'</span>'+
          '<span style="font-size:11px;color:var(--text2)">'+(t.time||'')+'</span>'+
          '</div>'
        ).join('') : '<span style="color:var(--text2)">暂无定时任务</span>'}</div>
      </div>
      <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);margin-bottom:8px">
        <div style="font-size:12px;font-weight:600;margin-bottom:6px">➕ 新建定时任务</div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
          <button onclick="switchView('matrix-commands')" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">→ 前往命令与任务页</button>
        </div>
      </div>
      <div style="font-size:10px;color:var(--text2)">完整调度管理在「矩阵 → 命令与任务」页面</div>`;
  } catch(e) {
    document.getElementById('schedPanel').innerHTML = '<div style="padding:20px"><h2 style="font-size:18px;margin-bottom:12px">⏰ 定时任务</h2><div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border)"><div class="error">❌ '+e.message+'</div><p style="font-size:12px;color:var(--text2);margin-top:8px">完整调度管理在「矩阵 → 命令与任务」页面</p></div></div>';
  }
}

// 矩阵系列 — 收藏点赞（共享选择器）
async function loadMatrixLike() {
  const el = document.getElementById('view-matrix-like');
  el.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">❤️ 收藏点赞 <span style="font-size:10px;color:var(--text2);font-weight:400">选择账号 → 填入视频链接 → 执行点赞</span></div>
        <div id="likeAccountList" style="margin-bottom:6px">
          <div class="loading" style="padding:8px;font-size:12px">⏳ 加载账号列表...</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
          <textarea id="likeUrls" placeholder="视频链接（每行一个，支持多个）" rows="3" style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
          <button onclick="runLike()" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:4px;cursor:pointer;font-size:12px;align-self:flex-start">❤️ 执行点赞</button>
        </div>
        <div id="likeResult" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;
  const data = await _loadAccounts();
  _renderAccountSelector('likeAccountList', {_data: data, height: '350px'});
}

window.runLike = async function() {
  const selected = _getSelectedAccounts();
  const urlsText = document.getElementById('likeUrls')?.value;
  const el = document.getElementById('likeResult');
  if (!urlsText || !urlsText.trim()) { el.textContent = '请填写视频链接'; return; }
  const urls = urlsText.split('\n').map(u => u.trim()).filter(u => u);
  if (!urls.length) { el.textContent = '请填写有效的视频链接'; return; }
  if (!selected.length) { el.textContent = '请先选择要执行的账号'; return; }
  el.textContent = '⏳ 执行 ' + urls.length + ' 个点赞...\n';
  let results = [];
  for (const url of urls) {
    for (const s of selected) {
      try {
        const r = await fetch('/api/matrix/task/run', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'like',url,account:s.id})});
        const d = await r.json();
        results.push({url, account:s.id, status: d.error ? '❌' : '✅', msg: d.error || (d.task_id || 'OK')});
      } catch(e) { results.push({url, account:s.id, status: '❌', msg: e.message}); }
    }
  }
  const ok = results.filter(r => r.status === '✅').length;
  el.textContent = '✅ ' + ok + '/' + results.length + '\n' +
    results.slice(0,30).map(r => r.status + ' ' + (r.account||'') + ' ' + (r.url||'').slice(0,35)).join('\n');
};

// 矩阵系列 — 登录管理 → 已合并到信息采集
async function loadMatrixLogin() {
  const el = document.getElementById('view-matrix-login');
  el.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:16px;border:1px solid var(--border);text-align:center">
        <div style="font-size:24px;margin-bottom:8px">🔑</div>
        <div style="font-size:14px;font-weight:600;margin-bottom:4px">登录管理已合并到信息采集</div>
        <div style="font-size:12px;color:var(--text2);margin-bottom:12px">登录 → 采集是同一流程，请前往「信息采集」页面操作</div>
        <button onclick="switchView('matrix-collect')" style="background:var(--primary);color:#fff;border:none;padding:8px 24px;border-radius:6px;cursor:pointer;font-size:13px">→ 前往信息采集</button>
      </div>
    </div>`;
}

// 联邦指挥台（共享选择器 + 操作类型选择）
async function loadOpsCommand() {
  const el = document.getElementById('view-ops-command');
  el.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border);margin-bottom:8px">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">🖥️ 联邦指挥台 <span style="font-size:10px;color:var(--text2);font-weight:400">选机器 → 选操作 → 选账号 → 批量执行</span></div>
        <div id="opsAccountList" style="margin-bottom:6px">
          <div class="loading" style="padding:8px;font-size:12px">⏳ 加载账号列表...</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:11px;color:var(--text2)">操作:
            <select id="opsType" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
              <option value="nurture">🏃 养号</option>
              <option value="collect">📡 采集</option>
              <option value="login">🔑 登录</option>
              <option value="logout">🔒 登出</option>
            </select>
          </label>
          <label style="font-size:11px;color:var(--text2)" id="opsRoundsLabel">轮数:
            <select id="opsRounds" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
              <option value="1">1</option><option value="5">5</option>
              <option value="10" selected>10</option><option value="20">20</option>
            </select>
          </label>
          <button onclick="opsBatchExec()" style="background:#22c55e;color:#000;border:none;padding:5px 16px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 批量执行</button>
          <span id="opsSelCount" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>
        <div id="opsResult" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>
      <div id="opsHistoryBox" style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-size:12px;font-weight:600;margin-bottom:4px">📋 执行历史</div>
        <div id="opsHistoryList" style="font-size:10px;max-height:180px;overflow-y:auto">
          <div class="loading">⏳ 加载执行历史...</div>
        </div>
      </div>
    </div>`;
  const data = await _loadAccounts();
  _renderAccountSelector('opsAccountList', {_data: data, height: '350px'});
  document.getElementById('opsSelCount').textContent = '已选 ' + _getSelectedAccounts().length + ' 个';
  loadOpsHistory();
}

async function loadOpsHistory() {
  try {
    const r = await fetch('/api/matrix/nurture/results');
    const d = await r.json();
    const items = d.results || [];
    const el = document.getElementById('opsHistoryList');
    if (!items.length) { el.innerHTML = '<div style="color:var(--text2)">暂无执行记录</div>'; return; }
    let html = '<table style="width:100%"><tr><th>时间</th><th>账号</th><th>状态</th><th>步骤</th><th>耗时</th></tr>';
    items.slice(0, 20).forEach(r => {
      const st = r.status === 'completed' ? '✅' : r.status === 'running' ? '⏳' : '❌';
      const ts = r.completed_at || r.started_at || '';
      const time = ts ? new Date(ts).toLocaleString('zh-CN',{hour:'2-digit',minute:'2-digit'}) : '-';
      const steps = r.steps ? (r.steps.success||0)+'/'+(r.steps.total||0) : '-';
      const dur = r.duration_secs ? Math.round(r.duration_secs/60)+'min' : '-';
      html += `<tr><td>${time}</td><td>${r.account}</td><td>${st}</td><td>${steps}</td><td>${dur}</td></tr>`;
    });
    html += '</table>';
    el.innerHTML = html;
  } catch(e) {}
}

// ════════════════════════════════════════════════════════
// 共享账号选择器（所有操作视图共用）
// ════════════════════════════════════════════════════════

let _allAccounts = [];
let _hpIndex = {};
let _collectedAt = '';

async function _loadAccounts() {
  if (_allAccounts.length) {
    return {accounts: _allAccounts, hpIndex: _hpIndex, collectedAt: _collectedAt};
  }
  const [r1, r2] = await Promise.all([
    fetch('/api/matrix/accounts'),
    fetch('/api/matrix/homepage-info').catch(() => ({json: () => ({})}))
  ]);
  const accts = await r1.json();
  const hpData = r2.json ? await r2.json() : {results:[]};
  _allAccounts = Array.isArray(accts) ? accts.filter(a => a.enabled !== false) : [];

  _hpIndex = {};
  (hpData.results || []).forEach(r => {
    if (r.identity_dir) _hpIndex[r.identity_dir] = r;
    if (r.phone) _hpIndex[r.phone] = r;
  });
  _collectedAt = hpData.collected_at || '';

  return {accounts: _allAccounts, hpIndex: _hpIndex, collectedAt: _collectedAt};
}

function _renderAccountSelector(containerId, options = {}) {
  /* options:
    onSelect: 账号选择变更回调 (selectedIds, selectedTree)
    filterMachine: 只显示某台机器
    filterPlatform: 只显示某平台
    checkAll: 默认全选
    hideFilter: 隐藏搜索框
    height: 最大高度
  */
  const container = document.getElementById(containerId);
  if (!container) return;

  const data = options._data || {};
  const allAccts = data.accounts || _allAccounts;
  const hpIndex = data.hpIndex || {};
  const collectedAt = data.collectedAt || '';

  // 按机器→身份分组
  const tree = {};
  allAccts.forEach(a => {
    if (options.filterMachine && a.owner_machine !== options.filterMachine) return;
    if (options.filterPlatform && a.platform !== options.filterPlatform) return;
    const machine = a.owner_machine || '未分配';
    const ident = a.identity_dir || a.id;
    if (!tree[machine]) tree[machine] = {};
    if (!tree[machine][ident]) tree[machine][ident] = {phone: a.phone || '', accounts: []};
    tree[machine][ident].accounts.push(a);
  });

  const machineOrder = Object.keys(tree).sort((a,b) => {
    if (a === 'chengzigedeAir') return -1;
    if (b === 'chengzigedeAir') return 1;
    return a.localeCompare(b);
  });

  const checkAll = options.checkAll !== false;

  // 统计计数器
  let totalAccts = 0, totalIdent = 0;

  let html = '';
  if (!options.hideFilter) {
    html += '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:4px">';
    html += '<input class="as-filter" placeholder="🔍 搜索账号ID/手机号/昵称..." oninput="_filterAccountSelector()"';
    html += ' style="flex:1;min-width:100px;padding:3px 6px;font-size:11px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px">';
    html += '</div>';
  }

  html += '<div class="as-body" style="max-height:' + (options.height || '400px') + ';overflow-y:auto">';

  machineOrder.forEach(machine => {
    const idents = tree[machine];
    const isLocal = machine === 'chengzigedeAir';
    const machineLabel = isLocal ? '🖥️ ' + machine : '☁️ ' + machine;
    const grpId = 'as_m_' + machine.replace(/[^a-zA-Z0-9]/g, '_');
    const acctCount = Object.values(idents).reduce((s, i) => s + i.accounts.length, 0);
    const identCount = Object.keys(idents).length;
    const loggedIn = Object.values(idents).reduce((s, i) => s + i.accounts.filter(a => a._status === 'logged_in').length, 0);
    totalAccts += acctCount;
    totalIdent += identCount;

    html += '<div style="border:1px solid var(--border);border-radius:5px;margin-bottom:3px;overflow:hidden">';
    // 机器标题
    html += '<div onclick="toggleCollectGroup(\'' + grpId + '\')" style="display:flex;align-items:center;gap:5px;padding:4px 8px;background:var(--bg3);cursor:pointer;font-size:11px;user-select:none">';
    html += '<span id="' + grpId + '_arrow" style="font-size:9px;opacity:.6">▼</span>';
    html += '<input type="checkbox" onclick="event.stopPropagation();_asToggleMachine(this)" data-machine="' + machine + '" ' + (checkAll ? 'checked' : '') + '>';
    html += '<strong>' + machineLabel + '</strong>';
    html += '<span style="font-size:9px;color:var(--text2)">' + identCount + ' 身份 ' + acctCount + ' 账号 | ' + loggedIn + ' 已登录</span>';
    html += '</div>';
    // 账号列表
    html += '<div id="' + grpId + '" style="overflow-x:auto">';
    html += '<table style="width:100%;font-size:10px;border-collapse:collapse"><tbody>';
    Object.keys(idents).sort().forEach(ident => {
      const identity = idents[ident];
      const hp = hpIndex[ident] || hpIndex[identity.phone];
      const phoneDisplay = identity.phone ? identity.phone.slice(0,11) : ident.replace('phone_','');
      const nickDisplay = hp?.display_name ? hp.display_name.slice(0,10) : '';
      const rowspan = identity.accounts.length;

      identity.accounts.forEach((a, idx) => {
        const plat = a.platform === 'douyin' ? '🎵' : '📕';
        const defBP = a.platform === 'xiaohongshu' ? 'xhs_daily' : 'douyin_daily';
        const hpAcc = hp ? (a.platform === 'douyin' ? hp.douyin : hp.xiaohongshu) : null;
        const nickname = hpAcc?.nickname ? hpAcc.nickname.slice(0,12) : '';
        const hpTime = hpAcc?.collected_at || '';
        const hpTimeDisplay = hpTime ? new Date(hpTime).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}) : '';

        let statusIcon, cookieIcon;
        if (a._status === 'logged_in') {
          statusIcon = '<span class="badge badge-green" style="font-size:9px">已登录</span>';
          cookieIcon = '<span style="color:var(--green);font-size:9px">🍪有效</span>';
        } else {
          statusIcon = '<span class="badge badge-amber" style="font-size:9px">'+(a._status||'未知')+'</span>';
          cookieIcon = '<span style="color:var(--red);font-size:9px">🍪'+(a._status||'')+'</span>';
        }

        html += '<tr class="as-row" data-account="'+a.id+'" data-machine="'+machine+'" data-platform="'+a.platform+'" data-bp="'+defBP+'">';
        if (idx === 0) {
          html += '<td rowspan="'+rowspan+'" style="padding:2px 4px;font-size:9px;color:var(--text2);vertical-align:middle;border-right:1px solid var(--border);white-space:nowrap">📱'+phoneDisplay+(nickDisplay?' '+nickDisplay:'')+'</td>';
        }
        html += '<td style="padding:2px 3px;width:20px"><input type="checkbox" class="as-cb" value="'+a.id+'" data-plat="'+a.platform+'" data-bp="'+defBP+'" data-machine="'+machine+'" ' + (checkAll ? 'checked' : '') + '></td>';
        html += '<td style="padding:2px 4px;white-space:nowrap"><strong>'+a.id+'</strong></td>';
        html += '<td style="padding:2px 4px">'+plat+'</td>';
        html += '<td style="padding:2px 4px;font-size:9px;max-width:70px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+(nickname||'<span class="text-muted">-</span>')+'</td>';
        html += '<td style="padding:2px 4px;white-space:nowrap">'+statusIcon+'</td>';
        html += '<td style="padding:2px 4px;font-size:9px;white-space:nowrap">'+cookieIcon+'</td>';
        html += '<td style="padding:2px 4px;font-size:9px;color:var(--text2);white-space:nowrap">采集:'+hpTimeDisplay+'</td>';
        html += '<td style="padding:2px 4px;font-size:9px;color:var(--text2);white-space:nowrap">📋'+defBP+'</td>';
        html += '</tr>';
      });
    });
    html += '</tbody></table></div></div>';
  });
  html += '</div>';

  html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 4px;font-size:10px;color:var(--text2)">';
  html += '<span>共 ' + allAccts.length + ' 个账号</span>';
  html += '<span id="' + containerId + '_count">已选 ' + (checkAll ? allAccts.length : 0) + ' 个</span>';
  html += '</div>';

  container.innerHTML = html;
  _asRefreshCount(containerId);
}

function _asToggleMachine(master) {
  const machine = master.dataset.machine;
  document.querySelectorAll('.as-cb[data-machine="' + machine + '"]').forEach(cb => cb.checked = master.checked);
  _asRefreshCount(null);
}

function _asRefreshCount(containerId) {
  const checked = document.querySelectorAll('.as-cb:checked').length;
  if (containerId) {
    const el = document.getElementById(containerId + '_count');
    if (el) el.textContent = '已选 ' + checked + ' 个';
  }
}

function _getSelectedAccounts() {
  return Array.from(document.querySelectorAll('.as-cb:checked')).map(cb => ({
    id: cb.value,
    platform: cb.dataset.plat,
    blueprint: cb.dataset.bp,
    machine: cb.dataset.machine,
  }));
}

function _filterAccountSelector() {
  const q = (document.querySelector('.as-filter')?.value || '').toLowerCase();
  document.querySelectorAll('.as-row').forEach(row => {
    const acct = row.dataset.account || '';
    const phone = row.querySelector('td:first-child')?.textContent?.replace('📱','') || '';
    const nick = row.querySelectorAll('td')[4]?.textContent || '';
    const match = !q || acct.includes(q) || phone.includes(q) || nick.includes(q);
    row.style.display = match ? '' : 'none';
  });
  _asRefreshCount(null);
}


// 统一操作执行函数（供各视图调用）
async function opsRun(type, accounts, extraParams) {
  const body = {type, accounts};
  if (extraParams) body.params = extraParams;
  try {
    const r = await fetch('/api/ops/run', {
      method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)
    });
    const d = await r.json();
    return d;
  } catch(e) {
    return {status:'error', message: e.message};
  }
}

async function opsBatchExec() {
  const type = document.getElementById('opsType')?.value || 'nurture';
  const rounds = parseInt(document.getElementById('opsRounds')?.value) || 10;
  const resultEl = document.getElementById('opsResult');
  const selected = _getSelectedAccounts();

  if (!selected.length) { resultEl.textContent = '请先选择要执行的账号'; return; }

  resultEl.textContent = '⏳ 执行 ' + type + ' 于 ' + selected.length + ' 个账号...';

  const result = await opsRun(type, selected.map(s => s.id), {rounds});

  if (result.status === 'started') {
    let txt = '✅ 已启动:\n';
    (result.ops || []).forEach(o => {
      txt += '  ' + o.account + ': ' + (o.status || 'OK') + '\n';
    });
    resultEl.textContent = txt;
    setTimeout(loadOpsHistory, 5000);
  } else {
    resultsEl.innerHTML = '<div style="color:var(--red)">❌ '+(result.message||JSON.stringify(result))+'</div>';
  }
}

// 视频工厂系列 — Shell（无API）
async function loadAveRender()   { _renderShell('view-ave-render', '🎬 渲染任务', '无API', 'AVE 渲染任务的 API 尚未暴露。需要完成 agentos ave CLI 封装后对接。'); }
async function loadAveScript()   { _renderShell('view-ave-script', '📝 脚本生成', '无API', '脚本生成模块的 API 尚未暴露。需要完成 agentos ave CLI 封装后对接。'); }
async function loadAveMaterials(){ _renderShell('view-ave-materials', '📦 素材库', '无API', '素材管理模块的 API 尚未暴露。当前素材通过 SQLite 管理，需封装为 Dashboard API。'); }
async function loadAveTemplates(){ _renderShell('view-ave-templates', '📋 模板', '无API', '模板管理模块的 API 尚未暴露。需要完成 agentos ave CLI 封装后对接。'); }

// 内容采集系列 — 采集任务（有 plugin-collector → 集成）
async function loadCrawlTasks() {
  const el = document.getElementById('view-crawl-tasks');
  el.innerHTML = '<div id="crawlTaskPanel" style="padding:20px"><div class="loading">⏳ 加载采集管理...</div></div>';
  try {
    const rs = await fetch('/api/plugins/collector/summary');
    const d = await rs.json();
    document.getElementById('crawlTaskPanel').innerHTML = `
      <h2 style="font-size:18px;margin-bottom:12px">📡 采集任务</h2>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;margin-bottom:12px">
        <div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
          <div style="font-size:12px;color:var(--text2)">总采集数</div>
          <div style="font-size:24px;font-weight:700">${d.total||0}</div>
        </div>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
          <div style="font-size:12px;color:var(--text2)">今日新增</div>
          <div style="font-size:24px;font-weight:700;color:var(--green)">${d.today||0}</div>
        </div>
      </div>
      <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border)">
        <div style="font-size:12px;font-weight:600;margin-bottom:8px">🔧 操作</div>
        <button onclick="switchView('plugin-collector')" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">→ 打开采集管理器</button>
        <span style="font-size:11px;color:var(--text2);margin-left:8px">完整采集管理界面</span>
      </div>`;
  } catch(e) {
    document.getElementById('crawlTaskPanel').innerHTML = `<div style="padding:0"><h2 style="font-size:18px;margin-bottom:12px">📡 采集任务</h2>
      <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border)">
        <p style="font-size:13px;color:var(--text2);margin-bottom:8px">采集管理器可通过下方按钮访问</p>
        <button onclick="switchView('plugin-collector')" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">→ 打开采集管理器</button>
      </div></div>`;
  }
}
async function loadCrawlSources(){ _renderShell('view-crawl-sources', '📡 源管理', '无CLI', '采集源管理需要 agentos crawl CLI 封装后实现。'); }
async function loadCrawlHistory(){ _renderShell('view-crawl-history', '📜 采集历史', '无API', '采集历史的统一展示 API 尚未完成。'); }

// 联邦系列 — 一键同步（有CLI）
async function loadFleetSync() {
  const el = document.getElementById('view-fleet-sync');
  el.innerHTML = `
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">🔄 一键同步</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">通过 Git 同步三台机器（本机 / 5kecheng / 7kecheng）的最新代码</p>
      <div style="display:flex;gap:8px;margin-bottom:12px">
        <button onclick="doFleetSync()" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">🔄 执行同步</button>
      </div>
      <div id="fleetSyncLog" style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:400px;overflow:auto"></div>
    </div>`;
}
window.doFleetSync = async function() {
  const el = document.getElementById('fleetSyncLog');
  el.textContent = '⏳ 执行中...\n';
  try {
    const r = await fetch('/api/fleet/sync', {method:'POST'});
    const d = await r.json();
    el.textContent = d.output || JSON.stringify(d, null, 2);
  } catch(e) { el.textContent = '❌ ' + e.message; }
};

// 联邦系列 — 对账检查（有CLI）
async function loadFleetReconcile() {
  const el = document.getElementById('view-fleet-reconcile');
  el.innerHTML = `
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">🔍 对账检查</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">检查本机是否符合 ORACLE.yaml 宪法定义</p>
      <div style="display:flex;gap:8px;margin-bottom:12px">
        <button onclick="doFleetReconcile()" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">🔍 执行对账</button>
      </div>
      <div id="fleetReconcileLog" style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:400px;overflow:auto"></div>
    </div>`;
}
window.doFleetReconcile = async function() {
  const el = document.getElementById('fleetReconcileLog');
  el.textContent = '⏳ 执行中...\n';
  try {
    const r = await fetch('/api/fleet/reconcile', {method:'POST'});
    const d = await r.json();
    el.textContent = d.output || JSON.stringify(d, null, 2);
  } catch(e) { el.textContent = '❌ ' + e.message; }
};

// 联邦系列 — 远程Shell（有CLI）
async function loadFleetExec() {
  const el = document.getElementById('view-fleet-exec');
  el.innerHTML = `
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">💻 远程Shell</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">在远程机器上执行命令（通过 mc remote exec）</p>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px">
        <select id="fleetExecMachine" style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px">
          <option value="5kechengdeAir">5kechengdeAir</option>
          <option value="7kecheng">7kecheng</option>
        </select>
        <input id="fleetExecCmd" placeholder="输入命令..." style="flex:1;min-width:200px;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px">
        <button onclick="doFleetExec()" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">➡ 执行</button>
      </div>
      <div id="fleetExecLog" style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:400px;overflow:auto"></div>
    </div>`;
}
window.doFleetExec = async function() {
  const machine = document.getElementById('fleetExecMachine')?.value;
  const cmd = document.getElementById('fleetExecCmd')?.value;
  const el = document.getElementById('fleetExecLog');
  if (!cmd) { el.textContent = '请输入命令'; return; }
  el.textContent = '⏳ 执行中...\n';
  try {
    const r = await fetch('/api/federation/exec', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({machine,command:cmd,timeout:30})});
    const d = await r.json();
    el.textContent = d.output || JSON.stringify(d, null, 2);
  } catch(e) { el.textContent = '❌ ' + e.message; }
};

// 服务系列 — Shell（无功能）
async function loadServeMCP()      { _renderShell('view-serve-mcp', '🔌 MCP状态', '无功能', 'MCP 状态监控尚未实现。这是显示当前 MCP Server 连接状态和运行指标的页面。'); }
async function loadServeDashboard(){ _renderShell('view-serve-dashboard', '📊 Dashboard日志', '无功能', 'Dashboard 日志聚合页面尚未实现。将汇总各模块的运行日志。'); }
async function loadServeSchedule() { _renderShell('view-serve-schedule', '⏰ 全局定时任务', '无功能', '全局调度器管理页面尚未实现。将在 agentos serve schedule CLI 封装完成后对接。'); }

// ── SMS & Proxy ──
async function loadSmsProxy() {
  await Promise.all([
    loadSmsConfig(),
    loadProxyList(),
    loadPhonePresets(),
    loadSmsAccounts(),
  ]);
}

async function loadSmsAccounts() {
  const sel = document.getElementById('smsAccountSelect');
  const overview = document.getElementById('smsAccountsOverview');
  if (!sel) return;
  try {
    // 直接从 SMS API 获取账号（/api/federation/accounts 返回的是 HTML，不是 JSON）
    const r = await fetch('/api/matrix/sms/accounts');
    const d = await r.json();
    if (d.error) {
      if (overview) overview.innerHTML = '<span style="color:var(--red)">❌ '+d.error+'</span>';
      return;
    }
    const accounts = d.accounts || [];

    window._lastSmsAccounts = accounts;
    // 下拉框（隐藏，用于存储完整选项数据）
    sel.innerHTML = '<option value="">— 选择账号 —</option>' +
      accounts.map(a => '<option value="'+a.id+'" data-phone="'+(a.phone||'')+'" data-nick="'+(a.nickname||'')+'" data-display="'+
        ((a.platform==='xiaohongshu'?'📕':'🎵')+' '+a.nickname+' '+(a.owner_machine||(a.is_local?'本机':'远程'))+' ('+a.phone+')').replace(/"/g,'&quot;')+'">'+
        ((a.platform==='xiaohongshu'?'📕':'🎵')+' '+a.nickname+' '+(a.owner_machine||(a.is_local?'本机':'远程'))+' ('+a.phone+')')+'</option>').join('');
    // 搜索框：存一份完整选项用于搜索
    window._smsAccountOptions = accounts;
    // 加载人设信息（供卡片渲染使用）
    let personas = {};
    try {
      const pr = await fetch('/api/matrix/personas');
      const pd = await pr.json();
      personas = pd.personas || {};
    } catch(e) { /* ignore */ }

    // 账号管理 — 身份卡片（手机号分组）+ 账号列表（表格）
    if (overview) {
      const dot = (ok) => ok ? '✅' : '❌';
      const machineLabel = (a) => a.owner_machine || (a.is_local ? '本机' : '远程');
      const isRemote = (a) => !a.is_local && a.owner_machine;
      const loginDisabled = (a) => a.busy || isRemote(a);
      const loginTitle = (a) => a.busy ? '忙碌中' : (isRemote(a) ? '需在 '+machineLabel(a)+' 操作' : '登录');
      const clearTitle = (a) => a.busy ? '忙碌中' : (isRemote(a) ? '需在 '+machineLabel(a)+' 操作' : '清除');
      const delTitle = (a) => a.busy ? '忙碌中' : (isRemote(a) ? '需在 '+machineLabel(a)+' 操作' : '删除');
      const btnStyle = (a, disabled) => disabled ? 'opacity:.3;cursor:not-allowed' : 'cursor:pointer';
      
      // 加载录制统计
      let recStats = {};
      try { 
        const rr = await fetch('/api/matrix/recordings/stats');
        const rd = await rr.json();
        recStats = rd.stats || {};
      } catch(e) {}

      // ═══ 上部: 身份卡片（按手机号分组）═══
      const groups = {};
      accounts.forEach(a => {
        const m = machineLabel(a);
        const p = a.phone || '未设置手机号';
        const key = m + '|' + p;
        if (!groups[key]) groups[key] = { machine: m, phone: p, accts: [] };
        groups[key].accts.push(a);
      });
      
      var cardsHtml = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:10px;margin-bottom:16px">'+
        Object.values(groups).sort(function(a,b) {
          // 本机优先
          var aLocal = a.accts.some(function(acct){return acct.is_local;});
          var bLocal = b.accts.some(function(acct){return acct.is_local;});
          if (aLocal && !bLocal) return -1;
          if (!aLocal && bLocal) return 1;
          // 同是本机或同是远程：按机器名+手机号排
          var ma = a.machine, mb = b.machine;
          if (ma < mb) return -1;
          if (ma > mb) return 1;
          return a.phone.localeCompare(b.phone);
        }).map(function(g) {
          var accts = g.accts;
          var sharedIdent = accts.find(function(a){return (a.identity_dir||'').startsWith('phone_');})?.identity_dir
            || accts.find(function(a){return a.has_identity;})?.id || accts[0]?.id;
          var recCount = accts.reduce(function(s,a){return s+(recStats[a.id]||0);},0);
          var cooked = accts.reduce(function(s,a){return s+(a.has_cookie?1:0);},0);
          var fmtNum = function(v) { if(!v||v==='?'||v==='-')return'-';var n=parseInt(v);if(isNaN(n))return v;if(n>=10000)return(n/10000).toFixed(1)+'w';if(n>=1000)return(n/1000).toFixed(1)+'k';return n; };
          var statusBadge = function(a) { return a.has_cookie ? '<span style="color:var(--green)">✅</span>' : '<span style="color:var(--text2)">❌</span>'; };
          
          return '<div style="background:var(--bg2);border-radius:var(--radius);padding:10px;border:1px solid var(--border);box-shadow:var(--shadow)">'+
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;font-size:12px">'+
              '<div><strong>📱 '+g.phone+'</strong> <span style="font-size:10px;color:var(--text2);margin-left:4px">🆔 '+(sharedIdent||'')+'</span></div>'+
              '<span style="font-size:10px;color:var(--text2)">🍪 '+cooked+'/'+accts.length+'已登录 | 📦 '+recCount+'次录制</span>'+
            '</div>'+
            '<div style="font-size:10px;color:var(--primary);margin-bottom:6px">🖥️ '+g.machine+'</div>'+
            '<table style="width:100%;font-size:11px">'+
              '<thead><tr style="color:var(--text2);font-size:10px">'+
                '<th style="text-align:left;padding:2px 4px;font-weight:500">平台</th>'+
                '<th style="text-align:left;padding:2px 4px;font-weight:500">账号</th>'+
                '<th style="text-align:left;padding:2px 4px;font-weight:500">状态</th>'+
                '<th style="text-align:left;padding:2px 4px;font-weight:500">粉丝</th>'+
                '<th style="padding:2px 4px;font-weight:500">操作</th></tr></thead><tbody>'+
            accts.map(function(a) {
              var icon = a.platform==='xiaohongshu'?'📕':'🎵';
              var platName = a.platform==='xiaohongshu'?'小红书':'抖音';
              var ld = loginDisabled(a);
              var lop = ld?'':"accountLogin('"+a.id+"')";
              var cop = ld?'':"clearCookies('"+a.id+"','"+a.platform+"')";
              var dop = ld?'':"deleteAccount('"+a.id+"')";
              return '<tr>'+
                '<td style="padding:2px 4px">'+icon+' '+platName+'</td>'+
                '<td style="padding:2px 4px;color:var(--text)">'+a.nickname+'</td>'+
                '<td style="padding:2px 4px">'+statusBadge(a)+'</td>'+
                '<td style="padding:2px 4px;color:var(--text2)">'+fmtNum(a.fans)+'</td>'+
                '<td style="padding:2px 4px;white-space:nowrap">'+
                  '<button onclick="'+lop+'" style="background:transparent;border:none;font-size:11px;'+btnStyle(a,ld)+'" title="'+loginTitle(a)+'">🔑</button>'+
                  '<button onclick="'+cop+'" style="background:transparent;border:none;font-size:11px;'+btnStyle(a,ld)+'" title="'+clearTitle(a)+'">🚫</button>'+
                  '<button onclick="'+dop+'" style="background:transparent;border:none;font-size:11px;'+btnStyle(a,ld)+'" title="'+delTitle(a)+'">🗑</button>'+
                '</td></tr>';
            }).join('')+'</tbody></table>'+
            '<div style="margin-top:6px;display:flex;gap:4px;font-size:10px">'+
              '<button onclick="loadSmsAccounts()" style="background:var(--bg3);border:1px solid var(--border);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px;color:var(--text)">🔄 刷新</button>'+
              (g.machine==='本机'||g.machine===window.location.hostname
                ? '<button onclick="loginAllPlatforms(\''+g.phone+'\')" style="background:var(--bg3);border:1px solid var(--border);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px;color:var(--text)">🔄 全部登录</button>'+
                  '<button onclick="collectAllPlatforms(\''+g.phone+'\')" style="background:var(--bg3);border:1px solid var(--border);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px;color:var(--text)">👤 全部采集</button>'+
                  '<button onclick="deleteIdentityByPhone(\''+g.phone+'\')" style="background:rgba(220,38,38,.08);color:var(--red);border:1px solid var(--red);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">🗑 删除身份</button>'
                : '<span style="color:var(--text2);padding:3px 0">📡 操作需在 '+g.machine+' 上执行</span>'
              )+
            '</div></div>';
        }).join('')+'</div>';

      // ═══ 下部: 账号列表（可排序表格 + 搜索 + 统计）═══
      // 统计信息
      var phoneSet = {}; accounts.forEach(function(a){if(a.phone)phoneSet[a.phone]=true;});
      var identitySet = {}; accounts.forEach(function(a){if(a.identity_dir)identitySet[a.identity_dir]=true;});
      var phoneCount = Object.keys(phoneSet).length;
      var identityCount = Object.keys(identitySet).length;
      var totalCount = accounts.length;
      var localCount = accounts.filter(function(a){return a.is_local;}).length;
      var loggedIn = accounts.filter(function(a){return a.has_cookie;}).length;

      // 本机优先排序
      var sortedAccounts = accounts.slice().sort(function(a,b) {
        if (a.is_local && !b.is_local) return -1;
        if (!a.is_local && b.is_local) return 1;
        var ma = machineLabel(a), mb = machineLabel(b);
        if (ma < mb) return -1;
        if (ma > mb) return 1;
        var pa = a.phone||'', pb = b.phone||'';
        if (pa < pb) return -1;
        if (pa > pb) return 1;
        return a.id < b.id ? -1 : (a.id > b.id ? 1 : 0);
      });

      var tableId = 'acctTableBody';
      var sortState = {col:'账号', asc:true};

      var tableHtml = '<div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px;box-shadow:var(--shadow)">'+
        '<div style="font-size:13px;font-weight:600;margin-bottom:6px">📋 全部账号列表</div>'+
        '<div style="display:flex;gap:12px;font-size:11px;color:var(--text2);margin-bottom:8px">'+
          '<span>📱 <strong style="color:var(--text)">'+phoneCount+'</strong> 个手机号</span>'+
          '<span>🆔 <strong style="color:var(--text)">'+identityCount+'</strong> 个身份</span>'+
          '<span>👤 <strong style="color:var(--text)">'+totalCount+'</strong> 个账号</span>'+
          '<span>🎯 <strong style="color:var(--text)">'+localCount+'/'+totalCount+'</strong> 本机</span>'+
          '<span>✅ <strong style="color:var(--green)">'+loggedIn+'</strong> 已登录</span>'+
        '</div>'+
        '<div style="display:flex;gap:6px;margin-bottom:8px">'+
          '<input id="acctSearchInput" placeholder="🔍 搜索账号/手机/昵称..." oninput="filterAcctTable()" style="flex:1;min-width:150px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 10px;border-radius:5px;font-size:12px">'+
          '<select id="acctPlatformFilter" onchange="filterAcctTable()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:5px;font-size:11px">'+
            '<option value="">全部平台</option>'+
            '<option value="douyin">🎵 抖音</option>'+
            '<option value="xiaohongshu">📕 小红书</option>'+
          '</select>'+
          '<select id="acctMachineFilter" onchange="filterAcctTable()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:5px;font-size:11px">'+
            '<option value="">全部机器</option>'+
            '<option value="local">本机</option>'+
            '<option value="remote">远程</option>'+
          '</select>'+
          '<select id="acctStatusFilter" onchange="filterAcctTable()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:5px;font-size:11px">'+
            '<option value="">全部状态</option>'+
            '<option value="logged_in">已登录</option>'+
            '<option value="not_logged">未登录</option>'+
          '</select>'+
        '</div>'+
        '<div style="max-height:400px;overflow-y:auto">'+
        '<table style="width:100%;font-size:12px"><thead><tr>'+
          '<th onclick="sortAcctTable(0)" style="cursor:pointer;text-align:left;padding:4px 6px;font-weight:500;font-size:11px;color:var(--text2);user-select:none">账号 <span style="font-size:9px">▲</span></th>'+
          '<th onclick="sortAcctTable(1)" style="cursor:pointer;text-align:left;padding:4px 6px;font-weight:500;font-size:11px;color:var(--text2);user-select:none">平台</th>'+
          '<th onclick="sortAcctTable(2)" style="cursor:pointer;text-align:left;padding:4px 6px;font-weight:500;font-size:11px;color:var(--text2);user-select:none">手机</th>'+
          '<th onclick="sortAcctTable(3)" style="cursor:pointer;text-align:left;padding:4px 6px;font-weight:500;font-size:11px;color:var(--text2);user-select:none">机器</th>'+
          '<th onclick="sortAcctTable(4)" style="cursor:pointer;text-align:center;padding:4px 6px;font-weight:500;font-size:11px;color:var(--text2);user-select:none">状态</th>'+
          '<th onclick="sortAcctTable(5)" style="cursor:pointer;text-align:left;padding:4px 6px;font-weight:500;font-size:11px;color:var(--text2);user-select:none">昵称</th>'+
          '<th style="padding:4px 6px;font-weight:500;font-size:11px;color:var(--text2)">操作</th></tr></thead>'+
          '<tbody id="'+tableId+'">'+
        sortedAccounts.map(function(a, idx) {
          var ml = machineLabel(a);
          var icon = a.platform==='xiaohongshu'?'📕':'🎵';
          var platName = a.platform==='xiaohongshu'?'小红书':'抖音';
          var ld = loginDisabled(a);
          var lop = ld?'':"accountLogin('"+a.id+"')";
          var cop = ld?'':"clearCookies('"+a.id+"','"+a.platform+"')";
          var dop = ld?'':"deleteAccount('"+a.id+"')";
          return '<tr data-idx="'+idx+'" data-phone="'+(a.phone||'')+'" data-platform="'+a.platform+'" data-machine="'+(a.is_local?'local':'remote')+'" data-login="'+(a.has_cookie?'yes':'no')+'" data-search="'+(a.id+' '+(a.phone||'')+' '+a.nickname).toLowerCase()+'">'+
            '<td style="padding:3px 6px;font-size:11px">'+a.id+'</td>'+
            '<td style="padding:3px 6px;font-size:11px">'+icon+' '+platName+'</td>'+
            '<td style="padding:3px 6px;font-size:10px;color:var(--text2)">'+(a.phone||'')+'</td>'+
            '<td style="padding:3px 6px;font-size:10px;color:var(--primary)">'+ml+'</td>'+
            '<td style="padding:3px 6px;text-align:center;font-size:11px">'+(a.has_cookie?'✅':'❌')+'</td>'+
            '<td style="padding:3px 6px;font-size:11px">'+a.nickname+'</td>'+
            '<td style="padding:3px 6px;white-space:nowrap;font-size:11px">'+
              '<button onclick="'+lop+'" style="background:transparent;border:none;cursor:pointer;'+btnStyle(a,ld)+'" title="'+loginTitle(a)+'">🔑</button>'+
              '<button onclick="'+cop+'" style="background:transparent;border:none;cursor:pointer;'+btnStyle(a,ld)+'" title="'+clearTitle(a)+'">🚫</button>'+
              '<button onclick="'+dop+'" style="background:transparent;border:none;cursor:pointer;'+btnStyle(a,ld)+'" title="'+delTitle(a)+'">🗑</button>'+
            '</td></tr>';
        }).join('')+'</tbody></table></div></div>';
      // 保存accounts数据供排序筛选用（使用已排序的列表）
      window._acctTableData = sortedAccounts;

      overview.innerHTML = cardsHtml + tableHtml;
    }
  } catch(e) {
    if (overview) overview.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>';
  }
}

// ── 短信账号搜索 ──
function smsFilterAccounts() {
  const input = document.getElementById('smsAccountSearch');
  const sel = document.getElementById('smsAccountSelect');
  if (!input || !sel) return;
  if (!window._smsAccountOptions) {
    sel.innerHTML = '<option value="">⏳ 账号列表加载中...</option>';
    sel.style.display = 'block';
    return;
  }
  const opts = window._smsAccountOptions;
  const q = input.value.trim().toLowerCase();

  // 构建匹配选项
  let matched = [];
  if (!q) {
    matched = opts.slice(0, 30); // 无输入时显示前30个
  } else {
    matched = opts.filter(a => {
      const phone = (a.phone || '').toLowerCase();
      const nick = (a.nickname || '').toLowerCase();
      const id = (a.id || '').toLowerCase();
      // 支持输入任意连续几位号码匹配
      return phone.includes(q) || nick.includes(q) || id.includes(q) ||
        // 手机号后4位/后6位匹配
        (phone.endsWith(q)) || phone.startsWith(q);
    });
  }

  sel.innerHTML = '<option value="">— 选择账号 —</option>' +
    matched.map(a => '<option value="'+a.id+'" data-phone="'+(a.phone||'')+'" data-nick="'+(a.nickname||'')+'">'+
      ((a.platform==='xiaohongshu'?'📕':'🎵')+' '+a.nickname+' '+(a.is_local?'(本机)':'')+' ('+a.phone+')')+'</option>').join('');

  // 如果有精确匹配（输入完全等于某个手机号），自动选中
  if (q.length >= 4) {
    const exact = opts.find(a => a.phone === input.value.trim());
    if (exact) {
      sel.value = exact.id;
      smsSelectAccount();
      smsCheckSelected();
      sel.style.display = 'none';
      return;
    }
  }

  // 显示下拉列表
  sel.style.display = 'block';
  sel.size = Math.min(matched.length + 1, 8);
  sel.selectedIndex = 0;
}

// 点击外部关闭下拉
document.addEventListener('click', function(e) {
  const sel = document.getElementById('smsAccountSelect');
  const input = document.getElementById('smsAccountSearch');
  if (sel && input && !e.target.closest('#smsAccountSearch') && !e.target.closest('#smsAccountSelect')) {
    sel.style.display = 'none';
  }
});

function smsSelectAccount() {
  const sel = document.getElementById('smsAccountSelect');
  const info = document.getElementById('smsSelectedAccount');
  const input = document.getElementById('smsAccountSearch');
  if (!sel || !info) return;
  const opt = sel.options[sel.selectedIndex];
  if (!opt || !opt.value) { info.innerHTML = ''; return; }
  const nick = opt.getAttribute('data-nick') || opt.value;
  const phone = opt.getAttribute('data-phone') || '';
  info.innerHTML = '<span style="color:var(--green)">'+nick+'</span> <span style="color:var(--text2)">('+phone+')</span>';
  // 同步更新搜索框
  if (input) {
    input.value = phone || opt.textContent.trim();
    document.getElementById('smsAccountSelect').style.display = 'none';
  }
}

// ── 格式化时间 ──
function fmtSmsTime(t) {
  if (!t) return '';
  // 如果已有格式化时间字符串 (如 "2026-06-14 10:30")，截取时分
  if (typeof t === 'string' && t.includes('-')) {
    const parts = t.split(' ');
    if (parts.length >= 2) {
      const date = parts[0].slice(5); // "06-14"
      const time = parts[1].slice(0, 5); // "10:30"
      return date+' '+time;
    }
    return t.slice(0, 16);
  }
  return t;
}

async function smsCheckSelected() {
  const sel = document.getElementById('smsAccountSelect');
  const el = document.getElementById('smsTestResult');
  const msgEl = document.getElementById('smsMessages');
  if (!sel || !sel.value) { alert('请先选择一个账号'); return; }
  const opt = sel.options[sel.selectedIndex];
  const phone = opt.getAttribute('data-phone');
  if (!phone) { if (el) el.innerHTML = '❌ 该账号无手机号'; return; }
  if (el) el.innerHTML = '⏳ 查询...';
  if (msgEl) msgEl.innerHTML = '';
  try {
    const r = await fetch('/api/matrix/sms/test/'+encodeURIComponent(phone));
    const d = await r.json();
    if (el) el.innerHTML = d.status==='ok' ? '✅ '+d.total+'条消息' : '❌ '+d.error;
    if (msgEl) {
      if (d.status !== 'ok') { msgEl.innerHTML = '<span style="color:var(--red)">'+d.error+'</span>'; return; }
      msgEl.innerHTML = (d.messages||[]).map(m => '<div style="padding:3px 0;border-bottom:1px solid var(--border);font-size:11px">'+
        (m.code ? '<span style="color:var(--green)">✅ 验证码 '+m.code+'</span>' : '📩')+
        ' <span style="color:var(--text2);font-size:10px">'+((m.content||'').slice(0,60))+'</span>'+
        '<span style="color:#6366f1;font-size:9px;float:right">'+fmtSmsTime(m.time)+'</span>'+
      '</div>').join('') || '<div style="color:var(--text2);font-size:11px;padding:4px 0">无短信记录</div>';
    }
  } catch(e) { if (msgEl) msgEl.innerHTML = '<span style="color:var(--red)">'+e.message+'</span>'; }
}

async function loadPhonePresets() {
  const list = document.getElementById('smsPhoneList');
  if (!list) return;
  try {
    const r = await fetch('/api/matrix/accounts');
    const d = await r.json();
    const phones = new Set();
    Object.values(d).forEach(arr => (arr||[]).forEach(a => {
      const p = a.phone || a.phone_mask || '';
      if (p && p.length >= 11) phones.add(p);
    }));
    list.innerHTML = [...phones].map(p => `<option value="${p}">`).join('');
  } catch(e) { /* ignore */ }
}

async function loadSmsConfig() {
  const el = document.getElementById('smsConfigPanel');
  if (!el) return;
  try {
    const r = await fetch('/api/matrix/sms/config');
    const d = await r.json();
    el.innerHTML = `<div style="margin-bottom:4px"><span style="color:var(--text2)">API:</span> <code>${(d.base_url||'').slice(0,35)}</code></div>
      <div style="margin-bottom:4px"><span style="color:var(--text2)">当前手机号:</span> <strong style="color:var(--green)">${d.phone||'-'}</strong></div>
      <div><span style="color:var(--text2)">Key:</span> <code>${d.api_key||'-'}</code> | 轮询 ${d.poll_interval||3}s</div>`;
    if (d.phone) smsQuery(d.phone);
  } catch(e) { el.innerHTML = '<span style="color:var(--red)">'+e.message+'</span>'; }
}

async function smsUpdateAndTest() {
  const phone = document.getElementById('smsNewPhone')?.value;
  if (!phone) { alert('输入手机号'); return; }
  const el = document.getElementById('smsTestResult');
  const msgEl = document.getElementById('smsMessages');
  if (el) el.innerHTML = '⏳ 切换...';
  if (msgEl) msgEl.innerHTML = '';
  try {
    const r = await fetch('/api/matrix/sms/config', {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone})});
    const res = await r.json();
    if (res.status !== 'ok') { if (el) el.innerHTML = '❌ '+res.error; return; }
  } catch(e) { if (el) el.innerHTML = '❌ '+e.message; return; }
  loadSmsConfig();
  if (msgEl) msgEl.innerHTML = '<span style="color:var(--text2)">⏳ 查询...';
  try {
    const r2 = await fetch('/api/matrix/sms/test/'+encodeURIComponent(phone));
    const d2 = await r2.json();
    if (el) el.innerHTML = d2.status==='ok' ? '✅ 已切换, '+d2.total+'条消息' : '❌ '+d2.error;
    if (msgEl) {
      if (d2.status !== 'ok') { msgEl.innerHTML = '<span style="color:var(--red)">'+d2.error+'</span>'; return; }
      msgEl.innerHTML = (d2.messages||[]).map(m => `<div style="padding:3px 0;border-bottom:1px solid var(--border);font-size:11px">
        ${m.code ? '<span style="color:var(--green)">✅ 验证码 '+m.code+'</span>' : '📩'}
        <span style="color:var(--text2);font-size:10px;margin-left:4px">${(m.content||'').slice(0,60)}</span>
        <span style="color:#6366f1;font-size:9px;float:right">${fmtSmsTime(m.time)}</span>
      </div>`).join('') || '<div style="color:var(--text2);font-size:11px;padding:4px 0">无短信记录</div>';
    }
  } catch(e) { if (msgEl) msgEl.innerHTML = '<span style="color:var(--red)">'+e.message+'</span>'; }
}

async function smsQuery(phone) {
  const msgEl = document.getElementById('smsMessages');
  if (!msgEl || !phone) return;
  try {
    const r = await fetch('/api/matrix/sms/test/'+encodeURIComponent(phone));
    const d = await r.json();
    if (d.status !== 'ok') return;
    msgEl.innerHTML = (d.messages||[]).map(m => `<div style="padding:3px 0;border-bottom:1px solid var(--border);font-size:11px">
      ${m.code ? '<span style="color:var(--green)">✅ '+m.code+'</span>' : '📩'}
      <span style="color:var(--text2);font-size:10px;margin-left:4px">${(m.content||'').slice(0,60)}</span>
      <span style="color:#6366f1;font-size:9px;float:right">${fmtSmsTime(m.time)}</span>
    </div>`).join('') || '<div style="color:var(--text2);font-size:11px;padding:4px 0">无短信记录</div>';
  } catch(e) { /* silent */ }
}

// ── 代理面板折叠 ──
function toggleProxyPanel() {
  const body = document.getElementById('proxyPanelBody');
  const icon = document.getElementById('proxyToggleIcon');
  if (!body || !icon) return;
  const isOpen = body.style.display !== 'none';
  body.style.display = isOpen ? 'none' : 'block';
  icon.textContent = isOpen ? '▶ 展开' : '▼ 收起';
  if (!isOpen) loadProxyList();
}

// ── 主页信息折叠 ──
function toggleHomepageInfo() {
  const body = document.getElementById('hpInfoBody');
  const icon = document.getElementById('hpInfoToggle');
  if (!body || !icon) return;
  const isOpen = body.style.display !== 'none';
  body.style.display = isOpen ? 'none' : 'block';
  icon.textContent = isOpen ? '▶ 展开' : '▼ 收起';
  if (!isOpen) loadHomepageInfoSms();
}

async function loadHomepageInfoSms() {
  const el = document.getElementById('hpInfoContent');
  if (!el) return;
  el.innerHTML = '<div class="loading">加载中...</div>';

  try {
    const r = await fetch('/api/matrix/homepage-info');
    const data = await r.json();
    if (data.error) {
      el.innerHTML = '<div style="color:var(--amber);font-size:11px">' + data.error + '</div>';
      return;
    }

    const results = data.results || [];
    const collectedAt = data.collected_at || '';
    const ts = collectedAt ? collectedAt.replace('T',' ').slice(0,19) : '未知';

    const badge = document.getElementById('hpInfoBadge');
    if (badge) badge.textContent = '(' + results.length + ' 个身份 · ' + ts.slice(5,16) + ')';

    let html = '<div style="color:#6366f1;font-size:10px;margin-bottom:4px">🕐 采集时间: ' + ts + '</div>';
    html += '<table style="width:100%;border-collapse:collapse;font-size:10px"><thead><tr style="background:var(--bg3)">';
    html += '<th style="padding:3px 6px;text-align:left">身份</th>';
    html += '<th style="padding:3px 6px;text-align:left">手机</th>';
    html += '<th style="padding:3px 6px;text-align:left">🎵 抖音</th>';
    html += '<th style="padding:3px 6px;text-align:right">粉丝</th>';
    html += '<th style="padding:3px 6px;text-align:left">📕 小红书</th>';
    html += '<th style="padding:3px 6px;text-align:right">粉丝</th>';
    html += '</tr></thead><tbody>';

    results.forEach(function(r) {
      const dy = r.douyin || {};
      const xhs = r.xiaohongshu || {};
      const dyOk = dy.nickname && dy.nickname.indexOf('登录后') === -1;
      const xhsOk = xhs.nickname && xhs.nickname.indexOf('问点点') === -1 && xhs.nickname.indexOf('推荐') === -1;
      html += '<tr style="border-top:1px solid var(--border)">';
      html += '<td style="padding:3px 6px">' + (r.display_name||'?') + '</td>';
      html += '<td style="padding:3px 6px;color:var(--text2);font-size:9px">' + (r.phone||'-') + '</td>';
      html += '<td style="padding:3px 6px">' + (dyOk ? dy.nickname : '<span style="color:var(--text2);font-style:italic">(无)</span>') + '</td>';
      html += '<td style="padding:3px 6px;text-align:right;color:var(--text2)">' + (dyOk ? (dy.fans||'-') : '-') + '</td>';
      html += '<td style="padding:3px 6px">' + (xhsOk ? xhs.nickname : '<span style="color:var(--text2);font-style:italic">(无)</span>') + '</td>';
      html += '<td style="padding:3px 6px;text-align:right;color:var(--text2)">' + (xhsOk ? (xhs.fans||'-') : '-') + '</td>';
      html += '</tr>';
    });

    html += '</tbody></table>';

    let suc = 0;
    results.forEach(function(r) {
      const d = r.douyin, x = r.xiaohongshu;
      if ((d && d.nickname && d.nickname.indexOf('登录后') === -1) ||
          (x && x.nickname && x.nickname.indexOf('问点点') === -1 && x.nickname.indexOf('推荐') === -1)) {
        suc++;
      }
    });
    html += '<div style="margin-top:4px;font-size:9px;color:var(--text2)">✅ 成功: ' + suc + '/' + results.length + '  &nbsp; 采集: mc collect --all</div>';

    el.innerHTML = html;
  } catch(e) {
    el.innerHTML = '<div style="color:var(--red);font-size:11px">' + e.message + '</div>';
  }
}

// ── 采集历史 ──
function toggleCollectHistory() {
  const body = document.getElementById('chBody');
  const icon = document.getElementById('chToggle');
  if (!body || !icon) return;
  const isOpen = body.style.display !== 'none';
  body.style.display = isOpen ? 'none' : 'block';
  icon.textContent = isOpen ? '▶ 展开' : '▼ 收起';
  if (!isOpen) loadCollectHistory();
}

async function loadCollectHistory() {
  const el = document.getElementById('chContent');
  if (!el) return;
  el.innerHTML = '<div class="loading">加载中...</div>';
  try {
    const r = await fetch('/api/matrix/homepage-history');
    const data = await r.json();
    const history = data.history || [];
    if (!history.length) {
      el.innerHTML = '<div style="color:var(--text2);font-size:11px">暂无采集历史</div>';
      return;
    }

    // 时间倒序
    history.reverse();

    let html = '<table style="width:100%;border-collapse:collapse;font-size:10px"><thead><tr style="background:var(--bg3)">';
    html += '<th style="padding:3px 6px;text-align:left">#</th>';
    html += '<th style="padding:3px 6px;text-align:left">采集时间</th>';
    html += '<th style="padding:3px 6px;text-align:right">身份</th>';
    html += '<th style="padding:3px 6px;text-align:right">账号</th>';
    html += '<th style="padding:3px 6px;text-align:right">成功</th>';
    html += '<th style="padding:3px 6px;text-align:right">失败</th>';
    html += '</tr></thead><tbody>';

    history.forEach(function(h, i) {
      const ts = (h.collected_at || '').replace('T',' ').slice(0,19);
      const bg = i % 2 === 0 ? '' : 'background:#1e2133';
      html += '<tr style="border-top:1px solid var(--border);' + bg + '">';
      html += '<td style="padding:3px 6px">' + (history.length - i) + '</td>';
      html += '<td style="padding:3px 6px;color:#6366f1">' + ts.slice(5,16) + '</td>';
      html += '<td style="padding:3px 6px;text-align:right">' + (h.total_identities||'?') + '</td>';
      html += '<td style="padding:3px 6px;text-align:right">' + (h.total_accounts||'?') + '</td>';
      html += '<td style="padding:3px 6px;text-align:right;color:var(--green)">' + (h.success||0) + '</td>';
      html += '<td style="padding:3px 6px;text-align:right;color:var(--red)">' + (h.failed||0) + '</td>';
      html += '</tr>';
    });

    html += '</tbody></table>';
    html += '<div style="margin-top:4px;font-size:9px;color:var(--text2)">📜 共 ' + history.length + ' 次采集记录</div>';

    el.innerHTML = html;
  } catch(e) {
    el.innerHTML = '<div style="color:var(--red);font-size:11px">' + e.message + '</div>';
  }
}

// ── Proxy ──
async function proxyTest() {
  const proxy = document.getElementById('proxyTestInput')?.value;
  const el = document.getElementById('proxyTestResult');
  if (!proxy) { alert('输入代理地址'); return; }
  if (el) el.innerHTML = '<span style="color:var(--text2)">⏳ 测试中...</span>';
  try {
    const r = await fetch('/api/matrix/proxies/test', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proxy})});
    const d = await r.json();
    if (el) {
      if (d.status === 'ok') el.innerHTML = `<span style="color:var(--green)">✅ ${d.ip||'?'} | ${d.type||'HTTP'} | ${d.elapsed||'?'}</span>`;
      else el.innerHTML = `<span style="color:var(--red)">❌ ${d.error}</span>`;
    }
  } catch(e) { if (el) el.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>'; }
}

async function loadProxyList() {
  const el = document.getElementById('proxyList');
  if (!el) return;
  try {
    const r = await fetch('/api/matrix/proxies');
    const d = await r.json();
    const proxies = d.proxies||[];
    if (!proxies.length) { el.innerHTML = '<div style="color:var(--text2);font-size:12px">无本地账号</div>'; return; }
    el.innerHTML = proxies.map(p => `<div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:6px;font-size:12px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div><strong>${p.account}</strong> <span style="color:var(--text2);font-size:10px">${p.platform}</span>
          <span style="font-size:10px;margin-left:6px;color:${p.login_status==='logged_in'?'#22c55e':(p.login_status==='remote'?'#8b8fa3':'#f59e0b')}">${p.login_status}</span>
        </div>
        <div><span style="color:${p.has_proxy?'#22c55e':'#8b8fa3'};font-size:10px">${p.proxy||'无代理'}</span></div>
      </div>
      <div style="margin-top:4px;display:flex;gap:4px;align-items:center">
        <input placeholder="绑定代理地址" style="flex:1;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px" id="proxy_${p.account}">
        <button onclick="setProxy('${p.account}')" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">绑定</button>
        <button onclick="testAccountProxy('${p.account}')" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">测试</button>
        <span id="proxyResult_${p.account}" style="font-size:10px"></span>
      </div>
    </div>`).join('');
  } catch(e) { el.innerHTML = '<span style="color:var(--red)">'+e.message+'</span>'; }
}

async function setProxy(account) {
  const proxy = document.getElementById('proxy_'+account)?.value;
  const el = document.getElementById('proxyResult_'+account);
  if (el) el.innerHTML = '⏳';
  try {
    const r = await fetch('/api/matrix/proxies/'+encodeURIComponent(account), {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({proxy: proxy||''})});
    const res = await r.json();
    if (el) el.innerHTML = res.status==='ok' ? '✅ 已绑定' : '❌';
    loadProxyList();
  } catch(e) { if (el) el.innerHTML = '❌'; }
}

async function testAccountProxy(account) {
  const el = document.getElementById('proxyResult_'+account);
  if (el) el.innerHTML = '⏳';
  try {
    const r = await fetch('/api/matrix/proxies');
    const d = await r.json();
    const p = (d.proxies||[]).find(x => x.account === account);
    if (!p || !p.proxy) { if (el) el.innerHTML = '❌ 无代理'; return; }
    const r2 = await fetch('/api/matrix/proxies/test', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proxy: p.proxy})});
    const d2 = await r2.json();
    if (el) {
      if (d2.status === 'ok') el.innerHTML = `✅ ${d2.ip||'?'} | ${d2.elapsed||'?'}`;
      else el.innerHTML = '❌ '+d2.error;
    }
  } catch(e) { if (el) el.innerHTML = '❌ '+e.message; }
}

// ── Notes editing ──
function editNote(id) {
  const row = document.querySelector(`.notes-display[data-account="${id}"]`);
  const edit = document.querySelector(`.notes-edit[style*="display:none"]`);
  if (row) row.style.display = 'none';
  if (edit) edit.style.display = 'inline';
}

async function saveNote(id) {
  const input = document.querySelector(`.notes-input[data-account="${id}"]`);
  if (!input) return;
  const notes = input.value.trim();
  try {
    const r = await fetch(`/api/matrix/accounts/${id}`, {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({notes})
    });
    if (!r.ok) throw new Error((await r.json()).detail);
    // Toggle back
    const display = document.querySelector(`.notes-display[data-account="${id}"]`);
    if (display) { display.textContent = notes.slice(0,10) || '-'; display.style.display = 'inline'; }
    input.closest('span.notes-edit').style.display = 'none';
  } catch(e) { alert('❌ '+e.message); }
}

function editDialog(id) {
  alert('完整编辑功能请在独立管理页操作: /matrix-mgmt');
}

// ════════════════════════════════════════════════════════
// Corpus Management
// ════════════════════════════════════════════════════════

async function loadCorpus() {
  const el = document.getElementById('corpusContent');
  const meta = document.getElementById('corpusMeta');
  if (!el) return;
  el.innerHTML = '<div class="loading">加载中...</div>';
  try {
    const r = await fetch('/api/matrix/corpus');
    const d = await r.json();
    const cats = d.categories || [];
    meta.textContent = `共 ${cats.length} 个分类 · ${d.total_comments||0} 条评论`;

    let html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px">';

    // Group by platform
    const groups = {};
    cats.forEach(c => {
      const p = c.platform === 'xiaohongshu' ? '📕 小红书' : '🎵 抖音';
      if (!groups[p]) groups[p] = [];
      groups[p].push(c);
    });

    Object.entries(groups).forEach(([platform, items]) => {
      html += `<div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:14px;margin-bottom:10px">${platform}</div>
        <table><thead><tr><th>分类</th><th>权重</th><th>评论数</th><th>状态</th><th>操作</th></tr></thead><tbody>
        ${items.map(c => `<tr>
          <td><strong>${c.name}</strong></td>
          <td>${c.weight}</td>
          <td>${c.count}</td>
          <td>${c.enabled ? '<span class="badge badge-green">✅ 启用</span>' : '<span class="badge badge-gray">⏸ 停用</span>'}</td>
          <td><button class="btn btn-sm btn-outline" onclick="corpusShowDetail('${c.platform}','${c.name}')">📝</button></td>
        </tr>`).join('')}
        </tbody></table>
      </div>`;
    });
    html += '</div>';

    // Add comment form
    html += `<div style="margin-top:12px;background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
      <div style="font-weight:600;font-size:13px;margin-bottom:8px">✏️ 添加评论</div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <select id="corpusAddPlatform" style="width:120px">
          <option value="douyin">🎵 抖音</option>
          <option value="xiaohongshu">📕 小红书</option>
        </select>
        <input id="corpusAddCategory" placeholder="分类名" style="width:100px">
        <input id="corpusAddText" placeholder="评论内容" style="flex:1;min-width:200px">
        <button class="btn btn-primary btn-sm" onclick="corpusAdd()">+ 添加</button>
        <span id="corpusAddResult" style="font-size:12px"></span>
      </div>
    </div>
    <!-- 批量导入 -->
    <div style="margin-top:8px;background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
      <div style="font-weight:600;font-size:13px;margin-bottom:8px">📥 批量导入</div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px">
        <select id="corpusBatchPlatform" style="width:120px">
          <option value="douyin">🎵 抖音</option>
          <option value="xiaohongshu">📕 小红书</option>
        </select>
        <input id="corpusBatchCategory" placeholder="分类名" style="width:100px">
        <button class="btn btn-primary btn-sm" onclick="corpusBatchImport()">📥 导入</button>
        <span id="corpusBatchResult" style="font-size:12px"></span>
      </div>
      <textarea id="corpusBatchTexts" placeholder="每行一条评论，直接粘贴即可&#10;例：&#10;讲得太好了，受益匪浅！&#10;这个观点很新颖，学习了&#10;干货满满，感谢分享" style="width:100%;height:100px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:8px;border-radius:5px;font-size:12px;font-family:monospace"></textarea>
      <div style="font-size:10px;color:var(--text2);margin-top:4px">支持粘贴、拖入 txt 文件（点击下方「选择文件」或直接粘贴内容）</div>
    </div>
    <!-- 格式模板 -->
    <div style="margin-top:8px;background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div style="font-weight:600;font-size:13px">📋 格式模板</div>
        <span style="font-size:10px;color:var(--text2);cursor:pointer" onclick="copyTemplate()">📋 复制模板</span>
      </div>
      <pre style="font-size:10px;background:var(--bg2);padding:8px;border-radius:4px;margin-top:6px;overflow-x:auto;white-space:pre-wrap;color:var(--text2)">
# 语料库格式模板 v2.0
# 支持身份(Persona)×场景(Scene)×内容(Content) 三维结构
# 也兼容当前的一维分类格式（categories）

## 一维格式（当前使用）
categories:
  赞美:
    comments:
      - "讲得太好了，受益匪浅！"
      - "干货满满，感谢分享"
  提问:
    comments:
      - "请问这是在哪里？"

## 二维格式（推荐）
personas:
  health_lover:
    name: "养生爱好者"
    tags: ["养生","健康"]
scenes:
  first_comment:
    label: "首次评论"
content:
  health_lover.first_comment:
    - "这个养生方法很实用"
    - "坚持调理最重要"

## 三维格式（含多轮对话）
content:
  health_lover.follow_up:
    round_1:
      - "确实如此，{keyword}我也是这么认为的"
    round_2:
      - "对，后来我换了一种方法就好了"
      </pre>
    </div>`;

    el.innerHTML = html;
  } catch(e) {
    el.innerHTML = `<div class="error">❌ ${e.message}</div>`;
  }
}

async function corpusAdd() {
  const platform = document.getElementById('corpusAddPlatform')?.value;
  const category = document.getElementById('corpusAddCategory')?.value;
  const text = document.getElementById('corpusAddText')?.value;
  const result = document.getElementById('corpusAddResult');
  if (!category || !text) { result.textContent = '❌ 请输入分类和评论'; return; }
  try {
    const r = await fetch('/api/matrix/corpus/add', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({platform, category, text})
    });
    const d = await r.json();
    if (d.status === 'ok') {
      result.textContent = '✅ 已添加';
      document.getElementById('corpusAddText').value = '';
      loadCorpus();
    } else {
      result.textContent = '❌ '+d.error;
    }
  } catch(e) { result.textContent = '❌ '+e.message; }
}

async function corpusBatchImport() {
  const platform = document.getElementById('corpusBatchPlatform')?.value;
  const category = document.getElementById('corpusBatchCategory')?.value;
  const textsEl = document.getElementById('corpusBatchTexts');
  const result = document.getElementById('corpusBatchResult');
  if (!category || !textsEl?.value.trim()) { result.textContent = '❌ 请输入分类名和评论内容'; return; }
  const texts = textsEl.value.split('\n').filter(t => t.trim());
  result.textContent = '⏳ 导入 ' + texts.length + ' 条...';
  try {
    const r = await fetch('/api/matrix/corpus/batch-add', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({platform, category, texts})
    });
    const d = await r.json();
    if (d.status === 'ok') {
      result.textContent = '✅ 成功导入 ' + d.added + ' 条';
      textsEl.value = '';
      loadCorpus();
    } else {
      result.textContent = '❌ ' + (d.detail || d.error);
    }
  } catch(e) { result.textContent = '❌ ' + e.message; }
}

function copyTemplate() {
  const text = `# 语料库模板 v2.0
# 分类 + 评论（一维）
categories:
  赞美:
    comments:
      - "讲得太好了，受益匪浅！"
  提问:
    comments:
      - "请问这是在哪里？"

# 身份 + 场景 + 内容（三维）
personas:
  health_lover:
    name: "养生爱好者"
    tags: ["养生","健康"]
scenes:
  first_comment:
    label: "首次评论"
content:
  health_lover.first_comment:
    - "这个养生方法很实用"
  health_lover.follow_up:
    round_1:
      - "确实如此，{keyword}我也是这么认为的"
    round_2:
      - "对，后来我换了一种方法就好了"`;
  navigator.clipboard.writeText(text).then(() => alert('✅ 已复制模板')).catch(() => alert('复制失败，请手动选中复制'));
}

let _corpusModalOpen = false;

function corpusShowDetail(platform, category) {
  if (_corpusModalOpen) return;
  _corpusModalOpen = true;

  // Create modal
  const modal = document.createElement('div');
  modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:9999';
  modal.innerHTML = `<div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:20px;max-width:600px;width:90%;max-height:70vh;display:flex;flex-direction:column">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <span style="font-weight:600;font-size:15px">📚 ${platform}/${category}</span>
      <span style="cursor:pointer;font-size:20px" onclick="this.closest('div[style*=\\'fixed\\']').remove();_corpusModalOpen=false">✕</span>
    </div>
    <div id="corpusDetailBody" style="flex:1;overflow-y:auto;padding:4px 0">
      <div style="text-align:center;color:var(--text2);padding:20px">加载中...</div>
    </div>
    <div style="margin-top:10px;display:flex;gap:6px">
      <input id="corpusDetailAddText" placeholder="添加评论..." style="flex:1">
      <button class="btn btn-primary btn-sm" onclick="corpusDetailAdd()">添加</button>
    </div>
  </div>`;
  document.body.appendChild(modal);

  // Load comments
  fetch(`/api/matrix/corpus/detail?platform=${platform}&category=${encodeURIComponent(category)}`)
    .then(r => r.json())
    .then(d => {
      const body = document.getElementById('corpusDetailBody');
      if (!body) return;
      const allComments = [...(d.comments||[]).map((c,i) => ({type:'comment', text:c, index:i})),
                          ...(d.templates||[]).map((t,i) => ({type:'template', text:t, index:i+999}))];
      if (!allComments.length) {
        body.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text2)">暂无评论</div>';
        return;
      }
      body.innerHTML = allComments.map((item,i) => `<div style="display:flex;align-items:center;gap:6px;padding:5px 0;border-bottom:1px solid var(--border)">
        <span style="font-size:10px;color:var(--text2);width:40px;flex-shrink:0">#${i+1}${item.type==='template'?' 📝':''}</span>
        <span style="flex:1;font-size:12px">${item.text}</span>
        <span style="cursor:pointer;color:var(--red);font-size:14px;opacity:.5" onclick="corpusDetailDelete('${platform}','${category}',${item.index >= 999 ? -1 : item.index})">✕</span>
      </div>`).join('');
    })
    .catch(e => {
      const body = document.getElementById('corpusDetailBody');
      if (body) body.innerHTML = `<div style="color:var(--red);text-align:center;padding:20px">❌ ${e.message}</div>`;
    });
}

async function corpusDetailAdd() {
  const input = document.getElementById('corpusDetailAddText');
  if (!input || !input.value.trim()) return;
  const modal = input.closest('div[style*="fixed"]');
  const platform = modal?.querySelector('span')?.textContent?.split('/')[0]?.replace('📚 ','') || 'douyin';
  const category = modal?.querySelector('span')?.textContent?.split('/')[1] || '';
  try {
    const r = await fetch('/api/matrix/corpus/add', {method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({platform, category, text: input.value.trim()})});
    const d = await r.json();
    if (d.status === 'ok') {
      input.value = '';
      corpusShowDetail(platform, category);
      loadCorpus();
    }
  } catch(e) { alert(e.message); }
}

async function corpusDetailDelete(platform, category, index) {
  if (index === -1) { alert('模板暂不支持看板删除，请使用 CLI'); return; }
  if (!confirm(`删除第 ${index+1} 条评论？`)) return;
  try {
    const r = await fetch('/api/matrix/corpus/delete', {method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({platform, category, index})});
    const d = await r.json();
    if (d.status === 'ok') {
      // Close old modal, reopen
      document.querySelector('div[style*="fixed"]')?.remove();
      _corpusModalOpen = false;
      corpusShowDetail(platform, category);
      loadCorpus();
    }
  } catch(e) { alert(e.message); }
}

// ── Git Sync ──
async function gitSync() {
  var btn = document.querySelector('[onclick="gitSync()"]');
  if (!btn) return;
  btn.textContent = 'sync...';
  btn.style.opacity = '0.5';
  try {
    var r = await fetch('/api/git-sync', {method: 'POST'});
    var res = await r.json();
    btn.textContent = 'done';
    setTimeout(function(){ btn.textContent = 'sync'; btn.style.opacity = '1'; }, 2000);
    if (typeof loadMachines === 'function') loadMachines();
    if (typeof loadStats === 'function') loadStats();
  } catch(e) {
    btn.textContent = 'err';
    setTimeout(function(){ btn.textContent = 'sync'; btn.style.opacity = '1'; }, 2000);
  }
}

// ── 账号注册 ──
async function accountRegister() {
  const plat = document.getElementById('regPlatform')?.value;
  const phone = document.getElementById('regPhone')?.value;
  const nick = document.getElementById('regNickname')?.value;
  const statusEl = document.getElementById('regStatus');
  if (!phone) { alert('请输入手机号'); return; }
  if (statusEl) statusEl.innerHTML = '<span style="color:var(--text2)">⏳ 注册中...</span>';
  try {
    const r = await fetch('/api/matrix/accounts/register', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({platform:plat, phone:phone, nickname:nick})
    });
    const d = await r.json();
    if (d.status === 'ok') {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">✅ '+d.message+'</span>'+
        '<div style="margin-top:4px;font-size:10px;color:var(--text2)">账号ID: '+d.account_id+' | 登录后可以采集昵称</div>';
      document.getElementById('regPhone').value = '';
      document.getElementById('regNickname').value = '';
      setTimeout(loadSmsAccounts, 2000);
    } else {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ '+(d.error||'注册失败')+'</span>';
    }
  } catch(e) {
    if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>';
  }
}

// ════════════════════════════════════════════════════════
// Operation Router — 统一操作路由 (本地/远程)
// ════════════════════════════════════════════════════════

function _getAccountById(accountId) {
  return (window._lastSmsAccounts || []).find(function(a){return a.id===accountId;});
}

async function _getMachineStatus(machineName) {
  try {
    var r = await fetch('/api/federation/machine-status/'+encodeURIComponent(machineName));
    return await r.json();
  } catch(e) {
    return {status: 'error', message: '查询失败'};
  }
}

async function _routeOperation(accountId, opType, params) {
  var account = _getAccountById(accountId);
  if (!account) return {status: 'error', message: '账号不存在'};

  var targetMachine = account.owner_machine || (account.is_local ? window.location.hostname : '远程');
  var isLocal = !targetMachine || targetMachine === window.location.hostname;
  var statusEl = document.getElementById('collectProfileStatus');

  if (!isLocal) {
    // 远程执行
    if (statusEl) statusEl.innerHTML = '⏳ 通过 '+targetMachine+' 远程执行...';
    var ep = '';
    var body = {machine: targetMachine, account: accountId};
    if (opType === 'login') ep = '/api/federation/login';
    else if (opType === 'logout') ep = '/api/federation/logout';
    else if (opType === 'comment') { ep = '/api/federation/comment'; body.url = params.url; if (params.direction) body.direction = params.direction; }
    else if (opType === 'nurture') { ep = '/api/federation/nurture'; body.accounts = [accountId]; body.blueprints = params.blueprints || ['douyin_daily']; body.rounds = params.rounds || 3; }
    else if (opType === 'collect') { ep = '/api/federation/collect'; body.phone = params.phone || ''; }
    else return {status: 'error', message: '未知操作类型: '+opType};

    try {
      var r = await fetch(ep, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
      return await r.json();
    } catch(e) {
      return {status: 'error', message: e.message};
    }
  }

  // 本地执行
  if (statusEl) statusEl.innerHTML = '⏳ 正在执行...';
  if (opType === 'login') {
    var r = await fetch('/api/matrix/accounts/'+accountId+'/login', {method:'POST'});
    return await r.json();
  }
  if (opType === 'logout') {
    var r = await fetch('/api/matrix/accounts/'+accountId+'/clear-cookies', {method:'POST'});
    return await r.json();
  }
  return {status: 'error', message: '本地不支持操作: '+opType};
}

// ── 账号登录（带操作路由）──
async function accountLogin(accountId) {
  if (!accountId) return;
  var account = _getAccountById(accountId);
  if (!account) return;
  var machine = account.owner_machine || (account.is_local ? '本机' : '远程');
  if (!confirm('打开浏览器登录 '+accountId+' ？('+machine+')')) return;
  var result = await _routeOperation(accountId, 'login', {});
  var statusEl = document.getElementById('collectProfileStatus');
  if (statusEl) {
    if (result.status === 'ok' || result.returncode === 0) {
      statusEl.innerHTML = '<span style="color:var(--green)">✅ 登录命令已发送到 '+machine+'</span>';
    } else {
      statusEl.innerHTML = '<span style="color:var(--red)">❌ '+(result.message||result.error||'失败')+'</span>';
    }
  }
}

// ── 清除登录状态（带操作路由）──
async function clearCookies(accountId, platform) {
  if (!accountId) return;
  var account = _getAccountById(accountId);
  if (!account) return;
  var machine = account.owner_machine || (account.is_local ? '本机' : '远程');
  var platName = platform === 'xiaohongshu' ? '小红书' : '抖音';
  if (!confirm('清除 '+accountId+' ('+platName+') 的登录状态？('+machine+')')) return;
  var result = await _routeOperation(accountId, 'logout', {});
  var statusEl = document.getElementById('collectProfileStatus');
  if (statusEl) {
    if (result.status === 'ok' || result.returncode === 0) {
      statusEl.innerHTML = '<span style="color:var(--green)">✅ 清除命令已发送到 '+machine+'</span>';
      loadSmsAccounts().catch(function(){});
    } else {
      statusEl.innerHTML = '<span style="color:var(--red)">❌ '+(result.message||result.error||'清除失败')+'</span>';
    }
  }
}

// ── 全部登录 / 全部采集 / 删除整个身份 ──
async function loginAllPlatforms(phone) {
  const accts = (window._lastSmsAccounts || []).filter(a => a.is_local && a.phone === phone);
  if (!accts.length) return;
  if (!confirm('打开浏览器登录 '+phone+' 下所有平台（共 '+accts.length+' 个）？')) return;
  const statusEl = document.getElementById('collectProfileStatus');
  for (const a of accts) {
    if (statusEl) statusEl.innerHTML = '⏳ 正在登录 '+a.id+'...';
    try {
      await fetch('/api/matrix/accounts/'+a.id+'/login', { method:'POST' });
      await new Promise(r => setTimeout(r, 3000));
    } catch(e) { /* ignore */ }
  }
  if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">✅ 全部登录已启动</span>';
}

async function collectAllPlatforms(phone) {
  const accts = (window._lastSmsAccounts || []).filter(a => a.is_local && a.phone === phone);
  if (!accts.length) return;
  if (!confirm('📡 采集 ' + phone + ' 下的 ' + accts.length + ' 个平台？')) return;
  const statusEl = document.getElementById('collectProfileStatus');
  if (statusEl) statusEl.innerHTML = '⏳ 启动采集（仅该身份，不分批）...';
  
  try {
    const r = await fetch('/api/matrix/collect-homepage/phone', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({phone: phone})
    });
    const data = await r.json();
    if (data.status === 'already_running') {
      if (statusEl) statusEl.innerHTML = '⏳ 已有采集任务在运行...';
    } else if (data.status === 'started') {
      if (statusEl) statusEl.innerHTML = '⏳ 采集中（仅 ' + phone + '）...';
      const poll = setInterval(async () => {
        try {
          const pr = await fetch('/api/matrix/collect-homepage/status');
          const ps = await pr.json();
          if (ps.status === 'running') {
            if (statusEl) statusEl.innerHTML = '⏳ 采集中... ' + (ps.completed||0) + '/' + (ps.total_identities||'?');
          } else {
            clearInterval(poll);
            if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">✅ 采集完成</span>';
            loadSmsAccounts();
          }
        } catch(e) { /* silent */ }
      }, 5000);
    } else {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ ' + (data.error||data.message) + '</span>';
    }
  } catch(e) {
    if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ ' + e.message + '</span>';
  }
}

async function deleteIdentityByPhone(phone) {
  const accts = (window._lastSmsAccounts || []).filter(a => a.is_local && a.phone === phone);
  if (!accts.length) return;
  const msg = '⚠️ 确定要删除 '+phone+' 下的所有账号？\n\n将删除 '+accts.length+' 个账号:\n' + accts.map(a => '  - '+a.id+' ('+a.platform+')').join('\n')+'\n\n以及共享身份目录。';
  if (!confirm(msg)) return;
  const statusEl = document.getElementById('collectProfileStatus');
  for (const a of accts) {
    if (statusEl) statusEl.innerHTML = '⏳ 正在删除 '+a.id+'...';
    try {
      await fetch('/api/matrix/accounts/'+a.id+'?delete_identity=true', { method:'DELETE' });
      await fetch('/api/matrix/accounts/'+a.id+'/cleanup', { method:'POST' });
    } catch(e) { /* ignore */ }
  }
  if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">✅ 已删除 '+phone+' 下所有账号</span>';
  loadSmsAccounts();
}

// ── 删除账号 ──
async function deleteAccount(accountId) {
  if (!accountId) return;
  if (!confirm('确定删除账号 '+accountId+' ？\n身份目录和配置将被清理，不可恢复。')) return;
  const statusEl = document.getElementById('collectProfileStatus');
  if (statusEl) statusEl.innerHTML = '⏳ 正在删除...';
  try {
    // app.py 删除（有 bug，不清理 accounts.yaml）
    const r = await fetch('/api/matrix/accounts/'+accountId+'?delete_identity=true', { method:'DELETE' });
    const d = await r.json();
    // 补清理 accounts.yaml + registry
    await fetch('/api/matrix/accounts/'+accountId+'/cleanup', { method:'POST' });
    if (d.status === 'ok') {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">✅ 已删除，刷新中...</span>';
      // 立即刷新 + 1秒后重试保障
      loadSmsAccounts().catch(e => console.error('refresh err', e));
      setTimeout(() => loadSmsAccounts().catch(e => {}), 1000);
    } else {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ '+(d.error||'失败')+'</span>';
    }
  } catch(e) {
    if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>';
  }
}

// ── 采集昵称 ──
async function collectProfile(accountId) {
  if (!accountId) { alert('请先选择一个账号'); return; }
  const statusEl = document.getElementById('collectProfileStatus');
  if (statusEl) statusEl.innerHTML = '⏳ 正在采集昵称（会打开浏览器）…';
  try {
    const r = await fetch('/api/matrix/accounts/'+accountId+'/collect-profile', { method:'POST' });
    const d = await r.json();
    if (d.status === 'ok') {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">✅ '+d.message+'</span>';
      // 立即刷新 + 3秒后重试保障
      loadSmsAccounts().catch(e => {});
      setTimeout(() => loadSmsAccounts().catch(e => {}), 3000);
    } else {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ '+(d.error||'采集失败')+'</span>';
    }
  } catch(e) {
    if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>';
  }
}

// 定向评论任务已合并到 cmdRunCommentTask（命令与任务页面）

// ════════════════════════════════════════════════════════
// 录制管理
// ════════════════════════════════════════════════════════

async function loadMatrixRecord() {
  const listEl = document.getElementById('recordList');
  const detailEl = document.getElementById('recordDetail');
  const statusEl = document.getElementById('recordStatus');
  if (statusEl) statusEl.innerHTML = '';
  if (detailEl) detailEl.innerHTML = '';
  // 填充账号下拉
  const acctSel = document.getElementById('recordAccountSelect');
  if (acctSel) {
    try {
      const r = await fetch('/api/matrix/sms/accounts');
      const d = await r.json();
      acctSel.innerHTML = '<option value="">选择账号…</option>' +
        (d.accounts||[]).filter(a => a.is_local).map(a =>
          '<option value="'+a.id+'">'+(a.platform==='xiaohongshu'?'📕':'🎵')+' '+a.nickname+'</option>').join('');
    } catch(e) { /* ignore */ }
  }
  // 加载录制包列表
  refreshRecordingList();
}

async function refreshRecordingList() {
  const listEl = document.getElementById('recordList');
  if (!listEl) return;
  const statusEl = document.getElementById('recordStatus');
  listEl.innerHTML = '<div class="loading">加载录制包...</div>';
  try {
    const [listR, statR] = await Promise.all([
      fetch('/api/matrix/recordings'),
      fetch('/api/matrix/recordings/status'),
    ]);
    const list = await listR.json();
    const stat = await statR.json();
    const recordings = list.recordings || [];

    // 更新录制状态
    if (statusEl) {
      if (stat.status === 'running') {
        statusEl.innerHTML = '<span style="color:var(--green)">🔴 录制中 (PID '+stat.pid+')</span>';
        document.getElementById('recordStartBtn').style.display = 'none';
        document.getElementById('recordStopBtn').style.display = '';
      } else {
        statusEl.innerHTML = '<span style="color:var(--text2)">⏸ 空闲</span>';
        document.getElementById('recordStartBtn').style.display = '';
        document.getElementById('recordStopBtn').style.display = 'none';
      }
    }

    if (!recordings.length) {
      listEl.innerHTML = '<div style="color:var(--text2);font-size:13px;padding:20px;text-align:center">暂无录制包<br><span style="font-size:11px">选择一个账号点击「开始录制」，在浏览器中操作并按数字键 1-8 标记，按 0 结束</span></div>';
      return;
    }
    listEl.innerHTML = '<div style="display:grid;gap:6px">'+
      recordings.map(r => '<div style="background:var(--bg3);border-radius:6px;padding:8px 10px;border:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">'+
        '<div><span style="font-weight:600;font-size:12px">'+(r.account||'?')+'</span> '+
        '<span style="color:var(--text2);font-size:10px">'+r.steps+'步 '+(r.duration||0)+'s</span>'+
        '<span style="color:var(--text2);font-size:9px;margin-left:6px">'+(r.created||'').slice(0,16)+'</span></div>'+
        '<div style="display:flex;gap:4px">'+
          '<button onclick="recordingAnalyze(\''+r.file+'\')" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">🔍 分析</button>'+
          '<button onclick="recordingExport(\''+r.file+'\')" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">📦 导出</button>'+
          '<button onclick="recordingDelete(\''+r.file+'\')" style="background:rgba(220,38,38,.08);color:var(--red);border:1px solid var(--red);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">🗑 删除</button>'+
        '</div></div>').join('')+'</div>';
  } catch(e) {
    listEl.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>';
  }
}

async function recordingStart() {
  const sel = document.getElementById('recordAccountSelect');
  if (!sel || !sel.value) { alert('请先选择一个账号'); return; }
  const acct = sel.value;
  try {
    const r = await fetch('/api/matrix/recordings/start', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({account:acct})
    });
    const d = await r.json();
    if (d.status === 'ok') {
      refreshRecordingList();
    } else {
      alert('❌ '+(d.error||d.detail||'启动失败'));
    }
  } catch(e) { alert('❌ '+e.message); }
}

async function recordingStop() {
  try {
    const r = await fetch('/api/matrix/recordings/stop', { method:'POST' });
    const d = await r.json();
    refreshRecordingList();
  } catch(e) { alert('❌ '+e.message); }
}

async function recordingAnalyze(name) {
  const detailEl = document.getElementById('recordDetail');
  if (!detailEl) return;
  detailEl.innerHTML = '<div class="loading">分析中...</div>';
  try {
    const r = await fetch('/api/matrix/recordings/'+encodeURIComponent(name));
    const d = await r.json();
    if (d.error) { detailEl.innerHTML = '<span style="color:var(--red)">❌ '+d.error+'</span>'; return; }
    const actions = d.actions || [];
    const suggestions = d.blueprint_suggestions || [];
    let html = '<div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border);margin-top:6px">'+
      '<div style="font-weight:600;font-size:13px;margin-bottom:6px">🔍 分析结果 ('+d.steps_analyzed+'步)</div>';
    if (actions.length) {
      html += '<div style="font-size:11px;margin-bottom:6px;color:var(--text2)">操作序列:</div>'+
        actions.slice(0,15).map(a => '<div style="font-size:11px;padding:2px 0;border-bottom:1px solid var(--border)">'+
          '<span style="color:#6366f1">'+(a.action_type||'?')+'</span> '+
          '<span style="color:var(--text2)">→ '+(a.action_desc||'')+'</span>'+
        '</div>').join('');
    }
    if (suggestions.length) {
      html += '<div style="font-size:11px;margin-top:6px;color:var(--text2)">蓝图建议:</div>'+
        suggestions.slice(0,5).map(s => '<div style="font-size:11px;padding:2px 0">'+
          '<span style="color:var(--green)">步骤'+s.step+'</span>: '+(s.suggested_op||'')+'</div>').join('');
    }
    html += '</div>';
    detailEl.innerHTML = html;
  } catch(e) { detailEl.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>'; }
}

async function recordingExport(name) {
  const detailEl = document.getElementById('recordDetail');
  if (!detailEl) return;
  detailEl.innerHTML = '<div class="loading">导出中...</div>';
  try {
    const r = await fetch('/api/matrix/recordings/'+encodeURIComponent(name)+'/export', { method:'POST' });
    const d = await r.json();
    if (d.error) { detailEl.innerHTML = '<span style="color:var(--red)">❌ '+d.error+'</span>'; return; }
    let html = '<div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border);margin-top:6px">'+
      '<div style="font-weight:600;font-size:13px;margin-bottom:6px">📦 导出结果</div>'+
      '<div style="font-size:11px">蓝图: <code>'+(d.blueprint_name||'?')+'</code> ('+d.steps+'步)</div>'+
      '<div style="font-size:11px">代码: <code>'+(d.script_name||'?')+'</code></div>'+
      '<div style="font-size:11px;margin-top:4px;color:var(--text2)">导出位置: blueprints/ 和 scripts/recorded_ops/</div>'+
    '</div>';
    detailEl.innerHTML = html;
    refreshRecordingList();
  } catch(e) { detailEl.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>'; }
}

async function recordingDelete(name) {
  if (!confirm('确定删除录制包 '+name+'？')) return;
  try {
    await fetch('/api/matrix/recordings/'+encodeURIComponent(name), { method:'DELETE' });
    refreshRecordingList();
  } catch(e) { alert('❌ '+e.message); }
}

// ════════════════════════════════════════════════════════
// 命令与任务 TAB
// ════════════════════════════════════════════════════════

function switchCmdTab(tab, el) {
  document.querySelectorAll('.cmd-tab').forEach(t => {
    t.style.borderBottom = '2px solid transparent';
    t.style.color = '#8b8fa3';
  });
  el.style.borderBottom = '2px solid #6366f1';
  el.style.color = '#e1e4f0';
  ['cmd-run-content','cmd-comment-content','cmd-schedule-content','cmd-collect-content','cmd-corpus-content','cmd-nurture-content'].forEach(id => {
    document.getElementById(id).style.display = id === tab+'-content' ? 'block' : 'none';
  });
}

async function loadMatrixCommands() {
  // 加载批量执行内容（复用原始 loadMatrixRun 的渲染结果）
  const runEl = document.getElementById('matrixRunContent2');
  if (runEl) {
    // 先渲染原始内容
    await loadMatrixRun();
    // 把渲染结果复制到命令与任务的 TAB 中
    const origEl = document.getElementById('matrixRunContent');
    if (origEl && origEl.innerHTML) {
      runEl.innerHTML = origEl.innerHTML;
      // 持续监控同步（原始内容变化时自动更新）
      if (!window._cmdRunObserver) {
        window._cmdRunObserver = new MutationObserver(() => {
          document.getElementById('matrixRunContent2').innerHTML = origEl.innerHTML;
        });
        window._cmdRunObserver.observe(origEl, { childList: true, subtree: true, characterData: true });
      }
    }
  }
  // 加载定时任务列表
  refreshScheduleList();
  // 填充定时任务的账号下拉
  const schedAcct = document.getElementById('schedAccount');
  if (schedAcct) {
    try {
      const r = await fetch('/api/matrix/sms/accounts');
      const d = await r.json();
      schedAcct.innerHTML = '<option value="">选账号</option>' +
        (d.accounts||[]).filter(a => a.is_local).map(a =>
          '<option value="'+a.id+'">'+(a.platform==='xiaohongshu'?'📕':'🎵')+' '+a.nickname+'</option>').join('');
    } catch(e) { /* ignore */ }
  }

  // 语料库 TAB 绑定（同步原始 corpusContent 到 corpusContent3）
  const corpusEl3 = document.getElementById('corpusContent3');
  const corpusOrig = document.getElementById('corpusContent');
  if (corpusEl3 && corpusOrig && !window._corpusObs3) {
    window._corpusObs3 = new MutationObserver(() => {
      const target = document.getElementById('corpusContent3');
      const src = document.getElementById('corpusContent');
      if (target && src) target.innerHTML = src.innerHTML;
    });
    window._corpusObs3.observe(corpusOrig, { childList: true, subtree: true, characterData: true });
    // 强制加载语料库（无论原始页面是否已加载）
    if (typeof loadCorpus === 'function') {
      loadCorpus().catch(e => console.error('corpus load err', e));
    }
    corpusEl3.innerHTML = corpusOrig.innerHTML || '<div class="loading">加载语料库...</div>';
  }

  // 加载采集模块账号列表
  try {
    const r = await fetch('/api/matrix/sms/accounts');
    const d = await r.json();
    _collectAccounts = d.accounts || [];
    renderCollectList();
  } catch(e) { /* ignore */ }

  // 填充定向评论的账号下拉
  const acctSel = document.getElementById('cmdTaskAccount');
  if (acctSel) {
    try {
      const r = await fetch('/api/matrix/sms/accounts');
      const d = await r.json();
      acctSel.innerHTML = '<option value="">自动选账号</option>' +
        (d.accounts||[]).filter(a => a.is_local).map(a =>
          '<option value="'+a.id+'">'+(a.platform==='xiaohongshu'?'📕':'🎵')+' '+a.nickname+'</option>').join('');
    } catch(e) { /* ignore */ }
  }
}

async function cmdRunCommentTask() {
  const url = document.getElementById('cmdTaskUrl')?.value.trim();
  if (!url) { alert('请填写视频链接'); return; }
  const direction = document.getElementById('cmdTaskDirection')?.value || '';
  const account = document.getElementById('cmdTaskAccount')?.value || '';
  const resultEl = document.getElementById('cmdTaskResult');
  if (resultEl) resultEl.innerHTML = '⏳ 执行中...';
  try {
    const r = await fetch('/api/matrix/task/run', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({type:'comment', url, direction, account})
    });
    const d = await r.json();
    if (resultEl) {
      if (d.status === 'ok') {
        resultEl.innerHTML = '<span style="color:var(--green)">✅ 完成！成功 '+d.success+'/'+d.total+' 步 ('+d.duration+'s)</span>'+
          '<div style="font-size:10px;color:var(--text2);margin-top:2px">'+d.task_summary+'</div>';
      } else {
        resultEl.innerHTML = '<span style="color:var(--red)">❌ '+(d.errors||[d.detail||'失败']).join('; ')+'</span>';
      }
    }
  } catch(e) { if (resultEl) resultEl.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>'; }
}

// ── 从定时任务页面创建 WorkBuddy 任务 ──
async function createAutoTaskFromSchedule() {
  const target = document.getElementById('autoNewTarget')?.value;
  const prompt = document.getElementById('autoNewPrompt')?.value.trim();
  if (!target) { alert('请选择目标机器'); return; }
  if (!prompt) { alert('请输入提示词'); return; }
  try {
    const r = await fetch('/api/kb/automations', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({target, type:'custom', params:prompt})
    });
    const d = await r.json();
    if (d.status === 'ok') {
      alert('✅ 任务已创建');
      document.getElementById('autoNewPrompt').value = '';
      refreshScheduleList();
    } else {
      alert('❌ ' + (d.error || '创建失败'));
    }
  } catch(e) { alert('❌ ' + e.message); }
}

// ════════════════════════════════════════════════════════
// 信息采集（三维选择）
// ════════════════════════════════════════════════════════

var _collectMode = 'identity';
var _collectAccounts = [];

function switchCollectMode(mode, el) {
  _collectMode = mode;
  document.querySelectorAll('.collect-mode').forEach(e => {
    e.style.background = 'var(--bg3)';
    e.style.color = '#e1e4f0';
  });
  el.style.background = '#6366f1';
  el.style.color = '#fff';
  renderCollectList();
}

function renderCollectList() {
  const listEl = document.getElementById('collectList');
  if (!listEl) return;
  const accts = _collectAccounts.filter(a => a.is_local);
  if (!accts.length) { listEl.innerHTML = '<div style="color:var(--text2);padding:6px">暂无本机账号</div>'; return; }

  if (_collectMode === 'identity') {
    // 按手机号分组显示
    const groups = {};
    accts.forEach(a => {
      const phone = a.phone || '未设置手机号';
      if (!groups[phone]) groups[phone] = [];
      groups[phone].push(a);
    });
    listEl.innerHTML = Object.entries(groups).map(([phone, list]) =>
      '<div style="margin:2px 0">' +
      '<label style="cursor:pointer;font-size:12px">' +
      '<input type="checkbox" class="collect-id-item" data-phone="'+phone+'" onchange="toggleCollectIdentity(this)"> ' +
      '📱 ' + phone + ' (' + list.length + '个平台)</label>' +
      list.map(a => '<div style="margin-left:20px;font-size:11px;color:var(--text2)">' +
        (a.platform==='xiaohongshu'?'📕':'🎵')+' '+a.id+' ('+a.nickname+')</div>').join('') +
      '</div>'
    ).join('');
  } else if (_collectMode === 'platform') {
    // 按平台分组
    const groups = { douyin: [], xiaohongshu: [] };
    accts.forEach(a => { if (groups[a.platform]) groups[a.platform].push(a); });
    listEl.innerHTML = Object.entries(groups).filter(g=>g[1].length).map(([plat, list]) =>
      '<div style="margin:2px 0">' +
      '<label style="cursor:pointer;font-size:12px">' +
      '<input type="checkbox" class="collect-plat-item" data-platform="'+plat+'" onchange="toggleCollectPlatform(this)"> ' +
      (plat==='xiaohongshu'?'📕 小红书':'🎵 抖音') + ' (' + list.length + '个账号)</label>' +
      list.map(a => '<div style="margin-left:20px;font-size:11px;color:var(--text2)">' +
        a.id+' ('+a.nickname+')</div>').join('') +
      '</div>'
    ).join('');
  } else {
    // 按账号
    listEl.innerHTML = accts.map(a =>
      '<label style="display:block;cursor:pointer;font-size:12px;padding:2px 0">' +
      '<input type="checkbox" class="collect-acct-item" value="'+a.id+'"> ' +
      (a.platform==='xiaohongshu'?'📕':'🎵')+' '+a.id+' ('+a.nickname+')</label>'
    ).join('');
  }
}

function toggleCollectIdentity(el) {
  // 子账号全选/全不选
  const phone = el.getAttribute('data-phone');
  const checked = el.checked;
  document.querySelectorAll('.collect-acct-item').forEach(cb => {
    if (cb.getAttribute('data-phone') === phone) cb.checked = checked;
  });
}

function toggleCollectPlatform(el) {
  const plat = el.getAttribute('data-platform');
  const checked = el.checked;
  document.querySelectorAll('.collect-acct-item').forEach(cb => {
    if (cb.getAttribute('data-platform') === plat) cb.checked = checked;
  });
}

function getSelectedAccounts() {
  const sel = new Set();
  if (_collectMode === 'identity') {
    document.querySelectorAll('.collect-id-item:checked').forEach(cb => {
      const phone = cb.getAttribute('data-phone');
      _collectAccounts.filter(a => a.is_local && a.phone === phone).forEach(a => sel.add(a.id));
    });
  } else if (_collectMode === 'platform') {
    document.querySelectorAll('.collect-plat-item:checked').forEach(cb => {
      const plat = cb.getAttribute('data-platform');
      _collectAccounts.filter(a => a.is_local && a.platform === plat).forEach(a => sel.add(a.id));
    });
  } else {
    document.querySelectorAll('.collect-acct-item:checked').forEach(cb => sel.add(cb.value));
  }
  return [...sel];
}

async function cmdCollectSelected() {
  const ids = getSelectedAccounts();
  if (!ids.length) { alert('请先选择要采集的账号'); return; }
  const statusEl = document.getElementById('collectStatus');
  const logEl = document.getElementById('collectLog');
  if (logEl) logEl.textContent = '';
  if (statusEl) statusEl.innerHTML = '⏳ 启动批量采集（所有身份，取选中结果）...';

  try {
    const r = await fetch('/api/matrix/collect-homepage', { method: 'POST' });
    const data = await r.json();
    if (data.status === 'already_running') {
      if (statusEl) statusEl.innerHTML = '⏳ 已有任务在运行，等待完成...';
    } else if (data.status !== 'started') {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ 启动失败: ' + (data.error||data.message) + '</span>';
      return;
    }
    if (logEl) logEl.textContent += '🚀 采集任务已启动\n';

    // 轮询进度
    const poll = setInterval(async () => {
      try {
        const pr = await fetch('/api/matrix/collect-homepage/status');
        const ps = await pr.json();
        if (ps.status === 'running') {
          if (statusEl) statusEl.innerHTML = '⏳ 采集中... ' + (ps.completed||0) + '/' + (ps.total_identities||'?') + ' 身份';
          if (logEl) {
            const line = '  ⏳ 进度: ' + (ps.completed||0) + '/' + (ps.total_identities||'?') + ' (成功' + (ps.success||0) + ', 失败' + (ps.failed||0) + ')\n';
            if (!logEl.textContent.includes(line.trim())) logEl.textContent += line;
          }
        } else if (ps.status === 'completed') {
          clearInterval(poll);
          await showCollectReport(ids, statusEl, logEl);
        } else {
          clearInterval(poll);
          if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ 采集异常</span>';
          if (logEl) logEl.textContent += '❌ 状态: ' + ps.status + ' - ' + (ps.message||'') + '\n';
        }
      } catch(e) { /* silent */ }
    }, 5000);

  } catch(e) {
    if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ ' + e.message + '</span>';
  }
}

async function cmdCollectAll() {
  const statusEl = document.getElementById('collectStatus');
  const logEl = document.getElementById('collectLog');
  if (logEl) logEl.textContent = '';
  if (statusEl) statusEl.innerHTML = '⏳ 启动批量采集...';

  try {
    const r = await fetch('/api/matrix/collect-homepage', { method: 'POST' });
    const data = await r.json();
    if (data.status === 'already_running') {
      if (statusEl) statusEl.innerHTML = '⏳ 已有任务在运行，等待完成...';
    } else if (data.status !== 'started') {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ 启动失败: ' + (data.error||data.message) + '</span>';
      return;
    }
    if (logEl) logEl.textContent += '🚀 批量采集已启动 (批次并行，最多3个浏览器)\n';

    const poll = setInterval(async () => {
      try {
        const pr = await fetch('/api/matrix/collect-homepage/status');
        const ps = await pr.json();
        if (ps.status === 'running') {
          if (statusEl) statusEl.innerHTML = '⏳ 采集中... ' + (ps.completed||0) + '/' + (ps.total_identities||'?') + ' 身份';
          if (logEl) {
            const line = '  ⏳ ' + (ps.completed||0) + '/' + (ps.total_identities||'?') + ' | 成功' + (ps.success||0) + ' 失败' + (ps.failed||0) + '\n';
            if (!logEl.textContent.includes(line.trim())) logEl.textContent += line;
          }
        } else if (ps.status === 'completed') {
          clearInterval(poll);
          await showCollectReport(null, statusEl, logEl);
        } else {
          clearInterval(poll);
          if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ 采集异常</span>';
          if (logEl) logEl.textContent += '❌ 状态: ' + ps.status + ' - ' + (ps.message||'') + '\n';
        }
      } catch(e) { /* silent */ }
    }, 5000);

  } catch(e) {
    if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ ' + e.message + '</span>';
  }
}

async function showCollectReport(filterIds, statusEl, logEl) {
  // 读最终结果
  try {
    const hp = await (await fetch('/api/matrix/homepage-info')).json();
    const results = hp.results || [];
    const collectedAt = hp.collected_at || '未知';

    // 筛选
    let display = results;
    if (filterIds && filterIds.length) {
      display = results.filter(r => {
        const accts = (_collectAccounts||[]).filter(a => a.phone === r.phone);
        return accts.some(a => filterIds.includes(a.id));
      });
    }

    // 统计
    let dy_ok = 0, dy_fail = 0, xhs_ok = 0, xhs_fail = 0;
    display.forEach(r => {
      const dy = r.douyin;
      if (dy) {
        (dy.nickname && !dy.nickname.includes('登录后')) ? dy_ok++ : dy_fail++;
      }
      const xhs = r.xiaohongshu;
      if (xhs) {
        (xhs.nickname && !xhs.nickname.includes('问点点') && !xhs.nickname.includes('推荐')) ? xhs_ok++ : xhs_fail++;
      }
    });

    // 格式化采集时间
    const ts = collectedAt && collectedAt !== '未知' ? collectedAt.replace('T',' ').slice(0,19) : '未知';
    // 计算相对时间
    let relativeTime = '';
    try {
      const then = new Date(collectedAt);
      const now = new Date();
      const diffMin = Math.floor((now - then) / 60000);
      if (diffMin < 1) relativeTime = '刚刚';
      else if (diffMin < 60) relativeTime = diffMin + '分钟前';
      else if (diffMin < 1440) relativeTime = Math.floor(diffMin/60) + '小时前';
      else relativeTime = Math.floor(diffMin/1440) + '天前';
    } catch(e) {}
    const ageColor = relativeTime.includes('小时前') || relativeTime === '刚刚' ? '#22c55e' : 
                     relativeTime.includes('天前') ? '#f59e0b' : '#8b8fa3';

    // 渲染报告
    let html = '<div style="font-size:11px">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">';
    html += '<span style="color:#6366f1;font-weight:600">🕐 更新于: ' + ts + '</span>';
    html += '<span style="color:' + ageColor + ';font-size:10px">(' + relativeTime + ')</span>';
    html += '</div>';
    html += '<div style="border:1px solid var(--border);border-radius:6px;overflow:hidden;margin-bottom:6px">';
    html += '<table style="width:100%;border-collapse:collapse;font-size:10px">';
    html += '<thead><tr style="background:var(--bg3)">';
    html += '<th style="padding:3px 6px;text-align:left">身份</th>';
    html += '<th style="padding:3px 6px;text-align:left">手机</th>';
    html += '<th style="padding:3px 6px;text-align:left">🎵 抖音昵称</th>';
    html += '<th style="padding:3px 6px;text-align:right">粉丝</th>';
    html += '<th style="padding:3px 6px;text-align:left">📕 小红书昵称</th>';
    html += '<th style="padding:3px 6px;text-align:right">粉丝</th>';
    html += '<th style="padding:3px 6px;text-align:center">状态</th>';
    html += '</tr></thead><tbody>';

    display.forEach(r => {
      const dy = r.douyin;
      const xhs = r.xiaohongshu;
      const dyName = (dy && dy.nickname && !dy.nickname.includes('登录后')) ? dy.nickname : '<span style="color:var(--text2);font-style:italic">(无数据)</span>';
      const dyFans = (dy && dy.fans && !dy.nickname.includes('登录后')) ? dy.fans : '-';
      const xhsName = (xhs && xhs.nickname && !xhs.nickname.includes('问点点') && !xhs.nickname.includes('推荐')) ? xhs.nickname : '<span style="color:var(--text2);font-style:italic">(无数据)</span>';
      const xhsFans = (xhs && xhs.fans && !xhs.nickname.includes('问点点') && !xhs.nickname.includes('推荐')) ? xhs.fans : '-';
      const dyOk = dy && dy.nickname && !dy.nickname.includes('登录后');
      const xhsOk = xhs && xhs.nickname && !xhs.nickname.includes('问点点') && !xhs.nickname.includes('推荐');
      const statusIcon = dyOk || xhsOk ? '✅' : '❌';
      html += '<tr style="border-top:1px solid var(--border)">';
      html += '<td style="padding:3px 6px;white-space:nowrap">' + (r.display_name||'?') + '</td>';
      html += '<td style="padding:3px 6px;color:var(--text2);font-size:9px;white-space:nowrap">' + (r.phone||'-') + '</td>';
      html += '<td style="padding:3px 6px">' + dyName + '</td>';
      html += '<td style="padding:3px 6px;text-align:right;color:var(--text2)">' + dyFans + '</td>';
      html += '<td style="padding:3px 6px">' + xhsName + '</td>';
      html += '<td style="padding:3px 6px;text-align:right;color:var(--text2)">' + xhsFans + '</td>';
      html += '<td style="padding:3px 6px;text-align:center">' + statusIcon + '</td>';
      html += '</tr>';
    });

    html += '</tbody></table></div>';
    html += '<div style="display:flex;gap:12px;font-size:10px">';
    html += '<span style="color:var(--green)">✅ 抖音: ' + dy_ok + '/' + (dy_ok+dy_fail) + '</span>';
    html += '<span style="color:#6366f1">📕 小红书: ' + xhs_ok + '/' + (xhs_ok+xhs_fail) + '</span>';
    html += '</div>';
    html += '</div>';

    if (logEl) logEl.innerHTML = html;
    if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">✅ 采集完成</span>';

  } catch(e) {
    if (logEl) logEl.textContent += '❌ 读取结果失败: ' + e.message + '\n';
  }
}

// ════════════════════════════════════════════════════════
// 养号调度器
// ════════════════════════════════════════════════════════

let nurturePollTimer = null;

// ── 养号执行（新版：账号选择 + 自动蓝图 + 机器路由）──

// 全局存账号列表
let _nurtureAccounts = [];

async function loadCmdNurture() {
  // 已迁至独立页面 view-matrix-nurture，此 tab 仅保留入口
}

async function loadNurtureAccounts() {
  const el = document.getElementById('nurtureAcctList');
  if (!el) return;
  try {
    const [r1, r2] = await Promise.all([
      fetch('/api/matrix/accounts'),
      fetch('/api/matrix/homepage-info').catch(() => ({json: () => ({})}))
    ]);
    const accts = await r1.json();
    const hpData = r2.json ? await r2.json() : {results:[]};
    const allAccts = Array.isArray(accts) ? accts.filter(a => a.enabled !== false) : [];
    _nurtureAccounts = allAccts;
    const collectedAt = hpData.collected_at || '';
    
    const hpIndex = {};
    (hpData.results || []).forEach(r => {
      const key = r.identity_dir || r.phone;
      if (key) hpIndex[key] = r;
      if (r.phone) hpIndex[r.phone] = r;
    });
    
    // 三级分组: 机器 → 身份(identity_dir) → 账号
    const tree = {};
    allAccts.forEach(a => {
      const machine = a.owner_machine || '未分配';
      const ident = a.identity_dir || a.id;
      if (!tree[machine]) tree[machine] = {};
      if (!tree[machine][ident]) tree[machine][ident] = {phone: a.phone || '', accounts: []};
      tree[machine][ident].accounts.push(a);
    });
    
    // 机器排序：本机优先
    const machineOrder = Object.keys(tree).sort((a,b) => {
      if (a === 'chengzigedeAir') return -1;
      if (b === 'chengzigedeAir') return 1;
      return a.localeCompare(b);
    });
    
    // 搜索框 + 统计
    let html = '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:6px">';
    html += '<input id="nurtureFilter" placeholder="🔍 搜索账号ID/手机号/昵称..." style="flex:1;min-width:120px;padding:4px 8px;font-size:12px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px" oninput="filterNurtureList()">';
    html += '<span style="font-size:11px;color:var(--text2)">' + allAccts.length + ' 个启用</span>';
    html += '<span style="font-size:11px;color:var(--green)">🎵 ' + allAccts.filter(a=>a.platform==='douyin').length + '</span>';
    html += '<span style="font-size:11px;color:#6366f1">📕 ' + allAccts.filter(a=>a.platform==='xiaohongshu').length + '</span>';
    if (collectedAt) html += '<span style="font-size:10px;color:var(--text2)">采集: ' + new Date(collectedAt).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}) + '</span>';
    html += '</div>';
    
    // 三级渲染: 机器 → 身份(手机号) → 账号
    machineOrder.forEach(machine => {
      const idents = tree[machine];
      const isLocal = machine === 'chengzigedeAir';
      const machineLabel = isLocal ? '🖥️ ' + machine : '☁️ ' + machine;
      const grpId = 'nt_m_' + machine.replace(/[^a-zA-Z0-9]/g, '_');
      const totalAccts = Object.values(idents).reduce((s, i) => s + i.accounts.length, 0);
      const identCount = Object.keys(idents).length;
      const loggedIn = Object.values(idents).reduce((s, i) => s + i.accounts.filter(a => a._status === 'logged_in').length, 0);
      
      html += '<div style="border:1px solid var(--border);border-radius:6px;margin-bottom:4px;overflow:hidden">';
      html += '<div onclick="toggleNurtureGroup(\'' + grpId + '\')" style="display:flex;align-items:center;gap:6px;padding:5px 8px;background:var(--bg3);cursor:pointer;font-size:12px;user-select:none">';
      html += '<span id="' + grpId + '_arrow" style="font-size:10px;opacity:.6">▼</span>';
      html += '<input type="checkbox" onclick="event.stopPropagation();ntToggleMachine(this,\'' + machine + '\')" checked>';
      html += '<strong>' + machineLabel + '</strong>';
      html += '<span style="font-size:10px;color:var(--text2)">' + identCount + ' 身份 ' + totalAccts + ' 账号 | ' + loggedIn + ' 账号已登录</span>';
      html += '</div>';
      
      html += '<div id="' + grpId + '" style="overflow-x:auto">';
      // 一台机器一张表，手机号用 rowspan 合并
      html += '<table style="width:100%;font-size:11px;border-collapse:collapse"><tbody>';
      Object.keys(idents).sort().forEach(ident => {
        const identity = idents[ident];
        const hp = hpIndex[ident] || hpIndex[identity.phone];
        const phoneDisplay = identity.phone ? identity.phone.slice(0,11) : ident.replace('phone_','');
        const nickDisplay = hp?.display_name ? hp.display_name.slice(0,10) : '';
        const rowspan = identity.accounts.length;
        
        identity.accounts.forEach((a, idx) => {
          const plat = a.platform === 'douyin' ? '🎵' : '📕';
          const defBP = a.platform === 'xiaohongshu' ? 'xhs_daily' : 'douyin_daily';
          const phone = a.phone || identity.phone || '-';
          const hpAcc = hp ? (a.platform === 'douyin' ? hp.douyin : hp.xiaohongshu) : null;
          const nickname = hpAcc?.nickname ? hpAcc.nickname.slice(0,12) : '';
          const hpTime = hpAcc?.collected_at || '';
          const hpTimeDisplay = hpTime ? new Date(hpTime).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}) : '';
          
          let statusIcon, cookieIcon;
          if (a._status === 'logged_in') {
            statusIcon = '<span class="badge badge-green" style="font-size:10px">已登录</span>';
            cookieIcon = '<span style="color:var(--green);font-size:10px">🍪有效</span>';
          } else if (a._status === 'no_cookie' || a._status === 'no_session' || a._status === 'empty_cookie') {
            statusIcon = '<span class="badge badge-amber" style="font-size:10px">未登录</span>';
            cookieIcon = '<span style="color:var(--red);font-size:10px">🍪'+(a._status||'')+'</span>';
          } else {
            statusIcon = '<span class="badge badge-red" style="font-size:10px">'+(a._status||'')+'</span>';
            cookieIcon = '';
          }
          
          html += '<tr class="nurture-row" data-account="'+a.id+'" data-phone="'+phone+'" data-nick="'+nickname+'" data-machine="'+machine+'">';
          // 手机号列: 同身份第一个显示(rowspan合并)，后续隐藏
          if (idx === 0) {
            html += '<td rowspan="'+rowspan+'" style="padding:3px 6px;font-size:10px;color:var(--text2);vertical-align:middle;border-right:1px solid var(--border);white-space:nowrap">📱'+phoneDisplay+(nickDisplay?' '+nickDisplay:'')+'</td>';
          }
          html += '<td style="padding:3px 4px;width:24px"><input type="checkbox" class="nurture-cb" value="'+a.id+'" data-plat="'+a.platform+'" data-bp="'+defBP+'" data-machine="'+machine+'" checked></td>';
          html += '<td style="padding:3px 4px;white-space:nowrap"><strong>'+a.id+'</strong></td>';
          html += '<td style="padding:3px 4px">'+plat+'</td>';
          html += '<td style="padding:3px 4px;font-size:10px;max-width:80px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+(nickname||'<span class="text-muted">-</span>')+'</td>';
          html += '<td style="padding:3px 4px;white-space:nowrap">'+statusIcon+'</td>';
          html += '<td style="padding:3px 4px;font-size:10px;white-space:nowrap">'+cookieIcon+'</td>';
          html += '<td style="padding:3px 4px;font-size:10px;color:var(--text2);white-space:nowrap">采集:'+hpTimeDisplay+'</td>';
          html += '<td style="padding:3px 4px;font-size:10px;color:var(--text2);white-space:nowrap">📋'+defBP+'</td>';
          html += '</tr>';
        });
      });
      html += '</tbody></table></div></div>';
    });
    
    el.innerHTML = html;
    updateNurtureCount();
  } catch(e) {
    const el2 = document.getElementById('nurtureAcctList');
    if (el2) el2.innerHTML = '<div class="error">❌ '+e.message+'</div>';
  }
}

// 折叠/展开机器组
function toggleNurtureGroup(grpId) {
  const el = document.getElementById(grpId);
  const arrow = document.getElementById(grpId + '_arrow');
  if (!el) return;
  const hidden = el.style.display === 'none';
  el.style.display = hidden ? '' : 'none';
  if (arrow) arrow.textContent = hidden ? '▼' : '▶';
}

function ntToggleMachine(master, machine) {
  document.querySelectorAll('.nurture-cb[data-machine="'+machine+'"]').forEach(cb => cb.checked = master.checked);
  updateNurtureCount();
}

function ntToggleIdentity(master) {
  const table = master.closest('div').nextElementSibling?.querySelector('table');
  if (table) table.querySelectorAll('.nurture-cb').forEach(cb => cb.checked = master.checked);
  updateNurtureCount();
}

// 搜索过滤
function filterNurtureList() {
  const q = (document.getElementById('nurtureFilter')?.value || '').toLowerCase();
  document.querySelectorAll('.nurture-row').forEach(row => {
    const acct = row.dataset.account || '';
    const phone = row.dataset.phone || '';
    const nick = row.dataset.nick || '';
    const match = !q || acct.includes(q) || phone.includes(q) || nick.includes(q);
    row.style.display = match ? '' : 'none';
  });
  updateNurtureCount();
}

function nurtureToggleAll(master) {
  document.querySelectorAll('.nurture-cb').forEach(cb => cb.checked = master.checked);
  updateNurtureCount();
}

function updateNurtureCount() {
  const checked = document.querySelectorAll('.nurture-cb:checked').length;
  const el = document.getElementById('nurtureSelCount');
  if (el) el.textContent = '已选 ' + checked + ' 个';
}

// ── 预检 ──
async function nurturePreflight() {
  const statusEl = document.getElementById('nurtureStatus');
  const logEl = document.getElementById('nurtureLog');
  const preflightEl = document.getElementById('nurturePreflightInfo');
  if (statusEl) statusEl.innerHTML = '🔍 正在预检各机器状态...';
  if (logEl) logEl.textContent = '';

  try {
    const r = await fetch('/api/matrix/nurture/status');
    const d = await r.json();

    let html = '🖥️ 本机: ' + (d.local_browsers?.length || 0) + ' 浏览器运行中\n';
    (d.local_browsers || []).forEach(b => {
      html += '  PID=' + b.pid + ' ' + b.cmd.slice(0, 60) + '\n';
    });

    (d.remote_machines || []).forEach(m => {
      html += '☁️ ' + m.machine + ': ' + (m.browsers_running || 0) + ' 浏览器 | 可用槽位: ' + (m.slots_available || '?') + '\n';
      if (m.error) html += '  ❌ ' + m.error + '\n';
    });

    if (preflightEl) preflightEl.textContent = html;
    if (statusEl) statusEl.innerHTML = '✅ 预检完成';
  } catch(e) {
    if (statusEl) statusEl.innerHTML = '❌ 预检失败: ' + e.message;
  }
}

// ── 执行选中 ──
async function nurtureExec() {
  const selected = _getSelectedAccounts();
  if (!selected.length) { alert('请先选择要执行的账号'); return; }
  await doNurtureExec(selected.map(s => s.id));
}

// ── 执行全部启用 ──
async function nurtureExecAll() {
  const selected = _getSelectedAccounts();
  // 如果选中计数和总计数不一致，说明用户手动反选了某些
  const total = document.querySelectorAll('.as-cb').length;
  const checked = selected.length;
  if (checked < total) {
    if (!confirm('当前仅 ' + checked + '/' + total + ' 个账号被选中。确认执行这 ' + checked + ' 个？')) return;
  } else {
    if (!confirm('执行全部 ' + checked + ' 个账号（每台机器各自运行）？')) return;
  }
  await doNurtureExec(selected.map(s => s.id));
}

async function doNurtureExec(accountIds) {
  const statusEl = document.getElementById('nurtureStatus');
  const logEl = document.getElementById('nurtureLog');
  const preflightEl = document.getElementById('nurturePreflightInfo');
  const rounds = parseInt(document.getElementById('ndRounds').value) || 10;
  const bpOverride = document.getElementById('ndBlueprint').value;

  if (logEl) logEl.textContent = '';
  if (preflightEl) preflightEl.textContent = '';
  if (statusEl) statusEl.innerHTML = '⏳ 启动中 (' + accountIds.length + ' 个账号)...';

  try {
    const body = {accounts: accountIds, rounds, dry_run: true};
    if (bpOverride) body.blueprint = bpOverride;

    // 先 dry_run 预览执行计划
    const r1 = await fetch('/api/matrix/nurture/start', {
      method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)
    });
    const plan = await r1.json();

    if (plan.status !== 'plan') {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ '+(plan.message||JSON.stringify(plan))+'</span>';
      return;
    }

    let planText = '📋 执行计划:\n';
    plan.plan.forEach(p => {
      const loc = p.is_local ? '🖥️' : '☁️';
      planText += loc + ' ' + p.account + ' → ' + p.machine + ' [' + p.blueprint + '] ' + p.rounds + '轮\n';
    });
    if (logEl) logEl.textContent = planText;
    if (statusEl) statusEl.innerHTML = '📋 计划确认中...';

    if (!confirm(planText + '\n确认执行？')) {
      if (statusEl) statusEl.innerHTML = '⏸ 已取消';
      return;
    }

    // ── 真正执行 ──
    if (statusEl) statusEl.innerHTML = '⏳ 执行中（预检 → 分配窗口 → 启动 → 验证）...';
    delete body.dry_run;

    const r2 = await fetch('/api/matrix/nurture/start', {
      method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)
    });
    const result = await r2.json();

    if (result.status === 'started') {
      // 显示预检结果
      if (preflightEl && result.preflight) {
        let pfText = '🔍 预检结果:\n';
        Object.entries(result.preflight).forEach(([machine, info]) => {
          pfText += '  ' + machine + ': ' + info.message + '\n';
          if (info.slot) pfText += '    槽位 ' + info.slot.id + ' 位置 (' + info.slot.position + ')\n';
        });
        preflightEl.textContent = pfText;
      }

      // 显示执行结果
      let out = '🚀 执行结果:\n';
      (result.results || []).forEach(r => {
        const icon = r.status === 'started' ? '✅' : r.status === 'verify_failed' ? '⚠️' : '❌';
        const verified = r.verified_pid ? ' PID=' + r.verified_pid : '';
        out += '  ' + icon + ' ' + r.account + ': ' + r.status + ' 槽位' + (r.slot||'?') + verified + '\n';
      });
      if (logEl) logEl.textContent = out;
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">✅ 已启动，正在轮询...</span>';

      // 轮询结果
      const pollInterval = setInterval(async () => {
        try {
          const pr = await fetch('/api/matrix/nurture/results?limit=10');
          const pd = await pr.json();
          const items = pd.results || [];
          if (!items.length) return;

          let html = '<div style="font-size:10px"><table style="width:100%"><tr><th>账号</th><th>状态</th><th>步骤</th><th>耗时</th><th>槽位</th></tr>';
          let allDone = true;
          items.slice(0, 8).forEach(r => {
            const st = r.status === 'completed' ? '✅' : r.status === 'running' ? '⏳' : '❌';
            if (r.status === 'running') allDone = false;
            const steps = r.steps ? (r.steps.success||0) + '/' + (r.steps.total||0) : '-';
            const dur = r.duration_secs ? Math.round(r.duration_secs/60) + 'min' : '-';
            html += `<tr><td>${r.account}</td><td>${st} ${r.status}</td><td>${steps}</td><td>${dur}</td><td>槽${r.slot||'-'}</td></tr>`;
          });
          html += '</table></div>';
          if (logEl) logEl.innerHTML = html;

          if (allDone) {
            clearInterval(pollInterval);
            if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">✅ 全部执行完成</span>';
          } else {
            if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">⏳ 执行中...</span>';
          }
        } catch(e) {}
      }, 10000);
    } else {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ '+(result.message||JSON.stringify(result))+'</span>';
    }
  } catch(e) {
    if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>';
  }
}

// ════════════════════════════════════════════════════════
// 定时任务
// ════════════════════════════════════════════════════════

async function refreshScheduleList() {
  const listEl = document.getElementById('scheduleList');
  const histEl = document.getElementById('scheduleHistory');
  const statusEl = document.getElementById('scheduleStatus');
  // 加载任务列表
  if (listEl) {
    try {
      const r = await fetch('/api/matrix/schedules');
      const d = await r.json();
      const scheds = d.schedules || {};
      const entries = Object.entries(scheds);
      if (!entries.length) {
        listEl.innerHTML = '<div style="color:var(--text2);padding:10px;text-align:center">暂无定时任务，在上方添加</div>';
      } else {
        listEl.innerHTML = entries.map(([sid, s]) =>
          '<div style="background:var(--bg3);border-radius:4px;padding:6px 8px;border:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;font-size:11px;margin-bottom:3px">' +
          '<div><strong>' + sid + '</strong> <span style="color:var(--text2)">' + (s.account||'') + ' → ' + (s.blueprint||'') + '</span></div>' +
          '<div style="display:flex;align-items:center;gap:6px">' +
          '<span style="color:#6366f1">' + (s.time||'') + '</span>' +
          '<span style="color:var(--text2);font-size:10px">' + (s.days||'每天') + '</span>' +
          '<span style="cursor:pointer" onclick="scheduleToggle(\''+sid+'\',' + (!s.enabled) + ')">' + (s.enabled ? '🟢' : '⚪') + '</span>' +
          '<span style="cursor:pointer;color:var(--red);font-size:10px" onclick="scheduleDelete(\''+sid+'\')">✕</span>' +
          '</div></div>'
        ).join('');
      }
    } catch(e) { if (listEl) listEl.innerHTML = '<span style="color:var(--red)">'+e.message+'</span>'; }
  }
  // 加载历史
  if (histEl) {
    try {
      const r = await fetch('/api/matrix/schedules/history');
      const d = await r.json();
      const hist = d.history || [];
      if (!hist.length) {
        histEl.innerHTML = '<div style="color:var(--text2);padding:6px">暂无执行记录</div>';
      } else {
        histEl.innerHTML = hist.map(e =>
          '<div style="padding:3px 0;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;font-size:10px">' +
          '<span>' + (e.timestamp||'').slice(0,16) + ' ' + (e.schedule_id||'') + '</span>' +
          '<span>' + (e.error ? '❌ '+e.error.slice(0,20) : (e.status||'✅')) + ' ' + (e.success||0)+'/'+((e.success||0)+(e.failed||0)) + ' ' + (e.duration||0)+'s</span>' +
          '</div>'
        ).join('');
      }
    } catch(e) { if (histEl) histEl.innerHTML = '<span style="color:var(--red)">'+e.message+'</span>'; }
  }
  // 调度器状态
  if (statusEl) statusEl.innerHTML = '<span style="color:var(--text2)">需手动启动: mc schedule start</span>';
  // 加载 WorkBuddy 自动化任务
  const autoEl = document.getElementById('autoTasksSummary');
  if (autoEl) {
    try {
      const r = await fetch('/api/kb/automations');
      const d = await r.json();
      const machines = d.machines || {};
      const entries = Object.entries(machines);
      if (!entries.length) {
        autoEl.innerHTML = '<div style="color:var(--text2);font-size:11px;padding:4px 0">暂无自动化任务</div>' +
          '<div style="margin-top:8px;display:flex;gap:6px"><select id="autoNewTarget" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;font-size:11px">' +
          '<option value="">选目标机器</option>' +
          Object.keys(machines).map(m => '<option value="'+m+'">'+m+'</option>').join('') +
          '</select>' +
          '<input id="autoNewPrompt" placeholder="输入提示词..." style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;font-size:11px">' +
          '<button onclick="createAutoTaskFromSchedule()" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">+ 创建任务</button></div>';
      } else {
        let html = entries.map(([machine, tasks]) => {
          const wbTasks = tasks.filter(t => t.source_type === 'workbuddy');
          if (!wbTasks.length) return '';
          return '<div style="margin-bottom:6px">' +
            '<div style="font-weight:600;font-size:11px;color:#6366f1;margin-bottom:3px">💻 ' + machine + '</div>' +
            wbTasks.map(t => {
              const prompt = t.prompt || t.name || '';
              return '<div style="padding:3px 6px;font-size:10px;background:var(--bg3);border-radius:4px;margin-bottom:3px;border:1px solid var(--border)">' +
                '<div style="display:flex;justify-content:space-between">' +
                '<span style="color:' + (t.status === 'ACTIVE' ? '#22c55e' : '#8b8fa3') + '">' + (t.status === 'ACTIVE' ? '▶ 运行中' : '⏸ 暂停') + '</span>' +
                '<span style="color:var(--text2)">' + (t.rrule || t.scheduleType || '即时') + '</span>' +
                '</div>' +
                '<div style="margin-top:2px;color:var(--text);word-break:break-all">' + (prompt.slice(0, 120) + (prompt.length > 120 ? '...' : '')) + '</div>' +
                '</div>';
            }).join('') +
            '</div>';
        }).filter(Boolean).join('');
        if (!html) html = '<div style="color:var(--text2);font-size:11px;padding:4px 0">无 WorkBuddy 任务</div>';
        // 新建任务表单
        html += '<div style="margin-top:8px;padding:6px;background:var(--bg3);border-radius:4px">' +
          '<div style="font-size:11px;font-weight:600;margin-bottom:4px">✏️ 新建自动化任务</div>' +
          '<div style="display:flex;gap:6px">' +
          '<select id="autoNewTarget" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:3px;font-size:10px;width:120px">' +
          '<option value="">选目标</option>' +
          Object.keys(machines).map(m => '<option value="'+m+'">'+m+'</option>').join('') +
          '</select>' +
          '<input id="autoNewPrompt" placeholder="输入提示词，描述要执行的任务..." style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:3px;font-size:10px">' +
          '<button onclick="createAutoTaskFromSchedule()" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:3px;cursor:pointer;font-size:10px">+ 创建</button>' +
          '</div></div>';
        autoEl.innerHTML = html;
      }
    } catch(e) { autoEl.innerHTML = '<span style="color:var(--text2);font-size:11px">自动化任务API不可用</span>'; }
  }
}

async function scheduleAdd() {
  const id = document.getElementById('schedId')?.value.trim();
  const account = document.getElementById('schedAccount')?.value;
  const blueprint = document.getElementById('schedBlueprint')?.value;
  const time = document.getElementById('schedTime')?.value || '09:00';
  const days = document.getElementById('schedDays')?.value || '1,2,3,4,5,6,7';
  const rounds = parseInt(document.getElementById('schedRounds')?.value) || 3;
  if (!id) { alert('请输入任务ID'); return; }
  if (!account) { alert('请选择账号'); return; }
  // 通过 mc CLI 添加
  const cmd = 'mc schedule add --id '+id+' --account '+account+' --blueprint '+blueprint+' --time '+time+' --days '+days+' --rounds '+rounds;
  if (!confirm('将在终端执行:\n'+cmd+'\n\n确认？')) return;
  alert('请在终端执行:\n'+cmd+'\n\n或手动编辑 config/schedule.yaml');
  refreshScheduleList();
}

async function scheduleToggle(sid, enabled) {
  try {
    await fetch('/api/matrix/schedules/toggle', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({id:sid, enabled})
    });
    refreshScheduleList();
  } catch(e) { alert('❌ '+e.message); }
}

async function scheduleDelete(sid) {
  if (!confirm('删除定时任务 '+sid+' ？')) return;
  try {
    await fetch('/api/matrix/schedules/delete', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({id:sid})
    });
    refreshScheduleList();
  } catch(e) { alert('❌ '+e.message); }
}

// ════════════════════════════════════════════════════════
// 矩阵设置 TAB
// ════════════════════════════════════════════════════════

function switchSetTab(tab, el) {
  document.querySelectorAll('.set-tab').forEach(t => {
    t.style.borderBottom = '2px solid transparent';
    t.style.color = '#8b8fa3';
  });
  el.style.borderBottom = '2px solid #6366f1';
  el.style.color = '#e1e4f0';
  ['set-export-content','set-backup-content','set-corpus-content'].forEach(id => {
    document.getElementById(id).style.display = id === tab+'-content' ? 'block' : 'none';
  });
}

async function loadMatrixSettings() {
  // 三个 TAB 都使用 MutationObserver 同步原始内容
  const syncMap = [
    { id: 'matrixExportContent2', load: 'loadMatrixExport', orig: 'matrixExportContent' },
    { id: 'matrixBackupContent2', load: 'loadMatrixBackup', orig: 'matrixBackupContent' },
    { id: 'corpusContent2', load: 'loadCorpus', orig: 'corpusContent' },
  ];
  for (const {id, load, orig} of syncMap) {
    const el = document.getElementById(id);
    const origEl = document.getElementById(orig);
    if (el && origEl && typeof window[load] === 'function') {
      await window[load]();
      el.innerHTML = origEl.innerHTML;
      if (!window['_setObs_' + id]) {
        window['_setObs_' + id] = new MutationObserver(() => {
          const target = document.getElementById(id);
          const source = document.getElementById(orig);
          if (target && source) target.innerHTML = source.innerHTML;
        });
        window['_setObs_' + id].observe(origEl, { childList: true, subtree: true, characterData: true });
      }
    }
  }
}

// ── Keyboard ──
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDetail(); });

// ── Timeline ──
let timelineChart = null;
async function loadTimeline(hostname) {
  if (!hostname) {
    // 展示 selector
    const sel = document.getElementById('timelineSelector');
    const r = await fetch('/api/machines'); const res = await r.json();
    sel.innerHTML = (res.machines||[]).map(m =>
      `<button class="btn" onclick="loadTimeline('${m.hostname}')">${m.hostname}</button>`
    ).join('');
    document.getElementById('timelineStatus').textContent = '点击机器查看';
    return;
  }
  document.getElementById('timelineStatus').textContent = `加载 ${hostname}...`;
  const r = await fetch(`/api/timeline/${hostname}?window=120`);
  const res = await r.json();
  const pts = res.points || [];
  if (!pts.length) { document.getElementById('timelineStatus').textContent = `${hostname}: 暂无数据`; return; }
  
  const labels = pts.map(p => { try { return new Date(p.t).toLocaleTimeString(); } catch(e) { return ''; }});
  const cpu = pts.map(p => p.cpu || 0);
  const disk = pts.map(p => p.disk_pct || 0);
  
  document.getElementById('timelineStatus').textContent = `${hostname}: ${pts.length} 个采样点 (最近${res.total}条)`;
  
  // 简单 Canvas 绘图
  const canvas = document.getElementById('timelineChart');
  const ctx = canvas.getContext('2d');
  canvas.width = canvas.offsetWidth * 2; canvas.height = canvas.offsetHeight * 2;
  ctx.scale(2,2); const w = canvas.offsetWidth, h = canvas.offsetHeight;
  
  const maxVal = Math.max(...cpu, ...disk, 1);
  const pad = {top:20, bottom:20, left:40, right:20};
  const cw = w - pad.left - pad.right, ch = h - pad.top - pad.bottom;
  
  ctx.clearRect(0,0,w,h);
  // grid
  ctx.strokeStyle = 'rgba(255,255,255,0.05)'; ctx.lineWidth = 0.5;
  for(let i=0;i<5;i++) { ctx.beginPath(); ctx.moveTo(pad.left, pad.top+ch*i/4); ctx.lineTo(w-pad.right, pad.top+ch*i/4); ctx.stroke(); }
  
  function drawLine(data, color) {
    ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath();
    data.forEach((v,i) => {
      const x = pad.left + (i/(data.length-1||1))*cw;
      const y = pad.top + ch - (v/maxVal)*ch;
      i===0 ? ctx.moveTo(x,y) : ctx.lineTo(x,y);
    }); ctx.stroke();
  }
  drawLine(cpu, '#378ADD');
  drawLine(disk, '#D85A30');
  
  // legend
  ctx.fillStyle = '#378ADD'; ctx.fillRect(w-130, 10, 12, 12);
  ctx.fillStyle = 'var(--text)'; ctx.font = '11px sans-serif'; ctx.fillText('CPU', w-112, 20);
  ctx.fillStyle = '#D85A30'; ctx.fillRect(w-80, 10, 12, 12);
  ctx.fillStyle = 'var(--text)'; ctx.fillText('磁盘(G)', w-62, 20);
}

// ── Alerts ──
async function loadAlerts() {
  const el = document.getElementById('alertsList');
  try {
    const r = await fetch('/api/alerts'); const res = await r.json();
    const alerts = res.alerts || [];
    if (!alerts.length) { el.innerHTML = '<div class="card"><div style="color:var(--green)">✅ 所有机器运行正常</div></div>'; return; }
    el.innerHTML = alerts.map(a => {
      const color = a.level === 'critical' ? 'var(--red)' : a.level === 'warning' ? 'var(--amber)' : 'var(--text2)';
      const since = a.since_sec < 3600 ? `${(a.since_sec/60).toFixed(0)}分钟` : `${(a.since_sec/3600).toFixed(1)}小时`;
      return `<div class="card" style="border-left:3px solid ${color}">
        <div style="font-weight:600">${a.hostname}</div>
        <div style="font-size:12px;color:${color}">${a.level==='critical'?'🔴 严重':a.level==='warning'?'🟡 警告':'ℹ️ 提示'}: 离线 ${since}</div>
        ${a.note ? `<div style="font-size:11px;color:var(--text2)">${a.note}</div>` : ''}
        <div style="margin-top:8px;display:flex;gap:8px">
          <button class="btn" onclick="wakeupMachine('${a.hostname}')">🔄 唤醒</button>
          <button class="btn" onclick="upgradeMachine('${a.hostname}')">⬆️ 升级</button>
        </div>
      </div>`;
    }).join('');
  } catch(e) { el.innerHTML = `<div class="error">❌ ${e.message}</div>`; }
}

async function wakeupMachine(hostname) {
  await fetch(`/api/wakeup/${hostname}`, {method:'POST'});
  alert(`已发送唤醒命令到 ${hostname}`);
}
async function upgradeMachine(hostname) {
  if (!confirm(`确认对 ${hostname} 执行 git pull + 重启服务?`)) return;
  await fetch(`/api/upgrade/${hostname}`, {method:'POST'});
  alert(`已发送升级命令到 ${hostname}`);
}

// ═══════════════════════════════════════════════════════════
// 工作流编辑器 — SVG DAG 节点编辑器
// ═══════════════════════════════════════════════════════════
let wfNodes = [], wfEdges = [], wfNodeIdCounter = 0;
let wfSelectedNodeId = null, wfDraggingNode = null, wfDragOffX = 0, wfDragOffY = 0;
let wfConnecting = null, wfCurrentRunId = null, wfPendingGateId = null;
let wfNodeDefs = {}, wfTemplates = {};
const WF_ZOOM = 1;

const NODE_COLORS = {
  input: '#6366f1', core: '#22c55e', audio: '#f59e0b', generate: '#3b82f6',
  material: '#ec4899', visual: '#8b5cf6', process: '#a855f7', flow: '#ef4444',
  output: '#64748b', default: '#888',
};

function wfNodeColor(type) {
  const def = wfNodeDefs[type];
  return def?.color || NODE_COLORS[def?.category] || NODE_COLORS.default;
}

async function loadWorkflow() {
  const el = document.getElementById('workflowContent');
  el.innerHTML = `
  <div style="display:flex;flex-direction:column;height:calc(100vh - 180px);min-height:500px">
    <!-- 工具栏 -->
    <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;flex-shrink:0">
      <span style="font-size:14px;font-weight:600;color:var(--text)">🔀 工作流</span>
      <select id="wfTemplateSelect" onchange="wfLoadTemplate(this.value)"
        style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;font-size:12px;width:160px">
        <option value="">— 模板 —</option>
      </select>
      <div style="display:flex;gap:3px;flex-wrap:wrap;flex:1;overflow-x:auto;padding:2px 0" id="wfNodePalette"></div>
      <button onclick="wfRun()" style="background:var(--primary);border:none;color:#fff;padding:3px 12px;border-radius:4px;cursor:pointer;font-size:12px;white-space:nowrap">▶ 运行</button>
      <button onclick="wfClear()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:12px;white-space:nowrap">🗑 清空</button>
      <span id="wfRunStatus" style="font-size:11px;color:var(--text2);white-space:nowrap"></span>
    </div>
    <!-- 主体：画布 + 配置面板 -->
    <div style="display:flex;gap:8px;flex:1;min-height:0">
      <!-- 画布区 -->
      <div style="flex:1;position:relative;background:var(--bg3);border-radius:8px;overflow:hidden;border:1px solid var(--border)">
        <svg id="wfCanvas" width="100%" height="100%" style="cursor:grab;display:block"></svg>
        <div id="wfCanvasPlaceholder" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;color:var(--text2);font-size:13px;pointer-events:none">
          从上方拖拽节点到画布，或选择模板开始
        </div>
      </div>
      <!-- 配置面板 -->
      <div id="wfConfigPanel" style="width:300px;background:var(--bg2);border-radius:8px;border:1px solid var(--border);overflow-y:auto;flex-shrink:0">
        <div id="wfConfigContent" style="padding:14px;font-size:12px;color:var(--text2)">点击节点编辑配置</div>
      </div>
    </div>
  </div>`;
  await wfInit();
}

async function wfInit() {
  // 一次性加载所有节点定义和模板，避免 N+1 查询
  try {
    const [nodesR, tmplR] = await Promise.all([
      fetch(API + '/api/workflow/nodes'),
      fetch(API + '/api/workflow/templates'),
    ]);
    const nodesD = await nodesR.json();
    const tmplD = await tmplR.json();
    // 构建节点定义字典
    wfNodeDefs = {};
    for (const cat of (nodesD.categories || [])) {
      for (const nid of (cat.nodes || [])) {
        wfNodeDefs[nid] = cat._defs?.[nid] || {};
      }
    }
    wfTemplates = tmplD.templates || {};
  } catch(e) {
    wfNodeDefs = {};
    wfTemplates = {};
  }
  wfRenderPalette();
  wfRenderTemplateSelect();
  wfLoadCharacters();
  wfInitCanvas();
}

function wfInitCanvas() {
  const canvas = document.getElementById('wfCanvas');
  if (!canvas) return;
  canvas.addEventListener('dragover', e => e.preventDefault());
  canvas.addEventListener('drop', e => {
    e.preventDefault();
    const type = e.dataTransfer.getData('text/plain');
    if (!type || !wfNodeDefs[type]) return;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - 120) / WF_ZOOM;
    const y = (e.clientY - rect.top - 30) / WF_ZOOM;
    wfAddNode(type, Math.max(0,x), Math.max(0,y));
  });
}

function wfRenderPalette() {
  const el = document.getElementById('wfNodePalette');
  if (!el) return;
  el.innerHTML = Object.entries(wfNodeDefs).map(([type, def]) => {
    const color = def.color || '#888';
    const icon = def.icon || '●';
    return `<div draggable="true" ondragstart="wfDragStart(event,'${type}')" title="${def.description||''}"
      style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;margin:1px;border-radius:4px;font-size:11px;cursor:grab;white-space:nowrap;background:${color}15;border:1px solid ${color}30;color:${color}">${icon} ${def.label}</div>`;
  }).join('');
}

function wfRenderTemplateSelect() {
  const sel = document.getElementById('wfTemplateSelect');
  if (!sel) return;
  sel.innerHTML = '<option value="">— 选择模板 —</option>' +
    Object.entries(wfTemplates).map(([id, t]) =>
      `<option value="${id}">${t.name||id} ${t.cost||''}</option>`
    ).join('');
}

// ══ SVG 渲染 ══
function wfRender() {
  const svg = document.getElementById('wfCanvas');
  const ph = document.getElementById('wfCanvasPlaceholder');
  if (!svg) return;
  ph.style.display = wfNodes.length === 0 ? 'flex' : 'none';

  let html = `<defs><marker id="wfArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M2 1L8 5L2 9" fill="none" stroke="#888" stroke-width="1.5"/></marker></defs>`;

  // 边
  wfEdges.forEach((e, i) => {
    const from = wfNodes.find(n => n.id === e.from);
    const to = wfNodes.find(n => n.id === e.to);
    if (from && to) {
      const x1 = from.x + 120, y1 = from.y + 30;
      const x2 = to.x, y2 = to.y + 30;
      const cx = (x1 + x2) / 2;
      html += `<path d="M${x1} ${y1} C${cx} ${y1},${cx} ${y2},${x2} ${y2}" fill="none" stroke="#888" stroke-width="2" marker-end="url(#wfArrow)" opacity="0.6"/>`;
    }
  });

  // 节点
  wfNodes.forEach(n => {
    const def = wfNodeDefs[n.type] || {};
    const color = def.color || '#888';
    html += `<g class="wf-node" data-id="${n.id}" onmousedown="wfNodeMouseDown(event,'${n.id}')" style="cursor:move">
      <rect x="${n.x}" y="${n.y}" width="240" height="60" rx="8" fill="var(--bg2)" stroke="${wfSelectedNodeId === n.id ? color : 'var(--border)'}" stroke-width="${wfSelectedNodeId === n.id ? 2 : 1}"/>
      <rect x="${n.x}" y="${n.y}" width="240" height="24" rx="8" fill="${color}" opacity="0.15"/>
      <text x="${n.x+12}" y="${n.y+17}" font-size="12" fill="${color}" font-weight="600">${def.icon||'●'} ${n.label||def.label||n.type}</text>
      <text x="${n.x+12}" y="${n.y+42}" font-size="10" fill="var(--text2)">${def.description||''}</text>
      ${(def.ports?.input||[]).map((p,i) =>
        `<circle cx="${n.x}" cy="${n.y+40+i*16}" r="5" fill="var(--bg3)" stroke="${color}" stroke-width="1.5" style="cursor:crosshair" onmousedown="wfConnStart(event,'${n.id}','${p}')" onmouseup="wfConnEnd(event,'${n.id}','${p}')"/>`
      ).join('')}
      ${(def.ports?.output||[]).map((p,i) =>
        `<circle cx="${n.x+240}" cy="${n.y+30+i*16}" r="5" fill="${color}" stroke="${color}" stroke-width="1.5" style="cursor:crosshair" onmousedown="wfConnStart(event,'${n.id}','${p}')" onmouseup="wfConnEnd(event,'${n.id}','${p}')"/>`
      ).join('')}
      <rect x="${n.x+200}" y="${n.y+4}" width="34" height="18" rx="4" fill="${color}" opacity="0.8" style="cursor:pointer" onclick="wfSelectNode('${n.id}')"/>
      <text x="${n.x+217}" y="${n.y+16}" font-size="9" fill="#fff" text-anchor="middle" style="cursor:pointer" onclick="wfSelectNode('${n.id}')">配置</text>
    </g>`;
  });

  svg.innerHTML = html;
}

// ══ 拖拽创建节点 ══
function wfDragStart(e, type) {
  e.dataTransfer.setData('text/plain', type);
}

function wfAddNode(type, x, y) {
  const id = 'n' + (++wfNodeIdCounter);
  const def = wfNodeDefs[type] || {};
  wfNodes.push({
    id, type, label: def.label || type,
    config: JSON.parse(JSON.stringify(def.default_config || {})),
    x, y,
  });
  wfRender();
  wfSelectNode(id);
}

function wfSelectNode(id) {
  wfSelectedNodeId = id;
  wfRender();
  wfRenderConfig(id);
}

function wfDeleteNode(id) {
  wfNodes = wfNodes.filter(n => n.id !== id);
  wfEdges = wfEdges.filter(e => e.from !== id && e.to !== id);
  if (wfSelectedNodeId === id) wfSelectedNodeId = null;
  wfRender();
  document.getElementById('wfConfigContent').innerHTML = '<div style="text-align:center;padding:40px 0;color:var(--text2);font-size:13px">点击节点编辑配置</div>';
}

// ══ 节点拖拽移动 ══
function wfNodeMouseDown(e, id) {
  if (e.target.closest('circle') || e.target.closest('rect[onclick]')) return;
  const rect = document.getElementById('wfCanvas').getBoundingClientRect();
  const n = wfNodes.find(x => x.id === id);
  if (!n) return;
  wfDragOffX = e.clientX - rect.left - n.x;
  wfDragOffY = e.clientY - rect.top - n.y;
  wfDraggingNode = id;
  document.addEventListener('mousemove', wfNodeMouseMove);
  document.addEventListener('mouseup', wfNodeMouseUp);
}

function wfNodeMouseMove(e) {
  if (!wfDraggingNode) return;
  const rect = document.getElementById('wfCanvas').getBoundingClientRect();
  const n = wfNodes.find(x => x.id === wfDraggingNode);
  if (n) {
    n.x = Math.max(0, (e.clientX - rect.left - wfDragOffX) / WF_ZOOM);
    n.y = Math.max(0, (e.clientY - rect.top - wfDragOffY) / WF_ZOOM);
    wfRender();
  }
}

function wfNodeMouseUp() {
  wfDraggingNode = null;
  document.removeEventListener('mousemove', wfNodeMouseMove);
  document.removeEventListener('mouseup', wfNodeMouseUp);
}

// ══ 连线 ══
function wfConnStart(e, nodeId, port) {
  wfConnecting = {nodeId, port, isOutput: true};
  e.stopPropagation();
}

function wfConnEnd(e, nodeId, port) {
  if (!wfConnecting) return;
  if (wfConnecting.nodeId !== nodeId) {
    // 检测方向：从上一个节点的 output 到当前节点的 input
    if (e.target.getAttribute('fill') !== '#888' && e.target.getAttribute('fill') !== 'var(--bg3)') {
      // 当前是 output → 另一个节点的 input
    }
    wfEdges.push({from: wfConnecting.nodeId, to: nodeId, from_port: wfConnecting.port, to_port: port});
  }
  wfConnecting = null;
  wfRender();
}

// ══ 加载模板 ══
async function wfLoadTemplate(tid) {
  if (!tid || !wfTemplates[tid]) return;
  const t = wfTemplates[tid];
  wfNodes = JSON.parse(JSON.stringify(t.nodes || []));
  wfEdges = JSON.parse(JSON.stringify(t.edges || []));
  wfNodeIdCounter = wfNodes.length;
  wfSelectedNodeId = null;
  wfRender();
  document.getElementById('wfConfigContent').innerHTML = '<div style="text-align:center;padding:40px 0;color:var(--text2);font-size:13px">点击节点编辑配置</div>';
}

function wfClear() {
  wfNodes = []; wfEdges = []; wfSelectedNodeId = null; wfCurrentRunId = null;
  wfRender();
  document.getElementById('wfConfigContent').innerHTML = '<div style="text-align:center;padding:40px 0;color:var(--text2);font-size:13px">点击节点编辑配置</div>';
}

// ══ 运行 ══
async function wfRun() {
  const statusEl = document.getElementById('wfRunStatus');
  statusEl.textContent = '⏳ 运行中...';
  try {
    const r = await fetch(API + '/api/workflow/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({template_id: 'custom', nodes: wfNodes, edges: wfEdges}),
    });
    const d = await r.json();
    wfCurrentRunId = d.run_id;
    statusEl.textContent = '✅ 已启动';
  } catch(e) {
    statusEl.textContent = '❌ ' + e.message;
  }
}

// ══ 配置面板渲染（含中文映射） ══
const WF_FIELD_LABELS = {
  // script
  editor_mode: '编辑模式', content: '脚本内容', path: '文件路径',
  type: '脚本格式', parser: '解析方式',
  // strategy
  strategy: '生产策略',
  // tts
  voice_id: '语音模型', speed: '语速', pitch: '音调',
  // model
  provider: '供应商', model: '模型版本', duration: '时长(秒)', seed: '随机种子',
  // material
  source: '素材来源', search_keyword: '搜索关键词', count: '素材数量', orientation: '画面方向',
  // style
  style: '视觉风格', color_grade: '色调',
  // bgm
  mode: '模式', mood: '情绪风格', rhythm: '节奏强度', bpm: 'BPM',
  volume: '音量', duck_enabled: '自动避让',
  // character
  registry_name: '选择角色', outfit_preset: '服装预设',
  use_reference_images: '传递参考图', lip_sync: '唇形同步',
  // storyboard
  camera_style: '运镜风格', transition: '转场方式', scene_count: '场景数量',
  output_format: '输出格式',
  // prompt_gen
  prompt_style: '提示词风格', quality: '品质等级', add_negative: '添加负面提示',
  // subtitle
  format: '字幕格式', position: '字幕位置', style: '字幕样式', max_length: '每行最大字数',
  // output
  format: '视频格式', resolution: '分辨率', output_path: '输出路径', auto_open: '自动打开',
  // audit_gate
  message: '审核提示', auto_approve: '自动通过', timeout_minutes: '超时(分钟)',
  // story_prototype
  genre: '故事类型', title: '故事标题',
  // script_adaptor
  adapt_style: '改编风格',
};

const WF_OPTION_LABELS = {
  auto: '自动', manual: '手动', ai_generated: 'AI生成',
  turbo: '极速', standard: '标准', quality: '高品质',
  kling: '可灵AI', jimeng: '即梦', wan: '万相',
  pexels: 'Pexels图库', local: '本地文件', upload: '上传',
  portrait: '竖屏', landscape: '横屏', square: '方形',
  cinematic: '电影感', hyper_realistic: '超写实', artistic: '艺术风',
  anime: '动漫', vintage: '复古',
  warm: '暖调', cool: '冷调', neutral: '中性', dramatic: '戏剧性', monochrome: '黑白',
  default: '默认', casual: '休闲', sport: '运动', formal: '正式', fantasy: '奇幻',
  happy: '欢快', sad: '伤感', epic: '史诗', calm: '平静', tense: '紧张', upbeat: '积极',
  romantic: '浪漫', inspiring: '激励', healing: '治愈',
  detailed: '详细描述', simple: '简洁指令', stepwise: '分步式',
  json: 'JSON格式', yaml: 'YAML格式', md: 'Markdown格式',
  inline: '在线编辑', path: '文件路径',
  srt: 'SRT格式', ass: 'ASS格式', vtt: 'VTT格式',
  bottom: '底部', top: '顶部', white: '白色', yellow: '黄色', cyan: '青色',
  'hard': '硬切', 'fade_in': '淡入', 'fade_out': '淡出', 'dissolve': '叠化',
  'slide': '划像', 'cut': '跳切',
  default: '默认', running: '跑步装', gym: '健身装', basketball: '篮球装',
  modern: '现代', ancient: '古风', sci_fi: '科幻',
  mystery: '悬疑', comedy: '喜剧',
  'detailed_adapt': '详细改编', 'fast_extract': '快速提炼', 'dialogue_first': '对白优先',
};

// 角色定妆照 body key 映射
const BODY_LABELS = {right_three_quarter:'右侧45°', right_side:'纯右侧面', back:'背面', front:'正面', side:'侧面'};

let wfCharacterList = [];
let wfCharDetails = {};  // {name: {description, art_style, ...}}

async function wfLoadCharacters() {
  try {
    const r = await fetch(`${API}/api/characters`);
    const data = await r.json();
    const chars = data.characters || {};
    const active = data.active || '';
    wfCharacterList = Object.keys(chars).map(name => ({name, active: name === active}));
    // 缓存详情
    wfCharDetails = {};
    for (const [name, info] of Object.entries(chars)) {
      wfCharDetails[name] = info;
    }
  } catch(e) {
    wfCharacterList = [];
  }
}

function wfRenderConfig(nodeId) {
  const el = document.getElementById('wfConfigContent');
  const node = wfNodes.find(n => n.id === nodeId);
  if (!node) { el.innerHTML = '<div style="text-align:center;padding:40px 0;color:var(--text2);font-size:13px">点击节点编辑配置</div>'; return; }
  const def = wfNodeDefs[node.type] || {};
  const config = node.config || {};
  const fields = def.default_config || {};
  const color = def.color || '#888';
  const optMap = def.options_map || {};

  let html = `<div style="margin-bottom:10px">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <span style="font-size:14px;font-weight:600">${def.icon||'●'} ${node.label}</span>
      <button onclick="wfDeleteNode('${node.id}')" style="background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:var(--red);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">删除</button>
    </div>
    <div style="font-size:10px;color:var(--text2);margin-top:4px">${def.description||''}</div>
  </div>`;

  for (const [key, val] of Object.entries(fields)) {
    const curVal = config[key] !== undefined ? config[key] : val;
    const label = WF_FIELD_LABELS[key] || key.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
    const fieldId = 'wf_cfg_' + node.id + '_' + key;
    const fieldOptions = optMap[key];

    // 角色选择下拉（动态加载）
    if (key === 'registry_name') {
      const opts = Array.isArray(wfCharacterList) ? wfCharacterList : [];
      html += `<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${label}</div>
        <select id="${fieldId}" onchange="wfUpdateConfig('${node.id}','${key}',this.value)"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
          <option value="">— 请选择角色 —</option>
          ${opts.map(c => `<option value="${c.name}" ${String(curVal) === c.name ? 'selected' : ''}>${c.name}${c.active ? ' (默认)' : ''}</option>`).join('')}
        </select>
      </div>`;
      continue;
    }

    // 下拉选择（有 options_map）
    if (fieldOptions && Array.isArray(fieldOptions)) {
      html += `<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${label}</div>
        <select id="${fieldId}" onchange="wfUpdateConfig('${node.id}','${key}',this.value)"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
          ${fieldOptions.map(o => `<option value="${o}" ${String(curVal) === String(o) ? 'selected' : ''}>${WF_OPTION_LABELS[o] || o}</option>`).join('')}
        </select>
      </div>`;
      continue;
    }

    // 数字输入
    if (typeof fieldOptions === 'string' && fieldOptions.startsWith('::number:')) {
      const parts = fieldOptions.split(':');
      const min = parts[1] || 0;
      const max = parts[2] || 100;
      const step = parts[3] || 'any';
      html += `<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${label}</div>
        <input type="number" id="${fieldId}" value="${curVal}" min="${min}" max="${max}" step="${step}"
          onchange="wfUpdateConfig('${node.id}','${key}',parseFloat(this.value))"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
      </div>`;
      continue;
    }

    // 长文本（content 等）
    if (key === 'content' && typeof curVal === 'string' && curVal.length > 50) {
      html += `<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${label}</div>
        <textarea id="${fieldId}" rows="4" onchange="wfUpdateConfig('${node.id}','${key}',this.value)"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px;font-family:inherit;resize:vertical">${curVal}</textarea>
      </div>`;
      continue;
    }

    // 布尔值
    if (typeof val === 'boolean') {
      html += `<div style="margin-bottom:6px;display:flex;align-items:center;gap:8px">
        <input type="checkbox" id="${fieldId}" ${curVal ? 'checked' : ''}
          onchange="wfUpdateConfig('${node.id}','${key}',this.checked)"
          style="accent-color:${color}">
        <label for="${fieldId}" style="font-size:11px;color:var(--text2)">${label}</label>
      </div>`;
      continue;
    }

    // 普通文本输入
    html += `<div style="margin-bottom:6px">
      <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${label}</div>
      <input id="${fieldId}" value="${curVal}" onchange="wfUpdateConfig('${node.id}','${key}',this.value)"
        style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
    </div>`;
  }

  // 定妆照生成区（角色节点）
  if (node.type === 'character' && config.registry_name) {
    // 尝试从本地缓存获取角色详情
    const charDetail = wfCharDetails[config.registry_name];
    html += `<div style="margin-top:12px;padding-top:10px;border-top:1px solid var(--border)">
      <div style="font-size:10px;color:var(--text2);margin-bottom:4px">📸 定妆照生成</div>
      ${charDetail ? `
        <div style="font-size:10px;color:var(--text2);margin-bottom:6px;background:var(--bg3);padding:6px 8px;border-radius:4px">
          <div>画风: ${charDetail.art_style || '-'} | 性格: ${charDetail.personality || '-'}</div>
          <div>${charDetail.description ? charDetail.description.slice(0,60)+'...' : ''}</div>
        </div>` : ''}
      <div style="display:flex;gap:8px">
        <button onclick="wfGeneratePortrait()" style="background:#f97316;border:none;color:#fff;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px">🚀 一键生成</button>
        <span id="wfPortraitStatus" style="font-size:10px;color:var(--text2);display:flex;align-items:center">点击生成多角度+表情+网格定妆照</span>
      </div>
      <div id="wfPortraitResult" style="font-size:10px;color:var(--text2);margin-top:4px"></div>
    </div>`;
  }
  el.innerHTML = html;
}

function wfUpdateConfig(nodeId, key, value) {
  const node = wfNodes.find(n => n.id === nodeId);
  if (node) node.config[key] = value;
}

// ══ 定妆照生成 ══
async function wfGeneratePortrait() {
  const resultEl = document.getElementById('wfPortraitResult');
  const statusEl = document.getElementById('wfPortraitStatus');
  if (!resultEl) return;
  const node = wfNodes.find(n => n.id === wfSelectedNodeId);
  if (!node) return;
  const registryName = node.config?.registry_name || '';
  if (!registryName) { resultEl.innerHTML = '❌ 请先选择角色'; return; }
  let description = '';
  try {
    const r = await fetch(API + '/api/characters');
    const d = await r.json();
    const chars = d.characters || {};
    const charInfo = chars[registryName];
    if (charInfo?.description) description = charInfo.description;
  } catch(e) {}
  
  resultEl.innerHTML = '<div style="margin-top:4px">⏳ 生成中: 基准照 → 多角度 → 表情 → 网格</div>';
  if (statusEl) statusEl.innerHTML = '⏳ 生成中...';
  try {
    const r = await fetch(API + '/api/characters/generate-portrait', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({character_name: registryName, description, force: true}),
    });
    const data = await r.json();
    if (r.ok) {
      resultEl.innerHTML = '✅ 定妆照已生成！<a href="javascript:switchView(\'characters\')" style="color:var(--primary);text-decoration:underline">查看角色库</a>';
      if (statusEl) statusEl.innerHTML = '✅ 生成完成';
    } else {
      resultEl.innerHTML = '❌ ' + (data.detail || '失败');
    }
  } catch(e) {
    resultEl.innerHTML = '❌ ' + e.message;
  }
}

// ── Summary ──
async function loadSummary() {
  const el = document.getElementById('summaryContent');
  try {
    const [sumR, heatR, dailyR] = await Promise.all([
      fetch('/api/summary').then(r=>r.json()),
      fetch('/api/heatmap').then(r=>r.json()),
      fetch('/api/daily-summary').then(r=>r.json()),
    ]);
    const heat = heatR.machines || {};
    const daily = dailyR.machines || {};
    let html = '';
    // 热力图卡片
    for (const [hostname, info] of Object.entries(heat)) {
      const acts = info.hourly || [];
      const total = acts.reduce((a,b)=>a+b,0);
      const barMax = Math.max(...acts, 1);
      html += `<div class="card"><h3>${hostname}</h3>
        <div style="font-size:12px;color:var(--text2);margin-bottom:8px">今日心跳: ${total} 次</div>
        <div style="display:flex;gap:2px;height:40px;align-items:flex-end">`;
      for (let h=0;h<24;h++) {
        const pct = acts[h] / barMax * 100;
        html += `<div title="${h}时: ${acts[h]}次" style="flex:1;background:${acts[h] > barMax*0.7 ? 'var(--coral)' : acts[h] > barMax*0.3 ? 'var(--amber)' : 'var(--bg3)'};height:${Math.max(pct,3)}%;border-radius:2px 2px 0 0"></div>`;
      }
      html += `</div><div style="display:flex;justify-content:space-between;font-size:9px;color:var(--text2);margin-top:2px">
        <span>0时</span><span>6时</span><span>12时</span><span>18时</span><span>24时</span>
      </div>`;
      // 最近事件
      const ms = daily[hostname];
      if (ms && ms.events && ms.events.length) {
        html += `<div style="margin-top:8px;font-size:11px;color:var(--text2)">最近事件:</div>`;
        ms.events.slice(-3).forEach(ev => {
          html += `<div style="font-size:10px;color:var(--text2);padding:2px 0">• ${ev.type}: ${JSON.stringify(ev.payload||{}).slice(0,40)}</div>`;
        });
      }
      html += `</div>`;
    }
    if (!html) html = '<div class="card"><div style="color:var(--text2)">暂无推送数据</div></div>';
    el.innerHTML = html;
  } catch(e) { el.innerHTML = `<div class="error">❌ ${e.message}</div>`; }
}

// ── View switcher ──
const origSwitch = switchView;
switchView = function(v) {
  // 隐藏所有固定视图
  document.querySelectorAll('[id^="view-"]').forEach(el => el.classList.add('hidden'));
  // 隐藏所有插件视图
  document.querySelectorAll('[id^="plugin-view-"]').forEach(el => el.style.display = 'none');
  
  origSwitch(v);
  if (v === 'timeline') loadTimeline();
  if (v === 'alerts') loadAlerts();
  if (v === 'summary') loadSummary();
  // 插件视图
  if (v.startsWith('plugin-')) {
    const name = v.replace('plugin-', '');
    loadPluginView(name);
  }
};

// ══ 模块化角色生成流 ══

// 角色模块定义（前端本地版，不依赖后端）
const CHAR_GEN_MODULES = {
  identity: { icon: '🆔', label: '身份', desc: '姓名/性别/年龄/种族' },
  face_shape: { icon: '🗿', label: '面部轮廓', desc: '脸型/下颌/颧骨' },
  facial_features: { icon: '👁️', label: '五官细节', desc: '眼/眉/鼻/唇' },
  hair_skin: { icon: '💇', label: '头发&皮肤', desc: '发型/肤色/妆容' },
  body: { icon: '🏋️', label: '体型姿态', desc: '身高/体型/姿态' },
  clothing: { icon: '👔', label: '服装配饰', desc: '上衣/下装/配饰' },
  expression_scene: { icon: '😊', label: '神态&场景', desc: '表情/光线/背景' },
};

// 每个模块的字段配置（用于渲染表单）
const CHAR_GEN_FIELDS = {
  identity: [
    { key:'name', label:'角色名', type:'text', ph:'如: 阿远' },
    { key:'gender', label:'性别', type:'select', opts:['男性','女性'] },
    { key:'age', label:'年龄', type:'select', opts:['少年','青年','壮年','中年','老年'] },
    { key:'ethnicity', label:'地域', type:'select', opts:['中国','东亚','东南亚','南亚','欧美'] },
  ],
  face_shape: [
    { key:'shape', label:'脸型', type:'select', opts:['鹅蛋脸','瓜子脸','圆脸','方脸','国字脸','长脸','菱形脸','心形脸'] },
    { key:'jaw', label:'下颌线', type:'select', opts:['清晰分明','柔和模糊','棱角突出','圆润温和'] },
    { key:'cheekbone', label:'颧骨', type:'select', opts:['适中自然','高突出','饱满圆润','低平'] },
    { key:'forehead', label:'额头', type:'select', opts:['饱满宽阔','适中','窄小','高额头'] },
  ],
  facial_features: [
    { key:'eyes_shape', label:'眼型', type:'select', opts:['丹凤眼','杏眼','桃花眼','圆眼','细长眼','单眼皮','双眼皮','内双'] },
    { key:'eyes_color', label:'瞳孔色', type:'select', opts:['深褐','浅褐','黑色','琥珀色','灰色','蓝色','绿色'] },
    { key:'eyes_spirit', label:'眼神', type:'text', ph:'如: 深邃锐利、清澈温柔' },
    { key:'eyebrows', label:'眉型', type:'select', opts:['剑眉','柳叶眉','一字眉','上挑眉','弯眉','粗眉','细长眉'] },
    { key:'nose', label:'鼻型', type:'select', opts:['高挺','挺直窄小','中等挺拔','低平柔和'] },
    { key:'nose_tip', label:'鼻头', type:'select', opts:['小巧圆润','圆润饱满','尖翘','略宽'] },
    { key:'lips', label:'唇型', type:'select', opts:['薄唇','厚唇','M形唇','饱满','樱桃小嘴','微笑唇'] },
    { key:'lips_state', label:'唇状态', type:'select', opts:['自然闭合','微张','紧抿','嘴角微扬','含笑意'] },
  ],
  hair_skin: [
    { key:'hair_style', label:'发型', type:'select', opts:['短发','寸头','中长发','背头','三七分','齐刘海','碎发','高马尾','披肩发'] },
    { key:'hair_color', label:'发色', type:'select', opts:['黑色','深棕','浅棕','亚麻色','灰色','银白'] },
    { key:'hair_detail', label:'发型细节', type:'text', ph:'如: 两侧收短顶部略长' },
    { key:'skin_tone', label:'肤色', type:'select', opts:['冷白皮','暖白皮','健康小麦','蜜色','古铜色','深色'] },
    { key:'skin_texture', label:'肤质', type:'select', opts:['细腻光滑','自然肌理','毛孔可见','水润光泽'] },
    { key:'complexion', label:'气色', type:'select', opts:['红润健康','略显苍白','容光焕发','自然均匀'] },
    { key:'makeup', label:'妆容风格', type:'select', opts:['素颜','淡妆','精致妆容','裸妆','烟熏妆'] },
    { key:'blemish', label:'特殊标记', type:'text', ph:'如: 右眉上细疤、左颊美人痣' },
  ],
  body: [
    { key:'height', label:'身高', type:'select', opts:['矮小(155-165)','中等(165-175)','中高(175-185)','高大(185+)'] },
    { key:'build', label:'体型', type:'select', opts:['纤细瘦弱','偏瘦','标准匀称','健壮','壮硕','魁梧'] },
    { key:'shoulder', label:'肩宽', type:'select', opts:['窄肩','标准','宽肩','厚肩'] },
    { key:'posture', label:'姿态', type:'select', opts:['挺拔','自然放松','微驼','端庄','慵懒'] },
  ],
  clothing: [
    { key:'top', label:'上装', type:'text', ph:'如: 深灰色拉链运动夹克' },
    { key:'inner', label:'内搭', type:'text', ph:'如: 白色圆领速干内衬' },
    { key:'bottom', label:'下装', type:'text', ph:'如: 深蓝色牛仔裤' },
    { key:'shoes', label:'鞋子', type:'text', ph:'如: 白色跑步鞋' },
    { key:'accessories', label:'配饰', type:'text', ph:'如: 蓝色无线运动耳机(右耳)、细框眼镜' },
    { key:'style_tag', label:'穿搭风格', type:'select', opts:['运动休闲','商务正装','日系清新','街头潮流','简约素雅'] },
  ],
  expression_scene: [
    { key:'base_mood', label:'情绪基调', type:'select', opts:['平静从容','温和友善','冷峻严肃','沉稳内敛','自信昂扬','恬静淡然'] },
    { key:'expression', label:'表面表情', type:'select', opts:['中性无表情','淡淡微笑','微笑','开怀大笑','皱眉沉思','目光坚定'] },
    { key:'eye_spirit', label:'眼神细节', type:'text', ph:'如: 目光坚定直视前方、眼中带笑意' },
    { key:'aura', label:'气质气场', type:'text', ph:'如: 沉稳内敛不怒自威、亲和温暖如沐春风' },
    { key:'light_type', label:'光型', type:'select', opts:['柔光箱均匀布光','美人碟柔光','伦勃朗光','分割光','逆光轮廓光','阴天漫射光'] },
    { key:'lens', label:'镜头', type:'select', opts:['标准50mm','中焦85mm','长焦135mm'] },
    { key:'background', label:'背景环境', type:'text', ph:'如: 纯灰色专业背景、清晨城市街道' },
  ],
};

let charGenLayerData = {};  // 存储所有模块的当前值

function loadCharGen() {
  document.getElementById('charGenStep1').classList.remove('hidden');
  document.getElementById('charGenStep2').classList.add('hidden');
  document.getElementById('charGenStep3').classList.add('hidden');
  document.getElementById('charGenDirection').value = '';
  document.getElementById('charGenStep1Result').innerHTML = '';
  document.getElementById('charGenStep2Result').innerHTML = '';
  document.getElementById('charGenResultBody').innerHTML = '';
  charGenLayerData = {};
  // 渲染模块Tab
  renderCharGenTabs();
  // 默认选中第一个模块
  charGenSwitchTab(Object.keys(CHAR_GEN_MODULES)[0]);
}

function renderCharGenTabs() {
  const tabsEl = document.getElementById('charGenTabs');
  tabsEl.innerHTML = Object.entries(CHAR_GEN_MODULES).map(([id, mod]) =>
    `<div class="char-gen-tab" data-tab="${id}" onclick="charGenSwitchTab('${id}')"
      style="padding:5px 10px;border-radius:6px;cursor:pointer;font-size:11px;
             background:var(--bg3);color:var(--text2);border:1px solid transparent;
             display:flex;align-items:center;gap:4px;
             transition:all .15s">
      ${mod.icon} ${mod.label}
    </div>`
  ).join('');
}

function charGenSwitchTab(tabId) {
  // 更新tab高亮
  document.querySelectorAll('.char-gen-tab').forEach(el => {
    const isActive = el.dataset.tab === tabId;
    el.style.background = isActive ? 'var(--primary)' : 'var(--bg3)';
    el.style.color = isActive ? '#fff' : 'var(--text2)';
    el.style.borderColor = isActive ? 'var(--primary)' : 'transparent';
  });
  
  // 渲染选中模块的表单
  const mod = CHAR_GEN_MODULES[tabId];
  const fields = CHAR_GEN_FIELDS[tabId] || [];
  const container = document.getElementById('charGenPanelContent');
  
  let html = `<div style="background:var(--bg3);border-radius:8px;padding:14px;margin-bottom:8px">
    <div style="font-size:12px;color:var(--text2);margin-bottom:8px">${mod.desc}</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">`;
  
  for (const f of fields) {
    const val = (charGenLayerData[tabId] || {})[f.key] || '';
    const fieldId = 'cg_' + tabId + '_' + f.key;
    
    if (f.type === 'select') {
      html += `<div>
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${f.label}</div>
        <select id="${fieldId}" onchange="charGenFieldChange('${tabId}','${f.key}',this.value)"
          style="width:100%;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
          <option value="">— 选择 —</option>
          ${(f.opts||[]).map(o => `<option value="${o}" ${val === o ? 'selected' : ''}>${o}</option>`).join('')}
        </select>
      </div>`;
    } else {
      html += `<div style="${f.key === 'eye_spirit' || f.key === 'background' || f.key === 'accessories' ? 'grid-column:1/-1' : ''}">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${f.label}</div>
        <input id="${fieldId}" value="${val}" placeholder="${f.ph||''}"
          onchange="charGenFieldChange('${tabId}','${f.key}',this.value)"
          style="width:100%;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
      </div>`;
    }
  }
  
  html += `</div></div>`;
  
  // 这个模块的文本描述预览
  html += `<div style="font-size:10px;color:var(--text2);background:var(--bg2);padding:6px 10px;border-radius:4px;margin-bottom:4px">
    📝 当前 <strong>${mod.label}</strong> 描述: <span id="cg_preview_${tabId}">${buildLayerDesc(tabId)}</span>
  </div>`;
  
  container.innerHTML = html;
  charGenUpdatePreview();
}

function charGenFieldChange(tabId, key, value) {
  if (!charGenLayerData[tabId]) charGenLayerData[tabId] = {};
  charGenLayerData[tabId][key] = value;
  // 更新该模块的描述预览
  const prev = document.getElementById('cg_preview_' + tabId);
  if (prev) prev.textContent = buildLayerDesc(tabId);
  // 更新总预览
  charGenUpdatePreview();
}

function buildLayerDesc(tabId) {
  const data = charGenLayerData[tabId] || {};
  const parts = [];
  for (const v of Object.values(data)) {
    if (v) parts.push(v);
  }
  return parts.join('、') || '—';
}

function buildFullDescription() {
  const parts = [];
  // 按模块顺序组装
  const moduleOrder = Object.keys(CHAR_GEN_MODULES);
  for (const tabId of moduleOrder) {
    const desc = buildLayerDesc(tabId);
    if (desc && desc !== '—') {
      parts.push(`【${CHAR_GEN_MODULES[tabId].label}】${desc}`);
    }
  }
  return parts.join('\n');
}

function charGenUpdatePreview() {
  const el = document.getElementById('charGenPromptPreview');
  if (!el) return;
  const full = buildFullDescription();
  el.value = full || '— 填写模块后自动生成预览 —';
}

async function charGenAutoFill() {
  const dirEl = document.getElementById('charGenDirection');
  const resultEl = document.getElementById('charGenStep1Result');
  const direction = dirEl.value.trim();
  if (!direction) { resultEl.innerHTML = '❌ 请输入角色方向'; return; }
  
  resultEl.innerHTML = '⏳ AI 正在生成完整角色定义...';
  document.getElementById('charGenStep2').classList.remove('hidden');
  
  try {
    const r = await fetch(API + '/api/characters/expand-direction', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({direction}),
    });
    const data = await r.json();
    const description = data.description || direction;
    
    // 从描述中智能填充各模块的字段
    charGenAutoFillFromDescription(description);
    
    // 自动生成角色名
    const nameMatch = description.match(/([\u4e00-\u9fff]{2,6})(?:男性|女性|少年|少女|中年|老人)/);
    if (nameMatch) {
      document.getElementById('charGenName').value = nameMatch[1].slice(-3).replace(/[的男女人]/g,'');
    }
    
    resultEl.innerHTML = '✅ 各模块已自动填充！请逐项检查调整';
    // 默认选中"身份"模块
    charGenSwitchTab('identity');
    document.getElementById('charGenStep2').scrollIntoView({behavior: 'smooth', block: 'start'});
  } catch(e) {
    resultEl.innerHTML = '❌ 自动填充失败: ' + e.message;
    // 降级：显示空面板
    charGenSwitchTab('identity');
    document.getElementById('charGenStep2').classList.remove('hidden');
  }
}

function charGenAutoFillFromDescription(desc) {
  // 智能提取：从自然语言描述中提取各字段值
  const match = (pattern) => {
    const m = new RegExp(pattern).exec(desc);
    return m ? m[1] : '';
  };
  
  // 试探性地填充各字段
  charGenLayerData = {};
  
  // 身份
  charGenLayerData.identity = {
    gender: match(/(男性|女性)/),
    age: match(/(少年|青年|壮年|中年|老年)/),
    ethnicity: match(/(中国|东亚|东南亚|南亚|欧美)/) || '中国',
    name: match(/([\u4e00-\u9fff]{2,4})[，,]/),
  };
  
  // 面部轮廓
  charGenLayerData.face_shape = {
    shape: match(/(鹅蛋脸|瓜子脸|圆脸|方脸|国字脸|长脸|菱形脸|心形脸)/),
    jaw: match(/(清晰分明|柔和模糊|棱角突出|圆润温和)/),
    cheekbone: match(/(高突出|饱满圆润|低平)/) || '适中自然',
    forehead: match(/(饱满宽阔|窄小|高额头)/) || '适中',
  };
  
  // 五官
  charGenLayerData.facial_features = {
    eyes_shape: match(/(丹凤眼|杏眼|桃花眼|圆眼|细长眼|单眼皮|双眼皮|内双)/),
    eyes_color: match(/(深褐|浅褐|黑色|琥珀色|灰色|蓝色|绿色)/) || '深褐',
    eyes_spirit: match(/(深邃[^，。]*?|清澈[^，。]*?|锐利[^，。]*?|温柔[^，。]*?|沉稳[^，。]*?)/) || '',
    eyebrows: match(/(剑眉|柳叶眉|一字眉|上挑眉|弯眉|粗眉|细长眉)/),
    nose: match(/(高挺|挺直窄小|中等挺拔|低平柔和)/) || '高挺',
    nose_tip: match(/(小巧圆润|圆润饱满|尖翘|略宽)/) || '适中',
    lips: match(/(薄唇|厚唇|M形唇|饱满|樱桃小嘴|微笑唇)/),
    lips_state: match(/(微张|紧抿|嘴角微扬|含笑意)/) || '自然闭合',
  };
  
  // 头发皮肤
  charGenLayerData.hair_skin = {
    hair_style: match(/(短发|寸头|中长发|背头|三七分|齐刘海|碎发|高马尾|披肩发)/) || '短发',
    hair_color: match(/(黑色|深棕|浅棕|亚麻色|灰色|银白)/) || '黑色',
    hair_detail: match(/(两侧收短[^，。]*?|发际线[^，。]*?)/) || '',
    skin_tone: match(/(冷白皮|暖白皮|健康小麦|蜜色|古铜色|深色)/) || '健康小麦',
    skin_texture: match(/(细腻光滑|自然肌理|毛孔可见|水润光泽)/) || '自然肌理',
    complexion: match(/(红润健康|略显苍白|容光焕发|自然均匀)/) || '红润健康',
    makeup: match(/(素颜|淡妆|精致妆容|裸妆|烟熏妆)/) || '素颜',
    blemish: match(/([^，。]*?疤[^，。]*?|[^，。]*?痣[^，。]*?|[^，。]*?纹[^，。]*?)/) || '',
  };
  
  // 体型
  const heightMatch = desc.match(/(\d+)/);
  const heightStr = heightMatch ? (parseInt(heightMatch[1]) < 170 ? '中等(165-175)' : parseInt(heightMatch[1]) < 180 ? '中高(175-185)' : '高大(185+)') : '';
  charGenLayerData.body = {
    height: heightStr,
    build: match(/(纤细瘦弱|偏瘦|标准匀称|健壮|壮硕|魁梧)/),
    shoulder: match(/(窄肩|标准|宽肩|厚肩)/) || '标准',
    posture: match(/(挺拔|自然放松|微驼|端庄|慵懒)/) || '挺拔',
  };
  
  // 服装配饰
  const topMatch = match(/身穿([^，。]*?夹克|[^，。]*?卫衣|[^，。]*?T恤|[^，。]*?衬衫|[^，。]*?外套|[^，。]*?运动装)/);
  const innerMatch = match(/内搭([^，。]*?内衬|[^，。]*?T恤|[^，。]*?打底|[^，。]*?背心)/);
  const bottomMatch = match(/(下穿|下着|穿着)[^，。]*?(牛仔裤|[^，。]*?短裤|[^，。]*?长裤|[^，。]*?裙子)/);
  const accMatch = match(/[佩戴戴着带着]([^，。]*?耳机|[^，。]*?眼镜|[^，。]*?手表|[^，。]*?手环|[^，。]*?帽子|[^，。]*?项链)/);
  
  charGenLayerData.clothing = {
    top: topMatch || '',
    inner: innerMatch || '',
    bottom: bottomMatch ? bottomMatch[0] : '',
    shoes: '',
    accessories: accMatch || '',
    style_tag: match(/(运动休闲|商务正装|日系清新|街头潮流|简约素雅)/) || '',
  };
  
  // 神态场景
  charGenLayerData.expression_scene = {
    base_mood: match(/(平静从容|温和友善|冷峻严肃|沉稳内敛|自信昂扬|恬静淡然)/),
    expression: match(/(中性无表情|淡淡微笑|微笑|开怀大笑|皱眉沉思|目光坚定)/),
    eye_spirit: match(/(目光[^，。]*?|眼神[^，。]*?)/) || '',
    aura: match(/(沉稳内敛[^，。]*|亲和温暖[^，。]*|疏离清冷[^，。]*)/) || '',
    light_type: '柔光箱均匀布光',
    lens: '中焦85mm',
    background: match(/([^，。]*?背景[^，。]*?|在[^，。]*?[城里路巷][^，。]*?|[^，。]*?环境[^，。]*?)/) || '纯灰色专业背景',
  };
}

async function charGenRun() {
  const resultEl = document.getElementById('charGenStep2Result');
  const name = document.getElementById('charGenName').value.trim();
  const seed = parseInt(document.getElementById('charGenSeed').value) || 42;
  const genImages = document.getElementById('charGenGenImages').checked;
  
  // 收集所有模块数据
  const allData = {};
  for (const [tabId, data] of Object.entries(charGenLayerData)) {
    for (const [key, val] of Object.entries(data)) {
      if (val) allData[`${tabId}.${key}`] = val;
    }
  }
  
  const fullDesc = buildFullDescription();
  if (!fullDesc || fullDesc === '— 填写模块后自动生成预览 —') {
    resultEl.innerHTML = '❌ 请至少填写1个模块的字段';
    return;
  }
  
  resultEl.innerHTML = '⏳ 正在生成角色...<br>';
  resultEl.innerHTML += '<div style="font-size:10px;color:var(--text2);margin-top:4px">步骤: 注册属性 → ' + (genImages ? '生成变体 → ' : '') + '写入知识库</div>';
  
  try {
    const r = await fetch(API + '/api/characters/generate-from-direction', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        direction: fullDesc,
        name: name,
        generate_images: genImages,
        seed: seed,
        layers: allData,
      }),
    });
    const data = await r.json();
    if (!r.ok) {
      resultEl.innerHTML = '❌ 生成失败: ' + (data.detail || '未知错误');
      return;
    }
    
    document.getElementById('charGenStep3').classList.remove('hidden');
    document.getElementById('charGenResultTitle').textContent = `✅ 角色「${data.name}」生成完成`;
    
    let html = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
      <div style="background:var(--bg3);border-radius:6px;padding:14px">
        <div style="font-size:11px;color:var(--text2);font-weight:600;margin-bottom:6px">📋 角色信息</div>
        <div style="font-size:12px;color:var(--text);line-height:1.6">${data.description}</div>
      </div>
      <div style="background:var(--bg3);border-radius:6px;padding:14px">
        <div style="font-size:11px;color:var(--text2);font-weight:600;margin-bottom:6px">🏷 标签 & 属性</div>
        <div style="font-size:11px;color:var(--text2)">
          外观特征: ${(data.attributes?.appearance || []).join('、') || '-'}<br>
          性格: ${data.attributes?.personality || '-'}<br>
          画风: ${data.attributes?.art_style || '-'}<br>
          音色: ${data.attributes?.voice_style || '-'}
        </div>
      </div>
    </div>`;
    
    if (data.baseline && data.baseline.path) {
      html += `<div style="margin-top:12px">
        <div style="font-size:12px;color:var(--text2);font-weight:600;margin-bottom:6px">📸 生成结果</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px">`;
      if (data.baseline && data.baseline.url) {
        html += `<div style="text-align:center"><img src="${data.baseline.url}" style="width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:6px;background:var(--bg3)" onerror="this.parentElement.style.display='none'"><div style="font-size:10px;color:var(--text2);margin-top:2px">正面基准</div></div>`;
      }
      if (data.angles) {
        for (const [angle, info] of Object.entries(data.angles)) {
          if (info && info.url) {
            html += `<div style="text-align:center"><img src="${info.url}" style="width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:6px;background:var(--bg3)" onerror="this.parentElement.style.display='none'"><div style="font-size:10px;color:var(--text2);margin-top:2px">${BODY_LABELS[angle] || angle}</div></div>`;
          }
        }
      }
      if (data.expressions) {
        const exprLabels = {neutral:'中性', smile:'微笑', focused:'专注', laugh:'大笑', serious:'严肃'};
        for (const [expr, info] of Object.entries(data.expressions)) {
          if (info && info.url) {
            html += `<div style="text-align:center"><img src="${info.url}" style="width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:6px;background:var(--bg3)" onerror="this.parentElement.style.display='none'"><div style="font-size:10px;color:var(--text2);margin-top:2px">${exprLabels[expr] || expr}</div></div>`;
          }
        }
      }
      if (data.grid && data.grid.url) {
        html += `<div style="text-align:center;grid-column:1/-1"><img src="${data.grid.url}" style="width:100%;max-height:300px;object-fit:contain;border-radius:6px;background:var(--bg3)" onerror="this.parentElement.style.display='none'"><div style="font-size:10px;color:var(--text2);margin-top:2px">网格定妆照</div></div>`;
      }
      html += `</div></div>`;
    }
    
    html += `<div style="margin-top:12px;display:flex;gap:8px">
      <button onclick="switchView('characters')" style="background:var(--primary);border:none;color:#fff;padding:6px 16px;border-radius:4px;cursor:pointer;font-size:12px">📋 查看角色库</button>
      <button onclick="switchView('workflow')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 16px;border-radius:4px;cursor:pointer;font-size:12px">🔀 去工作流</button>
      <button onclick="loadCharGen()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 16px;border-radius:4px;cursor:pointer;font-size:12px">🔄 新建角色</button>
    </div>`;
    
    document.getElementById('charGenResultBody').innerHTML = html;
    resultEl.innerHTML = '✅ 角色生成完成！';
    document.getElementById('charGenStep3').scrollIntoView({behavior: 'smooth', block: 'center'});
  } catch(e) {
    resultEl.innerHTML = '❌ 生成失败: ' + e.message;
  }
}

// ── Characters ──
async function loadCharacters() {
  const el = document.getElementById('characterGrid');
  const countEl = document.getElementById('charCount');
  el.innerHTML = '<div class="loading">加载角色数据...</div>';
  try {
    const r = await fetch(`${API}/api/characters`);
    const d = await r.json();
    const chars = d.characters || {};
    const active = d.active || '';
    const entries = Object.entries(chars);
    countEl.textContent = `共 ${entries.length} 个角色`;

    if (!entries.length) {
      el.innerHTML = '<div class="error" style="padding:40px">暂无角色数据</div>';
      return;
    }

    el.innerHTML = entries.map(([name, char]) => {
      const isActive = name === active;
      const refImgs = char.reference_images || {};
      const exprs = refImgs.expressions || {};
      const exprCount = Object.keys(exprs).length;
      // 兼容新旧两种 key 名: 旧=grid/portrait, 新=face_anchor/baseline/body
      const hasGrid = !!(refImgs.grid || refImgs.face_anchor || refImgs.baseline);
      const hasPortrait = !!(refImgs.portrait || refImgs.face_anchor);
      const hasBody = refImgs.body && Object.values(refImgs.body).some(Boolean);
      const hasRealPhoto = !!(refImgs.real_photo_fullbody || refImgs.real_photo_portrait);
      return `<div style="background:var(--bg2);border-radius:var(--radius);padding:20px;border:1px solid ${isActive ? 'var(--primary)' : 'var(--border)'}">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px">
            <div>
              <div style="font-weight:600;font-size:16px">${name}</div>
              <div style="font-size:11px;color:var(--text2)">${char.description||''}</div>
            </div>
          </div>
          ${isActive ? `<span style="padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:rgba(99,102,241,.15);color:var(--primary);border:1px solid rgba(99,102,241,.3)">当前角色</span>` : ''}
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;margin-bottom:10px;color:var(--text2)">
          <div>画风: ${char.art_style||'-'}</div>
          <div>音色: ${char.voice_style||'-'}</div>
          <div>性格: ${char.personality||'-'}</div>
          <div>BGM: ${char.default_bgm_style||'-'}</div>
        </div>

        ${char.prompt_template ? `<div style="margin-bottom:10px;font-size:11px;color:var(--text2)">
          <span style="font-weight:600">提示词模板:</span>
          <div style="background:var(--bg3);padding:8px;border-radius:6px;margin-top:4px;font-family:mono;font-size:10px;word-break:break-all">${Object.values(char.prompt_template).join(' | ')}</div>
        </div>` : ''}

        ${char.outfit_presets ? `<div style="margin-bottom:10px">
          <div style="font-size:11px;color:var(--text2);font-weight:600;margin-bottom:4px">穿搭预设</div>
          <div style="display:flex;gap:4px;flex-wrap:wrap">${Object.keys(char.outfit_presets).map(k => `<span style="background:var(--bg3);padding:2px 8px;border-radius:4px;font-size:10px">${k}</span>`).join('')}</div>
        </div>` : ''}

        <div style="font-size:11px;color:var(--text2)">
          <div>定妆照: ${hasGrid ? '✅ 已生成' : '❌ 未生成'} ${hasRealPhoto ? '·📷 真人参考照' : ''} ${hasBody ? `·${Object.keys(refImgs.body).length}个角度` : ''}</div>
          ${char.seed ? `<div>固定 Seed: ${char.seed}</div>` : ''}
        </div>

        ${hasBody ? renderCharPortraitGallery(refImgs, name) : ''}

        ${!hasBody && hasRealPhoto ? `<div style="margin-top:8px;border-top:1px solid var(--border);padding-top:8px">
          <div style="font-size:10px;color:var(--text2)">📷 已上传真人参考照，点击「视频工厂→工作流编辑器」中的角色节点，生成定妆照</div>
        </div>` : ''}

        ${char.appearance && char.appearance.length ? `<div style="margin-top:8px;border-top:1px solid var(--border);padding-top:8px">
          <div style="font-size:11px;color:var(--text2);font-weight:600;margin-bottom:4px">外观特征</div>
          <ul style="margin:0;padding-left:16px;font-size:11px;color:var(--text2)">${char.appearance.map(a => `<li>${a}</li>`).join('')}</ul>
        </div>` : ''}
      </div>`;
    }).join('');
  } catch(e) {
    el.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}

// ── 角色定妆照画廊预览（兼容新旧 body key） ──
function renderCharPortraitGallery(refImgs, name) {
  const body = refImgs.body || {};
  const faceAnchor = refImgs.face_anchor || refImgs.baseline || '';
  const charName = faceAnchor ? faceAnchor.split('/').slice(-2, -1)[0] : name;
  const base = charName ? API + '/api/portrait-files/' + encodeURIComponent(charName) : '';
  
  const items = [];
  if (faceAnchor) items.push({
    label: '正面基准', 
    src: base + '/' + faceAnchor.split('/').pop(),
    isAnchor: true,
  });
  for (const [k, p] of Object.entries(body)) {
    if (p) {
      items.push({
        label: BODY_LABELS[k] || k,
        src: base + '/' + p.split('/').pop(),
        isAnchor: false,
      });
    }
  }
  
  // 也尝试显示真人参考照
  const realPhoto = refImgs.real_photo_fullbody || refImgs.real_photo_portrait || '';
  
  const folderPath = faceAnchor ? faceAnchor.substring(0, faceAnchor.lastIndexOf('/')) : '';
  const colCount = Math.min(items.length + (realPhoto ? 1 : 0), 4);
  
  return `<div style="margin-top:10px;border-top:1px solid var(--border);padding-top:10px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
      <span style="font-size:12px;color:var(--text2);font-weight:600">📸 定妆照预览</span>
      ${folderPath ? `<a href="file://${folderPath}" target="_blank" style="font-size:10px;color:var(--primary);text-decoration:none">📂 打开文件夹</a>` : ''}
    </div>
    <div style="display:grid;grid-template-columns:repeat(${colCount},1fr);gap:6px">
      ${items.map(item => `<div style="text-align:center">
        <img src="${item.src}" style="width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:6px;background:var(--bg3);border:2px solid ${item.isAnchor ? 'var(--primary)' : 'transparent'}"
          onerror="this.parentElement.style.display='none'"
          onclick="window.open('file://${faceAnchor ? body[Object.keys(body).find(k => body[k].split('/').pop() === item.src.split('/').pop())] || faceAnchor : ''}')">
        <div style="font-size:10px;color:var(--text2);margin-top:2px">${item.label}</div>
      </div>`).join('')}
    </div>
  </div>`;
}

// ── Capabilities ──
let currentCapGroup = null;
async function loadCapabilities() {
  const el = document.getElementById('capabilityContent');
  const tabsEl = document.getElementById('capGroupTabs');
  const countEl = document.getElementById('capCount');
  el.innerHTML = '<div class="loading">加载原子能力...</div>';
  try {
    const r = await fetch(`${API}/api/capabilities`);
    const d = await r.json();
    const groups = d.groups || [];
    const matrix = d.matrix || [];
    countEl.textContent = `共 ${d.total_items||0} 个能力`;

    if (!groups.length) {
      el.innerHTML = '<div class="error" style="padding:40px">暂无能力数据</div>';
      return;
    }

    // 分组标签
    tabsEl.innerHTML = groups.map((g, i) =>
      `<button class="btn ${i === 0 ? 'active' : ''}" onclick="switchCapGroup(${i})" style="${i === 0 ? 'background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px' : 'background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px'}">${g.name} (${g.items.length})</button>`
    ).join('');

    currentCapGroup = 0;
    renderCapGroup(groups[0], matrix);
  } catch(e) {
    el.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}

function switchCapGroup(idx) {
  currentCapGroup = idx;
  const tabs = document.getElementById('capGroupTabs').children;
  for (let i = 0; i < tabs.length; i++) {
    tabs[i].style.background = i === idx ? 'var(--primary)' : 'var(--bg2)';
    tabs[i].style.color = i === idx ? '#fff' : 'var(--text)';
    tabs[i].style.border = i === idx ? 'none' : '1px solid var(--border)';
  }
  fetch(`${API}/api/capabilities`).then(r => r.json()).then(d => {
    renderCapGroup(d.groups[idx], d.matrix);
  });
}

function renderCapGroup(group, matrix) {
  const el = document.getElementById('capabilityContent');
  if (!group || !group.items) {
    el.innerHTML = '<div class="error">无数据</div>';
    return;
  }

  el.innerHTML = `<div class="chart-box">
    <div style="font-size:14px;font-weight:600;margin-bottom:12px">${group.name}</div>
    <table><thead><tr>${Object.keys(group.items[0]||{}).map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>
      ${group.items.map(item => `<tr>${Object.values(item).map(v => `<td>${v||'-'}</td>`).join('')}</tr>`).join('')}
    </tbody></table>
  </div>`;

  // 如果当前是第一个分组（音频），且有关联的 matrix，显示交叉矩阵
  if (matrix && matrix.length && currentCapGroup === 0) {
    const matrixHeaders = Object.keys(matrix[0]?.usages || {});
    el.innerHTML += `<div class="chart-box" style="margin-top:16px">
      <div style="font-size:14px;font-weight:600;margin-bottom:12px">交叉能力矩阵 (全量)</div>
      <div style="font-size:11px;color:var(--text2);margin-bottom:8px">⬛ = 核心依赖 · ⬜ = 可用 · ↔ = 可选接入</div>
      <table><thead><tr><th style="position:sticky;left:0;background:var(--bg2)">能力</th>${matrixHeaders.map(h => `<th style="font-size:10px">${h}</th>`).join('')}</tr></thead><tbody>
        ${matrix.map(row => `<tr><td style="position:sticky;left:0;background:var(--bg2);font-weight:600;white-space:nowrap">${row.name}</td>${matrixHeaders.map(h => {
          const v = row.usages[h] || '';
          const bg = v.includes('⬛') ? 'rgba(99,102,241,.15)' : v.includes('↔') ? 'rgba(245,158,11,.1)' : v ? 'rgba(34,197,94,.08)' : '';
          return `<td style="text-align:center;background:${bg};font-size:11px">${v||'-'}</td>`;
        }).join('')}</tr>`).join('')}
      </tbody></table>
    </div>`;
  }
}

// ── Plugin Detail View ──
async function loadPluginView(name) {
  let viewId = 'plugin-view-' + name;
  document.querySelectorAll('[id^="plugin-view-"]').forEach(el => el.style.display = 'none');
  
  let el = document.getElementById(viewId);
  if (!el) {
    el = document.createElement('div');
    el.id = viewId;
    document.getElementById('app').appendChild(el);
  }
  el.style.display = 'block';
  el.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text2)">加载中...</div>';

  try {
    const [metaR, sumR, detR] = await Promise.all([
      fetch('/api/plugins').then(r=>r.json()),
      fetch('/api/plugins/'+name+'/summary').then(r=>r.json()),
      fetch('/api/plugins/'+name+'/detail').then(r=>r.json()),
    ]);

    const meta = (metaR.plugins || []).find(p => p.name === name) || {};
    const summary = sumR.data || {};
    const detail = detR.data || {};
    
    let html = '<h2 style="font-size:18px;font-weight:500;margin-bottom:16px">' + (meta.icon || '') + ' ' + (meta.label || name) + '</h2>';

    // Summary cards
    var machData = summary['各机器'] || {};
    if (Object.keys(machData).length > 0) {
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;margin-bottom:20px">';
      for (var hn in machData) {
        var info = machData[hn];
        if (typeof info === 'object' && info._note) {
          html += '<div class="card"><h4 style="margin:0 0 6px">' + hn + '</h4><div style="color:var(--text2);font-size:12px">' + info._note + '</div></div>';
          continue;
        }
        if (typeof info === 'object') {
          html += '<div class="card"><h4 style="margin:0 0 6px">' + hn + '</h4>';
          for (var k in info) {
            html += '<div style="font-size:12px;padding:2px 0"><span style="color:var(--text2)">' + k + ':</span> <strong>' + info[k] + '</strong></div>';
          }
          html += '</div>';
        }
      }
      html += '</div>';
    }

    // Detail lists
    if (Object.keys(detail).length > 0) {
      for (var hn in detail) {
        var info = detail[hn];
        if (typeof info === 'object') {
          // Table fields (arrays)
          for (var key in info) {
            var items = info[key];
            if (Array.isArray(items) && items.length > 0) {
              html += '<div class="card" style="margin-bottom:12px"><h4 style="margin:0 0 8px">' + hn + ' - ' + key + '</h4>';
              html += '<table style="width:100%;font-size:12px;border-collapse:collapse">';
              html += '<thead><tr style="background:var(--bg3)">';
              var sample = items[0];
              if (typeof sample === 'object') {
                var keys = Object.keys(sample).slice(0, 6);
                for (var ki = 0; ki < keys.length; ki++) {
                  html += '<th style="padding:6px 8px;text-align:left;font-weight:500">' + keys[ki] + '</th>';
                }
              }
              html += '</tr></thead><tbody>';
              var maxItems = Math.min(items.length, 50);
              for (var ii = 0; ii < maxItems; ii++) {
                var item = items[ii];
                html += '<tr style="border-top:1px solid var(--border)">';
                if (typeof item === 'object') {
                  var vals = Object.values(item).slice(0, 6);
                  for (var vi = 0; vi < vals.length; vi++) {
                    html += '<td style="padding:4px 8px">' + String(vals[vi] || '-').slice(0,40) + '</td>';
                  }
                }
                html += '</tr>';
              }
              if (items.length > 50) {
                html += '<tr><td colspan="6" style="padding:8px;text-align:center;color:var(--text2)">... 还有 ' + (items.length - 50) + ' 条</td></tr>';
              }
              html += '</tbody></table></div>';
            }
          }
          // Key-value fields
          var plainItems = [];
          for (var key in info) {
            var v = info[key];
            if (!Array.isArray(v) && typeof v !== 'object') {
              plainItems.push({k:key, v:v});
            }
          }
          if (plainItems.length > 0) {
            html += '<div class="card" style="margin-bottom:12px"><h4 style="margin:0 0 6px">' + hn + '</h4>';
            for (var pi = 0; pi < plainItems.length; pi++) {
              html += '<div style="font-size:12px;padding:2px 0"><span style="color:var(--text2)">' + plainItems[pi].k + ':</span> <strong>' + plainItems[pi].v + '</strong></div>';
            }
            html += '</div>';
          }
        }
      }
    }

    if (html.indexOf('card') === -1) {
      html += '<div style="padding:40px;text-align:center;color:var(--text2)">暂无数据</div>';
    }
    el.innerHTML = html;
  } catch(e) {
    el.innerHTML = '<div class="error">加载失败: ' + e.message + '</div>';
  }
}

// ════════════════════════════════════════════════════════
// C2 Remote Control
// ════════════════════════════════════════════════════════

function toggleC2Params() {
  const type = document.getElementById('c2Type')?.value;
  const el = document.getElementById('c2NurtureParams');
  if (el) el.style.display = type === 'nurture_run' ? 'block' : 'none';
}

async function loadC2Machines() {
  const targetEl = document.getElementById('c2Target');
  const statusEl = document.getElementById('c2MachineStatus');
  if (!statusEl) return;
  statusEl.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text2)">加载中...</div>';
  try {
    const r = await fetch('/api/c2/machines');
    const d = await r.json();
    if (targetEl) targetEl.innerHTML = '<option value="">选择机器...</option>' +
      d.machines.map(m => '<option value="'+m+'">'+m+(m==='chengzigedeAir'?' (本机)':'')+'</option>').join('');

    let html = '';
    for (const m of d.machines) {
      try {
        const sr = await fetch('/api/c2/environment/'+encodeURIComponent(m));
        const st = await sr.json();
        if (st.output) {
          const o = st.output;
          html += '<div style="padding:8px 0;border-bottom:1px solid var(--border);font-size:12px;display:flex;justify-content:space-between">' +
            '<strong>'+m+'</strong>' +
            '<span>'+(o.guardd_running ? '✅ guardd运行' : '❌ guardd停')+' · 💾'+ (o.disk_avail_gb||'?')+'G' +' · 📱'+(o.matrix_accounts||'?')+'账号</span></div>';
        } else {
          html += '<div style="padding:8px 0;border-bottom:1px solid var(--border);font-size:12px">'+m+' · '+ (st.status||'未知') +'</div>';
        }
      } catch(e) {
        html += '<div style="padding:8px 0;border-bottom:1px solid var(--border);font-size:12px;color:var(--amber)">'+m+' · ⏳ 查询超时</div>';
      }
    }
    statusEl.innerHTML = html || '<div style="text-align:center;padding:20px;color:var(--text2)">无机器数据</div>';
  } catch(e) {
    statusEl.innerHTML = '<div style="padding:20px;color:var(--red)">'+e.message+'</div>';
  }
}

// ════════════════════════════════════════════════════════
// Machine Status Bar — 全局三台机器状态条
// ════════════════════════════════════════════════════════

let _machineBarTimer = null;

async function loadMachineBar() {
  const bar = document.getElementById('machineBar');
  if (!bar) return;
  try {
    const rh = await fetch('/api/federation/health');
    const health = await rh.json();
    // 补充本机健康（federation/health 只含远程机器）
    try {
      const lr = await fetch('/api/health');
      const ld = await lr.json();
      health['chengzigedeAir'] = ld;
    } catch(e) {}
    
    const rm = await fetch('/api/machines');
    const md = await rm.json();
    const machineList = md.machines || [];

    const MACHINE_NAMES = {
      'chengzigedeAir': { label: '主控', icon: '🖥️' },
      '5kechengdeAir': { label: '养号', icon: '🖥️' },
      '7kecheng': { label: '养号', icon: '🖥️' },
    };

    let html = '<div style="display:flex;gap:8px;flex-wrap:wrap">';
    for (const [name, info] of Object.entries(MACHINE_NAMES)) {
      // 优先使用 /api/machines 的状态（比 federation/health 更可靠）
      const mData = machineList.find(function(m){return m.hostname===name || m.hostname===h.hostname;});
      const apiStatus = mData ? mData.status : 'offline';
      let statusClass = 'offline', statusText = '离线';
      if (apiStatus === 'online') {
        statusClass = 'online';
        statusText = '在线';
        if (mData && mData.current_task) {
          statusClass = 'busy';
          statusText = '忙碌';
        }
      }
      var dotColor = statusClass === 'online' ? 'var(--green)' : (statusClass === 'busy' ? 'var(--amber)' : 'var(--text2)');
      var opacity = statusClass === 'offline' ? '0.3' : '1';
      html += '<div style="display:flex;align-items:center;gap:5px;padding:5px 10px;border-radius:6px;background:var(--bg2);border:1px solid var(--border);font-size:12px;opacity:'+opacity+'">'+
        '<span style="width:8px;height:8px;border-radius:50%;background:'+dotColor+'"></span>'+
        '<span style="font-weight:600;color:var(--text)">'+name+'</span>'+
        '<span style="font-size:10px;color:var(--text2)">'+info.label+'</span>'+
        '<span style="font-size:10px;color:'+dotColor+'">'+statusText+'</span></div>';
    }
    html += '</div>';
    bar.innerHTML = html;
  } catch(e) {
    // silent — status bar is not critical
  }
}

function initMachineBar() {
  if (_machineBarTimer) clearInterval(_machineBarTimer);
  loadMachineBar();
  _machineBarTimer = setInterval(loadMachineBar, 30000);
}

// 在页面加载完成后初始化
if (document.readyState === 'complete') {
  initMachineBar();
} else {
  window.addEventListener('load', initMachineBar);
}

async function sendC2Command() {
  const target = document.getElementById('c2Target')?.value;
  const type = document.getElementById('c2Type')?.value;
  const schedule = document.getElementById('c2Schedule')?.value;
  const resultEl = document.getElementById('c2Result');
  if (!resultEl) return;
  if (!target || !type) { resultEl.innerHTML = '<div style="color:var(--red);font-size:13px;padding:8px">请选择目标和命令类型</div>'; return; }

  const params = {};
  if (type === 'nurture_run') {
    params.accounts = (document.getElementById('c2Accounts')?.value||'').split(',').map(s=>s.trim()).filter(Boolean);
    params.rounds = parseInt(document.getElementById('c2Rounds')?.value) || 10;
  }

  resultEl.innerHTML = '<div style="text-align:center;padding:10px;color:var(--text2)">发送中...</div>';
  try {
    const r = await fetch('/api/c2/send', {method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({target,type,params,schedule_at:schedule||null})});
    const res = await r.json();
    const ch = res._channel || 'git';
    resultEl.innerHTML = '<div style="padding:8px;background:rgba(34,197,94,.1);border-radius:6px;font-size:13px;color:var(--green)">' +
      (ch==='http'?'⚡':'📤')+' 命令已发送 通道:'+ch+' 状态:'+(res.status||'?')+'<br>'+
      (res.message||'')+(res.command_id?'<br>ID:'+res.command_id:'')+'</div>';
    loadC2History();
  } catch(e) {
    resultEl.innerHTML = '<div style="color:var(--red);font-size:13px;padding:8px">'+e.message+'</div>';
  }
}

async function loadC2History() {
  const el = document.getElementById('c2CommandHistory');
  if (!el) return;
  try {
    const r = await fetch('/api/c2/commands');
    const d = await r.json();
    const cmds = d.recent || [];
    if (!cmds.length) { el.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text2);font-size:13px">暂无执行历史</div>'; return; }
    el.innerHTML = '<table><thead><tr><th>类型</th><th>目标</th><th>状态</th><th>时间</th><th>结果</th></tr></thead><tbody>' +
      cmds.slice(0,20).map(c => {
        const st = c.status||'?';
        const cl = st==='completed' ? '#22c55e' : (st==='failed'?'#ef4444':'#f59e0b');
        const out = c.output ? (c.output.accounts?c.output.accounts.join(','):Object.keys(c.output).slice(0,3).join('|')) : (c.error||'-');
        const ts = (c.completed_at||c.created_at||'').slice(0,19).replace('T',' ');
        return '<tr><td style="font-weight:600">'+c.type+'</td><td>'+(c.target_machine||'-')+'</td>' +
          '<td><span style="color:'+cl+'">●</span> '+st+'</td><td style="font-size:11px;color:var(--text2)">'+ts+'</td>' +
          '<td style="font-size:11px;color:var(--text2);max-width:150px;overflow:hidden;text-overflow:ellipsis">'+String(out).slice(0,40)+'</td></tr>';
      }).join('') + '</tbody></table>';
  } catch(e) {
    el.innerHTML = '<div style="padding:20px;color:var(--red)">'+e.message+'</div>';
  }
}

function c2Nurture(accountId) {
  document.getElementById('c2Target').value = 'chengzigedeAir';
  document.getElementById('c2Type').value = 'nurture_run';
  document.getElementById('c2Accounts').value = accountId;
  document.getElementById('c2NurtureParams').style.display = 'block';
  switchView('matrix-c2');
}

// ════════════════════════════════════════════════════════
// Knowledge Base Management
// ════════════════════════════════════════════════════════

function kbRefresh() { kbLoadStats(); memLoadStats(); sysLoadDocs(); skillsLoad(); toolsLoad(); }

function kbSwitchTab(name, el) {
  document.querySelectorAll('.kb-tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');
  document.querySelectorAll('.kb-tab-body').forEach(b => b.style.display = 'none');
  const tab = document.getElementById(name.replace('kb-', 'kb-tab-'));
  if (tab) {
    tab.style.display = 'block';
    if (name === 'kb-knowledge') kbLoadStats();
    if (name === 'kb-memory') memLoadStats();
    if (name === 'kb-system') sysLoadDocs();
    if (name === 'kb-skills') { skillsLoad(); toolsLoad(); }
  }
}

// ── Tab 1: Knowledge Base ──
async function kbLoadStats() {
  const el = document.getElementById('kbStats');
  if (!el) return;
  try {
    const r = await fetch('/api/kb/stats');
    const d = await r.json();
    const cats = d.categories || {};
    let html = ''; let total = 0;
    const colors = ['#6366f1','#22c55e','#f59e0b','#3b82f6','#ef4444','#8b5cf6','#14b8a6','#f97316','#06b6d4','#84cc16','#a855f7'];
    for (const [key, info] of Object.entries(cats)) {
      total += info.count;
      html += `<div style="background:var(--bg3);border-radius:8px;padding:8px;border:1px solid var(--border);text-align:center">
        <div style="font-size:9px;color:var(--text2)">${info.label}</div>
        <div style="font-size:18px;font-weight:600;color:${colors[Object.keys(cats).indexOf(key)%colors.length]}">${info.count}</div>
        <div style="font-size:9px;color:var(--text2)">${key}</div></div>`;
    }
    html += `<div style="background:#6366f1;border-radius:8px;padding:8px;text-align:center">
      <div style="font-size:9px;color:rgba(255,255,255,.7)">总计</div>
      <div style="font-size:18px;font-weight:600;color:#fff">${total}</div>
      <div style="font-size:9px;color:rgba(255,255,255,.5)">篇</div></div>`;
    el.innerHTML = html;
    kbLoadLogs();
  } catch(e) { if (el) el.innerHTML = `<div style="color:var(--red)">${e.message}</div>`; }
}

function kbShowRefine() {
  document.getElementById('kbResultPanel').innerHTML =
    `<div style="font-weight:600;margin-bottom:8px">🧹 提纯收件箱</div>
    <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text2);cursor:pointer;margin-bottom:8px">
      <input type="checkbox" id="kbRefineAuto" checked> 自动分类</label>
    <div style="display:flex;gap:8px">
      <button onclick="kbDoRefine()" style="background:#6366f1;color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">▶ 执行</button>
      <span id="kbRefineResult" style="font-size:12px;display:flex;align-items:center"></span></div>`;
}
function kbShowCollect() { /* same as before */ document.getElementById('kbResultPanel').innerHTML =
  `<div style="font-weight:600;margin-bottom:8px">📥 汇聚到收件箱</div>
  <div style="margin-bottom:8px"><input id="kbCollectDirs" placeholder="20_methods,40_references" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:5px;font-size:12px"></div>
  <div style="display:flex;gap:8px">
    <button onclick="kbDoCollect()" style="background:#6366f1;color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">▶ 执行</button>
    <span id="kbCollectResult"></span></div>`;
}
function kbShowIngest() {
  document.getElementById('kbResultPanel').innerHTML =
    `<div style="font-weight:600;margin-bottom:8px">📝 导入知识</div>
    <textarea id="kbIngestSource" rows="2" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px;border-radius:5px;font-size:12px;resize:vertical" placeholder="URL 或文本"></textarea>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:6px 0">
      <select id="kbIngestCat" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px;border-radius:5px;font-size:12px">
        ${['00_inbox','10_concepts','20_methods','30_facts','40_references','50_resources'].map(c => `<option value="${c}">${c}</option>`).join('')}
      </select>
      <input id="kbIngestTags" placeholder="标签" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px;border-radius:5px;font-size:12px"></div>
    <div style="display:flex;gap:8px"><button onclick="kbDoIngest()" style="background:#6366f1;color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">▶ 导入</button><span id="kbIngestResult"></span></div>`;
}
function kbShowSearch() {
  document.getElementById('kbResultPanel').innerHTML =
    `<div style="font-weight:600;margin-bottom:8px">🔍 搜索</div>
    <input id="kbSearchQuery" placeholder="关键词..." style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px;border-radius:5px;font-size:12px" onkeydown="if(event.key==='Enter')kbDoSearch()">
    <button onclick="kbDoSearch()" style="background:#6366f1;color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px;margin-top:6px">搜索</button>
    <div id="kbSearchResult" style="margin-top:6px;max-height:250px;overflow-y:auto;font-size:12px"></div>`;
}
function kbShowBackup() {
  document.getElementById('kbResultPanel').innerHTML =
    `<div style="font-weight:600;margin-bottom:8px">💾 备份</div>
    <input id="kbBackupLabel" value="manual_${Date.now()}" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px;border-radius:5px;font-size:12px">
    <button onclick="kbDoBackup()" style="background:#6366f1;color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px;margin-top:6px">▶ 开始备份</button>
    <span id="kbBackupResult" style="font-size:12px;margin-left:8px"></span>`;
}

// Execute functions (same as before, simplified)
async function kbDoRefine() {
  const auto = document.getElementById('kbRefineAuto')?.checked;
  const el = document.getElementById('kbRefineResult'); if (el) el.innerHTML = '⏳';
  try {
    const r = await fetch('/api/kb/refine', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({auto_classify:auto||true})});
    const res = await r.json();
    if (el) el.innerHTML = res.status==='ok' ? '<span style="color:var(--green)">✅</span>' : '<span style="color:var(--red)">❌ '+res.error+'</span>';
    kbLoadLogs();
  } catch(e) { if (el) el.innerHTML = '<span style="color:var(--red)">'+e.message+'</span>'; }
}
async function kbDoCollect() {
  const dirs = document.getElementById('kbCollectDirs')?.value;
  const el = document.getElementById('kbCollectResult'); if (el) el.innerHTML = '⏳';
  try {
    const r = await fetch('/api/kb/collect', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source_dirs:dirs?dirs.split(',').map(s=>s.trim()).filter(Boolean):[]})});
    const res = await r.json();
    if (el) el.innerHTML = res.status==='ok' ? '✅' : '❌ '+res.error;
    kbLoadLogs();
  } catch(e) { if (el) el.innerHTML = '❌ '+e.message; }
}
async function kbDoIngest() {
  const s = document.getElementById('kbIngestSource')?.value; if (!s) return alert('请输入内容');
  const el = document.getElementById('kbIngestResult'); if (el) el.innerHTML = '⏳';
  try {
    const r = await fetch('/api/kb/ingest', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:s,category:document.getElementById('kbIngestCat')?.value||'00_inbox',tags:document.getElementById('kbIngestTags')?.value||''})});
    const res = await r.json();
    if (el) el.innerHTML = res.status==='ok' ? '✅ 已入库' : '❌ '+res.error;
    kbLoadStats(); kbLoadLogs();
  } catch(e) { if (el) el.innerHTML = '❌ '+e.message; }
}
async function kbDoSearch() {
  const q = document.getElementById('kbSearchQuery')?.value; if (!q) return;
  const el = document.getElementById('kbSearchResult'); if (el) el.innerHTML = '⏳';
  try {
    const r = await fetch('/api/kb/search', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:q,limit:20})});
    const res = await r.json();
    if (!el) return;
    if (!res.results||!res.results.length) { el.innerHTML = '<div style="color:var(--text2);padding:6px">无结果</div>'; return; }
    el.innerHTML = '<div style="color:var(--text2);margin-bottom:4px;font-size:11px">'+res.total+' 个结果</div>' +
      res.results.map(r2 => `<div style="padding:4px 0;border-bottom:1px solid var(--border);font-size:11px">
        <span style="color:#6366f1">${r2.category}</span>/<strong>${r2.file.split('/').pop()}</strong>
        <div style="color:var(--text2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:10px">${(r2.context||'').slice(0,80)}</div></div>`).join('');
  } catch(e) { if (el) el.innerHTML = '❌ '+e.message; }
}
async function kbDoBackup() {
  const el = document.getElementById('kbBackupResult'); if (el) el.innerHTML = '⏳';
  try {
    const r = await fetch('/api/kb/backup', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({label:document.getElementById('kbBackupLabel')?.value||'manual'})});
    const res = await r.json();
    if (el) el.innerHTML = res.status==='ok' ? '✅ '+res.files+'篇' : '❌ '+res.error;
    kbLoadLogs();
  } catch(e) { if (el) el.innerHTML = '❌ '+e.message; }
}
async function kbGitSync() {
  const panel = document.getElementById('kbResultPanel');
  panel.innerHTML = '<div style="color:var(--text2);font-size:12px">⏳ 同步中...</div>';
  try {
    const r = await fetch('/api/kb/git-sync', {method:'POST',headers:{'Content-Type':'application/json'}});
    const res = await r.json();
    panel.innerHTML = '<div style="font-weight:600;margin-bottom:6px;font-size:12px">🔄 完成</div><pre style="font-size:11px;color:var(--green);background:var(--bg3);padding:8px;border-radius:4px;overflow:auto">'+(res.outputs||['ok']).join('\\n').slice(0,500)+'</pre>';
    kbLoadLogs();
  } catch(e) { panel.innerHTML = '<div style="color:var(--red);font-size:12px">'+e.message+'</div>'; }
}
async function kbLoadLogs() {
  const el = document.getElementById('kbLogs'); if (!el) return;
  try {
    const r = await fetch('/api/kb/logs?limit=10');
    const d = await r.json(); const logs = d.logs||[];
    if (!logs.length) { el.innerHTML = '<div style="padding:10px;color:var(--text2);font-size:12px">暂无操作记录</div>'; return; }
    const names = {refine:'提纯',collect_to_inbox:'汇聚',ingest:'入库',search:'搜索',backup:'备份',git_sync:'Git同步'};
    el.innerHTML = '<div style="font-size:12px;font-weight:600;margin-bottom:6px">📜 最近操作</div>' +
      logs.reverse().slice(0,10).map(l => {
        const ts = (l.timestamp||'').slice(11,19);
        return `<div style="display:flex;gap:6px;padding:3px 0;border-bottom:1px solid var(--border);font-size:11px">
          <span>${l.status==='ok'?'✅':'❌'}</span>
          <span style="color:var(--text2);width:50px">${names[l.op]||l.op}</span>
          <span style="color:var(--text2);font-size:10px">${ts}</span>
          <span style="color:var(--text2);margin-left:auto;font-size:10px">${l.result?l.result.files||l.result.returncode||'' : l.status}</span>
        </div>`;
      }).join('');
  } catch(e) { if (el) el.innerHTML = '<div style="color:var(--red)">'+e.message+'</div>'; }
}

// ── Tab 2: Memory ──
async function memLoadStats() {
  const el = document.getElementById('memStats'); if (!el) return;
  try {
    const r = await fetch('/api/kb/memory/stats');
    const d = await r.json();
    el.innerHTML =
      `<div style="background:var(--bg3);border-radius:8px;padding:10px;text-align:center;border:1px solid var(--border)">
        <div style="font-size:10px;color:var(--text2)">L1 关键词</div><div style="font-size:22px;font-weight:600;color:#8b5cf6">${d.l1_keywords}</div></div>
      <div style="background:var(--bg3);border-radius:8px;padding:10px;text-align:center;border:1px solid var(--border)">
        <div style="font-size:10px;color:var(--text2)">L2 事实</div><div style="font-size:22px;font-weight:600;color:var(--blue)">${d.l2_facts}</div></div>
      <div style="background:var(--bg3);border-radius:8px;padding:10px;text-align:center;border:1px solid var(--border)">
        <div style="font-size:10px;color:var(--text2)">L3 原文</div><div style="font-size:22px;font-weight:600;color:var(--green)">${d.l3_files}</div></div>
      <div style="background:var(--bg3);border-radius:8px;padding:10px;text-align:center;border:1px solid var(--border)">
        <div style="font-size:10px;color:var(--text2)">向量</div><div style="font-size:22px;font-weight:600;color:var(--amber)">${d.vector_count}</div></div>`;
  } catch(e) { el.innerHTML = '<div style="color:var(--red)">'+e.message+'</div>'; }
}
async function memShowL1() {
  const el = document.getElementById('memDetailContent'); if (!el) return;
  el.innerHTML = '⏳';
  try {
    const r = await fetch('/api/kb/memory/l1');
    const d = await r.json(); const kws = d.keywords||[];
    if (!kws.length) { el.innerHTML = '<div style="color:var(--text2);font-size:12px">无关键词</div>'; return; }
    el.innerHTML = '<table style="width:100%;font-size:11px;border-collapse:collapse"><tr style="background:var(--bg3)"><th style="padding:4px 8px;text-align:left">关键词</th><th style="padding:4px 8px;text-align:left">频次</th></tr>' +
      kws.map(k => `<tr><td style="padding:4px 8px;border-bottom:1px solid var(--border)">${k.word||k}</td><td style="padding:4px 8px;border-bottom:1px solid var(--border)">${k.freq||'-'}</td></tr>`).join('') + '</table>';
  } catch(e) { el.innerHTML = '❌ '+e.message; }
}
async function memShowL2() {
  const el = document.getElementById('memDetailContent'); if (!el) return;
  el.innerHTML = '⏳';
  try {
    const r = await fetch('/api/kb/memory/l2?limit=50');
    const d = await r.json();
    if (!d.facts||!d.facts.length) { el.innerHTML = '<div style="color:var(--text2);font-size:12px">无事实</div>'; return; }
    el.innerHTML = '<div style="color:var(--text2);font-size:11px;margin-bottom:4px">共 '+d.total+' 条</div>' +
      d.facts.map(f => `<div style="padding:4px 0;border-bottom:1px solid var(--border);font-size:11px">
        <span style="color:#6366f1">#${f.rowid}</span>
        <span style="color:var(--text2);margin-left:4px">${(f.content||'').slice(0,120)}</span>
        ${f.category ? '<span style="color:var(--amber);margin-left:4px">['+f.category+']</span>' : ''}
      </div>`).join('');
  } catch(e) { el.innerHTML = '❌ '+e.message; }
}
async function memShowL3() {
  const el = document.getElementById('memDetailContent'); if (!el) return;
  el.innerHTML = '⏳';
  try {
    const r = await fetch('/api/kb/memory/l3');
    const d = await r.json(); const files = d.files||[];
    if (!files.length) { el.innerHTML = '<div style="color:var(--text2);font-size:12px">无原文文件</div>'; return; }
    el.innerHTML = files.map(f => `<div style="padding:4px 0;border-bottom:1px solid var(--border);font-size:11px;cursor:pointer" onclick="memShowL3File('${f.name}')">
      <span style="color:var(--green)">📄</span> <strong>${f.name}</strong>
      <span style="color:var(--text2);margin-left:8px">${f.size_kb}KB</span>
      <span style="color:var(--text2);font-size:10px">${(f.updated||'').slice(0,10)}</span>
    </div>`).join('');
  } catch(e) { el.innerHTML = '❌ '+e.message; }
}
async function memShowL3File(name) {
  const el = document.getElementById('memDetailContent'); if (!el) return;
  el.innerHTML = '⏳';
  try {
    const r = await fetch('/api/kb/memory/l3/'+encodeURIComponent(name));
    const d = await r.json();
    if (d.status !== 'ok') { el.innerHTML = '❌ '+d.error; return; }
    el.innerHTML = '<div style="font-weight:600;font-size:12px;margin-bottom:6px">📄 '+d.name+'</div>' +
      '<pre style="font-size:11px;color:var(--text);background:var(--bg3);padding:8px;border-radius:4px;overflow:auto;max-height:350px;white-space:pre-wrap">'+d.content.slice(0,2000)+'</pre>';
  } catch(e) { el.innerHTML = '❌ '+e.message; }
}

// ── Tab 3: System Docs ──
async function sysLoadDocs() {
  const el = document.getElementById('sysDocsList'); if (!el) return;
  try {
    const r = await fetch('/api/kb/system/docs');
    const d = await r.json(); const docs = d.docs||[];
    if (!docs.length) { el.innerHTML = '<div style="color:var(--text2)">无文档</div>'; return; }
    el.innerHTML = docs.map(doc => `<div style="padding:4px 0;border-bottom:1px solid var(--border);font-size:11px;cursor:pointer" onclick="sysShowDoc('${doc.name}')">
      <span style="color:#6366f1">📄</span> <strong>${doc.title||doc.name}</strong>
      <span style="color:var(--text2);margin-left:8px">${doc.size_kb}KB</span>
    </div>`).join('');
  } catch(e) { el.innerHTML = '❌ '+e.message; }
}
async function sysShowDoc(name) {
  const el = document.getElementById('sysDocPreview'); if (!el) return;
  el.textContent = '⏳ 加载中...';
  try {
    const r = await fetch('/api/kb/system/docs/'+encodeURIComponent(name));
    const d = await r.json();
    el.textContent = d.content || '❌ '+(d.error||'读取失败');
  } catch(e) { el.textContent = '❌ '+e.message; }
}

// ── Tab 4: Skills & Tools ──
async function skillsLoad() {
  const el = document.getElementById('skillsList'); if (!el) return;
  try {
    const r = await fetch('/api/kb/skills');
    const d = await r.json(); const skills = d.skills||[];
    if (!skills.length) { el.innerHTML = '<div style="color:var(--text2);font-size:12px">无自定义技能</div>'; return; }
    el.innerHTML = skills.map(s => `<div style="padding:4px 0;border-bottom:1px solid var(--border);font-size:11px">
      <strong style="color:#6366f1">${s.name}</strong>
      <div style="color:var(--text2);font-size:10px">${s.description||''}</div>
      ${s.triggers&&s.triggers.length ? '<div style="color:var(--amber);font-size:10px">触发: '+s.triggers.slice(0,3).join(', ')+'</div>' : ''}
    </div>`).join('');
  } catch(e) { el.innerHTML = '❌ '+e.message; }
}
async function toolsLoad() {
  const el = document.getElementById('toolsList'); if (!el) return;
  try {
    const r = await fetch('/api/kb/tools');
    const d = await r.json(); const tools = d.tools||[];
    if (!tools.length) { el.innerHTML = '<div style="color:var(--text2);font-size:12px">无工具目录</div>'; return; }
    el.innerHTML = tools.map(t => `<div style="padding:4px 0;border-bottom:1px solid var(--border);font-size:11px">
      <strong style="color:var(--green)">${t.name}</strong>
      <span style="color:var(--text2);margin-left:6px;font-size:10px">${t.items} 文件</span>
      <div style="color:var(--text2);font-size:10px">${t.path}</div>
    </div>`).join('');
  } catch(e) { el.innerHTML = '❌ '+e.message; }
}

// ── Tab 5: Automation ──
async function autoLoadTasks() {
  const listEl = document.getElementById('autoTaskList');
  const targetEl = document.getElementById('autoTarget');
  const historyEl = document.getElementById('autoHistory');
  if (!listEl) return;
  try {
    const r = await fetch('/api/kb/automations');
    const d = await r.json();
    const machines = d.machines || {};
    const history = d.history || [];
    let html = '';
    for (const [machine, tasks] of Object.entries(machines)) {
      const isLocal = machine === 'chengzigedeAir';
      html += '<div style="margin-bottom:8px"><div style="font-weight:600;font-size:12px;color:'+(isLocal?'#6366f1':'#8b8fa3')+';margin-bottom:4px">'+(isLocal?'💻':'📡')+' '+machine+'</div>';
      tasks.forEach(t => {
        if (t.source_type === 'workbuddy') {
          html += '<div style="display:flex;align-items:center;gap:6px;padding:4px 6px;background:var(--bg3);border-radius:4px;margin-bottom:3px;font-size:11px">'+
            '<span style="color:var(--green)">'+(t.status==='ACTIVE'?'▶':'⏸')+'</span>'+
            '<span style="flex:1">'+(t.name||t.prompt||'').slice(0,30)+'</span>'+
            '<span style="color:var(--text2);font-size:10px">'+(t.rrule||t.scheduleType||'')+'</span>'+
            (isLocal ? '<span onclick="autoDeleteTask(\''+t.id+'\')" style="cursor:pointer;color:var(--red);font-size:12px">✕</span>' : '')+
          '</div>';
        }
      });
      if (!tasks.length) html += '<div style="color:var(--text2);font-size:11px;padding:4px 0">无任务</div>';
      html += '</div>';
    }
    if (!Object.keys(machines).length) html = '<div style="color:var(--text2);font-size:12px">暂无自动化任务</div>';
    listEl.innerHTML = html;
    if (targetEl) {
      const all = ['chengzigedeAir','5kechengdeAir','7kecheng'].concat(Object.keys(machines));
      targetEl.innerHTML = '<option value="">选择目标...</option>'+all.filter((v,i,a)=>a.indexOf(v)===i).map(m=>'<option value="'+m+'">'+m+'</option>').join('');
    }
    if (historyEl) {
      if (!history.length) { historyEl.innerHTML = '<div style="color:var(--text2);font-size:12px">暂无执行历史</div>'; return; }
      historyEl.innerHTML = history.map(h => {
        const cl = h.status==='completed'?'#22c55e':(h.status==='failed'?'#ef4444':'#f59e0b');
        return '<div style="display:flex;gap:6px;padding:3px 0;border-bottom:1px solid var(--border);font-size:11px">'+
          '<span style="color:'+cl+'">●</span>'+
          '<span style="width:60px">'+(h.type||'-')+'</span>'+
          '<span style="color:var(--text2);width:80px">'+(h.target||'-')+'</span>'+
          '<span style="color:var(--text2);font-size:10px">'+(h.time||'-')+'</span>'+
          '<span style="color:var(--text2);font-size:10px;margin-left:auto">'+(h.output||'').slice(0,30)+'</span></div>';
      }).join('');
    }
  } catch(e) { if (listEl) listEl.innerHTML = '<span style="color:var(--red)">'+e.message+'</span>'; }
}
async function autoCreateTask() {
  const target = document.getElementById('autoTarget')?.value;
  const type = document.getElementById('autoType')?.value;
  const p = document.getElementById('autoParams')?.value;
  const sched = document.getElementById('autoSchedule')?.value;
  if (!target||!type) { alert('请选择目标和命令'); return; }
  try {
    const r = await fetch('/api/kb/automations', {method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({target,type,params:p,schedule_at:sched||null})});
    const res = await r.json();
    if (res.status==='ok') { alert('✅ 已创建'); autoLoadTasks(); }
    else alert('❌ '+res.error);
  } catch(e) { alert('❌ '+e.message); }
}
async function autoCreateLocal() {
  const p = prompt('任务描述:'); if (!p) return;
  const rr = prompt('定时规则(RFC 5545):\nFREQ=DAILY;BYHOUR=8\n留空=立即')||'';
  try {
    const r = await fetch('/api/kb/automations', {method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({target:'chengzigedeAir',prompt:p,rrule:rr})});
    const res = await r.json();
    if (res.status==='ok') alert('✅ 已创建 ID:'+res.id);
    else alert('❌ '+res.error);
    autoLoadTasks();
  } catch(e) { alert('❌ '+e.message); }
}
async function autoDeleteTask(id) { alert('删除需通过 WorkBuddy 管理'); }
const __origKbSwitch = kbSwitchTab;
kbSwitchTab = function(name, el) {
  __origKbSwitch(name, el);
  if (name === 'kb-automation') autoLoadTasks();
};

// Patch switchView for KB
const __origSwitchView = switchView;
switchView = function(view) {
  // Redirect kb-skills and kb-tools to 'kb' for sidebar backward compat
  if (view === 'kb-skills') {
    __origSwitchView('kb');
    kbSwitchTab('kb-skills', document.querySelector('.kb-tab[data-tab="kb-skills"]'));
    if (typeof skillsLoad === 'function') { skillsLoad(); toolsLoad(); }
    return;
  }
  __origSwitchView(view);
  if (view === 'kb') { kbLoadStats(); memLoadStats(); sysLoadDocs(); }
};

// ═══ 账号表格：排序 + 筛选 ═══
var _acctSortCol = 0, _acctSortAsc = true;
function sortAcctTable(colIdx) {
  if (_acctSortCol === colIdx) _acctSortAsc = !_acctSortAsc;
  else { _acctSortCol = colIdx; _acctSortAsc = true; }
  var tbody = document.getElementById('acctTableBody');
  if (!tbody) return;
  var rows = Array.from(tbody.querySelectorAll('tr'));
  var colSelectors = ['td:nth-child(1)','td:nth-child(2)','td:nth-child(3)','td:nth-child(4)','td:nth-child(5)','td:nth-child(6)'];
  var sel = colSelectors[colIdx] || colSelectors[0];
  rows.sort(function(a,b){
    var va = (a.querySelector(sel)||{}).textContent||'';
    var vb = (b.querySelector(sel)||{}).textContent||'';
    if (!isNaN(parseFloat(va)) && !isNaN(parseFloat(vb))) return parseFloat(va)-parseFloat(vb);
    return va.localeCompare(vb, 'zh');
  });
  if (!_acctSortAsc) rows.reverse();
  rows.forEach(function(r){tbody.appendChild(r);});
  // 更新表头箭头
  var headers = document.querySelectorAll('#acctTableBody');
  if (headers.length > 0) {
    var headerRow = (headers[0].previousElementSibling || {}).querySelectorAll ? headers[0].previousElementSibling.querySelectorAll('th') : [];
    headerRow.forEach(function(th,i){
      var arrow = th.querySelector('span');
      if (arrow) arrow.textContent = i===colIdx ? (_acctSortAsc ? '▲' : '▼') : '';
    });
  }
}
function filterAcctTable() {
  var q = (document.getElementById('acctSearchInput')||{}).value||'';
  var platform = (document.getElementById('acctPlatformFilter')||{}).value||'';
  var machine = (document.getElementById('acctMachineFilter')||{}).value||'';
  var status = (document.getElementById('acctStatusFilter')||{}).value||'';
  q = q.toLowerCase().trim();
  document.querySelectorAll('#acctTableBody tr').forEach(function(tr){
    var search = tr.getAttribute('data-search')||'';
    var p = tr.getAttribute('data-platform')||'';
    var m = tr.getAttribute('data-machine')||'';
    var l = tr.getAttribute('data-login')||'';
    var show = true;
    if (q && !search.includes(q)) show = false;
    if (platform && p !== platform) show = false;
    if (machine === 'local' && m !== 'local') show = false;
    if (machine === 'remote' && m !== 'remote') show = false;
    if (status === 'logged_in' && l !== 'yes') show = false;
    if (status === 'not_logged' && l !== 'no') show = false;
    tr.style.display = show ? '' : 'none';
  });
}


// ═══════════════════════════════════════════════
// ES Module 全局暴露（原本是 <script> 全局作用域）
// ═══════════════════════════════════════════════
window.toggleSidebar = toggleSidebar;
window.toggleGroup = toggleGroup;
window.collapseAllGroups = collapseAllGroups;
window.switchView = switchView;
window.loadStats = loadStats;
window.debounceSearch = debounceSearch;
window.showDetail = showDetail;
window.closeDetail = closeDetail;
window.debounceAssetSearch = debounceAssetSearch;
window.loadIdentity = loadIdentity;
window.loadPlugins = loadPlugins;
window.loadMatrixSummary = loadMatrixSummary;
window.loadMatrixRun = loadMatrixRun;
window.corpusToggleRandom = corpusToggleRandom;
window.batchPreview = batchPreview;
window.batchExecute = batchExecute;
window.loadIdentities = loadIdentities;
window.acctSwitchTab = acctSwitchTab;
window.deleteIdentity = deleteIdentity;
window.unbindAccount = unbindAccount;
window.sortAccounts = sortAccounts;
window.renderAccountsTable = renderAccountsTable;
window.bpRenderSteps = bpRenderSteps;
window.bpGetPlatform = bpGetPlatform;
window.bpUpdatePlatform = bpUpdatePlatform;
window.bpCanFollow = bpCanFollow;
window.bpRenderOps = bpRenderOps;
window.bpExecute = bpExecute;
window.bpDoExec = bpDoExec;
window.closeBpModal = closeBpModal;
window.loadMatrixAtomOps = loadMatrixAtomOps;
window.loadMatrixBackup = loadMatrixBackup;
window.loadMatrixExport = loadMatrixExport;
window.createBackup = createBackup;
window.restoreBackup = restoreBackup;
window.doExport = doExport;
window.doImport = doImport;
window._renderShell = _renderShell;
// 被 modules/account_selector.js 覆盖
// window.loadMatrixNurture = loadMatrixNurture;
// window.loadMatrixCollect = loadMatrixCollect;
window.toggleCollectGroup = toggleCollectGroup;
window.toggleCollectMachine = toggleCollectMachine;
window.collectSelected = collectSelected;
// 被 modules/account_selector.js 覆盖
// window.loadMatrixComment = loadMatrixComment;
// window.loadMatrixLike = loadMatrixLike;
// 被 modules/account_selector.js 覆盖
// window.loadOpsCommand = loadOpsCommand;
window.loadOpsHistory = loadOpsHistory;
// 被 modules/corpus.js 覆盖
// window._loadAccounts = _loadAccounts;
// window._renderAccountSelector = _renderAccountSelector;
window._asToggleMachine = _asToggleMachine;
window._asRefreshCount = _asRefreshCount;
window._getSelectedAccounts = _getSelectedAccounts;
window._filterAccountSelector = _filterAccountSelector;
window.opsRun = opsRun;
window.opsBatchExec = opsBatchExec;
window.loadCrawlHistory = loadCrawlHistory;
// 已迁移，由 views/fleet-reconcile.js 接管
// window.loadFleetReconcile = loadFleetReconcile;
window.fmtSmsTime = fmtSmsTime;
window.smsUpdateAndTest = smsUpdateAndTest;
window.toggleProxyPanel = toggleProxyPanel;
window.toggleHomepageInfo = toggleHomepageInfo;
window.loadHomepageInfoSms = loadHomepageInfoSms;
window.toggleCollectHistory = toggleCollectHistory;
window.proxyTest = proxyTest;
window.setProxy = setProxy;
window.testAccountProxy = testAccountProxy;
window.editNote = editNote;
window.saveNote = saveNote;
window.editDialog = editDialog;
window.corpusAdd = corpusAdd;
window.corpusBatchImport = corpusBatchImport;
window.copyTemplate = copyTemplate;
window.corpusShowDetail = corpusShowDetail;
window.corpusDetailAdd = corpusDetailAdd;
window.corpusDetailDelete = corpusDetailDelete;
window.gitSync = gitSync;
window.accountRegister = accountRegister;
window._getAccountById = _getAccountById;
window._getMachineStatus = _getMachineStatus;
window._routeOperation = _routeOperation;
window.accountLogin = accountLogin;
window.clearCookies = clearCookies;
window.loginAllPlatforms = loginAllPlatforms;
window.collectAllPlatforms = collectAllPlatforms;
window.deleteIdentityByPhone = deleteIdentityByPhone;
window.deleteAccount = deleteAccount;
window.collectProfile = collectProfile;
window.loadMatrixRecord = loadMatrixRecord;
window.refreshRecordingList = refreshRecordingList;
window.recordingStart = recordingStart;
window.recordingStop = recordingStop;
window.recordingAnalyze = recordingAnalyze;
window.recordingExport = recordingExport;
window.recordingDelete = recordingDelete;
window.switchCmdTab = switchCmdTab;
// 被 modules/collect.js 覆盖
// window.loadMatrixCommands = loadMatrixCommands;
// window.cmdRunCommentTask = cmdRunCommentTask;
window.createAutoTaskFromSchedule = createAutoTaskFromSchedule;
window.switchCollectMode = switchCollectMode;
window.renderCollectList = renderCollectList;
window.toggleCollectIdentity = toggleCollectIdentity;
window.toggleCollectPlatform = toggleCollectPlatform;
window.getSelectedAccounts = getSelectedAccounts;
window.cmdCollectSelected = cmdCollectSelected;
window.cmdCollectAll = cmdCollectAll;
window.showCollectReport = showCollectReport;
window.loadCmdNurture = loadCmdNurture;
window.loadNurtureAccounts = loadNurtureAccounts;
window.toggleNurtureGroup = toggleNurtureGroup;
window.ntToggleMachine = ntToggleMachine;
window.ntToggleIdentity = ntToggleIdentity;
window.filterNurtureList = filterNurtureList;
window.nurtureToggleAll = nurtureToggleAll;
window.updateNurtureCount = updateNurtureCount;
window.getSelectedAccounts = getSelectedAccounts;
window.nurturePreflight = nurturePreflight;
window.nurtureExec = nurtureExec;
window.nurtureExecAll = nurtureExecAll;
window.doNurtureExec = doNurtureExec;
window.refreshScheduleList = refreshScheduleList;
window.scheduleAdd = scheduleAdd;
window.scheduleToggle = scheduleToggle;
window.scheduleDelete = scheduleDelete;
window.switchSetTab = switchSetTab;
window.loadMatrixSettings = loadMatrixSettings;
window.loadTimeline = loadTimeline;
window.loadAlerts = loadAlerts;
window.wakeupMachine = wakeupMachine;
window.upgradeMachine = upgradeMachine;
window.wfNodeColor = wfNodeColor;
window.wfInit = wfInit;
window.wfInitCanvas = wfInitCanvas;
window.wfRenderPalette = wfRenderPalette;
window.wfRenderTemplateSelect = wfRenderTemplateSelect;
window.wfRender = wfRender;
window.wfDragStart = wfDragStart;
window.wfAddNode = wfAddNode;
window.wfSelectNode = wfSelectNode;
window.wfDeleteNode = wfDeleteNode;
window.wfNodeMouseDown = wfNodeMouseDown;
window.wfNodeMouseMove = wfNodeMouseMove;
window.wfNodeMouseUp = wfNodeMouseUp;
window.wfConnStart = wfConnStart;
window.wfConnEnd = wfConnEnd;
window.wfLoadTemplate = wfLoadTemplate;
window.wfClear = wfClear;
window.wfRun = wfRun;
window.wfLoadCharacters = wfLoadCharacters;
window.wfRenderConfig = wfRenderConfig;
window.wfUpdateConfig = wfUpdateConfig;
window.wfGeneratePortrait = wfGeneratePortrait;
window.loadCharGen = loadCharGen;
window.renderCharGenTabs = renderCharGenTabs;
window.charGenSwitchTab = charGenSwitchTab;
window.charGenFieldChange = charGenFieldChange;
window.buildLayerDesc = buildLayerDesc;
window.buildFullDescription = buildFullDescription;
window.charGenUpdatePreview = charGenUpdatePreview;
window.charGenAutoFill = charGenAutoFill;
window.charGenAutoFillFromDescription = charGenAutoFillFromDescription;
window.charGenRun = charGenRun;
window.loadCharacters = loadCharacters;
window.renderCharPortraitGallery = renderCharPortraitGallery;
window.switchCapGroup = switchCapGroup;
window.renderCapGroup = renderCapGroup;
window.loadPluginView = loadPluginView;
window.toggleC2Params = toggleC2Params;
window.loadC2Machines = loadC2Machines;
window.loadMachineBar = loadMachineBar;
window.initMachineBar = initMachineBar;
window.sendC2Command = sendC2Command;
window.loadC2History = loadC2History;
window.c2Nurture = c2Nurture;
window.kbRefresh = kbRefresh;
window.kbSwitchTab = kbSwitchTab;
window.kbLoadStats = kbLoadStats;
window.kbShowRefine = kbShowRefine;
window.kbShowCollect = kbShowCollect;
window.kbShowIngest = kbShowIngest;
window.kbShowSearch = kbShowSearch;
window.kbShowBackup = kbShowBackup;
window.kbDoRefine = kbDoRefine;
window.kbDoCollect = kbDoCollect;
window.kbDoIngest = kbDoIngest;
window.kbDoSearch = kbDoSearch;
window.kbDoBackup = kbDoBackup;
window.kbGitSync = kbGitSync;
window.kbLoadLogs = kbLoadLogs;
window.memLoadStats = memLoadStats;
window.memShowL1 = memShowL1;
window.memShowL2 = memShowL2;
window.memShowL3 = memShowL3;
window.memShowL3File = memShowL3File;
window.sysLoadDocs = sysLoadDocs;
window.sysShowDoc = sysShowDoc;
window.skillsLoad = skillsLoad;
window.toolsLoad = toolsLoad;
window.autoLoadTasks = autoLoadTasks;
window.autoCreateTask = autoCreateTask;
window.autoCreateLocal = autoCreateLocal;
window.autoDeleteTask = autoDeleteTask;
window.sortAcctTable = sortAcctTable;
window.filterAcctTable = filterAcctTable;


// ═══════════════════════════════════════════════
// 机器心跳检测 & 告警显示
// ═══════════════════════════════════════════════

async function refreshMachineHealth() {
  try {
    const r = await fetch('/api/machines');
    const d = await r.json();
    const machines = d.machines || [];
    const healthEl = document.getElementById('machineHealthBar');
    if (!healthEl) return;
    let html = '';
    let hasOffline = false;
    for (const m of machines) {
      const host = m.hostname || m.name || '?';
      const status = m.status || 'offline';
      const lastPush = m._last_push_sec || 0;
      let icon, color;
      if (status === 'online') { icon = '🟢'; color = 'var(--green)'; }
      else if (status === 'recent') { icon = '🟡'; color = 'var(--amber)'; }
      else { icon = '🔴'; color = 'var(--red)'; hasOffline = true; }
      let timeStr = '';
      if (lastPush > 3600) timeStr = ` (${Math.round(lastPush/3600)}h前)`;
      else if (lastPush > 60) timeStr = ` (${Math.round(lastPush/60)}m前)`;
      else if (lastPush > 0) timeStr = ` (${lastPush}s前)`;
      html += '<span style="color:'+color+';font-size:11px;margin-right:8px">'+icon+' '+host+timeStr+'</span>';
    }
    healthEl.innerHTML = html;
    const alertEl = document.getElementById('fleetAlert');
    if (alertEl) {
      if (hasOffline) {
        const offlineCount = machines.filter(function(m) { return m.status !== 'online' && m.status !== 'recent'; }).length;
        alertEl.innerHTML = '<span style="color:var(--red);font-size:10px;padding:2px 6px;border-radius:3px;background:rgba(220,38,38,.1)">⚠️ '+offlineCount+'台离线</span>';
        alertEl.style.display = '';
      } else { alertEl.style.display = 'none'; }
    }
  } catch(e) {}
}

// 加载历史执行记录
async function loadExecutionHistory() {
  try {
    const r = await fetch('/api/ops/status');
    const d = await r.json();
    const cmds = d.commands || (Array.isArray(d) ? d : []);
    const el = document.getElementById('execHistory');
    if (!el) return;
    if (!cmds.length) {
      el.innerHTML = '<div style="color:var(--text2);font-size:11px;padding:8px">暂无执行记录</div>';
      return;
    }
    var stats = { total: cmds.length, completed: 0, failed: 0, running: 0 };
    var byMachine = {};
    var terminal = ['completed','failed','timed_out','crashed','cancelled'];
    for (var i = 0; i < cmds.length; i++) {
      var c = cmds[i];
      var s = c.status || '?';
      if (s === 'completed') stats.completed++;
      else if (terminal.indexOf(s) >= 0) stats.failed++;
      else stats.running++;
      var mach = c.machine || '?';
      if (!byMachine[mach]) byMachine[mach] = { total:0, ok:0, fail:0 };
      byMachine[mach].total++;
      if (s === 'completed') byMachine[mach].ok++;
      else if (terminal.indexOf(s) >= 0) byMachine[mach].fail++;
    }
    var html = '<div style="display:flex;gap:12px;margin-bottom:6px;font-size:11px">';
    html += '<span>📊 总数: '+stats.total+'</span>';
    html += '<span style="color:var(--green)">✅ 成功: '+stats.completed+'</span>';
    html += '<span style="color:var(--red)">❌ 失败: '+stats.failed+'</span>';
    html += '<span style="color:var(--blue)">⏳ 运行中: '+stats.running+'</span>';
    html += '</div><div style="font-size:10px">';
    for (var mach in byMachine) {
      var s = byMachine[mach];
      var rate = s.total > 0 ? Math.round(s.ok / s.total * 100) : 0;
      html += '<div style="margin:2px 0">  '+mach+': '+s.ok+'/'+s.total+' ('+rate+'%) '+Array(Math.round(rate/10)+1).join('█')+Array(10-Math.round(rate/10)+1).join('░')+'</div>';
    }
    html += '</div>';
    html += '<div style="font-size:10px;margin-top:4px;border-top:1px solid var(--border);padding-top:4px"><div style="color:var(--text2);margin-bottom:2px">最近执行:</div>';
    for (var i = 0; i < Math.min(5, cmds.length); i++) {
      var c = cmds[i];
      var accts = c.accounts ? c.accounts.join(',') : (c.account || '?');
      var icon = c.status === 'completed' ? '✅' : c.status === 'running' ? '⏳' : c.status === 'dispatching' ? '📡' : '❌';
      html += '<div>'+icon+' '+c.machine+' '+accts+': '+(c.message || c.status)+' ('+c.elapsed_sec+'s)</div>';
    }
    html += '</div>';
    el.innerHTML = html;
  } catch(e) {
    var el = document.getElementById('execHistory');
    if (el) el.innerHTML = '<div style="color:var(--text2);font-size:11px">❌ 加载失败: '+e.message+'</div>';
  }
}

// 增加自动刷新
window.refreshMachineHealth = refreshMachineHealth;
window.loadExecutionHistory = loadExecutionHistory;

// ── 冲突解决：确保内部调用使用最终版本（来自后被导入的模块）──
// 这些函数在其他模块中有覆盖定义，这里将本地引用指向最终版本
_loadAccounts = typeof window._loadAccounts !== 'undefined' ? window._loadAccounts : _loadAccounts;
_renderAccountSelector = typeof window._renderAccountSelector !== 'undefined' ? window._renderAccountSelector : _renderAccountSelector;

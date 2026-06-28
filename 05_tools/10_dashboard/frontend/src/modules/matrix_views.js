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
// 自动刷新: 10秒轮询机器状态, 30秒轮询摘要
setInterval(() => { if (currentView === 'machines') loadMachines(); }, 10000);
setInterval(() => { if (currentView === 'summary') loadSummary(); }, 30000);

// ── Navigation ──
// 保存原生的 switchView（来自 inline.js），然后扩展
const _origSwitchView = window.switchView;
window.switchView = function(view) {
  // 先调原函数（处理viewIds显隐 + tryLoadView）
  if (typeof _origSwitchView === 'function') {
    _origSwitchView(view);
  }
  
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
  const matrixSubViews = ['matrix-nurture','matrix-collect','matrix-publish','matrix-blueprints','matrix-interact','matrix-comment','matrix-schedule','matrix-corpus','matrix-sms-proxy','matrix-like','ops-command','ops-recorder'];
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
     'crawl-tasks','crawl-sources',
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
  const viewIds = ['matrix-sms-proxy','matrix-nurture','matrix-collect','matrix-publish','matrix-blueprints','matrix-interact','matrix-comment','matrix-schedule','matrix-corpus','matrix-record',
                   'matrix-accounts','matrix-atom-ops','matrix-settings','matrix-run','matrix-commands','matrix-summary',
                   'matrix-c2','matrix-backup','matrix-export',
                   'ave-render','ave-script','ave-materials','ave-templates',
                   'crawl-tasks','crawl-sources',
                   'machines','fleet-sync','fleet-reconcile','fleet-exec',
                   'serve-mcp','serve-dashboard','serve-schedule',
                   'productions','assets','costs','capabilities','workflow','kb',
                   'ops-command','dynamic',
                   'timeline','alerts','summary','characters','char-gen'];
  viewIds.forEach(v => {
    document.getElementById('view-' + v)?.classList.toggle('hidden', v !== view);
  });

  // 插件视图（动态加载）
  document.querySelectorAll('[id^="plugin-view-"]').forEach(el => el.classList.add('hidden'));
  if (view.startsWith('plugin-') && !matrixSubViews.includes(view) && view !== 'matrix-summary') {
    const pv = document.getElementById('plugin-view-' + view.replace('plugin-',''));
    if (pv) pv.classList.remove('hidden');
  }

  // ── 已迁移视图（动态加载，先试路由再回退旧逻辑）──
  if (_tryMigratedView(view)) return;

  // 加载数据（回退：未迁移视图走旧 inline 函数）
  // ── 所有视图已迁移，无 inline.js fallback ──
}

// ── 迁移视图辅助函数（全部33个已迁移视图）──
function _tryMigratedView(view) {
  // 完整白名单 = views/ 目录下所有含 loadView 的文件
  // 白名单：只保留确认功能完整的视图
  // 交互操作类视图（accounts/nurture/collect）回退到 inline 旧代码
  var _migratedViews = [
    // ── 只读仪表盘 ──
    'matrix-summary','machines','productions','assets','costs',
    // ── 功能完整的操作视图 ──
    'accounts-center','matrix-interact','matrix-comment','matrix-collect','matrix-like','matrix-accounts','matrix-nurture','matrix-sms-proxy','matrix-blueprints','matrix-corpus','ops-command',
    // ── 录制标注 ──
    'ops-recorder',
    // ── 列表/管理视图 ──
    'matrix-atom-ops','matrix-schedule',
    // ── 联邦管理 ──
    'fleet-sync','fleet-reconcile','fleet-exec',
    // ── 服务状态 ──
    'serve-mcp','serve-dashboard','serve-schedule',
    // ── 视频工厂外壳 ──
    'ave-render','ave-script','ave-materials','ave-templates','workflow','capabilities',
    // ── 采集外壳 + 重定向 ──
    'crawl-tasks','crawl-sources',
    'matrix-publish','matrix-login',
    // ── 已迁移旧代码视图（共13个已完成迁移）──
    'matrix-record','matrix-c2','matrix-backup','matrix-export',
    'matrix-run','matrix-commands','matrix-settings',
    'characters','char-gen','alerts','timeline',
    'summary','crawl-history',
  ];
  if (_migratedViews.indexOf(view) === -1) return false;

  var container = document.getElementById('view-dynamic');
  if (!container) return false;

  // 隐藏所有旧视图（通杀所有 view- 和 plugin-view- 开头的元素）
  document.querySelectorAll('[id^="view-"]').forEach(function(el) { el.classList.add('hidden'); });
  document.querySelectorAll('[id^="plugin-view-"]').forEach(function(el) { el.classList.add('hidden'); });

  // 显示动态容器并开始加载
  container.classList.remove('hidden');
  container.innerHTML = '<div class="loading">⏳ 加载中...</div>';

  import(`../views/${view}.js`).then(function(m) {
    if (m && typeof m.loadView === 'function') {
      m.loadView(container);
    } else {
      container.innerHTML = '<div class="error">❌ 视图 ' + view + ' 没有 loadView 导出</div>';
    }
  }).catch(function(e) {
    container.innerHTML = '<div class="error">❌ 加载失败: ' + e.message + '</div>';
  });

  return true;
}

// ── 暴露全局（供 onclick 使用）──
window.toggleGroup = toggleGroup;
window.collapseAllGroups = collapseAllGroups;
window.switchView = switchView;
window.closeDetail = closeDetail;
window.showDetail = showDetail;

// ── 执行历史（细腻度增强版：显示完整状态机 10 种状态）──
var STATUS_MAP = {
  'queued':          { icon: '📋', color: '#6b7280', label: '已排队',      group: 'active' },
  'preflighting':    { icon: '🔍', color: '#f59e0b', label: '预检中',      group: 'active' },
  'preflight_failed':{ icon: '⚠️', color: '#ef4444', label: '预检失败',    group: 'fail' },
  'dispatching':     { icon: '📡', color: '#3b82f6', label: '分发中',      group: 'active' },
  'running':         { icon: '🟢', color: '#22c55e', label: '运行中',      group: 'active' },
  'completed':       { icon: '✅', color: '#22c55e', label: '已完成',      group: 'ok' },
  'failed':          { icon: '❌', color: '#ef4444', label: '执行失败',    group: 'fail' },
  'timed_out':       { icon: '⏰', color: '#f97316', label: '执行超时',    group: 'fail' },
  'crashed':         { icon: '💥', color: '#dc2626', label: '进程崩溃',    group: 'fail' },
  'cancelled':       { icon: '⏸️', color: '#9ca3af', label: '用户取消',    group: 'fail' },
};
var STATUS_GROUPS = ['ok','active','fail'];
var STATUS_GROUP_LABELS = { 'ok':'✅ 成功','active':'⏳ 活跃','fail':'❌ 终止' };
var STATUS_GROUP_COLORS = { 'ok':'var(--green)','active':'var(--blue)','fail':'var(--red)' };

function formatElapsed(sec) {
  if (sec == null || sec === 0) return '-';
  sec = Math.round(sec);
  if (sec < 60) return sec + 's';
  var m = Math.floor(sec / 60);
  var s = sec % 60;
  return m + 'm' + (s > 0 ? s + 's' : '');
}

async function loadTaskPanel() {
  const el = document.getElementById('execHistory');
  if (!el) return;

  try {
    // 获取 guardd 运行中任务 + 命令历史
    const [rr, sr] = await Promise.all([
      fetch('/api/ops/running').then(r => r.json()).catch(() => ({machines:[]})),
      fetch('/api/ops/status').then(r => r.json()).catch(() => ({commands:[]})),
    ]);
    const runningMachines = rr.machines || [];
    const cmds = sr.commands || (Array.isArray(sr) ? sr : []);

    let html = '<div style="font-size:10px">';

    // ── 运行中任务（从 guardd 获取）──
    const hasRunning = runningMachines.some(m => m.tasks && m.tasks.some(t => t.status === 'running'));
    if (hasRunning) {
      html += '<div style="font-weight:600;font-size:11px;margin-bottom:4px">🟢 运行中任务</div>';
      for (const m of runningMachines) {
        const running = (m.tasks || []).filter(t => t.status === 'running');
        if (!running.length) continue;
        for (const t of running) {
          const elapsed = t.start_time ? Math.round((Date.now() - new Date(t.start_time).getTime())/1000) + 's' : '?';
          html += `<div style="display:flex;align-items:center;gap:4px;padding:3px 6px;margin:2px 0;background:var(--bg3);border-radius:4px">`
            + `<span style="font-weight:500;min-width:80px">🖥 ${m.machine}</span>`
            + `<span style="color:var(--green);font-weight:600">🟢 运行中</span>`
            + `<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${t.cmd || ''}</span>`
            + `<span style="color:var(--text2)">${elapsed}</span>`
            + `<button onclick="window._stopRun('${t.run_id}')" style="background:rgba(220,38,38,.1);color:var(--red);border:1px solid rgba(220,38,38,.3);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">⏹ 停止</button>`
            + `</div>`;
        }
      }
      html += '<div style="margin:6px 0"></div>';
    }

    // ── 状态统计（从命令历史）──
    if (cmds.length) {
      var byStatus = {}, byMachine = {};
      for (var i = 0; i < cmds.length; i++) {
        var c = cmds[i], s = c.status || 'unknown';
        var sm = STATUS_MAP[s] || { icon: '❓', label: s, group: 'fail' };
        byStatus[s] = (byStatus[s] || 0) + 1;
        var mach = c.machine || '?';
        if (!byMachine[mach]) byMachine[mach] = { total:0, ok:0, active:0, fail:0 };
        byMachine[mach].total++;
        byMachine[mach][sm.group]++;
      }

      html += '<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px">';
      for (var s in STATUS_MAP) {
        var sm = STATUS_MAP[s];
        var count = byStatus[s] || 0;
        if (count === 0) continue;
        html += '<span style="display:inline-flex;align-items:center;gap:3px;background:var(--bg3);padding:2px 8px;border-radius:4px;font-size:10px">'
          + sm.icon + ' <span style="font-weight:600;color:' + sm.color + '">' + count + '</span> ' + sm.label + '</span>';
      }
      html += '</div>';

      // 总数
      var okCount = 0, activeCount = 0, failCount = 0;
      for (var s in byStatus) {
        var g = (STATUS_MAP[s] || STATUS_MAP['cancelled']).group;
        if (g === 'ok') okCount += byStatus[s];
        else if (g === 'active') activeCount += byStatus[s];
        else failCount += byStatus[s];
      }
      html += '<div style="display:flex;gap:12px;margin-bottom:6px;font-size:11px">'
        + '<span>📊 <strong>' + cmds.length + '</strong></span>'
        + '<span style="color:var(--green)">✅ ' + okCount + '</span>'
        + '<span style="color:var(--red)">❌ ' + failCount + '</span>'
        + '<span style="color:var(--blue)">⏳ ' + activeCount + '</span>'
        + '</div>';

      // 每台机器
      for (var mach in byMachine) {
        var s = byMachine[mach];
        var rate = s.total > 0 ? Math.round(s.ok / s.total * 100) : 0;
        var barLen = Math.round(rate / 10);
        var bar = '█'.repeat(Math.max(0, barLen)) + '░'.repeat(Math.max(0, 10 - barLen));
        var dtl = [];
        if (s.active > 0) dtl.push('<span style="color:var(--blue)">▶' + s.active + '</span>');
        if (s.fail > 0) dtl.push('<span style="color:var(--red)">✕' + s.fail + '</span>');
        html += '<div style="margin:2px 0;display:flex;align-items:center;gap:6px;font-size:10px">'
          + '<span style="min-width:100px;font-weight:500">🖥 ' + mach + '</span>'
          + '<span style="color:var(--text2)">' + s.ok + '/' + s.total + ' (' + rate + '%)</span>'
          + '<span style="font-size:9px">' + bar + '</span>'
          + (dtl.length ? '<span style="font-size:10px"> (' + dtl.join(' ') + ')</span>' : '')
          + '</div>';
      }

      // 最近执行
      html += '<div style="margin-top:4px;border-top:1px solid var(--border);padding-top:4px">'
        + '<div style="color:var(--text2);font-size:10px;margin-bottom:2px;font-weight:500">最近执行:</div>';
      var showCount = Math.min(6, cmds.length);
      for (var i = 0; i < showCount; i++) {
        var c = cmds[i], s = c.status || 'unknown';
        var sm = STATUS_MAP[s] || { icon: '❓', color: '#999', label: s };
        var accts = c.accounts ? c.accounts.join(',') : (c.account || '?');
        var elapsed = formatElapsed(c.elapsed_sec);
        var msg = (c.message || sm.label).slice(0, 40);
        var timeStr = c.created_at ? c.created_at.slice(11, 19) : '';
        html += '<div style="display:flex;align-items:center;gap:3px;padding:1px 0;font-size:10px">'
          + '<span style="flex-shrink:0">' + sm.icon + '</span>'
          + '<span style="color:' + sm.color + ';font-weight:500;min-width:26px;font-size:9px">' + sm.label + '</span>'
          + '<span style="color:var(--text2);min-width:75px">' + (c.machine || '?') + '</span>'
          + '<span style="font-weight:500;min-width:50px">' + accts + '</span>'
          + '<span style="color:var(--text2);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + msg + '</span>'
          + '<span style="color:var(--text2);min-width:30px;text-align:right">' + elapsed + '</span>'
          + (timeStr ? '<span style="color:var(--text2);font-size:9px;min-width:45px;text-align:right">' + timeStr + '</span>' : '')
          + '</div>';
      }
      html += '</div>';
    } else {
      html += '<div style="color:var(--text2);padding:6px 0;font-size:11px">暂无执行记录</div>';
    }

    html += '</div>';
    el.innerHTML = html;
  } catch(e) {
    el.innerHTML = '<div style="color:var(--text2);font-size:11px">❌ 加载失败: ' + e.message + '</div>';
  }
}

window.loadExecutionHistory = loadTaskPanel;
window._stopRun = async function(runId) {
  if (!confirm('确定停止任务 ' + runId + '？')) return;
  try {
    const r = await fetch('/api/ops/cancel/' + runId, {method:'POST'});
    const d = await r.json();
    loadTaskPanel();
  } catch(e) { alert('❌ ' + e.message); }
};

// 自动刷新 + 初始化
setTimeout(function() { window.loadExecutionHistory(); }, 500);
setInterval(function() {
  try { if (typeof window.loadStats === 'function') window.loadStats(); } catch(e) {}
  try { if (typeof window.loadMachineBar === 'function') window.loadMachineBar(); } catch(e) {}
  try { window.loadExecutionHistory(); } catch(e) {}
}, 30000);

console.log('✅ Dashboard boot complete');

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
        {view:'accounts-center', label:'👤 账号中心'},
        // {view:'matrix-sms-proxy', label:'🪪 短信与代理'}, // 已合并到账号中心展开栏
        // {view:'matrix-collect', label:'📡 信息采集'},      // 已合并到账号中心批量操作
        {view:'matrix-nurture', label:'🏃 养号执行'},
        {view:'matrix-publish', label:'📤 内容发布'},
        {view:'matrix-interact', label:'💬 评论互动'},
        {view:'matrix-blueprints', label:'📋 蓝图管理'},
        // {view:'matrix-login', label:'🔑 登录管理'}, // 已合并到信息采集
        {view:'matrix-schedule', label:'⏱ 定时任务'},
        {view:'ops-recorder', label:'🎬 录制标注'},
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
      ]},
      '联邦': { icon: '🖥️', items: [
        {view:'machines', label:'机器状态'},
        {view:'fleet-sync', label:'一键同步'},
        {view:'fleet-reconcile', label:'对账检查'},
        {view:'fleet-exec', label:'远程Shell'},
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

// ═══════════════════════════════════════════════════════════════
// 对账检查视图（内联 — 防 tree-shake）
// ═══════════════════════════════════════════════════════════════

async function loadFleetReconcileView(container) {
  const uid = 'fr_' + Math.random().toString(36).slice(2, 6);
  let _rawData = null;

  container.innerHTML = `
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">🔍 对账检查</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">检查本机是否符合 ORACLE.yaml 宪法定义</p>
      <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
        <button onclick="window._doFleetReconcile('${uid}')" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">🔍 执行对账</button>
        <button id="exportBtn_${uid}" onclick="window._exportReconcile('${uid}')" style="display:none;background:var(--bg2);color:var(--text);border:1px solid var(--border);padding:8px 16px;border-radius:6px;cursor:pointer;font-size:12px">📋 导出报告</button>
      </div>
      <div id="stats_${uid}" style="display:none;margin-bottom:12px">
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:8px">
          <div style="background:var(--bg3);border-radius:8px;padding:10px 14px;text-align:center">
            <div style="font-size:11px;color:var(--text2)">总项</div>
            <div id="statTotal_${uid}" style="font-size:22px;font-weight:500;margin-top:4px">0</div>
          </div>
          <div id="statPassCard_${uid}" style="background:#EAF3DE;border-radius:8px;padding:10px 14px;text-align:center">
            <div style="font-size:11px;color:#27500A">通过</div>
            <div id="statPass_${uid}" style="font-size:22px;font-weight:500;color:#3B6D11;margin-top:4px">0</div>
          </div>
          <div id="statWarnCard_${uid}" style="background:#FAEEDA;border-radius:8px;padding:10px 14px;text-align:center">
            <div style="font-size:11px;color:#633806">警告</div>
            <div id="statWarn_${uid}" style="font-size:22px;font-weight:500;color:#854F0B;margin-top:4px">0</div>
          </div>
          <div id="statFailCard_${uid}" style="background:#FCEBEB;border-radius:8px;padding:10px 14px;text-align:center">
            <div style="font-size:11px;color:#791F1F">失败</div>
            <div id="statFail_${uid}" style="font-size:22px;font-weight:500;color:#A32D2D;margin-top:4px">0</div>
          </div>
          <div style="background:var(--bg3);border-radius:8px;padding:10px 14px;text-align:center">
            <div style="font-size:11px;color:var(--text2)">通过率</div>
            <div id="statRate_${uid}" style="font-size:22px;font-weight:500;margin-top:4px">0%</div>
          </div>
        </div>
      </div>
      <div id="filter_${uid}" style="display:none;margin-bottom:10px">
        <div style="display:flex;gap:6px;flex-wrap:wrap;font-size:12px">
          ${['全部','环境','目录','文件','Git','服务','任务'].map((label, i) =>
            '<div id="filterTab_'+uid+'_'+i+'" class="reconcile-filter-tab" style="height:28px;padding:0 14px;border-radius:6px;display:inline-flex;align-items:center;cursor:pointer;background:'+(i===0?'var(--primary)':'var(--bg3)')+';color:'+(i===0?'#fff':'var(--text)')+'" onclick="window._filterReconcile(\''+uid+'\','+i+')">'+label+'</div>'
          ).join('')}
        </div>
      </div>
      <div id="detail_${uid}" style="display:none">
        <div style="font-size:11px;color:var(--text2);margin-bottom:6px">明细</div>
        <div id="detailList_${uid}" style="display:flex;flex-direction:column;gap:4px"></div>
      </div>
      <div id="log_${uid}" style="margin-top:12px;background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:300px;overflow:auto;display:none"></div>
    </div>`;

  window._doFleetReconcile = window._doFleetReconcile || (async function(uid) {
    const logEl = document.getElementById('log_' + uid);
    if (!logEl) return;
    logEl.style.display = '';
    logEl.textContent = '⏳ 执行对账...\n';
    try {
      const r = await fetch('/api/fleet/reconcile', { method: 'POST' });
      const d = await r.json();
      const output = d.output || JSON.stringify(d, null, 2);
      logEl.textContent = output;
      _rawData = parseReconcileOutput(output);
      renderReconcileStats(uid, _rawData);
    } catch(e) { logEl.textContent = '❌ ' + e.message; }
  });

  function parseReconcileOutput(text) {
    const items = []; let currentSection = '';
    for (const line of text.split('\n')) {
      const t = line.replace(/\\u001b\\[[\\d;]+m/g, '').trim();
      if (!t) continue;
      if (/^[═━]{3,}\\s*\\d+\\.\\s/.test(t)) { currentSection = t.replace(/[═━\\s]+/g, ' ').trim(); continue; }
      let status = null, content = t;
      if (/^✅/.test(t)) { status = 'pass'; content = t.replace(/^✅\\s*/, ''); }
      else if (/^⚠️/.test(t)) { status = 'warn'; content = t.replace(/^⚠️\\s*/, ''); }
      else if (/^❌/.test(t)) { status = 'fail'; content = t.replace(/^❌\\s*/, ''); }
      if (status && content) {
        const ci = content.indexOf(':'); const label = ci>0?content.slice(0,ci).trim():content; const detail = ci>0?content.slice(ci+1).trim():'';
        items.push({status,label,detail,section:currentSection});
      }
    }
    return items;
  }

  function renderReconcileStats(uid, items) {
    const total = items.length; const pass = items.filter(i=>i.status==='pass').length;
    const warn = items.filter(i=>i.status==='warn').length; const fail = items.filter(i=>i.status==='fail').length;
    const rate = total>0?Math.round(pass/total*100):0;
    document.getElementById('statTotal_'+uid).textContent = total;
    document.getElementById('statPass_'+uid).textContent = pass;
    document.getElementById('statWarn_'+uid).textContent = warn;
    document.getElementById('statFail_'+uid).textContent = fail;
    document.getElementById('statRate_'+uid).textContent = rate+'%';
    document.getElementById('stats_'+uid).style.display = '';
    document.getElementById('filter_'+uid).style.display = '';
    document.getElementById('detail_'+uid).style.display = '';
    const eb = document.getElementById('exportBtn_'+uid); if (eb) eb.style.display = '';
    _rawData = items; window._filterReconcile(uid, 0);
  }

  window._filterReconcile = window._filterReconcile || function(uid, tabIdx) {
    const tabs = document.querySelectorAll('#filter_'+uid+' [id^="filterTab_"]');
    tabs.forEach((t,i)=>{ t.style.background=i===tabIdx?'var(--primary)':'var(--bg3)'; t.style.color=i===tabIdx?'#fff':'var(--text)'; });
    const filter = ['全部','环境','目录','文件','Git','服务','任务'][tabIdx];
    let filtered = _rawData||[];
    if (filter!=='全部') filtered = filtered.filter(i=>i.section.includes(filter));
    renderDetailList(uid, filtered);
  };

  function renderDetailList(uid, items) {
    const list = document.getElementById('detailList_'+uid); if (!list) return;
    if (!items.length) { list.innerHTML = '<div style="font-size:12px;color:var(--text2);padding:8px">无匹配项</div>'; return; }
    let html = '';
    for (const item of items) {
      const icon = item.status==='pass'?'✅':item.status==='warn'?'⚠️':'❌';
      const color = item.status==='pass'?'var(--green)':item.status==='warn'?'var(--amber)':'var(--red)';
      html += '<div style="display:flex;gap:8px;align-items:flex-start;padding:6px 8px;background:var(--bg3);border-radius:6px;font-size:12px;line-height:1.5">';
      html += '<span style="color:'+color+';flex-shrink:0">'+icon+'</span>';
      html += '<span style="color:var(--text2);flex-shrink:0;min-width:80px">'+escapeHtml2(item.label)+'</span>';
      if (item.detail) html += '<span>'+escapeHtml2(item.detail)+'</span>';
      html += '</div>';
    }
    list.innerHTML = html;
  }

  window._exportReconcile = window._exportReconcile || function(uid) {
    if (!_rawData||!_rawData.length) return;
    const pass = _rawData.filter(i=>i.status==='pass').length, warn = _rawData.filter(i=>i.status==='warn').length, fail = _rawData.filter(i=>i.status==='fail').length;
    const total = _rawData.length, rate = total>0?Math.round(pass/total*100):0, now = new Date().toLocaleString();
    let md = '# AgentOS 联邦对账报告\\n\\n**生成时间**: '+now+'\\n\\n';
    md += '| 指标 | 数值 |\\n|:-----|:-----|\\n| 总项 | '+total+' |\\n| 通过 | '+pass+' |\\n| 警告 | '+warn+' |\\n| 失败 | '+fail+' |\\n| 通过率 | '+rate+'% |\\n\\n';
    md += '| 状态 | 检查项 | 详情 |\\n|:-----|:-------|:------|\\n';
    for (const item of _rawData) md += '| '+(item.status==='pass'?'✅':item.status==='warn'?'⚠️':'❌')+' | '+item.label+' | '+item.detail+' |\\n';
    navigator.clipboard.writeText(md).then(function(){
      var b = document.getElementById('exportBtn_'+uid); if(b){ var o=b.textContent; b.textContent='✅ 已复制'; setTimeout(function(){b.textContent=o;},2000); }
    }).catch(function(){
      var ta = document.createElement('textarea'); ta.value=md; ta.style.cssText='position:fixed;left:-9999px';
      document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
    });
  };

  function escapeHtml2(str) { return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
}
window.loadFleetReconcileView = loadFleetReconcileView;
// ── 导出（防 Rollup tree-shake）──
window.loadIdentity = loadIdentity;
window.loadMatrixSummary = loadMatrixSummary;
window.loadPlugins = loadPlugins;
window.loadStats = loadStats;
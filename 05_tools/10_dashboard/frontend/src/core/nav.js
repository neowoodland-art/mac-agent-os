/**
 * core/nav.js — 导航框架
 * 
 * 职责：
 * - 侧边栏折叠/展开
 * - 视图切换 (switchView)
 * - 导航分组渲染
 * 
 * 依赖：无
 * 导出: window.toggleSidebar, window.switchView 等
 */

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

// ── Navigation ──
function switchView(view) {
  if (view === 'plugin-matrix') { view = 'matrix-summary'; }
  currentView = view;

  document.querySelectorAll('.nav-item, .nav-sub').forEach(e => {
    e.classList.toggle('active', e.dataset.view === view);
  });

  const aveSubViews = ['ave-render', 'ave-script', 'ave-materials', 'ave-templates'];
  const isAve = view === 'plugin-ave' || aveSubViews.includes(view);
  document.querySelectorAll('.nav-sub[data-group="ave"]').forEach(e => {
    e.style.display = isAve ? 'block' : 'none';
  });

  const matrixSubViews = ['matrix-nurture','matrix-collect','matrix-publish','matrix-blueprints',
    'matrix-comment','matrix-schedule','matrix-corpus','matrix-sms-proxy',
    'matrix-like','matrix-login','ops-command','matrix-record'];
  const isMatrix = view === 'plugin-matrix' || matrixSubViews.includes(view);
  document.querySelectorAll('.nav-sub[data-group="matrix"]').forEach(e => {
    e.style.display = isMatrix ? 'block' : 'none';
  });

  if (view === 'plugin-ave') {
    document.querySelector('.nav-item[data-view="plugin-ave"]')?.classList.add('active');
    document.querySelector('.nav-sub[data-view="workflow"]')?.classList.add('active');
    switchView('workflow');
    return;
  }
  if (view === 'plugin-matrix') {
    document.querySelector('.nav-item[data-view="plugin-matrix"]')?.classList.add('active');
    switchView('matrix-summary');
    return;
  }

  const kbViewToTab = {'kb-knowledge':'kb-knowledge','kb-memory':'kb-memory','kb-system':'kb-system','kb-skills-int':'kb-skills'};
  if (kbViewToTab[view]) {
    const tabName = kbViewToTab[view];
    document.querySelectorAll('.nav-item').forEach(e => {
      e.classList.toggle('active', e.dataset.view === view);
    });
    ['matrix-sms-proxy','matrix-nurture','matrix-collect','matrix-publish',
     'matrix-blueprints','matrix-comment','matrix-schedule','matrix-corpus',
     'matrix-record',
     'ave-render','ave-script','ave-materials','ave-templates',
     'crawl-tasks','crawl-sources','crawl-history',
     'machines','fleet-sync','fleet-reconcile','fleet-exec',
     'serve-mcp','serve-dashboard','serve-schedule',
     'productions','assets','costs','capabilities','workflow','kb'].forEach(v => {
      document.getElementById('view-' + v)?.classList.add('hidden');
    });
    document.querySelectorAll('[id^="plugin-view-"]').forEach(el => el.classList.add('hidden'));
    document.getElementById('view-kb')?.classList.remove('hidden');
    currentView = 'kb';
    const tab = document.querySelector('.kb-tab[data-tab="'+tabName+'"]');
    if (tab) kbSwitchTab(tabName, tab);
    return;
  }

  if (aveSubViews.includes(view)) {
    document.querySelector('.nav-item[data-view="plugin-ave"]')?.classList.add('active');
  }
  if (matrixSubViews.includes(view)) {
    document.querySelector('.nav-item[data-view="plugin-matrix"]')?.classList.add('active');
  }

  const viewIds = ['matrix-sms-proxy','matrix-nurture','matrix-collect','matrix-publish',
    'matrix-blueprints','matrix-comment','matrix-schedule','matrix-corpus','matrix-record',
    'ave-render','ave-script','ave-materials','ave-templates',
    'crawl-tasks','crawl-sources','crawl-history',
    'machines','fleet-sync','fleet-reconcile','fleet-exec',
    'serve-mcp','serve-dashboard','serve-schedule',
    'productions','assets','costs','capabilities','workflow','kb'];
  viewIds.forEach(v => {
    document.getElementById('view-' + v)?.classList.toggle('hidden', v !== view);
  });

  document.querySelectorAll('[id^="plugin-view-"]').forEach(el => el.classList.add('hidden'));
  if (view.startsWith('plugin-') && !matrixSubViews.includes(view) && view !== 'matrix-summary') {
    const pv = document.getElementById('plugin-view-' + view.replace('plugin-',''));
    if (pv) pv.classList.remove('hidden');
  }

  // 触发视图加载（来自 inline.js 或 views/ 模块）
  try { if (view === 'productions') loadProductions(); } catch(e) {}
  try { if (view === 'assets') loadAssets(); } catch(e) {}
  try { if (view === 'costs') loadCosts(); } catch(e) {}
  try { if (view === 'capabilities') loadCapabilities(); } catch(e) {}
  try { if (view === 'workflow') loadWorkflow(); } catch(e) {}
  try { if (view === 'machines') loadMachines(); } catch(e) {}
  try { if (view === 'matrix-sms-proxy') window.loadSmsProxy(); } catch(e) {}
  try { if (view === 'matrix-nurture') window.loadMatrixNurture(); } catch(e) {}
  try { if (view === 'matrix-recrd') window.loadMatrixRecord(); } catch(e) {}
  // ... 其余视图由 modules/ 和 inline.js 注册的 window.onXxx 处理
}

// ── 导出到 window（供 index.html onclick 使用）──
window.toggleSidebar = toggleSidebar;
window.toggleGroup = toggleGroup;
window.collapseAllGroups = collapseAllGroups;
window.switchView = switchView;

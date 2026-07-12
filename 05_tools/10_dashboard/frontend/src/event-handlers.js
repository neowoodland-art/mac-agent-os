/**
 * event-handlers.js — 事件处理函数（从 inline.js 提取）
 *
 * 所有 window.* 函数在此定义并注册到 window，
 * 因为 HTML onclick 属性直接引用它们。
 * 需在 inline.js 之后加载。
 */

// ── switchView ──
window.switchView = function(view) {
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
  const matrixSubViews = ['matrix-nurture','matrix-collect','matrix-publish','matrix-blueprints','matrix-interact','matrix-comment','comment-workbench','matrix-schedule','matrix-corpus','matrix-sms-proxy','matrix-like','matrix-login','ops-command'];
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
    ['comment-workbench','matrix-sms-proxy','matrix-nurture','matrix-collect','matrix-publish','matrix-blueprints','matrix-interact','matrix-comment','matrix-schedule','matrix-corpus',
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
  const viewIds = ['comment-workbench','matrix-sms-proxy','matrix-nurture','matrix-collect','matrix-publish','matrix-blueprints','matrix-interact','matrix-comment','matrix-schedule','matrix-corpus',
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

  // 已迁移视图 → 动态加载（由 views/*.js 的 loadView 接管）
  // 抓取管理旧路由 → 新抓取视图（scrape）
  if (view === 'crawl-tasks' || view === 'crawl-sources' || view === 'crawl-history') {
    view = 'scrape';
  }
  // window.tryLoadView 由 router.js 和本文件共同暴露
  if (window.tryLoadView && window.tryLoadView(view)) {
    return;
  }

  // URL hash 同步：支持浏览器刷新后回到当前页
  window.location.hash = view;
}

// ── Hash change handler ──
window.addEventListener('hashchange', function() {
  var hash = window.location.hash.replace('#', '');
  if (hash && hash !== currentView) {
    window.switchView(hash);
  }
});

// ── Blueprint helpers ──
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

// ── Collect helpers ──
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

window.collectAll = async function() {
  const selected = _getSelectedAccounts();
  if (!selected.length) { alert('没有可采集的账号'); return; }
  if (!confirm('采集全部 ' + selected.length + ' 个账号？')) return;
  await collectExec();
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

// ── Comment / Like helpers ──
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

// ── Fleet helpers ──
window.doFleetSync = async function() {
  const el = document.getElementById('fleetSyncLog');
  el.textContent = '⏳ 执行中...\n';
  try {
    const r = await fetch('/api/fleet/sync', {method:'POST'});
    const d = await r.json();
    el.textContent = d.output || JSON.stringify(d, null, 2);
  } catch(e) { el.textContent = '❌ ' + e.message; }
};

window.doFleetReconcile = async function() {
  const el = document.getElementById('fleetReconcileLog');
  el.textContent = '⏳ 执行中...\n';
  try {
    const r = await fetch('/api/fleet/reconcile', {method:'POST'});
    const d = await r.json();
    el.textContent = d.output || JSON.stringify(d, null, 2);
  } catch(e) { el.textContent = '❌ ' + e.message; }
};

window.doFleetExec = async function() {
  const machine = document.getElementById('fleetExecMachine')?.value;
  const cmd = document.getElementById('fleetExecCmd')?.value;
  const el = document.getElementById('fleetExecLog');
  if (!machine || !cmd) { el.textContent = '请填写目标机器和命令'; return; }
  el.textContent = '⏳ 执行 ' + cmd + ' @' + machine + '...\n';
  try {
    const r = await fetch('/api/fleet/exec', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({machine, cmd})});
    const d = await r.json();
    el.textContent = d.output || JSON.stringify(d, null, 2);
  } catch(e) { el.textContent = '❌ ' + e.message; }
};

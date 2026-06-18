// ════════════════════════════════════════════════════════
// 共享账号选择器（所有操作视图共用）
// ════════════════════════════════════════════════════════

let _allAccounts = [];

async function _loadAccounts() {
  if (_allAccounts.length) return _allAccounts;
  const [r1, r2] = await Promise.all([
    fetch('/api/matrix/accounts'),
    fetch('/api/matrix/homepage-info').catch(() => ({json: () => ({})}))
  ]);
  const accts = await r1.json();
  const hpData = r2.json ? await r2.json() : {results:[]};
  _allAccounts = Array.isArray(accts) ? accts.filter(a => a.enabled !== false) : [];

  const hpIndex = {};
  (hpData.results || []).forEach(r => {
    if (r.identity_dir) hpIndex[r.identity_dir] = r;
    if (r.phone) hpIndex[r.phone] = r;
  });

  return {accounts: _allAccounts, hpIndex, collectedAt: hpData.collected_at || ''};
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
// 导出供其他模块调用
window.loadAveRender = loadAveRender;

async function loadAveScript()   { _renderShell('view-ave-script', '📝 脚本生成', '无API', '脚本生成模块的 API 尚未暴露。需要完成 agentos ave CLI 封装后对接。'); }
// 导出供其他模块调用
window.loadAveScript = loadAveScript;

async function loadAveMaterials(){ _renderShell('view-ave-materials', '📦 素材库', '无API', '素材管理模块的 API 尚未暴露。当前素材通过 SQLite 管理，需封装为 Dashboard API。'); }
// 导出供其他模块调用
window.loadAveMaterials = loadAveMaterials;

async function loadAveTemplates(){ _renderShell('view-ave-templates', '📋 模板', '无API', '模板管理模块的 API 尚未暴露。需要完成 agentos ave CLI 封装后对接。'); }
// 导出供其他模块调用
window.loadAveTemplates = loadAveTemplates;


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
// 导出供其他模块调用
window.loadCrawlTasks = loadCrawlTasks;

async function loadCrawlSources(){ _renderShell('view-crawl-sources', '📡 源管理', '无CLI', '采集源管理需要 agentos crawl CLI 封装后实现。'); }
// 导出供其他模块调用
window.loadCrawlSources = loadCrawlSources;

async function loadCrawlHistory(){ _renderShell('view-crawl-history', '📜 采集历史', '无API', '采集历史的统一展示 API 尚未完成。'); }
// 导出供其他模块调用
window.loadCrawlHistory = loadCrawlHistory;


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
// 导出供其他模块调用
window.loadFleetSync = loadFleetSync;

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
// 导出供其他模块调用
window.loadFleetReconcile = loadFleetReconcile;

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
// 导出供其他模块调用
window.loadFleetExec = loadFleetExec;

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
// 导出供其他模块调用
window.loadServeMCP = loadServeMCP;

async function loadServeDashboard(){ _renderShell('view-serve-dashboard', '📊 Dashboard日志', '无功能', 'Dashboard 日志聚合页面尚未实现。将汇总各模块的运行日志。'); }
// 导出供其他模块调用
window.loadServeDashboard = loadServeDashboard;

async function loadServeSchedule() { _renderShell('view-serve-schedule', '⏰ 全局定时任务', '无功能', '全局调度器管理页面尚未实现。将在 agentos serve schedule CLI 封装完成后对接。'); }
// 导出供其他模块调用
window.loadServeSchedule = loadServeSchedule;


// ── SMS & Proxy ──
async function loadSmsProxy() {
  loadSmsConfig();
  loadProxyList();
  loadPhonePresets();
  loadSmsAccounts();
}
// 导出供其他模块调用
window.loadSmsProxy = loadSmsProxy;


async function loadSmsAccounts() {
  const sel = document.getElementById('smsAccountSelect');
  const overview = document.getElementById('smsAccountsOverview');
  if (!sel) return;
  try {
    // 用联邦API获取所有机器的账号，本地API作为下拉选择的数据源
    let accounts = [];
    let fedOk = false;
    try {
      const fr = await fetch('/api/federation/accounts');
      const fd = await fr.json();
      if (Array.isArray(fd) && fd.length) {
        accounts = fd.map(a => ({
          id: a.id,
          phone: a.phone || a.phone_mask || '',
          nickname: a.identity_hint || a.id,
          platform: a.platform || '',
          is_local: a.is_local || a.owner_machine === window.location.hostname,
          owner_machine: a.owner_machine || a._source_machine_name || '',
          has_cookie: a._status === 'logged_in',
          has_identity: a.identity_dir ? true : false,
          has_profile: false,
          has_registry: false,
          fans: a.fans || '?',
          posts: a.posts || '?',
          following: a.following || '?',
          likes: a.likes || '?',
          identity_dir: a.identity_dir || '',
          fingerprint: a.fingerprint || {},
          busy: a.busy || false,
          busy_since: a.busy_since || '',
        }));
        fedOk = true;
      }
    } catch(e) { /* fallback to local API */ }

    if (!fedOk) {
      // 降级：使用本地 SMS API
      const r = await fetch('/api/matrix/sms/accounts');
      const d = await r.json();
      if (d.error) {
        if (overview) overview.innerHTML = '<span style="color:var(--red)">❌ '+d.error+'</span>';
        return;
      }
      accounts = d.accounts || [];
    }

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
        Object.values(groups).map(function(g) {
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
        accounts.map(function(a, idx) {
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
      // 保存accounts数据供排序筛选用
      window._acctTableData = accounts;

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
  const opts = window._smsAccountOptions || [];
  if (!input || !sel) return;
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
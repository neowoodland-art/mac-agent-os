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
              <option value="douyin_daily">🎵 douyin_daily</option>
              <option value="xhs_daily">📕 xhs_daily</option>
              <option value="douyin_active_v1">🎵 douyin_active_v1</option>
              <option value="xhs_active_v1">📕 xhs_active_v1</option>
            </select>
          </label>
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
  _renderAccountSelector('collectAccountList', {_data: data, height: '300px', checkAll: false});
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
  _renderAccountSelector('commentAccountList', {_data: data, height: '300px', checkAll: false, hideFilter: true});
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
  _renderAccountSelector('likeAccountList', {_data: data, height: '300px', checkAll: false, hideFilter: true});
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
  _renderAccountSelector('opsAccountList', {_data: data, height: '280px', checkAll: false});
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
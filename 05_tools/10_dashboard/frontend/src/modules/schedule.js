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
// ── 导出（防 Rollup tree-shake）──
window.doNurtureExec = doNurtureExec;
window.filterNurtureList = filterNurtureList;
window.loadCmdNurture = loadCmdNurture;
window.loadNurtureAccounts = loadNurtureAccounts;
window.ntToggleIdentity = ntToggleIdentity;
window.ntToggleMachine = ntToggleMachine;
window.nurtureExec = nurtureExec;
window.nurtureExecAll = nurtureExecAll;
window.nurturePreflight = nurturePreflight;
window.nurtureToggleAll = nurtureToggleAll;
window.toggleNurtureGroup = toggleNurtureGroup;
window.updateNurtureCount = updateNurtureCount;
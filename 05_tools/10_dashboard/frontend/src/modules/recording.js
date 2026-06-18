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
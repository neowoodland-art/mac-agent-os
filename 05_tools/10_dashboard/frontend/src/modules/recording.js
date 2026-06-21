// ════════════════════════════════════════════════════════
// Operation Router — 统一操作路由 (本地/远程)
// ════════════════════════════════════════════════════════

function _getAccountById(accountId) {
  // 优先从 _lastSmsAccounts 找（SMS代理视图加载后的缓存）
  var fromCache = (window._lastSmsAccounts || []).find(function(a){return a.id===accountId;});
  if (fromCache) return fromCache;
  // 兜底: 从 accounts API 查（Vite视图打开时 _lastSmsAccounts 可能为空）
  if (window._allAccounts) {
    return window._allAccounts.find(function(a){return a.id===accountId;});
  }
  return null;
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
    if (result.status === 'ok') {
      statusEl.innerHTML = '<span style="color:var(--green)">✅ 登录命令已发送到 '+machine+'</span>';
    } else {
      statusEl.innerHTML = '<span style="color:var(--red)">❌ '+(result.message||result.error||'失败')+'</span>';
    }
  }
}

// ── 加载 accounts API 缓存（供 _getAccountById 兜底）──
(async function() {
  try {
    var r = await fetch('/api/matrix/accounts');
    var d = await r.json();
    window._allAccounts = Array.isArray(d) ? d : (d.accounts || []);
  } catch(e) { /* 静默 */ }
})();

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
// 录制管理 — 列表 / 详情 / 导出
// ════════════════════════════════════════════════════════

async function loadMatrixRecord() {
  // 先填充账号下拉框
  try {
    var acctR = await fetch('/api/matrix/accounts');
    var acctD = await acctR.json();
    var accts = Array.isArray(acctD) ? acctD : (acctD.accounts || []);
    var sel = document.getElementById('recordAccountSelect');
    if (sel) {
      sel.innerHTML = '<option value="">选择账号…</option>';
      accts.forEach(function(a) {
        sel.innerHTML += '<option value="'+a.id+'">'+a.id+'</option>';
      });
    }
  } catch(e) {}

  var listEl = document.getElementById('recordList');
  if (!listEl) return;
  listEl.innerHTML = '<div class="loading">⏳ 加载录制包...</div>';

  try {
    var r = await fetch('/api/matrix/record/list');
    var d = await r.json();
    var recs = d.recordings || [];

    if (!recs.length) {
      listEl.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text2)">暂无录制包。选择账号后点击「开始录制」。</div>';
      document.getElementById('recordDetail').innerHTML = '';
      return;
    }

    var html = '<div style="display:grid;gap:4px">';
    recs.forEach(function(rec) {
      var created = (rec.created || '').slice(0, 16).replace('T', ' ');
      html += '<div class="record-item" data-name="'+rec.name+'" onclick="recordingDetail(this.dataset.name)" style="padding:6px 10px;cursor:pointer;border-radius:4px;background:var(--bg2);display:flex;justify-content:space-between;font-size:12px">';
      html += '<span><b>'+rec.account+'</b> · '+rec.platform+' · '+rec.steps+'步 · '+rec.duration+'s</span>';
      html += '<span style="color:var(--text2)">'+created+' <span style="color:var(--text2)">'+rec.size_kb+'KB</span></span>';
      html += '</div>';
    });
    html += '</div>';
    listEl.innerHTML = html;
  } catch(e) {
    listEl.innerHTML = '<div style="color:var(--red);padding:10px">❌ 加载失败: '+e.message+'</div>';
  }
}

async function recordingStart() {
  var sel = document.getElementById('recordAccountSelect');
  var aid = sel ? sel.value : '';
  if (!aid) { alert('请先选择账号'); return; }

  // 先确认账号有没有登录（浏览器打开）
  try {
    var acctR = await fetch('/api/matrix/accounts');
    var acctD = await acctR.json();
    var accts = Array.isArray(acctD) ? acctD : (acctD.accounts || []);
    var acct = accts.find(function(a){return a.id===aid;});
    if (acct && !acct.is_login && !acct.is_local) {
      if (!confirm('账号 '+aid+' 可能未登录。是否先登录？')) return;
      await accountLogin(aid);
    }
  } catch(e) {}

  document.getElementById('recordStartBtn').style.display = 'none';
  document.getElementById('recordStopBtn').style.display = 'inline-block';
  document.getElementById('recordStatus').innerHTML = '⏳ 正在启动录制...';
  try {
    var r = await fetch('/api/matrix/accounts/'+aid+'/record', {method:'POST'});
    var d = await r.json();
    document.getElementById('recordStatus').innerHTML = '<span style="color:var(--green)">🎬 录制中... 操作浏览器，然后按反引号 `·` 标记步骤（截图），Esc 结束保存</span>';
  } catch(e) {
    document.getElementById('recordStatus').innerHTML = '<span style="color:var(--green)">🎬 录制已启动（操作浏览器后按数字键标记步骤，0=结束）</span>';
  }
}

async function recordingStop() {
  document.getElementById('recordStatus').innerHTML = '⏳ 刷新录制列表...';
  document.getElementById('recordStartBtn').style.display = 'inline-block';
  document.getElementById('recordStopBtn').style.display = 'none';
  try {
    loadMatrixRecord();
    document.getElementById('recordStatus').innerHTML = '<span style="color:var(--green)">✅ 录制已保存</span>';
  } catch(e) {
    document.getElementById('recordStatus').innerHTML = '<span style="color:var(--text2)">💡 在浏览器中按 0 键结束录制并保存</span>';
  }
}

var _recordLabels = {};  // step_num → {op, args}

async function recordingDetail(name) {
  var detailEl = document.getElementById('recordDetail');
  if (!detailEl) return;
  detailEl.innerHTML = '<div class="loading">⏳ 加载录制详情...</div>';

  try {
    var r = await fetch('/api/matrix/record/detail/'+encodeURIComponent(name));
    var d = await r.json();
    var meta = d.meta || {};
    var steps = d.steps || [];
    var analysis = d.analysis || {};

    _recordLabels = {};
    var html = '<div style="background:var(--bg2);padding:10px;border-radius:6px;margin-top:8px">';
    html += '<div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:12px;color:var(--text2)">';
    html += '<span>账号: <b>'+meta.account_id+'</b> · 平台: '+meta.platform+' · 共 '+steps.length+' 步</span>';
    html += '<span style="display:flex;gap:4px">';
    html += '<button onclick="recordingExport(\''+name+'\')" style="background:#6366f1;color:#fff;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:11px">📦 导出为蓝图</button>';
    html += '<button onclick="if(confirm(\'确定删除?\')){fetch(\'/api/matrix/record/delete\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({name:\''+name+'\'})}).then(function(){loadMatrixRecord();document.getElementById(\'recordDetail\').innerHTML=\'\';})}" style="background:rgba(220,38,38,.08);color:var(--red);border:1px solid var(--red);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:11px">🗑 删除</button>';
    html += '</span></div>';

    // 分析建议
    var actions = analysis.actions || [];
    var actMap = {};
    actions.forEach(function(a) {
      var idx = a.step_after || a.step_before;
      actMap[idx] = a;
    });

    // 每一步
    var opOptions = ['skip','goto_home','like','collect','follow','comment','open_comments','close_comments','post_comment','search','scroll_feed','wait_watch','next_video','prev_video','go_back','open_video','xhs_like','xhs_collect','xhs_comment','xhs_follow','xhs_scroll_feed','xhs_click_note','xhs_search'];

    steps.forEach(function(step, i) {
      var sn = step.step || (i+1);
      var pg = step.page || {};
      var suggests = actMap[sn] ? (actMap[sn].action_type || '') : '';
      var suggestText = actMap[sn] ? (actMap[sn].action_desc || suggests) : '';

      html += '<div style="border:1px solid var(--border);border-radius:4px;padding:8px;margin-bottom:6px;font-size:12px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">';
      html += '<span><b>步骤 '+sn+'</b>  <span style="color:var(--text2)">'+pg.page_mode+'</span>  <span style="color:var(--text2);font-size:11px">'+(pg.url||'').slice(0,60)+'</span></span>';
      html += '<span>';
      if (suggests) html += '<span style="color:#6366f1;font-size:11px;margin-right:6px">💡 '+suggestText+'</span>';
      html += '<select id="rec_op_'+sn+'" onchange="_recordLabels['+sn+']={op:this.value}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 6px;border-radius:4px;font-size:11px">';
      html += '<option value="">— 选择操作 —</option>';
      opOptions.forEach(function(op) {
        var sel = (suggests === op || suggests === op.replace('xhs_', '').replace('dy_', '')) ? ' selected' : '';
        html += '<option value="'+op+'"'+sel+'>'+op+'</option>';
      });
      html += '</select>';
      html += '</span></div>';

      if (step.events_since_last > 0) {
        html += '<div style="color:var(--text2);font-size:11px">事件: '+step.events_since_last+' 个</div>';
      }
      html += '</div>';
    });

    html += '</div>';
    detailEl.innerHTML = html;
  } catch(e) {
    detailEl.innerHTML = '<div style="color:var(--red);padding:10px">❌ 加载失败: '+e.message+'</div>';
  }
}

async function recordingExport(name) {
  var labels = [];
  Object.keys(_recordLabels).forEach(function(sn) {
    var sel = document.getElementById('rec_op_'+sn);
    if (sel && sel.value) {
      labels.push({step: parseInt(sn), op: sel.value});
    }
  });
  if (!labels.length) {
    alert('请先为至少一步选择操作类型');
    return;
  }
  try {
    var r = await fetch('/api/matrix/record/export', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:name, labels:labels, blueprint_name: name.replace('recording_','bp_')})
    });
    var d = await r.json();
    if (d.status === 'ok') {
      alert('✅ 蓝图已生成: '+d.blueprint+' ('+d.steps+'步)');
      loadMatrixRecord();
      document.getElementById('recordDetail').innerHTML = '';
    } else {
      alert('❌ 导出失败: '+(d.message||d.error));
    }
  } catch(e) {
    alert('❌ 导出异常: '+e.message);
  }
}

// ── 导出（防 Rollup tree-shake）──
window.accountLogin = accountLogin;
window.loadMatrixRecord = loadMatrixRecord;
window.recordingStart = recordingStart;
window.recordingStop = recordingStop;
window.recordingDetail = recordingDetail;
window.recordingExport = recordingExport;
window._recordLabels = _recordLabels;
window.clearCookies = clearCookies;
window.collectAllPlatforms = collectAllPlatforms;
window.collectProfile = collectProfile;
window.deleteAccount = deleteAccount;
window.deleteIdentityByPhone = deleteIdentityByPhone;
window.loginAllPlatforms = loginAllPlatforms;
window._getAccountById = _getAccountById;
window._routeOperation = _routeOperation;
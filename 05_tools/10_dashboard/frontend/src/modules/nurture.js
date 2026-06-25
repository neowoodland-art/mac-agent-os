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
    const r = await fetch('/api/ops/run', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({type:'collect', accounts:ids, params:{rounds:1}})});
    const data = await r.json();
    if (data.status !== 'accepted') {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ 启动失败: ' + (data.error||data.message||data.status) + '</span>';
      return;
    }
    const runId = data.commands?.[0]?.run_id;
    if (logEl) logEl.textContent += '🚀 采集任务已启动 (runId=' + (runId||'?') + ')\n';

    if (!runId) { if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">✅ 已提交</span>'; return; }

    const poll = setInterval(async () => {
      try {
        const pr = await fetch('/api/ops/status');
        const ps = await pr.json();
        const cmds = Array.isArray(ps) ? ps : (ps.commands || []);
        const cmd = cmds.find(c => c.run_id === runId);
        if (!cmd) return;
        if (cmd.status === 'running' || cmd.status === 'dispatching' || cmd.status === 'queued') {
          if (statusEl) statusEl.innerHTML = '⏳ ' + cmd.status + '... ' + (cmd.elapsed_sec>0 ? Math.round(cmd.elapsed_sec)+'s' : '');
          if (logEl) {
            const line = '  ⏳ ' + cmd.status + ' (' + ((cmd.elapsed_sec>0) ? Math.round(cmd.elapsed_sec)+'s' : '') + ')\n';
            if (!logEl.textContent.includes(line.trim())) logEl.textContent += line;
          }
        } else if (['completed','failed','crashed','cancelled','timed_out'].includes(cmd.status)) {
          clearInterval(poll);
          if (cmd.status === 'completed') {
            if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">✅ 采集完成</span>';
          } else {
            if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ ' + cmd.status + '</span>';
          }
          if (logEl) logEl.textContent += '🏁 状态: ' + cmd.status + ' - ' + (cmd.message||'') + '\n';
          await showCollectReport(ids, statusEl, logEl);
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
    const r = await fetch('/api/ops/run', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({type:'collect', params:{rounds:1}})});
    const data = await r.json();
    if (data.status !== 'accepted') {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ 启动失败: ' + (data.error||data.message||data.status) + '</span>';
      return;
    }
    const runId = data.commands?.[0]?.run_id;
    if (logEl) logEl.textContent += '🚀 批量采集已启动 (runId=' + (runId||'?') + ')\n';

    if (!runId) { if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">✅ 已提交</span>'; return; }

    const poll = setInterval(async () => {
      try {
        const pr = await fetch('/api/ops/status');
        const ps = await pr.json();
        const cmds = Array.isArray(ps) ? ps : (ps.commands || []);
        const cmd = cmds.find(c => c.run_id === runId);
        if (!cmd) return;
        if (cmd.status === 'running' || cmd.status === 'dispatching' || cmd.status === 'queued') {
          if (statusEl) statusEl.innerHTML = '⏳ ' + cmd.status + '... ' + (cmd.elapsed_sec>0 ? Math.round(cmd.elapsed_sec)+'s' : '');
        } else if (['completed','failed','crashed','cancelled','timed_out'].includes(cmd.status)) {
          clearInterval(poll);
          if (cmd.status === 'completed') {
            if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">✅ 采集完成</span>';
          } else {
            if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ ' + cmd.status + '</span>';
          }
          if (logEl) logEl.textContent += '🏁 状态: ' + cmd.status + ' - ' + (cmd.message||'') + '\n';
          await showCollectReport(null, statusEl, logEl);
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
// ── 导出（防 Rollup tree-shake）──
window.cmdCollectAll = cmdCollectAll;
window.cmdCollectSelected = cmdCollectSelected;
window.getSelectedAccounts = getSelectedAccounts;
window.renderCollectList = renderCollectList;
window.showCollectReport = showCollectReport;
window.switchCollectMode = switchCollectMode;
window.toggleCollectIdentity = toggleCollectIdentity;
window.toggleCollectPlatform = toggleCollectPlatform;
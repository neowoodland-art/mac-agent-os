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
        const stepsPreview = (b.steps||[]).slice(0,3).map(s => { var sn = s.op||s.name; return window._matrixOps?.[sn]?.label||sn||''; }).join(' → ');
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
// 导出供其他模块调用
window.loadMatrixBlueprints = loadMatrixBlueprints;


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
      label = (typeof op2?.label === 'string') ? op2.label : (s.name || '(未知)');
    }
    if (typeof label !== 'string') {
      // 最终兜底：尝试用 s.op 或 s.name 直接查 _matrixOps
      var stepKey = s.op || s.name;
      if (stepKey && window._matrixOps?.[stepKey]) {
        var lbl = window._matrixOps[stepKey].label;
        if (typeof lbl === 'string') label = lbl;
        else label = stepKey;
      } else {
        label = '❌错误:' + String(typeof s) + '/' + String(s);
      }
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
    const bp = (d.blueprints||[]).find(b => b.name === name);
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
let _bpExecName = '';
function bpExecute(name) {
  _bpExecName = name;
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
  if (!sel || !sel.value) { resultEl.innerHTML = '<span style="color:var(--red)">请选择身份</span>'; return; }
  resultEl.innerHTML = '<span style="color:var(--text2)">⏳ 执行中...</span>';
  try {
    const r = await fetch('/api/matrix/blueprints/'+encodeURIComponent(_bpExecName)+'/execute', {
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
// ── 导出（防 Rollup tree-shake）──
window.acctSwitchTab = acctSwitchTab;
window.batchExecute = batchExecute;
window.batchPreview = batchPreview;
window.bpCanFollow = bpCanFollow;
window.bpDoExec = bpDoExec;
window.bpExecute = bpExecute;
window.bpGetPlatform = bpGetPlatform;
window.bpRenderOps = bpRenderOps;
window.bpRenderSteps = bpRenderSteps;
window.bpUpdatePlatform = bpUpdatePlatform;
window.closeBpModal = closeBpModal;
window.corpusToggleRandom = corpusToggleRandom;
window.deleteIdentity = deleteIdentity;
window.loadIdentities = loadIdentities;
window.loadMatrixAccounts = loadMatrixAccounts;
window.loadMatrixRun = loadMatrixRun;
window.renderAccountsTable = renderAccountsTable;
window.sortAccounts = sortAccounts;
window.unbindAccount = unbindAccount;
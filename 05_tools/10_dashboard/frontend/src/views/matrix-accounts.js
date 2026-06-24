/**
 * 账号管理视图（v3 — 自包含，带搜索/筛选/建号功能）
 */
export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
  try {
    const BASE = '/api';
    const [ar, hr] = await Promise.all([
      fetch(BASE + '/matrix/accounts').then(r => r.ok ? r.json() : { accounts: [] }).catch(() => ({ accounts: [] })),
      fetch(BASE + '/matrix/homepage-info').then(r => r.ok ? r.json() : { results: [] }).catch(() => ({ results: [] })),
    ]);
    const allAccounts = Array.isArray(ar) ? ar : (ar.accounts || []);
    const results = (hr.results || []);

    const hpIndex = {};
    results.forEach(r => { if (r.identity_dir) hpIndex[r.identity_dir] = r; if (r.phone) hpIndex[r.phone] = r; });

    // 构建展示数据
    function buildAccounts(accounts) {
      const machineOrder = ['chengzigedeAir', '5kechengdeAir', '7kecheng'];
      const groups = {};
      accounts.forEach(a => {
        const m = a.owner_machine || 'unknown';
        if (!groups[m]) groups[m] = [];
        const hp = hpIndex[a.identity_dir] || hpIndex[a.phone];
        const hpAcc = hp ? (a.platform === 'douyin' ? hp.douyin : hp.xiaohongshu) : null;
        groups[m].push({
          id: a.id, platform: a.platform, phone: a.phone || '',
          identity_dir: (a.identity_dir || '').replace('identities/', ''),
          nickname: hpAcc?.nickname || a.nickname || '',
          fans: hpAcc?.fans || a.fans || '', following: hpAcc?.following || a.following || '',
          likes: hpAcc?.likes || a.likes || '', posts: hpAcc?.posts || a.posts || '',
          status: a._status || 'unknown',
        });
      });
      let html = '<table style="width:100%;font-size:11px;border-collapse:collapse">';
      html += '<tr style="font-size:9px;color:var(--text2);border-bottom:1px solid var(--border)">'
        + '<th style="padding:4px 6px;font-weight:400;text-align:left">机器</th>'
        + '<th style="padding:4px 6px;font-weight:400;text-align:left">📱手机号</th>'
        + '<th style="padding:4px 6px;font-weight:400;text-align:left">身份</th>'
        + '<th style="padding:4px 6px;font-weight:400;text-align:left">账号ID</th>'
        + '<th style="padding:4px 6px;font-weight:400;text-align:left">平台</th>'
        + '<th style="padding:4px 6px;font-weight:400;text-align:left">昵称</th>'
        + '<th style="padding:4px 6px;font-weight:400;text-align:right" title="粉丝">👥</th>'
        + '<th style="padding:4px 6px;font-weight:400;text-align:right" title="关注">👍</th>'
        + '<th style="padding:4px 6px;font-weight:400;text-align:right" title="获赞">❤️</th>'
        + '<th style="padding:4px 6px;font-weight:400;text-align:right" title="作品">📝</th>'
        + '<th style="padding:4px 6px;font-weight:400;text-align:left">状态</th></tr>';
      machineOrder.filter(m => groups[m]).forEach(m => {
        groups[m].forEach(a => {
          const statusMap = { logged_in:'🟢已登录', remote:'🔵远程', expired:'🟡过期', no_cookie:'🔴无Cookie', disabled:'⚪禁用' };
          const s = statusMap[a.status] || a.status;
          html += `<tr style="border-bottom:1px solid var(--border)" data-filter="${(a.id+a.phone+a.nickname+a.identity_dir+m).toLowerCase()}">`
            + `<td style="padding:3px 6px">${m === 'chengzigedeAir' ? '🖥️' : '☁️'}${m}</td>`
            + `<td style="padding:3px 6px;font-size:10px;color:var(--text2)">${a.phone || '-'}</td>`
            + `<td style="padding:3px 6px;font-size:10px;color:var(--text2)">📁${a.identity_dir}</td>`
            + `<td style="padding:3px 6px"><strong>${a.id}</strong></td>`
            + `<td style="padding:3px 6px">${a.platform === 'douyin' ? '🎵' : '📕'}</td>`
            + `<td style="padding:3px 6px">${a.nickname || '-'}</td>`
            + `<td style="padding:3px 6px;text-align:right">${a.fans || '-'}</td>`
            + `<td style="padding:3px 6px;text-align:right">${a.following || '-'}</td>`
            + `<td style="padding:3px 6px;text-align:right">${a.likes || '-'}</td>`
            + `<td style="padding:3px 6px;text-align:right">${a.posts || '-'}</td>`
            + `<td style="padding:3px 6px;font-size:10px">${s}</td></tr>`;
        });
      });
      html += '</table>';
      return html;
    }

    function render(q, machine, platform) {
      let filtered = allAccounts;
      if (q) { const lq = q.toLowerCase(); filtered = allAccounts.filter(a => (a.id+a.phone+(a.nickname||'')+(a.identity_dir||'')+(a.owner_machine||'')).toLowerCase().includes(lq)); }
      if (machine) filtered = filtered.filter(a => a.owner_machine === machine);
      if (platform) filtered = filtered.filter(a => a.platform === platform);
      // machineList 已在外部定义
      const tableDiv = document.getElementById('acctTable');
      if (tableDiv) tableDiv.innerHTML = buildAccounts(filtered);
      const cnt = document.getElementById('acctCount');
      if (cnt) cnt.textContent = `共 ${filtered.length}/${allAccounts.length} 个`;
    }

    const machineList = [...new Set(allAccounts.map(a => a.owner_machine).filter(Boolean))];
    container.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <h2 style="font-size:18px;margin:0">👤 账号管理</h2>
        <div style="display:flex;gap:6px">
          <button onclick="window._showCreateAcct()" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">+ 新建账号</button>
          <button onclick="try{window.switchView('matrix-sms-proxy')}catch(e){}" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">📡 短信与代理</button>
        </div>
      </div>
      <div style="display:flex;gap:6px;margin-bottom:8px;align-items:center">
        <input id="acctSearch" placeholder="🔍 搜索手机号/昵称/账号ID/机器..." oninput="_filterAcct()"
          style="flex:1;padding:4px 8px;font-size:12px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px">
        <select id="acctMachineFilter" onchange="_filterAcct()" style="padding:4px 8px;font-size:11px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px">
          <option value="">全部机器</option>
          ${machineList.map(m => `<option value="${m}">${m}</option>`).join('')}
        </select>
        <select id="acctPlatformFilter" onchange="_filterAcct()" style="padding:4px 8px;font-size:11px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px">
          <option value="">全部平台</option>
          <option value="douyin">🎵 抖音</option>
          <option value="xiaohongshu">📕 小红书</option>
        </select>
        <span id="acctCount" style="font-size:10px;color:var(--text2);white-space:nowrap">共 ${allAccounts.length} 个</span>
      </div>
      <div id="acctTable" style="overflow-x:auto">${buildAccounts(allAccounts)}</div>`;

    window._filterAcct = () => {
      const q = document.getElementById('acctSearch')?.value || '';
      const m = document.getElementById('acctMachineFilter')?.value || '';
      const p = document.getElementById('acctPlatformFilter')?.value || '';
      render(q, m, p);
    };

    // 新建账号对话框（ID 自动生成: douyin_手机号 / xhs_手机号）
    window._showCreateAcct = () => {
      const overlay = document.createElement('div');
      overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:99999;display:flex;align-items:center;justify-content:center';
      overlay.innerHTML = `
        <div style="background:var(--bg2);border-radius:12px;padding:20px;max-width:360px;width:90%">
          <div style="font-size:15px;font-weight:600;margin-bottom:12px">+ 新建账号</div>
          <div style="display:grid;gap:6px;font-size:12px">
            <label>平台 <select id="newAcctPlat" onchange="_updateAcctId()" style="width:100%;padding:4px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px">
              <option value="douyin">🎵 抖音</option><option value="xiaohongshu">📕 小红书</option></select></label>
            <label>手机号 <input id="newAcctPhone" oninput="_updateAcctId()" placeholder="手机号" style="width:100%;padding:4px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px"></label>
            <label>账号ID <input id="newAcctId" readonly style="width:100%;padding:4px;background:var(--bg3);border:1px solid var(--border);color:var(--text2);border-radius:4px;font-size:10px"></label>
          </div>
          <div style="display:flex;gap:6px;justify-content:flex-end;margin-top:12px">
            <button onclick="this.closest('div[style]').parentElement.remove()" style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">取消</button>
            <button id="newAcctOk" style="background:var(--primary);color:#fff;border:none;border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">✅ 创建</button>
          </div>
        </div>`;
      document.body.appendChild(overlay);
      window._updateAcctId = () => {
        const plat = document.getElementById('newAcctPlat')?.value || 'douyin';
        const phone = document.getElementById('newAcctPhone')?.value?.trim() || '';
        const prefix = plat === 'douyin' ? 'douyin_' : 'xhs_';
        document.getElementById('newAcctId').value = phone ? prefix + phone : '';
      };
      window._updateAcctId();
      document.getElementById('newAcctOk').onclick = async () => {
        const id = document.getElementById('newAcctId').value.trim();
        const plat = document.getElementById('newAcctPlat').value;
        const phone = document.getElementById('newAcctPhone').value.trim();
        if (!id) { alert('请先输入手机号'); return; }
        try {
          const r = await fetch(BASE + '/matrix/accounts', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id, platform: plat, phone, enabled: true }),
          });
          const d = await r.json();
          if (d.status === 'ok') { overlay.remove(); window._filterAcct(); }
          else { alert('创建失败: ' + (d.detail || d.message)); }
        } catch(e) { alert('创建失败: ' + e.message); }
      };
    };

  } catch (e) {
    container.innerHTML = `<div class="error">❌ ${e.message || e}</div>`;
  }
}

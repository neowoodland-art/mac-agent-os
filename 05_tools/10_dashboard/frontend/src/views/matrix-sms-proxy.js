/**
 * 短信与代理管理（v5 — 固定 ID 冲突问题）
 */
export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载中...</div>';

  // 注册全局函数（使用唯一 ID 前缀避免与旧壳层冲突）
  const P = 'smp_'; // sms-proxy 前缀
  window._smsFilter = () => {
    const input = document.getElementById(P + 'acctSearch');
    const sel = document.getElementById(P + 'acctSelect');
    if (!input || !sel) return;
    if (!window._smsAccountOptions) {
      sel.innerHTML = '<option>⏳ 加载中...</option>';
      sel.style.display = 'block';
      return;
    }
    const opts = window._smsAccountOptions;
    const q = input.value.trim().toLowerCase();
    let matched = [];
    if (!q) { matched = opts.slice(0, 30); }
    else {
      matched = opts.filter(a => {
        const phone = (a.phone || '').toLowerCase();
        const nick = (a.nickname || '').toLowerCase();
        return phone.includes(q) || nick.includes(q) || (a.id||'').toLowerCase().includes(q);
      });
    }
    sel.innerHTML = '<option value="">— 选择账号 —</option>' +
      matched.map(a => '<option value="'+a.id+'" data-phone="'+(a.phone||'')+'" data-nick="'+(a.nickname||'')+'">'+
        ((a.platform==='xiaohongshu'?'📕':'🎵')+' '+a.nickname+' '+
        (a.owner_machine||(a.is_local?'本机':'远程'))+' ('+a.phone+')')+'</option>').join('');
    if (q.length >= 4) {
      const exact = opts.find(a => a.phone === input.value.trim());
      if (exact) { sel.value = exact.id; window._smsSelect(); sel.style.display = 'none'; return; }
    }
    sel.style.display = 'block';
    sel.size = Math.min(matched.length + 1, 6);
    sel.selectedIndex = 0;
  };

  window._smsSelect = () => {
    const sel = document.getElementById(P + 'acctSelect');
    const info = document.getElementById(P + 'selectedAcct');
    const input = document.getElementById(P + 'acctSearch');
    if (!sel || !info) return;
    const opt = sel.options[sel.selectedIndex];
    if (!opt || !opt.value) { info.innerHTML = ''; return; }
    const nick = opt.getAttribute('data-nick') || opt.value;
    const phone = opt.getAttribute('data-phone') || '';
    info.innerHTML = '<span style="color:var(--green)">'+nick+'</span> <span style="color:var(--text2)">('+phone+')</span>';
    if (input) { input.value = phone || opt.textContent.trim(); document.getElementById(P + 'acctSelect').style.display = 'none'; }
  };

  try {
    const BASE = '/api';
    const [accountsR, proxiesR] = await Promise.all([
      fetch(BASE + '/matrix/sms/accounts').then(r => r.ok ? r.json() : { accounts: [] }).catch(() => ({ accounts: [] })),
      fetch(BASE + '/matrix/proxies').then(r => r.ok ? r.json() : { proxies: [] }).catch(() => ({ proxies: [] })),
    ]);

    const accounts = accountsR.accounts || [];
    const proxies = proxiesR.proxies || [];
    window._smsAccountOptions = accounts;
    const proxyAccts = proxies.filter((p, i, a) => a.findIndex(x => x.account === p.account) === i);
    const presetProxies = [...new Set(proxies.map(p => p.proxy).filter(Boolean))];

    container.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">📡 短信与代理</h2>
        <button onclick="location.reload()" style="background:transparent;color:var(--text);border:1px solid var(--border);padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px">🔄 刷新</button>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
          <div style="font-size:13px;font-weight:600;margin-bottom:8px">📱 短信接收</div>
          <div style="display:flex;gap:4px;margin-bottom:4px">
            <div style="flex:1;position:relative">
              <input id="smp_acctSearch" placeholder="输入手机号/昵称搜索..." autocomplete="off"
                oninput="window._smsFilter()" onfocus="window._smsFilter()"
                style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px;border-radius:5px;font-size:12px">
              <select id="smp_acctSelect" onchange="window._smsSelect()" size="4"
                style="display:none;position:absolute;top:100%;left:0;right:0;z-index:10;background:var(--bg2);border:1px solid var(--primary);color:var(--text);padding:2px;border-radius:5px;font-size:11px;max-height:150px">
                <option value="">— 选择账号 —</option>
              </select>
            </div>
          </div>
          <div style="display:flex;gap:4px;margin-bottom:4px">
            <button onclick="window._smsCheckSelected()" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">📩 查短信</button>
            <button onclick="window._collectProfile()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">👤 采集昵称</button>
          </div>
          <div id="smp_selectedAcct" style="font-size:11px;color:var(--text2);margin-top:2px"></div>
          <div id="smp_messages" style="font-size:11px;margin-top:4px;max-height:280px;overflow-y:auto"></div>
        </div>
        <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
          <div style="font-size:13px;font-weight:600;margin-bottom:8px">🖥️ 代理配置</div>
          <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:4px">
            <select id="smp_proxyAcct" style="flex:1;min-width:120px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:4px;font-size:11px">
              <option value="">— 选择账号 —</option>
              ${proxyAccts.map(p => `<option value="${p.account}" data-proxy="${p.proxy||''}">${p.platform==='xiaohongshu'?'📕':'🎵'} ${p.account}</option>`).join('')}
            </select>
            ${presetProxies.length ? `<select id="smp_proxyPreset" onchange="document.getElementById('smp_proxyVal').value=this.value" style="flex:1;min-width:80px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:4px;font-size:11px">
              <option value="">预设代理</option>
              ${presetProxies.map(p => `<option value="${p}">${p.slice(0,25)}</option>`).join('')}
            </select>` : ''}
            <input id="smp_proxyVal" placeholder="代理地址" style="flex:2;min-width:120px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:4px;font-size:11px">
          </div>
          <div style="display:flex;gap:4px">
            <button onclick="window._setProxy()" style="background:#6366f1;color:#fff;border:none;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px">🔗 绑定</button>
            <button onclick="window._testProxy()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px">🧪 测试</button>
            <span id="smp_proxyResult" style="font-size:10px;line-height:28px"></span>
          </div>
          <hr style="border-color:var(--border);margin:10px 0">
          <div style="font-size:11px;color:var(--text2);margin-bottom:4px">当前绑定</div>
          <div id="smp_proxyList" style="font-size:11px;max-height:200px;overflow-y:auto">
            ${proxies.length ? proxies.filter((p,i,a)=>a.findIndex(x=>x.account===p.account)===i).map(p =>
              `<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid var(--border);font-size:11px">
                <span>${p.platform==='xiaohongshu'?'📕':'🎵'} <strong>${p.account}</strong></span>
                <span style="color:${p.has_proxy?'#22c55e':'#8b8fa3'}">${p.proxy||'无代理'}</span>
                <span style="color:${p.login_status==='logged_in'?'#22c55e':(p.login_status==='remote'?'#8b8fa3':'#f59e0b')};font-size:9px">${p.login_status}</span>
              </div>`).join('')
            : '<span style="color:var(--text2)">无账号数据</span>'}
          </div>
        </div>
      </div>`;

    // 加载数据后刷新
    window._smsFilter();

    // 查短信
    window._smsCheckSelected = async () => {
      const sel = document.getElementById('smp_acctSelect');
      if (!sel) return;
      const opt = sel.options[sel.selectedIndex];
      if (!opt || !opt.value) { alert('请先选一个账号'); return; }
      const phone = opt.getAttribute('data-phone') || opt.value;
      const el = document.getElementById('smp_messages');
      el.innerHTML = '⏳ 查询中...';
      try {
        const r = await fetch(BASE + '/matrix/sms/test/' + encodeURIComponent(phone));
        const d = await r.json();
        if (d.status !== 'ok') { el.innerHTML = '❌ ' + (d.error || '查询失败'); return; }
        const msgs = d.messages || [];
        if (!msgs.length) { el.innerHTML = '📭 无短信记录'; return; }
        el.innerHTML = msgs.map(m =>
          `<div style="padding:3px 0;border-bottom:1px solid var(--border);font-size:11px">
            ${m.code ? '<span style="color:var(--green)">✅ '+m.code+'</span>' : '📩'}
            <span style="font-size:10px;color:var(--text2)">${(m.content||'').slice(0,80)}</span>
            <span style="color:#6366f1;font-size:9px;float:right">${m.time ? new Date(m.time).toLocaleString('zh-CN') : ''}</span>
          </div>`
        ).join('');
      } catch(e) { el.innerHTML = '❌ ' + e.message; }
    };

    // 采集昵称
    window._collectProfile = async () => {
      const sel = document.getElementById('smp_acctSelect');
      if (!sel) return;
      const opt = sel.options[sel.selectedIndex];
      if (!opt || !opt.value) { alert('请先选一个账号'); return; }
      alert('⏳ 采集 ' + opt.value + '... 请稍后查看账号管理');
      // 简单采集
      try {
        await fetch(BASE + '/matrix/collect-homepage', {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({account_ids: [opt.value]})
        });
      } catch(e) { console.error(e); }
    };

    // 选择账号自动填充代理
    document.getElementById('smp_proxyAcct').onchange = function() {
      const opt = this.options[this.selectedIndex];
      if (opt && opt.dataset.proxy) document.getElementById('smp_proxyVal').value = opt.dataset.proxy;
    };

    window._setProxy = async () => {
      const acct = document.getElementById('smp_proxyAcct').value;
      const proxy = document.getElementById('smp_proxyVal').value.trim();
      if (!acct) { alert('请选择账号'); return; }
      document.getElementById('smp_proxyResult').textContent = '⏳';
      try {
        const r = await fetch(BASE + '/matrix/proxies/' + encodeURIComponent(acct), {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ proxy }),
        });
        const d = await r.json();
        document.getElementById('smp_proxyResult').textContent = d.status === 'ok' ? '✅ 已绑定' : '❌';
        location.reload();
      } catch(e) { document.getElementById('smp_proxyResult').textContent = '❌ ' + e.message; }
    };

    window._testProxy = async () => {
      const proxy = document.getElementById('smp_proxyVal').value.trim();
      if (!proxy) { document.getElementById('smp_proxyResult').textContent = '❌ 无代理地址'; return; }
      document.getElementById('smp_proxyResult').textContent = '⏳';
      try {
        const r = await fetch(BASE + '/matrix/proxies/test', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ proxy }),
        });
        const d = await r.json();
        document.getElementById('smp_proxyResult').textContent = d.status === 'ok' ? '✅ '+ (d.ip||'') + ' ' + (d.elapsed||'') : '❌ ' + d.error;
      } catch(e) { document.getElementById('smp_proxyResult').textContent = '❌ ' + e.message; }
    };

  } catch (e) {
    container.innerHTML = `<div class="error">❌ ${e.message || e}</div>`;
  }
}

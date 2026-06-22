/**
 * SMS代理视图（已迁移）
 */
export async function loadView(container) {
  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);margin-bottom:8px">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">📱 SMS 代理管理</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
          <div>
            <div style="font-size:11px;color:var(--text2);margin-bottom:4px">预设手机号</div>
            <div id="phonePresets"><div class="loading">加载中...</div></div>
          </div>
          <div>
            <div style="font-size:11px;color:var(--text2);margin-bottom:4px">代理配置</div>
            <div id="proxyList"><div class="loading">加载中...</div></div>
          </div>
        </div>
      </div>
      <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);margin-bottom:8px">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">🔧 SMS API 配置</div>
        <div id="smsConfig"><div class="loading">加载中...</div></div>
      </div>
      <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">📊 账号概览</div>
        <div id="smsAccountsOverview"><div class="loading">加载中...</div></div>
      </div>
    </div>`;

  // 并行加载各模块
  Promise.all([
    loadPhonePresets(),
    loadProxyList(),
    loadSmsConfig(),
    loadSmsAccounts(),
  ]).catch(e => console.error('SMS view error:', e));
}

async function loadPhonePresets() {
  const el = document.getElementById('phonePresets');
  if (!el) return;
  try {
    const r = await fetch('/api/matrix/accounts');
    const d = await r.json();
    const accounts = Array.isArray(d) ? d : (d.accounts || []);
    const phones = [];
    accounts.forEach(function(a) {
      var p = a.phone || '';
      if (p && p.length >= 11 && phones.indexOf(p) === -1) {
        phones.push(p);
      }
    });
    el.innerHTML = phones.length
      ? phones.map(function(p) {
          var acct = accounts.find(function(a) { return a.phone === p; });
          return '<div style="font-size:11px;padding:3px 4px;border-bottom:1px solid var(--border)">' +
            p + (acct && acct.platform ? ' (' + acct.platform + ')' : '') + '</div>';
        }).join('')
      : '<span style="font-size:11px;color:var(--text2)">无预设</span>';
  } catch (e) {
    el.innerHTML = `<span style="color:var(--red);font-size:11px">❌ ${e.message}</span>`;
  }
}

async function loadProxyList() {
  const el = document.getElementById('proxyList');
  if (!el) return;
  try {
    const r = await fetch('/api/matrix/proxies');
    const d = await r.json();
    const proxies = d.proxies || [];
    el.innerHTML = proxies.length
      ? proxies.map(function(p) {
          var proxyInfo = p.proxy || '-';
          var statusIcon = p.login_status === 'logged_in' ? '🟢' : '🔴';
          return '<div style="font-size:11px;padding:3px 4px;border-bottom:1px solid var(--border)">' +
            statusIcon + ' ' + p.account + ' (' + p.platform + ') → ' + proxyInfo + '</div>';
        }).join('')
      : '<span style="font-size:11px;color:var(--text2)">无代理配置</span>';
  } catch (e) {
    el.innerHTML = `<span style="color:var(--red);font-size:11px">❌ ${e.message}</span>`;
  }
}

async function loadSmsConfig() {
  const el = document.getElementById('smsConfig');
  if (!el) return;
  try {
    const r = await fetch('/api/matrix/sms/config');
    const d = await r.json();
    el.innerHTML = `
      <div style="font-size:11px;display:grid;gap:4px">
        ${Object.entries(d).map(([k, v]) =>
          `<div style="display:flex;gap:8px;padding:2px 0;border-bottom:1px solid var(--border)">
            <span style="color:var(--text2);min-width:100px">${k}</span>
            <span>${typeof v === 'object' ? JSON.stringify(v) : String(v).slice(0, 60)}</span>
          </div>`
        ).join('')}
      </div>`;
  } catch (e) {
    el.innerHTML = `<span style="color:var(--red);font-size:11px">❌ ${e.message}</span>`;
  }
}

async function loadSmsAccounts() {
  const el = document.getElementById('smsAccountsOverview');
  if (!el) return;
  try {
    const r = await fetch('/api/matrix/sms/accounts');
    const d = await r.json();
    const accounts = d.accounts || [];
    const local = accounts.filter(a => a.is_local);
    const online = accounts.filter(a => a.has_cookie);
    const profiled = accounts.filter(a => a.has_profile);

    el.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;font-size:12px;text-align:center">
        <div><div style="font-size:20px;font-weight:700;color:#6366f1">${local.length}</div><div style="font-size:10px;color:var(--text2)">📱 本机</div></div>
        <div><div style="font-size:20px;font-weight:700;color:var(--green)">${accounts.length}</div><div style="font-size:10px;color:var(--text2)">📱 全部</div></div>
        <div><div style="font-size:20px;font-weight:700;color:var(--amber)">${online.length}</div><div style="font-size:10px;color:var(--text2)">🔑 已登录</div></div>
        <div><div style="font-size:20px;font-weight:700;color:var(--blue)">${profiled.length}</div><div style="font-size:10px;color:var(--text2)">📋 已采集</div></div>
      </div>`;
  } catch (e) {
    el.innerHTML = `<span style="color:var(--red);font-size:11px">❌ ${e.message}</span>`;
  }
}

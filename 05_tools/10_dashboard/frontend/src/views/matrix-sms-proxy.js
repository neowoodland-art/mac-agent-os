/**
 * 短信与代理管理（v2 自包含版 — 不依赖外部组件）
 */
export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
  try {
    const BASE = '/api';
    // 并行加载所有数据
    const [configD, proxyD] = await Promise.all([
      fetch(BASE + '/matrix/sms/config').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch(BASE + '/matrix/proxy/list').then(r => r.ok ? r.json() : null).catch(() => null),
    ]);

    function fmt(v) { return v != null && v !== '' ? v : '-'; }

    const configHtml = configD
      ? `<div style="font-size:11px;line-height:1.6">
          <div>📱 短信平台: <strong>${fmt(configD.provider || configD.platform)}</strong></div>
          <div>📊 余额: <strong>${fmt(configD.balance)}</strong></div>
          <div>📡 API: <span style="font-size:10px;color:var(--text2)">${fmt(configD.api_url || configD.endpoint)}</span></div>
         </div>`
      : '<span style="color:var(--text2);font-size:11px">⚠️ 未配置短信平台</span>';

    const proxyArr = proxyD ? (Array.isArray(proxyD) ? proxyD : (proxyD.proxies || [])) : [];
    const proxyHtml = proxyArr.length
      ? proxyArr.map(p => `<div style="padding:3px 0;font-size:11px">🔌 ${p.name || p.host || p}${p.location ? ' ('+p.location+')' : ''}</div>`).join('')
      : '<span style="color:var(--text2);font-size:11px">无代理配置</span>';

    container.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">📡 短信与代理</h2>
        <button onclick="location.reload()" style="background:transparent;color:var(--text);border:1px solid var(--border);padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px">🔄 刷新</button>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
        <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
          <div style="font-size:13px;font-weight:600;margin-bottom:8px">📱 短信接收</div>
          <div id="smsConfigPanel">${configHtml}</div>
          <hr style="border-color:var(--border);margin:8px 0">
          <div style="font-size:11px;color:var(--text2);margin-bottom:4px">选择账号</div>
          <div style="display:flex;gap:4px">
            <input id="smsPhone" placeholder="输入手机号" style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px;border-radius:5px;font-size:12px">
            <button onclick="window._smsCheck()" style="background:var(--primary);color:#fff;border:none;padding:5px 12px;border-radius:5px;cursor:pointer;font-size:12px">📥 查短信</button>
          </div>
          <div id="smsResult" style="font-size:11px;margin-top:4px"></div>
        </div>
        <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
          <div style="font-size:13px;font-weight:600;margin-bottom:8px">🖥️ 代理配置</div>
          <div id="proxyList">${proxyHtml}</div>
        </div>
      </div>`;

    // 查短信功能
    window._smsCheck = async () => {
      const phone = document.getElementById('smsPhone')?.value?.trim();
      if (!phone) { alert('请输入手机号'); return; }
      const el = document.getElementById('smsResult');
      el.innerHTML = '⏳ 查询中...';
      try {
        const r = await fetch(BASE + '/matrix/sms/messages?phone=' + encodeURIComponent(phone));
        if (!r.ok) { el.innerHTML = '❌ 查询失败'; return; }
        const d = await r.json();
        const msgs = d.messages || d.data || [];
        if (!msgs.length) { el.innerHTML = '📭 无短信记录'; return; }
        el.innerHTML = msgs.slice(0, 10).map(m =>
          `<div style="padding:2px 0;border-bottom:1px solid var(--border);font-size:10px">
            ${m.time || m.created_at ? new Date(m.time || m.created_at).toLocaleString('zh-CN') : ''}
            <strong>${m.code || m.content || '-'}</strong>
          </div>`
        ).join('');
      } catch(e) { el.innerHTML = '❌ ' + e.message; }
    };

  } catch (e) {
    container.innerHTML = `<div class="error">❌ ${e.message || e}</div>`;
  }
}

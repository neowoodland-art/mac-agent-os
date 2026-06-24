/**
 * 短信与代理管理（v3 — 使用旧代码确认有效的API路径）
 */
export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
  try {
    const BASE = '/api';

    // 三个并行请求
    const [configR, proxyR, smsR] = await Promise.all([
      fetch(BASE + '/matrix/sms/config').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch(BASE + '/matrix/proxies').then(r => r.ok ? r.json() : null).catch(() => null),  // 注意: proxies 带 s
      fetch(BASE + '/matrix/sms/accounts').then(r => r.ok ? r.json() : null).catch(() => null),
    ]);

    const config = configR || {};
    const proxiesObj = proxyR || { proxies: [] };
    const proxies = proxiesObj.proxies || [];
    const accounts = smsR?.accounts || [];

    // SMS 配置面板
    const configHtml = config.base_url
      ? `<div style="font-size:11px;line-height:1.6">
          <div><span style="color:var(--text2)">API:</span> <code>${(config.base_url||'').slice(0,40)}</code></div>
          <div><span style="color:var(--text2)">当前手机号:</span> <strong style="color:var(--green)">${config.phone||'-'}</strong></div>
          <div><span style="color:var(--text2)">Key:</span> <code>${config.api_key||'-'}</code> | 轮询 ${config.poll_interval||3}s</div>
         </div>`
      : '<span style="color:var(--text2);font-size:11px">⚠️ 短信平台未配置</span>';

    // 代理列表
    const proxyHtml = proxies.length
      ? proxies.map(p => `<div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:6px;font-size:12px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div><strong>${p.account}</strong> <span style="color:var(--text2);font-size:10px">${p.platform}</span>
              <span style="font-size:10px;margin-left:6px;color:${p.login_status==='logged_in'?'#22c55e':(p.login_status==='remote'?'#8b8fa3':'#f59e0b')}">${p.login_status}</span>
            </div>
            <div><span style="color:${p.has_proxy?'#22c55e':'#8b8fa3'};font-size:10px">${p.proxy||'无代理'}</span></div>
          </div>
          <div style="margin-top:4px;display:flex;gap:4px;align-items:center">
            <input id="proxy_${p.account}" placeholder="绑定代理地址" value="${p.proxy||''}" style="flex:1;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
            <button onclick="window._setProxy('${p.account}')" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">绑定</button>
            <button onclick="window._testProxy('${p.account}')" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">测试</button>
            <span id="proxyResult_${p.account}" style="font-size:10px"></span>
          </div>
        </div>`).join('')
      : '<div style="color:var(--text2);font-size:12px">无本地账号</div>';

    // 账号选项（供查短信用）
    const accountOptions = accounts.map(a =>
      `<option value="${a.id}" data-phone="${a.phone||''}">${a.platform==='xiaohongshu'?'📕':'🎵'} ${a.nickname||a.id} ${a.owner_machine||(a.is_local?'本机':'远程')} (${a.phone||''})</option>`
    ).join('');

    container.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">📡 短信与代理</h2>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
        <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
          <div style="font-size:13px;font-weight:600;margin-bottom:8px">📱 短信接收</div>
          <div>${configHtml}</div>
          <hr style="border-color:var(--border);margin:8px 0">
          <div style="font-size:11px;color:var(--text2);margin-bottom:4px">搜索/选择账号</div>
          <div style="display:flex;gap:4px;flex-wrap:wrap">
            <input id="smsSearch" placeholder="🔍 输入手机号/昵称过滤..." oninput="_smsFilter()"
              style="flex:1;min-width:120px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
            <select id="smsAccountSelect" size="4" style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px;border-radius:4px;font-size:11px">
              <option value="">— 选择账号 —</option>
              ${accountOptions}
            </select>
            <button onclick="window._smsQuery()" style="background:var(--primary);color:#fff;border:none;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:12px">📥 查短信</button>
          </div>
          <div style="font-size:10px;color:var(--text2);margin-top:2px">选中后点"查短信"查看验证码</div>
          <div id="smsResult" style="font-size:11px;margin-top:4px;max-height:250px;overflow-y:auto"></div>
        </div>
        <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
          <div style="font-size:13px;font-weight:600;margin-bottom:8px">🖥️ 代理配置</div>
          <div id="proxyList" style="max-height:400px;overflow-y:auto">${proxyHtml}</div>
        </div>
      </div>`;

    // 账号搜索过滤
    window._smsFilter = () => {
      const q = (document.getElementById('smsSearch')?.value || '').toLowerCase();
      const sel = document.getElementById('smsAccountSelect');
      if (!sel) return;
      for (let i = 0; i < sel.options.length; i++) {
        const opt = sel.options[i];
        const txt = opt.text.toLowerCase();
        const phone = opt.dataset?.phone || '';
        sel.options[i].style.display = (!q || txt.includes(q) || phone.includes(q)) ? '' : 'none';
      }
    };

    // 查短信
    window._smsQuery = async () => {
      const sel = document.getElementById('smsAccountSelect');
      if (!sel) { alert('页面未就绪'); return; }
      const idx = sel.selectedIndex;
      if (idx < 1) { alert('请先选择一个账号'); return; }
      const opt = sel.options[idx];
      const phone = opt.dataset?.phone || opt.value || '';
      if (!phone) { alert('该账号无手机号'); return; }
      const el = document.getElementById('smsResult');
      el.innerHTML = '⏳ 查询中...';
      try {
        const r = await fetch(BASE + '/matrix/sms/test/' + encodeURIComponent(phone));
        const d = await r.json();
        if (d.status !== 'ok') { el.innerHTML = '❌ ' + (d.error || '查询失败'); return; }
        const msgs = d.messages || [];
        if (!msgs.length) { el.innerHTML = '📭 无短信记录'; return; }
        el.innerHTML = msgs.map(m =>
          `<div style="padding:3px 0;border-bottom:1px solid var(--border);font-size:11px">
            ${m.code ? '<span style="color:var(--green)">✅ 验证码 '+m.code+'</span>' : '📩'}
            <span style="font-size:10px;color:var(--text2)">${(m.content||'').slice(0,60)}</span>
            <span style="color:#6366f1;font-size:9px;float:right">${m.time ? new Date(m.time).toLocaleString('zh-CN') : ''}</span>
          </div>`
        ).join('');
      } catch(e) { el.innerHTML = '❌ ' + e.message; }
    };

    // 绑定代理
    window._setProxy = async (account) => {
      const input = document.getElementById('proxy_' + account);
      const proxy = input?.value || '';
      const el = document.getElementById('proxyResult_' + account);
      if (el) el.innerHTML = '⏳';
      try {
        const r = await fetch(BASE + '/matrix/proxies/' + encodeURIComponent(account), {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ proxy }),
        });
        const d = await r.json();
        if (el) el.innerHTML = d.status === 'ok' ? '✅ 已绑定' : '❌';
        // 刷新代理列表
        const pr = await fetch(BASE + '/matrix/proxies').then(r => r.ok ? r.json() : null);
        const list = document.getElementById('proxyList');
        if (pr && list) {
          list.innerHTML = pr.proxies.map(p =>
            `<div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:6px;font-size:12px">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <div><strong>${p.account}</strong> <span style="color:var(--text2);font-size:10px">${p.platform}</span>
                  <span style="font-size:10px;margin-left:6px;color:${p.login_status==='logged_in'?'#22c55e':(p.login_status==='remote'?'#8b8fa3':'#f59e0b')}">${p.login_status}</span>
                </div>
                <div><span style="color:${p.has_proxy?'#22c55e':'#8b8fa3'};font-size:10px">${p.proxy||'无代理'}</span></div>
              </div>
            </div>`
          ).join('');
        }
      } catch(e) { if (el) el.innerHTML = '❌'; }
    };

    // 测试代理
    window._testProxy = async (account) => {
      const el = document.getElementById('proxyResult_' + account);
      if (el) el.innerHTML = '⏳';
      try {
        const r = await fetch(BASE + '/matrix/proxies');
        const d = await r.json();
        const p = (d.proxies||[]).find(x => x.account === account);
        if (!p || !p.proxy) { if (el) el.innerHTML = '❌ 无代理'; return; }
        const r2 = await fetch(BASE + '/matrix/proxies/test', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ proxy: p.proxy }),
        });
        const d2 = await r2.json();
        if (el) el.innerHTML = d2.status === 'ok' ? `✅ ${d2.ip||'?'} | ${d2.elapsed||'?'}` : '❌ '+d2.error;
      } catch(e) { if (el) el.innerHTML = '❌ ' + e.message; }
    };

  } catch (e) {
    container.innerHTML = `<div class="error">❌ ${e.message || e}</div>`;
  }
}

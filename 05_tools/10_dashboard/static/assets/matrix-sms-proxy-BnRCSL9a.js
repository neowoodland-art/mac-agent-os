async function e(e){e.innerHTML=`
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
    </div>`,Promise.all([t(),n(),r(),i()]).catch(e=>console.error(`SMS view error:`,e))}async function t(){let e=document.getElementById(`phonePresets`);if(e)try{let t=(await(await fetch(`/api/matrix/sms/presets`)).json()).presets||[];e.innerHTML=t.length?t.map(e=>`<div style="font-size:11px;padding:3px 4px;border-bottom:1px solid var(--border)">
          ${e.phone||e} ${e.platform?`(`+e.platform+`)`:``}
        </div>`).join(``):`<span style="font-size:11px;color:var(--text2)">无预设</span>`}catch(t){e.innerHTML=`<span style="color:var(--red);font-size:11px">❌ ${t.message}</span>`}}async function n(){let e=document.getElementById(`proxyList`);if(e)try{let t=(await(await fetch(`/api/matrix/sms/proxies`)).json()).proxies||[];e.innerHTML=t.length?t.map(e=>`<div style="font-size:11px;padding:3px 4px;border-bottom:1px solid var(--border)">
          ${e.name||e.host||e} ${e.status===`online`?`🟢`:`🔴`}
        </div>`).join(``):`<span style="font-size:11px;color:var(--text2)">无代理</span>`}catch(t){e.innerHTML=`<span style="color:var(--red);font-size:11px">❌ ${t.message}</span>`}}async function r(){let e=document.getElementById(`smsConfig`);if(e)try{let t=await(await fetch(`/api/matrix/sms/config`)).json();e.innerHTML=`
      <div style="font-size:11px;display:grid;gap:4px">
        ${Object.entries(t).map(([e,t])=>`<div style="display:flex;gap:8px;padding:2px 0;border-bottom:1px solid var(--border)">
            <span style="color:var(--text2);min-width:100px">${e}</span>
            <span>${typeof t==`object`?JSON.stringify(t):String(t).slice(0,60)}</span>
          </div>`).join(``)}
      </div>`}catch(t){e.innerHTML=`<span style="color:var(--red);font-size:11px">❌ ${t.message}</span>`}}async function i(){let e=document.getElementById(`smsAccountsOverview`);if(e)try{let t=(await(await fetch(`/api/matrix/sms/accounts`)).json()).accounts||[],n=t.filter(e=>e.is_local),r=t.filter(e=>e.has_cookie),i=t.filter(e=>e.has_profile);e.innerHTML=`
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;font-size:12px;text-align:center">
        <div><div style="font-size:20px;font-weight:700;color:#6366f1">${n.length}</div><div style="font-size:10px;color:var(--text2)">📱 本机</div></div>
        <div><div style="font-size:20px;font-weight:700;color:var(--green)">${t.length}</div><div style="font-size:10px;color:var(--text2)">📱 全部</div></div>
        <div><div style="font-size:20px;font-weight:700;color:var(--amber)">${r.length}</div><div style="font-size:10px;color:var(--text2)">🔑 已登录</div></div>
        <div><div style="font-size:20px;font-weight:700;color:var(--blue)">${i.length}</div><div style="font-size:10px;color:var(--text2)">📋 已采集</div></div>
      </div>`}catch(t){e.innerHTML=`<span style="color:var(--red);font-size:11px">❌ ${t.message}</span>`}}export{e as loadView};
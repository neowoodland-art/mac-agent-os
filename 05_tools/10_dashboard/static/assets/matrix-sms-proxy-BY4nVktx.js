async function e(e){e.innerHTML=`<div class="loading">⏳ 加载中...</div>`;try{let[t,n,r]=await Promise.all([fetch(`/api/matrix/sms/config`).then(e=>e.ok?e.json():null).catch(()=>null),fetch(`/api/matrix/proxies`).then(e=>e.ok?e.json():null).catch(()=>null),fetch(`/api/matrix/sms/accounts`).then(e=>e.ok?e.json():null).catch(()=>null)]),i=t||{},a=(n||{proxies:[]}).proxies||[],o=r?.accounts||[],s=i.base_url?`<div style="font-size:11px;line-height:1.6">
          <div><span style="color:var(--text2)">API:</span> <code>${(i.base_url||``).slice(0,40)}</code></div>
          <div><span style="color:var(--text2)">当前手机号:</span> <strong style="color:var(--green)">${i.phone||`-`}</strong></div>
          <div><span style="color:var(--text2)">Key:</span> <code>${i.api_key||`-`}</code> | 轮询 ${i.poll_interval||3}s</div>
         </div>`:`<span style="color:var(--text2);font-size:11px">⚠️ 短信平台未配置</span>`,c=a.length?a.map(e=>`<div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:6px;font-size:12px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div><strong>${e.account}</strong> <span style="color:var(--text2);font-size:10px">${e.platform}</span>
              <span style="font-size:10px;margin-left:6px;color:${e.login_status===`logged_in`?`#22c55e`:e.login_status===`remote`?`#8b8fa3`:`#f59e0b`}">${e.login_status}</span>
            </div>
            <div><span style="color:${e.has_proxy?`#22c55e`:`#8b8fa3`};font-size:10px">${e.proxy||`无代理`}</span></div>
          </div>
          <div style="margin-top:4px;display:flex;gap:4px;align-items:center">
            <input id="proxy_${e.account}" placeholder="绑定代理地址" value="${e.proxy||``}" style="flex:1;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
            <button onclick="window._setProxy('${e.account}')" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">绑定</button>
            <button onclick="window._testProxy('${e.account}')" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">测试</button>
            <span id="proxyResult_${e.account}" style="font-size:10px"></span>
          </div>
        </div>`).join(``):`<div style="color:var(--text2);font-size:12px">无本地账号</div>`;e.innerHTML=`
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">📡 短信与代理</h2>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
        <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
          <div style="font-size:13px;font-weight:600;margin-bottom:8px">📱 短信接收</div>
          <div>${s}</div>
          <hr style="border-color:var(--border);margin:8px 0">
          <div style="font-size:11px;color:var(--text2);margin-bottom:4px">选择账号</div>
          <div style="display:flex;gap:4px;flex-wrap:wrap">
            <select id="smsAccountSelect" style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:4px;font-size:11px">
              <option value="">— 选择账号 —</option>
              ${o.map(e=>`<option value="${e.id}" data-phone="${e.phone||``}">${e.platform===`xiaohongshu`?`📕`:`🎵`} ${e.nickname||e.id} ${e.owner_machine||(e.is_local?`本机`:`远程`)} (${e.phone||``})</option>`).join(``)}
            </select>
            <button onclick="window._smsQuery()" style="background:var(--primary);color:#fff;border:none;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:12px">📥 查短信</button>
          </div>
          <div id="smsResult" style="font-size:11px;margin-top:4px;max-height:250px;overflow-y:auto"></div>
        </div>
        <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
          <div style="font-size:13px;font-weight:600;margin-bottom:8px">🖥️ 代理配置</div>
          <div id="proxyList" style="max-height:400px;overflow-y:auto">${c}</div>
        </div>
      </div>`,window._smsQuery=async()=>{let e=document.getElementById(`smsAccountSelect`),t=(e?.options[e.selectedIndex])?.dataset?.phone||e?.value||``;if(!t){alert(`请选择账号`);return}let n=document.getElementById(`smsResult`);n.innerHTML=`⏳ 查询中...`;try{let e=await(await fetch(`/api/matrix/sms/test/`+encodeURIComponent(t))).json();if(e.status!==`ok`){n.innerHTML=`❌ `+(e.error||`查询失败`);return}let r=e.messages||[];if(!r.length){n.innerHTML=`📭 无短信记录`;return}n.innerHTML=r.map(e=>`<div style="padding:3px 0;border-bottom:1px solid var(--border);font-size:11px">
            ${e.code?`<span style="color:var(--green)">✅ 验证码 `+e.code+`</span>`:`📩`}
            <span style="font-size:10px;color:var(--text2)">${(e.content||``).slice(0,60)}</span>
            <span style="color:#6366f1;font-size:9px;float:right">${e.time?new Date(e.time).toLocaleString(`zh-CN`):``}</span>
          </div>`).join(``)}catch(e){n.innerHTML=`❌ `+e.message}},window._setProxy=async e=>{let t=document.getElementById(`proxy_`+e)?.value||``,n=document.getElementById(`proxyResult_`+e);n&&(n.innerHTML=`⏳`);try{let r=await(await fetch(`/api/matrix/proxies/`+encodeURIComponent(e),{method:`PUT`,headers:{"Content-Type":`application/json`},body:JSON.stringify({proxy:t})})).json();n&&(n.innerHTML=r.status===`ok`?`✅ 已绑定`:`❌`);let i=await fetch(`/api/matrix/proxies`).then(e=>e.ok?e.json():null),a=document.getElementById(`proxyList`);i&&a&&(a.innerHTML=i.proxies.map(e=>`<div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:6px;font-size:12px">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <div><strong>${e.account}</strong> <span style="color:var(--text2);font-size:10px">${e.platform}</span>
                  <span style="font-size:10px;margin-left:6px;color:${e.login_status===`logged_in`?`#22c55e`:e.login_status===`remote`?`#8b8fa3`:`#f59e0b`}">${e.login_status}</span>
                </div>
                <div><span style="color:${e.has_proxy?`#22c55e`:`#8b8fa3`};font-size:10px">${e.proxy||`无代理`}</span></div>
              </div>
            </div>`).join(``))}catch{n&&(n.innerHTML=`❌`)}},window._testProxy=async e=>{let t=document.getElementById(`proxyResult_`+e);t&&(t.innerHTML=`⏳`);try{let n=((await(await fetch(`/api/matrix/proxies`)).json()).proxies||[]).find(t=>t.account===e);if(!n||!n.proxy){t&&(t.innerHTML=`❌ 无代理`);return}let r=await(await fetch(`/api/matrix/proxies/test`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({proxy:n.proxy})})).json();t&&(t.innerHTML=r.status===`ok`?`✅ ${r.ip||`?`} | ${r.elapsed||`?`}`:`❌ `+r.error)}catch(e){t&&(t.innerHTML=`❌ `+e.message)}}}catch(t){e.innerHTML=`<div class="error">❌ ${t.message||t}</div>`}}export{e as loadView};
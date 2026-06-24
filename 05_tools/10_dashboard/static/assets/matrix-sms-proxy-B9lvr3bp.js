async function e(e){e.innerHTML=`<div class="loading">⏳ 加载中...</div>`,window._smsFilter=()=>{let e=document.getElementById(`smp_acctSearch`),t=document.getElementById(`smp_acctSelect`);if(!e||!t)return;if(!window._smsAccountOptions){t.innerHTML=`<option>⏳ 加载中...</option>`,t.style.display=`block`;return}let n=window._smsAccountOptions,r=e.value.trim().toLowerCase(),i=[];if(i=r?n.filter(e=>{let t=(e.phone||``).toLowerCase(),n=(e.nickname||``).toLowerCase();return t.includes(r)||n.includes(r)||(e.id||``).toLowerCase().includes(r)}):n.slice(0,30),t.innerHTML=`<option value="">— 选择账号 —</option>`+i.map(e=>`<option value="`+e.id+`" data-phone="`+(e.phone||``)+`" data-nick="`+(e.nickname||``)+`">`+((e.platform===`xiaohongshu`?`📕`:`🎵`)+` `+e.nickname+` `+(e.owner_machine||(e.is_local?`本机`:`远程`))+` (`+e.phone+`)`)+`</option>`).join(``),r.length>=4){let r=n.find(t=>t.phone===e.value.trim());if(r){t.value=r.id,window._smsSelect(),t.style.display=`none`;return}}t.style.display=`block`,t.size=Math.min(i.length+1,6),t.selectedIndex=0},window._smsSelect=()=>{let e=document.getElementById(`smp_acctSelect`),t=document.getElementById(`smp_selectedAcct`),n=document.getElementById(`smp_acctSearch`);if(!e||!t)return;let r=e.options[e.selectedIndex];if(!r||!r.value){t.innerHTML=``;return}let i=r.getAttribute(`data-nick`)||r.value,a=r.getAttribute(`data-phone`)||``;t.innerHTML=`<span style="color:var(--green)">`+i+`</span> <span style="color:var(--text2)">(`+a+`)</span>`,n&&(n.value=a||r.textContent.trim(),document.getElementById(`smp_acctSelect`).style.display=`none`)};try{let[t,n]=await Promise.all([fetch(`/api/matrix/sms/accounts`).then(e=>e.ok?e.json():{accounts:[]}).catch(()=>({accounts:[]})),fetch(`/api/matrix/proxies`).then(e=>e.ok?e.json():{proxies:[]}).catch(()=>({proxies:[]}))]),r=t.accounts||[],i=n.proxies||[];window._smsAccountOptions=r;let a=i.filter((e,t,n)=>n.findIndex(t=>t.account===e.account)===t),o=[...new Set(i.map(e=>e.proxy).filter(Boolean))];e.innerHTML=`
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
              ${a.map(e=>`<option value="${e.account}" data-proxy="${e.proxy||``}">${e.platform===`xiaohongshu`?`📕`:`🎵`} ${e.account}</option>`).join(``)}
            </select>
            ${o.length?`<select id="smp_proxyPreset" onchange="document.getElementById('smp_proxyVal').value=this.value" style="flex:1;min-width:80px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:4px;font-size:11px">
              <option value="">预设代理</option>
              ${o.map(e=>`<option value="${e}">${e.slice(0,25)}</option>`).join(``)}
            </select>`:``}
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
            ${i.length?i.filter((e,t,n)=>n.findIndex(t=>t.account===e.account)===t).map(e=>`<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid var(--border);font-size:11px">
                <span>${e.platform===`xiaohongshu`?`📕`:`🎵`} <strong>${e.account}</strong></span>
                <span style="color:${e.has_proxy?`#22c55e`:`#8b8fa3`}">${e.proxy||`无代理`}</span>
                <span style="color:${e.login_status===`logged_in`?`#22c55e`:e.login_status===`remote`?`#8b8fa3`:`#f59e0b`};font-size:9px">${e.login_status}</span>
              </div>`).join(``):`<span style="color:var(--text2)">无账号数据</span>`}
          </div>
        </div>
      </div>`,window._smsFilter(),window._smsCheckSelected=async()=>{let e=document.getElementById(`smp_acctSelect`);if(!e)return;let t=e.options[e.selectedIndex];if(!t||!t.value){alert(`请先选一个账号`);return}let n=t.getAttribute(`data-phone`)||t.value,r=document.getElementById(`smp_messages`);r.innerHTML=`⏳ 查询中...`;try{let e=await(await fetch(`/api/matrix/sms/test/`+encodeURIComponent(n))).json();if(e.status!==`ok`){r.innerHTML=`❌ `+(e.error||`查询失败`);return}let t=e.messages||[];if(!t.length){r.innerHTML=`📭 无短信记录`;return}r.innerHTML=t.map(e=>`<div style="padding:3px 0;border-bottom:1px solid var(--border);font-size:11px">
            ${e.code?`<span style="color:var(--green)">✅ `+e.code+`</span>`:`📩`}
            <span style="font-size:10px;color:var(--text2)">${(e.content||``).slice(0,80)}</span>
            <span style="color:#6366f1;font-size:9px;float:right">${e.time?new Date(e.time).toLocaleString(`zh-CN`):``}</span>
          </div>`).join(``)}catch(e){r.innerHTML=`❌ `+e.message}},window._collectProfile=async()=>{let e=document.getElementById(`smp_acctSelect`);if(!e)return;let t=e.options[e.selectedIndex];if(!t||!t.value){alert(`请先选一个账号`);return}alert(`⏳ 采集 `+t.value+`... 请稍后查看账号管理`);try{await fetch(`/api/matrix/collect-homepage`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({account_ids:[t.value]})})}catch(e){console.error(e)}},document.getElementById(`smp_proxyAcct`).onchange=function(){let e=this.options[this.selectedIndex];e&&e.dataset.proxy&&(document.getElementById(`smp_proxyVal`).value=e.dataset.proxy)},window._setProxy=async()=>{let e=document.getElementById(`smp_proxyAcct`).value,t=document.getElementById(`smp_proxyVal`).value.trim();if(!e){alert(`请选择账号`);return}document.getElementById(`smp_proxyResult`).textContent=`⏳`;try{let n=await(await fetch(`/api/matrix/proxies/`+encodeURIComponent(e),{method:`PUT`,headers:{"Content-Type":`application/json`},body:JSON.stringify({proxy:t})})).json();document.getElementById(`smp_proxyResult`).textContent=n.status===`ok`?`✅ 已绑定`:`❌`,location.reload()}catch(e){document.getElementById(`smp_proxyResult`).textContent=`❌ `+e.message}},window._testProxy=async()=>{let e=document.getElementById(`smp_proxyVal`).value.trim();if(!e){document.getElementById(`smp_proxyResult`).textContent=`❌ 无代理地址`;return}document.getElementById(`smp_proxyResult`).textContent=`⏳`;try{let t=await(await fetch(`/api/matrix/proxies/test`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({proxy:e})})).json();document.getElementById(`smp_proxyResult`).textContent=t.status===`ok`?`✅ `+(t.ip||``)+` `+(t.elapsed||``):`❌ `+t.error}catch(e){document.getElementById(`smp_proxyResult`).textContent=`❌ `+e.message}}}catch(t){e.innerHTML=`<div class="error">❌ ${t.message||t}</div>`}}export{e as loadView};
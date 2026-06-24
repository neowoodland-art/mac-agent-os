async function e(e){e.innerHTML=`<div class="loading">⏳ 加载中...</div>`;try{let[t,n]=await Promise.all([fetch(`/api/matrix/sms/config`).then(e=>e.ok?e.json():null).catch(()=>null),fetch(`/api/matrix/proxy/list`).then(e=>e.ok?e.json():null).catch(()=>null)]);function r(e){return e!=null&&e!==``?e:`-`}let i=t?`<div style="font-size:11px;line-height:1.6">
          <div>📱 短信平台: <strong>${r(t.provider||t.platform)}</strong></div>
          <div>📊 余额: <strong>${r(t.balance)}</strong></div>
          <div>📡 API: <span style="font-size:10px;color:var(--text2)">${r(t.api_url||t.endpoint)}</span></div>
         </div>`:`<span style="color:var(--text2);font-size:11px">⚠️ 未配置短信平台</span>`,a=n?Array.isArray(n)?n:n.proxies||[]:[];e.innerHTML=`
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">📡 短信与代理</h2>
        <button onclick="location.reload()" style="background:transparent;color:var(--text);border:1px solid var(--border);padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px">🔄 刷新</button>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
        <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
          <div style="font-size:13px;font-weight:600;margin-bottom:8px">📱 短信接收</div>
          <div id="smsConfigPanel">${i}</div>
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
          <div id="proxyList">${a.length?a.map(e=>`<div style="padding:3px 0;font-size:11px">🔌 ${e.name||e.host||e}${e.location?` (`+e.location+`)`:``}</div>`).join(``):`<span style="color:var(--text2);font-size:11px">无代理配置</span>`}</div>
        </div>
      </div>`,window._smsCheck=async()=>{let e=document.getElementById(`smsPhone`)?.value?.trim();if(!e){alert(`请输入手机号`);return}let t=document.getElementById(`smsResult`);t.innerHTML=`⏳ 查询中...`;try{let n=await fetch(`/api/matrix/sms/messages?phone=`+encodeURIComponent(e));if(!n.ok){t.innerHTML=`❌ 查询失败`;return}let r=await n.json(),i=r.messages||r.data||[];if(!i.length){t.innerHTML=`📭 无短信记录`;return}t.innerHTML=i.slice(0,10).map(e=>`<div style="padding:2px 0;border-bottom:1px solid var(--border);font-size:10px">
            ${e.time||e.created_at?new Date(e.time||e.created_at).toLocaleString(`zh-CN`):``}
            <strong>${e.code||e.content||`-`}</strong>
          </div>`).join(``)}catch(e){t.innerHTML=`❌ `+e.message}}}catch(t){e.innerHTML=`<div class="error">❌ ${t.message||t}</div>`}}export{e as loadView};
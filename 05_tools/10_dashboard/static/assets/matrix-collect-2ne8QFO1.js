import{t as e}from"./index-DmH7H8vv.js";import{t}from"./account-selector-DBZWFo9Z.js";var n=null;async function r(t){let n=t.id||`collect`;t.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">📡 登录与信息采集 <span style="font-size:10px;color:var(--text2);font-weight:400">登录+采集一体化</span></div>
        <div id="acctList_${n}" style="margin-bottom:6px"><div class="loading">⏳ 加载账号列表...</div></div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
          <span id="status_${n}" style="font-size:10px;color:var(--text2)">⏸️ 空闲</span>
          <button onclick="window._collectLogin()" style="background:#6366f1;color:#fff;border:none;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600">🔑 登录选中</button>
          <button onclick="window._collectExec()" style="background:var(--primary);color:#fff;border:none;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600">📥 采集选中</button>
          <button onclick="window._collectAll()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">📋 采集全部</button>
          <button onclick="window._cancelCollect()" style="background:rgba(220,38,38,.1);color:var(--red);border:1px solid rgba(220,38,38,.3);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">⏹ 停止</button>
          <span id="selCount_${n}" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>
        <div id="log_${n}" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:250px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`,await i(n),a(n);try{(await e(`/matrix/collect-homepage/status`)).running&&(document.getElementById(`status_${n}`).innerHTML=`<span style="color:var(--green)">🟢 采集中</span>`)}catch{}}async function i(r){let i=document.getElementById(`acctList_${r}`);if(i)try{let[r,a]=await Promise.all([e(`/matrix/accounts`),e(`/matrix/homepage-info`).catch(()=>({results:[]}))]),o=Array.isArray(r)?r.filter(e=>e.enabled!==!1):(r.accounts||[]).filter(e=>e.enabled!==!1),s={};(a.results||[]).forEach(e=>{e.identity_dir&&(s[e.identity_dir]=e),e.phone&&(s[e.phone]=e)}),n=t(i,{accounts:o,hpIndex:s,checkAll:!1,height:`300px`,showBlueprint:!1})}catch(e){i.innerHTML=`<div class="error">❌ 加载失败: ${e.message}</div>`}}function a(t){window._collectGlobals||(window._collectGlobals=!0,window._collectLogin=async function(){let r=n?.getSelected()||[];if(!r.length){alert(`请先选择要登录的账号`);return}let i=document.getElementById(`log_${t}`);i&&(i.textContent=`🔑 登录 `+r.length+` 个账号...
`);for(let t of r)try{let n=await e(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`login`,accounts:[t.id]})});i&&(i.textContent+=t.id+`: `+(n.status||`OK`)+`
`)}catch(e){i&&(i.textContent+=t.id+`: ❌ `+e.message+`
`)}},window._collectExec=async function(){let r=n?.getSelected()||[];if(!r.length){alert(`请先选择要采集的账号`);return}let i=document.getElementById(`log_${t}`),a=document.getElementById(`status_${t}`);i&&(i.textContent=`📥 采集 `+r.length+` 个账号...
`);for(let t of r)try{let n=await e(`/matrix/collect-homepage`,{method:`POST`,body:JSON.stringify({account_id:t.id})});a&&(a.innerHTML=`<span style="color:var(--green)">🟢 采集中</span>`),i&&(i.textContent+=t.id+`: `+(n.status||`OK`)+` 机器:`+(n.machine||t.machine)+`
`)}catch(e){i&&(i.textContent+=t.id+`: ❌ `+e.message+`
`)}},window._collectAll=async function(){let e=n?.getSelected()||[];if(!e.length){alert(`没有可采集的账号`);return}confirm(`采集全部 `+e.length+` 个账号？`)&&await window._collectExec()},window._cancelCollect=async function(){let n=document.getElementById(`log_${t}`);n&&(n.textContent+=`⏹ 发送停止请求...
`);try{await e(`/matrix/collect-homepage/cancel`,{method:`POST`}),n&&(n.textContent+=`✅ 已发送停止命令
`)}catch(e){n&&(n.textContent+=`❌ `+e.message+`
`)}})}export{r as loadView};
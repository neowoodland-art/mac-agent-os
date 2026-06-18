import{t as e}from"./index-ruflvycv.js";import{t}from"./account-selector-DBZWFo9Z.js";var n=null;async function r(r){let a=r.id||`ops`;r.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border);margin-bottom:8px">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">🖥️ 联邦指挥台 <span style="font-size:10px;color:var(--text2);font-weight:400">选机器 → 选操作 → 选账号 → 批量执行</span></div>
        <div id="acctList_${a}" style="margin-bottom:6px"><div class="loading">⏳ 加载账号列表...</div></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:11px;color:var(--text2)">操作:
            <select id="opsType_${a}" onchange="window._opsTypeChange()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
              <option value="nurture">🏃 养号</option>
              <option value="collect">📡 采集</option>
              <option value="login">🔑 登录</option>
              <option value="logout">🔒 登出</option>
            </select>
          </label>
          <label style="font-size:11px;color:var(--text2)" id="roundsLabel_${a}">轮数:
            <select id="rounds_${a}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
              <option value="1">1</option><option value="5">5</option>
              <option value="10" selected>10</option><option value="20">20</option>
            </select>
          </label>
          <button onclick="window._opsExec()" style="background:#22c55e;color:#000;border:none;padding:5px 16px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 批量执行</button>
          <span id="selCount_${a}" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>
        <div id="log_${a}" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:300px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;try{let r=await e(`/matrix/accounts`),i=Array.isArray(r)?r:r.accounts||[],o=document.getElementById(`acctList_${a}`);o&&(n=t(o,{accounts:i,checkAll:!0,height:`300px`}))}catch(e){let t=document.getElementById(`acctList_${a}`);t&&(t.innerHTML=`<div class="error">❌ ${e.message}</div>`)}i(a)}function i(t){window._opsGlobals||(window._opsGlobals=!0,window._opsTypeChange=function(){let e=document.getElementById(`opsType_${t}`)?.value,n=document.getElementById(`roundsLabel_${t}`);n&&(n.style.display=e===`nurture`?``:`none`)},window._opsExec=async function(){let r=n?.getSelected()||[];if(!r.length){alert(`请先选择账号`);return}let i=document.getElementById(`opsType_${t}`)?.value||`nurture`,a=parseInt(document.getElementById(`rounds_${t}`)?.value||`10`),o=document.getElementById(`log_${t}`);o.textContent=`🚀 提交 `+i+` 任务: `+r.length+` 个账号...
`;try{let t=(await e(`/ops/run`,{method:`POST`,body:JSON.stringify({type:i,accounts:r,params:i===`nurture`?{rounds:a}:{}})})).results||[];o.textContent+=`📋 结果 (`+t.length+` 个):
`,t.forEach(e=>{o.textContent+=`  ${e.status===`started`||e.status===`ok`?`✅`:`❌`} ${e.account_id||e.target}: ${e.status}\n`})}catch(e){o.textContent+=`❌ `+e.message+`
`}})}export{r as loadView};
import{n as e,t}from"./index-CMoGILrH.js";import{t as n}from"./account-selector-BssNMpad.js";var r=null;async function i(i){let a=i.id||`nurture`,o=await t(`/matrix/accounts`),s=Array.isArray(o)?o:o.accounts||[];i.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">🌱 养号执行 <span style="font-size:10px;color:var(--text2);font-weight:400">预检 → 窗口定位 → 执行 → 验证</span></div>
        <div id="acctList_${a}" style="margin-bottom:6px"></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:11px;color:var(--text2)">轮数:
            <select id="ndRounds" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="1">1 测试</option><option value="5">5</option>
              <option value="10" selected>10 默认</option>
              <option value="20">20</option><option value="30">30</option>
            </select>
          </label>
          <label style="font-size:11px;color:var(--text2)">蓝图:
            <select id="ndBlueprint" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="">自动匹配</option>
              <option value="douyin_daily">🎵 douyin_daily</option>
              <option value="xhs_daily">📕 xhs_daily</option>
              <option value="douyin_active_v1">🎵 douyin_active_v1</option>
              <option value="xhs_active_v1">📕 xhs_active_v1</option>
            </select>
          </label>
          <button onclick="window._nurturePreflight('${a}')" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔍 预检</button>
          <button onclick="window._nurtureExec('${a}')" style="background:#22c55e;color:#000;border:none;padding:4px 14px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 执行选中</button>
          <button onclick="window._nurtureAll('${a}')" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">📋 全部启用</button>
          <span id="selCount_${a}" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>
        <div id="preflightInfo_${a}" style="font-size:10px;color:var(--text2);margin-top:2px;font-family:monospace;white-space:pre-wrap"></div>
        <div id="log_${a}" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:300px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`,r=n(document.getElementById(`acctList_${a}`),{accounts:s,checkAll:!1,height:`350px`}),document.getElementById(`selCount_${a}`).textContent=`已选 `+(r?.getCount()||0)+` 个`,window._nurtureRegistered||(window._nurtureRegistered=!0,window._nurturePreflight=async function(e){let n=document.getElementById(`log_${e}`),r=document.getElementById(`preflightInfo_${e}`);n&&(n.textContent=`🔍 预检中...
`),r&&(r.textContent=``);try{let e=await t(`/matrix/nurture/preflight`);r&&(r.textContent=e.info||JSON.stringify(e,null,2))}catch(e){n&&(n.textContent+=`❌ `+e.message+`
`)}},window._nurtureExec=async function(n){let i=r?.getSelected()||[];if(!i.length){alert(`请先选择要执行的账号`);return}let a=document.getElementById(`log_${n}`),o=document.getElementById(`ndRounds`)?.value||`10`,s=document.getElementById(`ndBlueprint`)?.value||``;if(await e(`养号执行 ${i.length} 个账号？`,`轮数: ${o}\n蓝图: ${s||`自动匹配`}`)){a&&(a.textContent=`🚀 提交 `+i.length+` 个账号到执行队列...
`);try{let e=await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`nurture`,accounts:i.map(e=>e.id),params:{blueprint:s,rounds:parseInt(o)}})});a&&(a.textContent+=`✅ 状态: ${e.status}\n`,e.commands&&e.commands.forEach(e=>{a.textContent+=`  ${e.machine}: ${e.accounts.join(`,`)} → ${e.status}\n`}),e.errors&&(a.textContent+=`⚠️ 错误: ${JSON.stringify(e.errors)}\n`),e.warnings&&(a.textContent+=`⚠️ 警告: ${JSON.stringify(e.warnings)}\n`))}catch(e){a&&(a.textContent+=`❌ `+e.message+`
`)}}},window._nurtureAll=async function(e){r?.selectAll(!0),await window._nurtureExec(e)})}export{i as loadView};
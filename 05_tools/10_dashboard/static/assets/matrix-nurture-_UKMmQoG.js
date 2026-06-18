import{t as e}from"./index-BVG99h1c.js";import{t}from"./account-selector-DBZWFo9Z.js";var n=null,r=null;async function i(e){let t=e.id||`nurture`;e.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">
          🌱 养号执行 <span style="font-size:10px;color:var(--text2);font-weight:400">预检 → 窗口定位 → 执行 → 验证</span>
        </div>

        <div id="acctList_${t}" style="margin-bottom:6px">
          <div class="loading" style="padding:8px;font-size:12px">⏳ 加载账号列表...</div>
        </div>

        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:11px;color:var(--text2)">轮数:
            <select id="ndRounds_${t}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="1">1 测试</option>
              <option value="5">5</option>
              <option value="10" selected>10 默认</option>
              <option value="20">20</option>
              <option value="30">30</option>
            </select>
          </label>
          <label style="font-size:11px;color:var(--text2)">蓝图:
            <select id="ndBlueprint_${t}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="">自动匹配</option>
              <option value="douyin_daily">🎵 douyin_daily</option>
              <option value="xhs_daily">📕 xhs_daily</option>
              <option value="douyin_active_v1">🎵 douyin_active_v1</option>
              <option value="xhs_active_v1">📕 xhs_active_v1</option>
            </select>
          </label>
          <button onclick="window._nurturePreflight('${t}')" 
            style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔍 预检</button>
          <button onclick="window._nurtureExec('${t}')" 
            style="background:#22c55e;color:#000;border:none;padding:4px 14px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 执行选中</button>
          <button onclick="window._nurtureAll('${t}')" 
            style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">📋 全部启用</button>
          <span id="selCount_${t}" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>

        <div id="nurtureStatus_${t}" style="font-size:11px;color:var(--text2);margin-top:4px"></div>
        <div id="nurturePreflight_${t}" style="font-size:10px;color:var(--text2);margin-top:2px;font-family:monospace;white-space:pre-wrap"></div>
        <div id="nurtureLog_${t}" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:300px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`,await a(t),o(t)}async function a(n){let i=document.getElementById(`acctList_${n}`);if(i)try{let[n,a]=await Promise.all([e(`/matrix/accounts`),e(`/matrix/homepage-info`).catch(()=>({results:[],collected_at:``}))]),o=Array.isArray(n)?n.filter(e=>e.enabled!==!1):[],s={};(a.results||[]).forEach(e=>{e.identity_dir&&(s[e.identity_dir]=e),e.phone&&(s[e.phone]=e)}),r=t(i,{accounts:o,hpIndex:s,checkAll:!0,height:`350px`})}catch(e){i.innerHTML=`<div class="error">❌ 加载失败: ${e.message}</div>`}}function o(t){window._nurtureGlobals||(window._nurtureGlobals=!0,window._nurturePreflight=async function(){let n=document.getElementById(`nurtureStatus_${t}`),r=document.getElementById(`nurturePreflight_${t}`);if(n){n.innerHTML=`<span style="color:var(--amber)">🟡 预检中...</span>`,r.textContent=``;try{let t=(await e(`/matrix/nurture/status`)).running||[];r.textContent=t.length?`⚠️ ${t.length} 个任务运行中:\n`+t.map(e=>`  ${e.account_id||e.id}: ${e.elapsed_sec||`?`}s`).join(`
`):`✅ 预检通过，可以执行`,n.innerHTML=t.length?`<span style="color:var(--green)">🟢 发现运行中任务</span>`:`<span style="color:var(--green)">🟢 就绪</span>`}catch(e){n.innerHTML=`<span style="color:var(--red)">🔴 预检失败: ${e.message}</span>`}}},window._nurtureExec=async function(){let n=r?.getSelected()||[];if(!n.length){alert(`请先选择要执行的账号`);return}let i=parseInt(document.getElementById(`ndRounds_${t}`)?.value||`10`),a=document.getElementById(`ndBlueprint_${t}`)?.value||``,o=document.getElementById(`nurtureStatus_${t}`),c=document.getElementById(`nurtureLog_${t}`);o.innerHTML=`<span style="color:var(--amber)">🟡 提交任务...</span>`,c&&(c.textContent=`🚀 提交 ${n.length} 个账号, ${i} 轮...\n`);try{let r=(await e(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`nurture`,accounts:n,params:{rounds:i,blueprint:a||void 0}})})).results||[];c&&(c.textContent=r.map(e=>`  ${e.status===`started`||e.status===`ok`?`✅`:`❌`} ${e.account_id||e.target}: ${e.status}`).join(`
`)),o.innerHTML=`<span style="color:var(--green)">🟢 已提交 ${r.filter(e=>e.status===`started`||e.status===`ok`).length} 个</span>`,s(t)}catch(e){o.innerHTML=`<span style="color:var(--red)">🔴 提交失败: ${e.message}</span>`,c&&(c.textContent+=`❌ ${e.message}\n`)}},window._nurtureAll=async function(){r?.selectAll(!0),await window._nurtureExec()})}function s(t){c();let r=document.getElementById(`nurtureLog_${t}`),i=document.getElementById(`nurtureStatus_${t}`);n=setInterval(async()=>{try{let t=(await e(`/matrix/nurture/status`)).running||[];if(!t.length){i.innerHTML=`<span style="color:var(--green)">🟢 全部完成</span>`,r&&(r.textContent+=`
✅ 养号执行全部完成`),c();return}i.innerHTML=`<span style="color:var(--amber)">🟡 ${t.length} 个任务运行中...</span>`,r&&(r.textContent=t.map(e=>`  ${e.account_id||e.id}: ${e.status||`运行中`} (${e.elapsed_sec||`?`}s)`).join(`
`))}catch{}},3e3)}function c(){n&&=(clearInterval(n),null)}export{i as loadView};
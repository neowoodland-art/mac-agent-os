import{t as e}from"./index-ChcXIF0h.js";var t=null,n=[];async function r(e){e.innerHTML=`
    <div style="padding:16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <div style="font-weight:700;font-size:16px">🚀 联邦指挥台</div>
        <div style="display:flex;gap:8px;align-items:center">
          <span id="cmdLastUpdate" style="font-size:10px;color:var(--text2)"></span>
          <button onclick="window._cmdRefresh()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔄 刷新</button>
          <label style="font-size:10px;color:var(--text2)"><input type="checkbox" id="cmdAutoRefresh" checked onchange="window._cmdToggleAuto()"> 自动(15s)</label>
        </div>
      </div>

      <!-- 告警栏 -->
      <div id="cmdAlerts" style="display:none;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:8px;margin-bottom:8px;font-size:11px">
        <div style="font-weight:600;margin-bottom:4px">⚠️ 告警</div>
        <div id="cmdAlertsList"></div>
      </div>

      <!-- 操作栏 -->
      <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;align-items:center;padding:6px 8px;background:var(--bg2);border-radius:8px;border:1px solid var(--border)">
        <span style="font-size:11px;font-weight:600">🛠️ 管理:</span>
        <select id="cmdResetMachine" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 6px;border-radius:4px;font-size:10px"><option value="">全部机器</option></select>
        <button onclick="window._cmdResetMachine()" style="background:rgba(220,38,38,.1);color:#ef4444;border:1px solid rgba(220,38,38,.3);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔄 初始化机器</button>
        <button onclick="window._cmdResetAll()" style="background:rgba(220,38,38,.1);color:#ef4444;border:1px solid rgba(220,38,38,.3);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:11px">⚠️ 重置全部</button>
        <span id="cmdResetResult" style="font-size:10px;color:var(--text2)"></span>
      </div>

      <!-- 三台机器面板 -->
      <div id="cmdMachinesGrid"></div>

      <!-- 最近事件 -->
      <div id="cmdEventLog" style="margin-top:12px"></div>
    </div>`,s(e),await c(e),a(e)}function i(){o()}function a(e){o(),t=setInterval(()=>{document.getElementById(`cmdAutoRefresh`)?.checked&&c(e,!0)},15e3)}function o(){t&&=(clearInterval(t),null)}function s(t){window._cmdRegisteredV5||(window._cmdRegisteredV5=!0,window._cmdRefresh=()=>c(t),window._cmdToggleAuto=()=>{document.getElementById(`cmdAutoRefresh`)?.checked?a(t):o()},window._cmdResetMachine=async()=>{let n=document.getElementById(`cmdResetMachine`)?.value||``;if(!n){alert(`请先选择要初始化的机器`);return}if(!confirm(`确定初始化机器 ${n}？\n将杀掉所有活跃任务和浏览器进程`))return;let r=document.getElementById(`cmdResetResult`);r&&(r.textContent=`⏳`);try{await e(`/ops/reset`,{method:`POST`,body:JSON.stringify({machine:n})}),r&&(r.textContent=`✅ ${n} 已初始化`),c(t)}catch(e){r&&(r.textContent=`❌ `+e.message)}},window._cmdResetAll=async()=>{if(!confirm(`⚠️ 重置全部机器？
将杀掉所有活跃任务和浏览器进程`))return;let n=document.getElementById(`cmdResetResult`);n&&(n.textContent=`⏳`);try{let r=await e(`/ops/reset`,{method:`POST`,body:JSON.stringify({})});n&&(n.textContent=`✅ 已重置 ${Object.keys(r.machines||{}).length} 台`),c(t)}catch(e){n&&(n.textContent=`❌ `+e.message)}},window._cmdStop=async(n,r)=>{if(confirm(`停止 ${r}?`))try{await e(`/ops/task/cancel`,{method:`POST`,body:JSON.stringify({task_id:r,machine:n})}),c(t)}catch(e){alert(`❌ `+e.message)}})}async function c(t,r=!1){let i=document.getElementById(`cmdLastUpdate`);i&&(i.textContent=`🕐 ${new Date().toLocaleTimeString()}`);try{let[t,r]=await Promise.all([e(`/ops/queue?local_only=false`).catch(()=>({machines:{}})),e(`/ops/task-events?limit=50`).catch(()=>({events:[]}))]);n=(r.events||[]).slice(-30);let i=t?.machines||{},a=Object.keys(i);for(let e of[`cmdResetMachine`]){let t=document.getElementById(e);t&&t.options.length<=1&&a.forEach(e=>{let n=document.createElement(`option`);n.value=e,n.textContent=e,t.appendChild(n)})}l(t),u(t),d()}catch(e){r||(document.getElementById(`cmdMachinesGrid`).innerHTML=`<div style="color:#ef4444;font-size:12px;padding:20px;text-align:center">❌ 加载失败: ${e.message}</div>`)}}function l(e){let t=document.getElementById(`cmdAlerts`),n=document.getElementById(`cmdAlertsList`);if(!t||!n)return;let r=[];for(let[t,n]of Object.entries(e?.machines||{})){n?.error&&r.push({machine:t,level:`error`,msg:`🔴 不可达: ${n.error}`});let e=n?.counts||{};e?.failed>0&&r.push({machine:t,level:`warning`,msg:`❌ ${e.failed} 个任务失败`})}r.length?(t.style.display=`block`,n.innerHTML=r.map(e=>`<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 8px;margin-bottom:2px;background:${e.level===`error`?`#fef2f2`:`#fffbeb`};border:1px solid ${e.level===`error`?`#fecaca`:`#fde68a`};border-radius:4px;font-size:10px">
        <span>[${e.machine}] ${e.msg}</span>
        <button onclick="this.parentElement.remove()" style="background:none;border:none;cursor:pointer;font-size:9px;color:var(--text2)">✕</button>
      </div>`).join(``)):t.style.display=`none`}function u(e){let t=document.getElementById(`cmdMachinesGrid`),n=e?.machines||{},r=``;for(let[e,t]of Object.entries(n)){let n=!t?.error,i=t?.slots||{},a=Array.isArray(i)?i:i.slots||i.list||[],o=i?.used||0,s=i?.max||3,c=t?.counts||{},l=t?.queue||[],u=t?.queue_sizes||{},d=l.filter(e=>e.queue===`P0`),p=l.filter(e=>e.queue===`P1`);r+=`<details open style="margin-bottom:8px;background:var(--bg2);border-radius:10px;border:1px solid var(--border);overflow:hidden">
      <summary style="padding:8px 12px;cursor:pointer;display:flex;align-items:center;gap:8px;background:var(--bg3)">
        <span style="font-size:16px">${n?`🟢`:`🔴`}</span>
        <span style="font-weight:600;font-size:13px">${e}</span>
        <span style="font-size:10px;color:var(--text2)">${o}/${s} slot · 完成${c?.completed||0} 失败${c?.failed||0}</span>
        <span style="margin-left:auto;font-size:10px;color:var(--text2)">
          P0:${u?.priority||0} P1:${u?.normal||0} P2:${u?.filler||0}
        </span>
      </summary>
      <div style="padding:8px 12px">

        <!-- 3 slot 显示 -->
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:8px">`;for(let e=0;e<s;e++){let t=a.find(t=>t.slot_id===e)||{};if(!t.account_id){r+=`<div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px dashed var(--border);display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:70px">
          <div style="font-size:18px;opacity:0.2">○</div>
          <div style="font-size:9px;color:var(--text2)">Slot ${e+1} 空闲</div>
        </div>`;continue}let n=t.nickname||t.account_id||``,i=(t.platform||``)===`xiaohongshu`?`📕`:`🎵`,o=t.step_index||0,s=t.total_steps||0,c=t.health||`healthy`,l=c===`healthy`?`🟢`:c===`warning`?`🟡`:`🔴`;r+=`<div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600;font-size:11px">${i} ${t.account_id||``}</span>
          <span style="font-size:9px;color:var(--text2)">${l}</span>
        </div>
        <div style="font-size:9px;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${n}</div>
        ${t.current_step?`<div style="font-size:8px;color:var(--text2);margin-top:2px">🔧 ${t.current_step}</div>`:``}
        ${t.elapsed_sec?`<div style="font-size:8px;color:var(--text2)">⏱ ${f(t.elapsed_sec)}</div>`:``}
        ${s>0?`
        <div style="margin-top:4px">
          <div style="display:flex;justify-content:space-between;font-size:8px;color:var(--text2)">
            <span>${o}/${s}</span>
            <span>${Math.round(o/(s||1)*100)}%</span>
          </div>
          <div style="height:3px;background:var(--bg2);border-radius:2px;margin-top:2px">
            <div style="height:100%;width:${Math.min(100,o/(s||1)*100)}%;background:#22c55e;border-radius:2px"></div>
          </div>
        </div>`:``}
      </div>`}r+=`</div>`;let m=[...d,...p];m.length?(r+=`<div style="font-size:10px;font-weight:600;margin-bottom:4px;color:var(--text2)">📋 排队队列 (${m.length})</div>
      <div style="font-size:9px">`,m.slice(0,10).forEach(e=>{let t=e.queue===`P0`?`🔴P0`:e.queue===`P1`?`🟢P1`:`⚪P2`,n=e.task_id?e.task_id.split(`_`).slice(0,3).join(`_`):``;r+=`<div style="display:flex;gap:4px;padding:2px 4px;border-bottom:1px solid var(--border)">
          <span style="min-width:32px">${t}</span>
          <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${n}</span>
        </div>`}),m.length>10&&(r+=`<div style="color:var(--text2);padding:2px 4px">...还有 ${m.length-10} 个</div>`),r+=`</div>`):r+=`<div style="font-size:9px;color:var(--text2);padding:2px 0">📋 队列为空</div>`,r+=`</div></details>`}t.innerHTML=r||`<div style="font-size:12px;color:var(--text2);padding:20px">暂无机器数据</div>`}function d(){let e=document.getElementById(`cmdEventLog`);if(!e||!n.length){e&&(e.innerHTML=``);return}let t={started:`▶️`,completed:`✅`,failed:`❌`};e.innerHTML=`
    <details>
      <summary style="cursor:pointer;font-weight:600;font-size:11px;margin-bottom:4px">📡 最近事件 (${n.length})</summary>
      <div style="font-size:9px;max-height:150px;overflow-y:auto">
        ${n.slice(-15).reverse().map(e=>{let n=t[e.event]||`❓`,r=(e.accounts||[]).join(`,`)||``;return`<div style="display:flex;gap:4px;padding:2px 4px;border-bottom:1px solid var(--border)">
            <span>${n}</span>
            <span style="min-width:70px;color:var(--text2)">${e.machine||``}</span>
            <span style="color:var(--text2)">${e.cmd_type||``}</span>
            <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r}</span>
            <span style="color:var(--text2)">${e.time?e.time.slice(11,19):``}</span>
          </div>`}).join(``)}
      </div>
    </details>`}function f(e){if(!e||e<=0)return``;let t=Math.floor(e/60),n=e%60;return t>0?`${t}m${n}s`:`${n}s`}export{r as loadView,i as unloadView};
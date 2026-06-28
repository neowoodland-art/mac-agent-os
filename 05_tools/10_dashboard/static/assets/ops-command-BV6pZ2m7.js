import{t as e}from"./index-rHyD4197.js";var t=null;async function n(t){t.innerHTML=`
    <div style="padding:16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <div style="font-weight:700;font-size:16px">🚀 联邦指挥台</div>
        <div style="display:flex;gap:8px;align-items:center">
          <span id="cmdLastUpdate" style="font-size:10px;color:var(--text2)"></span>
          <button onclick="window._cmdRefresh()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔄 刷新</button>
          <button onclick="window._cmdReset()" style="background:#ef4444;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🗑 重置所有</button>
          <label style="font-size:10px;color:var(--text2)">
            <input type="checkbox" id="cmdAutoRefresh" checked onchange="window._cmdToggleAuto()"> 自动刷新(15s)
          </label>
        </div>
      </div>

      <!-- 账号健康度面板 -->
      <div id="cmdHealthPanel" style="background:var(--bg2);border-radius:8px;padding:8px;border:1px solid var(--border);margin-bottom:8px;display:none">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
          <div style="font-weight:600;font-size:12px">🩺 账号健康度</div>
          <button onclick="document.getElementById('cmdHealthPanel').style.display='none'" style="background:none;border:none;cursor:pointer;font-size:10px;color:var(--text2)">✕</button>
        </div>
        <div id="cmdHealthList" style="font-size:10px;max-height:120px;overflow-y:auto">加载中...</div>
      </div>

      <!-- 三机状态总览 -->
      <div id="cmdMachineOverview" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px">
        <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border);text-align:center">
          <div style="font-size:10px;color:var(--text2)">加载中...</div>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;align-items:center">
        <span style="font-size:11px;color:var(--text2);font-weight:600">筛选:</span>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P0" checked onchange="window._cmdRefresh()"> 🔴 优先任务</label>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P1" checked onchange="window._cmdRefresh()"> 🟢 日常任务</label>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P2" onchange="window._cmdRefresh()"> ⚪ 闲时任务</label>
        <span style="margin-left:12px;font-size:11px;color:var(--text2);font-weight:600">机器:</span>
        <select id="cmdMachineFilter" onchange="window._cmdRefresh()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 6px;border-radius:4px;font-size:10px">
          <option value="all">全部</option>
        </select>
      </div>

      <!-- 告警中心 -->
      <div id="cmdAlerts" style="display:none;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:8px;margin-bottom:8px;font-size:11px">
        <div style="font-weight:600;margin-bottom:4px">⚠️ 告警中心</div>
        <div id="cmdAlertsList"></div>
      </div>

      <!-- 各机详细队列 -->
      <div id="cmdQueueDetail"></div>
    </div>`,window._cmdRegistered||(window._cmdRegistered=!0,window._cmdRefresh=()=>o(t),window._cmdMoveUp=(e,t)=>{},window._cmdMoveDown=(e,t)=>{},window._cmdRemoveQueue=async(e,t)=>{confirm(`确定从队列中移除此任务？`)&&alert(`移出队列功能待实现`)},window._cmdStop=async(n,r)=>{if(confirm(`确定停止任务 `+r+` ？`))try{await e(`/ops/task/cancel`,{method:`POST`,body:JSON.stringify({task_id:r,machine:n})}),alert(`✅ 已发送停止指令`),o(t)}catch(e){alert(`❌ 停止失败: `+e.message)}},window._cmdReset=async()=>{if(confirm(`确定重置所有机器？将清空任务队列、终止运行中的任务。`))try{let n=await e(`/ops/reset`,{method:`POST`,body:`{}`});alert(`✅ 已重置: `+JSON.stringify(n.machines)),o(t)}catch(e){alert(`❌ 重置失败: `+e.message)}},window._cmdToggleAuto=()=>{document.getElementById(`cmdAutoRefresh`)?.checked?i(t):a()}),await o(t),i(t)}function r(){a()}function i(e){a(),t=setInterval(()=>{document.getElementById(`cmdAutoRefresh`)?.checked&&o(e,!0)},15e3)}function a(){t&&=(clearInterval(t),null)}async function o(t,n=!1){try{let[t,r,i]=await Promise.all([e(`/ops/queue`),e(`/ops/machines`),e(`/matrix/accounts`).catch(()=>[])]);s(i),n||(document.getElementById(`cmdLastUpdate`).textContent=`最后更新: ${new Date().toLocaleTimeString()}`),l(t),c(t,r),u(t)}catch(e){n||(document.getElementById(`cmdQueueDetail`).innerHTML=`<div style="color:#ef4444;font-size:12px">❌ 加载失败: ${e.message}</div>`)}}function s(e){let t=document.getElementById(`cmdHealthPanel`),n=document.getElementById(`cmdHealthList`);if(!t||!n||!Array.isArray(e)||e.length===0)return;let r=e.filter(e=>e.status===`banned`||e.status===`login_expired`);if(r.length===0){t.style.display=`none`;return}t.style.display=`block`,n.innerHTML=r.map(e=>`<div style="padding:2px 0;color:#ef4444">⚠️ `+(e.platform||`?`)+` `+(e.id||`?`)+` — `+(e.status||`unknown`)+`</div>`).join(``)}function c(e,t){let n=document.getElementById(`cmdMachineOverview`),r=document.getElementById(`cmdMachineFilter`),i=e?.machines||{};t?.machines;let a=r.value;r.innerHTML=`<option value="all">全部</option>`;let o=``,s=0;for(let[e,t]of Object.entries(i)){r.innerHTML+=`<option value="${e}">${e}</option>`;let n=t?.slots||{},i=t?.active||null,a=t?.counts||{},c=!t?.error,l=n?.used||0,u=n?.max||3;o+=`
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <div style="font-weight:600;font-size:12px">${c?`🟢`:`🔴`} ${e}</div>
          <div style="font-size:10px;color:var(--text2)">${l}/${u} 槽位</div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(${Math.min(u,3)},1fr);gap:4px;margin-bottom:4px">
          ${Array.from({length:u},(e,t)=>{let r=n?.slots?.find(e=>e.slot_id===t);return r&&r.account_id?`<div style="background:#22c55e20;border-radius:6px;padding:6px;border:1px solid #22c55e">
              <div style="font-size:9px;font-weight:600">${r.platform===`xiaohongshu`?`📕`:`🎵`} ${r.nickname||r.account_id}</div>
              <div style="font-size:8px;color:var(--text2)">${r.account_id}</div>
              ${r.current_step?`<div style="font-size:8px;color:var(--text2);margin-top:2px">🔧 ${r.current_step}</div>`:``}
              ${r.elapsed_sec?`<div style="font-size:8px;color:var(--text2)">⏱ ${Math.floor(r.elapsed_sec/60)}分</div>`:``}
              ${r.blueprint?`<div style="font-size:8px;color:var(--text2)">📋 ${r.blueprint}</div>`:``}
            </div>`:`<div style="background:var(--bg3);border-radius:6px;padding:6px;border:1px solid var(--border);text-align:center;font-size:9px;color:var(--text2)">空闲</div>`}).join(``)}
        </div>
        ${i?`
          <div style="font-size:10px;color:var(--text);background:var(--bg3);border-radius:4px;padding:4px 6px;margin-top:4px">
            <div><strong>${i.cmd_type||`?`}</strong> · ${i.account||``}</div>
            <div style="color:var(--text2)">${i.blueprint||``} · ${i.progress?.current_step||``} (${i.progress?.step_index||0}/${i.progress?.total_steps||`?`})</div>
          </div>
        `:`
          <div style="font-size:10px;color:var(--text2);margin-top:4px">空闲</div>
        `}
        <div style="font-size:9px;color:var(--text2);margin-top:4px">
          ${a?.running?`▶️运行:${a.running}`:``}
          ${a?.queued?` ⏳排队:${a.queued}`:``}
          ${a?.completed?` ✅完成:${a.completed}`:``}
          ${a?.failed?` ❌失败:${a.failed}`:``}
        </div>
      </div>`,s++}n.innerHTML=o,a&&(r.value=a)}function l(e){let t=document.getElementById(`cmdAlerts`),n=document.getElementById(`cmdAlertsList`);if(!t||!n)return;let r=[],i=e?.machines||{};for(let[e,t]of Object.entries(i)){let n=t?.active||null,i=t?.counts||{};t?.error&&r.push({machine:e,type:`error`,msg:`不可达: `+t.error}),n?.status===`failed`&&r.push({machine:e,type:`failed`,msg:`任务失败: `+n.task_id}),i?.failed>0&&r.push({machine:e,type:`failed_count`,msg:i.failed+` 个任务失败`})}r.length>0?(t.style.display=`block`,n.innerHTML=r.map(e=>`<div style="padding:2px 0">⚠️ [`+e.machine+`] `+e.msg+`</div>`).join(``)):t.style.display=`none`}function u(e){let t=document.getElementById(`cmdQueueDetail`),n=document.getElementById(`cmdMachineFilter`)?.value||`all`,r=e?.machines||{},i=document.querySelector(`.cmdFilter[value="P0"]`)?.checked??!0,a=document.querySelector(`.cmdFilter[value="P1"]`)?.checked??!0,o=document.querySelector(`.cmdFilter[value="P2"]`)?.checked??!1,s=``;for(let[e,t]of Object.entries(r)){if(n!==`all`&&e!==n)continue;let r=t?.active||null,c=t?.queue||[],l=t?.counts||{},u=t?.slots?.slots||[],d=c.filter(e=>!(e.priority===0&&!i||e.priority===1&&!a||e.priority===2&&!o||e.priority==null&&!a));s+=`
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border);margin-bottom:8px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <div style="font-weight:600;font-size:13px">${e}</div>
          <div style="font-size:10px;color:var(--text2)">队列: ${d.length} | 完成: ${l.completed||0} | 失败: ${l.failed||0}</div>
        </div>
        
        ${r?`
          <div style="background:var(--bg3);border-radius:6px;padding:8px;margin-bottom:6px;border-left:3px solid #22c55e">
            <div style="display:flex;justify-content:space-between">
              <div><span style="font-size:10px;background:#ef4444;color:#fff;padding:1px 5px;border-radius:3px;margin-right:4px">P0</span><strong style="font-size:12px">${r.cmd_type||``}</strong></div>
              <div style="font-size:10px;color:var(--text2)">⏱ ${r.elapsed_sec?Math.floor(r.elapsed_sec/60)+`分`:`刚刚`}</div>
            </div>
            <div style="font-size:11px;margin-top:4px">账号: ${r.account||``}</div>
            <div style="font-size:10px;color:var(--text2);margin-top:2px">蓝图: ${r.blueprint||``}</div>
            <div style="font-size:10px;color:var(--text2);margin-top:2px">当前: ${r.progress?.current_step||``} (${r.progress?.step_index||0}/${r.progress?.total_steps||`?`})</div>
            <div style="font-size:10px;color:var(--text2);margin-top:2px">状态: ${r.status||``}</div>
          </div>
        `:`
          <div style="background:var(--bg3);border-radius:6px;padding:8px;margin-bottom:6px;color:var(--text2);font-size:11px">当前无活跃任务</div>
        `}
        
        ${u.length>0?`
          <div style="display:grid;grid-template-columns:repeat(${Math.min(u.length,3)},1fr);gap:4px;margin-bottom:6px">
            ${u.map(e=>{if(!e.account_id)return`<div style="background:var(--bg3);border-radius:4px;padding:6px;border:1px solid var(--border);font-size:9px;color:var(--text2)"><div style="font-weight:600">槽位`+(e.slot_id+1)+`</div><div>空闲</div></div>`;let t=e.platform===`xiaohongshu`?`📕`:`🎵`,n=e.nickname||e.account_id;return`<div style="background:#22c55e20;border-radius:4px;padding:6px;border:1px solid #22c55e;font-size:9px"><div style="font-weight:600">槽位`+(e.slot_id+1)+`</div><div>`+t+` `+n+`</div><div style="color:var(--text2)">`+e.account_id+`</div>`+(e.current_step?`<div style="color:var(--text2);margin-top:2px">🔧 `+e.current_step+`</div>`:``)+(e.blueprint?`<div style="color:var(--text2)">📋 `+e.blueprint+`</div>`:``)+(e.elapsed_sec?`<div style="color:var(--text2)">⏱ `+Math.floor(e.elapsed_sec/60)+`分</div>`:``)+`</div>`}).join(``)}
          </div>
        `:``}
        
        ${d.length>0?`
          <div style="font-size:10px;color:var(--text2);margin-bottom:4px">⏳ 排队中 (${d.length}) <span style="font-size:9px;color:var(--text2);margin-left:8px">(拖拽调整顺序功能开发中)</span></div>
          ${d.slice(0,10).map((t,n)=>`<div style="font-size:10px;padding:2px 4px;background:var(--bg3);border-radius:3px;margin-bottom:2px;display:flex;justify-content:space-between">
              <span>${t.priority===0?`🔴`:t.priority===1?`🟢`:`⚪`} [${t.priority===0?`P0优先`:t.priority===1?`P1日常`:`P2闲时`}] ${t.task_id?.slice(0,40)||``}</span>
              <span>
                <button onclick="window._cmdMoveUp('${e}',${n})" style="background:none;border:none;cursor:pointer;font-size:9px;color:var(--text2)">↑</button>
                <button onclick="window._cmdMoveDown('${e}',${n})" style="background:none;border:none;cursor:pointer;font-size:9px;color:var(--text2)">↓</button>
                <button onclick="window._cmdRemoveQueue('${e}',${n})" style="background:none;border:none;cursor:pointer;font-size:9px;color:#ef4444">✕</button>
              </span>
            </div>`).join(``)}
        `:`<div style="font-size:10px;color:var(--text2)">队列为空</div>`}
      </div>`}t.innerHTML=s||`<div style="color:var(--text2);font-size:12px;text-align:center;padding:20px">没有机器数据</div>`}export{n as loadView,r as unloadView};
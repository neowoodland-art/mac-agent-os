import{t as e}from"./index-DAh1zjLe.js";var t=null,n=[];async function r(t){try{n=(await e(`/v2/accounts`)).accounts||[]}catch{n=[]}t.innerHTML=`
    <div style="padding:16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <div style="font-weight:700;font-size:16px">🚀 联邦指挥台</div>
        <div style="display:flex;gap:8px;align-items:center">
          <span id="cmdLastUpdate" style="font-size:10px;color:var(--text2)"></span>
          <button onclick="window._cmdRefresh()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔄 刷新</button>
          <label style="font-size:10px;color:var(--text2)">
            <input type="checkbox" id="cmdAutoRefresh" checked onchange="window._cmdToggleAuto()"> 自动(15s)
          </label>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;align-items:center">
        <span style="font-size:11px;color:var(--text2);font-weight:600">筛选:</span>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P0" checked onchange="window._cmdRefresh()"> 🔴 优先</label>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P1" checked onchange="window._cmdRefresh()"> 🟢 日常</label>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P2" onchange="window._cmdRefresh()"> ⚪ 闲时</label>
        <span style="margin-left:12px;font-size:11px;color:var(--text2);font-weight:600">机器:</span>
        <select id="cmdMachineFilter" onchange="window._cmdRefresh()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 6px;border-radius:4px;font-size:10px">
          <option value="all">全部</option>
        </select>
        <span id="cmdQueueCount" style="font-size:10px;color:var(--text2);margin-left:auto"></span>
      </div>

      <!-- 告警中心 -->
      <div id="cmdAlerts" style="display:none;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:8px;margin-bottom:8px;font-size:11px">
        <div style="font-weight:600;margin-bottom:4px">⚠️ 告警</div>
        <div id="cmdAlertsList"></div>
      </div>

      <!-- 9 轨道 slot 视图 -->
      <div id="cmdTrackGrid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px"></div>

      <!-- 各机任务队列详情 -->
      <div id="cmdQueueDetail"></div>
    </div>`,window._cmdRegistered2||(window._cmdRegistered2=!0,window._cmdRefresh=()=>d(t),window._cmdStop=async(n,r)=>{if(confirm(`停止 ${r} ?`))try{await e(`/ops/task/cancel`,{method:`POST`,body:JSON.stringify({task_id:r,machine:n})}),alert(`✅ 已停止`),d(t)}catch(e){alert(`❌ `+e.message)}},window._cmdRemoveQueue=(e,t)=>alert(`移出队列功能开发中`),window._cmdToggleAuto=()=>{document.getElementById(`cmdAutoRefresh`)?.checked?a(t):o()},window._cmdRefresh()),await d(t),a(t)}function i(){o()}function a(e){o(),t=setInterval(()=>{document.getElementById(`cmdAutoRefresh`)?.checked&&d(e,!0)},15e3)}function o(){t&&=(clearInterval(t),null)}function s(e){return n.find(t=>t.id===e)||{}}function c(e){if(!e||e<=0)return``;let t=Date.now()/1e3;if(e>t)return`刚刚`;let n=Math.floor(t-e);return n<5?`刚刚`:n<60?`${n}秒`:n<3600?`${Math.floor(n/60)}分${n%60}秒`:`${Math.floor(n/3600)}时${Math.floor(n%3600/60)}分`}function l(e,t){return!t||t<=0?``:`${Math.round(e/t*100)}%`}function u(e){if(!e.account_id)return`#8b8fa3`;let t=e.health||`healthy`;return t===`healthy`?`#22c55e`:t===`warning`?`#eab308`:`#ef4444`}async function d(t,n=!1){try{let[t,r]=await Promise.all([e(`/ops/queue`),e(`/ops/machines`)]);if(!n){let e=document.getElementById(`cmdLastUpdate`);e&&(e.textContent=`🕐 ${new Date().toLocaleTimeString()}`)}f(t),p(t),m(t)}catch(e){n||(document.getElementById(`cmdTrackGrid`).innerHTML=`<div style="color:#ef4444;font-size:12px;grid-column:1/-1;padding:20px;text-align:center">❌ 加载失败: ${e.message}</div>`)}}function f(e){let t=document.getElementById(`cmdAlerts`),n=document.getElementById(`cmdAlertsList`);if(!t||!n)return;let r=[],i=e?.machines||{};for(let[e,t]of Object.entries(i)){let n=t?.active||null,i=t?.counts||{};t?.error&&r.push(`[${e}] 🔴 不可达: ${t.error}`),i?.failed>0&&r.push(`[${e}] ❌ ${i.failed} 个任务失败`),n?.status===`failed`&&r.push(`[${e}] ⛔ 任务失败: ${n.task_id}`)}r.length>0?(t.style.display=`block`,n.innerHTML=r.map(e=>`<div style="padding:2px 0">${e}</div>`).join(``)):t.style.display=`none`}function p(e){let t=document.getElementById(`cmdTrackGrid`),n=document.getElementById(`cmdMachineFilter`),r=e?.machines||{},i=n?.value||`all`;n.innerHTML=`<option value="all">全部</option>`;let a=0,o=0,d=``;for(let[e,t]of Object.entries(r)){if(n.innerHTML+=`<option value="${e}">${e}</option>`,i!==`all`&&e!==i)continue;let r=t?.slots||{},f=Array.isArray(r)?r:r.slots||r.list||[],p=r?.used||0,m=r?.max||3;a+=p,o+=m;let h=!t?.error,g=t?.counts||{};d+=`<div style="grid-column:1/-1;font-size:11px;font-weight:600;padding:6px 8px;background:var(--bg3);border-radius:6px;margin:4px 0;display:flex;align-items:center;gap:6px">
      <span>${h?`🟢`:`🔴`} ${e}</span>
      <span style="font-size:10px;color:var(--text2);font-weight:400">${p}/${m} 槽位 · ${g?.completed||0}完成/${g?.failed||0}失败</span>
    </div>`;for(let t=0;t<m;t++){let n=f.find(e=>e.slot_id===t)||{},r=n.account_id||``,i=s(r),a=(i.phone||r)&&n.phone||``,o=n.nickname||i.nickname||r,p=(n.platform||i.platform)===`xiaohongshu`?`📕`:`🎵`;if(!r){d+=`<div style="background:var(--bg2);border-radius:8px;padding:8px;border:1px dashed var(--border);display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:80px;gap:4px">
          <div style="font-size:20px;opacity:0.2">○</div>
          <div style="font-size:9px;color:var(--text2)">${e} · Slot ${t+1}</div>
          <div style="font-size:8px;color:var(--text2)">空闲</div>
        </div>`;continue}let m=n.health||`healthy`,h=m===`healthy`?`🟢`:m===`warning`?`🟡`:`🔴`,g=n.step_index||0,_=n.total_steps||0;d+=`<div style="background:var(--bg2);border-radius:8px;padding:8px;border:1px solid var(--border);position:relative">
        <!-- 运行中状态条 -->
        <div style="height:3px;background:${u(n)};border-radius:2px;margin-bottom:6px"></div>
        
        <!-- 账号信息 -->
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div style="font-weight:600;font-size:11px">${p} ${n.account_id||``}</div>
          <div style="font-size:9px;color:var(--text2)">${h}</div>
        </div>
        ${a?`<div style="font-size:9px;color:var(--text2);margin-top:2px">📱 ${a}</div>`:``}
        <div style="font-size:9px;color:var(--text);margin-top:1px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${o}</div>
        
        <!-- 任务信息 -->
        ${n.blueprint?`<div style="font-size:8px;color:var(--text2);margin-top:4px">📋 ${n.blueprint}</div>`:``}
        ${n.current_step?`<div style="font-size:8px;color:var(--text2)">🔧 ${n.current_step}</div>`:``}
        
        <!-- 进度 -->
        ${_>0?`
        <div style="margin-top:4px">
          <div style="display:flex;justify-content:space-between;font-size:8px;color:var(--text2)">
            <span>步骤 ${g}/${_}</span>
            <span>${l(g,_)}</span>
          </div>
          <div style="height:4px;background:var(--bg3);border-radius:2px;margin-top:2px">
            <div style="height:100%;width:${Math.min(100,g/_*100)}%;background:#22c55e;border-radius:2px;transition:width 0.5s"></div>
          </div>
        </div>`:``}
        
        <!-- 耗时 -->
        ${n.elapsed_sec?`<div style="font-size:8px;color:var(--text2);margin-top:3px">⏱ ${c(n.elapsed_sec)}</div>`:``}
      </div>`}}t.innerHTML=d||`<div style="grid-column:1/-1;text-align:center;padding:20px;color:var(--text2);font-size:12px">无机器数据</div>`;let f=document.getElementById(`cmdQueueCount`);if(f){let e=0;for(let[t,n]of Object.entries(r))e+=(n?.queue||[]).length;f.textContent=`⏳ ${e} 排队 | ${a}/${o} 槽位使用中`}}function m(e){let t=document.getElementById(`cmdQueueDetail`),n=document.getElementById(`cmdMachineFilter`)?.value||`all`,r=e?.machines||{},i=document.querySelector(`.cmdFilter[value="P0"]`)?.checked??!0,a=document.querySelector(`.cmdFilter[value="P1"]`)?.checked??!0,o=document.querySelector(`.cmdFilter[value="P2"]`)?.checked??!1,s=``;for(let[e,t]of Object.entries(r)){if(n!==`all`&&e!==n)continue;let r=t?.queue||[],c=t?.counts||{},l=r.filter(e=>{let t=e.priority==null?1:e.priority;return!(t===0&&!i||t===1&&!a||t===2&&!o)}).sort((e,t)=>(e.priority||1)-(t.priority||1));l.length===0&&n===`all`||(s+=`<div style="background:var(--bg2);border-radius:8px;padding:8px;border:1px solid var(--border);margin-bottom:6px">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <span style="font-weight:600;font-size:11px">${e}</span>
        <span style="font-size:9px;color:var(--text2)">排队: ${l.length} | 完成: ${c.completed||0} | 失败: ${c.failed||0}</span>
      </div>
      ${l.length>0?l.slice(0,15).map((t,n)=>`<div style="font-size:9px;padding:2px 4px;background:var(--bg3);border-radius:3px;margin-bottom:2px;display:flex;justify-content:space-between;align-items:center">
          <span>${t.priority===0?`🔴`:t.priority===1?`🟢`:`⚪`} [${t.priority===0?`P0`:t.priority===1?`P1`:`P2`}] ${(t.task_id||``).slice(0,36)} ${t.accounts?t.accounts.join(`,`):``}</span>
          <button onclick="window._cmdRemoveQueue('${e}',${n})" style="background:none;border:none;cursor:pointer;font-size:9px;color:#ef4444;padding:0 2px" title="移出队列">✕</button>
        </div>`).join(``):n===`all`?``:`<div style="font-size:9px;color:var(--text2);padding:2px 0">队列为空</div>`}
    </div>`)}t.innerHTML=s||``}export{r as loadView,i as unloadView};
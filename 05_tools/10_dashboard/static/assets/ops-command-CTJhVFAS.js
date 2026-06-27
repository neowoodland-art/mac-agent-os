import{t as e}from"./index-CNXsTUbo.js";var t=null;async function n(e){e.innerHTML=`
    <div style="padding:16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <div style="font-weight:700;font-size:16px">🚀 联邦指挥台</div>
        <div style="display:flex;gap:8px;align-items:center">
          <span id="cmdLastUpdate" style="font-size:10px;color:var(--text2)"></span>
          <button onclick="window._cmdRefresh()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔄 刷新</button>
          <label style="font-size:10px;color:var(--text2)">
            <input type="checkbox" id="cmdAutoRefresh" checked onchange="window._cmdToggleAuto()"> 自动刷新(15s)
          </label>
        </div>
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
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P0" checked> 🔴 优先任务</label>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P1" checked> 🟢 日常任务</label>
        <label style="font-size:10px;color:var(--text2)"><input type="checkbox" class="cmdFilter" value="P2"> ⚪ 闲时任务</label>
        <span style="margin-left:12px;font-size:11px;color:var(--text2);font-weight:600">机器:</span>
        <select id="cmdMachineFilter" onchange="window._cmdRefresh()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 6px;border-radius:4px;font-size:10px">
          <option value="all">全部</option>
        </select>
      </div>

      <!-- 各机详细队列 -->
      <div id="cmdQueueDetail"></div>
    </div>`,window._cmdRegistered||(window._cmdRegistered=!0,window._cmdRefresh=()=>o(e),window._cmdToggleAuto=()=>{document.getElementById(`cmdAutoRefresh`)?.checked?i(e):a()}),await o(e),i(e)}function r(){a()}function i(e){a(),t=setInterval(()=>{document.getElementById(`cmdAutoRefresh`)?.checked&&o(e,!0)},15e3)}function a(){t&&=(clearInterval(t),null)}async function o(t,n=!1){try{let[t,r]=await Promise.all([e(`/api/ops/queue`),e(`/api/ops/machines`)]);n||(document.getElementById(`cmdLastUpdate`).textContent=`最后更新: ${new Date().toLocaleTimeString()}`),s(t,r),c(t)}catch(e){n||(document.getElementById(`cmdQueueDetail`).innerHTML=`<div style="color:#ef4444;font-size:12px">❌ 加载失败: ${e.message}</div>`)}}function s(e,t){let n=document.getElementById(`cmdMachineOverview`),r=document.getElementById(`cmdMachineFilter`),i=e?.machines||{};t?.machines;let a=r.value;r.innerHTML=`<option value="all">全部</option>`;let o=``,s=0;for(let[e,t]of Object.entries(i)){r.innerHTML+=`<option value="${e}">${e}</option>`;let n=t?.slots||{},i=t?.tasks?.active||null,a=t?.tasks?.counts||{},c=!t?.error,l=n?.used||0,u=n?.max||3;o+=`
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <div style="font-weight:600;font-size:12px">${c?`🟢`:`🔴`} ${e}</div>
          <div style="font-size:10px;color:var(--text2)">${l}/${u} 槽位</div>
        </div>
        <div style="display:flex;gap:4px;margin-bottom:4px">
          ${Array.from({length:u},(e,t)=>{let r=n?.slots?.find(e=>e.slot_id===t),i=r&&r.account_id;return`<div style="width:28px;height:28px;border-radius:6px;background:${i?`#22c55e`:`var(--bg3)`};border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:8px;color:${i?`#000`:`var(--text2)`}">${i?r.account_id.slice(-3):`∅`}</div>`}).join(``)}
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
      </div>`,s++}n.innerHTML=o,a&&(r.value=a)}function c(e){let t=document.getElementById(`cmdQueueDetail`),n=document.getElementById(`cmdMachineFilter`)?.value||`all`,r=e?.machines||{},i=``;for(let[e,t]of Object.entries(r)){if(n!==`all`&&e!==n)continue;let r=t?.tasks?.active||null,a=t?.tasks?.queued||[],o=t?.tasks?.counts||{},s=t?.slots?.slots||[];i+=`
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border);margin-bottom:8px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <div style="font-weight:600;font-size:13px">${e}</div>
          <div style="font-size:10px;color:var(--text2)">队列: ${a.length} | 完成: ${o.completed||0} | 失败: ${o.failed||0}</div>
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
        
        ${s.length>0?`
          <div style="display:grid;grid-template-columns:repeat(${Math.min(s.length,3)},1fr);gap:4px;margin-bottom:6px">
            ${s.map(e=>`
              <div style="background:${e.account_id?`#22c55e20`:`var(--bg3)`};border-radius:4px;padding:6px;border:1px solid var(--border);font-size:9px">
                <div style="font-weight:600">槽位${e.slot_id+1}</div>
                <div>${e.account_id||`空闲`}</div>
                ${e.current_step?`<div style="color:var(--text2)">${e.current_step}</div>`:``}
                ${e.elapsed_sec?`<div style="color:var(--text2)">${Math.floor(e.elapsed_sec/60)}分</div>`:``}
              </div>
            `).join(``)}
          </div>
        `:``}
        
        ${a.length>0?`
          <div style="font-size:10px;color:var(--text2);margin-bottom:4px">⏳ 排队中 (${a.length})</div>
          ${a.slice(0,10).map(e=>`<div style="font-size:10px;padding:2px 4px;background:var(--bg3);border-radius:3px;margin-bottom:2px">${e.priority===0?`🔴`:e.priority===1?`🟢`:`⚪`} [${e.priority===0?`P0优先`:e.priority===1?`P1日常`:`P2闲时`}] ${e.task_id?.slice(0,40)||``}</div>`).join(``)}
        `:`<div style="font-size:10px;color:var(--text2)">队列为空</div>`}
      </div>`}t.innerHTML=i||`<div style="color:var(--text2);font-size:12px;text-align:center;padding:20px">没有机器数据</div>`}export{n as loadView,r as unloadView};
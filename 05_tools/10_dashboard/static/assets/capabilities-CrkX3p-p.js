async function e(e){e.innerHTML=`
    <div style="padding:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">⚡ 能力目录</h2>
        <span id="capCount" style="font-size:12px;color:var(--text2)"></span>
      </div>
      <div id="capGroupTabs" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px"></div>
      <div id="capabilityContent"><div class="loading">加载原子能力...</div></div>
    </div>`;try{let e=await(await fetch(`/api/capabilities`)).json(),n=e.groups||[],r=e.matrix||[],i=document.getElementById(`capCount`);if(i&&(i.textContent=`共 ${e.total_items||0} 个能力`),!n.length){document.getElementById(`capabilityContent`).innerHTML=`<div class="error" style="padding:40px">暂无能力数据</div>`;return}document.getElementById(`capGroupTabs`).innerHTML=n.map((e,t)=>`<button class="btn ${t===0?`active`:``}" onclick="window._switchCapGroup(${t})"
        style="${t===0?`background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px`:`background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px`}">
        ${e.name} (${e.items.length})
      </button>`).join(``),t(n[0],r),window._switchCapGroup=function(e){document.querySelectorAll(`#capGroupTabs .btn`).forEach((t,n)=>{Object.assign(t.style,n===e?{background:`var(--primary)`,color:`#fff`,border:`none`}:{background:`var(--bg2)`,border:`1px solid var(--border)`,color:`var(--text)`})}),t(n[e],r)}}catch(t){e.innerHTML=`<div class="error">❌ 加载失败: ${t.message}</div>`}}function t(e,t){let n=document.getElementById(`capabilityContent`);if(n){if(!e||!e.items||!e.items.length){n.innerHTML=`<div class="error" style="padding:40px">暂无数据</div>`;return}n.innerHTML=`
    <div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border);overflow-x:auto">
      <table style="width:100%;font-size:12px;border-collapse:collapse">
        <thead><tr>
          ${Object.keys(e.items[0]||{}).map(e=>`<th style="text-align:left;padding:6px 8px;border-bottom:2px solid var(--border);white-space:nowrap">${e}</th>`).join(``)}
        </tr></thead>
        <tbody>
          ${e.items.map(e=>`<tr>${Object.values(e).map(e=>`<td style="padding:4px 8px;border-bottom:1px solid var(--border);font-size:11px">${e||`-`}</td>`).join(``)}</tr>`).join(``)}
        </tbody>
      </table>
    </div>`}}export{e as loadView};
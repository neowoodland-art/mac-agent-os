import{n as e,r as t,t as n}from"./index-DcP1UEin.js";async function r(r){t(r,`读取联邦心跳中...`);try{let e=(await n(`/machines`)).machines||[],t=document.getElementById(`machineCount`);if(t&&(t.textContent=`共 ${e.length} 台主机`),!e.length){r.innerHTML=`<div class="error" style="padding:40px">无心跳数据</div>`;return}r.innerHTML=`
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px" id="machineGrid">
        ${e.map(e=>i(e)).join(``)}
      </div>
    `}catch(t){e(r,`加载失败: ${t.message}`)}}function i(e){let t=e.status===`online`||e._live===!0,n=e.status===`recent`,r=e._live===!0,i=r?`#1D9E75`:t?`#22C55E`:n?`#F59E0B`:`#EF4444`,a=e._last_push_sec||0,o=e.minutes_ago||Math.round(a/60)||999,s=r?`${a}秒前`:o<60?`${o} 分钟前`:`${(o/60).toFixed(1)} 小时前`,c=e.disk_used_gb||0,l=e.disk_total_gb||1,u=Math.round(c/l*100),d=`
    <div style="height:6px;background:var(--bg3);border-radius:3px;margin:6px 0;overflow:hidden">
      <div style="height:100%;width:${u}%;background:${u>85?`var(--red)`:u>60?`var(--amber)`:`var(--green)`};border-radius:3px;transition:width .3s"></div>
    </div>`;return`
    <div style="background:var(--bg2);border-radius:var(--radius);padding:20px;border:1px solid ${t?`rgba(34,197,94,.2)`:`var(--border)`}">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
        <div style="display:flex;align-items:center;gap:10px">
          <span style="width:10px;height:10px;border-radius:50%;background:${i};display:inline-block;"></span>
          <div>
            <div style="font-weight:600;font-size:15px">${e.hostname}</div>
            ${e._uid?`<span style="font-size:10px;color:var(--text2);margin-left:6px">UID: ${e._uid}</span>`:``}
            <div style="font-size:11px;color:var(--text2)">${e.os||``}</div>
          </div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px;margin-bottom:12px">
        <div><span style="color:var(--text2)">guardd</span><br>v${e.guardd_version||`-`}</div>
        <div><span style="color:var(--text2)">最后心跳</span><br>${s}</div>
        <div><span style="color:var(--text2)">CPU 负载</span><br>${e.cpu_load||`-`}</div>
        <div><span style="color:var(--text2)">当前任务</span><br>${e.current_task||`无`}</div>
      </div>

      <div style="font-size:12px;color:var(--text2);margin-bottom:2px">磁盘: ${c.toFixed(0)}G / ${l.toFixed(0)}G</div>
      ${d}
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text2)">
        <span>已用 ${u}%</span>
        <span>剩余 ${(e.disk_avail_gb||0).toFixed(0)}G</span>
      </div>

      ${e.is_duplicate?`<div style="margin-top:8px;padding:4px 8px;background:rgba(245,158,11,.1);border-radius:4px;font-size:11px;color:var(--amber)">⚠ hostname 变更: 原名 ${e.duplicate_of||``}</div>`:``}
    </div>`}export{r as loadView};
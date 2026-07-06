import{i as e,r as t,t as n}from"./index-HbgklmvM.js";async function r(r){e(r,`读取联邦心跳中...`);try{let e=(await n(`/machines`)).machines||[],t=document.getElementById(`machineCount`);if(t&&(t.textContent=`共 ${e.length} 台主机`),!e.length){r.innerHTML=`<div class="error" style="padding:40px">无心跳数据</div>`;return}r.innerHTML=`
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px" id="machineGrid">
        ${e.map(e=>i(e)).join(``)}
      </div>
    `}catch(e){t(r,`加载失败: ${e.message}`)}}function i(e){let t=e._last_push_sec||0,n=e.status===`online`,r=e.status===`recent`,i=n?`#22C55E`:r?`#F59E0B`:`#EF4444`,a=e.minutes_ago||Math.round(t/60)||0,o=t<60?`${t}秒前`:a<60?`${a} 分钟前`:`${(a/60).toFixed(1)} 小时前`,s=e.disk_used_gb||0,c=e.disk_total_gb||1,l=Math.round(s/c*100),u=`
    <div style="height:6px;background:var(--bg3);border-radius:3px;margin:6px 0;overflow:hidden">
      <div style="height:100%;width:${l}%;background:${l>85?`var(--red)`:l>60?`var(--amber)`:`var(--green)`};border-radius:3px;transition:width .3s"></div>
    </div>`;return`
    <div style="background:var(--bg2);border-radius:var(--radius);padding:20px;border:1px solid ${n?`rgba(34,197,94,.2)`:`var(--border)`}">
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
        <div><span style="color:var(--text2)">最后心跳</span><br>${o}</div>
        <div><span style="color:var(--text2)">CPU 负载</span><br>${e.cpu_load||`-`}</div>
        <div><span style="color:var(--text2)">当前任务</span><br>${e.current_task||`无`}</div>
      </div>

      <div style="font-size:12px;color:var(--text2);margin-bottom:2px">磁盘: ${s.toFixed(0)}G / ${c.toFixed(0)}G</div>
      ${u}
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text2)">
        <span>已用 ${l}%</span>
        <span>剩余 ${(e.disk_avail_gb||0).toFixed(0)}G</span>
      </div>

      ${e.is_duplicate?`<div style="margin-top:8px;padding:4px 8px;background:rgba(245,158,11,.1);border-radius:4px;font-size:11px;color:var(--amber)">⚠ hostname 变更: 原名 ${e.duplicate_of||``}</div>`:``}
    </div>`}export{r as loadView};
async function e(e){let n=`ms_`+Math.random().toString(36).slice(2,6);e.innerHTML=`
    <div style="padding:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">📊 多机总览</h2>
        <span id="meta_${n}" style="font-size:12px;color:var(--text2)"></span>
      </div>
      <div id="grid_${n}" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:14px">
        <div class="loading">加载矩阵状态...</div>
      </div>
    </div>`,t(n)}async function t(e){let t=document.getElementById(`grid_${e}`),n=document.getElementById(`meta_${e}`);if(t)try{let e=await(await fetch(`/api/matrix/cross-machines`)).json(),r=0;try{r=(await(await fetch(`/api/matrix/system-info`)).json()).identity_dirs||0}catch{}n&&(n.textContent=`${e.total_machines} 机器 · ${e.total_accounts} 账号 · 🪪 ${r} 身份目录`);let i={},a=[];e.machines.forEach(e=>{(e.accounts||[]).forEach(t=>{i[t.id]&&i[t.id]!==e.hostname&&a.push({id:t.id,m1:i[t.id],m2:e.hostname}),i[t.id]=e.hostname})}),t.innerHTML=e.machines.map(e=>{let t=e.accounts||[],n=t.filter(t=>t.owner_machine===e.hostname||t.is_local),r=t.filter(t=>t.owner_machine!==e.hostname&&!t.is_local),i=t.filter(e=>e._status===`logged_in`),o=e.hostname===`chengzigedeAir`||e.is_local;return`<div style="background:var(--bg2);border-radius:var(--radius);padding:16px;border:1px solid var(--border)">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
          <span style="width:10px;height:10px;border-radius:50%;background:${e.online?`var(--green)`:`var(--red)`};display:inline-block"></span>
          <span style="font-weight:600;font-size:14px">${o?`🖥️`:`☁️`} ${e.hostname}</span>
          <span style="font-size:11px;color:var(--text2)">${t.length} 账号 | ${i.length} 已登录</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;margin-bottom:8px">
          <div><span style="color:var(--text2)">本机声明:</span> ${n.length}</div>
          <div><span style="color:var(--text2)">远程读取:</span> ${r.length}</div>
          <div><span style="color:var(--text2)">登录:</span> <span style="color:var(--green)">${i.length}</span></div>
          <div><span style="color:var(--text2)">蓝图:</span> ${e.blueprint_count||0}</div>
        </div>
        ${t.length?`<div style="font-size:10px;color:var(--text2);max-height:120px;overflow-y:auto">
          ${t.slice(0,20).map(e=>`<div style="display:flex;gap:6px;padding:1px 0">
              <span>${e.platform===`douyin`?`🎵`:`📕`}</span>
              <span>${e.id}</span>
              <span style="color:${e._status===`logged_in`?`var(--green)`:`var(--text2)`}">${e._status||`-`}</span>
            </div>`).join(``)}
          ${t.length>20?`<div style="color:var(--text2);margin-top:2px">... 还有 ${t.length-20} 个</div>`:``}
        </div>`:`<div style="font-size:11px;color:var(--text2)">暂无账号</div>`}
        ${a.filter(t=>t.m1===e.hostname||t.m2===e.hostname).map(e=>`<div style="margin-top:6px;padding:3px 6px;background:rgba(245,158,11,.1);border-radius:4px;font-size:10px;color:var(--amber)">⚠ 重复: ${e.id} (${e.m1} / ${e.m2})</div>`).join(``)}
      </div>`}).join(``)}catch(e){t.innerHTML=`<div class="error">❌ 加载失败: ${e.message}</div>`}}export{e as loadView};
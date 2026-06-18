async function e(e){e.innerHTML=`<div class="loading">加载中...</div>`;try{let t=((await(await fetch(`/api/matrix/sms/accounts`)).json()).accounts||[]).filter(e=>e.is_local),n=t.filter(e=>e.has_cookie),r=t.filter(e=>e.has_profile),i=`<div style="padding:16px">
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px">
        <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center">
          <div style="font-size:24px;font-weight:700;color:#6366f1">${t.length}</div>
          <div style="font-size:11px;color:var(--text2)">📱 本机账号</div>
        </div>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center">
          <div style="font-size:24px;font-weight:700;color:var(--green)">${n.length}</div>
          <div style="font-size:11px;color:var(--text2)">🔑 已登录</div>
        </div>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center">
          <div style="font-size:24px;font-weight:700;color:var(--amber)">${r.length}</div>
          <div style="font-size:11px;color:var(--text2)">📋 已采集</div>
        </div>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center">
          <div style="font-size:24px;font-weight:700;color:var(--blue)">${n.length-r.length}</div>
          <div style="font-size:11px;color:var(--text2)">🔄 待采集</div>
        </div>
      </div>`;i+=`<div class="filter-bar">
      <select id="filterStrategy_p"><option value="">全部策略</option>
        <option>口播</option><option>卡点</option><option>数字人</option><option>test</option>
      </select>
      <select id="filterStatus_p"><option value="">全部状态</option>
        <option value="completed">已完成</option><option value="failed">失败</option><option value="running">运行中</option>
      </select>
      <input id="searchInput_p" placeholder="搜索脚本名称...">
      <button onclick="window._loadProdList()">查询</button>
      <div id="pagination_p"></div>
    </div>
    <div id="prodList_p" style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);margin-top:8px;min-height:100px">
      <div class="loading">加载生产列表...</div>
    </div>`,e.innerHTML=i,window._loadProdList=window._loadProdList||async function(){let e=document.getElementById(`prodList_p`);if(e){e.innerHTML=`<div class="loading">加载中...</div>`;try{let t=document.getElementById(`filterStrategy_p`)?.value||``,n=document.getElementById(`filterStatus_p`)?.value||``,r=document.getElementById(`searchInput_p`)?.value||``,i=new URLSearchParams({limit:20});t&&i.set(`strategy`,t),n&&i.set(`status`,n),r&&i.set(`search`,r);let a=await(await fetch(`/api/productions?${i}`)).json(),o=a.productions||a.data||a||[];if(!Array.isArray(o)||!o.length){e.innerHTML=`<div style="padding:40px;color:var(--text2);font-size:12px;text-align:center">暂无生产记录</div>`;return}e.innerHTML=o.map(e=>`<div style="padding:8px;border-bottom:1px solid var(--border);font-size:12px;cursor:pointer" onclick="alert(JSON.stringify(${JSON.stringify(e).replace(/"/g,`&quot;`)},null,2))">
            <div style="font-weight:500">${e.name||e.script_name||`未知`}</div>
            <div style="font-size:10px;color:var(--text2)">${e.status||`-`} · ${e.strategy||`-`} · ${e.created_at?new Date(e.created_at).toLocaleString():``}</div>
          </div>`).join(``)}catch(t){e.innerHTML=`<div class="error">❌ ${t.message}</div>`}}},window._loadProdList()}catch(t){e.innerHTML=`<div class="error">❌ 加载失败: ${t.message}</div>`}}export{e as loadView};
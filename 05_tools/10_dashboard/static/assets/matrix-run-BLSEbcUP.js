async function e(e){e.innerHTML=`<div class="loading">⏳ 加载中...</div>`;try{let[t,n]=await Promise.all([fetch(`/api/matrix/accounts`).then(e=>e.ok?e.json():{accounts:[]}).catch(()=>({accounts:[]})),fetch(`/api/ops/history`).then(e=>e.ok?e.json():{commands:[]}).catch(()=>({commands:[]}))]),r=Array.isArray(t)?t:t.accounts||[],i=n.commands||[];r.map(e=>`<option value="${e.id}">${e.platform===`xiaohongshu`?`📕`:`🎵`} ${e.id} (${e.phone||``})</option>`).join(``),e.innerHTML=`
      <div style="font-size:18px;font-weight:600;margin-bottom:12px">🚀 批量执行</div>
      <div style="display:grid;gap:8px;background:var(--bg2);padding:12px;border-radius:10px;border:1px solid var(--border);margin-bottom:12px">
        <div><label style="font-size:12px;font-weight:600">选择账号</label>
          <div style="display:flex;gap:4px;flex-wrap:wrap;max-height:150px;overflow-y:auto;margin-top:4px">
            ${r.map(e=>`<label style="font-size:11px;display:inline-flex;align-items:center;gap:4px;padding:2px 6px;background:var(--bg3);border-radius:4px"><input type="checkbox" class="runAcct" value="${e.id}"> ${e.platform===`xiaohongshu`?`📕`:`🎵`} ${e.id}</label>`).join(``)}
          </div>
        </div>
        <div><label style="font-size:12px;font-weight:600">命令类型 <select id="runType" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:4px;font-size:11px">
          <option value="login">🔑 登录</option><option value="collect">📡 采集</option><option value="nurture">🏃 养号</option><option value="comment">💬 评论</option>
        </select></label></div>
        <div><label style="font-size:12px;font-weight:600">额外参数 <input id="runParams" placeholder='{"blueprint":"douyin_daily","rounds":3}' style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:4px;font-size:11px"></label></div>
        <button id="runBtn" style="background:var(--primary);color:#fff;border:none;padding:8px;border-radius:6px;cursor:pointer;font-size:13px">▶ 执行选中账号</button>
        <div id="runResult" style="font-size:11px"></div>
      </div>
      <div style="font-size:13px;font-weight:600;margin-bottom:8px">📋 最近执行</div>
      <div style="font-size:11px;max-height:300px;overflow-y:auto">
        ${i.length?i.slice(0,20).map(e=>`<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid var(--border);font-size:11px">
          <span>${e.status===`completed`?`✅`:e.status===`running`?`🟢`:e.status===`failed`?`❌`:`⏳`} ${e.type||`?`}</span>
          <span>${(e.accounts||[]).join(`,`)}</span><span style="color:var(--text2)">${e.message||``}</span>
          <span style="color:var(--text2)">${e.elapsed_sec||0}s</span>
        </div>`).join(``):`<span style="color:var(--text2)">暂无执行记录</span>`}
      </div>`,document.getElementById(`runBtn`).onclick=async()=>{let e=[...document.querySelectorAll(`.runAcct:checked`)].map(e=>e.value);if(!e.length){alert(`请选择至少一个账号`);return}let t=document.getElementById(`runType`).value,n={};try{n=JSON.parse(document.getElementById(`runParams`).value||`{}`)}catch{}document.getElementById(`runResult`).innerHTML=`⏳ 执行中...`;try{let r=await(await fetch(`/api/ops/run`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({type:t,accounts:e,params:n})})).json();document.getElementById(`runResult`).innerHTML=`<span style="color:var(--green)">✅ ${r.status||`已发送`} ${r.message||``}</span>`}catch(e){document.getElementById(`runResult`).innerHTML=`<span style="color:var(--red)">❌ ${e.message}</span>`}}}catch(t){e.innerHTML=`<div class="error">❌ ${t.message}</div>`}}export{e as loadView};
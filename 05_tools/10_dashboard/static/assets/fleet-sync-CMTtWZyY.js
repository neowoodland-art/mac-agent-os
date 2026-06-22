async function e(e){let t=`fs_`+Math.random().toString(36).slice(2,6);e.innerHTML=`
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">🔄 一键同步</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">通过 Git 同步三台机器（本机 / 5kecheng / 7kecheng）的最新代码</p>
      <div style="display:flex;gap:8px;margin-bottom:12px">
        <button id="btnSync_${t}" onclick="window._doFleetSync('${t}')" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">🔄 执行同步</button>
      </div>
      <div id="log_${t}" style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:400px;overflow:auto"></div>
    </div>`,window._doFleetSync=window._doFleetSync||async function(e){let t=document.getElementById(`log_${e}`),n=document.getElementById(`btnSync_${e}`);if(t){t.textContent=`⏳ 执行中...
`,n.disabled=!0,n.textContent=`⏳ 同步中...`;try{let e=await(await fetch(`/api/fleet/sync`,{method:`POST`})).json();t.textContent=e.output||JSON.stringify(e,null,2)}catch(e){t.textContent=`❌ `+e.message}n.disabled=!1,n.textContent=`🔄 执行同步`}}}export{e as loadView};
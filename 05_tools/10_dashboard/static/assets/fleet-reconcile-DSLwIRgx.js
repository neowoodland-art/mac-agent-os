async function e(e){let t=`fr_`+Math.random().toString(36).slice(2,6);e.innerHTML=`
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">🔍 对账检查</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">检查本机是否符合 ORACLE.yaml 宪法定义</p>
      <div style="display:flex;gap:8px;margin-bottom:12px">
        <button id="btnReconcile_${t}" onclick="window._doFleetReconcile('${t}')" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">🔍 执行对账</button>
      </div>
      <div id="log_${t}" style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:400px;overflow:auto"></div>
    </div>`,window._doFleetReconcile=window._doFleetReconcile||async function(e){let t=document.getElementById(`log_${e}`);if(t){t.textContent=`⏳ 执行中...
`;try{let e=await(await fetch(`/api/fleet/reconcile`,{method:`POST`})).json();t.textContent=e.output||JSON.stringify(e,null,2)}catch(e){t.textContent=`❌ `+e.message}}}}export{e as loadView};
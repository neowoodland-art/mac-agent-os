async function e(e){let t=`fe_`+Math.random().toString(36).slice(2,6);e.innerHTML=`
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">💻 远程Shell</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">在远程机器上执行命令（通过 mc remote exec）</p>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px">
        <select id="execMachine_${t}" style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px">
          <option value="5kechengdeAir">5kechengdeAir</option>
          <option value="7kecheng">7kecheng</option>
        </select>
        <input id="execCmd_${t}" placeholder="输入命令..." style="flex:1;min-width:200px;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px"
          onkeydown="if(event.key==='Enter')window._doFleetExec('${t}')">
        <button id="btnExec_${t}" onclick="window._doFleetExec('${t}')" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">➡ 执行</button>
      </div>
      <div id="log_${t}" style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:400px;overflow:auto"></div>
    </div>`,window._doFleetExec=window._doFleetExec||async function(e){let t=document.getElementById(`execMachine_${e}`)?.value,n=document.getElementById(`execCmd_${e}`)?.value,r=document.getElementById(`log_${e}`);if(!n){r.textContent=`请输入命令`;return}r.textContent=`⏳ 执行中...
`;try{let e=await(await fetch(`/api/federation/exec`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({machine:t,command:n,timeout:30})})).json();r.textContent=e.output||JSON.stringify(e,null,2)}catch(e){r.textContent=`❌ `+e.message}}}export{e as loadView};
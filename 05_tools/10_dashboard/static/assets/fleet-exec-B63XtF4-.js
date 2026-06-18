async function e(e){let t=`fe_`+Math.random().toString(36).slice(2,6);e.innerHTML=`
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">💻 远程Shell</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">在远程机器上执行命令（通过 mc remote exec）</p>

      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px">
        <select id="execMachine_${t}" style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;min-width:160px">
          <option value="">⏳ 加载机器列表...</option>
        </select>
        <input id="execCmd_${t}" placeholder="输入命令..." style="flex:1;min-width:200px;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px"
          onkeydown="if(event.key==='Enter')window._doFleetExec('${t}')">
        <button onclick="window._doFleetExec('${t}')" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">➡ 执行</button>
        <button onclick="document.getElementById('execCmd_${t}').value=''; document.getElementById('log_${t}').innerHTML=''" style="background:var(--bg2);color:var(--text);border:1px solid var(--border);padding:6px 10px;border-radius:6px;cursor:pointer;font-size:11px">✕ 清空</button>
      </div>

      <div style="margin-bottom:10px;display:flex;gap:6px;flex-wrap:wrap">
        ${[`hostname`,`df -h /`,`pgrep -a camoufox`,`ps aux | wc -l`,`curl -s localhost:9988/api/health`,`agentos guardd status`].map(e=>`<button onclick="document.getElementById('execCmd_${t}').value='${e.replace(/'/g,`\\'`)}';window._doFleetExec('${t}')" style="height:26px;background:var(--bg3);border:0.5px solid var(--border);border-radius:6px;padding:0 10px;display:inline-flex;align-items:center;font-size:11px;color:var(--text);cursor:pointer">${e}</button>`).join(``)}
      </div>

      <div id="log_${t}" style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:420px;overflow:auto"></div>

      <div id="history_${t}" style="margin-top:8px;font-size:11px;display:none">
        <div style="color:var(--text2);margin-bottom:4px">最近执行</div>
        <div id="historyList_${t}" style="display:flex;gap:6px;flex-wrap:wrap"></div>
      </div>
    </div>`;let n=document.getElementById(`execMachine_`+t);(async()=>{try{let e=(await(await fetch(`/api/machines`)).json()).machines||[];n.innerHTML=e.map(e=>`<option value="${e.hostname}">${e.hostname} ${e.status===`online`?`🟢`:`🔴`}</option>`).join(``);let t=e.find(e=>e.status===`online`);t&&(n.value=t.hostname)}catch{n.innerHTML=`<option value="">加载失败</option>`}})(),window._doFleetExec=window._doFleetExec||(async function(e){let t=document.getElementById(`execMachine_`+e)?.value,n=document.getElementById(`execCmd_`+e)?.value,i=document.getElementById(`log_`+e),a=document.getElementById(`history_`+e),o=document.getElementById(`historyList_`+e);if(!n||!t){i&&(i.innerHTML=`<span style="color:var(--red)">⚠️ 请选择机器并输入命令</span>`);return}i.innerHTML=`<span style="color:var(--text2)">⏳ 执行中...</span>
`;try{let e=await(await fetch(`/api/federation/exec`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({machine:t,command:n,timeout:30})})).json(),s=e.output||e.stdout||JSON.stringify(e,null,2),c=e.status===`error`||e.returncode>0||s.includes(`❌`),l=``,u=s.split(`
`);for(let e of u){let t=e.trim();if(!t){l+=`<br>`;continue}t.startsWith(`$ `)?l+=`<span style="color:var(--green)">${r(t)}</span>\n`:t.startsWith(`❌`)||t.toLowerCase().includes(`error`)||t.toLowerCase().includes(`failed`)?l+=`<span style="color:var(--red)">${r(t)}</span>\n`:t.startsWith(`✅`)||t.startsWith(`✓`)||t.startsWith(`+`)?l+=`<span style="color:var(--green)">${r(t)}</span>\n`:/^\d/.test(t)||t.includes(`GB`)||t.includes(`%`)?l+=`<span style="color:var(--blue)">${r(t)}</span>\n`:l+=`${r(t)}\n`}c&&(l=`<div style="padding:6px 10px;background:rgba(227,75,74,.1);border-radius:4px;margin-bottom:8px;color:var(--red)">❌ 命令返回非零退出码</div>
`+l),i.innerHTML=`<span style="color:var(--green)">$ ${r(n)}</span>\n`+l;let d=new Date,f=d.getHours().toString().padStart(2,`0`)+`:`+d.getMinutes().toString().padStart(2,`0`),p=c?`❌`:`✅`,m=document.createElement(`div`);if(m.style.cssText=`background:var(--bg3);padding:4px 8px;border-radius:4px;font-size:10px;white-space:nowrap`,m.innerHTML=`${p} ${t}: ${n.slice(0,18)}${n.length>18?`..`:``} (${f})`,c?m.style.color=`var(--red)`:m.style.color=`var(--green)`,o)for(o.prepend(m);o.children.length>10;)o.removeChild(o.lastChild);a&&(a.style.display=``)}catch(e){i.innerHTML=`<span style="color:var(--red)">❌ ${r(e.message)}</span>`}});function r(e){return String(e).replace(/&/g,`&amp;`).replace(/</g,`&lt;`).replace(/>/g,`&gt;`).replace(/"/g,`&quot;`)}}export{e as loadView};
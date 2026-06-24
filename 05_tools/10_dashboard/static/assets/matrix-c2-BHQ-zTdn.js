async function e(e){e.innerHTML=`<div class="loading">⏳ 加载中...</div>`;try{let t=Date.now().toString(36),n=await fetch(`/api/c2/machines`),r=n.ok?await n.json():{machines:[]},i=Array.isArray(r)?r:r.machines||[];e.innerHTML=`
      <div style="padding:16px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
          <h2 style="font-size:18px;margin:0">🖥️ 远程控制</h2>
          <span style="font-size:12px;color:var(--text2)">
            <strong>${i.length}</strong> 台机器
            <span style="margin-left:8px;font-size:11px">🟢在线 <strong id="onlineCount_${t}">0</strong></span>
            <span style="margin-left:4px;font-size:11px">🔴离线 <strong id="offlineCount_${t}">0</strong></span>
          </span>
        </div>
        <div id="machineGrid_${t}" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:10px"></div>
      </div>`;let a=document.getElementById(`machineGrid_`+t);if(!a){e.innerHTML=`<div class="error">❌ 渲染错误: 容器丢失</div>`;return}function o(e){let n=e.filter(e=>e.online!==!1),r=document.getElementById(`onlineCount_`+t),i=document.getElementById(`offlineCount_`+t);if(r&&(r.textContent=n.length),i&&(i.textContent=e.length-n.length),!e.length){a.innerHTML=`<div style="font-size:12px;color:var(--text2);padding:40px;text-align:center">暂无机器数据</div>`;return}a.innerHTML=e.map(e=>`<div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div style="display:flex;align-items:center;gap:6px">
              <span style="width:8px;height:8px;border-radius:50%;background:${e.online===!1?`var(--red, #ef4444)`:`var(--green, #22c55e)`};display:inline-block"></span>
              <span style="font-weight:600;font-size:13px">${e.hostname||e.name||e.id}</span>
            </div>
            <span style="font-size:10px;color:var(--text2)">${e.ip||e.address||``}</span>
          </div>
          <div style="font-size:11px;color:var(--text2);margin-bottom:8px">
            ${e.os?`<span style="margin-right:8px">${e.os}</span>`:``}
            ${e.platform?`<span>${e.platform}</span>`:``}
            ${e.version?`<span style="margin-left:8px">v${e.version}</span>`:``}
          </div>
          <div style="display:flex;gap:4px;flex-wrap:wrap">
            <button onclick="window._sendC2('${e.id||e.hostname||e.name}','shell','')" style="background:var(--bg3);border:1px solid var(--border);border-radius:4px;padding:3px 10px;font-size:10px;cursor:pointer">💻 Shell</button>
            <button onclick="window._sendC2('${e.id||e.hostname||e.name}','exec','')" style="background:var(--bg3);border:1px solid var(--border);border-radius:4px;padding:3px 10px;font-size:10px;cursor:pointer">⚡ 执行</button>
            <button onclick="window._sendC2('${e.id||e.hostname||e.name}','file','')" style="background:var(--bg3);border:1px solid var(--border);border-radius:4px;padding:3px 10px;font-size:10px;cursor:pointer">📁 文件</button>
            <button onclick="window._sendC2('${e.id||e.hostname||e.name}','ping','')" style="background:var(--bg3);border:1px solid var(--border);border-radius:4px;padding:3px 10px;font-size:10px;cursor:pointer">🏓 Ping</button>
            <button onclick="window._showCustomC2('${e.id||e.hostname||e.name}')" style="background:var(--primary);color:#fff;border:none;border-radius:4px;padding:3px 10px;font-size:10px;cursor:pointer">✏️ 自定义</button>
          </div>
          <div id="c2Result_${(e.id||e.hostname||e.name).replace(/[^a-zA-Z0-9]/g,`_`)}" style="margin-top:6px;font-size:10px;color:var(--text2);min-height:0"></div>
        </div>`).join(``)}o(i),window._sendC2=async(e,t,n)=>{let r=`c2Result_`+e.replace(/[^a-zA-Z0-9]/g,`_`),i=document.getElementById(r);i&&(i.innerHTML=`<span style="color:var(--amber)">⏳ 发送中...</span>`);try{let r=await fetch(`/api/c2/send`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({target:e,type:t,params:n})}),a=await r.json();if(i){let e=a.output||a.result||a.message||JSON.stringify(a);i.innerHTML=`<span style="color:${r.ok?`var(--green)`:`var(--red)`}">${r.ok?`✅`:`❌`} ${e}</span>`}}catch(e){i&&(i.innerHTML=`<span style="color:var(--red)">❌ ${e.message}</span>`)}},window._showCustomC2=e=>{let t=document.createElement(`div`);t.style.cssText=`position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:99999;display:flex;align-items:center;justify-content:center`,t.innerHTML=`
        <div style="background:var(--bg2);border-radius:12px;padding:20px;max-width:400px;width:90%">
          <div style="font-size:15px;font-weight:600;margin-bottom:12px">✏️ 发送命令 → ${e}</div>
          <div style="display:grid;gap:8px;font-size:12px">
            <label>类型
              <select id="customC2Type" style="width:100%;padding:4px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px">
                <option value="shell">💻 Shell</option>
                <option value="exec">⚡ 执行</option>
                <option value="file">📁 文件</option>
                <option value="ping">🏓 Ping</option>
                <option value="custom">🔧 自定义</option>
              </select>
            </label>
            <label>参数
              <textarea id="customC2Params" rows="4" placeholder='JSON 格式或文本参数' style="width:100%;padding:4px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:11px;resize:vertical"></textarea>
            </label>
          </div>
          <div style="display:flex;gap:6px;justify-content:flex-end;margin-top:12px">
            <button onclick="this.closest('div[style]').parentElement.remove()" style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">取消</button>
            <button onclick="window._doCustomC2('${e}')" style="background:var(--primary);color:#fff;border:none;border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">🚀 发送</button>
          </div>
        </div>`,document.body.appendChild(t)},window._doCustomC2=e=>{let t=document.getElementById(`customC2Type`)?.value||`shell`,n=document.getElementById(`customC2Params`)?.value||``,r=n;try{r=JSON.parse(n)}catch{}window._sendC2(e,t,r),document.querySelector(`div[style*="position:fixed"]`)?.remove()}}catch(t){e.innerHTML=`<div class="error">❌ ${t.message||t}</div>`}}export{e as loadView};
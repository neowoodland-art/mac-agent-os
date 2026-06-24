async function e(e){e.innerHTML=`<div class="loading">⏳ 加载中...</div>`;try{let[t,n]=await Promise.all([fetch(`/api/matrix/export/list`).then(e=>e.ok?e.json():{exports:[]}).catch(()=>({exports:[]})),fetch(`/api/matrix/profiles`).then(e=>e.ok?e.json():{profiles:{}}).catch(()=>({profiles:{}}))]),r=t.exports||[];e.innerHTML=`
      <div style="font-size:18px;font-weight:600;margin-bottom:12px">📦 导入导出</div>
      ${r.length?`<div style="font-size:12px;margin-bottom:8px">已有导出包:</div>
        <table style="width:100%;font-size:11px;border-collapse:collapse">
          <tr style="border-bottom:1px solid var(--border);color:var(--text2);font-size:10px"><th style="padding:4px;text-align:left">名称</th><th style="padding:4px;text-align:left">账号数</th><th style="padding:4px;text-align:left">时间</th><th style="padding:4px">操作</th></tr>
          ${r.map(e=>`<tr style="border-bottom:1px solid var(--border)"><td style="padding:4px">${e.name}</td><td style="padding:4px">${e.count||0}</td><td style="padding:4px">${e.created_at||`-`}</td><td style="padding:4px"><button onclick="fetch('/api/matrix/export/download/${e.id}').then(r=>r.blob()).then(b=>{const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='${e.name}.json';a.click()})" style="background:var(--bg3);border:1px solid var(--border);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">⬇下载</button></td></tr>`).join(``)}
        </table>`:`<div style="color:var(--text2);font-size:12px;margin-bottom:12px">暂无导出包</div>`}
      <hr style="border-color:var(--border);margin:12px 0">
      <div style="font-size:13px;font-weight:600;margin-bottom:8px">快速导出</div>
      <button onclick="fetch('/api/matrix/export/export',{method:'POST'}).then(()=>location.reload())" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">📤 导出所有账号</button>
      <hr style="border-color:var(--border);margin:12px 0">
      <div style="font-size:13px;font-weight:600;margin-bottom:8px">快捷导入</div>
      <input type="file" id="importFile" style="font-size:12px;margin-bottom:8px">
      <button onclick="(async()=>{const f=document.getElementById('importFile').files[0];if(!f)return;const fd=new FormData();fd.append('file',f);await fetch('/api/matrix/import/import',{method:'POST',body:fd});location.reload()})()" style="background:#6366f1;color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">📥 导入</button>`}catch(t){e.innerHTML=`<div class="error">❌ ${t.message}</div>`}}export{e as loadView};
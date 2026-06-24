async function e(e){e.innerHTML=`<div class="loading">⏳ 加载中...</div>`;try{let t=(await(await fetch(`/api/matrix/characters/list`)).json()).characters||[];e.innerHTML=`
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">🧑 角色管理 <span style="font-size:12px;color:var(--text2)">${t.length} 个</span></h2>
        <button onclick="location.reload()" style="background:var(--bg3);border:1px solid var(--border);padding:5px 12px;border-radius:5px;cursor:pointer;font-size:12px">🔄 刷新</button>
      </div>
      ${t.length?`<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px">
        ${t.map(e=>`<div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
          <div style="font-weight:600;font-size:13px">${e.name}</div>
          <div style="font-size:11px;color:var(--text2);margin-top:4px">${e.description||``}</div>
          <div style="font-size:10px;color:var(--text2);margin-top:4px">🆔 ${e.id} · ${e.platform||`通用`} · 📅 ${e.created_at?e.created_at.slice(0,10):``}</div>
        </div>`).join(``)}
      </div>`:`<div style="color:var(--text2);font-size:12px">暂无角色</div>`}
      <div style="margin-top:12px"><button onclick="alert('新建角色功能尚未实现')" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">+ 新建角色</button></div>`}catch(t){e.innerHTML=`<div class="error">❌ ${t.message}</div>`}}export{e as loadView};
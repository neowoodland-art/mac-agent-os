async function e(e){e.innerHTML=`<div class="loading">加载中...</div>`;try{let[t,n]=await Promise.all([fetch(`/api/matrix/blueprints`),fetch(`/api/matrix/atom-ops`)]),r=await t.json(),i=await n.json(),a=Array.isArray(r)?r:r.blueprints||[],o=i.ops||[];window._matrixOps={},o.forEach(e=>{window._matrixOps[e.name]=e});let s={douyin:`🎵 抖音`,xiaohongshu:`📕 小红书`},c={douyin:[],xiaohongshu:[]};a.forEach(e=>{let t=e.platform||`douyin`;c[t]&&c[t].push(e)});let l=`<div style="padding:16px">`;l+=`<div style="display:flex;gap:10px;margin-bottom:10px;font-size:12px;color:var(--text2)">
      <span>📋 蓝图库: <strong>${a.length}</strong></span>
      <span>🎵 抖音: <strong>${c.douyin.length}</strong></span>
      <span>📕 小红书: <strong>${c.xiaohongshu.length}</strong></span>
    </div>`,Object.entries(c).forEach(([e,t])=>{t.length&&(l+=`<div style="background:var(--bg2);border-radius:var(--radius);padding:10px;border:1px solid var(--border);margin-bottom:8px">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">${s[e]||e} (${t.length})</div>`,t.forEach(e=>{let t=e.steps||e.ops||[];l+=`<div style="background:var(--bg3);border-radius:6px;padding:8px;margin-bottom:4px;border:1px solid var(--border)">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-weight:600;font-size:12px">${e.name}</span>
            <span style="font-size:10px;color:var(--text2)">${t.length} 步</span>
          </div>
          <div style="font-size:10px;color:var(--text2);margin-top:2px">${t.map((e,t)=>`${t+1}. ${e.op||e.name||``}`).join(` · `)}
          </div>
        </div>`}),l+=`</div>`)}),l+=`<div style="background:var(--bg2);border-radius:var(--radius);padding:10px;border:1px solid var(--border)">
      <div style="font-weight:600;font-size:13px;margin-bottom:6px">⚙️ 原子操作 (${o.length})</div>`;let u={};o.forEach(e=>{let t=e.platform||`通用`;u[t]||(u[t]=[]),u[t].push(e)}),Object.entries(u).forEach(([e,t])=>{l+=`<div style="margin-bottom:4px">
        <div style="font-size:11px;font-weight:500;color:var(--text2);margin-bottom:2px">${e}</div>
        <div style="display:flex;flex-wrap:wrap;gap:3px">${t.map(e=>`<span style="font-size:10px;background:var(--bg3);padding:2px 6px;border-radius:4px;border:1px solid var(--border)">${e.name}</span>`).join(``)}</div>
      </div>`}),l+=`</div></div>`,e.innerHTML=l}catch(t){e.innerHTML=`<div class="error">❌ 加载失败: ${t.message}</div>`}}export{e as loadView};
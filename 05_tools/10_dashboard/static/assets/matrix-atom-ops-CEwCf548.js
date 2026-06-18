async function e(e){e.innerHTML=`<div class="loading">加载中...</div>`;try{let t=(await(await fetch(`/api/matrix/atom-ops`)).json()).ops||[],n={};t.forEach(e=>{let t=e.platform||`通用`;n[t]||(n[t]=[]),n[t].push(e)});let r={douyin:`🎵 抖音`,xiaohongshu:`📕 小红书`,通用:`⚙️ 通用`},i=`<div style="padding:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <h2 style="font-size:18px;margin:0">⚙️ 原子操作</h2>
        <span style="font-size:12px;color:var(--text2)">共 ${t.length} 个操作</span>
      </div>`;Object.entries(n).forEach(([e,t])=>{let n={};t.forEach(e=>{let t=e.category||`其他`;n[t]||(n[t]=[]),n[t].push(e)});let a={navigation:`🏠 导航`,browse:`📱 浏览`,interact:`💡 交互`,utility:`⏳ 工具`};i+=`<div style="margin-bottom:16px">
        <div style="font-size:14px;font-weight:700;margin-bottom:10px;padding:6px 10px;border-radius:6px;background:var(--bg3)">${r[e]||e} <span style="font-weight:400;font-size:11px;color:var(--text2)">(${t.length})</span></div>`,Object.entries(n).forEach(([e,t])=>{i+=`<div style="margin-bottom:8px">
          <div style="font-size:11px;color:var(--text2);margin-bottom:4px;padding-left:4px">${a[e]||e}</div>
          <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:4px">`,t.forEach(e=>{i+=`<div style="background:var(--bg3);border-radius:6px;padding:6px 8px;border:1px solid var(--border)">
            <div style="font-size:11px;font-weight:500">${e.name}</div>
            <div style="font-size:9px;color:var(--text2);margin-top:1px">${e.description||e.desc||`-`}</div>
          </div>`}),i+=`</div></div>`}),i+=`</div>`}),i+=`</div>`,e.innerHTML=i}catch(t){e.innerHTML=`<div class="error">❌ 加载失败: ${t.message}</div>`}}export{e as loadView};
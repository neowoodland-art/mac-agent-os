async function e(e){e.innerHTML=`<div class="loading">加载中...</div>`;try{let t=await(await fetch(`/api/matrix/corpus`)).json(),n=t.categories||t.corpus||[],r={};n.forEach(e=>{let t=e.platform===`xiaohongshu`?`📕 小红书`:`🎵 抖音`;r[t]||(r[t]=[]),r[t].push(e)});let i=`<div style="padding:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <h2 style="font-size:18px;margin:0">📚 语料库</h2>
        <span style="font-size:12px;color:var(--text2)">共 ${n.length} 个分类 · ${t.total_comments||0} 条评论</span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px">`;Object.entries(r).forEach(([e,t])=>{i+=`<div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:14px;margin-bottom:10px">${e}</div>
        <table style="width:100%;font-size:11px;border-collapse:collapse">
        <thead><tr><th style="text-align:left;padding:4px;border-bottom:1px solid var(--border)">分类</th><th style="padding:4px;border-bottom:1px solid var(--border)">权重</th><th style="padding:4px;border-bottom:1px solid var(--border)">评论数</th></tr></thead>
        <tbody>${t.map(e=>`<tr>
          <td style="padding:4px;border-bottom:1px solid var(--border)">${e.name}</td>
          <td style="padding:4px;border-bottom:1px solid var(--border);text-align:center">${e.weight||`-`}</td>
          <td style="padding:4px;border-bottom:1px solid var(--border);text-align:center">${e.count||e.comment_count||0}</td>
        </tr>`).join(``)}</tbody></table>
      </div>`}),i+=`</div></div>`,e.innerHTML=i}catch(t){e.innerHTML=`<div class="error">❌ 加载失败: ${t.message}</div>`}}export{e as loadView};
var e=`/api`,t={sharer:`分享型`,questioner:`提问型`,sympathizer:`共情型`,skeptic:`质疑型`,sufferer:`患者型`,filler:`灌水型`,expert_ref:`推荐型`},n=[],r={},i=[];async function a(t){t.innerHTML=`<div class="loading">⏳ 加载评论工作台...</div>`;try{n=(await(await fetch(`${e}/comment-workbench/roles`)).json()).roles||[],r={},n.forEach(e=>{r[e.id]=e.default_pct}),o(t)}catch(e){t.innerHTML=`<div class="error">❌ ${e.message||e}</div>`}}function o(e){let t=Object.values(r).reduce((e,t)=>e+t,0),i=Math.abs(t-1)<.01;e.innerHTML=`
    <div style="padding:16px;max-width:900px">

      <!-- ═══ 顶部：标题 + 操作按钮 ═══ -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">💬 评论工作台</h2>
        <div style="display:flex;gap:6px">
          <button onclick="window._cwLoadRoles()" style="background:var(--bg3);border:1px solid var(--border);padding:4px 10px;border-radius:6px;cursor:pointer;font-size:11px">🔄 刷新角色</button>
        </div>
      </div>

      <!-- ═══ 第一步：视频信息 ═══ -->
      <div style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-bottom:10px">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">📹 视频信息</div>
        <div style="display:flex;gap:6px">
          <input id="cwVideoTitle" type="text" placeholder="视频标题（必填）"
                 style="flex:1;padding:6px 10px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:12px">
          <input id="cwVideoTags" type="text" placeholder="标签（可选，逗号分隔）"
                 style="width:200px;padding:6px 10px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:12px">
        </div>
      </div>

      <!-- ═══ 第二步：角色比例滑条 ═══ -->
      <div style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-bottom:10px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="font-weight:600;font-size:13px">🎭 角色比例</span>
          <span id="cwPctStatus" style="font-size:11px;color:${i?`var(--green)`:`var(--red)`}">
            总计 ${(t*100).toFixed(0)}% ${i?`✅`:`⚠️ 需等于 100%`}
          </span>
        </div>
        <div id="cwRoleSliders" style="display:grid;gap:6px">
          ${n.map(e=>s(e)).join(``)}
        </div>
      </div>

      <!-- ═══ 第三步：生成设置 ═══ -->
      <div style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-bottom:10px">
        <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
          <label style="font-size:11px;display:flex;align-items:center;gap:4px">
            生成条数
            <input id="cwTotal" type="number" value="30" min="5" max="100"
                   style="width:60px;padding:3px 6px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:11px;text-align:center">
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px">
            长评占比
            <input id="cwLongRatio" type="range" min="0" max="100" value="20"
                   oninput="document.getElementById('cwLongRatioVal').textContent=this.value+'%'"
                   style="width:100px">
            <span id="cwLongRatioVal" style="font-size:11px;color:var(--text2);min-width:35px">20%</span>
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px">
            <input type="checkbox" id="cwAiEnhance" checked>
            🧠 AI 增强改写
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px">
            <input type="checkbox" id="cwAutoDispatch" checked>
            ✅ 生成后自动分发
          </label>
          <button id="cwGenerateBtn" onclick="window._cwGenerate()"
                  style="background:var(--primary);color:#fff;border:none;padding:6px 16px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600">🚀 生成评论</button>
        </div>
      </div>

      <!-- ═══ 第四步：预览编排 ═══ -->
      <div id="cwPreview" style="display:none">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="font-weight:600;font-size:13px">📝 生成预览</span>
          <div style="display:flex;gap:6px">
            <span id="cwPreviewCount" style="font-size:11px;color:var(--text2)"></span>
            <button onclick="window._cwRegenerate()" style="background:var(--bg3);border:1px solid var(--border);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">🔄 重新生成</button>
            <button onclick="window._cwDispatch()" style="background:var(--primary);color:#fff;border:none;padding:3px 12px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600">✅ 确认分发</button>
          </div>
        </div>
        <div id="cwCommentList" style="display:grid;gap:4px"></div>
      </div>

      <!-- ═══ 第五步：分发结果 ═══ -->
      <div id="cwResult" style="display:none;background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-top:10px">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">📊 分发结果</div>
        <div id="cwResultContent" style="font-size:11px;line-height:1.6"></div>
      </div>

    </div>
  `}function s(e){let t=(r[e.id]||0)*100,n=c(e.id);return`
    <div style="display:flex;align-items:center;gap:8px;font-size:11px">
      <span style="min-width:55px;font-weight:500">${e.label}</span>
      <input type="range" min="0" max="100" value="${Math.round(t)}"
             data-role="${e.id}"
             oninput="window._cwUpdatePct('${e.id}', this.value)"
             style="flex:1;height:6px;accent-color:${n}">
      <span id="cwPct_${e.id}" style="min-width:35px;text-align:right;color:var(--text2)">${Math.round(t)}%</span>
      <span style="font-size:9px;color:var(--text2)">${e.count}条</span>
    </div>
  `}function c(e){return{filler:`#8b8fa3`,questioner:`#3b82f6`,sharer:`#22c55e`,sympathizer:`#f59e0b`,sufferer:`#ef4444`,skeptic:`#8b5cf6`,expert_ref:`#06b6d4`}[e]||`#3b82f6`}window._cwUpdatePct=(e,t)=>{r[e]=parseInt(t)/100,document.getElementById(`cwPct_${e}`).textContent=`${t}%`;let n=Object.values(r).reduce((e,t)=>e+t,0),i=Math.abs(n-1)<.01,a=document.getElementById(`cwPctStatus`);a&&(a.textContent=`总计 ${(n*100).toFixed(0)}% ${i?`✅`:`⚠️ 需等于 100%`}`)},window._cwLoadRoles=async()=>{let t=document.querySelector(`#cwRoleSliders`);if(t)try{n=(await(await fetch(`${e}/comment-workbench/roles`)).json()).roles||[],n.forEach(e=>{_r.id in r||(r[e.id]=e.default_pct)}),t.innerHTML=n.map(e=>s(e)).join(``)}catch(e){alert(`❌ 加载角色失败: `+e.message)}},window._cwGenerate=async()=>{let t=document.getElementById(`cwVideoTitle`)?.value?.trim();if(!t){alert(`请填写视频标题`);return}let n=document.getElementById(`cwGenerateBtn`);n.textContent=`⏳ 生成中...`,n.disabled=!0;let a=document.getElementById(`cwVideoTags`)?.value?.trim()||``,o=parseInt(document.getElementById(`cwTotal`)?.value||`30`),s=parseInt(document.getElementById(`cwLongRatio`)?.value||`20`)/100,c=document.getElementById(`cwAiEnhance`)?.checked||!1;try{i=(await(await fetch(`${e}/comment-workbench/generate`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({video_title:t,video_tags:a?a.split(/[,，]/).map(e=>e.trim()).filter(Boolean):[],role_distribution:r,total:o,ai_enhance:c,long_ratio:s})})).json()).comments||[],l()}catch(e){alert(`❌ `+e.message)}n.textContent=`🚀 生成评论`,n.disabled=!1};function l(){let e=document.getElementById(`cwPreview`),n=document.getElementById(`cwCommentList`),r=document.getElementById(`cwPreviewCount`);!e||!n||(e.style.display=`block`,r&&(r.textContent=`共 ${i.length} 条`),n.innerHTML=i.map((e,n)=>{let r=c(e.role),i=e.is_long?` 📖`:``;return`
      <div style="display:flex;align-items:center;gap:6px;padding:4px 8px;background:var(--bg3);border-radius:4px;font-size:11px;border-left:3px solid ${r}">
        <span style="font-size:9px;color:var(--text2);min-width:20px">#${n+1}</span>
        <span style="font-size:9px;padding:1px 5px;border-radius:3px;background:${r}20;color:${r};min-width:45px;text-align:center">${e.role_label||t[e.role]||e.role}${i}</span>
        <span style="flex:1;color:var(--text)">${u(e.text)}</span>
        <button onclick="window._cwEditComment(${n})" style="background:none;border:none;cursor:pointer;font-size:12px;opacity:.5" title="编辑">✏️</button>
        <button onclick="window._cwDeleteComment(${n})" style="background:none;border:none;cursor:pointer;font-size:12px;opacity:.3" title="删除">✕</button>
      </div>
    `}).join(``))}window._cwEditComment=e=>{let n=i[e];if(!n)return;let r=document.createElement(`div`);r.style.cssText=`position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:99999;display:flex;align-items:center;justify-content:center`,r.onclick=e=>{e.target===r&&r.remove()},r.innerHTML=`
    <div style="background:var(--bg2);border-radius:12px;padding:20px;max-width:500px;width:90%">
      <div style="font-size:14px;font-weight:600;margin-bottom:8px">✏️ 编辑评论 #${e+1}</div>
      <div style="font-size:11px;color:var(--text2);margin-bottom:6px">角色：${n.role_label||t[n.role]||n.role}</div>
      <textarea id="cwEditText" style="width:100%;min-height:80px;padding:6px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:12px">${u(n.text)}</textarea>
      <div style="display:flex;gap:6px;justify-content:flex-end;margin-top:8px">
        <button onclick="this.closest('div[style]').parentElement.remove()" style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">取消</button>
        <button onclick="window._cwSaveEdit(${e})" style="background:var(--primary);color:#fff;border:none;border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">✅ 保存</button>
      </div>
    </div>`,document.body.appendChild(r)},window._cwSaveEdit=e=>{let t=document.getElementById(`cwEditText`)?.value?.trim();t&&(i[e]&&(i[e].text=t),document.querySelector(`div[style*="position:fixed"]`)?.remove(),l())},window._cwDeleteComment=e=>{i.splice(e,1),l()},window._cwRegenerate=()=>{window._cwGenerate()},window._cwDispatch=async()=>{if(!i.length){alert(`没有可分发的评论`);return}if(!confirm(`确认分发 ${i.length} 条评论？`))return;let n=document.getElementById(`cwAutoDispatch`)?.checked||!1,r=document.getElementById(`cwResult`),a=document.getElementById(`cwResultContent`);if(r.style.display=`block`,a.innerHTML=`⏳ 处理中...`,!n){a.innerHTML=`
      <div style="margin-bottom:6px;color:var(--text2)">✅ 已生成 ${i.length} 条评论（未分发）</div>
      <div style="font-size:10px;background:var(--bg3);padding:8px;border-radius:4px;white-space:pre-wrap;max-height:300px;overflow-y:auto">
        ${i.map((e,n)=>`#${n+1} [${e.role_label||t[e.role]||e.role}] ${e.text}`).join(`
`)}
      </div>
      <button onclick="navigator.clipboard.writeText(document.querySelector('#cwResultContent div:last-child').textContent)" style="margin-top:6px;background:var(--bg3);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">📋 复制全部</button>
    `;return}let o=0,s=0,c=[];for(let n=0;n<i.length;n++){let r=i[n];a.innerHTML=`⏳ 分发中 ${n+1}/${i.length}...`;try{let i=await(await fetch(`${e}/ops/run`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({type:`smart_comment`,accounts:[],params:{urls:[document.getElementById(`cwVideoTitle`)?.value?.trim()||``],direction:`praise`,custom_comment:r.text}})})).json();i.status===`accepted`||i.status===`ok`?(o++,c.push(`#${n+1} [${r.role_label||t[r.role]||r.role}] ✅`)):(s++,c.push(`#${n+1} [${r.role_label||t[r.role]||r.role}] ❌ ${i.message||i.error||``}`))}catch(e){s++,c.push(`#${n+1} ❌ ${e.message}`)}}a.innerHTML=`
    <div style="margin-bottom:6px;font-weight:600">✅ 完成：成功 ${o} / 失败 ${s}</div>
    <div style="font-size:10px;background:var(--bg3);padding:8px;border-radius:4px;max-height:300px;overflow-y:auto">
      ${c.join(`<br>`)}
    </div>
  `};function u(e){return e?String(e).replace(/&/g,`&amp;`).replace(/</g,`&lt;`).replace(/>/g,`&gt;`).replace(/"/g,`&quot;`).replace(/'/g,`&#39;`):``}export{a as loadView};
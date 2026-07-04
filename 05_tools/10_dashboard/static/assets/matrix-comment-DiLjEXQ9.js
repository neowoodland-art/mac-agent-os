import{n as e,t}from"./index-BKzPl-uu.js";import{t as n}from"./account-selector-D87mja1n.js";var r=null,i=``,a=[];async function o(e,o){i=e.id||`sc`,e.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border)">
        <!-- 标题 -->
        <div style="font-weight:600;font-size:14px;margin-bottom:10px">
          💬 定向评论
          <span style="font-size:10px;color:var(--text2);font-weight:400">分析预览后手动分发，或一键分析+自动分发</span>
        </div>

        <!-- 账号选择 -->
        <div id="acctList_${i}" style="margin-bottom:8px"><div class="loading">⏳ 加载账号列表...</div></div>

        <!-- 参数输入 -->
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
          <textarea id="urls_${i}" placeholder="视频链接（每行一个，支持多个）" rows="3"
                    style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
          <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:160px">
            <select id="dir_${i}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
              <option value="praise">👍 称赞</option>
              <option value="question">🤔 提问</option>
              <option value="empathy">💗 共鸣</option>
              <option value="agree">✅ 认同</option>
            </select>
            <select id="corpus_${i}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
              <option value="">🌐 自动匹配</option>
            </select>
            <div style="display:flex;gap:4px">
              <button id="btn_analyze_${i}" onclick="window._sc_analyze('${i}')"
                      style="flex:1;background:var(--primary);color:#fff;border:none;padding:5px 8px;border-radius:4px;cursor:pointer;font-size:11px">🔍 分析预览</button>
              <button id="btn_go_${i}" onclick="window._sc_go('${i}')"
                      style="flex:1;background:#16a34a;color:#fff;border:none;padding:5px 8px;border-radius:4px;cursor:pointer;font-size:11px">🚀 一键执行</button>
            </div>
          </div>
        </div>

        <!-- 状态/结果 -->
        <div id="result_${i}" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>

      <!-- 分析结果预览区 -->
      <div id="preview_${i}" style="display:none;margin-top:10px"></div>
    </div>`;try{let[e,o]=await Promise.all([t(`/matrix/accounts`),t(`/matrix/corpus`).catch(()=>({categories:[]}))]),s=Array.isArray(e)?e:e.accounts||[];a=o.categories||[];let c=document.getElementById(`acctList_${i}`);c&&(r=n(c,{accounts:s,checkAll:!1,height:`180px`,showBlueprint:!1,showCollectTime:!1}))}catch(e){let t=document.getElementById(`acctList_${i}`);t&&(t.innerHTML=`<div class="error">❌ ${e.message}</div>`)}let c=document.getElementById(`corpus_${i}`);c&&a.forEach(e=>{let t=document.createElement(`option`);t.value=e.name,t.textContent=`${e.name} (${(e.accessible||[]).join(`,`)||`通用`})`,c.appendChild(t)}),o&&o.accounts&&r&&setTimeout(()=>{let e=o.accounts;document.querySelectorAll(`#acctList_${i} .acct-cb`).forEach(t=>{e.includes(t.value)&&(t.checked=!0)})},300),s(i)}function s(n){window[`_sc_ready_${n}`]||(window[`_sc_ready_${n}`]=!0,window._sc_modeChange=e=>{let t=document.querySelector(`input[name="mode_${e}"]:checked`).value===`smart`;document.getElementById(`btn_analyze_${e}`).style.display=t?``:`none`,document.getElementById(`btn_go_${e}`).style.display=t?`none`:``,t||(document.getElementById(`preview_${e}`).style.display=`none`)},window._sc_analyze=async e=>{let n=r?.getSelected()||[],i=document.getElementById(`urls_${e}`)?.value,a=document.getElementById(`dir_${e}`)?.value||`praise`,o=document.getElementById(`corpus_${e}`)?.value||``,s=document.getElementById(`result_${e}`),l=document.getElementById(`preview_${e}`);if(!i||!i.trim()){s.textContent=`请填写至少一个视频链接`;return}let u=i.split(`
`).map(e=>e.trim()).filter(e=>e);if(!u.length){s.textContent=`请填写有效的视频链接`;return}if(!n.length){s.textContent=`请先选择要执行的账号`;return}s.textContent=`⏳ 正在分析 ${u.length} 个视频...`,l.style.display=`none`;let d=n[0].id;try{let r=(await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`smart_comment`,accounts:[d],params:{urls:u,direction:a,corpus_category:o||void 0,preview:!0}})})).preview||{},i=Object.entries(r);if(!i.length){s.textContent=`⚠️ 分析完成但没有返回结果`;return}l.innerHTML=`
        <div style="font-weight:600;font-size:12px;margin-bottom:6px;color:var(--text)">📋 分析结果（共 ${i.length} 个视频）
          <span style="font-size:10px;color:var(--text2);font-weight:400"> — 可修改预评论后确认分发</span>
        </div>
        ${i.map(([e,t])=>`
          <div style="background:var(--bg2);border-radius:6px;padding:8px 10px;border:1px solid var(--border);margin-bottom:4px">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
              <span style="font-size:11px;color:var(--text2);max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${c(e.slice(0,60))}</span>
              <span class="industry-tag" style="font-size:9px;padding:1px 6px;border-radius:3px;background:${t.industry===`health`?`rgba(34,197,94,.15)`:`var(--bg3)`};color:${t.industry===`health`?`#16a34a`:`var(--text2)`}">${t.industry||`general`}</span>
              <span style="font-size:10px;color:var(--text2)">${c(t.title||``).slice(0,30)}</span>
            </div>
            <div style="display:flex;gap:6px;align-items:center">
              <input class="sc-preview-input" data-url="${c(e)}"
                     value="${c(t.comment||``)}"
                     style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;font-size:11px">
              <span style="font-size:9px;color:var(--text2);cursor:pointer" onclick="navigator.clipboard.writeText(this.parentElement.querySelector('input').value)">📋</span>
            </div>
          </div>
        `).join(``)}
        <div style="font-size:10px;color:var(--text2);margin-top:6px;text-align:center">
          当前选中 ${n.length} 个账号，分发后将产生 ${i.length*n.length} 条评论任务（P0）
        </div>
        <button onclick="window[\`_sc_confirmDistribute\`]('${e}')"
                style="background:#16a34a;color:#fff;border:none;padding:5px 20px;border-radius:4px;cursor:pointer;font-size:12px;margin-top:6px;float:right">✅ 确认并分发</button>
        <div style="clear:both"></div>
      `,l.style.display=`block`,s.textContent=`✅ 分析完成，${i.length} 个视频`}catch(e){s.textContent=`❌ 分析失败: ${e.message}`}},window._sc_confirmDistribute=async n=>{let i=r?.getSelected()||[];if(!i.length){alert(`请选择账号`);return}let a=document.querySelectorAll(`.sc-preview-input`),o={};if(a.forEach(e=>{let t=e.getAttribute(`data-url`);o[t]=e.value}),!Object.keys(o).length){alert(`没有可分发的评论`);return}let s=i.length*Object.keys(o).length;if(!await e(`确认分发到 ${i.length} 个账号`,`共 ${s} 条评论任务（P0 优先）\n${Object.entries(o).slice(0,3).map(([e,t])=>`${e.slice(0,30)} → ${t.slice(0,25)}`).join(`
`)}${Object.keys(o).length>3?`
...`:``}`))return;let c=document.getElementById(`result_${n}`);c.textContent=`⏳ 正在分发 ${s} 条任务...`;try{await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`smart_comment`,accounts:i.map(e=>e.id),params:{urls:Object.keys(o),comments:o,direction:document.getElementById(`dir_${n}`)?.value||`praise`}})}),c.textContent=`✅ 已分发 ${s} 条评论任务 (P0)`}catch(e){c.textContent=`❌ 分发失败: ${e.message}`}},window._sc_go=async n=>{let i=r?.getSelected()||[],a=document.getElementById(`urls_${n}`)?.value,o=document.getElementById(`dir_${n}`)?.value,s=document.getElementById(`corpus_${n}`)?.value||``,c=document.getElementById(`result_${n}`);if(!a||!a.trim()){c.textContent=`请填写至少一个视频链接`;return}let l=a.split(`
`).map(e=>e.trim()).filter(e=>e);if(!i.length){c.textContent=`请先选择账号`;return}let u=i.length*l.length,d=`账号 ${i.length} 个 · 视频 ${l.length} 个\n方向: ${o} · 语料: ${s||`自动`}`;if(!await e(`即将一键分析并分发 ${u} 条评论`,d)){c.textContent=`已取消`;return}c.textContent=`⏳ 分析 ${l.length} 个视频并分发到 ${i.length} 个账号...`;try{let e=(await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`smart_comment`,accounts:i.map(e=>e.id),params:{urls:l,direction:o,corpus_category:s||void 0,preview:!1}})}))?.machines||{},n=``;for(let[t,r]of Object.entries(e)){let e=r?.success||0,i=r?.failed||0;n+=`🖥 ${t}: ✅${e} ❌${i}\n`}c.textContent=n||`✅ 已分发 ${u} 条评论任务 (P0)`}catch(e){c.textContent=`❌ 执行失败: ${e.message}`}})}function c(e){return e?String(e).replace(/&/g,`&amp;`).replace(/</g,`&lt;`).replace(/>/g,`&gt;`).replace(/"/g,`&quot;`):``}export{o as loadView};
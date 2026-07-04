import{n as e,t}from"./index-BFzzaMkr.js";import{t as n}from"./account-selector-D87mja1n.js";var r=null,i=``;async function a(e,a){i=e.id||`sc`,e.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border)">
        <!-- 标题 -->
        <div style="font-weight:600;font-size:14px;margin-bottom:10px">
          💬 定向评论
          <span style="font-size:10px;color:var(--text2);font-weight:400">
            <label style="margin:0 8px"><input type="radio" name="mode_${i}" value="smart" checked onchange="window._sc_modeChange('${i}')"> 智能分析</label>
            <label style="margin:0 8px"><input type="radio" name="mode_${i}" value="direct" onchange="window._sc_modeChange('${i}')"> 直接执行</label>
          </span>
        </div>

        <!-- 账号选择 -->
        <div id="acctList_${i}" style="margin-bottom:8px"><div class="loading">⏳ 加载账号列表...</div></div>

        <!-- 参数输入 -->
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
          <textarea id="urls_${i}" placeholder="视频链接（每行一个，支持多个）" rows="3"
                    style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
          <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:140px">
            <select id="dir_${i}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
              <option value="praise">👍 称赞</option>
              <option value="question">🤔 提问</option>
              <option value="empathy">💗 共鸣</option>
              <option value="agree">✅ 认同</option>
            </select>
            <button id="btn_analyze_${i}" onclick="window._sc_analyze('${i}')"
                    style="background:var(--primary);color:#fff;border:none;padding:5px 12px;border-radius:4px;cursor:pointer;font-size:12px">🔍 分析视频</button>
            <button id="btn_go_${i}" onclick="window._sc_go('${i}')"
                    style="background:#16a34a;color:#fff;border:none;padding:5px 12px;border-radius:4px;cursor:pointer;font-size:12px;display:none">🚀 确认分发</button>
          </div>
        </div>

        <!-- 状态/结果 -->
        <div id="result_${i}" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>

      <!-- 分析结果预览区 -->
      <div id="preview_${i}" style="display:none;margin-top:10px"></div>
    </div>`;try{let[e,a]=await Promise.all([t(`/matrix/accounts`),t(`/matrix/corpus`).catch(()=>({categories:[]}))]),o=Array.isArray(e)?e:e.accounts||[];a.categories;let s=document.getElementById(`acctList_${i}`);s&&(r=n(s,{accounts:o,checkAll:!1,height:`180px`,showBlueprint:!1,showCollectTime:!1}))}catch(e){let t=document.getElementById(`acctList_${i}`);t&&(t.innerHTML=`<div class="error">❌ ${e.message}</div>`)}a&&a.accounts&&r&&setTimeout(()=>{let e=a.accounts;document.querySelectorAll(`#acctList_${i} .acct-cb`).forEach(t=>{e.includes(t.value)&&(t.checked=!0)})},300),o(i)}function o(n){window[`_sc_ready_${n}`]||(window[`_sc_ready_${n}`]=!0,window._sc_modeChange=e=>{let t=document.querySelector(`input[name="mode_${e}"]:checked`).value===`smart`;document.getElementById(`btn_analyze_${e}`).style.display=t?``:`none`,document.getElementById(`btn_go_${e}`).style.display=t?`none`:``,t||(document.getElementById(`preview_${e}`).style.display=`none`)},window._sc_analyze=async e=>{let n=r?.getSelected()||[],i=document.getElementById(`urls_${e}`)?.value,a=document.getElementById(`dir_${e}`)?.value||`praise`,o=document.getElementById(`result_${e}`),c=document.getElementById(`preview_${e}`);if(!i||!i.trim()){o.textContent=`请填写至少一个视频链接`;return}let l=i.split(`
`).map(e=>e.trim()).filter(e=>e);if(!l.length){o.textContent=`请填写有效的视频链接`;return}if(!n.length){o.textContent=`请先选择要执行的账号`;return}o.textContent=`⏳ 正在分析 ${l.length} 个视频...`,c.style.display=`none`;let u=n[0].id;try{let r=(await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`smart_comment`,accounts:[u],params:{urls:l,direction:a,preview:!0}})})).preview||{},i=Object.entries(r);if(!i.length){o.textContent=`⚠️ 分析完成但没有返回结果`;return}c.innerHTML=`
        <div style="font-weight:600;font-size:12px;margin-bottom:6px;color:var(--text)">📋 分析结果（共 ${i.length} 个视频）
          <span style="font-size:10px;color:var(--text2);font-weight:400"> — 可修改预评论后确认分发</span>
        </div>
        ${i.map(([e,t])=>`
          <div style="background:var(--bg2);border-radius:6px;padding:8px 10px;border:1px solid var(--border);margin-bottom:4px">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
              <span style="font-size:11px;color:var(--text2);max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${s(e.slice(0,60))}</span>
              <span class="industry-tag" style="font-size:9px;padding:1px 6px;border-radius:3px;background:${t.industry===`health`?`rgba(34,197,94,.15)`:`var(--bg3)`};color:${t.industry===`health`?`#16a34a`:`var(--text2)`}">${t.industry||`general`}</span>
              <span style="font-size:10px;color:var(--text2)">${s(t.title||``).slice(0,30)}</span>
            </div>
            <div style="display:flex;gap:6px;align-items:center">
              <input class="sc-preview-input" data-url="${s(e)}"
                     value="${s(t.comment||``)}"
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
      `,c.style.display=`block`,o.textContent=`✅ 分析完成，${i.length} 个视频`}catch(e){o.textContent=`❌ 分析失败: ${e.message}`}},window._sc_confirmDistribute=async n=>{let i=r?.getSelected()||[];if(!i.length){alert(`请选择账号`);return}let a=document.querySelectorAll(`.sc-preview-input`),o={};if(a.forEach(e=>{let t=e.getAttribute(`data-url`);o[t]=e.value}),!Object.keys(o).length){alert(`没有可分发的评论`);return}let s=i.length*Object.keys(o).length;if(!await e(`确认分发到 ${i.length} 个账号`,`共 ${s} 条评论任务（P0 优先）\n${Object.entries(o).slice(0,3).map(([e,t])=>`${e.slice(0,30)} → ${t.slice(0,25)}`).join(`
`)}${Object.keys(o).length>3?`
...`:``}`))return;let c=document.getElementById(`result_${n}`);c.textContent=`⏳ 正在分发 ${s} 条任务...`;try{await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`smart_comment`,accounts:i.map(e=>e.id),params:{urls:Object.keys(o),comments:o,direction:document.getElementById(`dir_${n}`)?.value||`praise`}})}),c.textContent=`✅ 已分发 ${s} 条评论任务 (P0)`}catch(e){c.textContent=`❌ 分发失败: ${e.message}`}},window._sc_go=async n=>{let i=r?.getSelected()||[],a=document.getElementById(`urls_${n}`)?.value,o=document.getElementById(`dir_${n}`)?.value,s=document.getElementById(`result_${n}`);if(!a||!a.trim()){s.textContent=`请填写至少一个视频链接`;return}let c=a.split(`
`).map(e=>e.trim()).filter(e=>e);if(!i.length){s.textContent=`请先选择账号`;return}let l=i.length*c.length,u=`账号: ${i.map(e=>e.id).slice(0,5).join(`, `)}${i.length>5?`...`:``}\n视频: ${c.join(`
`)}\n方式: 直接执行（不分析）`;if(!await e(`即将用 ${i.length} 个账号评论 ${c.length} 个视频`,u)){s.textContent=`已取消`;return}s.textContent=`⏳ ${l} 个任务...`;let d=0;for(let e of c)for(let n of i)try{await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`comment`,accounts:[n.id],params:{url:e,direction:o}})}),d++}catch{}s.textContent=`✅ ${d}/${l} 已提交`})}function s(e){return e?String(e).replace(/&/g,`&amp;`).replace(/</g,`&lt;`).replace(/>/g,`&gt;`).replace(/"/g,`&quot;`):``}export{a as loadView};
import{n as e,t}from"./index-wekEWxQs.js";import{t as n}from"./account-selector-D87mja1n.js";var r=null,i=``,a=[],o={},s=localStorage.getItem(`_sc_api_url`)||`https://wx.tyhtak.com/api/biz/activity/api/v1/activity/recordswx1`;async function c(e,c){i=e.id||`sc`,o={},e.innerHTML=`
    <div style="padding:16px">
      <!-- 主面板 -->
      <div style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:14px;margin-bottom:10px">
          💬 定向评论
          <span style="font-size:10px;color:var(--text2);font-weight:400">导入热帖一键分发，或手动粘贴分析后分发</span>
        </div>

        <!-- ⚙ 数据源设置（可折叠） -->
        <details style="margin-bottom:8px;font-size:11px">
          <summary style="cursor:pointer;color:var(--text2)">⚙ 数据源设置</summary>
          <div style="margin-top:6px;display:flex;gap:6px;align-items:center">
            <input id="apiUrl_${i}" type="text" value="${d(s)}"
                   style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;font-size:11px">
            <button id="btn_testApi_${i}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">测试连接</button>
            <span id="apiTestResult_${i}" style="font-size:10px;color:var(--text2)"></span>
          </div>
        </details>

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
            <details style="font-size:10px;margin:2px 0">
              <summary style="cursor:pointer;color:var(--text2)">📂 语料分类（可多选）</summary>
              <div id="corpusList_${i}" style="margin-top:4px;max-height:120px;overflow-y:auto;background:var(--bg3);border-radius:4px;padding:4px">
                <label style="display:flex;align-items:center;gap:4px;padding:2px 4px;cursor:pointer;font-size:10px"><input type="checkbox" class="corpus-cb-${i}" value="" checked onchange="window._sc_updateCorpus('${i}')"> 🌐 自动匹配</label>
              </div>
            </details>
            <input id="corpusInput_${i}" type="hidden" value="">

            <label style="display:flex;align-items:center;gap:4px;font-size:10px;color:var(--text2);cursor:pointer">
              <input id="skipAnalysis_${i}" type="checkbox" checked>
              ⏭ 跳过分析（导入热帖时默认开启）
            </label>
            <div style="display:flex;gap:4px">
              <button id="btn_import_${i}" onclick="window._sc_import('${i}')"
                      style="flex:1;background:var(--primary);color:#fff;border:none;padding:5px 8px;border-radius:4px;cursor:pointer;font-size:11px">📥 导入热帖</button>
              <button id="btn_go_${i}" onclick="window._sc_go('${i}')"
                      style="flex:1;background:#16a34a;color:#fff;border:none;padding:5px 8px;border-radius:4px;cursor:pointer;font-size:11px">🚀 一键执行</button>
            </div>
          </div>
        </div>

        <!-- 状态/结果 -->
        <div id="result_${i}" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>

      <!-- 导入面板（折叠） -->
      <div id="importPanel_${i}" style="display:none;margin-top:10px"></div>

      <!-- 分析预览区 -->
      <div id="preview_${i}" style="display:none;margin-top:10px"></div>

      <!-- 📋 执行记录 -->
      <div id="batchLogs_${i}" style="margin-top:16px"></div>
    </div>`;try{let[e,o]=await Promise.all([t(`/matrix/accounts`),t(`/matrix/corpus`).catch(()=>({categories:[]}))]),s=Array.isArray(e)?e:e.accounts||[];a=o.categories||[];let c=document.getElementById(`acctList_${i}`);c&&(r=n(c,{accounts:s,checkAll:!1,height:`160px`,showBlueprint:!1,showCollectTime:!1}))}catch(e){let t=document.getElementById(`acctList_${i}`);t&&(t.innerHTML=`<div class="error">❌ ${e.message}</div>`)}let f=document.getElementById(`corpusList_${i}`);f&&a.forEach(e=>{let t=document.createElement(`label`);t.style.cssText=`display:flex;align-items:center;gap:4px;padding:2px 4px;cursor:pointer;font-size:10px`,t.innerHTML=`<input type="checkbox" class="corpus-cb-${i}" value="${e.name}" onchange="window._sc_updateCorpus('${i}')"> ${e.name} (${(e.accessible||[]).join(`,`)||`通用`})`,f.appendChild(t)}),window._sc_updateCorpus=e=>{let t=document.querySelectorAll(`.corpus-cb-${e}:checked`),n=Array.from(t).map(e=>e.value).filter(e=>e);document.getElementById(`corpusInput_${e}`).value=n.join(`,`)},u(i),l(i)}function l(n){window[`_sc_ready_${n}`]||(window[`_sc_ready_${n}`]=!0,window._sc_testApi=async e=>{let n=document.getElementById(`apiUrl_${e}`)?.value,r=document.getElementById(`apiTestResult_${e}`);if(!n){r.textContent=`❌ 请输入 API 地址`;return}r.textContent=`⏳`;try{let e=await t(`/ops/import-topics`,{method:`POST`,body:JSON.stringify({api_url:n,page:1,page_size:1})});e.status===`ok`?(r.textContent=`✅ ${e.total} 条`,localStorage.setItem(`_sc_api_url`,n),s=n):r.textContent=`❌ ${e.message}`}catch(e){r.textContent=`❌ ${e.message}`}},window._sc_import=async e=>{let n=document.getElementById(`apiUrl_${e}`)?.value||s;if(!n){alert(`请先在⚙ 数据源设置中配置 API 地址`);return}localStorage.setItem(`_sc_api_url`,n),s=n;let r=document.getElementById(`importPanel_${e}`);r.style.display=`block`,r.innerHTML=`<div class="loading" style="padding:10px">⏳ 加载热帖列表...</div>`;try{let i=await t(`/ops/import-topics`,{method:`POST`,body:JSON.stringify({api_url:n,page:1,page_size:100})});if(i.status!==`ok`){r.innerHTML=`<div class="error">❌ ${i.message||`加载失败`}</div>`;return}let a=i.items||[];r.innerHTML=`
        <div style="background:var(--bg2);border-radius:8px;border:1px solid var(--border);overflow:hidden">
          <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 10px;background:var(--bg3);font-size:11px;font-weight:600">
            <span>📋 今日热帖（共 ${i.total||0} 条，未完成 ${a.filter(e=>!e.completed&&!e.already_commented).length} 条）</span>
            <div style="display:flex;gap:4px">
              <button onclick="window._sc_toggleAll('${e}', true)" style="background:none;border:1px solid var(--border);color:var(--text);padding:2px 8px;border-radius:3px;cursor:pointer;font-size:10px">☑ 全选未完成</button>
              <button onclick="window._sc_toggleAll('${e}', false)" style="background:none;border:1px solid var(--border);color:var(--text);padding:2px 8px;border-radius:3px;cursor:pointer;font-size:10px">☐ 取消全选</button>
              <button onclick="window._sc_importSelected('${e}')" style="background:#16a34a;color:#fff;border:none;padding:2px 10px;border-radius:3px;cursor:pointer;font-size:10px">导入选中</button>
            </div>
          </div>
          <div id="importList_${e}" style="max-height:320px;overflow-y:auto;font-size:10px">
            ${a.map(e=>{let t=e.completed||e.already_commented,n=(e.tags||[]).length?`#`+(e.tags||[]).slice(0,3).join(` #`):``,r=e.created_at?e.created_at.slice(5,16):``;return`<label style="display:flex;align-items:center;gap:4px;padding:4px 10px;border-bottom:1px solid var(--border);cursor:${t?`not-allowed`:`pointer`};opacity:${t?.5:1}">
                <input type="checkbox" class="import-cb" data-url="${d(e.url)}" data-title="${d(e.title||``)}" data-id="${e.id}" ${t?`disabled`:``} ${t?``:`checked`}>
                <div style="flex:1;overflow:hidden;min-width:0">
                  <div style="font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${d((e.title||``).slice(0,55))}</div>
                  <div style="font-size:8px;color:var(--text2);margin-top:1px">
                    ${d(e.author||``)}
                    ${n?`<span style="margin-left:4px">${d(n)}</span>`:``}
                    ${r?`<span style="margin-left:4px">${d(r)}</span>`:``}
                  </div>
                </div>
                <span style="font-size:9px;color:${e.already_commented?`#16a34a`:`var(--text2)`};white-space:nowrap">${e.already_commented?`✅已评`:e.completed?`☑已完成`:``}</span>
              </label>`}).join(``)}
          </div>
        </div>`}catch(e){r.innerHTML=`<div class="error">❌ 加载失败: ${e.message}</div>`}},window._sc_toggleAll=(e,t)=>{document.querySelectorAll(`#importList_${e} .import-cb:not(:disabled)`).forEach(e=>e.checked=t)},window._sc_importSelected=e=>{let t=document.querySelectorAll(`#importList_${e} .import-cb:checked`);if(!t.length){alert(`请先勾选要导入的视频`);return}let n=[];o={},t.forEach(e=>{n.push(e.dataset.url),o[e.dataset.url]=e.dataset.title}),document.getElementById(`urls_${e}`).value=n.join(`
`),document.getElementById(`skipAnalysis_${e}`).checked=!0,document.getElementById(`importPanel_${e}`).style.display=`none`,document.getElementById(`result_${e}`).textContent=`✅ 已导入 ${n.length} 个视频（跳过分析模式）`},window._sc_analyze=async e=>{let n=r?.getSelected()||[],i=document.getElementById(`urls_${e}`)?.value,a=document.getElementById(`dir_${e}`)?.value||`praise`,o=document.getElementById(`corpusInput_${e}`)?.value||``,s=document.getElementById(`result_${e}`),c=document.getElementById(`preview_${e}`);if(!i||!i.trim()){s.textContent=`请填写至少一个视频链接`;return}let l=i.split(`
`).map(e=>e.trim()).filter(e=>e);if(!l.length){s.textContent=`请填写有效的视频链接`;return}if(!n.length){s.textContent=`请先选择要执行的账号`;return}s.textContent=`⏳ 正在分析 ${l.length} 个视频...`,c.style.display=`none`;let u=n[0].id;try{let r=(await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`smart_comment`,accounts:[u],params:{urls:l,direction:a,corpus_category:o||void 0,preview:!0}})})).preview||{},i=Object.entries(r);if(!i.length){s.textContent=`⚠️ 分析完成但没有返回结果`;return}c.innerHTML=`
        <div style="font-weight:600;font-size:12px;margin-bottom:6px">📋 分析结果（共 ${i.length} 个视频）<span style="font-size:10px;color:var(--text2);font-weight:400"> — 可修改后确认分发</span></div>
        ${i.map(([e,t])=>`
          <div style="background:var(--bg2);border-radius:6px;padding:8px 10px;border:1px solid var(--border);margin-bottom:4px">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
              <span style="font-size:11px;color:var(--text2);max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${d(e.slice(0,60))}</span>
              <span style="font-size:9px;padding:1px 6px;border-radius:3px;background:${t.industry===`health`?`rgba(34,197,94,.15)`:`var(--bg3)`};color:${t.industry===`health`?`#16a34a`:`var(--text2)`}">${t.industry||`general`}</span>
              <span style="font-size:10px;color:var(--text2)">${d((t.title||``).slice(0,30))}</span>
            </div>
            <div style="display:flex;gap:6px;align-items:center">
              <input class="sc-preview-input" data-url="${d(e)}" value="${d(t.comment||``)}"
                     style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;font-size:11px">
              <span style="font-size:9px;color:var(--text2);cursor:pointer" onclick="navigator.clipboard.writeText(this.parentElement.querySelector('input').value)">📋</span>
            </div>
          </div>
        `).join(``)}
        <div style="font-size:10px;color:var(--text2);margin-top:6px;text-align:center">当前选中 ${n.length} 个账号</div>
        <button onclick="window[\`_sc_confirmDistribute\`]('${e}')" style="background:#16a34a;color:#fff;border:none;padding:5px 20px;border-radius:4px;cursor:pointer;font-size:12px;margin-top:6px;float:right">✅ 确认并分发</button>
        <div style="clear:both"></div>`,c.style.display=`block`,s.textContent=`✅ 分析完成，${i.length} 个视频`}catch(e){s.textContent=`❌ 分析失败: ${e.message}`}},window._sc_confirmDistribute=async n=>{let i=r?.getSelected()||[];if(!i.length){alert(`请选择账号`);return}let a=document.querySelectorAll(`.sc-preview-input`),o={};if(a.forEach(e=>{o[e.getAttribute(`data-url`)]=e.value}),!Object.keys(o).length){alert(`没有可分发的评论`);return}let s=i.length*Object.keys(o).length;if(!await e(`确认分发到 ${i.length} 个账号`,`共 ${s} 条评论任务（P0 优先）`))return;let c=document.getElementById(`result_${n}`);c.textContent=`⏳ 正在分发 ${s} 条任务...`;try{await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`smart_comment`,accounts:i.map(e=>e.id),params:{urls:Object.keys(o),comments:o,direction:document.getElementById(`dir_${n}`)?.value||`praise`}})}),c.textContent=`✅ 已分发 ${s} 条评论任务 (P0)`,setTimeout(()=>u(n),2e3)}catch(e){c.textContent=`❌ 分发失败: ${e.message}`}},window._sc_go=async n=>{let i=r?.getSelected()||[],a=document.getElementById(`urls_${n}`)?.value,s=document.getElementById(`dir_${n}`)?.value,c=document.getElementById(`corpus_${n}`)?.value||``,l=document.getElementById(`skipAnalysis_${n}`)?.checked,d=document.getElementById(`result_${n}`);if(!a||!a.trim()){d.textContent=`请填写至少一个视频链接`;return}let f=a.split(`
`).map(e=>e.trim()).filter(e=>e);if(!i.length){d.textContent=`请先选择账号`;return}let p=i.length*f.length,m=`账号 ${i.length} 个 · 视频 ${f.length} 个\n方向: ${s}${l?` · ⏭ 跳过分析`:``}`;if(!await e(`即将${l?``:`分析并`}分发 ${p} 条评论`,m)){d.textContent=`已取消`;return}d.textContent=`⏳ 分发 ${p} 条任务...`;try{let e=await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`smart_comment`,accounts:i.map(e=>e.id),params:{urls:f,direction:s,corpus_category:c||void 0,preview:!1,skip_analysis:l&&Object.keys(o).length>0,titles:l?o:{},video_ids:f.map(e=>``)}})}),r=e?.per_machine||{},a=``,m=Object.keys(r).length>0;for(let[e,t]of Object.entries(r))a+=`🖥 ${e}: ✅${t?.success||0} ❌${t?.failed||0}\n`;let h=e?.commands?.length||0;d.textContent=m?a:h>0?`✅ 已提交 ${h} 条任务，正在排队执行`:`✅ 已分发 ${p} 条评论任务`,setTimeout(()=>u(n),2e3)}catch(e){d.textContent=`❌ 执行失败: ${e.message}`}})}async function u(e){let n=document.getElementById(`batchLogs_${e}`);if(n)try{let e=(await t(`/ops/batch-logs?limit=30`)).logs||[];if(!e.length){n.innerHTML=``;return}n.innerHTML=`
      <details open>
        <summary style="cursor:pointer;font-weight:600;font-size:12px;color:var(--text);margin-bottom:4px">
          📋 执行记录（${e.length} 条）
        </summary>
        <div style="font-size:10px">
          ${e.map((e,t)=>{let n=e.machine_counts||{},r=Object.entries(n).map(([e,t])=>`${e}:✅${t.success||0}❌${t.failed||0}`).join(` `);return`<div style="background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:6px 8px;margin-bottom:3px;cursor:pointer" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span>${e.time||``}</span>
                <span>${e.video_count||0}视频×${e.account_count||0}账号=${e.total||0}条</span>
                <span>${r||`等待执行`}</span>
              </div>
            </div>
            <div style="display:none;padding:4px 8px;margin-bottom:4px;font-size:9px;color:var(--text2);background:var(--bg3);border-radius:0 0 4px 4px">
              <div>方向: ${e.direction||`-`}</div>
              <div>视频: ${(e.urls||[]).slice(0,5).map(e=>e.slice(0,40)).join(`; `)}${(e.urls||[]).length>5?`...`:``}</div>
            </div>`}).join(``)}
        </div>
      </details>`}catch{}}function d(e){return e?String(e).replace(/&/g,`&amp;`).replace(/</g,`&lt;`).replace(/>/g,`&gt;`).replace(/"/g,`&quot;`):``}export{c as loadView};
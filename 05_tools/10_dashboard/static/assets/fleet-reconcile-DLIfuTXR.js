async function e(e){let t=`fr_`+Math.random().toString(36).slice(2,6),n=null;e.innerHTML=`
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">🔍 对账检查</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">检查本机是否符合 ORACLE.yaml 宪法定义</p>

      <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
        <button onclick="window._doFleetReconcile('${t}')" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">🔍 执行对账</button>
        <button id="exportBtn_${t}" onclick="window._exportReconcile('${t}')" style="display:none;background:var(--bg2);color:var(--text);border:1px solid var(--border);padding:8px 16px;border-radius:6px;cursor:pointer;font-size:12px">📋 导出报告</button>
      </div>

      <!-- 统计卡片 -->
      <div id="stats_${t}" style="display:none;margin-bottom:12px">
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:8px">
          <div style="background:var(--bg3);border-radius:8px;padding:10px 14px;text-align:center">
            <div style="font-size:11px;color:var(--text2)">总项</div>
            <div id="statTotal_${t}" style="font-size:22px;font-weight:500;margin-top:4px">0</div>
          </div>
          <div id="statPassCard_${t}" style="background:#EAF3DE;border-radius:8px;padding:10px 14px;text-align:center">
            <div style="font-size:11px;color:#27500A">通过</div>
            <div id="statPass_${t}" style="font-size:22px;font-weight:500;color:#3B6D11;margin-top:4px">0</div>
          </div>
          <div id="statWarnCard_${t}" style="background:#FAEEDA;border-radius:8px;padding:10px 14px;text-align:center">
            <div style="font-size:11px;color:#633806">警告</div>
            <div id="statWarn_${t}" style="font-size:22px;font-weight:500;color:#854F0B;margin-top:4px">0</div>
          </div>
          <div id="statFailCard_${t}" style="background:#FCEBEB;border-radius:8px;padding:10px 14px;text-align:center">
            <div style="font-size:11px;color:#791F1F">失败</div>
            <div id="statFail_${t}" style="font-size:22px;font-weight:500;color:#A32D2D;margin-top:4px">0</div>
          </div>
          <div style="background:var(--bg3);border-radius:8px;padding:10px 14px;text-align:center">
            <div style="font-size:11px;color:var(--text2)">通过率</div>
            <div id="statRate_${t}" style="font-size:22px;font-weight:500;margin-top:4px">0%</div>
          </div>
        </div>
      </div>

      <!-- 筛选 tab -->
      <div id="filter_${t}" style="display:none;margin-bottom:10px">
        <div style="display:flex;gap:6px;flex-wrap:wrap;font-size:12px">
          ${[`全部`,`环境`,`目录`,`文件`,`Git`,`服务`,`任务`].map((e,n)=>`<div id="filterTab_${t}_${n}" class="reconcile-filter-tab" style="height:28px;padding:0 14px;border-radius:6px;display:inline-flex;align-items:center;cursor:pointer;background:${n===0?`var(--primary)`:`var(--bg3)`};color:${n===0?`#fff`:`var(--text)`}" onclick="window._filterReconcile('${t}',${n})">${e}</div>`).join(``)}
        </div>
      </div>

      <!-- 明细 -->
      <div id="detail_${t}" style="display:none">
        <div style="font-size:11px;color:var(--text2);margin-bottom:6px">明细</div>
        <div id="detailList_${t}" style="display:flex;flex-direction:column;gap:4px"></div>
      </div>

      <!-- 原始日志 -->
      <div id="log_${t}" style="margin-top:12px;background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:300px;overflow:auto;display:none"></div>
    </div>`,window._doFleetReconcile=window._doFleetReconcile||(async function(e){let t=document.getElementById(`log_`+e);if(document.getElementById(`stats_`+e),document.getElementById(`filter_`+e),document.getElementById(`detail_`+e),document.getElementById(`detailList_`+e),t){t.style.display=``,t.textContent=`⏳ 执行对账...
`;try{let a=await(await fetch(`/api/fleet/reconcile`,{method:`POST`,timeout:12e4})).json(),o=a.output||JSON.stringify(a,null,2);t.textContent=o,n=r(o),i(e,n)}catch(e){t.textContent=`❌ `+e.message}}});function r(e){let t=[],n=``,r=e.split(`
`);for(let e of r){let r=e.replace(/\u001b\[[\d;]+m/g,``).trim();if(!r)continue;if(/^[═━]{3,}\s*\d+\.\s/.test(r)){n=r.replace(/[═━\s]+/g,` `).trim();continue}let i=null,a=r;if(/^✅/.test(r)?(i=`pass`,a=r.replace(/^✅\s*/,``)):/^⚠️/.test(r)?(i=`warn`,a=r.replace(/^⚠️\s*/,``)):/^❌/.test(r)&&(i=`fail`,a=r.replace(/^❌\s*/,``)),i&&a){let e=a.indexOf(`:`),r=a,o=``;e>0&&(r=a.slice(0,e).trim(),o=a.slice(e+1).trim()),t.push({status:i,label:r,detail:o,section:n})}}return t}function i(e,t){let r=t.length,i=t.filter(e=>e.status===`pass`).length,a=t.filter(e=>e.status===`warn`).length,o=t.filter(e=>e.status===`fail`).length,s=r>0?Math.round(i/r*100):0;document.getElementById(`statTotal_`+e).textContent=r,document.getElementById(`statPass_`+e).textContent=i,document.getElementById(`statWarn_`+e).textContent=a,document.getElementById(`statFail_`+e).textContent=o,document.getElementById(`statRate_`+e).textContent=s+`%`,document.getElementById(`stats_`+e).style.display=``,document.getElementById(`filter_`+e).style.display=``,document.getElementById(`detail_`+e).style.display=``;let c=document.getElementById(`exportBtn_`+e);c&&(c.style.display=``);let l=document.getElementById(`statPassCard_`+e);document.getElementById(`statWarnCard_`+e);let u=document.getElementById(`statFailCard_`+e);i>0&&o===0?l.style.background=`#EAF3DE`:r>0&&o===0||o>0&&(u.style.background=`#FCEBEB`),n=t,window._filterReconcile(e,0)}window._filterReconcile=window._filterReconcile||function(e,t){document.querySelectorAll(`#filter_`+e+` [id^="filterTab_"]`).forEach((e,n)=>{e.style.background=n===t?`var(--primary)`:`var(--bg3)`,e.style.color=n===t?`#fff`:`var(--text)`});let r=[`全部`,`环境`,`目录`,`文件`,`Git`,`服务`,`任务`][t],i=n||[];r!==`全部`&&(i=i.filter(e=>e.section.includes(r))),a(e,i)};function a(e,t){let n=document.getElementById(`detailList_`+e);if(!n)return;if(t.length===0){n.innerHTML=`<div style="font-size:12px;color:var(--text2);padding:8px">无匹配项</div>`;return}let r=``;for(let e of t){let t=e.status===`pass`?`✅`:e.status===`warn`?`⚠️`:`❌`,n=e.status===`pass`?`var(--green)`:e.status===`warn`?`var(--amber)`:`var(--red)`;r+=`<div style="display:flex;gap:8px;align-items:flex-start;padding:6px 8px;background:var(--bg3);border-radius:6px;font-size:12px;line-height:1.5">`,r+=`<span style="color:${n};flex-shrink:0">${t}</span>`,r+=`<span style="color:var(--text2);flex-shrink:0;min-width:80px">${o(e.label)}</span>`,e.detail&&(r+=`<span>${o(e.detail)}</span>`),r+=`</div>`}n.innerHTML=r}window._exportReconcile=window._exportReconcile||function(e){if(!n||n.length===0)return;let t=n.filter(e=>e.status===`pass`).length,r=n.filter(e=>e.status===`warn`).length,i=n.filter(e=>e.status===`fail`).length,a=n.length,o=a>0?Math.round(t/a*100):0,s=new Date().toLocaleString(),c=`# AgentOS 联邦对账报告

`;c+=`**生成时间**: ${s}\n\n`,c+=`## 统计

`,c+=`| 指标 | 数值 |
|:-----|:-----|
`,c+=`| 总项 | ${a} |\n`,c+=`| 通过 | ${t} |\n`,c+=`| 警告 | ${r} |\n`,c+=`| 失败 | ${i} |\n`,c+=`| 通过率 | ${o}% |\n\n`,c+=`## 明细

`,c+=`| 状态 | 检查项 | 详情 |
|:-----|:-------|:------|
`;for(let e of n){let t=e.status===`pass`?`✅`:e.status===`warn`?`⚠️`:`❌`;c+=`| ${t} | ${e.label} | ${e.detail} |\n`}navigator.clipboard.writeText(c).then(()=>{let t=document.getElementById(`exportBtn_`+e);if(t){let e=t.textContent;t.textContent=`✅ 已复制`,setTimeout(()=>{t.textContent=e},2e3)}}).catch(()=>{let e=document.createElement(`textarea`);e.value=c,e.style.cssText=`position:fixed;left:-9999px`,document.body.appendChild(e),e.select(),document.execCommand(`copy`),document.body.removeChild(e)})};function o(e){return String(e).replace(/&/g,`&amp;`).replace(/</g,`&lt;`).replace(/>/g,`&gt;`)}}export{e as loadView};
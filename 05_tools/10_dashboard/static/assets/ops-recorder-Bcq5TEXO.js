async function e(e){let t=Math.random().toString(36).slice(2,6),n=null,r={atomOps:[],deleted:[],stepLabels:{}},i=null,a=[],o=!1;function s(){try{let e=localStorage.getItem(`rec_annotations_v4`)||`{}`;r=JSON.parse(e)[n?.name]||{atomOps:[],deleted:[],stepLabels:{}}}catch{r={atomOps:[],deleted:[],stepLabels:{}}}}function c(){if(n)try{let e=localStorage.getItem(`rec_annotations_v4`)||`{}`,t=JSON.parse(e);t[n.name]=r,localStorage.setItem(`rec_annotations_v4`,JSON.stringify(t))}catch{}}let l=0;function u(){return`ao_`+ ++l+`_`+Date.now().toString(36)}function d(e){return r.atomOps.find(t=>e>=t.stepRange[0]&&e<=t.stepRange[1])}function f(e){return r.deleted.includes(e)}function p(e){let[t,r]=e.stepRange,i=[];for(let e=t;e<=r;e++){let t=n.steps[e];if(t&&n.actMap){let e=n.actMap[t.step]||[];i.push(...e)}}let a=n.steps[t],o=n.steps[r];return{firstAct:i[0]||{},acts:i,screenshotBefore:a?.screenshot_url||``,screenshotAfter:o?n.steps[Math.min(r+1,n.steps.length-1)]?.screenshot_url:``,from:a?.page||{},to:o?.page||{},events:n.steps.slice(t,r+1).flatMap(e=>e.events||[])}}e.innerHTML=`
    <div style="padding:12px">
      <!-- 标题 + 录制控制 -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:6px">
        <h2 style="font-size:18px;margin:0">🎬 录制标注</h2>
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
          <select id="recAcct_${t}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;font-size:11px;width:120px"><option value="">加载账号...</option></select>
          <button id="recStartBtn_${t}" onclick="window._recStart('${t}')" style="background:#22c55e;color:#fff;border:none;padding:5px 12px;border-radius:5px;cursor:pointer;font-size:11px">▶ 开始录制</button>
          <button id="recStopBtn_${t}" onclick="window._recStop('${t}')" style="display:none;background:#ef4444;color:#fff;border:none;padding:5px 12px;border-radius:5px;cursor:pointer;font-size:11px">⏹ 停止</button>
          <span id="recStatus_${t}" style="font-size:10px;color:var(--text2)"></span>
          <button onclick="window._reloadAll('${t}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 10px;border-radius:4px;cursor:pointer;font-size:10px">⟳ 刷新</button>
        </div>
      </div>

      <!-- 录制包列表 -->
      <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px;margin-bottom:10px">
        <div style="font-size:12px;font-weight:600;margin-bottom:6px">📋 录制包</div>
        <div id="recList_${t}" style="font-size:11px;max-height:180px;overflow-y:auto"><div class="loading">加载中...</div></div>
      </div>

      <!-- 标注面板 -->
      <div id="recAnalysis_${t}" style="display:none">
        <div id="recAnalysisInner_${t}" style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px">
          <!-- 标题 -->
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div>
              <span id="recName_${t}" style="font-size:13px;font-weight:600"></span>
              <span id="recMeta_${t}" style="font-size:10px;color:var(--text2);margin-left:6px"></span>
            </div>
            <div style="display:flex;gap:4px;align-items:center">
              <span id="aoStatus_${t}" style="font-size:10px;color:var(--text2)"></span>
              <button onclick="window._toggleSelectionMode('${t}')" id="selModeBtn_${t}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">☐ 选择模式</button>
              <button onclick="window._collapseAll('${t}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">⊟ 全部收起</button>
              <button onclick="document.getElementById('recAnalysis_${t}').style.display='none'" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">✕ 关闭</button>
            </div>
          </div>

          <!-- 步骤横条（总览） -->
          <div id="recStepsBar_${t}" style="display:flex;gap:3px;margin-bottom:8px;overflow-x:auto;padding:2px 0"></div>

          <!-- 选择模式工具栏 -->
          <div id="selToolbar_${t}" style="display:none;background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.2);border-radius:5px;padding:6px;margin-bottom:6px">
            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
              <span style="font-size:10px;color:var(--text2)">已选 <span id="selCount_${t}">0</span> 步</span>
              <button onclick="window._mergeSelected('${t}')" id="mergeBtn_${t}" disabled style="background:#6366f1;color:#fff;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">🔗 打包为原子操作</button>
              <button onclick="window._deleteSelected('${t}')" id="delBtn_${t}" disabled style="background:#ef4444;color:#fff;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">🗑️ 删除步骤</button>
              <button onclick="window._clearSelection('${t}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">✕ 清除选择</button>
            </div>
          </div>

          <!-- 原子操作列表 + 未打包步骤 -->
          <div id="recContent_${t}"></div>

          <!-- 保存/导出底部 -->
          <div style="display:flex;gap:4px;margin-top:8px;border-top:1px solid var(--border);padding-top:8px">
            <button onclick="window._saveAnnotations('${t}')" style="flex:1;background:var(--primary);color:#fff;border:none;padding:3px;border-radius:4px;cursor:pointer;font-size:10px">💾 保存标注</button>
            <button onclick="window._exportBp('${t}')" style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">📦 导出蓝图</button>
            <span id="recStatusMsg_${t}" style="font-size:9px;color:var(--text2);align-self:center;flex:1"></span>
          </div>
        </div>
      </div>
    </div>`,window._reloadAll=function(e){m(e),y(e),v(e)},window._recStart=function(e){h(e)},window._recStop=function(e){_(e)},window._analyzeRec=function(e,t){b(e,t)},window._deleteRec=async function(e,t){if(confirm(`确定删除录制包「`+e+`」？`))try{let n=await(await fetch(`/api/matrix/record/delete/`+encodeURIComponent(e),{method:`POST`})).json();n.status===`ok`?(document.getElementById(`recStatusMsg_`+t).textContent=`✅ 已删除: `+e,y(t)):alert(`删除失败: `+(n.message||``))}catch(e){alert(`删除失败: `+e.message)}},window._toggleSelectionMode=function(e){x(e)},window._mergeSelected=function(e){D(e)},window._deleteSelected=function(e){T(e)},window._clearSelection=function(e){S(e)},window._collapseAll=function(e){i=null,j(e)},window._toggleAo=function(e,t){i=i===e?null:e,j(t)},window._saveAnnotations=function(e){c(),document.getElementById(`recStatusMsg_`+e).textContent=`✅ 已保存`,setTimeout(()=>{let t=document.getElementById(`recStatusMsg_`+e);t&&(t.textContent=``)},2e3)},window._editAo=function(e,t){O(e,t)},window._deleteAo=function(e,t){k(e,t)},window._stepClick=function(e,t){w(e,t)},window._deleteStep=function(e,t){E(e,t)},m(t),y(t),v(t);async function m(e){let t=document.getElementById(`recAcct_${e}`);if(t)try{let e=await(await fetch(`/api/matrix/accounts`)).json();t.innerHTML=`<option value="">— 选择账号 —</option>`+(Array.isArray(e)?e:e.accounts||[]).filter(e=>e.is_local&&e.platform).map(e=>`<option value="${e.id}">${e.platform===`douyin`?`🎵`:`📕`} ${e.id}</option>`).join(``)}catch{t.innerHTML=`<option value="">加载失败</option>`}}async function h(e){let t=document.getElementById(`recAcct_${e}`)?.value;if(!t){alert(`请先选择账号`);return}let n=document.getElementById(`recStartBtn_${e}`);n.textContent=`⏳ 启动中...`,n.disabled=!0;try{let r=await(await fetch(`/api/matrix/record/start`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({account:t})})).json();r.status===`ok`?(document.getElementById(`recStatus_${e}`).textContent=`🟢 录制中 (PID ${r.pid})`,document.getElementById(`recStopBtn_${e}`).style.display=``,n.style.display=`none`):r.need_login?g(t,r.platform||`douyin`,r.message,e):alert(r.message)}catch(e){alert(`启动失败: `+e.message)}finally{n.textContent=`▶ 开始录制`,n.disabled=!1}}function g(e,t,n,r){let i=document.getElementById(`recAnalysisInner_`+r)||document.body,a=document.createElement(`div`);a.style.cssText=`position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.5);z-index:999;display:flex;align-items:center;justify-content:center`,a.onclick=e=>{e.target===a&&a.remove()},a.innerHTML=`<div style="background:var(--bg2);border-radius:10px;padding:20px;width:400px;max-width:90vw;border:1px solid var(--border);text-align:center">
      <div style="font-size:32px;margin-bottom:8px">🔐</div>
      <div style="font-size:14px;font-weight:600;margin-bottom:4px">账号未登录</div>
      <div style="font-size:11px;color:var(--text2);margin-bottom:12px;line-height:1.5">${n}</div>
      <div style="background:rgba(99,102,241,.06);border-radius:6px;padding:10px;margin-bottom:12px;text-align:left;font-size:10px">
        <div style="font-weight:600;margin-bottom:4px">📋 操作步骤：</div>
        <div style="color:var(--text2);line-height:1.6">
          1. 前往左侧导航「📡 信息采集」<br>
          2. 选择账号 <b>${e}</b><br>
          3. 系统会自动检测登录状态并引导登录<br>
          4. 登录成功后返回此页重新录制
        </div>
      </div>
      <div style="display:flex;gap:6px">
        <button onclick="window.switchView('matrix-collect');this.closest('div[style]').remove()"
          style="flex:1;background:var(--primary);color:#fff;border:none;padding:8px;border-radius:5px;cursor:pointer;font-size:12px">→ 前往信息采集登录</button>
        <button onclick="this.closest('div[style]').remove()"
          style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:8px 12px;border-radius:5px;cursor:pointer;font-size:11px">取消</button>
      </div>
    </div>`,i.appendChild(a)}async function _(e){try{await fetch(`/api/matrix/record/stop`,{method:`POST`}),document.getElementById(`recStatus_${e}`).textContent=`⏹ 已停止`,document.getElementById(`recStopBtn_${e}`).style.display=`none`,document.getElementById(`recStartBtn_${e}`).style.display=``,y(e)}catch(e){alert(`停止失败: `+e.message)}}async function v(e){try{let t=await(await fetch(`/api/matrix/record/status`)).json();t.running&&(document.getElementById(`recStatus_${e}`).textContent=`🟢 录制中 (PID ${t.pid})`,document.getElementById(`recStopBtn_${e}`).style.display=``,document.getElementById(`recStartBtn_${e}`).style.display=`none`)}catch{}}async function y(e){let t=document.getElementById(`recList_${e}`);if(t)try{let n=(await(await fetch(`/api/matrix/record/list`)).json()).recordings||[];if(!n.length){t.innerHTML=`<div style="color:var(--text2);padding:8px;text-align:center">暂无录制包</div>`;return}t.innerHTML=n.map(t=>`<div style="display:flex;align-items:center;gap:6px;padding:4px 6px;border-bottom:1px solid var(--border);font-size:10px">
        <span style="font-weight:500;flex:1">${t.name}</span>
        <span style="color:var(--text2);width:30px">${t.platform===`douyin`?`🎵`:`📕`}</span>
        <span style="color:var(--text2);width:80px">${t.account}</span>
        <span style="color:var(--text2);width:30px;text-align:center">${t.steps}步</span>
        <span style="color:var(--text2);width:50px;text-align:center">${t.created||``}</span>
        <button onclick="window._analyzeRec('${t.name}','${e}')" style="background:none;border:none;cursor:pointer;font-size:11px;color:var(--primary)">📊 分析</button>
        <button onclick="window._deleteRec('${t.name}','${e}')" style="background:none;border:none;cursor:pointer;font-size:11px;color:#ef4444">🗑️</button>
      </div>`).join(``)}catch(e){t.innerHTML=`<div style="color:var(--red);padding:8px">❌ ${e.message}</div>`}}async function b(e,t){document.getElementById(`recAnalysis_${t}`).style.display=``;try{let r=await(await fetch(`/api/matrix/record/detail/`+encodeURIComponent(e))).json();n={name:e,meta:r.meta||{},steps:r.steps||[],actions:(r.analysis||{}).actions||[],suggestions:(r.analysis||{}).blueprint_suggestions||[]};let i={};n.actions.forEach(e=>{let t=e.step_after||e.step_before;i[t]||(i[t]=[]),i[t].push(e)}),n.actMap=i;let a={};n.suggestions.forEach(e=>{a[e.step]=e}),n.sugMap=a,s(),document.getElementById(`recName_${t}`).textContent=`📹 ${e}`;let o=n.meta;document.getElementById(`recMeta_${t}`).textContent=`${o.platform||`?`} · ${o.account_id||`?`} · ${n.steps.length}步 · ${Math.round(o.duration||0)}s`,j(t)}catch(e){document.getElementById(`recContent_`+t).innerHTML=`<div style="color:var(--red);padding:8px">❌ ${e.message}</div>`}}function x(e){o=!o,a=[],document.getElementById(`selModeBtn_`+e).textContent=o?`✓ 退出选择`:`☐ 选择模式`,document.getElementById(`selModeBtn_`+e).style.background=o?`rgba(99,102,241,.2)`:`var(--bg3)`,document.getElementById(`selModeBtn_`+e).style.color=o?`var(--primary)`:`var(--text)`,document.getElementById(`selToolbar_`+e).style.display=o?``:`none`,j(e)}function S(e){a=[],C(e),j(e)}function C(e){let t=a.length;document.getElementById(`selCount_`+e).textContent=t,document.getElementById(`mergeBtn_`+e).disabled=t<2,document.getElementById(`delBtn_`+e).disabled=t===0}function w(e,t){if(!o)return;let n=a.indexOf(e);n>=0?a.splice(n,1):a.push(e),C(t),j(t)}function T(e){a.length&&confirm(`确定删除这 `+a.length+` 步？`)&&(a.forEach(e=>{f(e)||r.deleted.push(e)}),a=[],c(),C(e),j(e))}function E(e,t){confirm(`确定删除步骤 `+(e+1)+`？`)&&(f(e)||r.deleted.push(e),c(),j(t))}function D(e){if(a.length<2)return;let t=[...a].sort((e,t)=>e-t);if(!t.every((e,t,n)=>t===0||e===n[t-1]+1)){alert(`只能选择连续的步骤合并为原子操作`);return}for(let e of r.atomOps){let[n,r]=e.stepRange;if(t[0]<=r&&t[t.length-1]>=n){alert(`选择的步骤与已有原子操作 "`+(e.label||e.name)+`" 重叠`);return}}let i=(n.actMap[n.steps[t[0]]?.step]?.[0]||{}).action_type||`custom_op`;A({title:`打包为原子操作`,fields:[{id:`aoName`,label:`标识名`,value:i,placeholder:`英文标识, 如 like_video`},{id:`aoLabel`,label:`中文名`,value:``,placeholder:`如 "点赞视频"`},{id:`aoNote`,label:`备注`,value:``,placeholder:`描述该原子操作的功能和注意点`,type:`textarea`},{id:`aoTags`,label:`特征标签`,value:`验证码:否, 框架:player`,placeholder:`逗号分隔，如 验证码:是, 框架:player`}],onConfirm:n=>{let o={id:u(),name:n.aoName||i,label:n.aoLabel||n.aoName||i,note:n.aoNote||``,tags:(n.aoTags||``).split(`,`).map(e=>e.trim()).filter(Boolean),stepRange:[t[0],t[t.length-1]]};r.atomOps.push(o),a=[],c(),C(e),j(e)}},e)}function O(e,t){let n=r.atomOps.find(t=>t.id===e);n&&A({title:`编辑原子操作`,fields:[{id:`aoName`,label:`标识名`,value:n.name},{id:`aoLabel`,label:`中文名`,value:n.label},{id:`aoNote`,label:`备注`,value:n.note,type:`textarea`},{id:`aoTags`,label:`特征标签`,value:(n.tags||[]).join(`, `)}],onConfirm:e=>{n.name=e.aoName||n.name,n.label=e.aoLabel||e.aoName||n.name,n.note=e.aoNote||``,n.tags=(e.aoTags||``).split(`,`).map(e=>e.trim()).filter(Boolean),c(),j(t)}},t)}function k(e,t){confirm(`确定删除此原子操作？步骤将恢复为未打包状态`)&&(r.atomOps=r.atomOps.filter(t=>t.id!==e),i===e&&(i=null),c(),j(t))}function A(e,t){let n=document.getElementById(`recAnalysisInner_`+t),r=document.createElement(`div`);r.style.cssText=`position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.4);z-index:999;display:flex;align-items:center;justify-content:center`,r.onclick=e=>{e.target===r&&r.remove()},r.innerHTML=`<div style="background:var(--bg2);border-radius:8px;padding:16px;width:380px;max-width:90vw;border:1px solid var(--border)">
      <div style="font-size:14px;font-weight:600;margin-bottom:10px">${e.title}</div>
      ${e.fields.map(e=>{let t=e.type===`textarea`?`textarea`:`input`,n=e.type===`textarea`?`rows="3" style="resize:vertical"`:`type="text"`;return`<div style="margin-bottom:8px">
          <label style="font-size:10px;color:var(--text2);display:block;margin-bottom:2px">${e.label}</label>
          <${t} id="edit_${e.id}" value="${(e.value||``).replace(/"/g,`&quot;`)}" placeholder="${e.placeholder||``}"
            ${n}
            style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px;box-sizing:border-box">${e.type===`textarea`&&e.value||``}</${t}>
        </div>`}).join(``)}
      <div style="display:flex;gap:6px;margin-top:10px">
        <button id="editConfirmBtn" style="flex:1;background:var(--primary);color:#fff;border:none;padding:6px;border-radius:4px;cursor:pointer;font-size:11px">✅ 确认</button>
        <button onclick="this.closest('div[style]').remove()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 12px;border-radius:4px;cursor:pointer;font-size:11px">取消</button>
      </div>
    </div>`,n.appendChild(r),document.getElementById(`editConfirmBtn`).onclick=()=>{let t={};e.fields.forEach(e=>{let n=document.getElementById(`edit_`+e.id);t[e.id]=n?n.value:``}),e.onConfirm(t),r.remove()}}function j(e){M(e);let t=document.getElementById(`recContent_`+e);if(!t||!n)return;let a=n.steps.length,o=r.deleted.length,s=r.atomOps.length,c=r.atomOps.reduce((e,t)=>e+(t.stepRange[1]-t.stepRange[0]+1),0),l=s;document.getElementById(`aoStatus_`+e).textContent=`🏗️ ${l}个原子操作·${c}步已合并·${o}步已删除·剩余${a-o-c}步`;let u=``;r.atomOps.length&&(u+=`<div style="margin-bottom:6px"><div style="font-size:11px;font-weight:600;color:var(--primary);margin-bottom:4px">🏗️ 原子操作</div>`,r.atomOps.forEach(t=>{let n=i===t.id,[r,a]=t.stepRange,o=p(t);u+=N(t,o,n,e)}),u+=`</div>`);let m=[];for(let e=0;e<a;e++)!f(e)&&!d(e)&&m.push(e);m.length&&(u+=`<div><div style="font-size:11px;font-weight:600;color:#f59e0b;margin-bottom:4px;margin-top:6px">📄 未打包步骤 (${m.length})</div>`,m.forEach(t=>{let r=n.steps[t];u+=F(r,t,e)}),u+=`</div>`),!r.atomOps.length&&m.length===0&&(u=`<div style="text-align:center;padding:20px;color:var(--text2);font-size:11px">所有步骤已删除或已打包</div>`),t.innerHTML=u}function M(e){let t=document.getElementById(`recStepsBar_`+e);!t||!n||(t.innerHTML=n.steps.map((t,n)=>{if(f(n))return``;let r=d(n),i=o&&a.includes(n),s,c;o&&i?(s=`#6366f1`,c=`${n+1}`):r?(s=`#22c55e`,c=`${n+1}`):(s=`#6b7280`,c=`${n+1}`);let l=o?`window._stepClick(${n},'${e}')`:``;return`<span ${l?`onclick="`+l+`"`:``}
        style="cursor:${o?`pointer`:`default`};display:inline-flex;align-items:center;justify-content:center;
        width:22px;height:22px;border-radius:4px;font-size:9px;font-weight:600;
        background:${s};color:#fff;opacity:${o&&i?`1`:`0.7`};
        border:${o&&i?`2px solid #818cf8`:`none`}">${c}</span>`}).filter(Boolean).join(``)||`<span style="color:var(--text2);font-size:10px">(全部已删除)</span>`)}function N(e,t,n,r){let[i,a]=e.stepRange,o=t.events||[],s=o.filter(e=>e.t===`click`).length,c=o.filter(e=>e.t===`key`).length,l=o.filter(e=>e.t===`scroll`).length,u=``;s&&(u+=`🖱`),c&&(u+=`⌨️`),l&&(u+=`📜`),u||=`⏸`;let d=(e.tags||[]).map(e=>`<span style="background:rgba(99,102,241,.1);padding:1px 5px;border-radius:3px;font-size:8px;color:var(--text2)">${e}</span>`).join(``),f=i===a?`步骤${i+1}`:`步骤${i+1}-${a+1}`;return`<div style="border:1px solid var(--border);border-radius:6px;margin-bottom:4px;overflow:hidden">
      <!-- 原子操作头 -->
      <div onclick="window._toggleAo('${e.id}','${r}')"
        style="display:flex;align-items:center;gap:6px;padding:6px 8px;
        cursor:pointer;background:${n?`var(--bg3)`:`var(--bg2)`};
        border-bottom:${n?`1px solid var(--border)`:`none`};
        font-size:11px;user-select:none">
        <span style="background:#22c55e;color:#fff;border-radius:3px;padding:1px 5px;font-size:9px;flex-shrink:0">${f}</span>
        <span style="font-weight:600;flex-shrink:0">${e.label||e.name}</span>
        <span style="color:var(--text2);font-size:9px;flex-shrink:0">${u}</span>
        <span style="font-size:8px;color:var(--text2);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${e.note||``}</span>
        <div style="display:flex;gap:2px;flex-shrink:0">
          ${d}
        </div>
        <span style="color:var(--text2);font-size:9px">${n?`▼`:`▶`}</span>
      </div>
      <!-- 原子操作详情 -->
      <div style="display:${n?`block`:`none`};padding:8px">
        ${P(e,t,r)}
      </div>
    </div>`}function P(e,t,r){let[i,a]=e.stepRange,o=t.firstAct,s=t.from||{},c=t.to||{},l=L(s,{}),u=L(c,{}),d=[];return(o.url_changed||s.url&&c.url&&s.url!==c.url)&&d.push(`🔗 <b>URL</b>: ${(s.url||`?`).slice(0,40)} → ${(c.url||`?`).slice(0,40)}`),o.mode_changed&&d.push(`🏗️ <b>框架</b>: ${o.mode_changed}`),o.selector_changes&&Object.entries(o.selector_changes).forEach(([e,t])=>{d.push(`🧩 <b>元素</b>: <code style="font-size:8px">${e.replace(/^\[data-e2e="/,``).replace(/"\]$/,``)}</code> ${t}`)}),`
      <!-- 三栏简约版 -->
      <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:6px;margin-bottom:6px">
        <div style="background:rgba(37,99,235,.04);border-radius:5px;padding:5px;border:1px solid rgba(37,99,235,.1)">
          <div style="font-size:8px;color:#3b82f6;font-weight:600;margin-bottom:2px">⬅ 操作前</div>
          <table style="font-size:8px;width:100%"><tr><td style="color:var(--text2);width:32px">URL</td><td style="word-break:break-all">${l.url.slice(0,45)}</td></tr>
          <tr><td style="color:var(--text2)">框架</td><td>${R(l.mode)}</td></tr>
          <tr><td style="color:var(--text2)">状态</td><td>${t.from?.before_state?.markers?Object.entries(t.from.before_state.markers).map(([e,t])=>`${e}:${t}`).join(` `):`-`}</td></tr></table>
          ${t.screenshotBefore?`<img src="${t.screenshotBefore}" style="max-width:100%;max-height:50px;border-radius:3px;margin-top:2px" onerror="this.style.display='none'">`:``}
        </div>
        <div style="display:flex;align-items:center;font-size:14px;color:var(--text2);padding:0 2px">→</div>
        <div style="background:rgba(5,150,105,.04);border-radius:5px;padding:5px;border:1px solid rgba(5,150,105,.1)">
          <div style="font-size:8px;color:#22c55e;font-weight:600;margin-bottom:2px">➡ 操作后</div>
          <table style="font-size:8px;width:100%"><tr><td style="color:var(--text2);width:32px">URL</td><td style="word-break:break-all">${u.url.slice(0,45)}</td></tr>
          <tr><td style="color:var(--text2)">框架</td><td>${R(u.mode)}</td></tr>
          <tr><td style="color:var(--text2)">状态</td><td>${t.to?.before_state?.markers?Object.entries(t.to.before_state.markers).map(([e,t])=>`${e}:${t}`).join(` `):`-`}</td></tr></table>
          ${t.screenshotAfter?`<img src="${t.screenshotAfter}" style="max-width:100%;max-height:50px;border-radius:3px;margin-top:2px" onerror="this.style.display='none'">`:``}
        </div>
      </div>

      <!-- 变化特征码 -->
      ${d.length?`<div style="background:rgba(99,102,241,.05);border-radius:4px;padding:4px 6px;margin-bottom:4px;border:1px solid rgba(99,102,241,.1)">
        <div style="font-size:8px;color:#6366f1;font-weight:600;margin-bottom:2px">🔍 变化特征码</div>
        ${d.map(e=>`<div style="font-size:8px;color:var(--text);padding:1px 0">${e}</div>`).join(``)}
      </div>`:``}

      <!-- 包含的步骤列表（折叠在内部） -->
      <div style="font-size:9px;color:var(--text2);margin-bottom:3px">📋 包含 ${a-i+1} 个步骤:</div>
      ${(()=>{let e=``;for(let t=i;t<=a;t++){let i=n.steps[t];i&&(e+=I(i,t,r))}return e})()}

      <!-- 编辑/删除 -->
      <div style="display:flex;gap:4px;margin-top:4px;border-top:1px solid var(--border);padding-top:4px">
        <button onclick="window._editAo('${e.id}','${r}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 8px;border-radius:3px;cursor:pointer;font-size:9px">✏️ 编辑</button>
        <button onclick="window._deleteAo('${e.id}','${r}')" style="background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.2);color:#ef4444;padding:2px 8px;border-radius:3px;cursor:pointer;font-size:9px">🗑️ 删除</button>
      </div>
    `}function F(e,t,r){let i=(n.actMap[e.step]||[])[0]||{},s=n.sugMap[e.step]||{},c=e.events||[],l=o&&a.includes(t),u=i.action_type||i.action_desc||s.suggested_op||`浏览/等待`,d=``;c.some(e=>e.t===`click`)&&(d+=`🖱`),c.some(e=>e.t===`key`)&&(d+=`⌨️`),c.some(e=>e.t===`scroll`)&&(d+=`📜`),d||=`⏸`;let f=e.page||{};return`<div style="display:flex;align-items:center;gap:4px;padding:4px 6px;border-bottom:1px solid var(--border);font-size:10px;
      ${l?`background:rgba(99,102,241,.12);border-radius:4px;`:``}
      ${o?`cursor:pointer;`:``}"
      ${o?`onclick="window._stepClick(${t},'${r}')"`:``}>
      <span style="background:#6b7280;color:#fff;border-radius:3px;padding:0 4px;font-size:8px;font-weight:600;flex-shrink:0">${t+1}</span>
      <span>${d}</span>
      <span style="color:var(--text2);font-size:9px;min-width:60px">${R(f.page_mode||`?`)}</span>
      <span style="flex:1;font-weight:500">${u}</span>
      <span style="color:var(--text2);font-size:8px">${c.length}事件</span>
      <button onclick="event.stopPropagation();window._deleteStep(${t},'${r}')" style="background:none;border:none;cursor:pointer;color:var(--text2);font-size:10px" title="删除步骤">✕</button>
    </div>`}function I(e,t,r){let i=(n.actMap[e.step]||[])[0]||{},a=e.events||[],o=i.action_type||i.action_desc||`浏览/等待`,s=a.slice(0,3).map(e=>e.t===`click`?`🖱(${e.x},${e.y})`:e.t===`key`?`⌨️${e.k}`:e.t===`scroll`?`📜${Math.abs(e.dy||0)}`:e.t).join(` `),c=e.page||{};return`<div style="display:flex;align-items:center;gap:4px;padding:3px 6px;border-bottom:1px solid var(--border);font-size:9px">
      <span style="color:var(--text2);min-width:24px;font-size:8px">#${t+1}</span>
      <span style="color:var(--text2);font-size:8px;min-width:50px">${R(c.page_mode||`?`)}</span>
      <span style="flex:1">${o}</span>
      <span style="color:var(--text2);font-size:8px">${s}</span>
      ${e.screenshot_url?`<img src="${e.screenshot_url}" style="width:40px;height:30px;border-radius:2px;object-fit:cover" onerror="this.style.display='none'">`:``}
    </div>`}window._exportBp=function(e){if(!n)return;let t=r.atomOps;if(!t.length){alert(`请先打包至少一个原子操作再导出`);return}let i=prompt(`蓝图名称:`,`录制_`+n.name.replace(`recording_`,``).slice(0,20));if(!i)return;let a=t.map((e,t)=>({step_id:t+1,op:e.name,label:e.label,args:{},note:e.note,tags:e.tags,raw_steps:e.stepRange})),o={name:i,description:`从录制标注导出: `+n.name,platform:n.meta.platform||`douyin`,atom_ops:a,_meta:{source_recording:n.name,exported_at:new Date().toISOString(),total_steps:n.steps.length,deleted_steps:r.deleted.length}},s=new Blob([JSON.stringify(o,null,2)],{type:`application/json`}),c=document.createElement(`a`);c.href=URL.createObjectURL(s),c.download=i+`.json`,c.click(),URL.revokeObjectURL(c.href),document.getElementById(`recStatusMsg_`+e).textContent=`📦 蓝图已导出: `+a.length+` 个原子操作`};function L(e,t){let n={};return n.url=e?.url||t?.url_pattern||`?`,n.mode=e?.page_mode||t?.page_mode||`?`,n.viewport=e?.viewport||``,n.textSnippet=e?.text_snippet||``,n}function R(e){return{grid:`列表页`,player:`播放页`,player_full:`全屏播放`,profile:`个人主页`,search:`搜索页`,unknown:`未知`,modal:`弹窗`}[e]||e}}export{e as loadView};
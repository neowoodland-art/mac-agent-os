async function e(e){let t=Math.random().toString(36).slice(2,6),n=null,r={},i=0;try{r=JSON.parse(localStorage.getItem(`rec_names`)||`{}`)}catch{}e.innerHTML=`
    <div style="padding:12px">
      <!-- ═══ 标题 + 录制控制 ═══ -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:6px">
        <h2 style="font-size:18px;margin:0">🎬 录制与标注</h2>
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
          <select id="recAcct_${t}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;font-size:11px;width:120px"><option value="">加载账号...</option></select>
          <button id="recStartBtn_${t}" onclick="_recStart('${t}')" style="background:#22c55e;color:#fff;border:none;padding:5px 12px;border-radius:5px;cursor:pointer;font-size:11px">▶ 开始录制</button>
          <button id="recStopBtn_${t}" onclick="_recStop('${t}')" style="display:none;background:#ef4444;color:#fff;border:none;padding:5px 12px;border-radius:5px;cursor:pointer;font-size:11px">⏹ 停止</button>
          <span id="recStatus_${t}" style="font-size:10px;color:var(--text2)"></span>
          <button onclick="_reloadAll('${t}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 10px;border-radius:4px;cursor:pointer;font-size:10px">⟳ 刷新</button>
        </div>
      </div>

      <!-- ═══ 录制列表 ═══ -->
      <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px;margin-bottom:10px">
        <div style="font-size:12px;font-weight:600;margin-bottom:6px">📋 录制包</div>
        <div id="recList_${t}" style="font-size:11px;max-height:180px;overflow-y:auto"><div class="loading">加载中...</div></div>
      </div>

      <!-- ═══ 分析面板 ═══ -->
      <div id="recAnalysis_${t}" style="display:none">
        <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px">
          <!-- 标题 -->
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div>
              <span id="recName_${t}" style="font-size:13px;font-weight:600"></span>
              <span id="recMeta_${t}" style="font-size:10px;color:var(--text2);margin-left:6px"></span>
            </div>
            <button onclick="document.getElementById('recAnalysis_${t}').style.display='none'" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">✕ 关闭</button>
          </div>
          <!-- 步骤导航 -->
          <div id="recSteps_${t}" style="display:flex;gap:3px;margin-bottom:8px;overflow-x:auto;padding:2px 0"></div>
          <!-- 当前步骤详情 -->
          <div id="recStepDetail_${t}"></div>
        </div>
      </div>
    </div>`,window._reloadAll=function(e){a(e),l(e),c(e)},window._recStart=function(e){o(e)},window._recStop=function(e){s(e)},window._analyzeRec=function(e,t){u(e,t)},a(t),l(t),c(t);async function a(e){let t=document.getElementById(`recAcct_${e}`);if(t)try{let e=await(await fetch(`/api/matrix/accounts`)).json();t.innerHTML=`<option value="">— 选择账号 —</option>`+(Array.isArray(e)?e:e.accounts||[]).filter(e=>e.is_local&&e.platform).map(e=>`<option value="${e.id}">${e.platform===`douyin`?`🎵`:`📕`} ${e.id}</option>`).join(``)}catch{t.innerHTML=`<option value="">加载失败</option>`}}async function o(e){let t=document.getElementById(`recAcct_${e}`)?.value;if(!t){alert(`请先选择账号`);return}let n=document.getElementById(`recStartBtn_${e}`);n.textContent=`⏳ 启动中...`,n.disabled=!0;try{let r=await(await fetch(`/api/matrix/record/start`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({account:t})})).json();r.status===`ok`?(document.getElementById(`recStatus_${e}`).textContent=`🟢 录制中 (PID ${r.pid})`,document.getElementById(`recStopBtn_${e}`).style.display=``,n.style.display=`none`):alert(r.message)}catch(e){alert(`启动失败: `+e.message)}finally{n.textContent=`▶ 开始录制`,n.disabled=!1}}async function s(e){try{await(await fetch(`/api/matrix/record/stop`,{method:`POST`})).json(),document.getElementById(`recStatus_${e}`).textContent=`⏹ 已停止`,document.getElementById(`recStopBtn_${e}`).style.display=`none`,document.getElementById(`recStartBtn_${e}`).style.display=``,l(e)}catch(e){alert(`停止失败: `+e.message)}}async function c(e){try{let t=await(await fetch(`/api/matrix/record/status`)).json();t.running&&(document.getElementById(`recStatus_${e}`).textContent=`🟢 录制中 (PID ${t.pid})`,document.getElementById(`recStopBtn_${e}`).style.display=``,document.getElementById(`recStartBtn_${e}`).style.display=`none`)}catch{}}async function l(e){let t=document.getElementById(`recList_${e}`);if(t)try{let n=(await(await fetch(`/api/matrix/record/list`)).json()).recordings||[];if(!n.length){t.innerHTML=`<div style="color:var(--text2);padding:8px;text-align:center">暂无录制包</div>`;return}t.innerHTML=n.map(t=>`<div style="display:flex;align-items:center;gap:6px;padding:4px 6px;border-bottom:1px solid var(--border);font-size:10px">
        <span style="font-weight:500;flex:1">${t.name}</span>
        <span style="color:var(--text2);width:30px">${t.platform===`douyin`?`🎵`:`📕`}</span>
        <span style="color:var(--text2);width:80px">${t.account}</span>
        <span style="color:var(--text2);width:30px;text-align:center">${t.steps}步</span>
        <button onclick="window._analyzeRec('${t.name}','${e}')" style="background:none;border:none;cursor:pointer;font-size:11px;color:var(--primary)">📊 分析</button>
      </div>`).join(``)}catch(e){t.innerHTML=`<div style="color:var(--red);padding:8px">❌ ${e.message}</div>`}}async function u(e,t){let r=document.getElementById(`recAnalysis_${t}`);r.style.display=``,document.getElementById(`recName_${t}`).textContent=`📹 ${e}`;try{let r=await(await fetch(`/api/matrix/record/detail/`+encodeURIComponent(e))).json();n={name:e,meta:r.meta||{},steps:r.steps||[],actions:(r.analysis||{}).actions||[],suggestions:(r.analysis||{}).blueprint_suggestions||[]};let a={};n.actions.forEach(e=>{let t=e.step_after||e.step_before;a[t]||(a[t]=[]),a[t].push(e)}),n.actMap=a;let o={};n.suggestions.forEach(e=>{o[e.step]=e}),n.sugMap=o;let s=n.meta;document.getElementById(`recMeta_${t}`).textContent=`${s.platform||`?`} · ${s.account_id||`?`} · ${n.steps.length}步 · ${Math.round(s.duration||0)}s`,d(t),i=0,f(0,t)}catch(e){document.getElementById(`recStepDetail_`+t).innerHTML=`<div style="color:var(--red);padding:8px">❌ ${e.message}</div>`}}function d(e){let t=document.getElementById(`recSteps_${e}`);!t||!n||(t.innerHTML=n.steps.map((t,r)=>{let a=n.sugMap[t.step];return`<span onclick="var _curStep=${r};renderStepDetail(${r},'${e}')" id="stepDot_${r}_${e}"
        style="cursor:pointer;display:inline-block;width:20px;height:20px;line-height:20px;text-align:center;
        border-radius:3px;font-size:9px;background:${a?a.confidence===`high`?`#22c55e`:`#f59e0b`:`#6b7280`};color:#fff;opacity:${r===i?`1`:`0.5`}"
        title="步骤${r+1}">${r+1}</span>`}).join(``))}function f(e,t){let a=document.getElementById(`recStepDetail_${t}`);if(!a||!n||!n.steps[e])return;i=e,document.querySelectorAll(`[id^="stepDot_"]`).forEach(n=>{n.style.opacity=n.id===`stepDot_${e}_${t}`?`1`:`0.5`});let o=n.steps[e],s=(n.actMap[o.step]||[])[0]||{},c=n.sugMap[o.step]||{},l=n.steps[e+1],u=o.page||{},d=l&&l.page||{},f=o.events||[],p=s.features||[],m=s.inferred_action||{},h=c.suggested_op||s.action_type||``,g=r[n.name]?.[e]||``,_=``;_=f.length?f.map(e=>e.t===`click`?`<span style="display:inline-block;background:rgba(99,102,241,.1);border-radius:3px;padding:2px 6px;margin:1px;font-size:9px">🖱 点击 (${e.x},${e.y}) <span style="color:var(--text2)">${e.target||``}</span></span>`:e.t===`key`?`<span style="display:inline-block;background:rgba(245,158,11,.1);border-radius:3px;padding:2px 6px;margin:1px;font-size:9px">⌨️ 按键 ${e.k} ${e.c?`(组合)`:``}</span>`:e.t===`scroll`?`<span style="display:inline-block;background:rgba(34,197,94,.1);border-radius:3px;padding:2px 6px;margin:1px;font-size:9px">📜 滚动</span>`:`<span style="display:inline-block;background:var(--bg3);border-radius:3px;padding:2px 6px;margin:1px;font-size:9px">${e.t||`事件`}</span>`).join(``):`<span style="color:var(--text2);font-size:10px">${s.action_desc||`浏览/等待`}</span>`,a.innerHTML=`
      <!-- 导航 -->
      <div style="display:flex;gap:4px;margin-bottom:6px">
        <button onclick="renderStepDetail(${Math.max(0,e-1)},'${t}')" ${e===0?`disabled`:``}
          style="flex:1;background:${e===0?`var(--bg3)`:`#6366f1`};color:${e===0?`var(--text2)`:`#fff`};border:none;padding:3px;border-radius:4px;cursor:${e===0?`default`:`pointer`};font-size:10px">◀ 上一步</button>
        <span style="font-size:10px;color:var(--text2);padding:3px">${e+1}/${n.steps.length}</span>
        <button onclick="renderStepDetail(${Math.min(n.steps.length-1,e+1)},'${t}')" ${e>=n.steps.length-1?`disabled`:``}
          style="flex:1;background:${e>=n.steps.length-1?`var(--bg3)`:`#6366f1`};color:${e>=n.steps.length-1?`var(--text2)`:`#fff`};border:none;padding:3px;border-radius:4px;cursor:${e>=n.steps.length-1?`default`:`pointer`};font-size:10px">下一步 ▶</button>
      </div>

      <!-- ═══ 三栏：前状态 | 动作 | 后状态 ═══ -->
      <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:6px;margin-bottom:6px">
        <!-- 前状态 -->
        <div style="background:rgba(37,99,235,.06);border-radius:5px;padding:6px;border:1px solid rgba(37,99,235,.12)">
          <div style="font-size:9px;color:#3b82f6;font-weight:600;margin-bottom:3px">⬅ 前状态</div>
          <table style="font-size:9px;width:100%;border-collapse:collapse">
            <tr><td style="color:var(--text2);padding:1px 3px;width:45px">URL</td><td style="padding:1px 3px;word-break:break-all">${(u.url||`?`).slice(0,50)}</td></tr>
            <tr><td style="color:var(--text2);padding:1px 3px">模式</td><td style="padding:1px 3px">${u.page_mode||`?`}</td></tr>
            <tr><td style="color:var(--text2);padding:1px 3px">元素</td><td style="padding:1px 3px">${u.interactable_count||0} 个可交互</td></tr>
            <tr><td style="color:var(--text2);padding:1px 3px">视口</td><td style="padding:1px 3px">${u.viewport||`?`}</td></tr>
          </table>
          ${o.screenshot_url?`<img src="${o.screenshot_url}" style="max-width:100%;max-height:70px;border-radius:3px;margin-top:3px" onerror="this.style.display='none'">`:``}
          ${u.text_snippet?`<div style="font-size:8px;color:var(--text2);margin-top:2px;max-height:40px;overflow:hidden">📄 ${u.text_snippet.slice(0,80)}</div>`:``}
        </div>

        <!-- 动作 -->
        <div style="display:flex;align-items:center;font-size:18px;color:var(--text2);padding:0 2px">→</div>

        <!-- 后状态 -->
        <div style="background:rgba(5,150,105,.06);border-radius:5px;padding:6px;border:1px solid rgba(5,150,105,.12)">
          <div style="font-size:9px;color:#22c55e;font-weight:600;margin-bottom:3px">➡ 后状态</div>
          <table style="font-size:9px;width:100%;border-collapse:collapse">
            <tr><td style="color:var(--text2);padding:1px 3px;width:45px">URL</td><td style="padding:1px 3px;word-break:break-all">${d?(d.url||`同页`).slice(0,50):`(结束)`}</td></tr>
            <tr><td style="color:var(--text2);padding:1px 3px">模式</td><td style="padding:1px 3px">${d?d.page_mode||`?`:`-`}</td></tr>
            <tr><td style="color:var(--text2);padding:1px 3px">变化</td><td style="padding:1px 3px">
              ${s.url_changed?`🔗 URL变化 `:``}${s.text_changed?`📝 文本变化 `:``}${s.mode_changed||``}
            </td></tr>
          </table>
          ${l&&l.screenshot_url?`<img src="${l.screenshot_url}" style="max-width:100%;max-height:70px;border-radius:3px;margin-top:3px" onerror="this.style.display='none'">`:``}
          ${d&&d.text_snippet?`<div style="font-size:8px;color:var(--text2);margin-top:2px;max-height:40px;overflow:hidden">📄 ${d.text_snippet.slice(0,80)}</div>`:``}
        </div>
      </div>

      <!-- ═══ 动作详情与推断 ═══ -->
      <div style="background:var(--bg3);border-radius:5px;padding:6px;margin-bottom:6px">
        <div style="font-size:9px;color:var(--text2);font-weight:600;margin-bottom:3px">🖱 检测到的动作</div>
        <div style="display:flex;gap:3px;flex-wrap:wrap;margin-bottom:3px">${_}</div>
        ${p.length?`<div style="font-size:8px;color:var(--text2)">${p.map(e=>`<code style="background:var(--bg2);padding:1px 3px;border-radius:2px;margin:1px">${e.code}</code>`).join(``)}</div>`:``}
        ${m.trigger?`<div style="font-size:8px;color:var(--text2);margin-top:2px">触发: ${m.trigger}</div>`:``}
        ${m.desc?`<div style="font-size:8px;color:var(--text2)">描述: ${m.desc}</div>`:``}
      </div>

      <!-- ═══ 原子操作命名 ═══ -->
      <div style="display:flex;gap:4px;align-items:center;margin-bottom:4px">
        <span style="font-size:10px;color:var(--text2)">🏷️ 原子操作:</span>
        <input id="nameInput_${e}_${t}" value="${g||h}"
          style="flex:1;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:3px;font-size:10px"
          onchange="var v=this.value.trim();if(v){if(!_names['${n.name}'])_names['${n.name}']={};_names['${n.name}'][${e}]=v;localStorage.setItem('rec_names',JSON.stringify(_names))}">
        <button onclick="window._testAtomOp(document.getElementById('nameInput_${e}_${t}').value,'${t}')"
          style="background:#22c55e;color:#fff;border:none;padding:3px 8px;border-radius:3px;cursor:pointer;font-size:10px">🧪 测试</button>
      </div>

      <!-- 保存/导出 -->
      <div style="display:flex;gap:4px">
        <button onclick="var c=_names['${n.name}']?Object.keys(_names['${n.name}']).length:0;localStorage.setItem('rec_names',JSON.stringify(_names));document.getElementById('recSaveStatus_${t}').textContent='✅ 已保存 '+c+'/'+_recording.steps.length+' 步'"
          style="flex:1;background:var(--primary);color:#fff;border:none;padding:3px;border-radius:4px;cursor:pointer;font-size:10px">💾 保存命名</button>
        <button onclick="_exportBp('${t}')"
          style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">📦 导出蓝图</button>
      </div>
      <div id="recSaveStatus_${t}" style="margin-top:2px;font-size:9px;color:var(--text2)"></div>
    `}window._testAtomOp=async function(e,t){if(!e||!n)return;let r=n.meta.account_id,i=n.meta.platform||`douyin`,a=document.getElementById(`recSaveStatus_`+t);if(!r){a.textContent=`❌ 无账号信息`;return}a.textContent=`⏳ 正在提交测试...`;try{let t=await(await fetch(`/api/ops/test-atom`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({op:e,account:r,platform:i})})).json();a.textContent=`✅ 测试已提交: `+(t.status||`ok`)+(t.details?` | `+t.details:``)}catch(e){a.textContent=`❌ `+e.message}},window._exportBp=function(e){if(!n)return;let t=r[n.name]||{};if(Object.keys(t).length===0){alert(`请先命名步骤再导出`);return}let i=prompt(`蓝图名称:`,`录制_`+n.name.replace(`recording_`,``).slice(0,20));if(!i)return;let a=Object.keys(t).sort((e,t)=>e-t).map(e=>({step_id:parseInt(e)+1,op:t[e],args:{}})),o={name:i,description:`从录制标注导出: `+n.name,platform:n.meta.platform||`douyin`,steps:a},s=new Blob([JSON.stringify(o,null,2)],{type:`application/json`}),c=document.createElement(`a`);c.href=URL.createObjectURL(s),c.download=i+`.json`,c.click(),URL.revokeObjectURL(c.href),document.getElementById(`recSaveStatus_`+e).textContent=`📦 蓝图已导出: `+a.length+` 步`}}export{e as loadView};
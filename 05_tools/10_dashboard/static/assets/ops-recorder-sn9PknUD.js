async function e(e){let t=Math.random().toString(36).slice(2,6),n=null,r={};try{r=JSON.parse(localStorage.getItem(`rec_names`)||`{}`)}catch{}e.innerHTML=`
    <div style="padding:12px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">🎬 录制标注</h2>
        <div style="display:flex;gap:6px;font-size:12px">
          <button onclick="_reloadRec('${t}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 12px;border-radius:6px;cursor:pointer">⟳ 刷新</button>
        </div>
      </div>

      <!-- 录制列表（初始可见） -->
      <div id="recList_${t}" style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:12px;margin-bottom:10px">
        <div style="font-size:12px;font-weight:600;margin-bottom:8px">📋 录制包列表</div>
        <div id="recListBody_${t}"><div class="loading" style="font-size:12px;padding:8px">加载录制列表...</div></div>
      </div>

      <!-- 录制详情面板（选择后显示） -->
      <div id="recDetail_${t}" style="display:none">
        <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:12px">
          <!-- 标题行 -->
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div>
              <span id="recName_${t}" style="font-size:13px;font-weight:600"></span>
              <span id="recMeta_${t}" style="font-size:11px;color:var(--text2);margin-left:8px"></span>
            </div>
            <button onclick="_recBack('${t}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">← 返回列表</button>
          </div>

          <!-- 步骤概览条 -->
          <div style="display:flex;gap:4px;margin-bottom:8px;overflow-x:auto;padding:2px 0" id="recStepBar_${t}"></div>

          <!-- 当前步骤详情 -->
          <div id="recStepDetail_${t}" style="font-size:11px">选择步骤查看详情</div>
        </div>
      </div>
    </div>`,window._reloadRec=function(e){i(e)},window._selectRec=function(e,t){a(e,t)},window._recBack=function(e){document.getElementById(`recDetail_${e}`).style.display=`none`,document.getElementById(`recList_${e}`).style.display=``},window._goStep=function(e,t){s(e,t)},i(t);async function i(e){let t=document.getElementById(`recListBody_${e}`);if(t)try{let n=(await(await fetch(`/api/matrix/record/list`)).json()).recordings||[];if(!n.length){t.innerHTML=`<div style="color:var(--text2);padding:12px;text-align:center">暂无录制包</div>`;return}t.innerHTML=`<table style="width:100%;border-collapse:collapse;font-size:12px">
        <thead><tr style="font-size:10px;color:var(--text2);border-bottom:1px solid var(--border)">
          <th style="padding:4px 6px;text-align:left">名称</th>
          <th style="padding:4px 6px;text-align:left">平台</th>
          <th style="padding:4px 6px;text-align:left">账号</th>
          <th style="padding:4px 6px;text-align:center">步数</th>
          <th style="padding:4px 6px;text-align:center">时长</th>
          <th style="padding:4px 6px;text-align:center">操作</th>
        </tr></thead><tbody>${n.map(t=>`<tr style="border-bottom:1px solid var(--border)">
            <td style="padding:4px 6px;font-weight:500">${t.name}</td>
            <td style="padding:4px 6px">${t.platform===`douyin`?`🎵`:`📕`} ${t.platform}</td>
            <td style="padding:4px 6px;color:var(--text2)">${t.account}</td>
            <td style="padding:4px 6px;text-align:center">${t.steps}</td>
            <td style="padding:4px 6px;text-align:center;color:var(--text2)">${Math.round(t.duration)}s</td>
            <td style="padding:4px 6px;text-align:center">
              <button onclick="window._selectRec('${t.name}','${e}')" style="background:none;border:none;cursor:pointer;font-size:12px;color:var(--primary)">📝 标注</button>
            </td>
          </tr>`).join(``)}</tbody></table>`}catch(e){t.innerHTML=`<div style="color:var(--red);padding:8px;font-size:12px">❌ 加载失败: ${e.message}</div>`}}async function a(e,t){document.getElementById(`recList_${t}`).style.display=`none`;let r=document.getElementById(`recDetail_${t}`);r.style.display=``,document.getElementById(`recName_${t}`).textContent=`📹 ${e}`;try{let r=await(await fetch(`/api/matrix/record/detail/`+encodeURIComponent(e))).json(),i=r.meta||{},a=r.steps||[],c=r.analysis||{},l=c.actions||[],u=c.blueprint_suggestions||[];n={name:e,meta:i,steps:a,actions:l,suggestions:u},document.getElementById(`recMeta_${t}`).textContent=`${i.platform||`?`} · ${i.account_id||`?`} · ${a.length}步 · ${Math.round(i.duration||0)}s`;let d={};l.forEach(e=>{let t=e.step_after||e.step_before;d[t]||(d[t]=[]),d[t].push(e)}),n.actMap=d;let f={};u.forEach(e=>{f[e.step]=e}),n.sugMap=f,o(t),s(0,t)}catch(e){document.getElementById(`recStepDetail_${t}`).innerHTML=`<div style="color:var(--red);font-size:12px;padding:8px">❌ ${e.message}</div>`}}function o(e){let t=document.getElementById(`recStepBar_${e}`);if(!t||!n)return;let r=n.actions,i=[];r.forEach(e=>{e.page_mode&&i.indexOf(e.page_mode)===-1&&i.push(e.page_mode)}),t.innerHTML=`<span style="font-size:10px;color:var(--text2);white-space:nowrap;margin-right:6px">状态流:</span>
      <div style="display:flex;gap:3px;font-size:9px;flex-wrap:nowrap">${n.steps.slice(0,20).map((t,r)=>{let i=n.actMap[t.step]||[],a=i.length&&i[0].page_mode||`?`,o=n.sugMap[t.step];return`<span onclick="showStep(${r},'${e}')" id="stepDot_${r}_${e}"
            style="cursor:pointer;display:inline-block;width:18px;height:18px;line-height:18px;text-align:center;
            border-radius:3px;font-size:8px;background:${o?o.confidence===`high`?`#22c55e`:`#f59e0b`:`#6b7280`};color:#fff;opacity:${r===0?`1`:`0.6`}"
            title="步骤${r+1}: ${a}">${r+1}</span>`}).join(``)}</div>`}function s(e,t){let i=document.getElementById(`recStepDetail_${t}`);if(!i||!n||!n.steps[e])return;if(document.querySelectorAll(`[id^="stepDot_"]`).forEach(n=>{n.style.opacity=n.id===`stepDot_${e}_${t}`?`1`:`0.6`}),window._recordingStepIdx!==void 0&&window._recordingStepIdx!==e){let e=document.getElementById(`nameInput_${window._recordingStepIdx}_${t}`);e&&e.value.trim()&&(r[n.name]||(r[n.name]={}),r[n.name][window._recordingStepIdx]=e.value.trim())}window._recordingStepIdx=e;let a=n.steps[e],o=(n.actMap[a.step]||[])[0]||{},s=n.sugMap[a.step]||{},c=o.action_desc||`浏览/等待`,l=s.suggested_op||o.action_type||``,u=o.page_mode||`?`,d=n.steps[e+1],f=d&&(n.actMap[d.step]||[])[0]?.page_mode||`?`,p=a.screenshot_url||``,m=a.page?a.page.url:``;a.page&&(a.page.text_snippet||``).slice(0,60);let h=o.features||[],g=o.inferred_action||{},_=r[n.name]?.[e]||``;i.innerHTML=`
      <div style="display:flex;gap:4px;margin-bottom:6px">
        <button onclick="showStep(${Math.max(0,e-1)},'${t}')" ${e===0?`disabled`:``}
          style="flex:1;background:${e===0?`var(--bg3)`:`#6366f1`};color:${e===0?`var(--text2)`:`#fff`};border:none;padding:4px;border-radius:4px;cursor:${e===0?`default`:`pointer`};font-size:10px">◀ 上一步</button>
        <span style="font-size:10px;color:var(--text2);padding:4px">${e+1} / ${n.steps.length}</span>
        <button onclick="showStep(${Math.min(n.steps.length-1,e+1)},'${t}')" ${e>=n.steps.length-1?`disabled`:``}
          style="flex:1;background:${e>=n.steps.length-1?`var(--bg3)`:`#6366f1`};color:${e>=n.steps.length-1?`var(--text2)`:`#fff`};border:none;padding:4px;border-radius:4px;cursor:${e>=n.steps.length-1?`default`:`pointer`};font-size:10px">下一步 ▶</button>
      </div>

      <div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;margin-bottom:6px">
          <span style="font-weight:600;font-size:11px">步骤 ${e+1}: ${u} → ${f}</span>
          <span style="font-size:10px;color:var(--text2)">🖱 ${c}</span>
        </div>

        <!-- before / after 截图 -->
        <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:6px;margin-bottom:6px">
          <div style="background:rgba(37,99,235,.08);border-radius:4px;padding:4px;border:1px solid rgba(37,99,235,.15)">
            <div style="font-size:8px;color:#3b82f6;font-weight:600;margin-bottom:2px">⬅ 前状态</div>
            <div style="font-size:8px;color:var(--text2);word-break:break-all">${m?m.slice(0,60):`(无URL)`}</div>
            ${p?`<div style="margin-top:2px"><img src="${p}" style="max-width:100%;max-height:80px;border-radius:3px;background:var(--bg2)" onerror="this.style.display='none'"></div>`:``}
          </div>
          <div style="display:flex;align-items:center;font-size:14px;color:var(--text2)">→</div>
          <div style="background:rgba(5,150,105,.08);border-radius:4px;padding:4px;border:1px solid rgba(5,150,105,.15)">
            <div style="font-size:8px;color:#22c55e;font-weight:600;margin-bottom:2px">➡ 后状态</div>
            <div style="font-size:8px;color:var(--text2)">${d?(d.page?.url||`同页`).slice(0,60):`(结束)`}</div>
            ${d&&d.screenshot_url?`<div style="margin-top:2px"><img src="${d.screenshot_url}" style="max-width:100%;max-height:80px;border-radius:3px;background:var(--bg2)" onerror="this.style.display='none'"></div>`:``}
          </div>
        </div>

        <!-- 原子操作命名 -->
        <div style="margin-bottom:4px">
          <div style="font-size:9px;color:var(--text2);margin-bottom:2px">🏷️ 原子操作名:</div>
          <div style="display:flex;gap:4px">
            <input id="nameInput_${e}_${t}" value="${_||l}"
              style="flex:1;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:3px;font-size:10px"
              onchange="var v=this.value.trim();if(v){if(!_names['${n.name}'])_names['${n.name}']={};_names['${n.name}'][${e}]=v;localStorage.setItem('rec_names',JSON.stringify(_names))}">
            <select style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px;border-radius:3px;font-size:9px;max-width:120px"
              onchange="var inp=document.getElementById('nameInput_${e}_${t}');if(this.value){inp.value=this.value;inp.onchange()};this.value=''">
              <option value="">↕ 快速选</option>
              ${[``,`goto_home`,`scroll_feed`,`open_video`,`like`,`collect`,`comment`,`follow`,`go_back`,`next_video`,`search_input`,`read_field`,`click_result`,`send_comment`,`post_comment`,`expand_full`,`goto_profile`,`goto_branch`,`search_user`,`close_modal`,`wait_watch`].filter(e=>e!==(_||l)).map(e=>`<option value="${e}">${e||`清空`}</option>`).join(``)}
            </select>
          </div>
        </div>

        <!-- 特征代码 -->
        ${h.length?`<div style="margin-top:4px;font-size:8px;color:var(--text2)">${h.map(e=>`<code style="background:var(--bg2);padding:1px 3px;border-radius:2px;margin:1px;font-size:8px">${e.code}</code>`).join(``)}</div>`:``}

        <!-- 推断详情 -->
        <div style="margin-top:4px;display:flex;gap:6px;font-size:9px;color:var(--text2)">
          ${g.coords?`<span>📌 坐标: (${g.coords.x},${g.coords.y})</span>`:``}
          ${o.url_changed?`<span>🔗 URL变化</span>`:``}
          ${o.text_changed?`<span>📝 文本变化</span>`:``}
          ${g.trigger?`<span>⚡ ${g.trigger}</span>`:``}
        </div>
      </div>

      <!-- 保存/导出按钮 -->
      <div style="margin-top:6px;display:flex;gap:4px">
        <button onclick="var nms=_names['${n.name}'];var c=Object.keys(nms||{}).length;localStorage.setItem('rec_names',JSON.stringify(_names));document.getElementById('recSaveStatus_${t}').textContent='✅ 已保存 '+c+'/'+_recording.steps.length+' 步'" style="flex:1;background:var(--primary);color:#fff;border:none;padding:4px;border-radius:4px;cursor:pointer;font-size:10px">💾 保存全部命名</button>
        <button onclick="_exportRec('${t}')" style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">📦 导出蓝图</button>
      </div>
      <div id="recSaveStatus_${t}" style="margin-top:2px;font-size:9px;color:var(--text2)"></div>
    `}window._exportRec=function(e){if(!n)return;let t=n.name,i=r[t]||{};if(Object.keys(i).length===0){alert(`请先命名步骤再导出`);return}let a=prompt(`蓝图名称:`,`录制_`+t.replace(`recording_`,``).slice(0,20));if(!a)return;let o=Object.keys(i).sort((e,t)=>e-t).map(e=>({step_id:parseInt(e)+1,op:i[e],args:{}})),s={name:a,description:`从录制标注自动导出: `+t,platform:n.meta.platform||`douyin`,steps:o},c=new Blob([JSON.stringify(s,null,2)],{type:`application/json`}),l=document.createElement(`a`);l.href=URL.createObjectURL(c),l.download=a+`.json`,l.click(),URL.revokeObjectURL(l.href),document.getElementById(`recSaveStatus_${e}`).textContent=`📦 蓝图已导出: `+o.length+` 步`}}export{e as loadView};
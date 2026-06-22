async function e(e){let i=Math.random().toString(36).slice(2,6);e.innerHTML=`
    <div style="padding:12px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">🎬 录制标注</h2>
        <div style="display:flex;gap:6px;font-size:12px">
          <button onclick="_reloadRec('${i}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 12px;border-radius:6px;cursor:pointer">⟳ 刷新</button>
        </div>
      </div>

      <!-- 录制列表 -->
      <div id="recList_${i}" style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:12px;margin-bottom:10px">
        <div style="font-size:12px;font-weight:600;margin-bottom:8px">📋 录制包列表</div>
        <div id="recListBody_${i}"><div class="loading" style="font-size:12px;padding:8px">加载录制列表...</div></div>
      </div>

      <!-- 录制详情 + 标注面板 -->
      <div id="recDetail_${i}" style="display:none">
        <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:12px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div>
              <span id="recName_${i}" style="font-size:13px;font-weight:600"></span>
              <span id="recMeta_${i}" style="font-size:11px;color:var(--text2);margin-left:8px"></span>
            </div>
            <div style="display:flex;gap:6px">
              <button onclick="_exportRec('${i}')" style="background:var(--primary);color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">📦 导出蓝图</button>
            </div>
          </div>
          <div id="stepsTimeline_${i}" style="font-size:11px">
            <div class="loading" style="padding:8px">加载步骤...</div>
          </div>
        </div>
      </div>
    </div>`,t(i),window._reloadRec=function(e){t(e)},window._selectRec=function(e,t){n(e,t)},window._renameStep=function(e,t){var n=document.getElementById(`stepLabel_${e}_${t}`),r=prompt(`输入操作名称（如: like, collect, post_comment）:`,n?.dataset.op||``);r&&n&&(n.textContent=r,n.dataset.op=r)},window._exportRec=function(e){r(e)},window._mergeSteps=function(e,t){var n=document.getElementById(`stepBlock_${e+1}_${t}`);if(!n){alert(`没有下一步可合并`);return}if(confirm(`合并步骤 `+(e+1)+` 和 `+(e+2)+` ？`)){n.style.display=`none`;var r=document.getElementById(`stepSep_${e}_${t}`);r&&(r.style.display=`none`),alert(`✅ 已合并（显示中隐藏了下一步，导出时会合并操作）`)}}}async function t(e){var t=document.getElementById(`recListBody_${e}`);if(t)try{var n=(await(await fetch(`/api/matrix/record/list`)).json()).recordings||[];if(!n.length){t.innerHTML=`<div style="font-size:12px;color:var(--text2);padding:8px">暂无录制记录</div>`;return}t.innerHTML=`<table style="width:100%;font-size:11px;border-collapse:collapse">
      <thead><tr style="border-bottom:1px solid var(--border)">
        <th style="padding:4px 6px;text-align:left">名称</th>
        <th style="padding:4px 6px;text-align:left">平台</th>
        <th style="padding:4px 6px;text-align:left">账号</th>
        <th style="padding:4px 6px;text-align:center">步数</th>
        <th style="padding:4px 6px;text-align:center">时长</th>
        <th style="padding:4px 6px;text-align:center">操作</th>
      </tr></thead>
      <tbody>${n.map(function(t){return`
        <tr style="border-bottom:1px solid var(--border)">
          <td style="padding:4px 6px;font-weight:500">${t.name}</td>
          <td style="padding:4px 6px">${t.platform===`douyin`?`🎵`:`📕`} ${t.platform}</td>
          <td style="padding:4px 6px;color:var(--text2)">${t.account}</td>
          <td style="padding:4px 6px;text-align:center">${t.steps}</td>
          <td style="padding:4px 6px;text-align:center;color:var(--text2)">${Math.round(t.duration)}s</td>
          <td style="padding:4px 6px;text-align:center">
            <button onclick="window._selectRec('${t.name}','${e}')" style="background:none;border:none;cursor:pointer;font-size:12px;color:var(--primary)">📝 标注</button>
          </td>
        </tr>`}).join(``)}</tbody></table>`}catch(e){t.innerHTML=`<div style="color:var(--red);padding:8px;font-size:12px">❌ 加载失败: `+e.message+`</div>`}}async function n(e,t){var n=document.getElementById(`recDetail_${t}`),r=document.getElementById(`recName_${t}`),i=document.getElementById(`recMeta_${t}`),a=document.getElementById(`stepsTimeline_${t}`);if(n){n.style.display=`block`,r.textContent=`📹 ${e}`;try{var o=await(await fetch(`/api/matrix/record/detail/`+encodeURIComponent(e))).json(),s=o.meta||{},c=o.steps||[],l=(o.analysis||{}).actions||[];i.textContent=`${s.platform||`?`} · ${s.account_id||`?`} · ${c.length}步 · ${Math.round(s.duration||0)}s`;var u={};l.forEach(function(e){var t=e.step_after||e.step_before;u[t]||(u[t]=[]),u[t].push(e)});var d=`<div style="margin-bottom:10px;font-size:10px;color:var(--text2)">状态流: `;d+=c.map(function(e,t){var n=u[e.step]||[],r=n.length&&n[0].page_mode||`?`,i=u[c[t+1]?c[t+1].step:-1]||[];return`<span style="display:inline-block;padding:1px 6px;margin:1px;background:var(--bg3);border-radius:3px">${r} → ${i.length&&i[0].page_mode||`?`}</span>`}).join(` `),d+=`</div>`,c.forEach(function(e,n){var r=(u[e.step]||[])[0]||{},i=r.inferred_action||{},a=r.action_desc||`浏览/等待`,o=r.action_type||``,s=r.page_mode||`?`,l=c[n+1],f=l&&u[l.step]||[],p=f.length&&f[0].page_mode||`?`,m=e.screenshot_url||``,h=e.page?e.page.url:``,g=e.page?(e.page.text_snippet||``).slice(0,80):``;d+=`<div id="stepBlock_${n}_${t}" style="background:var(--bg3);border-radius:6px;padding:10px;margin-bottom:8px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <span style="font-size:11px;font-weight:600">步骤 ${n+1}: ${s} → ${p}</span>
          <div style="display:flex;gap:4px;font-size:10px">
            <button onclick="window._renameStep(${n},'${t}')" style="background:var(--primary);color:#fff;border:none;padding:2px 8px;border-radius:4px;cursor:pointer">✏️ 命名</button>
            <button onclick="window._mergeSteps(${n},'${t}')" style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:2px 8px;border-radius:4px;cursor:pointer">🔗 合并下步</button>
          </div>
        </div>

        <!-- before → action → after 三栏 -->
        <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:start">
          <div style="background:rgba(37,99,235,.08);border-radius:5px;padding:6px;border:1px solid rgba(37,99,235,.15)">
            <div style="font-size:9px;color:#3b82f6;font-weight:600;margin-bottom:2px">⬅ 前状态</div>
            <div style="font-size:10px;word-break:break-all">${h?`<span style="color:var(--text2)">URL:</span> `+h.slice(0,60):`<span style="color:var(--text2)">(无URL)</span>`}</div>
            ${g?`<div style="font-size:9px;color:var(--text2);margin-top:2px">📄 `+g+`</div>`:``}
            ${m?`<div style="margin-top:4px"><img src="`+m+`" style="max-width:100%;max-height:120px;border-radius:4px;background:var(--bg3)" onerror="this.style.display='none'"></div>`:``}
          </div>

          <div style="display:flex;align-items:center;padding:0 4px;font-size:16px;color:var(--text2)">→</div>

          <div style="background:rgba(5,150,105,.08);border-radius:5px;padding:6px;border:1px solid rgba(5,150,105,.15)">
            <div style="font-size:9px;color:#22c55e;font-weight:600;margin-bottom:2px">➡ 后状态</div>
            <div style="font-size:10px">${l?l.page?l.page.url.slice(0,60):`同页`:`(结束)`}</div>
            ${l&&l.screenshot_url?`<div style="margin-top:4px"><img src="`+l.screenshot_url+`" style="max-width:100%;max-height:120px;border-radius:4px;background:var(--bg3)" onerror="this.style.display='none'"></div>`:``}
          </div>
        </div>

        <!-- 操作详情 -->
        <div style="margin-top:6px;display:flex;gap:8px;align-items:flex-start;flex-wrap:wrap">
          <div style="background:var(--bg2);border-radius:4px;padding:4px 8px;font-size:10px;flex:1">
            <span style="color:var(--text2)">🖱 操作:</span> ${a}
            ${i.coords?` <span style="color:var(--text2)">坐标:</span> (`+i.coords.x+`,`+i.coords.y+`)`:``}
            ${r.text_changed?`<span style="color:var(--green);margin-left:4px">📝 文本变化</span>`:``}
            ${r.url_changed?`<span style="color:#3b82f6;margin-left:4px">🔗 URL变化</span>`:``}
          </div>
          <div style="display:flex;align-items:center;gap:4px;font-size:11px">
            <span style="color:var(--text2)">🏷️ 原子操作名:</span>
            <span id="stepLabel_${n}_${t}" data-op="${o}" style="font-weight:600;background:var(--bg2);padding:2px 8px;border-radius:4px;cursor:pointer;border:1px dashed var(--border)" onclick="window._renameStep(${n},'${t}')">${o||`点击命名...`}</span>
          </div>
        </div>

        <!-- 特征代码 -->
        ${r.features&&r.features.length?`<div style="margin-top:4px;font-size:9px;color:var(--text2)">`+r.features.map(function(e){return`<code style="background:var(--bg2);padding:1px 4px;border-radius:2px;margin:1px">`+e.code+`</code>`}).join(``)+`</div>`:``}

      </div>`,n<c.length-1&&(d+=`<div id="stepSep_${n}_${t}" style="text-align:center;padding:2px 0;color:var(--text2);font-size:14px">↓</div>`)}),d+=`<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:4px">
      <span style="font-size:10px;color:var(--text2);flex:1">💡 点击名称命名，连续步骤可合并</span>
      <button onclick="window._exportRec('${t}')" style="background:var(--primary);color:#fff;border:none;padding:5px 14px;border-radius:6px;cursor:pointer;font-size:12px">📦 导出为蓝图</button>
    </div>`,a.innerHTML=d}catch(e){a.innerHTML=`<div style="color:var(--red);padding:8px;font-size:12px">❌ 加载失败: `+e.message+`</div>`}}}async function r(e){var t=document.querySelectorAll(`[id^="stepLabel_"]`),n=[];t.forEach(function(e){var t=e.dataset.op||e.textContent;t&&t!==`点击命名...`&&n.push(t)});var r=prompt(`蓝图名称:`,`recording_export`);if(r)try{var i=await fetch(`/api/matrix/blueprints`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({name:r,description:`从录制标注导出`,platform:`douyin`,steps:n.map(function(e){return{name:e}})})});i.ok?alert(`✅ 蓝图 "`+r+`" 已创建 (`+n.length+`步)`):alert(`❌ 创建失败: `+(await i.json()).detail)}catch(e){alert(`❌ `+e.message)}}export{e as loadView};
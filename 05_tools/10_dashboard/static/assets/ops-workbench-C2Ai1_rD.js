async function e(e){let t=Math.random().toString(36).slice(2,6);e.innerHTML=`
    <div style="padding:12px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">🧭 操作原子工作台</h2>
        <div style="display:flex;gap:6px;font-size:12px">
          <button onclick="_reloadWorkbench('${t}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 12px;border-radius:6px;cursor:pointer">⟳ 刷新</button>
        </div>
      </div>

      <!-- 三栏布局 -->
      <div style="display:grid;grid-template-columns:220px 1fr 280px;gap:10px;min-height:500px">

        <!-- ═══ 左栏：状态流 ═══ -->
        <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px;font-size:11px">
          <div style="font-weight:600;font-size:12px;margin-bottom:8px">🔄 状态流</div>
          <div id="stateFlow_${t}" style="color:var(--text2)">
            <div class="loading" style="padding:8px">加载流程图...</div>
          </div>
        </div>

        <!-- ═══ 中栏：原子操作面板 ═══ -->
        <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px;font-size:11px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <span style="font-weight:600;font-size:12px">⚡ 原子操作</span>
            <span id="opCount_${t}" style="font-size:10px;color:var(--text2)"></span>
          </div>
          <div style="display:flex;gap:4px;margin-bottom:8px;flex-wrap:wrap" id="opCategoryTabs_${t}">
            <span onclick="_filterCat('all','${t}')" data-cat="all" style="padding:3px 8px;border-radius:4px;cursor:pointer;background:var(--primary);color:#fff;font-size:10px">全部</span>
          </div>
          <div id="opList_${t}" style="max-height:260px;overflow-y:auto">
            <div class="loading" style="padding:8px">加载原子操作...</div>
          </div>
          <!-- 操作详情面板 -->
          <div id="opDetail_${t}" style="margin-top:6px;font-size:10px;display:none">
            <div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--primary)">
              <div id="opDetailBody_${t}"></div>
            </div>
          </div>
        </div>

        <!-- ═══ 右栏：录制标注 ═══ -->
        <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px;font-size:11px;display:flex;flex-direction:column">
          <div style="font-weight:600;font-size:12px;margin-bottom:8px">🎬 录制标注</div>
          <div id="recPanel_${t}" style="flex:1;overflow-y:auto">
            <div style="color:var(--text2);padding:8px;text-align:center">
              <p style="font-size:12px;margin-bottom:8px">选择录制包开始标注</p>
              <select id="recSelect_${t}" onchange="_loadRecDetail(this.value,'${t}')" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px;border-radius:4px;font-size:11px;margin-bottom:6px">
                <option value="">— 选择录制包 —</option>
              </select>
              <button onclick="_reloadRecList('${t}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">⟳ 刷新</button>
            </div>
            <div id="recSteps_${t}" style="font-size:10px;margin-top:4px"></div>
          </div>
        </div>

      </div>
    </div>`,window._reloadWorkbench=function(e){i(e),n(e),p(e)},window._filterCat=function(e,t){a(e,t)},window._reloadRecList=function(e){p(e)},window._loadRecDetail=function(e,t){e&&m(e,t)},i(t),n(t),p(t)}var t={douyin:[{id:`grid`,label:`首页精选`,icon:`🏠`},{id:`branch`,label:`分支页`,icon:`📂`},{id:`player_modal`,label:`视频浮层`,icon:`▶️`},{id:`player_full`,label:`视频全屏`,icon:`📺`},{id:`search`,label:`搜索结果`,icon:`🔍`},{id:`profile`,label:`个人主页`,icon:`👤`},{id:`user_profile`,label:`博主主页`,icon:`🌟`}],xiaohongshu:[{id:`grid`,label:`首页推荐`,icon:`🏠`},{id:`note_detail`,label:`笔记详情`,icon:`📄`},{id:`search`,label:`搜索结果`,icon:`🔍`},{id:`profile`,label:`个人主页`,icon:`👤`}]};async function n(e){let n=document.getElementById(`stateFlow_${e}`);if(!n)return;let r=``,i=t.douyin;i.forEach((e,t)=>{r+=`<div style="display:flex;align-items:center;padding:4px 6px;border-radius:4px;margin:2px 0;background:var(--bg3)">
      <span style="margin-right:6px">${e.icon}</span>
      <span style="flex:1">${e.label}</span>
      <span style="font-size:9px;color:var(--text2)">⬤</span>
    </div>`,t<i.length-1&&(r+=`<div style="text-align:center;font-size:8px;color:var(--text2);padding:1px 0">│</div>`)}),r+=`<div style="margin-top:8px;padding-top:6px;border-top:1px solid var(--border)">
    <div style="font-size:10px;color:var(--text2);margin-bottom:4px">📕 小红书流程</div>`,t.xiaohongshu.forEach(e=>{r+=`<div style="display:flex;align-items:center;padding:3px 6px;border-radius:3px;margin:1px 0;background:var(--bg3)">
      <span style="margin-right:6px">${e.icon}</span>
      <span>${e.label}</span>
    </div>`}),r+=`</div>`,n.innerHTML=r}var r=[];async function i(e){let t=document.getElementById(`opList_${e}`),n=document.getElementById(`opCategoryTabs_${e}`),i=document.getElementById(`opCount_${e}`);if(t)try{r=(await(await fetch(`/api/matrix/atom-ops`)).json()).ops||[];let t={};r.forEach(e=>{let n=e.category||`其他`;t[n]||(t[n]=0),t[n]++});let a=`<span onclick="_filterCat('all','${e}')" data-cat="all" style="padding:3px 8px;border-radius:4px;cursor:pointer;background:var(--primary);color:#fff;font-size:10px">全部 (${r.length})</span>`;Object.keys(t).sort().forEach(n=>{a+=`<span onclick="_filterCat('${n.replace(/'/g,`\\'`)}','${e}')" data-cat="${n}" style="padding:3px 8px;border-radius:4px;cursor:pointer;background:var(--bg3);color:var(--text);font-size:10px">${n} (${t[n]})</span>`}),n.innerHTML=a,i.textContent=`${r.length} 个操作`,l(r,e)}catch(e){t.innerHTML=`<div style="color:var(--red);padding:8px">❌ 加载失败: ${e.message}</div>`}}function a(e,t){document.querySelectorAll(`[data-cat]`).forEach(t=>{let n=t.dataset.cat===e;t.style.background=n?`var(--primary)`:`var(--bg3)`,t.style.color=n?`#fff`:`var(--text)`}),l(e===`all`?r:r.filter(t=>(t.category||`其他`)===e),t)}var o={tested:`#22c55e`,partial:`#f59e0b`,untested:`#6b7280`,failed:`#ef4444`},s={scroll_feed:`tested`,open_video:`tested`,go_back:`tested`,like:`tested`,comment:`tested`,next_video:`tested`,read_field:`tested`,goto_home:`tested`,goto_branch:`tested`,search_input:`tested`,goto_profile:`partial`,follow:`partial`,click_result:`partial`,search_user:`partial`,read_fans:`partial`,collect:`failed`,collect_profile:`failed`,post_comment:`failed`,open_video_new:`untested`,goto_author:`untested`,expand_full:`untested`,open_comments:`untested`,goto_user:`untested`,click_user:`untested`,click_note:`untested`,next_note:`untested`};function c(e){return s[e]||`untested`}function l(e,t){let n=document.getElementById(`opList_${t}`);if(!n)return;if(!e.length){n.innerHTML=`<div style="color:var(--text2);padding:12px;text-align:center">无匹配操作</div>`;return}let r=``;e.forEach(e=>{let n=c(e.name),i=o[n]||`#6b7280`,a={tested:`✅已通过`,partial:`🟡部分`,failed:`🔴失败`,untested:`⚪未测`}[n]||`⚪未测`,s=e.label||e.name||`?`,l=e.desc||``,u=e.requires&&e.requires[0]!==`*`?`← ${e.requires[0]}`:``,d=e.name.replace(/'/g,`\\'`);r+=`<div onclick="window._showOpDetail('${d}','${t}')" style="cursor:pointer;background:var(--bg3);border-radius:6px;padding:8px;margin-bottom:4px;border:1px solid var(--border)">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${i}"></span>
        <span style="font-weight:600;font-size:11px">${s}</span>
        <span style="font-size:9px;color:${i};margin-left:8px;font-weight:600">${a}</span>
        <span style="font-size:9px;color:var(--text2);margin-left:auto">${e.name}</span>
      </div>
      <div style="font-size:9px;color:var(--text2)">${l} ${u?` | `+u:``}</div>
    </div>`}),n.innerHTML=r}window._showOpDetail=function(e,t){let n=document.getElementById(`opDetail_${t}`),i=document.getElementById(`opDetailBody_${t}`);if(!n||!i)return;let a=r.find(t=>t.name===e);if(!a)return;let o={tested:`✅已通过`,partial:`🟡部分`,failed:`🔴失败`,untested:`⚪未测`}[c(e)]||`⚪未测`,s=a.label||e,l=a.desc||`暂无描述`,u=a.requires&&a.requires[0]!==`*`?`前置: ${a.requires.join(`, `)}`:`无前置依赖`,d=a.category||`其他`,f=a.params?Object.keys(a.params).map(e=>`${e}: ${a.params[e]}`).join(`, `):`无参数`,p=a.returns?a.returns.slice(0,200):`无返回值`;n.style.display=`block`,i.innerHTML=`
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
      <span style="font-weight:600;font-size:12px">${s}</span>
      <span style="font-size:10px;color:var(--text2);cursor:pointer" onclick="document.getElementById('opDetail_${t}').style.display='none'">✕ 关闭</span>
    </div>
    <div style="margin-bottom:4px"><span style="color:var(--text2)">ID:</span> ${e} · <span style="color:var(--text2)">分类:</span> ${d} · ${o}</div>
    <div style="margin-bottom:4px;color:var(--text2)">${l}</div>
    <div style="margin-bottom:4px;color:var(--text2)">${u}</div>
    <div style="margin-bottom:6px;color:var(--text2);font-size:9px"><span style="color:var(--text2)">参数:</span> ${f}</div>
    <div style="margin-bottom:6px;color:var(--text2);font-size:9px"><span style="color:var(--text2)">返回:</span> ${p}</div>
    <div style="display:flex;gap:4px">
      <button onclick="console.log('TODO: 测试 '+opName)" style="flex:1;background:#22c55e;color:#fff;border:none;padding:4px;border-radius:4px;cursor:pointer;font-size:10px">🧪 测试此操作</button>
    </div>`};var u={},d={};try{d=JSON.parse(localStorage.getItem(`rec_names`)||`{}`)}catch{}function f(){try{localStorage.setItem(`rec_names`,JSON.stringify(d))}catch{}}async function p(e){let t=document.getElementById(`recSelect_${e}`);if(t)try{t.innerHTML=`<option value="">— 选择录制包 —</option>`+((await(await fetch(`/api/matrix/record/list`)).json()).recordings||[]).map(e=>`<option value="${e.name}">🎬 ${e.account} ${e.platform} (${e.steps}步)</option>`).join(``)}catch{t.innerHTML=`<option value="">加载失败</option>`}}async function m(e,t){let n=document.getElementById(`recSteps_${t}`);if(n)try{let r=await(await fetch(`/api/matrix/record/detail/`+encodeURIComponent(e))).json(),i=r.steps||[],a=(r.analysis||{}).actions||[],o={};a.forEach(e=>{let t=e.step_after||e.step_before;o[t]||(o[t]=[]),o[t].push(e)}),u={steps:i,actMap:o,uid:t,name:e};let s=`<div style="font-weight:600;margin-bottom:6px;font-size:11px;display:flex;justify-content:space-between">
      <span>${e}</span>
      <span style="font-size:10px;color:var(--text2)">${i.length}步</span>
    </div>`;s+=`<div style="max-height:220px;overflow-y:auto;margin-bottom:6px">`,i.forEach((e,t)=>{let n=o[e.step]||[],r=n[0]||{};(r.action_desc||`浏览`).slice(0,30);let a=r.suggested_op||r.action_type||`?`,c=r.page_mode||`?`,l=n.length&&(o[i[t+1]?i[t+1].step:-1]||[])[0]?.page_mode||`?`,u=window._recActiveStep;s+=`<div onclick="window._recShowDetail(${t})" data-sidx="${t}"
        style="cursor:pointer;background:${u===t?`var(--primary)`:`var(--bg3)`};border-radius:4px;padding:5px 6px;margin-bottom:3px;border:1px solid var(--border);display:flex;gap:4px;align-items:center">
        <span style="font-size:9px;font-weight:600;color:${u===t?`#fff`:`var(--text)`}">#${t+1}</span>
        <span style="font-size:8px;color:${u===t?`rgba(255,255,255,.7)`:`var(--text2)`}">${c}→${l}</span>
        <span style="font-size:8px;color:${u===t?`rgba(255,255,255,.7)`:`var(--text2)`};margin-left:auto">${a}</span>
      </div>`}),s+=`</div>`,s+=`<div id="recStepDetail_${t}" style="font-size:10px"></div>`;let c=d[e]?Object.keys(d[e]).length:0;s+=`<div style="margin-top:6px;display:flex;gap:4px;align-items:center">
      <button onclick="window._recSaveAll('${t}')" style="flex:1;background:var(--primary);color:#fff;border:none;padding:4px;border-radius:4px;cursor:pointer;font-size:10px">💾 保存全部命名</button>
      <span id="recSaveStatus_${t}" style="font-size:9px;color:var(--text2)">${c>0?`已保存 `+c+` 步`:``}</span>
    </div>`,n.innerHTML=s,window._recShowDetail=function(e){h(e,t)},window._recSetName=function(e,t){let n=document.getElementById(`recNameInput_${e}_${t}`)?.value?.trim();n&&(d[u.name]||(d[u.name]={}),d[u.name][e]=n,document.getElementById(`recNameLabel_${e}_${t}`).textContent=n)},window._recSaveAll=function(e){u.steps.forEach((t,n)=>{let r=document.getElementById(`recNameInput_${n}_${e}`);r&&r.value.trim()&&(d[u.name]||(d[u.name]={}),d[u.name][n]=r.value.trim())}),f();let t=d[u.name]?Object.keys(d[u.name]).length:0;document.getElementById(`recSaveStatus_${e}`).textContent=`✅ 已保存 `+t+`/`+u.steps.length+` 步命名`},h(0,t)}catch(e){n.innerHTML=`<div style="color:var(--red);padding:8px">❌ ${e.message}</div>`}}function h(e,t){let n=document.getElementById(`recStepDetail_${t}`);if(!n||!u.steps)return;if(window._recActiveStep!==void 0&&window._recActiveStep!==e){let e=document.getElementById(`recNameInput_${window._recActiveStep}_${t}`);e&&e.value.trim()&&(d[u.name]||(d[u.name]={}),d[u.name][window._recActiveStep]=e.value.trim())}window._recActiveStep=e;let r=u.steps[e];if(!r)return;document.querySelectorAll(`#recSteps_${t} [data-sidx]`).forEach(t=>{let n=parseInt(t.dataset.sidx)===e;t.style.background=n?`var(--primary)`:`var(--bg3)`,t.style.color=n?`#fff`:``,t.querySelectorAll(`span`).forEach(e=>{n&&(e.style.color=e.dataset.origColor||(e.style.color===`rgb(255,255,255)`?``:`rgba(255,255,255,.7)`))})});let i=(u.actMap[r.step]||[])[0]||{},a=i.action_desc||`浏览`,o=i.suggested_op||i.action_type||`?`,s=d[u.name]?.[e]||o,c=r.screenshot_url||``,l=r.page?r.page.url:``;r.page&&(r.page.text_snippet||``).slice(0,100);let f=u.steps[e+1],p=i.features||[];n.innerHTML=`
    <div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--primary)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <span style="font-weight:600;font-size:11px">步骤 #${e+1}</span>
        <span style="font-size:9px;color:var(--text2)">操作: ${a}</span>
      </div>

      <!-- before / after 截图 -->
      <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:6px;margin-bottom:6px">
        <div style="background:rgba(37,99,235,.08);border-radius:4px;padding:4px;border:1px solid rgba(37,99,235,.15)">
          <div style="font-size:8px;color:#3b82f6;font-weight:600;margin-bottom:2px">⬅ 前状态</div>
          <div style="font-size:8px;word-break:break-all;color:var(--text2)">${l?l.slice(0,50):`(无URL)`}</div>
          ${c?`<div style="margin-top:2px"><img src="`+c+`" style="max-width:100%;max-height:80px;border-radius:3px;background:var(--bg2)" onerror="this.style.display='none'"></div>`:``}
        </div>
        <div style="display:flex;align-items:center;font-size:14px;color:var(--text2)">→</div>
        <div style="background:rgba(5,150,105,.08);border-radius:4px;padding:4px;border:1px solid rgba(5,150,105,.15)">
          <div style="font-size:8px;color:#22c55e;font-weight:600;margin-bottom:2px">➡ 后状态</div>
          <div style="font-size:8px;word-break:break-all;color:var(--text2)">${f?(f.page?.url||`同页`).slice(0,50):`(结束)`}</div>
          ${f&&f.screenshot_url?`<div style="margin-top:2px"><img src="`+f.screenshot_url+`" style="max-width:100%;max-height:80px;border-radius:3px;background:var(--bg2)" onerror="this.style.display='none'"></div>`:``}
        </div>
      </div>

      <!-- 原子操作命名 -->
      <div style="display:flex;gap:4px;align-items:center">
        <span style="font-size:9px;color:var(--text2)">🏷️ 命名:</span>
        <input id="recNameInput_${e}_${t}" value="${s}" style="flex:1;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:3px;font-size:10px" onchange="window._recSetName(${e},'${t}')">
        <span id="recNameLabel_${e}_${t}" style="display:none">${s}</span>
      </div>

      ${p.length?`<div style="margin-top:4px;font-size:8px;color:var(--text2)">`+p.map(e=>`<code style="background:var(--bg2);padding:1px 3px;border-radius:2px;margin:1px;font-size:8px">`+e.code+`</code>`).join(``)+`</div>`:``}
      
      <!-- 步骤导航 -->
      <div style="display:flex;gap:4px;margin-top:6px">
        <button onclick="showStepDetail(${Math.max(0,e-1)},'${t}')" ${e===0?`disabled`:``} style="flex:1;background:${e===0?`var(--bg3)`:`var(--primary)`};color:${e===0?`var(--text2)`:`#fff`};border:none;padding:3px;border-radius:3px;cursor:${e===0?`default`:`pointer`};font-size:9px">◀ 上一步</button>
        <button onclick="showStepDetail(${Math.min(u.steps.length-1,e+1)},'${t}')" ${e>=u.steps.length-1?`disabled`:``} style="flex:1;background:${e>=u.steps.length-1?`var(--bg3)`:`var(--primary)`};color:${e>=u.steps.length-1?`var(--text2)`:`#fff`};border:none;padding:3px;border-radius:3px;cursor:${e>=u.steps.length-1?`default`:`pointer`};font-size:9px">下一步 ▶</button>
      </div>
    </div>`}export{e as loadView};
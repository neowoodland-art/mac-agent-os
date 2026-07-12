import{t as e}from"./index-CEGJ4Kyq.js";import{t}from"./account-selector-D87mja1n.js";var n=null,r={},i=[],a=[],o=``,s={sharer:`分享型`,questioner:`提问型`,sympathizer:`共情型`,skeptic:`质疑型`,sufferer:`患者型`,filler:`灌水型`,expert_ref:`推荐型`};async function c(s){o=s.id||`cw`,i=[],a=[],s.innerHTML=`
    <div style="padding:16px;max-width:960px">

      <!-- ═══ 标题 ═══ -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">💬 评论工作台</h2>
        <span style="font-size:10px;color:var(--text2)">批量视频 × 批量账号 × 角色化评论</span>
      </div>

      <!-- ═══ 自动更新总计 ═══ -->
      <span id="cwPctStatus_${o}" style="display:none"></span>

      <!-- ═══ 第一步：导入视频 ═══ -->
      <div class="cw-section" style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-bottom:10px">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">📥 第一步：导入视频</div>
        <div style="display:flex;gap:6px;margin-bottom:6px">
          <textarea id="cwUrls_${o}" placeholder="视频链接（每行一个，支持多个）" rows="3"
                    style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
          <div style="display:flex;flex-direction:column;gap:4px;width:180px">
            <button onclick="window._cwParseUrls('${o}')"
                    style="background:var(--primary);color:#fff;border:none;padding:5px 8px;border-radius:4px;cursor:pointer;font-size:11px">📋 解析链接</button>
            <button onclick="window._cwShowApiImport('${o}')"
                    style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;cursor:pointer;font-size:11px">📡 导入热帖</button>
          </div>
        </div>
        <!-- 导入热帖面板（折叠） -->
        <div id="cwImportPanel_${o}" style="display:none;background:var(--bg3);border-radius:6px;padding:8px;margin-bottom:6px">
          <div style="display:flex;gap:4px;align-items:center;margin-bottom:4px">
            <input id="cwApiUrl_${o}" type="text"
                   placeholder="API 地址" value="https://wx.tyhtak.com/api/biz/activity/api/v1/activity/recordswx1"
                   style="flex:1;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:3px;font-size:10px">
            <input id="cwApiPages_${o}" type="number" value="3" min="1" max="10"
                   style="width:40px;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:3px;font-size:10px;text-align:center">
            <span style="font-size:9px;color:var(--text2)">页</span>
            <button onclick="window._cwApiImport('${o}')"
                    style="background:#2563eb;color:#fff;border:none;padding:4px 10px;border-radius:3px;cursor:pointer;font-size:10px">导入</button>
            <span id="cwApiImportStatus_${o}" style="font-size:9px;color:var(--text2)"></span>
          </div>
        </div>
        <!-- 视频列表 -->
        <div id="cwVideoList_${o}" style="display:none;background:var(--bg3);border-radius:6px;padding:6px;max-height:240px;overflow-y:auto"></div>
      </div>

      <!-- ═══ 第二步：选择账号 ═══ -->
      <div class="cw-section" style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-bottom:10px">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">👥 第二步：选择账号</div>
        <div id="cwAcctList_${o}"><div class="loading">⏳ 加载账号列表...</div></div>
      </div>

      <!-- ═══ 第三步：角色比例 ═══ -->
      <div id="cwRoleSection_${o}" style="display:none;background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-bottom:10px">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">🎭 第三步：角色比例（所有视频通用）</div>
        <div id="cwRoleSliders_${o}" style="display:grid;gap:6px"></div>
        <div style="display:flex;gap:10px;align-items:center;margin-top:8px;flex-wrap:wrap">
          <label style="font-size:11px;display:flex;align-items:center;gap:4px">
            每条视频生成
            <input id="cwPerVideo_${o}" type="number" value="15" min="3" max="60"
                   style="width:50px;padding:3px 6px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:11px;text-align:center">
            条评论
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px">
            长评占比
            <input id="cwLongRatio_${o}" type="range" min="0" max="100" value="20"
                   oninput="document.getElementById('cwLongVal_${o}').textContent=this.value+'%'"
                   style="width:80px">
            <span id="cwLongVal_${o}" style="font-size:11px;color:var(--text2);min-width:35px">20%</span>
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px">
            <input type="checkbox" id="cwAiEnhance_${o}" checked>
            🧠 AI 改写
          </label>
          <button id="cwGenerateBtn_${o}" onclick="window._cwGenerate('${o}')"
                  style="background:var(--primary);color:#fff;border:none;padding:6px 16px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600">🚀 生成评论</button>
        </div>
      </div>

      <!-- ═══ 第四步：预览 ═══ -->
      <div id="cwPreview_${o}" style="display:none;background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-bottom:10px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="font-weight:600;font-size:13px">📝 第四步：预览编排</span>
          <div style="display:flex;gap:6px">
            <span id="cwPreviewCount_${o}" style="font-size:11px;color:var(--text2)"></span>
            <button onclick="window._cwRegenerate('${o}')"
                    style="background:var(--bg3);border:1px solid var(--border);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">🔄 重新生成</button>
            <button onclick="window._cwDispatch('${o}')"
                    style="background:var(--primary);color:#fff;border:none;padding:3px 12px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600">✅ 分发</button>
          </div>
        </div>
        <div id="cwCommentList_${o}" style="display:grid;gap:4px;max-height:500px;overflow-y:auto"></div>
      </div>

      <!-- ═══ 第五步：结果 ═══ -->
      <div id="cwResult_${o}" style="display:none;background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-top:10px">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">📊 分发结果</div>
        <div id="cwResultContent_${o}" style="font-size:11px;line-height:1.6"></div>
      </div>

    </div>
  `,r={},m.forEach(e=>{r[e.id]=e.pct}),l();try{let r=await e(`/matrix/accounts`),i=Array.isArray(r)?r:r.accounts||[],a=document.getElementById(`cwAcctList_${o}`);a&&(n=t(a,{accounts:i,checkAll:!0,height:`160px`,showBlueprint:!1,showCollectTime:!1}))}catch(e){let t=document.getElementById(`cwAcctList_${o}`);t&&(t.innerHTML=`<div class="error">❌ ${e.message}</div>`)}}function l(){let e=document.getElementById(`cwRoleSliders_${o}`);e&&(e.innerHTML=[{key:`filler`,label:`灌水/搞怪`,items:m.filter(e=>e.group===`filler`||e.group===`funny`)},{key:`emotion`,label:`情感类`,items:m.filter(e=>e.group===`emotion`)},{key:`guide`,label:`引导类（穿插埋入）`,items:m.filter(e=>e.group===`guide`)}].map(e=>`
    <div style="font-size:9px;color:var(--text2);margin:5px 0 2px 0;font-weight:500;border-top:1px solid var(--border);padding-top:4px">${e.label}</div>
    ${e.items.map(e=>{let t=(r[e.id]||0)*100;return`
      <div style="display:flex;align-items:center;gap:6px;font-size:10px">
        <span style="min-width:80px;font-weight:400">${e.label}</span>
        <input type="range" min="0" max="50" value="${Math.round(t)}"
               data-role="${e.id}"
               oninput="window._cwRolePct('${o}','${e.id}',this.value)"
               style="flex:1;height:5px;accent-color:${u(e.id)}">
        <span id="cwPct_${e.id}_${o}" style="min-width:30px;text-align:right;color:var(--text2)">${Math.round(t)}%</span>
      </div>`}).join(``)}
  `).join(``),document.getElementById(`cwRoleSection_${o}`).style.display=`block`)}function u(e){return{filler:`#8b8fa3`,funny:`#a78bfa`,sympathizer:`#f59e0b`,sharer:`#22c55e`,angry:`#ef4444`,oppose:`#dc2626`,guide_analyze:`#3b82f6`,guide_share:`#06b6d4`,guide_agree:`#10b981`,guide_benefit:`#f97316`,guide_compare:`#8b5cf6`}[e]||`#3b82f6`}window._cwRolePct=(e,t,n)=>{let i=parseInt(n)/100;r[t],r[t]=i;let a=Object.entries(r).filter(([e])=>e!==t).reduce((e,[,t])=>e+t,0);if(a>.001){let e=(1-i)/a;Object.keys(r).forEach(n=>{n!==t&&(r[n]=Math.round(r[n]*e*100)/100)})}m.forEach(t=>{let n=document.getElementById(`cwPct_${t.id}_${e}`);n&&(n.textContent=`${Math.round(r[t.id]*100)}%`);let i=document.querySelector(`[data-role="${t.id}"]`);i&&(i.value=Math.round(r[t.id]*100))});let o=Object.values(r).reduce((e,t)=>e+t,0),s=document.getElementById(`cwPctStatus_${e}`);s&&(s.textContent=`总计 ${(o*100).toFixed(0)}% ${Math.abs(o-1)<.01?`✅`:`⚠️`}`)},window._cwParseUrls=async e=>{let t=document.getElementById(`cwUrls_${e}`)?.value?.trim();if(!t){alert(`请先粘贴视频链接`);return}let n=t.split(`
`).map(e=>e.trim()).filter(Boolean);if(!n.length){alert(`没有有效的链接`);return}let r=[];if(n.forEach(e=>{i.find(t=>t.url===e)||(i.push({url:e,title:``,tags:``,checked:!0,industry:``,content_type:``,direction:`auto`,guide_points:``}),r.push(e))}),d(e),r.length)try{let t=await(await fetch(`/api/ops/fetch-titles`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({urls:r})})).json();t.status===`ok`&&t.titles&&(t.titles.forEach(e=>{let t=i.find(t=>t.url===e.url);t&&e.title&&(t.title=e.title)}),d(e))}catch(e){console.warn(`标题提取失败:`,e)}},window._cwShowApiImport=e=>{let t=document.getElementById(`cwImportPanel_${e}`);t.style.display=t.style.display===`none`?`block`:`none`},window._cwApiImport=async t=>{let n=document.getElementById(`cwApiUrl_${t}`)?.value?.trim(),r=parseInt(document.getElementById(`cwApiPages_${t}`)?.value||`3`);if(!n){alert(`请输入 API 地址`);return}let a=document.getElementById(`cwApiImportStatus_${t}`);a.textContent=`⏳ 导入中...`;let o=0;for(let t=1;t<=r;t++)try{let r=await e(`/ops/import-topics`,{method:`POST`,body:JSON.stringify({api_url:n,page:t,page_size:10})});r.status===`ok`&&r.items&&r.items.length&&r.items.forEach(e=>{let t=e.url||e.link||e.title;i.find(e=>e.url===t)||(i.push({url:t,title:e.title||e.content||``,tags:Array.isArray(e.tags)?e.tags.join(`,`):e.tags||``,checked:!0,industry:``,content_type:``,direction:`auto`,guide_points:``}),o++)})}catch(e){console.warn(`导入第${t}页失败:`,e)}a.textContent=o>0?`✅ 导入 ${o} 条`:`⚠️ 未获取到视频`,o>0&&d(t)};function d(e){let t=document.getElementById(`cwVideoList_${e}`);if(!t)return;if(!i.length){t.style.display=`none`;return}t.style.display=`block`;let n=i.filter(e=>e.checked).length;t.innerHTML=`
    <div style="display:flex;align-items:center;gap:3px;margin-bottom:2px;font-size:9px;color:var(--text2);flex-wrap:wrap">
      <label style="display:flex;align-items:center;gap:2px;cursor:pointer">
        <input type="checkbox" onchange="window._cwToggleAllVideo('${e}',this.checked)" ${i.every(e=>e.checked)?`checked`:``} style="margin:0">
        全选
      </label>
      <span>${i.length}个</span>
      <span style="color:var(--primary)">已选${n}</span>
      <span style="font-size:8px;color:var(--text2);margin:0 2px">|</span>
      <span style="font-size:8px">批量:</span>
      <select onchange="window._cwBatchSetVideoAttr('${e}','industry',this.value)" style="width:52px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:1px;border-radius:2px;font-size:8px">
        ${f.map(e=>`<option value="${e.id}">${e.label.replace(/^[^\s]+\s/,``)}</option>`).join(``)}
      </select>
      <select onchange="window._cwBatchSetVideoAttr('${e}','content_type',this.value)" style="width:46px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:1px;border-radius:2px;font-size:8px">
        ${p.map(e=>`<option value="${e.id}">${e.label.replace(/^[^\s]+\s/,``)}</option>`).join(``)}
      </select>
      <input type="text" placeholder="统一标签" maxlength="14" onchange="window._cwBatchSetVideoAttr('${e}','tags',this.value)"
             style="width:46px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:1px 2px;border-radius:2px;font-size:8px">
      <input type="text" placeholder="统一引导" maxlength="14" onchange="window._cwBatchSetVideoAttr('${e}','guide_points',this.value)"
             style="width:46px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:1px 2px;border-radius:2px;font-size:8px">
      <button onclick="window._cwClearVideos('${e}')" style="margin-left:auto;background:none;border:none;cursor:pointer;font-size:9px;color:var(--red)">清空</button>
    </div>
    ${i.map((t,n)=>{let r=f.map(e=>`<option value="${e.id}" ${(t.industry||``)===e.id?`selected`:``}>${e.label.replace(/^[^\s]+\s/,``)}</option>`).join(``),i=p.map(e=>`<option value="${e.id}" ${(t.content_type||``)===e.id?`selected`:``}>${e.label.replace(/^[^\s]+\s/,``)}</option>`).join(``);return`
      <div style="display:flex;align-items:center;gap:2px;padding:2px 2px;font-size:9px;background:var(--bg2);border-radius:3px;margin-bottom:1px">
        <input type="checkbox" ${t.checked?`checked`:``} onchange="window._cwToggleVideo('${e}',${n},this.checked)" style="flex-shrink:0">
        <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:30px;max-width:100px;font-size:9px" title="${t.title||t.url}">${t.title?t.title.slice(0,14):h(t.url,18)}</span>
        <select onchange="window._cwSetVideoIndustry('${e}',${n},this.value)" style="width:52px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:1px 1px;border-radius:2px;font-size:8px">${r}</select>
        <select onchange="window._cwSetVideoContentType('${e}',${n},this.value)" style="width:46px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:1px 1px;border-radius:2px;font-size:8px">${i}</select>
        <input type="text" value="${t.tags||``}" maxlength="12" placeholder="标签"
               onchange="window._cwSetVideoTag('${e}',${n},this.value)"
               style="width:48px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:1px 2px;border-radius:2px;font-size:8px">
        <input type="text" value="${t.guide_points||``}" maxlength="16" placeholder="引导"
               onchange="window._cwSetVideoGuidePoints('${e}',${n},this.value)"
               style="width:48px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:1px 2px;border-radius:2px;font-size:8px">
        <button onclick="window._cwRemoveVideo('${e}',${n})"
                style="background:none;border:none;cursor:pointer;font-size:9px;opacity:.3;padding:0 1px;flex-shrink:0">✕</button>
      </div>`}).join(``)}
  `}window._cwToggleVideo=(e,t,n)=>{i[t]&&(i[t].checked=n)},window._cwToggleAllVideo=(e,t)=>{i.forEach(e=>e.checked=t),d(e)},window._cwClearVideos=e=>{i=[],d(e)},window._cwSetVideoTag=(e,t,n)=>{i[t]&&(i[t].tags=n)},window._cwRemoveVideo=(e,t)=>{i.splice(t,1),d(e)},window._cwSetVideoIndustry=(e,t,n)=>{i[t]&&(i[t].industry=n)},window._cwSetVideoContentType=(e,t,n)=>{i[t]&&(i[t].content_type=n)},window._cwSetVideoGuidePoints=(e,t,n)=>{i[t]&&(i[t].guide_points=n)},window._cwBatchSetVideoAttr=(e,t,n)=>{i.forEach(e=>{e.checked&&(e[t]=n)}),d(e)};var f=[{id:``,label:`自动识别`},{id:`medical`,label:`🏥 医疗健康`},{id:`suzhou`,label:`📍 苏州本地`},{id:`entertainment`,label:`🎮 休闲娱乐`},{id:`news`,label:`📰 热点实讯`},{id:`food`,label:`🍜 吃喝玩乐`},{id:`patriotic`,label:`🇨🇳 家国情怀`},{id:`misc`,label:`📦 其他灌水`}],p=[{id:``,label:`自动`},{id:`real_person`,label:`🎭 真人出镜`},{id:`ad`,label:`📢 纯广告`},{id:`knowledge`,label:`📚 知识分享`},{id:`experience`,label:`💡 经验分享`},{id:`explore`,label:`🔍 探店`},{id:`review`,label:`📊 测评`},{id:`other`,label:`其他`}],m=[{id:`filler`,label:`灌水/路过`,group:`filler`,pct:.3,desc:`路过灌水`},{id:`funny`,label:`😜 搞怪`,group:`funny`,pct:.08,desc:`搞怪吐槽`},{id:`sympathizer`,label:`感同身受`,group:`emotion`,pct:.12,desc:`共情感同身受`},{id:`sharer`,label:`喜欢赞扬`,group:`emotion`,pct:.12,desc:`赞美赞扬`},{id:`angry`,label:`愤世嫉俗`,group:`emotion`,pct:.08,desc:`愤怒吐槽现实`},{id:`oppose`,label:`坚决抵制`,group:`emotion`,pct:.05,desc:`反对抵制`},{id:`guide_analyze`,label:`客观分析引导`,group:`guide`,pct:.08,desc:`客观分析夸优点引导`},{id:`guide_share`,label:`经验分享引导`,group:`guide`,pct:.06,desc:`相同经历经验分享引导`},{id:`guide_agree`,label:`赞同博主引导`,group:`guide`,pct:.04,desc:`赞同博主引导`},{id:`guide_benefit`,label:`薅羊毛推荐引导`,group:`guide`,pct:.04,desc:`利益分享薅羊毛引导`},{id:`guide_compare`,label:`对比反证引导`,group:`guide`,pct:.03,desc:`对比其他差评反证引导`}];function h(e,t){if(!e)return``;let n=e.replace(/^https?:\/\//,``).replace(/^www\./,``);return n.length>t?n.slice(0,t)+`…`:n}window._cwEditVideo=(e,t)=>{let n=i[t];if(!n)return;let r=document.createElement(`div`);r.style.cssText=`position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:99999;display:flex;align-items:center;justify-content:center`,r.onclick=e=>{e.target===r&&r.remove()};let a=f.map(e=>`<option value="${e.id}" ${n.industry===e.id?`selected`:``}>${e.label}</option>`).join(``),o=DIRECTIONS.map(e=>`<option value="${e.id}" ${(n.direction||`auto`)===e.id?`selected`:``}>${e.label}</option>`).join(``);r.innerHTML=`
    <div style="background:var(--bg2);border-radius:12px;padding:20px;max-width:450px;width:90%">
      <div style="font-size:14px;font-weight:600;margin-bottom:10px">✏️ 编辑视频</div>
      <div style="font-size:11px;color:var(--text2);margin-bottom:10px;word-break:break-all">${n.title||h(n.url,50)}</div>

      <div style="margin-bottom:10px">
        <div style="font-size:11px;font-weight:500;margin-bottom:4px">行业</div>
        <select id="cwEditInd_${e}" style="width:100%;padding:6px 8px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:12px">
          ${a}
        </select>
      </div>

      <div style="margin-bottom:10px">
        <div style="font-size:11px;font-weight:500;margin-bottom:4px">标签（逗号分隔）</div>
        <input id="cwEditTags_${e}" type="text" value="${n.tags||``}" placeholder="如: 运动,健身,跑步"
               style="width:100%;padding:6px 8px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:12px">
      </div>

      <div style="margin-bottom:14px">
        <div style="font-size:11px;font-weight:500;margin-bottom:4px">情感方向（角色滑条仍生效，此为主方向）</div>
        <select id="cwEditDir_${e}" style="width:100%;padding:6px 8px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:12px">
          ${o}
        </select>
      </div>

      <div style="display:flex;gap:6px;justify-content:flex-end">
        <button onclick="this.closest('[style*=\"position:fixed\"]').remove()"
                style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">取消</button>
        <button onclick="window._cwSaveVideoEdit('${e}',${t})"
                style="background:var(--primary);color:#fff;border:none;border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">✅ 确认</button>
      </div>
    </div>`,document.body.appendChild(r)},window._cwSaveVideoEdit=(e,t)=>{let n=i[t];n&&(n.industry=document.getElementById(`cwEditInd_${e}`)?.value||``,n.tags=document.getElementById(`cwEditTags_${e}`)?.value?.trim()||``,n.direction=document.getElementById(`cwEditDir_${e}`)?.value||`auto`,document.querySelector(`[style*="position:fixed"]`)?.remove(),d(e))},window._cwGenerate=async e=>{let t=i.filter(e=>e.checked);if(!t.length){alert(`请至少选择一个视频`);return}let o=n?n.getSelected():[];if(!o||!o.length){alert(`请至少选择一个账号`);return}let c=parseInt(document.getElementById(`cwPerVideo_${e}`)?.value||`15`),l=parseInt(document.getElementById(`cwLongRatio_${e}`)?.value||`20`)/100,u=document.getElementById(`cwAiEnhance_${e}`)?.checked||!1;if(c*t.length,c>o.length){let e=c-o.length;if(!confirm(`每个视频生成 ${c} 条评论，但只有 ${o.length} 个账号。每视频多 ${e} 条将不分配账号。继续？`))return}let d=document.getElementById(`cwGenerateBtn_${e}`);d.textContent=`⏳ 生成中...`,d.disabled=!0,a=[];for(let e=0;e<t.length;e++){let n=t[e],i=n.title||n.url||``;if(!i){console.warn(`视频 #${e+1} 无标题无URL，跳过`);continue}let d=(n.tags||``).split(/[,，]/).map(e=>e.trim()).filter(Boolean),f=n.guide_points||``,p=n.content_type||``;try{let t=(await(await fetch(`/api/comment-workbench/generate`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({video_title:i,video_tags:d,video_industry:n.industry||``,guide_points:f,content_type:p,role_distribution:r,total:c,ai_enhance:u,long_ratio:l})})).json()).comments||[],m=g(i);m&&(t=t.map(e=>({...e,text:e.text?e.text.replace(/\{keyword\}/g,m):e.text}))),t.forEach((t,n)=>{let r=n%o.length;a.push({video_idx:e,account_idx:r,account_id:o[r]?.id||o[r]||`account_${r}`,text:t.text,role:t.role,role_label:t.role_label||s[t.role]||t.role,is_long:!!t.is_long})})}catch(t){console.error(`视频 #${e+1} 生成失败:`,t)}}d.textContent=`🚀 生成评论`,d.disabled=!1,_(e)};function g(e){if(!e)return``;let t=e.match(/(?:关于|分享|推荐|说说|聊聊|如何|怎么|什么|为什么)(.{2,8})/);return t?t[1]:e.replace(/[的在了是就都和与及、，。！？]/g,` `).split(/\s+/).filter(Boolean)[0]||e.slice(0,6)}function _(e){let t=document.getElementById(`cwPreview_${e}`),n=document.getElementById(`cwCommentList_${e}`),r=document.getElementById(`cwPreviewCount_${e}`);if(!t||!n)return;if(!a.length){t.style.display=`none`;return}t.style.display=`block`,r.textContent=`共 ${a.length} 条`;let o=i.filter(e=>e.checked);n.innerHTML=`
    <div style="display:flex;align-items:center;gap:4px;margin-bottom:4px;font-size:9px;color:var(--text2)">
      <span style="min-width:16px"><input type="checkbox" id="cwSelAll_${e}" onchange="document.querySelectorAll('.cw-comment-cb').forEach(cb=>cb.checked=this.checked)"></span>
      <span style="flex:1;font-size:9px">${a.length} 条 | ${o.length} 视频</span>
      <button onclick="window._cwSaveSelectedComments('${e}')" style="background:var(--bg3);border:1px solid var(--border);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:9px">💾 入库</button>
    </div>
    ${a.map((t,n)=>{let r=o[t.video_idx],i=r?r.title?r.title.slice(0,16):h(r.url,18):`视频#${t.video_idx+1}`,a=u(t.role);return`
      <div style="display:flex;align-items:center;gap:3px;padding:3px 6px;background:var(--bg3);border-radius:4px;font-size:9px;border-left:3px solid ${a};margin-bottom:2px">
        <input type="checkbox" class="cw-comment-cb" data-idx="${n}" style="flex-shrink:0">
        <span style="font-size:8px;color:var(--text2);min-width:28px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${r?r.title||r.url:``}">📹${i}</span>
        <span style="font-size:8px;padding:1px 3px;border-radius:2px;background:${a}20;color:${a};min-width:30px;text-align:center;flex-shrink:0">${t.role_label}${t.is_long?`📖`:``}</span>
        <span style="font-size:8px;color:var(--text2);min-width:40px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex-shrink:0">${t.account_id}</span>
        <span style="flex:1;color:var(--text);min-width:0">${v(t.text)}</span>
        <button onclick="window._cwEditComment(${n},'${e}')" style="background:none;border:none;cursor:pointer;font-size:10px;opacity:.4;flex-shrink:0">✏️</button>
        <button onclick="window._cwDeleteComment(${n},'${e}')" style="background:none;border:none;cursor:pointer;font-size:10px;opacity:.3;flex-shrink:0">✕</button>
      </div>`}).join(``)}`}window._cwEditComment=(e,t)=>{let n=a[e];if(!n)return;let r=document.createElement(`div`);r.style.cssText=`position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:99999;display:flex;align-items:center;justify-content:center`,r.onclick=e=>{e.target===r&&r.remove()},r.innerHTML=`
    <div style="background:var(--bg2);border-radius:12px;padding:20px;max-width:500px;width:90%">
      <div style="font-size:14px;font-weight:600;margin-bottom:4px">✏️ 编辑评论 #${e+1}</div>
      <div style="font-size:10px;color:var(--text2);margin-bottom:6px">
        角色：${n.role_label} | 账号：${n.account_id} | 视频 #${n.video_idx+1}
      </div>
      <textarea id="cwEditText_${t}" style="width:100%;min-height:80px;padding:6px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:12px">${v(n.text)}</textarea>
      <div style="display:flex;gap:6px;justify-content:flex-end;margin-top:8px">
        <button onclick="this.closest('[style*=\"position:fixed\"]').remove()" style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">取消</button>
        <button onclick="window._cwSaveEdit(${e},'${t}')" style="background:var(--primary);color:#fff;border:none;border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">✅ 保存</button>
      </div>
    </div>`,document.body.appendChild(r)},window._cwSaveEdit=(e,t)=>{let n=document.getElementById(`cwEditText_${t}`)?.value?.trim();n&&(a[e]&&(a[e].text=n),document.querySelector(`[style*="position:fixed"]`)?.remove(),_(t))},window._cwDeleteComment=(e,t)=>{a.splice(e,1),_(t)},window._cwSaveSelectedComments=async e=>{let t=document.querySelectorAll(`.cw-comment-cb:checked`);if(!t.length){alert(`请先勾选要入库的评论`);return}let n=[];t.forEach(e=>{let t=parseInt(e.dataset.idx),r=a[t];r&&n.push({text:r.text,role:r.role,category:`入库评论`})});try{let e=await(await fetch(`/api/comment-workbench/save-comments`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({comments:n,platform:`douyin`})})).json();e.status===`ok`?alert(`✅ 入库 ${e.saved} 条评论`):alert(`❌ `+(e.message||`入库失败`))}catch(e){alert(`❌ `+e.message)}},window._cwRegenerate=e=>{a=[],window._cwGenerate(e)},window._cwDispatch=async e=>{if(!a.length){alert(`没有可分发的内容`);return}if(!confirm(`确认分发 ${a.length} 条评论？`))return;let t=document.getElementById(`cwResult_${e}`),r=document.getElementById(`cwResultContent_${e}`);t.style.display=`block`,r.innerHTML=`⏳ 分发中...`;let o=i.filter(e=>e.checked);n&&n.getSelected();let s=0,c=0,l=[];for(let e=0;e<a.length;e++){let t=a[e],n=o[t.video_idx];r.innerHTML=`⏳ 分发中 ${e+1}/${a.length}...`;try{let r=await(await fetch(`/api/ops/run`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({type:`smart_comment`,accounts:[t.account_id],params:{urls:[n?n.url:``],direction:`praise`,comments:n?{[n.url]:t.text}:{},titles:n&&n.title?{[n.url]:n.title}:{},skip_analysis:!0}})})).json();r.status===`accepted`||r.status===`ok`?(s++,l.push(`#${e+1} ${t.account_id} [${t.role_label}] ✅`)):(c++,l.push(`#${e+1} ${t.account_id} ❌ ${r.message||r.error||``}`))}catch(n){c++,l.push(`#${e+1} ${t.account_id} ❌ ${n.message}`)}}r.innerHTML=`
    <div style="margin-bottom:6px;font-weight:600">完成：成功 ${s} / 失败 ${c} / 共 ${a.length}</div>
    <div style="font-size:10px;background:var(--bg3);padding:8px;border-radius:4px;max-height:300px;overflow-y:auto">
      ${l.join(`<br>`)}
    </div>
  `};function v(e){return e?String(e).replace(/&/g,`&amp;`).replace(/</g,`&lt;`).replace(/>/g,`&gt;`).replace(/"/g,`&quot;`).replace(/'/g,`&#39;`):``}export{c as loadView};
(function(){let e=document.createElement(`link`).relList;if(e&&e.supports&&e.supports(`modulepreload`))return;for(let e of document.querySelectorAll(`link[rel="modulepreload"]`))n(e);new MutationObserver(e=>{for(let t of e)if(t.type===`childList`)for(let e of t.addedNodes)e.tagName===`LINK`&&e.rel===`modulepreload`&&n(e)}).observe(document,{childList:!0,subtree:!0});function t(e){let t={};return e.integrity&&(t.integrity=e.integrity),e.referrerPolicy&&(t.referrerPolicy=e.referrerPolicy),e.crossOrigin===`use-credentials`?t.credentials=`include`:e.crossOrigin===`anonymous`?t.credentials=`omit`:t.credentials=`same-origin`,t}function n(e){if(e.ep)return;e.ep=!0;let n=t(e);fetch(e.href,n)}})();var e=``,t=`productions`;function n(e){let t=e.nextElementSibling;if(!t||!t.classList)return;document.querySelectorAll(`.nav-group-header`).forEach(t=>{if(t===e)return;let n=t.nextElementSibling;if(n&&n.classList&&!n.classList.contains(`collapsed`)){n.classList.add(`collapsed`),t.dataset.collapsed=`true`;let e=t.querySelector(`span:last-child`);e&&(e.textContent=`▶`)}});let n=t.classList.toggle(`collapsed`);e.dataset.collapsed=n?`true`:`false`,e.querySelector(`span:last-child`).textContent=n?`▶`:`▼`}function r(){document.querySelectorAll(`.nav-group-header`).forEach(e=>{let t=e.nextElementSibling;if(t&&t.classList&&!t.classList.contains(`collapsed`)){t.classList.add(`collapsed`),e.dataset.collapsed=`true`;let n=e.querySelector(`span:last-child`);n&&(n.textContent=`▶`)}})}var i=0,a=30;m(),h(),s(),setInterval(()=>{t===`machines`&&p()},1e4),setInterval(()=>{t===`summary`&&loadSummary()},3e4);function o(e){e===`plugin-matrix`&&(e=`matrix-summary`),t=e,document.querySelectorAll(`.nav-item, .nav-sub`).forEach(t=>{t.classList.toggle(`active`,t.dataset.view===e)});let n=[`ave-render`,`ave-script`,`ave-materials`,`ave-templates`],r=e===`plugin-ave`||n.includes(e);document.querySelectorAll(`.nav-sub[data-group="ave"]`).forEach(e=>{e.style.display=r?`block`:`none`});let i=[`matrix-nurture`,`matrix-collect`,`matrix-publish`,`matrix-blueprints`,`matrix-comment`,`matrix-schedule`,`matrix-corpus`,`matrix-sms-proxy`,`matrix-like`,`matrix-login`,`ops-command`],a=e===`plugin-matrix`||i.includes(e);if(document.querySelectorAll(`.nav-sub[data-group="matrix"]`).forEach(e=>{e.style.display=a?`block`:`none`}),e===`plugin-ave`){document.querySelector(`.nav-item[data-view="plugin-ave"]`)?.classList.add(`active`),document.querySelector(`.nav-sub[data-view="workflow"]`)?.classList.add(`active`),o(`workflow`);return}if(e===`plugin-matrix`){document.querySelector(`.nav-item[data-view="plugin-matrix"]`)?.classList.add(`active`),o(`matrix-summary`);return}let s={"kb-knowledge":`kb-knowledge`,"kb-memory":`kb-memory`,"kb-system":`kb-system`,"kb-skills-int":`kb-skills`};if(s[e]){let n=s[e];document.querySelectorAll(`.nav-item`).forEach(t=>{t.classList.toggle(`active`,t.dataset.view===e)}),`matrix-sms-proxy.matrix-nurture.matrix-collect.matrix-publish.matrix-blueprints.matrix-comment.matrix-schedule.matrix-corpus.ave-render.ave-script.ave-materials.ave-templates.crawl-tasks.crawl-sources.crawl-history.machines.fleet-sync.fleet-reconcile.fleet-exec.serve-mcp.serve-dashboard.serve-schedule.productions.assets.costs.capabilities.workflow.kb`.split(`.`).forEach(e=>{document.getElementById(`view-`+e)?.classList.add(`hidden`)}),document.querySelectorAll(`[id^="plugin-view-"]`).forEach(e=>e.classList.add(`hidden`)),document.getElementById(`view-kb`)?.classList.remove(`hidden`),t=`kb`;let r=document.querySelector(`.kb-tab[data-tab="`+n+`"]`);r&&kbSwitchTab(n,r);return}if(n.includes(e)&&document.querySelector(`.nav-item[data-view="plugin-ave"]`)?.classList.add(`active`),i.includes(e)&&document.querySelector(`.nav-item[data-view="plugin-matrix"]`)?.classList.add(`active`),`matrix-sms-proxy.matrix-nurture.matrix-collect.matrix-publish.matrix-blueprints.matrix-comment.matrix-schedule.matrix-corpus.ave-render.ave-script.ave-materials.ave-templates.crawl-tasks.crawl-sources.crawl-history.machines.fleet-sync.fleet-reconcile.fleet-exec.serve-mcp.serve-dashboard.serve-schedule.productions.assets.costs.capabilities.workflow.kb`.split(`.`).forEach(t=>{document.getElementById(`view-`+t)?.classList.toggle(`hidden`,t!==e)}),document.querySelectorAll(`[id^="plugin-view-"]`).forEach(e=>e.classList.add(`hidden`)),e.startsWith(`plugin-`)&&!i.includes(e)&&e!==`matrix-summary`){let t=document.getElementById(`plugin-view-`+e.replace(`plugin-`,``));t&&t.classList.remove(`hidden`)}try{e===`productions`&&window.loadProductions()}catch{}try{e===`assets`&&window.loadAssets()}catch{}try{e===`costs`&&window.loadCosts()}catch{}try{e===`capabilities`&&window.loadCapabilities()}catch{}try{e===`workflow`&&window.loadWorkflow()}catch{}try{e===`machines`&&window.loadMachines()}catch{}try{e===`matrix-sms-proxy`&&window.loadSmsProxy()}catch{}try{e===`matrix-nurture`&&window.loadMatrixNurture()}catch{}try{e===`matrix-collect`&&window.loadMatrixCollect()}catch{}try{e===`matrix-publish`&&window.loadMatrixPublish()}catch{}try{e===`matrix-blueprints`&&window.loadMatrixBlueprints()}catch{}try{e===`matrix-comment`&&window.loadMatrixComment()}catch{}try{e===`matrix-schedule`&&window.loadMatrixSchedule()}catch{}try{e===`matrix-corpus`&&window.loadCorpus()}catch{}try{e===`ave-render`&&window.loadAveRender()}catch{}try{e===`ave-script`&&window.loadAveScript()}catch{}try{e===`ave-materials`&&window.loadAveMaterials()}catch{}try{e===`ave-templates`&&window.loadAveTemplates()}catch{}try{e===`crawl-tasks`&&window.loadCrawlTasks()}catch{}try{e===`crawl-sources`&&window.loadCrawlSources()}catch{}try{e===`crawl-history`&&window.loadCrawlHistory()}catch{}try{e===`fleet-sync`&&window.loadFleetSync()}catch{}try{e===`fleet-exec`&&window.loadFleetExec()}catch{}try{e===`matrix-like`&&window.loadMatrixLike()}catch{}try{e===`matrix-login`&&window.loadMatrixLogin()}catch{}try{e===`ops-command`&&window.loadOpsCommand()}catch{}try{e===`serve-mcp`&&window.loadServeMCP()}catch{}try{e===`serve-dashboard`&&window.loadServeDashboard()}catch{}try{e===`serve-schedule`&&window.loadServeSchedule()}catch{}if(e===`fleet-reconcile`){var c=document.getElementById(`view-fleet-reconcile`);if(c)try{g(c)}catch(e){c.innerHTML=`<div class="error">❌ `+e.message+`</div>`}}}window.toggleGroup=n,window.collapseAllGroups=r,window.switchView=o,window.closeDetail=u,window.showDetail=l,window.loadProductions=c,window.loadAssets=d,window.loadCosts=f,window.loadMachines=p,window.loadFleetReconcileView=g,setInterval(function(){try{typeof window.loadStats==`function`&&window.loadStats()}catch{}try{typeof window.loadMachineBar==`function`&&window.loadMachineBar()}catch{}},3e4),console.log(`✅ Dashboard boot complete`);async function s(){try{let t=await(await fetch(`${e}/api/summary`)).json(),n=t.plugins&&t.plugins.ave,r=n&&n.data||{},i=r.各机器||{},a=0,o=0,s=0;Object.values(i).forEach(e=>{a+=e.总生产||0,o+=e.费用||0,s+=e.今日||0}),document.getElementById(`statsBar`).innerHTML=`
      <div class="stat-card"><div class="label">机器数</div><div class="value" style="color:var(--green)">${Object.keys(i).length}</div><div class="sub">在线 ${r.在线||0}</div></div>
      <div class="stat-card"><div class="label">模块</div><div class="value" style="color:var(--blue)">${Object.keys(t.plugins||{}).length}</div><div class="sub">已加载</div></div>
      <div class="stat-card"><div class="label">主机</div><div class="value" style="color:var(--amber)">${t.source_hostname||`-`}</div></div>
      <div class="stat-card"><div class="label">知识库</div><div class="value" style="color:var(--primary)">${t.kb_stats?.total||`?`}</div><div class="sub">篇</div></div>
    `}catch{document.getElementById(`statsBar`).innerHTML=`<div class="error">❌ 连接失败</div>`}}async function c(t){t!==void 0&&(i=t);let n=document.getElementById(`productionList`);try{let e=document.getElementById(`matrixDashboardStats`);e||(e=document.createElement(`div`),e.id=`matrixDashboardStats`,n.parentNode.insertBefore(e,n));let t=await(await fetch(`/api/matrix/sms/accounts`)).json(),r=(t.accounts||[]).filter(e=>e.is_local),i=r.filter(e=>e.has_cookie),a=r.filter(e=>e.has_profile);e.innerHTML=`<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px"><div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center"><div style="font-size:24px;font-weight:700;color:#6366f1">`+r.length+`</div><div style="font-size:11px;color:var(--text2)">📱 本机账号</div></div><div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center"><div style="font-size:24px;font-weight:700;color:var(--green)">`+i.length+`</div><div style="font-size:11px;color:var(--text2)">🔑 已登录</div></div><div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center"><div style="font-size:24px;font-weight:700;color:var(--amber)">`+a.length+`</div><div style="font-size:11px;color:var(--text2)">👤 已采集</div></div><div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);text-align:center"><div style="font-size:24px;font-weight:700;color:var(--text2)">`+t.accounts.length+`</div><div style="font-size:11px;color:var(--text2)">🌐 联邦账号</div></div></div>`}catch{}n.innerHTML=`<div class="loading">加载中...</div>`;try{let t=document.getElementById(`filterStrategy`).value,r=document.getElementById(`filterStatus`).value,o=document.getElementById(`searchInput`).value,c=new URLSearchParams({limit:a,offset:i*a});t&&c.set(`strategy`,t),r&&c.set(`status`,r);let l=(await(await fetch(`${e}/api/productions?${c}`)).json()).data||[];if(!l.length){n.innerHTML=`<div class="error" style="padding:40px">暂无生产记录</div>`;return}let u=o?l.filter(e=>(e.script_name||``).includes(o)):l;if(!u.length){n.innerHTML=`<div class="error">未找到匹配记录</div>`;return}n.innerHTML=`<table><thead><tr>
      <th>编号</th><th>策略</th><th>脚本</th><th>状态</th><th>费用</th><th>时长</th><th>时间</th>
    </tr></thead><tbody>${u.map(e=>`<tr onclick="showDetail(${e.id})">
      <td>#${e.id}</td>
      <td>${e.strategy||`-`}</td>
      <td>${(e.script_name||``).slice(0,30)||`-`}</td>
      <td><span class="badge badge-${(e.status||`unknown`).toLowerCase()}">${e.status}</span></td>
      <td>¥${(e.total_cost||0).toFixed(2)}</td>
      <td>${e.duration_sec?e.duration_sec.toFixed(0)+`s`:`-`}</td>
      <td style="white-space:nowrap">${(e.created_at||``).slice(0,16)}</td>
    </tr>`).join(``)}</tbody></table>`,document.getElementById(`pagination`).innerHTML=i>0?`<button onclick="loadProductions(${i-1})">← 上一页</button><span style="padding:6px 12px;color:var(--text2)">第 ${i+1} 页</span><button onclick="loadProductions(${i+1})">下一页 →</button>`:`<span style="padding:6px 12px;color:var(--text2)">第 1 页</span><button onclick="loadProductions(${i+1})">下一页 →</button>`,s()}catch(e){n.innerHTML=`<div class="error">❌ 加载失败: ${e.message}</div>`}}async function l(t){let n=document.getElementById(`detailModal`);n.classList.remove(`hidden`),n.innerHTML=`<div class="loading" style="padding:60px">加载详情...</div>`;try{let r=await(await fetch(`${e}/api/productions/${t}`)).json(),i=r.production,a=r.steps||[],o=r.assets||[],s=r.costs||[];n.innerHTML=`<div style="position:fixed;inset:0;z-index:100;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;padding:20px" onclick="event.target===this&&closeDetail()">
      <div style="background:var(--bg2);border-radius:12px;max-width:800px;width:100%;max-height:85vh;overflow-y:auto;padding:24px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <div class="detail-header"><h2>#${i.id} ${i.strategy||``}</h2></div>
          <button onclick="closeDetail()" style="background:var(--bg3);border:none;color:var(--text);padding:6px 14px;border-radius:6px;cursor:pointer">✕ 关闭</button>
        </div>
        <div class="detail-meta">
          <span>状态: <span class="badge badge-${(i.status||``).toLowerCase()}">${i.status}</span></span>
          <span>时长: ${i.duration_sec?i.duration_sec.toFixed(0)+`s`:`-`}</span>
          <span>费用: ¥${(i.total_cost||0).toFixed(2)}</span>
          <span>输出: ${(i.output_path||`-`).slice(-30)}</span>
        </div>
        ${i.error_message?`<div style="margin-top:12px;padding:10px;background:rgba(239,68,68,.1);border-radius:6px;color:var(--red);font-size:13px">${i.error_message}</div>`:``}

        <div class="section-title">📋 步骤 (${a.length})</div>
        <div class="step-list">${a.length?a.map(e=>`<div class="step-item">
          <div class="dot" style="background:${e.status===`completed`?`var(--green)`:e.status===`failed`?`var(--red)`:`var(--amber)`}"></div>
          <span class="name">${e.step_name}</span>
          <span class="meta">${e.detail||``}${e.cost?` ¥`+e.cost.toFixed(2):``}</span>
          ${e.error_message?`<span style="color:var(--red);font-size:12px">${e.error_message}</span>`:``}
        </div>`).join(``):`<div style="color:var(--text2);padding:10px">无步骤记录</div>`}</div>

        <div class="section-title">💰 费用明细 (${s.length})</div>
        ${s.length?`<table><thead><tr><th>服务</th><th>时长</th><th>费用</th><th>备注</th></tr></thead><tbody>${s.map(e=>`<tr><td>${e.service||`-`}</td><td>${e.duration_s?e.duration_s+`s`:e.chars?e.chars+`字`:`-`}</td><td>¥${(e.cost_yuan||0).toFixed(2)}</td><td>${e.note||``}</td></tr>`).join(``)}</tbody></table>`:`<div style="color:var(--text2);padding:10px">无费用记录</div>`}

        <div class="section-title">💾 资产 (${o.length})</div>
        <div class="asset-grid">${o.length?o.map(e=>`<div class="asset-card">
          <div class="type">${e.asset_type||`-`}</div>
          <div class="name">${(e.name||e.file_path||`-`).slice(0,40)}</div>
          <div class="meta">${e.source||``}${e.file_size?` · `+(e.file_size/1024).toFixed(0)+`KB`:``}</div>
          ${e.tags?`<div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap">${e.tags.split(`,`).map(e=>`<span style="background:var(--bg3);padding:1px 6px;border-radius:4px;font-size:10px">${e}</span>`).join(``)}</div>`:``}
        </div>`).join(``):`<div style="color:var(--text2);padding:10px">无关联资产</div>`}</div>
      </div>
    </div>`}catch{n.innerHTML=`<div class="error">❌ 加载失败</div>`}}function u(){document.getElementById(`detailModal`).classList.add(`hidden`)}async function d(t){let n=document.getElementById(`assetList`);n.innerHTML=`<div class="loading">加载中...</div>`;try{let t=document.getElementById(`assetTypeFilter`).value,r=document.getElementById(`assetSearch`).value,i=new URLSearchParams({limit:50});t&&i.set(`type`,t),r&&i.set(`tag`,r);let a=await(await fetch(`${e}/api/assets?${i}`)).json();if(!a.length){n.innerHTML=`<div class="error" style="padding:40px">暂无资产</div>`;return}n.innerHTML=`<div class="asset-grid">${a.map(e=>`<div class="asset-card" onclick="showDetail(${e.production_id})" style="cursor:pointer">
      <div class="type">${e.asset_type||`-`}</div>
      <div class="name">${(e.name||e.file_path||`-`).slice(0,40)}</div>
      <div class="meta">${e.source||``}${e.file_size?` · `+(e.file_size/1024).toFixed(0)+`KB`:``}</div>
      ${e.tags?`<div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap">${e.tags.split(`,`).map(e=>`<span style="background:var(--bg3);padding:1px 6px;border-radius:4px;font-size:10px">${e}</span>`).join(``)}</div>`:``}
    </div>`).join(``)}</div>`}catch{n.innerHTML=`<div class="error">❌ 加载失败</div>`}}async function f(){let t=document.getElementById(`costSummary`),n=document.getElementById(`costBreakdown`);try{let r=await(await fetch(`${e}/api/summary`)).json(),i=r.ave||r;t.innerHTML=`<div class="stats" style="grid-template-columns:repeat(3,1fr)">
      <div class="stat-card"><div class="label">总费用</div><div class="value">¥${(i.total_cost||0).toFixed(2)}</div></div>
      <div class="stat-card"><div class="label">本月费用</div><div class="value">¥${(i.month_cost||0).toFixed(2)}</div></div>
      <div class="stat-card"><div class="label">平均费用/生产</div><div class="value">¥${i.total_productions?(i.total_cost/i.total_productions).toFixed(2):`0.00`}</div></div>
    </div>`;let a=await(await fetch(`${e}/api/costs/breakdown`)).json(),o=[`#6366f1`,`#22c55e`,`#f59e0b`,`#ef4444`,`#3b82f6`];if(!a.length){n.innerHTML=`<div class="error" style="padding:40px">暂无费用数据</div>`;return}let s=Math.max(...a.map(e=>e.total_cost),1);n.innerHTML=`<div class="chart-box">
      <div style="font-size:14px;font-weight:600;margin-bottom:12px">按策略统计</div>
      <div class="cost-bar">${a.map((e,t)=>`<div style="flex:${(e.total_cost/s*100).toFixed(0)};background:${o[t%5]};min-width:20px" title="${e.strategy}: ¥${e.total_cost.toFixed(2)}">¥${e.total_cost.toFixed(0)}</div>`).join(``)}</div>
      <table><thead><tr><th>策略</th><th>次数</th><th>总时长</th><th>总费用</th><th>平均费用</th></tr></thead><tbody>
        ${a.map(e=>`<tr><td>${e.strategy}</td><td>${e.count}</td><td>${(e.total_duration||0).toFixed(0)}s</td><td>¥${(e.total_cost||0).toFixed(2)}</td><td>¥${e.avg_cost||`0.00`}</td></tr>`).join(``)}
      </tbody></table>
    </div>`}catch(e){t.innerHTML=`<div class="error">❌ 加载失败: ${e.message}</div>`}}async function p(){let t=document.getElementById(`machineGrid`),n=document.getElementById(`machineCount`);t.innerHTML=`<div class="loading">读取联邦心跳中...</div>`;try{let r=(await(await fetch(`${e}/api/machines`)).json()).machines||[];if(n.textContent=`共 ${r.length} 台主机`,!r.length){t.innerHTML=`<div class="error" style="padding:40px">无心跳数据</div>`;return}t.innerHTML=r.map(e=>{let t=e.status===`online`||e._live===!0,n=e.status===`recent`,r=e._live===!0,i=r?`#1D9E75`:t?`#22C55E`:n?`#F59E0B`:`#EF4444`,a=e._last_push_sec||0,o=e.minutes_ago||Math.round(a/60)||999,s=r?`${a}秒前`:o<60?`${o} 分钟前`:`${(o/60).toFixed(1)} 小时前`,c=e.disk_used_gb||0,l=e.disk_total_gb||1,u=Math.round(c/l*100);e.disk_avail_gb;let d=`<div style="height:6px;background:var(--bg3);border-radius:3px;margin:6px 0;overflow:hidden">
        <div style="height:100%;width:${u}%;background:${u>85?`var(--red)`:u>60?`var(--amber)`:`var(--green)`};border-radius:3px;transition:width .3s"></div>
      </div>`;return`<div style="background:var(--bg2);border-radius:var(--radius);padding:20px;border:1px solid ${t?`rgba(34,197,94,.2)`:`var(--border)`}">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px">
            <span style="width:10px;height:10px;border-radius:50%;background:${i};display:inline-block;"></span>
            <div>
              <div style="font-weight:600;font-size:15px">${e.hostname}</div>
              ${e._uid?`<span style="font-size:10px;color:var(--text2);margin-left:6px">UID: ${e._uid}</span>`:``}
              <div style="font-size:11px;color:var(--text2)">${e.os||``}</div>
            </div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px;margin-bottom:12px">
          <div><span style="color:var(--text2)">guardd</span><br>v${e.guardd_version||`-`}</div>
          <div><span style="color:var(--text2)">最后心跳</span><br>${s}</div>
          <div><span style="color:var(--text2)">CPU 负载</span><br>${e.cpu_load||`-`}</div>
          <div><span style="color:var(--text2)">当前任务</span><br>${e.current_task||`无`}</div>
        </div>

        <div style="font-size:12px;color:var(--text2);margin-bottom:2px">磁盘: ${(e.disk_used_gb||0).toFixed(0)}G / ${(e.disk_total_gb||0).toFixed(0)}G</div>
        ${d}
        <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text2)">
          <span>已用 ${u}%</span>
          <span>剩余 ${(e.disk_avail_gb||0).toFixed(0)}G</span>
        </div>

        ${e.is_duplicate?`<div style="margin-top:8px;padding:4px 8px;background:rgba(245,158,11,.1);border-radius:4px;font-size:11px;color:var(--amber)">⚠ hostname 变更: 原名 ${e.duplicate_of||``}</div>`:``}
      </div>`}).join(``)}catch(e){t.innerHTML=`<div class="error">❌ 加载失败: ${e.message}</div>`}}async function m(){try{let e=await(await fetch(`/api/identity`)).json();document.getElementById(`identityHostname`).innerHTML=`📡 ${e.hostname}`,document.getElementById(`identityMeta`).innerHTML=`UID: ${e.uid} · ${e.role} · ${e.git_repo} @ ${(e.git_version||``).slice(0,7)}`}catch{}}async function h(){try{let e=await(await fetch(`/api/plugins`)).json(),n=document.getElementById(`navBar`);e.plugins;let r={矩阵:{icon:`📱`,items:[{view:`matrix-sms-proxy`,label:`🪪 账号管理`},{view:`matrix-nurture`,label:`🏃 养号执行`},{view:`matrix-collect`,label:`📡 信息采集`},{view:`matrix-publish`,label:`📤 内容发布`},{view:`matrix-comment`,label:`💬 定向评论`},{view:`matrix-like`,label:`❤️ 收藏点赞`},{view:`matrix-blueprints`,label:`📋 蓝图管理`},{view:`matrix-login`,label:`🔑 登录管理`},{view:`matrix-schedule`,label:`⏱ 定时任务`},{view:`matrix-corpus`,label:`📚 语料库`},{view:`ops-command`,label:`🖥️ 联邦指挥台`}]},视频工厂:{icon:`🎬`,items:[{view:`ave-render`,label:`渲染任务`},{view:`ave-script`,label:`脚本生成`},{view:`ave-materials`,label:`素材库`},{view:`ave-templates`,label:`模板`}]},内容采集:{icon:`📡`,items:[{view:`crawl-tasks`,label:`采集任务`},{view:`crawl-sources`,label:`源管理`},{view:`crawl-history`,label:`采集历史`}]},联邦:{icon:`🖥️`,items:[{view:`machines`,label:`机器状态`},{view:`fleet-sync`,label:`一键同步`},{view:`fleet-reconcile`,label:`对账检查`},{view:`fleet-exec`,label:`远程Shell`}]},服务:{icon:`⚙️`,items:[{view:`serve-mcp`,label:`MCP状态`},{view:`serve-dashboard`,label:`Dashboard日志`},{view:`serve-schedule`,label:`全局定时任务`}]}};async function i(){a()}function a(){let e=``;for(let[t,n]of Object.entries(r)){e+=`<div class="nav-group-header" onclick="toggleGroup(this)" data-collapsed="true">${n.icon} ${t} <span style="float:right;font-size:10px;opacity:.5">▶</span></div>`,e+=`<div class="nav-group-body collapsed">`;for(let t of n.items)if(t.sub){e+=`<div class="nav-item" data-view="${t.view}" onclick="switchView('${t.view}')">${t.label}</div>`;for(let n of t.sub)e+=`<div class="nav-sub" data-group="${t.view.replace(`plugin-`,``)}" data-view="${n.view}" onclick="switchView('${n.view}')" style="display:none">${n.label}</div>`}else e+=`<div class="nav-item" data-view="${t.view}" onclick="switchView('${t.view}')">${t.label}</div>`;e+=`</div>`}e+=`<div class="nav-item" data-view="timeline" onclick="switchView('timeline')" style="display:none">📈 时间线</div>`,n.innerHTML=e}a(),i(),o(t)}catch{c()}}async function g(e){let t=`fr_`+Math.random().toString(36).slice(2,6),n=null;e.innerHTML=`
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">🔍 对账检查</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">检查本机是否符合 ORACLE.yaml 宪法定义</p>
      <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
        <button onclick="window._doFleetReconcile('${t}')" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">🔍 执行对账</button>
        <button id="exportBtn_${t}" onclick="window._exportReconcile('${t}')" style="display:none;background:var(--bg2);color:var(--text);border:1px solid var(--border);padding:8px 16px;border-radius:6px;cursor:pointer;font-size:12px">📋 导出报告</button>
      </div>
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
      <div id="filter_${t}" style="display:none;margin-bottom:10px">
        <div style="display:flex;gap:6px;flex-wrap:wrap;font-size:12px">
          ${[`全部`,`环境`,`目录`,`文件`,`Git`,`服务`,`任务`].map((e,n)=>`<div id="filterTab_`+t+`_`+n+`" class="reconcile-filter-tab" style="height:28px;padding:0 14px;border-radius:6px;display:inline-flex;align-items:center;cursor:pointer;background:`+(n===0?`var(--primary)`:`var(--bg3)`)+`;color:`+(n===0?`#fff`:`var(--text)`)+`" onclick="window._filterReconcile('`+t+`',`+n+`)">`+e+`</div>`).join(``)}
        </div>
      </div>
      <div id="detail_${t}" style="display:none">
        <div style="font-size:11px;color:var(--text2);margin-bottom:6px">明细</div>
        <div id="detailList_${t}" style="display:flex;flex-direction:column;gap:4px"></div>
      </div>
      <div id="log_${t}" style="margin-top:12px;background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:300px;overflow:auto;display:none"></div>
    </div>`,window._doFleetReconcile=window._doFleetReconcile||(async function(e){let t=document.getElementById(`log_`+e);if(t){t.style.display=``,t.textContent=`⏳ 执行对账...
`;try{let a=await(await fetch(`/api/fleet/reconcile`,{method:`POST`})).json(),o=a.output||JSON.stringify(a,null,2);t.textContent=o,n=r(o),i(e,n)}catch(e){t.textContent=`❌ `+e.message}}});function r(e){let t=[],n=``;for(let r of e.split(`
`)){let e=r.replace(/\\u001b\\[[\\d;]+m/g,``).trim();if(!e)continue;if(/^[═━]{3,}\\s*\\d+\\.\\s/.test(e)){n=e.replace(/[═━\\s]+/g,` `).trim();continue}let i=null,a=e;if(/^✅/.test(e)?(i=`pass`,a=e.replace(/^✅\\s*/,``)):/^⚠️/.test(e)?(i=`warn`,a=e.replace(/^⚠️\\s*/,``)):/^❌/.test(e)&&(i=`fail`,a=e.replace(/^❌\\s*/,``)),i&&a){let e=a.indexOf(`:`),r=e>0?a.slice(0,e).trim():a,o=e>0?a.slice(e+1).trim():``;t.push({status:i,label:r,detail:o,section:n})}}return t}function i(e,t){let r=t.length,i=t.filter(e=>e.status===`pass`).length,a=t.filter(e=>e.status===`warn`).length,o=t.filter(e=>e.status===`fail`).length,s=r>0?Math.round(i/r*100):0;document.getElementById(`statTotal_`+e).textContent=r,document.getElementById(`statPass_`+e).textContent=i,document.getElementById(`statWarn_`+e).textContent=a,document.getElementById(`statFail_`+e).textContent=o,document.getElementById(`statRate_`+e).textContent=s+`%`,document.getElementById(`stats_`+e).style.display=``,document.getElementById(`filter_`+e).style.display=``,document.getElementById(`detail_`+e).style.display=``;let c=document.getElementById(`exportBtn_`+e);c&&(c.style.display=``),n=t,window._filterReconcile(e,0)}window._filterReconcile=window._filterReconcile||function(e,t){document.querySelectorAll(`#filter_`+e+` [id^="filterTab_"]`).forEach((e,n)=>{e.style.background=n===t?`var(--primary)`:`var(--bg3)`,e.style.color=n===t?`#fff`:`var(--text)`});let r=[`全部`,`环境`,`目录`,`文件`,`Git`,`服务`,`任务`][t],i=n||[];r!==`全部`&&(i=i.filter(e=>e.section.includes(r))),a(e,i)};function a(e,t){let n=document.getElementById(`detailList_`+e);if(!n)return;if(!t.length){n.innerHTML=`<div style="font-size:12px;color:var(--text2);padding:8px">无匹配项</div>`;return}let r=``;for(let e of t){let t=e.status===`pass`?`✅`:e.status===`warn`?`⚠️`:`❌`,n=e.status===`pass`?`var(--green)`:e.status===`warn`?`var(--amber)`:`var(--red)`;r+=`<div style="display:flex;gap:8px;align-items:flex-start;padding:6px 8px;background:var(--bg3);border-radius:6px;font-size:12px;line-height:1.5">`,r+=`<span style="color:`+n+`;flex-shrink:0">`+t+`</span>`,r+=`<span style="color:var(--text2);flex-shrink:0;min-width:80px">`+o(e.label)+`</span>`,e.detail&&(r+=`<span>`+o(e.detail)+`</span>`),r+=`</div>`}n.innerHTML=r}window._exportReconcile=window._exportReconcile||function(e){if(!n||!n.length)return;let t=n.filter(e=>e.status===`pass`).length,r=n.filter(e=>e.status===`warn`).length,i=n.filter(e=>e.status===`fail`).length,a=n.length,o=a>0?Math.round(t/a*100):0,s=`# AgentOS 联邦对账报告\\n\\n**生成时间**: `+new Date().toLocaleString()+`\\n\\n`;s+=`| 指标 | 数值 |\\n|:-----|:-----|\\n| 总项 | `+a+` |\\n| 通过 | `+t+` |\\n| 警告 | `+r+` |\\n| 失败 | `+i+` |\\n| 通过率 | `+o+`% |\\n\\n`,s+=`| 状态 | 检查项 | 详情 |\\n|:-----|:-------|:------|\\n`;for(let e of n)s+=`| `+(e.status===`pass`?`✅`:e.status===`warn`?`⚠️`:`❌`)+` | `+e.label+` | `+e.detail+` |\\n`;navigator.clipboard.writeText(s).then(function(){var t=document.getElementById(`exportBtn_`+e);if(t){var n=t.textContent;t.textContent=`✅ 已复制`,setTimeout(function(){t.textContent=n},2e3)}}).catch(function(){var e=document.createElement(`textarea`);e.value=s,e.style.cssText=`position:fixed;left:-9999px`,document.body.appendChild(e),e.select(),document.execCommand(`copy`),document.body.removeChild(e)})};function o(e){return String(e).replace(/&/g,`&amp;`).replace(/</g,`&lt;`).replace(/>/g,`&gt;`)}}window.loadFleetReconcileView=g;async function _(){let e=document.getElementById(`matrixBlueprintsContent`);e.innerHTML=`<div class="loading">加载中...</div>`;try{let[t,n]=await Promise.all([fetch(`/api/matrix/blueprints`),fetch(`/api/matrix/atom-ops`)]),r=await t.json(),i=await n.json(),a=Array.isArray(r)?r:r.blueprints||[],o=i.ops||[];window._matrixOps={},o.forEach(e=>{window._matrixOps[e.name]=e});let s=``;s+=`<div style="margin-bottom:10px;background:var(--bg2);border-radius:10px;border:1px solid var(--border);overflow:hidden">`,s+=`<div onclick="bpToggleList()" style="padding:10px 14px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;user-select:none">
      <span style="font-weight:600;font-size:13px">📋 蓝图库 <span class="badge badge-blue" style="font-size:10px;background:rgba(37,99,235,.1);color:var(--blue);padding:2px 6px;border-radius:6px">${a.length}</span></span>
      <span id="bp-list-arrow" style="color:var(--text2);font-size:12px">▶ 展开</span>
    </div>`,s+=`<div id="bp-list-body" style="display:none;padding:0 14px 10px">`,a.length?a.forEach(e=>{let t=(e.steps||[]).slice(0,3).map(e=>window._matrixOps?.[e.name]?.label||e.name).join(` → `);s+=`<div style="display:flex;align-items:center;gap:8px;padding:8px 10px;border-bottom:1px solid var(--border);font-size:13px">
          <span style="flex:1"><strong>${e.name}</strong> <span style="color:var(--text2);font-size:11px">${e.step_count}步 · ${e.platform||`douyin`}</span>
            ${t?`<br><span style="color:var(--text2);font-size:11px">${t}</span>`:``}</span>
          <span style="display:flex;gap:4px;flex-shrink:0">
            <button class="btn btn-sm" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:6px;cursor:pointer;font-size:11px" onclick="event.stopPropagation();bpExecute('${e.name}')">▶ 执行</button>
            <button class="btn btn-sm" style="background:transparent;color:var(--text);border:1px solid var(--border);padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px" onclick="event.stopPropagation();showBpEditor('${e.name}')">✏️</button>
            <button class="btn btn-sm" style="background:transparent;color:var(--red);border:1px solid rgba(239,68,68,.3);padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px" onclick="event.stopPropagation();delBp('${e.name}')">🗑</button>
          </span>
        </div>`}):s+=`<div style="padding:6px 0;color:var(--text2);font-size:13px">暂无蓝图</div>`,s+=`</div></div>`,s+=`<div style="background:var(--bg2);border-radius:var(--radius);padding:16px;border:1px solid var(--border)">`,s+=`
      <div id="bp-editor">
        <div style="display:flex;gap:12px;align-items:end;flex-wrap:wrap;margin-bottom:12px">
          <div style="flex:2;min-width:200px">
            <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:2px">蓝图名称</label>
            <input id="bp-name" placeholder="my_blueprint" style="font-size:14px;font-weight:600">
          </div>
          <div style="flex:1;min-width:120px">
            <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:2px">平台</label>
            <select id="bp-platform" onchange="bpUpdatePlatform()" style="font-size:13px">
              <option value="douyin">🎵 抖音</option>
              <option value="xiaohongshu">📕 小红书</option>
            </select>
          </div>
          <div style="flex:2;min-width:150px">
            <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:2px">说明</label>
            <input id="bp-desc" placeholder="可选说明">
          </div>
          <div style="display:flex;gap:6px;flex-shrink:0">
            <button class="btn btn-primary" onclick="bpSave()" style="padding:7px 18px">💾 保存</button>
            <button class="btn btn-outline" onclick="bpClear()" style="padding:7px 14px">🗑 清空</button>
            <button class="btn btn-outline" onclick="showBpEditor(null)" style="padding:7px 14px">+ 新建</button>
          </div>
        </div>

        <div style="margin:14px 0 8px;display:flex;align-items:center;gap:8px">
          <span style="font-weight:600;font-size:13px;color:var(--text2);white-space:nowrap">⚡ 原子操作</span>
          <div style="display:flex;gap:3px;flex-wrap:wrap" id="bp-op-tabs">
            <span class="badge badge-blue" style="cursor:pointer;padding:3px 8px;font-size:10px" data-ft="all" onclick="bpFilterOps('all')">📋 全部</span>
            <span class="badge badge-gray" style="cursor:pointer;padding:3px 8px;font-size:10px" data-ft="navigation" onclick="bpFilterOps('navigation')">🏠 导航</span>
            <span class="badge badge-gray" style="cursor:pointer;padding:3px 8px;font-size:10px" data-ft="browse" onclick="bpFilterOps('browse')">📱 浏览</span>
            <span class="badge badge-gray" style="cursor:pointer;padding:3px 8px;font-size:10px" data-ft="interact" onclick="bpFilterOps('interact')">💡 交互</span>
            <span class="badge badge-gray" style="cursor:pointer;padding:3px 8px;font-size:10px" data-ft="utility" onclick="bpFilterOps('utility')">⏳ 工具</span>
          </div>
        </div>
        <div id="bp-op-list" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:5px;margin:0 0 16px"></div>

        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-weight:600;font-size:13px;color:var(--text2)">📋 编排步骤</span>
          <span id="bp-step-count" style="font-size:11px;color:var(--text2)">0 步</span>
          <span id="bp-validate" style="font-size:11px"></span>
        </div>
        <div id="bp-steps" style="min-height:80px;border:2px dashed var(--border);border-radius:8px;padding:10px">
          <div style="color:var(--text2);font-size:13px;text-align:center;padding:20px">👆 点击上方原子操作卡片添加到步骤，可无限向下编排</div>
        </div>
      </div>`,s+=`</div>`,e.innerHTML=s,window._bpSteps=[],window._editingBp=null,window._bpFilter=`all`,window._bpListOpen=!1,ee()}catch(t){e.innerHTML=`<div class="error">${t.message}</div>`}}window.loadMatrixBlueprints=_,window.bpToggleList=function(){window._bpListOpen=!window._bpListOpen;let e=document.getElementById(`bp-list-body`),t=document.getElementById(`bp-list-arrow`);e&&t&&(e.style.display=window._bpListOpen?`block`:`none`,t.textContent=window._bpListOpen?`▼ 收起`:`▶ 展开`)},window.bpAddStep=function(e){let t=window._matrixOps?.[e];t&&(window._bpSteps=window._bpSteps||[],window._bpSteps.push({name:e,label:t.label||e,requires:t.requires||[],allows:t.allows||[]}),v())},window.bpRemoveStep=function(e){window._bpSteps=window._bpSteps||[],window._bpSteps.splice(e,1),v()};function v(){let e=document.getElementById(`bp-steps`),t=document.getElementById(`bp-validate`),n=document.getElementById(`bp-step-count`),r=window._bpSteps||[];if(e){if(n&&(n.textContent=`${r.length} 步`),!r.length){e.innerHTML=`<div style="color:var(--text2);font-size:13px;text-align:center;padding:20px">👆 点击上方原子操作卡片添加到步骤，可无限向下编排</div>`,t&&(t.innerHTML=``);return}e.innerHTML=r.map((e,t)=>{let n=``;if(t>0){let i=r[t-1],a=window._matrixOps?.[i.name];a&&a.allows&&a.allows[0]!==`*`&&!a.allows.includes(e.name)&&(n=`<span style="color:var(--red);font-size:11px;margin-left:6px">⚠ 与前一步不兼容</span>`)}if(t===0){let t=window._matrixOps?.[e.name];t&&!t.can_be_first?n=`<span style="color:var(--red);font-size:11px;margin-left:6px">⚠ 不能作为首步</span>`:t&&t.can_be_first&&(n=`<span style="color:var(--green);font-size:11px;margin-left:6px">✅ 起点</span>`)}let i=t<r.length-1?`<div style="padding:2px 0 2px 32px;color:var(--text2);font-size:14px">↓</div>`:``;return`<div style="padding:2px 0">
      <div style="display:flex;align-items:center;gap:8px;padding:6px 10px;background:var(--bg3);border-radius:6px;border:1px solid var(--border)">
        <span style="width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0;${n.includes(`不兼容`)||n.includes(`不能作为首步`)?`background:var(--red);color:#fff`:`background:var(--primary);color:#fff`}">${t+1}</span>
        <span style="flex:1;font-size:13px"><strong>${e.label}</strong> ${n}</span>
        <span style="cursor:pointer;color:var(--red);font-size:16px;opacity:.5" onclick="bpRemoveStep(${t})">✕</span>
      </div>
      ${i}
    </div>`}).join(``),t&&fetch(`/api/matrix/blueprints/validate`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({steps:r.map(e=>({name:e.name}))})}).then(e=>e.json()).then(e=>{t.innerHTML=e.valid?`<span style="color:var(--green);font-size:12px">✅ 编排合法</span>`:`<span style="color:var(--red);font-size:12px">❌ `+(e.errors||[]).map(e=>e.msg).join(`; `)+`</span>`}).catch(()=>{})}}window.bpSave=async function(){let e=document.getElementById(`bp-name`)?.value;if(!e){alert(`请输入蓝图名称`);return}let t=(window._bpSteps||[]).map(e=>({name:e.name,description:window._matrixOps?.[e.name]?.desc||``}));if(!t.length){alert(`请添加至少一个步骤`);return}try{let n=await fetch(`/api/matrix/blueprints`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({name:e,description:document.getElementById(`bp-desc`)?.value||``,platform:document.getElementById(`bp-platform`)?.value||`douyin`,steps:t})});if(!n.ok)throw Error((await n.json()).detail);bpClear(),_()}catch(e){alert(`❌ `+e.message)}},window.bpClear=function(){window._bpSteps=[];let e=document.getElementById(`bp-name`);e&&(e.value=``),window._editingBp=null,v()},window._bpFilter=`all`;var y={douyin:[`navigation`,`browse`,`interact`,`utility`],xiaohongshu:[`navigation`,`browse`,`interact`,`utility`]};window.bpFilterOps=function(e){window._bpFilter=e,document.querySelectorAll(`#bp-op-tabs span`).forEach(t=>{t.style.display!==`none`&&(t.className=t.dataset.ft===e?`badge badge-blue`:`badge badge-gray`,t.style.cssText=`cursor:pointer;padding:3px 8px;font-size:10px`)}),S()};function b(){let e=document.getElementById(`bp-platform`);return e?e.value:`douyin`}function ee(){let e=y[b()]||[`navigation`,`browse`,`interact`,`utility`];document.querySelectorAll(`#bp-op-tabs span`).forEach(t=>{let n=t.dataset.ft,r=n===`all`||e.includes(n);t.style.display=r?`inline-block`:`none`}),window._bpFilter!==`all`&&!e.includes(window._bpFilter)&&(window._bpFilter=`all`),S()}function x(e,t){if(!e){let e=window._matrixOps?.[t];return e?!!e.can_be_first:!0}let n=window._matrixOps?.[e];return!n||n.allows&&n.allows[0]===`*`?!0:n.allows?n.allows.includes(t):!0}function S(){let e=document.getElementById(`bp-op-list`);if(!e)return;let t=Object.values(window._matrixOps||{}),n=b(),r=window._bpFilter||`all`,i=window._bpSteps||[],a=i.length>0?i[i.length-1]:null,o=a?a.name:null,s=t.filter(e=>{let t=e.platform||`通用`;return t===n||t===`通用`}),c=r===`all`?s:s.filter(e=>(e.category||``)===r);e.innerHTML=c.map(e=>{let t=x(o,e.name),n=``;e.requires&&e.requires.length&&e.requires[0]!==`*`?n=`<span style="font-size:9px;color:var(--blue)">← ${e.requires.join(`,`)}</span>`:e.can_be_first&&!o&&(n=`<span style="font-size:9px;color:var(--green)">✅ 首步</span>`);let r=t?`1`:`.35`,i=t?`pointer`:`not-allowed`,a=t?`bpAddStep('${e.name}')`:``,s=t?``:`<span style="font-size:9px;color:var(--red);margin-left:4px">🚫</span>`;return`<div class="op-card" style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);cursor:${i};opacity:${r}" onclick="${a}">
      <div style="font-size:12px;font-weight:600">${e.label||e.name}${s}</div>
      <div style="font-size:10px;color:var(--text2);margin-top:2px">${e.desc||``}</div>
      <div style="margin-top:2px">${n}</div>
    </div>`}).join(``),c.length||(e.innerHTML=`<div style="color:var(--text2);font-size:12px;padding:10px;grid-column:1/-1">当前平台/分类无可用操作</div>`)}window.showBpEditor=async function(e){if(!e){bpClear();return}try{let t=((await(await fetch(`/api/matrix/blueprints`)).json()).blueprints||[]).find(t=>t.name===e);if(!t)return;window._editingBp=e,document.getElementById(`bp-name`).value=e,document.getElementById(`bp-desc`).value=t.description||``,document.getElementById(`bp-platform`).value=t.platform||`douyin`,window._bpSteps=(t.steps||[]).map(e=>{let t=window._matrixOps?.[e.name||e];return{name:e.name||e,label:t?.label||e.name||e,requires:t?.requires||[],allows:t?.allows||[]}}),v()}catch(e){alert(`❌ `+e.message)}},window.delBp=async function(e){if(confirm(`删除蓝图 ${e}?`))try{let t=await fetch(`/api/matrix/blueprints/${e}`,{method:`DELETE`});if(!t.ok)throw Error((await t.json()).detail);_()}catch(e){alert(`❌ `+e.message)}};function te(e,t,n,r){let i=document.getElementById(e);i&&(i.innerHTML=`
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:60px 20px;text-align:center">
      <div style="font-size:48px;margin-bottom:16px;opacity:.3">${{无功能:`❌`,无API:`🔌`,无CLI:`🖥️`,待集成:`⏳`}[n]||`📋`}</div>
      <h2 style="font-size:20px;margin-bottom:8px;color:var(--text)">${t}</h2>
      <div style="display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:6px;background:rgba(217,119,6,.1);color:#d97706;font-size:12px;font-weight:600;margin-bottom:12px">
        🏗️ ${n}
      </div>
      <p style="font-size:13px;color:var(--text2);max-width:400px;line-height:1.6">${r}</p>
    </div>`)}async function ne(){let e=document.getElementById(`view-matrix-nurture`);e.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">🌱 养号执行 <span style="font-size:10px;color:var(--text2);font-weight:400">预检 → 窗口定位 → 执行 → 验证</span></div>
        <div id="nurtureAcctList" style="margin-bottom:6px">
          <div class="loading" style="padding:8px;font-size:12px">⏳ 加载账号列表...</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:11px;color:var(--text2)">轮数:
            <select id="ndRounds" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="1">1 测试</option><option value="5">5</option>
              <option value="10" selected>10 默认</option>
              <option value="20">20</option><option value="30">30</option>
            </select>
          </label>
          <label style="font-size:11px;color:var(--text2)">蓝图:
            <select id="ndBlueprint" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="">自动匹配</option>
              <option value="douyin_daily">🎵 douyin_daily</option>
              <option value="xhs_daily">📕 xhs_daily</option>
              <option value="douyin_active_v1">🎵 douyin_active_v1</option>
              <option value="xhs_active_v1">📕 xhs_active_v1</option>
            </select>
          </label>
          <button onclick="nurturePreflight()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔍 预检</button>
          <button onclick="nurtureExec()" style="background:#22c55e;color:#000;border:none;padding:4px 14px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 执行选中</button>
          <button onclick="nurtureExecAll()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">📋 全部启用</button>
          <span id="nurtureSelCount" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>
        <div id="nurtureStatus" style="font-size:11px;color:var(--text2);margin-top:4px"></div>
        <div id="nurturePreflightInfo" style="font-size:10px;color:var(--text2);margin-top:2px;font-family:monospace;white-space:pre-wrap"></div>
        <div id="nurtureLog" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:300px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;let t=await _loadAccounts();_renderAccountSelector(`nurtureAcctList`,{_data:t,height:`350px`}),document.getElementById(`nurtureSelCount`).textContent=`已选 `+_getSelectedAccounts().length+` 个`}window.loadMatrixNurture=ne;async function re(){let e=document.getElementById(`view-matrix-collect`);e.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">📡 登录与信息采集 <span style="font-size:10px;color:var(--text2);font-weight:400">登录+采集一体化，选择账号后可仅登录或登录后采集</span></div>
        <div id="collectAccountList" style="margin-bottom:6px">
          <div class="loading" style="padding:8px;font-size:12px">⏳ 加载账号列表...</div>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
          <span id="collectStatus" style="font-size:10px;color:var(--text2)">⏸️ 空闲</span>
          <button onclick="collectLogin()" style="background:#6366f1;color:#fff;border:none;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600">🔑 登录选中</button>
          <button onclick="collectExec()" style="background:var(--primary);color:#fff;border:none;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600">📥 采集选中</button>
          <button onclick="collectAll()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">📋 采集全部</button>
          <button onclick="cancelCollect()" style="background:rgba(220,38,38,.1);color:var(--red);border:1px solid rgba(220,38,38,.3);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">⏹ 停止</button>
          <span id="collectSelCount" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>
        <div id="collectLog" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:250px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;let t=await _loadAccounts();_renderAccountSelector(`collectAccountList`,{_data:t,height:`300px`,checkAll:!1}),document.getElementById(`collectSelCount`).textContent=`已选 `+_getSelectedAccounts().length+` 个`;try{(await(await fetch(`/api/matrix/collect-homepage/status`)).json()).running&&(document.getElementById(`collectStatus`).innerHTML=`<span style="color:var(--green)">🟢 采集中</span>`)}catch{}}window.loadMatrixCollect=re,window.collectLogin=async function(){let e=_getSelectedAccounts();if(!e.length){alert(`请先选择要登录的账号`);return}let t=document.getElementById(`collectLog`);t&&(t.textContent=`🔑 登录 `+e.length+` 个账号...
`);for(let n of e)try{let e=await(await fetch(`/api/ops/run`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({type:`login`,accounts:[n.id]})})).json();t&&(t.textContent+=n.id+`: `+(e.status||`OK`)+`
`)}catch(e){t&&(t.textContent+=n.id+`: ❌ `+e.message+`
`)}},window.collectExec=async function(){let e=_getSelectedAccounts();if(!e.length){alert(`请先选择要采集的账号`);return}let t=document.getElementById(`collectLog`);t&&(t.textContent=`📥 采集 `+e.length+` 个账号...
`);for(let n of e)try{let e=await(await fetch(`/api/matrix/collect-homepage`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({account_id:n.id})})).json();document.getElementById(`collectStatus`).innerHTML=`<span style="color:var(--green)">🟢 采集中</span>`,t&&(t.textContent+=n.id+`: `+(e.status||`OK`)+` 机器:`+(e.machine||n.machine)+`
`)}catch(e){t&&(t.textContent+=n.id+`: ❌ `+e.message+`
`)}},window.collectAll=async function(){let e=_getSelectedAccounts();if(!e.length){alert(`没有可采集的账号`);return}confirm(`采集全部 `+e.length+` 个账号？`)&&await collectExec()},window.collectByIdentity=async function(e){let t=document.getElementById(`collectLog`);if(t){t.textContent=`⏳ 开始采集身份: `+e+`
`;try{let n=await(await fetch(`/api/matrix/collect-homepage`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({identity_dir:e})})).json();t.textContent+=JSON.stringify(n,null,2)}catch(e){t.textContent+=`❌ `+e.message}}},window.collectByIdentity=async function(e){let t=document.getElementById(`collectLog`);if(t){t.textContent=`⏳ 开始采集身份: `+e+`
`;try{let n=await(await fetch(`/api/matrix/collect-homepage`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({identity_dir:e})})).json();t.textContent+=JSON.stringify(n,null,2)}catch(e){t.textContent+=`❌ `+e.message}}},window.collectByPhone=async function(){let e=document.getElementById(`collectPhoneInput`)?.value,t=document.getElementById(`collectLog`);if(t){if(!e){t.textContent=`请输入手机号`;return}t.textContent=`⏳ 开始采集手机号: `+e+`
`;try{let n=await(await fetch(`/api/matrix/collect-homepage/phone`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({phone:e})})).json();t.textContent+=JSON.stringify(n,null,2)}catch(e){t.textContent+=`❌ `+e.message}}},window.cancelCollect=async function(){let e=document.getElementById(`collectLog`);if(e){e.textContent=`⏳ 停止中...
`;try{let t=await(await fetch(`/api/matrix/collect-homepage/cancel`,{method:`POST`})).json();e.textContent+=JSON.stringify(t,null,2)}catch(t){e.textContent+=`❌ `+t.message}}},window.loadCollectHistory=async function(){let e=document.getElementById(`collectLog`);if(e){e.textContent=`⏳ 加载历史...
`;try{let t=await(await fetch(`/api/matrix/homepage-history`)).json();e.textContent+=JSON.stringify(t,null,2)}catch(t){e.textContent+=`❌ `+t.message}}};async function ie(){te(`view-matrix-publish`,`📤 内容发布`,`无CLI`,`发布模块的 CLI 封装尚未完成。现有的 publish_video.py 在 agent-os/agent-sync/05_tools/07_matrix/scripts/ 目录下。需要 agentos matrix publish CLI 封装。`)}window.loadMatrixPublish=ie;async function ae(){let e=document.getElementById(`view-matrix-comment`);e.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">💬 定向评论 <span style="font-size:10px;color:var(--text2);font-weight:400">选择账号 → 填入视频链接 → 方向/语料 → 执行</span></div>
        <div id="commentAccountList" style="margin-bottom:6px">
          <div class="loading" style="padding:8px;font-size:12px">⏳ 加载账号列表...</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
          <textarea id="commentUrls" placeholder="视频链接（每行一个，支持多个）" rows="3" style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
          <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:140px">
            <select id="commentDirection" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
              <option value="">自动选方向</option>
              <option value="称赞">👍 称赞</option>
              <option value="提问">🤔 提问</option>
              <option value="共鸣">💗 共鸣</option>
              <option value="感慨">😌 感慨</option>
              <option value="客观">📊 客观</option>
            </select>
            <select id="commentCorpus" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
              <option value="">默认语料</option>
              <option value="通用">📚 通用</option>
              <option value="科技">💻 科技</option>
              <option value="生活">🏠 生活</option>
              <option value="美食">🍔 美食</option>
              <option value="娱乐">🎮 娱乐</option>
            </select>
            <button onclick="runComment()" style="background:var(--primary);color:#fff;border:none;padding:5px 12px;border-radius:4px;cursor:pointer;font-size:12px">🚀 执行评论</button>
          </div>
        </div>
        <div id="commentResult" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;let t=await _loadAccounts();_renderAccountSelector(`commentAccountList`,{_data:t,height:`300px`,checkAll:!1,hideFilter:!0})}window.loadMatrixComment=ae,window.runComment=async function(){let e=_getSelectedAccounts(),t=document.getElementById(`commentUrls`)?.value,n=document.getElementById(`commentDirection`)?.value,r=document.getElementById(`commentCorpus`)?.value,i=document.getElementById(`commentResult`);if(!t||!t.trim()){i.textContent=`请填写至少一个视频链接`;return}let a=t.split(`
`).map(e=>e.trim()).filter(e=>e);if(!a.length){i.textContent=`请填写有效的视频链接`;return}if(!e.length){i.textContent=`请先选择要执行的账号`;return}i.textContent=`⏳ 使用 `+e.length+` 个账号评论 `+a.length+` 个视频...
`;let o=[];for(let t of a)for(let i of e)try{let e=await(await fetch(`/api/matrix/task/run`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({type:`comment`,url:t,direction:n||null,account:i.id,corpus:r||null})})).json();o.push({url:t,account:i.id,status:e.error?`❌`:`✅`,msg:e.error||e.task_id||`OK`})}catch(e){o.push({url:t,account:i.id,status:`❌`,msg:e.message})}i.textContent=`✅ `+o.filter(e=>e.status===`✅`).length+`/`+o.length+` 完成
`+o.slice(0,30).map(e=>e.status+` `+(e.account||``)+` `+(e.url||``).slice(0,35)+` `+(e.msg||``)).join(`
`)};async function oe(){let e=document.getElementById(`view-matrix-schedule`);e.innerHTML=`<div id="schedPanel" style="padding:20px"><div class="loading">⏳ 加载定时任务...</div></div>`;try{let e=await(await fetch(`/api/matrix/schedules`)).json(),t=e.tasks||e||[];document.getElementById(`schedPanel`).innerHTML=`
      <h2 style="font-size:18px;margin-bottom:12px">⏰ 定时任务</h2>
      <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);margin-bottom:12px">
        <div style="font-size:12px;font-weight:600;margin-bottom:6px">📋 任务列表 (${Array.isArray(t)?t.length:0})</div>
        <div style="font-size:12px">${Array.isArray(t)&&t.length?t.map(e=>`<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border)"><span style="font-size:10px">`+(e.enabled?`🟢`:`⚪`)+`</span><span>`+(e.account||e.id||`-`)+`</span><span style="font-size:11px;color:var(--text2)">`+(e.blueprint||``)+`</span><span style="font-size:11px;color:var(--text2)">`+(e.time||``)+`</span></div>`).join(``):`<span style="color:var(--text2)">暂无定时任务</span>`}</div>
      </div>
      <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);margin-bottom:8px">
        <div style="font-size:12px;font-weight:600;margin-bottom:6px">➕ 新建定时任务</div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
          <button onclick="switchView('matrix-commands')" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">→ 前往命令与任务页</button>
        </div>
      </div>
      <div style="font-size:10px;color:var(--text2)">完整调度管理在「矩阵 → 命令与任务」页面</div>`}catch(e){document.getElementById(`schedPanel`).innerHTML=`<div style="padding:20px"><h2 style="font-size:18px;margin-bottom:12px">⏰ 定时任务</h2><div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border)"><div class="error">❌ `+e.message+`</div><p style="font-size:12px;color:var(--text2);margin-top:8px">完整调度管理在「矩阵 → 命令与任务」页面</p></div></div>`}}window.loadMatrixSchedule=oe;async function se(){let e=document.getElementById(`view-matrix-like`);e.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">❤️ 收藏点赞 <span style="font-size:10px;color:var(--text2);font-weight:400">选择账号 → 填入视频链接 → 执行点赞</span></div>
        <div id="likeAccountList" style="margin-bottom:6px">
          <div class="loading" style="padding:8px;font-size:12px">⏳ 加载账号列表...</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
          <textarea id="likeUrls" placeholder="视频链接（每行一个，支持多个）" rows="3" style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
          <button onclick="runLike()" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:4px;cursor:pointer;font-size:12px;align-self:flex-start">❤️ 执行点赞</button>
        </div>
        <div id="likeResult" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;let t=await _loadAccounts();_renderAccountSelector(`likeAccountList`,{_data:t,height:`300px`,checkAll:!1,hideFilter:!0})}window.loadMatrixLike=se,window.runLike=async function(){let e=_getSelectedAccounts(),t=document.getElementById(`likeUrls`)?.value,n=document.getElementById(`likeResult`);if(!t||!t.trim()){n.textContent=`请填写视频链接`;return}let r=t.split(`
`).map(e=>e.trim()).filter(e=>e);if(!r.length){n.textContent=`请填写有效的视频链接`;return}if(!e.length){n.textContent=`请先选择要执行的账号`;return}n.textContent=`⏳ 执行 `+r.length+` 个点赞...
`;let i=[];for(let t of r)for(let n of e)try{let e=await(await fetch(`/api/matrix/task/run`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({type:`like`,url:t,account:n.id})})).json();i.push({url:t,account:n.id,status:e.error?`❌`:`✅`,msg:e.error||e.task_id||`OK`})}catch(e){i.push({url:t,account:n.id,status:`❌`,msg:e.message})}n.textContent=`✅ `+i.filter(e=>e.status===`✅`).length+`/`+i.length+`
`+i.slice(0,30).map(e=>e.status+` `+(e.account||``)+` `+(e.url||``).slice(0,35)).join(`
`)};async function ce(){let e=document.getElementById(`view-matrix-login`);e.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:16px;border:1px solid var(--border);text-align:center">
        <div style="font-size:24px;margin-bottom:8px">🔑</div>
        <div style="font-size:14px;font-weight:600;margin-bottom:4px">登录管理已合并到信息采集</div>
        <div style="font-size:12px;color:var(--text2);margin-bottom:12px">登录 → 采集是同一流程，请前往「信息采集」页面操作</div>
        <button onclick="switchView('matrix-collect')" style="background:var(--primary);color:#fff;border:none;padding:8px 24px;border-radius:6px;cursor:pointer;font-size:13px">→ 前往信息采集</button>
      </div>
    </div>`}window.loadMatrixLogin=ce;async function le(){let e=document.getElementById(`view-ops-command`);e.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border);margin-bottom:8px">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">🖥️ 联邦指挥台 <span style="font-size:10px;color:var(--text2);font-weight:400">选机器 → 选操作 → 选账号 → 批量执行</span></div>
        <div id="opsAccountList" style="margin-bottom:6px">
          <div class="loading" style="padding:8px;font-size:12px">⏳ 加载账号列表...</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:11px;color:var(--text2)">操作:
            <select id="opsType" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
              <option value="nurture">🏃 养号</option>
              <option value="collect">📡 采集</option>
              <option value="login">🔑 登录</option>
              <option value="logout">🔒 登出</option>
            </select>
          </label>
          <label style="font-size:11px;color:var(--text2)" id="opsRoundsLabel">轮数:
            <select id="opsRounds" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
              <option value="1">1</option><option value="5">5</option>
              <option value="10" selected>10</option><option value="20">20</option>
            </select>
          </label>
          <button onclick="opsBatchExec()" style="background:#22c55e;color:#000;border:none;padding:5px 16px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 批量执行</button>
          <span id="opsSelCount" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>
        <div id="opsResult" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>
      <div id="opsHistoryBox" style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-size:12px;font-weight:600;margin-bottom:4px">📋 执行历史</div>
        <div id="opsHistoryList" style="font-size:10px;max-height:180px;overflow-y:auto">
          <div class="loading">⏳ 加载执行历史...</div>
        </div>
      </div>
    </div>`;let t=await _loadAccounts();_renderAccountSelector(`opsAccountList`,{_data:t,height:`280px`,checkAll:!1}),document.getElementById(`opsSelCount`).textContent=`已选 `+_getSelectedAccounts().length+` 个`,ue()}window.loadOpsCommand=le;async function ue(){try{let e=(await(await fetch(`/api/matrix/nurture/results`)).json()).results||[],t=document.getElementById(`opsHistoryList`);if(!e.length){t.innerHTML=`<div style="color:var(--text2)">暂无执行记录</div>`;return}let n=`<table style="width:100%"><tr><th>时间</th><th>账号</th><th>状态</th><th>步骤</th><th>耗时</th></tr>`;e.slice(0,20).forEach(e=>{let t=e.status===`completed`?`✅`:e.status===`running`?`⏳`:`❌`,r=e.completed_at||e.started_at||``,i=r?new Date(r).toLocaleString(`zh-CN`,{hour:`2-digit`,minute:`2-digit`}):`-`,a=e.steps?(e.steps.success||0)+`/`+(e.steps.total||0):`-`,o=e.duration_secs?Math.round(e.duration_secs/60)+`min`:`-`;n+=`<tr><td>${i}</td><td>${e.account}</td><td>${t}</td><td>${a}</td><td>${o}</td></tr>`}),n+=`</table>`,t.innerHTML=n}catch{}}async function de(){_renderShell(`view-ave-render`,`🎬 渲染任务`,`无API`,`AVE 渲染任务的 API 尚未暴露。需要完成 agentos ave CLI 封装后对接。`)}window.loadAveRender=de;async function fe(){_renderShell(`view-ave-script`,`📝 脚本生成`,`无API`,`脚本生成模块的 API 尚未暴露。需要完成 agentos ave CLI 封装后对接。`)}window.loadAveScript=fe;async function C(){_renderShell(`view-ave-materials`,`📦 素材库`,`无API`,`素材管理模块的 API 尚未暴露。当前素材通过 SQLite 管理，需封装为 Dashboard API。`)}window.loadAveMaterials=C;async function w(){_renderShell(`view-ave-templates`,`📋 模板`,`无API`,`模板管理模块的 API 尚未暴露。需要完成 agentos ave CLI 封装后对接。`)}window.loadAveTemplates=w;async function T(){let e=document.getElementById(`view-crawl-tasks`);e.innerHTML=`<div id="crawlTaskPanel" style="padding:20px"><div class="loading">⏳ 加载采集管理...</div></div>`;try{let e=await(await fetch(`/api/plugins/collector/summary`)).json();document.getElementById(`crawlTaskPanel`).innerHTML=`
      <h2 style="font-size:18px;margin-bottom:12px">📡 采集任务</h2>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;margin-bottom:12px">
        <div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
          <div style="font-size:12px;color:var(--text2)">总采集数</div>
          <div style="font-size:24px;font-weight:700">${e.total||0}</div>
        </div>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
          <div style="font-size:12px;color:var(--text2)">今日新增</div>
          <div style="font-size:24px;font-weight:700;color:var(--green)">${e.today||0}</div>
        </div>
      </div>
      <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border)">
        <div style="font-size:12px;font-weight:600;margin-bottom:8px">🔧 操作</div>
        <button onclick="switchView('plugin-collector')" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">→ 打开采集管理器</button>
        <span style="font-size:11px;color:var(--text2);margin-left:8px">完整采集管理界面</span>
      </div>`}catch{document.getElementById(`crawlTaskPanel`).innerHTML=`<div style="padding:0"><h2 style="font-size:18px;margin-bottom:12px">📡 采集任务</h2>
      <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border)">
        <p style="font-size:13px;color:var(--text2);margin-bottom:8px">采集管理器可通过下方按钮访问</p>
        <button onclick="switchView('plugin-collector')" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">→ 打开采集管理器</button>
      </div></div>`}}window.loadCrawlTasks=T;async function E(){_renderShell(`view-crawl-sources`,`📡 源管理`,`无CLI`,`采集源管理需要 agentos crawl CLI 封装后实现。`)}window.loadCrawlSources=E;async function D(){_renderShell(`view-crawl-history`,`📜 采集历史`,`无API`,`采集历史的统一展示 API 尚未完成。`)}window.loadCrawlHistory=D;async function O(){let e=document.getElementById(`view-fleet-sync`);e.innerHTML=`
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">🔄 一键同步</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">通过 Git 同步三台机器（本机 / 5kecheng / 7kecheng）的最新代码</p>
      <div style="display:flex;gap:8px;margin-bottom:12px">
        <button onclick="doFleetSync()" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">🔄 执行同步</button>
      </div>
      <div id="fleetSyncLog" style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:400px;overflow:auto"></div>
    </div>`}window.loadFleetSync=O,window.doFleetSync=async function(){let e=document.getElementById(`fleetSyncLog`);e.textContent=`⏳ 执行中...
`;try{let t=await(await fetch(`/api/fleet/sync`,{method:`POST`})).json();e.textContent=t.output||JSON.stringify(t,null,2)}catch(t){e.textContent=`❌ `+t.message}};async function k(){let e=document.getElementById(`view-fleet-reconcile`);e.innerHTML=`
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">🔍 对账检查</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">检查本机是否符合 ORACLE.yaml 宪法定义</p>
      <div style="display:flex;gap:8px;margin-bottom:12px">
        <button onclick="doFleetReconcile()" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">🔍 执行对账</button>
      </div>
      <div id="fleetReconcileLog" style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:400px;overflow:auto"></div>
    </div>`}window.loadFleetReconcile=k,window.doFleetReconcile=async function(){let e=document.getElementById(`fleetReconcileLog`);e.textContent=`⏳ 执行中...
`;try{let t=await(await fetch(`/api/fleet/reconcile`,{method:`POST`})).json();e.textContent=t.output||JSON.stringify(t,null,2)}catch(t){e.textContent=`❌ `+t.message}};async function A(){let e=document.getElementById(`view-fleet-exec`);e.innerHTML=`
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">💻 远程Shell</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">在远程机器上执行命令（通过 mc remote exec）</p>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px">
        <select id="fleetExecMachine" style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px">
          <option value="5kechengdeAir">5kechengdeAir</option>
          <option value="7kecheng">7kecheng</option>
        </select>
        <input id="fleetExecCmd" placeholder="输入命令..." style="flex:1;min-width:200px;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px">
        <button onclick="doFleetExec()" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">➡ 执行</button>
      </div>
      <div id="fleetExecLog" style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:400px;overflow:auto"></div>
    </div>`}window.loadFleetExec=A,window.doFleetExec=async function(){let e=document.getElementById(`fleetExecMachine`)?.value,t=document.getElementById(`fleetExecCmd`)?.value,n=document.getElementById(`fleetExecLog`);if(!t){n.textContent=`请输入命令`;return}n.textContent=`⏳ 执行中...
`;try{let r=await(await fetch(`/api/federation/exec`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({machine:e,command:t,timeout:30})})).json();n.textContent=r.output||JSON.stringify(r,null,2)}catch(e){n.textContent=`❌ `+e.message}};async function j(){_renderShell(`view-serve-mcp`,`🔌 MCP状态`,`无功能`,`MCP 状态监控尚未实现。这是显示当前 MCP Server 连接状态和运行指标的页面。`)}window.loadServeMCP=j;async function M(){_renderShell(`view-serve-dashboard`,`📊 Dashboard日志`,`无功能`,`Dashboard 日志聚合页面尚未实现。将汇总各模块的运行日志。`)}window.loadServeDashboard=M;async function N(){_renderShell(`view-serve-schedule`,`⏰ 全局定时任务`,`无功能`,`全局调度器管理页面尚未实现。将在 agentos serve schedule CLI 封装完成后对接。`)}window.loadServeSchedule=N;async function P(){R(),B(),L(),F()}window.loadSmsProxy=P;async function F(){let e=document.getElementById(`smsAccountSelect`),t=document.getElementById(`smsAccountsOverview`);if(e)try{let d=[],f=!1;try{let e=await(await fetch(`/api/federation/accounts`)).json();Array.isArray(e)&&e.length&&(d=e.map(e=>({id:e.id,phone:e.phone||e.phone_mask||``,nickname:e.identity_hint||e.id,platform:e.platform||``,is_local:e.is_local||e.owner_machine===window.location.hostname,owner_machine:e.owner_machine||e._source_machine_name||``,has_cookie:e._status===`logged_in`,has_identity:!!e.identity_dir,has_profile:!1,has_registry:!1,fans:e.fans||`?`,posts:e.posts||`?`,following:e.following||`?`,likes:e.likes||`?`,identity_dir:e.identity_dir||``,fingerprint:e.fingerprint||{},busy:e.busy||!1,busy_since:e.busy_since||``})),f=!0)}catch{}if(!f){let e=await(await fetch(`/api/matrix/sms/accounts`)).json();if(e.error){t&&(t.innerHTML=`<span style="color:var(--red)">❌ `+e.error+`</span>`);return}d=e.accounts||[]}window._lastSmsAccounts=d,e.innerHTML=`<option value="">— 选择账号 —</option>`+d.map(e=>`<option value="`+e.id+`" data-phone="`+(e.phone||``)+`" data-nick="`+(e.nickname||``)+`" data-display="`+((e.platform===`xiaohongshu`?`📕`:`🎵`)+` `+e.nickname+` `+(e.owner_machine||(e.is_local?`本机`:`远程`))+` (`+e.phone+`)`).replace(/"/g,`&quot;`)+`">`+((e.platform===`xiaohongshu`?`📕`:`🎵`)+` `+e.nickname+` `+(e.owner_machine||(e.is_local?`本机`:`远程`))+` (`+e.phone+`)`)+`</option>`).join(``),window._smsAccountOptions=d;try{(await(await fetch(`/api/matrix/personas`)).json()).personas}catch{}if(t){let e=e=>e.owner_machine||(e.is_local?`本机`:`远程`),f=e=>!e.is_local&&e.owner_machine,p=e=>e.busy||f(e),m=t=>t.busy?`忙碌中`:f(t)?`需在 `+e(t)+` 操作`:`登录`,h=t=>t.busy?`忙碌中`:f(t)?`需在 `+e(t)+` 操作`:`清除`,g=t=>t.busy?`忙碌中`:f(t)?`需在 `+e(t)+` 操作`:`删除`,_=(e,t)=>t?`opacity:.3;cursor:not-allowed`:`cursor:pointer`,v={};try{v=(await(await fetch(`/api/matrix/recordings/stats`)).json()).stats||{}}catch{}let y={};d.forEach(t=>{let n=e(t),r=t.phone||`未设置手机号`,i=n+`|`+r;y[i]||(y[i]={machine:n,phone:r,accts:[]}),y[i].accts.push(t)});var n=`<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:10px;margin-bottom:16px">`+Object.values(y).map(function(e){var t=e.accts,n=t.find(function(e){return(e.identity_dir||``).startsWith(`phone_`)})?.identity_dir||t.find(function(e){return e.has_identity})?.id||t[0]?.id,r=t.reduce(function(e,t){return e+(v[t.id]||0)},0),i=t.reduce(function(e,t){return e+ +!!t.has_cookie},0),a=function(e){if(!e||e===`?`||e===`-`)return`-`;var t=parseInt(e);return isNaN(t)?e:t>=1e4?(t/1e4).toFixed(1)+`w`:t>=1e3?(t/1e3).toFixed(1)+`k`:t},o=function(e){return e.has_cookie?`<span style="color:var(--green)">✅</span>`:`<span style="color:var(--text2)">❌</span>`};return`<div style="background:var(--bg2);border-radius:var(--radius);padding:10px;border:1px solid var(--border);box-shadow:var(--shadow)"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;font-size:12px"><div><strong>📱 `+e.phone+`</strong> <span style="font-size:10px;color:var(--text2);margin-left:4px">🆔 `+(n||``)+`</span></div><span style="font-size:10px;color:var(--text2)">🍪 `+i+`/`+t.length+`已登录 | 📦 `+r+`次录制</span></div><div style="font-size:10px;color:var(--primary);margin-bottom:6px">🖥️ `+e.machine+`</div><table style="width:100%;font-size:11px"><thead><tr style="color:var(--text2);font-size:10px"><th style="text-align:left;padding:2px 4px;font-weight:500">平台</th><th style="text-align:left;padding:2px 4px;font-weight:500">账号</th><th style="text-align:left;padding:2px 4px;font-weight:500">状态</th><th style="text-align:left;padding:2px 4px;font-weight:500">粉丝</th><th style="padding:2px 4px;font-weight:500">操作</th></tr></thead><tbody>`+t.map(function(e){var t=e.platform===`xiaohongshu`?`📕`:`🎵`,n=e.platform===`xiaohongshu`?`小红书`:`抖音`,r=p(e),i=r?``:`accountLogin('`+e.id+`')`,s=r?``:`clearCookies('`+e.id+`','`+e.platform+`')`,c=r?``:`deleteAccount('`+e.id+`')`;return`<tr><td style="padding:2px 4px">`+t+` `+n+`</td><td style="padding:2px 4px;color:var(--text)">`+e.nickname+`</td><td style="padding:2px 4px">`+o(e)+`</td><td style="padding:2px 4px;color:var(--text2)">`+a(e.fans)+`</td><td style="padding:2px 4px;white-space:nowrap"><button onclick="`+i+`" style="background:transparent;border:none;font-size:11px;`+_(e,r)+`" title="`+m(e)+`">🔑</button><button onclick="`+s+`" style="background:transparent;border:none;font-size:11px;`+_(e,r)+`" title="`+h(e)+`">🚫</button><button onclick="`+c+`" style="background:transparent;border:none;font-size:11px;`+_(e,r)+`" title="`+g(e)+`">🗑</button></td></tr>`}).join(``)+`</tbody></table><div style="margin-top:6px;display:flex;gap:4px;font-size:10px"><button onclick="loadSmsAccounts()" style="background:var(--bg3);border:1px solid var(--border);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px;color:var(--text)">🔄 刷新</button>`+(e.machine===`本机`||e.machine===window.location.hostname?`<button onclick="loginAllPlatforms('`+e.phone+`')" style="background:var(--bg3);border:1px solid var(--border);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px;color:var(--text)">🔄 全部登录</button><button onclick="collectAllPlatforms('`+e.phone+`')" style="background:var(--bg3);border:1px solid var(--border);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px;color:var(--text)">👤 全部采集</button><button onclick="deleteIdentityByPhone('`+e.phone+`')" style="background:rgba(220,38,38,.08);color:var(--red);border:1px solid var(--red);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">🗑 删除身份</button>`:`<span style="color:var(--text2);padding:3px 0">📡 操作需在 `+e.machine+` 上执行</span>`)+`</div></div>`}).join(``)+`</div>`,r={};d.forEach(function(e){e.phone&&(r[e.phone]=!0)});var i={};d.forEach(function(e){e.identity_dir&&(i[e.identity_dir]=!0)});var a=Object.keys(r).length,o=Object.keys(i).length,s=d.length,c=d.filter(function(e){return e.is_local}).length,l=d.filter(function(e){return e.has_cookie}).length,u=`<div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px;box-shadow:var(--shadow)"><div style="font-size:13px;font-weight:600;margin-bottom:6px">📋 全部账号列表</div><div style="display:flex;gap:12px;font-size:11px;color:var(--text2);margin-bottom:8px"><span>📱 <strong style="color:var(--text)">`+a+`</strong> 个手机号</span><span>🆔 <strong style="color:var(--text)">`+o+`</strong> 个身份</span><span>👤 <strong style="color:var(--text)">`+s+`</strong> 个账号</span><span>🎯 <strong style="color:var(--text)">`+c+`/`+s+`</strong> 本机</span><span>✅ <strong style="color:var(--green)">`+l+`</strong> 已登录</span></div><div style="display:flex;gap:6px;margin-bottom:8px"><input id="acctSearchInput" placeholder="🔍 搜索账号/手机/昵称..." oninput="filterAcctTable()" style="flex:1;min-width:150px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 10px;border-radius:5px;font-size:12px"><select id="acctPlatformFilter" onchange="filterAcctTable()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:5px;font-size:11px"><option value="">全部平台</option><option value="douyin">🎵 抖音</option><option value="xiaohongshu">📕 小红书</option></select><select id="acctMachineFilter" onchange="filterAcctTable()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:5px;font-size:11px"><option value="">全部机器</option><option value="local">本机</option><option value="remote">远程</option></select><select id="acctStatusFilter" onchange="filterAcctTable()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:5px;font-size:11px"><option value="">全部状态</option><option value="logged_in">已登录</option><option value="not_logged">未登录</option></select></div><div style="max-height:400px;overflow-y:auto"><table style="width:100%;font-size:12px"><thead><tr><th onclick="sortAcctTable(0)" style="cursor:pointer;text-align:left;padding:4px 6px;font-weight:500;font-size:11px;color:var(--text2);user-select:none">账号 <span style="font-size:9px">▲</span></th><th onclick="sortAcctTable(1)" style="cursor:pointer;text-align:left;padding:4px 6px;font-weight:500;font-size:11px;color:var(--text2);user-select:none">平台</th><th onclick="sortAcctTable(2)" style="cursor:pointer;text-align:left;padding:4px 6px;font-weight:500;font-size:11px;color:var(--text2);user-select:none">手机</th><th onclick="sortAcctTable(3)" style="cursor:pointer;text-align:left;padding:4px 6px;font-weight:500;font-size:11px;color:var(--text2);user-select:none">机器</th><th onclick="sortAcctTable(4)" style="cursor:pointer;text-align:center;padding:4px 6px;font-weight:500;font-size:11px;color:var(--text2);user-select:none">状态</th><th onclick="sortAcctTable(5)" style="cursor:pointer;text-align:left;padding:4px 6px;font-weight:500;font-size:11px;color:var(--text2);user-select:none">昵称</th><th style="padding:4px 6px;font-weight:500;font-size:11px;color:var(--text2)">操作</th></tr></thead><tbody id="acctTableBody">`+d.map(function(t,n){var r=e(t),i=t.platform===`xiaohongshu`?`📕`:`🎵`,a=t.platform===`xiaohongshu`?`小红书`:`抖音`,o=p(t),s=o?``:`accountLogin('`+t.id+`')`,c=o?``:`clearCookies('`+t.id+`','`+t.platform+`')`,l=o?``:`deleteAccount('`+t.id+`')`;return`<tr data-idx="`+n+`" data-phone="`+(t.phone||``)+`" data-platform="`+t.platform+`" data-machine="`+(t.is_local?`local`:`remote`)+`" data-login="`+(t.has_cookie?`yes`:`no`)+`" data-search="`+(t.id+` `+(t.phone||``)+` `+t.nickname).toLowerCase()+`"><td style="padding:3px 6px;font-size:11px">`+t.id+`</td><td style="padding:3px 6px;font-size:11px">`+i+` `+a+`</td><td style="padding:3px 6px;font-size:10px;color:var(--text2)">`+(t.phone||``)+`</td><td style="padding:3px 6px;font-size:10px;color:var(--primary)">`+r+`</td><td style="padding:3px 6px;text-align:center;font-size:11px">`+(t.has_cookie?`✅`:`❌`)+`</td><td style="padding:3px 6px;font-size:11px">`+t.nickname+`</td><td style="padding:3px 6px;white-space:nowrap;font-size:11px"><button onclick="`+s+`" style="background:transparent;border:none;cursor:pointer;`+_(t,o)+`" title="`+m(t)+`">🔑</button><button onclick="`+c+`" style="background:transparent;border:none;cursor:pointer;`+_(t,o)+`" title="`+h(t)+`">🚫</button><button onclick="`+l+`" style="background:transparent;border:none;cursor:pointer;`+_(t,o)+`" title="`+g(t)+`">🗑</button></td></tr>`}).join(``)+`</tbody></table></div></div>`;window._acctTableData=d,t.innerHTML=n+u}}catch(e){t&&(t.innerHTML=`<span style="color:var(--red)">❌ `+e.message+`</span>`)}}document.addEventListener(`click`,function(e){let t=document.getElementById(`smsAccountSelect`),n=document.getElementById(`smsAccountSearch`);t&&n&&!e.target.closest(`#smsAccountSearch`)&&!e.target.closest(`#smsAccountSelect`)&&(t.style.display=`none`)});function I(e){if(!e)return``;if(typeof e==`string`&&e.includes(`-`)){let t=e.split(` `);if(t.length>=2){let e=t[0].slice(5),n=t[1].slice(0,5);return e+` `+n}return e.slice(0,16)}return e}async function L(){let e=document.getElementById(`smsPhoneList`);if(e)try{let t=await(await fetch(`/api/matrix/accounts`)).json(),n=new Set;Object.values(t).forEach(e=>(e||[]).forEach(e=>{let t=e.phone||e.phone_mask||``;t&&t.length>=11&&n.add(t)})),e.innerHTML=[...n].map(e=>`<option value="${e}">`).join(``)}catch{}}async function R(){let e=document.getElementById(`smsConfigPanel`);if(e)try{let t=await(await fetch(`/api/matrix/sms/config`)).json();e.innerHTML=`<div style="margin-bottom:4px"><span style="color:var(--text2)">API:</span> <code>${(t.base_url||``).slice(0,35)}</code></div>
      <div style="margin-bottom:4px"><span style="color:var(--text2)">当前手机号:</span> <strong style="color:var(--green)">${t.phone||`-`}</strong></div>
      <div><span style="color:var(--text2)">Key:</span> <code>${t.api_key||`-`}</code> | 轮询 ${t.poll_interval||3}s</div>`,t.phone&&z(t.phone)}catch(t){e.innerHTML=`<span style="color:var(--red)">`+t.message+`</span>`}}async function z(e){let t=document.getElementById(`smsMessages`);if(!(!t||!e))try{let n=await(await fetch(`/api/matrix/sms/test/`+encodeURIComponent(e))).json();if(n.status!==`ok`)return;t.innerHTML=(n.messages||[]).map(e=>`<div style="padding:3px 0;border-bottom:1px solid var(--border);font-size:11px">
      ${e.code?`<span style="color:var(--green)">✅ `+e.code+`</span>`:`📩`}
      <span style="color:var(--text2);font-size:10px;margin-left:4px">${(e.content||``).slice(0,60)}</span>
      <span style="color:#6366f1;font-size:9px;float:right">${I(e.time)}</span>
    </div>`).join(``)||`<div style="color:var(--text2);font-size:11px;padding:4px 0">无短信记录</div>`}catch{}}async function B(){let e=document.getElementById(`proxyList`);if(e)try{let t=(await(await fetch(`/api/matrix/proxies`)).json()).proxies||[];if(!t.length){e.innerHTML=`<div style="color:var(--text2);font-size:12px">无本地账号</div>`;return}e.innerHTML=t.map(e=>`<div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:6px;font-size:12px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div><strong>${e.account}</strong> <span style="color:var(--text2);font-size:10px">${e.platform}</span>
          <span style="font-size:10px;margin-left:6px;color:${e.login_status===`logged_in`?`#22c55e`:e.login_status===`remote`?`#8b8fa3`:`#f59e0b`}">${e.login_status}</span>
        </div>
        <div><span style="color:${e.has_proxy?`#22c55e`:`#8b8fa3`};font-size:10px">${e.proxy||`无代理`}</span></div>
      </div>
      <div style="margin-top:4px;display:flex;gap:4px;align-items:center">
        <input placeholder="绑定代理地址" style="flex:1;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px" id="proxy_${e.account}">
        <button onclick="setProxy('${e.account}')" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">绑定</button>
        <button onclick="testAccountProxy('${e.account}')" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">测试</button>
        <span id="proxyResult_${e.account}" style="font-size:10px"></span>
      </div>
    </div>`).join(``)}catch(t){e.innerHTML=`<span style="color:var(--red)">`+t.message+`</span>`}}document.addEventListener(`keydown`,e=>{e.key===`Escape`&&closeDetail()});var V=[],pe=[],me=0,H=null,U={},W={},G=1;async function he(){let e=document.getElementById(`workflowContent`);e.innerHTML=`
  <div style="display:flex;flex-direction:column;height:calc(100vh - 180px);min-height:500px">
    <!-- 工具栏 -->
    <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;flex-shrink:0">
      <span style="font-size:14px;font-weight:600;color:var(--text)">🔀 工作流</span>
      <select id="wfTemplateSelect" onchange="wfLoadTemplate(this.value)"
        style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;font-size:12px;width:160px">
        <option value="">— 模板 —</option>
      </select>
      <div style="display:flex;gap:3px;flex-wrap:wrap;flex:1;overflow-x:auto;padding:2px 0" id="wfNodePalette"></div>
      <button onclick="wfRun()" style="background:var(--primary);border:none;color:#fff;padding:3px 12px;border-radius:4px;cursor:pointer;font-size:12px;white-space:nowrap">▶ 运行</button>
      <button onclick="wfClear()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:12px;white-space:nowrap">🗑 清空</button>
      <span id="wfRunStatus" style="font-size:11px;color:var(--text2);white-space:nowrap"></span>
    </div>
    <!-- 主体：画布 + 配置面板 -->
    <div style="display:flex;gap:8px;flex:1;min-height:0">
      <!-- 画布区 -->
      <div style="flex:1;position:relative;background:var(--bg3);border-radius:8px;overflow:hidden;border:1px solid var(--border)">
        <svg id="wfCanvas" width="100%" height="100%" style="cursor:grab;display:block"></svg>
        <div id="wfCanvasPlaceholder" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;color:var(--text2);font-size:13px;pointer-events:none">
          从上方拖拽节点到画布，或选择模板开始
        </div>
      </div>
      <!-- 配置面板 -->
      <div id="wfConfigPanel" style="width:300px;background:var(--bg2);border-radius:8px;border:1px solid var(--border);overflow-y:auto;flex-shrink:0">
        <div id="wfConfigContent" style="padding:14px;font-size:12px;color:var(--text2)">点击节点编辑配置</div>
      </div>
    </div>
  </div>`,await ge()}window.loadWorkflow=he;async function ge(){try{let[e,t]=await Promise.all([fetch(API+`/api/workflow/nodes`),fetch(API+`/api/workflow/templates`)]),n=await e.json(),r=await t.json();U={};for(let e of n.categories||[])for(let t of e.nodes||[])U[t]=e._defs?.[t]||{};W=r.templates||{}}catch{U={},W={}}ve(),ye(),we(),_e()}function _e(){let e=document.getElementById(`wfCanvas`);e&&(e.addEventListener(`dragover`,e=>e.preventDefault()),e.addEventListener(`drop`,t=>{t.preventDefault();let n=t.dataTransfer.getData(`text/plain`);if(!n||!U[n])return;let r=e.getBoundingClientRect(),i=(t.clientX-r.left-120)/G,a=(t.clientY-r.top-30)/G;be(n,Math.max(0,i),Math.max(0,a))}))}function ve(){let e=document.getElementById(`wfNodePalette`);e&&(e.innerHTML=Object.entries(U).map(([e,t])=>{let n=t.color||`#888`,r=t.icon||`●`;return`<div draggable="true" ondragstart="wfDragStart(event,'${e}')" title="${t.description||``}"
      style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;margin:1px;border-radius:4px;font-size:11px;cursor:grab;white-space:nowrap;background:${n}15;border:1px solid ${n}30;color:${n}">${r} ${t.label}</div>`}).join(``))}function ye(){let e=document.getElementById(`wfTemplateSelect`);e&&(e.innerHTML=`<option value="">— 选择模板 —</option>`+Object.entries(W).map(([e,t])=>`<option value="${e}">${t.name||e} ${t.cost||``}</option>`).join(``))}function K(){let e=document.getElementById(`wfCanvas`),t=document.getElementById(`wfCanvasPlaceholder`);if(!e)return;t.style.display=V.length===0?`flex`:`none`;let n=`<defs><marker id="wfArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M2 1L8 5L2 9" fill="none" stroke="#888" stroke-width="1.5"/></marker></defs>`;pe.forEach((e,t)=>{let r=V.find(t=>t.id===e.from),i=V.find(t=>t.id===e.to);if(r&&i){let e=r.x+120,t=r.y+30,a=i.x,o=i.y+30,s=(e+a)/2;n+=`<path d="M${e} ${t} C${s} ${t},${s} ${o},${a} ${o}" fill="none" stroke="#888" stroke-width="2" marker-end="url(#wfArrow)" opacity="0.6"/>`}}),V.forEach(e=>{let t=U[e.type]||{},r=t.color||`#888`;n+=`<g class="wf-node" data-id="${e.id}" onmousedown="wfNodeMouseDown(event,'${e.id}')" style="cursor:move">
      <rect x="${e.x}" y="${e.y}" width="240" height="60" rx="8" fill="var(--bg2)" stroke="${H===e.id?r:`var(--border)`}" stroke-width="${H===e.id?2:1}"/>
      <rect x="${e.x}" y="${e.y}" width="240" height="24" rx="8" fill="${r}" opacity="0.15"/>
      <text x="${e.x+12}" y="${e.y+17}" font-size="12" fill="${r}" font-weight="600">${t.icon||`●`} ${e.label||t.label||e.type}</text>
      <text x="${e.x+12}" y="${e.y+42}" font-size="10" fill="var(--text2)">${t.description||``}</text>
      ${(t.ports?.input||[]).map((t,n)=>`<circle cx="${e.x}" cy="${e.y+40+n*16}" r="5" fill="var(--bg3)" stroke="${r}" stroke-width="1.5" style="cursor:crosshair" onmousedown="wfConnStart(event,'${e.id}','${t}')" onmouseup="wfConnEnd(event,'${e.id}','${t}')"/>`).join(``)}
      ${(t.ports?.output||[]).map((t,n)=>`<circle cx="${e.x+240}" cy="${e.y+30+n*16}" r="5" fill="${r}" stroke="${r}" stroke-width="1.5" style="cursor:crosshair" onmousedown="wfConnStart(event,'${e.id}','${t}')" onmouseup="wfConnEnd(event,'${e.id}','${t}')"/>`).join(``)}
      <rect x="${e.x+200}" y="${e.y+4}" width="34" height="18" rx="4" fill="${r}" opacity="0.8" style="cursor:pointer" onclick="wfSelectNode('${e.id}')"/>
      <text x="${e.x+217}" y="${e.y+16}" font-size="9" fill="#fff" text-anchor="middle" style="cursor:pointer" onclick="wfSelectNode('${e.id}')">配置</text>
    </g>`}),e.innerHTML=n}function be(e,t,n){let r=`n`+ ++me,i=U[e]||{};V.push({id:r,type:e,label:i.label||e,config:JSON.parse(JSON.stringify(i.default_config||{})),x:t,y:n}),K(),xe(r)}function xe(e){H=e,K(),Y(e)}var Se={editor_mode:`编辑模式`,content:`脚本内容`,path:`文件路径`,type:`脚本格式`,parser:`解析方式`,strategy:`生产策略`,voice_id:`语音模型`,speed:`语速`,pitch:`音调`,provider:`供应商`,model:`模型版本`,duration:`时长(秒)`,seed:`随机种子`,source:`素材来源`,search_keyword:`搜索关键词`,count:`素材数量`,orientation:`画面方向`,style:`视觉风格`,color_grade:`色调`,mode:`模式`,mood:`情绪风格`,rhythm:`节奏强度`,bpm:`BPM`,volume:`音量`,duck_enabled:`自动避让`,registry_name:`选择角色`,outfit_preset:`服装预设`,use_reference_images:`传递参考图`,lip_sync:`唇形同步`,camera_style:`运镜风格`,transition:`转场方式`,scene_count:`场景数量`,output_format:`输出格式`,prompt_style:`提示词风格`,quality:`品质等级`,add_negative:`添加负面提示`,format:`字幕格式`,position:`字幕位置`,style:`字幕样式`,max_length:`每行最大字数`,format:`视频格式`,resolution:`分辨率`,output_path:`输出路径`,auto_open:`自动打开`,message:`审核提示`,auto_approve:`自动通过`,timeout_minutes:`超时(分钟)`,genre:`故事类型`,title:`故事标题`,adapt_style:`改编风格`},Ce={auto:`自动`,manual:`手动`,ai_generated:`AI生成`,turbo:`极速`,standard:`标准`,quality:`高品质`,kling:`可灵AI`,jimeng:`即梦`,wan:`万相`,pexels:`Pexels图库`,local:`本地文件`,upload:`上传`,portrait:`竖屏`,landscape:`横屏`,square:`方形`,cinematic:`电影感`,hyper_realistic:`超写实`,artistic:`艺术风`,anime:`动漫`,vintage:`复古`,warm:`暖调`,cool:`冷调`,neutral:`中性`,dramatic:`戏剧性`,monochrome:`黑白`,default:`默认`,casual:`休闲`,sport:`运动`,formal:`正式`,fantasy:`奇幻`,happy:`欢快`,sad:`伤感`,epic:`史诗`,calm:`平静`,tense:`紧张`,upbeat:`积极`,romantic:`浪漫`,inspiring:`激励`,healing:`治愈`,detailed:`详细描述`,simple:`简洁指令`,stepwise:`分步式`,json:`JSON格式`,yaml:`YAML格式`,md:`Markdown格式`,inline:`在线编辑`,path:`文件路径`,srt:`SRT格式`,ass:`ASS格式`,vtt:`VTT格式`,bottom:`底部`,top:`顶部`,white:`白色`,yellow:`黄色`,cyan:`青色`,hard:`硬切`,fade_in:`淡入`,fade_out:`淡出`,dissolve:`叠化`,slide:`划像`,cut:`跳切`,default:`默认`,running:`跑步装`,gym:`健身装`,basketball:`篮球装`,modern:`现代`,ancient:`古风`,sci_fi:`科幻`,mystery:`悬疑`,comedy:`喜剧`,detailed_adapt:`详细改编`,fast_extract:`快速提炼`,dialogue_first:`对白优先`},q=[],J={};async function we(){try{let e=await(await fetch(`${API}/api/characters`)).json(),t=e.characters||{},n=e.active||``;q=Object.keys(t).map(e=>({name:e,active:e===n})),J={};for(let[e,n]of Object.entries(t))J[e]=n}catch{q=[]}}function Y(e){let t=document.getElementById(`wfConfigContent`),n=V.find(t=>t.id===e);if(!n){t.innerHTML=`<div style="text-align:center;padding:40px 0;color:var(--text2);font-size:13px">点击节点编辑配置</div>`;return}let r=U[n.type]||{},i=n.config||{},a=r.default_config||{},o=r.color||`#888`,s=r.options_map||{},c=`<div style="margin-bottom:10px">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <span style="font-size:14px;font-weight:600">${r.icon||`●`} ${n.label}</span>
      <button onclick="wfDeleteNode('${n.id}')" style="background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:var(--red);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">删除</button>
    </div>
    <div style="font-size:10px;color:var(--text2);margin-top:4px">${r.description||``}</div>
  </div>`;for(let[e,t]of Object.entries(a)){let r=i[e]===void 0?t:i[e],a=Se[e]||e.replace(/_/g,` `).replace(/\b\w/g,e=>e.toUpperCase()),l=`wf_cfg_`+n.id+`_`+e,u=s[e];if(e===`registry_name`){let t=Array.isArray(q)?q:[];c+=`<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${a}</div>
        <select id="${l}" onchange="wfUpdateConfig('${n.id}','${e}',this.value)"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
          <option value="">— 请选择角色 —</option>
          ${t.map(e=>`<option value="${e.name}" ${String(r)===e.name?`selected`:``}>${e.name}${e.active?` (默认)`:``}</option>`).join(``)}
        </select>
      </div>`;continue}if(u&&Array.isArray(u)){c+=`<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${a}</div>
        <select id="${l}" onchange="wfUpdateConfig('${n.id}','${e}',this.value)"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
          ${u.map(e=>`<option value="${e}" ${String(r)===String(e)?`selected`:``}>${Ce[e]||e}</option>`).join(``)}
        </select>
      </div>`;continue}if(typeof u==`string`&&u.startsWith(`::number:`)){let t=u.split(`:`),i=t[1]||0,o=t[2]||100,s=t[3]||`any`;c+=`<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${a}</div>
        <input type="number" id="${l}" value="${r}" min="${i}" max="${o}" step="${s}"
          onchange="wfUpdateConfig('${n.id}','${e}',parseFloat(this.value))"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
      </div>`;continue}if(e===`content`&&typeof r==`string`&&r.length>50){c+=`<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${a}</div>
        <textarea id="${l}" rows="4" onchange="wfUpdateConfig('${n.id}','${e}',this.value)"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px;font-family:inherit;resize:vertical">${r}</textarea>
      </div>`;continue}if(typeof t==`boolean`){c+=`<div style="margin-bottom:6px;display:flex;align-items:center;gap:8px">
        <input type="checkbox" id="${l}" ${r?`checked`:``}
          onchange="wfUpdateConfig('${n.id}','${e}',this.checked)"
          style="accent-color:${o}">
        <label for="${l}" style="font-size:11px;color:var(--text2)">${a}</label>
      </div>`;continue}c+=`<div style="margin-bottom:6px">
      <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${a}</div>
      <input id="${l}" value="${r}" onchange="wfUpdateConfig('${n.id}','${e}',this.value)"
        style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
    </div>`}if(n.type===`character`&&i.registry_name){let e=J[i.registry_name];c+=`<div style="margin-top:12px;padding-top:10px;border-top:1px solid var(--border)">
      <div style="font-size:10px;color:var(--text2);margin-bottom:4px">📸 定妆照生成</div>
      ${e?`
        <div style="font-size:10px;color:var(--text2);margin-bottom:6px;background:var(--bg3);padding:6px 8px;border-radius:4px">
          <div>画风: ${e.art_style||`-`} | 性格: ${e.personality||`-`}</div>
          <div>${e.description?e.description.slice(0,60)+`...`:``}</div>
        </div>`:``}
      <div style="display:flex;gap:8px">
        <button onclick="wfGeneratePortrait()" style="background:#f97316;border:none;color:#fff;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px">🚀 一键生成</button>
        <span id="wfPortraitStatus" style="font-size:10px;color:var(--text2);display:flex;align-items:center">点击生成多角度+表情+网格定妆照</span>
      </div>
      <div id="wfPortraitResult" style="font-size:10px;color:var(--text2);margin-top:4px"></div>
    </div>`}t.innerHTML=c}var X=null;async function Te(){let e=document.getElementById(`capabilityContent`),t=document.getElementById(`capGroupTabs`),n=document.getElementById(`capCount`);e.innerHTML=`<div class="loading">加载原子能力...</div>`;try{let r=await(await fetch(`${API}/api/capabilities`)).json(),i=r.groups||[],a=r.matrix||[];if(n.textContent=`共 ${r.total_items||0} 个能力`,!i.length){e.innerHTML=`<div class="error" style="padding:40px">暂无能力数据</div>`;return}t.innerHTML=i.map((e,t)=>`<button class="btn ${t===0?`active`:``}" onclick="switchCapGroup(${t})" style="${t===0?`background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px`:`background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px`}">${e.name} (${e.items.length})</button>`).join(``),X=0,Ee(i[0],a)}catch(t){e.innerHTML=`<div class="error">❌ 加载失败: ${t.message}</div>`}}window.loadCapabilities=Te;function Ee(e,t){let n=document.getElementById(`capabilityContent`);if(!e||!e.items){n.innerHTML=`<div class="error">无数据</div>`;return}if(n.innerHTML=`<div class="chart-box">
    <div style="font-size:14px;font-weight:600;margin-bottom:12px">${e.name}</div>
    <table><thead><tr>${Object.keys(e.items[0]||{}).map(e=>`<th>${e}</th>`).join(``)}</tr></thead><tbody>
      ${e.items.map(e=>`<tr>${Object.values(e).map(e=>`<td>${e||`-`}</td>`).join(``)}</tr>`).join(``)}
    </tbody></table>
  </div>`,t&&t.length&&X===0){let e=Object.keys(t[0]?.usages||{});n.innerHTML+=`<div class="chart-box" style="margin-top:16px">
      <div style="font-size:14px;font-weight:600;margin-bottom:12px">交叉能力矩阵 (全量)</div>
      <div style="font-size:11px;color:var(--text2);margin-bottom:8px">⬛ = 核心依赖 · ⬜ = 可用 · ↔ = 可选接入</div>
      <table><thead><tr><th style="position:sticky;left:0;background:var(--bg2)">能力</th>${e.map(e=>`<th style="font-size:10px">${e}</th>`).join(``)}</tr></thead><tbody>
        ${t.map(t=>`<tr><td style="position:sticky;left:0;background:var(--bg2);font-weight:600;white-space:nowrap">${t.name}</td>${e.map(e=>{let n=t.usages[e]||``;return`<td style="text-align:center;background:${n.includes(`⬛`)?`rgba(99,102,241,.15)`:n.includes(`↔`)?`rgba(245,158,11,.1)`:n?`rgba(34,197,94,.08)`:``};font-size:11px">${n||`-`}</td>`}).join(``)}</tr>`).join(``)}
      </tbody></table>
    </div>`}}var Z=null;async function Q(){let e=document.getElementById(`machineBar`);if(e)try{let n=await(await fetch(`/api/federation/health`)).json();try{n.chengzigedeAir=await(await fetch(`/api/health`)).json()}catch{}let r=(await(await fetch(`/api/machines`)).json()).machines||[],i={chengzigedeAir:{label:`主控`,icon:`🖥️`},"5kechengdeAir":{label:`养号`,icon:`🖥️`},"7kecheng":{label:`养号`,icon:`🖥️`}},a=`<div style="display:flex;gap:8px;flex-wrap:wrap">`;for(let[e,o]of Object.entries(i)){let i=n[e]||{},s=i.status===`ok`,c=r.find(function(t){return t.hostname===e||t.hostname===i.hostname}),l=`offline`,u=`离线`;s&&(l=`online`,u=`在线`,c&&c.current_task&&(l=`busy`,u=`忙碌`));var t=l===`online`?`var(--green)`:l===`busy`?`var(--amber)`:`var(--text2)`;a+=`<div style="display:flex;align-items:center;gap:5px;padding:5px 10px;border-radius:6px;background:var(--bg2);border:1px solid var(--border);font-size:12px;opacity:`+(l===`offline`?`0.3`:`1`)+`"><span style="width:8px;height:8px;border-radius:50%;background:`+t+`"></span><span style="font-weight:600;color:var(--text)">`+e+`</span><span style="font-size:10px;color:var(--text2)">`+o.label+`</span><span style="font-size:10px;color:`+t+`">`+u+`</span></div>`}a+=`</div>`,e.innerHTML=a}catch{}}function $(){Z&&clearInterval(Z),Q(),Z=setInterval(Q,3e4)}document.readyState===`complete`?$():window.addEventListener(`load`,$);
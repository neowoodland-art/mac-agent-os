import"./index-BfayR3mR.js";var e=null;async function t(e){e.innerHTML=n(),r(e),p(),g(),_()}function n(){return`
  <div style="padding:12px;font-size:12px;color:var(--text)">
    <!-- Tab 栏 -->
    <div style="display:flex;gap:0;margin-bottom:10px;border-bottom:1px solid var(--border)">
      <div class="collect-tab active" data-tab="run" style="padding:6px 14px;cursor:pointer;border-bottom:2px solid #6366f1;font-weight:600;font-size:12px">📡 新建抓取</div>
      <div class="collect-tab" data-tab="sources" style="padding:6px 14px;cursor:pointer;color:var(--text2);font-size:12px">📋 抓取源</div>
      <div class="collect-tab" data-tab="history" style="padding:6px 14px;cursor:pointer;color:var(--text2);font-size:12px">📜 历史</div>
      <div style="flex:1"></div>
      <div id="collectStats" style="padding:6px 14px;font-size:10px;color:var(--text2);font-family:monospace"></div>
    </div>

    <!-- Tab: 新建抓取 -->
    <div id="collectTabRun" class="collect-tab-content">

      <!-- 输入区 -->
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border);margin-bottom:8px">
        <div style="display:flex;gap:6px;margin-bottom:6px;flex-wrap:wrap;align-items:center">
          <input id="ciTarget" type="text" placeholder="输入 sec_uid / URL / 关键词" style="flex:1;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:12px">
          <button id="ciBatchBtn" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 8px;border-radius:4px;cursor:pointer;font-size:10px">📋 批量导入</button>
          <button id="ciResolveBtn" style="background:var(--bg3);color:var(--text2);border:1px solid var(--border);padding:4px 8px;border-radius:4px;cursor:pointer;font-size:10px">🔍 解析</button>
        </div>
        <textarea id="ciBatchInput" style="display:none;width:100%;height:60px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:4px;font-size:11px;font-family:monospace;margin-bottom:4px" placeholder="每行一个 URL / sec_uid"></textarea>

        <!-- 选项行 -->
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:10px;color:var(--text2)">
            工具:
            <select id="ciToolLevel" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px">
              <option value="1">Level 1: OpenCLI</option>
              <option value="2" selected>Level 2: OpenCLI → Chrome</option>
              <option value="3">Level 3: OpenCLI → Chrome → Web</option>
            </select>
          </label>
          <label style="font-size:10px;color:var(--text2)">
            <input type="checkbox" id="ciDeep"> 深度分析(L2)
          </label>
          <label style="font-size:10px;color:var(--text2)">
            机器:
            <select id="ciMachine" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px">
              <option value="">本机</option>
              <option value="all">所有机器</option>
              <!-- 远程机器由 API 动态填充 -->
            </select>
          </label>
          <button id="ciExecBtn" style="background:#22c55e;color:#000;border:none;padding:4px 14px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 执行</button>
          <span id="ciStatus" style="font-size:10px;color:var(--text2);font-family:monospace"></span>
        </div>
      </div>

      <!-- 日志区 -->
      <div id="ciLog" style="background:var(--bg2);border-radius:8px;padding:6px;border:1px solid var(--border);max-height:200px;overflow-y:auto;font-family:monospace;font-size:10px;white-space:pre-wrap;margin-bottom:8px;display:none"></div>

      <!-- 结果区 -->
      <div id="ciResults" style="background:var(--bg2);border-radius:8px;padding:8px;border:1px solid var(--border);display:none">
        <div id="ciResultMeta" style="font-size:10px;color:var(--text2);margin-bottom:6px"></div>
        <div id="ciResultTable" style="overflow-x:auto"></div>
      </div>
    </div>

    <!-- Tab: 抓取源 -->
    <div id="collectTabSources" class="collect-tab-content" style="display:none">
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border)">
        <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;align-items:center">
          <input id="csTarget" type="text" placeholder="sec_uid / URL" style="flex:1;min-width:150px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
          <select id="csPlatform" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 4px;border-radius:3px;font-size:10px">
            <option value="douyin">🎵 抖音</option>
            <option value="xiaohongshu">📕 小红书</option>
          </select>
          <select id="csType" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 4px;border-radius:3px;font-size:10px">
            <option value="user">用户主页</option>
            <option value="keyword">关键词</option>
          </select>
          <input id="csName" type="text" placeholder="显示名称" style="width:120px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
          <button id="csAddBtn" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">➕ 添加</button>
        </div>
        <div id="csList" style="font-size:11px"></div>
      </div>
    </div>

    <!-- Tab: 历史 -->
    <div id="collectTabHistory" class="collect-tab-content" style="display:none">
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border)">
        <div id="chList" style="font-size:11px"></div>
      </div>
    </div>
  </div>`}function r(e){e.querySelectorAll(`.collect-tab`).forEach(e=>{e.addEventListener(`click`,()=>i(e.dataset.tab))});let t=document.getElementById(`ciBatchBtn`);t&&t.addEventListener(`click`,()=>{let e=document.getElementById(`ciBatchInput`);e&&(e.style.display=e.style.display===`none`?`block`:`none`)});let n=document.getElementById(`ciResolveBtn`);n&&n.addEventListener(`click`,c);let r=document.getElementById(`ciExecBtn`);r&&r.addEventListener(`click`,l);let a=document.getElementById(`csAddBtn`);a&&a.addEventListener(`click`,h),m()}function i(e){document.querySelectorAll(`.collect-tab`).forEach(t=>{t.style.borderBottom=t.dataset.tab===e?`2px solid #6366f1`:`2px solid transparent`,t.style.fontWeight=t.dataset.tab===e?`600`:`400`,t.style.color=t.dataset.tab===e?`var(--text)`:`var(--text2)`}),document.querySelectorAll(`.collect-tab-content`).forEach(e=>{e.style.display=`none`});let t=document.getElementById(`collectTab`+e.charAt(0).toUpperCase()+e.slice(1));t&&(t.style.display=`block`),e===`sources`&&g(),e===`history`&&_()}function a(e){let t=document.getElementById(`ciLog`);t&&(t.style.display=`block`,t.textContent+=e+`
`,t.scrollTop=t.scrollHeight)}function o(){let e=document.getElementById(`ciLog`);e&&(e.textContent=``,e.style.display=`none`)}function s(){let e=document.getElementById(`ciTarget`)?.value.trim(),t=document.getElementById(`ciBatchInput`)?.value.trim();return t?t.split(`
`).map(e=>e.trim()).filter(Boolean):e?[e]:[]}async function c(){let e=s();if(!e.length){alert(`请先输入目标`);return}try{let t=await(await fetch(`/api/scrape/resolve`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({targets:e})})).json();if(t.status!==`ok`){alert(`❌ `+(t.message||`解析失败`));return}a(t.data.map(e=>`${e.status===`resolved`?`✅`:`❌`} ${e.input.slice(0,40)} → ${e.platform}/${e.type}: ${e.target_id||`?`}`).join(`
`))}catch(e){a(`❌ 解析失败: `+e.message)}}async function l(){let e=s();if(!e.length){alert(`请先输入目标`);return}let t=document.getElementById(`ciStatus`),n=parseInt(document.getElementById(`ciToolLevel`)?.value||`2`),r=document.getElementById(`ciDeep`)?.checked?`deep`:`light`,i=document.getElementById(`ciMachine`)?.value||``,c=e.length>10;o(),a(`🚀 开始抓取: ${e.length} 个目标 (L${n}, ${r}, 机器:${i||`本机`})`),t&&(t.textContent=`⏳ 执行中...`);try{let o=await(await fetch(`/api/scrape/run`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({targets:e,tool_level:n,depth:r,machine:i,async_mode:c})})).json();if(o.status===`error`){a(`❌ `+o.message),t&&(t.textContent=`❌ 失败`);return}if(o.status===`async`){t&&(t.textContent=`⏳ 异步任务 ${o.run_id} (${o.total} 个目标)`),a(`⏳ 异步任务已创建: ${o.run_id}`),u(o.run_id,t);return}t&&(t.textContent=`✅ 完成 (${o.duration}s, ${o.success}/${o.total})`),a(`✅ 抓取完成: ${o.duration}s, ${o.success} 成功, ${o.errors?.length||0} 错误`),d(o.data||[],o)}catch(e){a(`❌ `+e.message),t&&(t.textContent=`❌ 异常`)}}async function u(t,n){e&&clearInterval(e);let r=0;e=setInterval(async()=>{r++;try{let r=await(await fetch(`/api/scrape/result?run_id=${t}`)).json();if(r.status!==`ok`)return;let i=r.data;if(!i||i.status===`running`){n&&(n.textContent=`⏳ 进行中: ${i?.completed||0}/${i?.total||`?`}`);return}clearInterval(e),e=null,n&&(n.textContent=`✅ 完成 (${i.results?.length||0}/${i.total})`),a(`✅ 异步任务完成: ${i.results?.length||0} 成功, ${i.errors?.length||0} 错误`),d(i.results||[],i)}catch{r>30&&(clearInterval(e),e=null,n&&(n.textContent=`❌ 轮询超时`),a(`❌ 异步任务轮询超时`))}},2e3)}function d(e,t){let n=document.getElementById(`ciResults`),r=document.getElementById(`ciResultMeta`),i=document.getElementById(`ciResultTable`);if(!n||!r||!i)return;if(!e||!e.length){r.textContent=`⚠️ 没有抓取到任何内容`,n.style.display=`block`,i.innerHTML=``;return}r.textContent=`共 ${e.length} 条内容${t?.duration?` | 耗时 `+t.duration+`s`:``}`,n.style.display=`block`;let a=`<table style="width:100%;border-collapse:collapse;font-size:10px">
    <thead><tr style="background:var(--bg3);color:var(--text2);text-align:left">
      <th style="padding:3px 4px">#</th>
      <th style="padding:3px 4px">平台</th>
      <th style="padding:3px 4px">标题</th>
      <th style="padding:3px 4px">作者</th>
      <th style="padding:3px 4px">👍</th>
      <th style="padding:3px 4px">💬</th>
      <th style="padding:3px 4px">发布时间</th>
      <th style="padding:3px 4px">操作</th>
    </tr></thead><tbody>`;e.forEach((e,t)=>{let n=e.platform===`douyin`?`🎵`:e.platform===`xiaohongshu`?`📕`:e.platform===`bilibili`?`📺`:`🌐`,r=e.item_id||e.id||t,i=(e.title||`无标题`).slice(0,50),o=e.author_name?.slice(0,15)||`?`,s=e.stats?.likes??e.likes??`?`,c=e.stats?.comments??e.comment_count??e.comments??`?`,l=(e.published_at||``).slice(0,10),u=e.url||`#`;a+=`<tr style="border-bottom:1px solid var(--border)">
      <td style="padding:3px 4px;color:var(--text2)">${t+1}</td>
      <td style="padding:3px 4px">${n}</td>
      <td style="padding:3px 4px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${i}">
        <a href="${u}" target="_blank" style="color:var(--primary);text-decoration:none">${i}</a>
      </td>
      <td style="padding:3px 4px;color:var(--text2)">${o}</td>
      <td style="padding:3px 4px">${s}</td>
      <td style="padding:3px 4px">${c}</td>
      <td style="padding:3px 4px;color:var(--text2)">${l}</td>
      <td style="padding:3px 4px">
        <button class="ci-comment-btn" data-item-id="${r}" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:1px 5px;border-radius:3px;cursor:pointer;font-size:9px">💬</button>
        ${e.media?.[0]?.url?`<button class="ci-dl-btn" data-url="${e.media[0].url}" style="background:var(--bg3);color:var(--text2);border:1px solid var(--border);padding:1px 5px;border-radius:3px;cursor:pointer;font-size:9px">⬇</button>`:``}
      </td>
    </tr>`}),a+=`</tbody></table>`,i.innerHTML=a,i.querySelectorAll(`.ci-comment-btn`).forEach(e=>{e.addEventListener(`click`,()=>f(e.dataset.itemId))}),i.querySelectorAll(`.ci-dl-btn`).forEach(e=>{e.addEventListener(`click`,()=>{navigator.clipboard?.writeText(e.dataset.url),e.textContent=`✅`,setTimeout(()=>{e.textContent=`⬇`},2e3)})})}async function f(e){try{let t=await(await fetch(`/api/scrape/items/${e}`)).json();if(t.status!==`ok`){alert(`❌ 加载评论失败`);return}let n=t.data?.comments||[];if(!n.length){alert(`暂无评论`);return}let r=n.map((e,t)=>`<div style="padding:4px 0;border-bottom:1px solid var(--border);font-size:11px">
        <b>${e.author_name||`匿名`}</b>
        <span style="color:var(--text2);float:right">👍 ${e.likes||0}</span>
        <div style="color:var(--text);margin-top:2px">${e.text||``}</div>
      </div>`).join(``),i=document.createElement(`div`);i.style.cssText=`position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center`,i.innerHTML=`<div style="background:var(--bg2);border-radius:10px;padding:16px;max-width:500px;width:80%;max-height:80vh;overflow-y:auto;border:1px solid var(--border)"><div style="font-weight:600;font-size:13px;margin-bottom:8px">💬 评论区</div>${r}<div style="text-align:center;margin-top:8px"><button class="ci-close-overlay" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 12px;border-radius:4px;cursor:pointer">关闭</button></div></div>`,document.body.appendChild(i),i.querySelector(`.ci-close-overlay`).addEventListener(`click`,()=>i.remove()),i.addEventListener(`click`,e=>{e.target===i&&i.remove()})}catch(e){alert(`❌ `+e.message)}}async function p(){let e=document.getElementById(`collectStats`);if(e)try{let t=await(await fetch(`/api/scrape/stats`)).json();t.total!==void 0&&(e.textContent=`📊 ${t.total} 条内容 | 今日 +${t.today} | ${t.sources||0} 源`)}catch{}}async function m(){let e=document.getElementById(`ciMachine`);if(e)try{let t=await(await fetch(`/api/ops/machines`)).json();t.machines&&t.machines.forEach(t=>{if(t.name&&t.name!==`local`){let n=document.createElement(`option`);n.value=t.name,n.textContent=`🖥 ${t.name}`,e.appendChild(n)}})}catch{}}async function h(){let e=document.getElementById(`csTarget`)?.value.trim(),t=document.getElementById(`csPlatform`)?.value,n=document.getElementById(`csType`)?.value,r=document.getElementById(`csName`)?.value.trim()||e;if(!e){alert(`请填写目标`);return}try{let i=await(await fetch(`/api/scrape/sources`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({platform:t,source_type:n,target:e,display_name:r})})).json();if(i.status!==`ok`){alert(`❌ `+(i.message||`添加失败`));return}document.getElementById(`csTarget`).value=``,document.getElementById(`csName`).value=``,g()}catch(e){alert(`❌ `+e.message)}}async function g(){let e=document.getElementById(`csList`);if(e)try{let t=await(await fetch(`/api/scrape/sources`)).json();if(t.status!==`ok`){e.textContent=`❌ 加载失败`;return}let n=t.data||[];if(!n.length){e.innerHTML=`<div style="color:var(--text2);padding:10px;text-align:center">暂无抓取源</div>`;return}e.innerHTML=n.map(e=>`<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 6px;border-bottom:1px solid var(--border)">
        <span>${e.display_name||e.target} <span style="color:var(--text2);font-size:9px">(${e.platform}/${e.source_type})</span></span>
        <span style="font-size:9px;color:var(--text2)">${e.last_collected?`上次: `+e.last_collected.slice(0,10):`未抓取`} <button class="cs-del-btn" data-id="${e.id}" style="background:var(--bg3);color:var(--red);border:1px solid var(--border);padding:1px 6px;border-radius:3px;cursor:pointer;font-size:9px">🗑</button></span>
      </div>`).join(``),e.querySelectorAll(`.cs-del-btn`).forEach(e=>{e.addEventListener(`click`,async()=>{if(confirm(`删除此抓取源？`))try{await fetch(`/api/scrape/sources/${e.dataset.id}`,{method:`DELETE`}),g()}catch(e){alert(`❌ `+e.message)}})})}catch(t){e.textContent=`❌ `+t.message}}async function _(){let e=document.getElementById(`chList`);if(e)try{let t=await(await fetch(`/api/scrape/tasks?limit=30`)).json();if(t.status!==`ok`){e.textContent=`❌ 加载失败`;return}let n=t.data||[];if(!n.length){e.innerHTML=`<div style="color:var(--text2);padding:10px;text-align:center">暂无抓取历史</div>`;return}let r=`<table style="width:100%;border-collapse:collapse;font-size:10px">
      <thead><tr style="background:var(--bg3);color:var(--text2);text-align:left">
        <th style="padding:3px 4px">时间</th>
        <th style="padding:3px 4px">类型</th>
        <th style="padding:3px 4px">目标</th>
        <th style="padding:3px 4px">状态</th>
        <th style="padding:3px 4px">结果</th>
      </tr></thead><tbody>`;n.forEach(e=>{let t=e.status===`completed`?`✅`:e.status===`failed`?`❌`:e.status===`running`?`⏳`:`⏸`;r+=`<tr style="border-bottom:1px solid var(--border)">
        <td style="padding:3px 4px;color:var(--text2)">${(e.created_at||``).slice(0,16)}</td>
        <td style="padding:3px 4px">${e.platform||`auto`}</td>
        <td style="padding:3px 4px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${(e.target||``).slice(0,40)}</td>
        <td style="padding:3px 4px">${t} ${e.status}</td>
        <td style="padding:3px 4px;color:var(--text2);font-size:9px">${e.completed_targets||0}/${e.total_targets||0}</td>
      </tr>`}),r+=`</tbody></table>`,e.innerHTML=r}catch(t){e.textContent=`❌ `+t.message}}export{t as loadView};
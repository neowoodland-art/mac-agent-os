import{r as e,t}from"./index-Cb71sUyt.js";e(`collect`);async function n(e){e.innerHTML=`
    <div style="padding:20px;max-width:1200px;margin:0 auto">
      <h2 style="margin-bottom:16px">📡 内容采集</h2>

      <!-- 采集输入 -->
      <div style="background:var(--bg2);border-radius:10px;padding:16px;margin-bottom:16px">
        <div style="font-size:13px;font-weight:600;margin-bottom:8px">新建采集任务</div>
        <textarea id="collectTargets" rows="4"
          placeholder="输入 URL / sec_uid / 关键词，每行一个&#10;支持抖音视频链接、用户主页链接、短链等"
          style="width:100%;padding:8px;border-radius:6px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:12px;resize:vertical"></textarea>

        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:10px;align-items:center">
          <label style="font-size:12px">深度:
            <select id="collectDepth" style="margin-left:4px;padding:4px 8px;border-radius:4px;background:var(--bg3);color:var(--text);border:1px solid var(--border);font-size:12px">
              <option value="light">轻量采集（L1）</option>
              <option value="deep">深度分析（L2）</option>
            </select>
          </label>
          <label style="font-size:12px">工具:
            <select id="collectToolLevel" style="margin-left:4px;padding:4px 8px;border-radius:4px;background:var(--bg3);color:var(--text);border:1px solid var(--border);font-size:12px">
              <option value="1">Level 1: OpenCLI 仅</option>
              <option value="2" selected>Level 2: OpenCLI → 浏览器</option>
              <option value="3">Level 3: OpenCLI → 浏览器 → 网页抓取</option>
            </select>
          </label>
          <label style="font-size:12px">
            <input type="checkbox" id="collectMultiMachine" style="margin-right:4px">多机协同
          </label>
          <label style="font-size:12px">
            <input type="checkbox" id="collectAsyncMode" style="margin-right:4px">异步执行（大量目标）
          </label>
          <button id="collectResolveBtn" class="btn btn-secondary" style="font-size:12px">🔍 解析</button>
          <button id="collectRunBtn" class="btn btn-primary" style="font-size:12px">🚀 执行采集</button>
        </div>
      </div>

      <!-- 解析预览 -->
      <div id="collectResolvePreview" style="display:none;background:var(--bg2);border-radius:10px;padding:16px;margin-bottom:16px">
        <div style="font-size:13px;font-weight:600;margin-bottom:8px">解析结果</div>
        <div id="collectResolveTable"></div>
      </div>

      <!-- 执行结果 -->
      <div id="collectResult" style="display:none;background:var(--bg2);border-radius:10px;padding:16px;margin-bottom:16px">
        <div style="font-size:13px;font-weight:600;margin-bottom:8px">采集结果</div>
        <div id="collectResultContent"></div>
      </div>

      <!-- 采集历史 -->
      <div style="background:var(--bg2);border-radius:10px;padding:16px">
        <div style="font-size:13px;font-weight:600;margin-bottom:8px">
          最近采集
          <button id="collectRefreshHistory" style="margin-left:8px;padding:2px 8px;border-radius:4px;background:var(--bg3);border:1px solid var(--border);cursor:pointer;font-size:11px">⟳ 刷新</button>
        </div>
        <div id="collectHistoryList"><div class="loading">加载中...</div></div>
      </div>
    </div>
  `,document.getElementById(`collectResolveBtn`).onclick=r,document.getElementById(`collectRunBtn`).onclick=i,document.getElementById(`collectRefreshHistory`).onclick=o,o()}async function r(){let e=document.getElementById(`collectTargets`).value.trim();if(!e)return alert(`请先输入目标`);let n=e.split(`
`).filter(e=>e.trim());try{let e=await t(`/collect/resolve`,{method:`POST`,body:JSON.stringify({targets:n})});if(e.status!==`ok`)return alert(e.message||`解析失败`);let r=document.getElementById(`collectResolvePreview`);r.style.display=`block`;let i=document.getElementById(`collectResolveTable`);if(!e.data||e.data.length===0){i.innerHTML=`<div style="color:var(--red);font-size:12px">❌ 无法解析任何目标</div>`;return}let a=`<table style="width:100%;font-size:11px;border-collapse:collapse">
      <tr style="background:var(--bg3)">
        <th style="padding:6px 8px;text-align:left">输入</th>
        <th style="padding:6px 8px;text-align:left">平台</th>
        <th style="padding:6px 8px;text-align:left">类型</th>
        <th style="padding:6px 8px;text-align:left">目标ID</th>
        <th style="padding:6px 8px;text-align:left">状态</th>
      </tr>`;for(let e of e.data){let t=e.status===`resolved`?`✅`:e.status===`pending`?`⏳`:`❌`;a+=`<tr>
        <td style="padding:4px 8px;max-width:200px;overflow:hidden;text-overflow:ellipsis">${s(e.input)}</td>
        <td style="padding:4px 8px">${e.platform||`-`}</td>
        <td style="padding:4px 8px">${e.type||`-`}</td>
        <td style="padding:4px 8px;font-family:monospace">${e.target_id||`-`}</td>
        <td style="padding:4px 8px">${t}</td>
      </tr>`}a+=`</table>`,i.innerHTML=a}catch(e){alert(`解析失败: `+e.message)}}async function i(){let e=document.getElementById(`collectTargets`).value.trim();if(!e)return alert(`请先输入目标`);let n=e.split(`
`).filter(e=>e.trim()),r=document.getElementById(`collectDepth`).value,i=parseInt(document.getElementById(`collectToolLevel`).value),s=document.getElementById(`collectMultiMachine`).checked,c=document.getElementById(`collectAsyncMode`).checked,l=document.getElementById(`collectResult`),u=document.getElementById(`collectResultContent`);l.style.display=`block`,u.innerHTML=`<div class="loading">⏳ 采集中...</div>`;try{let e=await t(`/collect/run`,{method:`POST`,body:JSON.stringify({targets:n,depth:r,tool_level:i,multi_machine:s,async_mode:c})});if(e.status!==`ok`){u.innerHTML=`<div style="color:var(--red);font-size:12px">❌ ${e.message||`采集失败`}</div>`;return}if(e.status===`async`){u.innerHTML=`<div style="font-size:12px">
        ✅ 异步任务已创建 (ID: ${e.run_id})<br>
        目标数: ${e.total}<br>
        <span style="color:var(--text2)">结果将稍后可用</span>
      </div>`;return}a(u,e),o()}catch(e){u.innerHTML=`<div style="color:var(--red);font-size:12px">❌ ${e.message}</div>`}}function a(e,t){let n=t.data||[],r=t.errors||[],i=`<div style="font-size:12px;margin-bottom:10px;color:var(--text2)">
    共 ${t.total} 个目标 | ✅ 成功 ${t.success} | ❌ 失败 ${r.length} | ⏱ ${t.duration}s
  </div>`;if(n.length===0){i+=`<div style="font-size:12px;color:var(--text2)">无采集结果</div>`,e.innerHTML=i;return}i+=`<table style="width:100%;font-size:11px;border-collapse:collapse">
    <tr style="background:var(--bg3)">
      <th style="padding:6px 8px;text-align:left">#</th>
      <th style="padding:6px 8px;text-align:left">标题</th>
      <th style="padding:6px 8px;text-align:left">作者</th>
      <th style="padding:6px 8px;text-align:right">❤️</th>
      <th style="padding:6px 8px;text-align:right">评论</th>
      <th style="padding:6px 8px;text-align:left">时间</th>
      <th style="padding:6px 8px;text-align:left">操作</th>
    </tr>`,n.forEach((e,t)=>{let n=e.stats||{};i+=`<tr>
      <td style="padding:4px 8px">${t+1}</td>
      <td style="padding:4px 8px;max-width:250px;overflow:hidden;text-overflow:ellipsis" title="${s(e.title)}">${s(c(e.title,40))}</td>
      <td style="padding:4px 8px">${s(e.author_name||`-`)}</td>
      <td style="padding:4px 8px;text-align:right">${n.likes??`-`}</td>
      <td style="padding:4px 8px;text-align:right">${n.comments??`-`}</td>
      <td style="padding:4px 8px;font-size:10px">${e.published_at?e.published_at.slice(0,10):`-`}</td>
      <td style="padding:4px 8px">
        <button class="collect-view-detail" data-id="${e.item_id||``}" style="padding:2px 6px;border-radius:4px;background:var(--bg3);border:1px solid var(--border);cursor:pointer;font-size:10px">详情</button>
      </td>
    </tr>`}),i+=`</table>`,e.innerHTML=i,e.querySelectorAll(`.collect-view-detail`).forEach(e=>{e.onclick=()=>{let t=e.dataset.id,r=n.find(e=>e.item_id===t);r&&alert([`标题: ${r.title}`,`作者: ${r.author_name}`,`链接: ${r.url}`,`点赞: ${r.stats?.likes??`-`} 评论: ${r.stats?.comments??`-`}`,r.media?.length?`下载链接: ${r.media[0]?.url||`-`}`:``].filter(Boolean).join(`
`))}})}async function o(){let e=document.getElementById(`collectHistoryList`);if(e)try{let n=await t(`/collect/tasks?limit=20`);if(n.status!==`ok`){e.innerHTML=`<div style="font-size:12px;color:var(--red)">加载失败</div>`;return}let r=n.data||[];if(r.length===0){e.innerHTML=`<div style="font-size:12px;color:var(--text2)">暂无采集记录</div>`;return}let i=`<table style="width:100%;font-size:11px;border-collapse:collapse"><tr style="background:var(--bg3)"><th style="padding:6px 8px;text-align:left">时间</th><th style="padding:6px 8px;text-align:left">平台</th><th style="padding:6px 8px;text-align:left">目标</th><th style="padding:6px 8px;text-align:left">状态</th><th style="padding:6px 8px;text-align:right">数量</th></tr>`;for(let e of r){let t=e.status===`completed`?`✅`:e.status===`running`?`⏳`:`❌`;i+=`<tr>
        <td style="padding:4px 8px;font-size:10px">${e.created_at||`-`}</td>
        <td style="padding:4px 8px">${e.platform||`-`}</td>
        <td style="padding:4px 8px;max-width:150px;overflow:hidden;text-overflow:ellipsis">${s(c(e.target,30))}</td>
        <td style="padding:4px 8px">${t} ${e.status}</td>
        <td style="padding:4px 8px;text-align:right">${e.total_targets||`-`}</td>
      </tr>`}i+=`</table>`,e.innerHTML=i}catch(t){e.innerHTML=`<div style="font-size:12px;color:var(--red)">❌ ${t.message}</div>`}}function s(e){return typeof e==`string`?e.replace(/&/g,`&amp;`).replace(/</g,`&lt;`).replace(/>/g,`&gt;`).replace(/"/g,`&quot;`):e??``}function c(e,t){return typeof e==`string`?e.length>t?e.slice(0,t)+`...`:e:e??``}export{n as loadView};
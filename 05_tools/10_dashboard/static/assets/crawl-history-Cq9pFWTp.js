async function e(n){n.innerHTML=`<div class="view-loading"><div class="spinner"></div><p>加载采集历史...</p></div>`;try{let r=await fetch(`/api/matrix/crawl-history?limit=50`);if(!r.ok)throw Error(`获取采集历史失败: ${r.status}`);let i=await r.json(),a=Array.isArray(i)?i:i.records||i.history||i.data||[];if(a.length===0){n.innerHTML=`
        <div class="view-header"><h2>🕸️ 采集历史</h2></div>
        <div class="empty-state">暂无采集记录</div>
        <div class="crawl-toolbar"><button id="crawl-refresh-btn" class="btn btn-secondary">🔄 刷新</button></div>
      `,n.querySelector(`#crawl-refresh-btn`)?.addEventListener(`click`,()=>e(n));return}n.innerHTML=`
      <div class="view-header">
        <h2>🕸️ 采集历史</h2>
        <span class="badge">${a.length} 条</span>
      </div>
      <div class="crawl-toolbar">
        <button id="crawl-refresh-btn" class="btn btn-secondary">🔄 刷新</button>
      </div>
      <div class="crawl-table-wrapper">
        <table class="crawl-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>账号</th>
              <th>平台</th>
              <th>状态</th>
              <th>详情</th>
            </tr>
          </thead>
          <tbody>
            ${a.map((e,n)=>{let r=e.time||e.timestamp||e.crawled_at||e.created_at||``,i=e.account||e.username||e.user||e.account_id||`-`,a=e.platform||e.source||e.type||`-`,o=(e.status||e.result||e.state||`unknown`).toLowerCase(),s=e.detail||e.message||e.error||e.description||e.url||``,c=o===`success`||o===`completed`?`成功`:o===`failed`||o===`error`?`失败`:o===`running`||o===`processing`?`进行中`:o;return`
                <tr class="crawl-row-${o===`success`||o===`completed`?`success`:o===`failed`||o===`error`?`failed`:`pending`}">
                  <td class="crawl-time">${t(r)}</td>
                  <td class="crawl-account">${i}</td>
                  <td class="crawl-platform">${a}</td>
                  <td class="crawl-status">
                    <span class="status-tag status-${o===`success`||o===`completed`?`success`:o===`failed`||o===`error`?`failed`:`pending`}">${c}</span>
                  </td>
                  <td class="crawl-detail">${s||`-`}</td>
                </tr>
              `}).join(``)}
          </tbody>
        </table>
      </div>
    `,n.querySelector(`#crawl-refresh-btn`)?.addEventListener(`click`,async()=>{n.innerHTML=`<div class="view-loading"><div class="spinner"></div><p>刷新中...</p></div>`;try{await e(n)}catch(e){n.innerHTML=`<div class="view-error"><h3>❌ 刷新失败</h3><p>${e.message}</p></div>`}})}catch(e){n.innerHTML=`<div class="view-error"><h3>❌ 加载失败</h3><p>${e.message}</p></div>`}}function t(e){if(!e)return`-`;try{let t=new Date(e);return isNaN(t.getTime())?e:t.toLocaleString(`zh-CN`,{hour12:!1})}catch{return e}}export{e as loadView};
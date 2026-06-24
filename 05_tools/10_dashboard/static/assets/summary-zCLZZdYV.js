async function e(e){e.innerHTML=`<div class="view-loading"><div class="spinner"></div><p>加载概览...</p></div>`;try{let[t,n,r]=await Promise.all([fetch(`/api/summary`),fetch(`/api/federation/health`),fetch(`/api/machines`)]),i=t.ok?await t.json():{},a=n.ok?await n.json():{},o=r.ok?await r.json():[],s=i.total_accounts??i.accounts??i.totalAccounts??0,c=i.total_blueprints??i.blueprints??i.totalBlueprints??0,l=i.new_messages??i.messages??i.newMessages??0,u=i.total_tasks??i.tasks??i.totalTasks??0,d=Array.isArray(o)?o:o.machines||o.data||o.nodes||[],f=(a.status||a.healthy)??!1,p=f===!0||f===`healthy`||f===`ok`||f===`online`,m=d.filter(e=>{let t=(e.status||e.state||``).toLowerCase();return t===`online`||t===`running`||t===`active`||t===`healthy`||e.online===!0}).length;e.innerHTML=`
      <div class="view-header">
        <h2>📊 系统概览</h2>
      </div>

      <!-- Summary Cards -->
      <div class="summary-grid">
        <div class="summary-card">
          <div class="summary-card-icon">🖥️</div>
          <div class="summary-card-value">${d.length}</div>
          <div class="summary-card-label">总机器数</div>
          <div class="summary-card-sub">${m} 在线</div>
        </div>
        <div class="summary-card">
          <div class="summary-card-icon">👤</div>
          <div class="summary-card-value">${s}</div>
          <div class="summary-card-label">总账号数</div>
        </div>
        <div class="summary-card">
          <div class="summary-card-icon">📋</div>
          <div class="summary-card-value">${c}</div>
          <div class="summary-card-label">总蓝图数</div>
        </div>
        <div class="summary-card">
          <div class="summary-card-icon">💬</div>
          <div class="summary-card-value">${l}</div>
          <div class="summary-card-label">新消息数</div>
        </div>
        <div class="summary-card">
          <div class="summary-card-icon">📌</div>
          <div class="summary-card-value">${u}</div>
          <div class="summary-card-label">任务总数</div>
        </div>
        <div class="summary-card health-card">
          <div class="summary-card-icon">${p?`✅`:`❌`}</div>
          <div class="summary-card-value">${p?`健康`:`异常`}</div>
          <div class="summary-card-label">联邦健康</div>
          <div class="summary-card-sub">${typeof f==`string`?f:p?`running`:`down`}</div>
        </div>
      </div>

      <!-- Machine Status -->
      <div class="view-section">
        <h3>🖥️ 机器在线状态</h3>
        <div class="machine-status-list">
          ${d.length===0?`<div class="empty-state">暂无机器数据</div>`:d.map(e=>{let t=(e.status||e.state||`unknown`).toLowerCase(),n=t===`online`||t===`running`||t===`active`||t===`healthy`||e.online===!0;return`
                  <div class="machine-status-item ${n?`online`:`offline`}">
                    <span class="machine-status-dot ${n?`dot-online`:`dot-offline`}"></span>
                    <span class="machine-name">${e.name||e.hostname||e.id||`未知`}</span>
                    <span class="machine-status-text">${n?`在线`:`离线`}</span>
                    ${e.ip||e.host?`<span class="machine-ip">${e.ip||e.host}</span>`:``}
                  </div>
                `}).join(``)}
        </div>
      </div>
    `}catch(t){e.innerHTML=`<div class="view-error"><h3>❌ 加载失败</h3><p>${t.message}</p></div>`}}export{e as loadView};
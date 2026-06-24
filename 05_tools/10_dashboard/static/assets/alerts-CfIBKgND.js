async function e(e){e.innerHTML=`<div class="view-loading"><div class="spinner"></div><p>加载告警中心...</p></div>`;try{await t(e)}catch(t){e.innerHTML=`<div class="view-error"><h3>❌ 加载失败</h3><p>${t.message}</p></div>`}}async function t(e){let r=await fetch(`/api/matrix/alerts/list`);if(!r.ok)throw Error(`获取告警列表失败: ${r.status}`);let i=await r.json(),a=Array.isArray(i)?i:i.alerts||i.data||[];e.innerHTML=`
    <div class="view-header">
      <h2>🔔 告警中心</h2>
      <span class="badge">${a.length} 条</span>
    </div>
    <div class="alerts-toolbar">
      <button id="alerts-refresh-btn" class="btn btn-secondary">🔄 刷新</button>
    </div>
    <div class="alerts-list">
      ${a.length===0?`<div class="empty-state">暂无告警 🎉</div>`:a.map((e,t)=>n(e,t)).join(``)}
    </div>
  `,e.querySelector(`#alerts-refresh-btn`).addEventListener(`click`,async()=>{e.innerHTML=`<div class="view-loading"><div class="spinner"></div><p>刷新中...</p></div>`;try{await t(e)}catch(t){e.innerHTML=`<div class="view-error"><h3>❌ 刷新失败</h3><p>${t.message}</p></div>`}}),e.querySelectorAll(`.alert-dismiss-btn`).forEach(t=>{t.addEventListener(`click`,async t=>{let n=t.target.dataset.alertId;if(n&&confirm(`确认清除此告警？`))try{let r=await fetch(`/api/matrix/alerts/${n}`,{method:`DELETE`});if(!r.ok)throw Error(`清除失败: ${r.status}`);let i=t.target.closest(`.alert-item`);i&&i.remove();let a=e.querySelector(`.badge`),o=e.querySelectorAll(`.alert-item`).length;if(a&&(a.textContent=`${o} 条`),o===0){let t=e.querySelector(`.alerts-list`);t&&(t.innerHTML=`<div class="empty-state">暂无告警 🎉</div>`)}}catch(e){alert(`清除告警失败: ${e.message}`)}})})}function n(e,t){let n=e.id||e.alert_id||`alert-${t}`,i=(e.severity||e.level||`info`).toLowerCase(),a=e.message||e.msg||e.title||JSON.stringify(e),o=e.time||e.timestamp||e.created_at||``,s={critical:`严重`,error:`错误`,warning:`警告`,info:`信息`}[i]||i;return`
    <div class="alert-item ${i===`critical`?`severity-critical`:i===`error`?`severity-error`:i===`warning`?`severity-warning`:`severity-info`}">
      <div class="alert-icon">${i===`critical`?`🔴`:i===`error`?`⛔`:i===`warning`?`⚠️`:`ℹ️`}</div>
      <div class="alert-body">
        <div class="alert-severity">${s}</div>
        <div class="alert-message">${a}</div>
        ${o?`<div class="alert-time">${r(o)}</div>`:``}
      </div>
      <button class="alert-dismiss-btn btn btn-sm" data-alert-id="${n}">✕</button>
    </div>
  `}function r(e){if(!e)return``;try{let t=new Date(e);return isNaN(t.getTime())?e:t.toLocaleString(`zh-CN`,{hour12:!1})}catch{return e}}export{e as loadView};
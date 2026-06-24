async function e(n){n.innerHTML=`<div class="view-loading"><div class="spinner"></div><p>加载实时时间线...</p></div>`;try{let r=await fetch(`/api/matrix/timeline`);if(!r.ok)throw Error(`获取时间线数据失败: ${r.status}`);let i=await r.json(),a=Array.isArray(i)?i:i.timeline||i.points||i.data||[];if(a.length===0){n.innerHTML=`
        <div class="view-header"><h2>📊 实时时间线</h2></div>
        <div class="empty-state">暂无时间线数据</div>
      `;return}let o=a.map((e,t)=>({label:e.label||e.time||e.timestamp||`T${t+1}`,cpu:parseFloat(e.cpu??e.cpu_usage??e.cpu_percent??0),disk:parseFloat(e.disk??e.disk_usage??e.disk_percent??0),time:e.time||e.timestamp||null})),s=Math.max(...o.map(e=>e.cpu),100),c=Math.max(...o.map(e=>e.disk),100),l=Math.max(s,c,1);n.innerHTML=`
      <div class="view-header">
        <h2>📊 实时时间线</h2>
        <span class="badge">${o.length} 个采样点</span>
      </div>
      <div class="timeline-controls">
        <button id="timeline-refresh-btn" class="btn btn-secondary">🔄 刷新</button>
      </div>

      <div class="timeline-section">
        <h3>💻 CPU 使用率</h3>
        <div class="bar-chart" id="cpu-chart">
          ${o.map(e=>`
            <div class="bar-column" title="${e.label}: CPU ${e.cpu.toFixed(1)}%">
              <div class="bar-fill cpu-bar" style="height:${e.cpu/l*100}%"></div>
              <div class="bar-label">${e.label.length>6?e.label.slice(0,6)+`..`:e.label}</div>
            </div>
          `).join(``)}
        </div>
      </div>

      <div class="timeline-section">
        <h3>💾 磁盘使用率</h3>
        <div class="bar-chart" id="disk-chart">
          ${o.map(e=>`
            <div class="bar-column" title="${e.label}: 磁盘 ${e.disk.toFixed(1)}%">
              <div class="bar-fill disk-bar" style="height:${e.disk/l*100}%"></div>
              <div class="bar-label">${e.label.length>6?e.label.slice(0,6)+`..`:e.label}</div>
            </div>
          `).join(``)}
        </div>
      </div>

      <div class="timeline-section">
        <h3>📋 详细数据</h3>
        <div class="timeline-table-wrapper">
          <table class="timeline-table">
            <thead>
              <tr>
                <th>时间 / 标签</th>
                <th>CPU (%)</th>
                <th>磁盘 (%)</th>
              </tr>
            </thead>
            <tbody>
              ${o.map(e=>`
                <tr>
                  <td>${e.time?t(e.time):e.label}</td>
                  <td><span class="value-bar" style="width:${Math.min(e.cpu,100)}%">${e.cpu.toFixed(1)}</span></td>
                  <td><span class="value-bar disk-bar-inline" style="width:${Math.min(e.disk,100)}%">${e.disk.toFixed(1)}</span></td>
                </tr>
              `).join(``)}
            </tbody>
          </table>
        </div>
      </div>
    `,n.querySelector(`#timeline-refresh-btn`).addEventListener(`click`,async()=>{n.innerHTML=`<div class="view-loading"><div class="spinner"></div><p>刷新中...</p></div>`;try{await e(n)}catch(e){n.innerHTML=`<div class="view-error"><h3>❌ 刷新失败</h3><p>${e.message}</p></div>`}})}catch(e){n.innerHTML=`<div class="view-error"><h3>❌ 加载失败</h3><p>${e.message}</p></div>`}}function t(e){if(!e)return``;try{let t=new Date(e);return isNaN(t.getTime())?e:t.toLocaleString(`zh-CN`,{hour12:!1})}catch{return e}}export{e as loadView};
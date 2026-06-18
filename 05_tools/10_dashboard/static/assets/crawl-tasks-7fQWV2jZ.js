async function e(e){e.innerHTML=`<div id="crawlTaskPanel" style="padding:20px"><div class="loading">⏳ 加载采集管理...</div></div>`;try{let t=await(await fetch(`/api/plugins/collector/summary`)).json();e.innerHTML=`
      <div style="padding:20px">
        <h2 style="font-size:18px;margin-bottom:12px">📡 采集任务</h2>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;margin-bottom:12px">
          <div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
            <div style="font-size:12px;color:var(--text2)">总采集数</div>
            <div style="font-size:24px;font-weight:700">${t.total||0}</div>
          </div>
          <div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
            <div style="font-size:12px;color:var(--text2)">今日新增</div>
            <div style="font-size:24px;font-weight:700;color:var(--green)">${t.today||0}</div>
          </div>
        </div>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border)">
          <div style="font-size:12px;font-weight:600;margin-bottom:8px">🔧 操作</div>
          <button onclick="window.switchView('plugin-collector')" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">→ 打开采集管理器</button>
          <span style="font-size:11px;color:var(--text2);margin-left:8px">完整采集管理界面</span>
        </div>
      </div>`}catch(t){e.innerHTML=`<div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">📡 采集任务</h2>
      <div style="background:var(--bg2);border-radius:var(--radius);padding:20px;border:1px solid var(--border)">
        <span style="color:var(--red)">❌ 加载失败: ${t.message}</span>
      </div>
    </div>`}}export{e as loadView};
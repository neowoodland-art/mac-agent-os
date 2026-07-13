async function e(e){e.innerHTML=`<div class="view-loading"><div class="spinner"></div><p>加载时间线...</p></div>`;try{let t=((await(await fetch(`/api/identity`)).json()).uid||``).replace(`...`,``);if(!t){e.innerHTML=`<div style="padding:20px;color:var(--text2)">无法获取本机标识</div>`;return}let n=await fetch(`/api/timeline/${t}?window=120`);if(!n.ok)throw Error(`获取时间线数据失败: ${n.status}`);let r=await n.json(),i=r.points||[],a=r.hostname||`未知`;if(!i.length){e.innerHTML=`
        <div style="padding:16px">
          <div style="font-size:18px;font-weight:600;margin-bottom:8px">📊 时间线</div>
          <div style="color:var(--text2);font-size:13px">${a}: 暂无数据</div>
        </div>`;return}i.map(e=>{try{return new Date(e.t).toLocaleTimeString()}catch{return``}});let o=i.map(e=>e.cpu||0),s=i.map(e=>e.disk_pct||e.disk||0),c=Math.max(...o,...s,1);e.innerHTML=`
      <div style="padding:16px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="font-size:18px;font-weight:600">📊 时间线</span>
          <span style="font-size:11px;color:var(--text2)">${a} · ${i.length} 采样点</span>
        </div>
        <canvas id="tlChart" style="width:100%;height:200px;background:var(--bg2);border-radius:8px;border:1px solid var(--border)"></canvas>
        <div style="margin-top:8px;display:flex;gap:20px;font-size:11px;color:var(--text2)">
          <span><span style="display:inline-block;width:12px;height:12px;background:#378ADD;border-radius:2px;vertical-align:middle;margin-right:4px"></span>CPU</span>
          <span><span style="display:inline-block;width:12px;height:12px;background:#D85A30;border-radius:2px;vertical-align:middle;margin-right:4px"></span>磁盘</span>
          <button onclick="this.parentElement.parentElement.innerHTML='<div class=loading>刷新中...</div>';loadView(container)" style="background:var(--bg3);border:1px solid var(--border);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">🔄 刷新</button>
        </div>
      </div>`;let l=document.getElementById(`tlChart`),u=l.getContext(`2d`),d=l.parentElement.getBoundingClientRect();l.width=(d.width||600)*2,l.height=400,u.scale(2,2);let f=d.width||600,p={top:16,bottom:16,left:32,right:12},m=f-p.left-p.right,h=200-p.top-p.bottom;u.clearRect(0,0,f,200),u.strokeStyle=`rgba(255,255,255,0.06)`,u.lineWidth=.5;for(let e=0;e<4;e++)u.beginPath(),u.moveTo(p.left,p.top+h*e/4),u.lineTo(f-p.right,p.top+h*e/4),u.stroke();let g=(e,t)=>{u.strokeStyle=t,u.lineWidth=1.5,u.beginPath(),e.forEach((t,n)=>{let r=p.left+n/(e.length-1||1)*m,i=p.top+h-t/c*h;n===0?u.moveTo(r,i):u.lineTo(r,i)}),u.stroke()};g(o,`#378ADD`),g(s,`#D85A30`)}catch(t){e.innerHTML=`<div style="padding:20px;color:var(--red)">❌ ${t.message}</div>`}}export{e as loadView};
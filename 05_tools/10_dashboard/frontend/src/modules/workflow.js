// ════════════════════════════════════════════════════════
// 矩阵设置 TAB
// ════════════════════════════════════════════════════════

function switchSetTab(tab, el) {
  document.querySelectorAll('.set-tab').forEach(t => {
    t.style.borderBottom = '2px solid transparent';
    t.style.color = '#8b8fa3';
  });
  el.style.borderBottom = '2px solid #6366f1';
  el.style.color = '#e1e4f0';
  ['set-export-content','set-backup-content','set-corpus-content'].forEach(id => {
    document.getElementById(id).style.display = id === tab+'-content' ? 'block' : 'none';
  });
}

async function loadMatrixSettings() {
  // 三个 TAB 都使用 MutationObserver 同步原始内容
  const syncMap = [
    { id: 'matrixExportContent2', load: 'loadMatrixExport', orig: 'matrixExportContent' },
    { id: 'matrixBackupContent2', load: 'loadMatrixBackup', orig: 'matrixBackupContent' },
    { id: 'corpusContent2', load: 'loadCorpus', orig: 'corpusContent' },
  ];
  for (const {id, load, orig} of syncMap) {
    const el = document.getElementById(id);
    const origEl = document.getElementById(orig);
    if (el && origEl && typeof window[load] === 'function') {
      await window[load]();
      el.innerHTML = origEl.innerHTML;
      if (!window['_setObs_' + id]) {
        window['_setObs_' + id] = new MutationObserver(() => {
          const target = document.getElementById(id);
          const source = document.getElementById(orig);
          if (target && source) target.innerHTML = source.innerHTML;
        });
        window['_setObs_' + id].observe(origEl, { childList: true, subtree: true, characterData: true });
      }
    }
  }
}

// ── Keyboard ──
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDetail(); });

// ── Timeline ──
let timelineChart = null;
async function loadTimeline(hostname) {
  if (!hostname) {
    // 展示 selector
    const sel = document.getElementById('timelineSelector');
    const r = await fetch('/api/machines'); const res = await r.json();
    sel.innerHTML = (res.machines||[]).map(m =>
      `<button class="btn" onclick="loadTimeline('${m.hostname}')">${m.hostname}</button>`
    ).join('');
    document.getElementById('timelineStatus').textContent = '点击机器查看';
    return;
  }
  document.getElementById('timelineStatus').textContent = `加载 ${hostname}...`;
  const r = await fetch(`/api/timeline/${hostname}?window=120`);
  const res = await r.json();
  const pts = res.points || [];
  if (!pts.length) { document.getElementById('timelineStatus').textContent = `${hostname}: 暂无数据`; return; }
  
  const labels = pts.map(p => { try { return new Date(p.t).toLocaleTimeString(); } catch(e) { return ''; }});
  const cpu = pts.map(p => p.cpu || 0);
  const disk = pts.map(p => p.disk_pct || 0);
  
  document.getElementById('timelineStatus').textContent = `${hostname}: ${pts.length} 个采样点 (最近${res.total}条)`;
  
  // 简单 Canvas 绘图
  const canvas = document.getElementById('timelineChart');
  const ctx = canvas.getContext('2d');
  canvas.width = canvas.offsetWidth * 2; canvas.height = canvas.offsetHeight * 2;
  ctx.scale(2,2); const w = canvas.offsetWidth, h = canvas.offsetHeight;
  
  const maxVal = Math.max(...cpu, ...disk, 1);
  const pad = {top:20, bottom:20, left:40, right:20};
  const cw = w - pad.left - pad.right, ch = h - pad.top - pad.bottom;
  
  ctx.clearRect(0,0,w,h);
  // grid
  ctx.strokeStyle = 'rgba(255,255,255,0.05)'; ctx.lineWidth = 0.5;
  for(let i=0;i<5;i++) { ctx.beginPath(); ctx.moveTo(pad.left, pad.top+ch*i/4); ctx.lineTo(w-pad.right, pad.top+ch*i/4); ctx.stroke(); }
  
  function drawLine(data, color) {
    ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath();
    data.forEach((v,i) => {
      const x = pad.left + (i/(data.length-1||1))*cw;
      const y = pad.top + ch - (v/maxVal)*ch;
      i===0 ? ctx.moveTo(x,y) : ctx.lineTo(x,y);
    }); ctx.stroke();
  }
  drawLine(cpu, '#378ADD');
  drawLine(disk, '#D85A30');
  
  // legend
  ctx.fillStyle = '#378ADD'; ctx.fillRect(w-130, 10, 12, 12);
  ctx.fillStyle = 'var(--text)'; ctx.font = '11px sans-serif'; ctx.fillText('CPU', w-112, 20);
  ctx.fillStyle = '#D85A30'; ctx.fillRect(w-80, 10, 12, 12);
  ctx.fillStyle = 'var(--text)'; ctx.fillText('磁盘(G)', w-62, 20);
}

// ── Alerts ──
async function loadAlerts() {
  const el = document.getElementById('alertsList');
  try {
    const r = await fetch('/api/alerts'); const res = await r.json();
    const alerts = res.alerts || [];
    if (!alerts.length) { el.innerHTML = '<div class="card"><div style="color:var(--green)">✅ 所有机器运行正常</div></div>'; return; }
    el.innerHTML = alerts.map(a => {
      const color = a.level === 'critical' ? 'var(--red)' : a.level === 'warning' ? 'var(--amber)' : 'var(--text2)';
      const since = a.since_sec < 3600 ? `${(a.since_sec/60).toFixed(0)}分钟` : `${(a.since_sec/3600).toFixed(1)}小时`;
      return `<div class="card" style="border-left:3px solid ${color}">
        <div style="font-weight:600">${a.hostname}</div>
        <div style="font-size:12px;color:${color}">${a.level==='critical'?'🔴 严重':a.level==='warning'?'🟡 警告':'ℹ️ 提示'}: 离线 ${since}</div>
        ${a.note ? `<div style="font-size:11px;color:var(--text2)">${a.note}</div>` : ''}
        <div style="margin-top:8px;display:flex;gap:8px">
          <button class="btn" onclick="wakeupMachine('${a.hostname}')">🔄 唤醒</button>
          <button class="btn" onclick="upgradeMachine('${a.hostname}')">⬆️ 升级</button>
        </div>
      </div>`;
    }).join('');
  } catch(e) { el.innerHTML = `<div class="error">❌ ${e.message}</div>`; }
}

async function wakeupMachine(hostname) {
  await fetch(`/api/wakeup/${hostname}`, {method:'POST'});
  alert(`已发送唤醒命令到 ${hostname}`);
}
async function upgradeMachine(hostname) {
  if (!confirm(`确认对 ${hostname} 执行 git pull + 重启服务?`)) return;
  await fetch(`/api/upgrade/${hostname}`, {method:'POST'});
  alert(`已发送升级命令到 ${hostname}`);
}
/**
 * 时间线视图（已适配真实后端 API）
 * 后端:
 *   GET /api/identity → 获取本机 UID
 *   GET /api/timeline/{uid}?window=120 → 时间线数据
 */
export async function loadView(container) {
  container.innerHTML = `<div class="view-loading"><div class="spinner"></div><p>加载时间线...</p></div>`;
  try {
    // 获取本机 UID
    const idR = await fetch('/api/identity');
    const idD = await idR.json();
    const uid = (idD.uid || '').replace('...', '');
    if (!uid) { container.innerHTML = '<div style="padding:20px;color:var(--text2)">无法获取本机标识</div>'; return; }

    const res = await fetch(`/api/timeline/${uid}?window=120`);
    if (!res.ok) throw new Error(`获取时间线数据失败: ${res.status}`);
    const data = await res.json();
    const pts = data.points || [];
    const hostname = data.hostname || '未知';

    if (!pts.length) {
      container.innerHTML = `
        <div style="padding:16px">
          <div style="font-size:18px;font-weight:600;margin-bottom:8px">📊 时间线</div>
          <div style="color:var(--text2);font-size:13px">${hostname}: 暂无数据</div>
        </div>`;
      return;
    }

    const labels = pts.map(p => { try { return new Date(p.t).toLocaleTimeString(); } catch(e) { return ''; }});
    const cpu = pts.map(p => p.cpu || 0);
    const diskPct = pts.map(p => p.disk_pct || p.disk || 0);
    const maxVal = Math.max(...cpu, ...diskPct, 1);

    container.innerHTML = `
      <div style="padding:16px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="font-size:18px;font-weight:600">📊 时间线</span>
          <span style="font-size:11px;color:var(--text2)">${hostname} · ${pts.length} 采样点</span>
        </div>
        <canvas id="tlChart" style="width:100%;height:200px;background:var(--bg2);border-radius:8px;border:1px solid var(--border)"></canvas>
        <div style="margin-top:8px;display:flex;gap:20px;font-size:11px;color:var(--text2)">
          <span><span style="display:inline-block;width:12px;height:12px;background:#378ADD;border-radius:2px;vertical-align:middle;margin-right:4px"></span>CPU</span>
          <span><span style="display:inline-block;width:12px;height:12px;background:#D85A30;border-radius:2px;vertical-align:middle;margin-right:4px"></span>磁盘</span>
          <button onclick="this.parentElement.parentElement.innerHTML='<div class=loading>刷新中...</div>';loadView(container)" style="background:var(--bg3);border:1px solid var(--border);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">🔄 刷新</button>
        </div>
      </div>`;

    // Canvas 绘图
    const canvas = document.getElementById('tlChart');
    const ctx = canvas.getContext('2d');
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = (rect.width || 600) * 2;
    canvas.height = 200 * 2;
    ctx.scale(2, 2);
    const w = rect.width || 600, h = 200;
    const pad = {top: 16, bottom: 16, left: 32, right: 12};
    const cw = w - pad.left - pad.right, ch = h - pad.top - pad.bottom;

    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = 'rgba(255,255,255,0.06)'; ctx.lineWidth = 0.5;
    for (let i = 0; i < 4; i++) {
      ctx.beginPath(); ctx.moveTo(pad.left, pad.top + ch * i / 4);
      ctx.lineTo(w - pad.right, pad.top + ch * i / 4); ctx.stroke();
    }
    const drawLine = (data, color) => {
      ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.beginPath();
      data.forEach((v, i) => {
        const x = pad.left + (i / (data.length - 1 || 1)) * cw;
        const y = pad.top + ch - (v / maxVal) * ch;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }); ctx.stroke();
    };
    drawLine(cpu, '#378ADD');
    drawLine(diskPct, '#D85A30');
  } catch(e) {
    container.innerHTML = `<div style="padding:20px;color:var(--red)">❌ ${e.message}</div>`;
  }
}

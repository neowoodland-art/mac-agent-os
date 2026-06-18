// ════════════════════════════════════════════════════════
// Machine Status Bar — 全局三台机器状态条
// ════════════════════════════════════════════════════════

let _machineBarTimer = null;

async function loadMachineBar() {
  const bar = document.getElementById('machineBar');
  if (!bar) return;
  try {
    const rh = await fetch('/api/federation/health');
    const health = await rh.json();
    // 补充本机健康（federation/health 只含远程机器）
    try {
      const lr = await fetch('/api/health');
      const ld = await lr.json();
      health['chengzigedeAir'] = ld;
    } catch(e) {}
    
    const rm = await fetch('/api/machines');
    const md = await rm.json();
    const machineList = md.machines || [];

    const MACHINE_NAMES = {
      'chengzigedeAir': { label: '主控', icon: '🖥️' },
      '5kechengdeAir': { label: '养号', icon: '🖥️' },
      '7kecheng': { label: '养号', icon: '🖥️' },
    };

    let html = '<div style="display:flex;gap:8px;flex-wrap:wrap">';
    for (const [name, info] of Object.entries(MACHINE_NAMES)) {
      const h = health[name] || {};
      const isOnline = h.status === 'ok';
      const mData = machineList.find(function(m){return m.hostname===name || m.hostname===h.hostname;});
      let statusClass = 'offline', statusText = '离线';
      if (isOnline) {
        statusClass = 'online';
        statusText = '在线';
        if (mData && mData.current_task) {
          statusClass = 'busy';
          statusText = '忙碌';
        }
      }
      var dotColor = statusClass === 'online' ? 'var(--green)' : (statusClass === 'busy' ? 'var(--amber)' : 'var(--text2)');
      var opacity = statusClass === 'offline' ? '0.3' : '1';
      html += '<div style="display:flex;align-items:center;gap:5px;padding:5px 10px;border-radius:6px;background:var(--bg2);border:1px solid var(--border);font-size:12px;opacity:'+opacity+'">'+
        '<span style="width:8px;height:8px;border-radius:50%;background:'+dotColor+'"></span>'+
        '<span style="font-weight:600;color:var(--text)">'+name+'</span>'+
        '<span style="font-size:10px;color:var(--text2)">'+info.label+'</span>'+
        '<span style="font-size:10px;color:'+dotColor+'">'+statusText+'</span></div>';
    }
    html += '</div>';
    bar.innerHTML = html;
  } catch(e) {
    // silent — status bar is not critical
  }
}

function initMachineBar() {
  if (_machineBarTimer) clearInterval(_machineBarTimer);
  loadMachineBar();
  _machineBarTimer = setInterval(loadMachineBar, 30000);
}

// 在页面加载完成后初始化
if (document.readyState === 'complete') {
  initMachineBar();
} else {
  window.addEventListener('load', initMachineBar);
}

async function sendC2Command() {
  const target = document.getElementById('c2Target')?.value;
  const type = document.getElementById('c2Type')?.value;
  const schedule = document.getElementById('c2Schedule')?.value;
  const resultEl = document.getElementById('c2Result');
  if (!resultEl) return;
  if (!target || !type) { resultEl.innerHTML = '<div style="color:var(--red);font-size:13px;padding:8px">请选择目标和命令类型</div>'; return; }

  const params = {};
  if (type === 'nurture_run') {
    params.accounts = (document.getElementById('c2Accounts')?.value||'').split(',').map(s=>s.trim()).filter(Boolean);
    params.rounds = parseInt(document.getElementById('c2Rounds')?.value) || 10;
  }

  resultEl.innerHTML = '<div style="text-align:center;padding:10px;color:var(--text2)">发送中...</div>';
  try {
    const r = await fetch('/api/c2/send', {method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({target,type,params,schedule_at:schedule||null})});
    const res = await r.json();
    const ch = res._channel || 'git';
    resultEl.innerHTML = '<div style="padding:8px;background:rgba(34,197,94,.1);border-radius:6px;font-size:13px;color:var(--green)">' +
      (ch==='http'?'⚡':'📤')+' 命令已发送 通道:'+ch+' 状态:'+(res.status||'?')+'<br>'+
      (res.message||'')+(res.command_id?'<br>ID:'+res.command_id:'')+'</div>';
    loadC2History();
  } catch(e) {
    resultEl.innerHTML = '<div style="color:var(--red);font-size:13px;padding:8px">'+e.message+'</div>';
  }
}

async function loadC2History() {
  const el = document.getElementById('c2CommandHistory');
  if (!el) return;
  try {
    const r = await fetch('/api/c2/commands');
    const d = await r.json();
    const cmds = d.recent || [];
    if (!cmds.length) { el.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text2);font-size:13px">暂无执行历史</div>'; return; }
    el.innerHTML = '<table><thead><tr><th>类型</th><th>目标</th><th>状态</th><th>时间</th><th>结果</th></tr></thead><tbody>' +
      cmds.slice(0,20).map(c => {
        const st = c.status||'?';
        const cl = st==='completed' ? '#22c55e' : (st==='failed'?'#ef4444':'#f59e0b');
        const out = c.output ? (c.output.accounts?c.output.accounts.join(','):Object.keys(c.output).slice(0,3).join('|')) : (c.error||'-');
        const ts = (c.completed_at||c.created_at||'').slice(0,19).replace('T',' ');
        return '<tr><td style="font-weight:600">'+c.type+'</td><td>'+(c.target_machine||'-')+'</td>' +
          '<td><span style="color:'+cl+'">●</span> '+st+'</td><td style="font-size:11px;color:var(--text2)">'+ts+'</td>' +
          '<td style="font-size:11px;color:var(--text2);max-width:150px;overflow:hidden;text-overflow:ellipsis">'+String(out).slice(0,40)+'</td></tr>';
      }).join('') + '</tbody></table>';
  } catch(e) {
    el.innerHTML = '<div style="padding:20px;color:var(--red)">'+e.message+'</div>';
  }
}

function c2Nurture(accountId) {
  document.getElementById('c2Target').value = 'chengzigedeAir';
  document.getElementById('c2Type').value = 'nurture_run';
  document.getElementById('c2Accounts').value = accountId;
  document.getElementById('c2NurtureParams').style.display = 'block';
  switchView('matrix-c2');
}
// ── 导出（防 Rollup tree-shake）──
window.c2Nurture = c2Nurture;
window.initMachineBar = initMachineBar;
window.loadC2History = loadC2History;
window.loadMachineBar = loadMachineBar;
window.sendC2Command = sendC2Command;
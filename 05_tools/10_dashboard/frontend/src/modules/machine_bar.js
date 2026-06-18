// ════════════════════════════════════════════════════════
// C2 Remote Control
// ════════════════════════════════════════════════════════

function toggleC2Params() {
  const type = document.getElementById('c2Type')?.value;
  const el = document.getElementById('c2NurtureParams');
  if (el) el.style.display = type === 'nurture_run' ? 'block' : 'none';
}

async function loadC2Machines() {
  const targetEl = document.getElementById('c2Target');
  const statusEl = document.getElementById('c2MachineStatus');
  if (!statusEl) return;
  statusEl.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text2)">加载中...</div>';
  try {
    const r = await fetch('/api/c2/machines');
    const d = await r.json();
    if (targetEl) targetEl.innerHTML = '<option value="">选择机器...</option>' +
      d.machines.map(m => '<option value="'+m+'">'+m+(m==='chengzigedeAir'?' (本机)':'')+'</option>').join('');

    let html = '';
    for (const m of d.machines) {
      try {
        const sr = await fetch('/api/c2/environment/'+encodeURIComponent(m));
        const st = await sr.json();
        if (st.output) {
          const o = st.output;
          html += '<div style="padding:8px 0;border-bottom:1px solid var(--border);font-size:12px;display:flex;justify-content:space-between">' +
            '<strong>'+m+'</strong>' +
            '<span>'+(o.guardd_running ? '✅ guardd运行' : '❌ guardd停')+' · 💾'+ (o.disk_avail_gb||'?')+'G' +' · 📱'+(o.matrix_accounts||'?')+'账号</span></div>';
        } else {
          html += '<div style="padding:8px 0;border-bottom:1px solid var(--border);font-size:12px">'+m+' · '+ (st.status||'未知') +'</div>';
        }
      } catch(e) {
        html += '<div style="padding:8px 0;border-bottom:1px solid var(--border);font-size:12px;color:var(--amber)">'+m+' · ⏳ 查询超时</div>';
      }
    }
    statusEl.innerHTML = html || '<div style="text-align:center;padding:20px;color:var(--text2)">无机器数据</div>';
  } catch(e) {
    statusEl.innerHTML = '<div style="padding:20px;color:var(--red)">'+e.message+'</div>';
  }
}
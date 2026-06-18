// ════════════════════════════════════════════════════════
// 录制管理
// ════════════════════════════════════════════════════════

async function loadMatrixRecord() {
  const listEl = document.getElementById('recordList');
  const detailEl = document.getElementById('recordDetail');
  const statusEl = document.getElementById('recordStatus');
  if (statusEl) statusEl.innerHTML = '';
  if (detailEl) detailEl.innerHTML = '';
  // 填充账号下拉
  const acctSel = document.getElementById('recordAccountSelect');
  if (acctSel) {
    try {
      const r = await fetch('/api/matrix/sms/accounts');
      const d = await r.json();
      acctSel.innerHTML = '<option value="">选择账号…</option>' +
        (d.accounts||[]).filter(a => a.is_local).map(a =>
          '<option value="'+a.id+'">'+(a.platform==='xiaohongshu'?'📕':'🎵')+' '+a.nickname+'</option>').join('');
    } catch(e) { /* ignore */ }
  }
  // 加载录制包列表
  refreshRecordingList();
}

async function refreshRecordingList() {
  const listEl = document.getElementById('recordList');
  if (!listEl) return;
  const statusEl = document.getElementById('recordStatus');
  listEl.innerHTML = '<div class="loading">加载录制包...</div>';
  try {
    const [listR, statR] = await Promise.all([
      fetch('/api/matrix/recordings'),
      fetch('/api/matrix/recordings/status'),
    ]);
    const list = await listR.json();
    const stat = await statR.json();
    const recordings = list.recordings || [];

    // 更新录制状态
    if (statusEl) {
      if (stat.status === 'running') {
        statusEl.innerHTML = '<span style="color:var(--green)">🔴 录制中 (PID '+stat.pid+')</span>';
        document.getElementById('recordStartBtn').style.display = 'none';
        document.getElementById('recordStopBtn').style.display = '';
      } else {
        statusEl.innerHTML = '<span style="color:var(--text2)">⏸ 空闲</span>';
        document.getElementById('recordStartBtn').style.display = '';
        document.getElementById('recordStopBtn').style.display = 'none';
      }
    }

    if (!recordings.length) {
      listEl.innerHTML = '<div style="color:var(--text2);font-size:13px;padding:20px;text-align:center">暂无录制包<br><span style="font-size:11px">选择一个账号点击「开始录制」，在浏览器中操作并按数字键 1-8 标记，按 0 结束</span></div>';
      return;
    }
    listEl.innerHTML = '<div style="display:grid;gap:6px">'+
      recordings.map(r => '<div style="background:var(--bg3);border-radius:6px;padding:8px 10px;border:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">'+
        '<div><span style="font-weight:600;font-size:12px">'+(r.account||'?')+'</span> '+
        '<span style="color:var(--text2);font-size:10px">'+r.steps+'步 '+(r.duration||0)+'s</span>'+
        '<span style="color:var(--text2);font-size:9px;margin-left:6px">'+(r.created||'').slice(0,16)+'</span></div>'+
        '<div style="display:flex;gap:4px">'+
          '<button onclick="recordingAnalyze(\''+r.file+'\')" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">🔍 分析</button>'+
          '<button onclick="recordingExport(\''+r.file+'\')" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">📦 导出</button>'+
          '<button onclick="recordingDelete(\''+r.file+'\')" style="background:rgba(220,38,38,.08);color:var(--red);border:1px solid var(--red);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">🗑 删除</button>'+
        '</div></div>').join('')+'</div>';
  } catch(e) {
    listEl.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>';
  }
}

async function recordingStart() {
  const sel = document.getElementById('recordAccountSelect');
  if (!sel || !sel.value) { alert('请先选择一个账号'); return; }
  const acct = sel.value;
  try {
    const r = await fetch('/api/matrix/recordings/start', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({account:acct})
    });
    const d = await r.json();
    if (d.status === 'ok') {
      refreshRecordingList();
    } else {
      alert('❌ '+(d.error||d.detail||'启动失败'));
    }
  } catch(e) { alert('❌ '+e.message); }
}

async function recordingStop() {
  try {
    const r = await fetch('/api/matrix/recordings/stop', { method:'POST' });
    const d = await r.json();
    refreshRecordingList();
  } catch(e) { alert('❌ '+e.message); }
}

async function recordingAnalyze(name) {
  const detailEl = document.getElementById('recordDetail');
  if (!detailEl) return;
  detailEl.innerHTML = '<div class="loading">分析中...</div>';
  try {
    const r = await fetch('/api/matrix/recordings/'+encodeURIComponent(name));
    const d = await r.json();
    if (d.error) { detailEl.innerHTML = '<span style="color:var(--red)">❌ '+d.error+'</span>'; return; }
    const actions = d.actions || [];
    const suggestions = d.blueprint_suggestions || [];
    let html = '<div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border);margin-top:6px">'+
      '<div style="font-weight:600;font-size:13px;margin-bottom:6px">🔍 分析结果 ('+d.steps_analyzed+'步)</div>';
    if (actions.length) {
      html += '<div style="font-size:11px;margin-bottom:6px;color:var(--text2)">操作序列:</div>'+
        actions.slice(0,15).map(a => '<div style="font-size:11px;padding:2px 0;border-bottom:1px solid var(--border)">'+
          '<span style="color:#6366f1">'+(a.action_type||'?')+'</span> '+
          '<span style="color:var(--text2)">→ '+(a.action_desc||'')+'</span>'+
        '</div>').join('');
    }
    if (suggestions.length) {
      html += '<div style="font-size:11px;margin-top:6px;color:var(--text2)">蓝图建议:</div>'+
        suggestions.slice(0,5).map(s => '<div style="font-size:11px;padding:2px 0">'+
          '<span style="color:var(--green)">步骤'+s.step+'</span>: '+(s.suggested_op||'')+'</div>').join('');
    }
    html += '</div>';
    detailEl.innerHTML = html;
  } catch(e) { detailEl.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>'; }
}

async function recordingExport(name) {
  const detailEl = document.getElementById('recordDetail');
  if (!detailEl) return;
  detailEl.innerHTML = '<div class="loading">导出中...</div>';
  try {
    const r = await fetch('/api/matrix/recordings/'+encodeURIComponent(name)+'/export', { method:'POST' });
    const d = await r.json();
    if (d.error) { detailEl.innerHTML = '<span style="color:var(--red)">❌ '+d.error+'</span>'; return; }
    let html = '<div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border);margin-top:6px">'+
      '<div style="font-weight:600;font-size:13px;margin-bottom:6px">📦 导出结果</div>'+
      '<div style="font-size:11px">蓝图: <code>'+(d.blueprint_name||'?')+'</code> ('+d.steps+'步)</div>'+
      '<div style="font-size:11px">代码: <code>'+(d.script_name||'?')+'</code></div>'+
      '<div style="font-size:11px;margin-top:4px;color:var(--text2)">导出位置: blueprints/ 和 scripts/recorded_ops/</div>'+
    '</div>';
    detailEl.innerHTML = html;
    refreshRecordingList();
  } catch(e) { detailEl.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>'; }
}

async function recordingDelete(name) {
  if (!confirm('确定删除录制包 '+name+'？')) return;
  try {
    await fetch('/api/matrix/recordings/'+encodeURIComponent(name), { method:'DELETE' });
    refreshRecordingList();
  } catch(e) { alert('❌ '+e.message); }
}
// ── 导出（防 Rollup tree-shake）──
window.loadMatrixRecord = loadMatrixRecord;
window.recordingAnalyze = recordingAnalyze;
window.recordingDelete = recordingDelete;
window.recordingExport = recordingExport;
window.recordingStart = recordingStart;
window.recordingStop = recordingStop;
window.refreshRecordingList = refreshRecordingList;
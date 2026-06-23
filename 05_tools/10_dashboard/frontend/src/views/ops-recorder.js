/**
 * ops-recorder.js — 录制与标注工作台（完整版）
 * 
 * 功能:
 *   顶部: 选账号 → 开始录制 / 停止录制 / 录制状态
 *   中部: 录制包列表 → 点击分析
 *   底部: 分析面板（前状态 | 动作 | 后状态 + 原子操作命名 + 测试）
 */
export async function loadView(container) {
  const uid = Math.random().toString(36).slice(2, 6);
  let _recording = null;    // 当前分析的录制数据
  let _names = {};          // {录制名: {步骤索引: 命名}}
  let _curStep = 0;         // 当前查看的步骤索引

  try { _names = JSON.parse(localStorage.getItem('rec_names')||'{}'); } catch(e) {}

  container.innerHTML = `
    <div style="padding:12px">
      <!-- ═══ 标题 + 录制控制 ═══ -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:6px">
        <h2 style="font-size:18px;margin:0">🎬 录制与标注</h2>
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
          <select id="recAcct_${uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;font-size:11px;width:120px"><option value="">加载账号...</option></select>
          <button id="recStartBtn_${uid}" onclick="_recStart('${uid}')" style="background:#22c55e;color:#fff;border:none;padding:5px 12px;border-radius:5px;cursor:pointer;font-size:11px">▶ 开始录制</button>
          <button id="recStopBtn_${uid}" onclick="_recStop('${uid}')" style="display:none;background:#ef4444;color:#fff;border:none;padding:5px 12px;border-radius:5px;cursor:pointer;font-size:11px">⏹ 停止</button>
          <span id="recStatus_${uid}" style="font-size:10px;color:var(--text2)"></span>
          <button onclick="_reloadAll('${uid}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 10px;border-radius:4px;cursor:pointer;font-size:10px">⟳ 刷新</button>
        </div>
      </div>

      <!-- ═══ 录制列表 ═══ -->
      <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px;margin-bottom:10px">
        <div style="font-size:12px;font-weight:600;margin-bottom:6px">📋 录制包</div>
        <div id="recList_${uid}" style="font-size:11px;max-height:180px;overflow-y:auto"><div class="loading">加载中...</div></div>
      </div>

      <!-- ═══ 分析面板 ═══ -->
      <div id="recAnalysis_${uid}" style="display:none">
        <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px">
          <!-- 标题 -->
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div>
              <span id="recName_${uid}" style="font-size:13px;font-weight:600"></span>
              <span id="recMeta_${uid}" style="font-size:10px;color:var(--text2);margin-left:6px"></span>
            </div>
            <button onclick="document.getElementById('recAnalysis_${uid}').style.display='none'" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">✕ 关闭</button>
          </div>
          <!-- 步骤导航 -->
          <div id="recSteps_${uid}" style="display:flex;gap:3px;margin-bottom:8px;overflow-x:auto;padding:2px 0"></div>
          <!-- 当前步骤详情 -->
          <div id="recStepDetail_${uid}"></div>
        </div>
      </div>
    </div>`;

  // ── 全局函数 ──
  window._reloadAll = function(uid) { loadAccts(uid); loadRecList(uid); checkStatus(uid); };
  window._recStart = function(uid) { startRecording(uid); };
  window._recStop = function(uid) { stopRecording(uid); };
  window._analyzeRec = function(name, uid) { analyzeRecording(name, uid); };

  // 初始加载
  loadAccts(uid);
  loadRecList(uid);
  checkStatus(uid);

  // ── 加载账号列表 ──
  async function loadAccts(uid) {
    const sel = document.getElementById(`recAcct_${uid}`);
    if (!sel) return;
    try {
      const r = await fetch('/api/matrix/accounts');
      const d = await r.json();
      const accts = Array.isArray(d) ? d : (d.accounts||[]);
      const local = accts.filter(a => a.is_local && a.platform);
      sel.innerHTML = '<option value="">— 选择账号 —</option>' +
        local.map(a => `<option value="${a.id}">${a.platform==='douyin'?'🎵':'📕'} ${a.id}</option>`).join('');
    } catch(e) { sel.innerHTML = '<option value="">加载失败</option>'; }
  }

  // ── 开始录制 ──
  async function startRecording(uid) {
    const acct = document.getElementById(`recAcct_${uid}`)?.value;
    if (!acct) { alert('请先选择账号'); return; }
    const btn = document.getElementById(`recStartBtn_${uid}`);
    btn.textContent = '⏳ 启动中...';
    btn.disabled = true;
    try {
      const r = await fetch('/api/matrix/record/start', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({account: acct})
      });
      const d = await r.json();
      if (d.status === 'ok') {
        document.getElementById(`recStatus_${uid}`).textContent = `🟢 录制中 (PID ${d.pid})`;
        document.getElementById(`recStopBtn_${uid}`).style.display = '';
        btn.style.display = 'none';
      } else {
        alert(d.message);
      }
    } catch(e) { alert('启动失败: '+e.message); }
    finally { btn.textContent = '▶ 开始录制'; btn.disabled = false; }
  }

  // ── 停止录制 ──
  async function stopRecording(uid) {
    try {
      const r = await fetch('/api/matrix/record/stop', {method:'POST'});
      const d = await r.json();
      document.getElementById(`recStatus_${uid}`).textContent = '⏹ 已停止';
      document.getElementById(`recStopBtn_${uid}`).style.display = 'none';
      document.getElementById(`recStartBtn_${uid}`).style.display = '';
      // 刷新列表
      loadRecList(uid);
    } catch(e) { alert('停止失败: '+e.message); }
  }

  // ── 检查录制状态 ──
  async function checkStatus(uid) {
    try {
      const r = await fetch('/api/matrix/record/status');
      const d = await r.json();
      if (d.running) {
        document.getElementById(`recStatus_${uid}`).textContent = `🟢 录制中 (PID ${d.pid})`;
        document.getElementById(`recStopBtn_${uid}`).style.display = '';
        document.getElementById(`recStartBtn_${uid}`).style.display = 'none';
      }
    } catch(e) {}
  }

  // ── 加载录制列表 ──
  async function loadRecList(uid) {
    const el = document.getElementById(`recList_${uid}`);
    if (!el) return;
    try {
      const r = await fetch('/api/matrix/record/list');
      const d = await r.json();
      const recs = d.recordings || [];
      if (!recs.length) { el.innerHTML = '<div style="color:var(--text2);padding:8px;text-align:center">暂无录制包</div>'; return; }
      el.innerHTML = recs.map(r => `<div style="display:flex;align-items:center;gap:6px;padding:4px 6px;border-bottom:1px solid var(--border);font-size:10px">
        <span style="font-weight:500;flex:1">${r.name}</span>
        <span style="color:var(--text2);width:30px">${r.platform==='douyin'?'🎵':'📕'}</span>
        <span style="color:var(--text2);width:80px">${r.account}</span>
        <span style="color:var(--text2);width:30px;text-align:center">${r.steps}步</span>
        <button onclick="window._analyzeRec('${r.name}','${uid}')" style="background:none;border:none;cursor:pointer;font-size:11px;color:var(--primary)">📊 分析</button>
      </div>`).join('');
    } catch(e) { el.innerHTML = `<div style="color:var(--red);padding:8px">❌ ${e.message}</div>`; }
  }

  // ── 分析录制 ──
  async function analyzeRecording(name, uid) {
    const panel = document.getElementById(`recAnalysis_${uid}`);
    panel.style.display = '';
    document.getElementById(`recName_${uid}`).textContent = `📹 ${name}`;

    try {
      const r = await fetch('/api/matrix/record/detail/' + encodeURIComponent(name));
      const d = await r.json();
      _recording = { name, meta: d.meta||{}, steps: d.steps||[], actions: (d.analysis||{}).actions||[], suggestions: (d.analysis||{}).blueprint_suggestions||[] };

      // 构建索引
      const actMap = {};
      _recording.actions.forEach(a => { const idx = a.step_after||a.step_before; if (!actMap[idx]) actMap[idx]=[]; actMap[idx].push(a); });
      _recording.actMap = actMap;
      const sugMap = {};
      _recording.suggestions.forEach(s => { sugMap[s.step] = s; });
      _recording.sugMap = sugMap;

      const m = _recording.meta;
      document.getElementById(`recMeta_${uid}`).textContent = `${m.platform||'?'} · ${m.account_id||'?'} · ${_recording.steps.length}步 · ${Math.round(m.duration||0)}s`;

      // 步骤导航
      renderStepNav(uid);
      // 显示第0步
      _curStep = 0;
      renderStepDetail(0, uid);
    } catch(e) {
      document.getElementById('recStepDetail_'+uid).innerHTML = `<div style="color:var(--red);padding:8px">❌ ${e.message}</div>`;
    }
  }

  // ── 步骤导航条 ──
  function renderStepNav(uid) {
    const el = document.getElementById(`recSteps_${uid}`);
    if (!el || !_recording) return;
    el.innerHTML = _recording.steps.map((s, i) => {
      const sug = _recording.sugMap[s.step];
      const status = sug ? (sug.confidence==='high'?'#22c55e':'#f59e0b') : '#6b7280';
      return `<span onclick="var _curStep=${i};renderStepDetail(${i},'${uid}')" id="stepDot_${i}_${uid}"
        style="cursor:pointer;display:inline-block;width:20px;height:20px;line-height:20px;text-align:center;
        border-radius:3px;font-size:9px;background:${status};color:#fff;opacity:${i===_curStep?'1':'0.5'}"
        title="步骤${i+1}">${i+1}</span>`;
    }).join('');
  }

  // ── 渲染步骤详情（核心：前状态 | 动作 | 后状态）──
  function renderStepDetail(idx, uid) {
    const el = document.getElementById(`recStepDetail_${uid}`);
    if (!el || !_recording || !_recording.steps[idx]) return;

    _curStep = idx;
    // 更新导航高亮
    document.querySelectorAll(`[id^="stepDot_"]`).forEach(d => { d.style.opacity = d.id===`stepDot_${idx}_${uid}` ? '1' : '0.5'; });

    const s = _recording.steps[idx];
    const acts = (_recording.actMap[s.step] || []);
    const firstAct = acts[0] || {};
    const sug = _recording.sugMap[s.step] || {};
    const nextStep = _recording.steps[idx + 1];
    const from = s.page || {};
    const to = nextStep ? (nextStep.page || {}) : {};
    const events = s.events || [];
    const features = firstAct.features || [];
    const inferred = firstAct.inferred_action || {};
    const autoOp = sug.suggested_op || firstAct.action_type || '';
    const savedName = _names[_recording.name]?.[idx] || '';

    // 动作描述
    let actionHtml = '';
    if (events.length) {
      actionHtml = events.map(e => {
        if (e.t === 'click') return `<span style="display:inline-block;background:rgba(99,102,241,.1);border-radius:3px;padding:2px 6px;margin:1px;font-size:9px">🖱 点击 (${e.x},${e.y}) <span style="color:var(--text2)">${e.target||''}</span></span>`;
        if (e.t === 'key') return `<span style="display:inline-block;background:rgba(245,158,11,.1);border-radius:3px;padding:2px 6px;margin:1px;font-size:9px">⌨️ 按键 ${e.k} ${e.c?'(组合)':''}</span>`;
        if (e.t === 'scroll') return `<span style="display:inline-block;background:rgba(34,197,94,.1);border-radius:3px;padding:2px 6px;margin:1px;font-size:9px">📜 滚动</span>`;
        return `<span style="display:inline-block;background:var(--bg3);border-radius:3px;padding:2px 6px;margin:1px;font-size:9px">${e.t||'事件'}</span>`;
      }).join('');
    } else {
      actionHtml = `<span style="color:var(--text2);font-size:10px">${firstAct.action_desc || '浏览/等待'}</span>`;
    }

    el.innerHTML = `
      <!-- 导航 -->
      <div style="display:flex;gap:4px;margin-bottom:6px">
        <button onclick="renderStepDetail(${Math.max(0,idx-1)},'${uid}')" ${idx===0?'disabled':''}
          style="flex:1;background:${idx===0?'var(--bg3)':'#6366f1'};color:${idx===0?'var(--text2)':'#fff'};border:none;padding:3px;border-radius:4px;cursor:${idx===0?'default':'pointer'};font-size:10px">◀ 上一步</button>
        <span style="font-size:10px;color:var(--text2);padding:3px">${idx+1}/${_recording.steps.length}</span>
        <button onclick="renderStepDetail(${Math.min(_recording.steps.length-1,idx+1)},'${uid}')" ${idx>=_recording.steps.length-1?'disabled':''}
          style="flex:1;background:${idx>=_recording.steps.length-1?'var(--bg3)':'#6366f1'};color:${idx>=_recording.steps.length-1?'var(--text2)':'#fff'};border:none;padding:3px;border-radius:4px;cursor:${idx>=_recording.steps.length-1?'default':'pointer'};font-size:10px">下一步 ▶</button>
      </div>

      <!-- ═══ 三栏：前状态 | 动作 | 后状态 ═══ -->
      <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:6px;margin-bottom:6px">
        <!-- 前状态 -->
        <div style="background:rgba(37,99,235,.06);border-radius:5px;padding:6px;border:1px solid rgba(37,99,235,.12)">
          <div style="font-size:9px;color:#3b82f6;font-weight:600;margin-bottom:3px">⬅ 前状态</div>
          <table style="font-size:9px;width:100%;border-collapse:collapse">
            <tr><td style="color:var(--text2);padding:1px 3px;width:45px">URL</td><td style="padding:1px 3px;word-break:break-all">${(from.url||'?').slice(0,50)}</td></tr>
            <tr><td style="color:var(--text2);padding:1px 3px">模式</td><td style="padding:1px 3px">${from.page_mode||'?'}</td></tr>
            <tr><td style="color:var(--text2);padding:1px 3px">元素</td><td style="padding:1px 3px">${from.interactable_count||0} 个可交互</td></tr>
            <tr><td style="color:var(--text2);padding:1px 3px">视口</td><td style="padding:1px 3px">${from.viewport||'?'}</td></tr>
          </table>
          ${s.screenshot_url ? `<img src="${s.screenshot_url}" style="max-width:100%;max-height:70px;border-radius:3px;margin-top:3px" onerror="this.style.display='none'">` : ''}
          ${from.text_snippet ? `<div style="font-size:8px;color:var(--text2);margin-top:2px;max-height:40px;overflow:hidden">📄 ${from.text_snippet.slice(0,80)}</div>` : ''}
        </div>

        <!-- 动作 -->
        <div style="display:flex;align-items:center;font-size:18px;color:var(--text2);padding:0 2px">→</div>

        <!-- 后状态 -->
        <div style="background:rgba(5,150,105,.06);border-radius:5px;padding:6px;border:1px solid rgba(5,150,105,.12)">
          <div style="font-size:9px;color:#22c55e;font-weight:600;margin-bottom:3px">➡ 后状态</div>
          <table style="font-size:9px;width:100%;border-collapse:collapse">
            <tr><td style="color:var(--text2);padding:1px 3px;width:45px">URL</td><td style="padding:1px 3px;word-break:break-all">${to ? (to.url||'同页').slice(0,50) : '(结束)'}</td></tr>
            <tr><td style="color:var(--text2);padding:1px 3px">模式</td><td style="padding:1px 3px">${to ? (to.page_mode||'?') : '-'}</td></tr>
            <tr><td style="color:var(--text2);padding:1px 3px">变化</td><td style="padding:1px 3px">
              ${firstAct.url_changed?'🔗 URL变化 ':''}${firstAct.text_changed?'📝 文本变化 ':''}${firstAct.mode_changed||''}
            </td></tr>
          </table>
          ${nextStep && nextStep.screenshot_url ? `<img src="${nextStep.screenshot_url}" style="max-width:100%;max-height:70px;border-radius:3px;margin-top:3px" onerror="this.style.display='none'">` : ''}
          ${to && to.text_snippet ? `<div style="font-size:8px;color:var(--text2);margin-top:2px;max-height:40px;overflow:hidden">📄 ${to.text_snippet.slice(0,80)}</div>` : ''}
        </div>
      </div>

      <!-- ═══ 动作详情与推断 ═══ -->
      <div style="background:var(--bg3);border-radius:5px;padding:6px;margin-bottom:6px">
        <div style="font-size:9px;color:var(--text2);font-weight:600;margin-bottom:3px">🖱 检测到的动作</div>
        <div style="display:flex;gap:3px;flex-wrap:wrap;margin-bottom:3px">${actionHtml}</div>
        ${features.length ? `<div style="font-size:8px;color:var(--text2)">${features.map(f => `<code style="background:var(--bg2);padding:1px 3px;border-radius:2px;margin:1px">${f.code}</code>`).join('')}</div>` : ''}
        ${inferred.trigger ? `<div style="font-size:8px;color:var(--text2);margin-top:2px">触发: ${inferred.trigger}</div>` : ''}
        ${inferred.desc ? `<div style="font-size:8px;color:var(--text2)">描述: ${inferred.desc}</div>` : ''}
      </div>

      <!-- ═══ 原子操作命名 ═══ -->
      <div style="display:flex;gap:4px;align-items:center;margin-bottom:4px">
        <span style="font-size:10px;color:var(--text2)">🏷️ 原子操作:</span>
        <input id="nameInput_${idx}_${uid}" value="${savedName || autoOp}"
          style="flex:1;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:3px;font-size:10px"
          onchange="var v=this.value.trim();if(v){if(!_names['${_recording.name}'])_names['${_recording.name}']={};_names['${_recording.name}'][${idx}]=v;localStorage.setItem('rec_names',JSON.stringify(_names))}">
        <button onclick="window._testAtomOp(document.getElementById('nameInput_${idx}_${uid}').value,'${uid}')"
          style="background:#22c55e;color:#fff;border:none;padding:3px 8px;border-radius:3px;cursor:pointer;font-size:10px">🧪 测试</button>
      </div>

      <!-- 保存/导出 -->
      <div style="display:flex;gap:4px">
        <button onclick="var c=_names['${_recording.name}']?Object.keys(_names['${_recording.name}']).length:0;localStorage.setItem('rec_names',JSON.stringify(_names));document.getElementById('recSaveStatus_${uid}').textContent='✅ 已保存 '+c+'/'+_recording.steps.length+' 步'"
          style="flex:1;background:var(--primary);color:#fff;border:none;padding:3px;border-radius:4px;cursor:pointer;font-size:10px">💾 保存命名</button>
        <button onclick="_exportBp('${uid}')"
          style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">📦 导出蓝图</button>
      </div>
      <div id="recSaveStatus_${uid}" style="margin-top:2px;font-size:9px;color:var(--text2)"></div>
    `;
  }

  // ── 测试原子操作 ──
  window._testAtomOp = async function(opName, uid) {
    if (!opName || !_recording) return;
    const acct = _recording.meta.account_id;
    const platform = _recording.meta.platform || 'douyin';
    const statusEl = document.getElementById('recSaveStatus_'+uid);
    if (!acct) { statusEl.textContent = '❌ 无账号信息'; return; }
    statusEl.textContent = '⏳ 正在提交测试...';
    try {
      const r = await fetch('/api/ops/test-atom', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({op: opName, account: acct, platform})
      });
      const d = await r.json();
      statusEl.textContent = '✅ 测试已提交: ' + (d.status||'ok') + (d.details ? ' | '+d.details : '');
    } catch(e) { statusEl.textContent = '❌ '+e.message; }
  };

  // ── 导出蓝图 ──
  window._exportBp = function(uid) {
    if (!_recording) return;
    const names = _names[_recording.name] || {};
    const savedCount = Object.keys(names).length;
    if (savedCount === 0) { alert('请先命名步骤再导出'); return; }
    const bpName = prompt('蓝图名称:', '录制_'+_recording.name.replace('recording_','').slice(0,20));
    if (!bpName) return;
    const steps = Object.keys(names).sort((a,b)=>a-b).map(idx => ({step_id: parseInt(idx)+1, op: names[idx], args: {}}));
    const blueprint = { name: bpName, description: '从录制标注导出: '+_recording.name, platform: _recording.meta.platform||'douyin', steps };
    const blob = new Blob([JSON.stringify(blueprint,null,2)], {type:'application/json'});
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = bpName+'.json'; a.click();
    URL.revokeObjectURL(a.href);
    document.getElementById('recSaveStatus_'+uid).textContent = '📦 蓝图已导出: '+steps.length+' 步';
  };
}

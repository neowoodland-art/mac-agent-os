/**
 * 蓝图管理（step1：列表 + 执行/编辑/删除）
 */
export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
  try {
    const [br, ar] = await Promise.all([
      fetch('/api/matrix/blueprints'),
      fetch('/api/v2/accounts'),
    ]);
    const bpData = await br.json();
    const bps = Array.isArray(bpData) ? bpData : (bpData.blueprints || []);
    const accts = (await ar.json()).accounts || [];
    const platIcon = p => p === 'xiaohongshu' ? '📕' : '🎵';

    // 执行蓝图
    window._bpExec = name => {
      const ids = accts.map(a => a.id).join(', ');
      const input = prompt(`输入账号ID（逗号分隔，可用: ${ids.slice(0,40)}...）`, accts.slice(0,2).map(a=>a.id).join(','));
      if (!input) return;
      fetch('/api/ops/run', {method:'POST',headers:{'Content-Type':'application/json'}, body: JSON.stringify({type:'collect', accounts: input.split(',').map(s=>s.trim()), params:{blueprint: name, rounds:1}})})
        .then(r=>r.json()).then(d=>alert(d.status==='error'?'❌ '+d.message:'✅ 已提交')).catch(e=>alert('❌ '+e.message));
    };
    window._bpDel = async name => {
      if (!confirm(`删除 "${name}"？`)) return;
      try {
        const r = await fetch(`/api/matrix/blueprints/${encodeURIComponent(name)}`, {method:'DELETE'});
        if (!r.ok) throw new Error((await r.json()).detail);
        location.reload();
      } catch(e) { alert('❌ '+e.message); }
    };
    window._bpEdit = name => {
      const bp = bps.find(b => b.name === name);
      if (!bp) return;
      document.getElementById('bpName').value = bp.name;
      if (bp.platform) document.getElementById('bpPlatform').value = bp.platform;
      document.getElementById('bpDesc').value = bp.description || '';
      window._bpSteps = (bp.steps || []).map(s => ({ name: s.op || s.name || '', label: (window._matrixOps?.[s.op||s.name]?.label) || s.op || s.name || '' }));
      renderSteps();
      document.getElementById('bpListBody').style.display = 'block';
      document.getElementById('bpListArrow').textContent = '▼ 收起';
    };

    let html = `<div style="padding:16px">
      <h2 style="font-size:18px;margin:0 0 10px">📋 蓝图管理</h2>
      <div style="margin-bottom:10px;background:var(--bg2);border-radius:10px;border:1px solid var(--border);overflow:hidden">
        <div onclick="window._bpToggle()" style="padding:10px 14px;font-weight:600;font-size:13px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;user-select:none">
          <span>📋 全部 (${bps.length})</span>
          <span id="bpListArrow" style="color:var(--text2);font-size:12px">▶ 展开</span>
        </div>
        <div id="bpListBody" style="display:none;padding:0 14px 10px">`;
    bps.forEach(b => {
      html += `<div style="display:flex;align-items:center;gap:8px;padding:8px 10px;border-bottom:1px solid var(--border);font-size:13px">
        <span style="flex:1"><strong>${b.name}</strong> <span style="color:var(--text2);font-size:11px">${(b.steps||[]).length}步 · ${b.platform||'douyin'}</span></span>
        <span style="display:flex;gap:4px;flex-shrink:0">
          <button onclick="window._bpExec('${b.name.replace(/'/g,"\\'")}')" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:6px;cursor:pointer;font-size:11px">▶ 执行</button>
          <button onclick="window._bpEdit('${b.name.replace(/'/g,"\\'")}')" style="background:transparent;color:var(--text);border:1px solid var(--border);padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px">✏️</button>
          <button onclick="window._bpDel('${b.name.replace(/'/g,"\\'")}')" style="background:transparent;color:var(--red);border:1px solid rgba(239,68,68,.3);padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px">🗑</button>
        </span>
      </div>`;
    });
    html += '</div></div>';

    // 编辑器区域
    html += `<div style="background:var(--bg2);border-radius:10px;padding:16px;border:1px solid var(--border)">
      <div style="font-size:13px;font-weight:600;margin-bottom:8px">✏️ 编辑器 <span style="font-size:11px;color:var(--text2);font-weight:400">（编辑/新建蓝图）</span></div>
      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:8px">
        <input id="bpName" placeholder="蓝图名称" style="flex:2;min-width:150px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:13px">
        <select id="bpPlatform" onchange="window._bpPlatChange()" style="flex:1;min-width:80px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px">
          <option value="douyin">🎵 抖音</option>
          <option value="xiaohongshu">📕 小红书</option>
        </select>
        <input id="bpDesc" placeholder="备注" style="flex:2;min-width:150px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px">
      </div>
      <div style="display:flex;gap:4px;margin-bottom:8px;flex-wrap:wrap" id="bpOpTabs"></div>
      <div id="bpOpList" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;min-height:40px">加载原子操作...</div>
      <div style="font-size:11px;color:var(--text2);margin-bottom:4px">步骤 <span id="bpStepCount">0 步</span></div>
      <div id="bpSteps" style="min-height:40px;background:var(--bg3);border-radius:6px;padding:6px;border:1px solid var(--border);margin-bottom:8px"></div>
      <div id="bpValidate" style="font-size:12px;margin-bottom:8px"></div>
      <div style="display:flex;gap:8px">
        <button onclick="window._bpSave()" style="background:#6366f1;color:#fff;border:none;padding:6px 16px;border-radius:6px;cursor:pointer;font-size:12px">💾 保存</button>
        <button onclick="window._bpClear()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:6px 16px;border-radius:6px;cursor:pointer;font-size:12px">🗑 清空</button>
      </div>
    </div></div>`;

    container.innerHTML = html;

    // 加载原子操作
    const or = await fetch('/api/matrix/atom-ops');
    const od = await or.json();
    const allOps = od.ops || [];
    window._matrixOps = {};
    allOps.forEach(o => { window._matrixOps[o.name] = o; });
    window._bpSteps = [];

    const CAT_LABELS = { all:'📋 全部', navigation:'🏠 导航', browse:'📱 浏览', interact:'💡 交互', utility:'⏳ 工具' };
    const CATEGORIES = { douyin: ['navigation','browse','interact','utility'], xiaohongshu: ['navigation','browse','interact','utility'] };

    // 渲染分类标签
    document.getElementById('bpOpTabs').innerHTML = Object.entries(CAT_LABELS).map(([k,v]) =>
      `<span data-ft="${k}" onclick="window._bpf('${k}')" style="cursor:pointer;padding:3px 8px;font-size:10px;border-radius:4px;${k==='all'?'background:#6366f1;color:#fff':'background:var(--bg3);color:var(--text)'}">${v}</span>`
    ).join('');

    window._bpf = filter => { window._bpFilter = filter || 'all'; renderOps(); };
    window._bpPlatChange = () => { renderOps(); };
    window._bpToggle = () => {
      const body = document.getElementById('bpListBody'); const arrow = document.getElementById('bpListArrow');
      if (!body || !arrow) return;
      body.style.display = body.style.display === 'none' ? 'block' : 'none';
      arrow.textContent = body.style.display === 'none' ? '▶ 展开' : '▼ 收起';
    };
    window._bpRemoveStep = i => { window._bpSteps.splice(i, 1); renderSteps(); };
    window._bpStepUp = i => { if (i <= 0) return; const s = window._bpSteps; [s[i-1], s[i]] = [s[i], s[i-1]]; renderSteps(); };
    window._bpStepDown = i => { const s = window._bpSteps; if (i >= s.length-1) return; [s[i], s[i+1]] = [s[i+1], s[i]]; renderSteps(); };
    window._bpClear = () => { window._bpSteps = []; document.getElementById('bpName').value = ''; window._editingBp = null; renderSteps(); };
    window._bpSave = async () => {
      const name = document.getElementById('bpName')?.value;
      if (!name) { alert('请输入名称'); return; }
      const steps = (window._bpSteps||[]).map(s => ({name: s.name}));
      if (!steps.length) { alert('请添加步骤'); return; }
      try {
        const r = await fetch('/api/matrix/blueprints', {method:'POST',headers:{'Content-Type':'application/json'}, body:JSON.stringify({name, description: document.getElementById('bpDesc')?.value||'', platform: document.getElementById('bpPlatform')?.value||'douyin', steps})});
        if (!r.ok) throw new Error((await r.json()).detail);
        window._bpClear(); location.reload();
      } catch(e) { alert('❌ '+e.message); }
    };

    // 渲染原子操作
    function canFollow(lastName, opName) {
      if (!lastName) { const op = window._matrixOps?.[opName]; return op ? op.can_be_first !== false : true; }
      const lastOp = window._matrixOps?.[lastName];
      if (!lastOp) return true;
      if (lastOp.allows && lastOp.allows[0] === '*') return true;
      return lastOp.allows ? lastOp.allows.includes(opName) : true;
    }
    function renderOps() {
      const el = document.getElementById('bpOpList'); if (!el) return;
      const ops = Object.values(window._matrixOps || {});
      const platform = document.getElementById('bpPlatform')?.value || 'douyin';
      const filter = window._bpFilter || 'all';
      const steps = window._bpSteps || [];
      const last = steps.length > 0 ? steps[steps.length-1] : null;
      const filtered = ops.filter(o => o.platform === platform || !o.platform)
        .filter(o => filter === 'all' || (o.category||o.group||'') === filter);
      el.innerHTML = filtered.map(o => {
        const ok = canFollow(last?.name, o.name);
        return `<div onclick="${ok ? 'window._bpa(\''+o.name+'\')' : ''}" style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:5px 8px;font-size:11px;${ok?'cursor:pointer':'opacity:.4;cursor:not-allowed'}">
          <strong>${o.label||o.name}</strong>${o.desc?'<div style="font-size:9px;color:var(--text2)">'+o.desc+'</div>':''}</div>`;
      }).join('');
    }
    // 加步骤
    window._bpa = name => {
      const op = window._matrixOps?.[name]; if (!op) return;
      const steps = window._bpSteps;
      if (steps.length > 0) { const lo = window._matrixOps?.[steps[steps.length-1].name]; if (lo && lo.allows && lo.allows[0] !== '*' && !lo.allows.includes(name)) { if (!confirm('⚠️ 不兼容，仍添加？')) return; } }
      else if (op.can_be_first === false) { alert('⚠️ 不能作为首步'); return; }
      steps.push({name, label: op.label||name});
      renderSteps();
    };
    function renderSteps() {
      const el = document.getElementById('bpSteps'); const ve = document.getElementById('bpValidate'); const sc = document.getElementById('bpStepCount');
      const steps = window._bpSteps || []; if (sc) sc.textContent = `${steps.length} 步`;
      if (!el) return;
      if (!steps.length) { el.innerHTML = '<div style="color:var(--text2);font-size:13px;text-align:center;padding:20px">👆 点击原子操作</div>'; if(ve) ve.innerHTML=''; return; }
      el.innerHTML = steps.map((s,i) => {
        let w = '';
        if (i>0) { const po = window._matrixOps?.[steps[i-1].name]; if (po && po.allows && po.allows[0]!=='*' && !po.allows.includes(s.name)) w = '⚠ 不兼容'; }
        if (i===0) { const op = window._matrixOps?.[s.name]; if (op && op.can_be_first === false) w = '⚠ 不能为首步'; }
        const nb = w.includes('不兼容')||w.includes('不能为首步') ? 'background:var(--red)' : 'background:#6366f1';
        return `<div style="padding:2px 0"><div style="display:flex;align-items:center;gap:8px;padding:6px 10px;background:var(--bg3);border-radius:6px;border:1px solid var(--border)">
          <span style="width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0;${nb};color:#fff">${i+1}</span>
          <span style="flex:1;font-size:13px"><strong>${s.label||s.name}</strong></span>
          <span style="cursor:pointer;font-size:12px;color:var(--text2);opacity:.5" onclick="window._bpStepUp(${i})">↑</span>
          <span style="cursor:pointer;font-size:12px;color:var(--text2);opacity:.5" onclick="window._bpStepDown(${i})">↓</span>
          <span style="cursor:pointer;color:var(--red);font-size:16px;opacity:.5" onclick="window._bpRemoveStep(${i})">✕</span>
        </div></div>`;
      }).join('');
      if (ve) {
        fetch('/api/matrix/blueprints/validate', {method:'POST',headers:{'Content-Type':'application/json'}, body:JSON.stringify({steps:steps.map(s=>({name:s.name}))})})
          .then(r=>r.json()).then(res=>{ve.innerHTML=res.valid?'✅ 合法':'❌ '+(res.errors||[]).map(e=>e.msg).join('; ')}).catch(()=>{});
      }
    }
    renderOps();
    renderSteps();

  } catch(e) { container.innerHTML = `<div class="error">❌ ${e.message || e}</div>`; }
}

/**
 * ops-recorder.js — 录制标注工作台 v4
 * 
 * 层级: 蓝图 → 原子操作 → 步骤 → 事件
 * 
 * 功能:
 *   1. 录制控制（选账号→开始/停止）
 *   2. 录制包列表
 *   3. 原子操作标注面板：
 *      a. 选中多步 → 打包为原子操作（命名+中文备注+特征标签）
 *      b. 单步删除
 *      c. 原子操作展开/收起（内部显示步骤详情）
 *      d. 未打包步骤单独展示
 *      e. 导出蓝图（含原子操作集）
 */
export async function loadView(container) {
  const uid = Math.random().toString(36).slice(2, 6);
  let _recording = null;
  let _annotations = { atomOps: [], deleted: [], stepLabels: {} };
  let _openAtomOp = null;      // 当前展开的原子操作 id
  let _selectedSteps = [];     // 已被选中的步骤索引（批量合并用）
  let _selectionMode = false;  // 选择模式

  // ── 加载/保存标注数据 ──
  function _loadAnnotations() {
    try {
      const raw = localStorage.getItem('rec_annotations_v4') || '{}';
      const all = JSON.parse(raw);
      _annotations = all[_recording?.name] || { atomOps: [], deleted: [], stepLabels: {} };
    } catch(e) { _annotations = { atomOps: [], deleted: [], stepLabels: {} }; }
  }
  function _saveAnnotations() {
    if (!_recording) return;
    try {
      const raw = localStorage.getItem('rec_annotations_v4') || '{}';
      const all = JSON.parse(raw);
      all[_recording.name] = _annotations;
      localStorage.setItem('rec_annotations_v4', JSON.stringify(all));
    } catch(e) { /* ignore */ }
  }

  // ── 获取有效步骤（排除已删除的）──
  function _getValidSteps() {
    if (!_recording) return [];
    const delSet = new Set(_annotations.deleted);
    return _recording.steps.filter((_, i) => !delSet.has(i));
  }

  // ── 生成唯一的原子操作 ID ──
  let _aoCounter = 0;
  function _genAoId() {
    return 'ao_' + (++_aoCounter) + '_' + Date.now().toString(36);
  }

  // ── 判断步骤是否被某个原子操作包含 ──
  function _stepInAtomOp(idx) {
    return _annotations.atomOps.find(ao => idx >= ao.stepRange[0] && idx <= ao.stepRange[1]);
  }

  // ── 判断步骤是否已删除 ──
  function _isDeleted(idx) {
    return _annotations.deleted.includes(idx);
  }

  // ── 获取某个原子操作的分析数据 ──
  function _getAoAnalysis(ao) {
    const [start, end] = ao.stepRange;
    // 收集范围内所有 steps 的 action 分析
    const acts = [];
    for (let i = start; i <= end; i++) {
      const s = _recording.steps[i];
      if (s && _recording.actMap) {
        const aList = _recording.actMap[s.step] || [];
        acts.push(...aList);
      }
    }
    // 收集范围第一个 step 的截图
    const firstStep = _recording.steps[start];
    const lastStep = _recording.steps[end];
    return {
      firstAct: acts[0] || {},
      acts,
      screenshotBefore: firstStep?.screenshot_url || '',
      screenshotAfter: lastStep ? _recording.steps[Math.min(end+1, _recording.steps.length-1)]?.screenshot_url : '',
      from: firstStep?.page || {},
      to: lastStep?.page || {},
      events: _recording.steps.slice(start, end+1).flatMap(s => s.events || []),
    };
  }

  // ── 构建 HTML ──
  container.innerHTML = `
    <div style="padding:12px">
      <!-- 标题 + 录制控制 -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:6px">
        <h2 style="font-size:18px;margin:0">🎬 录制标注</h2>
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
          <select id="recAcct_${uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;font-size:11px;width:120px"><option value="">加载账号...</option></select>
          <button id="recStartBtn_${uid}" onclick="window._recStart('${uid}')" style="background:#22c55e;color:#fff;border:none;padding:5px 12px;border-radius:5px;cursor:pointer;font-size:11px">▶ 开始录制</button>
          <button id="recStopBtn_${uid}" onclick="window._recStop('${uid}')" style="display:none;background:#ef4444;color:#fff;border:none;padding:5px 12px;border-radius:5px;cursor:pointer;font-size:11px">⏹ 停止</button>
          <span id="recStatus_${uid}" style="font-size:10px;color:var(--text2)"></span>
          <button onclick="window._reloadAll('${uid}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 10px;border-radius:4px;cursor:pointer;font-size:10px">⟳ 刷新</button>
        </div>
      </div>

      <!-- 录制包列表 -->
      <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px;margin-bottom:10px">
        <div style="font-size:12px;font-weight:600;margin-bottom:6px">📋 录制包</div>
        <div id="recList_${uid}" style="font-size:11px;max-height:180px;overflow-y:auto"><div class="loading">加载中...</div></div>
      </div>

      <!-- 标注面板 -->
      <div id="recAnalysis_${uid}" style="display:none">
        <div id="recAnalysisInner_${uid}" style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px">
          <!-- 标题 -->
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div>
              <span id="recName_${uid}" style="font-size:13px;font-weight:600"></span>
              <span id="recMeta_${uid}" style="font-size:10px;color:var(--text2);margin-left:6px"></span>
            </div>
            <div style="display:flex;gap:4px;align-items:center">
              <span id="aoStatus_${uid}" style="font-size:10px;color:var(--text2)"></span>
              <button onclick="window._toggleSelectionMode('${uid}')" id="selModeBtn_${uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">☐ 选择模式</button>
              <button onclick="window._collapseAll('${uid}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">⊟ 全部收起</button>
              <button onclick="document.getElementById('recAnalysis_${uid}').style.display='none'" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">✕ 关闭</button>
            </div>
          </div>

          <!-- 步骤横条（总览） -->
          <div id="recStepsBar_${uid}" style="display:flex;gap:3px;margin-bottom:8px;overflow-x:auto;padding:2px 0"></div>

          <!-- 选择模式工具栏 -->
          <div id="selToolbar_${uid}" style="display:none;background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.2);border-radius:5px;padding:6px;margin-bottom:6px">
            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
              <span style="font-size:10px;color:var(--text2)">已选 <span id="selCount_${uid}">0</span> 步</span>
              <button onclick="window._mergeSelected('${uid}')" id="mergeBtn_${uid}" disabled style="background:#6366f1;color:#fff;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">🔗 打包为原子操作</button>
              <button onclick="window._deleteSelected('${uid}')" id="delBtn_${uid}" disabled style="background:#ef4444;color:#fff;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">🗑️ 删除步骤</button>
              <button onclick="window._clearSelection('${uid}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">✕ 清除选择</button>
            </div>
          </div>

          <!-- 原子操作列表 + 未打包步骤 -->
          <div id="recContent_${uid}"></div>

          <!-- 保存/导出底部 -->
          <div style="display:flex;gap:4px;margin-top:8px;border-top:1px solid var(--border);padding-top:8px">
            <button onclick="window._saveAnnotations('${uid}')" style="flex:1;background:var(--primary);color:#fff;border:none;padding:3px;border-radius:4px;cursor:pointer;font-size:10px">💾 保存标注</button>
            <button onclick="window._exportBp('${uid}')" style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">📦 导出蓝图</button>
            <span id="recStatusMsg_${uid}" style="font-size:9px;color:var(--text2);align-self:center;flex:1"></span>
          </div>
        </div>
      </div>
    </div>`;

  // ══════════════════════════════════════════
  // 全局函数
  // ══════════════════════════════════════════
  window._reloadAll = function(u) { loadAccts(u); loadRecList(u); checkStatus(u); };
  window._recStart = function(u) { startRecording(u); };
  window._recStop = function(u) { stopRecording(u); };
  window._analyzeRec = function(name, u) { analyzeRecording(name, u); };
  window._deleteRec = async function(name, u) {
    if (!confirm('确定删除录制包「' + name + '」？')) return;
    try {
      const r = await fetch('/api/matrix/record/delete/' + encodeURIComponent(name), {method:'POST'});
      const d = await r.json();
      if (d.status === 'ok') {
        document.getElementById('recStatusMsg_'+u).textContent = '✅ 已删除: ' + name;
        loadRecList(u);
      } else {
        alert('删除失败: ' + (d.message || ''));
      }
    } catch(e) { alert('删除失败: '+e.message); }
  };
  window._toggleSelectionMode = function(u) { toggleSelectionMode(u); };
  window._mergeSelected = function(u) { mergeSelected(u); };
  window._deleteSelected = function(u) { deleteSelected(u); };
  window._clearSelection = function(u) { clearSelection(u); };
  window._collapseAll = function(u) { _openAtomOp = null; renderContent(u); };
  window._toggleAo = function(id, u) { _openAtomOp = _openAtomOp === id ? null : id; renderContent(u); };
  window._saveAnnotations = function(u) { _saveAnnotations(); document.getElementById('recStatusMsg_'+u).textContent = '✅ 已保存'; setTimeout(() => { const el = document.getElementById('recStatusMsg_'+u); if (el) el.textContent = ''; }, 2000); };
  window._editAo = function(id, u) { editAtomOp(id, u); };
  window._deleteAo = function(id, u) { deleteAtomOp(id, u); };
  window._stepClick = function(idx, u) { handleStepClick(idx, u); };
  window._deleteStep = function(idx, u) { deleteStep(idx, u); };

  // 初始加载
  loadAccts(uid);
  loadRecList(uid);
  checkStatus(uid);

  // ══════════════════════════════════════════
  // 录制控制
  // ══════════════════════════════════════════
  async function loadAccts(u) {
    const sel = document.getElementById(`recAcct_${u}`);
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

  async function startRecording(u) {
    const acct = document.getElementById(`recAcct_${u}`)?.value;
    if (!acct) { alert('请先选择账号'); return; }
    const btn = document.getElementById(`recStartBtn_${u}`);
    btn.textContent = '⏳ 启动中...'; btn.disabled = true;
    try {
      const r = await fetch('/api/matrix/record/start', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({account: acct})
      });
      const d = await r.json();
      if (d.status === 'ok') {
        document.getElementById(`recStatus_${u}`).textContent = `🟢 录制中 (PID ${d.pid})`;
        document.getElementById(`recStopBtn_${u}`).style.display = '';
        btn.style.display = 'none';
      } else if (d.need_login) {
        // 未登录提示——弹出引导对话框
        showLoginGuide(acct, d.platform || 'douyin', d.message, u);
      } else {
        alert(d.message);
      }
    } catch(e) { alert('启动失败: '+e.message); }
    finally { btn.textContent = '▶ 开始录制'; btn.disabled = false; }
  }

  function showLoginGuide(acct, platform, msg, u) {
    const container = document.getElementById('recAnalysisInner_'+u) || document.body;
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.5);z-index:999;display:flex;align-items:center;justify-content:center';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
    overlay.innerHTML = `<div style="background:var(--bg2);border-radius:10px;padding:20px;width:400px;max-width:90vw;border:1px solid var(--border);text-align:center">
      <div style="font-size:32px;margin-bottom:8px">🔐</div>
      <div style="font-size:14px;font-weight:600;margin-bottom:4px">账号未登录</div>
      <div style="font-size:11px;color:var(--text2);margin-bottom:12px;line-height:1.5">${msg}</div>
      <div style="background:rgba(99,102,241,.06);border-radius:6px;padding:10px;margin-bottom:12px;text-align:left;font-size:10px">
        <div style="font-weight:600;margin-bottom:4px">📋 操作步骤：</div>
        <div style="color:var(--text2);line-height:1.6">
          1. 前往左侧导航「📡 信息采集」<br>
          2. 选择账号 <b>${acct}</b><br>
          3. 系统会自动检测登录状态并引导登录<br>
          4. 登录成功后返回此页重新录制
        </div>
      </div>
      <div style="display:flex;gap:6px">
        <button onclick="window.switchView('matrix-collect');this.closest('div[style]').remove()"
          style="flex:1;background:var(--primary);color:#fff;border:none;padding:8px;border-radius:5px;cursor:pointer;font-size:12px">→ 前往信息采集登录</button>
        <button onclick="this.closest('div[style]').remove()"
          style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:8px 12px;border-radius:5px;cursor:pointer;font-size:11px">取消</button>
      </div>
    </div>`;
    container.appendChild(overlay);
  }

  async function stopRecording(u) {
    try {
      await fetch('/api/matrix/record/stop', {method:'POST'});
      document.getElementById(`recStatus_${u}`).textContent = '⏹ 已停止';
      document.getElementById(`recStopBtn_${u}`).style.display = 'none';
      document.getElementById(`recStartBtn_${u}`).style.display = '';
      loadRecList(u);
    } catch(e) { alert('停止失败: '+e.message); }
  }

  async function checkStatus(u) {
    try {
      const r = await fetch('/api/matrix/record/status');
      const d = await r.json();
      if (d.running) {
        document.getElementById(`recStatus_${u}`).textContent = `🟢 录制中 (PID ${d.pid})`;
        document.getElementById(`recStopBtn_${u}`).style.display = '';
        document.getElementById(`recStartBtn_${u}`).style.display = 'none';
      }
    } catch(e) {}
  }

  // ══════════════════════════════════════════
  // 录制包列表
  // ══════════════════════════════════════════
  async function loadRecList(u) {
    const el = document.getElementById(`recList_${u}`);
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
        <span style="color:var(--text2);width:50px;text-align:center">${r.created||''}</span>
        <button onclick="window._analyzeRec('${r.name}','${u}')" style="background:none;border:none;cursor:pointer;font-size:11px;color:var(--primary)">📊 分析</button>
        <button onclick="window._deleteRec('${r.name}','${u}')" style="background:none;border:none;cursor:pointer;font-size:11px;color:#ef4444">🗑️</button>
      </div>`).join('');
    } catch(e) { el.innerHTML = `<div style="color:var(--red);padding:8px">❌ ${e.message}</div>`; }
  }

  // ══════════════════════════════════════════
  // 分析录制
  // ══════════════════════════════════════════
  async function analyzeRecording(name, u) {
    document.getElementById(`recAnalysis_${u}`).style.display = '';

    try {
      const r = await fetch('/api/matrix/record/detail/' + encodeURIComponent(name));
      const d = await r.json();

      _recording = {
        name,
        meta: d.meta || {},
        steps: d.steps || [],
        actions: (d.analysis || {}).actions || [],
        suggestions: (d.analysis || {}).blueprint_suggestions || [],
      };

      // 构建索引
      const actMap = {};
      _recording.actions.forEach(a => {
        const idx = a.step_after || a.step_before;
        if (!actMap[idx]) actMap[idx] = [];
        actMap[idx].push(a);
      });
      _recording.actMap = actMap;
      const sugMap = {};
      _recording.suggestions.forEach(s => { sugMap[s.step] = s; });
      _recording.sugMap = sugMap;

      // 加载已保存的标注
      _loadAnnotations();

      // 渲染
      document.getElementById(`recName_${u}`).textContent = `📹 ${name}`;
      const m = _recording.meta;
      document.getElementById(`recMeta_${u}`).textContent =
        `${m.platform||'?'} · ${m.account_id||'?'} · ${_recording.steps.length}步 · ${Math.round(m.duration||0)}s`;
      renderContent(u);
    } catch(e) {
      document.getElementById('recContent_'+u).innerHTML =
        `<div style="color:var(--red);padding:8px">❌ ${e.message}</div>`;
    }
  }

  // ══════════════════════════════════════════
  // 选择模式
  // ══════════════════════════════════════════
  function toggleSelectionMode(u) {
    _selectionMode = !_selectionMode;
    _selectedSteps = [];
    document.getElementById('selModeBtn_'+u).textContent = _selectionMode ? '✓ 退出选择' : '☐ 选择模式';
    document.getElementById('selModeBtn_'+u).style.background = _selectionMode ? 'rgba(99,102,241,.2)' : 'var(--bg3)';
    document.getElementById('selModeBtn_'+u).style.color = _selectionMode ? 'var(--primary)' : 'var(--text)';
    document.getElementById('selToolbar_'+u).style.display = _selectionMode ? '' : 'none';
    renderContent(u);
  }

  function clearSelection(u) {
    _selectedSteps = [];
    updateSelectionUI(u);
    renderContent(u);
  }

  function updateSelectionUI(u) {
    const count = _selectedSteps.length;
    document.getElementById('selCount_'+u).textContent = count;
    document.getElementById('mergeBtn_'+u).disabled = count < 2;
    document.getElementById('delBtn_'+u).disabled = count === 0;
  }

  function handleStepClick(idx, u) {
    if (!_selectionMode) return;
    const pos = _selectedSteps.indexOf(idx);
    if (pos >= 0) {
      _selectedSteps.splice(pos, 1);
    } else {
      _selectedSteps.push(idx);
    }
    updateSelectionUI(u);
    renderContent(u);
  }

  function deleteSelected(u) {
    if (!_selectedSteps.length) return;
    if (!confirm('确定删除这 ' + _selectedSteps.length + ' 步？')) return;
    _selectedSteps.forEach(idx => {
      if (!_isDeleted(idx)) _annotations.deleted.push(idx);
    });
    _selectedSteps = [];
    _saveAnnotations();
    updateSelectionUI(u);
    renderContent(u);
  }

  function deleteStep(idx, u) {
    if (!confirm('确定删除步骤 ' + (idx+1) + '？')) return;
    if (!_isDeleted(idx)) _annotations.deleted.push(idx);
    _saveAnnotations();
    renderContent(u);
  }

  function mergeSelected(u) {
    if (_selectedSteps.length < 2) return;
    // 排序
    const sorted = [..._selectedSteps].sort((a,b) => a-b);
    // 检查是否连续
    const isContinuous = sorted.every((v, i, arr) => i === 0 || v === arr[i-1] + 1);
    if (!isContinuous) {
      alert('只能选择连续的步骤合并为原子操作');
      return;
    }
    // 检查是否与已有原子操作重叠
    for (const ao of _annotations.atomOps) {
      const [s, e] = ao.stepRange;
      if (sorted[0] <= e && sorted[sorted.length-1] >= s) {
        alert('选择的步骤与已有原子操作 "' + (ao.label || ao.name) + '" 重叠');
        return;
      }
    }

    // 弹出编辑框
    const firstAct = _recording.actMap[_recording.steps[sorted[0]]?.step]?.[0] || {};
    const autoName = firstAct.action_type || 'custom_op';
    showEditDialog({
      title: '打包为原子操作',
      fields: [
        { id: 'aoName', label: '标识名', value: autoName, placeholder: '英文标识, 如 like_video' },
        { id: 'aoLabel', label: '中文名', value: '', placeholder: '如 "点赞视频"' },
        { id: 'aoNote', label: '备注', value: '', placeholder: '描述该原子操作的功能和注意点', type: 'textarea' },
        { id: 'aoTags', label: '特征标签', value: '验证码:否, 框架:player', placeholder: '逗号分隔，如 验证码:是, 框架:player' },
      ],
      onConfirm: (vals) => {
        const ao = {
          id: _genAoId(),
          name: vals.aoName || autoName,
          label: vals.aoLabel || vals.aoName || autoName,
          note: vals.aoNote || '',
          tags: (vals.aoTags || '').split(',').map(t => t.trim()).filter(Boolean),
          stepRange: [sorted[0], sorted[sorted.length-1]],
        };
        _annotations.atomOps.push(ao);
        _selectedSteps = [];
        _saveAnnotations();
        updateSelectionUI(u);
        renderContent(u);
      },
    }, u);
  }

  // ══════════════════════════════════════════
  // 原子操作编辑/删除
  // ══════════════════════════════════════════
  function editAtomOp(id, u) {
    const ao = _annotations.atomOps.find(a => a.id === id);
    if (!ao) return;
    showEditDialog({
      title: '编辑原子操作',
      fields: [
        { id: 'aoName', label: '标识名', value: ao.name },
        { id: 'aoLabel', label: '中文名', value: ao.label },
        { id: 'aoNote', label: '备注', value: ao.note, type: 'textarea' },
        { id: 'aoTags', label: '特征标签', value: (ao.tags || []).join(', ') },
      ],
      onConfirm: (vals) => {
        ao.name = vals.aoName || ao.name;
        ao.label = vals.aoLabel || vals.aoName || ao.name;
        ao.note = vals.aoNote || '';
        ao.tags = (vals.aoTags || '').split(',').map(t => t.trim()).filter(Boolean);
        _saveAnnotations();
        renderContent(u);
      },
    }, u);
  }

  function deleteAtomOp(id, u) {
    if (!confirm('确定删除此原子操作？步骤将恢复为未打包状态')) return;
    _annotations.atomOps = _annotations.atomOps.filter(a => a.id !== id);
    if (_openAtomOp === id) _openAtomOp = null;
    _saveAnnotations();
    renderContent(u);
  }

  // ══════════════════════════════════════════
  // 编辑对话框
  // ══════════════════════════════════════════
  function showEditDialog(cfg, u) {
    const container = document.getElementById('recAnalysisInner_'+u);
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.4);z-index:999;display:flex;align-items:center;justify-content:center';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    overlay.innerHTML = `<div style="background:var(--bg2);border-radius:8px;padding:16px;width:380px;max-width:90vw;border:1px solid var(--border)">
      <div style="font-size:14px;font-weight:600;margin-bottom:10px">${cfg.title}</div>
      ${cfg.fields.map(f => {
        const tag = f.type === 'textarea' ? 'textarea' : 'input';
        const extra = f.type === 'textarea' ? 'rows="3" style="resize:vertical"' : `type="text"`;
        return `<div style="margin-bottom:8px">
          <label style="font-size:10px;color:var(--text2);display:block;margin-bottom:2px">${f.label}</label>
          <${tag} id="edit_${f.id}" value="${(f.value||'').replace(/"/g,'&quot;')}" placeholder="${f.placeholder||''}"
            ${extra}
            style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px;box-sizing:border-box">${f.type==='textarea' ? (f.value||'') : ''}</${tag}>
        </div>`;
      }).join('')}
      <div style="display:flex;gap:6px;margin-top:10px">
        <button id="editConfirmBtn" style="flex:1;background:var(--primary);color:#fff;border:none;padding:6px;border-radius:4px;cursor:pointer;font-size:11px">✅ 确认</button>
        <button onclick="this.closest('div[style]').remove()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 12px;border-radius:4px;cursor:pointer;font-size:11px">取消</button>
      </div>
    </div>`;

    container.appendChild(overlay);

    // 确认按钮事件
    document.getElementById('editConfirmBtn').onclick = () => {
      const vals = {};
      cfg.fields.forEach(f => {
        const el = document.getElementById('edit_'+f.id);
        vals[f.id] = el ? el.value : '';
      });
      cfg.onConfirm(vals);
      overlay.remove();
    };
  }

  // ══════════════════════════════════════════
  // 渲染主内容
  // ══════════════════════════════════════════
  function renderContent(u) {
    renderStepsBar(u);
    const el = document.getElementById('recContent_'+u);
    if (!el || !_recording) return;

    const totalSteps = _recording.steps.length;
    const deletedCount = _annotations.deleted.length;
    const aoCount = _annotations.atomOps.length;
    const packedSteps = _annotations.atomOps.reduce((sum, ao) => sum + (ao.stepRange[1] - ao.stepRange[0] + 1), 0);
    const packedCount = aoCount;

    document.getElementById('aoStatus_'+u).textContent =
      `🏗️ ${packedCount}个原子操作·${packedSteps}步已合并·${deletedCount}步已删除·剩余${totalSteps-deletedCount-packedSteps}步`;

    let html = '';

    // ── 原子操作列表 ──
    if (_annotations.atomOps.length) {
      html += `<div style="margin-bottom:6px"><div style="font-size:11px;font-weight:600;color:var(--primary);margin-bottom:4px">🏗️ 原子操作</div>`;
      _annotations.atomOps.forEach(ao => {
        const isOpen = _openAtomOp === ao.id;
        const [s, e] = ao.stepRange;
        const analysis = _getAoAnalysis(ao);
        html += renderAtomOpCard(ao, analysis, isOpen, u);
      });
      html += `</div>`;
    }

    // ── 未合并且未删除的步骤 ──
    const unassigned = [];
    for (let i = 0; i < totalSteps; i++) {
      if (!_isDeleted(i) && !_stepInAtomOp(i)) unassigned.push(i);
    }

    if (unassigned.length) {
      html += `<div><div style="font-size:11px;font-weight:600;color:#f59e0b;margin-bottom:4px;margin-top:6px">📄 未打包步骤 (${unassigned.length})</div>`;
      unassigned.forEach(idx => {
        const s = _recording.steps[idx];
        html += renderSingleStep(s, idx, u);
      });
      html += `</div>`;
    }

    // 空状态
    if (!_annotations.atomOps.length && unassigned.length === 0) {
      html = `<div style="text-align:center;padding:20px;color:var(--text2);font-size:11px">所有步骤已删除或已打包</div>`;
    }

    el.innerHTML = html;
  }

  // ══════════════════════════════════════════
  // 步骤横条
  // ══════════════════════════════════════════
  function renderStepsBar(u) {
    const el = document.getElementById('recStepsBar_'+u);
    if (!el || !_recording) return;
    el.innerHTML = _recording.steps.map((s, i) => {
      if (_isDeleted(i)) return '';
      const inAo = _stepInAtomOp(i);
      const selected = _selectionMode && _selectedSteps.includes(i);
      let bg, label;
      if (_selectionMode && selected) {
        bg = '#6366f1'; label = `${i+1}`;
      } else if (inAo) {
        bg = '#22c55e'; label = `${i+1}`;
      } else {
        bg = '#6b7280'; label = `${i+1}`;
      }
      const onClick = _selectionMode ? `window._stepClick(${i},'${u}')` : '';
      return `<span ${onClick ? 'onclick="'+onClick+'"' : ''}
        style="cursor:${_selectionMode?'pointer':'default'};display:inline-flex;align-items:center;justify-content:center;
        width:22px;height:22px;border-radius:4px;font-size:9px;font-weight:600;
        background:${bg};color:#fff;opacity:${_selectionMode && selected ? '1' : '0.7'};
        border:${_selectionMode && selected ? '2px solid #818cf8' : 'none'}">${label}</span>`;
    }).filter(Boolean).join('') || '<span style="color:var(--text2);font-size:10px">(全部已删除)</span>';
  }

  // ══════════════════════════════════════════
  // 渲染原子操作卡片
  // ══════════════════════════════════════════
  function renderAtomOpCard(ao, analysis, isOpen, u) {
    const [s, e] = ao.stepRange;
    const events = analysis.events || [];
    const clickCount = events.filter(e => e.t==='click').length;
    const keyCount = events.filter(e => e.t==='key').length;
    const scrollCount = events.filter(e => e.t==='scroll').length;
    let eventIcon = '';
    if (clickCount) eventIcon += '🖱';
    if (keyCount) eventIcon += '⌨️';
    if (scrollCount) eventIcon += '📜';
    if (!eventIcon) eventIcon = '⏸';

    const tagHtml = (ao.tags || []).map(t =>
      `<span style="background:rgba(99,102,241,.1);padding:1px 5px;border-radius:3px;font-size:8px;color:var(--text2)">${t}</span>`
    ).join('');

    const rangeLabel = s === e ? `步骤${s+1}` : `步骤${s+1}-${e+1}`;

    return `<div style="border:1px solid var(--border);border-radius:6px;margin-bottom:4px;overflow:hidden">
      <!-- 原子操作头 -->
      <div onclick="window._toggleAo('${ao.id}','${u}')"
        style="display:flex;align-items:center;gap:6px;padding:6px 8px;
        cursor:pointer;background:${isOpen?'var(--bg3)':'var(--bg2)'};
        border-bottom:${isOpen?'1px solid var(--border)':'none'};
        font-size:11px;user-select:none">
        <span style="background:#22c55e;color:#fff;border-radius:3px;padding:1px 5px;font-size:9px;flex-shrink:0">${rangeLabel}</span>
        <span style="font-weight:600;flex-shrink:0">${ao.label || ao.name}</span>
        <span style="color:var(--text2);font-size:9px;flex-shrink:0">${eventIcon}</span>
        <span style="font-size:8px;color:var(--text2);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${ao.note || ''}</span>
        <div style="display:flex;gap:2px;flex-shrink:0">
          ${tagHtml}
        </div>
        <span style="color:var(--text2);font-size:9px">${isOpen?'▼':'▶'}</span>
      </div>
      <!-- 原子操作详情 -->
      <div style="display:${isOpen?'block':'none'};padding:8px">
        ${renderAoDetail(ao, analysis, u)}
      </div>
    </div>`;
  }

  // ══════════════════════════════════════════
  // 原子操作详情（展开内容）
  // ══════════════════════════════════════════
  function renderAoDetail(ao, analysis, u) {
    const [s, e] = ao.stepRange;
    const firstAct = analysis.firstAct;
    const from = analysis.from || {};
    const to = analysis.to || {};

    // 三栏：操作前 | 动作汇总 | 操作后
    const beforeFeat = _extractFeatures(from, {});
    const afterFeat = _extractFeatures(to, {});

    // 变化特征码
    const changes = [];
    if (firstAct.url_changed || (from.url && to.url && from.url !== to.url)) {
      changes.push(`🔗 <b>URL</b>: ${(from.url||'?').slice(0,40)} → ${(to.url||'?').slice(0,40)}`);
    }
    if (firstAct.mode_changed) {
      changes.push(`🏗️ <b>框架</b>: ${firstAct.mode_changed}`);
    }
    if (firstAct.selector_changes) {
      Object.entries(firstAct.selector_changes).forEach(([sel, val]) => {
        changes.push(`🧩 <b>元素</b>: <code style="font-size:8px">${sel.replace(/^\[data-e2e="/,'').replace(/"\]$/,'')}</code> ${val}`);
      });
    }

    return `
      <!-- 三栏简约版 -->
      <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:6px;margin-bottom:6px">
        <div style="background:rgba(37,99,235,.04);border-radius:5px;padding:5px;border:1px solid rgba(37,99,235,.1)">
          <div style="font-size:8px;color:#3b82f6;font-weight:600;margin-bottom:2px">⬅ 操作前</div>
          <table style="font-size:8px;width:100%"><tr><td style="color:var(--text2);width:32px">URL</td><td style="word-break:break-all">${beforeFeat.url.slice(0,45)}</td></tr>
          <tr><td style="color:var(--text2)">框架</td><td>${_pageModeLabel(beforeFeat.mode)}</td></tr>
          <tr><td style="color:var(--text2)">状态</td><td>${analysis.from?.before_state?.markers ? Object.entries(analysis.from.before_state.markers).map(([k,v]) => `${k}:${v}`).join(' ') : '-'}</td></tr></table>
          ${analysis.screenshotBefore ? `<img src="${analysis.screenshotBefore}" style="max-width:100%;max-height:50px;border-radius:3px;margin-top:2px" onerror="this.style.display='none'">` : ''}
        </div>
        <div style="display:flex;align-items:center;font-size:14px;color:var(--text2);padding:0 2px">→</div>
        <div style="background:rgba(5,150,105,.04);border-radius:5px;padding:5px;border:1px solid rgba(5,150,105,.1)">
          <div style="font-size:8px;color:#22c55e;font-weight:600;margin-bottom:2px">➡ 操作后</div>
          <table style="font-size:8px;width:100%"><tr><td style="color:var(--text2);width:32px">URL</td><td style="word-break:break-all">${afterFeat.url.slice(0,45)}</td></tr>
          <tr><td style="color:var(--text2)">框架</td><td>${_pageModeLabel(afterFeat.mode)}</td></tr>
          <tr><td style="color:var(--text2)">状态</td><td>${analysis.to?.before_state?.markers ? Object.entries(analysis.to.before_state.markers).map(([k,v]) => `${k}:${v}`).join(' ') : '-'}</td></tr></table>
          ${analysis.screenshotAfter ? `<img src="${analysis.screenshotAfter}" style="max-width:100%;max-height:50px;border-radius:3px;margin-top:2px" onerror="this.style.display='none'">` : ''}
        </div>
      </div>

      <!-- 变化特征码 -->
      ${changes.length ? `<div style="background:rgba(99,102,241,.05);border-radius:4px;padding:4px 6px;margin-bottom:4px;border:1px solid rgba(99,102,241,.1)">
        <div style="font-size:8px;color:#6366f1;font-weight:600;margin-bottom:2px">🔍 变化特征码</div>
        ${changes.map(c => `<div style="font-size:8px;color:var(--text);padding:1px 0">${c}</div>`).join('')}
      </div>` : ''}

      <!-- 包含的步骤列表（折叠在内部） -->
      <div style="font-size:9px;color:var(--text2);margin-bottom:3px">📋 包含 ${e-s+1} 个步骤:</div>
      ${(() => {
        let stepsHtml = '';
        for (let i = s; i <= e; i++) {
          const step = _recording.steps[i];
          if (!step) continue;
          stepsHtml += renderMiniStep(step, i, u);
        }
        return stepsHtml;
      })()}

      <!-- 编辑/删除 -->
      <div style="display:flex;gap:4px;margin-top:4px;border-top:1px solid var(--border);padding-top:4px">
        <button onclick="window._editAo('${ao.id}','${u}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 8px;border-radius:3px;cursor:pointer;font-size:9px">✏️ 编辑</button>
        <button onclick="window._deleteAo('${ao.id}','${u}')" style="background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.2);color:#ef4444;padding:2px 8px;border-radius:3px;cursor:pointer;font-size:9px">🗑️ 删除</button>
      </div>
    `;
  }

  // ══════════════════════════════════════════
  // 渲染单个步骤（未打包状态）
  // ══════════════════════════════════════════
  function renderSingleStep(s, idx, u) {
    const acts = (_recording.actMap[s.step] || []);
    const firstAct = acts[0] || {};
    const sug = _recording.sugMap[s.step] || {};
    const events = s.events || [];
    const selected = _selectionMode && _selectedSteps.includes(idx);

    // 动作摘要
    let actionLabel = firstAct.action_type || firstAct.action_desc || sug.suggested_op || '浏览/等待';
    let eventIcon = '';
    if (events.some(e => e.t==='click')) eventIcon += '🖱';
    if (events.some(e => e.t==='key')) eventIcon += '⌨️';
    if (events.some(e => e.t==='scroll')) eventIcon += '📜';
    if (!eventIcon) eventIcon = '⏸';

    const from = s.page || {};

    return `<div style="display:flex;align-items:center;gap:4px;padding:4px 6px;border-bottom:1px solid var(--border);font-size:10px;
      ${selected ? 'background:rgba(99,102,241,.12);border-radius:4px;' : ''}
      ${_selectionMode ? 'cursor:pointer;' : ''}"
      ${_selectionMode ? `onclick="window._stepClick(${idx},'${u}')"` : ''}>
      <span style="background:#6b7280;color:#fff;border-radius:3px;padding:0 4px;font-size:8px;font-weight:600;flex-shrink:0">${idx+1}</span>
      <span>${eventIcon}</span>
      <span style="color:var(--text2);font-size:9px;min-width:60px">${_pageModeLabel(from.page_mode||'?')}</span>
      <span style="flex:1;font-weight:500">${actionLabel}</span>
      <span style="color:var(--text2);font-size:8px">${events.length}事件</span>
      <button onclick="event.stopPropagation();window._deleteStep(${idx},'${u}')" style="background:none;border:none;cursor:pointer;color:var(--text2);font-size:10px" title="删除步骤">✕</button>
    </div>`;
  }

  // ══════════════════════════════════════════
  // 渲染迷你步骤（原子操作内部）
  // ══════════════════════════════════════════
  function renderMiniStep(s, idx, u) {
    const acts = (_recording.actMap[s.step] || []);
    const firstAct = acts[0] || {};
    const events = s.events || [];
    const actionLabel = firstAct.action_type || firstAct.action_desc || '浏览/等待';
    const eventHtml = events.slice(0, 3).map(e => {
      if (e.t === 'click') return `🖱(${e.x},${e.y})`;
      if (e.t === 'key') return `⌨️${e.k}`;
      if (e.t === 'scroll') return `📜${Math.abs(e.dy||0)}`;
      return e.t;
    }).join(' ');

    const from = s.page || {};

    return `<div style="display:flex;align-items:center;gap:4px;padding:3px 6px;border-bottom:1px solid var(--border);font-size:9px">
      <span style="color:var(--text2);min-width:24px;font-size:8px">#${idx+1}</span>
      <span style="color:var(--text2);font-size:8px;min-width:50px">${_pageModeLabel(from.page_mode||'?')}</span>
      <span style="flex:1">${actionLabel}</span>
      <span style="color:var(--text2);font-size:8px">${eventHtml}</span>
      ${s.screenshot_url ? `<img src="${s.screenshot_url}" style="width:40px;height:30px;border-radius:2px;object-fit:cover" onerror="this.style.display='none'">` : ''}
    </div>`;
  }

  // ══════════════════════════════════════════
  // 导出蓝图
  // ══════════════════════════════════════════
  window._exportBp = function(u) {
    if (!_recording) return;
    const aos = _annotations.atomOps;
    if (!aos.length) { alert('请先打包至少一个原子操作再导出'); return; }
    const bpName = prompt('蓝图名称:', '录制_'+_recording.name.replace('recording_','').slice(0,20));
    if (!bpName) return;

    // 构建蓝图步骤（原子操作级别）
    const steps = aos.map((ao, i) => ({
      step_id: i + 1,
      op: ao.name,
      label: ao.label,
      args: {},
      note: ao.note,
      tags: ao.tags,
      raw_steps: ao.stepRange,  // [startIdx, endIdx] 原始步骤范围（可选）
    }));

    const blueprint = {
      name: bpName,
      description: '从录制标注导出: ' + _recording.name,
      platform: _recording.meta.platform || 'douyin',
      atom_ops: steps,
      _meta: {
        source_recording: _recording.name,
        exported_at: new Date().toISOString(),
        total_steps: _recording.steps.length,
        deleted_steps: _annotations.deleted.length,
      }
    };

    const blob = new Blob([JSON.stringify(blueprint, null, 2)], {type:'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = bpName + '.json';
    a.click();
    URL.revokeObjectURL(a.href);
    document.getElementById('recStatusMsg_'+u).textContent = '📦 蓝图已导出: ' + steps.length + ' 个原子操作';
  };

  // ══════════════════════════════════════════
  // 辅助函数
  // ══════════════════════════════════════════
  function _extractFeatures(page, state) {
    const f = {};
    f.url = page?.url || state?.url_pattern || '?';
    f.mode = page?.page_mode || state?.page_mode || '?';
    f.viewport = page?.viewport || '';
    f.textSnippet = page?.text_snippet || '';
    return f;
  }

  function _pageModeLabel(mode) {
    const map = {
      'grid': '列表页', 'player': '播放页', 'player_full': '全屏播放',
      'profile': '个人主页', 'search': '搜索页', 'unknown': '未知', 'modal': '弹窗',
    };
    return map[mode] || mode;
  }
}

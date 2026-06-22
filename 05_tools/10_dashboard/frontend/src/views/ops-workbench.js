/**
 * ops-workbench.js — 操作原子工作台
 * 
 * 三栏布局：
 *   左栏：当前状态流（导航路径）
 *   中栏：原子操作库（可用操作 + 测试状态）
 *   右栏：录制标注（快捷标注 + 命名）
 * 
 * 数据源：
 *   /api/matrix/atom-ops — 原子操作库
 *   /api/matrix/record/list — 录制列表
 *   /api/matrix/blueprints — 蓝图（参考步骤）
 */
export async function loadView(container) {
  const uid = Math.random().toString(36).slice(2, 6);

  container.innerHTML = `
    <div style="padding:12px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">🧭 操作原子工作台</h2>
        <div style="display:flex;gap:6px;font-size:12px">
          <button onclick="_reloadWorkbench('${uid}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 12px;border-radius:6px;cursor:pointer">⟳ 刷新</button>
        </div>
      </div>

      <!-- 三栏布局 -->
      <div style="display:grid;grid-template-columns:220px 1fr 280px;gap:10px;min-height:500px">

        <!-- ═══ 左栏：状态流 ═══ -->
        <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px;font-size:11px">
          <div style="font-weight:600;font-size:12px;margin-bottom:8px">🔄 状态流</div>
          <div id="stateFlow_${uid}" style="color:var(--text2)">
            <div class="loading" style="padding:8px">加载流程图...</div>
          </div>
        </div>

        <!-- ═══ 中栏：原子操作面板 ═══ -->
        <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px;font-size:11px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <span style="font-weight:600;font-size:12px">⚡ 原子操作</span>
            <span id="opCount_${uid}" style="font-size:10px;color:var(--text2)"></span>
          </div>
          <div style="display:flex;gap:4px;margin-bottom:8px;flex-wrap:wrap" id="opCategoryTabs_${uid}">
            <span onclick="_filterCat('all','${uid}')" data-cat="all" style="padding:3px 8px;border-radius:4px;cursor:pointer;background:var(--primary);color:#fff;font-size:10px">全部</span>
          </div>
          <div id="opList_${uid}" style="max-height:260px;overflow-y:auto">
            <div class="loading" style="padding:8px">加载原子操作...</div>
          </div>
          <!-- 操作详情面板 -->
          <div id="opDetail_${uid}" style="margin-top:6px;font-size:10px;display:none">
            <div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--primary)">
              <div id="opDetailBody_${uid}"></div>
            </div>
          </div>
        </div>

        <!-- ═══ 右栏：录制标注 ═══ -->
        <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:10px;font-size:11px;display:flex;flex-direction:column">
          <div style="font-weight:600;font-size:12px;margin-bottom:8px">🎬 录制标注</div>
          <div id="recPanel_${uid}" style="flex:1;overflow-y:auto">
            <div style="color:var(--text2);padding:8px;text-align:center">
              <p style="font-size:12px;margin-bottom:8px">选择录制包开始标注</p>
              <select id="recSelect_${uid}" onchange="_loadRecDetail(this.value,'${uid}')" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px;border-radius:4px;font-size:11px;margin-bottom:6px">
                <option value="">— 选择录制包 —</option>
              </select>
              <button onclick="_reloadRecList('${uid}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">⟳ 刷新</button>
            </div>
            <div id="recSteps_${uid}" style="font-size:10px;margin-top:4px"></div>
          </div>
        </div>

      </div>
    </div>`;

  // ── 全局函数 ──
  window._reloadWorkbench = function(uid) {
    loadAtomOps(uid);
    loadStateFlow(uid);
    loadRecList(uid);
  };
  window._filterCat = function(cat, uid) { filterCategory(cat, uid); };
  window._reloadRecList = function(uid) { loadRecList(uid); };
  window._loadRecDetail = function(name, uid) { if (name) showRecSteps(name, uid); };

  // 初始加载
  loadAtomOps(uid);
  loadStateFlow(uid);
  loadRecList(uid);
}

// ── 状态流定义 ──
const STATE_FLOW = {
  douyin: [
    { id: 'grid', label: '首页精选', icon: '🏠' },
    { id: 'branch', label: '分支页', icon: '📂' },
    { id: 'player_modal', label: '视频浮层', icon: '▶️' },
    { id: 'player_full', label: '视频全屏', icon: '📺' },
    { id: 'search', label: '搜索结果', icon: '🔍' },
    { id: 'profile', label: '个人主页', icon: '👤' },
    { id: 'user_profile', label: '博主主页', icon: '🌟' },
  ],
  xiaohongshu: [
    { id: 'grid', label: '首页推荐', icon: '🏠' },
    { id: 'note_detail', label: '笔记详情', icon: '📄' },
    { id: 'search', label: '搜索结果', icon: '🔍' },
    { id: 'profile', label: '个人主页', icon: '👤' },
  ]
};

// ── 左栏：加载状态流 ──
async function loadStateFlow(uid) {
  const el = document.getElementById(`stateFlow_${uid}`);
  if (!el) return;

  let html = '';
  // 显示抖音流程
  const flow = STATE_FLOW.douyin;
  flow.forEach((node, i) => {
    html += `<div style="display:flex;align-items:center;padding:4px 6px;border-radius:4px;margin:2px 0;background:var(--bg3)">
      <span style="margin-right:6px">${node.icon}</span>
      <span style="flex:1">${node.label}</span>
      <span style="font-size:9px;color:var(--text2)">⬤</span>
    </div>`;
    if (i < flow.length - 1) {
      html += `<div style="text-align:center;font-size:8px;color:var(--text2);padding:1px 0">│</div>`;
    }
  });

  html += `<div style="margin-top:8px;padding-top:6px;border-top:1px solid var(--border)">
    <div style="font-size:10px;color:var(--text2);margin-bottom:4px">📕 小红书流程</div>`;
  STATE_FLOW.xiaohongshu.forEach((node) => {
    html += `<div style="display:flex;align-items:center;padding:3px 6px;border-radius:3px;margin:1px 0;background:var(--bg3)">
      <span style="margin-right:6px">${node.icon}</span>
      <span>${node.label}</span>
    </div>`;
  });
  html += `</div>`;

  el.innerHTML = html;
}

// ── 中栏：加载原子操作 ──
let _allOps = [];
let _currentCat = 'all';

async function loadAtomOps(uid) {
  const listEl = document.getElementById(`opList_${uid}`);
  const tabsEl = document.getElementById(`opCategoryTabs_${uid}`);
  const countEl = document.getElementById(`opCount_${uid}`);
  if (!listEl) return;

  try {
    const r = await fetch('/api/matrix/atom-ops');
    const d = await r.json();
    _allOps = d.ops || [];

    // 提取分类
    const cats = {};
    _allOps.forEach(o => {
      const cat = o.category || '其他';
      if (!cats[cat]) cats[cat] = 0;
      cats[cat]++;
    });

    // 渲染分类标签
    let tabsHtml = `<span onclick="_filterCat('all','${uid}')" data-cat="all" style="padding:3px 8px;border-radius:4px;cursor:pointer;background:var(--primary);color:#fff;font-size:10px">全部 (${_allOps.length})</span>`;
    Object.keys(cats).sort().forEach(cat => {
      tabsHtml += `<span onclick="_filterCat('${cat.replace(/'/g,"\\'")}','${uid}')" data-cat="${cat}" style="padding:3px 8px;border-radius:4px;cursor:pointer;background:var(--bg3);color:var(--text);font-size:10px">${cat} (${cats[cat]})</span>`;
    });
    tabsEl.innerHTML = tabsHtml;
    countEl.textContent = `${_allOps.length} 个操作`;

    // 渲染全部
    renderOps(_allOps, uid);
  } catch(e) {
    listEl.innerHTML = `<div style="color:var(--red);padding:8px">❌ 加载失败: ${e.message}</div>`;
  }
}

function filterCategory(cat, uid) {
  _currentCat = cat;
  // 更新标签样式
  document.querySelectorAll(`[data-cat]`).forEach(el => {
    const isActive = el.dataset.cat === cat;
    el.style.background = isActive ? 'var(--primary)' : 'var(--bg3)';
    el.style.color = isActive ? '#fff' : 'var(--text)';
  });

  const filtered = cat === 'all' ? _allOps : _allOps.filter(o => (o.category || '其他') === cat);
  renderOps(filtered, uid);
}

const OP_STATUS_COLORS = {
  tested: '#22c55e',
  partial: '#f59e0b',
  untested: '#6b7280',
  failed: '#ef4444',
};

// 测试状态映射（从 ops-flow 流程图定义 + 实际测试结果提取）
const OP_TEST_STATUS = {
  // 🟢 已测试通过
  'scroll_feed': 'tested',
  'open_video': 'tested',
  'go_back': 'tested',
  'like': 'tested',
  'comment': 'tested',
  'next_video': 'tested',
  'read_field': 'tested',
  'goto_home': 'tested',
  'goto_branch': 'tested',
  'search_input': 'tested',
  // 🟡 部分通过
  'goto_profile': 'partial',
  'follow': 'partial',
  'click_result': 'partial',
  'search_user': 'partial',
  'read_fans': 'partial',
  // 🔴 测试失败
  'collect': 'failed',
  'collect_profile': 'failed',
  'post_comment': 'failed',
  // ⚪ 未测试
  'open_video_new': 'untested',
  'goto_author': 'untested',
  'expand_full': 'untested',
  'open_comments': 'untested',
  'goto_user': 'untested',
  'click_user': 'untested',
  'click_note': 'untested',
  'next_note': 'untested',
};

function getOpStatus(opName) {
  return OP_TEST_STATUS[opName] || 'untested';
}

function renderOps(ops, uid) {
  const listEl = document.getElementById(`opList_${uid}`);
  if (!listEl) return;

  if (!ops.length) {
    listEl.innerHTML = '<div style="color:var(--text2);padding:12px;text-align:center">无匹配操作</div>';
    return;
  }

  let html = '';
  ops.forEach(o => {
    const status = getOpStatus(o.name);
    const color = OP_STATUS_COLORS[status] || '#6b7280';
    const statusText = {tested:'✅已通过', partial:'🟡部分', failed:'🔴失败', untested:'⚪未测'}[status] || '⚪未测';
    const label = o.label || o.name || '?';
    const desc = o.desc || '';
    const requires = o.requires && o.requires[0] !== '*' ? `← ${o.requires[0]}` : '';

    const safeName = o.name.replace(/'/g,"\\'");
    html += `<div onclick="window._showOpDetail('${safeName}','${uid}')" style="cursor:pointer;background:var(--bg3);border-radius:6px;padding:8px;margin-bottom:4px;border:1px solid var(--border)">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color}"></span>
        <span style="font-weight:600;font-size:11px">${label}</span>
        <span style="font-size:9px;color:${color};margin-left:8px;font-weight:600">${statusText}</span>
        <span style="font-size:9px;color:var(--text2);margin-left:auto">${o.name}</span>
      </div>
      <div style="font-size:9px;color:var(--text2)">${desc} ${requires ? ' | ' + requires : ''}</div>
    </div>`;
  });

  listEl.innerHTML = html;
}

// ── 中栏：操作详情 ──
window._showOpDetail = function(opName, uid) {
  const el = document.getElementById(`opDetail_${uid}`);
  const body = document.getElementById(`opDetailBody_${uid}`);
  if (!el || !body) return;

  const op = _allOps.find(o => o.name === opName);
  if (!op) return;

  const status = getOpStatus(opName);
  const statusText = {tested:'✅已通过', partial:'🟡部分', failed:'🔴失败', untested:'⚪未测'}[status] || '⚪未测';
  const label = op.label || opName;
  const desc = op.desc || '暂无描述';
  const requires = (op.requires && op.requires[0] !== '*') ? `前置: ${op.requires.join(', ')}` : '无前置依赖';
  const category = op.category || '其他';
  const params = op.params ? Object.keys(op.params).map(k => `${k}: ${op.params[k]}`).join(', ') : '无参数';
  const returns = op.returns ? op.returns.slice(0,200) : '无返回值';

  el.style.display = 'block';
  body.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
      <span style="font-weight:600;font-size:12px">${label}</span>
      <span style="font-size:10px;color:var(--text2);cursor:pointer" onclick="document.getElementById('opDetail_${uid}').style.display='none'">✕ 关闭</span>
    </div>
    <div style="margin-bottom:4px"><span style="color:var(--text2)">ID:</span> ${opName} · <span style="color:var(--text2)">分类:</span> ${category} · ${statusText}</div>
    <div style="margin-bottom:4px;color:var(--text2)">${desc}</div>
    <div style="margin-bottom:4px;color:var(--text2)">${requires}</div>
    <div style="margin-bottom:6px;color:var(--text2);font-size:9px"><span style="color:var(--text2)">参数:</span> ${params}</div>
    <div style="margin-bottom:6px;color:var(--text2);font-size:9px"><span style="color:var(--text2)">返回:</span> ${returns}</div>
    <div style="display:flex;gap:4px">
      <button id="testBtn_${uid}" onclick="window._testOp('${opName}','${uid}')" style="flex:1;background:#22c55e;color:#fff;border:none;padding:4px;border-radius:4px;cursor:pointer;font-size:10px">🧪 测试此操作</button>
      <div id="opTestResult_${uid}" style="margin-top:4px;font-size:9px;color:var(--text2)"></div>
    </div>`;
};

// 执行单步测试
window._testOp = async function(opName, uid) {
  const btn = document.getElementById('testBtn_'+uid);
  const res = document.getElementById('opTestResult_'+uid);
  if (!btn || !res) return;
  btn.disabled = true;
  btn.textContent = '⏳ 执行中...';
  btn.style.opacity = '0.6';
  res.textContent = '请求中...';

  try {
    // 尝试获取第一个可用的本机账号
    const ar = await fetch('/api/matrix/accounts');
    const accts = await ar.json();
    const accounts = (Array.isArray(accts) ? accts : accts.accounts||[]);
    const localAcct = accounts.find(a => a.is_local) || accounts[0];
    if (!localAcct) { res.textContent = '❌ 无可用账号'; return; }

    const r = await fetch('/api/ops/run', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        type: 'nurture',
        accounts: [localAcct.id],
        params: { blueprint: 'douyin_daily', rounds: 1, single_op: opName },
        wait: true
      })
    });
    const result = await r.json();
    res.textContent = '✅ 已提交: ' + (result.status || result.message || JSON.stringify(result));
  } catch(e) {
    res.textContent = '❌ ' + e.message;
  } finally {
    btn.disabled = false;
    btn.textContent = '🧪 测试此操作';
    btn.style.opacity = '1';
  }
};

// ── 右栏：录制标注 ──
let _recData = {}; // 缓存当前录制数据
let _recNames = {}; // {recordingName: {stepIdx: name}} 缓存命名

// 从 localStorage 加载已保存的命名
try { _recNames = JSON.parse(localStorage.getItem('rec_names')||'{}'); } catch(e) {}
function _saveRecNames() {
  try { localStorage.setItem('rec_names', JSON.stringify(_recNames)); } catch(e) {}
}

async function loadRecList(uid) {
  const selectEl = document.getElementById(`recSelect_${uid}`);
  if (!selectEl) return;
  try {
    const r = await fetch('/api/matrix/record/list');
    const d = await r.json();
    const recs = d.recordings || [];
    selectEl.innerHTML = '<option value="">— 选择录制包 —</option>' +
      recs.map(r => `<option value="${r.name}">🎬 ${r.account} ${r.platform} (${r.steps}步)</option>`).join('');
  } catch(e) {
    selectEl.innerHTML = '<option value="">加载失败</option>';
  }
}

async function showRecSteps(name, uid) {
  const el = document.getElementById(`recSteps_${uid}`);
  if (!el) return;
  try {
    const r = await fetch('/api/matrix/record/detail/' + encodeURIComponent(name));
    const d = await r.json();
    const steps = d.steps || [];
    const analysis = d.analysis || {};
    const actions = analysis.actions || [];

    // 构建 action 索引
    const actMap = {};
    actions.forEach(a => {
      const idx = a.step_after || a.step_before;
      if (!actMap[idx]) actMap[idx] = [];
      actMap[idx].push(a);
    });

    // 缓存数据
    _recData = { steps, actMap, uid, name };

    // 步骤列表（点击可看详情）
    let html = `<div style="font-weight:600;margin-bottom:6px;font-size:11px;display:flex;justify-content:space-between">
      <span>${name}</span>
      <span style="font-size:10px;color:var(--text2)">${steps.length}步</span>
    </div>`;

    html += `<div style="max-height:220px;overflow-y:auto;margin-bottom:6px">`;
    steps.forEach((s, idx) => {
      const acts = actMap[s.step] || [];
      const firstAct = acts[0] || {};
      const actionDesc = (firstAct.action_desc || '浏览').slice(0, 30);
      const autoOp = firstAct.suggested_op || firstAct.action_type || '?';
      const fromMode = firstAct.page_mode || '?';
      const toMode = acts.length ? (actMap[steps[idx+1] ? steps[idx+1].step : -1]||[])[0]?.page_mode || '?' : '?';

      const isActiveIdx = window._recActiveStep;
      html += `<div onclick="window._recShowDetail(${idx})" data-sidx="${idx}"
        style="cursor:pointer;background:${isActiveIdx===idx?'var(--primary)': 'var(--bg3)'};border-radius:4px;padding:5px 6px;margin-bottom:3px;border:1px solid var(--border);display:flex;gap:4px;align-items:center">
        <span style="font-size:9px;font-weight:600;color:${isActiveIdx===idx?'#fff':'var(--text)'}">#${idx+1}</span>
        <span style="font-size:8px;color:${isActiveIdx===idx?'rgba(255,255,255,.7)':'var(--text2)'}">${fromMode}→${toMode}</span>
        <span style="font-size:8px;color:${isActiveIdx===idx?'rgba(255,255,255,.7)':'var(--text2)'};margin-left:auto">${autoOp}</span>
      </div>`;
    });
    html += `</div>`;

    // 详情面板（默认展示第1步）
    html += `<div id="recStepDetail_${uid}" style="font-size:10px"></div>`;
    // 保存按钮 + 状态
    const savedCount = _recNames[name] ? Object.keys(_recNames[name]).length : 0;
    html += `<div style="margin-top:6px;display:flex;gap:4px;align-items:center">
      <button onclick="window._recSaveAll('${uid}')" style="flex:1;background:var(--primary);color:#fff;border:none;padding:4px;border-radius:4px;cursor:pointer;font-size:10px">💾 保存全部命名</button>
      <button onclick="window._recExport('${uid}')" style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;cursor:pointer;font-size:10px">📦 导出蓝图</button>
      <span id="recSaveStatus_${uid}" style="font-size:9px;color:var(--text2);flex-shrink:0">${savedCount > 0 ? '已保存 '+savedCount+' 步' : ''}</span>
    </div>`;
    el.innerHTML = html;

    // 挂载全局函数
    window._recShowDetail = function(idx) { showStepDetail(idx, uid); };
    window._recSetName = function(idx, uid) {
      const inp = document.getElementById(`recNameInput_${idx}_${uid}`);
      const val = inp?.value?.trim();
      if (val) {
        if (!_recNames[_recData.name]) _recNames[_recData.name] = {};
        _recNames[_recData.name][idx] = val;
        document.getElementById(`recNameLabel_${idx}_${uid}`).textContent = val;
      }
    };
    window._recSaveAll = function(uid) {
      // 遍历所有步骤，确保每个输入框的值都被收集
      _recData.steps.forEach((s, idx) => {
        const inp = document.getElementById(`recNameInput_${idx}_${uid}`);
        if (inp && inp.value.trim()) {
          if (!_recNames[_recData.name]) _recNames[_recData.name] = {};
          _recNames[_recData.name][idx] = inp.value.trim();
        }
      });
      _saveRecNames();
      const saved = _recNames[_recData.name] ? Object.keys(_recNames[_recData.name]).length : 0;
      document.getElementById(`recSaveStatus_${uid}`).textContent = '✅ 已保存 '+saved+'/'+_recData.steps.length+' 步命名';
    };
    window._recExport = function(uid) {
      const names = _recNames[_recData.name] || {};
      const namedSteps = _recData.steps.map((s, idx) => ({
        step_id: idx + 1,
        op: names[idx] || '',
        args: {}
      })).filter(s => s.op);
      const account = _recData.name.split('_').slice(1,2).join('_') || 'unknown';
      const blueprint = {
        name: 'recording_' + _recData.name.split('recording_').pop() || 'exported',
        description: '从录制导出：' + _recData.name,
        platform: _recData.steps[0]?.page?.url?.includes('douyin') ? 'douyin' : 'xiaohongshu',
        steps: namedSteps
      };
      const blob = new Blob([JSON.stringify(blueprint, null, 2)], {type: 'application/json'});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = blueprint.name + '.json';
      a.click();
      URL.revokeObjectURL(a.href);
      document.getElementById(`recSaveStatus_${uid}`).textContent = '📦 蓝图已导出: ' + namedSteps.length + ' 步';
    };

    // 显示第1步
    showStepDetail(0, uid);
  } catch(e) {
    el.innerHTML = `<div style="color:var(--red);padding:8px">❌ ${e.message}</div>`;
  }
}

function showStepDetail(idx, uid) {
  const detailEl = document.getElementById(`recStepDetail_${uid}`);
  if (!detailEl || !_recData.steps) return;

  // 切换步骤前，保存当前显示的输入框的值
  if (window._recActiveStep !== undefined && window._recActiveStep !== idx) {
    const curInp = document.getElementById(`recNameInput_${window._recActiveStep}_${uid}`);
    if (curInp && curInp.value.trim()) {
      if (!_recNames[_recData.name]) _recNames[_recData.name] = {};
      _recNames[_recData.name][window._recActiveStep] = curInp.value.trim();
    }
  }
  window._recActiveStep = idx;
  const s = _recData.steps[idx];
  if (!s) return;

  // 更新步骤列表高亮
  document.querySelectorAll(`#recSteps_${uid} [data-sidx]`).forEach(el => {
    const isActive = parseInt(el.dataset.sidx) === idx;
    el.style.background = isActive ? 'var(--primary)' : 'var(--bg3)';
    el.style.color = isActive ? '#fff' : '';
    el.querySelectorAll('span').forEach(sp => {
      if (isActive) sp.style.color = sp.dataset.origColor || (sp.style.color === 'rgb(255,255,255)' ? '' : 'rgba(255,255,255,.7)');
    });
  });

  const acts = (_recData.actMap[s.step] || []);
  const firstAct = acts[0] || {};
  const actionDesc = firstAct.action_desc || '浏览';
  const autoOp = firstAct.suggested_op || firstAct.action_type || '?';
  const savedName = _recNames[_recData.name]?.[idx] || '';
  const defaultName = savedName || autoOp;
  const screenshotUrl = s.screenshot_url || '';
  const pageUrl = s.page ? s.page.url : '';
  const pageText = s.page ? (s.page.text_snippet||'').slice(0,100) : '';
  const nextStep = _recData.steps[idx + 1];
  const features = firstAct.features || [];

  let html = `
    <div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--primary)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <span style="font-weight:600;font-size:11px">步骤 #${idx+1}</span>
        <span style="font-size:9px;color:var(--text2)">操作: ${actionDesc}</span>
      </div>

      <!-- before / after 截图 -->
      <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:6px;margin-bottom:6px">
        <div style="background:rgba(37,99,235,.08);border-radius:4px;padding:4px;border:1px solid rgba(37,99,235,.15)">
          <div style="font-size:8px;color:#3b82f6;font-weight:600;margin-bottom:2px">⬅ 前状态</div>
          <div style="font-size:8px;word-break:break-all;color:var(--text2)">${pageUrl ? pageUrl.slice(0,50) : '(无URL)'}</div>
          ${screenshotUrl ? '<div style="margin-top:2px"><img src="'+screenshotUrl+'" style="max-width:100%;max-height:80px;border-radius:3px;background:var(--bg2)" onerror="this.style.display=\'none\'"></div>' : ''}
        </div>
        <div style="display:flex;align-items:center;font-size:14px;color:var(--text2)">→</div>
        <div style="background:rgba(5,150,105,.08);border-radius:4px;padding:4px;border:1px solid rgba(5,150,105,.15)">
          <div style="font-size:8px;color:#22c55e;font-weight:600;margin-bottom:2px">➡ 后状态</div>
          <div style="font-size:8px;word-break:break-all;color:var(--text2)">${nextStep ? (nextStep.page?.url||'同页').slice(0,50) : '(结束)'}</div>
          ${nextStep && nextStep.screenshot_url ? '<div style="margin-top:2px"><img src="'+nextStep.screenshot_url+'" style="max-width:100%;max-height:80px;border-radius:3px;background:var(--bg2)" onerror="this.style.display=\'none\'"></div>' : ''}
        </div>
      </div>

      <!-- 原子操作命名 -->
      <div style="display:flex;gap:4px;align-items:center">
        <span style="font-size:9px;color:var(--text2)">🏷️ 命名:</span>
        <input id="recNameInput_${idx}_${uid}" value="${defaultName}" style="flex:1;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:3px;font-size:10px" onchange="window._recSetName(${idx},'${uid}')">
        <span id="recNameLabel_${idx}_${uid}" style="display:none">${defaultName}</span>
      </div>

      ${features.length ? '<div style="margin-top:4px;font-size:8px;color:var(--text2)">'+features.map(f => '<code style="background:var(--bg2);padding:1px 3px;border-radius:2px;margin:1px;font-size:8px">'+f.code+'</code>').join('')+'</div>' : ''}
      
      <!-- 步骤导航 -->
      <div style="display:flex;gap:4px;margin-top:6px">
        <button onclick="showStepDetail(${Math.max(0,idx-1)},'${uid}')" ${idx===0?'disabled':''} style="flex:1;background:${idx===0?'var(--bg3)':'var(--primary)'};color:${idx===0?'var(--text2)':'#fff'};border:none;padding:3px;border-radius:3px;cursor:${idx===0?'default':'pointer'};font-size:9px">◀ 上一步</button>
        <button onclick="showStepDetail(${Math.min(_recData.steps.length-1,idx+1)},'${uid}')" ${idx>=_recData.steps.length-1?'disabled':''} style="flex:1;background:${idx>=_recData.steps.length-1?'var(--bg3)':'var(--primary)'};color:${idx>=_recData.steps.length-1?'var(--text2)':'#fff'};border:none;padding:3px;border-radius:3px;cursor:${idx>=_recData.steps.length-1?'default':'pointer'};font-size:9px">下一步 ▶</button>
      </div>
    </div>`;

  detailEl.innerHTML = html;
}

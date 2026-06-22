/**
 * ops-recorder.js — 录制标注视图（对接真实后端API）
 * 
 * 从 /api/matrix/record/* 加载真实录制数据
 * 展示 before → action → after 三层状态
 * 支持人工命名、合并步骤、导出蓝图
 */

export async function loadView(container) {
  const uid = Math.random().toString(36).slice(2, 6);

  container.innerHTML = `
    <div style="padding:12px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">🎬 录制标注</h2>
        <div style="display:flex;gap:6px;font-size:12px">
          <button onclick="_reloadRec('${uid}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 12px;border-radius:6px;cursor:pointer">⟳ 刷新</button>
        </div>
      </div>

      <!-- 录制列表 -->
      <div id="recList_${uid}" style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:12px;margin-bottom:10px">
        <div style="font-size:12px;font-weight:600;margin-bottom:8px">📋 录制包列表</div>
        <div id="recListBody_${uid}"><div class="loading" style="font-size:12px;padding:8px">加载录制列表...</div></div>
      </div>

      <!-- 录制详情 + 标注面板 -->
      <div id="recDetail_${uid}" style="display:none">
        <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:12px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div>
              <span id="recName_${uid}" style="font-size:13px;font-weight:600"></span>
              <span id="recMeta_${uid}" style="font-size:11px;color:var(--text2);margin-left:8px"></span>
            </div>
            <div style="display:flex;gap:6px">
              <button onclick="_exportRec('${uid}')" style="background:var(--primary);color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">📦 导出蓝图</button>
            </div>
          </div>
          <div id="stepsTimeline_${uid}" style="font-size:11px">
            <div class="loading" style="padding:8px">加载步骤...</div>
          </div>
        </div>
      </div>
    </div>`;

  loadRecList(uid);

  // ── 全局函数 ──
  window._reloadRec = function(uid) { loadRecList(uid); };
  window._selectRec = function(name, uid) { showRecDetail(name, uid); };
  window._renameStep = function(idx, uid) {
    var el = document.getElementById(`stepLabel_${idx}_${uid}`);
    var newName = prompt('输入操作名称（如: like, collect, post_comment）:', el?.dataset.op || '');
    if (newName && el) { el.textContent = newName; el.dataset.op = newName; }
  };
  window._exportRec = function(uid) { exportBlueprint(uid); };
  window._mergeSteps = function(idx, uid) {
    var nextEl = document.getElementById(`stepBlock_${idx+1}_${uid}`);
    if (!nextEl) { alert('没有下一步可合并'); return; }
    if (!confirm('合并步骤 '+(idx+1)+' 和 '+(idx+2)+' ？')) return;
    nextEl.style.display = 'none';
    var sepEl = document.getElementById(`stepSep_${idx}_${uid}`);
    if (sepEl) sepEl.style.display = 'none';
    alert('✅ 已合并（显示中隐藏了下一步，导出时会合并操作）');
  };
}

// ── 加载录制列表 ──
async function loadRecList(uid) {
  var body = document.getElementById(`recListBody_${uid}`);
  if (!body) return;
  try {
    var r = await fetch('/api/matrix/record/list');
    var d = await r.json();
    var recs = d.recordings || [];
    if (!recs.length) {
      body.innerHTML = '<div style="font-size:12px;color:var(--text2);padding:8px">暂无录制记录</div>';
      return;
    }
    body.innerHTML = `<table style="width:100%;font-size:11px;border-collapse:collapse">
      <thead><tr style="border-bottom:1px solid var(--border)">
        <th style="padding:4px 6px;text-align:left">名称</th>
        <th style="padding:4px 6px;text-align:left">平台</th>
        <th style="padding:4px 6px;text-align:left">账号</th>
        <th style="padding:4px 6px;text-align:center">步数</th>
        <th style="padding:4px 6px;text-align:center">时长</th>
        <th style="padding:4px 6px;text-align:center">操作</th>
      </tr></thead>
      <tbody>${recs.map(function(r){return `
        <tr style="border-bottom:1px solid var(--border)">
          <td style="padding:4px 6px;font-weight:500">${r.name}</td>
          <td style="padding:4px 6px">${r.platform==='douyin'?'🎵':'📕'} ${r.platform}</td>
          <td style="padding:4px 6px;color:var(--text2)">${r.account}</td>
          <td style="padding:4px 6px;text-align:center">${r.steps}</td>
          <td style="padding:4px 6px;text-align:center;color:var(--text2)">${Math.round(r.duration)}s</td>
          <td style="padding:4px 6px;text-align:center">
            <button onclick="window._selectRec('${r.name}','${uid}')" style="background:none;border:none;cursor:pointer;font-size:12px;color:var(--primary)">📝 标注</button>
          </td>
        </tr>`}).join('')}</tbody></table>`;
  } catch(e) {
    body.innerHTML = '<div style="color:var(--red);padding:8px;font-size:12px">❌ 加载失败: '+e.message+'</div>';
  }
}

// ── 显示录制详情 + 标注 ──
async function showRecDetail(name, uid) {
  var detailEl = document.getElementById(`recDetail_${uid}`);
  var nameEl = document.getElementById(`recName_${uid}`);
  var metaEl = document.getElementById(`recMeta_${uid}`);
  var timelineEl = document.getElementById(`stepsTimeline_${uid}`);
  if (!detailEl) return;

  detailEl.style.display = 'block';
  nameEl.textContent = `📹 ${name}`;

  try {
    var r = await fetch('/api/matrix/record/detail/'+encodeURIComponent(name));
    var d = await r.json();
    var meta = d.meta || {};
    var steps = d.steps || [];
    var analysis = d.analysis || {};
    var actions = analysis.actions || [];

    metaEl.textContent = `${meta.platform||'?'} · ${meta.account_id||'?'} · ${steps.length}步 · ${Math.round(meta.duration||0)}s`;

    // 构建 action 索引
    var actMap = {};
    actions.forEach(function(a){
      var idx = a.step_after || a.step_before;
      if (!actMap[idx]) actMap[idx] = [];
      actMap[idx].push(a);
    });

    // 状态流概览
    var html = '<div style="margin-bottom:10px;font-size:10px;color:var(--text2)">状态流: ';
    html += steps.map(function(s,i){
      var acts = actMap[s.step] || [];
      var fromMode = acts.length ? (acts[0].page_mode||'?') : '?';
      var nextActs = actMap[steps[i+1] ? steps[i+1].step : -1] || [];
      var toMode = nextActs.length ? (nextActs[0].page_mode||'?') : '?';
      return `<span style="display:inline-block;padding:1px 6px;margin:1px;background:var(--bg3);border-radius:3px">${fromMode} → ${toMode}</span>`;
    }).join(' ');
    html += '</div>';

    // 每一步
    steps.forEach(function(s, idx){
      var acts = actMap[s.step] || [];
      var firstAct = acts[0] || {};
      var inferred = firstAct.inferred_action || {};
      var actionDesc = firstAct.action_desc || '浏览/等待';
      var autoOp = firstAct.action_type || '';
      var fromState = firstAct.page_mode || '?';
      var nextStep = steps[idx+1];
      var nextActs = nextStep ? (actMap[nextStep.step] || []) : [];
      var toState = nextActs.length ? (nextActs[0].page_mode||'?') : '?';
      var screenshotUrl = s.screenshot_url || '';
      var pageUrl = s.page ? s.page.url : '';
      var pageText = s.page ? (s.page.text_snippet||'').slice(0,80) : '';

      html += `<div id="stepBlock_${idx}_${uid}" style="background:var(--bg3);border-radius:6px;padding:10px;margin-bottom:8px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <span style="font-size:11px;font-weight:600">步骤 ${idx+1}: ${fromState} → ${toState}</span>
          <div style="display:flex;gap:4px;font-size:10px">
            <button onclick="window._renameStep(${idx},'${uid}')" style="background:var(--primary);color:#fff;border:none;padding:2px 8px;border-radius:4px;cursor:pointer">✏️ 命名</button>
            <button onclick="window._mergeSteps(${idx},'${uid}')" style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:2px 8px;border-radius:4px;cursor:pointer">🔗 合并下步</button>
          </div>
        </div>

        <!-- before → action → after 三栏 -->
        <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:start">
          <div style="background:rgba(37,99,235,.08);border-radius:5px;padding:6px;border:1px solid rgba(37,99,235,.15)">
            <div style="font-size:9px;color:#3b82f6;font-weight:600;margin-bottom:2px">⬅ 前状态</div>
            <div style="font-size:10px;word-break:break-all">${pageUrl ? '<span style="color:var(--text2)">URL:</span> '+pageUrl.slice(0,60) : '<span style="color:var(--text2)">(无URL)</span>'}</div>
            ${pageText ? '<div style="font-size:9px;color:var(--text2);margin-top:2px">📄 '+pageText+'</div>' : ''}
            ${screenshotUrl ? '<div style="margin-top:4px"><img src="'+screenshotUrl+'" style="max-width:100%;max-height:120px;border-radius:4px;background:var(--bg3)" onerror="this.style.display=\'none\'"></div>' : ''}
          </div>

          <div style="display:flex;align-items:center;padding:0 4px;font-size:16px;color:var(--text2)">→</div>

          <div style="background:rgba(5,150,105,.08);border-radius:5px;padding:6px;border:1px solid rgba(5,150,105,.15)">
            <div style="font-size:9px;color:#22c55e;font-weight:600;margin-bottom:2px">➡ 后状态</div>
            <div style="font-size:10px">${nextStep ? (nextStep.page ? nextStep.page.url.slice(0,60) : '同页') : '(结束)'}</div>
            ${nextStep && nextStep.screenshot_url ? '<div style="margin-top:4px"><img src="'+nextStep.screenshot_url+'" style="max-width:100%;max-height:120px;border-radius:4px;background:var(--bg3)" onerror="this.style.display=\'none\'"></div>' : ''}
          </div>
        </div>

        <!-- 操作详情 -->
        <div style="margin-top:6px;display:flex;gap:8px;align-items:flex-start;flex-wrap:wrap">
          <div style="background:var(--bg2);border-radius:4px;padding:4px 8px;font-size:10px;flex:1">
            <span style="color:var(--text2)">🖱 操作:</span> ${actionDesc}
            ${inferred.coords ? ' <span style="color:var(--text2)">坐标:</span> ('+inferred.coords.x+','+inferred.coords.y+')' : ''}
            ${firstAct.text_changed ? '<span style="color:var(--green);margin-left:4px">📝 文本变化</span>' : ''}
            ${firstAct.url_changed ? '<span style="color:#3b82f6;margin-left:4px">🔗 URL变化</span>' : ''}
          </div>
          <div style="display:flex;align-items:center;gap:4px;font-size:11px">
            <span style="color:var(--text2)">🏷️ 原子操作名:</span>
            <span id="stepLabel_${idx}_${uid}" data-op="${autoOp}" style="font-weight:600;background:var(--bg2);padding:2px 8px;border-radius:4px;cursor:pointer;border:1px dashed var(--border)" onclick="window._renameStep(${idx},'${uid}')">${autoOp || '点击命名...'}</span>
          </div>
        </div>

        <!-- 特征代码 -->
        ${firstAct.features && firstAct.features.length ? '<div style="margin-top:4px;font-size:9px;color:var(--text2)">'+
          firstAct.features.map(function(f){return '<code style="background:var(--bg2);padding:1px 4px;border-radius:2px;margin:1px">'+f.code+'</code>'}).join('')+
        '</div>' : ''}

      </div>`;

      // 步骤间分隔箭头
      if (idx < steps.length - 1) {
        html += `<div id="stepSep_${idx}_${uid}" style="text-align:center;padding:2px 0;color:var(--text2);font-size:14px">↓</div>`;
      }
    });

    // 底部导出
    html += `<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:4px">
      <span style="font-size:10px;color:var(--text2);flex:1">💡 点击名称命名，连续步骤可合并</span>
      <button onclick="window._exportRec('${uid}')" style="background:var(--primary);color:#fff;border:none;padding:5px 14px;border-radius:6px;cursor:pointer;font-size:12px">📦 导出为蓝图</button>
    </div>`;

    timelineEl.innerHTML = html;

  } catch(e) {
    timelineEl.innerHTML = '<div style="color:var(--red);padding:8px;font-size:12px">❌ 加载失败: '+e.message+'</div>';
  }
}

// ── 导出蓝图 ──
async function exportBlueprint(uid) {
  var steps = document.querySelectorAll('[id^="stepLabel_"]');
  var ops = [];
  steps.forEach(function(el){
    var name = el.dataset.op || el.textContent;
    if (name && name !== '点击命名...') ops.push(name);
  });
  var name = prompt('蓝图名称:', 'recording_export');
  if (!name) return;
  try {
    var r = await fetch('/api/matrix/blueprints', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        name: name,
        description: '从录制标注导出',
        platform: 'douyin',
        steps: ops.map(function(o){return {name: o};})
      })
    });
    if (r.ok) alert('✅ 蓝图 "'+name+'" 已创建 ('+ops.length+'步)');
    else alert('❌ 创建失败: '+(await r.json()).detail);
  } catch(e) { alert('❌ '+e.message); }
}

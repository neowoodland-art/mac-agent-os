/**
 * ops-recorder.js — 录制标注（完整版）
 * 
 * 功能：录制列表 → 选择录制 → 逐步骤标注
 *   - 步骤列表（点击切换）
 *   - before → action → after 三栏展示
 *   - 自动识别原子操作（blueprint_suggestions）
 *   - 内联命名 + 自动保存（localStorage）
 *   - 上一步/下一步导航 + 序号跳转
 *   - 导出蓝图
 */
export async function loadView(container) {
  const uid = Math.random().toString(36).slice(2, 6);
  let _recording = null;
  let _names = {};

  // 加载已保存命名
  try { _names = JSON.parse(localStorage.getItem('rec_names')||'{}'); } catch(e) {}

  container.innerHTML = `
    <div style="padding:12px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">🎬 录制标注</h2>
        <div style="display:flex;gap:6px;font-size:12px">
          <button onclick="_reloadRec('${uid}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 12px;border-radius:6px;cursor:pointer">⟳ 刷新</button>
        </div>
      </div>

      <!-- 录制列表（初始可见） -->
      <div id="recList_${uid}" style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:12px;margin-bottom:10px">
        <div style="font-size:12px;font-weight:600;margin-bottom:8px">📋 录制包列表</div>
        <div id="recListBody_${uid}"><div class="loading" style="font-size:12px;padding:8px">加载录制列表...</div></div>
      </div>

      <!-- 录制详情面板（选择后显示） -->
      <div id="recDetail_${uid}" style="display:none">
        <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:12px">
          <!-- 标题行 -->
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div>
              <span id="recName_${uid}" style="font-size:13px;font-weight:600"></span>
              <span id="recMeta_${uid}" style="font-size:11px;color:var(--text2);margin-left:8px"></span>
            </div>
            <button onclick="_recBack('${uid}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">← 返回列表</button>
          </div>

          <!-- 步骤概览条 -->
          <div style="display:flex;gap:4px;margin-bottom:8px;overflow-x:auto;padding:2px 0" id="recStepBar_${uid}"></div>

          <!-- 当前步骤详情 -->
          <div id="recStepDetail_${uid}" style="font-size:11px">选择步骤查看详情</div>
        </div>
      </div>
    </div>`;

  // ── 全局函数 ──
  window._reloadRec = function(uid) { loadRecList(uid); };
  window._selectRec = function(name, uid) { showRecDetail(name, uid); };
  window._recBack = function(uid) {
    document.getElementById(`recDetail_${uid}`).style.display = 'none';
    document.getElementById(`recList_${uid}`).style.display = '';
  };
  window._goStep = function(idx, uid) { showStep(idx, uid); };

  // 初始加载列表
  loadRecList(uid);

  // ── 加载录制列表 ──
  async function loadRecList(uid) {
    const body = document.getElementById(`recListBody_${uid}`);
    if (!body) return;
    try {
      const r = await fetch('/api/matrix/record/list');
      const d = await r.json();
      const recs = d.recordings || [];
      if (!recs.length) {
        body.innerHTML = '<div style="color:var(--text2);padding:12px;text-align:center">暂无录制包</div>';
        return;
      }
      body.innerHTML = `<table style="width:100%;border-collapse:collapse;font-size:12px">
        <thead><tr style="font-size:10px;color:var(--text2);border-bottom:1px solid var(--border)">
          <th style="padding:4px 6px;text-align:left">名称</th>
          <th style="padding:4px 6px;text-align:left">平台</th>
          <th style="padding:4px 6px;text-align:left">账号</th>
          <th style="padding:4px 6px;text-align:center">步数</th>
          <th style="padding:4px 6px;text-align:center">时长</th>
          <th style="padding:4px 6px;text-align:center">操作</th>
        </tr></thead><tbody>${
          recs.map(r => `<tr style="border-bottom:1px solid var(--border)">
            <td style="padding:4px 6px;font-weight:500">${r.name}</td>
            <td style="padding:4px 6px">${r.platform==='douyin'?'🎵':'📕'} ${r.platform}</td>
            <td style="padding:4px 6px;color:var(--text2)">${r.account}</td>
            <td style="padding:4px 6px;text-align:center">${r.steps}</td>
            <td style="padding:4px 6px;text-align:center;color:var(--text2)">${Math.round(r.duration)}s</td>
            <td style="padding:4px 6px;text-align:center">
              <button onclick="window._selectRec('${r.name}','${uid}')" style="background:none;border:none;cursor:pointer;font-size:12px;color:var(--primary)">📝 标注</button>
            </td>
          </tr>`).join('')
        }</tbody></table>`;
    } catch(e) {
      body.innerHTML = `<div style="color:var(--red);padding:8px;font-size:12px">❌ 加载失败: ${e.message}</div>`;
    }
  }

  // ── 显示录制详情 ──
  async function showRecDetail(name, uid) {
    document.getElementById(`recList_${uid}`).style.display = 'none';
    const detailEl = document.getElementById(`recDetail_${uid}`);
    detailEl.style.display = '';
    document.getElementById(`recName_${uid}`).textContent = `📹 ${name}`;

    try {
      const r = await fetch('/api/matrix/record/detail/' + encodeURIComponent(name));
      const d = await r.json();
      // API 返回: {meta, steps, analysis: {actions, blueprint_suggestions}}
      const meta = d.meta || {};
      const steps = d.steps || [];
      const analysis = d.analysis || {};
      const actions = analysis.actions || [];
      const suggestions = analysis.blueprint_suggestions || [];

      _recording = { name, meta, steps, actions, suggestions };

      document.getElementById(`recMeta_${uid}`).textContent =
        `${meta.platform||'?'} · ${meta.account_id||'?'} · ${steps.length}步 · ${Math.round(meta.duration||0)}s`;

      // 构建 action 索引（按 step 编号）
      const actMap = {};
      actions.forEach(a => {
        const idx = a.step_after || a.step_before;
        if (!actMap[idx]) actMap[idx] = [];
        actMap[idx].push(a);
      });
      _recording.actMap = actMap;

      // 构建 suggestion 索引
      const sugMap = {};
      suggestions.forEach(s => { sugMap[s.step] = s; });
      _recording.sugMap = sugMap;

      // 渲染步骤概览条
      renderStepBar(uid);
      // 显示第1步
      showStep(0, uid);
    } catch(e) {
      document.getElementById(`recStepDetail_${uid}`).innerHTML =
        `<div style="color:var(--red);font-size:12px;padding:8px">❌ ${e.message}</div>`;
    }
  }

  // ── 步骤概览条 ──
  function renderStepBar(uid) {
    const bar = document.getElementById(`recStepBar_${uid}`);
    if (!bar || !_recording) return;
    // 显示状态流摘要
    const acts = _recording.actions;
    const modes = [];
    acts.forEach(a => {
      if (a.page_mode && modes.indexOf(a.page_mode) === -1) modes.push(a.page_mode);
    });
    bar.innerHTML = `<span style="font-size:10px;color:var(--text2);white-space:nowrap;margin-right:6px">状态流:</span>
      <div style="display:flex;gap:3px;font-size:9px;flex-wrap:nowrap">${
        _recording.steps.slice(0,20).map((s, i) => {
          const acts = (_recording.actMap[s.step] || []);
          const m = acts.length ? (acts[0].page_mode || '?') : '?';
          const sug = _recording.sugMap[s.step];
          const status = sug ? (sug.confidence === 'high' ? '#22c55e' : '#f59e0b') : '#6b7280';
          return `<span onclick="showStep(${i},'${uid}')" id="stepDot_${i}_${uid}"
            style="cursor:pointer;display:inline-block;width:18px;height:18px;line-height:18px;text-align:center;
            border-radius:3px;font-size:8px;background:${status};color:#fff;opacity:${i===0?'1':'0.6'}"
            title="步骤${i+1}: ${m}">${i+1}</span>`;
        }).join('')
      }</div>`;
  }

  // ── 显示某一步 ──
  function showStep(idx, uid) {
    const detailEl = document.getElementById(`recStepDetail_${uid}`);
    if (!detailEl || !_recording || !_recording.steps[idx]) return;

    // 高亮当前步骤圆点
    document.querySelectorAll(`[id^="stepDot_"]`).forEach(el => {
      el.style.opacity = el.id === `stepDot_${idx}_${uid}` ? '1' : '0.6';
    });

    // 切换前保存当前步骤命名
    if (window._recordingStepIdx !== undefined && window._recordingStepIdx !== idx) {
      const inp = document.getElementById(`nameInput_${window._recordingStepIdx}_${uid}`);
      if (inp && inp.value.trim()) {
        if (!_names[_recording.name]) _names[_recording.name] = {};
        _names[_recording.name][window._recordingStepIdx] = inp.value.trim();
      }
    }
    window._recordingStepIdx = idx;

    const s = _recording.steps[idx];
    const acts = (_recording.actMap[s.step] || []);
    const firstAct = acts[0] || {};
    const sug = _recording.sugMap[s.step] || {};
    const actionDesc = firstAct.action_desc || '浏览/等待';
    const autoOp = sug.suggested_op || firstAct.action_type || '';
    const fromState = firstAct.page_mode || '?';
    const nextStep = _recording.steps[idx + 1];
    const toState = nextStep ? ((_recording.actMap[nextStep.step]||[])[0]?.page_mode || '?') : '?';
    const screenshotUrl = s.screenshot_url || '';
    const pageUrl = s.page ? s.page.url : '';
    const pageText = s.page ? (s.page.text_snippet||'').slice(0,60) : '';
    const features = firstAct.features || [];
    const inferred = firstAct.inferred_action || {};
    const savedName = _names[_recording.name]?.[idx] || '';

    // 原子操作候选列表（用于命名建议）
    const opCandidates = ['', 'goto_home', 'scroll_feed', 'open_video', 'like', 'collect',
      'comment', 'follow', 'go_back', 'next_video', 'search_input', 'read_field',
      'click_result', 'send_comment', 'post_comment', 'expand_full', 'goto_profile',
      'goto_branch', 'search_user', 'close_modal', 'wait_watch'];

    detailEl.innerHTML = `
      <div style="display:flex;gap:4px;margin-bottom:6px">
        <button onclick="showStep(${Math.max(0, idx-1)},'${uid}')" ${idx===0?'disabled':''}
          style="flex:1;background:${idx===0?'var(--bg3)':'#6366f1'};color:${idx===0?'var(--text2)':'#fff'};border:none;padding:4px;border-radius:4px;cursor:${idx===0?'default':'pointer'};font-size:10px">◀ 上一步</button>
        <span style="font-size:10px;color:var(--text2);padding:4px">${idx+1} / ${_recording.steps.length}</span>
        <button onclick="showStep(${Math.min(_recording.steps.length-1, idx+1)},'${uid}')" ${idx>=_recording.steps.length-1?'disabled':''}
          style="flex:1;background:${idx>=_recording.steps.length-1?'var(--bg3)':'#6366f1'};color:${idx>=_recording.steps.length-1?'var(--text2)':'#fff'};border:none;padding:4px;border-radius:4px;cursor:${idx>=_recording.steps.length-1?'default':'pointer'};font-size:10px">下一步 ▶</button>
      </div>

      <div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;margin-bottom:6px">
          <span style="font-weight:600;font-size:11px">步骤 ${idx+1}: ${fromState} → ${toState}</span>
          <span style="font-size:10px;color:var(--text2)">🖱 ${actionDesc}</span>
        </div>

        <!-- before / after 截图 -->
        <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:6px;margin-bottom:6px">
          <div style="background:rgba(37,99,235,.08);border-radius:4px;padding:4px;border:1px solid rgba(37,99,235,.15)">
            <div style="font-size:8px;color:#3b82f6;font-weight:600;margin-bottom:2px">⬅ 前状态</div>
            <div style="font-size:8px;color:var(--text2);word-break:break-all">${pageUrl ? pageUrl.slice(0,60) : '(无URL)'}</div>
            ${screenshotUrl ? `<div style="margin-top:2px"><img src="${screenshotUrl}" style="max-width:100%;max-height:80px;border-radius:3px;background:var(--bg2)" onerror="this.style.display='none'"></div>` : ''}
          </div>
          <div style="display:flex;align-items:center;font-size:14px;color:var(--text2)">→</div>
          <div style="background:rgba(5,150,105,.08);border-radius:4px;padding:4px;border:1px solid rgba(5,150,105,.15)">
            <div style="font-size:8px;color:#22c55e;font-weight:600;margin-bottom:2px">➡ 后状态</div>
            <div style="font-size:8px;color:var(--text2)">${nextStep ? (nextStep.page?.url||'同页').slice(0,60) : '(结束)'}</div>
            ${nextStep && nextStep.screenshot_url ? `<div style="margin-top:2px"><img src="${nextStep.screenshot_url}" style="max-width:100%;max-height:80px;border-radius:3px;background:var(--bg2)" onerror="this.style.display='none'"></div>` : ''}
          </div>
        </div>

        <!-- 原子操作命名 -->
        <div style="margin-bottom:4px">
          <div style="font-size:9px;color:var(--text2);margin-bottom:2px">🏷️ 原子操作名:</div>
          <div style="display:flex;gap:4px">
            <input id="nameInput_${idx}_${uid}" value="${savedName || autoOp}"
              style="flex:1;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:3px;font-size:10px"
              onchange="var v=this.value.trim();if(v){if(!_names['${_recording.name}'])_names['${_recording.name}']={};_names['${_recording.name}'][${idx}]=v;localStorage.setItem('rec_names',JSON.stringify(_names))}">
            <select style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px;border-radius:3px;font-size:9px;max-width:120px"
              onchange="var inp=document.getElementById('nameInput_${idx}_${uid}');if(this.value){inp.value=this.value;inp.onchange()};this.value=''">
              <option value="">↕ 快速选</option>
              ${opCandidates.filter(c => c !== (savedName||autoOp)).map(c => `<option value="${c}">${c||'清空'}</option>`).join('')}
            </select>
          </div>
        </div>

        <!-- 特征代码 -->
        ${features.length ? `<div style="margin-top:4px;font-size:8px;color:var(--text2)">${features.map(f => `<code style="background:var(--bg2);padding:1px 3px;border-radius:2px;margin:1px;font-size:8px">${f.code}</code>`).join('')}</div>` : ''}

        <!-- 推断详情 -->
        <div style="margin-top:4px;display:flex;gap:6px;font-size:9px;color:var(--text2)">
          ${inferred.coords ? `<span>📌 坐标: (${inferred.coords.x},${inferred.coords.y})</span>` : ''}
          ${firstAct.url_changed ? '<span>🔗 URL变化</span>' : ''}
          ${firstAct.text_changed ? '<span>📝 文本变化</span>' : ''}
          ${inferred.trigger ? `<span>⚡ ${inferred.trigger}</span>` : ''}
        </div>
      </div>

      <!-- 保存/导出按钮 -->
      <div style="margin-top:6px;display:flex;gap:4px">
        <button onclick="var nms=_names['${_recording.name}'];var c=Object.keys(nms||{}).length;localStorage.setItem('rec_names',JSON.stringify(_names));document.getElementById('recSaveStatus_${uid}').textContent='✅ 已保存 '+c+'/'+_recording.steps.length+' 步'" style="flex:1;background:var(--primary);color:#fff;border:none;padding:4px;border-radius:4px;cursor:pointer;font-size:10px">💾 保存全部命名</button>
        <button onclick="_exportRec('${uid}')" style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">📦 导出蓝图</button>
      </div>
      <div id="recSaveStatus_${uid}" style="margin-top:2px;font-size:9px;color:var(--text2)"></div>
    `;
  }

  // ── 导出蓝图 ──
  window._exportRec = function(uid) {
    if (!_recording) return;
    const name = _recording.name;
    const names = _names[name] || {};
    const savedCount = Object.keys(names).length;
    if (savedCount === 0) { alert('请先命名步骤再导出'); return; }

    const bpName = prompt('蓝图名称:', '录制_' + name.replace('recording_','').slice(0,20));
    if (!bpName) return;

    const steps = Object.keys(names).sort((a,b) => a-b).map(idx => ({
      step_id: parseInt(idx) + 1,
      op: names[idx],
      args: {}
    }));

    const blueprint = {
      name: bpName,
      description: '从录制标注自动导出: ' + name,
      platform: _recording.meta.platform || 'douyin',
      steps: steps
    };

    // 下载为 JSON 文件
    const blob = new Blob([JSON.stringify(blueprint, null, 2)], {type: 'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = bpName + '.json';
    a.click();
    URL.revokeObjectURL(a.href);

    document.getElementById(`recSaveStatus_${uid}`).textContent = '📦 蓝图已导出: ' + steps.length + ' 步';
  };
}

// ════════════════════════════════════════════════════════
// 命令与任务 TAB
// ════════════════════════════════════════════════════════

function switchCmdTab(tab, el) {
  document.querySelectorAll('.cmd-tab').forEach(t => {
    t.style.borderBottom = '2px solid transparent';
    t.style.color = '#8b8fa3';
  });
  el.style.borderBottom = '2px solid #6366f1';
  el.style.color = '#e1e4f0';
  ['cmd-run-content','cmd-comment-content','cmd-schedule-content','cmd-collect-content','cmd-corpus-content','cmd-nurture-content'].forEach(id => {
    document.getElementById(id).style.display = id === tab+'-content' ? 'block' : 'none';
  });
}

async function loadMatrixCommands() {
  // 加载批量执行内容（复用原始 loadMatrixRun 的渲染结果）
  const runEl = document.getElementById('matrixRunContent2');
  if (runEl) {
    // 先渲染原始内容
    await loadMatrixRun();
    // 把渲染结果复制到命令与任务的 TAB 中
    const origEl = document.getElementById('matrixRunContent');
    if (origEl && origEl.innerHTML) {
      runEl.innerHTML = origEl.innerHTML;
      // 持续监控同步（原始内容变化时自动更新）
      if (!window._cmdRunObserver) {
        window._cmdRunObserver = new MutationObserver(() => {
          document.getElementById('matrixRunContent2').innerHTML = origEl.innerHTML;
        });
        window._cmdRunObserver.observe(origEl, { childList: true, subtree: true, characterData: true });
      }
    }
  }
  // 加载定时任务列表
  refreshScheduleList();
  // 填充定时任务的账号下拉
  const schedAcct = document.getElementById('schedAccount');
  if (schedAcct) {
    try {
      const r = await fetch('/api/matrix/sms/accounts');
      const d = await r.json();
      schedAcct.innerHTML = '<option value="">选账号</option>' +
        (d.accounts||[]).filter(a => a.is_local).map(a =>
          '<option value="'+a.id+'">'+(a.platform==='xiaohongshu'?'📕':'🎵')+' '+a.nickname+'</option>').join('');
    } catch(e) { /* ignore */ }
  }

  // 语料库 TAB 绑定（同步原始 corpusContent 到 corpusContent3）
  const corpusEl3 = document.getElementById('corpusContent3');
  const corpusOrig = document.getElementById('corpusContent');
  if (corpusEl3 && corpusOrig && !window._corpusObs3) {
    window._corpusObs3 = new MutationObserver(() => {
      const target = document.getElementById('corpusContent3');
      const src = document.getElementById('corpusContent');
      if (target && src) target.innerHTML = src.innerHTML;
    });
    window._corpusObs3.observe(corpusOrig, { childList: true, subtree: true, characterData: true });
    // 强制加载语料库（无论原始页面是否已加载）
    if (typeof loadCorpus === 'function') {
      loadCorpus().catch(e => console.error('corpus load err', e));
    }
    corpusEl3.innerHTML = corpusOrig.innerHTML || '<div class="loading">加载语料库...</div>';
  }

  // 加载采集模块账号列表（复用养号执行的折叠式选择器）
  try {
    const data = await _loadAccounts();
    _collectAccounts = data.accounts || [];
    _renderAccountSelector('collectList', {_data: data, height: '350px'});
    document.getElementById('collectSelCount2').textContent = '已选 ' + _getSelectedAccounts().length + ' 个';
  } catch(e) { /* ignore */ }

  // 填充定向评论的账号选择器（折叠式）
  try {
    const data = await _loadAccounts();
    _renderAccountSelector('commentTaskAccountList', {_data: data, height: '200px'});
    document.getElementById('commentTaskSelCount').textContent = '已选 ' + _getSelectedAccounts().length + ' 个';
  } catch(e) { /* ignore */ }
}

async function cmdRunCommentTask() {
  const url = document.getElementById('cmdTaskUrl')?.value.trim();
  if (!url) { alert('请填写视频链接'); return; }
  const direction = document.getElementById('cmdTaskDirection')?.value || '';
  const selected = _getSelectedAccounts();
  const account = selected.length ? selected[0].id : '';
  const resultEl = document.getElementById('cmdTaskResult');
  if (resultEl) resultEl.innerHTML = '⏳ 执行中...';
  try {
    const r = await fetch('/api/matrix/task/run', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({type:'comment', url, direction, account})
    });
    const d = await r.json();
    if (resultEl) {
      if (d.status === 'ok') {
        resultEl.innerHTML = '<span style="color:var(--green)">✅ 完成！成功 '+d.success+'/'+d.total+' 步 ('+d.duration+'s)</span>'+
          '<div style="font-size:10px;color:var(--text2);margin-top:2px">'+d.task_summary+'</div>';
      } else {
        resultEl.innerHTML = '<span style="color:var(--red)">❌ '+(d.errors||[d.detail||'失败']).join('; ')+'</span>';
      }
    }
  } catch(e) { if (resultEl) resultEl.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>'; }
}

// ── 从定时任务页面创建 WorkBuddy 任务 ──
async function createAutoTaskFromSchedule() {
  const target = document.getElementById('autoNewTarget')?.value;
  const prompt = document.getElementById('autoNewPrompt')?.value.trim();
  if (!target) { alert('请选择目标机器'); return; }
  if (!prompt) { alert('请输入提示词'); return; }
  try {
    const r = await fetch('/api/kb/automations', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({target, type:'custom', params:prompt})
    });
    const d = await r.json();
    if (d.status === 'ok') {
      alert('✅ 任务已创建');
      document.getElementById('autoNewPrompt').value = '';
      refreshScheduleList();
    } else {
      alert('❌ ' + (d.error || '创建失败'));
    }
  } catch(e) { alert('❌ ' + e.message); }
}
// ── 导出（防 Rollup tree-shake）──
window.cmdRunCommentTask = cmdRunCommentTask;
window.createAutoTaskFromSchedule = createAutoTaskFromSchedule;
window.loadMatrixCommands = loadMatrixCommands;
window.switchCmdTab = switchCmdTab;
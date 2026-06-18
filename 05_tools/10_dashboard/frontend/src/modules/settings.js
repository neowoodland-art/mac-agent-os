// ════════════════════════════════════════════════════════
// 定时任务
// ════════════════════════════════════════════════════════

async function refreshScheduleList() {
  const listEl = document.getElementById('scheduleList');
  const histEl = document.getElementById('scheduleHistory');
  const statusEl = document.getElementById('scheduleStatus');
  // 加载任务列表
  if (listEl) {
    try {
      const r = await fetch('/api/matrix/schedules');
      const d = await r.json();
      const scheds = d.schedules || {};
      const entries = Object.entries(scheds);
      if (!entries.length) {
        listEl.innerHTML = '<div style="color:var(--text2);padding:10px;text-align:center">暂无定时任务，在上方添加</div>';
      } else {
        listEl.innerHTML = entries.map(([sid, s]) =>
          '<div style="background:var(--bg3);border-radius:4px;padding:6px 8px;border:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;font-size:11px;margin-bottom:3px">' +
          '<div><strong>' + sid + '</strong> <span style="color:var(--text2)">' + (s.account||'') + ' → ' + (s.blueprint||'') + '</span></div>' +
          '<div style="display:flex;align-items:center;gap:6px">' +
          '<span style="color:#6366f1">' + (s.time||'') + '</span>' +
          '<span style="color:var(--text2);font-size:10px">' + (s.days||'每天') + '</span>' +
          '<span style="cursor:pointer" onclick="scheduleToggle(\''+sid+'\',' + (!s.enabled) + ')">' + (s.enabled ? '🟢' : '⚪') + '</span>' +
          '<span style="cursor:pointer;color:var(--red);font-size:10px" onclick="scheduleDelete(\''+sid+'\')">✕</span>' +
          '</div></div>'
        ).join('');
      }
    } catch(e) { if (listEl) listEl.innerHTML = '<span style="color:var(--red)">'+e.message+'</span>'; }
  }
  // 加载历史
  if (histEl) {
    try {
      const r = await fetch('/api/matrix/schedules/history');
      const d = await r.json();
      const hist = d.history || [];
      if (!hist.length) {
        histEl.innerHTML = '<div style="color:var(--text2);padding:6px">暂无执行记录</div>';
      } else {
        histEl.innerHTML = hist.map(e =>
          '<div style="padding:3px 0;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;font-size:10px">' +
          '<span>' + (e.timestamp||'').slice(0,16) + ' ' + (e.schedule_id||'') + '</span>' +
          '<span>' + (e.error ? '❌ '+e.error.slice(0,20) : (e.status||'✅')) + ' ' + (e.success||0)+'/'+((e.success||0)+(e.failed||0)) + ' ' + (e.duration||0)+'s</span>' +
          '</div>'
        ).join('');
      }
    } catch(e) { if (histEl) histEl.innerHTML = '<span style="color:var(--red)">'+e.message+'</span>'; }
  }
  // 调度器状态
  if (statusEl) statusEl.innerHTML = '<span style="color:var(--text2)">需手动启动: mc schedule start</span>';
  // 加载 WorkBuddy 自动化任务
  const autoEl = document.getElementById('autoTasksSummary');
  if (autoEl) {
    try {
      const r = await fetch('/api/kb/automations');
      const d = await r.json();
      const machines = d.machines || {};
      const entries = Object.entries(machines);
      if (!entries.length) {
        autoEl.innerHTML = '<div style="color:var(--text2);font-size:11px;padding:4px 0">暂无自动化任务</div>' +
          '<div style="margin-top:8px;display:flex;gap:6px"><select id="autoNewTarget" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;font-size:11px">' +
          '<option value="">选目标机器</option>' +
          Object.keys(machines).map(m => '<option value="'+m+'">'+m+'</option>').join('') +
          '</select>' +
          '<input id="autoNewPrompt" placeholder="输入提示词..." style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;font-size:11px">' +
          '<button onclick="createAutoTaskFromSchedule()" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">+ 创建任务</button></div>';
      } else {
        let html = entries.map(([machine, tasks]) => {
          const wbTasks = tasks.filter(t => t.source_type === 'workbuddy');
          if (!wbTasks.length) return '';
          return '<div style="margin-bottom:6px">' +
            '<div style="font-weight:600;font-size:11px;color:#6366f1;margin-bottom:3px">💻 ' + machine + '</div>' +
            wbTasks.map(t => {
              const prompt = t.prompt || t.name || '';
              return '<div style="padding:3px 6px;font-size:10px;background:var(--bg3);border-radius:4px;margin-bottom:3px;border:1px solid var(--border)">' +
                '<div style="display:flex;justify-content:space-between">' +
                '<span style="color:' + (t.status === 'ACTIVE' ? '#22c55e' : '#8b8fa3') + '">' + (t.status === 'ACTIVE' ? '▶ 运行中' : '⏸ 暂停') + '</span>' +
                '<span style="color:var(--text2)">' + (t.rrule || t.scheduleType || '即时') + '</span>' +
                '</div>' +
                '<div style="margin-top:2px;color:var(--text);word-break:break-all">' + (prompt.slice(0, 120) + (prompt.length > 120 ? '...' : '')) + '</div>' +
                '</div>';
            }).join('') +
            '</div>';
        }).filter(Boolean).join('');
        if (!html) html = '<div style="color:var(--text2);font-size:11px;padding:4px 0">无 WorkBuddy 任务</div>';
        // 新建任务表单
        html += '<div style="margin-top:8px;padding:6px;background:var(--bg3);border-radius:4px">' +
          '<div style="font-size:11px;font-weight:600;margin-bottom:4px">✏️ 新建自动化任务</div>' +
          '<div style="display:flex;gap:6px">' +
          '<select id="autoNewTarget" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:3px;font-size:10px;width:120px">' +
          '<option value="">选目标</option>' +
          Object.keys(machines).map(m => '<option value="'+m+'">'+m+'</option>').join('') +
          '</select>' +
          '<input id="autoNewPrompt" placeholder="输入提示词，描述要执行的任务..." style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:3px;font-size:10px">' +
          '<button onclick="createAutoTaskFromSchedule()" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:3px;cursor:pointer;font-size:10px">+ 创建</button>' +
          '</div></div>';
        autoEl.innerHTML = html;
      }
    } catch(e) { autoEl.innerHTML = '<span style="color:var(--text2);font-size:11px">自动化任务API不可用</span>'; }
  }
}

async function scheduleAdd() {
  const id = document.getElementById('schedId')?.value.trim();
  const account = document.getElementById('schedAccount')?.value;
  const blueprint = document.getElementById('schedBlueprint')?.value;
  const time = document.getElementById('schedTime')?.value || '09:00';
  const days = document.getElementById('schedDays')?.value || '1,2,3,4,5,6,7';
  const rounds = parseInt(document.getElementById('schedRounds')?.value) || 3;
  if (!id) { alert('请输入任务ID'); return; }
  if (!account) { alert('请选择账号'); return; }
  // 通过 mc CLI 添加
  const cmd = 'mc schedule add --id '+id+' --account '+account+' --blueprint '+blueprint+' --time '+time+' --days '+days+' --rounds '+rounds;
  if (!confirm('将在终端执行:\n'+cmd+'\n\n确认？')) return;
  alert('请在终端执行:\n'+cmd+'\n\n或手动编辑 config/schedule.yaml');
  refreshScheduleList();
}

async function scheduleToggle(sid, enabled) {
  try {
    await fetch('/api/matrix/schedules/toggle', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({id:sid, enabled})
    });
    refreshScheduleList();
  } catch(e) { alert('❌ '+e.message); }
}

async function scheduleDelete(sid) {
  if (!confirm('删除定时任务 '+sid+' ？')) return;
  try {
    await fetch('/api/matrix/schedules/delete', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({id:sid})
    });
    refreshScheduleList();
  } catch(e) { alert('❌ '+e.message); }
}
// ── 导出（防 Rollup tree-shake）──
window.refreshScheduleList = refreshScheduleList;
window.scheduleAdd = scheduleAdd;
window.scheduleDelete = scheduleDelete;
window.scheduleToggle = scheduleToggle;
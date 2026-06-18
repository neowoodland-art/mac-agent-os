/**
 * 远程Shell视图（v2 — 动态机器 + 快捷命令 + 语法高亮 + 历史）
 */
export async function loadView(container) {
  const uid = 'fe_' + Math.random().toString(36).slice(2, 6);
  const PRESET_CMDS = [
    'hostname',
    'df -h /',
    'pgrep -a camoufox',
    'ps aux | wc -l',
    'curl -s localhost:9988/api/health',
    'agentos guardd status',
  ];

  container.innerHTML = `
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">💻 远程Shell</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">在远程机器上执行命令（通过 mc remote exec）</p>

      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px">
        <select id="execMachine_${uid}" style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;min-width:160px">
          <option value="">⏳ 加载机器列表...</option>
        </select>
        <input id="execCmd_${uid}" placeholder="输入命令..." style="flex:1;min-width:200px;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px"
          onkeydown="if(event.key==='Enter')window._doFleetExec('${uid}')">
        <button onclick="window._doFleetExec('${uid}')" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">➡ 执行</button>
        <button onclick="document.getElementById('execCmd_${uid}').value=''; document.getElementById('log_${uid}').innerHTML=''" style="background:var(--bg2);color:var(--text);border:1px solid var(--border);padding:6px 10px;border-radius:6px;cursor:pointer;font-size:11px">✕ 清空</button>
      </div>

      <div style="margin-bottom:10px;display:flex;gap:6px;flex-wrap:wrap">
        ${PRESET_CMDS.map(cmd =>
          `<button onclick="document.getElementById('execCmd_${uid}').value='${cmd.replace(/'/g, "\\'")}';window._doFleetExec('${uid}')" style="height:26px;background:var(--bg3);border:0.5px solid var(--border);border-radius:6px;padding:0 10px;display:inline-flex;align-items:center;font-size:11px;color:var(--text);cursor:pointer">${cmd}</button>`
        ).join('')}
      </div>

      <div id="log_${uid}" style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:420px;overflow:auto"></div>

      <div id="history_${uid}" style="margin-top:8px;font-size:11px;display:none">
        <div style="color:var(--text2);margin-bottom:4px">最近执行</div>
        <div id="historyList_${uid}" style="display:flex;gap:6px;flex-wrap:wrap"></div>
      </div>
    </div>`;

  // ── 动态加载机器列表 ──
  const machineSel = document.getElementById('execMachine_' + uid);
  (async () => {
    try {
      const r = await fetch('/api/machines');
      const d = await r.json();
      const machines = d.machines || [];
      machineSel.innerHTML = machines.map(m =>
        `<option value="${m.hostname}">${m.hostname} ${m.status === 'online' ? '🟢' : '🔴'}</option>`
      ).join('');
      // 选择第一台在线的
      const online = machines.find(m => m.status === 'online');
      if (online) machineSel.value = online.hostname;
    } catch(e) {
      machineSel.innerHTML = '<option value="">加载失败</option>';
    }
  })();

  // ── 执行 ──
  window._doFleetExec = window._doFleetExec || (async function(uid) {
    const machine = document.getElementById('execMachine_' + uid)?.value;
    const cmd = document.getElementById('execCmd_' + uid)?.value;
    const logEl = document.getElementById('log_' + uid);
    const historyEl = document.getElementById('history_' + uid);
    const historyList = document.getElementById('historyList_' + uid);
    if (!cmd || !machine) {
      if (logEl) logEl.innerHTML = '<span style="color:var(--red)">⚠️ 请选择机器并输入命令</span>';
      return;
    }

    logEl.innerHTML = '<span style="color:var(--text2)">⏳ 执行中...</span>\n';

    try {
      const r = await fetch('/api/federation/exec', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ machine, command: cmd, timeout: 30 }),
      });
      const d = await r.json();
      const rawOutput = d.output || d.stdout || JSON.stringify(d, null, 2);
      const hasError = d.status === 'error' || d.returncode > 0 || rawOutput.includes('❌');

      // ── 语法高亮 ──
      let html = '';
      const lines = rawOutput.split('\n');
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) { html += '<br>'; continue; }
        if (trimmed.startsWith('$ ')) {
          html += `<span style="color:var(--green)">${escapeHtml(trimmed)}</span>\n`;
        } else if (trimmed.startsWith('❌') || trimmed.toLowerCase().includes('error') || trimmed.toLowerCase().includes('failed')) {
          html += `<span style="color:var(--red)">${escapeHtml(trimmed)}</span>\n`;
        } else if (trimmed.startsWith('✅') || trimmed.startsWith('✓') || trimmed.startsWith('+')) {
          html += `<span style="color:var(--green)">${escapeHtml(trimmed)}</span>\n`;
        } else if (/^\d/.test(trimmed) || trimmed.includes('GB') || trimmed.includes('%')) {
          html += `<span style="color:var(--blue)">${escapeHtml(trimmed)}</span>\n`;
        } else {
          html += `${escapeHtml(trimmed)}\n`;
        }
      }

      // 如果是错误状态，顶部加红色 banner
      if (hasError) {
        html = `<div style="padding:6px 10px;background:rgba(227,75,74,.1);border-radius:4px;margin-bottom:8px;color:var(--red)">❌ 命令返回非零退出码</div>\n` + html;
      }

      logEl.innerHTML = `<span style="color:var(--green)">$ ${escapeHtml(cmd)}</span>\n` + html;

      // ── 追加执行历史 ──
      const now = new Date();
      const timeStr = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
      const icon = hasError ? '❌' : '✅';
      const entry = document.createElement('div');
      entry.style.cssText = 'background:var(--bg3);padding:4px 8px;border-radius:4px;font-size:10px;white-space:nowrap';
      entry.innerHTML = `${icon} ${machine}: ${cmd.slice(0,18)}${cmd.length>18?'..':''} (${timeStr})`;
      if (hasError) entry.style.color = 'var(--red)';
      else entry.style.color = 'var(--green)';

      if (historyList) {
        historyList.prepend(entry);
        // 保留最近10条
        while (historyList.children.length > 10) {
          historyList.removeChild(historyList.lastChild);
        }
      }
      if (historyEl) historyEl.style.display = '';

    } catch(e) {
      logEl.innerHTML = `<span style="color:var(--red)">❌ ${escapeHtml(e.message)}</span>`;
    }
  });

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}

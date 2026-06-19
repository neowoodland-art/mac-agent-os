import { apiRequest, confirmExecute } from '../router.js';

export async function loadView(container) {
  const uid = 'cmd_' + Math.random().toString(36).slice(2, 6);
  const PS = ['douyin_daily','douyin_comment','douyin_search','douyin_collect','douyin_read_profile',
              'xhs_daily','xhs_active_v1','xiaohongshu_read_profile'];

  container.innerHTML = `
    <div style="padding:16px;max-width:1100px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <div><span style="font-weight:600;font-size:15px">🖥️ 联邦指挥台</span>
        <span style="font-size:11px;color:var(--text2);margin-left:8px">跨机器命令下发 · 批量执行 · 状态监控</span></div>
        <div style="display:flex;gap:6px">
          <button onclick="window._refCmd('${uid}')" style="background:var(--bg2);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:11px;cursor:pointer">⟳ 刷新状态</button>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px">

        <!-- 左栏: 命令配置 -->
        <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
          <div style="font-weight:600;font-size:12px;margin-bottom:8px">📋 命令配置</div>

          <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:4px">目标机器</label>
          <select id="tgtMachine_${uid}" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:5px;font-size:11px;margin-bottom:8px">
            <option value="">⏳ 加载机器列表...</option>
          </select>

          <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:4px">操作类型</label>
          <select id="opsType_${uid}" onchange="window._opsTypeChange_${uid}()" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:5px;font-size:11px;margin-bottom:8px">
            <option value="nurture">🏃 养号</option>
            <option value="collect">📡 采集</option>
            <option value="comment">💬 评论</option>
            <option value="login">🔑 登录</option>
            <option value="logout">🔒 登出</option>
          </select>

          <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:4px">选择蓝图</label>
          <select id="bpSelect_${uid}" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:5px;font-size:11px;margin-bottom:8px">
            <option value="">⏳ 加载蓝图...</option>
          </select>

          <div id="paramsArea_${uid}" style="margin-bottom:8px;display:none">
            <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:4px">参数配置</label>
            <div id="paramFields_${uid}"></div>
          </div>

          <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:4px">轮数</label>
          <select id="rounds_${uid}" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:5px;font-size:11px;margin-bottom:8px">
            <option value="1">1</option><option value="3">3</option>
            <option value="5" selected>5</option><option value="10">10</option><option value="20">20</option>
          </select>

          <div style="display:flex;gap:6px">
            <button onclick="window._execCmd_${uid}()" style="flex:1;background:#22c55e;color:#000;border:none;padding:7px 0;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600">🚀 执行</button>
            <button onclick="window._clearLog_${uid}()" style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:11px;cursor:pointer">✕ 清空</button>
          </div>
        </div>

        <!-- 右栏: 账号选择 + 执行结果 -->
        <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
          <div style="font-weight:600;font-size:12px;margin-bottom:8px">👥 账号选择 <span id="selCount_${uid}" style="font-size:10px;color:var(--text2);font-weight:400"></span></div>
          <div id="acctList_${uid}" style="max-height:180px;overflow-y:auto;margin-bottom:8px;font-size:11px"><div class="loading">⏳ 加载账号列表...</div></div>

          <div style="font-weight:600;font-size:12px;margin-bottom:4px">📊 执行日志</div>
          <div id="log_${uid}" style="background:var(--bg3);border-radius:6px;padding:8px;font-size:10px;font-family:monospace;white-space:pre-wrap;max-height:260px;overflow-y:auto;border:1px solid var(--border)"><span style="color:var(--text2)">等待执行...</span></div>
        </div>
      </div>

      <!-- 底栏: 机器状态 + 快捷操作 -->
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <span style="font-weight:600;font-size:12px">🔌 机器状态</span>
          <div style="display:flex;gap:6px">
            <button onclick="window._syncAll_${uid}()" style="background:var(--bg3);border:1px solid var(--border);border-radius:5px;padding:3px 8px;font-size:10px;cursor:pointer">🔄 同步所有</button>
          </div>
        </div>
        <div id="machineList_${uid}" style="display:flex;gap:8px;flex-wrap:wrap;font-size:11px"><span style="color:var(--text2)">加载中...</span></div>
        <div id="statusLog_${uid}" style="margin-top:6px;font-size:10px;color:var(--text2);font-family:monospace"></div>
      </div>
    </div>`;

  // ── 数据加载 ──
  loadMachines(uid);
  loadBlueprints(uid);
  loadAccounts(uid);

  // ── 蓝图切换时动态参数 ──
  window[`_opsTypeChange_${uid}`] = function() {
    const type = document.getElementById(`opsType_${uid}`)?.value;
    const pa = document.getElementById(`paramsArea_${uid}`);
    const pf = document.getElementById(`paramFields_${uid}`);
    if (type === 'comment') {
      pa.style.display = '';
      pf.innerHTML = `
        <input id="url_${uid}" placeholder="视频链接" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:10px;margin-bottom:4px">
        <input id="text_${uid}" placeholder="评论内容(空=用语料库)" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:10px;margin-bottom:4px">
        <select id="corpus_${uid}" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:10px">
          <option value="">不用语料库</option>
          <option value="corpus_praise">赞美</option>
          <option value="corpus_question">提问</option>
          <option value="corpus_discuss">讨论</option>
        </select>`;
    } else if (type === 'collect') {
      pa.style.display = '';
      pf.innerHTML = `<input id="keyword_${uid}" placeholder="搜索关键词(可选)" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:10px">`;
    } else {
      pa.style.display = 'none';
    }
  };

  // ── 执行 ──
  window[`_execCmd_${uid}`] = async function() {
    const logEl = document.getElementById(`log_${uid}`);
    const accts = getSelectedAccounts(uid);
    if (!accts.length) { logEl.innerHTML = '<span style="color:var(--red)">⚠️ 请选择至少一个账号</span>'; return; }
    const type = document.getElementById(`opsType_${uid}`)?.value || 'nurture';
    const bp = document.getElementById(`bpSelect_${uid}`)?.value || 'douyin_daily';
    const rounds = parseInt(document.getElementById(`rounds_${uid}`)?.value || '5');
    const machine = document.getElementById(`tgtMachine_${uid}`)?.value || '';

    // 执行前确认弹窗
    const detail = `操作: ${type}\n蓝图: ${bp}\n账号: ${accts.join(', ')}\n轮数: ${rounds}\n机器: ${machine || '自动分配'}`;
    const confirmed = await confirmExecute(`即将在 ${accts.length} 个账号上执行 ${type} 操作`, detail);
    if (!confirmed) { logEl.innerHTML = '<span style="color:var(--text2)">已取消</span>'; return; }

    const params = { blueprint: bp, rounds };
    if (type === 'comment') {
      const url = document.getElementById(`url_${uid}`)?.value;
      const text = document.getElementById(`text_${uid}`)?.value;
      const corpus = document.getElementById(`corpus_${uid}`)?.value;
      if (url) params.url = url;
      if (text) params.text = text;
      if (corpus) params.corpus = corpus;
    }
    if (machine) params.machine = machine;

    logEl.innerHTML = '<span style="color:var(--text2)">⏳ 提交执行...</span>\n';
    try {
      const r = await fetch('/api/ops/run', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ type, accounts: accts, params }),
      });
      const d = await r.json();
      let html = `<span style="color:var(--green)">✅ 已提交</span>\n`;
      const cmds = d.commands || d.results || [];
      cmds.forEach(c => {
        const id = c.account || c.account_id || c.target || '?';
        const st = c.status || c.machine || 'sent';
        html += `  ${id}: ${st}\n`;
      });
      if (d.errors) html += `<span style="color:var(--red)">⚠️ 错误: ${JSON.stringify(d.errors)}</span>\n`;
      logEl.innerHTML = html;
    } catch(e) {
      logEl.innerHTML = `<span style="color:var(--red)">❌ ${e.message}</span>`;
    }
  };

  window[`_clearLog_${uid}`] = function() {
    document.getElementById(`log_${uid}`).innerHTML = '<span style="color:var(--text2)">已清空</span>';
  };

  window[`_refCmd_${uid}`] = function() {
    loadMachines(uid);
    const logEl = document.getElementById(`log_${uid}`);
    if (logEl) logEl.innerHTML = '<span style="color:var(--text2)">⟳ 已刷新</span>\n';
  };

  window[`_syncAll_${uid}`] = async function() {
    const sl = document.getElementById(`statusLog_${uid}`);
    if (sl) sl.textContent = '⏳ 同步中...';
    try {
      const r = await fetch('/api/fleet/sync', { method: 'POST' });
      const d = await r.json();
      if (sl) sl.textContent = '✅ 同步完成: ' + (d.message || JSON.stringify(d));
    } catch(e) {
      if (sl) sl.textContent = '❌ 同步失败: ' + e.message;
    }
  };
}

// ── 辅助函数 ──

async function loadMachines(uid) {
  try {
    const r = await fetch('/api/machines');
    const d = await r.json();
    const machines = d.machines || [];
    const sel = document.getElementById(`tgtMachine_${uid}`);
    if (sel) {
      sel.innerHTML = '<option value="">全部机器(自动分配)</option>' +
        machines.map(m => `<option value="${m.hostname}">${m.hostname} ${m.status === 'online' ? '🟢' : '🔴'}</option>`).join('');
      const online = machines.find(m => m.status === 'online');
      if (!online && machines.length) sel.value = machines[0].hostname;
    }
    const ml = document.getElementById(`machineList_${uid}`);
    if (ml) {
      ml.innerHTML = machines.map(m =>
        `<div style="background:var(--bg3);border-radius:6px;padding:6px 10px;border:1px solid var(--border);display:flex;align-items:center;gap:6px">
          ${m.status === 'online' ? '🟢' : '🔴'}
          <span style="font-weight:500">${m.hostname}</span>
          <span style="font-size:10px;color:var(--text2)">${m.ip || m.tailscale_ip || ''}</span>
          <span style="font-size:10px;color:${m.status === 'online' ? 'var(--green)' : 'var(--red)'}">${m.status || '?'}</span>
        </div>`
      ).join('');
    }
  } catch(e) {
    const sel = document.getElementById(`tgtMachine_${uid}`);
    if (sel) sel.innerHTML = '<option value="">加载失败</option>';
  }
}

async function loadBlueprints(uid) {
  try {
    const r = await fetch('/api/matrix/blueprints');
    const d = await r.json();
    const bps = Array.isArray(d) ? d : (d.blueprints || []);
    const sel = document.getElementById(`bpSelect_${uid}`);
    if (sel) {
      sel.innerHTML = bps.map(bp => {
        const val = bp.file ? bp.file.replace('.json','') : bp.name;
        const label = `${bp.name} — ${(bp.description || '').slice(0,36)}`;
        return `<option value="${val}">${label}</option>`;
      }).join('');
    }
  } catch(e) {
    const sel = document.getElementById(`bpSelect_${uid}`);
    if (sel) sel.innerHTML = '<option value="">加载失败</option>';
  }
}

async function loadAccounts(uid) {
  try {
    const r = await fetch('/api/matrix/accounts');
    const d = await r.json();
    const accts = Array.isArray(d) ? d : (d.accounts || []);
    const el = document.getElementById(`acctList_${uid}`);
    if (!el) return;
    el.innerHTML = accts.map(a => {
      const pid = `acct_${uid}_${a.id}`;
      return `<label style="display:flex;align-items:center;gap:4px;padding:2px 0;cursor:pointer">
        <input type="checkbox" id="${pid}" value="${a.id}" onchange="window._updateCount_${uid}()">
        <span>${a.id}</span>
        <span style="font-size:10px;color:var(--text2)">${a.platform || ''}</span>
        <span style="font-size:10px;color:${a._status === 'logged_in' ? 'var(--green)' : 'var(--red)'}">${a._status === 'logged_in' ? '🟢' : a._status === 'remote' ? '🟡远程' : '🔴离线'}</span>
      </label>`;
    }).join('');
    window[`_updateCount_${uid}`] = function() {
      const checked = document.querySelectorAll(`#acctList_${uid} input:checked`).length;
      const sc = document.getElementById(`selCount_${uid}`);
      if (sc) sc.textContent = `已选 ${checked} 个`;
    };
    window[`_updateCount_${uid}`]();
  } catch(e) {
    const el = document.getElementById(`acctList_${uid}`);
    if (el) el.innerHTML = `<span style="color:var(--red)">❌ ${e.message}</span>`;
  }
}

function getSelectedAccounts(uid) {
  return [...document.querySelectorAll(`#acctList_${uid} input:checked`)].map(el => el.value);
}

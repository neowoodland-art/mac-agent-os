/**
 * ⚙️ API 配置（已迁移视图）
 *
 * 让每个使用者配置自己的 API 密钥：
 *  - 密钥只写入本机 agent-local（不进 git 仓库）
 *  - 接口返回一律脱敏（前 5 + 后 4 位）
 *  - 支持「🧪 测试」就地验证连通性
 */
let _acData = null;

export async function loadView(container) {
  container.innerHTML = `
    <div style="padding:16px;max-width:920px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <h2 style="font-size:18px;margin:0">⚙️ API 配置</h2>
        <span id="acSummary" style="font-size:12px;color:var(--text2)"></span>
      </div>
      <div style="background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.3);border-radius:6px;
                  padding:9px 11px;font-size:11px;color:var(--text2);margin-bottom:12px;line-height:1.6">
        🔐 密钥只保存在<b>本机</b> <code id="acPath" style="background:var(--bg3);padding:1px 5px;border-radius:3px">…</code>，
        <b>不会提交到 git 仓库</b>；每个使用者配置自己的 key，互不影响。<br>
        💡 输入框留空 + 点保存 = 清除该项配置。
      </div>
      <div id="acGroups"><div class="loading">加载配置状态…</div></div>
    </div>`;
  await _acLoad();
}

async function _acLoad() {
  try {
    const r = await fetch('/api/config/api-keys');
    const d = await r.json();
    if (d.status !== 'ok') throw new Error(d.detail || '加载失败');
    _acData = d;
    _acRender(d);
  } catch (e) {
    const el = document.getElementById('acGroups');
    if (el) el.innerHTML = `<div class="error" style="padding:20px">❌ ${e.message}</div>`;
  }
}

function _esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function _acRender(d) {
  const sum = document.getElementById('acSummary');
  if (sum) sum.textContent = `已配置 ${d.configured} / ${d.total} 项`;
  const pathEl = document.getElementById('acPath');
  if (pathEl) pathEl.textContent = d.config_path || 'agent-local/…/local.yaml';

  const wrap = document.getElementById('acGroups');
  if (!wrap) return;
  wrap.innerHTML = (d.groups || []).map(g => `
    <div style="background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:10px 12px;margin-bottom:10px">
      <div style="font-size:12px;font-weight:600;margin-bottom:8px">${_esc(g.name)}</div>
      ${g.items.map(it => `
        <div style="padding:7px 0;border-top:1px solid var(--border)">
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
            <span style="font-size:11px;font-weight:500;min-width:150px">${_esc(it.label)}${it.required ? ' <span style="color:var(--red);font-size:9px">*必需</span>' : ''}</span>
            <span id="acBadge_${_esc(it.path)}" style="font-size:10px;padding:1px 7px;border-radius:9px;${it.configured
              ? 'background:rgba(34,197,94,.15);color:#22c55e;border:1px solid rgba(34,197,94,.35)'
              : 'background:rgba(239,68,68,.12);color:#ef4444;border:1px solid rgba(239,68,68,.3)'}">
              ${it.configured ? '✅ 已配置' : '⚠️ 未配置'}
            </span>
            ${it.masked ? `<code style="font-size:10px;color:var(--text2);background:var(--bg2);padding:1px 5px;border-radius:3px">${_esc(it.masked)}</code>` : ''}
            ${it.testable ? `<button onclick="window._acTest('${_esc(it.path)}')" style="background:var(--bg2);color:var(--text);border:1px solid var(--border);padding:2px 9px;border-radius:4px;cursor:pointer;font-size:10px">🧪 测试</button>` : ''}
          </div>
          <div style="font-size:10px;color:var(--text2);margin:3px 0 5px">${_esc(it.hint || '')}</div>
          <div style="display:flex;gap:6px;align-items:center">
            <input id="acInput_${_esc(it.path)}" type="${it.secret === false ? 'text' : 'password'}" autocomplete="off"
                   placeholder="${it.secret === false
                     ? (it.masked ? '当前: ' + it.masked : '输入新值（如 deepseek-v4-flash）')
                     : '输入新的 key' + (it.configured ? '（留空保存=清除）' : '')}"
                   style="flex:1;padding:4px 8px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:11px">
            <button onclick="window._acSave('${_esc(it.path)}')" style="background:var(--primary);color:#fff;border:none;padding:4px 14px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600">💾 保存</button>
            <span id="acMsg_${_esc(it.path)}" style="font-size:10px;color:var(--text2);min-width:60px"></span>
          </div>
          ${(it.history && it.history.length) ? `
          <details style="margin-top:5px">
            <summary style="cursor:pointer;font-size:10px;color:var(--text2)">📚 历史版本 (${it.history.length}) — 可切换 / 删除</summary>
            <div style="margin-top:5px;display:grid;gap:4px">
              ${it.history.map(h => `
                <div style="display:flex;align-items:center;gap:6px;font-size:10px;flex-wrap:wrap;
                            background:var(--bg2);padding:3px 6px;border-radius:4px;${h.active ? 'border:1px solid rgba(34,197,94,.4)' : ''}">
                  <span>${h.active ? '🟢' : '⚪'}</span>
                  <code style="color:var(--text2);background:var(--bg3);padding:1px 5px;border-radius:3px">${_esc(h.masked)}</code>
                  <span style="color:var(--text2)">${_esc(h.label || '')}</span>
                  <span style="color:var(--text2);opacity:.65">${_esc(h.added_at || '')}</span>
                  ${h.active
                    ? '<span style="color:#22c55e;font-weight:600">使用中</span>'
                    : `<button onclick="window._acActivate('${_esc(it.path)}', ${h.idx})" title="切换为该版本（当前版本会保留在历史，可回退）"
                              style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:1px 8px;border-radius:3px;cursor:pointer;font-size:9px">🔄 启用</button>
                       <button onclick="window._acDelete('${_esc(it.path)}', ${h.idx})" title="从历史中删除该版本"
                              style="background:var(--bg3);color:var(--red);border:1px solid var(--border);padding:1px 7px;border-radius:3px;cursor:pointer;font-size:9px">🗑</button>`}
                </div>`).join('')}
            </div>
          </details>` : ''}
        </div>`).join('')}
    </div>`).join('');
}

function _msg(path, text, color) {
  const el = document.getElementById(`acMsg_${path}`);
  if (el) {
    el.textContent = text || '';
    el.style.color = color || 'var(--text2)';
  }
}

function _isSecret(path) {
  if (_acData) {
    for (const g of (_acData.groups || [])) {
      for (const it of (g.items || [])) {
        if (it.path === path) return it.secret !== false;
      }
    }
  }
  return true;
}

window._acSave = async (path) => {
  const input = document.getElementById(`acInput_${path}`);
  const val = (input?.value || '').trim();
  if (val && _isSecret(path) && !confirm(`确认保存该 key？\n（只写入本机 agent-local，不会进 git）\n\n${val.slice(0, 6)}…${val.slice(-4)}`)) return;
  _msg(path, '⏳ 保存中…');
  try {
    const r = await fetch('/api/config/api-keys', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ updates: { [path]: val } }),
    });
    const d = await r.json();
    if (d.status !== 'ok') throw new Error(d.detail || '保存失败');
    if (input) input.value = '';
    _msg(path, val ? '✅ 已保存' : '🗑 已清除', '#22c55e');
    await _acLoad();
  } catch (e) {
    _msg(path, '❌ ' + e.message, '#ef4444');
  }
};

window._acTest = async (path) => {
  const input = document.getElementById(`acInput_${path}`);
  const typed = (input?.value || '').trim();
  _msg(path, '⏳ 测试中…');
  try {
    const r = await fetch('/api/config/api-keys/test', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, value: typed }),  // 输入框有值则测新 key
    });
    const d = await r.json();
    const color = d.ok === true ? '#22c55e' : (d.ok === false ? '#f59e0b' : 'var(--text2)');
    _msg(path, d.detail || '(无返回)', color);
  } catch (e) {
    _msg(path, '❌ ' + e.message, '#ef4444');
  }
};

window._acActivate = async (path, idx) => {
  if (!confirm('切换到该版本？\n\n当前版本会自动保留在历史里，可随时切回。')) return;
  _msg(path, '⏳ 切换中…');
  try {
    const r = await fetch('/api/config/api-keys/activate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, idx }),
    });
    const d = await r.json();
    if (d.status !== 'ok') throw new Error(d.detail || '切换失败');
    _msg(path, `🔄 已切换为 ${d.activated}`, '#22c55e');
    await _acLoad();
  } catch (e) {
    _msg(path, '❌ ' + e.message, '#ef4444');
  }
};

window._acDelete = async (path, idx) => {
  if (!confirm('删除该历史版本？\n\n此操作不可撤销（不影响当前使用中的版本）。')) return;
  _msg(path, '⏳ 删除中…');
  try {
    const r = await fetch('/api/config/api-keys/delete', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, idx }),
    });
    const d = await r.json();
    if (d.status !== 'ok') throw new Error(d.detail || '删除失败');
    _msg(path, `🗑 已删除 ${d.removed}`, '#22c55e');
    await _acLoad();
  } catch (e) {
    _msg(path, '❌ ' + e.message, '#ef4444');
  }
};

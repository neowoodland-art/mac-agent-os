/**
 * accounts-center.js — 统一账号中心视图（v4 联邦版）
 *
 * 功能：
 *   顶部概要栏        状态汇总
 *   筛选栏            搜索/机器/平台/状态筛选
 *   表格              多选 + 颜色状态 + 行内操作
 *   展开栏            代理/短信/录制/执行记录
 *   批量操作栏        选中后浮动底部
 *   养号弹窗          选蓝图+轮次
 *
 * 依赖 API：
 *   GET  /api/v2/accounts          — 账号列表
 *   GET  /api/v2/status-summary    — 状态汇总
 *   POST /api/v2/accounts/batch    — 批量操作
 *   POST /api/v2/accounts/refresh  — 刷新状态
 */

const BASE = '/api';

// ── 状态显示配置 ──
const STATUS_CFG = {
  logged_in:       { color: '#22c55e', dot: '🟢', label: '已登录' },
  cookie_expiring: { color: '#eab308', dot: '🟡', label: 'Cookie将过期' },
  no_cookie:       { color: '#ef4444', dot: '🔴', label: '无Cookie' },
  no_identity:     { color: '#8b8fa3', dot: '⚪', label: '未配置' },
  banned:          { color: '#000',    dot: '⚫', label: '已封号' },
  disabled:        { color: '#d1d5db', dot: '⬜', label: '已禁用' },
  no_session:      { color: '#f59e0b', dot: '🟠', label: 'Cookie无Session' },
  empty_cookie:    { color: '#f59e0b', dot: '🟠', label: 'Cookie为空' },
  new:             { color: '#3b82f6', dot: '🔵', label: '新建' },
  unknown:         { color: '#8b8fa3', dot: '⚪', label: '未知' },
};

// 状态排序优先级（用于概要栏排序）
const STATUS_ORDER = ['banned', 'no_cookie', 'cookie_expiring', 'no_session', 'empty_cookie', 'disabled', 'unknown', 'new', 'logged_in'];

// ── 主入口 ──
export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载账号中心...</div>';

  try {
    const [accountsRes, summaryRes] = await Promise.all([
      fetch(`${BASE}/v2/accounts`).then(r => r.ok ? r.json() : { accounts: [] }),
      fetch(`${BASE}/v2/status-summary`).then(r => r.ok ? r.json() : {}),
    ]);

    const allAccounts = accountsRes.accounts || [];
    const summary = summaryRes;

    // 确保 window._allAccounts 用于筛选
    window._v2Accounts = allAccounts;

    container.innerHTML = '';
    container.appendChild(renderSummaryBar(summary, allAccounts));
    container.appendChild(renderFilterBar());
    container.appendChild(renderBatchBar());
    container.appendChild(renderTable(allAccounts));

  } catch (e) {
    container.innerHTML = `<div class="error">❌ ${e.message || e}</div>`;
  }
}


// ── 概要栏 ──
function renderSummaryBar(summary, accounts) {
  const div = document.createElement('div');
  div.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;align-items:center';

  // 状态卡片
  const statusKeys = STATUS_ORDER.filter(k => (summary[k] || 0) > 0);
  statusKeys.forEach(k => {
    const cfg = STATUS_CFG[k] || { dot: '⚪', label: k, color: '#8b8fa3' };
    const count = summary[k] || 0;
    const card = document.createElement('span');
    card.style.cssText = `padding:2px 10px;border-radius:12px;font-size:11px;background:${cfg.color}15;border:1px solid ${cfg.color}40;color:var(--text)`;
    card.innerHTML = `${cfg.dot} ${cfg.label} ${count}`;
    card.onclick = () => applyFilter('status', k);
    card.style.cursor = 'pointer';
    div.appendChild(card);
  });

  // 总数
  const total = document.createElement('span');
  total.style.cssText = 'font-size:10px;color:var(--text2);margin-left:auto';
  total.textContent = `共 ${accounts.length} 个账号`;
  div.appendChild(total);

  // 刷新按钮
  const refreshBtn = document.createElement('button');
  refreshBtn.textContent = '🔄 刷新';
  refreshBtn.style.cssText = 'background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:3px 10px;border-radius:6px;cursor:pointer;font-size:11px';
  refreshBtn.onclick = async () => {
    refreshBtn.textContent = '⏳';
    refreshBtn.disabled = true;
    await refreshView();
    refreshBtn.textContent = '🔄 刷新';
    refreshBtn.disabled = false;
  };
  div.appendChild(refreshBtn);

  return div;
}


// ── 筛选栏 ──
function renderFilterBar() {
  const div = document.createElement('div');
  div.style.cssText = 'display:flex;gap:6px;margin-bottom:8px;align-items:center;flex-wrap:wrap';
  div.id = 'acctFilterBar';

  // 搜索框
  const search = document.createElement('input');
  search.placeholder = '🔍 搜索手机号/昵称/账号ID/机器...';
  search.style.cssText = 'flex:1;min-width:160px;padding:4px 8px;font-size:12px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px';
  search.oninput = () => doFilter();

  // 机器筛选
  const machineSel = document.createElement('select');
  machineSel.style.cssText = 'padding:4px 8px;font-size:11px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px';
  machineSel.innerHTML = '<option value="">全部机器</option>';

  // 平台筛选
  const platSel = document.createElement('select');
  platSel.style.cssText = 'padding:4px 8px;font-size:11px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px';
  platSel.innerHTML = '<option value="">全部平台</option><option value="douyin">🎵 抖音</option><option value="xiaohongshu">📕 小红书</option>';

  // 状态筛选
  const statusSel = document.createElement('select');
  statusSel.style.cssText = 'padding:4px 8px;font-size:11px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px';
  let ops = '<option value="">全部状态</option>';
  STATUS_ORDER.forEach(k => {
    const cfg = STATUS_CFG[k];
    ops += `<option value="${k}">${cfg.dot} ${cfg.label}</option>`;
  });
  statusSel.innerHTML = ops;

  // 收集机器列表
  const accts = window._v2Accounts || [];
  const machines = [...new Set(accts.map(a => a.owner_machine).filter(Boolean))];
  machines.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m;
    opt.textContent = m;
    machineSel.appendChild(opt);
  });

  // 🔍 搜索按钮
  const searchBtn = document.createElement('button');
  searchBtn.textContent = '🔍 搜索';
  searchBtn.style.cssText = 'padding:4px 12px;font-size:11px;background:var(--primary);color:#fff;border:none;border-radius:4px;cursor:pointer';

  div.append(search, machineSel, platSel, statusSel, searchBtn);

  // 计数
  const count = document.createElement('span');
  count.id = 'acctCount';
  count.style.cssText = 'font-size:10px;color:var(--text2);white-space:nowrap';
  count.textContent = `共 ${accts.length} 个`;
  div.appendChild(count);

  // ── 绑定事件 ──
  // 下拉框 onchange → 自动筛选
  machineSel.onchange = doFilter;
  platSel.onchange = doFilter;
  statusSel.onchange = doFilter;
  // 搜索按钮点击 → 筛选
  searchBtn.onclick = doFilter;
  // 搜索框回车也触发
  search.onkeydown = (e) => { if (e.key === 'Enter') doFilter(); };
  // 绑定筛选函数
  window._doAcctFilter = doFilter;

  // 用闭包存储引用
  div._search = search;
  div._machine = machineSel;
  div._plat = platSel;
  div._status = statusSel;

  return div;
}


// ── 批量操作栏 ──
function renderBatchBar() {
  const bar = document.createElement('div');
  bar.id = 'acctBatchBar';
  bar.style.cssText = 'display:none;position:sticky;bottom:0;background:var(--bg2);border:1px solid var(--primary);border-radius:8px;padding:8px 12px;margin-top:4px;z-index:100;align-items:center;gap:8px;flex-wrap:wrap';

  bar.innerHTML = `
    <span id="batchCount" style="font-size:12px;font-weight:600"></span>
    <button data-action="collect" class="batch-btn" style="background:var(--primary);color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">📡 采集</button>
    <button data-action="login" class="batch-btn" style="background:var(--primary);color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔑 登录</button>
    <button data-action="nurture" class="batch-btn" style="background:var(--primary);color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🏃 养号</button>
    <button data-action="comment" class="batch-btn" style="background:var(--primary);color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">💬 评论</button>
    <button id="batchClearBtn" style="background:transparent;color:var(--text2);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px;margin-left:auto">取消选择</button>
  `;

  // 绑定操作事件
  bar.querySelectorAll('.batch-btn').forEach(btn => {
    btn.onclick = () => handleBatchAction(btn.dataset.action);
  });
  bar.querySelector('#batchClearBtn').onclick = clearSelection;

  return bar;
}


// ── 表格渲染 ──
function renderTable(accounts, filterFn) {
  const div = document.createElement('div');
  div.id = 'acctTableWrap';
  div.style.cssText = 'overflow-x:auto';

  if (!accounts || accounts.length === 0) {
    div.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text2)">暂无账号数据</div>';
    return div;
  }

  // 按机器分组
  const MACHINE_ORDER = ['chengzigedeAir', '5kechengdeAir', '7kecheng'];
  const groups = {};
  accounts.forEach(a => {
    const m = a.owner_machine || 'unknown';
    if (!groups[m]) groups[m] = [];
    groups[m].push(a);
  });

  let html = '<table style="width:100%;font-size:11px;border-collapse:collapse">';
  html += '<thead><tr style="font-size:9px;color:var(--text2);border-bottom:2px solid var(--border)">'
    + '<th style="padding:4px 6px;width:28px"><input type="checkbox" id="acctSelectAll" onchange="window._toggleAll()" title="全选"></th>'
    + '<th style="padding:4px 6px;font-weight:400;text-align:left">机器</th>'
    + '<th style="padding:4px 6px;font-weight:400;text-align:left">账号</th>'
    + '<th style="padding:4px 6px;font-weight:400;text-align:left">手机号</th>'
    + '<th style="padding:4px 6px;font-weight:400;text-align:left">昵称</th>'
    + '<th style="padding:4px 6px;font-weight:400;text-align:right">粉丝</th>'
    + '<th style="padding:4px 6px;font-weight:400;text-align:left">状态</th>'
    + '<th style="padding:4px 6px;font-weight:400;text-align:left">操作</th></tr></thead><tbody>';

  MACHINE_ORDER.filter(m => groups[m]).forEach(m => {
    const accts = groups[m].sort((a, b) => (a.phone || '').localeCompare(b.phone || ''));
    accts.forEach(a => {
      const st = a.login_status || 'unknown';
      const cfg = STATUS_CFG[st] || { dot: '⚪', label: st, color: '#8b8fa3' };
      const idEsc = a.id.replace(/'/g, "\\'");
      // data 属性用于筛选
      const filterData = `${a.id} ${a.phone || ''} ${a.nickname || ''} ${a.identity_dir || ''} ${m}`.toLowerCase();

      html += `<tr class="acct-row" data-filter="${filterData}" data-id="${a.id}" data-machine="${m}" data-platform="${a.platform}" data-status="${st}" style="border-bottom:1px solid var(--border);cursor:pointer" onclick="window._toggleDetail('${idEsc}')">`;
      html += `<td style="padding:3px 6px"><input type="checkbox" class="acct-cb" value="${a.id}" onchange="window._updateBatch()"></td>`;
      html += `<td style="padding:3px 6px;font-size:10px;color:var(--text2)">${m === 'chengzigedeAir' ? '🖥️' : '☁️'}${m}</td>`;
      html += `<td style="padding:3px 6px"><strong>${a.id}</strong></td>`;
      html += `<td style="padding:3px 6px;font-size:10px;color:var(--text2)">${a.phone || '-'}</td>`;
      const platIcon = a.platform === 'xiaohongshu' ? '📕' : '🎵';
      html += `<td style="padding:3px 6px">${platIcon} ${a.nickname || '-'}</td>`;
      html += `<td style="padding:3px 6px;text-align:right">${a.fans || '-'}</td>`;
      html += `<td style="padding:3px 6px;font-size:10px;white-space:nowrap"><span style="color:${cfg.color}">${cfg.dot}</span> ${cfg.label}</td>`;
      html += `<td style="padding:3px 6px;white-space:nowrap">
        <button onclick="window._actSingle('${idEsc}','collect')" class="row-btn" title="采集">📡</button>
        <button onclick="window._actSingle('${idEsc}','login')" class="row-btn" title="登录">🔑</button>
        <button onclick="window._actSingle('${idEsc}','nurture')" class="row-btn" title="养号">🏃</button>
        <button onclick="window._actSingle('${idEsc}','comment')" class="row-btn" title="评论">💬</button>
      </td></tr>`;

      // 展开详情行（初始隐藏）
      html += `<tr class="acct-detail-row" data-parent="${a.id}" style="display:none">
        <td colspan="8" style="padding:8px 12px;background:var(--bg3);font-size:11px">
          ${renderDetailContent(a)}
        </td></tr>`;
    });
  });

  html += '</tbody></table>';
  div.innerHTML = html;

  // 绑定展开事件
  window._toggleDetail = (id) => {
    const rows = document.querySelectorAll(`.acct-detail-row[data-parent="${id}"]`);
    rows.forEach(r => { r.style.display = r.style.display === 'none' ? 'table-row' : 'none'; });
  };

  return div;
}


// ── 展开详情内容 ──
function renderDetailContent(a) {
  const aidEsc = a.id.replace(/'/g, "\\'");
  const phone = a.phone || '';
  const proxy = a.proxy || '';
  const platIcon = a.platform === 'xiaohongshu' ? '📕' : '🎵';

  return `
    <div style="display:flex;gap:16px;flex-wrap:wrap">
      <!-- 左侧：信息 -->
      <div style="min-width:200px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:4px">基本信息</div>
        <div style="display:grid;grid-template-columns:auto 1fr;gap:2px 8px;font-size:11px">
          <span style="color:var(--text2)">身份目录</span><span>${a.identity_dir || '-'}</span>
          <span style="color:var(--text2)">归属机器</span><span>${a.owner_machine || '-'}</span>
          <span style="color:var(--text2)">粉丝/关注</span><span>${a.fans || '-'} / ${a.following || '-'}</span>
          <span style="color:var(--text2)">获赞/作品</span><span>${a.likes || '-'} / ${a.posts || '-'}</span>
          <span style="color:var(--text2)">身份目录</span><span>${a._identity_dir_exists ? '✅' : '❌'}</span>
        </div>
      </div>
      <!-- 右侧：操作 -->
      <div style="min-width:200px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:4px">快捷操作</div>
        <div style="display:flex;flex-direction:column;gap:4px">
          <!-- 短信 -->
          <div style="display:flex;align-items:center;gap:6px;font-size:11px">
            <span>📱 短信</span>
            <button onclick="window._dtSms('${aidEsc}','${phone}')" style="background:var(--bg3);border:1px solid var(--border);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">查看</button>
            <span id="dt_sms_${a.id}" style="font-size:10px;color:var(--text2)"></span>
          </div>
          <!-- 代理 -->
          <div style="display:flex;align-items:center;gap:6px;font-size:11px">
            <span>🖧 代理</span>
            <span id="dt_proxy_${a.id}" style="font-size:10px;color:var(--text2);max-width:140px;overflow:hidden;text-overflow:ellipsis">${proxy || '未设置'}</span>
            <button onclick="window._dtProxy('${aidEsc}')" style="background:var(--bg3);border:1px solid var(--border);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">编辑</button>
          </div>
          <!-- 录制 -->
          <div style="display:flex;align-items:center;gap:6px;font-size:11px">
            <span>🎬 录制</span>
            <button onclick="window._dtRecord('${aidEsc}')" style="background:var(--bg3);border:1px solid var(--border);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">开始录制 →</button>
          </div>
          <!-- 执行记录 -->
          <div style="display:flex;align-items:center;gap:6px;font-size:11px">
            <span>📋 执行记录</span>
            <button onclick="window._dtHistory('${aidEsc}')" style="background:var(--bg3);border:1px solid var(--border);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">查看</button>
            <span id="dt_history_${a.id}" style="font-size:10px;color:var(--text2)"></span>
          </div>
        </div>
      </div>
    </div>
  `;
}


// ── 展开栏操作函数 ──

/** 查看最新短信 — 浮动层展示全部消息 */
window._dtSms = async (id, phone) => {
  const el = document.querySelector('#dt_sms_' + id);
  if (el) el.textContent = '⏳ 查询中...';

  if (!phone) {
    if (el) el.textContent = '❌ 无手机号';
    return;
  }

  try {
    const r = await fetch(`/api/matrix/sms/test/${encodeURIComponent(phone)}`);
    const d = await r.json();

    // 无论有没有消息，都弹窗展示
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:9999;display:flex;align-items:center;justify-content:center';
    overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };

    let bodyHtml = '';
    if (d.status === 'ok' && d.messages && d.messages.length > 0) {
      bodyHtml = `<div style="font-size:10px;color:var(--text2);margin-bottom:8px">共 ${d.total} 条消息，显示最近 ${d.messages.length} 条</div>
        <div style="max-height:400px;overflow-y:auto">`;
      d.messages.forEach(m => {
        const code = m.code ? `<span style="background:#22c55e20;color:#22c55e;padding:1px 6px;border-radius:4px;font-weight:600">${m.code}</span> ` : '';
        const t = m.time || '';
        bodyHtml += `<div style="padding:6px 8px;border-bottom:1px solid var(--border);font-size:11px;line-height:1.5">
          <div>${code}${m.content || ''}</div>
          <div style="font-size:9px;color:var(--text2);margin-top:2px">${t}</div>
        </div>`;
      });
      bodyHtml += '</div>';
    } else if (d.status === 'ok') {
      bodyHtml = '<div style="text-align:center;padding:20px;color:var(--text2);font-size:12px">📭 暂无新短信</div>';
    } else {
      bodyHtml = `<div style="text-align:center;padding:20px;color:#ef4444;font-size:12px">❌ ${d.error || '查询失败'}</div>`;
    }

    overlay.innerHTML = `
      <div style="background:var(--bg2);border-radius:12px;padding:16px;max-width:460px;width:90%;max-height:80vh;overflow-y:auto">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <div style="font-size:14px;font-weight:600">📱 短信 · ${phone}</div>
          <button onclick="this.closest('div[style]').parentElement.remove()" style="background:transparent;border:none;font-size:18px;cursor:pointer;color:var(--text2)">✕</button>
        </div>
        ${bodyHtml}
      </div>`;
    document.body.appendChild(overlay);

    if (el) el.textContent = `📨 ${d.messages?.length || 0}条`;
  } catch(e) {
    if (el) el.textContent = '❌ ' + (e.message || '查询失败');
  }
};

/** 编辑代理（弹窗，含预设下拉） */
window._dtProxy = async (id) => {
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:9999;display:flex;align-items:center;justify-content:center';
  overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };

  // 获取当前代理值
  const cur = document.querySelector('#dt_proxy_' + id)?.textContent || '';
  const curVal = cur === '未设置' ? '' : cur;

  // 获取已有代理列表生成预设
  let presetOpts = '';
  try {
    const pr = await fetch('/api/matrix/proxies');
    const pd = await pr.json();
    const proxies = pd.proxies || [];
    const unique = [...new Set(proxies.map(p => p.proxy).filter(Boolean))];
    if (unique.length) {
      presetOpts = unique.map(p => `<option value="${p.replace(/"/g,'&quot;')}">${p}</option>`).join('');
    }
  } catch(e) { /* ignore */ }

  overlay.innerHTML = `
    <div style="background:var(--bg2);border-radius:12px;padding:20px;max-width:400px;width:90%">
      <div style="font-size:15px;font-weight:600;margin-bottom:12px">🖧 代理设置 — ${id}</div>
      <div style="display:flex;gap:4px;margin-bottom:4px">
        <input id="dtProxyInput" value="${curVal}" placeholder="socks5://127.0.0.1:1080" style="flex:1;padding:6px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:12px;box-sizing:border-box">
        ${curVal ? '<button onclick="document.getElementById(\'dtProxyInput\').value=\'\'" style="background:rgba(220,38,38,.1);color:#ef4444;border:1px solid rgba(220,38,38,.3);border-radius:4px;cursor:pointer;font-size:14px;padding:0 8px" title="清除">✕</button>' : ''}
      </div>
      ${presetOpts ? `
      <select id="dtProxyPreset" onchange="if(this.value)document.getElementById('dtProxyInput').value=this.value" style="width:100%;padding:4px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:11px;margin-bottom:4px">
        <option value="">— 选择已有代理 —</option>
        ${presetOpts}
      </select>` : ''}
      <div style="font-size:10px;color:var(--text2)">留空 = 清除代理</div>
      <div style="display:flex;gap:6px;justify-content:flex-end;margin-top:8px">
        <button onclick="this.closest('div[style]').parentElement.remove()" style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">取消</button>
        <button id="dtProxyOk" style="background:var(--primary);color:#fff;border:none;border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">✅ 保存</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);

  overlay.querySelector('#dtProxyOk').onclick = async () => {
    const val = document.querySelector('#dtProxyInput')?.value?.trim() || '';
    const btn = overlay.querySelector('#dtProxyOk');
    btn.textContent = '⏳ 保存中...'; btn.disabled = true;
    try {
      const r = await fetch(`/api/matrix/proxies/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proxy: val }),
      });
      const d = await r.json();
      if (d.status === 'ok') {
        const el = document.querySelector('#dt_proxy_' + id);
        if (el) el.textContent = val || '未设置';
        overlay.remove();
      } else {
        alert('❌ ' + (d.error || '保存失败'));
      }
    } catch(e) {
      alert('❌ ' + e.message);
    }
    btn.textContent = '✅ 保存'; btn.disabled = false;
  };
};

/** 开始录制（跳转到录制视图） */
window._dtRecord = async (id) => {
  try {
    // 先调用录制 API 启动
    const r = await fetch(`/api/matrix/accounts/${encodeURIComponent(id)}/record`, { method: 'POST' });
    const d = await r.json();
    if (d.status === 'ok') {
      // 跳转到录制页面
      if (typeof window.switchView === 'function') {
        window.switchView('matrix-record');
      } else {
        alert('✅ 录制已启动 (' + (d.message || '') + ')，请前往录制页面操作');
      }
    } else {
      alert('❌ ' + (d.message || d.error || '录制启动失败'));
    }
  } catch(e) {
    alert('❌ ' + e.message);
  }
};

/** 查看最近执行记录 */
window._dtHistory = async (id) => {
  const el = document.querySelector('#dt_history_' + id);
  if (!el) return;
  el.textContent = '⏳ 查询中...';
  try {
    const r = await fetch('/api/matrix/nurture/results?limit=5');
    const d = await r.json();
    const results = d.results || [];
    // 筛选属于该账号的记录
    const mine = results.filter(r => (r.accounts || []).includes(id) || r.account === id);
    if (mine.length === 0) {
      el.textContent = '📭 无执行记录';
    } else {
      const lines = mine.slice(0, 3).map(r => {
        const t = r.blueprint || r.type || '未知';
        const time = r.completed_at ? new Date(r.completed_at).toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : '';
        return `${t} ${time}`;
      });
      el.textContent = lines.join(' · ');
    }
  } catch(e) {
    el.textContent = '❌ ' + (e.message || '查询失败');
  }
};


// ── 筛选逻辑 ──
function doFilter() {
  const bar = document.querySelector('#acctFilterBar');
  if (!bar) return;
  const q = (bar._search?.value || '').toLowerCase();
  const machine = bar._machine?.value || '';
  const plat = bar._plat?.value || '';
  const status = bar._status?.value || '';

  const rows = document.querySelectorAll('.acct-row');
  let visible = 0;
  rows.forEach(row => {
    const fd = (row.dataset.filter || '').toLowerCase();
    let show = true;
    if (q && !fd.includes(q)) show = false;
    if (machine && row.dataset.machine !== machine) show = false;
    if (plat && row.dataset.platform !== plat) show = false;
    if (status && row.dataset.status !== status) show = false;
    row.style.display = show ? '' : 'none';
    // 隐藏对应的详情行
    const detail = document.querySelector(`.acct-detail-row[data-parent="${row.dataset.id}"]`);
    if (detail && !show) detail.style.display = 'none';
    if (show) visible++;
  });

  const count = document.querySelector('#acctCount');
  if (count) count.textContent = `共 ${visible}/${window._v2Accounts?.length || 0} 个`;
}


// ── 全选/取消全选 ──
window._toggleAll = () => {
  const checked = document.querySelector('#acctSelectAll')?.checked || false;
  document.querySelectorAll('.acct-cb').forEach(cb => {
    // 只勾选可见的行
    const row = cb.closest('.acct-row');
    if (row && row.style.display !== 'none') cb.checked = checked;
  });
  updateBatchBar();
};

window._updateBatch = updateBatchBar;

function updateBatchBar() {
  const checked = document.querySelectorAll('.acct-cb:checked');
  const bar = document.querySelector('#acctBatchBar');
  const count = document.querySelector('#batchCount');
  if (!bar || !count) return;

  if (checked.length === 0) {
    bar.style.display = 'none';
    return;
  }
  bar.style.display = 'flex';
  count.textContent = `已选 ${checked.length} 个账号`;
}

function clearSelection() {
  document.querySelectorAll('.acct-cb').forEach(cb => cb.checked = false);
  document.querySelector('#acctSelectAll') && (document.querySelector('#acctSelectAll').checked = false);
  updateBatchBar();
}

function getSelectedIds() {
  return [...document.querySelectorAll('.acct-cb:checked')].map(cb => cb.value);
}


// ── 单账号操作 ──
window._actSingle = async (accountId, action) => {
  if (action === 'comment') {
    // 评论跳转专用页面
    try { window.switchView('matrix-comment', { accounts: [accountId] }); }
    catch(e) { alert('评论页面不可用'); }
    return;
  }
  if (action === 'nurture') {
    // 养号弹窗
    showNurtureDialog([accountId]);
    return;
  }
  // 采集/登录 → 直接提交
  try {
    const r = await fetch(`${BASE}/v2/accounts/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ account_ids: [accountId], action }),
    });
    const d = await r.json();
    if (d.status === 'ok') {
      alert(`✅ 已提交${action === 'collect' ? '采集' : '登录'}任务`);
    } else {
      alert('❌ ' + (d.detail || '操作失败'));
    }
  } catch(e) {
    alert('❌ ' + e.message);
  }
};


// ── 批量操作 ──
async function handleBatchAction(action) {
  const ids = getSelectedIds();
  if (ids.length === 0) { alert('请先选择账号'); return; }

  if (action === 'comment') {
    // 评论 → 跳转到评论页面，带入选中的账号
    try { window.switchView('matrix-comment', { accounts: ids }); }
    catch(e) { alert('评论页面不可用'); }
    return;
  }

  if (action === 'nurture') {
    showNurtureDialog(ids);
    return;
  }

  // 采集/登录 → 直接提交
  try {
    const r = await fetch(`${BASE}/v2/accounts/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ account_ids: ids, action }),
    });
    const d = await r.json();
    if (d.status === 'ok') {
      alert(`✅ 已提交 ${ids.length} 个账号的${action === 'collect' ? '采集' : '登录'}任务`);
      clearSelection();
    } else {
      alert('❌ ' + (d.detail || '操作失败'));
    }
  } catch(e) {
    alert('❌ ' + e.message);
  }
}


// ── 养号弹窗 ──
function showNurtureDialog(accountIds) {
  // 参数：蓝图按平台过滤，轮次 1-20
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:9999;display:flex;align-items:center;justify-content:center';
  overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };

  overlay.innerHTML = `
    <div style="background:var(--bg2);border-radius:12px;padding:20px;max-width:360px;width:90%">
      <div style="font-size:15px;font-weight:600;margin-bottom:12px">🏃 养号设置</div>
      <div style="font-size:11px;color:var(--text2);margin-bottom:10px">选中 ${accountIds.length} 个账号</div>
      <div style="display:grid;gap:8px;font-size:12px">
        <label>
          蓝图
          <select id="nurtureBlueprint" style="width:100%;padding:4px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;margin-top:3px">
            <option value="douyin_daily">🎵 douyin_daily</option>
            <option value="xhs_daily">📕 xhs_daily</option>
          </select>
        </label>
        <label>
          轮次
          <div style="display:flex;gap:4px;margin-top:3px">
            ${[1, 3, 5, 10].map(n => `<button class="round-preset" data-val="${n}" style="flex:1;padding:4px;background:var(--bg3);border:1px solid var(--border);border-radius:4px;cursor:pointer;font-size:11px">${n}轮</button>`).join('')}
          </div>
          <input id="nurtureRounds" type="number" min="1" max="20" value="3" style="width:100%;padding:4px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;margin-top:3px;text-align:center">
        </label>
      </div>
      <div style="display:flex;gap:6px;justify-content:flex-end;margin-top:12px">
        <button onclick="this.closest('div[style]').parentElement.remove()" style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">取消</button>
        <button id="nurtureOk" style="background:var(--primary);color:#fff;border:none;border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">✅ 开始养号</button>
      </div>
    </div>`;

  document.body.appendChild(overlay);

  // 轮次预设按钮
  overlay.querySelectorAll('.round-preset').forEach(btn => {
    btn.onclick = () => {
      document.querySelector('#nurtureRounds').value = btn.dataset.val;
    };
  });

  // 确认按钮
  overlay.querySelector('#nurtureOk').onclick = async () => {
    const blueprint = document.querySelector('#nurtureBlueprint')?.value || 'douyin_daily';
    const rounds = parseInt(document.querySelector('#nurtureRounds')?.value || '3');
    const btn = document.querySelector('#nurtureOk');
    btn.textContent = '⏳ 提交中...'; btn.disabled = true;

    try {
      const r = await fetch(`${BASE}/v2/accounts/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_ids: accountIds, action: 'nurture', params: { blueprint, rounds } }),
      });
      const d = await r.json();
      if (d.status === 'ok') {
        alert(`✅ 已提交 ${accountIds.length} 个账号的养号任务`);
        overlay.remove();
        clearSelection();
      } else {
        alert('❌ ' + (d.detail || '操作失败'));
      }
    } catch(e) {
      alert('❌ ' + e.message);
    }
    btn.textContent = '✅ 开始养号'; btn.disabled = false;
  };
}


// ── 刷新视图（只刷新表格区域，保留概要栏/筛选栏/批量栏）──
async function refreshView() {
  // 显示表格加载状态
  const wrap = document.querySelector('#acctTableWrap');
  if (!wrap) return;
  wrap.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text2)">⏳ 刷新中...</div>';

  try {
    const [accountsRes, summaryRes] = await Promise.all([
      fetch(`${BASE}/v2/accounts`).then(r => r.ok ? r.json() : { accounts: [] }),
      fetch(`${BASE}/v2/status-summary`).then(r => r.ok ? r.json() : {}),
    ]);
    const allAccounts = accountsRes.accounts || [];
    window._v2Accounts = allAccounts;

    // 更新概要栏的状态卡片（不重建，只改文本）
    const summaryBar = wrap.parentElement?.querySelector('div:first-child');
    if (summaryBar) {
      const keys = STATUS_ORDER.filter(k => (summaryRes[k] || 0) > 0);
      const cards = summaryBar.querySelectorAll('span[style*="border-radius:12px"]');
      // 重建概要栏中状态卡片部分
      cards.forEach(c => c.remove());
      const totalSpan = summaryBar.querySelector('span[style*="margin-left:auto"]');
      if (totalSpan) totalSpan.textContent = `共 ${allAccounts.length} 个账号`;

      // 重新插入状态卡片
      let insertBefore = totalSpan || summaryBar.firstChild;
      keys.forEach(k => {
        const cfg = STATUS_CFG[k] || { dot: '⚪', label: k, color: '#8b8fa3' };
        const count = summaryRes[k] || 0;
        const card = document.createElement('span');
        card.style.cssText = `padding:2px 10px;border-radius:12px;font-size:11px;background:${cfg.color}15;border:1px solid ${cfg.color}40;color:var(--text);cursor:pointer`;
        card.innerHTML = `${cfg.dot} ${cfg.label} ${count}`;
        card.onclick = () => applyFilter('status', k);
        summaryBar.insertBefore(card, insertBefore);
      });
    }

    // 更新筛选栏计数
    const countEl = document.querySelector('#acctCount');
    if (countEl) countEl.textContent = `共 ${allAccounts.length} 个`;

    // 只刷新表格
    const newTable = renderTable(allAccounts);
    wrap.replaceWith(newTable);

    // 应用当前筛选条件
    doFilter();
  } catch(e) {
    wrap.innerHTML = `<div class="error">❌ ${e.message || e}</div>`;
  }
}


// ── 外部调用筛选（颜色卡片点击） ──
function applyFilter(type, value) {
  const bar = document.querySelector('#acctFilterBar');
  if (!bar) return;
  if (type === 'status' && bar._status) {
    bar._status.value = value;
  }
  doFilter();
}

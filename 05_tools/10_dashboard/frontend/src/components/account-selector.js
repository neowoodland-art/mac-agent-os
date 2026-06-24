/**
 * 统一账号选择器（v2 — 全字段版）
 * 
 * 显示字段: 身份目录 | 账号ID | 昵称 | 粉丝 | 关注 | 获赞 | 作品 | 平台 | 状态 | 蓝图 | 采集时间
 * 
 * @param {object} opts.accounts - [{id, platform, owner_machine, identity_dir, phone, 
 *   _status, nickname, fans, following, likes, posts, enabled}]
 * @param {object} [opts.hpIndex] - 采集信息索引 {identity_dir: {douyin: {}, xiaohongshu: {}}}
 * @param {boolean} [opts.checkAll=true] - 默认全选
 * @param {string} [opts.height='350px'] - 最大高度
 * @param {boolean} [opts.compact=false] - 紧凑模式
 * @param {function} [opts.onSelect] - 选择变更回调
 */

let _uidCounter = 0;

export function createAccountSelector(container, opts = {}) {
  const el = typeof container === 'string' ? document.getElementById(container) : container;
  if (!el) return null;

  const uid = `as_${++_uidCounter}`;
  const allAccts = (opts.accounts || []).filter(a => a.enabled !== false);
  const hpIndex = opts.hpIndex || {};
  const checkAll = opts.checkAll !== false;
  const compact = !!opts.compact;

  // 机器→身份分组
  const tree = {};
  allAccts.forEach(a => {
    if (opts.filterMachine && a.owner_machine !== opts.filterMachine) return;
    if (opts.filterPlatform && a.platform !== opts.filterPlatform) return;
    const machine = a.owner_machine || '未分配';
    const ident = a.identity_dir || a.id;
    if (!tree[machine]) tree[machine] = {};
    if (!tree[machine][ident]) tree[machine][ident] = { phone: a.phone || '', accounts: [] };
    tree[machine][ident].accounts.push(a);
  });

  const machineOrder = Object.keys(tree).sort((a, b) => {
    if (a === 'chengzigedeAir') return -1;
    if (b === 'chengzigedeAir') return 1;
    return a.localeCompare(b);
  });

  let html = '';

  // 搜索框
  if (!compact) {
    html += `<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:4px">
      <input class="as-filter-${uid}" placeholder="🔍 搜索账号ID/手机号/昵称..."
        oninput="_filterAS('${uid}')"
        style="flex:1;min-width:100px;padding:3px 6px;font-size:11px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px">
      <span style="font-size:11px;color:var(--text2)">${allAccts.length} 个</span>
      <span style="font-size:11px;color:var(--green)">🎵 ${allAccts.filter(a => a.platform === 'douyin').length}</span>
      <span style="font-size:11px;color:#6366f1">📕 ${allAccts.filter(a => a.platform === 'xiaohongshu').length}</span>
    </div>`;
  }

  html += `<div class="as-body-${uid}" style="max-height:${opts.height || '350px'};overflow-y:auto">`;

  machineOrder.forEach(machine => {
    const idents = tree[machine];
    const isLocal = machine === 'chengzigedeAir';
    const machineLabel = isLocal ? '🖥️ ' + machine : '☁️ ' + machine;
    const grpId = `${uid}_m_${machine.replace(/[^a-zA-Z0-9]/g, '_')}`;
    const acctCount = Object.values(idents).reduce((s, i) => s + i.accounts.length, 0);
    const identCount = Object.keys(idents).length;
    const loggedIn = Object.values(idents).reduce((s, i) => s + i.accounts.filter(a => a._status === 'logged_in').length, 0);

    html += '<div style="border:1px solid var(--border);border-radius:5px;margin-bottom:3px;overflow:hidden">';
    html += `<div onclick="_toggleGroup('${grpId}')" style="display:flex;align-items:center;gap:5px;padding:4px 8px;background:var(--bg3);cursor:pointer;font-size:11px;user-select:none">`;
    html += `<span id="${grpId}_arrow" style="font-size:9px;opacity:.6">▼</span>`;
    html += `<input type="checkbox" onclick="event.stopPropagation();_toggleMachineCB(this,'${uid}')" data-machine="${machine}" ${checkAll ? 'checked' : ''}>`;
    html += `<strong>${machineLabel}</strong>`;
    html += `<span style="font-size:9px;color:var(--text2)">${identCount}身份 ${acctCount}账号 | ${loggedIn}已登录</span>`;
    html += '</div>';
    html += `<div id="${grpId}" style="overflow-x:auto">`;
    html += '<table style="width:100%;font-size:10px;border-collapse:collapse"><tbody>';

    // 表头
    html += '<tr style="font-size:9px;color:var(--text2);border-bottom:1px solid var(--border)">';
    html += '<th style="padding:2px 4px;font-weight:400;text-align:left">身份/手机</th>';
    html += '<th style="padding:2px 4px;font-weight:400;width:20px"></th>'; // checkbox col header
    html += '<th style="padding:2px 4px;font-weight:400;text-align:left">账号ID</th>';
    html += '<th style="padding:2px 4px;font-weight:400;text-align:left">昵称</th>';
    html += '<th style="padding:2px 4px;font-weight:400;text-align:right" title="粉丝">👥</th>';
    html += '<th style="padding:2px 4px;font-weight:400;text-align:right" title="关注">👍</th>';
    html += '<th style="padding:2px 4px;font-weight:400;text-align:right" title="获赞">❤️</th>';
    html += '<th style="padding:2px 4px;font-weight:400;text-align:right" title="作品">📝</th>';
    html += '<th style="padding:2px 4px;font-weight:400"></th>'; // platform
    html += '<th style="padding:2px 4px;font-weight:400;text-align:left">状态</th>';
    html += '<th style="padding:2px 4px;font-weight:400;text-align:left">蓝图</th>';
    html += '<th style="padding:2px 4px;font-weight:400;text-align:left">采集</th>';
    html += '</tr>';

    Object.keys(idents).sort().forEach(ident => {
      const identity = idents[ident];
      const hp = hpIndex[ident] || hpIndex[identity.phone];
      const phoneDisplay = identity.phone ? identity.phone.slice(0, 11) : '';
      // 身份路径简称：identities/xxx → xxx
      const identShort = ident.replace('identities/', '');
      const rowspan = identity.accounts.length;

      identity.accounts.forEach((a, idx) => {
        const plat = a.platform === 'douyin' ? '🎵' : '📕';
        const defBP = a.platform === 'xiaohongshu' ? 'xhs_daily' : 'douyin_daily';
        const hpAcc = hp ? (a.platform === 'douyin' ? hp.douyin : hp.xiaohongshu) : null;
        const nickname = hpAcc?.nickname || a.nickname || '';
        const fans = hpAcc?.fans || a.fans || '';
        const following = hpAcc?.following || a.following || '';
        const likes = hpAcc?.likes || a.likes || '';
        const posts = hpAcc?.posts || a.posts || '';
        const hpTime = hpAcc?.collected_at || '';
        const hpTimeDisplay = hpTime ? new Date(hpTime).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '';

        // 状态图标
        const statusMap = {
          'logged_in':     '<span style="color:#22c55e;font-size:9px">🟢 已登录</span>',
          'remote':        '<span style="color:#6366f1;font-size:9px">🔵 远程</span>',
          'expired':       '<span style="color:#f59e0b;font-size:9px">🟡 过期</span>',
          'no_cookie':     '<span style="color:#ef4444;font-size:9px">🔴 无Cookie</span>',
          'disabled':      '<span style="color:#9ca3af;font-size:9px">⚪ 禁用</span>',
          'error':         '<span style="color:#ef4444;font-size:9px">❌ 错误</span>',
        };
        const statusIcon = statusMap[a._status] || `<span style="color:var(--text2);font-size:9px">${a._status || '未知'}</span>`;

        html += `<tr class="as-row-${uid}" data-account="${a.id}" data-machine="${machine}" data-platform="${a.platform}" data-bp="${defBP}">`;
        if (idx === 0) {
          // 身份行（合并单元格）
          const dirDisplay = identShort.length > 20 ? identShort.slice(0, 18) + '…' : identShort;
          html += `<td rowspan="${rowspan}" style="padding:2px 4px;font-size:9px;color:var(--text2);vertical-align:middle;border-right:1px solid var(--border);white-space:nowrap" title="身份: ${identShort}">`;
          html += `📁${dirDisplay}`;
          if (phoneDisplay) html += `<br><span style="opacity:.6">📱${phoneDisplay}</span>`;
          html += '</td>';
        }
        html += `<td style="padding:2px 3px;width:20px"><input type="checkbox" class="as-cb-${uid}" value="${a.id}" data-plat="${a.platform}" data-bp="${defBP}" data-machine="${machine}" ${checkAll ? 'checked' : ''} onchange="_onASChange('${uid}')"></td>`;
        html += `<td style="padding:2px 4px;white-space:nowrap"><strong>${a.id}</strong></td>`;
        html += `<td style="padding:2px 4px;max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${nickname || '-'}</td>`;
        html += `<td style="padding:2px 4px;text-align:right;white-space:nowrap">${fans || '-'}</td>`;
        html += `<td style="padding:2px 4px;text-align:right;white-space:nowrap">${following || '-'}</td>`;
        html += `<td style="padding:2px 4px;text-align:right;white-space:nowrap">${likes || '-'}</td>`;
        html += `<td style="padding:2px 4px;text-align:right;white-space:nowrap">${posts || '-'}</td>`;
        html += `<td style="padding:2px 4px">${plat}</td>`;
        html += `<td style="padding:2px 4px;white-space:nowrap">${statusIcon}</td>`;
        html += `<td style="padding:2px 4px;font-size:9px;color:var(--text2);white-space:nowrap">📋${defBP}</td>`;
        html += `<td style="padding:2px 4px;font-size:9px;color:var(--text2);white-space:nowrap">${hpTimeDisplay || '-'}</td>`;
        html += '</tr>';
      });
    });

    html += '</tbody></table></div></div>';
  });
  html += '</div>';

  // 统计行
  if (!compact) {
    html += `<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 4px;font-size:10px;color:var(--text2)">
      <span>共 ${allAccts.length} 个账号</span>
      <span id="${uid}_count">已选 ${checkAll ? allAccts.length : 0} 个</span>
    </div>`;
  }

  el.innerHTML = html;
  _refreshCount(uid);
  _registerGlobals();

  return {
    uid,
    el,
    getSelected() {
      return Array.from(document.querySelectorAll(`.as-cb-${uid}:checked`)).map(cb => ({
        id: cb.value,
        platform: cb.dataset.plat,
        blueprint: cb.dataset.bp,
        machine: cb.dataset.machine,
      }));
    },
    getCount() {
      return document.querySelectorAll(`.as-cb-${uid}:checked`).length;
    },
    selectAll(checked) {
      document.querySelectorAll(`.as-cb-${uid}`).forEach(cb => cb.checked = !!checked);
      _refreshCount(uid);
      if (opts.onSelect) opts.onSelect(this.getSelected());
    },
    destroy() {
      el.innerHTML = '';
    },
  };
}

function _refreshCount(uid) {
  const checked = document.querySelectorAll(`.as-cb-${uid}:checked`).length;
  const el = document.getElementById(`${uid}_count`);
  if (el) el.textContent = '已选 ' + checked + ' 个';
}

function _registerGlobals() {
  if (window._asGlobalsRegistered) return;
  window._asGlobalsRegistered = true;

  window._toggleGroup = function (grpId) {
    const el = document.getElementById(grpId);
    const arrow = document.getElementById(grpId + '_arrow');
    if (!el) return;
    const hidden = el.style.display === 'none';
    el.style.display = hidden ? '' : 'none';
    if (arrow) arrow.textContent = hidden ? '▼' : '▶';
  };

  window._toggleMachineCB = function (cb, uid) {
    const machine = cb.dataset.machine;
    const checked = cb.checked;
    document.querySelectorAll(`.as-cb-${uid}[data-machine="${machine}"]`).forEach(c => c.checked = checked);
    _refreshCount(uid);
  };

  window._onASChange = function (uid) {
    _refreshCount(uid);
    // 触发自定义事件供外部监听
    const evt = new CustomEvent('acct-selector-change', { detail: { uid } });
    document.dispatchEvent(evt);
  };

  window._filterAS = function (uid) {
    const q = document.querySelector(`.as-filter-${uid}`)?.value?.toLowerCase() || '';
    document.querySelectorAll(`.as-row-${uid}`).forEach(row => {
      const txt = (row.textContent || '').toLowerCase();
      row.style.display = txt.includes(q) ? '' : 'none';
    });
  };
}

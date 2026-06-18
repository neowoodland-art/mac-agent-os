/**
 * 统一账号选择器
 * 
 * 所有视图共用的账号选择组件。
 * 支持三级分组（机器→身份→账号）、搜索、筛选、多选。
 * 每个视图只需传账号数据 + 配置选项，返回选择结果。
 */

let _uidCounter = 0;

/**
 * 创建账号选择器
 * @param {HTMLElement|string} container - 容器元素或ID
 * @param {object} opts
 * @param {Array} opts.accounts - 账号数组 [{id, platform, owner_machine, identity_dir, phone, _status, enabled}]
 * @param {object} [opts.hpIndex] - 采集信息索引 {identity_dir: {douyin: {}, xiaohongshu: {nickname, collected_at} }}
 * @param {boolean} [opts.checkAll=true] - 默认全选
 * @param {string} [opts.height='350px'] - 最大高度
 * @param {boolean} [opts.compact=false] - 紧凑模式（无搜索、无统计、无采集时间列）
 * @param {string} [opts.filterMachine=''] - 只显示某台机器
 * @param {string} [opts.filterPlatform=''] - 只显示某平台
 * @param {boolean} [opts.showPlatform=true] - 显示平台图标列
 * @param {boolean} [opts.showStatus=true] - 显示登录状态列
 * @param {boolean} [opts.showBlueprint=true] - 显示蓝图列
 * @param {boolean} [opts.showCollectTime=true] - 显示采集时间列
 * @param {function} [opts.onSelect] - 选择变更回调 (selected) => void
 * @returns {object} { el, getSelected(), getCount(), uid }
 */
export function createAccountSelector(container, opts = {}) {
  const el = typeof container === 'string' ? document.getElementById(container) : container;
  if (!el) return null;

  const uid = `as_${++_uidCounter}`;
  const allAccts = (opts.accounts || []).filter(a => a.enabled !== false);
  const hpIndex = opts.hpIndex || {};
  const checkAll = opts.checkAll !== false;
  const compact = !!opts.compact;
  const showPlat = opts.showPlatform !== false;
  const showStatus = opts.showStatus !== false;
  const showBP = opts.showBlueprint !== false;
  const showCol = opts.showCollectTime !== false && !compact;

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

  // 搜索框（非紧凑模式）
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
    html += `<span style="font-size:9px;color:var(--text2)">${identCount} 身份 ${acctCount} 账号 | ${loggedIn} 已登录</span>`;
    html += '</div>';
    html += `<div id="${grpId}" style="overflow-x:auto">`;
    html += '<table style="width:100%;font-size:10px;border-collapse:collapse"><tbody>';

    Object.keys(idents).sort().forEach(ident => {
      const identity = idents[ident];
      const hp = hpIndex[ident] || hpIndex[identity.phone];
      const phoneDisplay = identity.phone ? identity.phone.slice(0, 11) : ident.replace('phone_', '');
      const nickDisplay = hp?.display_name ? hp.display_name.slice(0, 10) : '';
      const rowspan = identity.accounts.length;

      identity.accounts.forEach((a, idx) => {
        const plat = a.platform === 'douyin' ? '🎵' : '📕';
        const defBP = a.platform === 'xiaohongshu' ? 'xhs_daily' : 'douyin_daily';
        const hpAcc = hp ? (a.platform === 'douyin' ? hp.douyin : hp.xiaohongshu) : null;
        const nickname = hpAcc?.nickname ? hpAcc.nickname.slice(0, 12) : '';
        const hpTime = hpAcc?.collected_at || '';
        const hpTimeDisplay = hpTime ? new Date(hpTime).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '';

        let statusIcon = '';
        if (showStatus) {
          statusIcon = a._status === 'logged_in'
            ? '<span class="badge badge-green" style="font-size:9px">已登录</span>'
            : `<span class="badge badge-amber" style="font-size:9px">${a._status || '未知'}</span>`;
        }

        html += `<tr class="as-row-${uid}" data-account="${a.id}" data-machine="${machine}" data-platform="${a.platform}" data-bp="${defBP}">`;
        if (idx === 0) {
          html += `<td rowspan="${rowspan}" style="padding:2px 4px;font-size:9px;color:var(--text2);vertical-align:middle;border-right:1px solid var(--border);white-space:nowrap">📱${phoneDisplay}${nickDisplay ? ' ' + nickDisplay : ''}</td>`;
        }
        html += `<td style="padding:2px 3px;width:20px"><input type="checkbox" class="as-cb-${uid}" value="${a.id}" data-plat="${a.platform}" data-bp="${defBP}" data-machine="${machine}" ${checkAll ? 'checked' : ''} onchange="_onASChange('${uid}')"></td>`;
        html += `<td style="padding:2px 4px;white-space:nowrap"><strong>${a.id}</strong></td>`;
        if (showPlat) html += `<td style="padding:2px 4px">${plat}</td>`;
        if (showStatus) html += `<td style="padding:2px 4px;white-space:nowrap">${statusIcon}</td>`;
        if (showBP) html += `<td style="padding:2px 4px;font-size:9px;color:var(--text2);white-space:nowrap">📋${defBP}</td>`;
        if (showCol) html += `<td style="padding:2px 4px;font-size:9px;color:var(--text2);white-space:nowrap">采集:${hpTimeDisplay}</td>`;
        html += '</tr>';
      });
    });

    html += '</tbody></table></div></div>';
  });
  html += '</div>';

  // 统计行（非紧凑模式）
  if (!compact) {
    html += `<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 4px;font-size:10px;color:var(--text2)">
      <span>共 ${allAccts.length} 个账号</span>
      <span id="${uid}_count">已选 ${checkAll ? allAccts.length : 0} 个</span>
    </div>`;
  }

  el.innerHTML = html;
  _refreshCount(uid);

  // 注册全局辅助函数
  _registerGlobals();

  const api = {
    uid,
    el,

    /** 获取选中账号列表 */
    getSelected() {
      return Array.from(document.querySelectorAll(`.as-cb-${uid}:checked`)).map(cb => ({
        id: cb.value,
        platform: cb.dataset.plat,
        blueprint: cb.dataset.bp,
        machine: cb.dataset.machine,
      }));
    },

    /** 获取选中数量 */
    getCount() {
      return document.querySelectorAll(`.as-cb-${uid}:checked`).length;
    },

    /** 全选/取消全选 */
    selectAll(checked) {
      document.querySelectorAll(`.as-cb-${uid}`).forEach(cb => cb.checked = !!checked);
      _refreshCount(uid);
      if (opts.onSelect) opts.onSelect(api.getSelected());
    },

    /** 销毁 */
    destroy() {
      el.innerHTML = '';
    },
  };

  return api;
}

// ── 内部辅助 ──

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

  window._toggleMachineCB = function (master, uid) {
    const machine = master.dataset.machine;
    document.querySelectorAll(`.as-cb-${uid}[data-machine="${machine}"]`).forEach(cb => cb.checked = master.checked);
    _refreshCount(uid);
  };

  window._filterAS = function (uid) {
    const q = (document.querySelector(`.as-filter-${uid}`)?.value || '').toLowerCase();
    document.querySelectorAll(`.as-row-${uid}`).forEach(row => {
      const acct = row.dataset.account || '';
      const phone = row.querySelector('td:first-child')?.textContent?.replace('📱', '') || '';
      const nick = row.querySelectorAll('td')[4]?.textContent || '';
      const match = !q || acct.includes(q) || phone.includes(q) || nick.includes(q);
      row.style.display = match ? '' : 'none';
    });
    _refreshCount(uid);
  };

  window._onASChange = function (uid) {
    _refreshCount(uid);
  };
}

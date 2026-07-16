/**
 * 统一账号选择器（v3 — 联邦风格版）
 * 
 * 保留原 v2 特性：
 *   按机器可折叠分组、搜索/筛选、checkbox 多选、getSelected() API
 * 
 * 升级内容：
 *   状态显示：颜色圆点+中文文字
 *   行展示：☑ | 📱手机号 | 账号 | 🎵昵称 | 粉丝 | 🟢状态
 *   按身份分组，同一身份用同一颜色标记
 *   底部批量操作栏：📡采集 🔑登录 🏃养号 💬评论
 *   数据源：V2 API（统一口径）
 * 
 * @param {HTMLElement|string} container 容器元素或ID
 * @param {object} opts
 * @param {Array} opts.accounts - 账号列表
 * @param {object} [opts.hpIndex] - 采集信息索引（兼容旧接口）
 * @param {boolean} [opts.checkAll=true] - 默认全选
 * @param {string} [opts.height='350px'] - 最大高度
 * @param {boolean} [opts.compact=false] - 紧凑模式（隐藏筛选栏+统计）
 * @param {boolean} [opts.showBatchBar=true] - 显示底部批量操作栏
 * @param {Array} [opts.batchActions=['collect','login','nurture','comment']] - 批量操作按钮
 * @param {function} [opts.onSelect] - 选择变更回调
 * @param {function} [opts.onBatchDone] - 批量操作完成回调
 */

let _uidCounter = 0;

// ── 状态配置（与 accounts-center.js 一致）──
const STATUS_CFG = {
  logged_in:       { color: '#22c55e', dot: '🟢', label: '已登录' },
  need_login:      { color: '#ef4444', dot: '🔴', label: '需重新登录' },
  no_cookie:       { color: '#8b8fa3', dot: '⚪', label: '无Cookie' },
  no_identity:     { color: '#8b8fa3', dot: '⚪', label: '未配置' },
  banned:          { color: '#000',    dot: '⚫', label: '已封号' },
  sms_skip:        { color: '#f97316', dot: '📱', label: '短信待验证' },
  running:         { color: '#3b82f6', dot: '🔵', label: '执行中' },
  disabled:        { color: '#d1d5db', dot: '⬜', label: '已禁用' },
  unknown:         { color: '#8b8fa3', dot: '⚪', label: '未知' },
};
const STATUS_ORDER = ['banned', 'need_login', 'sms_skip', 'no_cookie', 'running', 'disabled', 'unknown', 'logged_in'];

// ── 身份颜色池（按身份分配，方便辨识同一身份的不同平台账号）──
const IDENTITY_COLORS = [
  '#e3f2fd', '#fce4ec', '#e8f5e9', '#fff3e0', '#f3e5f5',
  '#e0f7fa', '#fff8e1', '#fbe9e7', '#e8eaf6', '#f1f8e9',
  '#fce4ec', '#e8f5e9', '#fff3e0', '#e0f7fa', '#f3e5f5',
];


export function createAccountSelector(container, opts = {}) {
  const el = typeof container === 'string' ? document.getElementById(container) : container;
  if (!el) return null;

  const uid = `as_${++_uidCounter}`;
  const allAccts = (opts.accounts || []).filter(a => a.enabled !== false);
  const hpIndex = opts.hpIndex || {};
  const checkAll = opts.checkAll !== false;
  const compact = !!opts.compact;
  const showBatchBar = opts.showBatchBar !== false;
  const batchActions = opts.batchActions || ['collect','login','nurture','comment'];

  // ── 全局筛选状态 ──
  let _filterQ = '';
  let _filterMachine = '';
  let _filterPlatform = '';
  let _filterStatus = '';

  // ── 状态图标辅助 ──
  function _statusHtml(st) {
    const cfg = STATUS_CFG[st] || { dot: '⚪', label: st, color: '#8b8fa3' };
    return `<span style="color:${cfg.color}">${cfg.dot}</span> ${cfg.label}`;
  }

  // ── 分配身份颜色 ──
  function _assignIdentityColors(accts) {
    // 同一机器内，同一身份用相同颜色
    const byMachine = {};
    accts.forEach(a => {
      const m = a.owner_machine || a._source_machine || '未分配';
      if (!byMachine[m]) byMachine[m] = {};
      const ident = a.identity_dir || a.id;
      if (!byMachine[m][ident]) byMachine[m][ident] = [];
      byMachine[m][ident].push(a);
    });

    const colorMap = {};
    Object.keys(byMachine).forEach(m => {
      const idents = Object.keys(byMachine[m]);
      idents.forEach((ident, idx) => {
        colorMap[`${m}::${ident}`] = IDENTITY_COLORS[idx % IDENTITY_COLORS.length];
      });
    });
    return colorMap;
  }

  // ── 构建 HTML ──
  function _render() {
    // 筛选所有账号
    let filtered = allAccts;
    if (_filterQ) {
      const lq = _filterQ.toLowerCase();
      filtered = filtered.filter(a =>
        (a.id || '').toLowerCase().includes(lq) ||
        (a.phone || '').toLowerCase().includes(lq) ||
        (a.nickname || '').toLowerCase().includes(lq) ||
        (a.owner_machine || '').toLowerCase().includes(lq)
      );
    }
    if (_filterMachine) filtered = filtered.filter(a => (a.owner_machine || a._source_machine) === _filterMachine);
    if (_filterPlatform) filtered = filtered.filter(a => a.platform === _filterPlatform);
    if (_filterStatus) filtered = filtered.filter(a => a.login_status === _filterStatus || a._status === _filterStatus);

    // 树形分组：机器 → 身份 → [账号]
    const fTree = {};
    filtered.forEach(a => {
      const machine = a.owner_machine || a._source_machine || '未分配';
      if (!fTree[machine]) fTree[machine] = {};
      const ident = a.identity_dir || a.id;
      if (!fTree[machine][ident]) fTree[machine][ident] = [];
      fTree[machine][ident].push(a);
    });

    const fMachineOrder = Object.keys(fTree).sort((a, b) => {
      if (a === 'chengzigedeAir') return -1;
      if (b === 'chengzigedeAir') return 1;
      return a.localeCompare(b);
    });

    const colorMap = _assignIdentityColors(filtered);

    let html = '';

    // ── 快速条件栏（机器/平台/状态 → 只筛选显示，不自动选中）──
    if (!compact) {
      const machines = [...new Set(allAccts.map(a => a.owner_machine || a._source_machine || '').filter(Boolean))];

      html += `<div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center;margin-bottom:4px">
        <select id="${uid}_machine" onchange="window._asFilter('${uid}')"
          style="padding:3px 6px;font-size:11px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px">
          <option value="">🖥️ 全部机器</option>
          ${machines.map(m => `<option value="${m}">${m}</option>`).join('')}
        </select>
        <select id="${uid}_plat" onchange="window._asFilter('${uid}')"
          style="padding:3px 6px;font-size:11px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px">
          <option value="">🌐 全部平台</option>
          <option value="douyin">🎵 抖音</option>
          <option value="xiaohongshu">📕 小红书</option>
        </select>
        <select id="${uid}_status" onchange="window._asFilter('${uid}')"
          style="padding:3px 6px;font-size:11px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px">
          <option value="">全部状态</option>
          ${STATUS_ORDER.map(k => {
            const cfg = STATUS_CFG[k] || { dot: '⚪', label: k };
            return `<option value="${k}">${cfg.dot} ${cfg.label}</option>`;
          }).join('')}
        </select>
        <button onclick="window._as_selectFiltered('${uid}')"
          style="background:#6366f1;color:#fff;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600">✅ 全选筛选结果</button>
        <span id="${uid}_selCount" style="font-size:11px;color:var(--text2);white-space:nowrap"></span>
      </div>`;

      // ── 搜索栏（进一步缩小显示范围）──
      html += `<div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center;margin-bottom:4px">
        <input id="${uid}_q" placeholder="🔍 搜索账号ID/昵称/手机号"
          oninput="window._asFilter('${uid}')"
          style="flex:1;min-width:80px;padding:3px 6px;font-size:11px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px">
        <span style="font-size:11px;color:var(--text2);white-space:nowrap">共 ${filtered.length} 个</span>
      </div>`;
    }

    // ── 列表体 ──
    html += `<div id="${uid}_body" style="max-height:${opts.height || '350px'};overflow-y:auto">`;

    if (fMachineOrder.length === 0) {
      html += `<div style="padding:12px;text-align:center;color:var(--text2);font-size:11px">无匹配账号</div>`;
    } else {
      fMachineOrder.forEach(machine => {
        const idents = fTree[machine];
        const isLocal = machine === 'chengzigedeAir';
        const grpId = `${uid}_m_${machine.replace(/[^a-zA-Z0-9]/g, '_')}`;
        const totalAccts = Object.values(idents).reduce((s, arr) => s + arr.length, 0);

        // 机器头（可折叠）
        html += `<div style="margin-bottom:2px;border:1px solid var(--border);border-radius:6px;overflow:hidden">`;
        html += `<div onclick="_toggleASGroup('${uid}','${machine}')" style="display:flex;align-items:center;gap:4px;padding:4px 6px;background:var(--bg3);cursor:pointer;font-size:11px;font-weight:600;user-select:none">
          <span id="${grpId}_arrow">▼</span>
          <span>${isLocal ? '🖥️' : '☁️'} ${machine}</span>
          <span style="font-size:10px;color:var(--text2);font-weight:400">${totalAccts} 个</span>
        </div>`;

        // 折叠体
        html += `<div id="${grpId}_body" style="display:block">`;

        // 表头（精简 + 新增身份列）
        html += `<div style="display:flex;align-items:center;padding:2px 6px;font-size:9px;color:var(--text2);border-bottom:1px solid var(--border);background:var(--bg2)">
          <div style="width:22px"><input type="checkbox" id="${grpId}_all" onchange="_toggleGroupAS('${uid}','${machine}')" title="全选本机" ${checkAll ? 'checked' : ''}></div>
          <div style="width:70px;font-weight:400">📁 身份</div>
          <div style="width:95px;font-weight:400">📱 手机号</div>
          <div style="width:90px;font-weight:400">账号</div>
          <div style="flex:1;min-width:100px;font-weight:400">🎵 昵称</div>
          <div style="width:40px;text-align:right;font-weight:400">粉丝</div>
          <div style="width:80px;font-weight:400">状态</div>
        </div>`;

        // 按身份顺序输出
        const identKeys = Object.keys(idents);
        identKeys.forEach(ident => {
          const accts = idents[ident];
          const colorKey = `${machine}::${ident}`;
          const bgColor = colorMap[colorKey] || '#ffffff';
          const borderLeft = `3px solid ${bgColor}`;

          // 身份分隔行（简单分隔线，去掉颜色背景）
          html += `<div style="display:flex;align-items:center;padding:1px 6px;font-size:8px;color:var(--text2);border-bottom:1px dotted var(--border);margin-top:1px">
            <span>📁 ${ident}</span>
            <span style="margin-left:8px">${accts.length} 个账号</span>
          </div>`;

          accts.forEach(a => {
            const st = a.login_status || a._status || 'unknown';
            const platIcon = a.platform === 'xiaohongshu' ? '📕' : '🎵';
            const nick = a.nickname || a._nickname || '';
            const fans = a.fans || a._fans || '';
            const phone = a.phone || '';
            const aidEsc = a.id.replace(/'/g, "\\'");

            html += `<div class="as-row-${uid}" data-account="${a.id}" data-machine="${machine}" data-platform="${a.platform}"
              style="display:flex;align-items:center;padding:3px 6px;font-size:11px;border-bottom:1px solid var(--border);cursor:pointer"
              onclick="window._asToggleDetail('${uid}','${aidEsc}')">`;

            html += `<div style="width:22px"><input type="checkbox" class="as-cb-${uid}" value="${a.id}" data-plat="${a.platform}" data-machine="${machine}" ${checkAll ? 'checked' : ''} onclick="event.stopPropagation();_onASChange('${uid}')"></div>`;
            // 身份列（新增）
            const identShort = (a.identity_dir || a.id).length > 10 ? (a.identity_dir || a.id).slice(0,10)+'…' : (a.identity_dir || a.id);
            html += `<div style="width:70px;font-size:9px;color:var(--text2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${a.identity_dir || a.id}">${identShort}</div>`;
            // 📱手机号列
            html += `<div style="width:95px;font-size:10px;color:var(--text2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${phone || '-'}</div>`;
            // 账号列
            html += `<div style="width:90px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"><strong>${a.id}</strong></div>`;
            // 🎵昵称列
            html += `<div style="flex:1;min-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:10px">${platIcon} ${nick || '-'}</div>`;
            // 粉丝列
            html += `<div style="width:40px;text-align:right;font-size:10px">${fans || '-'}</div>`;
            // 状态列
            html += `<div style="width:80px;font-size:10px">${_statusHtml(st)}</div>`;

            html += `</div>`;
          });
        });

        html += `</div></div>`;
      });
    }

    html += `</div>`;

    // ── 统计行 ──
    if (!compact) {
      html += `<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 4px;font-size:10px;color:var(--text2)">
        <span>共 ${filtered.length} 个账号</span>
        <span id="${uid}_count">已选 ${checkAll ? filtered.length : 0} 个</span>
      </div>`;
    }

    // ── 批量操作栏 ──
    if (showBatchBar) {
      const actionLabels = {
        collect: '📡 采集', login: '🔑 登录',
        nurture: '🏃 养号', comment: '💬 评论',
      };
      html += `<div id="${uid}_batchBar" style="display:none;position:sticky;bottom:0;background:var(--bg2);border:1px solid var(--primary);border-radius:6px;padding:6px 10px;margin-top:4px;align-items:center;gap:6px;flex-wrap:wrap">
        <span id="${uid}_batchCount" style="font-size:11px;font-weight:600"></span>
        ${batchActions.map(act => `<button class="as-batch-btn-${uid}" data-action="${act}" style="background:var(--primary);color:#fff;border:none;padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">${actionLabels[act] || act}</button>`).join('')}
      </div>`;
    }

    el.innerHTML = html;

    // ── 绑定事件 ──
    _refreshCount();
    if (showBatchBar) {
      el.querySelectorAll(`.as-batch-btn-${uid}`).forEach(btn => {
        btn.onclick = (e) => {
          e.stopPropagation();
          _handleBatch(btn.dataset.action);
        };
      });
    }
  }

  // ── 刷新选中计数 ──
  function _refreshCount() {
    const checked = document.querySelectorAll(`.as-cb-${uid}:checked`).length;
    const countEl = document.getElementById(`${uid}_count`);
    if (countEl) countEl.textContent = `已选 ${checked} 个`;
    const selCountEl = document.getElementById(`${uid}_selCount`);
    if (selCountEl) selCountEl.textContent = `已选 ${checked} 个`;

    const batchBar = document.getElementById(`${uid}_batchBar`);
    const batchCount = document.getElementById(`${uid}_batchCount`);
    if (batchBar && batchCount) {
      if (checked > 0) {
        batchBar.style.display = 'flex';
        batchCount.textContent = `已选 ${checked} 个账号`;
      } else {
        batchBar.style.display = 'none';
      }
    }
    if (opts.onSelect) opts.onSelect(_getSelected());
  }

  // ── 获取选中 ──
  function _getSelected() {
    return Array.from(document.querySelectorAll(`.as-cb-${uid}:checked`)).map(cb => ({
      id: cb.value,
      platform: cb.dataset.plat,
      machine: cb.dataset.machine,
      login_status: '',
      nickname: '',
    }));
  }

  // ── 批量操作 ──
  async function _handleBatch(action) {
    const ids = _getSelected().map(s => s.id);
    if (!ids.length) return;

    if (action === 'nurture') {
      _showNurtureDialog(ids);
      return;
    }

    try {
      const r = await fetch('/api/v2/accounts/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_ids: ids, action }),
      });
      const d = await r.json();
      if (d.status === 'ok') {
        alert(`✅ 已提交 ${ids.length} 个账号${action==='collect'?'采集':'登录'}任务`);
        if (opts.onBatchDone) opts.onBatchDone(d);
      } else {
        alert('❌ ' + (d.detail || '操作失败'));
      }
    } catch(e) {
      alert('❌ ' + e.message);
    }
  }

  // ── 养号弹窗 ──
  function _showNurtureDialog(ids) {
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:9999;display:flex;align-items:center;justify-content:center';
    overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };
    overlay.innerHTML = `
      <div style="background:var(--bg2);border-radius:12px;padding:20px;max-width:340px;width:90%">
        <div style="font-size:14px;font-weight:600;margin-bottom:10px">🏃 养号设置</div>
        <div style="font-size:11px;color:var(--text2);margin-bottom:8px">选中 ${ids.length} 个账号</div>
        <div style="display:grid;gap:6px;font-size:12px">
          <label>蓝图 <select id="${uid}_bp" style="width:100%;padding:4px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px">
            <option value="douyin_daily">🎵 douyin_daily</option>
            <option value="xhs_daily">📕 xhs_daily</option>
          </select></label>
          <label>轮次 <input id="${uid}_rounds" type="number" min="1" max="20" value="3" style="width:100%;padding:4px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px"></label>
        </div>
        <div style="display:flex;gap:6px;justify-content:flex-end;margin-top:10px">
          <button onclick="this.closest('div[style]').parentElement.remove()" style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:5px 14px;font-size:11px;cursor:pointer">取消</button>
          <button id="${uid}_nurtureOk" style="background:var(--primary);color:#fff;border:none;border-radius:6px;padding:5px 14px;font-size:11px;cursor:pointer">✅ 开始</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.querySelector(`#${uid}_nurtureOk`).onclick = async () => {
      const blueprint = document.getElementById(`${uid}_bp`).value;
      const rounds = parseInt(document.getElementById(`${uid}_rounds`).value) || 3;
      try {
        const r = await fetch('/api/v2/accounts/batch', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ account_ids: ids, action: 'nurture', params: { blueprint, rounds } }),
        });
        const d = await r.json();
        if (d.status === 'ok') {
          alert(`✅ 已提交 ${ids.length} 个账号养号`);
          overlay.remove();
          if (opts.onBatchDone) opts.onBatchDone(d);
        } else {
          alert('❌ ' + (d.detail || '操作失败'));
        }
      } catch(e) { alert('❌ ' + e.message); }
    };
  }

  // ── 全选筛选结果：勾选当前筛选条件下所有可见账号 ──
  window._as_selectFiltered = (u) => {
    if (u !== uid) return;
    document.querySelectorAll(`.as-cb-${uid}`).forEach(cb => cb.checked = true);
    // 同时勾选各机器全选框
    document.querySelectorAll(`[id^="${uid}_m_"][id$="_all"]`).forEach(cb => cb.checked = true);
    _refreshCount();
  };

  // ── 全局函数 ──
  window._asFilter = (u) => {
    if (u !== uid) return;
    _filterQ = (document.getElementById(`${uid}_q`)?.value || '').trim();
    _filterMachine = document.getElementById(`${uid}_machine`)?.value || '';
    _filterPlatform = document.getElementById(`${uid}_plat`)?.value || '';
    _filterStatus = document.getElementById(`${uid}_status`)?.value || '';
    _render();
  };

  window._asToggleDetail = (u, id) => {
    if (u !== uid) return;
    const el = document.getElementById(`${uid}_detail_${id}`);
    if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
  };

  window._onASChange = (u) => {
    if (u !== uid) return;
    _refreshCount();
  };

  window._toggleASGroup = (u, machine) => {
    if (u !== uid) return;
    const grpId = `${uid}_m_${machine.replace(/[^a-zA-Z0-9]/g, '_')}`;
    const body = document.getElementById(`${grpId}_body`);
    const arrow = document.getElementById(`${grpId}_arrow`);
    if (body && arrow) {
      const isHidden = body.style.display === 'none';
      body.style.display = isHidden ? 'block' : 'none';
      arrow.textContent = isHidden ? '▼' : '▶';
    }
  };

  window._toggleGroupAS = (u, machine) => {
    if (u !== uid) return;
    const grpId = `${uid}_m_${machine.replace(/[^a-zA-Z0-9]/g, '_')}`;
    const allCb = document.getElementById(`${grpId}_all`);
    const checked = allCb?.checked || false;
    document.querySelectorAll(`#${grpId}_body .as-cb-${uid}`).forEach(cb => cb.checked = checked);
    _refreshCount();
  };

  // ── 初始渲染 ──
  _render();

  // ── 返回 API（完全兼容 v2）──
  return {
    uid,
    el,
    getSelected() {
      return _getSelected();
    },
    getCount() {
      return document.querySelectorAll(`.as-cb-${uid}:checked`).length;
    },
    selectAll(checked) {
      document.querySelectorAll(`.as-cb-${uid}`).forEach(cb => cb.checked = !!checked);
      _refreshCount();
      if (opts.onSelect) opts.onSelect(this.getSelected());
    },
    destroy() {
      el.innerHTML = '';
    },
  };
}
